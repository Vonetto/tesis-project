"""Swap-based refinement on top of the softmax initial assignment.

This module adds the next article-inspired stage after the initial assignment:
- define a global energy from manzana-level attribute residuals
- propose swaps between households from two manzanas in the same commune
- accept improving swaps, and optionally some worsening swaps via Metropolis

The implementation keeps household quotas by manzana exactly constant because
it only swaps assignments between already-placed households.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
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
)
from lib.censo2024_spatialize_profile import summarize_eval_by_cut
from lib.censo2024_spatialize_softmax import (
    PROFILE_TARGET_VARS,
    assign_households_softmax_quota,
    build_scaled_manzent_targets,
)

ATTR_COLS = ["attr_n_per", "attr_compu", "attr_internet", "attr_hacin"]
TARGET_COLS = ["obj_n_per_scaled", "obj_compu_scaled", "obj_internet_scaled", "obj_hacin_scaled"]
ENERGY_MODES = ("count", "share", "hybrid")

# Conservative energy variants to avoid wide parameter tuning.
SHARE_MODE_WEIGHTS = {
    "pph": 0.35,
    "compu": 0.20,
    "internet": 0.15,
    "hacin": 0.30,
}
HYBRID_MODE_WEIGHTS = {
    "n_per": 0.30,
    "compu": 0.25,
    "internet": 0.15,
    "hacin": 0.30,
}


@dataclass
class CommuneRefinementState:
    cut: str
    household_indices: np.ndarray
    current_manz_idx: np.ndarray
    attrs: np.ndarray
    current: np.ndarray
    target: np.ndarray
    denom: np.ndarray
    quota_hogares: np.ndarray
    manz_energy: np.ndarray
    members: list[list[int]]
    manzent_codes: np.ndarray


def prepare_assignment_attrs(assigned: pd.DataFrame) -> pd.DataFrame:
    df = assigned.copy()
    df["attr_n_per"] = pd.to_numeric(df["n_personas_hogar_num"], errors="coerce").fillna(0.0)
    df["attr_compu"] = pd.to_numeric(df["has_compu"], errors="coerce").fillna(0.0)
    df["attr_internet"] = pd.to_numeric(df["has_internet_any"], errors="coerce").fillna(0.0)
    df["attr_hacin"] = pd.to_numeric(df["is_hacinado"], errors="coerce").fillna(0.0)
    return df


def _validate_energy_mode(energy_mode: str) -> str:
    if energy_mode not in ENERGY_MODES:
        raise ValueError(f"Unknown energy_mode={energy_mode!r}. Expected one of {ENERGY_MODES}.")
    return energy_mode


def _shares_from_row(row: np.ndarray, quota_hogares: float) -> tuple[float, float, float, float]:
    quota = max(float(quota_hogares), 1.0)
    return (
        float(row[0]) / quota,
        float(row[1]) / quota,
        float(row[2]) / quota,
        float(row[3]) / quota,
    )


def manzana_energy(
    current_row: np.ndarray,
    target_row: np.ndarray,
    denom: np.ndarray,
    quota_hogares: float,
    energy_mode: str = "count",
) -> float:
    energy_mode = _validate_energy_mode(energy_mode)
    if energy_mode == "count":
        return float((np.abs(current_row - target_row) / denom).sum())

    current_pph, current_compu, current_internet, current_hacin = _shares_from_row(current_row, quota_hogares)
    target_pph, target_compu, target_internet, target_hacin = _shares_from_row(target_row, quota_hogares)

    if energy_mode == "share":
        return float(
            SHARE_MODE_WEIGHTS["pph"] * abs(current_pph - target_pph)
            + SHARE_MODE_WEIGHTS["compu"] * abs(current_compu - target_compu)
            + SHARE_MODE_WEIGHTS["internet"] * abs(current_internet - target_internet)
            + SHARE_MODE_WEIGHTS["hacin"] * abs(current_hacin - target_hacin)
        )

    return float(
        HYBRID_MODE_WEIGHTS["n_per"] * (abs(float(current_row[0]) - float(target_row[0])) / float(denom[0]))
        + HYBRID_MODE_WEIGHTS["compu"] * abs(current_compu - target_compu)
        + HYBRID_MODE_WEIGHTS["internet"] * abs(current_internet - target_internet)
        + HYBRID_MODE_WEIGHTS["hacin"] * abs(current_hacin - target_hacin)
    )


def total_energy(
    current: np.ndarray,
    target: np.ndarray,
    denom: np.ndarray,
    quota_hogares: np.ndarray,
    energy_mode: str = "count",
) -> float:
    energy_mode = _validate_energy_mode(energy_mode)
    return float(
        sum(
            manzana_energy(
                current_row=current[i],
                target_row=target[i],
                denom=denom,
                quota_hogares=float(quota_hogares[i]),
                energy_mode=energy_mode,
            )
            for i in range(current.shape[0])
        )
    )


def build_commune_state(
    assigned_cut: pd.DataFrame,
    scaled_targets_cut: pd.DataFrame,
    energy_mode: str = "count",
) -> CommuneRefinementState:
    energy_mode = _validate_energy_mode(energy_mode)
    assigned_cut = prepare_assignment_attrs(assigned_cut)
    scaled_targets_cut = scaled_targets_cut.copy().reset_index(drop=True)

    manzent_codes = scaled_targets_cut["MANZENT"].astype("string").to_numpy()
    manz_to_idx = {m: i for i, m in enumerate(manzent_codes)}
    current_manz_idx = assigned_cut["MANZENT"].astype("string").map(manz_to_idx).to_numpy(dtype=int)

    attrs = assigned_cut[ATTR_COLS].to_numpy(dtype=float)
    target = scaled_targets_cut[TARGET_COLS].to_numpy(dtype=float)
    denom = target.sum(axis=0)
    denom = np.where(denom <= 0, 1.0, denom)
    quota_hogares = pd.to_numeric(scaled_targets_cut["quota_hogares_scaled"], errors="coerce").fillna(0).to_numpy(dtype=float)
    quota_hogares = np.where(quota_hogares <= 0, 1.0, quota_hogares)

    current = np.zeros_like(target, dtype=float)
    for k in range(attrs.shape[1]):
        np.add.at(current[:, k], current_manz_idx, attrs[:, k])

    members = [list(np.where(current_manz_idx == i)[0]) for i in range(len(manzent_codes))]
    manz_energy = np.array(
        [
            manzana_energy(
                current_row=current[i],
                target_row=target[i],
                denom=denom,
                quota_hogares=float(quota_hogares[i]),
                energy_mode=energy_mode,
            )
            for i in range(len(manzent_codes))
        ],
        dtype=float,
    )

    return CommuneRefinementState(
        cut=str(assigned_cut["CUT_target"].iloc[0]),
        household_indices=assigned_cut.index.to_numpy(),
        current_manz_idx=current_manz_idx,
        attrs=attrs,
        current=current,
        target=target,
        denom=denom,
        quota_hogares=quota_hogares,
        manz_energy=manz_energy,
        members=members,
        manzent_codes=manzent_codes,
    )


def select_manzana_pair(state: CommuneRefinementState, rng: np.random.Generator) -> tuple[int, int] | None:
    nonempty = np.array([i for i, members in enumerate(state.members) if len(members) > 0], dtype=int)
    if len(nonempty) < 2:
        return None

    error_weights = state.manz_energy[nonempty] + 1e-12
    i = int(rng.choice(nonempty, p=error_weights / error_weights.sum()))

    others = nonempty[nonempty != i]
    inv_weights = 1.0 / (state.manz_energy[others] + 1e-9)
    j = int(rng.choice(others, p=inv_weights / inv_weights.sum()))
    return i, j


def best_swap_between_manzanas(
    state: CommuneRefinementState,
    manz_i: int,
    manz_j: int,
    rng: np.random.Generator,
    sample_size: int = 6,
    energy_mode: str = "count",
) -> tuple[int, int, float] | None:
    energy_mode = _validate_energy_mode(energy_mode)
    members_i = state.members[manz_i]
    members_j = state.members[manz_j]
    if len(members_i) == 0 or len(members_j) == 0:
        return None

    sample_i = rng.choice(members_i, size=min(sample_size, len(members_i)), replace=False)
    sample_j = rng.choice(members_j, size=min(sample_size, len(members_j)), replace=False)

    old_e = state.manz_energy[manz_i] + state.manz_energy[manz_j]
    best: tuple[int, int, float] | None = None

    for hi in sample_i:
        ai = state.attrs[hi]
        for hj in sample_j:
            aj = state.attrs[hj]
            if np.array_equal(ai, aj):
                continue
            new_i = state.current[manz_i] - ai + aj
            new_j = state.current[manz_j] - aj + ai
            new_e = (
                manzana_energy(
                    current_row=new_i,
                    target_row=state.target[manz_i],
                    denom=state.denom,
                    quota_hogares=float(state.quota_hogares[manz_i]),
                    energy_mode=energy_mode,
                )
                + manzana_energy(
                    current_row=new_j,
                    target_row=state.target[manz_j],
                    denom=state.denom,
                    quota_hogares=float(state.quota_hogares[manz_j]),
                    energy_mode=energy_mode,
                )
            )
            delta = float(new_e - old_e)
            if (best is None) or (delta < best[2]):
                best = (int(hi), int(hj), delta)
    return best


def apply_swap(state: CommuneRefinementState, hi: int, hj: int, energy_mode: str = "count") -> None:
    energy_mode = _validate_energy_mode(energy_mode)
    manz_i = int(state.current_manz_idx[hi])
    manz_j = int(state.current_manz_idx[hj])
    ai = state.attrs[hi].copy()
    aj = state.attrs[hj].copy()

    state.current[manz_i] = state.current[manz_i] - ai + aj
    state.current[manz_j] = state.current[manz_j] - aj + ai
    state.manz_energy[manz_i] = manzana_energy(
        current_row=state.current[manz_i],
        target_row=state.target[manz_i],
        denom=state.denom,
        quota_hogares=float(state.quota_hogares[manz_i]),
        energy_mode=energy_mode,
    )
    state.manz_energy[manz_j] = manzana_energy(
        current_row=state.current[manz_j],
        target_row=state.target[manz_j],
        denom=state.denom,
        quota_hogares=float(state.quota_hogares[manz_j]),
        energy_mode=energy_mode,
    )

    state.current_manz_idx[hi] = manz_j
    state.current_manz_idx[hj] = manz_i

    state.members[manz_i].remove(hi)
    state.members[manz_j].append(hi)
    state.members[manz_j].remove(hj)
    state.members[manz_i].append(hj)


def refine_commune_state(
    state: CommuneRefinementState,
    n_iter: int = 5000,
    seed: int = 42,
    init_temp: float = 0.001,
    alpha: float = 0.9995,
    sample_size: int = 6,
    energy_mode: str = "count",
) -> tuple[np.ndarray, dict]:
    energy_mode = _validate_energy_mode(energy_mode)
    rng = np.random.default_rng(seed)
    temperature = float(init_temp)
    current_total = total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode=energy_mode)
    best_total = current_total
    best_assignment = state.current_manz_idx.copy()

    accepted = 0
    improved = 0
    accepted_worse = 0

    for _ in range(n_iter):
        pair = select_manzana_pair(state, rng)
        if pair is None:
            break
        manz_i, manz_j = pair
        best_swap = best_swap_between_manzanas(
            state,
            manz_i,
            manz_j,
            rng=rng,
            sample_size=sample_size,
            energy_mode=energy_mode,
        )
        if best_swap is None:
            temperature *= alpha
            continue
        hi, hj, delta = best_swap

        accept = delta <= 0
        if (not accept) and temperature > 0:
            prob = math.exp(-delta / max(temperature, 1e-12))
            accept = rng.random() < prob

        if accept:
            apply_swap(state, hi, hj, energy_mode=energy_mode)
            current_total += delta
            accepted += 1
            if delta < 0:
                improved += 1
            else:
                accepted_worse += 1
            if current_total < best_total:
                best_total = current_total
                best_assignment = state.current_manz_idx.copy()

        temperature *= alpha

    stats = {
        "cut": state.cut,
        "energy_mode": energy_mode,
        "n_iter": int(n_iter),
        "accepted_swaps": int(accepted),
        "improving_swaps": int(improved),
        "accepted_worse_swaps": int(accepted_worse),
        "initial_energy": float(
            total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode=energy_mode)
            if accepted == 0
            else np.nan
        ),
        "best_energy": float(best_total),
    }
    return best_assignment, stats


def refine_assignment_with_annealing(
    assigned: pd.DataFrame,
    scaled_targets: pd.DataFrame,
    n_iter: int = 5000,
    seed: int = 42,
    init_temp: float = 0.001,
    alpha: float = 0.9995,
    sample_size: int = 6,
    energy_mode: str = "count",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    energy_mode = _validate_energy_mode(energy_mode)
    assigned = prepare_assignment_attrs(assigned)
    outputs: list[pd.DataFrame] = []
    stats_rows: list[dict] = []

    for cut, assigned_cut in assigned.groupby("CUT_target", sort=True):
        targets_cut = scaled_targets.loc[scaled_targets["CUT"] == str(cut)].copy()
        state = build_commune_state(assigned_cut, targets_cut, energy_mode=energy_mode)
        initial_energy = total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode=energy_mode)
        best_assignment, stats = refine_commune_state(
            state=state,
            n_iter=n_iter,
            seed=seed,
            init_temp=init_temp,
            alpha=alpha,
            sample_size=sample_size,
            energy_mode=energy_mode,
        )
        stats["initial_energy"] = float(initial_energy)
        stats_rows.append(stats)

        cut_out = assigned_cut.copy().reset_index(drop=True)
        cut_out["MANZENT"] = pd.Series(state.manzent_codes[best_assignment], dtype="string")
        outputs.append(cut_out)

    return pd.concat(outputs, ignore_index=True), pd.DataFrame(stats_rows).sort_values("cut").reset_index(drop=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas-zip", type=Path, required=True)
    parser.add_argument("--hogares-zip", type=Path, required=True)
    parser.add_argument("--viviendas-zip", type=Path, required=True)
    parser.add_argument("--base-zip", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--tau", type=float, default=0.03)
    parser.add_argument("--n-iter", type=int, default=5000)
    parser.add_argument("--init-temp", type=float, default=0.001)
    parser.add_argument("--alpha", type=float, default=0.9995)
    parser.add_argument("--sample-size", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--comunas", nargs="+", default=DEFAULT_PILOT_COMUNAS)
    parser.add_argument("--energy-mode", choices=ENERGY_MODES, default="count")
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
    initial_assigned = assign_households_softmax_quota(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        tau=args.tau,
        seed=args.seed,
    )
    scaled_targets = build_scaled_manzent_targets(artifacts.household_base, artifacts.manzent_targets)
    refined_assigned, anneal_stats = refine_assignment_with_annealing(
        assigned=initial_assigned,
        scaled_targets=scaled_targets,
        n_iter=args.n_iter,
        seed=args.seed,
        init_temp=args.init_temp,
        alpha=args.alpha,
        sample_size=args.sample_size,
        energy_mode=args.energy_mode,
    )

    refined_by_manzent = aggregate_assignment_to_manzent(refined_assigned)
    merged_eval, metrics = evaluate_assignment(refined_by_manzent, artifacts.manzent_targets)
    metrics_by_cut = summarize_eval_by_cut(merged_eval)

    artifacts.household_base.to_parquet(out_dir / "pilot_household_base.parquet", index=False)
    artifacts.manzent_targets.to_parquet(out_dir / "pilot_manzent_targets.parquet", index=False)
    scaled_targets.to_parquet(out_dir / "pilot_targets_scaled.parquet", index=False)
    initial_assigned.to_parquet(out_dir / "pilot_assignment_softmax_initial.parquet", index=False)
    refined_assigned.to_parquet(out_dir / "pilot_assignment_annealed.parquet", index=False)
    refined_by_manzent.to_parquet(out_dir / "pilot_assignment_annealed_by_manzent.parquet", index=False)
    merged_eval.to_parquet(out_dir / "pilot_assignment_annealed_eval.parquet", index=False)
    metrics_by_cut.to_parquet(out_dir / "pilot_assignment_annealed_metrics_by_cut.parquet", index=False)
    anneal_stats.to_parquet(out_dir / "pilot_assignment_annealed_stats.parquet", index=False)
    (out_dir / "pilot_assignment_annealed_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    print(metrics_by_cut.to_string(index=False))
    print(anneal_stats.to_string(index=False))


if __name__ == "__main__":
    main()
