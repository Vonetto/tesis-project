from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import polars as pl
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config.constants import HORAS_PUNTA_MANANA, HORAS_PUNTA_TARDE  # noqa: E402
from lib.interannual_offer_context import build_zona777_area_table_from_gdf  # noqa: E402


DEFAULT_WEEKS = [
    "2024-W14",
    "2024-W15",
    "2024-W16",
    "2024-W17",
    "2025-W14",
    "2025-W15",
    "2025-W16",
    "2025-W17",
]

TRIPS_BY_WEEK = {
    week: PROJECT_ROOT / "tmp" / f"viajes_con_te_calculado_{week}.parquet"
    for week in DEFAULT_WEEKS
}

BUS_FREQUENCIES_BY_WEEK = {
    week: PROJECT_ROOT / "tmp" / f"frecuencias_buses_{week}.parquet"
    for week in DEFAULT_WEEKS
}

GTFS_BY_WEEK = {
    "2024-W14": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20240210",
    "2024-W15": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20240210",
    "2024-W16": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20240210",
    "2024-W17": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20240210",
    "2025-W14": PROJECT_ROOT / "tmp" / "gtfs_proxy_2025-W14" / "GTFS" / "GTFS_20250331_PROXY",
    "2025-W15": PROJECT_ROOT / "tmp" / "gtfs_proxy_2025-W15" / "GTFS" / "GTFS_20250407_PROXY",
    "2025-W16": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20250412",
    "2025-W17": PROJECT_ROOT / "config" / "GTFS" / "GTFS_20250412",
}

DEFAULT_OUT_DIR = PROJECT_ROOT / "02_eda" / "tmp" / "operational_offer_demand"
DEFAULT_ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)

REQUIRED_TRIP_COLUMNS = [
    "id_tarjeta",
    "zona_inicio_viaje",
    "paradero_inicio_viaje",
    "tiempo_inicio_viaje",
    "tipodia",
    "tipo_transporte_1",
]

REQUIRED_BUS_FREQUENCY_COLUMNS = [
    "ServicioSentido",
    "Paradero",
    "hour_start",
    "freq_buses_h",
]

GTFS_REQUIRED_FILES = [
    "routes.txt",
    "trips.txt",
    "stop_times.txt",
    "stops.txt",
    "calendar.txt",
]

FRANJA_ORDER = ["LAB_PM", "LAB_VALLE", "LAB_PT", "NO_LAB"]
BUS_LIKE_MODE_CODES = ["1", "3"]  # bus, zona paga


def percentile_within_groups(column: str, groups: list[str]) -> pl.Expr:
    return (
        pl.col(column).rank(method="average").over(groups)
        / pl.col(column).count().over(groups)
    )


def load_zone_area(zonas777_shp: Path) -> pl.DataFrame:
    if not zonas777_shp.exists():
        raise FileNotFoundError(f"No existe shapefile ZONA777: {zonas777_shp}")
    gdf = gpd.read_file(zonas777_shp)
    return build_zona777_area_table_from_gdf(gdf).rename(
        {"zona_inicio_viaje": "zone_id"}
    )


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def parquet_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "is_symlink": path.is_symlink(),
        "target": str(path.resolve()) if path.exists() or path.is_symlink() else None,
        "target_exists": path.resolve().exists() if path.exists() or path.is_symlink() else False,
        "rows": None,
        "columns": None,
    }
    if path.exists():
        pf = pq.ParquetFile(path)
        info["rows"] = pf.metadata.num_rows
        info["columns"] = pf.schema.names
    return info


def gtfs_info(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "required_files_present": {name: (path / name).exists() for name in GTFS_REQUIRED_FILES},
    }


def audit_inputs(weeks: list[str], zonas777_shp: Path = DEFAULT_ZONAS777_SHP) -> dict[str, Any]:
    rows = []
    for week in weeks:
        trip_info = parquet_info(TRIPS_BY_WEEK[week])
        freq_info = parquet_info(BUS_FREQUENCIES_BY_WEEK[week])
        gtfs = gtfs_info(GTFS_BY_WEEK[week])

        trip_columns = set(trip_info["columns"] or [])
        freq_columns = set(freq_info["columns"] or [])

        rows.append(
            {
                "week": week,
                "trip": {
                    **{k: v for k, v in trip_info.items() if k != "columns"},
                    "missing_required_columns": sorted(set(REQUIRED_TRIP_COLUMNS) - trip_columns),
                    "n_columns": len(trip_columns),
                },
                "bus_frequency": {
                    **{k: v for k, v in freq_info.items() if k != "columns"},
                    "missing_required_columns": sorted(set(REQUIRED_BUS_FREQUENCY_COLUMNS) - freq_columns),
                    "n_columns": len(freq_columns),
                },
                "gtfs": gtfs,
            }
        )

    blocking_errors = []
    if not zonas777_shp.exists():
        blocking_errors.append(f"falta shapefile ZONA777: {zonas777_shp}")
    for row in rows:
        week = row["week"]
        if not row["trip"]["exists"]:
            blocking_errors.append(f"{week}: falta archivo de viajes")
        if row["trip"]["missing_required_columns"]:
            blocking_errors.append(f"{week}: faltan columnas viajes {row['trip']['missing_required_columns']}")
        if not row["bus_frequency"]["exists"]:
            blocking_errors.append(f"{week}: falta archivo frecuencias bus")
        if row["bus_frequency"]["missing_required_columns"]:
            blocking_errors.append(
                f"{week}: faltan columnas frecuencias bus {row['bus_frequency']['missing_required_columns']}"
            )

    return {
        "weeks": weeks,
        "zonas777_shp": {
            "path": str(zonas777_shp),
            "exists": zonas777_shp.exists(),
        },
        "rows": rows,
        "blocking_errors": blocking_errors,
        "notes": [
            "GTFS se audita para extension Metro, pero este primer script no construye oferta Metro.",
            "2025-W14 y 2025-W15 usan carpetas GTFS proxy si existen.",
        ],
    }


def validate_or_raise(audit: dict[str, Any]) -> None:
    if audit["blocking_errors"]:
        raise RuntimeError("Inputs incompletos:\n- " + "\n- ".join(audit["blocking_errors"]))


def add_franja_v2(
    lf: pl.LazyFrame,
    *,
    timestamp_col: str,
    tipodia_col: str = "tipodia",
) -> pl.LazyFrame:
    return (
        lf.with_columns(
            [
                pl.col(timestamp_col)
                .dt.replace_time_zone("America/Santiago", ambiguous="earliest")
                .alias("_ts_local"),
                (pl.col(tipodia_col).cast(pl.Int8, strict=False) == 0).alias("_is_laboral"),
            ]
        )
        .with_columns(
            [
                pl.col("_ts_local").dt.hour().alias("_hora"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("_is_laboral") & pl.col("_hora").is_in(HORAS_PUNTA_MANANA))
                .then(pl.lit("LAB_PM"))
                .when(pl.col("_is_laboral") & pl.col("_hora").is_in(HORAS_PUNTA_TARDE))
                .then(pl.lit("LAB_PT"))
                .when(pl.col("_is_laboral"))
                .then(pl.lit("LAB_VALLE"))
                .otherwise(pl.lit("NO_LAB"))
                .alias("franja_v2")
            ]
        )
    )


def trip_base_lf(week: str) -> pl.LazyFrame:
    return (
        pl.scan_parquet(TRIPS_BY_WEEK[week])
        .select(
            [
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zone_id"),
                pl.col("paradero_inicio_viaje").cast(pl.Utf8).alias("stop_id"),
                pl.col("tiempo_inicio_viaje"),
                pl.col("tipodia").cast(pl.Int8, strict=False),
                pl.col("tipo_transporte_1").cast(pl.Utf8).alias("mode_1"),
            ]
        )
        .drop_nulls(["id_tarjeta", "zone_id", "tiempo_inicio_viaje"])
        .with_columns(pl.lit(week).alias("partition"))
    )


def build_stop_zone_mapping(weeks: list[str], out_path: Path) -> pl.DataFrame:
    weekly_counts = []
    for week in weeks:
        counts = (
            trip_base_lf(week)
            .drop_nulls(["stop_id", "zone_id"])
            .group_by(["stop_id", "zone_id"])
            .agg(pl.len().alias("n_trips_stop_zone_week"))
            .with_columns(pl.lit(week).alias("partition"))
        )
        weekly_counts.append(collect_streaming(counts))

    all_counts = (
        pl.concat(weekly_counts, how="diagonal_relaxed")
        .group_by(["stop_id", "zone_id"])
        .agg(pl.col("n_trips_stop_zone_week").sum().alias("n_trips_stop_zone"))
    )

    mapping = (
        all_counts.sort(["stop_id", "n_trips_stop_zone", "zone_id"], descending=[False, True, False])
        .group_by("stop_id", maintain_order=True)
        .agg(
            [
                pl.col("zone_id").first().alias("zone_id"),
                pl.col("n_trips_stop_zone").first().alias("n_trips_modal_zone"),
                pl.col("n_trips_stop_zone").sum().alias("n_trips_stop_total"),
                pl.len().alias("n_zone_candidates"),
            ]
        )
        .with_columns(
            (pl.col("n_trips_modal_zone") / pl.col("n_trips_stop_total")).alias("modal_zone_share")
        )
        .sort("stop_id")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mapping.write_parquet(out_path)
    return mapping


def build_demand_by_week(weeks: list[str], out_path: Path) -> pl.DataFrame:
    parts = []
    for week in weeks:
        lf = add_franja_v2(trip_base_lf(week), timestamp_col="tiempo_inicio_viaje")
        part = (
            lf.group_by(["partition", "zone_id", "franja_v2"])
            .agg(
                [
                    pl.len().alias("op_demand_trips_zone_franja_week"),
                    pl.col("id_tarjeta").n_unique().alias("op_demand_cards_zone_franja_week"),
                ]
            )
            .with_columns(
                pl.col("franja_v2").replace_strict(
                    {label: idx for idx, label in enumerate(FRANJA_ORDER)},
                    default=None,
                ).alias("_franja_order")
            )
            .sort(["partition", "zone_id", "_franja_order"])
            .drop("_franja_order")
        )
        parts.append(collect_streaming(part))

    demand = pl.concat(parts, how="diagonal_relaxed")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    demand.write_parquet(out_path)
    return demand


def date_tipodia_lf(week: str) -> pl.LazyFrame:
    return (
        trip_base_lf(week)
        .with_columns(pl.col("tiempo_inicio_viaje").dt.date().alias("service_date"))
        .drop_nulls(["service_date", "tipodia"])
        .group_by("service_date")
        .agg(
            [
                pl.col("tipodia").min().alias("tipodia"),
                pl.col("tipodia").n_unique().alias("n_tipodia_values"),
            ]
        )
    )


def build_bus_offer_by_week(weeks: list[str], stop_zone_mapping: pl.DataFrame, out_path: Path) -> pl.DataFrame:
    stop_zone_lf = stop_zone_mapping.select(["stop_id", "zone_id"]).lazy()
    parts = []
    for week in weeks:
        freq = (
            pl.scan_parquet(BUS_FREQUENCIES_BY_WEEK[week])
            .select(
                [
                    pl.col("Paradero").cast(pl.Utf8).alias("stop_id"),
                    pl.col("ServicioSentido").cast(pl.Utf8).alias("service_direction"),
                    pl.col("hour_start"),
                    pl.col("freq_buses_h").cast(pl.Float64),
                ]
            )
            .drop_nulls(["stop_id", "service_direction", "hour_start", "freq_buses_h"])
            .with_columns(pl.col("hour_start").dt.date().alias("service_date"))
            .join(stop_zone_lf, on="stop_id", how="inner")
            .join(date_tipodia_lf(week), on="service_date", how="left")
        )
        freq = add_franja_v2(freq, timestamp_col="hour_start")

        stop_hour = (
            freq.group_by(["zone_id", "franja_v2", "hour_start", "stop_id"])
            .agg(
                [
                    pl.col("freq_buses_h").sum().alias("op_bus_supply_buses_h_stop_hour"),
                    pl.col("service_direction").n_unique().alias("op_bus_service_directions_stop_hour"),
                ]
            )
        )

        zone_hour = (
            stop_hour.group_by(["zone_id", "franja_v2", "hour_start"])
            .agg(
                [
                    pl.col("op_bus_supply_buses_h_stop_hour").sum().alias(
                        "op_bus_supply_buses_h_zone_hour"
                    ),
                    pl.col("op_bus_supply_buses_h_stop_hour").mean().alias(
                        "op_bus_supply_typical_stop_buses_h_zone_hour_mean"
                    ),
                    pl.col("op_bus_supply_buses_h_stop_hour").median().alias(
                        "op_bus_supply_typical_stop_buses_h_zone_hour_median"
                    ),
                    pl.col("op_bus_service_directions_stop_hour").sum().alias(
                        "op_bus_service_directions_stop_hour_sum_zone_hour"
                    ),
                    pl.col("stop_id").n_unique().alias("op_bus_stops_with_supply_zone_hour"),
                ]
            )
            .with_columns(pl.lit(week).alias("partition"))
        )

        zone_service_hour = (
            freq.group_by(["zone_id", "franja_v2", "hour_start"])
            .agg(pl.col("service_direction").n_unique().alias("op_bus_service_directions_zone_hour"))
            .with_columns(pl.lit(week).alias("partition"))
        )

        zone_hour = zone_hour.join(
            zone_service_hour,
            on=["partition", "zone_id", "franja_v2", "hour_start"],
            how="left",
        )

        part = (
            zone_hour.group_by(["partition", "zone_id", "franja_v2"])
            .agg(
                [
                    pl.len().alias("op_bus_supply_hours_observed"),
                    pl.col("op_bus_supply_buses_h_zone_hour").mean().alias(
                        "op_bus_supply_buses_h_zone_franja_mean"
                    ),
                    pl.col("op_bus_supply_buses_h_zone_hour").median().alias(
                        "op_bus_supply_buses_h_zone_franja_median"
                    ),
                    pl.col("op_bus_supply_typical_stop_buses_h_zone_hour_mean").mean().alias(
                        "op_bus_supply_typical_stop_buses_h_zone_franja_mean"
                    ),
                    pl.col("op_bus_supply_typical_stop_buses_h_zone_hour_median").mean().alias(
                        "op_bus_supply_typical_stop_buses_h_zone_franja_median"
                    ),
                    pl.col("op_bus_service_directions_zone_hour").mean().alias(
                        "op_bus_service_directions_zone_franja_mean"
                    ),
                    pl.col("op_bus_stops_with_supply_zone_hour").mean().alias(
                        "op_bus_stops_with_supply_zone_franja_mean"
                    ),
                ]
            )
            .with_columns(
                pl.col("franja_v2").replace_strict(
                    {label: idx for idx, label in enumerate(FRANJA_ORDER)},
                    default=None,
                ).alias("_franja_order")
            )
            .sort(["partition", "zone_id", "_franja_order"])
            .drop("_franja_order")
        )
        parts.append(collect_streaming(part))

    bus_offer = pl.concat(parts, how="diagonal_relaxed")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bus_offer.write_parquet(out_path)
    return bus_offer


def build_zone_context(
    demand: pl.DataFrame,
    bus_offer: pl.DataFrame,
    zone_area: pl.DataFrame,
    out_path: Path,
) -> pl.DataFrame:
    percentile_groups = ["partition", "franja_v2"]

    context = (
        demand.join(bus_offer, on=["partition", "zone_id", "franja_v2"], how="left")
        .join(zone_area, on="zone_id", how="left")
        .with_columns(
            [
                pl.col("op_bus_supply_buses_h_zone_franja_mean").is_not_null().alias(
                    "op_has_bus_supply_context"
                ),
                pl.col("op_demand_trips_zone_franja_week").log1p().alias("op_demand_log1p_trips_zone_franja_week"),
                pl.col("op_bus_supply_buses_h_zone_franja_mean")
                .log1p()
                .alias("op_bus_log1p_supply_buses_h_zone_franja_mean"),
                pl.col("op_bus_supply_typical_stop_buses_h_zone_franja_mean")
                .log1p()
                .alias("op_bus_log1p_supply_typical_stop_buses_h_zone_franja_mean"),
                pl.col("op_bus_service_directions_zone_franja_mean")
                .log1p()
                .alias("op_bus_log1p_service_directions_zone_franja_mean"),
                pl.when(pl.col("AREA_KM2") > 0)
                .then(
                    pl.col("op_bus_stops_with_supply_zone_franja_mean")
                    / pl.col("AREA_KM2")
                )
                .otherwise(None)
                .alias("op_bus_stops_with_supply_zone_franja_density_km2"),
                percentile_within_groups(
                    "op_demand_trips_zone_franja_week",
                    percentile_groups,
                ).alias(
                    "op_demand_trips_zone_franja_week_percentile"
                ),
                percentile_within_groups(
                    "op_bus_supply_typical_stop_buses_h_zone_franja_mean",
                    percentile_groups,
                ).alias(
                    "op_bus_supply_typical_stop_buses_h_zone_franja_percentile"
                ),
                percentile_within_groups(
                    "op_bus_service_directions_zone_franja_mean",
                    percentile_groups,
                ).alias(
                    "op_bus_service_directions_zone_franja_percentile"
                ),
                percentile_within_groups(
                    "op_bus_stops_with_supply_zone_franja_mean",
                    percentile_groups,
                ).alias(
                    "op_bus_stops_with_supply_zone_franja_percentile"
                ),
            ]
        )
        .with_columns(
            percentile_within_groups(
                "op_bus_stops_with_supply_zone_franja_density_km2",
                percentile_groups,
            ).alias("op_bus_stops_with_supply_zone_franja_density_percentile")
        )
        .sort(["partition", "zone_id", "franja_v2"])
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    context.write_parquet(out_path)
    return context


def bus_stop_hour_context_lf(week: str) -> pl.LazyFrame:
    base = (
        pl.scan_parquet(BUS_FREQUENCIES_BY_WEEK[week])
        .select(
            [
                pl.col("Paradero").cast(pl.Utf8).alias("stop_id"),
                pl.col("ServicioSentido").cast(pl.Utf8).alias("service_direction"),
                pl.col("hour_start"),
                pl.col("freq_buses_h").cast(pl.Float64),
            ]
        )
        .drop_nulls(["stop_id", "service_direction", "hour_start", "freq_buses_h"])
        .with_columns(pl.col("hour_start").dt.date().alias("service_date"))
        .join(date_tipodia_lf(week), on="service_date", how="left")
    )
    stop_hour = (
        add_franja_v2(base, timestamp_col="hour_start")
        .group_by(["stop_id", "hour_start"])
        .agg(
            [
                pl.col("franja_v2").first().alias("franja_v2"),
                pl.col("freq_buses_h").sum().alias("op_stop_bus_supply_buses_h_observed"),
                pl.col("service_direction")
                .n_unique()
                .cast(pl.Float64)
                .alias("op_stop_bus_service_directions_observed"),
            ]
        )
        .with_columns(
            (60.0 / pl.col("op_stop_bus_supply_buses_h_observed")).alias(
                "op_stop_bus_headway_min_observed"
            ),
            percentile_within_groups(
                "op_stop_bus_supply_buses_h_observed",
                ["franja_v2"],
            ).alias("op_stop_bus_supply_buses_h_observed_percentile"),
        )
    )
    return stop_hour.drop("franja_v2")


def build_card_exposure(weeks: list[str], zone_context: pl.DataFrame, out_path: Path) -> pl.DataFrame:
    context_lf = zone_context.lazy()
    weekly = []
    for week in weeks:
        trips = (
            add_franja_v2(trip_base_lf(week), timestamp_col="tiempo_inicio_viaje")
            .with_columns(
                [
                    pl.col("tiempo_inicio_viaje").dt.truncate("1h").alias("hour_start"),
                    pl.col("mode_1").is_in(BUS_LIKE_MODE_CODES).alias("op_is_origin_bus_like"),
                ]
            )
        )
        card_cell_counts = (
            trips.group_by(["id_tarjeta", "partition", "zone_id", "franja_v2"])
            .agg(pl.len().alias("op_demand_trips_card_zone_franja_week"))
        )
        joined = (
            trips.join(card_cell_counts, on=["id_tarjeta", "partition", "zone_id", "franja_v2"], how="left")
            .join(context_lf, on=["partition", "zone_id", "franja_v2"], how="left")
            .join(bus_stop_hour_context_lf(week), on=["stop_id", "hour_start"], how="left")
            .with_columns(
                [
                    (pl.col("op_demand_trips_zone_franja_week").fill_null(0) - 1)
                    .clip(lower_bound=0)
                    .alias("op_demand_trips_excl_current"),
                    (
                        pl.col("op_demand_trips_zone_franja_week").fill_null(0)
                        - pl.col("op_demand_trips_card_zone_franja_week").fill_null(0)
                    )
                    .clip(lower_bound=0)
                    .alias("op_demand_trips_excl_card"),
                    (pl.col("op_demand_cards_zone_franja_week").fill_null(0) - 1)
                    .clip(lower_bound=0)
                    .alias("op_demand_cards_excl_card"),
                    pl.col("op_bus_supply_buses_h_zone_franja_mean")
                    .is_not_null()
                    .alias("op_has_bus_supply_context_trip"),
                    pl.col("op_bus_stops_with_supply_zone_franja_density_percentile")
                    .is_not_null()
                    .alias("op_has_bus_stops_density_context_trip"),
                    (
                        pl.col("op_is_origin_bus_like")
                        & pl.col("op_stop_bus_supply_buses_h_observed").is_not_null()
                    ).alias("op_stop_bus_supply_matched_trip"),
                ]
            )
        )
        joined = joined.with_columns(
            [
                pl.col("op_demand_trips_excl_current")
                .log1p()
                .alias("op_demand_log1p_trips_excl_current"),
                pl.col("op_demand_trips_excl_card").log1p().alias("op_demand_log1p_trips_excl_card"),
                pl.col("op_demand_cards_excl_card").log1p().alias("op_demand_log1p_cards_excl_card"),
            ]
        )

        agg = (
            joined.group_by("id_tarjeta")
            .agg(
                [
                    pl.len().alias("op_n_trips_context"),
                    pl.col("op_demand_trips_excl_current").sum().alias("_sum_demand_trips_excl_current"),
                    pl.col("op_demand_log1p_trips_excl_current").sum().alias("_sum_demand_log1p_trips_excl_current"),
                    pl.col("op_demand_trips_excl_card").sum().alias("_sum_demand_trips_excl_card"),
                    pl.col("op_demand_log1p_trips_excl_card").sum().alias(
                        "_sum_demand_log1p_trips_excl_card"
                    ),
                    pl.col("op_demand_cards_excl_card").sum().alias("_sum_demand_cards_excl_card"),
                    pl.col("op_demand_log1p_cards_excl_card").sum().alias(
                        "_sum_demand_log1p_cards_excl_card"
                    ),
                    pl.col("op_demand_trips_zone_franja_week_percentile").sum().alias(
                        "_sum_demand_trips_zone_franja_week_percentile"
                    ),
                    pl.col("op_has_bus_supply_context_trip").sum().alias("op_n_trips_with_bus_supply_context"),
                    pl.col("op_bus_supply_buses_h_zone_franja_mean").sum().alias(
                        "_sum_bus_supply_buses_h_zone_franja_mean"
                    ),
                    pl.col("op_bus_supply_typical_stop_buses_h_zone_franja_mean").sum().alias(
                        "_sum_bus_supply_typical_stop_buses_h_zone_franja_mean"
                    ),
                    pl.col("op_bus_supply_typical_stop_buses_h_zone_franja_median").sum().alias(
                        "_sum_bus_supply_typical_stop_buses_h_zone_franja_median"
                    ),
                    pl.col("op_bus_supply_typical_stop_buses_h_zone_franja_percentile").sum().alias(
                        "_sum_bus_supply_typical_stop_buses_h_zone_franja_percentile"
                    ),
                    pl.col("op_bus_service_directions_zone_franja_mean").sum().alias(
                        "_sum_bus_service_directions_zone_franja_mean"
                    ),
                    pl.col("op_bus_service_directions_zone_franja_percentile").sum().alias(
                        "_sum_bus_service_directions_zone_franja_percentile"
                    ),
                    pl.col("op_bus_stops_with_supply_zone_franja_mean").sum().alias(
                        "_sum_bus_stops_with_supply_zone_franja_mean"
                    ),
                    pl.col("op_bus_stops_with_supply_zone_franja_percentile").sum().alias(
                        "_sum_bus_stops_with_supply_zone_franja_percentile"
                    ),
                    pl.col("op_has_bus_stops_density_context_trip").sum().alias(
                        "op_n_trips_with_bus_stops_density_context"
                    ),
                    pl.col("op_bus_stops_with_supply_zone_franja_density_km2").sum().alias(
                        "_sum_bus_stops_with_supply_zone_franja_density_km2"
                    ),
                    pl.col("op_bus_stops_with_supply_zone_franja_density_percentile").sum().alias(
                        "_sum_bus_stops_with_supply_zone_franja_density_percentile"
                    ),
                    pl.col("op_is_origin_bus_like").sum().alias("op_n_trips_bus_like"),
                    pl.col("op_stop_bus_supply_matched_trip").sum().alias(
                        "op_n_trips_with_stop_bus_supply_context"
                    ),
                    pl.when(pl.col("op_stop_bus_supply_matched_trip"))
                    .then(pl.col("op_stop_bus_supply_buses_h_observed"))
                    .otherwise(None)
                    .sum()
                    .alias("_sum_stop_bus_supply_buses_h_observed"),
                    pl.when(pl.col("op_stop_bus_supply_matched_trip"))
                    .then(pl.col("op_stop_bus_service_directions_observed"))
                    .otherwise(None)
                    .sum()
                    .alias("_sum_stop_bus_service_directions_observed"),
                    pl.when(pl.col("op_stop_bus_supply_matched_trip"))
                    .then(pl.col("op_stop_bus_headway_min_observed"))
                    .otherwise(None)
                    .sum()
                    .alias("_sum_stop_bus_headway_min_observed"),
                    pl.when(pl.col("op_stop_bus_supply_matched_trip"))
                    .then(pl.col("op_stop_bus_supply_buses_h_observed_percentile"))
                    .otherwise(None)
                    .sum()
                    .alias("_sum_stop_bus_supply_buses_h_observed_percentile"),
                ]
            )
            .with_columns(pl.lit(week).alias("partition"))
        )
        weekly.append(collect_streaming(agg))

    card_week = pl.concat(weekly, how="diagonal_relaxed")
    card = (
        card_week.group_by("id_tarjeta")
        .agg(
            [
                pl.col("op_n_trips_context").sum(),
                pl.col("op_n_trips_with_bus_supply_context").sum(),
                pl.col("_sum_demand_trips_excl_current").sum(),
                pl.col("_sum_demand_log1p_trips_excl_current").sum(),
                pl.col("_sum_demand_trips_excl_card").sum(),
                pl.col("_sum_demand_log1p_trips_excl_card").sum(),
                pl.col("_sum_demand_cards_excl_card").sum(),
                pl.col("_sum_demand_log1p_cards_excl_card").sum(),
                pl.col("_sum_demand_trips_zone_franja_week_percentile").sum(),
                pl.col("_sum_bus_supply_buses_h_zone_franja_mean").sum(),
                pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_mean").sum(),
                pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_median").sum(),
                pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_percentile").sum(),
                pl.col("_sum_bus_service_directions_zone_franja_mean").sum(),
                pl.col("_sum_bus_service_directions_zone_franja_percentile").sum(),
                pl.col("_sum_bus_stops_with_supply_zone_franja_mean").sum(),
                pl.col("_sum_bus_stops_with_supply_zone_franja_percentile").sum(),
                pl.col("op_n_trips_with_bus_stops_density_context").sum(),
                pl.col("_sum_bus_stops_with_supply_zone_franja_density_km2").sum(),
                pl.col("_sum_bus_stops_with_supply_zone_franja_density_percentile").sum(),
                pl.col("op_n_trips_bus_like").sum(),
                pl.col("op_n_trips_with_stop_bus_supply_context").sum(),
                pl.col("_sum_stop_bus_supply_buses_h_observed").sum(),
                pl.col("_sum_stop_bus_service_directions_observed").sum(),
                pl.col("_sum_stop_bus_headway_min_observed").sum(),
                pl.col("_sum_stop_bus_supply_buses_h_observed_percentile").sum(),
            ]
        )
        .with_columns(
            [
                (pl.col("_sum_demand_trips_excl_current") / pl.col("op_n_trips_context")).alias(
                    "op_demand_trips_excl_current_mean"
                ),
                (pl.col("_sum_demand_log1p_trips_excl_current") / pl.col("op_n_trips_context")).alias(
                    "op_demand_log1p_trips_excl_current_mean"
                ),
                (pl.col("_sum_demand_trips_excl_card") / pl.col("op_n_trips_context")).alias(
                    "op_demand_trips_excl_card_mean"
                ),
                (pl.col("_sum_demand_log1p_trips_excl_card") / pl.col("op_n_trips_context")).alias(
                    "op_demand_log1p_trips_excl_card_mean"
                ),
                (pl.col("_sum_demand_cards_excl_card") / pl.col("op_n_trips_context")).alias(
                    "op_demand_cards_excl_card_mean"
                ),
                (pl.col("_sum_demand_log1p_cards_excl_card") / pl.col("op_n_trips_context")).alias(
                    "op_demand_log1p_cards_excl_card_mean"
                ),
                (
                    pl.col("_sum_demand_trips_zone_franja_week_percentile")
                    / pl.col("op_n_trips_context")
                ).alias("op_demand_trips_zone_franja_week_percentile_mean"),
                (pl.col("op_n_trips_with_bus_supply_context") / pl.col("op_n_trips_context")).alias(
                    "op_bus_supply_context_trip_share"
                ),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_supply_buses_h_zone_franja_mean")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_supply_buses_h_zone_franja_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_mean")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_supply_typical_stop_buses_h_zone_franja_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_median")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_supply_typical_stop_buses_h_zone_franja_median"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_supply_typical_stop_buses_h_zone_franja_percentile")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_supply_typical_stop_buses_h_zone_franja_percentile_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_service_directions_zone_franja_mean")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_service_directions_zone_franja_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_service_directions_zone_franja_percentile")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_service_directions_zone_franja_percentile_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_stops_with_supply_zone_franja_mean")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_stops_with_supply_zone_franja_mean"),
                pl.when(pl.col("op_n_trips_with_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_bus_stops_with_supply_zone_franja_percentile")
                    / pl.col("op_n_trips_with_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_bus_stops_with_supply_zone_franja_percentile_mean"),
                pl.when(pl.col("op_n_trips_with_bus_stops_density_context") > 0)
                .then(
                    pl.col("_sum_bus_stops_with_supply_zone_franja_density_km2")
                    / pl.col("op_n_trips_with_bus_stops_density_context")
                )
                .otherwise(None)
                .alias("op_bus_stops_with_supply_zone_franja_density_km2_mean"),
                pl.when(pl.col("op_n_trips_with_bus_stops_density_context") > 0)
                .then(
                    pl.col("_sum_bus_stops_with_supply_zone_franja_density_percentile")
                    / pl.col("op_n_trips_with_bus_stops_density_context")
                )
                .otherwise(None)
                .alias("op_bus_stops_with_supply_zone_franja_density_percentile_mean"),
                (
                    pl.col("op_n_trips_with_bus_stops_density_context")
                    / pl.col("op_n_trips_context")
                ).alias("op_bus_stops_density_context_trip_share"),
                pl.when(pl.col("op_n_trips_bus_like") > 0)
                .then(pl.col("op_n_trips_with_stop_bus_supply_context") / pl.col("op_n_trips_bus_like"))
                .otherwise(None)
                .alias("op_stop_bus_supply_match_share"),
                pl.when(pl.col("op_n_trips_with_stop_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_stop_bus_supply_buses_h_observed")
                    / pl.col("op_n_trips_with_stop_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_stop_bus_supply_buses_h_observed_mean"),
                pl.when(pl.col("op_n_trips_with_stop_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_stop_bus_service_directions_observed")
                    / pl.col("op_n_trips_with_stop_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_stop_bus_service_directions_observed_mean"),
                pl.when(pl.col("op_n_trips_with_stop_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_stop_bus_headway_min_observed")
                    / pl.col("op_n_trips_with_stop_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_stop_bus_headway_min_observed_mean"),
                pl.when(pl.col("op_n_trips_with_stop_bus_supply_context") > 0)
                .then(
                    pl.col("_sum_stop_bus_supply_buses_h_observed_percentile")
                    / pl.col("op_n_trips_with_stop_bus_supply_context")
                )
                .otherwise(None)
                .alias("op_stop_bus_supply_buses_h_observed_percentile_mean"),
            ]
        )
        .select(
            [
                "id_tarjeta",
                "op_n_trips_context",
                "op_demand_trips_excl_current_mean",
                "op_demand_log1p_trips_excl_current_mean",
                "op_demand_trips_excl_card_mean",
                "op_demand_log1p_trips_excl_card_mean",
                "op_demand_cards_excl_card_mean",
                "op_demand_log1p_cards_excl_card_mean",
                "op_demand_trips_zone_franja_week_percentile_mean",
                "op_n_trips_with_bus_supply_context",
                "op_bus_supply_context_trip_share",
                "op_bus_supply_buses_h_zone_franja_mean",
                "op_bus_supply_typical_stop_buses_h_zone_franja_mean",
                "op_bus_supply_typical_stop_buses_h_zone_franja_median",
                "op_bus_supply_typical_stop_buses_h_zone_franja_percentile_mean",
                "op_bus_service_directions_zone_franja_mean",
                "op_bus_service_directions_zone_franja_percentile_mean",
                "op_bus_stops_with_supply_zone_franja_mean",
                "op_bus_stops_with_supply_zone_franja_percentile_mean",
                "op_n_trips_with_bus_stops_density_context",
                "op_bus_stops_density_context_trip_share",
                "op_bus_stops_with_supply_zone_franja_density_km2_mean",
                "op_bus_stops_with_supply_zone_franja_density_percentile_mean",
                "op_n_trips_bus_like",
                "op_n_trips_with_stop_bus_supply_context",
                "op_stop_bus_supply_match_share",
                "op_stop_bus_supply_buses_h_observed_mean",
                "op_stop_bus_supply_buses_h_observed_percentile_mean",
                "op_stop_bus_service_directions_observed_mean",
                "op_stop_bus_headway_min_observed_mean",
            ]
        )
        .sort("id_tarjeta")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    card.write_parquet(out_path)
    return card


def summarize_build(
    *,
    weeks: list[str],
    stop_zone_mapping: pl.DataFrame,
    demand: pl.DataFrame,
    bus_offer: pl.DataFrame,
    zone_context: pl.DataFrame,
    card_exposure: pl.DataFrame,
) -> dict[str, Any]:
    return {
        "weeks": weeks,
        "outputs": {
            "n_stop_zone_mapping_rows": stop_zone_mapping.height,
            "n_zone_franja_week_demand_rows": demand.height,
            "n_zone_franja_week_bus_offer_rows": bus_offer.height,
            "n_zone_franja_week_context_rows": zone_context.height,
            "n_card_exposure_rows": card_exposure.height,
        },
        "stop_zone_mapping": {
            "p50_modal_zone_share": stop_zone_mapping.select(pl.col("modal_zone_share").quantile(0.50)).item(),
            "p10_modal_zone_share": stop_zone_mapping.select(pl.col("modal_zone_share").quantile(0.10)).item(),
            "share_modal_zone_ge_080": stop_zone_mapping.select((pl.col("modal_zone_share") >= 0.80).mean()).item(),
        },
        "zone_context": {
            "share_rows_with_bus_supply_context": zone_context.select(pl.col("op_has_bus_supply_context").mean()).item(),
            "share_rows_with_bus_stops_density_context": zone_context.select(
                pl.col("op_bus_stops_with_supply_zone_franja_density_percentile")
                .is_not_null()
                .mean()
            ).item(),
            "n_partitions": zone_context.select(pl.col("partition").n_unique()).item(),
            "n_zones": zone_context.select(pl.col("zone_id").n_unique()).item(),
        },
        "card_exposure": {
            "n_cards": card_exposure.height,
            "n_trips_context": card_exposure.select(pl.col("op_n_trips_context").sum()).item(),
            "mean_bus_supply_context_trip_share": card_exposure.select(
                pl.col("op_bus_supply_context_trip_share").mean()
            ).item(),
            "share_cards_with_bus_like_trips": card_exposure.select(
                (pl.col("op_n_trips_bus_like") > 0).mean()
            ).item(),
            "mean_stop_bus_supply_match_share_among_bus_like_cards": card_exposure.filter(
                pl.col("op_n_trips_bus_like") > 0
            )
            .select(pl.col("op_stop_bus_supply_match_share").mean())
            .item(),
            "mean_bus_stops_density_context_trip_share": card_exposure.select(
                pl.col("op_bus_stops_density_context_trip_share").mean()
            ).item(),
            "normalized_offer_ranges": {
                "zone_stops_density_percentile_min": card_exposure.select(
                    pl.col("op_bus_stops_with_supply_zone_franja_density_percentile_mean").min()
                ).item(),
                "zone_stops_density_percentile_max": card_exposure.select(
                    pl.col("op_bus_stops_with_supply_zone_franja_density_percentile_mean").max()
                ).item(),
                "stop_hour_supply_percentile_min": card_exposure.select(
                    pl.col("op_stop_bus_supply_buses_h_observed_percentile_mean").min()
                ).item(),
                "stop_hour_supply_percentile_max": card_exposure.select(
                    pl.col("op_stop_bus_supply_buses_h_observed_percentile_mean").max()
                ).item(),
            },
        },
    }


def build_all(
    weeks: list[str],
    out_dir: Path,
    *,
    zonas777_shp: Path,
    force: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "input_audit": out_dir / "operational_input_audit.json",
        "stop_zone_mapping": out_dir / "operational_stop_zone_mapping.parquet",
        "demand": out_dir / "operational_zone_franja_week_demand.parquet",
        "bus_offer": out_dir / "operational_zone_franja_week_bus_offer.parquet",
        "zone_context": out_dir / "operational_zone_franja_week_context.parquet",
        "card_exposure": out_dir / "operational_card_exposure.parquet",
        "summary": out_dir / "operational_build_summary.json",
    }

    existing = [str(path) for key, path in paths.items() if key != "input_audit" and path.exists()]
    if existing and not force:
        raise FileExistsError("Outputs ya existen. Usa --force para sobrescribir:\n- " + "\n- ".join(existing))

    audit = audit_inputs(weeks, zonas777_shp)
    write_json(paths["input_audit"], audit)
    validate_or_raise(audit)

    stop_zone_mapping = build_stop_zone_mapping(weeks, paths["stop_zone_mapping"])
    demand = build_demand_by_week(weeks, paths["demand"])
    bus_offer = build_bus_offer_by_week(weeks, stop_zone_mapping, paths["bus_offer"])
    zone_area = load_zone_area(zonas777_shp)
    zone_context = build_zone_context(demand, bus_offer, zone_area, paths["zone_context"])
    card_exposure = build_card_exposure(weeks, zone_context, paths["card_exposure"])

    summary = summarize_build(
        weeks=weeks,
        stop_zone_mapping=stop_zone_mapping,
        demand=demand,
        bus_offer=bus_offer,
        zone_context=zone_context,
        card_exposure=card_exposure,
    )
    write_json(paths["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reconstruye oferta/demanda operacional desde viajes procesados y frecuencias bus, "
            "sin usar variables LOG_* ni artefactos antiguos de oferta/demanda."
        )
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--zonas777-shp", type=Path, default=DEFAULT_ZONAS777_SHP)
    parser.add_argument("--weeks", nargs="+", default=DEFAULT_WEEKS)
    parser.add_argument("--audit-inputs", action="store_true", help="solo audita disponibilidad de inputs")
    parser.add_argument("--force", action="store_true", help="sobrescribe outputs existentes")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    unknown = sorted(set(args.weeks) - set(DEFAULT_WEEKS))
    if unknown:
        raise ValueError(f"Semanas no configuradas: {unknown}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.audit_inputs:
        audit = audit_inputs(args.weeks, args.zonas777_shp)
        out_path = args.out_dir / "operational_input_audit.json"
        write_json(out_path, audit)
        print(f"Audit escrito: {out_path}")
        if audit["blocking_errors"]:
            print("Errores bloqueantes:")
            for error in audit["blocking_errors"]:
                print(f"- {error}")
            raise SystemExit(1)
        print("Inputs OK.")
        return

    summary = build_all(
        args.weeks,
        args.out_dir,
        zonas777_shp=args.zonas777_shp,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
