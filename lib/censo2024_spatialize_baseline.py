"""Simple auditable baseline for communal microdata -> manzana-entidad assignment.

Baseline strategy:
- restrict to a pilot set of communes
- scale observed manzana household capacities to the pilot microdata household total
- randomly assign households to manzanas within the same commune using exact quotas
- aggregate holdout variables and compare against observed manzana-entidad targets
"""
from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from lib.censo2024_manzent_targets import build_manzent_target_table
from lib.censo2024_microdata_base import (
    HOGARES_USECOLS,
    PERSONAS_USECOLS,
    VIVIENDAS_USECOLS,
    MicrodataPaths,
    build_household_microdata_base,
    clean_censo_microdata,
)

DEFAULT_PILOT_COMUNAS = ["13132", "13112", "13101"]  # Vitacura, La Pintana, Santiago


@dataclass
class PilotArtifacts:
    household_base: pd.DataFrame
    manzent_targets: pd.DataFrame


def read_filtered_zip_csv(
    zip_path: Path,
    csv_name: str,
    comuna_codes: Sequence[str],
    usecols: Sequence[str],
    chunksize: int = 200_000,
) -> pd.DataFrame:
    comuna_codes = {str(c) for c in comuna_codes}
    pieces: list[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(csv_name) as fp:
            for chunk in pd.read_csv(
                fp,
                sep=";",
                usecols=usecols,
                dtype="string",
                encoding="utf-8-sig",
                keep_default_na=False,
                chunksize=chunksize,
                low_memory=False,
            ):
                chunk["comuna"] = chunk["comuna"].astype("string").str.strip()
                filt = chunk[chunk["comuna"].isin(comuna_codes)]
                if not filt.empty:
                    pieces.append(filt.copy())
    if not pieces:
        return clean_censo_microdata(pd.DataFrame(columns=list(usecols)))
    return clean_censo_microdata(pd.concat(pieces, ignore_index=True))


def build_pilot_artifacts(
    micro_paths: MicrodataPaths,
    base_zip: Path,
    comuna_codes: Sequence[str] = DEFAULT_PILOT_COMUNAS,
    target_vars: Sequence[str] | None = None,
) -> PilotArtifacts:
    personas = read_filtered_zip_csv(
        micro_paths.personas_zip,
        micro_paths.personas_csv_name,
        comuna_codes=comuna_codes,
        usecols=PERSONAS_USECOLS,
    )
    hogares = read_filtered_zip_csv(
        micro_paths.hogares_zip,
        micro_paths.hogares_csv_name,
        comuna_codes=comuna_codes,
        usecols=HOGARES_USECOLS,
    )
    viviendas = read_filtered_zip_csv(
        micro_paths.viviendas_zip,
        micro_paths.viviendas_csv_name,
        comuna_codes=comuna_codes,
        usecols=VIVIENDAS_USECOLS,
    )
    household_base = build_household_microdata_base(personas=personas, hogares=hogares, viviendas=viviendas)

    manzent_targets = build_manzent_target_table(base_zip=base_zip, variables=target_vars)
    manzent_targets["CUT"] = manzent_targets["CUT"].astype("string")
    manzent_targets = manzent_targets[manzent_targets["CUT"].isin([str(c) for c in comuna_codes])].copy()

    return PilotArtifacts(household_base=household_base, manzent_targets=manzent_targets)


def scale_integer_quotas(weights: pd.Series, target_total: int) -> pd.Series:
    weights = pd.to_numeric(weights, errors="coerce").fillna(0.0)
    if target_total < 0:
        raise ValueError("target_total must be non-negative")
    if len(weights) == 0:
        return pd.Series(dtype="Int64")
    total_weight = float(weights.sum())
    if total_weight <= 0:
        base = pd.Series(0, index=weights.index, dtype="Int64")
        if target_total > 0:
            n = len(base)
            q, r = divmod(target_total, n)
            if q > 0:
                base[:] = q
            if r > 0:
                base.iloc[:r] = base.iloc[:r] + 1
        return base

    scaled = weights / total_weight * target_total
    floors = scaled.apply(int)
    remainder = int(target_total - floors.sum())
    if remainder > 0:
        order = (scaled - floors).sort_values(ascending=False).index[:remainder]
        floors.loc[order] = floors.loc[order] + 1
    return floors.astype("Int64")


def assign_households_random_quota(
    household_base: pd.DataFrame,
    manzent_targets: pd.DataFrame,
    seed: int = 42,
) -> pd.DataFrame:
    rng = pd.Series(range(len(household_base))).sample(frac=1, random_state=seed).index
    shuffled = household_base.loc[rng].reset_index(drop=True).copy()
    shuffled["CUT"] = shuffled["comuna"].astype("string")

    assignments: list[pd.DataFrame] = []
    for cut, hh_cut in shuffled.groupby("CUT", sort=True):
        targets_cut = manzent_targets.loc[manzent_targets["CUT"] == cut].copy()
        targets_cut = targets_cut.loc[pd.to_numeric(targets_cut["n_hog"], errors="coerce").fillna(0) > 0].copy()
        quotas = scale_integer_quotas(targets_cut["n_hog"], target_total=len(hh_cut))
        targets_cut["quota_hogares_scaled"] = quotas.values
        quota_total = int(targets_cut["quota_hogares_scaled"].sum())
        if quota_total != len(hh_cut):
            raise ValueError(f"Scaled quotas do not match household total for CUT={cut}: {quota_total} vs {len(hh_cut)}")
        expanded = targets_cut.loc[targets_cut.index.repeat(targets_cut["quota_hogares_scaled"])].copy()
        expanded = expanded.reset_index(drop=True)
        assign = hh_cut.reset_index(drop=True).copy()
        assign["MANZENT"] = expanded["MANZENT"].astype("string")
        assign["CUT_target"] = expanded["CUT"].astype("string")
        assignments.append(assign)

    out = pd.concat(assignments, ignore_index=True)
    return out


def aggregate_assignment_to_manzent(assigned: pd.DataFrame) -> pd.DataFrame:
    df = assigned.copy()
    grouped = (
        df.groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            n_hog_recon=("hogar_uid", "count"),
            n_per_recon=("n_personas_hogar", "sum"),
            n_18_mas_recon=("n_18_mas", "sum"),
            n_discapacidad_recon=("n_discapacidad_5mas", "sum"),
            n_analfabet_recon=("n_analfabet_15mas", "sum"),
            n_ocupado_recon=("n_ocupado_15mas", "sum"),
            n_desocupado_recon=("n_desocupado_15mas", "sum"),
            n_fuera_fuerza_recon=("n_fuera_fuerza_trabajo_15mas", "sum"),
            n_independiente_recon=("n_independiente", "sum"),
            n_dependiente_recon=("n_dependiente", "sum"),
            n_no_remunerado_recon=("n_no_remunerado", "sum"),
            n_cine_nunca_recon=("n_cine_nunca_curso_primera_infancia", "sum"),
            n_cine_primaria_recon=("n_cine_primaria", "sum"),
            n_cine_secundaria_recon=("n_cine_secundaria", "sum"),
            n_cine_terciaria_recon=("n_cine_terciaria_maestria_doctorado", "sum"),
            n_cine_especial_recon=("n_cine_especial_diferencial", "sum"),
            sum_escolaridad18=("prom_escolaridad18_micro", lambda s: 0.0),
        )
        .reset_index()
    )

    # Weighted mean for educational holdout.
    weighted = (
        df.assign(_weighted_escol=df["prom_escolaridad18_micro"] * df["n_18_mas"])
        .groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            weighted_escol_sum=("_weighted_escol", "sum"),
            n_18_mas_recon=("n_18_mas", "sum"),
        )
        .reset_index()
    )
    grouped = grouped.drop(columns=["n_18_mas_recon"]).merge(
        weighted,
        on=["CUT_target", "MANZENT"],
        how="left",
        validate="one_to_one",
    )
    grouped["prom_escolaridad18_recon"] = grouped["weighted_escol_sum"] / grouped["n_18_mas_recon"].replace({0: pd.NA})
    grouped["share_cine_terciaria_recon"] = grouped["n_cine_terciaria_recon"] / grouped["n_per_recon"].replace({0: pd.NA})
    return grouped


def evaluate_assignment(
    assigned_manzent: pd.DataFrame,
    manzent_targets: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    target = manzent_targets.copy()
    target["share_cine_terciaria_target"] = target["n_cine_terciaria_maestria_doctorado"] / target["n_per"].replace({0: pd.NA})

    merged = target.merge(
        assigned_manzent,
        left_on=["CUT", "MANZENT"],
        right_on=["CUT_target", "MANZENT"],
        how="left",
        validate="one_to_one",
    )

    metrics = {}
    for left, right, prefix in [
        ("prom_escolaridad18", "prom_escolaridad18_recon", "prom_escolaridad18"),
        ("share_cine_terciaria_target", "share_cine_terciaria_recon", "share_cine_terciaria"),
    ]:
        valid = merged[[left, right]].dropna()
        if len(valid) == 0:
            metrics[f"{prefix}_n"] = 0
            continue
        diff = valid[right] - valid[left]
        metrics[f"{prefix}_n"] = int(len(valid))
        metrics[f"{prefix}_mae"] = float(diff.abs().mean())
        metrics[f"{prefix}_rmse"] = float((diff.pow(2).mean()) ** 0.5)
        metrics[f"{prefix}_corr"] = (
            float(valid[left].corr(valid[right])) if len(valid) >= 2 else float("nan")
        )
    return merged, metrics


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
    paths = MicrodataPaths(
        personas_zip=args.personas_zip,
        hogares_zip=args.hogares_zip,
        viviendas_zip=args.viviendas_zip,
    )
    artifacts = build_pilot_artifacts(paths, base_zip=args.base_zip, comuna_codes=args.comunas)
    assigned = assign_households_random_quota(
        household_base=artifacts.household_base,
        manzent_targets=artifacts.manzent_targets,
        seed=args.seed,
    )
    agg = aggregate_assignment_to_manzent(assigned)
    merged, metrics = evaluate_assignment(agg, artifacts.manzent_targets)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    artifacts.household_base.to_parquet(args.out_dir / "pilot_household_base.parquet", index=False)
    artifacts.manzent_targets.to_parquet(args.out_dir / "pilot_manzent_targets.parquet", index=False)
    assigned.to_parquet(args.out_dir / "pilot_assignment_random_quota.parquet", index=False)
    agg.to_parquet(args.out_dir / "pilot_assignment_random_quota_agg.parquet", index=False)
    merged.to_parquet(args.out_dir / "pilot_assignment_random_quota_eval.parquet", index=False)
    (args.out_dir / "pilot_assignment_random_quota_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False)
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
