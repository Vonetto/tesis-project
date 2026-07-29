from __future__ import annotations

# IMPORTANT: limitar threads de BLAS ANTES de importar numpy/sklearn.
# OpenBLAS precompilado en larch-env tiene cap=128; con n_init paralelo
# se excede y corrompe memoria. threadpoolctl no logra controlarlo en
# este binario, por lo que forzamos thread=1 a nivel de proceso. sklearn
# paraleliza los n_init en Python (joblib) sin entrar al pool BLAS.
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
DEFAULT_INVENTORY_PATH = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "feature_matrix_inventory.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"


def load_feature_list(inventory_path: Path, variant_id: str, branch_id: str) -> list[str]:
    inventory = pl.read_csv(inventory_path)
    row = inventory.filter(
        (pl.col("variant_id") == variant_id) & (pl.col("branch_id") == branch_id)
    )
    if row.height == 0:
        available = (
            inventory.select(["variant_id", "branch_id"]).unique().sort(["variant_id", "branch_id"])
        )
        raise ValueError(
            f"No se encontro {variant_id} | {branch_id} en inventory. Disponibles:\n{available}"
        )
    features_str = row["features"][0]
    return [f.strip() for f in features_str.split(",") if f.strip()]


def apply_feature_drops(features: list[str], drop_features: list[str]) -> tuple[list[str], list[str]]:
    """Aplica drops a la lista de features del inventario.

    Retorna (features_finales, drops_aplicados). Falla si algun drop solicitado
    no estaba en la lista original (proteccion contra typos).
    """
    if not drop_features:
        return features, []
    drop_set = set(drop_features)
    not_present = sorted(drop_set - set(features))
    if not_present:
        raise ValueError(
            f"Features a dropear no estan en la rama: {not_present}. "
            f"Features disponibles: {features}"
        )
    final = [f for f in features if f not in drop_set]
    applied = [f for f in features if f in drop_set]
    return final, applied


def apply_feature_whitelist(features: list[str], include_features: list[str]) -> list[str]:
    """Filtra a una whitelist explicita, preservando el orden de la whitelist.

    Falla si algun feature pedido no esta en el inventario (proteccion contra typos).
    """
    if not include_features:
        return features
    available = set(features)
    not_present = [f for f in include_features if f not in available]
    if not_present:
        raise ValueError(
            f"Features pedidas no estan en la rama: {not_present}. "
            f"Features disponibles: {features}"
        )
    return list(include_features)


def assert_no_nulls(df: pl.DataFrame, features: list[str]) -> None:
    null_counts = {}
    nan_counts = {}
    for f in features:
        s = df[f]
        n_null = int(s.null_count())
        if n_null:
            null_counts[f] = n_null
        if s.dtype in (pl.Float32, pl.Float64):
            n_nan = int(s.is_nan().sum())
            if n_nan:
                nan_counts[f] = n_nan
    if null_counts or nan_counts:
        raise ValueError(
            f"Features con nulos/NaN detectados antes de KMeans. nulls={null_counts} nans={nan_counts}"
        )


def silhouette_with_subsample(X: np.ndarray, labels: np.ndarray, max_n: int, rng: np.random.Generator) -> tuple[float, int]:
    n = X.shape[0]
    if n <= max_n:
        return float(silhouette_score(X, labels)), n
    idx = rng.choice(n, size=max_n, replace=False)
    return float(silhouette_score(X[idx], labels[idx])), max_n


def detect_elbow(ks: list[int], inertias: list[float]) -> dict:
    """Detecta el codo en curva inercia(k).

    Estrategias:
    - Segunda diferencia discreta: para k interiores, calcula
      d2[i] = inertia[i-1] - 2*inertia[i] + inertia[i+1].
      El codo es el k con mayor d2 (mayor curvatura concava hacia arriba).
    - Distancia al segmento que une los extremos (metodo del segmento).
      Robusto cuando d2 es ruidosa.

    Devuelve ambos y un k recomendado por votacion simple.
    """
    if len(ks) < 3:
        return {
            "elbow_d2_k": None,
            "elbow_d2_value": None,
            "elbow_segment_k": None,
            "elbow_segment_distance": None,
            "elbow_consensus_k": None,
        }

    ks_arr = np.asarray(ks, dtype=float)
    in_arr = np.asarray(inertias, dtype=float)

    # Segunda diferencia
    d2 = np.full_like(in_arr, np.nan)
    d2[1:-1] = in_arr[:-2] - 2 * in_arr[1:-1] + in_arr[2:]
    interior = d2[1:-1]
    idx_d2 = int(np.nanargmax(interior)) + 1
    elbow_d2_k = int(ks_arr[idx_d2])
    elbow_d2_value = float(d2[idx_d2])

    # Distancia al segmento (extremos)
    p0 = np.array([ks_arr[0], in_arr[0]])
    p1 = np.array([ks_arr[-1], in_arr[-1]])
    seg = p1 - p0
    seg_norm = np.linalg.norm(seg)
    distances = np.full_like(in_arr, np.nan)
    for i in range(len(ks_arr)):
        p = np.array([ks_arr[i], in_arr[i]])
        # distancia punto-recta en 2D
        distances[i] = abs(np.cross(seg, p - p0)) / seg_norm
    idx_seg = int(np.argmax(distances))
    elbow_segment_k = int(ks_arr[idx_seg])
    elbow_segment_distance = float(distances[idx_seg])

    consensus = elbow_d2_k if elbow_d2_k == elbow_segment_k else elbow_segment_k

    return {
        "elbow_d2_k": elbow_d2_k,
        "elbow_d2_value": elbow_d2_value,
        "elbow_segment_k": elbow_segment_k,
        "elbow_segment_distance": elbow_segment_distance,
        "elbow_consensus_k": consensus,
    }


def plot_diagnostics(
    metrics_df: pd.DataFrame,
    elbow: dict,
    out_path: Path,
    title_suffix: str,
) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    ks = metrics_df["k"].to_numpy()

    ax = axes[0, 0]
    ax.plot(ks, metrics_df["inertia"], marker="o", color="C0")
    if elbow.get("elbow_d2_k") is not None:
        ax.axvline(elbow["elbow_d2_k"], color="C3", ls="--", alpha=0.7, label=f"codo d2 (k={elbow['elbow_d2_k']})")
    if elbow.get("elbow_segment_k") is not None and elbow.get("elbow_segment_k") != elbow.get("elbow_d2_k"):
        ax.axvline(elbow["elbow_segment_k"], color="C2", ls=":", alpha=0.7, label=f"codo segmento (k={elbow['elbow_segment_k']})")
    ax.set_xlabel("k")
    ax.set_ylabel("inertia")
    ax.set_title("Codo (inertia)")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)

    ax = axes[0, 1]
    ax.plot(ks, metrics_df["silhouette"], marker="o", color="C1")
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette")
    ax.set_title("Silhouette (subsample)")
    ax.grid(alpha=0.3)

    ax = axes[1, 0]
    ax.plot(ks, metrics_df["calinski_harabasz"], marker="o", color="C4", label="CH")
    ax.set_xlabel("k")
    ax.set_ylabel("Calinski-Harabasz")
    ax.set_title("Calinski-Harabasz (mayor = mejor)")
    ax.grid(alpha=0.3)

    ax = axes[1, 1]
    ax.plot(ks, metrics_df["davies_bouldin"], marker="o", color="C5", label="DB")
    ax.plot(ks, metrics_df["smallest_cluster_share"], marker="s", color="C6", label="min cluster share")
    ax.axhline(0.05, color="grey", ls=":", alpha=0.5, label="5% floor")
    ax.set_xlabel("k")
    ax.set_ylabel("DB / share")
    ax.set_title("Davies-Bouldin y min share")
    ax.legend(loc="best", fontsize=8)
    ax.grid(alpha=0.3)

    fig.suptitle(f"KMeans diagnostics | {title_suffix}", fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def run_kmeans(
    variant_id: str,
    branch_id: str,
    input_dir: Path = DEFAULT_INPUT_DIR,
    inventory_path: Path = DEFAULT_INVENTORY_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    sample_size: int | None = 100_000,
    silhouette_sample: int = 50_000,
    k_min: int = 2,
    k_max: int = 10,
    n_init: int = 10,
    random_seed: int = 42,
    blas_threads: int = 1,
    drop_features: list[str] | None = None,
    include_features: list[str] | None = None,
    feature_tag: str | None = None,
) -> dict:
    print(f"--- KMeans | variant={variant_id} | branch={branch_id} ---", flush=True)

    input_path = input_dir / variant_id / f"{branch_id}.parquet"
    if not input_path.exists():
        raise FileNotFoundError(f"No existe matriz: {input_path}")

    df = pl.read_parquet(input_path)
    if "id_tarjeta" not in df.columns:
        raise ValueError("id_tarjeta ausente en la matriz")
    print(f"  cargado: rows={df.height:,} cols={df.width}", flush=True)

    features_full = load_feature_list(inventory_path, variant_id, branch_id)
    missing = [f for f in features_full if f not in df.columns]
    if missing:
        raise ValueError(f"Features ausentes en parquet: {missing}")

    if include_features and drop_features:
        raise ValueError("No usar --include-features y --drop-features juntos. Elige uno.")

    if include_features:
        features = apply_feature_whitelist(features_full, include_features)
        drops_applied: list[str] = []
        print(
            f"  features ({len(features_full)} inventario -> {len(features)} whitelist): "
            f"selected={features}",
            flush=True,
        )
    else:
        features, drops_applied = apply_feature_drops(features_full, drop_features or [])
        if drops_applied:
            print(
                f"  features ({len(features_full)} -> {len(features)} tras drops): "
                f"dropped={drops_applied}",
                flush=True,
            )
    print(f"  features finales ({len(features)}): {features}", flush=True)

    assert_no_nulls(df, features)

    n_total = df.height
    if sample_size and df.height > sample_size:
        print(f"  sample: {sample_size:,} de {df.height:,}", flush=True)
        df = df.sample(n=sample_size, seed=random_seed)
    n_used = df.height

    X = df.select(features).to_numpy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    rng = np.random.default_rng(random_seed)

    assignments = df.select(["id_tarjeta"]).to_pandas()
    metrics: list[dict] = []

    for k in range(k_min, k_max + 1):
        t0 = time.perf_counter()
        # Limitar threadpools de BLAS dentro del fit para evitar leak con n_init paralelo.
        with threadpool_limits(limits=blas_threads):
            kmeans = KMeans(
                n_clusters=k,
                init="k-means++",
                random_state=random_seed,
                n_init=n_init,
                algorithm="lloyd",
            )
            labels = kmeans.fit_predict(X_scaled)
        fit_seconds = time.perf_counter() - t0

        with threadpool_limits(limits=blas_threads):
            sil, sil_n = silhouette_with_subsample(X_scaled, labels, silhouette_sample, rng)
            ch = float(calinski_harabasz_score(X_scaled, labels))
            db = float(davies_bouldin_score(X_scaled, labels))

        unique, counts = np.unique(labels, return_counts=True)
        smallest_share = float(counts.min() / labels.size)

        print(
            f"  k={k} sil={sil:.4f} (n={sil_n}) ch={ch:.1f} db={db:.4f} "
            f"min_share={smallest_share:.3%} fit={fit_seconds:.1f}s",
            flush=True,
        )
        metrics.append(
            {
                "k": k,
                "silhouette": sil,
                "silhouette_sample_n": sil_n,
                "calinski_harabasz": ch,
                "davies_bouldin": db,
                "inertia": float(kmeans.inertia_),
                "smallest_cluster_share": smallest_share,
                "fit_seconds": fit_seconds,
            }
        )
        assignments[f"cluster_k{k}"] = labels.astype(np.int16)

    branch_subdir = branch_id if not feature_tag else f"{branch_id}__{feature_tag}"
    out_path = output_dir / variant_id / branch_subdir / "kmeans"
    out_path.mkdir(parents=True, exist_ok=True)

    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(out_path / "kmeans_metrics.csv", index=False)
    pl.from_pandas(assignments).write_parquet(out_path / "kmeans_assignments.parquet")

    elbow = detect_elbow(metrics_df["k"].tolist(), metrics_df["inertia"].tolist())
    (out_path / "kmeans_elbow.json").write_text(json.dumps(elbow, indent=2), encoding="utf-8")
    print(
        f"  codo: d2={elbow['elbow_d2_k']} segmento={elbow['elbow_segment_k']} "
        f"consenso={elbow['elbow_consensus_k']}",
        flush=True,
    )

    plot_path = out_path / "kmeans_diagnostics.png"
    plot_diagnostics(metrics_df, elbow, plot_path, f"{variant_id} | {branch_id} | n={n_used:,}")
    print(f"  plot -> {plot_path}", flush=True)

    run_meta = {
        "variant_id": variant_id,
        "branch_id": branch_id,
        "feature_tag": feature_tag,
        "input_path": str(input_path),
        "n_total": n_total,
        "n_used": n_used,
        "sample_size": sample_size,
        "silhouette_sample": silhouette_sample,
        "k_min": k_min,
        "k_max": k_max,
        "n_init": n_init,
        "random_seed": random_seed,
        "features_original": features_full,
        "features": features,
        "drops_applied": drops_applied,
        "include_features": include_features,
        "elbow": elbow,
    }
    (out_path / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")
    print(f"  outputs -> {out_path}", flush=True)
    return run_meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Run KMeans for segmentation feature matrices.")
    parser.add_argument("--variant-id", type=str, default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", type=str, default="R1_lizana3")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100_000,
        help="Tamano de muestra para fit. 0 = poblacion completa.",
    )
    parser.add_argument(
        "--silhouette-sample",
        type=int,
        default=50_000,
        help="Sub-muestra para silhouette si fit_n > este valor.",
    )
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--n-init", type=int, default=10)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--blas-threads",
        type=int,
        default=1,
        help="Limite de threads BLAS dentro de fits. Default 1 por bug de OpenBLAS en larch-env.",
    )
    parser.add_argument(
        "--drop-features",
        type=str,
        default="",
        help="Features a eliminar de la lista del inventario, separadas por coma. Util para dedup.",
    )
    parser.add_argument(
        "--include-features",
        type=str,
        default="",
        help="Whitelist explicita de features (separadas por coma). Mutuamente excluyente con --drop-features.",
    )
    parser.add_argument(
        "--feature-tag",
        type=str,
        default=None,
        help="Sufijo para el directorio de salida (ej. 'B1_intensidad'). Si se omite y hay drops/include, se asigna 'dedup' o 'whitelist'.",
    )
    args = parser.parse_args()

    drop_list = [f.strip() for f in args.drop_features.split(",") if f.strip()]
    include_list = [f.strip() for f in args.include_features.split(",") if f.strip()]
    if drop_list and include_list:
        raise SystemExit("No usar --include-features y --drop-features juntos. Elige uno.")
    feature_tag = args.feature_tag
    if feature_tag is None:
        if include_list:
            feature_tag = "whitelist"
        elif drop_list:
            feature_tag = "dedup"

    run_kmeans(
        variant_id=args.variant_id,
        branch_id=args.branch_id,
        input_dir=args.input_dir,
        inventory_path=args.inventory_path,
        output_dir=args.output_dir,
        sample_size=args.sample_size if args.sample_size > 0 else None,
        silhouette_sample=args.silhouette_sample,
        k_min=args.k_min,
        k_max=args.k_max,
        n_init=args.n_init,
        random_seed=args.random_seed,
        blas_threads=args.blas_threads,
        drop_features=drop_list or None,
        include_features=include_list or None,
        feature_tag=feature_tag,
    )


if __name__ == "__main__":
    main()
