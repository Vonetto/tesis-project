"""Evaluate hard NMF segment quality for behavioral_wide runs.

These metrics are diagnostic only. NMF is a parts-based reconstruction model,
so compact hard-cluster metrics such as silhouette are useful stress tests, not
the objective that the model optimized.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

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
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

from scripts.audits.run_behavioral_wide_nmf import (
    DEFAULT_INPUT_DIR,
    DEFAULT_INVENTORY,
    DEFAULT_OUT_DIR,
    VARIANT_ID,
    load_feature_list,
    parse_k_range,
    transform_matrix,
)


def sample_positions(n: int, sample_size: int, seed: int) -> np.ndarray:
    if sample_size <= 0 or sample_size >= n:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=sample_size, replace=False))


def evaluate_from_args(args: argparse.Namespace) -> Path:
    matrix_path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    nmf_dir = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}" / "nmf"
    assignments_path = nmf_dir / "nmf_assignments.parquet"
    params_path = nmf_dir / "nmf_transform_parameters.csv"
    metrics_path = nmf_dir / "nmf_metrics.csv"

    if not matrix_path.exists():
        raise FileNotFoundError(f"No existe matriz: {matrix_path}")
    if not assignments_path.exists():
        raise FileNotFoundError(f"No existen asignaciones: {assignments_path}")
    if not params_path.exists():
        raise FileNotFoundError(f"No existen parametros de transformacion: {params_path}")

    features = load_feature_list(args.inventory_path, args.variant_id, args.branch_id)
    df = pl.read_parquet(matrix_path, columns=["id_tarjeta", *features])
    assignments = pl.read_parquet(assignments_path)
    if df.height != assignments.height:
        raise ValueError(f"Row mismatch: matrix={df.height} assignments={assignments.height}")
    if df.get_column("id_tarjeta").to_list() != assignments.get_column("id_tarjeta").to_list():
        raise ValueError("id_tarjeta order differs between matrix and assignments")

    params = pd.read_csv(params_path)
    x = transform_matrix(df, features, params)
    quality_idx = sample_positions(x.shape[0], args.quality_sample_size, args.seed)
    sil_idx = sample_positions(quality_idx.size, args.silhouette_sample_size, args.seed + 101)
    x_quality = x[quality_idx]
    x_sil = x_quality[sil_idx]

    nmf_metrics = pd.read_csv(metrics_path) if metrics_path.exists() else pd.DataFrame()
    nmf_by_k = nmf_metrics.set_index("k").to_dict(orient="index") if not nmf_metrics.empty else {}

    rows: list[dict] = []
    ks = parse_k_range(args.k_range)
    for k in ks:
        label_col = f"segment_k{k}"
        if label_col not in assignments.columns:
            continue
        labels_full = assignments.get_column(label_col).to_numpy()
        labels_quality = labels_full[quality_idx]
        labels_sil = labels_quality[sil_idx]
        unique_labels = np.unique(labels_quality)
        if unique_labels.size < 2:
            continue

        counts = np.bincount(labels_full.astype(int), minlength=k)
        quality_counts = np.bincount(labels_quality.astype(int), minlength=k)
        row = {
            "k": k,
            "n_full": int(labels_full.size),
            "n_quality_sample": int(x_quality.shape[0]),
            "n_silhouette_sample": int(x_sil.shape[0]),
            "full_min_segment_share": float(counts.min() / counts.sum()),
            "full_max_segment_share": float(counts.max() / counts.sum()),
            "sample_min_segment_share": float(quality_counts.min() / quality_counts.sum()),
            "sample_max_segment_share": float(quality_counts.max() / quality_counts.sum()),
            "silhouette_euclidean": float(silhouette_score(x_sil, labels_sil, metric="euclidean")),
            "silhouette_cosine": float(silhouette_score(x_sil, labels_sil, metric="cosine")),
            "calinski_harabasz": float(calinski_harabasz_score(x_quality, labels_quality)),
            "davies_bouldin": float(davies_bouldin_score(x_quality, labels_quality)),
        }
        for key in [
            "relative_best_reconstruction_error",
            "stability_pairwise_ari_mean",
            "sample_assignment_entropy_mean",
        ]:
            if k in nmf_by_k and key in nmf_by_k[k]:
                row[key] = nmf_by_k[k][key]
        rows.append(row)

    out = pd.DataFrame(rows)
    out_path = nmf_dir / "nmf_hard_segment_quality.csv"
    out.to_csv(out_path, index=False)
    print(f"OK quality metrics: {out_path}", flush=True)
    print(out.to_string(index=False), flush=True)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate behavioral_wide NMF hard segment quality.")
    parser.add_argument("--variant-id", default=VARIANT_ID)
    parser.add_argument("--branch-id", default="v0b_alta_n3")
    parser.add_argument("--feature-tag", default="nmf_v0b_robust_minmax_block")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--k-range", default="2-8")
    parser.add_argument("--quality-sample-size", type=int, default=100_000)
    parser.add_argument("--silhouette-sample-size", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20260604)
    args = parser.parse_args()
    evaluate_from_args(args)


if __name__ == "__main__":
    main()
