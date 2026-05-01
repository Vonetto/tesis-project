"""Discrete profile-quota assignment for communal microdata -> manzana-entidad.

This is the intermediate version after the continuous-score profile method.
It stays close to the professor article's logic:

- define household profiles on dimensions observed both in microdata and
  fine manzana targets
- allocate exact manzana profile quotas within each commune
- assign actual households to those slots while preserving exact commune totals

Profiles use only dimensions with fine-scale anchors:
- computer availability
- any internet availability
- overcrowding

Household size is used as a within-profile ordering criterion, not as a hard
profile dimension, because we only observe a manzana-level mean (`n_per/n_hog`)
and not a full household-size distribution.
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
from lib.censo2024_spatialize_profile import (
    PROFILE_TARGET_VARS,
    add_household_profile_features,
    add_manzent_profile_features,
    summarize_eval_by_cut,
)

PROFILE_CODES = [f"{compu}{internet}{hacin}" for compu in (0, 1) for internet in (0, 1) for hacin in (0, 1)]
PROFILE_EPSILON = 1e-3


def encode_household_profiles(household_base: pd.DataFrame) -> pd.DataFrame:
    df = add_household_profile_features(household_base)
    df["profile_code"] = (
        df["has_compu"].fillna(0).astype(int).astype(str)
        + df["has_internet_any"].fillna(0).astype(int).astype(str)
        + df["is_hacinado"].fillna(0).astype(int).astype(str)
    )
    df["n_personas_hogar_num"] = pd.to_numeric(df["n_personas_hogar"], errors="coerce").fillna(0.0)
    return df


def scale_integer_quotas_capped(
    weights: pd.Series,
    target_total: int,
    caps: pd.Series,
) -> pd.Series:
    weights = pd.to_numeric(weights, errors="coerce").fillna(0.0).clip(lower=0)
    caps = pd.to_numeric(caps, errors="coerce").fillna(0).clip(lower=0).astype(int)
    if target_total < 0:
        raise ValueError("target_total must be non-negative")
    if len(weights) != len(caps):
        raise ValueError("weights and caps must have same length")
    if target_total > int(caps.sum()):
        raise ValueError(f"target_total={target_total} exceeds total capacity={int(caps.sum())}")
    if len(weights) == 0:
        return pd.Series(dtype="Int64")
    if target_total == 0:
        return pd.Series(0, index=weights.index, dtype="Int64")

    effective_weights = weights.where(caps > 0, 0.0)
    if float(effective_weights.sum()) <= 0:
        effective_weights = caps.astype(float)

    ideal = effective_weights / float(effective_weights.sum()) * target_total
    alloc = pd.Series(
        np.minimum(np.floor(ideal).astype(int), caps.to_numpy(copy=True)),
        index=weights.index,
        dtype="Int64",
    )
    remainder = int(target_total - alloc.sum())
    if remainder == 0:
        return pd.Series(alloc, index=weights.index, dtype="Int64")

    frac = ideal - np.floor(ideal)
    eligible = caps.to_numpy(copy=True) - alloc
    order = pd.DataFrame(
        {
            "idx": np.arange(len(weights)),
            "frac": frac,
            "remaining_cap": eligible,
            "weight": effective_weights.to_numpy(copy=True),
        }
    )
    order = order.sort_values(
        by=["frac", "remaining_cap", "weight", "idx"],
        ascending=[False, False, False, True],
        kind="mergesort",
    )

    ordered_idx = list(order["idx"])
    while remainder > 0:
        progress = False
        for idx in ordered_idx:
            if remainder <= 0:
                break
            room = int(caps.iloc[idx] - alloc.iloc[idx])
            if room <= 0:
                continue
            alloc.iloc[idx] = int(alloc.iloc[idx]) + 1
            remainder -= 1
            progress = True
        if not progress:
            raise ValueError(f"Could not allocate full target_total; remainder={remainder}")

    if remainder != 0:
        raise ValueError(f"Could not allocate full target_total; remainder={remainder}")

    return alloc.astype("Int64")


def profile_weight_from_manzent(targets: pd.DataFrame, profile_code: str) -> pd.Series:
    compu, internet, hacin = (int(x) for x in profile_code)
    share_compu = pd.to_numeric(targets["share_compu"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    share_internet = pd.to_numeric(targets["share_internet"], errors="coerce").fillna(0.0).clip(0.0, 1.0)
    share_hacin = pd.to_numeric(targets["share_hacin"], errors="coerce").fillna(0.0).clip(0.0, 1.0)

    compu_term = share_compu if compu == 1 else (1.0 - share_compu)
    internet_term = share_internet if internet == 1 else (1.0 - share_internet)
    hacin_term = share_hacin if hacin == 1 else (1.0 - share_hacin)
    return (compu_term + PROFILE_EPSILON) * (internet_term + PROFILE_EPSILON) * (hacin_term + PROFILE_EPSILON)


def allocate_profile_counts_to_manzanas(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
) -> pd.DataFrame:
    hh = encode_household_profiles(household_base)
    targets = add_manzent_profile_features(manzent_targets)

    outputs: list[pd.DataFrame] = []
    for cut, hh_cut in hh.groupby("CUT", sort=True):
        targets_cut = targets.loc[targets["CUT"] == cut].copy()
        targets_cut = targets_cut.loc[pd.to_numeric(targets_cut["n_hog"], errors="coerce").fillna(0) > 0].copy()
        targets_cut["quota_hogares_scaled"] = scale_integer_quotas(targets_cut["n_hog"], target_total=len(hh_cut)).values
        targets_cut["remaining_capacity"] = targets_cut["quota_hogares_scaled"].astype(int)

        profile_counts = hh_cut["profile_code"].value_counts().reindex(PROFILE_CODES, fill_value=0)
        rare_to_common_profiles = list(profile_counts.sort_values(kind="mergesort").index)

        for profile_code in rare_to_common_profiles:
            count = int(profile_counts.loc[profile_code])
            col = f"profile_quota_{profile_code}"
            if count == 0:
                targets_cut[col] = 0
                continue
            weights = profile_weight_from_manzent(targets_cut, profile_code) * targets_cut["remaining_capacity"].astype(float)
            alloc = scale_integer_quotas_capped(weights=weights, target_total=count, caps=targets_cut["remaining_capacity"])
            targets_cut[col] = alloc.values
            targets_cut["remaining_capacity"] = targets_cut["remaining_capacity"] - targets_cut[col].astype(int)

        if int(targets_cut["remaining_capacity"].sum()) != 0:
            raise ValueError(f"Unfilled manzana capacity for CUT={cut}: {int(targets_cut['remaining_capacity'].sum())}")
        outputs.append(targets_cut)

    return pd.concat(outputs, ignore_index=True)


def assign_households_profile_discrete_quota(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    hh = encode_household_profiles(household_base)
    targets_alloc = allocate_profile_counts_to_manzanas(household_base=household_base, manzent_targets=manzent_targets)
    rng = np.random.default_rng(seed)

    assignments: list[pd.DataFrame] = []
    for cut, hh_cut in hh.groupby("CUT", sort=True):
        targets_cut = targets_alloc.loc[targets_alloc["CUT"] == cut].copy()
        for profile_code, hh_prof in hh_cut.groupby("profile_code", sort=True):
            quota_col = f"profile_quota_{profile_code}"
            slots = targets_cut.loc[targets_cut.index.repeat(targets_cut[quota_col].astype(int))].copy()
            slots = slots.reset_index(drop=True)
            if len(slots) != len(hh_prof):
                raise ValueError(
                    f"Profile slot mismatch for CUT={cut}, profile={profile_code}: "
                    f"{len(slots)} slots vs {len(hh_prof)} households"
                )

            slots["_slot_tie"] = rng.random(len(slots))
            slots = slots.sort_values(
                by=["persons_per_hog", "_slot_tie", "MANZENT"],
                ascending=[False, False, True],
                kind="mergesort",
            ).reset_index(drop=True)

            hh_prof = hh_prof.copy()
            hh_prof["_hh_tie"] = rng.random(len(hh_prof))
            hh_prof = hh_prof.sort_values(
                by=["n_personas_hogar_num", "_hh_tie", "hogar_uid"],
                ascending=[False, False, True],
                kind="mergesort",
            ).reset_index(drop=True)

            hh_prof["MANZENT"] = slots["MANZENT"].astype("string")
            hh_prof["CUT_target"] = slots["CUT"].astype("string")
            hh_prof["assigned_profile_code"] = profile_code
            hh_prof["assigned_manzent_persons_per_hog"] = slots["persons_per_hog"].astype(float)
            assignments.append(hh_prof)

    return pd.concat(assignments, ignore_index=True)


def profile_margin_fit_by_cut(assigned: pd.DataFrame, targets_alloc: pd.DataFrame) -> pd.DataFrame:
    out_rows = []
    assigned = assigned.copy()
    assigned["has_compu"] = assigned["has_compu"].fillna(0).astype(int)
    assigned["has_internet_any"] = assigned["has_internet_any"].fillna(0).astype(int)
    assigned["is_hacinado"] = assigned["is_hacinado"].fillna(0).astype(int)

    recon = (
        assigned.groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            n_hog_recon=("hogar_uid", "count"),
            n_compu_recon=("has_compu", "sum"),
            n_internet_recon=("has_internet_any", "sum"),
            n_hacin_recon=("is_hacinado", "sum"),
        )
        .reset_index()
        .rename(columns={"CUT_target": "CUT"})
    )
    merged = targets_alloc.merge(recon, on=["CUT", "MANZENT"], how="left")
    merged[["n_hog_recon", "n_compu_recon", "n_internet_recon", "n_hacin_recon"]] = merged[
        ["n_hog_recon", "n_compu_recon", "n_internet_recon", "n_hacin_recon"]
    ].fillna(0)

    for cut, grp in merged.groupby("CUT", dropna=False):
        out_rows.append(
            {
                "CUT": str(cut),
                "n_manzent": int(len(grp)),
                "quota_mae": float((grp["quota_hogares_scaled"] - grp["n_hog_recon"]).abs().mean()),
                "compu_mae": float((grp.filter(like="profile_quota_").mul(
                    [int(col.split("_")[-1][0]) for col in grp.filter(like="profile_quota_").columns], axis=1
                ).sum(axis=1) - grp["n_compu_recon"]).abs().mean()),
                "internet_mae": float((grp.filter(like="profile_quota_").mul(
                    [int(col.split("_")[-1][1]) for col in grp.filter(like="profile_quota_").columns], axis=1
                ).sum(axis=1) - grp["n_internet_recon"]).abs().mean()),
                "hacin_mae": float((grp.filter(like="profile_quota_").mul(
                    [int(col.split("_")[-1][2]) for col in grp.filter(like="profile_quota_").columns], axis=1
                ).sum(axis=1) - grp["n_hacin_recon"]).abs().mean()),
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
    targets_alloc = allocate_profile_counts_to_manzanas(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
    )
    assigned = assign_households_profile_discrete_quota(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        seed=args.seed,
    )
    assigned_manzent = aggregate_assignment_to_manzent(assigned)
    merged_eval, metrics = evaluate_assignment(assigned_manzent, artifacts.manzent_targets)
    metrics_by_cut = summarize_eval_by_cut(merged_eval)
    profile_fit_by_cut = profile_margin_fit_by_cut(assigned, targets_alloc)

    artifacts.household_base.to_parquet(out_dir / "pilot_household_base.parquet", index=False)
    artifacts.manzent_targets.to_parquet(out_dir / "pilot_manzent_targets.parquet", index=False)
    targets_alloc.to_parquet(out_dir / "pilot_profile_targets_alloc.parquet", index=False)
    assigned.to_parquet(out_dir / "pilot_assignment_profile_discrete.parquet", index=False)
    assigned_manzent.to_parquet(out_dir / "pilot_assignment_profile_discrete_by_manzent.parquet", index=False)
    merged_eval.to_parquet(out_dir / "pilot_assignment_profile_discrete_eval.parquet", index=False)
    metrics_by_cut.to_parquet(out_dir / "pilot_assignment_profile_discrete_metrics_by_cut.parquet", index=False)
    profile_fit_by_cut.to_parquet(out_dir / "pilot_assignment_profile_discrete_profile_fit_by_cut.parquet", index=False)
    (out_dir / "pilot_assignment_profile_discrete_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    print(metrics_by_cut.to_string(index=False))
    print(profile_fit_by_cut.to_string(index=False))


if __name__ == "__main__":
    main()
