"""Run NMF over user-level mobility segmentation matrices."""
from __future__ import annotations

# Limit BLAS before importing numpy/sklearn. This project has hit OpenBLAS
# thread issues in larch-env when sklearn is allowed to spawn many threads.
import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import itertools
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl
from sklearn.decomposition import NMF
from sklearn.metrics import adjusted_rand_score
from threadpoolctl import threadpool_limits

from scripts.audits.build_user_mobility_segmentation_matrix import (
    OUT_DIR as MATRIX_DIR,
    inventory_path,
    min_across_columns,
    matrix_stem,
    output_path as matrix_output_path,
)


SEG_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation"
NMF_DIR = SEG_DIR / "nmf"


@dataclass
class NMFRunResult:
    k: int
    seed: int
    model: NMF
    w_sample: np.ndarray
    h: np.ndarray
    reconstruction_error: float
    fit_seconds: float
    labels_sample: np.ndarray


def parse_k_range(value: str) -> list[int]:
    text = str(value).strip()
    if "-" in text:
        left, right = text.split("-", 1)
        start = int(left)
        end = int(right)
        if start > end:
            raise ValueError(f"k-range invalido: {value}")
        return list(range(start, end + 1))
    ks = sorted({int(x.strip()) for x in text.split(",") if x.strip()})
    if not ks:
        raise ValueError("k-range vacio")
    return ks


def detect_elbow(ks: list[int], errors: list[float]) -> dict:
    if len(ks) < 3:
        return {"elbow_d2_k": None, "elbow_segment_k": None, "elbow_consensus_k": None}
    ks_arr = np.asarray(ks, dtype=float)
    err_arr = np.asarray(errors, dtype=float)

    d2 = np.full_like(err_arr, np.nan)
    d2[1:-1] = err_arr[:-2] - 2 * err_arr[1:-1] + err_arr[2:]
    idx_d2 = int(np.nanargmax(d2[1:-1])) + 1
    elbow_d2_k = int(ks_arr[idx_d2])

    p0 = np.array([ks_arr[0], err_arr[0]])
    p1 = np.array([ks_arr[-1], err_arr[-1]])
    seg = p1 - p0
    seg_norm = np.linalg.norm(seg)
    distances = np.zeros_like(err_arr)
    for i, k in enumerate(ks_arr):
        p = np.array([k, err_arr[i]])
        distances[i] = abs((seg[0] * (p0[1] - p[1])) - (p0[0] - p[0]) * seg[1]) / seg_norm
    elbow_segment_k = int(ks_arr[int(np.argmax(distances))])
    consensus = elbow_d2_k if elbow_d2_k == elbow_segment_k else elbow_segment_k
    return {
        "elbow_d2_k": elbow_d2_k,
        "elbow_segment_k": elbow_segment_k,
        "elbow_consensus_k": consensus,
    }


def load_inventory(matrix_path: Path) -> dict:
    path = inventory_path(matrix_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe inventario de features: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_matrix_and_features(matrix_path: Path) -> tuple[pl.DataFrame, list[str], dict]:
    inv = load_inventory(matrix_path)
    feature_cols = list(inv["feature_cols"])
    if not feature_cols:
        raise ValueError("Inventario sin feature_cols")
    df = pl.read_parquet(matrix_path, columns=["id_tarjeta", *feature_cols])
    nulls = df.select([pl.col(c).null_count().alias(c) for c in feature_cols]).row(0, named=True)
    bad_nulls = {k: v for k, v in nulls.items() if v}
    if bad_nulls:
        raise ValueError(f"Features con nulls antes de NMF: {bad_nulls}")
    min_value = min_across_columns(df, feature_cols)
    if min_value < 0:
        raise ValueError(f"NMF requiere no negativos; min={min_value}")
    return df, feature_cols, inv


def to_float32_matrix(df: pl.DataFrame, feature_cols: list[str]) -> np.ndarray:
    return df.select(feature_cols).to_numpy().astype(np.float32, copy=False)


def sample_indices(n: int, sample_size: int | None, seed: int) -> np.ndarray:
    if sample_size is None or sample_size <= 0 or sample_size >= n:
        return np.arange(n)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=sample_size, replace=False))


def row_entropy(weights: np.ndarray) -> np.ndarray:
    denom = weights.sum(axis=1, keepdims=True)
    probs = np.divide(weights, denom, out=np.zeros_like(weights), where=denom > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.where(probs > 0, np.log(probs), 0.0)
    return -np.sum(probs * logp, axis=1)


def fit_one_nmf(X_sample: np.ndarray, k: int, seed: int, max_iter: int, tol: float, blas_threads: int) -> NMFRunResult:
    t0 = time.perf_counter()
    with threadpool_limits(limits=blas_threads):
        model = NMF(
            n_components=k,
            init="random",
            random_state=seed,
            max_iter=max_iter,
            tol=tol,
            solver="cd",
            beta_loss="frobenius",
        )
        w_sample = model.fit_transform(X_sample)
    fit_seconds = time.perf_counter() - t0
    labels = w_sample.argmax(axis=1).astype(np.int16)
    return NMFRunResult(
        k=k,
        seed=seed,
        model=model,
        w_sample=w_sample,
        h=model.components_.astype(np.float32, copy=True),
        reconstruction_error=float(model.reconstruction_err_),
        fit_seconds=fit_seconds,
        labels_sample=labels,
    )


def pairwise_ari(labels: list[np.ndarray]) -> float:
    if len(labels) < 2:
        return float("nan")
    scores = [adjusted_rand_score(a, b) for a, b in itertools.combinations(labels, 2)]
    return float(np.mean(scores)) if scores else float("nan")


def top_features_rows(k: int, h: np.ndarray, feature_cols: list[str], top_n: int) -> list[dict]:
    rows: list[dict] = []
    for component_idx in range(h.shape[0]):
        weights = h[component_idx]
        total = float(weights.sum())
        order = np.argsort(weights)[::-1][:top_n]
        for rank, j in enumerate(order, start=1):
            rows.append(
                {
                    "k": k,
                    "component": component_idx,
                    "rank": rank,
                    "feature": feature_cols[int(j)],
                    "weight": float(weights[int(j)]),
                    "weight_share_component": float(weights[int(j)] / total) if total > 0 else 0.0,
                }
            )
    return rows


def run_nmf_grid(
    X: np.ndarray,
    ids: pl.Series,
    feature_cols: list[str],
    *,
    ks: list[int],
    n_runs: int,
    seed: int,
    fit_sample_size: int | None,
    max_iter: int,
    tol: float,
    blas_threads: int,
    out_dir: Path,
    top_n: int,
    save_scores: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    idx = sample_indices(X.shape[0], fit_sample_size, seed)
    X_sample = X[idx]
    metrics_rows: list[dict] = []
    top_rows: list[dict] = []
    assignments = pl.DataFrame({"id_tarjeta": ids})
    best_models: dict[int, NMFRunResult] = {}

    for k in ks:
        run_results: list[NMFRunResult] = []
        for run_idx in range(n_runs):
            run_seed = seed + (k * 1000) + run_idx
            result = fit_one_nmf(X_sample, k, run_seed, max_iter, tol, blas_threads)
            run_results.append(result)
            print(
                f"k={k} run={run_idx + 1}/{n_runs} seed={run_seed} "
                f"recon={result.reconstruction_error:.6f} fit={result.fit_seconds:.1f}s",
                flush=True,
            )

        best = min(run_results, key=lambda r: r.reconstruction_error)
        best_models[k] = best
        stability_ari = pairwise_ari([r.labels_sample for r in run_results])
        reconstruction_errors = [r.reconstruction_error for r in run_results]
        entropy = row_entropy(best.w_sample)
        sample_segment_counts = np.bincount(best.labels_sample, minlength=k)
        sample_min_share = float(sample_segment_counts.min() / sample_segment_counts.sum())
        sample_max_share = float(sample_segment_counts.max() / sample_segment_counts.sum())

        with threadpool_limits(limits=blas_threads):
            w_full = best.model.transform(X)
        labels_full = w_full.argmax(axis=1).astype(np.int16)
        full_counts = np.bincount(labels_full, minlength=k)
        full_min_share = float(full_counts.min() / full_counts.sum())
        full_max_share = float(full_counts.max() / full_counts.sum())
        assignments = assignments.with_columns(pl.Series(f"segment_k{k}", labels_full))

        if save_scores:
            score_cols = {f"nmf_k{k}_c{j}": w_full[:, j].astype(np.float32) for j in range(k)}
            pl.DataFrame({"id_tarjeta": ids, **score_cols}).write_parquet(
                out_dir / f"nmf_scores_k{k}.parquet",
                compression="zstd",
            )

        top_rows.extend(top_features_rows(k, best.h, feature_cols, top_n))
        metrics_rows.append(
            {
                "k": k,
                "n_runs": n_runs,
                "fit_sample_n": int(X_sample.shape[0]),
                "best_seed": best.seed,
                "best_reconstruction_error": float(best.reconstruction_error),
                "mean_reconstruction_error": float(np.mean(reconstruction_errors)),
                "std_reconstruction_error": float(np.std(reconstruction_errors)),
                "stability_pairwise_ari_mean": stability_ari,
                "sample_assignment_entropy_mean": float(np.mean(entropy)),
                "sample_min_segment_share": sample_min_share,
                "sample_max_segment_share": sample_max_share,
                "full_min_segment_share": full_min_share,
                "full_max_segment_share": full_max_share,
                "best_fit_seconds": float(best.fit_seconds),
            }
        )

    assignments.write_parquet(out_dir / "nmf_assignments.parquet", compression="zstd")
    metrics = pd.DataFrame(metrics_rows)
    top_features = pd.DataFrame(top_rows)
    elbow = detect_elbow(metrics["k"].tolist(), metrics["best_reconstruction_error"].tolist())
    return metrics, top_features, {"fit_sample_n": int(X_sample.shape[0]), "sample_indices_seed": seed, "elbow": elbow}


def nmf_output_dir(matrix_path: Path) -> Path:
    return NMF_DIR / matrix_path.stem


def run_from_args(args: argparse.Namespace) -> Path:
    matrix_path = matrix_output_path(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
        args.matrix_spec,
        args.normalization,
    )
    if not matrix_path.exists():
        raise FileNotFoundError(f"No existe matriz de segmentacion: {matrix_path}")

    df, feature_cols, inventory = load_matrix_and_features(matrix_path)
    X = to_float32_matrix(df, feature_cols)
    ids = df["id_tarjeta"]
    ks = parse_k_range(args.k_range)

    out_dir = nmf_output_dir(matrix_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics, top_features, diagnostic = run_nmf_grid(
        X,
        ids,
        feature_cols,
        ks=ks,
        n_runs=args.n_runs,
        seed=args.seed,
        fit_sample_size=args.fit_sample_size if args.fit_sample_size > 0 else None,
        max_iter=args.max_iter,
        tol=args.tol,
        blas_threads=args.blas_threads,
        out_dir=out_dir,
        top_n=args.top_n,
        save_scores=not args.no_save_scores,
    )
    metrics.to_csv(out_dir / "nmf_metrics.csv", index=False)
    top_features.to_csv(out_dir / "nmf_top_features.csv", index=False)
    run_meta = {
        "matrix_path": str(matrix_path),
        "inventory": inventory,
        "k_range": ks,
        "n_runs": args.n_runs,
        "seed": args.seed,
        "fit_sample_size": args.fit_sample_size,
        "max_iter": args.max_iter,
        "tol": args.tol,
        "save_scores": not args.no_save_scores,
        **diagnostic,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    print(f"OK outputs: {out_dir}")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NMF on user-level mobility segmentation matrices.")
    parser.add_argument("--scope", default="interannual_ml")
    parser.add_argument("--variant", default="clean")
    parser.add_argument("--home-filter", default="alta")
    parser.add_argument("--min-trips", type=int, default=3)
    parser.add_argument("--min-home-trips", type=int, default=0)
    parser.add_argument("--matrix-spec", default="macro_franja_modo")
    parser.add_argument("--normalization", default="share")
    parser.add_argument("--k-range", default="2-8")
    parser.add_argument("--n-runs", type=int, default=10)
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
