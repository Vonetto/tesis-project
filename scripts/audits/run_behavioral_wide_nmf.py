"""Run NMF over behavioral_wide user-level segmentation features.

This runner is specific to the audited `behavioral_wide` matrices. It applies
the NMF-safe transformation documented in the user-level segmentation notes:

    clip(p01, p99) + minmax [0, 1] + block weight.

The raw behavioral_wide parquet remains unchanged. Transformation parameters
are saved with the model outputs so runs are reproducible.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

# Keep BLAS conservative before importing numpy/sklearn through the NMF helpers.
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl

from scripts.audits.run_user_nmf_segmentation import (
    parse_k_range,
    run_nmf_grid,
    sample_indices,
)


SEG_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation"
DEFAULT_INPUT_DIR = SEG_DIR / "features"
DEFAULT_INVENTORY = SEG_DIR / "behavioral_wide_feature_matrix_inventory.csv"
DEFAULT_OUT_DIR = SEG_DIR / "models"
VARIANT_ID = "behavioral_wide"
DEFAULT_TRANSFORM_ID = "robust_minmax_block_p01_p99"


def load_feature_list(inventory_path: Path, variant_id: str, branch_id: str) -> list[str]:
    inventory = pd.read_csv(inventory_path)
    row = inventory.loc[
        (inventory["variant_id"] == variant_id)
        & (inventory["branch_id"] == branch_id)
    ]
    if row.empty:
        raise SystemExit(f"No entry in inventory: {variant_id} | {branch_id}")
    return [f.strip() for f in row.iloc[0]["features"].split(",") if f.strip()]


def load_block_map(metadata_path: Path, features: list[str]) -> dict[str, str]:
    metadata = pd.read_csv(metadata_path)
    by_var = metadata.set_index("variable")["block"].to_dict()
    missing = [feature for feature in features if feature not in by_var]
    if missing:
        raise SystemExit(f"Features without block metadata: {missing}")
    return {feature: by_var[feature] for feature in features}


def build_transform_params(
    df: pl.DataFrame,
    features: list[str],
    block_map: dict[str, str],
    lower_q: float,
    upper_q: float,
) -> pd.DataFrame:
    block_counts: dict[str, int] = {}
    for feature in features:
        block = block_map[feature]
        block_counts[block] = block_counts.get(block, 0) + 1

    rows: list[dict] = []
    for feature in features:
        series = df.get_column(feature).cast(pl.Float64)
        p_low = float(series.quantile(lower_q))
        p_high = float(series.quantile(upper_q))
        if not np.isfinite(p_low) or not np.isfinite(p_high):
            raise ValueError(f"Invalid quantiles for {feature}: {p_low}, {p_high}")
        block = block_map[feature]
        block_weight = 1.0 / math.sqrt(block_counts[block])
        denom = p_high - p_low
        rows.append(
            {
                "feature": feature,
                "block": block,
                "lower_q": lower_q,
                "upper_q": upper_q,
                "p_low": p_low,
                "p_high": p_high,
                "denominator": denom,
                "is_constant_after_clip": bool(denom <= 0),
                "block_n_features": block_counts[block],
                "block_weight": block_weight,
            }
        )
    return pd.DataFrame(rows)


def transform_matrix(df: pl.DataFrame, features: list[str], params: pd.DataFrame) -> np.ndarray:
    params = params.set_index("feature").loc[features]
    x = df.select(features).to_numpy().astype(np.float32, copy=False)
    low = params["p_low"].to_numpy(dtype=np.float32)
    high = params["p_high"].to_numpy(dtype=np.float32)
    denom = params["denominator"].to_numpy(dtype=np.float32)
    weights = params["block_weight"].to_numpy(dtype=np.float32)

    x = np.clip(x, low, high)
    valid = denom > 0
    x_scaled = np.zeros_like(x, dtype=np.float32)
    x_scaled[:, valid] = (x[:, valid] - low[valid]) / denom[valid]
    x_scaled = np.clip(x_scaled, 0.0, 1.0)
    x_scaled *= weights

    if not np.isfinite(x_scaled).all():
        raise ValueError("Transformed matrix contains non-finite values")
    min_value = float(np.min(x_scaled))
    if min_value < -1e-8:
        raise ValueError(f"NMF requires non-negative matrix; min={min_value}")
    return x_scaled


def transformed_summary(x: np.ndarray, features: list[str], block_map: dict[str, str]) -> pd.DataFrame:
    rows: list[dict] = []
    for j, feature in enumerate(features):
        col = x[:, j]
        rows.append(
            {
                "feature": feature,
                "block": block_map[feature],
                "mean": float(np.mean(col)),
                "std": float(np.std(col)),
                "min": float(np.min(col)),
                "p01": float(np.quantile(col, 0.01)),
                "p05": float(np.quantile(col, 0.05)),
                "p25": float(np.quantile(col, 0.25)),
                "median": float(np.quantile(col, 0.50)),
                "p75": float(np.quantile(col, 0.75)),
                "p95": float(np.quantile(col, 0.95)),
                "p99": float(np.quantile(col, 0.99)),
                "max": float(np.max(col)),
                "share_zero": float(np.mean(col == 0)),
            }
        )
    return pd.DataFrame(rows)


def run_from_args(args: argparse.Namespace) -> Path:
    input_path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    if not input_path.exists():
        raise FileNotFoundError(f"No existe matriz behavioral_wide: {input_path}")

    features = load_feature_list(args.inventory_path, args.variant_id, args.branch_id)
    metadata_path = args.metadata_path or (SEG_DIR / f"{args.branch_id}_feature_metadata.csv")
    block_map = load_block_map(metadata_path, features)

    print(f"[load] {input_path} features={len(features)}", flush=True)
    df = pl.read_parquet(input_path, columns=["id_tarjeta", *features])
    null_counts = df.select([pl.col(c).null_count().alias(c) for c in features]).row(0, named=True)
    bad_nulls = {k: v for k, v in null_counts.items() if v}
    if bad_nulls:
        raise ValueError(f"Features with nulls before NMF transform: {bad_nulls}")

    params = build_transform_params(df, features, block_map, args.lower_q, args.upper_q)
    x = transform_matrix(df, features, params)
    ids = df["id_tarjeta"]
    ks = parse_k_range(args.k_range)

    out_dir = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}"
    nmf_dir = out_dir / "nmf"
    nmf_dir.mkdir(parents=True, exist_ok=True)

    params.to_csv(nmf_dir / "nmf_transform_parameters.csv", index=False)
    transformed_summary(x, features, block_map).to_csv(
        nmf_dir / "nmf_transformed_feature_summary.csv",
        index=False,
    )

    fit_sample_size = args.fit_sample_size if args.fit_sample_size > 0 else None
    idx = sample_indices(x.shape[0], fit_sample_size, args.seed)
    sample_fro_norm = float(np.linalg.norm(x[idx]))

    metrics, top_features, diagnostic = run_nmf_grid(
        x,
        ids,
        features,
        ks=ks,
        n_runs=args.n_runs,
        seed=args.seed,
        fit_sample_size=fit_sample_size,
        max_iter=args.max_iter,
        tol=args.tol,
        blas_threads=args.blas_threads,
        out_dir=nmf_dir,
        top_n=args.top_n,
        save_scores=not args.no_save_scores,
    )
    if sample_fro_norm > 0:
        metrics["relative_best_reconstruction_error"] = (
            metrics["best_reconstruction_error"] / sample_fro_norm
        )
        metrics["relative_mean_reconstruction_error"] = (
            metrics["mean_reconstruction_error"] / sample_fro_norm
        )
    metrics.to_csv(nmf_dir / "nmf_metrics.csv", index=False)
    top_features.to_csv(nmf_dir / "nmf_top_features.csv", index=False)

    run_meta = {
        "variant_id": args.variant_id,
        "branch_id": args.branch_id,
        "input_path": str(input_path),
        "inventory_path": str(args.inventory_path),
        "metadata_path": str(metadata_path),
        "features": features,
        "transform_id": args.transform_id,
        "feature_tag": args.feature_tag,
        "lower_q": args.lower_q,
        "upper_q": args.upper_q,
        "block_weighting": "1/sqrt(n_features_in_block)",
        "k_range": ks,
        "n_runs": args.n_runs,
        "seed": args.seed,
        "fit_sample_size": args.fit_sample_size,
        "sample_fro_norm": sample_fro_norm,
        "max_iter": args.max_iter,
        "tol": args.tol,
        "save_scores": not args.no_save_scores,
        **diagnostic,
    }
    (nmf_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    print(f"OK outputs: {nmf_dir}", flush=True)
    return nmf_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NMF over behavioral_wide matrices.")
    parser.add_argument("--variant-id", default=VARIANT_ID)
    parser.add_argument("--branch-id", default="v0b_alta_n3")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--metadata-path", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--transform-id", default=DEFAULT_TRANSFORM_ID)
    parser.add_argument("--feature-tag", default="nmf_v0b_robust_minmax_block")
    parser.add_argument("--lower-q", type=float, default=0.01)
    parser.add_argument("--upper-q", type=float, default=0.99)
    parser.add_argument("--k-range", default="2-8")
    parser.add_argument("--n-runs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260527)
    parser.add_argument("--fit-sample-size", type=int, default=300_000, help="0 = fit on full matrix.")
    parser.add_argument("--max-iter", type=int, default=500)
    parser.add_argument("--tol", type=float, default=1e-4)
    parser.add_argument("--blas-threads", type=int, default=1)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--no-save-scores", action="store_true")
    args = parser.parse_args()
    run_from_args(args)


if __name__ == "__main__":
    main()
