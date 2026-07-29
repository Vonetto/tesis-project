from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow.parquet as pq


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_operational_offer_demand_exposure import (  # noqa: E402
    BUS_FREQUENCIES_BY_WEEK,
    BUS_LIKE_MODE_CODES,
    DEFAULT_OUT_DIR,
    DEFAULT_WEEKS,
    REQUIRED_BUS_FREQUENCY_COLUMNS,
    TRIPS_BY_WEEK,
    add_franja_v2,
    bus_stop_hour_context_lf,
    date_tipodia_lf,
    percentile_within_groups,
    write_json,
)


N_STAGES = 6
STOP_ZONE_MAPPING_NAME = "operational_stop_zone_mapping.parquet"

REQUIRED_TRIP_COLUMNS = [
    "pk_viaje",
    "id_tarjeta",
    "tipodia",
    *[
        f"{field}_{stage}"
        for stage in range(1, N_STAGES + 1)
        for field in (
            "tipo_transporte",
            "paradero_subida",
            "zona_subida",
            "tiempo_subida",
        )
    ],
]

STOP_KEYS = ["partition", "stop_id", "hour_start", "franja_v2"]
ZONE_KEYS = ["partition", "zone_id", "hour_start", "franja_v2"]


def parse_stage_timestamp(column: str) -> pl.Expr:
    return pl.col(column).cast(pl.Utf8).str.to_datetime(
        "%Y-%m-%d %H:%M:%S",
        strict=False,
    )


def bus_boarding_events_lf(
    week: str,
    *,
    trips_path: Path | None = None,
) -> pl.LazyFrame:
    path = trips_path or TRIPS_BY_WEEK[week]
    stage_structs = [
        pl.struct(
            [
                pl.lit(stage).cast(pl.Int8).alias("stage_number"),
                pl.col(f"tipo_transporte_{stage}").cast(pl.Utf8).alias("mode_code"),
                pl.col(f"paradero_subida_{stage}").cast(pl.Utf8).alias("stop_id"),
                pl.col(f"zona_subida_{stage}")
                .cast(pl.Int64, strict=False)
                .alias("zone_id"),
                parse_stage_timestamp(f"tiempo_subida_{stage}").alias(
                    "boarding_timestamp"
                ),
            ]
        )
        for stage in range(1, N_STAGES + 1)
    ]

    events = (
        pl.scan_parquet(path)
        .select(
            [
                pl.col("pk_viaje").cast(pl.UInt64).alias("trip_id"),
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("tipodia").cast(pl.Int8, strict=False),
                pl.concat_list(stage_structs).alias("_stages"),
            ]
        )
        .explode("_stages")
        .unnest("_stages")
        .filter(pl.col("mode_code").is_in(BUS_LIKE_MODE_CODES))
        .with_columns(
            [
                pl.lit(week).alias("partition"),
                (pl.col("stage_number") == 1).alias("is_first_stage"),
                pl.col("boarding_timestamp").dt.truncate("1h").alias("hour_start"),
            ]
        )
    )
    return add_franja_v2(
        events,
        timestamp_col="boarding_timestamp",
    ).drop(["_ts_local", "_is_laboral", "_hora"])


def stop_hour_supply_lf(week: str) -> pl.LazyFrame:
    base = (
        bus_stop_hour_context_lf(week)
        .rename(
            {
                "op_stop_bus_supply_buses_h_observed": (
                    "op_bus_supply_buses_h_stop_hour"
                ),
                "op_stop_bus_service_directions_observed": (
                    "op_bus_supply_service_directions_stop_hour"
                ),
                "op_stop_bus_supply_buses_h_observed_percentile": (
                    "op_bus_supply_buses_h_stop_hour_percentile"
                ),
            }
        )
        .drop("op_stop_bus_headway_min_observed")
        .with_columns(
            [
                pl.lit(week).alias("partition"),
                pl.col("hour_start").dt.date().alias("service_date"),
            ]
        )
        .join(date_tipodia_lf(week), on="service_date", how="left")
    )
    return (
        add_franja_v2(base, timestamp_col="hour_start")
        .select(
            [
                *STOP_KEYS,
                "op_bus_supply_buses_h_stop_hour",
                "op_bus_supply_service_directions_stop_hour",
                "op_bus_supply_buses_h_stop_hour_percentile",
            ]
        )
    )


def zone_hour_supply_lf(
    week: str,
    stop_zone_mapping: pl.DataFrame,
) -> pl.LazyFrame:
    return (
        stop_hour_supply_lf(week)
        .join(
            stop_zone_mapping.select(["stop_id", "zone_id"]).lazy(),
            on="stop_id",
            how="inner",
        )
        .group_by(ZONE_KEYS)
        .agg(
            [
                pl.col("op_bus_supply_buses_h_stop_hour")
                .sum()
                .alias("op_bus_supply_buses_h_zone_hour"),
                pl.col("op_bus_supply_buses_h_stop_hour")
                .mean()
                .alias("op_bus_supply_typical_stop_buses_h_zone_hour"),
                pl.col("stop_id")
                .n_unique()
                .alias("op_bus_supply_active_stops_zone_hour"),
            ]
        )
        .with_columns(
            [
                percentile_within_groups(
                    "op_bus_supply_buses_h_zone_hour",
                    ["partition", "franja_v2"],
                ).alias("op_bus_supply_buses_h_zone_hour_percentile"),
                percentile_within_groups(
                    "op_bus_supply_typical_stop_buses_h_zone_hour",
                    ["partition", "franja_v2"],
                ).alias(
                    "op_bus_supply_typical_stop_buses_h_zone_hour_percentile"
                ),
            ]
        )
    )


def demand_by_cell_lf(
    events: pl.LazyFrame,
    *,
    geography: str,
) -> pl.LazyFrame:
    if geography == "stop":
        location_col = "stop_id"
        keys = STOP_KEYS
        suffix = "stop_hour"
    elif geography == "zone":
        location_col = "zone_id"
        keys = ZONE_KEYS
        suffix = "zone_hour"
    else:
        raise ValueError(f"Geografia no soportada: {geography}")

    return (
        events.drop_nulls(
            ["id_tarjeta", "trip_id", location_col, "hour_start", "franja_v2"]
        )
        .group_by(keys)
        .agg(
            [
                pl.len().alias(f"op_bus_demand_boardings_{suffix}"),
                pl.col("trip_id")
                .n_unique()
                .alias(f"op_bus_demand_trips_{suffix}"),
                pl.col("id_tarjeta")
                .n_unique()
                .alias(f"op_bus_demand_cards_{suffix}"),
            ]
        )
    )


def pressure_context_lf(
    demand: pl.LazyFrame,
    supply: pl.LazyFrame,
    *,
    geography: str,
) -> pl.LazyFrame:
    if geography == "stop":
        keys = STOP_KEYS
        suffix = "stop_hour"
    elif geography == "zone":
        keys = ZONE_KEYS
        suffix = "zone_hour"
    else:
        raise ValueError(f"Geografia no soportada: {geography}")

    supply_col = f"op_bus_supply_buses_h_{suffix}"
    boardings_col = f"op_bus_demand_boardings_{suffix}"
    trips_col = f"op_bus_demand_trips_{suffix}"
    cards_col = f"op_bus_demand_cards_{suffix}"
    pressure_boardings_col = f"op_bus_pressure_boardings_per_bus_{suffix}"
    pressure_cards_col = f"op_bus_pressure_cards_per_bus_{suffix}"
    canonical_pressure_boardings_col = (
        f"op_bus_pressure_boardings_per_scheduled_passage_{suffix}"
    )
    canonical_pressure_cards_col = (
        f"op_bus_pressure_cards_per_scheduled_passage_{suffix}"
    )

    return (
        demand.join(supply, on=keys, how="left")
        .with_columns(
            [
                pl.col(supply_col)
                .is_not_null()
                .alias(f"op_has_bus_supply_{suffix}"),
                pl.when(pl.col(supply_col) > 0)
                .then(pl.col(boardings_col) / pl.col(supply_col))
                .otherwise(None)
                .alias(pressure_boardings_col),
                pl.when(pl.col(supply_col) > 0)
                .then(pl.col(boardings_col) / pl.col(supply_col))
                .otherwise(None)
                .alias(canonical_pressure_boardings_col),
                pl.when(pl.col(supply_col) > 0)
                .then(pl.col(cards_col) / pl.col(supply_col))
                .otherwise(None)
                .alias(pressure_cards_col),
                pl.when(pl.col(supply_col) > 0)
                .then(pl.col(cards_col) / pl.col(supply_col))
                .otherwise(None)
                .alias(canonical_pressure_cards_col),
            ]
        )
        .with_columns(
            [
                percentile_within_groups(
                    boardings_col,
                    ["partition", "franja_v2"],
                ).alias(f"{boardings_col}_percentile"),
                percentile_within_groups(
                    trips_col,
                    ["partition", "franja_v2"],
                ).alias(f"{trips_col}_percentile"),
                percentile_within_groups(
                    cards_col,
                    ["partition", "franja_v2"],
                ).alias(f"{cards_col}_percentile"),
                percentile_within_groups(
                    pressure_boardings_col,
                    ["partition", "franja_v2"],
                ).alias(f"{pressure_boardings_col}_percentile"),
                percentile_within_groups(
                    canonical_pressure_boardings_col,
                    ["partition", "franja_v2"],
                ).alias(
                    f"{canonical_pressure_boardings_col}_percentile"
                ),
                percentile_within_groups(
                    pressure_cards_col,
                    ["partition", "franja_v2"],
                ).alias(f"{pressure_cards_col}_percentile"),
                percentile_within_groups(
                    canonical_pressure_cards_col,
                    ["partition", "franja_v2"],
                ).alias(f"{canonical_pressure_cards_col}_percentile"),
            ]
        )
        .sort(keys)
    )


def zone_franja_context_lf(zone_context: pl.LazyFrame) -> pl.LazyFrame:
    matched_supply = pl.when(pl.col("op_has_bus_supply_zone_hour")).then(
        pl.col("op_bus_supply_buses_h_zone_hour")
    )
    context = (
        zone_context.group_by(["partition", "zone_id", "franja_v2"])
        .agg(
            [
                pl.len().alias("op_bus_demand_hours_zone_franja_week"),
                pl.col("op_has_bus_supply_zone_hour")
                .sum()
                .alias("op_bus_supply_matched_hours_zone_franja_week"),
                pl.col("op_bus_demand_boardings_zone_hour")
                .sum()
                .alias("op_bus_demand_boardings_zone_franja_week"),
                pl.col("op_bus_demand_trips_zone_hour")
                .sum()
                .alias("op_bus_demand_trip_cells_zone_franja_week"),
                pl.col("op_bus_demand_cards_zone_hour")
                .sum()
                .alias("op_bus_demand_card_cells_zone_franja_week"),
                matched_supply.sum().alias(
                    "op_bus_supply_buses_h_demand_hours_zone_franja_week"
                ),
                pl.col(
                    "op_bus_pressure_boardings_per_scheduled_passage_zone_hour"
                )
                .mean()
                .alias(
                    "op_bus_pressure_boardings_per_scheduled_passage_zone_hour_mean"
                ),
            ]
        )
        .with_columns(
            [
                (
                    pl.col("op_bus_supply_matched_hours_zone_franja_week")
                    / pl.col("op_bus_demand_hours_zone_franja_week")
                ).alias("op_bus_supply_zone_hour_match_share"),
                pl.when(
                    pl.col(
                        "op_bus_supply_buses_h_demand_hours_zone_franja_week"
                    )
                    > 0
                )
                .then(
                    pl.col("op_bus_demand_boardings_zone_franja_week")
                    / pl.col(
                        "op_bus_supply_buses_h_demand_hours_zone_franja_week"
                    )
                )
                .otherwise(None)
                .alias(
                    "op_bus_pressure_boardings_per_scheduled_stop_passage_zone_franja_week"
                ),
            ]
        )
        .with_columns(
            [
                pl.col(
                    "op_bus_pressure_boardings_per_scheduled_passage_zone_hour_mean"
                ).alias(
                    "op_bus_pressure_boardings_per_bus_zone_hour_mean"
                ),
                pl.col(
                    "op_bus_pressure_boardings_per_scheduled_stop_passage_zone_franja_week"
                ).alias(
                    "op_bus_pressure_boardings_per_scheduled_bus_zone_franja_week"
                ),
            ]
        )
    )
    return context.with_columns(
        [
            percentile_within_groups(
                "op_bus_demand_boardings_zone_franja_week",
                ["partition", "franja_v2"],
            ).alias(
                "op_bus_demand_boardings_zone_franja_week_percentile"
            ),
            percentile_within_groups(
                "op_bus_pressure_boardings_per_scheduled_stop_passage_zone_franja_week",
                ["partition", "franja_v2"],
            ).alias(
                "op_bus_pressure_boardings_per_scheduled_stop_passage_zone_franja_week_percentile"
            ),
        ]
    ).with_columns(
        pl.col(
            "op_bus_pressure_boardings_per_scheduled_stop_passage_zone_franja_week_percentile"
        ).alias(
            "op_bus_pressure_boardings_per_scheduled_bus_zone_franja_week_percentile"
        )
    ).sort(["partition", "zone_id", "franja_v2"])


def _card_geography_sums_lf(
    events: pl.LazyFrame,
    context: pl.LazyFrame,
    *,
    geography: str,
) -> pl.LazyFrame:
    if geography == "stop":
        location_col = "stop_id"
        keys = STOP_KEYS
        suffix = "stop_hour"
        prefix = "stop"
    elif geography == "zone":
        location_col = "zone_id"
        keys = ZONE_KEYS
        suffix = "zone_hour"
        prefix = "zone"
    else:
        raise ValueError(f"Geografia no soportada: {geography}")

    card_keys = ["id_tarjeta", *keys]
    valid_events = events.drop_nulls(
        ["id_tarjeta", "trip_id", location_col, "hour_start", "franja_v2"]
    )
    own = valid_events.group_by(card_keys).agg(
        [
            pl.len().alias("_own_boardings"),
            pl.col("trip_id").n_unique().alias("_own_trips"),
        ]
    )
    cell_joined = (
        own.join(context, on=keys, how="left")
        .with_columns(
            [
                (
                    pl.col(f"op_bus_demand_boardings_{suffix}")
                    - pl.col("_own_boardings")
                )
                .clip(lower_bound=0)
                .alias("_external_boardings"),
                (
                    pl.col(f"op_bus_demand_trips_{suffix}")
                    - pl.col("_own_trips")
                )
                .clip(lower_bound=0)
                .alias("_external_trips"),
                (pl.col(f"op_bus_demand_cards_{suffix}") - 1)
                .clip(lower_bound=0)
                .alias("_external_cards"),
            ]
        )
        .with_columns(
            [
                pl.col(f"op_bus_supply_buses_h_{suffix}")
                .is_not_null()
                .alias("_matched_supply"),
                pl.when(pl.col(f"op_bus_supply_buses_h_{suffix}") > 0)
                .then(
                    pl.col("_external_boardings")
                    / pl.col(f"op_bus_supply_buses_h_{suffix}")
                )
                .otherwise(None)
                .alias("_external_boarding_pressure"),
                pl.when(pl.col(f"op_bus_supply_buses_h_{suffix}") > 0)
                .then(
                    pl.col("_external_cards")
                    / pl.col(f"op_bus_supply_buses_h_{suffix}")
                )
                .otherwise(None)
                .alias("_external_card_pressure"),
            ]
        )
    )
    event_joined = valid_events.join(
        cell_joined,
        on=card_keys,
        how="left",
    )
    event_agg = event_joined.group_by("id_tarjeta").agg(
        [
            pl.len().alias(f"_n_{prefix}_events"),
            pl.col("_matched_supply").sum().alias(f"_n_{prefix}_matched"),
            pl.col("_external_boardings")
            .sum()
            .alias(f"_sum_{prefix}_external_boardings"),
            pl.col("_external_trips")
            .sum()
            .alias(f"_sum_{prefix}_external_trips"),
            pl.col("_external_cards")
            .sum()
            .alias(f"_sum_{prefix}_external_cards"),
            pl.col("_external_boarding_pressure")
            .sum()
            .alias(f"_sum_{prefix}_external_boarding_pressure"),
            pl.col("_external_card_pressure")
            .sum()
            .alias(f"_sum_{prefix}_external_card_pressure"),
            pl.col(f"op_bus_demand_boardings_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_boarding_demand_percentile"),
            pl.col(f"op_bus_demand_trips_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_trip_demand_percentile"),
            pl.col(f"op_bus_demand_cards_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_card_demand_percentile"),
            pl.col(
                f"op_bus_pressure_boardings_per_scheduled_passage_{suffix}_percentile"
            )
            .sum()
            .alias(f"_sum_{prefix}_pressure_percentile"),
            pl.col(f"op_bus_supply_buses_h_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_supply_percentile"),
        ]
    )
    cell_agg = cell_joined.group_by("id_tarjeta").agg(
        [
            pl.len().alias(f"_n_{prefix}_cells"),
            pl.col("_matched_supply")
            .sum()
            .alias(f"_n_{prefix}_cells_matched"),
            pl.col("_external_boardings")
            .sum()
            .alias(f"_sum_{prefix}_cell_external_boardings"),
            pl.col("_external_trips")
            .sum()
            .alias(f"_sum_{prefix}_cell_external_trips"),
            pl.col("_external_cards")
            .sum()
            .alias(f"_sum_{prefix}_cell_external_cards"),
            pl.col("_external_boarding_pressure")
            .sum()
            .alias(
                f"_sum_{prefix}_cell_external_boarding_pressure"
            ),
            pl.col("_external_card_pressure")
            .sum()
            .alias(f"_sum_{prefix}_cell_external_card_pressure"),
            pl.col(f"op_bus_demand_boardings_{suffix}_percentile")
            .sum()
            .alias(
                f"_sum_{prefix}_cell_boarding_demand_percentile"
            ),
            pl.col(f"op_bus_demand_trips_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_cell_trip_demand_percentile"),
            pl.col(f"op_bus_demand_cards_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_cell_card_demand_percentile"),
            pl.col(
                f"op_bus_pressure_boardings_per_scheduled_passage_{suffix}_percentile"
            )
            .sum()
            .alias(f"_sum_{prefix}_cell_pressure_percentile"),
            pl.col(f"op_bus_supply_buses_h_{suffix}_percentile")
            .sum()
            .alias(f"_sum_{prefix}_cell_supply_percentile"),
        ]
    )
    return event_agg.join(cell_agg, on="id_tarjeta", how="left")


def card_exposure_week_lf(
    events: pl.LazyFrame,
    stop_context: pl.LazyFrame,
    zone_context: pl.LazyFrame,
) -> pl.LazyFrame:
    common = events.drop_nulls(["id_tarjeta", "trip_id"]).group_by(
        "id_tarjeta"
    ).agg(
        [
            pl.len().alias("_n_bus_boarding_stages"),
            pl.col("trip_id").n_unique().alias("_n_bus_trips"),
            pl.col("is_first_stage").sum().alias("_n_first_stage_boardings"),
        ]
    )
    stop = _card_geography_sums_lf(
        events,
        stop_context,
        geography="stop",
    )
    zone = _card_geography_sums_lf(
        events,
        zone_context,
        geography="zone",
    )
    return common.join(stop, on="id_tarjeta", how="left").join(
        zone,
        on="id_tarjeta",
        how="left",
    )


def finalize_card_exposure_lf(card_week: pl.LazyFrame) -> pl.LazyFrame:
    sum_columns = [
        name
        for name in card_week.collect_schema().names()
        if name.startswith("_") and name != "_dummy"
    ]
    aggregated = card_week.group_by("id_tarjeta").agg(
        [pl.col(column).sum().alias(column) for column in sum_columns]
    )

    expressions: list[pl.Expr] = [
        pl.col("_n_bus_boarding_stages").alias("op_bus_n_boarding_stages"),
        pl.col("_n_bus_trips").alias("op_bus_n_trips_with_boarding"),
        pl.col("_n_first_stage_boardings").alias(
            "op_bus_n_first_stage_boardings"
        ),
    ]
    for prefix, suffix in [("stop", "stop_hour"), ("zone", "zone_hour")]:
        events_col = f"_n_{prefix}_events"
        matched_col = f"_n_{prefix}_matched"
        cells_col = f"_n_{prefix}_cells"
        cells_matched_col = f"_n_{prefix}_cells_matched"
        expressions.extend(
            [
                pl.col(events_col).alias(
                    f"op_bus_n_boarding_stages_with_{prefix}"
                ),
                pl.col(matched_col).alias(
                    f"op_bus_n_boarding_stages_with_{prefix}_supply"
                ),
                pl.col(cells_col).alias(
                    f"op_bus_n_unique_{suffix}_cells"
                ),
                pl.col(cells_matched_col).alias(
                    f"op_bus_n_unique_{suffix}_cells_with_supply"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(pl.col(matched_col) / pl.col(events_col))
                .otherwise(None)
                .alias(f"op_bus_{prefix}_supply_match_share"),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_boardings")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_boardings_excl_card_{suffix}_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_boardings")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_boardings_excl_card_{suffix}_boarding_weighted_mean"
                ),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_external_boardings")
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_boardings_excl_card_{suffix}_cell_weighted_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_trips")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(f"op_bus_demand_trips_excl_card_{suffix}_mean"),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_external_trips")
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_trips_excl_card_{suffix}_cell_weighted_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_cards")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(f"op_bus_demand_cards_excl_card_{suffix}_mean"),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_external_cards")
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_cards_excl_card_{suffix}_cell_weighted_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_boarding_pressure")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_bus_excl_card_{suffix}_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_boarding_pressure")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_scheduled_passage_excl_card_{suffix}_boarding_weighted_mean"
                ),
                pl.when(pl.col(cells_matched_col) > 0)
                .then(
                    pl.col(
                        f"_sum_{prefix}_cell_external_boarding_pressure"
                    )
                    / pl.col(cells_matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_scheduled_passage_excl_card_{suffix}_cell_weighted_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_card_pressure")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_cards_per_bus_excl_card_{suffix}_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_external_card_pressure")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_cards_per_scheduled_passage_excl_card_{suffix}_boarding_weighted_mean"
                ),
                pl.when(pl.col(cells_matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_external_card_pressure")
                    / pl.col(cells_matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_cards_per_scheduled_passage_excl_card_{suffix}_cell_weighted_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_boarding_demand_percentile")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_boardings_{suffix}_percentile_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_trip_demand_percentile")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_trips_{suffix}_percentile_mean"
                ),
                pl.when(pl.col(events_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_card_demand_percentile")
                    / pl.col(events_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_cards_{suffix}_percentile_mean"
                ),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(
                        f"_sum_{prefix}_cell_boarding_demand_percentile"
                    )
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_boardings_{suffix}_percentile_cell_weighted_mean"
                ),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_trip_demand_percentile")
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_trips_{suffix}_percentile_cell_weighted_mean"
                ),
                pl.when(pl.col(cells_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_card_demand_percentile")
                    / pl.col(cells_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_demand_cards_{suffix}_percentile_cell_weighted_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_pressure_percentile")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_bus_{suffix}_percentile_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_pressure_percentile")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_scheduled_passage_{suffix}_percentile_boarding_weighted_mean"
                ),
                pl.when(pl.col(cells_matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_pressure_percentile")
                    / pl.col(cells_matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_pressure_boardings_per_scheduled_passage_{suffix}_percentile_cell_weighted_mean"
                ),
                pl.when(pl.col(matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_supply_percentile")
                    / pl.col(matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_supply_buses_h_{suffix}_percentile_mean"
                ),
                pl.when(pl.col(cells_matched_col) > 0)
                .then(
                    pl.col(f"_sum_{prefix}_cell_supply_percentile")
                    / pl.col(cells_matched_col)
                )
                .otherwise(None)
                .alias(
                    f"op_bus_supply_buses_h_{suffix}_percentile_cell_weighted_mean"
                ),
            ]
        )

    return aggregated.select(["id_tarjeta", *expressions]).sort("id_tarjeta")


def parquet_columns(path: Path) -> set[str]:
    return set(pq.ParquetFile(path).schema.names)


def audit_inputs(
    weeks: list[str],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    rows = []
    blocking_errors = []
    for week in weeks:
        trips_path = TRIPS_BY_WEEK[week]
        frequency_path = BUS_FREQUENCIES_BY_WEEK[week]
        trip_columns = parquet_columns(trips_path) if trips_path.exists() else set()
        frequency_columns = (
            parquet_columns(frequency_path) if frequency_path.exists() else set()
        )
        rows.append(
            {
                "week": week,
                "trips_path": str(trips_path),
                "trips_exists": trips_path.exists(),
                "missing_trip_columns": sorted(
                    set(REQUIRED_TRIP_COLUMNS) - trip_columns
                ),
                "frequency_path": str(frequency_path),
                "frequency_exists": frequency_path.exists(),
                "missing_frequency_columns": sorted(
                    set(REQUIRED_BUS_FREQUENCY_COLUMNS) - frequency_columns
                ),
            }
        )
        if not trips_path.exists():
            blocking_errors.append(f"{week}: falta archivo de viajes")
        if set(REQUIRED_TRIP_COLUMNS) - trip_columns:
            blocking_errors.append(
                f"{week}: faltan columnas de etapas bus"
            )
        if not frequency_path.exists():
            blocking_errors.append(f"{week}: falta archivo de frecuencias bus")
        if set(REQUIRED_BUS_FREQUENCY_COLUMNS) - frequency_columns:
            blocking_errors.append(
                f"{week}: faltan columnas de frecuencias bus"
            )

    mapping_path = out_dir / STOP_ZONE_MAPPING_NAME
    if not mapping_path.exists():
        blocking_errors.append(
            "falta operational_stop_zone_mapping.parquet; construye primero 13A-H"
        )

    return {
        "weeks": weeks,
        "stop_zone_mapping_path": str(mapping_path),
        "rows": rows,
        "blocking_errors": blocking_errors,
        "measurement_scope": {
            "main_demand_unit": "cada etapa de subida bus o zona paga",
            "stop_pressure": (
                "subidas o tarjetas observadas por pasada bus programada "
                "equivalente en el mismo paradero-hora"
            ),
            "zone_pressure": (
                "subidas o tarjetas observadas por pasada bus-paradero "
                "programada equivalente en la misma zona-hora"
            ),
            "card_weighting": (
                "principal ponderada por subida; sensibilidad con igual peso "
                "por tarjeta-celda"
            ),
            "not_measured": [
                "ocupacion",
                "capacidad",
                "congestion",
                "espera real",
                "servicio efectivamente abordado",
            ],
        },
    }


def unmapped_supply_stops_lf(
    week: str,
    events: pl.LazyFrame,
    stop_zone_mapping: pl.DataFrame,
) -> pl.LazyFrame:
    frequency_by_stop = (
        pl.scan_parquet(BUS_FREQUENCIES_BY_WEEK[week])
        .select(
            [
                pl.col("Paradero").cast(pl.Utf8).alias("stop_id"),
                pl.col("freq_buses_h").cast(pl.Float64),
            ]
        )
        .drop_nulls(["stop_id", "freq_buses_h"])
        .group_by("stop_id")
        .agg(
            [
                pl.col("freq_buses_h")
                .sum()
                .alias("frequency_supply_buses_h"),
                pl.len().alias("n_frequency_rows"),
            ]
        )
    )
    event_stop_zone_counts = (
        events.drop_nulls(["stop_id", "zone_id"])
        .group_by(["stop_id", "zone_id"])
        .agg(pl.len().alias("n_observed_boardings_stop_zone"))
    )
    event_modal_zone = (
        event_stop_zone_counts.sort(
            ["stop_id", "n_observed_boardings_stop_zone", "zone_id"],
            descending=[False, True, False],
        )
        .group_by("stop_id", maintain_order=True)
        .agg(
            [
                pl.col("zone_id").first().alias("stage_modal_zone_id"),
                pl.col("n_observed_boardings_stop_zone")
                .first()
                .alias("n_boardings_stage_modal_zone"),
                pl.col("n_observed_boardings_stop_zone")
                .sum()
                .alias("n_boardings_stage_total"),
                pl.col("zone_id")
                .n_unique()
                .alias("n_stage_zone_candidates"),
            ]
        )
        .with_columns(
            (
                pl.col("n_boardings_stage_modal_zone")
                / pl.col("n_boardings_stage_total")
            ).alias("stage_modal_zone_share")
        )
    )
    mapping = stop_zone_mapping.select(
        [
            "stop_id",
            pl.col("zone_id").alias("_existing_zone_id"),
        ]
    ).lazy()
    return (
        frequency_by_stop.join(mapping, on="stop_id", how="left")
        .filter(pl.col("_existing_zone_id").is_null())
        .drop("_existing_zone_id")
        .join(event_modal_zone, on="stop_id", how="left")
        .with_columns(
            [
                pl.lit(week).alias("partition"),
                (
                    pl.col("frequency_supply_buses_h")
                    / pl.col("frequency_supply_buses_h").sum()
                ).alias("share_unmapped_frequency_supply_within_week"),
            ]
        )
        .select(
            [
                "partition",
                "stop_id",
                "frequency_supply_buses_h",
                "share_unmapped_frequency_supply_within_week",
                "n_frequency_rows",
                "stage_modal_zone_id",
                "stage_modal_zone_share",
                "n_stage_zone_candidates",
                "n_boardings_stage_total",
            ]
        )
        .sort(
            ["partition", "frequency_supply_buses_h", "stop_id"],
            descending=[False, True, False],
        )
    )


def _sink(lf: pl.LazyFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lf.sink_parquet(path)


def _concat_parts(parts: list[Path], out_path: Path) -> None:
    _sink(
        pl.concat(
            [pl.scan_parquet(path) for path in parts],
            how="diagonal_relaxed",
        ),
        out_path,
    )


def summarize_build(
    paths: dict[str, Path],
    *,
    weeks: list[str],
    event_audit_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    stop_context = pl.scan_parquet(paths["stop_context"])
    zone_context = pl.scan_parquet(paths["zone_context"])
    card = pl.scan_parquet(paths["card_exposure"])
    unmapped_supply = pl.scan_parquet(paths["unmapped_supply_stops"])
    totals = {
        key: sum(int(row[key]) for row in event_audit_rows)
        for key in (
            "n_bus_boarding_stages",
            "n_with_stop_time",
            "n_with_zone_time",
            "n_first_stage_bus_boardings",
        )
    }
    total_frequency_supply = sum(
        float(row["frequency_supply_total"]) for row in event_audit_rows
    )
    mapped_frequency_supply = sum(
        float(row["frequency_supply_mapped"]) for row in event_audit_rows
    )
    return {
        "weeks": weeks,
        "boarding_events": {
            **totals,
            "stop_time_coverage": (
                totals["n_with_stop_time"]
                / totals["n_bus_boarding_stages"]
            ),
            "zone_time_coverage": (
                totals["n_with_zone_time"]
                / totals["n_bus_boarding_stages"]
            ),
            "weekly_audit": event_audit_rows,
        },
        "zone_supply_mapping": {
            "frequency_supply_share_mapped": (
                mapped_frequency_supply / total_frequency_supply
            ),
            "frequency_supply_total": total_frequency_supply,
            "frequency_supply_mapped": mapped_frequency_supply,
            "n_unmapped_stop_week_rows": unmapped_supply.select(
                pl.len()
            ).collect().item(),
            "n_unmapped_stops": unmapped_supply.select(
                pl.col("stop_id").n_unique()
            ).collect().item(),
            "share_unmapped_stop_week_rows_with_stage_zone": (
                unmapped_supply.select(
                    pl.col("stage_modal_zone_id").is_not_null().mean()
                )
                .collect()
                .item()
            ),
        },
        "stop_hour": {
            "n_demand_cells": pl.scan_parquet(paths["stop_demand"])
            .select(pl.len())
            .collect()
            .item(),
            "supply_match_share": stop_context.select(
                pl.col("op_has_bus_supply_stop_hour").mean()
            )
            .collect()
            .item(),
        },
        "zone_hour": {
            "n_demand_cells": pl.scan_parquet(paths["zone_demand"])
            .select(pl.len())
            .collect()
            .item(),
            "supply_match_share": zone_context.select(
                pl.col("op_has_bus_supply_zone_hour").mean()
            )
            .collect()
            .item(),
        },
        "card_exposure": {
            "n_cards_with_bus_boardings": card.select(pl.len()).collect().item(),
            "mean_stop_supply_match_share": card.select(
                pl.col("op_bus_stop_supply_match_share").mean()
            )
            .collect()
            .item(),
            "mean_zone_supply_match_share": card.select(
                pl.col("op_bus_zone_supply_match_share").mean()
            )
            .collect()
            .item(),
        },
    }


def build_all(
    weeks: list[str],
    out_dir: Path,
    *,
    force: bool,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "input_audit": out_dir
        / "operational_bus_demand_pressure_input_audit.json",
        "stop_demand": out_dir / "operational_bus_stop_hour_demand.parquet",
        "zone_demand": out_dir / "operational_bus_zone_hour_demand.parquet",
        "stop_context": out_dir
        / "operational_bus_stop_hour_pressure_context.parquet",
        "zone_context": out_dir
        / "operational_bus_zone_hour_pressure_context.parquet",
        "zone_franja_context": out_dir
        / "operational_bus_zone_franja_week_pressure_context.parquet",
        "unmapped_supply_stops": out_dir
        / "operational_bus_unmapped_supply_stops.parquet",
        "card_exposure": out_dir
        / "operational_bus_demand_pressure_card_exposure.parquet",
        "summary": out_dir
        / "operational_bus_demand_pressure_build_summary.json",
    }
    existing = [
        str(path)
        for key, path in paths.items()
        if key != "input_audit" and path.exists()
    ]
    if existing and not force:
        raise FileExistsError(
            "Outputs 13I ya existen. Usa --force para sobrescribir:\n- "
            + "\n- ".join(existing)
        )

    audit = audit_inputs(weeks, out_dir=out_dir)
    write_json(paths["input_audit"], audit)
    if audit["blocking_errors"]:
        raise RuntimeError(
            "Inputs incompletos:\n- "
            + "\n- ".join(audit["blocking_errors"])
        )

    stop_zone_mapping = pl.read_parquet(out_dir / STOP_ZONE_MAPPING_NAME)
    part_dir = out_dir / "_operational_bus_demand_pressure_parts"
    if part_dir.exists():
        shutil.rmtree(part_dir)
    part_dir.mkdir(parents=True)

    part_paths: dict[str, list[Path]] = {
        "stop_demand": [],
        "zone_demand": [],
        "stop_context": [],
        "zone_context": [],
        "zone_franja_context": [],
        "unmapped_supply_stops": [],
        "card_week": [],
    }
    event_audit_rows = []

    try:
        for week in weeks:
            event_path = part_dir / f"events_{week}.parquet"
            _sink(bus_boarding_events_lf(week), event_path)
            events = pl.scan_parquet(event_path)

            event_audit = (
                events.select(
                    [
                        pl.len().alias("n_bus_boarding_stages"),
                        (
                            pl.col("stop_id").is_not_null()
                            & pl.col("hour_start").is_not_null()
                        )
                        .sum()
                        .alias("n_with_stop_time"),
                        (
                            pl.col("zone_id").is_not_null()
                            & pl.col("hour_start").is_not_null()
                        )
                        .sum()
                        .alias("n_with_zone_time"),
                        pl.col("is_first_stage")
                        .sum()
                        .alias("n_first_stage_bus_boardings"),
                    ]
                )
                .collect()
                .row(0, named=True)
            )
            frequency_mapping_audit = (
                pl.scan_parquet(BUS_FREQUENCIES_BY_WEEK[week])
                .select(
                    [
                        pl.col("Paradero").cast(pl.Utf8).alias("stop_id"),
                        pl.col("freq_buses_h").cast(pl.Float64),
                    ]
                )
                .join(
                    stop_zone_mapping.select(["stop_id", "zone_id"]).lazy(),
                    on="stop_id",
                    how="left",
                )
                .select(
                    [
                        pl.col("freq_buses_h")
                        .sum()
                        .alias("frequency_supply_total"),
                        pl.when(pl.col("zone_id").is_not_null())
                        .then(pl.col("freq_buses_h"))
                        .otherwise(0.0)
                        .sum()
                        .alias("frequency_supply_mapped"),
                        pl.col("stop_id")
                        .filter(pl.col("zone_id").is_null())
                        .n_unique()
                        .alias("n_frequency_stops_unmapped"),
                    ]
                )
                .collect()
                .row(0, named=True)
            )
            event_audit_rows.append(
                {
                    "week": week,
                    **event_audit,
                    **frequency_mapping_audit,
                }
            )

            stop_demand_path = part_dir / f"stop_demand_{week}.parquet"
            zone_demand_path = part_dir / f"zone_demand_{week}.parquet"
            stop_context_path = part_dir / f"stop_context_{week}.parquet"
            zone_context_path = part_dir / f"zone_context_{week}.parquet"
            zone_franja_path = part_dir / f"zone_franja_{week}.parquet"
            card_week_path = part_dir / f"card_week_{week}.parquet"
            unmapped_supply_path = (
                part_dir / f"unmapped_supply_{week}.parquet"
            )

            _sink(
                demand_by_cell_lf(events, geography="stop"),
                stop_demand_path,
            )
            _sink(
                demand_by_cell_lf(events, geography="zone"),
                zone_demand_path,
            )
            _sink(
                pressure_context_lf(
                    pl.scan_parquet(stop_demand_path),
                    stop_hour_supply_lf(week),
                    geography="stop",
                ),
                stop_context_path,
            )
            _sink(
                pressure_context_lf(
                    pl.scan_parquet(zone_demand_path),
                    zone_hour_supply_lf(week, stop_zone_mapping),
                    geography="zone",
                ),
                zone_context_path,
            )
            _sink(
                zone_franja_context_lf(
                    pl.scan_parquet(zone_context_path)
                ),
                zone_franja_path,
            )
            _sink(
                card_exposure_week_lf(
                    events,
                    pl.scan_parquet(stop_context_path),
                    pl.scan_parquet(zone_context_path),
                ),
                card_week_path,
            )
            _sink(
                unmapped_supply_stops_lf(
                    week,
                    events,
                    stop_zone_mapping,
                ),
                unmapped_supply_path,
            )

            for key, path in [
                ("stop_demand", stop_demand_path),
                ("zone_demand", zone_demand_path),
                ("stop_context", stop_context_path),
                ("zone_context", zone_context_path),
                ("zone_franja_context", zone_franja_path),
                ("unmapped_supply_stops", unmapped_supply_path),
                ("card_week", card_week_path),
            ]:
                part_paths[key].append(path)
            event_path.unlink()

        for key in (
            "stop_demand",
            "zone_demand",
            "stop_context",
            "zone_context",
            "zone_franja_context",
            "unmapped_supply_stops",
        ):
            _concat_parts(part_paths[key], paths[key])

        _sink(
            finalize_card_exposure_lf(
                pl.concat(
                    [
                        pl.scan_parquet(path)
                        for path in part_paths["card_week"]
                    ],
                    how="diagonal_relaxed",
                )
            ),
            paths["card_exposure"],
        )
    finally:
        if part_dir.exists():
            shutil.rmtree(part_dir)

    summary = summarize_build(
        paths,
        weeks=weeks,
        event_audit_rows=event_audit_rows,
    )
    write_json(paths["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Construye demanda bus por etapa de subida y presion observada "
            "contra oferta programada en el mismo paradero-hora y zona-hora."
        )
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--weeks", nargs="+", default=DEFAULT_WEEKS)
    parser.add_argument("--audit-inputs", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    unknown = sorted(set(args.weeks) - set(DEFAULT_WEEKS))
    if unknown:
        raise ValueError(f"Semanas no configuradas: {unknown}")

    if args.audit_inputs:
        audit = audit_inputs(args.weeks, out_dir=args.out_dir)
        write_json(
            args.out_dir
            / "operational_bus_demand_pressure_input_audit.json",
            audit,
        )
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        if audit["blocking_errors"]:
            raise SystemExit(1)
        return

    summary = build_all(
        args.weeks,
        args.out_dir,
        force=args.force,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
