from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import polars as pl


def collapse_metric_scope(
    source: pl.LazyFrame,
    *,
    metric_col: str,
    support_col: str,
    scope_columns: Sequence[str],
) -> pl.LazyFrame:
    group_columns = ["id_tarjeta", *scope_columns]
    return (
        source.drop_nulls([metric_col, support_col])
        .filter(pl.col(support_col) > 0)
        .group_by(group_columns)
        .agg(
            [
                (pl.col(metric_col) * pl.col(support_col))
                .sum()
                .alias("_weighted_sum"),
                pl.col(support_col).sum().alias("metric_support"),
            ]
        )
        .with_columns(
            (pl.col("_weighted_sum") / pl.col("metric_support")).alias(
                "metric_value"
            )
        )
        .drop("_weighted_sum")
    )


def collapse_metrics_scope(
    source: pl.LazyFrame,
    *,
    metric_specs: Sequence[dict[str, str]],
    scope_columns: Sequence[str],
) -> pl.LazyFrame:
    group_columns = ["id_tarjeta", *scope_columns]
    support_columns = list(
        dict.fromkeys(spec["support_col"] for spec in metric_specs)
    )
    weighted_aliases = {
        spec["metric_col"]: f"__weighted__{spec['metric_col']}"
        for spec in metric_specs
    }
    aggregated = source.group_by(group_columns).agg(
        [
            *[
                (
                    pl.col(spec["metric_col"])
                    * pl.col(spec["support_col"])
                )
                .fill_null(0)
                .sum()
                .alias(weighted_aliases[spec["metric_col"]])
                for spec in metric_specs
            ],
            *[
                pl.col(column).sum().alias(column)
                for column in support_columns
            ],
        ]
    )
    return aggregated.with_columns(
        [
            pl.when(pl.col(spec["support_col"]) > 0)
            .then(
                pl.col(weighted_aliases[spec["metric_col"]])
                / pl.col(spec["support_col"])
            )
            .otherwise(None)
            .alias(spec["metric_col"])
            for spec in metric_specs
        ]
    ).drop(list(weighted_aliases.values()))


def gradient_tables(
    source: pl.LazyFrame,
    *,
    scope_columns: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    groups = list(scope_columns)
    ranked = (
        source.drop_nulls(
            ["metric_value", "is_qr", "origin_zone_top1"]
        )
        .sort([*groups, "metric_value", "id_tarjeta"])
        .with_columns(
            [
                pl.col("metric_value")
                .rank(method="ordinal")
                .over(groups if groups else pl.lit(1))
                .alias("_ordinal_rank"),
                pl.len()
                .over(groups if groups else pl.lit(1))
                .alias("_scope_n"),
            ]
        )
        .with_columns(
            (
                (
                    (pl.col("_ordinal_rank") - 1)
                    * 5
                    / pl.col("_scope_n")
                ).floor()
                + 1
            )
            .cast(pl.Int8)
            .alias("quintile_order")
        )
    )
    detail_groups = [*groups, "quintile_order"]
    detail = (
        ranked.group_by(detail_groups)
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("is_qr").sum().alias("n_qr"),
                pl.col("is_qr").mean().alias("qr_share"),
                pl.col("metric_value").median().alias("metric_median"),
                pl.col("origin_zone_top1")
                .n_unique()
                .alias("n_origin_clusters"),
            ]
        )
        .sort(detail_groups)
        .collect()
        .to_pandas()
    )
    cluster = (
        ranked.group_by(
            [*detail_groups, "origin_zone_top1"]
        )
        .agg(
            [
                pl.len().alias("cluster_n"),
                pl.col("is_qr").sum().alias("cluster_qr"),
            ]
        )
        .collect()
        .to_pandas()
    )

    merge_columns = detail_groups
    cluster = cluster.merge(
        detail[merge_columns + ["n_cards", "qr_share"]],
        on=merge_columns,
        how="left",
        validate="many_to_one",
    )
    cluster["score"] = (
        cluster["cluster_qr"]
        - cluster["qr_share"] * cluster["cluster_n"]
    )
    variance = (
        cluster.groupby(merge_columns, as_index=False)
        .agg(
            n_clusters=("origin_zone_top1", "nunique"),
            score_sq_sum=("score", lambda values: np.square(values).sum()),
            n_cards=("n_cards", "first"),
        )
    )
    variance["cluster_se"] = np.where(
        variance["n_clusters"] > 1,
        np.sqrt(
            variance["n_clusters"]
            / (variance["n_clusters"] - 1)
            * variance["score_sq_sum"]
            / np.square(variance["n_cards"])
        ),
        np.nan,
    )
    detail = detail.merge(
        variance[merge_columns + ["cluster_se"]],
        on=merge_columns,
        how="left",
        validate="one_to_one",
    )
    detail["qr_share_ci_low"] = (
        detail["qr_share"] - 1.96 * detail["cluster_se"]
    ).clip(0, 1)
    detail["qr_share_ci_high"] = (
        detail["qr_share"] + 1.96 * detail["cluster_se"]
    ).clip(0, 1)
    detail["quintile"] = "Q" + detail["quintile_order"].astype(str)

    summary_rows: list[dict[str, object]] = []
    summary_groups = groups or ["_pooled"]
    summary_source = detail.copy()
    if not groups:
        summary_source["_pooled"] = "Pooled"
    for keys, frame in summary_source.groupby(
        summary_groups,
        sort=False,
        dropna=False,
    ):
        key_values = keys if isinstance(keys, tuple) else (keys,)
        frame = frame.sort_values("quintile_order")
        first = frame.iloc[0]
        last = frame.iloc[-1]
        peak = frame.loc[frame["qr_share"].idxmax()]
        trough = frame.loc[frame["qr_share"].idxmin()]
        cluster_frame = cluster
        for column, value in zip(summary_groups, key_values):
            if column != "_pooled":
                cluster_frame = cluster_frame[
                    cluster_frame[column] == value
                ]
        end_scores = cluster_frame[
            cluster_frame["quintile_order"].isin(
                [
                    first["quintile_order"],
                    last["quintile_order"],
                ]
            )
        ].copy()
        end_scores["difference_influence"] = np.where(
            end_scores["quintile_order"] == last["quintile_order"],
            end_scores["score"] / end_scores["n_cards"],
            -end_scores["score"] / end_scores["n_cards"],
        )
        cluster_influence = end_scores.groupby(
            "origin_zone_top1",
            as_index=False,
        )["difference_influence"].sum()
        n_difference_clusters = len(cluster_influence)
        difference_se = (
            np.sqrt(
                n_difference_clusters
                / (n_difference_clusters - 1)
                * np.square(
                    cluster_influence["difference_influence"]
                ).sum()
            )
            if n_difference_clusters > 1
            else np.nan
        )
        difference_pp = (
            last["qr_share"] - first["qr_share"]
        ) * 100
        row = {
            column: value
            for column, value in zip(summary_groups, key_values)
            if column != "_pooled"
        }
        row.update(
            {
                "n_cards": int(frame["n_cards"].sum()),
                "q1_qr_share": first["qr_share"],
                "q5_qr_share": last["qr_share"],
                "q5_minus_q1_pp": difference_pp,
                "q5_minus_q1_cluster_se_pp": difference_se * 100,
                "q5_minus_q1_ci_low_pp": (
                    difference_pp - 1.96 * difference_se * 100
                ),
                "q5_minus_q1_ci_high_pp": (
                    difference_pp + 1.96 * difference_se * 100
                ),
                "max_minus_min_pp": (
                    peak["qr_share"] - trough["qr_share"]
                )
                * 100,
                "peak_quintile": peak["quintile"],
                "spearman_quintile_qr": frame[
                    "quintile_order"
                ].corr(frame["qr_share"], method="spearman"),
                "q1_cluster_se_pp": first["cluster_se"] * 100,
                "q5_cluster_se_pp": last["cluster_se"] * 100,
            }
        )
        summary_rows.append(row)

    return detail, pd.DataFrame(summary_rows)
