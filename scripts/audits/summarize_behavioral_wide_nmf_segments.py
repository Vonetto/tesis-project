"""Summarize behavioral_wide NMF assignments against QR/BIP and features."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import polars as pl

from scripts.audits.run_behavioral_wide_nmf import (
    DEFAULT_INPUT_DIR,
    DEFAULT_INVENTORY,
    DEFAULT_OUT_DIR,
    SEG_DIR,
    VARIANT_ID,
    load_feature_list,
)


TARGET_COLS = ["is_qr", "is_qr_red", "is_qr_other", "tipo_tarjeta"]
NUMERIC_METADATA_COLS = ["n_viajes", "share_trips_2025", "home_confidence"]


def cramers_v(contingency: np.ndarray) -> tuple[float, float]:
    observed = contingency.astype(float)
    n = observed.sum()
    if n == 0:
        return 0.0, 0.0
    expected = np.outer(observed.sum(axis=1), observed.sum(axis=0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.nansum(np.where(expected > 0, (observed - expected) ** 2 / expected, 0.0))
    denom = n * max(1, min(observed.shape[0] - 1, observed.shape[1] - 1))
    v = float(np.sqrt(chi2 / denom)) if denom > 0 else 0.0
    return float(chi2), v


def parse_k_values(value: str, assignments: pl.DataFrame) -> list[int]:
    available = sorted(
        int(c.replace("segment_k", ""))
        for c in assignments.columns
        if c.startswith("segment_k")
    )
    text = str(value).strip()
    if not text or text.lower() == "all":
        return available
    requested = [int(x.strip()) for x in text.split(",") if x.strip()]
    missing = [k for k in requested if k not in available]
    if missing:
        raise SystemExit(f"Requested k not present in assignments: {missing}")
    return requested


def target_association(joined: pl.DataFrame, cluster_col: str, k: int) -> pd.DataFrame:
    rows: list[dict] = []
    for target in ["is_qr", "tipo_tarjeta"]:
        if target not in joined.columns:
            continue
        contingency = (
            joined.group_by([cluster_col, target])
            .agg(pl.len().alias("n"))
            .pivot(values="n", index=cluster_col, on=target, aggregate_function="sum")
            .fill_null(0)
            .sort(cluster_col)
        )
        values = contingency.drop(cluster_col).to_numpy()
        chi2, v = cramers_v(values)
        rows.append({"k": k, "target": target, "chi2": chi2, "cramers_v": v, "n": int(values.sum())})
    return pd.DataFrame(rows)


def segment_qr_summary(joined: pl.DataFrame, cluster_col: str, k: int) -> pd.DataFrame:
    n_total = joined.height
    base_qr = float(joined["is_qr"].mean())
    base_red = float(joined["is_qr_red"].mean())
    base_other = float(joined["is_qr_other"].mean())
    exprs = [
        pl.len().alias("n_cards"),
        pl.col("is_qr").mean().alias("qr_rate"),
        pl.col("is_qr_red").mean().alias("qr_red_rate"),
        pl.col("is_qr_other").mean().alias("qr_other_rate"),
    ]
    for col in NUMERIC_METADATA_COLS:
        if col in joined.columns:
            exprs.extend(
                [
                    pl.col(col).mean().alias(f"{col}_mean"),
                    pl.col(col).median().alias(f"{col}_median"),
                ]
            )
    out = (
        joined.group_by(cluster_col)
        .agg(exprs)
        .sort(cluster_col)
        .rename({cluster_col: "segment"})
        .with_columns(
            [
                (pl.col("n_cards") / n_total).alias("segment_share"),
                (pl.col("qr_rate") / base_qr).alias("qr_lift_vs_base"),
                (pl.col("qr_red_rate") / base_red).alias("qr_red_lift_vs_base"),
                (pl.col("qr_other_rate") / base_other).alias("qr_other_lift_vs_base"),
            ]
        )
        .to_pandas()
    )
    out.insert(0, "k", k)
    return out


def feature_profile(joined: pl.DataFrame, cluster_col: str, k: int, features: list[str]) -> pd.DataFrame:
    overall = joined.select([pl.col(f).mean().alias(f) for f in features]).row(0, named=True)
    grouped = (
        joined.group_by(cluster_col)
        .agg([pl.col(f).mean().alias(f) for f in features])
        .sort(cluster_col)
    )
    rows: list[dict] = []
    for row in grouped.iter_rows(named=True):
        segment = row[cluster_col]
        for feature in features:
            base = float(overall[feature])
            value = float(row[feature])
            rows.append(
                {
                    "k": k,
                    "segment": segment,
                    "feature": feature,
                    "mean": value,
                    "overall_mean": base,
                    "mean_diff": value - base,
                    "mean_lift": value / base if base != 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def binary_payment_feature_profile(
    joined: pl.DataFrame,
    cluster_col: str,
    k: int,
    features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if "is_qr" not in joined.columns:
        return pd.DataFrame(), pd.DataFrame()

    feature_exprs = [pl.col(f).mean().alias(f) for f in features]
    grouped = (
        joined.group_by([cluster_col, "is_qr"])
        .agg([pl.len().alias("n_cards"), *feature_exprs])
        .sort([cluster_col, "is_qr"])
        .to_pandas()
    )
    payment_base = (
        joined.group_by("is_qr")
        .agg([pl.len().alias("payment_group_n_cards"), *feature_exprs])
        .sort("is_qr")
        .to_pandas()
    )
    segment_all = (
        joined.group_by(cluster_col)
        .agg([pl.len().alias("segment_n_cards"), *feature_exprs])
        .sort(cluster_col)
        .to_pandas()
    )
    universe = joined.select(feature_exprs).row(0, named=True)

    payment_lookup = payment_base.set_index("is_qr").to_dict(orient="index")
    segment_lookup = segment_all.set_index(cluster_col).to_dict(orient="index")

    profile_rows: list[dict] = []
    for row in grouped.to_dict(orient="records"):
        segment = row[cluster_col]
        is_qr = bool(row["is_qr"])
        payment_group = "QR" if is_qr else "BIP"
        payment_row = payment_lookup[row["is_qr"]]
        segment_row = segment_lookup[segment]
        for feature in features:
            value = float(row[feature])
            payment_mean = float(payment_row[feature])
            segment_mean = float(segment_row[feature])
            universe_mean = float(universe[feature])
            profile_rows.append(
                {
                    "k": k,
                    "segment": segment,
                    "payment_group": payment_group,
                    "n_cards": int(row["n_cards"]),
                    "feature": feature,
                    "mean": value,
                    "payment_group_overall_mean": payment_mean,
                    "segment_all_mean": segment_mean,
                    "universe_mean": universe_mean,
                    "mean_lift_vs_payment_group": value / payment_mean if payment_mean else np.nan,
                    "mean_lift_vs_segment_all": value / segment_mean if segment_mean else np.nan,
                    "mean_lift_vs_universe": value / universe_mean if universe_mean else np.nan,
                }
            )

    profile = pd.DataFrame(profile_rows)
    if profile.empty:
        return profile, pd.DataFrame()

    pivot = (
        profile.pivot_table(
            index=["k", "segment", "feature"],
            columns="payment_group",
            values="mean",
            aggfunc="first",
        )
        .reset_index()
    )
    for col in ["QR", "BIP"]:
        if col not in pivot.columns:
            pivot[col] = np.nan
    pivot = pivot.rename(columns={"QR": "qr_mean", "BIP": "bip_mean"})
    pivot["qr_minus_bip"] = pivot["qr_mean"] - pivot["bip_mean"]
    pivot["qr_over_bip"] = np.where(pivot["bip_mean"] != 0, pivot["qr_mean"] / pivot["bip_mean"], np.nan)
    pivot["qr_vs_bip_lift_minus_1"] = pivot["qr_over_bip"] - 1.0
    pivot["abs_qr_vs_bip_lift_minus_1"] = pivot["qr_vs_bip_lift_minus_1"].abs()
    return profile, pivot


def summarize_from_args(args: argparse.Namespace) -> Path:
    matrix_path = args.input_dir / args.variant_id / f"{args.branch_id}.parquet"
    nmf_dir = args.out_dir / args.variant_id / f"{args.branch_id}__{args.feature_tag}" / "nmf"
    assignments_path = nmf_dir / "nmf_assignments.parquet"
    if not matrix_path.exists():
        raise FileNotFoundError(f"No existe matriz: {matrix_path}")
    if not assignments_path.exists():
        raise FileNotFoundError(f"No existen asignaciones NMF: {assignments_path}")

    features = load_feature_list(args.inventory_path, args.variant_id, args.branch_id)
    matrix_cols = ["id_tarjeta", *features, *TARGET_COLS, *NUMERIC_METADATA_COLS]
    available_cols = set(pl.read_parquet_schema(matrix_path).names())
    matrix_cols = [c for c in dict.fromkeys(matrix_cols) if c in available_cols]
    matrix = pl.read_parquet(matrix_path, columns=matrix_cols)
    assignments = pl.read_parquet(assignments_path)
    joined = matrix.join(assignments, on="id_tarjeta", how="inner")
    ks = parse_k_values(args.k, assignments)

    summary_frames: list[pd.DataFrame] = []
    association_frames: list[pd.DataFrame] = []
    profile_frames: list[pd.DataFrame] = []
    payment_profile_frames: list[pd.DataFrame] = []
    payment_diff_frames: list[pd.DataFrame] = []
    for k in ks:
        cluster_col = f"segment_k{k}"
        summary_frames.append(segment_qr_summary(joined, cluster_col, k))
        association_frames.append(target_association(joined, cluster_col, k))
        profile_frames.append(feature_profile(joined, cluster_col, k, features))
        payment_profile, payment_diff = binary_payment_feature_profile(joined, cluster_col, k, features)
        if not payment_profile.empty:
            payment_profile_frames.append(payment_profile)
        if not payment_diff.empty:
            payment_diff_frames.append(payment_diff)

    out_dir = nmf_dir / "posthoc"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(summary_frames, ignore_index=True).to_csv(out_dir / "segment_qr_summary.csv", index=False)
    pd.concat(association_frames, ignore_index=True).to_csv(out_dir / "segment_target_association.csv", index=False)
    pd.concat(profile_frames, ignore_index=True).to_csv(out_dir / "segment_feature_profile.csv", index=False)
    if payment_profile_frames:
        pd.concat(payment_profile_frames, ignore_index=True).to_csv(
            out_dir / "segment_binary_payment_feature_profile.csv",
            index=False,
        )
    if payment_diff_frames:
        pd.concat(payment_diff_frames, ignore_index=True).to_csv(
            out_dir / "segment_qr_vs_bip_feature_diff.csv",
            index=False,
        )
    meta = {
        "matrix_path": str(matrix_path),
        "assignments_path": str(assignments_path),
        "k_values": ks,
        "n_joined": joined.height,
        "features": features,
        "outputs": [
            "segment_qr_summary.csv",
            "segment_target_association.csv",
            "segment_feature_profile.csv",
            "segment_binary_payment_feature_profile.csv",
            "segment_qr_vs_bip_feature_diff.csv",
        ],
    }
    (out_dir / "posthoc_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"OK outputs: {out_dir}", flush=True)
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize behavioral_wide NMF segments.")
    parser.add_argument("--variant-id", default=VARIANT_ID)
    parser.add_argument("--branch-id", default="v0b_alta_n3")
    parser.add_argument("--feature-tag", default="nmf_v0b_robust_minmax_block")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--k", default="all", help="all or comma-separated k values.")
    args = parser.parse_args()
    summarize_from_args(args)


if __name__ == "__main__":
    main()
