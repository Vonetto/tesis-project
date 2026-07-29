from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

PROCESSED_TRIPS_BY_WEEK = {
    "2024-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W14.parquet",
    "2024-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W15.parquet",
    "2024-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W16.parquet",
    "2024-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W17.parquet",
    "2025-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W14.parquet",
    "2025-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W15.parquet",
    "2025-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W16.parquet",
    "2025-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W17.parquet",
}

SCOPE_WEEKS = {
    "active": ["2024-W17", "2025-W17"],
    "ml_2025": ["2025-W14", "2025-W15", "2025-W17"],
    "interannual_ml": [
        "2024-W14",
        "2024-W15",
        "2024-W16",
        "2024-W17",
        "2025-W14",
        "2025-W15",
        "2025-W16",
        "2025-W17",
    ],
}

RHYTHM_FEATURES = [
    "rhythm_trips_per_active_day",
    "rhythm_trips_per_active_week",
    "rhythm_active_weeks_rate_scope",
    "rhythm_active_day_density_span",
    "rhythm_trips_per_span_day",
    "rhythm_activity_top1_day_share",
    "rhythm_activity_top2_day_share",
    "rhythm_daily_hhi",
    "rhythm_daily_entropy_norm",
    "rhythm_daily_burstiness",
    "rhythm_single_trip_day_share",
    "rhythm_has_gap",
    "rhythm_n_gap_days",
    "rhythm_median_gap_active_days",
    "rhythm_mean_gap_active_days",
    "rhythm_max_gap_active_days",
    "rhythm_weekly_top1_share",
    "rhythm_weekly_hhi",
    "rhythm_weekly_entropy_norm",
    "rhythm_weekly_burstiness",
]


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_rhythm_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_behavior_rhythm_features_{stem}_{scope}.csv"


def panel_path(scope: str, variant: str = "clean") -> Path:
    return OUT_DIR / f"user_level_payment_panel_{scope}_{variant}.parquet"


def validate_inputs(scope: str, weeks: list[str]) -> None:
    if scope not in SCOPE_WEEKS:
        raise ValueError(f"Scope no soportado: {scope}")
    missing = [str(PROCESSED_TRIPS_BY_WEEK[w]) for w in weeks if not PROCESSED_TRIPS_BY_WEEK[w].exists()]
    if missing:
        raise FileNotFoundError(f"Faltan viajes procesados: {missing}")


def assert_unique_key(df: pl.DataFrame, key: str, name: str) -> None:
    n_rows = df.height
    n_unique = df.select(pl.col(key).n_unique()).item()
    if n_rows != n_unique:
        raise ValueError(f"{name}: {key} no es unico ({n_unique} de {n_rows})")


def load_week_lf(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema = set(lf.collect_schema().names())
    required = {"id_tarjeta", "fecha", "semana_iso"}
    missing = sorted(required - schema)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    return (
        lf.select(
            [
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("fecha").cast(pl.Date).alias("trip_date"),
                pl.col("semana_iso").cast(pl.Utf8),
            ]
        )
        .drop_nulls(["id_tarjeta", "trip_date", "semana_iso"])
        .with_columns(pl.lit(week).alias("partition"))
    )


def trips_lf_for_scope(weeks: Iterable[str]) -> pl.LazyFrame:
    return pl.concat([load_week_lf(w) for w in weeks], how="diagonal_relaxed")


def safe_ratio(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den == 0).then(None).otherwise(num / den)


def entropy_norm_expr(entropy_col: str, n_col: str) -> pl.Expr:
    return (
        pl.when(pl.col(n_col) <= 1)
        .then(0.0)
        .otherwise(pl.col(entropy_col) / pl.col(n_col).cast(pl.Float64).log())
    )


def build_daily_features(daily_counts: pl.DataFrame) -> pl.DataFrame:
    totals = (
        daily_counts.group_by("id_tarjeta")
        .agg(
            [
                pl.col("n_day_trips").sum().alias("rhythm_n_trips"),
                pl.len().alias("rhythm_n_active_days"),
                pl.col("trip_date").min().alias("rhythm_first_active_date"),
                pl.col("trip_date").max().alias("rhythm_last_active_date"),
                pl.col("n_day_trips").max().alias("max_day_trips"),
                pl.col("n_day_trips").mean().alias("mean_day_trips"),
                pl.col("n_day_trips").median().alias("median_day_trips"),
                pl.col("n_day_trips").std().alias("std_day_trips"),
                (pl.col("n_day_trips") == 1).sum().alias("n_single_trip_days"),
            ]
        )
        .with_columns(
            (
                (pl.col("rhythm_last_active_date") - pl.col("rhythm_first_active_date"))
                .dt.total_days()
                + 1
            ).alias("rhythm_span_days")
        )
    )

    ranked = (
        daily_counts.sort(["id_tarjeta", "n_day_trips", "trip_date"], descending=[False, True, False])
        .with_columns((pl.int_range(pl.len()).over("id_tarjeta") + 1).alias("day_rank"))
        .filter(pl.col("day_rank") <= 2)
        .join(totals.select(["id_tarjeta", "rhythm_n_trips"]), on="id_tarjeta", how="left")
        .group_by("id_tarjeta")
        .agg(
            [
                pl.when(pl.col("day_rank") == 1)
                .then(pl.col("n_day_trips") / pl.col("rhythm_n_trips"))
                .otherwise(None)
                .max()
                .alias("rhythm_activity_top1_day_share"),
                (pl.col("n_day_trips").sum() / pl.col("rhythm_n_trips").max()).alias(
                    "rhythm_activity_top2_day_share"
                ),
            ]
        )
    )

    distribution = (
        daily_counts.join(totals.select(["id_tarjeta", "rhythm_n_trips", "rhythm_n_active_days"]), on="id_tarjeta")
        .with_columns((pl.col("n_day_trips") / pl.col("rhythm_n_trips")).alias("p_day"))
        .with_columns(
            [
                (pl.col("p_day") * pl.col("p_day")).alias("hhi_part"),
                (-(pl.col("p_day") * pl.col("p_day").log())).alias("entropy_part"),
            ]
        )
        .group_by("id_tarjeta")
        .agg(
            [
                pl.col("hhi_part").sum().alias("rhythm_daily_hhi"),
                pl.col("entropy_part").sum().alias("daily_entropy"),
            ]
        )
        .join(totals.select(["id_tarjeta", "rhythm_n_active_days"]), on="id_tarjeta", how="left")
        .with_columns(entropy_norm_expr("daily_entropy", "rhythm_n_active_days").alias("rhythm_daily_entropy_norm"))
        .with_columns((1.0 - pl.col("rhythm_daily_entropy_norm")).alias("rhythm_daily_burstiness"))
        .drop("daily_entropy")
    )

    out = (
        totals.join(ranked, on="id_tarjeta", how="left")
        .join(distribution, on="id_tarjeta", how="left")
        .with_columns(
            [
                safe_ratio(pl.col("rhythm_n_trips"), pl.col("rhythm_n_active_days")).alias(
                    "rhythm_trips_per_active_day"
                ),
                safe_ratio(pl.col("rhythm_n_active_days"), pl.col("rhythm_span_days")).alias(
                    "rhythm_active_day_density_span"
                ),
                safe_ratio(pl.col("rhythm_n_trips"), pl.col("rhythm_span_days")).alias(
                    "rhythm_trips_per_span_day"
                ),
                safe_ratio(pl.col("n_single_trip_days"), pl.col("rhythm_n_active_days")).alias(
                    "rhythm_single_trip_day_share"
                ),
            ]
        )
    )
    return out


def build_gap_features(daily_counts: pl.DataFrame) -> pl.DataFrame:
    active_days = daily_counts.select(["id_tarjeta", "trip_date"]).sort(["id_tarjeta", "trip_date"])
    gaps = (
        active_days.with_columns(
            (pl.col("trip_date") - pl.col("trip_date").shift(1).over("id_tarjeta"))
            .dt.total_days()
            .alias("gap_days")
        )
        .filter(pl.col("gap_days").is_not_null())
    )
    if gaps.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})

    return gaps.group_by("id_tarjeta").agg(
        [
            pl.len().alias("rhythm_n_gap_days"),
            pl.col("gap_days").median().alias("rhythm_median_gap_active_days"),
            pl.col("gap_days").mean().alias("rhythm_mean_gap_active_days"),
            pl.col("gap_days").max().alias("rhythm_max_gap_active_days"),
        ]
    )


def build_weekly_features(weekly_counts: pl.DataFrame, scope_n_weeks: int) -> pl.DataFrame:
    totals = weekly_counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_week_trips").sum().alias("rhythm_n_week_trips"),
            pl.len().alias("rhythm_n_active_weeks"),
            pl.col("n_week_trips").max().alias("max_week_trips"),
        ]
    )
    distribution = (
        weekly_counts.join(totals.select(["id_tarjeta", "rhythm_n_week_trips", "rhythm_n_active_weeks"]), on="id_tarjeta")
        .with_columns((pl.col("n_week_trips") / pl.col("rhythm_n_week_trips")).alias("p_week"))
        .with_columns(
            [
                (pl.col("p_week") * pl.col("p_week")).alias("hhi_part"),
                (-(pl.col("p_week") * pl.col("p_week").log())).alias("entropy_part"),
            ]
        )
        .group_by("id_tarjeta")
        .agg(
            [
                pl.col("hhi_part").sum().alias("rhythm_weekly_hhi"),
                pl.col("entropy_part").sum().alias("weekly_entropy"),
            ]
        )
        .join(totals, on="id_tarjeta", how="left")
        .with_columns(
            [
                safe_ratio(pl.col("rhythm_n_week_trips"), pl.col("rhythm_n_active_weeks")).alias(
                    "rhythm_trips_per_active_week"
                ),
                (pl.col("rhythm_n_active_weeks") / float(scope_n_weeks)).alias(
                    "rhythm_active_weeks_rate_scope"
                ),
                safe_ratio(pl.col("max_week_trips"), pl.col("rhythm_n_week_trips")).alias(
                    "rhythm_weekly_top1_share"
                ),
                entropy_norm_expr("weekly_entropy", "rhythm_n_active_weeks").alias("rhythm_weekly_entropy_norm"),
            ]
        )
        .with_columns((1.0 - pl.col("rhythm_weekly_entropy_norm")).alias("rhythm_weekly_burstiness"))
        .drop(["weekly_entropy", "max_week_trips"])
    )
    return distribution


def build_rhythm_features(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo rhythm_pack scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)

    daily_counts = collect_streaming(
        trips_lf.group_by(["id_tarjeta", "trip_date"]).agg(pl.len().alias("n_day_trips"))
    )
    weekly_counts = collect_streaming(
        trips_lf.group_by(["id_tarjeta", "semana_iso"]).agg(pl.len().alias("n_week_trips"))
    )

    daily = build_daily_features(daily_counts)
    gaps = build_gap_features(daily_counts)
    weekly = build_weekly_features(weekly_counts, scope_n_weeks=len(weeks))

    features = (
        daily.join(gaps, on="id_tarjeta", how="left")
        .join(weekly, on="id_tarjeta", how="left")
        .with_columns(
            [
                pl.col("rhythm_n_gap_days").fill_null(0).cast(pl.UInt32),
                pl.col("rhythm_n_gap_days").fill_null(0).gt(0).cast(pl.Int8).alias("rhythm_has_gap"),
                pl.lit(len(weeks)).cast(pl.UInt8).alias("rhythm_scope_n_weeks"),
            ]
        )
    )

    select_cols = [
        "id_tarjeta",
        "rhythm_n_trips",
        "rhythm_n_active_days",
        "rhythm_n_active_weeks",
        "rhythm_span_days",
        "rhythm_scope_n_weeks",
        *RHYTHM_FEATURES,
    ]
    features = features.select([c for c in select_cols if c in features.columns])

    assert_unique_key(features, "id_tarjeta", "rhythm_features")
    features.write_parquet(out_path, compression="zstd")
    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={len(features.columns):,}")
    return out_path


def write_audits(features: pl.DataFrame, scope: str) -> None:
    n_rows = features.height
    feature_cols = [c for c in RHYTHM_FEATURES if c in features.columns]
    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(n_rows)},
        {"metric": "n_cols", "value": str(len(features.columns))},
        {"metric": "n_features", "value": str(len(feature_cols))},
        {
            "metric": "n_duplicate_id_tarjeta",
            "value": str(n_rows - features.select(pl.col("id_tarjeta").n_unique()).item()),
        },
        {"metric": "total_rhythm_trips", "value": str(features.select(pl.col("rhythm_n_trips").sum()).item())},
        {
            "metric": "share_cards_with_gap",
            "value": f"{features.select(pl.col('rhythm_has_gap').mean()).item():.8f}",
        },
    ]
    pl.DataFrame(summary_rows).write_csv(audit_path(scope, "summary"))

    missing = (
        features.select([pl.col(c).is_null().sum().alias(c) for c in feature_cols])
        .transpose(include_header=True, header_name="feature", column_names=["n_missing"])
        .with_columns((pl.col("n_missing") / n_rows).alias("missing_rate"))
        .sort("missing_rate", descending=True)
    )
    missing.write_csv(audit_path(scope, "missing"))

    clean_panel = panel_path(scope, "clean")
    if clean_panel.exists():
        panel = pl.scan_parquet(clean_panel).select(
            [
                "id_tarjeta",
                pl.col("n_viajes").alias("panel_n_viajes"),
                pl.col("n_dias_activos").alias("panel_n_dias_activos"),
                pl.col("n_semanas_activas").alias("panel_n_semanas_activas"),
            ]
        )
        joined = features.lazy().join(panel, on="id_tarjeta", how="left")
        consistency = joined.select(
            [
                pl.len().alias("n_rhythm_rows"),
                pl.col("panel_n_viajes").is_null().sum().alias("n_missing_clean_panel"),
                (pl.col("rhythm_n_trips") != pl.col("panel_n_viajes")).sum().alias("n_n_viajes_mismatch"),
                (pl.col("rhythm_n_active_days") != pl.col("panel_n_dias_activos")).sum().alias(
                    "n_active_days_mismatch"
                ),
                (pl.col("rhythm_n_active_weeks") != pl.col("panel_n_semanas_activas")).sum().alias(
                    "n_active_weeks_mismatch"
                ),
            ]
        ).collect()
        consistency.write_csv(audit_path(scope, "consistency_clean_panel"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build rhythm_pack user-level behavioral features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_rhythm_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
