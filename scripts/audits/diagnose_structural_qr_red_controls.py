"""Post-hoc QR_RED control diagnostics for structural_wide matrices.

This script estimates nested binary logits to diagnose whether the QR_RED
association is carried by residential macrozone, socio-residential composition,
or access/supply controls. It is descriptive, not causal.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import train_test_split


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEG_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation"
DEFAULT_INPUT_DIR = SEG_DIR / "features"
DEFAULT_OUT_DIR = SEG_DIR / "models"
VARIANT_ID = "structural_wide"

OUTCOME = "is_qr_red"
REFERENCE_MACROZONE = "home_macro_poniente"

MACRO_ORIENTE = ["home_macro_oriente"]
MACRO_BLOCK = [
    # home_macro_poniente is the omitted reference category.
    "home_macro_oriente",
    "home_macro_centro",
    "home_macro_sur",
    "home_macro_suroriente",
    "home_macro_norte",
    "home_macro_externa_especial",
]
SOCIO_CORE = [
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
]
SOCIO_FULL = SOCIO_CORE + [
    "res_share_discapacidad_z",
    "res_share_inmigrantes_z",
    "res_share_asistencia_parv_z",
    "res_age_share_18_24",
    "res_age_share_25_44",
]
ACCESS_OFFER = [
    "home_bip_load_density_km2",
    "home_bip_load_dist_nearest_m",
    "origin_top1_bip_load_density_km2",
    "origin_top1_bip_load_dist_nearest_m",
    "offer_log_bus_stop_density_origin_mean",
    "offer_log_metro_station_density_origin_mean",
    "offer_origin_bus_like_share",
    "offer_origin_metro_like_share",
    "offer_bus_origin_headway_all_min_mean",
    "offer_bus_origin_headway_ge10_share",
]

SPECS = {
    "M1_oriente_only": MACRO_ORIENTE,
    "M1b_macro_block_ref_poniente": MACRO_BLOCK,
    "M2_socio_core": SOCIO_CORE,
    "M3_oriente_socio_core": MACRO_ORIENTE + SOCIO_CORE,
    "M4_macro_socio_full": MACRO_BLOCK + SOCIO_FULL,
    "M5_macro_socio_access_offer": MACRO_BLOCK + SOCIO_FULL + ACCESS_OFFER,
}

BINARY_FEATURES = set(MACRO_BLOCK)
FOCAL_EFFECT_FEATURES = [
    "home_macro_oriente",
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
]


def unique_features() -> list[str]:
    out: list[str] = []
    for features in SPECS.values():
        for feature in features:
            if feature not in out:
                out.append(feature)
    return out


def prepare_design(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    continuous = [f for f in features if f not in BINARY_FEATURES]
    x_train = train[features].copy()
    x_test = test[features].copy()

    medians = x_train.median(numeric_only=True)
    x_train = x_train.fillna(medians)
    x_test = x_test.fillna(medians)

    means = x_train[continuous].mean() if continuous else pd.Series(dtype=float)
    stds = x_train[continuous].std(ddof=0).replace(0, 1) if continuous else pd.Series(dtype=float)
    if continuous:
        x_train[continuous] = (x_train[continuous] - means) / stds
        x_test[continuous] = (x_test[continuous] - means) / stds

    transform = {
        "continuous_features": continuous,
        "binary_features": [f for f in features if f in BINARY_FEATURES],
        "medians": medians.to_dict(),
        "means": means.to_dict(),
        "stds": stds.to_dict(),
    }
    return x_train, x_test, transform


def apply_transform(raw: pd.DataFrame, features: list[str], transform: dict) -> pd.DataFrame:
    continuous = transform["continuous_features"]
    out = raw[features].copy()
    out = out.fillna(pd.Series(transform["medians"]))
    for feature in continuous:
        out[feature] = (out[feature] - transform["means"][feature]) / transform["stds"][feature]
    return out


def marginal_effects(
    model: LogisticRegression,
    raw_test: pd.DataFrame,
    features: list[str],
    transform: dict,
) -> list[dict]:
    rows: list[dict] = []
    baseline = model.predict_proba(apply_transform(raw_test, features, transform))[:, 1].mean()
    for feature in FOCAL_EFFECT_FEATURES:
        if feature not in features:
            continue
        lo = raw_test.copy()
        hi = raw_test.copy()
        if feature in BINARY_FEATURES:
            lo[feature] = 0
            hi[feature] = 1
            scale = "0_to_1"
        else:
            hi[feature] = hi[feature] + 1.0
            scale = "plus_1_raw_unit"

        pred_lo = model.predict_proba(apply_transform(lo, features, transform))[:, 1].mean()
        pred_hi = model.predict_proba(apply_transform(hi, features, transform))[:, 1].mean()
        rows.append(
            {
                "feature": feature,
                "effect_scale": scale,
                "baseline_pred_mean": baseline,
                "pred_lo_mean": pred_lo,
                "pred_hi_mean": pred_hi,
                "avg_probability_diff": pred_hi - pred_lo,
            }
        )
    return rows


def run_from_args(args: argparse.Namespace) -> Path:
    matrix_path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    if not matrix_path.exists():
        raise FileNotFoundError(f"No existe matriz: {matrix_path}")

    required_cols = ["id_tarjeta", OUTCOME] + unique_features()
    available = set(pl.read_parquet_schema(matrix_path).names())
    missing = [c for c in required_cols if c not in available]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    df = pl.read_parquet(matrix_path, columns=required_cols).to_pandas()
    df[OUTCOME] = df[OUTCOME].astype(int)
    if 0 < args.sample_size < len(df):
        df = df.sample(n=args.sample_size, random_state=args.seed)

    train, test = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=df[OUTCOME],
    )

    out_dir = args.out_dir / args.variant_id / f"{args.branch_id}__qr_red_controls"
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics: list[dict] = []
    coef_rows: list[dict] = []
    effect_rows: list[dict] = []

    for spec_name, features in SPECS.items():
        print(f"[fit] {spec_name} features={len(features)}", flush=True)
        x_train, x_test, transform = prepare_design(train, test, features)
        model = LogisticRegression(
            penalty="l2",
            C=args.c,
            solver="lbfgs",
            max_iter=args.max_iter,
            class_weight=None,
            random_state=args.seed,
        )
        model.fit(x_train, train[OUTCOME])
        pred = model.predict_proba(x_test)[:, 1]

        metrics.append(
            {
                "model": spec_name,
                "n_features": len(features),
                "n_train": len(train),
                "n_test": len(test),
                "qr_red_rate_test": float(test[OUTCOME].mean()),
                "auc": float(roc_auc_score(test[OUTCOME], pred)),
                "average_precision": float(average_precision_score(test[OUTCOME], pred)),
                "log_loss": float(log_loss(test[OUTCOME], pred)),
                "brier": float(brier_score_loss(test[OUTCOME], pred)),
            }
        )

        for feature, coef in zip(features, model.coef_[0]):
            scale = "0_to_1" if feature in BINARY_FEATURES else "per_1sd_train"
            coef_rows.append(
                {
                    "model": spec_name,
                    "feature": feature,
                    "effect_scale": scale,
                    "logit_coef": float(coef),
                    "odds_ratio": float(np.exp(coef)),
                    "abs_logit_coef": float(abs(coef)),
                }
            )

        for row in marginal_effects(model, test, features, transform):
            row["model"] = spec_name
            effect_rows.append(row)

    metrics_df = pd.DataFrame(metrics)
    coef_df = pd.DataFrame(coef_rows)
    effects_df = pd.DataFrame(effect_rows)
    metrics_df.to_csv(out_dir / "qr_red_nested_logit_metrics.csv", index=False)
    coef_df.to_csv(out_dir / "qr_red_nested_logit_coefficients.csv", index=False)
    effects_df.to_csv(out_dir / "qr_red_nested_logit_marginal_effects.csv", index=False)

    run_meta = {
        "variant_id": args.variant_id,
        "branch_id": args.branch_id,
        "matrix_path": str(matrix_path),
        "outcome": OUTCOME,
        "sample_size": len(df),
        "test_size": args.test_size,
        "seed": args.seed,
        "reference_macrozone": REFERENCE_MACROZONE,
        "specs": SPECS,
        "note": "Post-hoc diagnostic only; coefficients are associations, not causal effects.",
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    print("\nMETRICS", flush=True)
    print(metrics_df.to_string(index=False), flush=True)
    print("\nFOCAL MARGINAL EFFECTS", flush=True)
    print(effects_df.to_string(index=False), flush=True)
    print(f"\nOK outputs: {out_dir}", flush=True)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run post-hoc QR_RED control diagnostics.")
    parser.add_argument("--variant-id", default=VARIANT_ID)
    parser.add_argument("--branch-id", default="v1_alta_n3")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--sample-size", type=int, default=1_000_000, help="0 = full matrix.")
    parser.add_argument("--test-size", type=float, default=0.35)
    parser.add_argument("--seed", type=int, default=20260608)
    parser.add_argument("--max-iter", type=int, default=2000)
    parser.add_argument("--c", type=float, default=1.0)
    args = parser.parse_args()
    run_from_args(args)


if __name__ == "__main__":
    main()
