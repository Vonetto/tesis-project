"""Distance + softmax initial assignment for communal microdata -> manzana-entidad.

This module adds the main missing piece from the article's initial assignment:
- explicit scaling of fine manzana objectives to communal microdata totals
- weighted distance between household-group profiles and manzana target profiles
- softmax-like allocation with capacity constraints

We still assign commune by commune and preserve exact household quotas by
manzana. Simulated annealing is intentionally left for a later stage.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from lib.censo2024_microdata_base import MicrodataPaths
from lib.censo2024_spatialize_baseline import (
    DEFAULT_PILOT_COMUNAS,
    aggregate_assignment_to_manzent,
    build_pilot_artifacts,
    evaluate_assignment,
    scale_integer_quotas,
)
from lib.censo2024_spatialize_profile import PROFILE_TARGET_VARS, summarize_eval_by_cut
from lib.censo2024_spatialize_profile_discrete import scale_integer_quotas_capped

SIZE_BUCKETS = [
    ("1", 1, 1, 1.0),
    ("2", 2, 2, 2.0),
    ("34", 3, 4, 3.5),
    ("5p", 5, 999, 5.5),
]
SOFTMAX_WEIGHTS = {
    "compu": 0.30,
    "internet": 0.30,
    "hacin": 0.20,
    "size": 0.20,
}


def _size_bucket_and_value(n: float) -> tuple[str, float]:
    for label, low, high, rep in SIZE_BUCKETS:
        if low <= n <= high:
            return label, rep
    return "5p", 5.5


def encode_household_softmax_groups(household_base: pd.DataFrame) -> pd.DataFrame:
    df = household_base.copy()
    df["CUT"] = df["comuna"].astype("string")
    df["has_compu"] = (df["p15b_serv_compu"] == 1).fillna(False).astype(int)
    df["has_internet_any"] = (
        (df["p15d_serv_internet_fija"] == 1)
        | (df["p15e_serv_internet_movil"] == 1)
        | (df["p15f_serv_internet_satelital"] == 1)
    ).fillna(False).astype(int)
    df["is_hacinado"] = (pd.to_numeric(df["indice_hacinamiento"], errors="coerce") > 2.5).fillna(False).astype(int)
    df["n_personas_hogar_num"] = pd.to_numeric(df["n_personas_hogar"], errors="coerce").fillna(1.0).clip(lower=1.0)

    bucket_info = df["n_personas_hogar_num"].map(_size_bucket_and_value)
    df["size_bucket"] = bucket_info.map(lambda x: x[0])
    df["size_bucket_value"] = bucket_info.map(lambda x: x[1]).astype(float)
    df["group_code"] = (
        df["has_compu"].astype(str)
        + df["has_internet_any"].astype(str)
        + df["is_hacinado"].astype(str)
        + "_"
        + df["size_bucket"].astype(str)
    )
    return df


def _scaled_attr_by_cut(
    targets_cut: pd.DataFrame,
    observed_col: str,
    target_total: int,
    cap_col: str | None = None,
) -> pd.Series:
    weights = pd.to_numeric(targets_cut[observed_col], errors="coerce").fillna(0.0).clip(lower=0.0)
    if cap_col is None:
        return scale_integer_quotas(weights, target_total=target_total)
    caps = pd.to_numeric(targets_cut[cap_col], errors="coerce").fillna(0).clip(lower=0).astype(int)
    return scale_integer_quotas_capped(weights, target_total=target_total, caps=caps)


def build_scaled_manzent_targets(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
) -> pd.DataFrame:
    hh = encode_household_softmax_groups(household_base)
    targets = manzent_targets.copy()
    outputs: list[pd.DataFrame] = []

    for cut, hh_cut in hh.groupby("CUT", sort=True):
        t = targets.loc[targets["CUT"] == cut].copy()
        t_pos = t.loc[pd.to_numeric(t["n_hog"], errors="coerce").fillna(0) > 0].copy()
        if not t_pos.empty:
            t = t_pos
        elif t.empty:
            raise ValueError(f"No MANZENT targets found for CUT={cut}")

        total_hog = len(hh_cut)
        total_per = int(pd.to_numeric(hh_cut["n_personas_hogar_num"], errors="coerce").fillna(0).sum())
        total_compu = int(hh_cut["has_compu"].sum())
        total_internet = int(hh_cut["has_internet_any"].sum())
        total_hacin = int(hh_cut["is_hacinado"].sum())

        t["quota_hogares_scaled"] = _scaled_attr_by_cut(t, "n_hog", total_hog).values
        t["obj_n_per_scaled"] = _scaled_attr_by_cut(t, "n_per", total_per).values
        t["obj_compu_scaled"] = _scaled_attr_by_cut(t, "n_serv_compu", total_compu, cap_col="quota_hogares_scaled").values
        t["obj_internet_scaled"] = _scaled_attr_by_cut(t, "n_internet", total_internet, cap_col="quota_hogares_scaled").values
        t["obj_hacin_scaled"] = _scaled_attr_by_cut(t, "n_viv_hacinadas", total_hacin, cap_col="quota_hogares_scaled").values

        t["target_share_compu"] = t["obj_compu_scaled"] / t["quota_hogares_scaled"].replace({0: pd.NA})
        t["target_share_internet"] = t["obj_internet_scaled"] / t["quota_hogares_scaled"].replace({0: pd.NA})
        t["target_share_hacin"] = t["obj_hacin_scaled"] / t["quota_hogares_scaled"].replace({0: pd.NA})
        t["target_persons_per_hog"] = t["obj_n_per_scaled"] / t["quota_hogares_scaled"].replace({0: pd.NA})
        t["remaining_capacity"] = t["quota_hogares_scaled"].astype(int)
        outputs.append(t)

    return pd.concat(outputs, ignore_index=True)


def _group_feature_frame(hh_cut: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        hh_cut.groupby("group_code", dropna=False)
        .agg(
            group_count=("hogar_uid", "count"),
            has_compu=("has_compu", "first"),
            has_internet_any=("has_internet_any", "first"),
            is_hacinado=("is_hacinado", "first"),
            size_bucket_value=("size_bucket_value", "first"),
        )
        .reset_index()
    )
    return grouped.sort_values("group_count", ascending=True, kind="mergesort").reset_index(drop=True)


def group_to_manzent_distance(group_row: pd.Series, targets_cut: pd.DataFrame) -> pd.Series:
    size_norm = pd.to_numeric(targets_cut["target_persons_per_hog"], errors="coerce").fillna(0.0).clip(lower=1.0, upper=8.0) / 8.0
    group_size_norm = float(group_row["size_bucket_value"]) / 8.0
    dist = (
        SOFTMAX_WEIGHTS["compu"] * (pd.to_numeric(targets_cut["target_share_compu"], errors="coerce").fillna(0.0) - float(group_row["has_compu"])).abs()
        + SOFTMAX_WEIGHTS["internet"] * (pd.to_numeric(targets_cut["target_share_internet"], errors="coerce").fillna(0.0) - float(group_row["has_internet_any"])).abs()
        + SOFTMAX_WEIGHTS["hacin"] * (pd.to_numeric(targets_cut["target_share_hacin"], errors="coerce").fillna(0.0) - float(group_row["is_hacinado"])).abs()
        + SOFTMAX_WEIGHTS["size"] * (size_norm - group_size_norm).abs()
    )
    return dist


def softmax_capacity_weights(
    distance: pd.Series,
    capacity: pd.Series,
    tau: float,
) -> pd.Series:
    capacity = pd.to_numeric(capacity, errors="coerce").fillna(0.0).clip(lower=0.0)
    distance = pd.to_numeric(distance, errors="coerce").fillna(distance.max() if len(distance) else 0.0)
    logits = np.exp(-distance / max(tau, 1e-6))
    weights = capacity * logits
    if float(weights.sum()) <= 0:
        return capacity
    return weights


def allocate_group_counts_softmax(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
    tau: float = 0.03,
) -> pd.DataFrame:
    hh = encode_household_softmax_groups(household_base)
    scaled_targets = build_scaled_manzent_targets(household_base, manzent_targets)
    outputs: list[pd.DataFrame] = []

    for cut, hh_cut in hh.groupby("CUT", sort=True):
        t = scaled_targets.loc[scaled_targets["CUT"] == cut].copy()
        groups = _group_feature_frame(hh_cut)

        for _, group_row in groups.iterrows():
            group_code = group_row["group_code"]
            count = int(group_row["group_count"])
            col = f"group_quota_{group_code}"
            distance = group_to_manzent_distance(group_row, t)
            weights = softmax_capacity_weights(distance=distance, capacity=t["remaining_capacity"], tau=tau)
            alloc = scale_integer_quotas_capped(weights, target_total=count, caps=t["remaining_capacity"])
            t[col] = alloc.values
            t["remaining_capacity"] = t["remaining_capacity"] - t[col].astype(int)

        if int(t["remaining_capacity"].sum()) != 0:
            raise ValueError(f"Unfilled manzana capacity for CUT={cut}: {int(t['remaining_capacity'].sum())}")
        outputs.append(t)

    return pd.concat(outputs, ignore_index=True)


def assign_households_softmax_quota(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
    tau: float = 0.03,
    seed: int = 42,
) -> pd.DataFrame:
    hh = encode_household_softmax_groups(household_base)
    targets_alloc = allocate_group_counts_softmax(household_base, manzent_targets, tau=tau)
    rng = np.random.default_rng(seed)
    assignments: list[pd.DataFrame] = []

    for cut, hh_cut in hh.groupby("CUT", sort=True):
        t = targets_alloc.loc[targets_alloc["CUT"] == cut].copy()
        for group_code, hh_group in hh_cut.groupby("group_code", sort=True):
            quota_col = f"group_quota_{group_code}"
            slots = t.loc[t.index.repeat(t[quota_col].astype(int))].copy().reset_index(drop=True)
            if len(slots) != len(hh_group):
                raise ValueError(
                    f"Group slot mismatch for CUT={cut}, group={group_code}: "
                    f"{len(slots)} slots vs {len(hh_group)} households"
                )
            slots["_slot_tie"] = rng.random(len(slots))
            slots = slots.sort_values(
                by=["target_persons_per_hog", "_slot_tie", "MANZENT"],
                ascending=[False, False, True],
                kind="mergesort",
            ).reset_index(drop=True)

            hh_group = hh_group.copy()
            hh_group["_hh_tie"] = rng.random(len(hh_group))
            hh_group = hh_group.sort_values(
                by=["n_personas_hogar_num", "_hh_tie", "hogar_uid"],
                ascending=[False, False, True],
                kind="mergesort",
            ).reset_index(drop=True)

            hh_group["MANZENT"] = slots["MANZENT"].astype("string")
            hh_group["CUT_target"] = slots["CUT"].astype("string")
            hh_group["assigned_group_code"] = group_code
            assignments.append(hh_group)

    return pd.concat(assignments, ignore_index=True)


def softmax_margin_fit_by_cut(assigned: pd.DataFrame, scaled_targets: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    assigned = assigned.copy()
    assigned["has_compu"] = assigned["has_compu"].fillna(0).astype(int)
    assigned["has_internet_any"] = assigned["has_internet_any"].fillna(0).astype(int)
    assigned["is_hacinado"] = assigned["is_hacinado"].fillna(0).astype(int)
    assigned["n_personas_hogar_num"] = pd.to_numeric(assigned["n_personas_hogar_num"], errors="coerce").fillna(0.0)

    recon = (
        assigned.groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            n_hog_recon=("hogar_uid", "count"),
            n_compu_recon=("has_compu", "sum"),
            n_internet_recon=("has_internet_any", "sum"),
            n_hacin_recon=("is_hacinado", "sum"),
            n_per_recon=("n_personas_hogar_num", "sum"),
        )
        .reset_index()
        .rename(columns={"CUT_target": "CUT"})
    )
    merged = scaled_targets.merge(recon, on=["CUT", "MANZENT"], how="left")
    merged[["n_hog_recon", "n_compu_recon", "n_internet_recon", "n_hacin_recon", "n_per_recon"]] = merged[
        ["n_hog_recon", "n_compu_recon", "n_internet_recon", "n_hacin_recon", "n_per_recon"]
    ].fillna(0)

    for cut, grp in merged.groupby("CUT", dropna=False):
        out_rows.append(
            {
                "CUT": str(cut),
                "n_manzent": int(len(grp)),
                "hog_mae": float((grp["quota_hogares_scaled"] - grp["n_hog_recon"]).abs().mean()),
                "compu_mae": float((grp["obj_compu_scaled"] - grp["n_compu_recon"]).abs().mean()),
                "internet_mae": float((grp["obj_internet_scaled"] - grp["n_internet_recon"]).abs().mean()),
                "hacin_mae": float((grp["obj_hacin_scaled"] - grp["n_hacin_recon"]).abs().mean()),
                "per_mae": float((grp["obj_n_per_scaled"] - grp["n_per_recon"]).abs().mean()),
            }
        )
    return pd.DataFrame(out_rows).sort_values("CUT").reset_index(drop=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas-zip", type=Path, required=True)
    parser.add_argument("--hogares-zip", type=Path, required=True)
    parser.add_argument("--viviendas-zip", type=Path, required=True)
    parser.add_argument("--base-zip", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--tau", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--comunas", nargs="+", default=DEFAULT_PILOT_COMUNAS)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    micro_paths = MicrodataPaths(
        personas_zip=args.personas_zip,
        hogares_zip=args.hogares_zip,
        viviendas_zip=args.viviendas_zip,
    )
    artifacts = build_pilot_artifacts(
        micro_paths=micro_paths,
        base_zip=args.base_zip,
        comuna_codes=args.comunas,
        target_vars=PROFILE_TARGET_VARS,
    )
    scaled_targets = allocate_group_counts_softmax(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        tau=args.tau,
    )
    assigned = assign_households_softmax_quota(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        tau=args.tau,
        seed=args.seed,
    )
    assigned_manzent = aggregate_assignment_to_manzent(assigned)
    merged_eval, metrics = evaluate_assignment(assigned_manzent, artifacts.manzent_targets)
    metrics_by_cut = summarize_eval_by_cut(merged_eval)
    fit_by_cut = softmax_margin_fit_by_cut(assigned, scaled_targets)

    artifacts.household_base.to_parquet(out_dir / "pilot_household_base.parquet", index=False)
    artifacts.manzent_targets.to_parquet(out_dir / "pilot_manzent_targets.parquet", index=False)
    scaled_targets.to_parquet(out_dir / "pilot_softmax_targets_scaled.parquet", index=False)
    assigned.to_parquet(out_dir / "pilot_assignment_softmax.parquet", index=False)
    assigned_manzent.to_parquet(out_dir / "pilot_assignment_softmax_by_manzent.parquet", index=False)
    merged_eval.to_parquet(out_dir / "pilot_assignment_softmax_eval.parquet", index=False)
    metrics_by_cut.to_parquet(out_dir / "pilot_assignment_softmax_metrics_by_cut.parquet", index=False)
    fit_by_cut.to_parquet(out_dir / "pilot_assignment_softmax_fit_by_cut.parquet", index=False)
    (out_dir / "pilot_assignment_softmax_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    print(metrics_by_cut.to_string(index=False))
    print(fit_by_cut.to_string(index=False))


if __name__ == "__main__":
    main()
