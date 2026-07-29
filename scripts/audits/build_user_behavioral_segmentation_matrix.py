"""Build behavioral_wide matrices for user-level segmentation.

The script materializes the audited `behavioral_wide` specs so PCA and sparse
KMeans can run from stable parquet artifacts instead of rerendering the audit
notebook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
DEFAULT_OUT_DIR = USER_DIR / "segmentation"
VARIANT_ID = "behavioral_wide"

UNIVERSE_PATHS = {
    "alta_n3": USER_DIR / "user_model_matrix_interannual_ml_clean_alta_n3.parquet",
    "alta_n5": USER_DIR / "user_model_matrix_interannual_ml_clean_alta_n5.parquet",
    "alta_n10": USER_DIR / "user_model_matrix_interannual_ml_clean_alta_n10.parquet",
    "alta_n3_home3": USER_DIR / "user_model_matrix_interannual_ml_clean_alta_n3_home3.parquet",
}
DAILY_TOUR_ARTIFACT_PATH = USER_DIR / "user_behavior_daily_tour_features_interannual_ml.parquet"

TARGET_CONTEXT_COLS = ["is_qr", "is_qr_red", "is_qr_other", "tipo_tarjeta"]
OPTIONAL_METADATA_COLS = [
    "n_viajes",
    "share_trips_2025",
    "home_confidence",
    "home_zona",
    "activity_zone_top1_share",
    "activity_zone_entropy",
]

BEHAVIORAL_WIDE_MAIN_METADATA = [
    {"block": "intensidad", "variable": "log1p_n_viajes", "source": "model_matrix:derived", "caveat": "soporte puede dominar"},
    {"block": "intensidad", "variable": "rhythm_active_day_density_span", "source": "model_matrix", "caveat": "densidad/cotidianeidad"},
    {"block": "horario", "variable": "hora_mean", "source": "model_matrix", "caveat": "promedio horario"},
    {"block": "horario", "variable": "hora_std", "source": "model_matrix", "caveat": "dispersion vs soporte"},
    {"block": "horario", "variable": "share_lab_pm", "source": "model_matrix", "caveat": "composicional"},
    {"block": "horario", "variable": "share_lab_pt", "source": "model_matrix", "caveat": "composicional"},
    {"block": "horario", "variable": "share_no_lab", "source": "model_matrix", "caveat": "composicional"},
    {"block": "regularidad", "variable": "log1p_rhythm_mean_gap_active_days", "source": "model_matrix:derived", "caveat": "cola larga / missing gap"},
    {"block": "regularidad", "variable": "rhythm_daily_hhi", "source": "model_matrix", "caveat": "soporte diario"},
    {"block": "regularidad", "variable": "rhythm_single_trip_day_share", "source": "model_matrix", "caveat": "solapa daily-tour"},
    {"block": "regularidad", "variable": "rhythm_weekly_hhi", "source": "model_matrix", "caveat": "scope semanal corto"},
    {"block": "regularidad", "variable": "rhythm_weekly_entropy_norm", "source": "model_matrix", "caveat": "no incluir burstiness"},
    {"block": "modal", "variable": "share_trips_solo_bus", "source": "model_matrix", "caveat": "oferta/acceso"},
    {"block": "modal", "variable": "share_trips_metro_bus", "source": "model_matrix", "caveat": "intermodalidad"},
    {"block": "modal", "variable": "share_trips_with_transfer", "source": "model_matrix", "caveat": "red/oferta"},
    {"block": "modal", "variable": "share_trips_in_multi_route_od", "source": "model_matrix", "caveat": "red/oferta fuerte"},
    {"block": "espacial_od", "variable": "activity_zone_entropy", "source": "model_matrix", "caveat": "soporte/intensidad"},
    {"block": "espacial_od", "variable": "routine_od_hhi", "source": "model_matrix", "caveat": "concentracion OD"},
    {"block": "espacial_od", "variable": "routine_main_od_share", "source": "model_matrix", "caveat": "solapa commute/daily-tour"},
    {"block": "espacial_od", "variable": "routine_main_od_roundtrip_balance", "source": "model_matrix", "caveat": "discreta/bimodal"},
    {"block": "espacial_od", "variable": "origin_zone_top1_share", "source": "model_matrix", "caveat": "residencia/actividad"},
    {"block": "rutina", "variable": "routine_od_time_hhi", "source": "model_matrix", "caveat": "solapa OD/horario"},
    {"block": "rutina", "variable": "routine_lab_peak_share", "source": "model_matrix", "caveat": "solapa horario"},
    {"block": "rutina", "variable": "routine_od_time_entropy_norm", "source": "model_matrix", "caveat": "techo frecuente"},
    {"block": "daily_tour", "variable": "tour_three_plus_trip_day_share", "source": "daily_tour_artifact", "caveat": "solapa intensidad"},
    {"block": "daily_tour", "variable": "tour_reciprocal_od_day_share", "source": "daily_tour_artifact", "caveat": "solapa OD"},
    {"block": "daily_tour", "variable": "tour_closed_loop_day_share", "source": "daily_tour_artifact", "caveat": "solapa reciprocidad"},
    {"block": "daily_tour", "variable": "tour_mixed_mode_day_share", "source": "daily_tour_artifact", "caveat": "solapa modal"},
    {"block": "daily_tour", "variable": "tour_day_span_hours_mean", "source": "daily_tour_artifact", "caveat": "solapa horario"},
    {"block": "daily_tour", "variable": "tour_first_trip_lab_am_peak_share", "source": "daily_tour_artifact", "caveat": "solapa horario"},
    {"block": "daily_tour", "variable": "tour_last_trip_lab_pm_peak_share", "source": "daily_tour_artifact", "caveat": "solapa horario"},
]

BEHAVIORAL_WIDE_MAIN_COLS = [row["variable"] for row in BEHAVIORAL_WIDE_MAIN_METADATA]
BEHAVIORAL_WIDE_V0B_DROP_REASONS = {
    "log1p_rhythm_mean_gap_active_days": "redundante con densidad de dias activos",
    "tour_first_trip_lab_am_peak_share": "redundante con share_lab_pm / rutina peak",
    "rhythm_daily_hhi": "redundante con soporte/intensidad",
    "routine_od_hhi": "redundante con routine_od_time_hhi",
    "tour_reciprocal_od_day_share": "redundante con balance roundtrip OD principal",
}
BEHAVIORAL_WIDE_V0B_COLS = [
    c for c in BEHAVIORAL_WIDE_MAIN_COLS
    if c not in BEHAVIORAL_WIDE_V0B_DROP_REASONS
]

DAILY_TOUR_MAIN_COLS = [
    "tour_three_plus_trip_day_share",
    "tour_reciprocal_od_day_share",
    "tour_closed_loop_day_share",
    "tour_mixed_mode_day_share",
    "tour_day_span_hours_mean",
    "tour_first_trip_lab_am_peak_share",
    "tour_last_trip_lab_pm_peak_share",
]

BEHAVIORAL_WIDE_BASE_RAW_COLS = [
    "n_viajes",
    "rhythm_active_day_density_span",
    "hora_mean",
    "hora_std",
    "share_lab_pm",
    "share_lab_pt",
    "share_no_lab",
    "rhythm_mean_gap_active_days",
    "rhythm_daily_hhi",
    "rhythm_single_trip_day_share",
    "rhythm_weekly_hhi",
    "rhythm_weekly_entropy_norm",
    "share_trips_solo_bus",
    "share_trips_metro_bus",
    "share_trips_with_transfer",
    "share_trips_in_multi_route_od",
    "activity_zone_entropy",
    "routine_od_hhi",
    "routine_main_od_share",
    "routine_main_od_roundtrip_balance",
    "origin_zone_top1_share",
    "routine_od_time_hhi",
    "routine_lab_peak_share",
    "routine_od_time_entropy_norm",
]


def existing_columns(path: Path) -> list[str]:
    return pl.read_parquet_schema(path).names()


def spec_features(spec: str) -> list[str]:
    if spec == "v0":
        return BEHAVIORAL_WIDE_MAIN_COLS
    if spec == "v0b":
        return BEHAVIORAL_WIDE_V0B_COLS
    raise ValueError(f"Spec desconocida: {spec}")


def load_behavioral_wide_frame(path: Path) -> pl.DataFrame:
    cols = existing_columns(path)
    metadata_cols = [c for c in OPTIONAL_METADATA_COLS if c in cols]
    base_select = list(dict.fromkeys(
        ["id_tarjeta"] + BEHAVIORAL_WIDE_BASE_RAW_COLS + TARGET_CONTEXT_COLS + metadata_cols
    ))
    missing_base = [c for c in base_select if c not in cols]
    if missing_base:
        raise ValueError(f"Faltan columnas base en {path.name}: {missing_base}")

    daily_cols = existing_columns(DAILY_TOUR_ARTIFACT_PATH)
    required_daily = ["id_tarjeta"] + DAILY_TOUR_MAIN_COLS
    missing_daily = [c for c in required_daily if c not in daily_cols]
    if missing_daily:
        raise ValueError(f"Faltan columnas daily-tour: {missing_daily}")

    base_lf = (
        pl.scan_parquet(path)
        .select(base_select)
        .with_columns(
            [
                pl.col("n_viajes").cast(pl.Float64).log1p().alias("log1p_n_viajes"),
                pl.col("rhythm_mean_gap_active_days")
                .cast(pl.Float64)
                .log1p()
                .alias("log1p_rhythm_mean_gap_active_days"),
            ]
        )
    )
    daily_lf = pl.scan_parquet(DAILY_TOUR_ARTIFACT_PATH).select(required_daily)
    return base_lf.join(daily_lf, on="id_tarjeta", how="left").collect()


def impute_feature_nulls(df: pl.DataFrame, features: list[str]) -> tuple[pl.DataFrame, pd.DataFrame]:
    rows = []
    exprs = []
    n = df.height
    for feature in features:
        s = df.get_column(feature)
        null_count = int(s.null_count())
        nan_count = int(s.is_nan().sum()) if s.dtype.is_float() else 0
        median = df.select(pl.col(feature).median()).item()
        if median is None or (isinstance(median, float) and np.isnan(median)):
            raise ValueError(f"No se puede imputar {feature}: mediana invalida")
        rows.append(
            {
                "feature": feature,
                "missing_before": null_count + nan_count,
                "missing_rate_before": (null_count + nan_count) / n,
                "median_imputation": float(median),
            }
        )
        expr = pl.col(feature).cast(pl.Float64)
        expr = expr.fill_null(float(median))
        expr = pl.when(expr.is_nan()).then(float(median)).otherwise(expr).alias(feature)
        exprs.append(expr)

    out = df.with_columns(exprs)
    for row in rows:
        feature = row["feature"]
        s = out.get_column(feature)
        null_count = int(s.null_count())
        nan_count = int(s.is_nan().sum()) if s.dtype.is_float() else 0
        row["missing_after"] = null_count + nan_count
    return out, pd.DataFrame(rows)


def upsert_inventory(row: dict, inventory_path: Path) -> None:
    if inventory_path.exists():
        inventory = pd.read_csv(inventory_path)
        keep = ~(
            (inventory["variant_id"] == row["variant_id"])
            & (inventory["branch_id"] == row["branch_id"])
        )
        inventory = inventory.loc[keep].copy()
        inventory = pd.concat([inventory, pd.DataFrame([row])], ignore_index=True)
    else:
        inventory = pd.DataFrame([row])
    inventory = inventory.sort_values(["variant_id", "branch_id"]).reset_index(drop=True)
    inventory.to_csv(inventory_path, index=False)


def write_feature_metadata(spec: str, branch_id: str, out_dir: Path) -> None:
    metadata = pd.DataFrame(BEHAVIORAL_WIDE_MAIN_METADATA)
    metadata["spec"] = spec
    metadata["branch_id"] = branch_id
    metadata["spec_role"] = metadata["variable"].map(
        lambda c: "sensitivity_drop" if spec == "v0b" and c in BEHAVIORAL_WIDE_V0B_DROP_REASONS else f"{spec}_main"
    )
    metadata["v0b_drop_reason"] = metadata["variable"].map(BEHAVIORAL_WIDE_V0B_DROP_REASONS)
    metadata.to_csv(out_dir / f"{branch_id}_feature_metadata.csv", index=False)


def build_spec(universe: str, spec: str, out_dir: Path, force: bool) -> None:
    input_path = UNIVERSE_PATHS[universe]
    if not input_path.exists():
        raise FileNotFoundError(f"No existe universo {universe}: {input_path}")

    branch_id = f"{spec}_{universe}"
    feature_dir = out_dir / "features" / VARIANT_ID
    feature_dir.mkdir(parents=True, exist_ok=True)
    output_path = feature_dir / f"{branch_id}.parquet"
    if output_path.exists() and not force:
        raise FileExistsError(f"Ya existe {output_path}. Usar --force para sobrescribir.")

    features = spec_features(spec)
    df = load_behavioral_wide_frame(input_path)
    df, imputation = impute_feature_nulls(df, features)

    output_cols = list(dict.fromkeys(["id_tarjeta"] + features + TARGET_CONTEXT_COLS + OPTIONAL_METADATA_COLS))
    output_cols = [c for c in output_cols if c in df.columns]
    df.select(output_cols).write_parquet(output_path)

    inventory_path = out_dir / "behavioral_wide_feature_matrix_inventory.csv"
    upsert_inventory(
        {
            "variant_id": VARIANT_ID,
            "branch_id": branch_id,
            "universe": universe,
            "spec": spec,
            "n_rows": df.height,
            "n_features": len(features),
            "features": ",".join(features),
            "feature_path": str(output_path),
        },
        inventory_path,
    )

    imputation_path = out_dir / "features" / VARIANT_ID / f"{branch_id}_imputation_summary.csv"
    imputation.to_csv(imputation_path, index=False)
    write_feature_metadata(spec, branch_id, out_dir)

    run_meta = {
        "variant_id": VARIANT_ID,
        "branch_id": branch_id,
        "universe": universe,
        "spec": spec,
        "input_path": str(input_path),
        "daily_tour_artifact_path": str(DAILY_TOUR_ARTIFACT_PATH),
        "output_path": str(output_path),
        "inventory_path": str(inventory_path),
        "imputation_path": str(imputation_path),
        "features": features,
    }
    (out_dir / "features" / VARIANT_ID / f"{branch_id}_run_meta.json").write_text(
        json.dumps(run_meta, indent=2),
        encoding="utf-8",
    )
    print(f"[build] {branch_id}: rows={df.height:,} features={len(features)} -> {output_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", choices=sorted(UNIVERSE_PATHS), default="alta_n3")
    parser.add_argument("--spec", choices=["v0", "v0b", "both"], default="v0b")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    specs = ["v0", "v0b"] if args.spec == "both" else [args.spec]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        build_spec(args.universe, spec, args.out_dir, args.force)


if __name__ == "__main__":
    main()
