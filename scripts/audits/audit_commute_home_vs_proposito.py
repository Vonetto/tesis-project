from __future__ import annotations

import argparse
import json
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PK_BRIDGE_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "pk_bridge"
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "commute_home"


def bridge_path(scope: str) -> Path:
    return PK_BRIDGE_DIR / f"processed_trip_proposito_bridge_{scope}.parquet"


def proposito_home_path(scope: str) -> Path:
    return PK_BRIDGE_DIR / f"user_home_candidates_{scope}.parquet"


def output_suffix(args: argparse.Namespace) -> str:
    default_windows = (
        args.morning_start == 5
        and args.morning_end == 12
        and args.afternoon_start == 15
        and args.afternoon_end == 22
    )
    if default_windows and not args.weekday_only:
        return args.scope
    weekday = "_weekday" if args.weekday_only else ""
    return (
        f"{args.scope}_am{args.morning_start:02d}-{args.morning_end:02d}"
        f"_pm{args.afternoon_start:02d}-{args.afternoon_end:02d}{weekday}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audita una residencia alternativa por patrón AM/PM y la compara "
            "contra zona_hogar inferida desde proposito == HOGAR."
        )
    )
    parser.add_argument("--scope", choices=["active", "ml_2025", "active_ml"], default="ml_2025")
    parser.add_argument("--morning-start", type=int, default=5, help="Hora inicial inclusiva AM.")
    parser.add_argument("--morning-end", type=int, default=12, help="Hora final exclusiva AM.")
    parser.add_argument("--afternoon-start", type=int, default=15, help="Hora inicial inclusiva PM.")
    parser.add_argument("--afternoon-end", type=int, default=22, help="Hora final exclusiva PM.")
    parser.add_argument(
        "--weekday-only",
        action="store_true",
        help="Usar solo lunes-viernes para inferir residencia AM/PM.",
    )
    return parser.parse_args()


def ensure_inputs(scope: str) -> tuple[Path, Path]:
    bridge = bridge_path(scope)
    proposito_home = proposito_home_path(scope)
    missing = [p for p in [bridge, proposito_home] if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Faltan artefactos requeridos:\n"
            + "\n".join(f"- {p}" for p in missing)
            + f"\nPrimero corre: python scripts/audits/build_proposito_pk_bridge.py --scope {scope}"
        )
    return bridge, proposito_home


def write_csv(df: pl.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)
    return path


def base_trips_lf(path: Path, *, weekday_only: bool) -> pl.LazyFrame:
    ts = pl.col("ts_inicio_min_key").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M", strict=False)
    lf = (
        pl.scan_parquet(path)
        .select(
            [
                pl.coalesce([pl.col("id_tarjeta_processed"), pl.col("id_tarjeta")]).alias("id_tarjeta"),
                pl.col("zona_inicio_processed").cast(pl.Int64, strict=False).alias("zona_inicio"),
                pl.col("zona_fin_processed").cast(pl.Int64, strict=False).alias("zona_fin"),
                pl.col("semana_iso_processed").alias("semana_iso"),
                pl.col("ts_inicio_min_key"),
            ]
        )
        .with_columns(ts.alias("ts_inicio"))
        .with_columns(
            [
                pl.col("ts_inicio").dt.hour().alias("hour"),
                pl.col("ts_inicio").dt.weekday().alias("weekday"),
            ]
        )
        .filter(pl.col("id_tarjeta").is_not_null() & pl.col("ts_inicio").is_not_null())
    )
    if weekday_only:
        # Polars weekday: Monday=1, Sunday=7.
        lf = lf.filter(pl.col("weekday").is_between(1, 5))
    return lf


def period_mode(
    lf: pl.LazyFrame,
    *,
    zone_col: str,
    prefix: str,
    start_hour: int,
    end_hour: int,
) -> pl.DataFrame:
    count_col = f"n_{prefix}_trips"
    zone_alias = f"{prefix}_zone"
    total_col = f"n_{prefix}_trips_card"
    observed_col = f"n_{prefix}_zones_observed"
    top_share_col = f"{prefix}_top_share"
    tie_col = f"{prefix}_has_tie"

    period = (
        lf.filter(
            pl.col("hour").is_between(start_hour, end_hour - 1)
            & pl.col(zone_col).is_not_null()
        )
        .select(["id_tarjeta", pl.col(zone_col).alias("zone")])
    )
    counts = period.group_by(["id_tarjeta", "zone"]).agg(pl.len().alias(count_col))
    totals = period.group_by("id_tarjeta").agg(pl.len().alias(total_col))
    ranked = counts.sort(["id_tarjeta", count_col, "zone"], descending=[False, True, False])
    return (
        ranked.group_by("id_tarjeta")
        .agg(
            [
                pl.col("zone").first().alias(zone_alias),
                pl.col(count_col).first().alias(f"{count_col}_top"),
                pl.col("zone").n_unique().alias(observed_col),
                pl.col(count_col).max().alias(f"{count_col}_max"),
                (pl.col(count_col) == pl.col(count_col).max()).sum().alias(f"n_{prefix}_top_tied_zones"),
            ]
        )
        .join(totals, on="id_tarjeta", how="left")
        .with_columns((pl.col(f"{count_col}_top") / pl.col(total_col)).alias(top_share_col))
        .with_columns((pl.col(f"n_{prefix}_top_tied_zones") > 1).alias(tie_col))
        .collect()
    )


def commute_modal_candidate(
    lf: pl.LazyFrame,
    *,
    morning_start: int,
    morning_end: int,
    afternoon_start: int,
    afternoon_end: int,
) -> pl.DataFrame:
    am = (
        lf.filter(
            pl.col("hour").is_between(morning_start, morning_end - 1)
            & pl.col("zona_inicio").is_not_null()
        )
        .select(["id_tarjeta", pl.col("zona_inicio").alias("commute_zone")])
    )
    pm = (
        lf.filter(
            pl.col("hour").is_between(afternoon_start, afternoon_end - 1)
            & pl.col("zona_fin").is_not_null()
        )
        .select(["id_tarjeta", pl.col("zona_fin").alias("commute_zone")])
    )
    events = pl.concat([am, pm], how="diagonal_relaxed")
    counts = events.group_by(["id_tarjeta", "commute_zone"]).agg(pl.len().alias("n_commute_home_events"))
    totals = events.group_by("id_tarjeta").agg(pl.len().alias("n_commute_home_events_card"))
    ranked = counts.sort(
        ["id_tarjeta", "n_commute_home_events", "commute_zone"],
        descending=[False, True, False],
    )
    return (
        ranked.group_by("id_tarjeta")
        .agg(
            [
                pl.col("commute_zone").first().alias("commute_zona_hogar_modal"),
                pl.col("n_commute_home_events").first().alias("n_commute_home_events_top"),
                pl.col("commute_zone").n_unique().alias("n_commute_home_zones_observed"),
                pl.col("n_commute_home_events").max().alias("n_commute_home_events_max"),
                (pl.col("n_commute_home_events") == pl.col("n_commute_home_events").max())
                .sum()
                .alias("n_commute_top_tied_zones"),
            ]
        )
        .join(totals, on="id_tarjeta", how="left")
        .with_columns(
            [
                (pl.col("n_commute_home_events_top") / pl.col("n_commute_home_events_card")).alias(
                    "commute_home_top_share"
                ),
                (pl.col("n_commute_top_tied_zones") > 1).alias("commute_has_tie"),
            ]
        )
        .collect()
    )


def build_commute_candidates(args: argparse.Namespace, bridge: Path) -> pl.DataFrame:
    trips = base_trips_lf(bridge, weekday_only=args.weekday_only)
    am_mode = period_mode(
        trips,
        zone_col="zona_inicio",
        prefix="am_origin",
        start_hour=args.morning_start,
        end_hour=args.morning_end,
    )
    pm_mode = period_mode(
        trips,
        zone_col="zona_fin",
        prefix="pm_dest",
        start_hour=args.afternoon_start,
        end_hour=args.afternoon_end,
    )
    modal = commute_modal_candidate(
        trips,
        morning_start=args.morning_start,
        morning_end=args.morning_end,
        afternoon_start=args.afternoon_start,
        afternoon_end=args.afternoon_end,
    )

    candidates = (
        modal.join(am_mode, on="id_tarjeta", how="full", coalesce=True)
        .join(pm_mode, on="id_tarjeta", how="full", coalesce=True)
        .with_columns(
            [
                (
                    pl.col("am_origin_zone").is_not_null()
                    & pl.col("pm_dest_zone").is_not_null()
                    & (pl.col("am_origin_zone") == pl.col("pm_dest_zone"))
                ).alias("am_pm_same_zone"),
                pl.when(
                    pl.col("am_origin_zone").is_not_null()
                    & pl.col("pm_dest_zone").is_not_null()
                    & (pl.col("am_origin_zone") == pl.col("pm_dest_zone"))
                )
                .then(pl.col("am_origin_zone"))
                .otherwise(None)
                .alias("commute_zona_hogar_consensus"),
            ]
        )
        .with_columns(
            pl.when(pl.col("commute_has_tie"))
            .then(pl.lit("baja"))
            .when(pl.col("am_pm_same_zone"))
            .then(pl.lit("alta"))
            .when(pl.col("commute_home_top_share") >= 0.80)
            .then(pl.lit("alta"))
            .when(pl.col("commute_home_top_share") >= 0.60)
            .then(pl.lit("media"))
            .otherwise(pl.lit("baja"))
            .alias("commute_confidence")
        )
        .sort("id_tarjeta")
    )
    return candidates


def add_agreement_flags(df: pl.DataFrame) -> pl.DataFrame:
    has_prop = pl.col("zona_hogar").is_not_null()
    return df.with_columns(
        [
            (pl.col("commute_zona_hogar_modal").is_not_null()).alias("has_commute_modal"),
            (pl.col("commute_zona_hogar_consensus").is_not_null()).alias("has_commute_consensus"),
            (pl.col("am_origin_zone").is_not_null()).alias("has_am_origin"),
            (pl.col("pm_dest_zone").is_not_null()).alias("has_pm_dest"),
            (has_prop & (pl.col("zona_hogar") == pl.col("commute_zona_hogar_modal"))).alias(
                "agree_proposito_commute_modal"
            ),
            (has_prop & (pl.col("zona_hogar") == pl.col("commute_zona_hogar_consensus"))).alias(
                "agree_proposito_commute_consensus"
            ),
            (has_prop & (pl.col("zona_hogar") == pl.col("am_origin_zone"))).alias("agree_proposito_am_origin"),
            (has_prop & (pl.col("zona_hogar") == pl.col("pm_dest_zone"))).alias("agree_proposito_pm_dest"),
        ]
    )


def summarize_boolean_rates(df: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    bool_cols = [
        "has_commute_modal",
        "has_commute_consensus",
        "has_am_origin",
        "has_pm_dest",
        "am_pm_same_zone",
        "agree_proposito_commute_modal",
        "agree_proposito_commute_consensus",
        "agree_proposito_am_origin",
        "agree_proposito_pm_dest",
    ]
    has_both_modal = pl.col("zona_hogar").is_not_null() & pl.col("commute_zona_hogar_modal").is_not_null()
    has_both_consensus = pl.col("zona_hogar").is_not_null() & pl.col("commute_zona_hogar_consensus").is_not_null()
    return (
        df.group_by(by)
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("zona_hogar").is_not_null().sum().alias("n_cards_with_proposito_home"),
                has_both_modal.sum().alias("n_cards_with_both_modal"),
                pl.col("agree_proposito_commute_modal").fill_null(False).sum().alias("n_agree_modal"),
                has_both_consensus.sum().alias("n_cards_with_both_consensus"),
                pl.col("agree_proposito_commute_consensus").fill_null(False).sum().alias("n_agree_consensus"),
                *[pl.col(c).fill_null(False).sum().alias(f"n_{c}") for c in bool_cols],
                *[pl.col(c).fill_null(False).mean().alias(f"rate_{c}") for c in bool_cols],
                pl.col("home_zone_top_share").mean().alias("mean_proposito_home_top_share"),
                pl.col("commute_home_top_share").mean().alias("mean_commute_home_top_share"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_agree_modal") / pl.col("n_cards_with_both_modal")).alias(
                    "agreement_rate_modal_given_both"
                ),
                (pl.col("n_agree_consensus") / pl.col("n_cards_with_both_consensus")).alias(
                    "agreement_rate_consensus_given_both"
                ),
            ]
        )
        .sort(by)
    )


def build_outputs(args: argparse.Namespace) -> dict[str, Path]:
    bridge, proposito_home_path_ = ensure_inputs(args.scope)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = output_suffix(args)

    candidates = build_commute_candidates(args, bridge)
    candidates_path = OUT_DIR / f"commute_home_candidates_{suffix}.parquet"
    candidates.write_parquet(candidates_path, compression="zstd")

    prop_home = pl.read_parquet(proposito_home_path_)
    comparison = (
        prop_home.join(candidates, on="id_tarjeta", how="full", coalesce=True)
        .pipe(add_agreement_flags)
        .sort("id_tarjeta")
    )
    comparison_path = OUT_DIR / f"commute_vs_proposito_home_{suffix}.parquet"
    comparison.write_parquet(comparison_path, compression="zstd")

    summary = pl.DataFrame(
        [
            {
                "scope": args.scope,
                "morning_window": f"{args.morning_start:02d}:00-{args.morning_end:02d}:00",
                "afternoon_window": f"{args.afternoon_start:02d}:00-{args.afternoon_end:02d}:00",
                "weekday_only": args.weekday_only,
                "n_proposito_home_cards": prop_home.height,
                "n_commute_candidate_cards": candidates.height,
                "n_comparison_cards_union": comparison.height,
                "n_cards_with_both_modal": comparison.filter(
                    pl.col("zona_hogar").is_not_null() & pl.col("commute_zona_hogar_modal").is_not_null()
                ).height,
                "n_cards_agree_modal": comparison.filter(pl.col("agree_proposito_commute_modal")).height,
                "n_cards_with_both_consensus": comparison.filter(
                    pl.col("zona_hogar").is_not_null() & pl.col("commute_zona_hogar_consensus").is_not_null()
                ).height,
                "n_cards_agree_consensus": comparison.filter(pl.col("agree_proposito_commute_consensus")).height,
            }
        ]
    ).with_columns(
        [
            (pl.col("n_cards_agree_modal") / pl.col("n_cards_with_both_modal")).alias(
                "agreement_rate_modal_given_both"
            ),
            (pl.col("n_cards_agree_consensus") / pl.col("n_cards_with_both_consensus")).alias(
                "agreement_rate_consensus_given_both"
            ),
        ]
    )
    summary_path = write_csv(summary, OUT_DIR / f"commute_vs_proposito_summary_{suffix}.csv")

    by_home_conf_path = write_csv(
        summarize_boolean_rates(
            comparison.with_columns(pl.col("home_confidence").fill_null("sin_proposito_home")),
            ["home_confidence"],
        ),
        OUT_DIR / f"commute_vs_proposito_by_home_confidence_{suffix}.csv",
    )
    by_commute_conf_path = write_csv(
        summarize_boolean_rates(
            comparison.with_columns(pl.col("commute_confidence").fill_null("sin_commute_home")),
            ["commute_confidence"],
        ),
        OUT_DIR / f"commute_vs_proposito_by_commute_confidence_{suffix}.csv",
    )
    cross_conf_path = write_csv(
        summarize_boolean_rates(
            comparison.with_columns(
                [
                    pl.col("home_confidence").fill_null("sin_proposito_home"),
                    pl.col("commute_confidence").fill_null("sin_commute_home"),
                ]
            ),
            ["home_confidence", "commute_confidence"],
        ),
        OUT_DIR / f"commute_vs_proposito_by_confidence_cross_{suffix}.csv",
    )

    mismatch_sample = comparison.filter(
        pl.col("zona_hogar").is_not_null()
        & pl.col("commute_zona_hogar_modal").is_not_null()
        & ~pl.col("agree_proposito_commute_modal")
    ).head(1000)
    mismatch_path = write_csv(mismatch_sample, OUT_DIR / f"commute_vs_proposito_mismatch_sample_{suffix}.csv")

    zone_pair_path = write_csv(
        comparison.filter(
            pl.col("zona_hogar").is_not_null() & pl.col("commute_zona_hogar_modal").is_not_null()
        )
        .group_by(["zona_hogar", "commute_zona_hogar_modal"])
        .agg(pl.len().alias("n_cards"))
        .sort("n_cards", descending=True)
        .head(1000),
        OUT_DIR / f"commute_vs_proposito_zone_pairs_top_{suffix}.csv",
    )

    config = {
        "scope": args.scope,
        "bridge": str(bridge),
        "proposito_home": str(proposito_home_path_),
        "morning_start": args.morning_start,
        "morning_end": args.morning_end,
        "afternoon_start": args.afternoon_start,
        "afternoon_end": args.afternoon_end,
        "weekday_only": args.weekday_only,
        "outputs": {
            "commute_candidates": str(candidates_path),
            "comparison": str(comparison_path),
            "summary": str(summary_path),
            "by_home_confidence": str(by_home_conf_path),
            "by_commute_confidence": str(by_commute_conf_path),
            "by_confidence_cross": str(cross_conf_path),
            "mismatch_sample": str(mismatch_path),
            "zone_pairs_top": str(zone_pair_path),
        },
    }
    config_path = OUT_DIR / f"commute_vs_proposito_config_{suffix}.json"
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return {name: Path(path) for name, path in config["outputs"].items()} | {"config": config_path}


def main() -> None:
    args = parse_args()
    if not (0 <= args.morning_start < args.morning_end <= 24):
        raise ValueError("Ventana AM inválida.")
    if not (0 <= args.afternoon_start < args.afternoon_end <= 24):
        raise ValueError("Ventana PM inválida.")

    outputs = build_outputs(args)
    print("✅ Auditoría commute-home vs proposito completada.")
    for name, path in outputs.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
