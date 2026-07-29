"""PCA sobre una matriz de features de segmentacion.

Calcula:
- Componentes principales y % varianza explicada acumulada.
- Loadings (correlacion feature -> componente).
- KMeans opcional sobre los primeros K componentes.

Output:
- CSV: pca_loadings.csv, pca_explained_variance.csv
- PNG: pca_scree.png (varianza acumulada), pca_scatter_2d.png (PC1 vs PC2),
       pca_scatter_3d.png (PC1, PC2, PC3 en tres paneles 2D).
- run_meta.json con seed, sample, etc.

Si --with-kmeans:
- Corre KMeans sobre los primeros n_components componentes (default: los que
  acumulan 80% varianza).
- Genera kmeans_pca_metrics.csv, kmeans_pca_assignments.parquet, plots y elbow.
"""

from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import argparse
import json
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "features"
DEFAULT_INVENTORY = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "feature_matrix_inventory.csv"
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"


def load_feature_list(inventory_path: Path, variant_id: str, branch_id: str) -> list[str]:
    inv = pl.read_csv(inventory_path)
    row = inv.filter((pl.col("variant_id") == variant_id) & (pl.col("branch_id") == branch_id))
    if row.height == 0:
        raise SystemExit(f"No entry: {variant_id} | {branch_id}")
    return [f.strip() for f in row["features"][0].split(",") if f.strip()]


def silhouette_subsample(X: np.ndarray, labels: np.ndarray, max_n: int, rng: np.random.Generator) -> tuple[float, int]:
    n = X.shape[0]
    if n <= max_n:
        return float(silhouette_score(X, labels)), n
    idx = rng.choice(n, size=max_n, replace=False)
    return float(silhouette_score(X[idx], labels[idx])), max_n


def detect_elbow(ks: list[int], inertias: list[float]) -> dict:
    if len(ks) < 3:
        return {"elbow_d2_k": None, "elbow_segment_k": None, "elbow_consensus_k": None}
    ks_arr = np.asarray(ks, dtype=float)
    in_arr = np.asarray(inertias, dtype=float)
    d2 = np.full_like(in_arr, np.nan)
    d2[1:-1] = in_arr[:-2] - 2 * in_arr[1:-1] + in_arr[2:]
    interior = d2[1:-1]
    idx_d2 = int(np.nanargmax(interior)) + 1
    elbow_d2_k = int(ks_arr[idx_d2])

    p0 = np.array([ks_arr[0], in_arr[0]])
    p1 = np.array([ks_arr[-1], in_arr[-1]])
    seg = p1 - p0
    seg_norm = np.linalg.norm(seg)
    distances = np.zeros_like(in_arr)
    for i in range(len(ks_arr)):
        p = np.array([ks_arr[i], in_arr[i]])
        distances[i] = abs((seg[0] * (p0[1] - p[1])) - (p0[0] - p[0]) * seg[1]) / seg_norm
    idx_seg = int(np.argmax(distances))
    elbow_segment_k = int(ks_arr[idx_seg])
    consensus = elbow_d2_k if elbow_d2_k == elbow_segment_k else elbow_segment_k
    return {"elbow_d2_k": elbow_d2_k, "elbow_segment_k": elbow_segment_k, "elbow_consensus_k": consensus}


def plot_scree(explained: np.ndarray, cum: np.ndarray, out_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    ks = np.arange(1, len(explained) + 1)
    ax.bar(ks, explained, alpha=0.5, label="% varianza individual")
    ax.plot(ks, cum, marker="o", color="C3", label="% varianza acumulada")
    ax.axhline(0.80, ls="--", color="grey", alpha=0.6, label="80%")
    ax.axhline(0.90, ls=":", color="grey", alpha=0.6, label="90%")
    ax.set_xlabel("Componente principal")
    ax.set_ylabel("% varianza")
    ax.set_title(title)
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_scatter_2d(scores: np.ndarray, out_path: Path, title: str, labels: np.ndarray | None = None) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    if labels is None:
        ax.scatter(scores[:, 0], scores[:, 1], s=2, alpha=0.15, color="C0")
    else:
        for c in np.unique(labels):
            m = labels == c
            ax.scatter(scores[m, 0], scores[m, 1], s=2, alpha=0.2, label=f"k={c}")
        ax.legend(markerscale=4, loc="best", fontsize=8)
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(title)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_scatter_3panels(scores: np.ndarray, out_path: Path, title: str, labels: np.ndarray | None = None) -> None:
    pairs = [(0, 1), (0, 2), (1, 2)]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, (i, j) in zip(axes, pairs):
        if labels is None:
            ax.scatter(scores[:, i], scores[:, j], s=2, alpha=0.15, color="C0")
        else:
            for c in np.unique(labels):
                m = labels == c
                ax.scatter(scores[m, i], scores[m, j], s=2, alpha=0.2, label=f"k={c}")
        ax.set_xlabel(f"PC{i+1}")
        ax.set_ylabel(f"PC{j+1}")
        ax.grid(alpha=0.3)
    if labels is not None:
        axes[-1].legend(markerscale=4, loc="best", fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", default="R2_abs_core_2025")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--include-features", type=str, default="",
                        help="Whitelist explicita; default: usar todas las features del inventario.")
    parser.add_argument("--drop-features", type=str, default="",
                        help="Drop list; default: ninguno.")
    parser.add_argument("--sample-size", type=int, default=100_000,
                        help="Muestra para fit PCA + KMeans. 0 = full population.")
    parser.add_argument("--plot-sample", type=int, default=50_000,
                        help="Sub-muestra solo para scatter plots (densidad visual). 0 = todos.")
    parser.add_argument("--silhouette-sample", type=int, default=50_000)
    parser.add_argument("--n-components", type=int, default=None,
                        help="Cuantos PC retener. Default: auto (umbral 80%).")
    parser.add_argument("--variance-threshold", type=float, default=0.80,
                        help="Umbral para auto-seleccion de n_components.")
    parser.add_argument("--with-kmeans", action="store_true",
                        help="Correr KMeans sobre los PCs retenidos.")
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--n-init", type=int, default=10)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--feature-tag", type=str, default="pca")
    args = parser.parse_args()

    drop_list = [f.strip() for f in args.drop_features.split(",") if f.strip()]
    include_list = [f.strip() for f in args.include_features.split(",") if f.strip()]
    if drop_list and include_list:
        raise SystemExit("No usar --drop y --include juntos.")

    input_path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    if not input_path.exists():
        raise SystemExit(f"No existe: {input_path}")
    df = pl.read_parquet(input_path)
    print(f"[load] {input_path.name} rows={df.height:,} cols={df.width}", flush=True)

    features_full = load_feature_list(args.inventory_path, args.variant_id, args.branch_id)
    if include_list:
        missing = [f for f in include_list if f not in features_full]
        if missing:
            raise SystemExit(f"Whitelist con features ausentes en inventario: {missing}")
        features = include_list
    else:
        features = [f for f in features_full if f not in set(drop_list)]
    print(f"  features ({len(features)}): {features}", flush=True)

    # validar presencia y no-nulls
    missing_cols = [f for f in features if f not in df.columns]
    if missing_cols:
        raise SystemExit(f"Features ausentes en parquet: {missing_cols}")
    for f in features:
        if df[f].null_count() > 0:
            raise SystemExit(f"NULL en feature {f}")

    n_total = df.height
    if args.sample_size and args.sample_size > 0 and df.height > args.sample_size:
        df = df.sample(n=args.sample_size, seed=args.random_seed)
    n_used = df.height
    if args.sample_size == 0 or args.sample_size is None:
        print(f"  fit sobre poblacion completa: {n_used:,}", flush=True)
    else:
        print(f"  sample: {n_used:,} de {n_total:,}", flush=True)

    X = df.select(features).to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA con todos los componentes para diagnostico
    pca_full = PCA(n_components=len(features), random_state=args.random_seed)
    pca_full.fit(X_scaled)
    explained = pca_full.explained_variance_ratio_
    cum = np.cumsum(explained)

    # decidir n_components retenidos
    if args.n_components is not None:
        n_pc = int(args.n_components)
    else:
        n_pc = int(np.searchsorted(cum, args.variance_threshold) + 1)
        n_pc = max(2, n_pc)  # minimo 2 para poder graficar
    print(f"  PCA: {len(features)} features -> {n_pc} componentes (umbral={args.variance_threshold:.0%})", flush=True)
    print(f"  varianza acumulada hasta PC{n_pc}: {cum[n_pc-1]:.3f}", flush=True)

    pca = PCA(n_components=n_pc, random_state=args.random_seed)
    scores = pca.fit_transform(X_scaled)

    # loadings (correlacion feature -> PC)
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    loadings_df = pd.DataFrame(
        loadings,
        index=features,
        columns=[f"PC{i+1}" for i in range(n_pc)],
    )

    # output
    branch_subdir = f"{args.branch_id}__{args.feature_tag}"
    out_path = args.out_dir / args.variant_id / branch_subdir / "pca"
    out_path.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "PC": [f"PC{i+1}" for i in range(len(features))],
        "explained_var_ratio": explained,
        "cumulative_var_ratio": cum,
    }).to_csv(out_path / "pca_explained_variance.csv", index=False)
    loadings_df.to_csv(out_path / "pca_loadings.csv")

    plot_scree(explained, cum, out_path / "pca_scree.png",
               f"{args.variant_id} | {args.branch_id} | {len(features)} features")

    # Sub-muestreo de scores SOLO para plots (densidad visual)
    rng_plot = np.random.default_rng(args.random_seed)
    if args.plot_sample and args.plot_sample > 0 and scores.shape[0] > args.plot_sample:
        plot_idx = rng_plot.choice(scores.shape[0], size=args.plot_sample, replace=False)
        scores_for_plot = scores[plot_idx]
    else:
        plot_idx = np.arange(scores.shape[0])
        scores_for_plot = scores

    if n_pc >= 2:
        plot_scatter_2d(scores_for_plot, out_path / "pca_scatter_2d.png",
                        f"PCA scatter 2D | {args.branch_id} (fit_n={n_used:,}, plot_n={scores_for_plot.shape[0]:,})")
    if n_pc >= 3:
        plot_scatter_3panels(scores_for_plot, out_path / "pca_scatter_3panels.png",
                             f"PCA scatter 3 paneles | {args.branch_id} (fit_n={n_used:,}, plot_n={scores_for_plot.shape[0]:,})")

    print(f"  loadings ({n_pc} PCs):", flush=True)
    print(loadings_df.round(3).to_string(), flush=True)

    run_meta = {
        "variant_id": args.variant_id,
        "branch_id": args.branch_id,
        "feature_tag": args.feature_tag,
        "input_path": str(input_path),
        "n_total": n_total,
        "n_used": n_used,
        "features": features,
        "n_features": len(features),
        "n_components": n_pc,
        "variance_threshold": args.variance_threshold,
        "cumulative_variance_at_n_pc": float(cum[n_pc - 1]),
        "random_seed": args.random_seed,
    }

    # ---- KMeans sobre PCs (opcional) ----
    if args.with_kmeans:
        rng = np.random.default_rng(args.random_seed)
        metrics: list[dict] = []
        assignments = df.select(["id_tarjeta"]).to_pandas()
        for k in range(args.k_min, args.k_max + 1):
            t0 = time.perf_counter()
            with threadpool_limits(limits=1):
                km = KMeans(n_clusters=k, init="k-means++", random_state=args.random_seed,
                            n_init=args.n_init, algorithm="lloyd")
                labels = km.fit_predict(scores)
                fit_s = time.perf_counter() - t0
                sil, sil_n = silhouette_subsample(scores, labels, args.silhouette_sample, rng)
                ch = float(calinski_harabasz_score(scores, labels))
                db = float(davies_bouldin_score(scores, labels))
            unique, counts = np.unique(labels, return_counts=True)
            min_share = float(counts.min() / labels.size)
            print(
                f"  k={k} sil={sil:.4f} (n={sil_n}) ch={ch:.1f} db={db:.4f} "
                f"min_share={min_share:.3%} fit={fit_s:.1f}s",
                flush=True,
            )
            metrics.append({
                "k": k, "silhouette": sil, "silhouette_sample_n": sil_n,
                "calinski_harabasz": ch, "davies_bouldin": db,
                "inertia": float(km.inertia_),
                "smallest_cluster_share": min_share,
                "fit_seconds": fit_s,
            })
            assignments[f"cluster_k{k}"] = labels.astype(np.int16)

        metrics_df = pd.DataFrame(metrics)
        metrics_df.to_csv(out_path / "kmeans_pca_metrics.csv", index=False)
        pl.from_pandas(assignments).write_parquet(out_path / "kmeans_pca_assignments.parquet")

        elbow = detect_elbow(metrics_df["k"].tolist(), metrics_df["inertia"].tolist())
        print(f"  codo: d2={elbow['elbow_d2_k']} segmento={elbow['elbow_segment_k']} consenso={elbow['elbow_consensus_k']}", flush=True)
        run_meta["elbow"] = elbow

        # plots de scatter coloreados por k=2,3,4 (usando submuestra para densidad visual)
        for k_to_plot in [2, 3, 4]:
            if k_to_plot < args.k_min or k_to_plot > args.k_max:
                continue
            labels_k = assignments[f"cluster_k{k_to_plot}"].to_numpy()
            labels_k_plot = labels_k[plot_idx]
            if n_pc >= 2:
                plot_scatter_2d(scores_for_plot, out_path / f"pca_kmeans_2d_k{k_to_plot}.png",
                                f"PCA + KMeans k={k_to_plot} | {args.branch_id}", labels=labels_k_plot)
            if n_pc >= 3:
                plot_scatter_3panels(scores_for_plot, out_path / f"pca_kmeans_3panels_k{k_to_plot}.png",
                                     f"PCA + KMeans k={k_to_plot} | {args.branch_id}", labels=labels_k_plot)

    (out_path / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    print(f"\n  outputs -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
