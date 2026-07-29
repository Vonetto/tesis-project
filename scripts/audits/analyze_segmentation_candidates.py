"""Analisis comparativo de candidatos finales de segmentacion.

Para cada candidato (config + k):
1. Tamanos y shares por cluster.
2. Centroides en espacio PC (coordenadas de centroides en los PCs).
3. Medias de variables originales por cluster (sobre el parquet de features brutas).
4. ARI/NMI cross-candidate.

Candidatos asumidos por defecto:
- C1: R2_abs_full_2025 / pca_full27_pc8 / k=2
- C2: R2_abs_full_2025 / pca_full27_pc8 / k=4
- C3: R3_combined_full / pca_r3full_pc10 / k=4
"""

from __future__ import annotations

import argparse
import json
import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "features"
DEFAULT_MODELS_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"
DEFAULT_OUT_DIR = DEFAULT_MODELS_DIR


class Candidate:
    def __init__(self, label: str, variant: str, branch: str, feature_tag: str, k: int):
        self.label = label
        self.variant = variant
        self.branch = branch
        self.feature_tag = feature_tag
        self.k = k

    @property
    def assignments_path(self) -> Path:
        return (DEFAULT_MODELS_DIR / self.variant
                / f"{self.branch}__{self.feature_tag}" / "pca"
                / "kmeans_pca_assignments.parquet")

    @property
    def meta_path(self) -> Path:
        return (DEFAULT_MODELS_DIR / self.variant
                / f"{self.branch}__{self.feature_tag}" / "pca"
                / "run_meta.json")

    @property
    def features_parquet_path(self) -> Path:
        return DEFAULT_INPUT_DIR / self.variant / f"{self.branch}.parquet"

    @property
    def cluster_col(self) -> str:
        return f"cluster_k{self.k}"

    def load_assignments(self) -> pd.DataFrame:
        if not self.assignments_path.exists():
            raise SystemExit(f"No existe: {self.assignments_path}")
        df = pl.read_parquet(self.assignments_path).to_pandas()
        if self.cluster_col not in df.columns:
            raise SystemExit(f"Columna {self.cluster_col} ausente en {self.assignments_path}")
        return df[["id_tarjeta", self.cluster_col]].rename(columns={self.cluster_col: f"cluster_{self.label}"})

    def load_features_for_means(self) -> pl.DataFrame:
        if not self.features_parquet_path.exists():
            raise SystemExit(f"No existe parquet de features: {self.features_parquet_path}")
        return pl.read_parquet(self.features_parquet_path)


def compute_sizes(df: pd.DataFrame, cluster_col: str) -> pd.DataFrame:
    counts = df[cluster_col].value_counts().sort_index()
    shares = counts / counts.sum()
    return pd.DataFrame({"cluster": counts.index, "n": counts.values, "share": shares.values})


def compute_means_per_cluster(features_pl: pl.DataFrame, assignments_pd: pd.DataFrame,
                              cluster_col: str, feature_list: list[str]) -> pd.DataFrame:
    """Media de cada feature original por cluster, joinando por id_tarjeta."""
    assn_pl = pl.from_pandas(assignments_pd[["id_tarjeta", cluster_col]])
    joined = features_pl.select(["id_tarjeta", *feature_list]).join(
        assn_pl, on="id_tarjeta", how="inner"
    )
    grouped = joined.group_by(cluster_col).agg([pl.col(f).mean().alias(f) for f in feature_list])
    return grouped.sort(cluster_col).to_pandas()


def compute_pc_centroids(assignments_pd: pd.DataFrame, cluster_col: str,
                         pc_scores_path: Path | None = None) -> pd.DataFrame | None:
    """Centroides en espacio PC: requiere reconstruir scores. Si no hay, devuelve None.

    Por simplicidad, en esta version reportamos solo centroides en variables
    originales (no en PCs). Para centroides en PCs habria que recargar el PCA
    y reaplicar; lo dejamos como follow-up si interesa.
    """
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tag", default="candidates_v1",
                        help="Sufijo para la carpeta de outputs comparativos.")
    args = parser.parse_args()

    candidates = [
        Candidate("C1_full27_pc8_k2", args.variant_id, "R2_abs_full_2025", "pca_full27_pc8", 2),
        Candidate("C2_full27_pc8_k4", args.variant_id, "R2_abs_full_2025", "pca_full27_pc8", 4),
        Candidate("C3_R3_pc10_k4", args.variant_id, "R3_combined_full", "pca_r3full_pc10", 4),
    ]

    out_dir = args.out_dir / args.variant_id / f"comparison_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[out] {out_dir}", flush=True)

    # === 1. tamanos por cluster ===
    print("\n=== 1. Tamanos y shares por candidato ===")
    sizes_all = []
    assignments_by_label: dict[str, pd.DataFrame] = {}
    for c in candidates:
        a = c.load_assignments()
        assignments_by_label[c.label] = a
        sizes = compute_sizes(a, f"cluster_{c.label}")
        sizes["candidate"] = c.label
        sizes_all.append(sizes)
        print(f"\n[{c.label}] k={c.k} n={a.shape[0]:,}")
        print(sizes[["cluster", "n", "share"]].to_string(index=False, formatters={"share": "{:.4f}".format}))
    sizes_df = pd.concat(sizes_all, ignore_index=True)
    sizes_df.to_csv(out_dir / "01_sizes.csv", index=False)

    # === 2. medias de variables originales por cluster ===
    print("\n\n=== 2. Medias de variables originales por cluster ===")
    means_all = []
    for c in candidates:
        feats_pl = c.load_features_for_means()
        # excluir cols que no son features (id_tarjeta y metadatos)
        meta_cols = {"id_tarjeta", "variant_id", "share_is_qr_eval", "n_trips_eval",
                     "n_active_days_eval", "qr_share_eval_recomputed"}
        feature_list = [col for col in feats_pl.columns if col not in meta_cols]
        means = compute_means_per_cluster(
            feats_pl, assignments_by_label[c.label],
            f"cluster_{c.label}", feature_list,
        )
        means["candidate"] = c.label
        means_all.append(means)
        print(f"\n[{c.label}] media de cada variable por cluster:")
        # imprimir transpuesto para legibilidad
        cluster_col = f"cluster_{c.label}"
        printable = means.drop(columns=["candidate"]).set_index(cluster_col).T
        pd.set_option("display.float_format", lambda x: f"{x:.3f}")
        pd.set_option("display.max_rows", 60)
        pd.set_option("display.width", 200)
        print(printable.to_string())

    # Guardar un csv por candidato (formato wide para legibilidad)
    for c, means in zip(candidates, means_all):
        out_file = out_dir / f"02_means_{c.label}.csv"
        means.to_csv(out_file, index=False)

    # === 3. ARI / NMI cross-candidate ===
    print("\n\n=== 3. ARI / NMI cross-candidate ===")
    # join inner por id_tarjeta
    merged = assignments_by_label[candidates[0].label]
    for c in candidates[1:]:
        merged = merged.merge(assignments_by_label[c.label], on="id_tarjeta", how="inner")
    n_common = merged.shape[0]
    print(f"[join] {n_common:,} ids comunes")

    n_c = len(candidates)
    ari_mat = np.eye(n_c)
    nmi_mat = np.eye(n_c)
    for i in range(n_c):
        for j in range(n_c):
            if i == j:
                continue
            a = merged[f"cluster_{candidates[i].label}"].to_numpy()
            b = merged[f"cluster_{candidates[j].label}"].to_numpy()
            ari_mat[i, j] = adjusted_rand_score(a, b)
            nmi_mat[i, j] = normalized_mutual_info_score(a, b)

    labels = [c.label for c in candidates]
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    print("\nARI:")
    print(pd.DataFrame(ari_mat, index=labels, columns=labels).to_string())
    print("\nNMI:")
    print(pd.DataFrame(nmi_mat, index=labels, columns=labels).to_string())

    pd.DataFrame(ari_mat, index=labels, columns=labels).to_csv(out_dir / "03_ari.csv")
    pd.DataFrame(nmi_mat, index=labels, columns=labels).to_csv(out_dir / "03_nmi.csv")

    # tablas de contingencia para pares
    print("\n=== Tablas de contingencia (pares) ===")
    for i in range(n_c):
        for j in range(i + 1, n_c):
            a = merged[f"cluster_{candidates[i].label}"]
            b = merged[f"cluster_{candidates[j].label}"]
            tab = pd.crosstab(a, b, margins=True, margins_name="total")
            print(f"\n[{labels[i]} (filas) x {labels[j]} (columnas)] — conteo:")
            print(tab.to_string())
            tab_share = pd.crosstab(a, b, normalize="all").round(4) * 100
            print(f"\n[{labels[i]} x {labels[j]}] — % del total:")
            print(tab_share.to_string())
            tab.to_csv(out_dir / f"03_contingency_{labels[i]}_vs_{labels[j]}.csv")

    meta = {
        "variant_id": args.variant_id,
        "candidates": [
            {"label": c.label, "variant": c.variant, "branch": c.branch,
             "feature_tag": c.feature_tag, "k": c.k}
            for c in candidates
        ],
        "n_common_ids": n_common,
    }
    (out_dir / "run_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"\n[done] outputs en {out_dir}")


if __name__ == "__main__":
    main()
