"""Post-hoc payment lift diagnostic for PCA components.

Fits PCA on a feature matrix sample, bins PC scores into quantiles, and reports
QR / QR_RED / QR_OTHER / BIP rates and lifts by PC bin.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["BLIS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import polars as pl
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation" / "features"
DEFAULT_INVENTORY = (
    PROJECT_ROOT
    / "tmp"
    / "audits"
    / "user_level_redesign"
    / "segmentation"
    / "structural_wide_feature_matrix_inventory.csv"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation" / "models"

TARGET_COLS = ["is_qr", "is_qr_red", "is_qr_other", "tipo_tarjeta"]
OUTCOMES = {
    "qr": "is_qr",
    "qr_red": "is_qr_red",
    "qr_other": "is_qr_other",
    "bip": "is_bip",
}


def parse_csv_ints(raw: str) -> list[int]:
    values = [int(x.strip()) for x in raw.split(",") if x.strip()]
    if not values:
        raise SystemExit("Debe entregar al menos un bin en --bins.")
    if any(v < 2 for v in values):
        raise SystemExit("--bins debe contener enteros >= 2.")
    return values


def load_feature_list(inventory_path: Path, variant_id: str, branch_id: str) -> list[str]:
    inv = pl.read_csv(inventory_path)
    row = inv.filter((pl.col("variant_id") == variant_id) & (pl.col("branch_id") == branch_id))
    if row.height == 0:
        raise SystemExit(f"No entry in inventory: {variant_id} | {branch_id}")
    return [f.strip() for f in row["features"][0].split(",") if f.strip()]


def branch_input_path(input_dir: Path, variant_id: str, branch_id: str) -> Path:
    path = input_dir / variant_id / f"{branch_id}.parquet"
    if not path.exists():
        raise SystemExit(f"No existe input parquet: {path}")
    return path


def safe_quantile_bins(scores: pd.Series, n_bins: int) -> pd.Series:
    ranked = scores.rank(method="first")
    labels = [f"Q{i}" for i in range(1, n_bins + 1)]
    return pd.qcut(ranked, q=n_bins, labels=labels)


def make_lift_rows(scores_df: pd.DataFrame, pcs: list[str], bins: list[int]) -> pd.DataFrame:
    baselines = {name: float(scores_df[col].mean()) for name, col in OUTCOMES.items()}
    baseline_qr = np.clip(baselines["qr"], 1e-12, 1 - 1e-12)
    baseline_qr_odds = baseline_qr / (1 - baseline_qr)
    rows: list[dict] = []

    for pc in pcs:
        for n_bins in bins:
            binned = safe_quantile_bins(scores_df[pc], n_bins)
            tmp = scores_df.assign(bin=binned)
            grouped = tmp.groupby("bin", observed=True)
            for bin_label, g in grouped:
                row = {
                    "pc": pc,
                    "n_bins": n_bins,
                    "bin": str(bin_label),
                    "n": int(len(g)),
                    "share": float(len(g) / len(scores_df)),
                    "pc_score_min": float(g[pc].min()),
                    "pc_score_max": float(g[pc].max()),
                    "pc_score_mean": float(g[pc].mean()),
                }
                for name, col in OUTCOMES.items():
                    rate = float(g[col].mean())
                    base = baselines[name]
                    row[f"{name}_rate"] = rate
                    row[f"{name}_base_rate"] = base
                    row[f"{name}_lift"] = rate / base if base else np.nan

                qr = np.clip(row["qr_rate"], 1e-12, 1 - 1e-12)
                row["qr_vs_bip_odds_lift"] = (qr / (1 - qr)) / baseline_qr_odds
                rows.append(row)
    return pd.DataFrame(rows)


def summarize_extremes(lift_df: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "qr_lift",
        "qr_red_lift",
        "qr_other_lift",
        "bip_lift",
        "qr_vs_bip_odds_lift",
    ]
    rows: list[dict] = []
    for (pc, n_bins), g in lift_df.groupby(["pc", "n_bins"], sort=False):
        row = {"pc": pc, "n_bins": int(n_bins)}
        for metric in metrics:
            max_row = g.loc[g[metric].idxmax()]
            min_row = g.loc[g[metric].idxmin()]
            row[f"{metric}_max"] = float(max_row[metric])
            row[f"{metric}_max_bin"] = str(max_row["bin"])
            row[f"{metric}_min"] = float(min_row[metric])
            row[f"{metric}_min_bin"] = str(min_row["bin"])
            row[f"{metric}_spread"] = float(max_row[metric] - min_row[metric])
        rows.append(row)
    return pd.DataFrame(rows)


def make_long_extremes(summary_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in summary_df.iterrows():
        for outcome in ["qr_lift", "qr_red_lift", "qr_other_lift", "bip_lift", "qr_vs_bip_odds_lift"]:
            rows.append(
                {
                    "pc": row["pc"],
                    "n_bins": int(row["n_bins"]),
                    "outcome": outcome,
                    "max_lift": row[f"{outcome}_max"],
                    "max_bin": row[f"{outcome}_max_bin"],
                    "min_lift": row[f"{outcome}_min"],
                    "min_bin": row[f"{outcome}_min_bin"],
                    "spread": row[f"{outcome}_spread"],
                    "max_abs_deviation_from_1": max(abs(row[f"{outcome}_max"] - 1), abs(row[f"{outcome}_min"] - 1)),
                }
            )
    return pd.DataFrame(rows).sort_values(["outcome", "n_bins", "max_abs_deviation_from_1"], ascending=[True, True, False])


def payment_correlations(scores_df: pd.DataFrame, pcs: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for pc in pcs:
        for name, col in OUTCOMES.items():
            rows.append(
                {
                    "pc": pc,
                    "outcome": name,
                    "pearson_corr": float(scores_df[pc].corr(scores_df[col], method="pearson")),
                    "spearman_corr": float(scores_df[pc].corr(scores_df[col], method="spearman")),
                }
            )
    return pd.DataFrame(rows)


def summarize_loadings(features: list[str], loadings: np.ndarray, pcs: list[str], top_n: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    loadings_df = pd.DataFrame(loadings, columns=pcs)
    loadings_df.insert(0, "variable", features)

    rows: list[dict] = []
    for pc in pcs:
        tmp = loadings_df[["variable", pc]].copy()
        tmp["abs_loading"] = tmp[pc].abs()
        for rank, (_, row) in enumerate(tmp.sort_values("abs_loading", ascending=False).head(top_n).iterrows(), start=1):
            rows.append(
                {
                    "pc": pc,
                    "rank": rank,
                    "variable": row["variable"],
                    "loading": float(row[pc]),
                    "abs_loading": float(row["abs_loading"]),
                }
            )
    return loadings_df, pd.DataFrame(rows)


def plot_heatmap(lift_df: pd.DataFrame, metric: str, n_bins: int, out_path: Path) -> None:
    data = lift_df[lift_df["n_bins"] == n_bins].pivot(index="pc", columns="bin", values=metric)
    data = data.reindex(index=sorted(data.index, key=lambda x: int(x.replace("PC", ""))))
    ordered_cols = sorted(data.columns, key=lambda x: int(x.replace("Q", "")))
    data = data[ordered_cols]

    fig, ax = plt.subplots(figsize=(max(7, n_bins * 0.7), 7))
    centered = data.to_numpy(dtype=float) - 1
    vmax = np.nanmax(np.abs(centered))
    vmax = min(max(vmax, 0.15), 1.5)
    im = ax.imshow(centered, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(np.arange(len(data.columns)), data.columns)
    ax.set_yticks(np.arange(len(data.index)), data.index)
    ax.set_xlabel("Bin del score PCA")
    ax.set_ylabel("Componente")
    ax.set_title(f"{metric} - 1 por bin PCA ({n_bins} bins)")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("lift - 1")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant-id", default="structural_wide")
    parser.add_argument("--branch-id", required=True)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--feature-tag", default="pca_payment_lifts")
    parser.add_argument("--sample-size", type=int, default=1_000_000)
    parser.add_argument("--n-components", type=int, default=15)
    parser.add_argument("--bins", default="5,10")
    parser.add_argument("--random-seed", type=int, default=20260607)
    args = parser.parse_args()

    bins = parse_csv_ints(args.bins)
    input_path = branch_input_path(args.input_dir, args.variant_id, args.branch_id)
    features = load_feature_list(args.inventory_path, args.variant_id, args.branch_id)

    cols = ["id_tarjeta", *TARGET_COLS, *features]
    df = pl.read_parquet(input_path, columns=cols)
    missing_targets = [c for c in TARGET_COLS if c not in df.columns]
    if missing_targets:
        raise SystemExit(f"Faltan columnas target: {missing_targets}")
    missing_features = [c for c in features if c not in df.columns]
    if missing_features:
        raise SystemExit(f"Faltan features: {missing_features}")

    n_total = df.height
    if args.sample_size and args.sample_size > 0 and n_total > args.sample_size:
        df = df.sample(n=args.sample_size, seed=args.random_seed)
    print(f"[load] {input_path.name} total={n_total:,} sample={df.height:,} features={len(features)}", flush=True)

    pdf = df.to_pandas()
    pdf["is_bip"] = (pdf["tipo_tarjeta"] == "BIP").astype(np.int8)
    for col in ["is_qr", "is_qr_red", "is_qr_other"]:
        pdf[col] = pdf[col].astype(np.int8)

    X = pdf[features].to_numpy(dtype=np.float64)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    n_components = min(args.n_components, len(features))
    with threadpool_limits(limits=1):
        pca = PCA(n_components=n_components, random_state=args.random_seed, svd_solver="randomized")
        scores = pca.fit_transform(X_scaled)

    pcs = [f"PC{i}" for i in range(1, n_components + 1)]
    scores_df = pd.DataFrame(scores, columns=pcs)
    for col in ["id_tarjeta", "tipo_tarjeta", "is_qr", "is_qr_red", "is_qr_other", "is_bip"]:
        scores_df[col] = pdf[col].to_numpy()

    out_path = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}" / "pca_payment_lifts"
    out_path.mkdir(parents=True, exist_ok=True)

    explained = pd.DataFrame(
        {
            "pc": pcs,
            "explained_var_ratio": pca.explained_variance_ratio_,
            "cumulative_var_ratio": np.cumsum(pca.explained_variance_ratio_),
        }
    )
    lift_df = make_lift_rows(scores_df, pcs, bins)
    summary_df = summarize_extremes(lift_df).merge(explained, on="pc", how="left")
    extremes_df = make_long_extremes(summary_df)
    corr_df = payment_correlations(scores_df, pcs).merge(explained, on="pc", how="left")
    loadings = pca.components_.T * np.sqrt(pca.explained_variance_)
    loadings_df, top_loadings_df = summarize_loadings(features, loadings, pcs)

    explained.to_csv(out_path / "pc_explained_variance_sample.csv", index=False)
    loadings_df.to_csv(out_path / "pc_loadings_sample.csv", index=False)
    top_loadings_df.to_csv(out_path / "pc_top_loadings_sample.csv", index=False)
    lift_df.to_csv(out_path / "pc_payment_lift_bins.csv", index=False)
    summary_df.to_csv(out_path / "pc_payment_lift_summary.csv", index=False)
    extremes_df.to_csv(out_path / "pc_payment_lift_extremes_long.csv", index=False)
    corr_df.to_csv(out_path / "pc_payment_correlations.csv", index=False)

    for n_bins in bins:
        for metric in ["qr_lift", "qr_red_lift", "qr_other_lift", "bip_lift", "qr_vs_bip_odds_lift"]:
            plot_heatmap(lift_df, metric, n_bins, out_path / f"heatmap_{metric}_{n_bins}bins.png")

    run_meta = {
        "variant_id": args.variant_id,
        "branch_id": args.branch_id,
        "input_path": str(input_path),
        "n_total": n_total,
        "n_sample": int(len(scores_df)),
        "n_features": len(features),
        "n_components": n_components,
        "bins": bins,
        "random_seed": args.random_seed,
        "features": features,
        "outcomes": OUTCOMES,
    }
    (out_path / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    print("\nTOP QR_RED EXTREMES", flush=True)
    top_red = extremes_df[(extremes_df["outcome"] == "qr_red_lift") & (extremes_df["n_bins"] == max(bins))]
    print(top_red.head(15).to_string(index=False), flush=True)
    print(f"\nOK outputs: {out_path}", flush=True)


if __name__ == "__main__":
    main()
