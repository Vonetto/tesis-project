"""Diagnostica codificaciones del bloque espacial-origen para B6.

Calcula sobre la matriz R2_abs_core (o cualquier rama con features absolutas):

1. Distribucion univariada de cada feature espacial existente y candidatas:
   - n_unique_origin_zones (entero, conteo)
   - entropy_origin_zones_norm (en [0,1], saturada cerca de 1)
   - share_top_origin_zone (en [0,1])
   - log1p_n_unique_origin_zones (transformacion log de la cola)
   - inv_entropy_origin_zones = 1 - entropy_origin_zones_norm (invierte saturacion)
   - log_inv_entropy = log(2 - entropy) (acentua extremos bajos)
   - top_zone_concentration = share_top_origin_zone (alias para claridad)

2. Para cada candidata:
   - Cuantiles p1, p50, mean, p99, p99.9, max, std
   - skew, kurt_excess
   - frac_zero (probabilidad de que sea dummy)
   - hist_entropy_raw_norm y hist_entropy_after_zscore

3. Correlacion con features de intensidad (Spearman) para detectar redundancia.

Output:
- CSV: tmp/audits/segmentation_models/<variant>/spatial_encoding_diagnostics.csv
- Stdout: tabla ordenada.
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
from scipy.stats import spearmanr


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_behavioral_2x2" / "features"
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_models"

INTENSIDAD_FEATURES = [
    "log_n_trips_total",
    "share_active_days",
    "avg_trips_per_active_day",
]


def histogram_entropy(arr: np.ndarray, bins: int = 50) -> float:
    hist, _ = np.histogram(arr, bins=bins)
    p = hist / hist.sum() if hist.sum() > 0 else hist
    p = p[p > 0]
    if p.size <= 1:
        return 0.0
    ent = -(p * np.log(p)).sum()
    return float(ent / np.log(bins))


def feature_distribution(arr: np.ndarray) -> dict:
    arr = arr[~np.isnan(arr)]
    if arr.size == 0:
        return {"n": 0}
    p1, p50, p99, p999, pmax = np.percentile(arr, [1, 50, 99, 99.9, 100])
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    if std > 0:
        m3 = float(((arr - mean) ** 3).mean())
        m4 = float(((arr - mean) ** 4).mean())
        skew = m3 / std ** 3
        kurt_excess = m4 / std ** 4 - 3.0
    else:
        skew = 0.0
        kurt_excess = 0.0
    frac_zero = float((arr == 0).mean())
    ent_raw = histogram_entropy(arr, bins=50)
    if std > 0:
        z = (arr - mean) / std
        ent_z = histogram_entropy(z, bins=50)
    else:
        ent_z = 0.0
    return {
        "n": int(arr.size),
        "p1": float(p1),
        "p50": float(p50),
        "mean": mean,
        "p99": float(p99),
        "p999": float(p999),
        "max": float(pmax),
        "std": std,
        "skew": skew,
        "kurt_excess": kurt_excess,
        "frac_zero": frac_zero,
        "hist_entropy_raw_norm": ent_raw,
        "hist_entropy_after_zscore": ent_z,
    }


def spearman_safe(a: np.ndarray, b: np.ndarray) -> float:
    mask = ~np.isnan(a) & ~np.isnan(b)
    if mask.sum() < 10:
        return float("nan")
    rho, _ = spearmanr(a[mask], b[mask])
    return float(rho)


def build_spatial_candidates(df: pl.DataFrame) -> dict[str, np.ndarray]:
    cols = df.columns
    candidates: dict[str, np.ndarray] = {}

    if "n_unique_origin_zones" in cols:
        n_zones = df["n_unique_origin_zones"].cast(pl.Float64).to_numpy()
        candidates["n_unique_origin_zones"] = n_zones
        candidates["log1p_n_unique_origin_zones"] = np.log1p(n_zones)

    if "entropy_origin_zones_norm" in cols:
        ent = df["entropy_origin_zones_norm"].to_numpy()
        candidates["entropy_origin_zones_norm"] = ent
        candidates["inv_entropy_origin_zones"] = 1.0 - ent
        # log(2 - x) acentua extremos bajos sin explotar en 0 (x maximo es 1, log(1)=0)
        candidates["neg_log_inv_entropy"] = -np.log(np.clip(1.0 - ent, 1e-6, 1.0))

    if "share_top_origin_zone" in cols:
        sto = df["share_top_origin_zone"].to_numpy()
        candidates["share_top_origin_zone"] = sto

    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", default="R2_abs_core_2025")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = parser.parse_args()

    path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    if not path.exists():
        raise SystemExit(f"No existe: {path}")
    df = pl.read_parquet(path)
    print(f"[load] {path.name} rows={df.height:,} cols={df.width}", flush=True)

    cand = build_spatial_candidates(df)
    print(f"[cand] {len(cand)} candidatas: {list(cand.keys())}", flush=True)

    intensity = {f: df[f].to_numpy() for f in INTENSIDAD_FEATURES if f in df.columns}
    missing_intensity = [f for f in INTENSIDAD_FEATURES if f not in intensity]
    if missing_intensity:
        print(f"[warn] features de intensidad ausentes: {missing_intensity}", flush=True)

    rows = []
    for name, arr in cand.items():
        stats = feature_distribution(arr)
        for f, iarr in intensity.items():
            stats[f"spearman_vs_{f}"] = spearman_safe(arr, iarr)
        # tambien correlacion cruzada entre candidatas espaciales para detectar redundancia
        stats["feature"] = name
        rows.append(stats)

    out_df = pd.DataFrame(rows)
    front = ["feature", "n", "p1", "p50", "mean", "p99", "p999", "max", "std",
             "skew", "kurt_excess", "frac_zero",
             "hist_entropy_raw_norm", "hist_entropy_after_zscore"]
    sp_cols = [c for c in out_df.columns if c.startswith("spearman_")]
    out_df = out_df[front + sp_cols]

    out_dir = args.out_dir / args.variant_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "spatial_encoding_diagnostics.csv"
    out_df.to_csv(out_path, index=False)

    pd.set_option("display.max_rows", 80)
    pd.set_option("display.width", 240)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(f"\nGuardado: {out_path}\n")

    print("=== DISTRIBUCION ===")
    print(out_df[front].to_string(index=False))

    if sp_cols:
        print("\n=== CORRELACIONES CON INTENSIDAD (Spearman) ===")
        print(out_df[["feature"] + sp_cols].to_string(index=False))

    # correlacion cruzada entre candidatas espaciales
    print("\n=== CORRELACIONES CRUZADAS (Spearman) entre candidatas espaciales ===")
    cand_names = list(cand.keys())
    n_c = len(cand_names)
    cross = np.full((n_c, n_c), np.nan)
    for i, a_name in enumerate(cand_names):
        for j, b_name in enumerate(cand_names):
            if i <= j:
                continue
            cross[i, j] = spearman_safe(cand[a_name], cand[b_name])
    cross_df = pd.DataFrame(cross, index=cand_names, columns=cand_names)
    print(cross_df.to_string())


if __name__ == "__main__":
    main()
