#!/usr/bin/env python3
"""Optimized external runner for wait-time recalculation.

This script keeps the current methodology from
`01_processing/06_recalculo_tiempos_espera.qmd` but moves the heavy row-wise
loop to a standalone CLI with precomputed indexes and caches.

Key optimizations:
- preserve batch processing, but avoid building row dicts;
- precompute GTFS coverage/order/frequency indexes once;
- cache structural Metro stage metadata by (subida, bajada, servicio);
- cache temporal Metro stage results by (stage, date, second-of-day);
- cache shortest same-line Metro paths by (route_id, origen, destino);
- append computed columns to each batch directly, then write batch parquet files.
- drop rows that are not model-ready because they contain stage blocks without
  identified service or non-contiguous stage structure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Iterable

import networkx as nx
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.gtfs_manifest import build_manifest, pick_version_for_date
from lib.transbordos_metro.metro_graph_builder import (
    base_line_code,
    matching_line_ids,
    normalize_station_name,
)


DAY_COLS = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday",
    5: "saturday",
    6: "sunday",
}


LOGIC_SEMANTICS = {
    "model_ready_filter_version": "v5",
    "bus_wait_formula": "3600/freq_buses_h",
    "metro_wait_formula": "headway_equiv/2",
    "stage_time_imputation": "prev_travel+observed_tc_or_fallback",
    "transfer_fallback_seconds": 170.0,
    "gtfs_station_normalization": "accent_insensitive_strip_direccion",
    "drop_rules": [
        "missing_stage_service",
        "non_contiguous_stage_blocks",
        "block_count_mismatch",
        "orig_gt4",
        "recon_gt4",
    ],
}
LOGIC_HASH = hashlib.sha256(
    json.dumps(LOGIC_SEMANTICS, sort_keys=True).encode("utf-8")
).hexdigest()


@dataclass(frozen=True)
class StageStructure:
    sub_n: str
    baj_n: str
    line_decl: str
    candidate_line_ids: tuple[str, ...]
    structural_variants: tuple[str, ...]
    valid_dirs: tuple[int, ...]
    variants_by_dir: tuple[tuple[str, ...], tuple[str, ...]]


@dataclass(frozen=True)
class StageRuntime:
    records: tuple[tuple[str, int, float], ...]  # (route_id, direction, headway_min)
    variants_used: tuple[str, ...]
    h_eq: float | None
    conflict: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition", required=True, help="ISO partition label, e.g. 2024-W17")
    parser.add_argument("--batch-size", type=int, default=200_000)
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit for smoke tests")
    parser.add_argument(
        "--gtfs-root",
        type=Path,
        default=None,
        help="Optional GTFS root override. Default: config/GTFS",
    )
    parser.add_argument(
        "--graph-dir",
        type=Path,
        default=None,
        help="Optional Metro graph directory override. Default: 01_processing/metro_graphs",
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=None,
        help="Input parquet. Default: 01_processing/tmp/etapas_reconstruidas_<partition>.parquet",
    )
    parser.add_argument(
        "--freq-path",
        type=Path,
        default=None,
        help="Bus frequency parquet. Default: tmp/frecuencias_buses_<partition>.parquet",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Output parquet. Default: tmp/viajes_con_te_calculado_<partition>.parquet",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=None,
        help="Temporary directory for batch parquet files",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing temp batch directory and manifest.",
    )
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Skip computation and only merge existing batch parquet files into the final output.",
    )
    return parser.parse_args()


def partition_start_date(partition: str) -> date:
    year_s, week_s = partition.split("-W")
    return date.fromisocalendar(int(year_s), int(week_s), 1)


def yyyymmdd(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def read_gtfs_csv(path: Path, schema_overrides: dict[str, pl.DataType]) -> pl.DataFrame:
    return pl.read_csv(
        path,
        schema_overrides=schema_overrides,
        infer_schema_length=10_000,
        truncate_ragged_lines=True,
    )


def parse_hms_to_seconds(raw: str | None) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text == "24:00:00":
        text = "23:59:59"
    try:
        hh, mm, ss = map(int, text.split(":"))
        return (hh % 24) * 3600 + mm * 60 + ss
    except Exception:
        return None


def parse_time_str(value) -> dtime | None:
    if value is None:
        return None
    if isinstance(value, dtime):
        return value
    if isinstance(value, datetime):
        return value.time()
    if hasattr(value, "hour") and hasattr(value, "minute") and hasattr(value, "second") and not isinstance(value, str):
        return dtime(value.hour, value.minute, value.second)
    sec = parse_hms_to_seconds(str(value))
    if sec is None:
        return None
    return dtime((sec // 3600) % 24, (sec % 3600) // 60, sec % 60)


def parse_stage_datetime(value, default_date: date | None = None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, dtime(0, 0, 0))

    raw = str(value).strip()
    if not raw:
        return None

    if "T" in raw or " " in raw[:19]:
        try:
            return datetime.fromisoformat(raw.replace("T", " "))
        except Exception:
            pass

    rolled_day = False
    if raw.startswith("24:"):
        raw = f"00:{raw[3:]}"
        rolled_day = True

    clock = parse_time_str(raw)
    if clock is None or default_date is None:
        return None
    dt_value = datetime.combine(default_date, clock)
    if rolled_day:
        dt_value += timedelta(days=1)
    return dt_value


TRANSFER_FALLBACK_SECONDS = float(LOGIC_SEMANTICS["transfer_fallback_seconds"])


def observed_transfer_seconds_from_row(
    row: tuple, idx: dict[str, int], stage_num: int
) -> float | None:
    if stage_num <= 1:
        return None
    tc_col = f"tc{stage_num - 1}"
    if tc_col not in idx:
        return None
    raw = row[idx[tc_col]]
    if raw is None:
        return None
    try:
        value = float(raw)
    except Exception:
        return None
    return value if value > 0 else None


def parse_service_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("T", " ")).date()
    except Exception:
        pass
    try:
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def observed_duration_seconds(start_value, end_value, default_date: date | None) -> float | None:
    start_dt = parse_stage_datetime(start_value, default_date)
    if start_dt is None:
        return None
    end_dt = parse_stage_datetime(end_value, start_dt.date())
    if end_dt is None:
        return None
    if end_dt < start_dt and " " not in str(end_value) and "T" not in str(end_value):
        end_dt += timedelta(days=1)
    delta = (end_dt - start_dt).total_seconds()
    return delta if delta >= 0 else None


def load_graph(graph_dir: Path, folder: str) -> nx.Graph:
    graph_path = graph_dir / f"metro_graph_{folder}.gpickle"
    with open(graph_path, "rb") as handle:
        return pickle.load(handle)


def list_batch_paths(temp_dir: Path) -> list[Path]:
    return sorted(temp_dir.glob("batch_*.parquet"))


def manifest_path_for(temp_dir: Path) -> Path:
    return temp_dir / "manifest.json"


def save_manifest(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def load_manifest(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def finalize_batches(temp_dir: Path, output_path: Path) -> None:
    batch_paths = list_batch_paths(temp_dir)
    if not batch_paths:
        raise FileNotFoundError(f"No batch parquet files found in {temp_dir}")
    print(f"Uniendo {len(batch_paths)} batch files -> {output_path}")
    pl.scan_parquet([str(path) for path in batch_paths]).sink_parquet(output_path)
    print(f"Finalizado: {output_path}")


def build_stage_quality_exprs(
    schema_names: set[str], max_stages: int = 6
) -> tuple[pl.Expr, pl.Expr, pl.Expr, dict[str, pl.Expr]]:
    block_exprs: dict[str, pl.Expr] = {}
    for stage_num in range(1, max_stages + 1):
        present_checks: list[pl.Expr] = []
        for base in (
            "srv",
            "tipo_transporte",
            "paradero_subida",
            "paradero_bajada",
            "tiempo_subida",
            "tiempo_bajada",
            "zona_subida",
            "zona_bajada",
        ):
            col = f"{base}_{stage_num}"
            if col in schema_names:
                present_checks.append(pl.col(col).is_not_null())
        block_exprs[f"block_{stage_num}"] = pl.any_horizontal(present_checks) if present_checks else pl.lit(False)

    missing_service_terms: list[pl.Expr] = []
    for stage_num in range(1, max_stages + 1):
        srv_col = f"srv_{stage_num}"
        block_expr = block_exprs[f"block_{stage_num}"]
        if srv_col in schema_names:
            missing_service_terms.append(block_expr & pl.col(srv_col).is_null())

    contig_terms: list[pl.Expr] = []
    for stage_num in range(1, max_stages):
        later_blocks = [block_exprs[f"block_{j}"] for j in range(stage_num + 1, max_stages + 1)]
        contig_terms.append((~block_exprs[f"block_{stage_num}"]) & pl.any_horizontal(later_blocks))

    block_count = sum(block_exprs[f"block_{stage_num}"].cast(pl.Int8) for stage_num in range(1, max_stages + 1))
    has_missing_service = pl.any_horizontal(missing_service_terms) if missing_service_terms else pl.lit(False)
    has_non_contiguous_blocks = pl.any_horizontal(contig_terms) if contig_terms else pl.lit(False)
    has_block_count_mismatch = (
        (block_count != pl.col("n_etapas_recon")) if "n_etapas_recon" in schema_names else pl.lit(False)
    )
    return has_missing_service, has_non_contiguous_blocks, has_block_count_mismatch, block_exprs


def filter_model_ready_rows(batch: pl.DataFrame, max_stages: int = 6) -> tuple[pl.DataFrame, dict[str, int]]:
    schema_names = set(batch.columns)
    missing_service_expr, non_contiguous_expr, block_mismatch_expr, _ = build_stage_quality_exprs(
        schema_names, max_stages=max_stages
    )
    orig_gt4_expr = (pl.col("n_etapas") > 4) if "n_etapas" in schema_names else pl.lit(False)
    recon_gt4_expr = (pl.col("n_etapas_recon") > 4) if "n_etapas_recon" in schema_names else pl.lit(False)
    audited = batch.with_columns(
        [
            missing_service_expr.alias("__drop_missing_stage_service"),
            non_contiguous_expr.alias("__drop_non_contiguous_stage_blocks"),
            block_mismatch_expr.alias("__drop_block_count_mismatch"),
            orig_gt4_expr.alias("__drop_orig_gt4"),
            recon_gt4_expr.alias("__drop_recon_gt4"),
        ]
    )
    stats = audited.select(
        [
            pl.len().alias("rows_in"),
            pl.col("__drop_missing_stage_service").sum().alias("drop_missing_stage_service"),
            pl.col("__drop_non_contiguous_stage_blocks").sum().alias("drop_non_contiguous_stage_blocks"),
            pl.col("__drop_block_count_mismatch").sum().alias("drop_block_count_mismatch"),
            pl.col("__drop_orig_gt4").sum().alias("drop_orig_gt4"),
            pl.col("__drop_recon_gt4").sum().alias("drop_recon_gt4"),
            (
                pl.col("__drop_missing_stage_service")
                | pl.col("__drop_non_contiguous_stage_blocks")
                | pl.col("__drop_block_count_mismatch")
                | pl.col("__drop_orig_gt4")
                | pl.col("__drop_recon_gt4")
            )
            .sum()
            .alias("rows_dropped"),
        ]
    ).row(0, named=True)
    filtered = audited.filter(
        ~(
            pl.col("__drop_missing_stage_service")
            | pl.col("__drop_non_contiguous_stage_blocks")
            | pl.col("__drop_block_count_mismatch")
            | pl.col("__drop_orig_gt4")
            | pl.col("__drop_recon_gt4")
        )
    ).drop(
        [
            "__drop_missing_stage_service",
            "__drop_non_contiguous_stage_blocks",
            "__drop_block_count_mismatch",
            "__drop_orig_gt4",
            "__drop_recon_gt4",
        ]
    )
    stats["rows_out"] = filtered.height
    return filtered, {key: int(value) for key, value in stats.items()}


class WaitTimeEngine:
    def __init__(
        self,
        project_root: Path,
        partition_label: str,
        partition_start: date,
        input_path: Path,
        freq_path: Path,
        gtfs_root: Path | None = None,
        graph_dir: Path | None = None,
    ) -> None:
        self.project_root = project_root
        self.partition_label = partition_label
        self.partition_start = partition_start
        self.input_path = input_path
        self.freq_path = freq_path
        self.gtfs_root = gtfs_root or (project_root / "config" / "GTFS")
        self.graph_dir = graph_dir or (project_root / "01_processing" / "metro_graphs")

        self.manifest = build_manifest(self.gtfs_root)
        if not self.manifest:
            raise FileNotFoundError(f"No GTFS versions found in {self.gtfs_root}")
        week_service_dates = [partition_start + timedelta(days=offset) for offset in range(7)]
        versions_in_week = {d: pick_version_for_date(d, self.manifest) for d in week_service_dates}
        missing_versions = [d for d, version in versions_in_week.items() if version is None]
        if missing_versions:
            raise ValueError(
                f"No GTFS version found for all dates in {partition_label}: {missing_versions}"
            )
        week_gtfs_folders = sorted({version.folder for version in versions_in_week.values() if version is not None})
        if len(week_gtfs_folders) != 1:
            raise ValueError(
                f"The week {partition_label} spans multiple GTFS versions {week_gtfs_folders}. "
                "The runner assumes a single GTFS version per ISO week."
            )
        self.version = versions_in_week[partition_start]
        if self.version is None:
            raise ValueError(f"No GTFS version found for partition {partition_label}")

        self.graph = load_graph(self.graph_dir, self.version.folder)
        self._build_gtfs_indexes()
        self._build_bus_indexes()
        self._build_graph_indexes()

        self.service_ids_cache: dict[date, frozenset[str]] = {}
        self.active_intervals_cache: dict[tuple[str, int, date], tuple[tuple[int, int, float], ...]] = {}
        self.stage_structure_cache: dict[tuple[str, str, str], StageStructure] = {}
        self.stage_runtime_cache: dict[tuple[str, str, str, int | None, date], StageRuntime] = {}
        self.metro_path_cache: dict[tuple[str, str, str], float | None] = {}

    def _build_gtfs_indexes(self) -> None:
        gtfs_dir = self.version.path
        routes = read_gtfs_csv(
            gtfs_dir / "routes.txt",
            schema_overrides={
                "route_id": pl.Utf8,
                "route_type": pl.Int64,
                "route_short_name": pl.Utf8,
            },
        )
        self.routes_metro = routes.filter(pl.col("route_type") == 1)
        self.metro_route_ids = sorted(self.routes_metro["route_id"].to_list())
        self.metro_base_codes = {base_line_code(rid) for rid in self.metro_route_ids}

        trips = read_gtfs_csv(
            gtfs_dir / "trips.txt",
            schema_overrides={
                "route_id": pl.Utf8,
                "trip_id": pl.Utf8,
                "service_id": pl.Utf8,
                "direction_id": pl.Int64,
            },
        )
        self.trips_metro = trips.filter(pl.col("route_id").is_in(self.metro_route_ids))

        self.calendar = read_gtfs_csv(
            gtfs_dir / "calendar.txt",
            schema_overrides={
                "service_id": pl.Utf8,
                "monday": pl.Int64,
                "tuesday": pl.Int64,
                "wednesday": pl.Int64,
                "thursday": pl.Int64,
                "friday": pl.Int64,
                "saturday": pl.Int64,
                "sunday": pl.Int64,
                "start_date": pl.Int64,
                "end_date": pl.Int64,
            },
        )
        calendar_dates_path = gtfs_dir / "calendar_dates.txt"
        if calendar_dates_path.exists():
            self.calendar_dates = read_gtfs_csv(
                calendar_dates_path,
                schema_overrides={
                    "service_id": pl.Utf8,
                    "date": pl.Int64,
                    "exception_type": pl.Int64,
                },
            )
        else:
            self.calendar_dates = pl.DataFrame(schema={"service_id": pl.Utf8, "date": pl.Int64, "exception_type": pl.Int64})

        freq = read_gtfs_csv(
            gtfs_dir / "frequencies.txt",
            schema_overrides={
                "trip_id": pl.Utf8,
                "start_time": pl.Utf8,
                "end_time": pl.Utf8,
                "headway_secs": pl.Int64,
            },
        )
        freq = freq.with_columns(
            pl.col("start_time").map_elements(parse_hms_to_seconds, return_dtype=pl.Int64).alias("start_sec"),
            pl.col("end_time").map_elements(parse_hms_to_seconds, return_dtype=pl.Int64).alias("end_sec"),
            (pl.col("headway_secs") / 60.0).alias("headway_min"),
        )
        freq_join = freq.join(
            self.trips_metro.select(["trip_id", "route_id", "service_id", "direction_id"]),
            on="trip_id",
            how="inner",
        )
        self.freq_rows_by_route_service_dir: dict[tuple[str, str, int], tuple[tuple[int, int, float], ...]] = {}
        for row in (
            freq_join.select(["route_id", "service_id", "direction_id", "start_sec", "end_sec", "headway_min"])
            .iter_rows()
        ):
            rid, sid, direction, start_sec, end_sec, headway_min = row
            key = (rid, sid, int(direction))
            self.freq_rows_by_route_service_dir.setdefault(key, [])
            if start_sec is not None and end_sec is not None and headway_min is not None:
                self.freq_rows_by_route_service_dir[key].append((int(start_sec), int(end_sec), float(headway_min)))
        self.freq_rows_by_route_service_dir = {
            key: tuple(value) for key, value in self.freq_rows_by_route_service_dir.items()
        }

        stops = read_gtfs_csv(
            gtfs_dir / "stops.txt",
            schema_overrides={
                "stop_id": pl.Utf8,
                "stop_name": pl.Utf8,
                "wheelchair_boarding": pl.Utf8,
            },
        )
        stop_times = read_gtfs_csv(
            gtfs_dir / "stop_times.txt",
            schema_overrides={
                "trip_id": pl.Utf8,
                "stop_id": pl.Utf8,
                "stop_sequence": pl.Int64,
            },
        )
        stop_times_metro = (
            stop_times.join(self.trips_metro.select(["trip_id", "route_id", "direction_id"]), on="trip_id", how="inner")
            .join(stops.select(["stop_id", "stop_name"]), on="stop_id", how="left")
            .with_columns(
                pl.col("stop_name")
                .map_elements(self.station_from_stop_name, return_dtype=pl.Utf8)
                .alias("station_norm")
            )
        )

        coverage_rows = (
            stop_times_metro.select(["route_id", "direction_id", "station_norm"])
            .unique()
            .iter_rows()
        )
        self.coverage_by_route_dir: dict[tuple[str, int], frozenset[str]] = {}
        for rid, direction, station_norm in coverage_rows:
            key = (rid, int(direction))
            self.coverage_by_route_dir.setdefault(key, set()).add(station_norm)
        self.coverage_by_route_dir = {
            key: frozenset(value) for key, value in self.coverage_by_route_dir.items()
        }

        order_rows = (
            stop_times_metro
            .group_by(["route_id", "direction_id", "station_norm"])
            .agg(pl.col("stop_sequence").min().alias("min_stop_sequence"))
            .iter_rows()
        )
        self.order_by_route_dir_station: dict[tuple[str, int, str], int] = {}
        for rid, direction, station_norm, min_seq in order_rows:
            self.order_by_route_dir_station[(rid, int(direction), station_norm)] = int(min_seq)

    def _build_bus_indexes(self) -> None:
        if not self.freq_path.exists():
            self.freq_bus_dict = {}
            return
        freq_buses = pl.read_parquet(self.freq_path)
        self.freq_bus_dict: dict[tuple[str, str, date, int], float] = {}
        for par, srv, hour_start, freq_h in freq_buses.select(
            ["Paradero", "ServicioSentido", "hour_start", "freq_buses_h"]
        ).iter_rows():
            if hour_start is None:
                continue
            self.freq_bus_dict[(par, srv, hour_start.date(), hour_start.hour)] = float(freq_h)

    def _build_graph_indexes(self) -> None:
        self.line_subgraphs: dict[str, nx.Graph] = {}
        nodes_by_line: dict[str, list[tuple[str, str]]] = {}
        for node in self.graph.nodes:
            nodes_by_line.setdefault(node[1], []).append(node)
        for route_id, line_nodes in nodes_by_line.items():
            self.line_subgraphs[route_id] = self.graph.subgraph(line_nodes).copy()

    @staticmethod
    def station_from_stop_name(name: str) -> str:
        if name is None:
            return ""
        import re
        import unicodedata

        text = str(name)
        text_ascii = "".join(
            c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
        )
        base = re.sub(r"(?i)\s*DIRECCION.*$", "", text_ascii).strip()
        base = re.sub(r"(?i)\s+DIR\s+.*$", "", base).strip()
        base = base.replace("(M)", "").replace("(m)", "").strip()
        return normalize_station_name(base)

    def active_service_ids_for_date(self, service_date: date) -> frozenset[str]:
        cached = self.service_ids_cache.get(service_date)
        if cached is not None:
            return cached
        day_col = DAY_COLS[service_date.weekday()]
        active = set(
            self.calendar.filter(
                (pl.col(day_col) == 1)
                & (pl.col("start_date") <= yyyymmdd(service_date))
                & (pl.col("end_date") >= yyyymmdd(service_date))
            )["service_id"].to_list()
        )
        if self.calendar_dates.height > 0:
            exceptions = self.calendar_dates.filter(pl.col("date") == yyyymmdd(service_date))
            added = set(exceptions.filter(pl.col("exception_type") == 1)["service_id"].to_list())
            removed = set(exceptions.filter(pl.col("exception_type") == 2)["service_id"].to_list())
            active = (active | added) - removed
        result = frozenset(active)
        self.service_ids_cache[service_date] = result
        return result

    def active_intervals_for_variant(self, route_id: str, direction: int, service_date: date) -> tuple[tuple[int, int, float], ...]:
        key = (route_id, direction, service_date)
        cached = self.active_intervals_cache.get(key)
        if cached is not None:
            return cached
        intervals: list[tuple[int, int, float]] = []
        for service_id in self.active_service_ids_for_date(service_date):
            intervals.extend(self.freq_rows_by_route_service_dir.get((route_id, service_id, direction), ()))
        result = tuple(intervals)
        self.active_intervals_cache[key] = result
        return result

    def variants_covering(self, station_sub: str, station_baj: str, line_decl: str, direction: int) -> tuple[str, ...]:
        candidates = matching_line_ids(line_decl, self.metro_route_ids)
        valid = []
        for rid in candidates:
            coverage = self.coverage_by_route_dir.get((rid, direction))
            if coverage and station_sub in coverage and station_baj in coverage:
                valid.append(rid)
        return tuple(sorted(valid))

    def valid_directions_by_order(self, station_sub: str, station_baj: str, line_decl: str) -> tuple[int, ...]:
        dirs_valid: list[int] = []
        for direction in (0, 1):
            variants = self.variants_covering(station_sub, station_baj, line_decl, direction)
            for rid in variants:
                sub_seq = self.order_by_route_dir_station.get((rid, direction, station_sub))
                baj_seq = self.order_by_route_dir_station.get((rid, direction, station_baj))
                if sub_seq is not None and baj_seq is not None and sub_seq < baj_seq:
                    dirs_valid.append(direction)
                    break
        return tuple(sorted(set(dirs_valid)))

    def stage_structure(self, sub: str | None, baj: str | None, srv: str | None) -> StageStructure | None:
        if not sub or not baj or not srv:
            return None
        key = (str(sub), str(baj), str(srv).strip().upper())
        cached = self.stage_structure_cache.get(key)
        if cached is not None:
            return cached

        sub_n = normalize_station_name(sub)
        baj_n = normalize_station_name(baj)
        line_decl = str(srv).strip().upper()
        candidates = tuple(matching_line_ids(line_decl, self.metro_route_ids))
        variants_by_dir = (
            self.variants_covering(sub_n, baj_n, line_decl, 0),
            self.variants_covering(sub_n, baj_n, line_decl, 1),
        )
        structural_variants = tuple(sorted(set(variants_by_dir[0]) | set(variants_by_dir[1])))
        valid_dirs = self.valid_directions_by_order(sub_n, baj_n, line_decl)
        stage = StageStructure(
            sub_n=sub_n,
            baj_n=baj_n,
            line_decl=line_decl,
            candidate_line_ids=candidates,
            structural_variants=structural_variants,
            valid_dirs=valid_dirs,
            variants_by_dir=variants_by_dir,
        )
        self.stage_structure_cache[key] = stage
        return stage

    @staticmethod
    def variant_headway_minutes(intervals: Iterable[tuple[int, int, float]], hour_sec: int | None) -> float | None:
        if hour_sec is None:
            return None
        intervals = list(intervals)
        if not intervals:
            return None
        current = [headway for start, end, headway in intervals if start <= hour_sec < end and headway > 0]
        if current:
            freq_sum = sum(1.0 / headway for headway in current)
            return None if freq_sum == 0 else 1.0 / freq_sum
        nearest = min(intervals, key=lambda item: min(abs(item[0] - hour_sec), abs(item[1] - hour_sec)))
        return nearest[2] if nearest[2] > 0 else None

    def stage_runtime(self, stage: StageStructure | None, hour_sec: int | None, service_date: date) -> StageRuntime:
        if stage is None:
            return StageRuntime(records=(), variants_used=(), h_eq=None, conflict=False)

        runtime_key = (stage.sub_n, stage.baj_n, stage.line_decl, hour_sec, service_date)
        cached = self.stage_runtime_cache.get(runtime_key)
        if cached is not None:
            return cached

        directions = stage.valid_dirs or tuple(
            direction for direction in (0, 1) if stage.variants_by_dir[direction]
        )
        records: list[tuple[str, int, float]] = []
        for direction in directions:
            for rid in stage.variants_by_dir[direction]:
                headway_min = self.variant_headway_minutes(
                    self.active_intervals_for_variant(rid, direction, service_date),
                    hour_sec,
                )
                if headway_min is None:
                    continue
                records.append((rid, direction, headway_min))

        if records:
            freq_sum = sum(1.0 / headway for _, _, headway in records if headway > 0)
            h_eq = None if freq_sum == 0 else 1.0 / freq_sum
            variants_used = tuple(sorted({rid for rid, _, _ in records}))
        else:
            h_eq = None
            variants_used = ()

        conflict = len(stage.candidate_line_ids) > 1 and bool(stage.structural_variants) and not bool(records)
        runtime = StageRuntime(records=tuple(records), variants_used=variants_used, h_eq=h_eq, conflict=conflict)
        self.stage_runtime_cache[runtime_key] = runtime
        return runtime

    def shortest_same_line_seconds(self, route_id: str, origen: str, destino: str) -> float | None:
        start_station = normalize_station_name(origen)
        end_station = normalize_station_name(destino)
        cache_key = (route_id, start_station, end_station)
        if cache_key in self.metro_path_cache:
            return self.metro_path_cache[cache_key]

        graph = self.line_subgraphs.get(route_id)
        start = (start_station, route_id)
        end = (end_station, route_id)
        if graph is None or start not in graph or end not in graph:
            self.metro_path_cache[cache_key] = None
            return None
        try:
            dist_min = nx.shortest_path_length(graph, start, end, weight="weight")
        except nx.NetworkXNoPath:
            dist_min = None
        result = None if dist_min is None else float(dist_min) * 60.0
        self.metro_path_cache[cache_key] = result
        return result

    def get_bus_freq(self, paradero, servicio, hora_dt: datetime | None) -> float | None:
        if not paradero or not servicio or hora_dt is None:
            return None
        return self.freq_bus_dict.get((paradero, servicio, hora_dt.date(), hora_dt.hour))

    @staticmethod
    def wt_bus_seconds(freq_h: float | None) -> float | None:
        if freq_h is None or freq_h <= 0:
            return None
        return 3600.0 / freq_h

    def infer_service_date(self, row: tuple, idx: dict[str, int]) -> date:
        for col in ("fecha", "tiempo_subida_1", "tiempo_inicio_viaje"):
            if col in idx:
                parsed = parse_service_date(row[idx[col]])
                if parsed is not None:
                    return parsed
        return self.partition_start

    def is_metro_stage(self, srv, tipo) -> bool:
        srv_upper = str(srv).strip().upper() if srv is not None else ""
        tipo_str = str(tipo) if tipo is not None else ""
        return tipo_str == "2" or base_line_code(srv_upper) in self.metro_base_codes

    def process_batch(self, batch: pl.DataFrame) -> pl.DataFrame:
        idx = {name: pos for pos, name in enumerate(batch.columns)}
        n_rows = batch.height

        waits = [[None] * n_rows for _ in range(6)]
        travel = [[None] * n_rows for _ in range(6)]
        conflicts = [[False] * n_rows for _ in range(6)]

        for row_idx, row in enumerate(batch.iter_rows()):
            service_date = self.infer_service_date(row, idx)
            stage_datetimes: list[datetime | None] = [None] * 6
            local_waits: list[float | None] = [None] * 6
            local_travel: list[float | None] = [None] * 6
            local_conflicts: list[bool] = [False] * 6

            for stage_num in range(1, 7):
                srv_col = f"srv_{stage_num}"
                tipo_col = f"tipo_transporte_{stage_num}"
                subida_col = f"paradero_subida_{stage_num}"
                bajada_col = f"paradero_bajada_{stage_num}"
                t_subida_col = f"tiempo_subida_{stage_num}"
                t_bajada_col = f"tiempo_bajada_{stage_num}"
                if srv_col not in idx:
                    continue

                srv = row[idx[srv_col]]
                if not srv:
                    continue

                tipo = row[idx[tipo_col]] if tipo_col in idx else None
                subida = row[idx[subida_col]] if subida_col in idx else None
                bajada = row[idx[bajada_col]] if bajada_col in idx else None
                stage_ix = stage_num - 1

                if stage_num == 1:
                    current_dt = parse_stage_datetime(row[idx[t_subida_col]] if t_subida_col in idx else None, service_date)
                    stage_datetimes[stage_ix] = current_dt
                else:
                    default_stage_date = stage_datetimes[stage_ix - 1].date() if stage_datetimes[stage_ix - 1] is not None else service_date
                    current_dt = parse_stage_datetime(row[idx[t_subida_col]] if t_subida_col in idx else None, default_stage_date)
                    if current_dt is None and stage_datetimes[stage_ix - 1] is not None:
                        prev_dt = stage_datetimes[stage_ix - 1]
                        prev_travel = local_travel[stage_ix - 1] or 0.0
                        transfer_seconds = (
                            observed_transfer_seconds_from_row(row, idx, stage_num)
                            or TRANSFER_FALLBACK_SECONDS
                        )
                        current_dt = prev_dt + timedelta(seconds=prev_travel + transfer_seconds)
                    stage_datetimes[stage_ix] = current_dt

                current_service_date = current_dt.date() if current_dt is not None else service_date
                hour_sec = None if current_dt is None else (current_dt.hour * 3600 + current_dt.minute * 60 + current_dt.second)

                if self.is_metro_stage(srv, tipo):
                    stage_struct = self.stage_structure(subida, bajada, srv)
                    runtime = self.stage_runtime(stage_struct, hour_sec, current_service_date)
                    if runtime.h_eq is not None:
                        local_waits[stage_ix] = runtime.h_eq / 2.0 * 60.0
                    local_conflicts[stage_ix] = runtime.conflict

                    weighted_terms: list[tuple[float, float]] = []
                    for route_id, _direction, headway_min in runtime.records:
                        tv_seconds = self.shortest_same_line_seconds(route_id, subida, bajada)
                        if tv_seconds is None or headway_min <= 0:
                            continue
                        weighted_terms.append((1.0 / headway_min, tv_seconds))
                    if weighted_terms:
                        lambda_sum = sum(weight for weight, _ in weighted_terms)
                        local_travel[stage_ix] = sum(weight * tv for weight, tv in weighted_terms) / lambda_sum
                elif str(tipo) in ("1", "3"):
                    local_waits[stage_ix] = self.wt_bus_seconds(self.get_bus_freq(subida, srv, current_dt))
                    local_travel[stage_ix] = observed_duration_seconds(
                        row[idx[t_subida_col]] if t_subida_col in idx else None,
                        row[idx[t_bajada_col]] if t_bajada_col in idx else None,
                        current_service_date,
                    )

            for stage_ix in range(6):
                waits[stage_ix][row_idx] = local_waits[stage_ix]
                travel[stage_ix][row_idx] = local_travel[stage_ix]
                conflicts[stage_ix][row_idx] = local_conflicts[stage_ix]

        extra = {
            "te0_calculado": waits[0],
            "te1_calculado": waits[1],
            "te2_calculado": waits[2],
            "te3_calculado": waits[3],
            "te4_calculado": waits[4],
            "te5_calculado": waits[5],
            "tv1_calculado": travel[0],
            "tv2_calculado": travel[1],
            "tv3_calculado": travel[2],
            "tv4_calculado": travel[3],
            "tv5_calculado": travel[4],
            "tv6_calculado": travel[5],
            "metro_variant_conflict_1": conflicts[0],
            "metro_variant_conflict_2": conflicts[1],
            "metro_variant_conflict_3": conflicts[2],
            "metro_variant_conflict_4": conflicts[3],
            "metro_variant_conflict_5": conflicts[4],
            "metro_variant_conflict_6": conflicts[5],
        }
        extra_df = pl.DataFrame(
            {
                name: pl.Series(
                    name,
                    values,
                    dtype=pl.Boolean if name.startswith("metro_variant_conflict_") else pl.Float64,
                )
                for name, values in extra.items()
            }
        )
        return batch.hstack(extra_df)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = parse_args()

    partition = args.partition
    partition_start = partition_start_date(partition)
    gtfs_root = args.gtfs_root or (PROJECT_ROOT / "config" / "GTFS")
    graph_dir = args.graph_dir or (PROJECT_ROOT / "01_processing" / "metro_graphs")
    input_path = args.input_path or (PROJECT_ROOT / "01_processing" / "tmp" / f"etapas_reconstruidas_{partition}.parquet")
    freq_path = args.freq_path or (PROJECT_ROOT / "tmp" / f"frecuencias_buses_{partition}.parquet")
    output_path = args.output_path or (PROJECT_ROOT / "tmp" / f"viajes_con_te_calculado_{partition}.parquet")
    temp_dir = args.temp_dir or (PROJECT_ROOT / "tmp" / f"viajes_con_te_calculado_{partition}_batches")
    manifest_path = manifest_path_for(temp_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input parquet not found: {input_path}")

    if args.finalize_only:
        finalize_batches(temp_dir, output_path)
        return

    print(f"Partición: {partition}")
    print(f"Input reconstruido: {input_path}")
    print(f"Frecuencias bus: {freq_path}")
    print(f"GTFS root: {gtfs_root}")
    print(f"Metro graph dir: {graph_dir}")
    start_t = time.time()
    engine = WaitTimeEngine(
        project_root=PROJECT_ROOT,
        partition_label=partition,
        partition_start=partition_start,
        input_path=input_path,
        freq_path=freq_path,
        gtfs_root=gtfs_root,
        graph_dir=graph_dir,
    )
    print(
        f"GTFS seleccionado: {engine.version.folder} "
        f"({engine.version.valid_from} -> {engine.version.valid_to})"
    )
    print(f"Grafo: {engine.graph.number_of_nodes()} nodos, {engine.graph.number_of_edges()} aristas")
    print(f"Servicios Metro GTFS: {len(engine.metro_route_ids)}")
    print(f"Índice de frecuencias bus: {len(engine.freq_bus_dict):,} entradas")

    lf = pl.scan_parquet(input_path)
    total_rows = lf.select(pl.len()).collect().item()
    if args.limit is not None:
        total_rows = min(total_rows, args.limit)
    print(f"Procesando {total_rows:,} filas en batches de {args.batch_size:,}")

    if args.resume:
        temp_dir.mkdir(parents=True, exist_ok=True)
        manifest = load_manifest(manifest_path)
        if manifest is None:
            raise FileNotFoundError(
                f"--resume requested but no manifest found at {manifest_path}"
            )
        expected = {
            "partition": partition,
            "batch_size": args.batch_size,
            "input_path": str(input_path.resolve()),
            "freq_path": str(freq_path.resolve()),
            "output_path": str(output_path.resolve()),
            "model_ready_filter": True,
            "logic_hash": LOGIC_HASH,
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise ValueError(
                    f"Resume manifest mismatch for {key}: expected {value!r}, found {manifest.get(key)!r}"
                )
        offset = int(manifest.get("offset", 0))
        batch_no = int(manifest.get("next_batch_no", 0))
        if args.limit is not None:
            offset = min(offset, total_rows)
        print(f"Reanudando desde offset {offset:,} (siguiente batch {batch_no:03d})")
    else:
        ensure_clean_dir(temp_dir)
        manifest = {
            "partition": partition,
            "batch_size": args.batch_size,
            "input_path": str(input_path.resolve()),
            "freq_path": str(freq_path.resolve()),
            "output_path": str(output_path.resolve()),
            "temp_dir": str(temp_dir.resolve()),
            "total_rows": total_rows,
            "offset": 0,
            "next_batch_no": 0,
            "model_ready_filter": True,
            "logic_hash": LOGIC_HASH,
            "logic_semantics": LOGIC_SEMANTICS,
            "rows_in_written_batches": 0,
            "rows_out_written_batches": 0,
            "rows_dropped_missing_stage_service": 0,
            "rows_dropped_non_contiguous_stage_blocks": 0,
            "rows_dropped_block_count_mismatch": 0,
            "rows_dropped_orig_gt4": 0,
            "rows_dropped_recon_gt4": 0,
            "rows_dropped_total": 0,
            "finished": False,
        }
        save_manifest(manifest_path, manifest)
        offset = 0
        batch_no = 0

    while offset < total_rows:
        batch_limit = min(args.batch_size, total_rows - offset)
        batch = lf.slice(offset, batch_limit).collect()
        batch_start = time.time()
        batch_out = engine.process_batch(batch)
        batch_out, filter_stats = filter_model_ready_rows(batch_out)
        batch_path = temp_dir / f"batch_{batch_no:05d}.parquet"
        tmp_batch_path = batch_path.with_suffix(".parquet.tmp")
        batch_out.write_parquet(tmp_batch_path)
        tmp_batch_path.replace(batch_path)
        offset += batch_limit
        batch_no += 1
        manifest["offset"] = offset
        manifest["next_batch_no"] = batch_no
        manifest["rows_in_written_batches"] = int(manifest.get("rows_in_written_batches", 0)) + filter_stats["rows_in"]
        manifest["rows_out_written_batches"] = int(manifest.get("rows_out_written_batches", 0)) + filter_stats["rows_out"]
        manifest["rows_dropped_missing_stage_service"] = int(manifest.get("rows_dropped_missing_stage_service", 0)) + filter_stats["drop_missing_stage_service"]
        manifest["rows_dropped_non_contiguous_stage_blocks"] = int(manifest.get("rows_dropped_non_contiguous_stage_blocks", 0)) + filter_stats["drop_non_contiguous_stage_blocks"]
        manifest["rows_dropped_block_count_mismatch"] = int(manifest.get("rows_dropped_block_count_mismatch", 0)) + filter_stats["drop_block_count_mismatch"]
        manifest["rows_dropped_orig_gt4"] = int(manifest.get("rows_dropped_orig_gt4", 0)) + filter_stats["drop_orig_gt4"]
        manifest["rows_dropped_recon_gt4"] = int(manifest.get("rows_dropped_recon_gt4", 0)) + filter_stats["drop_recon_gt4"]
        manifest["rows_dropped_total"] = int(manifest.get("rows_dropped_total", 0)) + filter_stats["rows_dropped"]
        save_manifest(manifest_path, manifest)
        elapsed = time.time() - batch_start
        rate = batch_limit / elapsed if elapsed > 0 else 0.0
        print(
            f"  batch {batch_no:03d}: {offset:,}/{total_rows:,} "
            f"({rate:,.0f} filas/s, drop={filter_stats['rows_dropped']:,})"
        )

    finalize_batches(temp_dir, output_path)
    manifest["finished"] = True
    manifest["final_output"] = str(output_path.resolve())
    save_manifest(manifest_path, manifest)
    total_elapsed = time.time() - start_t
    print(
        "Filtrado filas no model-ready: "
        f"{manifest['rows_dropped_total']:,} "
        f"(missing_srv={manifest['rows_dropped_missing_stage_service']:,}, "
        f"non_contiguous={manifest['rows_dropped_non_contiguous_stage_blocks']:,}, "
        f"block_mismatch={manifest['rows_dropped_block_count_mismatch']:,}, "
        f"orig_gt4={manifest['rows_dropped_orig_gt4']:,}, "
        f"recon_gt4={manifest['rows_dropped_recon_gt4']:,})"
    )
    print(f"Filas output final: {manifest['rows_out_written_batches']:,}")
    print(f"Listo en {total_elapsed/60:.1f} min: {output_path}")


if __name__ == "__main__":
    main()
