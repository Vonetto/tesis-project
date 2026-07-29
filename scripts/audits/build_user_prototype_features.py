from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"


PROTOTYPE_COMPONENTS: dict[str, list[tuple[str, int]]] = {
    "proto_commuter_peak_score": [
        ("routine_commute_like_score", 1),
        ("routine_lab_peak_share", 1),
        ("tour_peak_anchor_day_share", 1),
        ("tour_workday_commute_like_day_share", 1),
        ("tour_first_trip_lab_am_peak_share", 1),
        ("tour_last_trip_lab_pm_peak_share", 1),
    ],
    "proto_late_return_score": [
        ("tour_last_trip_hour_mean", 1),
        ("tour_day_span_hours_mean", 1),
        ("tour_day_span_hours_median", 1),
        ("tour_last_trip_lab_pm_peak_share", 1),
        ("tour_peak_anchor_day_share", 1),
    ],
    "proto_low_complexity_score": [
        ("tour_two_trip_day_share", 1),
        ("tour_three_plus_trip_day_share", -1),
        ("tour_complex_day_share", -1),
        ("tour_distinct_zones_per_day_mean", -1),
        ("tour_distinct_unordered_od_per_day_mean", -1),
        ("routine_od_n_unique", -1),
        ("routine_zone_n_unique", -1),
    ],
    "proto_explorer_score": [
        ("routine_zone_n_unique", 1),
        ("routine_od_n_unique", 1),
        ("routine_combo_n_unique", 1),
        ("routine_od_entropy_norm", 1),
        ("tour_distinct_zones_per_day_mean", 1),
        ("tour_distinct_unordered_od_per_day_mean", 1),
        ("tour_complex_day_share", 1),
    ],
    "proto_routine_repeater_score": [
        ("routine_combo_top1_share", 1),
        ("routine_combo_hhi", 1),
        ("routine_od_top1_share", 1),
        ("routine_od_hhi", 1),
        ("routine_main_od_share", 1),
        ("routine_combo_entropy_norm", -1),
        ("routine_od_n_unique", -1),
    ],
    "proto_multimodal_score": [
        ("tour_mixed_mode_day_share", 1),
        ("tour_distinct_modes_per_day_mean", 1),
        ("tour_mode_consistent_day_share", -1),
    ],
}

PROTOTYPE_FEATURES = list(PROTOTYPE_COMPONENTS)


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def routine_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_routine_features_{scope}.parquet"


def daily_tour_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_daily_tour_features_{scope}.parquet"


def rhythm_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_rhythm_features_{scope}.parquet"


def panel_path(scope: str, variant: str = "clean") -> Path:
    return OUT_DIR / f"user_level_payment_panel_{scope}_{variant}.parquet"


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_behavior_prototype_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_behavior_prototype_features_{stem}_{scope}.csv"


def assert_exists(paths: list[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Faltan artifacts requeridos para prototype_pack: {missing}")


def check_unique_key(path: Path, key: str) -> None:
    df = collect_streaming(
        pl.scan_parquet(path).select(
            [
                pl.len().alias("n_rows"),
                pl.col(key).n_unique().alias("n_unique"),
            ]
        )
    )
    n_rows = int(df["n_rows"][0])
    n_unique = int(df["n_unique"][0])
    if n_rows != n_unique:
        raise ValueError(f"{path.name}: {key} no es unico ({n_unique} de {n_rows})")


def required_components() -> list[str]:
    return list(dict.fromkeys(c for components in PROTOTYPE_COMPONENTS.values() for c, _ in components))


def percentile_expr(col: str, sign: int) -> pl.Expr:
    n = pl.col(col).is_not_null().sum()
    denom = pl.when(n <= 1).then(None).otherwise(n - 1)
    percentile = (
        pl.when(pl.col(col).is_null())
        .then(None)
        .otherwise((pl.col(col).rank("average") - 1.0) / denom)
    )
    if sign < 0:
        return 1.0 - percentile
    return percentile


def score_component_alias(score: str, col: str) -> str:
    return f"__{score}__{col}__pct"


def build_input_lf(scope: str) -> pl.LazyFrame:
    paths = [routine_path(scope), daily_tour_path(scope), rhythm_path(scope)]
    assert_exists(paths)
    for path in paths:
        check_unique_key(path, "id_tarjeta")

    required = required_components()
    source_paths = {
        "routine": routine_path(scope),
        "daily_tour": daily_tour_path(scope),
        "rhythm": rhythm_path(scope),
    }
    schemas = {
        source: set(pl.scan_parquet(path).collect_schema().names())
        for source, path in source_paths.items()
    }
    available = set().union(*schemas.values())
    missing = sorted(set(required) - available)
    if missing:
        raise ValueError(f"Faltan componentes para prototype_pack: {missing}")

    ids = pl.concat(
        [pl.scan_parquet(path).select("id_tarjeta") for path in paths],
        how="diagonal_relaxed",
    ).unique()

    lf = ids
    for source, path in source_paths.items():
        cols = ["id_tarjeta", *[c for c in required if c in schemas[source]]]
        lf = lf.join(pl.scan_parquet(path).select(cols), on="id_tarjeta", how="left")

    return lf.with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in required])


def build_prototype_features(scope: str) -> pl.DataFrame:
    lf = build_input_lf(scope)
    component_exprs = []
    score_exprs = []
    count_exprs = []

    for score, components in PROTOTYPE_COMPONENTS.items():
        aliases = []
        for col, sign in components:
            alias = score_component_alias(score, col)
            component_exprs.append(percentile_expr(col, sign).alias(alias))
            aliases.append(alias)

        score_exprs.append(pl.mean_horizontal([pl.col(a) for a in aliases]).alias(score))
        count_exprs.append(
            pl.sum_horizontal([pl.col(a).is_not_null().cast(pl.Int16) for a in aliases]).alias(
                f"{score}__n_components"
            )
        )

    return (
        lf.with_columns(component_exprs)
        .with_columns(score_exprs + count_exprs)
        .select(["id_tarjeta", *PROTOTYPE_FEATURES, *[f"{s}__n_components" for s in PROTOTYPE_FEATURES]])
        .collect()
    )


def write_audits(features: pl.DataFrame, scope: str) -> None:
    summary = features.select(
        [
            pl.len().alias("n_cards"),
            *[pl.col(c).mean().alias(f"{c}__mean") for c in PROTOTYPE_FEATURES],
            *[pl.col(c).is_null().mean().alias(f"{c}__missing") for c in PROTOTYPE_FEATURES],
        ]
    )
    summary.write_csv(audit_path(scope, "summary"))

    rows = []
    for score, components in PROTOTYPE_COMPONENTS.items():
        for component, sign in components:
            rows.append({"score": score, "component": component, "sign": sign})
    pl.DataFrame(rows).write_csv(audit_path(scope, "components"))

    panel = panel_path(scope)
    if panel.exists():
        by_target = (
            features.join(
                pl.read_parquet(panel, columns=["id_tarjeta", "tipo_tarjeta", "n_viajes"]),
                on="id_tarjeta",
                how="inner",
            )
            .group_by("tipo_tarjeta")
            .agg(
                [
                    pl.len().alias("n_cards"),
                    pl.col("n_viajes").sum().alias("n_trips"),
                    *[pl.col(c).mean().alias(f"{c}__mean") for c in PROTOTYPE_FEATURES],
                    *[pl.col(c).median().alias(f"{c}__median") for c in PROTOTYPE_FEATURES],
                ]
            )
        )
        by_target.write_csv(audit_path(scope, "by_target"))


def build_user_prototype_features(scope: str, *, force: bool) -> Path:
    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Construyendo prototype_pack scope={scope}")
    features = build_prototype_features(scope)
    check_df = features.select(
        [
            pl.len().alias("n_rows"),
            pl.col("id_tarjeta").n_unique().alias("n_unique"),
        ]
    )
    if int(check_df["n_rows"][0]) != int(check_df["n_unique"][0]):
        raise ValueError("prototype_pack: id_tarjeta no es unico")

    features.write_parquet(out_path, compression="zstd")
    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={features.width:,}")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic prototype user-level features.")
    parser.add_argument("--scope", default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_user_prototype_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
