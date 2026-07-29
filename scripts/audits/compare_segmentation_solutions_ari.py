"""Compara dos (o mas) asignaciones KMeans via ARI y NMI.

Lee parquets `kmeans_assignments.parquet` de runs previos, hace join por
id_tarjeta y calcula:
- Adjusted Rand Index (ARI): 1 = identicas, 0 = aleatorias, <0 = peor que aleatorio.
- Normalized Mutual Information (NMI): 0 a 1.
- Tabla de contingencia (cluster_A x cluster_B).
- Tamano de cada cluster en ambas soluciones.

Uso:
    python compare_segmentation_solutions_ari.py \\
        --variant-id B_calendar_W15_W17_N14 \\
        --solution R2_abs_core_2025__B0_intensidad_solo:cluster_k2 \\
        --solution R2_abs_full_2025__B0_modal_solo:cluster_k2

Cada --solution es 'subdir_relativo:cluster_col'. El parquet se busca en
tmp/audits/segmentation_models/<variant>/<subdir>/kmeans/kmeans_assignments.parquet.
"""

from __future__ import annotations

import argparse
import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import (
    adjusted_mutual_info_score,
    adjusted_rand_score,
    normalized_mutual_info_score,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"


def parse_solution(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        raise SystemExit(f"Formato invalido '{spec}'. Esperado 'subdir:cluster_col'.")
    subdir, col = spec.split(":", 1)
    return subdir, col


def load_assignment(out_dir: Path, variant: str, subdir: str, cluster_col: str) -> pd.DataFrame:
    p = out_dir / variant / subdir / "kmeans" / "kmeans_assignments.parquet"
    if not p.exists():
        raise SystemExit(f"No existe: {p}")
    df = pl.read_parquet(p).to_pandas()
    if cluster_col not in df.columns:
        available = [c for c in df.columns if c.startswith("cluster_")]
        raise SystemExit(f"Columna {cluster_col} ausente. Disponibles: {available}")
    return df[["id_tarjeta", cluster_col]].rename(columns={cluster_col: "cluster"}).copy()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--solution", action="append", required=True,
                        help="subdir:cluster_col. Repetir para varias soluciones.")
    parser.add_argument("--label", action="append", default=None,
                        help="Etiqueta corta para cada solucion (mismo orden). Opcional.")
    args = parser.parse_args()

    sols = [parse_solution(s) for s in args.solution]
    if len(sols) < 2:
        raise SystemExit("Se necesitan al menos 2 soluciones para comparar.")

    labels = args.label if args.label else [f"S{i+1}" for i in range(len(sols))]
    if len(labels) != len(sols):
        raise SystemExit(f"Mismatch labels ({len(labels)}) vs solutions ({len(sols)}).")

    print(f"[load] {len(sols)} soluciones...")
    frames = []
    for (subdir, col), lab in zip(sols, labels):
        df = load_assignment(args.out_dir, args.variant_id, subdir, col)
        df = df.rename(columns={"cluster": f"cluster_{lab}"})
        print(f"  {lab}: {subdir}:{col} | {df.shape[0]:,} filas", flush=True)
        frames.append(df)

    # join inner
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="id_tarjeta", how="inner")
    n_common = merged.shape[0]
    print(f"\n[join] {n_common:,} ids comunes (inner join)\n", flush=True)
    if n_common < 100:
        raise SystemExit("Muy pocos ids comunes; revisar runs.")

    # tamanos por solucion
    print("=== Tamanos por solucion ===")
    for lab in labels:
        sizes = merged[f"cluster_{lab}"].value_counts().sort_index()
        shares = (sizes / sizes.sum()).round(4)
        print(f"  {lab}: clusters={sizes.tolist()} shares={shares.tolist()}")

    print("\n=== ARI / NMI / AMI (matrices simetricas) ===")
    n_sols = len(labels)
    ari_mat = np.eye(n_sols)
    nmi_mat = np.eye(n_sols)
    ami_mat = np.eye(n_sols)
    for i in range(n_sols):
        for j in range(n_sols):
            if i == j:
                continue
            a = merged[f"cluster_{labels[i]}"].to_numpy()
            b = merged[f"cluster_{labels[j]}"].to_numpy()
            ari_mat[i, j] = adjusted_rand_score(a, b)
            nmi_mat[i, j] = normalized_mutual_info_score(a, b)
            ami_mat[i, j] = adjusted_mutual_info_score(a, b)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    print("\nARI (Adjusted Rand Index):")
    print(pd.DataFrame(ari_mat, index=labels, columns=labels).to_string())
    print("\nNMI (Normalized Mutual Information):")
    print(pd.DataFrame(nmi_mat, index=labels, columns=labels).to_string())
    print("\nAMI (Adjusted Mutual Information):")
    print(pd.DataFrame(ami_mat, index=labels, columns=labels).to_string())

    # contingencia para pares
    print("\n=== TABLAS DE CONTINGENCIA (pares) ===")
    for i in range(n_sols):
        for j in range(i + 1, n_sols):
            a = merged[f"cluster_{labels[i]}"]
            b = merged[f"cluster_{labels[j]}"]
            tab = pd.crosstab(a, b, margins=True, margins_name="total")
            tab_share = pd.crosstab(a, b, normalize="all").round(4) * 100
            print(f"\n[{labels[i]} (filas) x {labels[j]} (columnas)] — conteo:")
            print(tab.to_string())
            print(f"\n[{labels[i]} x {labels[j]}] — % del total:")
            print(tab_share.to_string())

    out_dir = args.out_dir / args.variant_id / "ari_comparisons"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = "_vs_".join(labels)
    pd.DataFrame(ari_mat, index=labels, columns=labels).to_csv(out_dir / f"ari_{tag}.csv")
    pd.DataFrame(nmi_mat, index=labels, columns=labels).to_csv(out_dir / f"nmi_{tag}.csv")
    pd.DataFrame(ami_mat, index=labels, columns=labels).to_csv(out_dir / f"ami_{tag}.csv")
    print(f"\nGuardado: {out_dir}/ari|nmi|ami_{tag}.csv")


if __name__ == "__main__":
    main()
