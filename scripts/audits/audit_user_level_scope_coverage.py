from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.od_buffers_nested_logit import (  # noqa: E402
    add_tipo_pago,
    load_caracterizacion,
    resolve_caracterizacion_path,
)


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


def out_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"{stem}_{scope}.csv"


def week_lf(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    if not path.exists():
        raise FileNotFoundError(f"No existe parquet procesado para {week}: {path}")
    df_caracterizacion = load_caracterizacion(resolve_caracterizacion_path(None, week))
    lf = (
        pl.scan_parquet(path)
        .select(
            [
                "id_tarjeta",
                "is_qr",
                "contrato",
                "tipodia",
                "tiempo_inicio_viaje",
                "zona_inicio_viaje",
                "zona_fin_viaje",
            ]
        )
        .with_columns(
            [
                pl.lit(week).alias("week"),
                pl.col("tiempo_inicio_viaje").dt.date().alias("trip_date"),
                pl.col("id_tarjeta").cast(pl.Utf8).alias("id_tarjeta"),
                pl.col("contrato").cast(pl.Utf8, strict=False).alias("contrato"),
            ]
        )
    )
    return add_tipo_pago(lf, df_caracterizacion).select(
        [
            "week",
            "trip_date",
            "tipodia",
            "id_tarjeta",
            "contrato",
            "is_qr",
            "tipo_app",
            "tipo_pago",
            "zona_inicio_viaje",
            "zona_fin_viaje",
        ]
    )


def build_weekly_coverage(trips: pl.LazyFrame) -> pl.DataFrame:
    type_counts = (
        trips.group_by(["week", "tipo_pago"])
        .agg([pl.len().alias("n_trips_tipo_pago"), pl.col("id_tarjeta").n_unique().alias("n_cards_tipo_pago")])
        .collect()
        .pivot(on="tipo_pago", index="week", values=["n_trips_tipo_pago", "n_cards_tipo_pago"])
    )
    return (
        trips.group_by("week")
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("trip_date").min().alias("min_date"),
                pl.col("trip_date").max().alias("max_date"),
                pl.col("trip_date").n_unique().alias("n_dates"),
                pl.col("tipodia").n_unique().alias("n_tipodia_values"),
                pl.col("zona_inicio_viaje").is_null().mean().alias("missing_origin_rate"),
                pl.col("zona_fin_viaje").is_null().mean().alias("missing_dest_rate"),
                pl.col("is_qr").mean().alias("trip_qr_share"),
            ]
        )
        .collect()
        .join(type_counts, on="week", how="left")
        .sort("week")
    )


def build_daily_coverage(trips: pl.LazyFrame) -> pl.DataFrame:
    return (
        trips.group_by(["week", "trip_date", "tipodia"])
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("is_qr").mean().alias("trip_qr_share"),
                (pl.col("tipo_pago") == "QR_RED").mean().alias("trip_qr_red_share"),
                (pl.col("tipo_pago") == "QR_OTHER").mean().alias("trip_qr_other_share"),
            ]
        )
        .collect()
        .sort(["week", "trip_date", "tipodia"])
    )


def build_pooled_target_audit(trips: pl.LazyFrame) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    cards = (
        trips.group_by("id_tarjeta")
        .agg(
            [
                pl.len().alias("n_viajes"),
                pl.col("tipo_pago").n_unique().alias("n_tipo_pago"),
                pl.col("tipo_pago").unique().sort().alias("tipo_pago_values"),
                pl.col("is_qr").n_unique().alias("n_is_qr"),
                pl.col("contrato").n_unique().alias("n_contrato"),
                pl.col("week").n_unique().alias("n_weeks_observed"),
                pl.col("trip_date").n_unique().alias("n_dates_observed"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("n_tipo_pago") == 1)
                .then(pl.col("tipo_pago_values").list.first())
                .otherwise(pl.lit("CONFLICT"))
                .alias("tipo_tarjeta"),
                pl.col("tipo_pago_values").list.join("|").alias("tipo_pago_set"),
            ]
        )
        .drop("tipo_pago_values")
        .collect()
    )
    target_distribution = (
        cards.group_by("tipo_tarjeta")
        .agg([pl.len().alias("n_cards"), pl.col("n_viajes").sum().alias("n_trips")])
        .with_columns(
            [
                (pl.col("n_cards") / cards.height).alias("card_share"),
                (pl.col("n_trips") / cards.select(pl.col("n_viajes").sum()).item()).alias("trip_share"),
            ]
        )
        .sort("tipo_tarjeta")
    )
    threshold_rows = []
    total_cards = cards.height
    total_trips = cards.select(pl.col("n_viajes").sum()).item()
    for threshold in [1, 3, 5, 10, 20, 50]:
        subset = cards.filter(pl.col("n_viajes") >= threshold)
        row = {
            "min_n_viajes": threshold,
            "n_cards": subset.height,
            "card_share": subset.height / total_cards,
            "n_trips": subset.select(pl.col("n_viajes").sum()).item() if subset.height else 0,
        }
        row["trip_share"] = row["n_trips"] / total_trips
        for item in subset.group_by("tipo_tarjeta").agg(pl.len().alias("n")).to_dicts():
            row[f"card_share_{item['tipo_tarjeta']}"] = item["n"] / subset.height
        threshold_rows.append(row)
    threshold_sensitivity = pl.DataFrame(threshold_rows)
    conflicts = cards.filter(pl.col("n_tipo_pago") > 1).sort("n_viajes", descending=True).head(1000)
    return target_distribution, threshold_sensitivity, conflicts


def run(scope: str) -> None:
    if scope not in SCOPE_WEEKS:
        raise ValueError(f"Scope no soportado: {scope}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    weeks = SCOPE_WEEKS[scope]
    trips = pl.concat([week_lf(w) for w in weeks], how="diagonal_relaxed")

    weekly = build_weekly_coverage(trips)
    daily = build_daily_coverage(trips)
    target_distribution, threshold_sensitivity, conflicts = build_pooled_target_audit(trips)

    weekly.write_csv(out_path(scope, "scope_coverage_weekly"))
    daily.write_csv(out_path(scope, "scope_coverage_daily"))
    target_distribution.write_csv(out_path(scope, "scope_pooled_target_distribution"))
    threshold_sensitivity.write_csv(out_path(scope, "scope_pooled_threshold_sensitivity"))
    conflicts.write_csv(out_path(scope, "scope_pooled_target_conflicts_sample"))

    print(f"✅ Auditoría de cobertura escrita en {OUT_DIR}")
    print(weekly)
    print(target_distribution)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.scope)


if __name__ == "__main__":
    main()
