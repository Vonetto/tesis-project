"""Build user-level interannual adoption/timing change features.

The pack compares observed behavior in the same calendar-week window across
2024 and 2025. Count/growth features treat an unobserved year as zero observed
activity. Delta features for averages/shares are only defined for users observed
in both years.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.od_buffers_nested_logit import add_time_dummies_v2, derive_metrics  # noqa: E402


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

TRANSPORT_COLS = [f"tipo_transporte_{i}" for i in range(1, 7)]
# docs/diccionario_viajes.txt: 1=Bus, 2=Metro, 3=Zona Paga, 4=MetroTren.
BUS_CODES = ["1", "3"]
METRO_CODES = ["2", "4"]

ADOPTION_STATUS_FEATURES = [
    "adopt_has_2024",
    "adopt_has_2025",
    "adopt_both_years",
    "adopt_only_2025",
    "adopt_only_2024",
]

ADOPTION_TIMING_FEATURES = [
    *ADOPTION_STATUS_FEATURES,
    "adopt_trip_growth_log_2025_2024",
    "adopt_active_day_growth_log_2025_2024",
    "adopt_active_week_growth_log_2025_2024",
    "adopt_trips_per_active_day_delta",
    "adopt_hora_mean_delta",
    "adopt_hora_std_delta",
    "adopt_lab_peak_share_delta",
    "adopt_no_lab_share_delta",
    "adopt_solo_bus_share_delta",
    "adopt_solo_metro_share_delta",
    "adopt_metro_bus_share_delta",
    "adopt_transfer_share_delta",
    "adopt_origin_n_unique_delta",
    "adopt_dest_n_unique_delta",
    "adopt_origin_top1_changed",
]


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_adoption_timing_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_behavior_adoption_timing_features_{stem}_{scope}.csv"


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


def any_code_expr(codes: list[str]) -> pl.Expr:
    return pl.any_horizontal(
        [pl.col(c).cast(pl.Utf8, strict=False).is_in(codes).fill_null(False) for c in TRANSPORT_COLS]
    )


def load_week_lf(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema = set(lf.collect_schema().names())
    required = {
        "id_tarjeta",
        "tiempo_inicio_viaje",
        "fecha",
        "tipodia",
        "semana_iso",
        "iso_year",
        "te0_calculado",
        "zona_inicio_viaje",
        "zona_fin_viaje",
        "n_etapas_recon",
        *TRANSPORT_COLS,
    }
    missing = sorted(required - schema)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    lf, _ = derive_metrics(lf, schema)
    lf = add_time_dummies_v2(lf)

    has_bus = any_code_expr(BUS_CODES)
    has_metro = any_code_expr(METRO_CODES)

    return (
        lf.with_columns(
            [
                pl.lit(week).alias("partition"),
                pl.col("id_tarjeta").cast(pl.Utf8).alias("id_tarjeta"),
                pl.col("fecha").cast(pl.Date).alias("trip_date"),
                pl.col("semana_iso").cast(pl.Utf8).alias("semana_iso"),
                pl.col("iso_year").cast(pl.Int16, strict=False).alias("trip_year"),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_viaje"),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_viaje"),
                has_bus.alias("has_bus"),
                has_metro.alias("has_metro"),
            ]
        )
        .with_columns(
            [
                (pl.col("has_bus") & ~pl.col("has_metro")).cast(pl.Int8).alias("trip_solo_bus"),
                (pl.col("has_metro") & ~pl.col("has_bus")).cast(pl.Int8).alias("trip_solo_metro"),
                (pl.col("has_bus") & pl.col("has_metro")).cast(pl.Int8).alias("trip_metro_bus"),
            ]
        )
        .select(
            [
                "id_tarjeta",
                "trip_date",
                "trip_year",
                "semana_iso",
                "zona_inicio_viaje",
                "zona_fin_viaje",
                "hora",
                "DUMMY_LAB_PM",
                "DUMMY_LAB_PT",
                "DUMMY_NO_LAB",
                "n_trasbordos",
                "trip_solo_bus",
                "trip_solo_metro",
                "trip_metro_bus",
            ]
        )
        .drop_nulls(["id_tarjeta", "trip_year", "trip_date"])
    )


def trips_lf_for_scope(weeks: Iterable[str]) -> pl.LazyFrame:
    return pl.concat([load_week_lf(w) for w in weeks], how="diagonal_relaxed")


def safe_ratio(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den == 0).then(None).otherwise(num / den)


def year_prefix(df: pl.DataFrame, year: int) -> pl.DataFrame:
    rename_map = {
        c: f"{c}_{year}"
        for c in df.columns
        if c not in {"id_tarjeta", "trip_year"}
    }
    return df.filter(pl.col("trip_year") == year).drop("trip_year").rename(rename_map)


def both_years_expr() -> pl.Expr:
    return (pl.col("adopt_has_2024") == 1) & (pl.col("adopt_has_2025") == 1)


def both_year_delta(col: str) -> pl.Expr:
    return (
        pl.when(both_years_expr())
        .then(pl.col(f"{col}_2025").cast(pl.Float64) - pl.col(f"{col}_2024").cast(pl.Float64))
        .otherwise(pl.lit(None, dtype=pl.Float64))
    )


def build_adoption_features(trips_lf: pl.LazyFrame) -> pl.DataFrame:
    yearly = collect_streaming(
        trips_lf.group_by(["id_tarjeta", "trip_year"]).agg(
            [
                pl.len().alias("n_trips"),
                pl.col("trip_date").n_unique().alias("n_active_days"),
                pl.col("semana_iso").n_unique().alias("n_active_weeks"),
                pl.col("hora").mean().alias("hora_mean"),
                pl.col("hora").std().fill_null(0.0).alias("hora_std"),
                (pl.col("DUMMY_LAB_PM").fill_null(0) + pl.col("DUMMY_LAB_PT").fill_null(0))
                .mean()
                .alias("lab_peak_share"),
                pl.col("DUMMY_NO_LAB").mean().alias("no_lab_share"),
                pl.col("trip_solo_bus").mean().alias("solo_bus_share"),
                pl.col("trip_solo_metro").mean().alias("solo_metro_share"),
                pl.col("trip_metro_bus").mean().alias("metro_bus_share"),
                (pl.col("n_trasbordos") > 0).mean().alias("transfer_share"),
                pl.col("zona_inicio_viaje").drop_nulls().n_unique().alias("origin_n_unique"),
                pl.col("zona_fin_viaje").drop_nulls().n_unique().alias("dest_n_unique"),
                pl.col("zona_inicio_viaje").drop_nulls().mode().first().alias("origin_top1"),
            ]
        )
    )

    all_ids = yearly.select("id_tarjeta").unique()
    y2024 = year_prefix(yearly, 2024)
    y2025 = year_prefix(yearly, 2025)
    wide = (
        all_ids.join(y2024, on="id_tarjeta", how="left")
        .join(y2025, on="id_tarjeta", how="left")
        .with_columns(
            [
                pl.col("n_trips_2024").fill_null(0).cast(pl.Int64),
                pl.col("n_trips_2025").fill_null(0).cast(pl.Int64),
                pl.col("n_active_days_2024").fill_null(0).cast(pl.Int64),
                pl.col("n_active_days_2025").fill_null(0).cast(pl.Int64),
                pl.col("n_active_weeks_2024").fill_null(0).cast(pl.Int64),
                pl.col("n_active_weeks_2025").fill_null(0).cast(pl.Int64),
            ]
        )
        .with_columns(
            [
                (pl.col("n_trips_2024") > 0).cast(pl.Int8).alias("adopt_has_2024"),
                (pl.col("n_trips_2025") > 0).cast(pl.Int8).alias("adopt_has_2025"),
            ]
        )
        .with_columns(
            [
                ((pl.col("adopt_has_2024") == 1) & (pl.col("adopt_has_2025") == 1))
                .cast(pl.Int8)
                .alias("adopt_both_years"),
                ((pl.col("adopt_has_2024") == 0) & (pl.col("adopt_has_2025") == 1))
                .cast(pl.Int8)
                .alias("adopt_only_2025"),
                ((pl.col("adopt_has_2024") == 1) & (pl.col("adopt_has_2025") == 0))
                .cast(pl.Int8)
                .alias("adopt_only_2024"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_trips_2025").log1p() - pl.col("n_trips_2024").log1p()).alias(
                    "adopt_trip_growth_log_2025_2024"
                ),
                (pl.col("n_active_days_2025").log1p() - pl.col("n_active_days_2024").log1p()).alias(
                    "adopt_active_day_growth_log_2025_2024"
                ),
                (pl.col("n_active_weeks_2025").log1p() - pl.col("n_active_weeks_2024").log1p()).alias(
                    "adopt_active_week_growth_log_2025_2024"
                ),
                (
                    safe_ratio(pl.col("n_trips_2025"), pl.col("n_active_days_2025"))
                    - safe_ratio(pl.col("n_trips_2024"), pl.col("n_active_days_2024"))
                ).alias("adopt_trips_per_active_day_delta"),
                both_year_delta("hora_mean").alias("adopt_hora_mean_delta"),
                both_year_delta("hora_std").alias("adopt_hora_std_delta"),
                both_year_delta("lab_peak_share").alias("adopt_lab_peak_share_delta"),
                both_year_delta("no_lab_share").alias("adopt_no_lab_share_delta"),
                both_year_delta("solo_bus_share").alias("adopt_solo_bus_share_delta"),
                both_year_delta("solo_metro_share").alias("adopt_solo_metro_share_delta"),
                both_year_delta("metro_bus_share").alias("adopt_metro_bus_share_delta"),
                both_year_delta("transfer_share").alias("adopt_transfer_share_delta"),
                both_year_delta("origin_n_unique").alias("adopt_origin_n_unique_delta"),
                both_year_delta("dest_n_unique").alias("adopt_dest_n_unique_delta"),
                pl.when(
                    both_years_expr()
                    & pl.col("origin_top1_2024").is_not_null()
                    & pl.col("origin_top1_2025").is_not_null()
                )
                .then((pl.col("origin_top1_2024") != pl.col("origin_top1_2025")).cast(pl.Int8))
                .otherwise(pl.lit(None, dtype=pl.Int8))
                .alias("adopt_origin_top1_changed"),
            ]
        )
    )
    return wide.select(["id_tarjeta", *ADOPTION_TIMING_FEATURES])


def build_adoption_timing_features(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Construyendo adoption_timing_pack scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    features = build_adoption_features(trips_lf)
    assert_unique_key(features, "id_tarjeta", "adoption_timing_features")
    features.write_parquet(out_path, compression="zstd")

    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={features.width:,}")
    return out_path


def write_audits(features: pl.DataFrame, scope: str) -> None:
    summary = pl.DataFrame(
        [
            {"metric": "scope", "value": scope},
            {"metric": "n_cards", "value": str(features.height)},
            {"metric": "n_features", "value": str(len(ADOPTION_TIMING_FEATURES))},
            {
                "metric": "share_only_2025",
                "value": f"{features['adopt_only_2025'].mean():.8f}",
            },
            {
                "metric": "share_only_2024",
                "value": f"{features['adopt_only_2024'].mean():.8f}",
            },
            {
                "metric": "share_both_years",
                "value": f"{features['adopt_both_years'].mean():.8f}",
            },
        ]
    )
    summary.write_csv(audit_path(scope, "summary"))

    missing = features.select([pl.col(c).is_null().sum().alias(c) for c in ADOPTION_TIMING_FEATURES])
    missing_long = (
        missing.transpose(include_header=True, header_name="feature", column_names=["n_missing"])
        .with_columns((pl.col("n_missing") / features.height).alias("missing_rate"))
        .sort("missing_rate", descending=True)
    )
    missing_long.write_csv(audit_path(scope, "feature_missing"))

    panel = panel_path(scope, "clean")
    if panel.exists():
        panel_df = pl.read_parquet(panel, columns=["id_tarjeta", "n_viajes"])
        check = features.join(
            panel_df.rename({"n_viajes": "panel_n_viajes"}),
            on="id_tarjeta",
            how="left",
        ).select(
            [
                pl.len().alias("n_adoption_rows"),
                pl.col("panel_n_viajes").is_null().sum().alias("n_missing_clean_panel"),
                (
                    pl.col("adopt_has_2024").cast(pl.Int64)
                    + pl.col("adopt_has_2025").cast(pl.Int64)
                )
                .is_null()
                .sum()
                .alias("n_missing_status"),
            ]
        )
        check.write_csv(audit_path(scope, "panel_join_check"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build adoption_timing_pack user-level features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_adoption_timing_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
