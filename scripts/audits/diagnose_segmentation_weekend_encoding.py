"""Diagnostica codificaciones de la senal 'finde' para el bloque B5.

Calcula sobre la matriz R2_abs_core (o cualquier rama con features absolutas):

1. Distribucion univariada de cada feature finde existente y de candidatas nuevas:
   - share_weekend_trips, share_weekend_active_days (existentes en builder)
   - weekend_to_weekday_ratio (nueva: weekend / max(weekday, 1))
   - has_weekend_activity (binaria: weekend_trips > 0)
   - log1p_weekend_active_days (nueva: log(1 + weekend_active_days))

2. Para cada candidata:
   - p1, p50, mean, p99, p99.9, max, std
   - skew, kurt_excess
   - fraccion de masa en 0 (= probabilidad de que no aporte varianza)
   - fraccion de varianza tras StandardScaler concentrada en pocos valores
     (uso entropia normalizada sobre histograma de 50 bins)

3. Correlacion con features de intensidad (Spearman) para detectar redundancia:
   - log_n_trips_total
   - share_active_days
   - avg_trips_per_active_day

Output:
- CSV: tmp/audits/segmentation_models/<variant>/weekend_encoding_diagnostics.csv
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
    """Entropia normalizada del histograma. 1.0 = uniforme, 0.0 = pico unico."""
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
    # mass en bins, post-scaler
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


def build_candidates(df: pl.DataFrame) -> dict[str, np.ndarray]:
    """Construye las codificaciones candidatas a partir de columnas del builder.

    Asume que df tiene n_trips_total reconstruible. Si no esta directo,
    derivamos de log_n_trips_total: n_trips_total = exp(log_n_trips_total) - 1.
    Para weekend_active_days y weekend_to_weekday_ratio necesitamos:
      - weekend_trips: n_trips_total * share_weekend_trips
      - weekday_trips: n_trips_total * share_weekday_trips = n_trips - weekend
    """
    cols = df.columns
    # reconstruir n_trips_total
    if "log_n_trips_total" not in cols:
        raise SystemExit("log_n_trips_total no esta en la matriz. Aborto.")
    n_trips = np.expm1(df["log_n_trips_total"].to_numpy())  # exp(x) - 1

    candidates: dict[str, np.ndarray] = {}

    if "share_weekend_trips" in cols:
        swt = df["share_weekend_trips"].to_numpy()
        candidates["share_weekend_trips"] = swt
        weekend_trips = swt * n_trips
        weekday_trips = (1.0 - swt) * n_trips
        candidates["weekend_to_weekday_ratio"] = weekend_trips / np.where(weekday_trips < 1.0, 1.0, weekday_trips)
        candidates["has_weekend_activity"] = (weekend_trips > 0).astype(float)
        candidates["log1p_weekend_trips"] = np.log1p(weekend_trips)

    if "share_weekend_active_days" in cols:
        swad = df["share_weekend_active_days"].to_numpy()
        candidates["share_weekend_active_days"] = swad

    if "weekend_active_days" in cols:
        wad = df["weekend_active_days"].to_numpy()
        candidates["weekend_active_days"] = wad
        candidates["log1p_weekend_active_days"] = np.log1p(wad)

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

    cand = build_candidates(df)
    print(f"[cand] {len(cand)} candidatas: {list(cand.keys())}", flush=True)

    # intensidad arrays
    intensity = {f: df[f].to_numpy() for f in INTENSIDAD_FEATURES if f in df.columns}
    missing_intensity = [f for f in INTENSIDAD_FEATURES if f not in intensity]
    if missing_intensity:
        print(f"[warn] features de intensidad ausentes: {missing_intensity}", flush=True)

    rows = []
    for name, arr in cand.items():
        stats = feature_distribution(arr)
        # correlaciones con intensidad
        for f, iarr in intensity.items():
            stats[f"spearman_vs_{f}"] = spearman_safe(arr, iarr)
        stats["feature"] = name
        rows.append(stats)

    out_df = pd.DataFrame(rows)
    # ordenar cols
    front = ["feature", "n", "p1", "p50", "mean", "p99", "p999", "max", "std",
             "skew", "kurt_excess", "frac_zero",
             "hist_entropy_raw_norm", "hist_entropy_after_zscore"]
    sp_cols = [c for c in out_df.columns if c.startswith("spearman_")]
    out_df = out_df[front + sp_cols]

    out_dir = args.out_dir / args.variant_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "weekend_encoding_diagnostics.csv"
    out_df.to_csv(out_path, index=False)

    pd.set_option("display.max_rows", 80)
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(f"\nGuardado: {out_path}\n")

    print("=== DISTRIBUCION ===")
    print(out_df[front].to_string(index=False))

    if sp_cols:
        print("\n=== CORRELACIONES CON INTENSIDAD (Spearman) ===")
        print(out_df[["feature"] + sp_cols].to_string(index=False))


if __name__ == "__main__":
    main()
