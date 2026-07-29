from __future__ import annotations

import argparse
import itertools
import math
from datetime import date
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from scipy.stats import pearsonr, spearmanr
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRIPS_DIR = PROJECT_ROOT / "tmp"
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_window_sensitivity"

MIN_TRIPS_EACH_PERIOD = 3
MIN_ACTIVE_DAYS_EACH_PERIOD = 2
KMEANS_MAX_ROWS = 250_000
TARGET_WEEK_FOR_DOWNSTREAM = "2025-W17"
N_MODEL_SPLITS = 5

BASE_COLUMNS = [
    "id_tarjeta",
    "fecha",
    "tiempo_inicio_viaje",
    "zona_inicio_viaje",
    "paradero_inicio_viaje",
    "n_etapas_recon",
    "metro_any",
    "t_total_calculado_seg",
    "is_qr",
]

INDICATOR_COLUMNS = [
    "dsi_day_sequence",
    "tsi_time_distribution",
    "lsi_origin_zone",
    "lsi_origin_stop",
    "log_ratio_n_trips",
    "delta_mean_n_etapas_recon",
    "delta_share_metro_any",
    "delta_mean_first_trip_hour",
    "delta_mean_total_time_min",
]

CLUSTER_FEATURES = [
    "dsi_day_sequence",
    "tsi_time_distribution",
    "lsi_origin_zone",
    "log_ratio_n_trips",
    "delta_mean_n_etapas_recon",
    "delta_share_metro_any",
    "delta_mean_first_trip_hour",
    "delta_mean_total_time_min",
]


@dataclass(frozen=True)
class WindowSpec:
    window_id: str
    base_weeks: tuple[str, ...]
    eval_weeks: tuple[str, ...]
    note: str


WINDOWS = [
    WindowSpec(
        "W17_baseline",
        ("2024-W17",),
        ("2025-W17",),
        "baseline actual de una semana",
    ),
    WindowSpec(
        "W15_W17_clean_nonconsecutive",
        ("2024-W15", "2024-W17"),
        ("2025-W15", "2025-W17"),
        "dos semanas completas no consecutivas; evita W14 incompleta y W16 feriado",
    ),
    WindowSpec(
        "W14_W15_incomplete_unbalanced",
        ("2024-W14", "2024-W15"),
        ("2025-W14", "2025-W15"),
        "sensibilidad incompleta sin balancear dias; 2025-W14 no tiene lunes",
    ),
    WindowSpec(
        "W15_W16_holiday",
        ("2024-W15", "2024-W16"),
        ("2025-W15", "2025-W16"),
        "sensibilidad con Semana Santa en 2025-W16",
    ),
    WindowSpec(
        "W16_W17_holiday_post",
        ("2024-W16", "2024-W17"),
        ("2025-W16", "2025-W17"),
        "sensibilidad con Semana Santa y semana posterior",
    ),
    # --- Ventanas INTRA-anuales: base y eval del MISMO año. Miden regularidad
    # del hábito DENTRO de un periodo, sin mezclar años. Útiles para separar
    # "estabilidad inter-anual" (cambio 2024->2025) de "regularidad intra-anual"
    # (consistencia de la persona dentro del mismo abril). W15 vs W17 son las
    # dos semanas limpias no consecutivas (evitan W14 incompleta y W16 feriado).
    WindowSpec(
        "intra2024_W15_W17",
        ("2024-W15",),
        ("2024-W17",),
        "intra-anual 2024: W15 (base) vs W17 (eval), mismo abril",
    ),
    WindowSpec(
        "intra2025_W15_W17",
        ("2025-W15",),
        ("2025-W17",),
        "intra-anual 2025: W15 (base) vs W17 (eval), mismo abril",
    ),
]


def trips_path(week: str) -> Path:
    path = TRIPS_DIR / f"viajes_con_te_calculado_{week}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe parquet para {week}: {path}")
    return path


def time_bin_expr() -> pl.Expr:
    hour = pl.col("tiempo_inicio_viaje").dt.hour()
    return (
        pl.when(hour < 7)
        .then(pl.lit(0))
        .when(hour < 9)
        .then(pl.lit(1))
        .when(hour < 12)
        .then(pl.lit(2))
        .when(hour < 14)
        .then(pl.lit(3))
        .when(hour < 16)
        .then(pl.lit(4))
        .when(hour < 18)
        .then(pl.lit(5))
        .when(hour < 20)
        .then(pl.lit(6))
        .otherwise(pl.lit(7))
        .cast(pl.Int8)
        .alias("time_bin")
    )


def first_trip_hour_expr(col_name: str = "first_trip_ts") -> pl.Expr:
    ts = pl.col(col_name)
    return (ts.dt.hour() + ts.dt.minute() / 60 + ts.dt.second() / 3600).cast(pl.Float64)


def scan_week(
    week: str,
    side: str,
    week_idx: int,
    *,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
) -> pl.LazyFrame:
    schema_names = pl.scan_parquet(trips_path(week)).collect_schema().names()
    select_cols = [c for c in BASE_COLUMNS if c in schema_names]
    weekday = pl.col("fecha").dt.weekday().cast(pl.Int8)
    lf = (
        pl.scan_parquet(trips_path(week))
        .select(select_cols)
        .with_columns(
            [
                pl.lit(week).alias("week"),
                pl.lit(side).alias("side"),
                pl.lit(week_idx).cast(pl.Int8).alias("week_slot"),
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("zona_inicio_viaje").cast(pl.Utf8),
                pl.col("paradero_inicio_viaje").cast(pl.Utf8),
                pl.col("metro_any").fill_null(False).cast(pl.Boolean, strict=False),
                pl.col("n_etapas_recon").cast(pl.Float64, strict=False),
                pl.col("t_total_calculado_seg").cast(pl.Float64, strict=False),
                pl.col("is_qr").cast(pl.Boolean, strict=False),
                time_bin_expr(),
                weekday.alias("weekday"),
                (pl.lit(week_idx * 10).cast(pl.Int16) + weekday.cast(pl.Int16)).alias("day_slot"),
            ]
        )
    )
    if weekdays_only:
        lf = lf.filter(pl.col("weekday") <= 5)
    if exclude_dates:
        lf = lf.filter(~pl.col("fecha").is_in(list(exclude_dates)))
    return lf


def scan_window(
    spec: WindowSpec,
    *,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
) -> pl.LazyFrame:
    frames: list[pl.LazyFrame] = []
    for i, week in enumerate(spec.base_weeks):
        frames.append(scan_week(week, "base", i, weekdays_only=weekdays_only, exclude_dates=exclude_dates))
    for i, week in enumerate(spec.eval_weeks):
        frames.append(scan_week(week, "eval", i, weekdays_only=weekdays_only, exclude_dates=exclude_dates))
    return pl.concat(frames, how="vertical")


def distribution_similarity(lf: pl.LazyFrame, category_col: str, output_col: str) -> pl.DataFrame:
    counts = lf.group_by(["id_tarjeta", "side", category_col]).agg(pl.len().alias("n"))
    totals = lf.group_by(["id_tarjeta", "side"]).agg(pl.len().alias("total"))
    shares = counts.join(totals, on=["id_tarjeta", "side"]).with_columns(
        (pl.col("n") / pl.col("total")).alias("share")
    )
    base = shares.filter(pl.col("side") == "base").select(
        ["id_tarjeta", category_col, pl.col("share").alias("share_base")]
    )
    evaluated = shares.filter(pl.col("side") == "eval").select(
        ["id_tarjeta", category_col, pl.col("share").alias("share_eval")]
    )
    return (
        base.join(evaluated, on=["id_tarjeta", category_col], how="full", coalesce=True)
        .with_columns([pl.col("share_base").fill_null(0), pl.col("share_eval").fill_null(0)])
        .group_by("id_tarjeta")
        .agg(
            (1 - 0.5 * (pl.col("share_base") - pl.col("share_eval")).abs().sum())
            .clip(0, 1)
            .alias(output_col)
        )
        .collect()
    )


def build_eligible_ids(lf: pl.LazyFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    per_side = (
        lf.group_by(["side", "id_tarjeta"])
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("day_slot").n_unique().alias("n_active_days"),
            ]
        )
        .collect()
    )
    base = per_side.filter(pl.col("side") == "base").select(
        [
            "id_tarjeta",
            pl.col("n_trips").alias("n_trips_base"),
            pl.col("n_active_days").alias("n_active_days_base"),
        ]
    )
    evaluated = per_side.filter(pl.col("side") == "eval").select(
        [
            "id_tarjeta",
            pl.col("n_trips").alias("n_trips_eval"),
            pl.col("n_active_days").alias("n_active_days_eval"),
        ]
    )
    wide = (
        base.join(evaluated, on="id_tarjeta", how="full", coalesce=True)
        .with_columns(
            [
                pl.col("n_trips_base").fill_null(0),
                pl.col("n_trips_eval").fill_null(0),
                pl.col("n_active_days_base").fill_null(0),
                pl.col("n_active_days_eval").fill_null(0),
            ]
        )
    )
    eligible = wide.filter(
        (pl.col("n_trips_base") >= MIN_TRIPS_EACH_PERIOD)
        & (pl.col("n_trips_eval") >= MIN_TRIPS_EACH_PERIOD)
        & (pl.col("n_active_days_base") >= MIN_ACTIVE_DAYS_EACH_PERIOD)
        & (pl.col("n_active_days_eval") >= MIN_ACTIVE_DAYS_EACH_PERIOD)
    ).select("id_tarjeta")
    return eligible, wide


def get_excluded_observed_day_slots(lf: pl.LazyFrame, exclude_dates: tuple[date, ...]) -> tuple[int, ...]:
    if not exclude_dates:
        return ()
    rows = (
        lf.filter(pl.col("fecha").is_in(list(exclude_dates)))
        .select("day_slot")
        .unique()
        .sort("day_slot")
        .collect()
    )
    return tuple(int(x) for x in rows["day_slot"].to_list())


def build_indicators(
    spec: WindowSpec,
    *,
    excluded_day_slots: tuple[int, ...] = (),
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
    window_id_override: str | None = None,
    note_suffix: str = "",
) -> tuple[pl.DataFrame, dict[str, object]]:
    lf_raw = scan_window(spec, weekdays_only=weekdays_only)
    excluded_date_day_slots = get_excluded_observed_day_slots(lf_raw, exclude_dates)
    effective_excluded_day_slots = tuple(sorted(set(excluded_day_slots) | set(excluded_date_day_slots)))
    lf = lf_raw
    if effective_excluded_day_slots:
        lf = lf.filter(~pl.col("day_slot").is_in(list(effective_excluded_day_slots)))
    eligible_ids, sample_wide = build_eligible_ids(lf)
    eligible_lf = eligible_ids.lazy()
    lf_eligible = lf.join(eligible_lf, on="id_tarjeta", how="inner")
    days_per_week = 5 if weekdays_only else 7
    expected_day_slots = max(len(spec.base_weeks), len(spec.eval_weeks)) * days_per_week - len(
        effective_excluded_day_slots
    )
    if expected_day_slots <= 0:
        raise ValueError(f"expected_day_slots no puede ser <= 0: {spec.window_id}")
    window_id = window_id_override or spec.window_id
    window_note = spec.note + note_suffix

    active_days = (
        lf_eligible.group_by(["id_tarjeta", "side", "day_slot"])
        .agg(pl.lit(1).alias("active"))
        .collect()
    )
    active_base = active_days.filter(pl.col("side") == "base").select(
        ["id_tarjeta", "day_slot", pl.col("active").alias("active_base")]
    )
    active_eval = active_days.filter(pl.col("side") == "eval").select(
        ["id_tarjeta", "day_slot", pl.col("active").alias("active_eval")]
    )
    dsi = (
        active_base.join(active_eval, on=["id_tarjeta", "day_slot"], how="full", coalesce=True)
        .with_columns([pl.col("active_base").fill_null(0), pl.col("active_eval").fill_null(0)])
        .group_by("id_tarjeta")
        .agg(
            (1 - (pl.col("active_base") - pl.col("active_eval")).abs().sum() / expected_day_slots)
            .clip(0, 1)
            .alias("dsi_day_sequence")
        )
    )

    tsi = distribution_similarity(lf_eligible, "time_bin", "tsi_time_distribution")
    lsi_zone = distribution_similarity(lf_eligible, "zona_inicio_viaje", "lsi_origin_zone")
    lsi_stop = distribution_similarity(lf_eligible, "paradero_inicio_viaje", "lsi_origin_stop")
    similarity = (
        dsi.join(tsi, on="id_tarjeta", how="inner")
        .join(lsi_zone, on="id_tarjeta", how="inner")
        .join(lsi_stop, on="id_tarjeta", how="inner")
    )

    period_metrics = (
        lf_eligible.group_by(["id_tarjeta", "side"])
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("day_slot").n_unique().alias("n_active_days"),
                pl.col("n_etapas_recon").mean().alias("mean_n_etapas_recon"),
                pl.col("metro_any").cast(pl.Int8).mean().alias("share_metro_any"),
                (pl.col("t_total_calculado_seg").mean() / 60).alias("mean_total_time_min"),
                pl.col("is_qr").cast(pl.Int8).mean().alias("share_is_qr"),
            ]
        )
        .collect()
    )
    daily_first = (
        lf_eligible.group_by(["id_tarjeta", "side", "day_slot"])
        .agg(pl.col("tiempo_inicio_viaje").min().alias("first_trip_ts"))
        .with_columns(first_trip_hour_expr().alias("first_trip_hour"))
        .group_by(["id_tarjeta", "side"])
        .agg(pl.col("first_trip_hour").mean().alias("mean_first_trip_hour"))
        .collect()
    )
    period_metrics = period_metrics.join(daily_first, on=["id_tarjeta", "side"], how="left")

    base_metrics = period_metrics.filter(pl.col("side") == "base").select(
        [
            "id_tarjeta",
            pl.col("n_trips").alias("n_trips_base"),
            pl.col("n_active_days").alias("n_active_days_base"),
            pl.col("mean_n_etapas_recon").alias("mean_n_etapas_recon_base"),
            pl.col("share_metro_any").alias("share_metro_any_base"),
            pl.col("mean_total_time_min").alias("mean_total_time_min_base"),
            pl.col("share_is_qr").alias("share_is_qr_base"),
            pl.col("mean_first_trip_hour").alias("mean_first_trip_hour_base"),
        ]
    )
    eval_metrics = period_metrics.filter(pl.col("side") == "eval").select(
        [
            "id_tarjeta",
            pl.col("n_trips").alias("n_trips_eval"),
            pl.col("n_active_days").alias("n_active_days_eval"),
            pl.col("mean_n_etapas_recon").alias("mean_n_etapas_recon_eval"),
            pl.col("share_metro_any").alias("share_metro_any_eval"),
            pl.col("mean_total_time_min").alias("mean_total_time_min_eval"),
            pl.col("share_is_qr").alias("share_is_qr_eval"),
            pl.col("mean_first_trip_hour").alias("mean_first_trip_hour_eval"),
        ]
    )
    wide_metrics = base_metrics.join(eval_metrics, on="id_tarjeta", how="inner")
    change = wide_metrics.with_columns(
        [
            ((pl.col("n_trips_eval") + 1).log() - (pl.col("n_trips_base") + 1).log()).alias(
                "log_ratio_n_trips"
            ),
            (pl.col("mean_n_etapas_recon_eval") - pl.col("mean_n_etapas_recon_base")).alias(
                "delta_mean_n_etapas_recon"
            ),
            (pl.col("share_metro_any_eval") - pl.col("share_metro_any_base")).alias(
                "delta_share_metro_any"
            ),
            (pl.col("mean_first_trip_hour_eval") - pl.col("mean_first_trip_hour_base")).alias(
                "delta_mean_first_trip_hour"
            ),
            (pl.col("mean_total_time_min_eval") - pl.col("mean_total_time_min_base")).alias(
                "delta_mean_total_time_min"
            ),
        ]
    )

    indicators = (
        change.join(similarity, on="id_tarjeta", how="inner")
        .with_columns(
            [
                pl.lit(window_id).alias("window_id"),
                pl.lit(",".join(spec.base_weeks)).alias("base_weeks"),
                pl.lit(",".join(spec.eval_weeks)).alias("eval_weeks"),
                pl.lit(window_note).alias("window_note"),
            ]
        )
        .select(
            [
                "window_id",
                "id_tarjeta",
                "base_weeks",
                "eval_weeks",
                "window_note",
                "n_trips_base",
                "n_trips_eval",
                "n_active_days_base",
                "n_active_days_eval",
                "share_is_qr_base",
                "share_is_qr_eval",
                *INDICATOR_COLUMNS,
            ]
        )
    )

    inventory = collect_window_inventory(
        spec,
        weekdays_only=weekdays_only,
        exclude_dates=exclude_dates,
        excluded_day_slots=effective_excluded_day_slots,
    )
    credentials_both = sample_wide.filter((pl.col("n_trips_base") > 0) & (pl.col("n_trips_eval") > 0)).height
    summary = {
        "window_id": window_id,
        "base_weeks": ",".join(spec.base_weeks),
        "eval_weeks": ",".join(spec.eval_weeks),
        "note": window_note,
        "excluded_day_slots": ",".join(str(x) for x in effective_excluded_day_slots),
        "excluded_dates": ",".join(x.isoformat() for x in exclude_dates),
        "excluded_date_slots": len(excluded_date_day_slots),
        "weekdays_only": weekdays_only,
        "expected_day_slots": expected_day_slots,
        "credentials_union": sample_wide.height,
        "credentials_both_periods_any_activity": credentials_both,
        "credentials_eligible": eligible_ids.height,
        "min_trips_each_period": MIN_TRIPS_EACH_PERIOD,
        "min_active_days_each_period": MIN_ACTIVE_DAYS_EACH_PERIOD,
        **inventory,
    }
    return indicators, summary


def collect_window_inventory(
    spec: WindowSpec,
    *,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
    excluded_day_slots: tuple[int, ...] = (),
) -> dict[str, object]:
    rows: dict[str, object] = {}
    for side, weeks in [("base", spec.base_weeks), ("eval", spec.eval_weeks)]:
        frames = []
        for week_idx, week in enumerate(weeks):
            weekday = pl.col("fecha").dt.weekday().cast(pl.Int8)
            lf = (
                pl.scan_parquet(trips_path(week))
                .select(["fecha", "is_qr"])
                .with_columns((pl.lit(week_idx * 10).cast(pl.Int16) + weekday.cast(pl.Int16)).alias("day_slot"))
            )
            if weekdays_only:
                lf = lf.filter(pl.col("fecha").dt.weekday() <= 5)
            if exclude_dates:
                lf = lf.filter(~pl.col("fecha").is_in(list(exclude_dates)))
            if excluded_day_slots:
                lf = lf.filter(~pl.col("day_slot").is_in(list(excluded_day_slots)))
            frames.append(
                lf.group_by("fecha")
                .agg(pl.len().alias("rows"), pl.col("is_qr").cast(pl.Float64).mean().alias("is_qr_share"))
                .with_columns(pl.lit(week).alias("week"))
                .collect()
            )
        inv = pl.concat(frames, how="vertical").sort(["week", "fecha"])
        rows[f"{side}_rows"] = int(inv["rows"].sum())
        rows[f"{side}_n_dates"] = inv["fecha"].n_unique()
        rows[f"{side}_min_fecha"] = str(inv["fecha"].min())
        rows[f"{side}_max_fecha"] = str(inv["fecha"].max())
        rows[f"{side}_is_qr_share_weighted"] = float(
            (inv["rows"] * inv["is_qr_share"]).sum() / inv["rows"].sum()
        )
    return rows


def summarize_indicators(df: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for col in INDICATOR_COLUMNS:
        s = df[col].drop_nulls().to_numpy()
        rows.append(
            {
                "window_id": df["window_id"][0],
                "feature": col,
                "n": int(len(s)),
                "mean": float(np.mean(s)),
                "std": float(np.std(s)),
                "p10": float(np.percentile(s, 10)),
                "p25": float(np.percentile(s, 25)),
                "median": float(np.median(s)),
                "p75": float(np.percentile(s, 75)),
                "p90": float(np.percentile(s, 90)),
            }
        )
    return pl.DataFrame(rows)


def finite_pair(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    x = a.to_numpy(dtype=float)
    y = b.to_numpy(dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    return x[mask], y[mask]


def compare_two_windows(left: pd.DataFrame, right: pd.DataFrame, left_id: str, right_id: str) -> pd.DataFrame:
    merged = left[["id_tarjeta", *INDICATOR_COLUMNS]].merge(
        right[["id_tarjeta", *INDICATOR_COLUMNS]],
        on="id_tarjeta",
        how="inner",
        suffixes=("_left", "_right"),
    )
    rows = []
    for col in INDICATOR_COLUMNS:
        x, y = finite_pair(merged[f"{col}_left"], merged[f"{col}_right"])
        if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
            pearson = math.nan
            spearman = math.nan
        else:
            pearson = float(pearsonr(x, y).statistic)
            spearman = float(spearmanr(x, y).statistic)
        rows.append(
            {
                "left_window": left_id,
                "right_window": right_id,
                "feature": col,
                "n_common": int(len(x)),
                "pearson": pearson,
                "spearman": spearman,
                "mae": float(np.mean(np.abs(y - x))) if len(x) else math.nan,
                "mean_delta_right_minus_left": float(np.mean(y - x)) if len(x) else math.nan,
                "median_abs_delta": float(np.median(np.abs(y - x))) if len(x) else math.nan,
            }
        )
    return pd.DataFrame(rows)


def day_slot_inventory(
    spec: WindowSpec,
    *,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
    excluded_day_slots: tuple[int, ...] = (),
) -> pd.DataFrame:
    rows = []
    lf = scan_window(spec, weekdays_only=weekdays_only, exclude_dates=exclude_dates)
    if excluded_day_slots:
        lf = lf.filter(~pl.col("day_slot").is_in(list(excluded_day_slots)))
    inv = lf.select(["side", "week", "fecha", "week_slot", "weekday", "day_slot"]).unique().sort(
        ["side", "week_slot", "weekday"]
    ).collect()
    for row in inv.iter_rows(named=True):
        rows.append({**row, "window_id": spec.window_id})
    return pd.DataFrame(rows)


def run_internal_reliability(
    out_dir: Path,
    *,
    windows: list[WindowSpec] = WINDOWS,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
) -> None:
    rows = []
    summaries = []
    for spec in windows:
        if len(spec.base_weeks) != len(spec.eval_weeks) or len(spec.base_weeks) < 2:
            continue
        component_frames: list[tuple[str, pd.DataFrame, dict[str, object]]] = []
        for i, (base_week, eval_week) in enumerate(zip(spec.base_weeks, spec.eval_weeks, strict=True)):
            component_id = f"{spec.window_id}__component_{i}_{base_week}_to_{eval_week}"
            component_spec = WindowSpec(
                component_id,
                (base_week,),
                (eval_week,),
                f"componente semanal {i} de {spec.window_id}",
            )
            df, summary = build_indicators(
                component_spec,
                weekdays_only=weekdays_only,
                exclude_dates=exclude_dates,
            )
            component_frames.append((component_id, df.to_pandas(), summary))
            summaries.append(summary)
        for (left_id, left_df, _), (right_id, right_df, _) in itertools.combinations(component_frames, 2):
            cmp_df = compare_two_windows(left_df, right_df, left_id, right_id)
            cmp_df.insert(0, "parent_window", spec.window_id)
            rows.append(cmp_df)
    if rows:
        pd.concat(rows, ignore_index=True).to_csv(out_dir / "internal_week_reliability.csv", index=False)
    if summaries:
        pl.DataFrame(summaries).write_csv(out_dir / "internal_week_component_summary.csv")


def run_leave_one_day_out(
    out_dir: Path,
    full_indicators_by_window: dict[str, pd.DataFrame],
    *,
    windows: list[WindowSpec] = WINDOWS,
    weekdays_only: bool = False,
    exclude_dates: tuple[date, ...] = (),
) -> None:
    rows = []
    day_inventory_rows = []
    for spec in windows:
        excluded_date_day_slots = get_excluded_observed_day_slots(
            scan_window(spec, weekdays_only=weekdays_only),
            exclude_dates,
        )
        inventory = day_slot_inventory(
            spec,
            weekdays_only=weekdays_only,
            exclude_dates=exclude_dates,
            excluded_day_slots=excluded_date_day_slots,
        )
        day_inventory_rows.append(inventory)
        full_df = full_indicators_by_window[spec.window_id]
        for day_slot in sorted(inventory["day_slot"].unique()):
            variant_id = f"{spec.window_id}__drop_day_slot_{int(day_slot)}"
            variant_df, summary = build_indicators(
                spec,
                excluded_day_slots=(int(day_slot),),
                weekdays_only=weekdays_only,
                exclude_dates=exclude_dates,
                window_id_override=variant_id,
                note_suffix=f"; leave-one-day-slot-out={int(day_slot)}",
            )
            cmp_df = compare_two_windows(full_df, variant_df.to_pandas(), spec.window_id, variant_id)
            cmp_df.insert(0, "parent_window", spec.window_id)
            cmp_df.insert(1, "dropped_day_slot", int(day_slot))
            cmp_df.insert(2, "variant_eligible", int(summary["credentials_eligible"]))
            cmp_df.insert(
                3,
                "delta_eligible_vs_full",
                int(summary["credentials_eligible"]) - int(len(full_df)),
            )
            rows.append(cmp_df)
    if rows:
        pd.concat(rows, ignore_index=True).to_csv(out_dir / "leave_one_day_out_stability.csv", index=False)
    if day_inventory_rows:
        pd.concat(day_inventory_rows, ignore_index=True).to_csv(out_dir / "day_slot_inventory.csv", index=False)


def run_consensus(pairwise: pd.DataFrame, out_dir: Path) -> None:
    mirrored = pairwise.copy()
    mirrored["left_window"] = pairwise["right_window"]
    mirrored["right_window"] = pairwise["left_window"]
    mirrored["mean_delta_right_minus_left"] = -pairwise["mean_delta_right_minus_left"]
    long = pd.concat([pairwise, mirrored], ignore_index=True)
    consensus = (
        long.groupby(["left_window", "feature"], as_index=False)
        .agg(
            n_comparisons=("right_window", "nunique"),
            mean_n_common=("n_common", "mean"),
            mean_spearman_vs_others=("spearman", "mean"),
            median_spearman_vs_others=("spearman", "median"),
            min_spearman_vs_others=("spearman", "min"),
            mean_mae_vs_others=("mae", "mean"),
            median_mae_vs_others=("mae", "median"),
        )
        .rename(columns={"left_window": "window_id"})
    )
    consensus.to_csv(out_dir / "consensus_window_similarity.csv", index=False)
    summary = (
        consensus.groupby("window_id", as_index=False)
        .agg(
            mean_spearman_all_features=("mean_spearman_vs_others", "mean"),
            min_spearman_all_features=("min_spearman_vs_others", "min"),
            mean_mae_all_features=("mean_mae_vs_others", "mean"),
            mean_n_common=("mean_n_common", "mean"),
        )
        .sort_values(["mean_spearman_all_features", "mean_mae_all_features"], ascending=[False, True])
    )
    summary.to_csv(out_dir / "consensus_window_summary.csv", index=False)


def week_to_order(week: str) -> int:
    year, week_no = week.split("-W")
    return int(year) * 100 + int(week_no)


def credential_channel_target(week: str) -> pd.DataFrame:
    return (
        pl.scan_parquet(trips_path(week))
        .select(["id_tarjeta", "is_qr"])
        .with_columns([pl.col("id_tarjeta").cast(pl.Utf8), pl.col("is_qr").cast(pl.Float64, strict=False)])
        .group_by("id_tarjeta")
        .agg(pl.col("is_qr").mean().alias("target_is_qr_share"))
        .with_columns((pl.col("target_is_qr_share") >= 0.5).cast(pl.Int8).alias("target_is_qr"))
        .collect()
        .to_pandas()
    )


def cross_validated_auc(x: np.ndarray, y: np.ndarray) -> tuple[float, float, int]:
    if len(np.unique(y)) < 2:
        return math.nan, math.nan, 0
    counts = np.bincount(y.astype(int))
    min_class_count = int(counts[counts > 0].min())
    n_splits = min(N_MODEL_SPLITS, min_class_count)
    if n_splits < 2:
        return math.nan, math.nan, 0
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    aucs = []
    for train_idx, test_idx in splitter.split(x, y):
        model = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"),
        )
        model.fit(x[train_idx], y[train_idx])
        proba = model.predict_proba(x[test_idx])[:, 1]
        aucs.append(roc_auc_score(y[test_idx], proba))
    return float(np.mean(aucs)), float(np.std(aucs)), int(n_splits)


def run_downstream_validity(
    indicators_by_window: dict[str, pd.DataFrame],
    out_dir: Path,
    *,
    windows: list[WindowSpec] = WINDOWS,
) -> None:
    target = credential_channel_target(TARGET_WEEK_FOR_DOWNSTREAM)
    target_order = week_to_order(TARGET_WEEK_FOR_DOWNSTREAM)
    rows = []
    for spec in windows:
        df = indicators_by_window[spec.window_id]
        eval_orders = [week_to_order(w) for w in spec.eval_weeks]
        includes_target_week = TARGET_WEEK_FOR_DOWNSTREAM in spec.eval_weeks
        strictly_pre_target = max(eval_orders) < target_order
        valid_for_target = strictly_pre_target and not includes_target_week
        merged = df.merge(target, on="id_tarjeta", how="inner")
        auc_mean = math.nan
        auc_std = math.nan
        n_splits = 0
        if valid_for_target and len(merged):
            x = merged[INDICATOR_COLUMNS].to_numpy(dtype=float)
            y = merged["target_is_qr"].to_numpy(dtype=int)
            auc_mean, auc_std, n_splits = cross_validated_auc(x, y)
        rows.append(
            {
                "window_id": spec.window_id,
                "base_weeks": ",".join(spec.base_weeks),
                "eval_weeks": ",".join(spec.eval_weeks),
                "target_week": TARGET_WEEK_FOR_DOWNSTREAM,
                "includes_target_week": includes_target_week,
                "strictly_pre_target": strictly_pre_target,
                "valid_for_downstream_target": valid_for_target,
                "n_common_with_target": int(len(merged)),
                "target_qr_prevalence": float(merged["target_is_qr"].mean()) if len(merged) else math.nan,
                "roc_auc_cv_mean": auc_mean,
                "roc_auc_cv_std": auc_std,
                "n_cv_splits": n_splits,
            }
        )
    pd.DataFrame(rows).to_csv(out_dir / "downstream_w17_no_leakage_validity.csv", index=False)


def run_channel_separation(indicators_by_window: dict[str, pd.DataFrame], out_dir: Path) -> None:
    model_rows = []
    assoc_rows = []
    for window_id, df in indicators_by_window.items():
        work = df.dropna(subset=INDICATOR_COLUMNS).copy()
        work["channel_is_qr"] = (work["share_is_qr_eval"].fillna(work["share_is_qr_base"]) >= 0.5).astype(int)
        x = work[INDICATOR_COLUMNS].to_numpy(dtype=float)
        y = work["channel_is_qr"].to_numpy(dtype=int)
        auc_mean, auc_std, n_splits = cross_validated_auc(x, y)
        model_rows.append(
            {
                "window_id": window_id,
                "n": int(len(work)),
                "qr_prevalence": float(work["channel_is_qr"].mean()) if len(work) else math.nan,
                "roc_auc_indicators_predict_channel_mean": auc_mean,
                "roc_auc_indicators_predict_channel_std": auc_std,
                "n_cv_splits": n_splits,
            }
        )
        for col in INDICATOR_COLUMNS:
            qr = work.loc[work["channel_is_qr"] == 1, col].to_numpy(dtype=float)
            bip = work.loc[work["channel_is_qr"] == 0, col].to_numpy(dtype=float)
            pooled = np.sqrt((np.nanvar(qr) + np.nanvar(bip)) / 2)
            x_col, y_col = finite_pair(work[col], work["channel_is_qr"])
            assoc_rows.append(
                {
                    "window_id": window_id,
                    "feature": col,
                    "n": int(len(x_col)),
                    "mean_qr": float(np.nanmean(qr)) if len(qr) else math.nan,
                    "mean_bip": float(np.nanmean(bip)) if len(bip) else math.nan,
                    "standardized_mean_diff_qr_minus_bip": float((np.nanmean(qr) - np.nanmean(bip)) / pooled)
                    if pooled and np.isfinite(pooled)
                    else math.nan,
                    "pearson_with_channel": float(pearsonr(x_col, y_col).statistic)
                    if len(x_col) >= 3 and np.std(x_col) > 0 and np.std(y_col) > 0
                    else math.nan,
                    "spearman_with_channel": float(spearmanr(x_col, y_col).statistic)
                    if len(x_col) >= 3 and np.std(x_col) > 0 and np.std(y_col) > 0
                    else math.nan,
                }
            )
    pd.DataFrame(model_rows).to_csv(out_dir / "channel_separation_by_window.csv", index=False)
    pd.DataFrame(assoc_rows).to_csv(out_dir / "indicator_channel_association.csv", index=False)


def kmeans_labels(df: pd.DataFrame, window_id: str, k: int, max_rows: int) -> tuple[pd.DataFrame, dict[str, object]]:
    cols = ["id_tarjeta", *CLUSTER_FEATURES]
    xdf = df[cols].dropna().copy()
    if len(xdf) > max_rows:
        xdf = xdf.sample(n=max_rows, random_state=42)
    x = xdf[CLUSTER_FEATURES].to_numpy(dtype=float)
    x_scaled = StandardScaler().fit_transform(x)
    model = KMeans(n_clusters=k, n_init=20, random_state=42)
    labels = model.fit_predict(x_scaled)
    sil_n = min(len(x_scaled), 5_000)
    sil = math.nan
    if len(x_scaled) > k:
        if len(x_scaled) > sil_n:
            rng = np.random.default_rng(42)
            idx = rng.choice(len(x_scaled), size=sil_n, replace=False)
            sil = float(silhouette_score(x_scaled[idx], labels[idx]))
        else:
            sil = float(silhouette_score(x_scaled, labels))
    out = pd.DataFrame({"id_tarjeta": xdf["id_tarjeta"].to_numpy(), f"k{k}_label": labels})
    meta = {
        "window_id": window_id,
        "k": k,
        "n_fit": int(len(xdf)),
        "inertia": float(model.inertia_),
        "silhouette_sample": sil,
    }
    return out, meta


def run_cluster_audit(indicators_by_window: dict[str, pd.DataFrame], out_dir: Path, max_rows: int) -> None:
    label_sets: dict[tuple[str, int], pd.DataFrame] = {}
    metrics = []
    for window_id, df in indicators_by_window.items():
        for k in [2, 3]:
            labels, meta = kmeans_labels(df, window_id, k, max_rows)
            label_sets[(window_id, k)] = labels
            metrics.append(meta)

    ari_rows = []
    for k in [2, 3]:
        baseline = label_sets[("W17_baseline", k)]
        for window_id in indicators_by_window:
            other = label_sets[(window_id, k)]
            merged = baseline.merge(other, on="id_tarjeta", how="inner")
            ari = adjusted_rand_score(merged[f"k{k}_label_x"], merged[f"k{k}_label_y"]) if len(merged) else math.nan
            ari_rows.append(
                {
                    "baseline_window": "W17_baseline",
                    "comparison_window": window_id,
                    "k": k,
                    "n_common_sampled": int(len(merged)),
                    "ari_vs_baseline": float(ari),
                }
            )
    pd.DataFrame(metrics).to_csv(out_dir / "kmeans_window_metrics.csv", index=False)
    pd.DataFrame(ari_rows).to_csv(out_dir / "kmeans_ari_vs_baseline.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit de sensibilidad de ventanas para indicadores de segmentacion.")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--max-kmeans-rows", type=int, default=KMEANS_MAX_ROWS)
    parser.add_argument("--skip-clusters", action="store_true")
    parser.add_argument("--skip-internal-reliability", action="store_true")
    parser.add_argument("--skip-leave-one-day", action="store_true")
    parser.add_argument("--skip-downstream-validity", action="store_true")
    parser.add_argument("--skip-channel-separation", action="store_true")
    parser.add_argument(
        "--weekdays-only",
        action="store_true",
        help="Usa solo lunes-viernes. DSI queda con N=5 por semana, N=10 en ventanas de dos semanas.",
    )
    parser.add_argument(
        "--window-id",
        action="append",
        default=None,
        help="Filtra una o mas ventanas por window_id. Puede repetirse.",
    )
    parser.add_argument(
        "--exclude-date",
        action="append",
        default=None,
        help="Excluye una fecha YYYY-MM-DD del calculo. Puede repetirse; util para feriados.",
    )
    args = parser.parse_args()
    exclude_dates = tuple(date.fromisoformat(x) for x in args.exclude_date or [])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    indicator_paths = []
    summaries = []
    indicator_summaries = []
    indicators_by_window: dict[str, pd.DataFrame] = {}

    selected_windows = WINDOWS
    if args.window_id:
        selected_ids = set(args.window_id)
        selected_windows = [spec for spec in WINDOWS if spec.window_id in selected_ids]
        missing_ids = selected_ids - {spec.window_id for spec in selected_windows}
        if missing_ids:
            raise ValueError(f"window_id desconocidos: {sorted(missing_ids)}")

    for spec in selected_windows:
        print(f"[window] {spec.window_id}: {spec.base_weeks} -> {spec.eval_weeks}", flush=True)
        df, summary = build_indicators(
            spec,
            weekdays_only=args.weekdays_only,
            exclude_dates=exclude_dates,
        )
        out_path = args.out_dir / f"indicators_{spec.window_id}.parquet"
        df.write_parquet(out_path, compression="zstd")
        indicator_paths.append({"window_id": spec.window_id, "path": str(out_path)})
        summaries.append(summary)
        indicator_summaries.append(summarize_indicators(df))
        indicators_by_window[spec.window_id] = df.to_pandas()
        print(f"  eligible={summary['credentials_eligible']:,} path={out_path}", flush=True)

    pl.DataFrame(summaries).write_csv(args.out_dir / "window_sample_summary.csv")
    pl.concat(indicator_summaries, how="vertical").write_csv(args.out_dir / "indicator_distribution_summary.csv")
    pl.DataFrame(indicator_paths).write_csv(args.out_dir / "indicator_artifact_inventory.csv")

    comparisons = []
    for left_id, right_id in itertools.combinations(indicators_by_window.keys(), 2):
        comparisons.append(compare_two_windows(indicators_by_window[left_id], indicators_by_window[right_id], left_id, right_id))
    if comparisons:
        pairwise = pd.concat(comparisons, ignore_index=True)
        pairwise.to_csv(args.out_dir / "pairwise_indicator_similarity.csv", index=False)
        run_consensus(pairwise, args.out_dir)

    if "W17_baseline" in indicators_by_window:
        baseline = indicators_by_window["W17_baseline"]
        vs_baseline = []
        for window_id, df in indicators_by_window.items():
            vs_baseline.append(compare_two_windows(baseline, df, "W17_baseline", window_id))
        pd.concat(vs_baseline, ignore_index=True).to_csv(args.out_dir / "indicator_similarity_vs_baseline.csv", index=False)

    if not args.skip_clusters:
        run_cluster_audit(indicators_by_window, args.out_dir, args.max_kmeans_rows)

    if not args.skip_internal_reliability:
        print("[diagnostic] internal week reliability", flush=True)
        run_internal_reliability(
            args.out_dir,
            windows=selected_windows,
            weekdays_only=args.weekdays_only,
            exclude_dates=exclude_dates,
        )
    if not args.skip_leave_one_day:
        print("[diagnostic] leave-one-day-out stability", flush=True)
        run_leave_one_day_out(
            args.out_dir,
            indicators_by_window,
            windows=selected_windows,
            weekdays_only=args.weekdays_only,
            exclude_dates=exclude_dates,
        )
    if not args.skip_downstream_validity:
        print("[diagnostic] downstream no-leakage validity", flush=True)
        run_downstream_validity(indicators_by_window, args.out_dir, windows=selected_windows)
    if not args.skip_channel_separation:
        print("[diagnostic] QR/BIP channel separation", flush=True)
        run_channel_separation(indicators_by_window, args.out_dir)

    print(f"Audit escrito en: {args.out_dir}", flush=True)


if __name__ == "__main__":
    main()
