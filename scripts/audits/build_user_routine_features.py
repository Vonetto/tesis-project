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

ROUTINE_FEATURES = [
    "routine_combo_top1_share",
    "routine_combo_hhi",
    "routine_combo_entropy_norm",
    "routine_combo_n_unique",
    "routine_od_time_top1_share",
    "routine_od_time_hhi",
    "routine_od_time_entropy_norm",
    "routine_od_time_n_unique",
    "routine_od_top1_share",
    "routine_od_hhi",
    "routine_od_entropy_norm",
    "routine_od_n_unique",
    "routine_zone_top1_usage_share",
    "routine_zone_top2_usage_share",
    "routine_zone_exploration_share",
    "routine_zone_n_unique",
    "routine_lab_peak_share",
    "routine_main_od_share",
    "routine_main_od_roundtrip_balance",
    "routine_commute_like_score",
]


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_routine_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_behavior_routine_features_{stem}_{scope}.csv"


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


def safe_ratio(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den == 0).then(None).otherwise(num / den)


def entropy_norm_expr(entropy_col: str, n_col: str) -> pl.Expr:
    return (
        pl.when(pl.col(n_col) <= 1)
        .then(0.0)
        .otherwise(pl.col(entropy_col) / pl.col(n_col).cast(pl.Float64).log())
    )


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
    hour = pl.col("routine_trip_ts").dt.hour()
    is_laboral = pl.col("routine_trip_ts").dt.weekday() <= 5
    mode_pattern = route_pattern(MODE_COLS, "-")

    return (
        lf.select(
            [
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("id_viaje").cast(pl.Utf8),
                ts.alias("routine_trip_ts"),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False),
                *[pl.col(c).cast(pl.Utf8, strict=False) for c in MODE_COLS],
            ]
        )
        .drop_nulls(["id_tarjeta", "routine_trip_ts"])
        .with_columns(
            [
                pl.lit(week).alias("partition"),
                mode_pattern.alias("routine_mode_pattern"),
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
                .alias("routine_od_pair"),
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
                .alias("routine_unordered_od_pair"),
                pl.when(pl.col("zona_inicio_viaje") <= pl.col("zona_fin_viaje"))
                .then(pl.lit("forward"))
                .when(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
                .then(pl.lit("reverse"))
                .otherwise(None)
                .alias("routine_od_direction"),
                pl.when(~is_laboral)
                .then(pl.lit("no_lab"))
                .when(hour.is_between(6, 8, closed="both"))
                .then(pl.lit("lab_am_peak"))
                .when(hour.is_between(17, 20, closed="both"))
                .then(pl.lit("lab_pm_peak"))
                .when(hour.is_between(9, 16, closed="both"))
                .then(pl.lit("lab_midday"))
                .otherwise(pl.lit("lab_other"))
                .alias("routine_time_band"),
            ]
        )
        .with_columns(
            [
                mode_coarse_expr("routine_mode_coarse")
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("routine_od_pair").is_not_null())
                .then(pl.concat_str(["routine_od_pair", "routine_time_band"], separator="__T__"))
                .otherwise(None)
                .alias("routine_od_time"),
                pl.when(pl.col("routine_od_pair").is_not_null())
                .then(
                    pl.concat_str(
                        ["routine_od_pair", "routine_time_band", "routine_mode_coarse"],
                        separator="__M__",
                    )
                )
                .otherwise(None)
                .alias("routine_combo"),
            ]
        )
        .select(
            [
                "partition",
                "id_tarjeta",
                "id_viaje",
                "routine_trip_ts",
                "zona_inicio_viaje",
                "zona_fin_viaje",
                "routine_time_band",
                "routine_mode_coarse",
                "routine_od_pair",
                "routine_unordered_od_pair",
                "routine_od_direction",
                "routine_od_time",
                "routine_combo",
            ]
        )
    )


def trips_lf_for_scope(weeks: Iterable[str]) -> pl.LazyFrame:
    return pl.concat([load_week_lf(w) for w in weeks], how="diagonal_relaxed")


def distribution_features_from_counts(counts: pl.DataFrame, *, prefix: str) -> pl.DataFrame:
    n_col = f"{prefix}_n_trips_valid"
    k_col = f"{prefix}_n_unique"
    top1_col = f"{prefix}_top1_share"
    hhi_col = f"{prefix}_hhi"
    entropy_col = f"{prefix}_entropy"
    entropy_norm_col = f"{prefix}_entropy_norm"

    if counts.is_empty():
        return pl.DataFrame(schema={"id_tarjeta": pl.Utf8})

    totals = counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_trips").sum().alias(n_col),
            pl.len().alias(k_col),
            pl.col("n_trips").max().alias(f"{prefix}_top1_n_trips"),
        ]
    )

    dist = (
        counts.join(totals.select(["id_tarjeta", n_col, k_col]), on="id_tarjeta", how="left")
        .with_columns((pl.col("n_trips") / pl.col(n_col)).alias("p"))
        .with_columns(
            [
                (pl.col("p") * pl.col("p")).alias("hhi_part"),
                (-(pl.col("p") * pl.col("p").log())).alias("entropy_part"),
            ]
        )
        .group_by("id_tarjeta")
        .agg(
            [
                pl.col("hhi_part").sum().alias(hhi_col),
                pl.col("entropy_part").sum().alias(entropy_col),
            ]
        )
        .join(totals, on="id_tarjeta", how="left")
        .with_columns(
            [
                safe_ratio(pl.col(f"{prefix}_top1_n_trips"), pl.col(n_col)).alias(top1_col),
                entropy_norm_expr(entropy_col, k_col).alias(entropy_norm_col),
            ]
        )
        .drop([entropy_col, f"{prefix}_top1_n_trips"])
    )
    return dist


def count_dimension(base: pl.DataFrame, col: str) -> pl.DataFrame:
    return (
        base.lazy()
        .filter(pl.col(col).is_not_null())
        .group_by(["id_tarjeta", col])
        .agg(pl.len().alias("n_trips"))
        .collect()
    )


def build_zone_features(base: pl.DataFrame) -> pl.DataFrame:
    origin = base.select(
        [
            "id_tarjeta",
            pl.col("zona_inicio_viaje").cast(pl.Utf8).alias("routine_zone"),
        ]
    )
    dest = base.select(
        [
            "id_tarjeta",
            pl.col("zona_fin_viaje").cast(pl.Utf8).alias("routine_zone"),
        ]
    )
    zone_events = pl.concat([origin, dest], how="diagonal_relaxed").drop_nulls(["id_tarjeta", "routine_zone"])
    if zone_events.is_empty():
        return pl.DataFrame(schema={"id_tarjeta": pl.Utf8})

    zone_counts = zone_events.group_by(["id_tarjeta", "routine_zone"]).agg(pl.len().alias("n_zone_events"))
    totals = zone_counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_zone_events").sum().alias("routine_zone_events"),
            pl.len().alias("routine_zone_n_unique"),
        ]
    )
    ranked = (
        zone_counts.sort(["id_tarjeta", "n_zone_events", "routine_zone"], descending=[False, True, False])
        .with_columns((pl.int_range(pl.len()).over("id_tarjeta") + 1).alias("zone_rank"))
        .filter(pl.col("zone_rank") <= 2)
        .join(totals, on="id_tarjeta", how="left")
        .group_by("id_tarjeta")
        .agg(
            [
                pl.when(pl.col("zone_rank") == 1)
                .then(pl.col("n_zone_events") / pl.col("routine_zone_events"))
                .otherwise(None)
                .max()
                .alias("routine_zone_top1_usage_share"),
                (pl.col("n_zone_events").sum() / pl.col("routine_zone_events").max()).alias(
                    "routine_zone_top2_usage_share"
                ),
                pl.col("routine_zone_n_unique").max().alias("routine_zone_n_unique"),
            ]
        )
        .with_columns((1.0 - pl.col("routine_zone_top2_usage_share")).alias("routine_zone_exploration_share"))
    )
    return ranked


def build_roundtrip_features(base: pl.DataFrame) -> pl.DataFrame:
    unordered_counts = (
        base.lazy()
        .filter(pl.col("routine_unordered_od_pair").is_not_null())
        .group_by(["id_tarjeta", "routine_unordered_od_pair"])
        .agg(pl.len().alias("n_unordered_od_trips"))
        .collect()
    )
    if unordered_counts.is_empty():
        return pl.DataFrame(schema={"id_tarjeta": pl.Utf8})

    top_unordered = (
        unordered_counts.sort(
            ["id_tarjeta", "n_unordered_od_trips", "routine_unordered_od_pair"],
            descending=[False, True, False],
        )
        .unique(subset=["id_tarjeta"], keep="first")
        .rename({"routine_unordered_od_pair": "routine_main_unordered_od_pair"})
    )

    dir_counts = (
        base.join(top_unordered.select(["id_tarjeta", "routine_main_unordered_od_pair"]), on="id_tarjeta", how="inner")
        .filter(pl.col("routine_unordered_od_pair") == pl.col("routine_main_unordered_od_pair"))
        .group_by(["id_tarjeta", "routine_od_direction"])
        .agg(pl.len().alias("n_direction_trips"))
    )

    return (
        dir_counts.group_by("id_tarjeta")
        .agg(
            [
                pl.col("n_direction_trips").sum().alias("routine_main_unordered_od_trips"),
                pl.col("n_direction_trips").max().alias("routine_main_unordered_od_top_direction_trips"),
                pl.len().alias("routine_main_unordered_od_n_directions"),
            ]
        )
        .join(top_unordered.select(["id_tarjeta", "n_unordered_od_trips"]), on="id_tarjeta", how="left")
        .with_columns(
            [
                pl.col("n_unordered_od_trips").alias("routine_main_unordered_od_n_trips"),
                (
                    2.0
                    * (
                        1.0
                        - safe_ratio(
                            pl.col("routine_main_unordered_od_top_direction_trips"),
                            pl.col("routine_main_unordered_od_trips"),
                        )
                    )
                ).alias("routine_main_od_roundtrip_balance"),
            ]
        )
        .drop(["n_unordered_od_trips"])
    )


def build_routine_features(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo routine_pack scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    base = collect_streaming(trips_lf)

    base_features = base.group_by("id_tarjeta").agg(
        [
            pl.len().alias("routine_n_trips"),
            pl.col("routine_combo").is_null().mean().alias("routine_combo_missing_rate"),
            pl.col("routine_od_pair").is_null().mean().alias("routine_od_missing_rate"),
            pl.col("routine_unordered_od_pair").is_null().mean().alias("routine_unordered_od_missing_rate"),
            pl.col("routine_time_band").is_in(["lab_am_peak", "lab_pm_peak"]).mean().alias(
                "routine_lab_peak_share"
            ),
        ]
    )

    combo_dist = distribution_features_from_counts(count_dimension(base, "routine_combo"), prefix="routine_combo")
    od_time_dist = distribution_features_from_counts(
        count_dimension(base, "routine_od_time"),
        prefix="routine_od_time",
    )
    od_dist = distribution_features_from_counts(count_dimension(base, "routine_od_pair"), prefix="routine_od")
    zone_features = build_zone_features(base)
    roundtrip_features = build_roundtrip_features(base)

    features = (
        base_features.join(combo_dist, on="id_tarjeta", how="left")
        .join(od_time_dist, on="id_tarjeta", how="left")
        .join(od_dist, on="id_tarjeta", how="left")
        .join(zone_features, on="id_tarjeta", how="left")
        .join(roundtrip_features, on="id_tarjeta", how="left")
        .with_columns(
            [
                safe_ratio(
                    pl.col("routine_main_unordered_od_n_trips"),
                    pl.col("routine_n_trips"),
                ).alias("routine_main_od_share"),
            ]
        )
        .with_columns(
            [
                (
                    pl.col("routine_combo_top1_share")
                    * pl.col("routine_zone_top2_usage_share")
                    * pl.col("routine_lab_peak_share")
                    * pl.col("routine_main_od_roundtrip_balance")
                ).alias("routine_commute_like_score")
            ]
        )
    )

    select_cols = [
        "id_tarjeta",
        "routine_n_trips",
        "routine_combo_missing_rate",
        "routine_od_missing_rate",
        "routine_unordered_od_missing_rate",
        "routine_main_unordered_od_n_trips",
        "routine_main_unordered_od_n_directions",
        *ROUTINE_FEATURES,
    ]
    features = features.select([c for c in select_cols if c in features.columns])

    assert_unique_key(features, "id_tarjeta", "routine_features")
    features.write_parquet(out_path, compression="zstd")
    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={len(features.columns):,}")
    return out_path


def write_audits(features: pl.DataFrame, scope: str) -> None:
    n_rows = features.height
    feature_cols = [c for c in ROUTINE_FEATURES if c in features.columns]
    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(n_rows)},
        {"metric": "n_cols", "value": str(len(features.columns))},
        {"metric": "n_features", "value": str(len(feature_cols))},
        {
            "metric": "n_duplicate_id_tarjeta",
            "value": str(n_rows - features.select(pl.col("id_tarjeta").n_unique()).item()),
        },
        {"metric": "total_routine_trips", "value": str(features.select(pl.col("routine_n_trips").sum()).item())},
        {
            "metric": "mean_routine_combo_missing_rate",
            "value": f"{features.select(pl.col('routine_combo_missing_rate').mean()).item():.8f}",
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
            ]
        )
        consistency = (
            features.lazy()
            .join(panel, on="id_tarjeta", how="left")
            .select(
                [
                    pl.len().alias("n_routine_rows"),
                    pl.col("panel_n_viajes").is_null().sum().alias("n_missing_clean_panel"),
                    (pl.col("routine_n_trips") != pl.col("panel_n_viajes")).sum().alias(
                        "n_n_viajes_mismatch"
                    ),
                ]
            )
            .collect()
        )
        consistency.write_csv(audit_path(scope, "consistency_clean_panel"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build routine_pack user-level behavioral features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_routine_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
