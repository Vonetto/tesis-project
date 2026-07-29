"""Diagnostica outliers en las matrices R2/R3 antes de re-correr KMeans.

Objetivo: decidir si conviene cambiar StandardScaler -> RobustScaler o aplicar
clip a percentiles. Mide por feature:

- cuantiles p1, p50, p99, p99.9
- skewness y kurtosis (exceso)
- ratio max/p99 (cuanto exagera el extremo respecto al p99)
- ratio (mean - median) / std (asimetria normalizada)
- fraccion de filas con z > 5 usando StandardScaler

Imprime tabla por (variant_id, branch_id, feature) y exporta CSV.
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


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "feature_matrix_inventory.csv"
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "features"
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"


def diagnose_branch(
    variant_id: str,
    branch_id: str,
    features: list[str],
    input_dir: Path,
) -> pd.DataFrame:
    path = input_dir / variant_id / f"{branch_id}.parquet"
    df = pl.read_parquet(path)
    rows = []
    n = df.height
    for f in features:
        arr = df[f].cast(pl.Float64).drop_nulls().to_numpy()
        if arr.size == 0:
            continue
        p1, p50, p99, p999, pmax = np.percentile(arr, [1, 50, 99, 99.9, 100])
        mean = float(arr.mean())
        std = float(arr.std(ddof=0))
        if std > 0:
            z = (arr - mean) / std
            frac_z_gt5 = float((np.abs(z) > 5).mean())
            frac_z_gt10 = float((np.abs(z) > 10).mean())
            asym_norm = (mean - p50) / std
            # momentos
            m3 = float(((arr - mean) ** 3).mean())
            m4 = float(((arr - mean) ** 4).mean())
            skew = m3 / (std ** 3)
            kurt_excess = m4 / (std ** 4) - 3.0
        else:
            frac_z_gt5 = 0.0
            frac_z_gt10 = 0.0
            asym_norm = 0.0
            skew = 0.0
            kurt_excess = 0.0
        ratio_max_p99 = float(pmax / p99) if p99 not in (0.0, -0.0) else float("inf") if pmax != 0 else 1.0
        rows.append(
            {
                "variant_id": variant_id,
                "branch_id": branch_id,
                "feature": f,
                "n": n,
                "p1": float(p1),
                "p50": float(p50),
                "mean": mean,
                "p99": float(p99),
                "p999": float(p999),
                "max": float(pmax),
                "std": std,
                "skew": skew,
                "kurt_excess": kurt_excess,
                "asym_norm": float(asym_norm),
                "ratio_max_p99": ratio_max_p99,
                "frac_abs_z_gt5": frac_z_gt5,
                "frac_abs_z_gt10": frac_z_gt10,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", action="append", default=None,
                        help="Repetir flag para varias ramas. Default: todas las del inventario.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    inventory = pl.read_csv(args.inventory_path)
    rows = inventory.filter(pl.col("variant_id") == args.variant_id)
    if args.branch_id is not None:
        rows = rows.filter(pl.col("branch_id").is_in(args.branch_id))
    if rows.height == 0:
        raise SystemExit(f"No hay entradas para variant={args.variant_id} branch={args.branch_id}")

    frames = []
    for record in rows.iter_rows(named=True):
        branch_id = record["branch_id"]
        features = [f.strip() for f in record["features"].split(",") if f.strip()]
        print(f"[diag] {args.variant_id} | {branch_id} | {len(features)} features", flush=True)
        frames.append(diagnose_branch(args.variant_id, branch_id, features, args.input_dir))

    df = pd.concat(frames, ignore_index=True)
    out_path = args.out_dir / args.variant_id / "outlier_diagnostics.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nGuardado: {out_path}\n", flush=True)

    # imprimir resumen ordenado por |skew| desc
    print("=== TOP outlier signals (por |skew|) ===")
    summary_cols = ["branch_id", "feature", "skew", "kurt_excess", "ratio_max_p99",
                    "frac_abs_z_gt5", "frac_abs_z_gt10", "asym_norm"]
    show = df.assign(abs_skew=df["skew"].abs()).sort_values("abs_skew", ascending=False)
    pd.set_option("display.max_rows", 60)
    pd.set_option("display.width", 200)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(show[summary_cols].to_string(index=False))


if __name__ == "__main__":
    main()
