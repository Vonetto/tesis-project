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

STAGES = range(1, 7)
MODE_COLS = [f"tipo_transporte_{i}" for i in STAGES]
# docs/diccionario_viajes.txt: 1=Bus, 2=Metro, 3=Zona Paga, 4=MetroTren.
# Zona Paga is bus-like; MetroTren is rail-like for coarse modal features.
BUS_CODES = ["1", "3"]
METRO_CODES = ["2", "4"]

DAILY_TOUR_FEATURES = [
    "tour_two_trip_day_share",
    "tour_three_plus_trip_day_share",
    "tour_complex_day_share",
    "tour_closed_loop_day_share",
    "tour_reciprocal_od_day_share",
    "tour_same_unordered_od_day_share",
    "tour_mode_consistent_day_share",
    "tour_mixed_mode_day_share",
    "tour_first_trip_lab_am_peak_share",
    "tour_last_trip_lab_pm_peak_share",
    "tour_peak_anchor_day_share",
    "tour_workday_commute_like_day_share",
    "tour_distinct_zones_per_day_mean",
    "tour_distinct_zones_per_day_median",
    "tour_distinct_od_per_day_mean",
    "tour_distinct_unordered_od_per_day_mean",
    "tour_distinct_modes_per_day_mean",
    "tour_day_span_hours_mean",
    "tour_day_span_hours_median",
    "tour_first_trip_hour_mean",
    "tour_last_trip_hour_mean",
]


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_daily_tour_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_behavior_daily_tour_features_{stem}_{scope}.csv"


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


def route_pattern(cols: list[str], separator: str) -> pl.Expr:
    return pl.concat_str(
        [pl.col(c).cast(pl.Utf8, strict=False).fill_null("NA") for c in cols],
        separator=separator,
    )


def any_mode_code_expr(codes: list[str]) -> pl.Expr:
    return pl.any_horizontal(
        [pl.col(c).cast(pl.Utf8, strict=False).is_in(codes).fill_null(False) for c in MODE_COLS]
    )


def mode_coarse_expr(alias: str) -> pl.Expr:
    has_bus = any_mode_code_expr(BUS_CODES)
    has_metro = any_mode_code_expr(METRO_CODES)
    return (
        pl.when(has_bus & has_metro)
        .then(pl.lit("metro_bus"))
        .when(has_metro)
        .then(pl.lit("metro_only"))
        .when(has_bus)
        .then(pl.lit("bus_only"))
        .otherwise(pl.lit("other_mode"))
        .alias(alias)
    )


def load_week_lf(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema = set(lf.collect_schema().names())
    required = {
        "id_tarjeta",
        "id_viaje",
        "tiempo_inicio_viaje",
        "zona_inicio_viaje",
        "zona_fin_viaje",
        *MODE_COLS,
    }
    missing = sorted(required - schema)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    ts = pl.col("tiempo_inicio_viaje").cast(pl.Datetime, strict=False)
    hour = pl.col("tour_trip_ts").dt.hour()
    is_laboral = pl.col("tour_trip_ts").dt.weekday() <= 5
    mode_pattern = route_pattern(MODE_COLS, "-")

    return (
        lf.select(
            [
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("id_viaje").cast(pl.Utf8),
                ts.alias("tour_trip_ts"),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False),
                *[pl.col(c).cast(pl.Utf8, strict=False) for c in MODE_COLS],
            ]
        )
        .drop_nulls(["id_tarjeta", "tour_trip_ts"])
        .with_columns(
            [
                pl.lit(week).alias("partition"),
                pl.col("tour_trip_ts").dt.date().alias("tour_date"),
                mode_pattern.alias("tour_mode_pattern"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
                .then(
                    pl.concat_str(
                        [
                            pl.col("zona_inicio_viaje").cast(pl.Utf8),
                            pl.col("zona_fin_viaje").cast(pl.Utf8),
                        ],
                        separator="->",
                    )
                )
                .otherwise(None)
                .alias("tour_od_pair"),
                pl.when(pl.col("zona_inicio_viaje") <= pl.col("zona_fin_viaje"))
                .then(
                    pl.concat_str(
                        [
                            pl.col("zona_inicio_viaje").cast(pl.Utf8),
                            pl.col("zona_fin_viaje").cast(pl.Utf8),
                        ],
                        separator="<->",
                    )
                )
                .when(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
                .then(
                    pl.concat_str(
                        [
                            pl.col("zona_fin_viaje").cast(pl.Utf8),
                            pl.col("zona_inicio_viaje").cast(pl.Utf8),
                        ],
                        separator="<->",
                    )
                )
                .otherwise(None)
                .alias("tour_unordered_od_pair"),
                pl.when(~is_laboral)
                .then(pl.lit("no_lab"))
                .when(hour.is_between(6, 8, closed="both"))
                .then(pl.lit("lab_am_peak"))
                .when(hour.is_between(17, 20, closed="both"))
                .then(pl.lit("lab_pm_peak"))
                .when(hour.is_between(9, 16, closed="both"))
                .then(pl.lit("lab_midday"))
                .otherwise(pl.lit("lab_other"))
                .alias("tour_time_band"),
            ]
        )
        .with_columns(
            [
                mode_coarse_expr("tour_mode_coarse")
            ]
        )
        .select(
            [
                "partition",
                "id_tarjeta",
                "id_viaje",
                "tour_trip_ts",
                "tour_date",
                "zona_inicio_viaje",
                "zona_fin_viaje",
                "tour_time_band",
                "tour_mode_coarse",
                "tour_od_pair",
                "tour_unordered_od_pair",
            ]
        )
    )


def trips_lf_for_scope(weeks: Iterable[str]) -> pl.LazyFrame:
    return pl.concat([load_week_lf(w) for w in weeks], how="diagonal_relaxed")


def build_daily_zone_counts(base: pl.DataFrame) -> pl.DataFrame:
    origin = base.select(
        [
            "id_tarjeta",
            "tour_date",
            pl.col("zona_inicio_viaje").alias("tour_zone"),
        ]
    )
    dest = base.select(
        [
            "id_tarjeta",
            "tour_date",
            pl.col("zona_fin_viaje").alias("tour_zone"),
        ]
    )
    zone_events = pl.concat([origin, dest], how="diagonal_relaxed").drop_nulls(
        ["id_tarjeta", "tour_date", "tour_zone"]
    )
    if zone_events.is_empty():
        return pl.DataFrame(schema={"id_tarjeta": pl.Utf8, "tour_date": pl.Date, "tour_day_n_zones": pl.UInt32})
    return zone_events.group_by(["id_tarjeta", "tour_date"]).agg(
        pl.col("tour_zone").n_unique().alias("tour_day_n_zones")
    )


def build_daily_features(base: pl.DataFrame) -> pl.DataFrame:
    if base.is_empty():
        return pl.DataFrame(schema={"id_tarjeta": pl.Utf8, "tour_date": pl.Date})

    ordered = base.sort(["id_tarjeta", "tour_date", "tour_trip_ts", "id_viaje"])
    daily_core = ordered.group_by(["id_tarjeta", "tour_date"], maintain_order=True).agg(
        [
            pl.len().alias("tour_day_n_trips"),
            pl.col("tour_trip_ts").first().alias("tour_day_first_ts"),
            pl.col("tour_trip_ts").last().alias("tour_day_last_ts"),
            pl.col("zona_inicio_viaje").first().alias("tour_day_first_origin"),
            pl.col("zona_fin_viaje").first().alias("tour_day_first_dest"),
            pl.col("zona_inicio_viaje").last().alias("tour_day_last_origin"),
            pl.col("zona_fin_viaje").last().alias("tour_day_last_dest"),
            pl.col("tour_time_band").first().alias("tour_day_first_time_band"),
            pl.col("tour_time_band").last().alias("tour_day_last_time_band"),
            pl.col("tour_mode_coarse").drop_nulls().n_unique().alias("tour_day_n_modes"),
            pl.col("tour_od_pair").drop_nulls().n_unique().alias("tour_day_n_od"),
            pl.col("tour_unordered_od_pair").drop_nulls().n_unique().alias("tour_day_n_unordered_od"),
        ]
    )

    daily_zones = build_daily_zone_counts(base)
    return (
        daily_core.join(daily_zones, on=["id_tarjeta", "tour_date"], how="left")
        .with_columns(pl.col("tour_day_n_zones").fill_null(0))
        .with_columns(
            [
                ((pl.col("tour_day_last_ts") - pl.col("tour_day_first_ts")).dt.total_seconds() / 3600.0).alias(
                    "tour_day_span_hours"
                ),
                pl.col("tour_day_first_ts").dt.hour().alias("tour_day_first_hour"),
                pl.col("tour_day_last_ts").dt.hour().alias("tour_day_last_hour"),
                (pl.col("tour_day_n_trips") == 2).alias("tour_day_is_two_trip"),
                (pl.col("tour_day_n_trips") >= 3).alias("tour_day_is_three_plus"),
                ((pl.col("tour_day_n_trips") >= 3) & (pl.col("tour_day_n_zones") >= 3)).alias(
                    "tour_day_is_complex"
                ),
                (
                    (pl.col("tour_day_n_trips") >= 2)
                    & pl.col("tour_day_first_origin").is_not_null()
                    & pl.col("tour_day_last_dest").is_not_null()
                    & (pl.col("tour_day_first_origin") == pl.col("tour_day_last_dest"))
                ).alias("tour_day_is_closed_loop"),
                (
                    (pl.col("tour_day_n_trips") >= 2)
                    & pl.col("tour_day_first_origin").is_not_null()
                    & pl.col("tour_day_first_dest").is_not_null()
                    & pl.col("tour_day_last_origin").is_not_null()
                    & pl.col("tour_day_last_dest").is_not_null()
                    & (pl.col("tour_day_first_origin") == pl.col("tour_day_last_dest"))
                    & (pl.col("tour_day_first_dest") == pl.col("tour_day_last_origin"))
                ).alias("tour_day_is_reciprocal_od"),
                ((pl.col("tour_day_n_trips") >= 2) & (pl.col("tour_day_n_unordered_od") == 1)).alias(
                    "tour_day_same_unordered_od"
                ),
                (pl.col("tour_day_n_modes") <= 1).alias("tour_day_mode_consistent"),
                (pl.col("tour_day_n_modes") > 1).alias("tour_day_mixed_mode"),
                (pl.col("tour_day_first_time_band") == "lab_am_peak").alias("tour_day_first_lab_am_peak"),
                (pl.col("tour_day_last_time_band") == "lab_pm_peak").alias("tour_day_last_lab_pm_peak"),
            ]
        )
        .with_columns(
            [
                (pl.col("tour_day_first_lab_am_peak") | pl.col("tour_day_last_lab_pm_peak")).alias(
                    "tour_day_peak_anchor"
                ),
                (
                    pl.col("tour_day_is_closed_loop")
                    & pl.col("tour_day_first_lab_am_peak")
                    & pl.col("tour_day_last_lab_pm_peak")
                ).alias("tour_day_workday_commute_like"),
            ]
        )
    )


def build_user_features(daily: pl.DataFrame) -> pl.DataFrame:
    return daily.group_by("id_tarjeta").agg(
        [
            pl.col("tour_day_n_trips").sum().alias("tour_n_trips"),
            pl.len().alias("tour_n_active_days"),
            pl.col("tour_day_is_two_trip").mean().alias("tour_two_trip_day_share"),
            pl.col("tour_day_is_three_plus").mean().alias("tour_three_plus_trip_day_share"),
            pl.col("tour_day_is_complex").mean().alias("tour_complex_day_share"),
            pl.col("tour_day_is_closed_loop").mean().alias("tour_closed_loop_day_share"),
            pl.col("tour_day_is_reciprocal_od").mean().alias("tour_reciprocal_od_day_share"),
            pl.col("tour_day_same_unordered_od").mean().alias("tour_same_unordered_od_day_share"),
            pl.col("tour_day_mode_consistent").mean().alias("tour_mode_consistent_day_share"),
            pl.col("tour_day_mixed_mode").mean().alias("tour_mixed_mode_day_share"),
            pl.col("tour_day_first_lab_am_peak").mean().alias("tour_first_trip_lab_am_peak_share"),
            pl.col("tour_day_last_lab_pm_peak").mean().alias("tour_last_trip_lab_pm_peak_share"),
            pl.col("tour_day_peak_anchor").mean().alias("tour_peak_anchor_day_share"),
            pl.col("tour_day_workday_commute_like").mean().alias("tour_workday_commute_like_day_share"),
            pl.col("tour_day_n_zones").mean().alias("tour_distinct_zones_per_day_mean"),
            pl.col("tour_day_n_zones").median().alias("tour_distinct_zones_per_day_median"),
            pl.col("tour_day_n_od").mean().alias("tour_distinct_od_per_day_mean"),
            pl.col("tour_day_n_unordered_od").mean().alias("tour_distinct_unordered_od_per_day_mean"),
            pl.col("tour_day_n_modes").mean().alias("tour_distinct_modes_per_day_mean"),
            pl.col("tour_day_span_hours").mean().alias("tour_day_span_hours_mean"),
            pl.col("tour_day_span_hours").median().alias("tour_day_span_hours_median"),
            pl.col("tour_day_first_hour").mean().alias("tour_first_trip_hour_mean"),
            pl.col("tour_day_last_hour").mean().alias("tour_last_trip_hour_mean"),
        ]
    )


def build_daily_tour_features(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo daily_tour_pack scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    base = collect_streaming(trips_lf)
    daily = build_daily_features(base)
    features = build_user_features(daily)
    features = features.select(["id_tarjeta", "tour_n_trips", "tour_n_active_days", *DAILY_TOUR_FEATURES])

    assert_unique_key(features, "id_tarjeta", "daily_tour_features")
    features.write_parquet(out_path, compression="zstd")
    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={len(features.columns):,}")
    return out_path


def write_audits(features: pl.DataFrame, scope: str) -> None:
    n_rows = features.height
    feature_cols = [c for c in DAILY_TOUR_FEATURES if c in features.columns]
    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(n_rows)},
        {"metric": "n_cols", "value": str(len(features.columns))},
        {"metric": "n_features", "value": str(len(feature_cols))},
        {
            "metric": "n_duplicate_id_tarjeta",
            "value": str(n_rows - features.select(pl.col("id_tarjeta").n_unique()).item()),
        },
        {"metric": "total_tour_trips", "value": str(features.select(pl.col("tour_n_trips").sum()).item())},
        {
            "metric": "mean_tour_active_days",
            "value": f"{features.select(pl.col('tour_n_active_days').mean()).item():.8f}",
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
                pl.col("n_dias_activos").alias("panel_n_active_days"),
            ]
        )
        consistency = (
            features.lazy()
            .join(panel, on="id_tarjeta", how="left")
            .select(
                [
                    pl.len().alias("n_tour_rows"),
                    pl.col("panel_n_viajes").is_null().sum().alias("n_missing_clean_panel"),
                    (pl.col("tour_n_trips") != pl.col("panel_n_viajes")).sum().alias("n_n_viajes_mismatch"),
                    (pl.col("tour_n_active_days") != pl.col("panel_n_active_days")).sum().alias(
                        "n_active_days_mismatch"
                    ),
                ]
            )
            .collect()
        )
        consistency.write_csv(audit_path(scope, "consistency_clean_panel"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build daily_tour_pack user-level behavioral features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_daily_tour_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
