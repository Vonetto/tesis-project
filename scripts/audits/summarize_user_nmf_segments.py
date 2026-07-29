"""Summarize NMF user segments against QR/BIP metadata."""
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

from scripts.audits.build_user_mobility_segmentation_matrix import output_path as matrix_output_path
from scripts.audits.run_user_nmf_segmentation import nmf_output_dir


NUMERIC_PROFILE_COLS = [
    "n_viajes",
    "share_trips_2025",
]
GROUP_PROFILE_COLS = [
    "tipo_tarjeta",
    "home_confidence",
    "home_macrozone",
    "origin_top1_macrozone",
]


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


def summarize_for_k(joined: pl.DataFrame, k: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cluster_col = f"segment_k{k}"
    if cluster_col not in joined.columns:
        raise ValueError(f"No existe columna {cluster_col}")

    base_qr = float(joined["is_qr"].mean())
    base_red = float(joined["is_qr_red"].mean())
    base_other = float(joined["is_qr_other"].mean())
    n_total = joined.height

    agg_exprs = [
        pl.len().alias("n_cards"),
        pl.col("is_qr").mean().alias("qr_rate"),
        pl.col("is_qr_red").mean().alias("qr_red_rate"),
        pl.col("is_qr_other").mean().alias("qr_other_rate"),
    ]
    for c in NUMERIC_PROFILE_COLS:
        if c in joined.columns:
            agg_exprs.extend(
                [
                    pl.col(c).mean().alias(f"{c}_mean"),
                    pl.col(c).median().alias(f"{c}_median"),
                ]
            )
    segment_summary = (
        joined.group_by(cluster_col)
        .agg(agg_exprs)
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

    association_rows = []
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
        association_rows.append({"k": k, "target": target, "chi2": chi2, "cramers_v": v, "n": int(values.sum())})
    association = pd.DataFrame(association_rows)

    long_rows: list[dict] = []
    for c in GROUP_PROFILE_COLS:
        if c not in joined.columns:
            continue
        dist = (
            joined.group_by([cluster_col, c])
            .agg(pl.len().alias("n"))
            .with_columns((pl.col("n") / pl.col("n").sum().over(cluster_col)).alias("share_within_segment"))
            .sort([cluster_col, "n"], descending=[False, True])
        )
        for row in dist.iter_rows(named=True):
            long_rows.append(
                {
                    "k": k,
                    "segment": row[cluster_col],
                    "variable": c,
                    "value": row[c],
                    "n": row["n"],
                    "share_within_segment": row["share_within_segment"],
                }
            )
    categorical_profile = pd.DataFrame(long_rows)
    return segment_summary, association, categorical_profile


def summarize_segments(matrix_path: Path, k_values: list[int] | None = None) -> Path:
    nmf_dir = nmf_output_dir(matrix_path)
    assignments_path = nmf_dir / "nmf_assignments.parquet"
    if not assignments_path.exists():
        raise FileNotFoundError(f"No existen asignaciones NMF: {assignments_path}")

    matrix = pl.read_parquet(matrix_path)
    assignments = pl.read_parquet(assignments_path)
    joined = matrix.join(assignments, on="id_tarjeta", how="inner")
    available_ks = sorted(
        int(c.replace("segment_k", "")) for c in assignments.columns if c.startswith("segment_k")
    )
    ks = available_ks if k_values is None else k_values

    summary_frames = []
    association_frames = []
    categorical_frames = []
    for k in ks:
        summary, association, categorical = summarize_for_k(joined, k)
        summary.insert(0, "k", k)
        summary_frames.append(summary)
        association_frames.append(association)
        categorical_frames.append(categorical)

    out_dir = nmf_dir / "posthoc"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(summary_frames, ignore_index=True).to_csv(out_dir / "segment_qr_summary.csv", index=False)
    pd.concat(association_frames, ignore_index=True).to_csv(out_dir / "segment_target_association.csv", index=False)
    if categorical_frames:
        pd.concat(categorical_frames, ignore_index=True).to_csv(out_dir / "segment_categorical_profile.csv", index=False)
    meta = {
        "matrix_path": str(matrix_path),
        "assignments_path": str(assignments_path),
        "k_values": ks,
        "n_joined": joined.height,
        "outputs": [
            "segment_qr_summary.csv",
            "segment_target_association.csv",
            "segment_categorical_profile.csv",
        ],
    }
    (out_dir / "posthoc_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"OK outputs: {out_dir}")
    return out_dir


def parse_k_values(value: str) -> list[int] | None:
    text = str(value).strip()
    if not text or text.lower() == "all":
        return None
    return [int(x.strip()) for x in text.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize NMF segment assignments against QR/BIP metadata.")
    parser.add_argument("--scope", default="interannual_ml")
    parser.add_argument("--variant", default="clean")
    parser.add_argument("--home-filter", default="alta")
    parser.add_argument("--min-trips", type=int, default=3)
    parser.add_argument("--min-home-trips", type=int, default=0)
    parser.add_argument("--matrix-spec", default="macro_franja_modo")
    parser.add_argument("--normalization", default="share")
    parser.add_argument("--k", default="all", help="all or comma-separated k values.")
    args = parser.parse_args()

    matrix_path = matrix_output_path(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
        args.matrix_spec,
        args.normalization,
    )
    summarize_segments(matrix_path, parse_k_values(args.k))


if __name__ == "__main__":
    main()
