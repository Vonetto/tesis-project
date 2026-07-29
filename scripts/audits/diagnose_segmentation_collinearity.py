"""Audita colinealidad en feature matrices de segmentacion.

Calcula:
- Matriz Pearson |r| por (variant_id, branch_id).
- Lista pares con |r| >= threshold (default 0.90).
- VIF aproximado por feature (1 / (1 - R^2_j)) via regresion lineal contra el resto.
  VIF > 10 es senal de colinealidad severa estandar.
- Para cada par redundante, marca cual feature recomendar drop con heuristica
  simple: la que tenga mayor VIF medio en el branch.

Exporta CSV por rama:
- correlation_pairs_above_threshold_<variant>.csv
- vif_<variant>.csv
- recommended_drops_<variant>.csv
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


def compute_pairs(corr: np.ndarray, features: list[str], threshold: float) -> list[dict]:
    rows = []
    n = len(features)
    for i in range(n):
        for j in range(i + 1, n):
            r = corr[i, j]
            if abs(r) >= threshold:
                rows.append(
                    {
                        "feature_a": features[i],
                        "feature_b": features[j],
                        "pearson_r": float(r),
                        "abs_r": float(abs(r)),
                    }
                )
    return rows


def compute_vif(X: np.ndarray, features: list[str]) -> list[dict]:
    """VIF clasico: VIF_j = 1 / (1 - R^2_j) regresando feature_j contra el resto."""
    n_feat = X.shape[1]
    rows = []
    # Centrado y escalado para estabilidad numerica
    Xs = (X - X.mean(axis=0)) / np.where(X.std(axis=0, ddof=0) > 0, X.std(axis=0, ddof=0), 1.0)
    for j in range(n_feat):
        y = Xs[:, j]
        Xr = np.delete(Xs, j, axis=1)
        # añadir columna de unos
        A = np.column_stack([np.ones(Xr.shape[0]), Xr])
        # least squares
        try:
            beta, *_ = np.linalg.lstsq(A, y, rcond=None)
            y_hat = A @ beta
            ss_res = ((y - y_hat) ** 2).sum()
            ss_tot = ((y - y.mean()) ** 2).sum()
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            r2 = max(min(r2, 1 - 1e-12), 0.0)
            vif = 1.0 / (1.0 - r2)
        except np.linalg.LinAlgError:
            r2 = float("nan")
            vif = float("inf")
        rows.append({"feature": features[j], "r2_vs_rest": r2, "vif": vif})
    return rows


def recommend_drops(pairs_df: pd.DataFrame, vif_df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Por cada par redundante (|r| >= threshold) recomienda drop: el de mayor VIF."""
    if pairs_df.empty:
        return pd.DataFrame(columns=["pair", "feature_a", "feature_b", "pearson_r", "drop_recommended", "reason"])
    vif_lookup = dict(zip(vif_df["feature"], vif_df["vif"]))
    rows = []
    for _, p in pairs_df.iterrows():
        a, b = p["feature_a"], p["feature_b"]
        vif_a = vif_lookup.get(a, float("nan"))
        vif_b = vif_lookup.get(b, float("nan"))
        if np.isnan(vif_a) and np.isnan(vif_b):
            drop = b
            reason = "VIF NaN en ambos; drop arbitrario (b)"
        elif np.isnan(vif_a):
            drop = a
            reason = "VIF NaN en a"
        elif np.isnan(vif_b):
            drop = b
            reason = "VIF NaN en b"
        else:
            if vif_a >= vif_b:
                drop = a
                reason = f"VIF mayor: a={vif_a:.1f} >= b={vif_b:.1f}"
            else:
                drop = b
                reason = f"VIF mayor: b={vif_b:.1f} > a={vif_a:.1f}"
        rows.append(
            {
                "pair": f"{a} <-> {b}",
                "feature_a": a,
                "feature_b": b,
                "pearson_r": float(p["pearson_r"]),
                "vif_a": float(vif_a) if not np.isnan(vif_a) else None,
                "vif_b": float(vif_b) if not np.isnan(vif_b) else None,
                "drop_recommended": drop,
                "reason": reason,
            }
        )
    return pd.DataFrame(rows)


def audit_branch(
    variant_id: str,
    branch_id: str,
    features: list[str],
    input_dir: Path,
    threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    path = input_dir / variant_id / f"{branch_id}.parquet"
    df = pl.read_parquet(path)
    arr = df.select(features).to_numpy()
    # Drop filas con cualquier nulo en features (no deberian haber, validacion ya paso)
    mask = ~np.isnan(arr).any(axis=1)
    arr = arr[mask]
    corr = np.corrcoef(arr, rowvar=False)
    pairs = compute_pairs(corr, features, threshold)
    pairs_df = pd.DataFrame(pairs)
    if not pairs_df.empty:
        pairs_df.insert(0, "branch_id", branch_id)
        pairs_df.insert(0, "variant_id", variant_id)
        pairs_df = pairs_df.sort_values("abs_r", ascending=False).reset_index(drop=True)

    vif_rows = compute_vif(arr, features)
    vif_df = pd.DataFrame(vif_rows)
    vif_df.insert(0, "branch_id", branch_id)
    vif_df.insert(0, "variant_id", variant_id)
    vif_df = vif_df.sort_values("vif", ascending=False).reset_index(drop=True)

    drops_df = recommend_drops(pairs_df, vif_df, threshold)
    if not drops_df.empty:
        drops_df.insert(0, "branch_id", branch_id)
        drops_df.insert(0, "variant_id", variant_id)
    return pairs_df, vif_df, drops_df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="B_calendar_W15_W17_N14")
    parser.add_argument("--branch-id", action="append", default=None)
    parser.add_argument("--threshold", type=float, default=0.90,
                        help="Umbral de |r| para considerar par redundante.")
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

    all_pairs = []
    all_vif = []
    all_drops = []
    for record in rows.iter_rows(named=True):
        branch_id = record["branch_id"]
        features = [f.strip() for f in record["features"].split(",") if f.strip()]
        print(f"[col] {args.variant_id} | {branch_id} | {len(features)} features", flush=True)
        pairs_df, vif_df, drops_df = audit_branch(
            args.variant_id, branch_id, features, args.input_dir, args.threshold
        )
        all_pairs.append(pairs_df)
        all_vif.append(vif_df)
        all_drops.append(drops_df)

    out_dir = args.out_dir / args.variant_id
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs_full = pd.concat([p for p in all_pairs if not p.empty], ignore_index=True) if any(not p.empty for p in all_pairs) else pd.DataFrame()
    vif_full = pd.concat(all_vif, ignore_index=True)
    drops_full = pd.concat([d for d in all_drops if not d.empty], ignore_index=True) if any(not d.empty for d in all_drops) else pd.DataFrame()

    pairs_path = out_dir / f"collinearity_pairs_thr{int(args.threshold * 100)}.csv"
    vif_path = out_dir / "collinearity_vif.csv"
    drops_path = out_dir / f"collinearity_recommended_drops_thr{int(args.threshold * 100)}.csv"

    pairs_full.to_csv(pairs_path, index=False)
    vif_full.to_csv(vif_path, index=False)
    drops_full.to_csv(drops_path, index=False)

    print(f"\nGuardados:")
    print(f"  pairs      -> {pairs_path}")
    print(f"  vif        -> {vif_path}")
    print(f"  drops rec. -> {drops_path}")

    pd.set_option("display.max_rows", 120)
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")

    if not pairs_full.empty:
        print(f"\n=== PARES con |r| >= {args.threshold} ===")
        print(pairs_full[["variant_id", "branch_id", "feature_a", "feature_b", "pearson_r"]].to_string(index=False))
    else:
        print(f"\n(Sin pares con |r| >= {args.threshold})")

    print("\n=== TOP 25 VIF (peores) ===")
    print(vif_full.sort_values("vif", ascending=False).head(25)[["branch_id", "feature", "r2_vs_rest", "vif"]].to_string(index=False))

    if not drops_full.empty:
        print("\n=== DROPS recomendados por par redundante ===")
        print(drops_full[["branch_id", "pair", "pearson_r", "vif_a", "vif_b", "drop_recommended"]].to_string(index=False))


if __name__ == "__main__":
    main()
