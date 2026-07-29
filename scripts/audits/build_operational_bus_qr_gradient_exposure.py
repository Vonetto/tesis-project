from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_operational_bus_demand_pressure import (  # noqa: E402
    bus_boarding_events_lf,
)
from scripts.audits.build_operational_offer_demand_exposure import (  # noqa: E402
    DEFAULT_OUT_DIR,
    DEFAULT_WEEKS,
    add_franja_v2,
    trip_base_lf,
)


DEFAULT_MATRIX_PATH = (
    PROJECT_ROOT
    / "tmp"
    / "audits"
    / "user_level_redesign"
    / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
)
DEFAULT_OUTPUT_NAME = "operational_bus_qr_gradient_exposure_year_franja.parquet"
ZONE_CONTEXT_NAME = "operational_zone_franja_week_context.parquet"
STOP_PRESSURE_CONTEXT_NAME = (
    "operational_bus_stop_hour_pressure_context.parquet"
)
ZONE_PRESSURE_CONTEXT_NAME = (
    "operational_bus_zone_hour_pressure_context.parquet"
)

KEYS = ["id_tarjeta", "partition", "year", "franja_v2"]


def origin_exposure_week_lf(
    trips: pl.LazyFrame,
    zone_context: pl.LazyFrame,
) -> pl.LazyFrame:
    joined = trips.join(
        zone_context,
        on=["partition", "zone_id", "franja_v2"],
        how="left",
    )
    density_col = "op_bus_stops_with_supply_zone_franja_density_km2"
    metrics = {
        "_sum_origin_offer_raw": (
            "op_bus_supply_typical_stop_buses_h_zone_franja_mean"
        ),
        "_sum_origin_offer_percentile": (
            "op_bus_supply_typical_stop_buses_h_zone_franja_percentile"
        ),
        "_sum_origin_diversity_raw": (
            "op_bus_service_directions_zone_franja_mean"
        ),
        "_sum_origin_diversity_percentile": (
            "op_bus_service_directions_zone_franja_percentile"
        ),
        "_sum_origin_density_raw": density_col,
        "_sum_origin_density_percentile": (
            "op_bus_stops_with_supply_zone_franja_density_percentile"
        ),
    }
    return joined.group_by(KEYS).agg(
        [
            pl.len().alias("_n_origin_context"),
            pl.col(density_col)
            .is_not_null()
            .sum()
            .alias("_n_origin_density"),
            *[
                pl.col(column).sum().alias(output)
                for output, column in metrics.items()
            ],
        ]
    )


def boarding_exposure_week_lf(
    events: pl.LazyFrame,
    context: pl.LazyFrame,
    *,
    geography: str,
) -> pl.LazyFrame:
    if geography == "stop":
        location_col = "stop_id"
        cell_keys = [
            "partition",
            "stop_id",
            "hour_start",
            "franja_v2",
        ]
        suffix = "stop_hour"
    elif geography == "zone":
        location_col = "zone_id"
        cell_keys = [
            "partition",
            "zone_id",
            "hour_start",
            "franja_v2",
        ]
        suffix = "zone_hour"
    else:
        raise ValueError(f"Geografia no soportada: {geography}")

    demand_col = f"op_bus_demand_boardings_{suffix}"
    demand_percentile_col = f"{demand_col}_percentile"
    supply_col = f"op_bus_supply_buses_h_{suffix}"
    supply_percentile_col = f"{supply_col}_percentile"
    pressure_percentile_col = (
        "op_bus_pressure_boardings_per_scheduled_passage_"
        f"{suffix}_percentile"
    )
    valid = events.drop_nulls(
        ["id_tarjeta", location_col, "hour_start", "franja_v2"]
    )
    own = valid.group_by(["id_tarjeta", *cell_keys]).agg(
        pl.len().alias("_own_boardings")
    )
    joined = (
        valid.join(own, on=["id_tarjeta", *cell_keys], how="left")
        .join(context, on=cell_keys, how="left")
        .with_columns(
            [
                (
                    pl.col(demand_col) - pl.col("_own_boardings")
                )
                .clip(lower_bound=0)
                .alias("_external_boardings"),
                (pl.col(supply_col) > 0).alias("_matched_supply"),
            ]
        )
        .with_columns(
            pl.when(pl.col("_matched_supply"))
            .then(pl.col("_external_boardings") / pl.col(supply_col))
            .otherwise(None)
            .alias("_external_pressure")
        )
    )

    prefix = f"_{geography}"
    aggregations: list[pl.Expr] = [
        pl.len().alias(f"{prefix}_n_events"),
        pl.col("_matched_supply").sum().alias(f"{prefix}_n_matched"),
        pl.col("_external_boardings")
        .sum()
        .alias(f"{prefix}_sum_external_demand"),
        pl.col(demand_percentile_col)
        .sum()
        .alias(f"{prefix}_sum_demand_percentile"),
        pl.when(pl.col("_matched_supply"))
        .then(pl.col(supply_col))
        .otherwise(None)
        .sum()
        .alias(f"{prefix}_sum_supply_raw"),
        pl.when(pl.col("_matched_supply"))
        .then(pl.col(supply_percentile_col))
        .otherwise(None)
        .sum()
        .alias(f"{prefix}_sum_supply_percentile"),
        pl.col("_external_pressure")
        .sum()
        .alias(f"{prefix}_sum_external_pressure"),
        pl.when(pl.col("_matched_supply"))
        .then(pl.col(pressure_percentile_col))
        .otherwise(None)
        .sum()
        .alias(f"{prefix}_sum_pressure_percentile"),
    ]
    if geography == "stop":
        aggregations.append(
            pl.when(pl.col("_matched_supply"))
            .then(pl.col("op_bus_supply_service_directions_stop_hour"))
            .otherwise(None)
            .sum()
            .alias("_stop_sum_diversity_raw")
        )

    return joined.group_by(KEYS).agg(aggregations)


def finalize_exposure_lf(source: pl.LazyFrame) -> pl.LazyFrame:
    schema = source.collect_schema().names()
    sum_columns = [column for column in schema if column.startswith("_")]
    aggregated = source.group_by(
        ["id_tarjeta", "year", "franja_v2"]
    ).agg(
        [
            pl.col(column).sum().alias(column)
            for column in sum_columns
        ]
    )

    expressions: list[pl.Expr] = [
        pl.col("_n_origin_context").alias("op_qr_n_origin_context_trips"),
        pl.col("_n_origin_density").alias("op_qr_n_origin_density_trips"),
        (
            pl.col("_sum_origin_offer_raw")
            / pl.col("_n_origin_context")
        ).alias("op_qr_zone_offer_raw_mean"),
        (
            pl.col("_sum_origin_offer_percentile")
            / pl.col("_n_origin_context")
        ).alias("op_qr_zone_offer_percentile_mean"),
        (
            pl.col("_sum_origin_diversity_raw")
            / pl.col("_n_origin_context")
        ).alias("op_qr_zone_diversity_raw_mean"),
        (
            pl.col("_sum_origin_diversity_percentile")
            / pl.col("_n_origin_context")
        ).alias("op_qr_zone_diversity_percentile_mean"),
        pl.when(pl.col("_n_origin_density") > 0)
        .then(
            pl.col("_sum_origin_density_raw")
            / pl.col("_n_origin_density")
        )
        .otherwise(None)
        .alias("op_qr_zone_density_raw_mean"),
        pl.when(pl.col("_n_origin_density") > 0)
        .then(
            pl.col("_sum_origin_density_percentile")
            / pl.col("_n_origin_density")
        )
        .otherwise(None)
        .alias("op_qr_zone_density_percentile_mean"),
    ]
    for geography in ("stop", "zone"):
        prefix = f"_{geography}"
        expressions.extend(
            [
                pl.col(f"{prefix}_n_events").alias(
                    f"op_qr_n_bus_{geography}_events"
                ),
                pl.col(f"{prefix}_n_matched").alias(
                    f"op_qr_n_bus_{geography}_matched_events"
                ),
                pl.when(pl.col(f"{prefix}_n_events") > 0)
                .then(
                    pl.col(f"{prefix}_sum_external_demand")
                    / pl.col(f"{prefix}_n_events")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_demand_external_mean"),
                pl.when(pl.col(f"{prefix}_n_events") > 0)
                .then(
                    pl.col(f"{prefix}_sum_demand_percentile")
                    / pl.col(f"{prefix}_n_events")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_demand_percentile_mean"),
                pl.when(pl.col(f"{prefix}_n_matched") > 0)
                .then(
                    pl.col(f"{prefix}_sum_supply_raw")
                    / pl.col(f"{prefix}_n_matched")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_supply_raw_mean"),
                pl.when(pl.col(f"{prefix}_n_matched") > 0)
                .then(
                    pl.col(f"{prefix}_sum_supply_percentile")
                    / pl.col(f"{prefix}_n_matched")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_supply_percentile_mean"),
                pl.when(pl.col(f"{prefix}_n_matched") > 0)
                .then(
                    pl.col(f"{prefix}_sum_external_pressure")
                    / pl.col(f"{prefix}_n_matched")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_pressure_external_mean"),
                pl.when(pl.col(f"{prefix}_n_matched") > 0)
                .then(
                    pl.col(f"{prefix}_sum_pressure_percentile")
                    / pl.col(f"{prefix}_n_matched")
                )
                .otherwise(None)
                .alias(f"op_qr_bus_{geography}_pressure_percentile_mean"),
            ]
        )
    expressions.append(
        pl.when(pl.col("_stop_n_matched") > 0)
        .then(
            pl.col("_stop_sum_diversity_raw")
            / pl.col("_stop_n_matched")
        )
        .otherwise(None)
        .alias("op_qr_bus_stop_diversity_raw_mean")
    )

    return aggregated.select(
        ["id_tarjeta", "year", "franja_v2", *expressions]
    ).sort(["id_tarjeta", "year", "franja_v2"])


def build_exposure(
    *,
    weeks: list[str],
    out_dir: Path,
    matrix_path: Path,
    force: bool,
) -> Path:
    output_path = out_dir / DEFAULT_OUTPUT_NAME
    if output_path.exists() and not force:
        return output_path

    required = [
        matrix_path,
        out_dir / ZONE_CONTEXT_NAME,
        out_dir / STOP_PRESSURE_CONTEXT_NAME,
        out_dir / ZONE_PRESSURE_CONTEXT_NAME,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Faltan insumos: {missing}")

    eligible_cards = (
        pl.scan_parquet(matrix_path)
        .select(pl.col("id_tarjeta").cast(pl.Utf8))
        .unique()
    )
    zone_context = pl.scan_parquet(out_dir / ZONE_CONTEXT_NAME)
    stop_context = pl.scan_parquet(out_dir / STOP_PRESSURE_CONTEXT_NAME)
    zone_pressure_context = pl.scan_parquet(
        out_dir / ZONE_PRESSURE_CONTEXT_NAME
    )

    part_dir = out_dir / "_qr_gradient_parts"
    if part_dir.exists():
        shutil.rmtree(part_dir)
    part_dir.mkdir(parents=True)
    paths: list[Path] = []
    try:
        for week in weeks:
            year = int(week[:4])
            trips = (
                add_franja_v2(
                    trip_base_lf(week),
                    timestamp_col="tiempo_inicio_viaje",
                )
                .join(eligible_cards, on="id_tarjeta", how="inner")
                .with_columns(pl.lit(year).cast(pl.Int16).alias("year"))
            )
            events = (
                bus_boarding_events_lf(week)
                .join(eligible_cards, on="id_tarjeta", how="inner")
                .with_columns(pl.lit(year).cast(pl.Int16).alias("year"))
            )
            origin = origin_exposure_week_lf(
                trips,
                zone_context.filter(pl.col("partition") == week),
            )
            stop = boarding_exposure_week_lf(
                events,
                stop_context.filter(pl.col("partition") == week),
                geography="stop",
            )
            zone = boarding_exposure_week_lf(
                events,
                zone_pressure_context.filter(pl.col("partition") == week),
                geography="zone",
            )
            part = (
                origin.join(stop, on=KEYS, how="full", coalesce=True)
                .join(zone, on=KEYS, how="full", coalesce=True)
            )
            path = part_dir / f"exposure_{week}.parquet"
            part.sink_parquet(path)
            paths.append(path)

        final = finalize_exposure_lf(
            pl.concat(
                [pl.scan_parquet(path) for path in paths],
                how="diagonal_relaxed",
            )
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.sink_parquet(output_path)
    finally:
        if part_dir.exists():
            shutil.rmtree(part_dir)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Materializa exposiciones bus por tarjeta, ano y franja para "
            "gradientes QR/BIP."
        )
    )
    parser.add_argument("--weeks", nargs="+", default=DEFAULT_WEEKS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--matrix-path",
        type=Path,
        default=DEFAULT_MATRIX_PATH,
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    unknown = sorted(set(args.weeks) - set(DEFAULT_WEEKS))
    if unknown:
        raise SystemExit(f"Semanas no soportadas: {unknown}")
    output = build_exposure(
        weeks=args.weeks,
        out_dir=args.out_dir,
        matrix_path=args.matrix_path,
        force=args.force,
    )
    print(output)


if __name__ == "__main__":
    main()
