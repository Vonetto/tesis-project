"""Sparse KMeans (Witten & Tibshirani 2010) — implementacion directa.

Witten DM, Tibshirani R (2010). "A Framework for Feature Selection in Clustering".
JASA 105(490): 713-726.

Algoritmo (Algorithm 1 del paper, especializado para KMeans):
- Inicializar pesos w_j = 1/sqrt(p) para cada feature j.
- Iterar hasta convergencia:
  1. Fijar w, resolver clusters: KMeans sobre matriz ponderada X * sqrt(w).
  2. Fijar clusters, resolver w via optimizacion L1+L2:
        max_w  sum_j w_j * a_j  s.t.  ||w||_2 <= 1, ||w||_1 <= s, w_j >= 0
     donde a_j = BCSS_j (between-cluster sum of squares de feature j).
     Solucion: w_j = soft_threshold(a_j, lambda) / ||soft_threshold(a, lambda)||_2
     con lambda elegido por busqueda binaria para satisfacer ||w||_1 = s.

El hiperparametro `s` (tuning parameter) controla la sparsidad:
- s = sqrt(p) → todas las features con peso ~igual.
- s pequeno → solo unas pocas features tienen peso > 0.

Permutation-based selection de `s`:
- Gap statistic adaptado: comparar BCSS observado vs BCSS bajo permutacion de filas.
- s optimo maximiza el gap.
"""

from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
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


def soft_threshold(x: np.ndarray, lam: float) -> np.ndarray:
    """Operador soft-thresholding: sign(x) * max(|x| - lam, 0)."""
    return np.sign(x) * np.maximum(np.abs(x) - lam, 0.0)


def bcss_per_feature(X: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Between-cluster sum of squares por feature.

    BCSS_j = TSS_j - WCSS_j
    """
    n, p = X.shape
    overall_mean = X.mean(axis=0)
    tss = ((X - overall_mean) ** 2).sum(axis=0)
    wcss = np.zeros(p)
    for c in np.unique(labels):
        mask = labels == c
        nc = mask.sum()
        if nc <= 1:
            continue
        cluster_mean = X[mask].mean(axis=0)
        wcss += ((X[mask] - cluster_mean) ** 2).sum(axis=0)
    return tss - wcss


def solve_weights(a: np.ndarray, s: float, tol: float = 1e-8, max_iter: int = 100) -> np.ndarray:
    """Resuelve el subproblema de w via soft-threshold con busqueda binaria.

    max  sum_j w_j a_j
    s.t. ||w||_2 <= 1, ||w||_1 <= s, w_j >= 0.

    Solucion (Witten Lemma 3): w = soft_threshold(a, lam) / ||soft_threshold(a, lam)||_2
    donde lam se elige para satisfacer ||w||_1 = s (si la version sin sparsidad
    viola la restriccion L1).
    """
    a_pos = np.maximum(a, 0.0)  # solo nos importan features con BCSS > 0
    # Caso 1: si la solucion sin lam=0 ya satisface ||w||_1 <= s, no hay sparsidad
    w0 = a_pos / max(np.linalg.norm(a_pos), 1e-12)
    if w0.sum() <= s:
        return w0
    # Caso 2: busqueda binaria sobre lam
    lo, hi = 0.0, a_pos.max()
    for _ in range(max_iter):
        lam = 0.5 * (lo + hi)
        w_st = soft_threshold(a_pos, lam)
        norm = np.linalg.norm(w_st)
        if norm < 1e-12:
            hi = lam
            continue
        w = w_st / norm
        l1 = w.sum()
        if abs(l1 - s) < tol:
            return w
        if l1 > s:
            lo = lam
        else:
            hi = lam
    return w


def weighted_objective(X: np.ndarray, labels: np.ndarray, w: np.ndarray) -> float:
    """Objetivo del paper: sum_j w_j * BCSS_j."""
    a = bcss_per_feature(X, labels)
    return float(np.sum(w * a))


def sparse_kmeans(
    X: np.ndarray,
    k: int,
    s: float,
    n_init: int = 10,
    random_seed: int = 42,
    max_iter_outer: int = 50,
    tol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, float, int]:
    """Sparse KMeans (Witten & Tibshirani 2010).

    Args:
        X: (n, p) matriz escalada.
        k: numero de clusters.
        s: parametro L1 sobre pesos.
        n_init: reinicios de KMeans interno por iteracion.
        random_seed: semilla.
        max_iter_outer: iteraciones max del loop w<->labels.
        tol: tolerancia para convergencia del objetivo.

    Returns:
        labels (n,), weights (p,), objective_final, n_iter_outer.
    """
    n, p = X.shape
    w = np.ones(p) / np.sqrt(p)  # inicializacion uniforme normalizada
    prev_obj = -np.inf
    labels = np.zeros(n, dtype=np.int32)

    for it in range(max_iter_outer):
        # Paso 1: fijo w, resolver clusters via KMeans en X * sqrt(w)
        X_weighted = X * np.sqrt(np.maximum(w, 0))[None, :]
        with threadpool_limits(limits=1):
            km = KMeans(n_clusters=k, init="k-means++", random_state=random_seed,
                        n_init=n_init, algorithm="lloyd")
            labels = km.fit_predict(X_weighted)
        # Paso 2: fijo labels, resolver w
        a = bcss_per_feature(X, labels)  # BCSS sobre X original, no ponderado
        w = solve_weights(a, s)
        # Convergencia
        obj = weighted_objective(X, labels, w)
        if abs(obj - prev_obj) / max(abs(prev_obj), 1e-12) < tol:
            return labels, w, obj, it + 1
        prev_obj = obj

    return labels, w, prev_obj, max_iter_outer


def permutation_gap(
    X: np.ndarray,
    k: int,
    s: float,
    n_perm: int,
    n_init: int,
    random_seed: int,
) -> tuple[float, float]:
    """Gap statistic via permutacion (Witten section 3.2).

    Para cada permutacion, permutar cada columna de X independientemente,
    correr sparse KMeans, calcular log(objetivo). El gap es log(obj_obs) -
    mean(log(obj_perm)).
    """
    _, _, obj_obs, _ = sparse_kmeans(X, k, s, n_init=n_init, random_seed=random_seed)
    log_obj_obs = np.log(max(obj_obs, 1e-12))
    rng = np.random.default_rng(random_seed)
    perm_logs = []
    for i in range(n_perm):
        X_perm = X.copy()
        for j in range(X_perm.shape[1]):
            rng.shuffle(X_perm[:, j])
        _, _, obj_p, _ = sparse_kmeans(X_perm, k, s, n_init=n_init, random_seed=random_seed + i + 1)
        perm_logs.append(np.log(max(obj_p, 1e-12)))
    return log_obj_obs - np.mean(perm_logs), float(np.std(perm_logs))


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", default="R2_abs_core_2025")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--include-features", type=str, default="")
    parser.add_argument("--drop-features", type=str, default="")
    parser.add_argument("--sample-size", type=int, default=100_000)
    parser.add_argument("--silhouette-sample", type=int, default=50_000)
    parser.add_argument("--k", type=int, default=2,
                        help="Numero de clusters. Sparse KMeans necesita k fijo.")
    parser.add_argument("--s-grid", type=str, default="1.2,1.5,2.0,2.5,3.0,3.5,4.0",
                        help="Grid de s a evaluar (L1 budget sobre pesos).")
    parser.add_argument("--n-perm", type=int, default=10,
                        help="Numero de permutaciones para gap (0 = no calcular).")
    parser.add_argument("--n-init", type=int, default=10)
    parser.add_argument("--max-iter-outer", type=int, default=30)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--feature-tag", type=str, default="sparse_kmeans")
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

    for f in features:
        if f not in df.columns:
            raise SystemExit(f"Feature ausente en parquet: {f}")
        if df[f].null_count() > 0:
            raise SystemExit(f"NULL en feature {f}")

    n_total = df.height
    if args.sample_size and df.height > args.sample_size:
        df = df.sample(n=args.sample_size, seed=args.random_seed)
    n_used = df.height
    print(f"  sample: {n_used:,} de {n_total:,}", flush=True)

    X = df.select(features).to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    p = X_scaled.shape[1]
    s_grid = [float(x) for x in args.s_grid.split(",") if x.strip()]
    s_max = float(np.sqrt(p))
    print(f"  p={p}, sqrt(p)={s_max:.3f}, s_grid={s_grid}", flush=True)

    rng = np.random.default_rng(args.random_seed)
    results = []
    assignments = df.select(["id_tarjeta"]).to_pandas()

    for s in s_grid:
        if s > s_max:
            print(f"  [skip] s={s} > sqrt(p)={s_max:.3f}", flush=True)
            continue
        t0 = time.perf_counter()
        labels, w, obj, n_iter = sparse_kmeans(
            X_scaled, args.k, s,
            n_init=args.n_init,
            random_seed=args.random_seed,
            max_iter_outer=args.max_iter_outer,
        )
        elapsed = time.perf_counter() - t0
        # metricas sobre X_scaled (no ponderado)
        sil, sil_n = silhouette_subsample(X_scaled, labels, args.silhouette_sample, rng)
        ch = float(calinski_harabasz_score(X_scaled, labels))
        db = float(davies_bouldin_score(X_scaled, labels))
        unique, counts = np.unique(labels, return_counts=True)
        min_share = float(counts.min() / labels.size)

        n_active = int((w > 1e-4).sum())
        print(
            f"  s={s:.2f} obj={obj:.1f} iter={n_iter} n_active_feat={n_active}/{p} "
            f"sil={sil:.4f} ch={ch:.1f} db={db:.4f} min_share={min_share:.3%} elapsed={elapsed:.1f}s",
            flush=True,
        )

        results.append({
            "s": s,
            "objective": obj,
            "n_iter_outer": n_iter,
            "n_active_features": n_active,
            "silhouette": sil,
            "silhouette_sample_n": sil_n,
            "calinski_harabasz": ch,
            "davies_bouldin": db,
            "smallest_cluster_share": min_share,
            "elapsed_seconds": elapsed,
        })
        assignments[f"cluster_s{s:.2f}"] = labels.astype(np.int16)

        # guardar weights por s
        out_path = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}" / "sparse_kmeans"
        out_path.mkdir(parents=True, exist_ok=True)
        weights_df = pd.DataFrame({
            "feature": features,
            "weight": w,
            "active": (w > 1e-4).astype(int),
        }).sort_values("weight", ascending=False)
        weights_df.to_csv(out_path / f"weights_k{args.k}_s{s:.2f}.csv", index=False)

    out_path = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}" / "sparse_kmeans"
    out_path.mkdir(parents=True, exist_ok=True)
    metrics_df = pd.DataFrame(results)
    metrics_df.to_csv(out_path / f"sparse_kmeans_metrics_k{args.k}.csv", index=False)
    pl.from_pandas(assignments).write_parquet(out_path / f"sparse_kmeans_assignments_k{args.k}.parquet")

    # ---- Gap statistic via permutacion (opcional) ----
    if args.n_perm > 0 and len(s_grid) > 0:
        print(f"\n[gap] calculando gap statistic con {args.n_perm} permutaciones por s...", flush=True)
        gap_rows = []
        for s in s_grid:
            if s > s_max:
                continue
            gap, perm_std = permutation_gap(
                X_scaled, args.k, s,
                n_perm=args.n_perm,
                n_init=args.n_init,
                random_seed=args.random_seed,
            )
            print(f"  s={s:.2f} gap={gap:.4f} perm_std={perm_std:.4f}", flush=True)
            gap_rows.append({"s": s, "gap": gap, "perm_std": perm_std})
        gap_df = pd.DataFrame(gap_rows)
        gap_df.to_csv(out_path / f"sparse_kmeans_gap_k{args.k}.csv", index=False)

        # plot gap
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.errorbar(gap_df["s"], gap_df["gap"], yerr=gap_df["perm_std"], marker="o", color="C3")
        ax.set_xlabel("s (L1 budget)")
        ax.set_ylabel("Gap = log(obj_obs) - mean(log(obj_perm))")
        ax.set_title(f"Sparse KMeans gap statistic | k={args.k} | {args.branch_id}")
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_path / f"sparse_kmeans_gap_k{args.k}.png", dpi=140, bbox_inches="tight")
        plt.close(fig)

    # plot trayectoria de pesos por s
    if results:
        fig, ax = plt.subplots(figsize=(10, max(4, len(features) * 0.25)))
        for i, s_val in enumerate([r["s"] for r in results]):
            wf = pd.read_csv(out_path / f"weights_k{args.k}_s{s_val:.2f}.csv")
            # ordenar por peso descendente del primer s para consistencia visual
            if i == 0:
                feature_order = wf.sort_values("weight", ascending=False)["feature"].tolist()
            wf = wf.set_index("feature").loc[feature_order].reset_index()
            ax.barh(np.arange(len(features)) + i * 0.12 - 0.3,
                    wf["weight"], height=0.1, label=f"s={s_val:.2f}")
        ax.set_yticks(np.arange(len(features)))
        ax.set_yticklabels(feature_order)
        ax.invert_yaxis()
        ax.set_xlabel("Peso w_j")
        ax.set_title(f"Sparse KMeans weights por s | k={args.k} | {args.branch_id}")
        ax.legend(loc="best", fontsize=7)
        ax.grid(alpha=0.3, axis="x")
        fig.tight_layout()
        fig.savefig(out_path / f"sparse_kmeans_weights_k{args.k}.png", dpi=140, bbox_inches="tight")
        plt.close(fig)

    run_meta = {
        "variant_id": args.variant_id,
        "branch_id": args.branch_id,
        "feature_tag": args.feature_tag,
        "features": features,
        "k": args.k,
        "s_grid": s_grid,
        "s_max_sqrt_p": s_max,
        "n_used": n_used,
        "n_total": n_total,
        "random_seed": args.random_seed,
    }
    (out_path / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    print(f"\n  outputs -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
