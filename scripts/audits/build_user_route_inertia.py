from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

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
SERVICE_COLS = [f"srv_{i}" for i in STAGES]
STOP_COLS = [
    col
    for i in STAGES
    for col in (f"paradero_subida_{i}", f"paradero_bajada_{i}")
]


@dataclass
class WeekParts:
    base: pl.DataFrame
    od_counts: pl.DataFrame
    coarse_counts: pl.DataFrame
    service_counts: pl.DataFrame
    stop_service_counts: pl.DataFrame | None
    od_service_counts: pl.DataFrame
    coarse_year_counts: pl.DataFrame
    service_year_counts: pl.DataFrame
    sequential: pl.DataFrame


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_route_inertia_{scope}.parquet"


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def validate_inputs(scope: str, weeks: list[str]) -> None:
    if scope not in SCOPE_WEEKS:
        raise ValueError(f"Scope no soportado: {scope}")
    missing = [str(PROCESSED_TRIPS_BY_WEEK[w]) for w in weeks if not PROCESSED_TRIPS_BY_WEEK[w].exists()]
    if missing:
        raise FileNotFoundError(f"Faltan viajes procesados: {missing}")


def route_pattern(cols: list[str], separator: str) -> pl.Expr:
    return pl.concat_str(
        [pl.col(c).cast(pl.Utf8, strict=False).fill_null("NA") for c in cols],
        separator=separator,
    )


def empty_counts(keys: list[str]) -> pl.DataFrame:
    schema = {k: pl.Utf8 for k in keys}
    schema["n_route_trips"] = pl.UInt32
    return pl.DataFrame(schema=schema)


def load_week_lf(week: str, *, include_stop_service: bool) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema = set(lf.collect_schema().names())
    required = {
        "id_tarjeta",
        "id_viaje",
        "tiempo_inicio_viaje",
        "iso_year",
        "zona_inicio_viaje",
        "zona_fin_viaje",
        *MODE_COLS,
        *SERVICE_COLS,
    }
    missing = sorted(required - schema)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    optional_stop_cols = [c for c in STOP_COLS if c in schema] if include_stop_service else []
    select_exprs: list[pl.Expr] = [
        pl.col("id_tarjeta").cast(pl.Utf8),
        pl.col("id_viaje").cast(pl.Utf8),
        pl.col("tiempo_inicio_viaje"),
        pl.col("iso_year").cast(pl.Int16, strict=False).alias("trip_year"),
        pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False),
        pl.col("zona_fin_viaje").cast(pl.Int64, strict=False),
        *[pl.col(c).cast(pl.Utf8, strict=False) for c in MODE_COLS],
        *[pl.col(c).cast(pl.Utf8, strict=False) for c in SERVICE_COLS],
        *[pl.col(c).cast(pl.Utf8, strict=False) for c in optional_stop_cols],
    ]

    lf = (
        lf.select(select_exprs)
        .drop_nulls(["id_tarjeta", "tiempo_inicio_viaje"])
        .with_columns(pl.lit(week).alias("partition"))
    )

    if include_stop_service:
        for c in STOP_COLS:
            if c not in optional_stop_cols:
                lf = lf.with_columns(pl.lit(None, dtype=pl.Utf8).alias(c))

    route_exprs: list[pl.Expr] = [
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
        .alias("od_pair"),
        route_pattern(MODE_COLS, "-").alias("mode_pattern"),
        route_pattern(SERVICE_COLS, "-").alias("service_pattern"),
    ]
    if include_stop_service:
        route_exprs.append(route_pattern(STOP_COLS, "-").alias("stop_pattern"))
    else:
        route_exprs.append(pl.lit(None, dtype=pl.Utf8).alias("stop_pattern"))

    return (
        lf.with_columns(route_exprs)
        .with_columns(
            [
                pl.when(pl.col("od_pair").is_not_null())
                .then(pl.concat_str(["od_pair", "mode_pattern"], separator="__M__"))
                .otherwise(None)
                .alias("coarse_route"),
                pl.when(pl.col("od_pair").is_not_null())
                .then(pl.concat_str(["od_pair", "mode_pattern", "service_pattern"], separator="__S__"))
                .otherwise(None)
                .alias("service_route"),
                pl.when(pl.col("od_pair").is_not_null() & pl.col("stop_pattern").is_not_null())
                .then(
                    pl.concat_str(
                        ["od_pair", "mode_pattern", "service_pattern", "stop_pattern"],
                        separator="__P__",
                    )
                )
                .otherwise(None)
                .alias("stop_service_route"),
            ]
        )
        .select(
            [
                "partition",
                "id_tarjeta",
                "id_viaje",
                "tiempo_inicio_viaje",
                "trip_year",
                "od_pair",
                "coarse_route",
                "service_route",
                "stop_service_route",
            ]
        )
    )


def count_by(lf: pl.LazyFrame, keys: list[str]) -> pl.DataFrame:
    return collect_streaming(
        lf.filter(pl.all_horizontal([pl.col(k).is_not_null() for k in keys]))
        .group_by(keys)
        .agg(pl.len().alias("n_route_trips"))
    )


def sequential_features_for_week(lf: pl.LazyFrame) -> pl.DataFrame:
    ordered = (
        lf.sort(["id_tarjeta", "tiempo_inicio_viaje", "id_viaje"])
        .with_columns(
            [
                pl.col("od_pair").shift(1).over("id_tarjeta").alias("prev_od_pair"),
                pl.col("coarse_route").shift(1).over("id_tarjeta").alias("prev_coarse_route"),
                pl.col("service_route").shift(1).over("id_tarjeta").alias("prev_service_route"),
                pl.col("stop_service_route").shift(1).over("id_tarjeta").alias("prev_stop_service_route"),
            ]
        )
    )
    same_od = pl.col("od_pair") == pl.col("prev_od_pair")
    same_coarse = pl.col("coarse_route") == pl.col("prev_coarse_route")
    same_service = pl.col("service_route") == pl.col("prev_service_route")
    same_stop_service = pl.col("stop_service_route") == pl.col("prev_stop_service_route")
    valid_prev_od = pl.col("prev_od_pair").is_not_null() & pl.col("od_pair").is_not_null()
    valid_prev_service = pl.col("prev_service_route").is_not_null() & pl.col("service_route").is_not_null()
    valid_prev_stop_service = (
        pl.col("prev_stop_service_route").is_not_null() & pl.col("stop_service_route").is_not_null()
    )
    valid_same_od_service = valid_prev_service & same_od

    return collect_streaming(
        ordered.group_by("id_tarjeta").agg(
            [
                valid_prev_od.sum().alias("n_prev_od_comparisons"),
                (valid_prev_od & same_od).sum().alias("same_od_as_prev_n"),
                valid_prev_service.sum().alias("n_prev_service_comparisons"),
                (valid_prev_service & same_coarse).sum().alias("coarse_same_as_prev_n"),
                (valid_prev_service & same_service).sum().alias("service_same_as_prev_n"),
                valid_prev_stop_service.sum().alias("n_prev_stop_service_comparisons"),
                (valid_prev_stop_service & same_stop_service).sum().alias("stop_service_same_as_prev_n"),
                valid_same_od_service.sum().alias("n_same_od_service_comparisons"),
                (valid_same_od_service & same_service).sum().alias("same_od_service_same_as_prev_n"),
            ]
        )
    )


def aggregate_week(week: str, *, include_stop_service: bool) -> WeekParts:
    lf = load_week_lf(week, include_stop_service=include_stop_service)
    base = collect_streaming(
        lf.group_by("id_tarjeta").agg(
            [
                pl.len().alias("route_n_trips"),
                pl.col("od_pair").is_null().sum().alias("route_od_missing_n"),
                pl.col("service_route").is_null().sum().alias("service_route_missing_n"),
                (pl.col("trip_year") == 2024).sum().alias("route_n_trips_2024"),
                (pl.col("trip_year") == 2025).sum().alias("route_n_trips_2025"),
            ]
        )
    )
    stop_counts = (
        count_by(lf, ["id_tarjeta", "stop_service_route"])
        if include_stop_service
        else None
    )
    return WeekParts(
        base=base,
        od_counts=count_by(lf, ["id_tarjeta", "od_pair"]),
        coarse_counts=count_by(lf, ["id_tarjeta", "coarse_route"]),
        service_counts=count_by(lf, ["id_tarjeta", "service_route"]),
        stop_service_counts=stop_counts,
        od_service_counts=count_by(lf, ["id_tarjeta", "od_pair", "service_route"]),
        coarse_year_counts=count_by(lf, ["id_tarjeta", "trip_year", "coarse_route"]),
        service_year_counts=count_by(lf, ["id_tarjeta", "trip_year", "service_route"]),
        sequential=sequential_features_for_week(lf),
    )


def concat_or_empty(frames: list[pl.DataFrame], keys: list[str]) -> pl.DataFrame:
    non_empty = [df for df in frames if df is not None and not df.is_empty()]
    if not non_empty:
        return empty_counts(keys)
    return pl.concat(non_empty, how="diagonal_relaxed")


def combine_count_frames(frames: list[pl.DataFrame], keys: list[str]) -> pl.DataFrame:
    stacked = concat_or_empty(frames, keys)
    if stacked.is_empty():
        return stacked
    return stacked.group_by(keys).agg(pl.col("n_route_trips").sum().alias("n_route_trips"))


def combine_base(frames: list[pl.DataFrame]) -> pl.DataFrame:
    return (
        pl.concat(frames, how="diagonal_relaxed")
        .group_by("id_tarjeta")
        .agg(
            [
                pl.col("route_n_trips").sum().alias("route_n_trips"),
                pl.col("route_od_missing_n").sum().alias("route_od_missing_n"),
                pl.col("service_route_missing_n").sum().alias("service_route_missing_n"),
                pl.col("route_n_trips_2024").sum().alias("route_n_trips_2024"),
                pl.col("route_n_trips_2025").sum().alias("route_n_trips_2025"),
            ]
        )
        .with_columns(
            [
                (pl.col("route_od_missing_n") / pl.col("route_n_trips")).alias("route_od_missing_rate"),
                (pl.col("service_route_missing_n") / pl.col("route_n_trips")).alias("service_route_missing_rate"),
                (
                    (pl.col("route_n_trips_2024") > 0).cast(pl.Int8)
                    + (pl.col("route_n_trips_2025") > 0).cast(pl.Int8)
                ).alias("route_n_years_observed"),
            ]
        )
    )


def distribution_features_from_counts(counts: pl.DataFrame, prefix: str) -> pl.DataFrame:
    if counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    totals = counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_route_trips").sum().alias(f"{prefix}_n_valid_trips"),
            pl.len().alias(f"{prefix}_n_unique"),
        ]
    )
    entropy = (
        counts.join(totals.select(["id_tarjeta", f"{prefix}_n_valid_trips"]), on="id_tarjeta")
        .with_columns((pl.col("n_route_trips") / pl.col(f"{prefix}_n_valid_trips")).alias("p_route"))
        .with_columns((-(pl.col("p_route") * pl.col("p_route").log())).alias("entropy_part"))
        .group_by("id_tarjeta")
        .agg(
            [
                pl.col("entropy_part").sum().alias(f"{prefix}_entropy"),
                pl.col("p_route").max().alias(f"{prefix}_top1_share"),
            ]
        )
    )
    return (
        totals.join(entropy, on="id_tarjeta", how="left")
        .with_columns(
            pl.when(pl.col(f"{prefix}_n_unique") > 1)
            .then(pl.col(f"{prefix}_entropy") / pl.col(f"{prefix}_n_unique").cast(pl.Float64).log())
            .otherwise(0.0)
            .alias(f"{prefix}_entropy_norm")
        )
    )


def top_od_service_features_from_counts(od_counts: pl.DataFrame, od_service_counts: pl.DataFrame) -> pl.DataFrame:
    if od_counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    top_od = (
        od_counts.sort(["id_tarjeta", "n_route_trips", "od_pair"], descending=[False, True, False])
        .with_columns((pl.int_range(pl.len()).over("id_tarjeta") + 1).alias("rank"))
        .filter(pl.col("rank") == 1)
        .select(
            [
                "id_tarjeta",
                pl.col("od_pair").alias("top_od_pair"),
                pl.col("n_route_trips").alias("top_od_n_trips"),
            ]
        )
    )
    total_od = od_counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_route_trips").sum().alias("od_n_valid_trips"),
            pl.len().alias("od_n_unique"),
        ]
    )
    top_od = top_od.join(total_od, on="id_tarjeta", how="left").with_columns(
        (pl.col("top_od_n_trips") / pl.col("od_n_valid_trips")).alias("top_od_share")
    )
    if od_service_counts.is_empty():
        return top_od

    top_route_counts = (
        od_service_counts.join(top_od.select(["id_tarjeta", "top_od_pair"]), on="id_tarjeta", how="inner")
        .filter(pl.col("od_pair") == pl.col("top_od_pair"))
        .select(["id_tarjeta", "service_route", "n_route_trips"])
    )
    route_features = distribution_features_from_counts(top_route_counts, "top_od_service")
    return top_od.join(route_features, on="id_tarjeta", how="left")


def within_od_route_features_from_counts(od_service_counts: pl.DataFrame) -> pl.DataFrame:
    if od_service_counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    od_totals = od_service_counts.group_by(["id_tarjeta", "od_pair"]).agg(
        [
            pl.col("n_route_trips").sum().alias("n_od_trips"),
            pl.len().alias("n_service_routes_od"),
            pl.col("n_route_trips").max().alias("top_route_n_od"),
        ]
    )
    return (
        od_totals.with_columns(
            [
                (pl.col("top_route_n_od") / pl.col("n_od_trips")).alias("od_top_route_share"),
                (pl.col("n_service_routes_od") > 1).cast(pl.Int8).alias("od_has_multi_route"),
            ]
        )
        .group_by("id_tarjeta")
        .agg(
            [
                (
                    (pl.col("od_top_route_share") * pl.col("n_od_trips")).sum()
                    / pl.col("n_od_trips").sum()
                ).alias("service_within_od_top_share_weighted"),
                (
                    (pl.col("od_has_multi_route") * pl.col("n_od_trips")).sum()
                    / pl.col("n_od_trips").sum()
                ).alias("share_trips_in_multi_route_od"),
            ]
        )
        .with_columns(
            (1 - pl.col("service_within_od_top_share_weighted")).alias(
                "service_within_od_variability_weighted"
            )
        )
    )


def combine_sequential(frames: list[pl.DataFrame]) -> pl.DataFrame:
    numeric_cols = [c for c in frames[0].columns if c != "id_tarjeta"]
    out = (
        pl.concat(frames, how="diagonal_relaxed")
        .group_by("id_tarjeta")
        .agg([pl.col(c).sum().alias(c) for c in numeric_cols])
    )

    def ratio(num: str, den: str, out_col: str) -> pl.Expr:
        return (
            pl.when(pl.col(den) > 0)
            .then(pl.col(num) / pl.col(den))
            .otherwise(None)
            .alias(out_col)
        )

    return out.with_columns(
        [
            ratio("same_od_as_prev_n", "n_prev_od_comparisons", "same_od_as_prev_share"),
            ratio("coarse_same_as_prev_n", "n_prev_service_comparisons", "coarse_same_as_prev_share"),
            ratio("service_same_as_prev_n", "n_prev_service_comparisons", "service_same_as_prev_share"),
            ratio(
                "stop_service_same_as_prev_n",
                "n_prev_stop_service_comparisons",
                "stop_service_same_as_prev_share",
            ),
            ratio(
                "same_od_service_same_as_prev_n",
                "n_same_od_service_comparisons",
                "same_od_service_same_as_prev_share",
            ),
        ]
    ).with_columns(
        (1 - pl.col("same_od_service_same_as_prev_share")).alias("same_od_service_switch_as_prev_share")
    )


def rcs_features_from_counts(counts: pl.DataFrame, sig_col: str, prefix: str) -> pl.DataFrame:
    if counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    totals = counts.group_by(["id_tarjeta", "trip_year"]).agg(
        pl.col("n_route_trips").sum().alias("n_year_route_trips")
    )
    props = counts.join(totals, on=["id_tarjeta", "trip_year"]).with_columns(
        (pl.col("n_route_trips") / pl.col("n_year_route_trips")).alias("p_route")
    )
    p2024 = (
        props.filter(pl.col("trip_year") == 2024)
        .select(["id_tarjeta", sig_col, pl.col("p_route").alias("p2024")])
    )
    p2025 = (
        props.filter(pl.col("trip_year") == 2025)
        .select(["id_tarjeta", sig_col, pl.col("p_route").alias("p2025")])
    )
    year_presence = totals.group_by("id_tarjeta").agg(
        [
            (pl.col("trip_year") == 2024).any().alias("has_routes_2024"),
            (pl.col("trip_year") == 2025).any().alias("has_routes_2025"),
        ]
    )
    return (
        p2024.join(p2025, on=["id_tarjeta", sig_col], how="full", coalesce=True)
        .with_columns([pl.col("p2024").fill_null(0.0), pl.col("p2025").fill_null(0.0)])
        .group_by("id_tarjeta")
        .agg(
            [
                (1 - 0.5 * (pl.col("p2024") - pl.col("p2025")).abs().sum()).alias(
                    f"{prefix}_rcs_2024_2025"
                ),
                (pl.col("p2024") - pl.col("p2025")).abs().sum().alias(f"{prefix}_l1_2024_2025"),
            ]
        )
        .join(year_presence, on="id_tarjeta", how="left")
        .with_columns(
            [
                pl.when(pl.col("has_routes_2024") & pl.col("has_routes_2025"))
                .then(pl.col(f"{prefix}_rcs_2024_2025"))
                .otherwise(None)
                .alias(f"{prefix}_rcs_2024_2025"),
                pl.when(pl.col("has_routes_2024") & pl.col("has_routes_2025"))
                .then(pl.col(f"{prefix}_l1_2024_2025"))
                .otherwise(None)
                .alias(f"{prefix}_l1_2024_2025"),
            ]
        )
        .drop(["has_routes_2024", "has_routes_2025"])
    )


def early_late_rcs_features_from_counts(
    counts: pl.DataFrame,
    sig_col: str,
    prefix: str,
    *,
    min_trips_per_half: int,
) -> pl.DataFrame:
    if counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})

    totals = counts.group_by(["id_tarjeta", "period_half"]).agg(
        pl.col("n_route_trips").sum().alias("n_half_route_trips")
    )
    props = counts.join(totals, on=["id_tarjeta", "period_half"]).with_columns(
        (pl.col("n_route_trips") / pl.col("n_half_route_trips")).alias("p_route")
    )
    early = (
        props.filter(pl.col("period_half") == "early")
        .select(["id_tarjeta", sig_col, pl.col("p_route").alias("p_early")])
    )
    late = (
        props.filter(pl.col("period_half") == "late")
        .select(["id_tarjeta", sig_col, pl.col("p_route").alias("p_late")])
    )
    half_presence = totals.group_by("id_tarjeta").agg(
        [
            pl.when(pl.col("period_half") == "early")
            .then(pl.col("n_half_route_trips"))
            .otherwise(0)
            .sum()
            .alias(f"{prefix}_early_n_trips"),
            pl.when(pl.col("period_half") == "late")
            .then(pl.col("n_half_route_trips"))
            .otherwise(0)
            .sum()
            .alias(f"{prefix}_late_n_trips"),
        ]
    )

    valid_expr = (
        (pl.col(f"{prefix}_early_n_trips") >= min_trips_per_half)
        & (pl.col(f"{prefix}_late_n_trips") >= min_trips_per_half)
    )

    return (
        early.join(late, on=["id_tarjeta", sig_col], how="full", coalesce=True)
        .with_columns([pl.col("p_early").fill_null(0.0), pl.col("p_late").fill_null(0.0)])
        .group_by("id_tarjeta")
        .agg(
            [
                (1 - 0.5 * (pl.col("p_early") - pl.col("p_late")).abs().sum()).alias(
                    f"{prefix}_early_late_rcs"
                ),
                (pl.col("p_early") - pl.col("p_late")).abs().sum().alias(f"{prefix}_early_late_l1"),
            ]
        )
        .join(half_presence, on="id_tarjeta", how="left")
        .with_columns(
            [
                valid_expr.cast(pl.Int8).alias(f"{prefix}_has_early_late_rcs"),
                pl.when(valid_expr)
                .then(pl.col(f"{prefix}_early_late_rcs"))
                .otherwise(None)
                .alias(f"{prefix}_early_late_rcs"),
                pl.when(valid_expr)
                .then(pl.col(f"{prefix}_early_late_l1"))
                .otherwise(None)
                .alias(f"{prefix}_early_late_l1"),
            ]
        )
    )


def combine_incremental_counts(
    acc: pl.DataFrame | None,
    counts: pl.DataFrame,
    keys: list[str],
) -> pl.DataFrame:
    if acc is None or acc.is_empty():
        return counts
    if counts.is_empty():
        return acc
    return (
        pl.concat([acc, counts], how="diagonal_relaxed")
        .group_by(keys)
        .agg(pl.col("n_route_trips").sum().alias("n_route_trips"))
    )


def early_late_counts_for_scope(
    weeks: list[str],
    totals: pl.DataFrame,
    sig_col: str,
    *,
    include_stop_service: bool,
) -> pl.DataFrame:
    offsets = totals.select("id_tarjeta").with_columns(pl.lit(0, dtype=pl.UInt32).alias("n_seen_before"))
    totals = totals.select(["id_tarjeta", "route_n_trips"])
    acc: pl.DataFrame | None = None
    keys = ["id_tarjeta", "period_half", sig_col]

    for week in weeks:
        print(f"Calculando early/late {sig_col} {week}...", flush=True)
        lf = load_week_lf(week, include_stop_service=include_stop_service)
        week_seen = collect_streaming(
            lf.group_by("id_tarjeta").agg(pl.len().cast(pl.UInt32).alias("n_week_trips"))
        )
        with_period = (
            lf.sort(["id_tarjeta", "tiempo_inicio_viaje", "id_viaje"])
            .with_columns((pl.int_range(pl.len()).over("id_tarjeta") + 1).alias("seq_in_week"))
            .join(offsets.lazy(), on="id_tarjeta", how="left")
            .join(totals.lazy(), on="id_tarjeta", how="left")
            .with_columns(
                [
                    pl.col("n_seen_before").fill_null(0),
                    (pl.col("n_seen_before") + pl.col("seq_in_week")).alias("global_seq"),
                ]
            )
            .with_columns(
                pl.when(pl.col("global_seq") <= (pl.col("route_n_trips") / 2).ceil())
                .then(pl.lit("early"))
                .otherwise(pl.lit("late"))
                .alias("period_half")
            )
        )
        counts = collect_streaming(
            with_period.filter(pl.col(sig_col).is_not_null())
            .group_by(keys)
            .agg(pl.len().cast(pl.UInt32).alias("n_route_trips"))
        )
        acc = combine_incremental_counts(acc, counts, keys)
        offsets = (
            offsets.join(week_seen, on="id_tarjeta", how="left")
            .with_columns(
                (pl.col("n_seen_before") + pl.col("n_week_trips").fill_null(0))
                .cast(pl.UInt32)
                .alias("n_seen_before")
            )
            .select(["id_tarjeta", "n_seen_before"])
        )

    return acc if acc is not None else empty_counts(keys)


def add_null_stop_service_columns(out: pl.DataFrame) -> pl.DataFrame:
    null_cols = {
        "stop_service_route_n_valid_trips": pl.UInt32,
        "stop_service_route_n_unique": pl.UInt32,
        "stop_service_route_entropy": pl.Float64,
        "stop_service_route_top1_share": pl.Float64,
        "stop_service_route_entropy_norm": pl.Float64,
    }
    for col, dtype in null_cols.items():
        if col not in out.columns:
            out = out.with_columns(pl.lit(None, dtype=dtype).alias(col))
    return out


def build_route_inertia(scope: str, weeks: list[str], *, include_stop_service: bool) -> pl.DataFrame:
    week_parts: list[WeekParts] = []
    for week in weeks:
        print(f"Procesando {week}...", flush=True)
        week_parts.append(aggregate_week(week, include_stop_service=include_stop_service))

    base = combine_base([p.base for p in week_parts])
    od_counts = combine_count_frames([p.od_counts for p in week_parts], ["id_tarjeta", "od_pair"])
    coarse_counts = combine_count_frames([p.coarse_counts for p in week_parts], ["id_tarjeta", "coarse_route"])
    service_counts = combine_count_frames([p.service_counts for p in week_parts], ["id_tarjeta", "service_route"])
    stop_counts = (
        combine_count_frames(
            [p.stop_service_counts for p in week_parts if p.stop_service_counts is not None],
            ["id_tarjeta", "stop_service_route"],
        )
        if include_stop_service
        else pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    )
    od_service_counts = combine_count_frames(
        [p.od_service_counts for p in week_parts],
        ["id_tarjeta", "od_pair", "service_route"],
    )
    coarse_year_counts = combine_count_frames(
        [p.coarse_year_counts for p in week_parts],
        ["id_tarjeta", "trip_year", "coarse_route"],
    )
    service_year_counts = combine_count_frames(
        [p.service_year_counts for p in week_parts],
        ["id_tarjeta", "trip_year", "service_route"],
    )

    parts = [
        base,
        distribution_features_from_counts(od_counts, "od_pair"),
        distribution_features_from_counts(coarse_counts, "coarse_route"),
        distribution_features_from_counts(service_counts, "service_route"),
        distribution_features_from_counts(stop_counts, "stop_service_route") if include_stop_service else None,
        top_od_service_features_from_counts(od_counts, od_service_counts),
        within_od_route_features_from_counts(od_service_counts),
        combine_sequential([p.sequential for p in week_parts]),
        rcs_features_from_counts(coarse_year_counts, "coarse_route", "coarse_route"),
        rcs_features_from_counts(service_year_counts, "service_route", "service_route"),
    ]
    del (
        week_parts,
        od_counts,
        coarse_counts,
        service_counts,
        stop_counts,
        od_service_counts,
        coarse_year_counts,
        service_year_counts,
    )

    coarse_half_counts = early_late_counts_for_scope(
        weeks,
        base.select(["id_tarjeta", "route_n_trips"]),
        "coarse_route",
        include_stop_service=include_stop_service,
    )
    parts.append(
        early_late_rcs_features_from_counts(
            coarse_half_counts,
            "coarse_route",
            "coarse_route",
            min_trips_per_half=3,
        )
    )
    del coarse_half_counts

    service_half_counts = early_late_counts_for_scope(
        weeks,
        base.select(["id_tarjeta", "route_n_trips"]),
        "service_route",
        include_stop_service=include_stop_service,
    )
    parts.append(
        early_late_rcs_features_from_counts(
            service_half_counts,
            "service_route",
            "service_route",
            min_trips_per_half=3,
        )
    )
    del service_half_counts

    out = parts[0]
    for part in parts[1:]:
        if part is not None:
            out = out.join(part, on="id_tarjeta", how="left")

    out = add_null_stop_service_columns(out).sort("id_tarjeta")
    if out["id_tarjeta"].n_unique() != out.height:
        raise ValueError("Salida no es unica por id_tarjeta")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Construye variables de inercia de ruta por id_tarjeta.")
    parser.add_argument("--scope", default="interannual_ml", choices=sorted(SCOPE_WEEKS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--include-stop-service",
        action="store_true",
        help="Incluye firma paradero-servicio. Es mucho mas costosa en memoria; por defecto se omite.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weeks = SCOPE_WEEKS[args.scope]
    validate_inputs(args.scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = output_path(args.scope)
    if out_path.exists() and not args.force:
        raise FileExistsError(f"Ya existe {out_path}. Usa --force para sobrescribir.")

    df = build_route_inertia(args.scope, weeks, include_stop_service=args.include_stop_service)
    df.write_parquet(out_path)
    print(f"OK: {out_path}")
    print(f"rows={df.height:,} cols={len(df.columns):,}")
    if not args.include_stop_service:
        print("Nota: stop_service_route_* queda nulo. Usa --include-stop-service solo como sensibilidad pesada.")


if __name__ == "__main__":
    main()
