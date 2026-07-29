from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

import polars as pl


PARTITION_PATTERN = re.compile(r"^(?P<year>\d{4})-W(?P<week>\d{2})$")


def build_partition_pairs(partitions: Iterable[str]) -> list[dict[str, str]]:
    parsed: list[tuple[str, int, str]] = []
    for partition in sorted(set(partitions)):
        match = PARTITION_PATTERN.match(partition)
        if match is None:
            raise ValueError(f"Particion semanal invalida: {partition}")
        parsed.append(
            (
                match.group("year"),
                int(match.group("week")),
                partition,
            )
        )

    pairs: list[dict[str, str]] = []
    by_year: dict[str, list[tuple[int, str]]] = {}
    by_week: dict[int, list[tuple[str, str]]] = {}
    for year, week, partition in parsed:
        by_year.setdefault(year, []).append((week, partition))
        by_week.setdefault(week, []).append((year, partition))

    for year, values in sorted(by_year.items()):
        ordered = sorted(values)
        for (week_a, partition_a), (week_b, partition_b) in zip(
            ordered,
            ordered[1:],
        ):
            if week_b - week_a == 1:
                pairs.append(
                    {
                        "comparison": "Semanas adyacentes",
                        "partition_a": partition_a,
                        "partition_b": partition_b,
                    }
                )

    for week, values in sorted(by_week.items()):
        ordered = sorted(values)
        for (_, partition_a), (_, partition_b) in zip(
            ordered,
            ordered[1:],
        ):
            pairs.append(
                {
                    "comparison": "Misma semana entre anos",
                    "partition_a": partition_a,
                    "partition_b": partition_b,
                }
            )

    return pairs


def aggregate_stop_hour_week(
    source: pl.LazyFrame | pl.DataFrame,
) -> pl.LazyFrame:
    lf = source.lazy() if isinstance(source, pl.DataFrame) else source
    supply_col = "op_bus_supply_buses_h_stop_hour"
    demand_col = "op_bus_demand_boardings_stop_hour"
    pressure_col = (
        "op_bus_pressure_boardings_per_scheduled_passage_stop_hour"
    )

    return (
        lf.with_columns(
            [
                pl.col("hour_start").dt.hour().alias("hour_of_day"),
                pl.col("hour_start").dt.date().alias("_service_date"),
                (pl.col(supply_col) > 0).alias("_has_matched_supply"),
                pl.when(pl.col(supply_col) > 0)
                .then(pl.col(demand_col))
                .otherwise(None)
                .alias("_matched_boardings"),
            ]
        )
        .group_by(
            ["partition", "stop_id", "hour_of_day", "franja_v2"]
        )
        .agg(
            [
                pl.len().alias("n_observed_demand_cells"),
                pl.col("_service_date")
                .n_unique()
                .alias("n_observed_days"),
                pl.col("_has_matched_supply")
                .sum()
                .alias("n_supply_matched_cells"),
                pl.col(demand_col)
                .sum()
                .alias("op_bus_demand_boardings_stop_hour_week"),
                pl.col(demand_col)
                .mean()
                .alias("op_bus_demand_boardings_stop_hour_week_mean"),
                pl.col("op_bus_demand_trips_stop_hour")
                .sum()
                .alias("op_bus_demand_trips_stop_hour_week"),
                pl.col("op_bus_demand_cards_stop_hour")
                .mean()
                .alias("op_bus_demand_cards_stop_hour_week_mean"),
                pl.col(supply_col)
                .mean()
                .alias("op_bus_supply_buses_h_stop_hour_week_mean"),
                pl.col(supply_col).sum().alias("_matched_supply_sum"),
                pl.col("_matched_boardings")
                .sum()
                .alias("_matched_boardings_sum"),
                pl.col("op_bus_supply_service_directions_stop_hour")
                .mean()
                .alias(
                    "op_bus_supply_service_directions_stop_hour_week_mean"
                ),
                pl.col(
                    "op_bus_supply_buses_h_stop_hour_percentile"
                )
                .mean()
                .alias(
                    "op_bus_supply_buses_h_stop_hour_percentile_mean"
                ),
                pl.col(
                    "op_bus_demand_boardings_stop_hour_percentile"
                )
                .mean()
                .alias(
                    "op_bus_demand_boardings_stop_hour_percentile_mean"
                ),
                pl.col(f"{pressure_col}_percentile")
                .mean()
                .alias(f"{pressure_col}_percentile_mean"),
            ]
        )
        .with_columns(
            [
                (
                    pl.col("n_supply_matched_cells")
                    / pl.col("n_observed_demand_cells")
                ).alias("op_bus_supply_match_share_stop_hour_week"),
                pl.when(pl.col("_matched_supply_sum") > 0)
                .then(
                    pl.col("_matched_boardings_sum")
                    / pl.col("_matched_supply_sum")
                )
                .otherwise(None)
                .alias(
                    "op_bus_pressure_boardings_per_scheduled_passage_"
                    "stop_hour_week"
                ),
            ]
        )
        .drop(["_matched_supply_sum", "_matched_boardings_sum"])
        .sort(["partition", "franja_v2", "stop_id", "hour_of_day"])
    )


def summarize_rank_stability(
    source: pl.DataFrame,
    *,
    scale: str,
    entity_columns: Sequence[str],
    metric_specs: Sequence[dict[str, str]],
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    pairs = build_partition_pairs(source["partition"].unique().to_list())
    franjas = sorted(source["franja_v2"].drop_nulls().unique().to_list())

    for spec in metric_specs:
        metric_col = spec["column"]
        for franja in franjas:
            franja_source = source.filter(pl.col("franja_v2") == franja)
            for pair in pairs:
                left = (
                    franja_source.filter(
                        pl.col("partition") == pair["partition_a"]
                    )
                    .select(
                        [
                            *entity_columns,
                            pl.col(metric_col).alias("_value_a"),
                        ]
                    )
                    .drop_nulls(["_value_a"])
                )
                right = (
                    franja_source.filter(
                        pl.col("partition") == pair["partition_b"]
                    )
                    .select(
                        [
                            *entity_columns,
                            pl.col(metric_col).alias("_value_b"),
                        ]
                    )
                    .drop_nulls(["_value_b"])
                )
                n_a = left.height
                n_b = right.height
                joined = left.join(
                    right,
                    on=list(entity_columns),
                    how="inner",
                )
                n_common = joined.height
                if n_common < 2:
                    pearson_r = None
                    spearman_r = None
                    share_change_quintile = None
                    median_abs_percentile_diff = None
                else:
                    compared = (
                        joined.with_columns(
                            [
                                (
                                    pl.col("_value_a").rank(
                                        method="average"
                                    )
                                    / pl.len()
                                ).alias("_rank_a"),
                                (
                                    pl.col("_value_b").rank(
                                        method="average"
                                    )
                                    / pl.len()
                                ).alias("_rank_b"),
                            ]
                        )
                        .with_columns(
                            [
                                (pl.col("_rank_a") * 5)
                                .ceil()
                                .clip(lower_bound=1, upper_bound=5)
                                .alias("_quintile_a"),
                                (pl.col("_rank_b") * 5)
                                .ceil()
                                .clip(lower_bound=1, upper_bound=5)
                                .alias("_quintile_b"),
                            ]
                        )
                    )
                    summary = compared.select(
                        [
                            pl.corr("_value_a", "_value_b").alias(
                                "pearson_r"
                            ),
                            pl.corr("_rank_a", "_rank_b").alias(
                                "spearman_r"
                            ),
                            (
                                pl.col("_quintile_a")
                                != pl.col("_quintile_b")
                            )
                            .mean()
                            .alias("share_change_quintile"),
                            (
                                pl.col("_rank_a") - pl.col("_rank_b")
                            )
                            .abs()
                            .median()
                            .alias("median_abs_percentile_diff"),
                        ]
                    ).row(0, named=True)
                    pearson_r = summary["pearson_r"]
                    spearman_r = summary["spearman_r"]
                    share_change_quintile = summary[
                        "share_change_quintile"
                    ]
                    median_abs_percentile_diff = summary[
                        "median_abs_percentile_diff"
                    ]

                rows.append(
                    {
                        "scale": scale,
                        "metric": spec["metric"],
                        "franja_v2": franja,
                        **pair,
                        "n_a": n_a,
                        "n_b": n_b,
                        "n_common": n_common,
                        "overlap_share_min": (
                            n_common / min(n_a, n_b)
                            if min(n_a, n_b) > 0
                            else None
                        ),
                        "pearson_r": pearson_r,
                        "spearman_r": spearman_r,
                        "share_change_quintile": share_change_quintile,
                        "median_abs_percentile_diff": (
                            median_abs_percentile_diff
                        ),
                    }
                )

    return pl.DataFrame(rows)


def summarize_recurrent_extremes(
    source: pl.DataFrame,
    *,
    scale: str,
    entity_columns: Sequence[str],
    metric_specs: Sequence[dict[str, str]],
    component_columns: Sequence[str],
    threshold: float = 0.005,
    top_n: int = 2,
) -> pl.DataFrame:
    parts: list[pl.DataFrame] = []
    grouping = ["partition", "franja_v2"]
    selected_columns = list(
        dict.fromkeys(
            [
                *entity_columns,
                *grouping,
                *component_columns,
            ]
        )
    )

    for spec in metric_specs:
        metric_col = spec["column"]
        metric_source = (
            source.select(selected_columns)
            .drop_nulls([metric_col])
            .with_columns(
                (
                    pl.col(metric_col)
                    .rank(method="average")
                    .over(grouping)
                    / pl.len().over(grouping)
                ).alias("within_cell_percentile")
            )
        )
        for extreme, predicate, descending in [
            (
                "Bajo",
                pl.col("within_cell_percentile") <= threshold,
                False,
            ),
            (
                "Alto",
                pl.col("within_cell_percentile") >= 1 - threshold,
                True,
            ),
        ]:
            flagged = metric_source.filter(predicate)
            recurrent = flagged.group_by(list(entity_columns)).agg(
                [
                    pl.len().alias("n_extreme_cells"),
                    pl.col("partition")
                    .n_unique()
                    .alias("n_weeks_extreme"),
                    pl.col("franja_v2")
                    .n_unique()
                    .alias("n_franjas_extreme"),
                ]
            )
            example = (
                flagged.sort(
                    "within_cell_percentile",
                    descending=descending,
                )
                .unique(
                    subset=list(entity_columns),
                    keep="first",
                    maintain_order=True,
                )
                .rename({metric_col: "example_value"})
            )
            selected = (
                recurrent.join(
                    example,
                    on=list(entity_columns),
                    how="left",
                )
                .sort(
                    ["n_extreme_cells", "within_cell_percentile"],
                    descending=[True, descending],
                )
                .head(top_n)
                .with_columns(
                    [
                        pl.lit(scale).alias("scale"),
                        pl.lit(spec["metric"]).alias("metric"),
                        pl.lit(extreme).alias("extreme"),
                        pl.lit(spec["expected"]).alias(
                            "expected_reading"
                        ),
                    ]
                )
            )
            parts.append(selected)

    if not parts:
        return pl.DataFrame()
    return pl.concat(parts, how="diagonal_relaxed")


def summarize_normalization_sensitivity(
    source: pl.DataFrame,
    *,
    scale: str,
    metric_specs: Sequence[dict[str, str]],
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for spec in metric_specs:
        raw_col = spec["raw_column"]
        normalized_col = spec["normalized_column"]
        pair = (
            source.select([raw_col, normalized_col])
            .drop_nulls()
            .with_columns(
                [
                    (
                        pl.col(raw_col).rank(method="average") / pl.len()
                    ).alias("_raw_rank"),
                    (
                        pl.col(normalized_col).rank(method="average")
                        / pl.len()
                    ).alias("_normalized_rank"),
                ]
            )
            .with_columns(
                [
                    (pl.col("_raw_rank") * 5)
                    .ceil()
                    .clip(lower_bound=1, upper_bound=5)
                    .alias("_raw_quintile"),
                    (pl.col("_normalized_rank") * 5)
                    .ceil()
                    .clip(lower_bound=1, upper_bound=5)
                    .alias("_normalized_quintile"),
                ]
            )
        )
        summary = pair.select(
            [
                pl.len().alias("n"),
                pl.corr(raw_col, normalized_col).alias("pearson_r"),
                pl.corr("_raw_rank", "_normalized_rank").alias(
                    "spearman_r"
                ),
                (
                    pl.col("_raw_rank") - pl.col("_normalized_rank")
                )
                .abs()
                .median()
                .alias("median_abs_percentile_diff"),
                (
                    pl.col("_raw_quintile")
                    != pl.col("_normalized_quintile")
                )
                .mean()
                .alias("share_change_quintile"),
            ]
        ).row(0, named=True)
        rows.append(
            {
                "scale": scale,
                "metric": spec["metric"],
                **summary,
            }
        )

    return pl.DataFrame(rows)
