from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRIPS_DIR = PROJECT_ROOT / "tmp"
DEFAULT_2X2_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_2x2_w15w17_w15w16"
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2"
DEFAULT_VARIANT_ID = "B_calendar_W15_W17_N14"

SIMILARITY_FEATURES_3 = ["dsi_day_sequence", "tsi_time_distribution", "lsi_origin_zone"]
SIMILARITY_FEATURES_4 = [*SIMILARITY_FEATURES_3, "lsi_origin_stop"]

ABS_CORE_FEATURES = [
    "log_n_trips_total",
    "n_active_days",
    "share_active_days",
    "avg_trips_per_active_day",
    "peak_share_am_6_9",
    "peak_share_pm_17_20",
    "noon_peak_share_12_14",
    "off_peak_share",
    # Contrastes temporales (reformulacion para reducir ruido):
    # peak_dominance_am_pm = peak_am - peak_pm in [-1, 1]
    # peak_vs_offpeak = (peak_am + peak_pm) - off_peak in [-1, 2]
    "peak_dominance_am_pm",
    "peak_vs_offpeak",
    "avg_first_trip_hour",
    "share_weekday_trips",
    "share_weekend_trips",
    "weekend_active_days",
    "share_weekend_active_days",
    "n_unique_origin_zones",
    "entropy_origin_zones_norm",
    "share_top_origin_zone",
]

ABS_FULL_EXTRA_FEATURES = [
    "n_unique_od_pairs",
    "share_top_od_pair",
    "entropy_od_pairs_norm",
    "share_metro_trips",
    "share_non_metro_trips",
    "share_metro_transfer_trips",
    "avg_n_etapas_per_trip",
    "avg_trip_duration_min",
    "total_time_in_system_hours",
]

ABS_FULL_FEATURES = [*ABS_CORE_FEATURES, *ABS_FULL_EXTRA_FEATURES]

BRANCH_FEATURES = {
    "R1_lizana3": SIMILARITY_FEATURES_3,
    "R1_lizana4_sensitivity": SIMILARITY_FEATURES_4,
    "R2_abs_core_2025": ABS_CORE_FEATURES,
    "R2_abs_full_2025": ABS_FULL_FEATURES,
    "R3_combined_core": [*SIMILARITY_FEATURES_3, *ABS_CORE_FEATURES],
    "R3_combined_full": [*SIMILARITY_FEATURES_3, *ABS_FULL_FEATURES],
}

WEEKDAY_ONLY_CONSTANT_FEATURES = {
    "share_weekday_trips",
    "share_weekend_trips",
    "weekend_active_days",
    "share_weekend_active_days",
}

TRIP_COLUMNS = [
    "id_tarjeta",
    "fecha",
    "tiempo_inicio_viaje",
    "zona_inicio_viaje",
    "zona_fin_viaje",
    "paradero_inicio_viaje",
    "paradero_fin_viaje",
    "n_etapas_recon",
    "metro_any",
    "t_total_calculado_seg",
    "is_qr",
]


@dataclass(frozen=True)
class VariantConfig:
    variant_id: str
    indicator_path: Path
    base_weeks: tuple[str, ...]
    eval_weeks: tuple[str, ...]
    weekdays_only: bool
    expected_day_slots: int
    excluded_day_slots: tuple[int, ...]
    n_label: str


def trips_path(week: str) -> Path:
    path = TRIPS_DIR / f"viajes_con_te_calculado_{week}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"No existe parquet de viajes para {week}: {path}")
    return path


def parse_week_list(value: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in str(value).split(",") if x.strip())


def parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return False
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n", ""}:
        return False
    raise ValueError(f"No se pudo interpretar booleano: {value!r}")


def parse_excluded_day_slots(value: object) -> tuple[int, ...]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ()
    text = str(value).strip()
    if not text:
        return ()
    slots: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if part:
            slots.append(int(float(part)))
    return tuple(sorted(set(slots)))


def load_variant_config(two_by_two_dir: Path, variant_id: str) -> VariantConfig:
    inventory = pd.read_csv(two_by_two_dir / "segmentation_2x2_artifact_inventory.csv")
    samples = pd.read_csv(two_by_two_dir / "segmentation_2x2_sample_summary.csv")
    inv_row = inventory.loc[inventory["variant_id"] == variant_id]
    sample_row = samples.loc[samples["variant_id"] == variant_id]
    if inv_row.empty or sample_row.empty:
        available = sorted(set(inventory["variant_id"]) | set(samples["variant_id"]))
        raise ValueError(f"variant_id desconocido: {variant_id}. Disponibles: {available}")
    inv = inv_row.iloc[0]
    sample = sample_row.iloc[0]
    return VariantConfig(
        variant_id=variant_id,
        indicator_path=Path(inv["indicator_path"]),
        base_weeks=parse_week_list(sample["base_weeks"]),
        eval_weeks=parse_week_list(sample["eval_weeks"]),
        weekdays_only=parse_bool(sample["weekdays_only"]),
        expected_day_slots=int(sample["expected_day_slots"]),
        excluded_day_slots=parse_excluded_day_slots(sample.get("excluded_day_slots")),
        n_label=str(inv["n_label"]),
    )


def day_slot_expr(week_idx: int) -> pl.Expr:
    weekday = pl.col("fecha").dt.weekday().cast(pl.Int8)
    return (pl.lit(week_idx * 10).cast(pl.Int16) + weekday.cast(pl.Int16)).alias("day_slot")


def scan_eval_trips(config: VariantConfig, eligible_ids: pl.DataFrame) -> pl.LazyFrame:
    frames: list[pl.LazyFrame] = []
    eligible_lf = eligible_ids.lazy()
    for week_idx, week in enumerate(config.eval_weeks):
        schema_names = pl.scan_parquet(trips_path(week)).collect_schema().names()
        missing = sorted(set(TRIP_COLUMNS) - set(schema_names))
        if missing:
            raise ValueError(f"Faltan columnas en {week}: {missing}")
        lf = (
            pl.scan_parquet(trips_path(week))
            .select(TRIP_COLUMNS)
            .with_columns(
                [
                    pl.lit(week).alias("week"),
                    pl.lit(week_idx).cast(pl.Int8).alias("week_slot"),
                    day_slot_expr(week_idx),
                    pl.col("id_tarjeta").cast(pl.Utf8),
                    pl.col("zona_inicio_viaje").cast(pl.Utf8).fill_null("missing"),
                    pl.col("zona_fin_viaje").cast(pl.Utf8).fill_null("missing"),
                    pl.col("paradero_inicio_viaje").cast(pl.Utf8).fill_null("missing"),
                    pl.col("paradero_fin_viaje").cast(pl.Utf8).fill_null("missing"),
                    pl.col("metro_any").fill_null(False).cast(pl.Boolean, strict=False),
                    pl.col("n_etapas_recon").cast(pl.Float64, strict=False),
                    pl.col("t_total_calculado_seg").cast(pl.Float64, strict=False),
                    pl.col("is_qr").cast(pl.Boolean, strict=False),
                    pl.col("fecha").dt.weekday().cast(pl.Int8).alias("weekday"),
                    pl.col("tiempo_inicio_viaje").dt.hour().cast(pl.Int8).alias("hour"),
                ]
            )
        )
        frames.append(lf)
    out = pl.concat(frames, how="vertical")
    if config.weekdays_only:
        out = out.filter(pl.col("weekday") <= 5)
    if config.excluded_day_slots:
        out = out.filter(~pl.col("day_slot").is_in(list(config.excluded_day_slots)))
    return out.join(eligible_lf, on="id_tarjeta", how="inner")


def normalized_entropy_frame(lf: pl.LazyFrame, category_col: str, output_col: str) -> pl.DataFrame:
    counts = lf.group_by(["id_tarjeta", category_col]).agg(pl.len().alias("n"))
    totals = counts.group_by("id_tarjeta").agg(
        [
            pl.col("n").sum().alias("total"),
            pl.col(category_col).n_unique().alias("n_unique"),
            pl.col("n").max().alias("top_n"),
        ]
    )
    shares = counts.join(totals, on="id_tarjeta").with_columns((pl.col("n") / pl.col("total")).alias("p"))
    entropy = (
        shares.group_by("id_tarjeta")
        .agg((-(pl.col("p") * pl.col("p").log()).sum()).alias("entropy_raw"))
        .join(totals, on="id_tarjeta")
        .with_columns(
            [
                pl.when(pl.col("n_unique") > 1)
                .then(pl.col("entropy_raw") / pl.col("n_unique").cast(pl.Float64).log())
                .otherwise(0.0)
                .clip(0, 1)
                .alias(output_col),
                (pl.col("top_n") / pl.col("total")).alias(f"share_top_{category_col}"),
            ]
        )
        .select(["id_tarjeta", "n_unique", output_col, f"share_top_{category_col}"])
        .collect()
    )
    return entropy


def branch_features_for_config(config: VariantConfig) -> dict[str, list[str]]:
    if not config.weekdays_only:
        return {branch_id: list(features) for branch_id, features in BRANCH_FEATURES.items()}
    return {
        branch_id: [feature for feature in features if feature not in WEEKDAY_ONLY_CONSTANT_FEATURES]
        for branch_id, features in BRANCH_FEATURES.items()
    }


def build_absolute_features(config: VariantConfig, indicators: pl.DataFrame) -> pl.DataFrame:
    eligible_ids = indicators.select("id_tarjeta").unique()
    trips = scan_eval_trips(config, eligible_ids)
    od_expr = (pl.col("zona_inicio_viaje") + pl.lit("->") + pl.col("zona_fin_viaje")).alias("od_pair")
    peak_am_expr = (pl.col("hour") >= 6) & (pl.col("hour") < 9)
    peak_pm_expr = (pl.col("hour") >= 17) & (pl.col("hour") < 20)
    noon_peak_expr = (pl.col("hour") >= 12) & (pl.col("hour") < 14)
    trips = trips.with_columns(
        [
            peak_am_expr.cast(pl.Int8).alias("is_peak_am"),
            peak_pm_expr.cast(pl.Int8).alias("is_peak_pm"),
            noon_peak_expr.cast(pl.Int8).alias("is_noon_peak"),
            (~(peak_am_expr | peak_pm_expr | noon_peak_expr)).cast(pl.Int8).alias("is_off_peak"),
            ((pl.col("weekday") <= 5)).cast(pl.Int8).alias("is_weekday_trip"),
            ((pl.col("weekday") >= 6)).cast(pl.Int8).alias("is_weekend_trip"),
            (pl.col("metro_any").cast(pl.Int8)).alias("is_metro_trip"),
            ((~pl.col("metro_any")).cast(pl.Int8)).alias("is_non_metro_trip"),
            ((pl.col("metro_any") & (pl.col("n_etapas_recon") > 1)).cast(pl.Int8)).alias("is_metro_transfer_trip"),
            od_expr,
        ]
    )
    first_trip = (
        trips.group_by(["id_tarjeta", "day_slot"])
        .agg(pl.col("tiempo_inicio_viaje").min().alias("first_trip_ts"))
        .with_columns(
            (
                pl.col("first_trip_ts").dt.hour()
                + pl.col("first_trip_ts").dt.minute() / 60
                + pl.col("first_trip_ts").dt.second() / 3600
            ).alias("first_trip_hour")
        )
        .group_by("id_tarjeta")
        .agg(pl.col("first_trip_hour").mean().alias("avg_first_trip_hour"))
    )
    base = (
        trips.group_by("id_tarjeta")
        .agg(
            [
                pl.len().alias("n_trips_total"),
                pl.col("day_slot").n_unique().alias("n_active_days"),
                pl.col("is_peak_am").mean().alias("peak_share_am_6_9"),
                pl.col("is_peak_pm").mean().alias("peak_share_pm_17_20"),
                pl.col("is_noon_peak").mean().alias("noon_peak_share_12_14"),
                pl.col("is_off_peak").mean().alias("off_peak_share"),
                pl.col("is_weekday_trip").mean().alias("share_weekday_trips"),
                pl.col("is_weekend_trip").mean().alias("share_weekend_trips"),
                pl.col("day_slot").filter(pl.col("weekday") >= 6).n_unique().alias("weekend_active_days"),
                pl.col("is_metro_trip").mean().alias("share_metro_trips"),
                pl.col("is_non_metro_trip").mean().alias("share_non_metro_trips"),
                pl.col("is_metro_transfer_trip").mean().alias("share_metro_transfer_trips"),
                pl.col("n_etapas_recon").mean().alias("avg_n_etapas_per_trip"),
                (pl.col("t_total_calculado_seg").mean() / 60).alias("avg_trip_duration_min"),
                (pl.col("t_total_calculado_seg").sum() / 3600).alias("total_time_in_system_hours"),
                pl.col("is_qr").cast(pl.Int8).mean().alias("qr_share_eval_recomputed"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_trips_total") + 1).log().alias("log_n_trips_total"),
                (pl.col("n_active_days") / config.expected_day_slots).alias("share_active_days"),
                (pl.col("n_trips_total") / pl.col("n_active_days")).alias("avg_trips_per_active_day"),
                (pl.col("peak_share_am_6_9") - pl.col("peak_share_pm_17_20")).alias("peak_dominance_am_pm"),
                (
                    pl.col("peak_share_am_6_9")
                    + pl.col("peak_share_pm_17_20")
                    - pl.col("off_peak_share")
                ).alias("peak_vs_offpeak"),
            ]
        )
    )
    # Weekend slots are observable in the eval window itself; for weekday-only variants this denominator is 1 to keep 0.
    weekend_slot_count = (
        trips.select("day_slot", "weekday")
        .unique()
        .filter(pl.col("weekday") >= 6)
        .select(pl.len())
        .collect()
        .item()
    )
    weekend_slot_denominator = max(int(weekend_slot_count), 1)
    base = base.with_columns((pl.col("weekend_active_days") / weekend_slot_denominator).alias("share_weekend_active_days"))

    origin = normalized_entropy_frame(trips, "zona_inicio_viaje", "entropy_origin_zones_norm").rename(
        {
            "n_unique": "n_unique_origin_zones",
            "share_top_zona_inicio_viaje": "share_top_origin_zone",
        }
    )
    od = normalized_entropy_frame(trips, "od_pair", "entropy_od_pairs_norm").rename(
        {
            "n_unique": "n_unique_od_pairs",
        }
    )
    absolute = (
        base.collect()
        .join(first_trip.collect(), on="id_tarjeta", how="left")
        .join(origin, on="id_tarjeta", how="left")
        .join(od, on="id_tarjeta", how="left")
        .select(["id_tarjeta", *ABS_FULL_FEATURES, "qr_share_eval_recomputed"])
    )
    return absolute


def build_branch_matrices(
    config: VariantConfig,
    indicators: pl.DataFrame,
    absolute: pl.DataFrame,
) -> tuple[dict[str, pl.DataFrame], dict[str, list[str]]]:
    base = (
        indicators.select(
            [
                "id_tarjeta",
                "share_is_qr_eval",
                "n_trips_eval",
                "n_active_days_eval",
                *SIMILARITY_FEATURES_4,
            ]
        )
        .join(absolute, on="id_tarjeta", how="inner")
        .with_columns(pl.lit(config.variant_id).alias("variant_id"))
    )
    branch_features = branch_features_for_config(config)
    matrices: dict[str, pl.DataFrame] = {}
    for branch_id, features in branch_features.items():
        matrices[branch_id] = base.select(
            [
                "variant_id",
                "id_tarjeta",
                "share_is_qr_eval",
                "n_trips_eval",
                "n_active_days_eval",
                *features,
            ]
        )
    return matrices, branch_features


def validation_rows(variant_id: str, branch_id: str, df: pl.DataFrame, features: list[str]) -> list[dict[str, object]]:
    rows = []
    n_rows = max(df.height, 1)
    rows.append(
        {
            "variant_id": variant_id,
            "branch_id": branch_id,
            "check": "unique_id_tarjeta",
            "feature": "id_tarjeta",
            "passed": df["id_tarjeta"].n_unique() == df.height,
            "value": float(df["id_tarjeta"].n_unique()),
            "detail": f"{df['id_tarjeta'].n_unique()} unique / {df.height} rows",
        }
    )
    for feature in features:
        s = df[feature]
        nan_count = int(s.is_nan().sum()) if s.dtype in (pl.Float32, pl.Float64) else 0
        std_value = float(s.std()) if s.null_count() < df.height else math.nan
        min_value = float(s.min()) if s.null_count() < df.height else math.nan
        max_value = float(s.max()) if s.null_count() < df.height else math.nan
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "check": "feature_missing_rate",
                "feature": feature,
                "passed": s.null_count() == 0,
                "value": float(s.null_count() / n_rows),
                "detail": "missing_rate",
            }
        )
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "check": "feature_nan_rate",
                "feature": feature,
                "passed": nan_count == 0,
                "value": float(nan_count / n_rows),
                "detail": "nan_rate",
            }
        )
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "check": "feature_std",
                "feature": feature,
                "passed": (not math.isnan(std_value)) and std_value > 0,
                "value": std_value,
                "detail": "std",
            }
        )
        if feature.startswith("share_") or "entropy_" in feature or feature in SIMILARITY_FEATURES_4:
            rows.append(
                {
                    "variant_id": variant_id,
                    "branch_id": branch_id,
                    "check": "feature_unit_interval",
                    "feature": feature,
                    "passed": min_value >= -1e-9 and max_value <= 1 + 1e-9,
                    "value": max(abs(min_value), abs(max_value)),
                    "detail": f"min={min_value:.6g}; max={max_value:.6g}",
                }
            )
    if {"share_metro_trips", "share_non_metro_trips"}.issubset(set(features)):
        max_abs_error = (
            df.select(((pl.col("share_metro_trips") + pl.col("share_non_metro_trips") - 1).abs()).max()).item()
        )
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "check": "modal_share_sum",
                "feature": "share_metro_trips+share_non_metro_trips",
                "passed": max_abs_error <= 1e-9,
                "value": float(max_abs_error),
                "detail": "max_abs(sum - 1)",
            }
        )
    if {"share_metro_transfer_trips", "share_metro_trips"}.issubset(set(features)):
        max_violation = df.select((pl.col("share_metro_transfer_trips") - pl.col("share_metro_trips")).max()).item()
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "check": "metro_transfer_leq_metro",
                "feature": "share_metro_transfer_trips",
                "passed": max_violation <= 1e-9,
                "value": float(max_violation),
                "detail": "max(transfer_share - metro_share)",
            }
        )
    return rows


def write_feature_registry(out_dir: Path) -> None:
    rows = []
    for branch_id, features in BRANCH_FEATURES.items():
        for feature in features:
            role = "similarity_2024_2025" if feature in SIMILARITY_FEATURES_4 else "absolute_2025"
            rows.append({"branch_id": branch_id, "feature": feature, "feature_role": role})
    pd.DataFrame(rows).to_csv(out_dir / "feature_registry.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build behavioral segmentation matrices for 2x2 variants.")
    parser.add_argument("--two-by-two-dir", type=Path, default=DEFAULT_2X2_DIR)
    parser.add_argument("--variant-id", action="append", default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--max-users", type=int, default=None)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_feature_registry(args.out_dir)
    variant_ids = args.variant_id or [DEFAULT_VARIANT_ID]
    inventory_rows = []
    validation = []

    for variant_id in variant_ids:
        config = load_variant_config(args.two_by_two_dir, variant_id)
        print(f"[variant] {variant_id}", flush=True)
        indicators = pl.read_parquet(config.indicator_path)
        if args.max_users is not None and indicators.height > args.max_users:
            indicators = indicators.sample(n=args.max_users, seed=args.random_seed)
        absolute = build_absolute_features(config, indicators)
        matrices, branch_features = build_branch_matrices(config, indicators, absolute)

        variant_dir = args.out_dir / "features" / variant_id
        variant_dir.mkdir(parents=True, exist_ok=True)
        absolute_path = variant_dir / "absolute_2025_features.parquet"
        absolute.write_parquet(absolute_path, compression="zstd")

        for branch_id, matrix in matrices.items():
            path = variant_dir / f"{branch_id}.parquet"
            matrix.write_parquet(path, compression="zstd")
            features = branch_features[branch_id]
            validation.extend(validation_rows(config.variant_id, branch_id, matrix, features))
            inventory_rows.append(
                {
                    "variant_id": variant_id,
                    "branch_id": branch_id,
                    "path": str(path),
                    "n_rows": matrix.height,
                    "n_features": len(features),
                    "features": ",".join(features),
                }
            )
            print(f"  {branch_id}: rows={matrix.height:,} features={len(features)}", flush=True)

        (variant_dir / "variant_config.json").write_text(
            json.dumps(
                {
                    "variant_id": config.variant_id,
                    "indicator_path": str(config.indicator_path),
                    "base_weeks": config.base_weeks,
                    "eval_weeks": config.eval_weeks,
                    "weekdays_only": config.weekdays_only,
                    "expected_day_slots": config.expected_day_slots,
                    "excluded_day_slots": config.excluded_day_slots,
                    "n_label": config.n_label,
                    "modal_definition": {
                        "share_metro_trips": "metro_any == true; at least one stage touched Metro",
                        "share_non_metro_trips": "metro_any == false; no stage touched Metro; proxy for surface/non-Metro, not strict bus-only",
                        "share_metro_transfer_trips": "metro_any == true and n_etapas_recon > 1",
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    pd.DataFrame(inventory_rows).to_csv(args.out_dir / "feature_matrix_inventory.csv", index=False)
    pd.DataFrame(validation).to_csv(args.out_dir / "feature_matrix_validation.csv", index=False)
    print(f"Feature matrices written to {args.out_dir}", flush=True)


if __name__ == "__main__":
    main()
