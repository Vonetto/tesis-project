"""Simple profile-based assignment for communal microdata -> manzana-entidad.

This is the first article-inspired method after the random quota baseline.
It keeps the exact scaled household quotas by manzana within each commune,
but replaces random placement with a monotone profile matching:

- households get a profile score from ICT availability, overcrowding and size
- manzanas get a target score from observed fine-scale ICT/housing aggregates
- households are assigned to manzana slots sorted by score within each commune

The method is intentionally simple and auditable. It is not yet simulated
annealing; it is an initial profile-aware assignment that should beat the
random baseline within commune before more complex optimization is justified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from lib.censo2024_spatialize_baseline import (
    DEFAULT_PILOT_COMUNAS,
    aggregate_assignment_to_manzent,
    build_pilot_artifacts,
    evaluate_assignment,
    scale_integer_quotas,
)
from lib.censo2024_microdata_base import MicrodataPaths

PROFILE_TARGET_VARS = [
    "n_per",
    "n_hog",
    "n_internet",
    "n_serv_compu",
    "n_viv_hacinadas",
    "prom_escolaridad18",
    "n_discapacidad",
    "n_cine_terciaria_maestria_doctorado",
]

PROFILE_WEIGHTS = {
    "compu": 0.40,
    "internet": 0.30,
    "not_hacinado": 0.20,
    "small_household": 0.10,
}


def _rank_pct_within_group(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    *,
    higher_is_better: bool,
) -> pd.Series:
    def _rank(s: pd.Series) -> pd.Series:
        numeric = pd.to_numeric(s, errors="coerce")
        return numeric.rank(method="average", pct=True, ascending=higher_is_better)

    return df.groupby(group_col, dropna=False)[value_col].transform(_rank)


def add_household_profile_features(household_base: pd.DataFrame) -> pd.DataFrame:
    df = household_base.copy()
    df["CUT"] = df["comuna"].astype("string")

    df["has_compu"] = (df["p15b_serv_compu"] == 1).astype(float)
    df["has_internet_any"] = (
        (df["p15d_serv_internet_fija"] == 1)
        | (df["p15e_serv_internet_movil"] == 1)
        | (df["p15f_serv_internet_satelital"] == 1)
    ).astype(float)
    # Match the aggregated "viviendas hacinadas" concept with a transparent threshold.
    df["is_hacinado"] = (pd.to_numeric(df["indice_hacinamiento"], errors="coerce") > 2.5).astype(float)
    df["n_personas_hogar_num"] = pd.to_numeric(df["n_personas_hogar"], errors="coerce")

    df["compu_rank"] = _rank_pct_within_group(df, "CUT", "has_compu", higher_is_better=True)
    df["internet_rank"] = _rank_pct_within_group(df, "CUT", "has_internet_any", higher_is_better=True)
    df["not_hacinado_rank"] = _rank_pct_within_group(df, "CUT", "is_hacinado", higher_is_better=False)
    df["small_household_rank"] = _rank_pct_within_group(df, "CUT", "n_personas_hogar_num", higher_is_better=False)

    df["household_profile_score"] = (
        PROFILE_WEIGHTS["compu"] * df["compu_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["internet"] * df["internet_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["not_hacinado"] * df["not_hacinado_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["small_household"] * df["small_household_rank"].fillna(0.5)
    )
    return df


def add_manzent_profile_features(manzent_targets: pd.DataFrame) -> pd.DataFrame:
    df = manzent_targets.copy()
    df["share_internet"] = df["n_internet"] / df["n_hog"].replace({0: pd.NA})
    df["share_compu"] = df["n_serv_compu"] / df["n_hog"].replace({0: pd.NA})
    df["share_hacin"] = df["n_viv_hacinadas"] / df["n_hog"].replace({0: pd.NA})
    df["persons_per_hog"] = df["n_per"] / df["n_hog"].replace({0: pd.NA})

    df["compu_rank"] = _rank_pct_within_group(df, "CUT", "share_compu", higher_is_better=True)
    df["internet_rank"] = _rank_pct_within_group(df, "CUT", "share_internet", higher_is_better=True)
    df["not_hacinado_rank"] = _rank_pct_within_group(df, "CUT", "share_hacin", higher_is_better=False)
    df["small_household_rank"] = _rank_pct_within_group(df, "CUT", "persons_per_hog", higher_is_better=False)

    df["manzent_profile_score"] = (
        PROFILE_WEIGHTS["compu"] * df["compu_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["internet"] * df["internet_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["not_hacinado"] * df["not_hacinado_rank"].fillna(0.5)
        + PROFILE_WEIGHTS["small_household"] * df["small_household_rank"].fillna(0.5)
    )
    return df


def assign_households_profile_quota(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    hh = add_household_profile_features(household_base)
    targets = add_manzent_profile_features(manzent_targets)
    rng = np.random.default_rng(seed)

    assignments: list[pd.DataFrame] = []
    for cut, hh_cut in hh.groupby("CUT", sort=True):
        targets_cut = targets.loc[targets["CUT"] == cut].copy()
        targets_cut = targets_cut.loc[pd.to_numeric(targets_cut["n_hog"], errors="coerce").fillna(0) > 0].copy()
        targets_cut["quota_hogares_scaled"] = scale_integer_quotas(targets_cut["n_hog"], target_total=len(hh_cut)).values

        expanded = targets_cut.loc[targets_cut.index.repeat(targets_cut["quota_hogares_scaled"])].copy()
        expanded = expanded.reset_index(drop=True)
        expanded["_slot_tie"] = rng.random(len(expanded))
        expanded = expanded.sort_values(
            by=["manzent_profile_score", "_slot_tie", "MANZENT"],
            ascending=[False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)

        hh_ordered = hh_cut.reset_index(drop=True).copy()
        hh_ordered["_hh_tie"] = rng.random(len(hh_ordered))
        hh_ordered = hh_ordered.sort_values(
            by=["household_profile_score", "_hh_tie", "hogar_uid"],
            ascending=[False, False, True],
            kind="mergesort",
        ).reset_index(drop=True)

        if len(expanded) != len(hh_ordered):
            raise ValueError(
                f"Expanded profile slots do not match household total for CUT={cut}: "
                f"{len(expanded)} vs {len(hh_ordered)}"
            )

        hh_ordered["MANZENT"] = expanded["MANZENT"].astype("string")
        hh_ordered["CUT_target"] = expanded["CUT"].astype("string")
        hh_ordered["assigned_manzent_profile_score"] = expanded["manzent_profile_score"].astype(float)
        assignments.append(hh_ordered)

    return pd.concat(assignments, ignore_index=True)


def summarize_eval_by_cut(merged_eval: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cut, grp in merged_eval.groupby("CUT", dropna=False):
        row = {"CUT": str(cut), "n_manzent": int(len(grp))}
        for left, right, prefix in [
            ("prom_escolaridad18", "prom_escolaridad18_recon", "prom_escolaridad18"),
            ("share_cine_terciaria_target", "share_cine_terciaria_recon", "share_cine_terciaria"),
        ]:
            valid = grp[[left, right]].dropna()
            row[f"{prefix}_n"] = int(len(valid))
            if len(valid) == 0:
                row[f"{prefix}_mae"] = np.nan
                row[f"{prefix}_rmse"] = np.nan
                row[f"{prefix}_corr"] = np.nan
                continue
            diff = valid[right] - valid[left]
            row[f"{prefix}_mae"] = float(diff.abs().mean())
            row[f"{prefix}_rmse"] = float((diff.pow(2).mean()) ** 0.5)
            row[f"{prefix}_corr"] = float(valid[left].corr(valid[right])) if len(valid) >= 2 else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("CUT").reset_index(drop=True)


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
    assigned = assign_households_profile_quota(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        seed=args.seed,
    )
    assigned_manzent = aggregate_assignment_to_manzent(assigned)
    merged_eval, metrics = evaluate_assignment(assigned_manzent, artifacts.manzent_targets)
    metrics_by_cut = summarize_eval_by_cut(merged_eval)

    artifacts.household_base.to_parquet(out_dir / "pilot_household_base.parquet", index=False)
    artifacts.manzent_targets.to_parquet(out_dir / "pilot_manzent_targets.parquet", index=False)
    assigned.to_parquet(out_dir / "pilot_assignment_profile.parquet", index=False)
    assigned_manzent.to_parquet(out_dir / "pilot_assignment_profile_by_manzent.parquet", index=False)
    merged_eval.to_parquet(out_dir / "pilot_assignment_profile_eval.parquet", index=False)
    metrics_by_cut.to_parquet(out_dir / "pilot_assignment_profile_metrics_by_cut.parquet", index=False)
    (out_dir / "pilot_assignment_profile_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    print(metrics_by_cut.to_string(index=False))


if __name__ == "__main__":
    main()
