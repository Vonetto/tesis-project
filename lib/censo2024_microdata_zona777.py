"""Operational pipeline: communal microdata -> softmax MANZENT -> ZONA777 features.

This module freezes the currently preferred spatialization path:
- build full or pilot household microdata base
- assign households to manzana-entidad with `softmax_tau003`
- aggregate compact socio-demographic proxies at MANZENT
- spatially aggregate those proxies to ZONA777 using the same geometry path as
  the existing Censo 2024 aggregated pipeline

Outputs are intentionally separate from the existing official Censo ZONA777
parquet so they can be audited as synthetic-population-derived features.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

from lib.censo2024_manzent_targets import build_manzent_target_table
from lib.censo2024_microdata_base import MicrodataPaths, build_household_microdata_base_from_paths
from lib.censo2024_spatialize_baseline import DEFAULT_PILOT_COMUNAS, build_pilot_artifacts
from lib.censo2024_spatialize_profile import PROFILE_TARGET_VARS
from lib.censo2024_spatialize_softmax import assign_households_softmax_quota
from lib.censo2024_zona777 import (
    _normalize_key,
    _overlay_area_weighted,
    _read_carto,
    _read_zonas777,
    _spatial_assign_zona777,
)

MANZENT_COUNT_COLS = [
    "n_hog",
    "n_per",
    "n_5_mas",
    "n_15_mas",
    "n_18_mas",
    "n_discapacidad_5mas",
    "n_analfabet_15mas",
    "n_ocupado_15mas",
    "n_desocupado_15mas",
    "n_fuera_fuerza_trabajo_15mas",
    "n_independiente",
    "n_dependiente",
    "n_no_remunerado",
    "n_cine18_nunca_curso_primera_infancia",
    "n_cine18_primaria",
    "n_cine18_secundaria",
    "n_cine18_terciaria_corta",
    "n_cine18_universitaria",
    "n_cine18_universitaria_o_mas",
    "n_cine18_postgrado",
    "n_cine18_terciaria_maestria_doctorado",
    "n_cine18_especial_diferencial",
]


@dataclass
class SpatializedMicrodataArtifacts:
    household_base: pd.DataFrame
    manzent_targets: pd.DataFrame
    household_assignment: pd.DataFrame
    manzent_features: pd.DataFrame
    zona777_features: pd.DataFrame


def build_microdata_manzent_features(assigned: pd.DataFrame) -> pd.DataFrame:
    df = assigned.copy()
    grouped = (
        df.groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            n_hog=("hogar_uid", "count"),
            n_per=("n_personas_hogar", "sum"),
            n_5_mas=("n_5_mas", "sum"),
            n_15_mas=("n_15_mas", "sum"),
            n_18_mas=("n_18_mas", "sum"),
            n_discapacidad_5mas=("n_discapacidad_5mas", "sum"),
            n_analfabet_15mas=("n_analfabet_15mas", "sum"),
            n_ocupado_15mas=("n_ocupado_15mas", "sum"),
            n_desocupado_15mas=("n_desocupado_15mas", "sum"),
            n_fuera_fuerza_trabajo_15mas=("n_fuera_fuerza_trabajo_15mas", "sum"),
            n_independiente=("n_independiente", "sum"),
            n_dependiente=("n_dependiente", "sum"),
            n_no_remunerado=("n_no_remunerado", "sum"),
            n_cine18_nunca_curso_primera_infancia=("n_cine18_nunca_curso_primera_infancia", "sum"),
            n_cine18_primaria=("n_cine18_primaria", "sum"),
            n_cine18_secundaria=("n_cine18_secundaria", "sum"),
            n_cine18_terciaria_corta=("n_cine18_terciaria_corta", "sum"),
            n_cine18_universitaria=("n_cine18_universitaria", "sum"),
            n_cine18_universitaria_o_mas=("n_cine18_universitaria_o_mas", "sum"),
            n_cine18_postgrado=("n_cine18_postgrado", "sum"),
            n_cine18_terciaria_maestria_doctorado=("n_cine18_terciaria_maestria_doctorado", "sum"),
            n_cine18_especial_diferencial=("n_cine18_especial_diferencial", "sum"),
        )
        .reset_index()
        .rename(columns={"CUT_target": "CUT"})
    )

    weighted = (
        df.assign(_weighted_escol=pd.to_numeric(df["prom_escolaridad18_micro"], errors="coerce") * pd.to_numeric(df["n_18_mas"], errors="coerce"))
        .groupby(["CUT_target", "MANZENT"], dropna=False)
        .agg(
            weighted_escol_sum=("_weighted_escol", "sum"),
        )
        .reset_index()
        .rename(columns={"CUT_target": "CUT"})
    )

    grouped = grouped.merge(weighted, on=["CUT", "MANZENT"], how="left", validate="one_to_one")
    grouped["prom_escolaridad18_micro"] = grouped["weighted_escol_sum"] / grouped["n_18_mas"].replace({0: pd.NA})
    grouped["n_cine18_total_obs"] = grouped[
        [
            "n_cine18_nunca_curso_primera_infancia",
            "n_cine18_primaria",
            "n_cine18_secundaria",
            "n_cine18_terciaria_maestria_doctorado",
            "n_cine18_especial_diferencial",
        ]
    ].sum(axis=1, min_count=1)

    grouped["share_discapacidad_5mas_micro"] = grouped["n_discapacidad_5mas"] / grouped["n_5_mas"].replace({0: pd.NA})
    grouped["share_analfabet_15mas_micro"] = grouped["n_analfabet_15mas"] / grouped["n_15_mas"].replace({0: pd.NA})
    grouped["share_ocupado_15mas_micro"] = grouped["n_ocupado_15mas"] / grouped["n_15_mas"].replace({0: pd.NA})
    grouped["share_fuera_fuerza_trabajo_15mas_micro"] = grouped["n_fuera_fuerza_trabajo_15mas"] / grouped["n_15_mas"].replace({0: pd.NA})
    grouped["share_dependiente_micro"] = grouped["n_dependiente"] / grouped["n_ocupado_15mas"].replace({0: pd.NA})
    grouped["share_independiente_micro"] = grouped["n_independiente"] / grouped["n_ocupado_15mas"].replace({0: pd.NA})
    grouped["share_cine18_primaria_micro"] = grouped["n_cine18_primaria"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_secundaria_micro"] = grouped["n_cine18_secundaria"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_terciaria_corta_micro"] = grouped["n_cine18_terciaria_corta"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_universitaria_micro"] = grouped["n_cine18_universitaria"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_universitaria_o_mas_micro"] = grouped["n_cine18_universitaria_o_mas"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_postgrado_micro"] = grouped["n_cine18_postgrado"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})
    grouped["share_cine18_terciaria_micro"] = grouped["n_cine18_terciaria_maestria_doctorado"] / grouped["n_cine18_total_obs"].replace({0: pd.NA})

    return grouped.sort_values(["CUT", "MANZENT"]).reset_index(drop=True)


def _apply_area_share_scaling(df_join: pd.DataFrame) -> pd.DataFrame:
    out = df_join.copy()
    scale_cols = set(MANZENT_COUNT_COLS) | {"n_cine18_total_obs"}
    for col in scale_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce") * pd.to_numeric(out["area_share"], errors="coerce")
    return out


def aggregate_microdata_to_zona777(
    manzent_features: pd.DataFrame,
    carto_parquet: Path,
    zonas777_shp: Path,
    area_weighted: bool = True,
    use_centroid: bool = False,
) -> pd.DataFrame:
    gdf_ent = _read_carto(carto_parquet)
    gdf_zonas = _read_zonas777(zonas777_shp)
    if "MANZENT" not in gdf_ent.columns:
        raise ValueError("Cartography parquet is missing MANZENT")
    gdf_ent["MANZENT"] = _normalize_key(gdf_ent["MANZENT"])

    df_feat = manzent_features.copy()
    df_feat["MANZENT"] = _normalize_key(df_feat["MANZENT"])
    gdf = gdf_ent.merge(df_feat, on="MANZENT", how="inner", validate="one_to_one")

    if area_weighted:
        gdf_inter = _overlay_area_weighted(gdf, gdf_zonas, "MANZENT")
        df_join = pd.DataFrame(gdf_inter.drop(columns="geometry")).merge(df_feat, on="MANZENT", how="left", validate="many_to_one")
        df_join = _apply_area_share_scaling(df_join)
    else:
        gdf_join = _spatial_assign_zona777(gdf, gdf_zonas, use_centroid=use_centroid)
        df_join = pd.DataFrame(gdf_join.drop(columns="geometry"))

    df_join = df_join[df_join["ZONA777"].notna()].copy()
    df_join["ZONA777"] = df_join["ZONA777"].astype(int)

    agg_dict = {col: "sum" for col in MANZENT_COUNT_COLS + ["n_cine18_total_obs"] if col in df_join.columns}
    grouped = df_join.groupby("ZONA777", dropna=True).agg(agg_dict)

    if {"prom_escolaridad18_micro", "n_18_mas"}.issubset(df_join.columns):
        num = (pd.to_numeric(df_join["prom_escolaridad18_micro"], errors="coerce") * pd.to_numeric(df_join["n_18_mas"], errors="coerce")).groupby(df_join["ZONA777"]).sum()
        den = pd.to_numeric(df_join["n_18_mas"], errors="coerce").groupby(df_join["ZONA777"]).sum()
        grouped["prom_escolaridad18_micro"] = num / den.where(den != 0)

    grouped["share_discapacidad_5mas_micro"] = grouped["n_discapacidad_5mas"] / grouped["n_5_mas"].where(grouped["n_5_mas"] != 0)
    grouped["share_analfabet_15mas_micro"] = grouped["n_analfabet_15mas"] / grouped["n_15_mas"].where(grouped["n_15_mas"] != 0)
    grouped["share_ocupado_15mas_micro"] = grouped["n_ocupado_15mas"] / grouped["n_15_mas"].where(grouped["n_15_mas"] != 0)
    grouped["share_fuera_fuerza_trabajo_15mas_micro"] = grouped["n_fuera_fuerza_trabajo_15mas"] / grouped["n_15_mas"].where(grouped["n_15_mas"] != 0)
    grouped["share_dependiente_micro"] = grouped["n_dependiente"] / grouped["n_ocupado_15mas"].where(grouped["n_ocupado_15mas"] != 0)
    grouped["share_independiente_micro"] = grouped["n_independiente"] / grouped["n_ocupado_15mas"].where(grouped["n_ocupado_15mas"] != 0)
    grouped["share_cine18_primaria_micro"] = grouped["n_cine18_primaria"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_secundaria_micro"] = grouped["n_cine18_secundaria"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_terciaria_corta_micro"] = grouped["n_cine18_terciaria_corta"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_universitaria_micro"] = grouped["n_cine18_universitaria"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_universitaria_o_mas_micro"] = grouped["n_cine18_universitaria_o_mas"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_postgrado_micro"] = grouped["n_cine18_postgrado"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)
    grouped["share_cine18_terciaria_micro"] = grouped["n_cine18_terciaria_maestria_doctorado"] / grouped["n_cine18_total_obs"].where(grouped["n_cine18_total_obs"] != 0)

    return grouped.reset_index().sort_values("ZONA777").reset_index(drop=True)


def build_spatialized_microdata_outputs(
    micro_paths: MicrodataPaths,
    base_zip: Path,
    carto_parquet: Path,
    zonas777_shp: Path,
    tau: float = 0.03,
    seed: int = 42,
    comuna_codes: Sequence[str] | None = None,
) -> SpatializedMicrodataArtifacts:
    if comuna_codes:
        artifacts = build_pilot_artifacts(
            micro_paths=micro_paths,
            base_zip=base_zip,
            comuna_codes=comuna_codes,
            target_vars=PROFILE_TARGET_VARS,
        )
        household_base = artifacts.household_base
        manzent_targets = artifacts.manzent_targets
    else:
        household_base = build_household_microdata_base_from_paths(micro_paths)
        manzent_targets = build_manzent_target_table(base_zip=base_zip, variables=PROFILE_TARGET_VARS)
        manzent_targets["CUT"] = manzent_targets["CUT"].astype("string")

    household_assignment = assign_households_softmax_quota(
        household_base=household_base,
        manzent_targets=manzent_targets,
        tau=tau,
        seed=seed,
    )
    manzent_features = build_microdata_manzent_features(household_assignment)
    zona777_features = aggregate_microdata_to_zona777(
        manzent_features=manzent_features,
        carto_parquet=carto_parquet,
        zonas777_shp=zonas777_shp,
        area_weighted=True,
        use_centroid=False,
    )
    return SpatializedMicrodataArtifacts(
        household_base=household_base,
        manzent_targets=manzent_targets,
        household_assignment=household_assignment,
        manzent_features=manzent_features,
        zona777_features=zona777_features,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas-zip", type=Path, required=True)
    parser.add_argument("--hogares-zip", type=Path, required=True)
    parser.add_argument("--viviendas-zip", type=Path, required=True)
    parser.add_argument("--base-zip", type=Path, required=True)
    parser.add_argument("--carto-parquet", type=Path, required=True)
    parser.add_argument("--zonas777-shp", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--tau", type=float, default=0.03)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--comunas", nargs="+", default=None)
    parser.add_argument("--write-household-assignment", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    artifacts = build_spatialized_microdata_outputs(
        micro_paths=MicrodataPaths(
            personas_zip=args.personas_zip,
            hogares_zip=args.hogares_zip,
            viviendas_zip=args.viviendas_zip,
        ),
        base_zip=args.base_zip,
        carto_parquet=args.carto_parquet,
        zonas777_shp=args.zonas777_shp,
        tau=args.tau,
        seed=args.seed,
        comuna_codes=args.comunas,
    )

    artifacts.manzent_features.to_parquet(out_dir / "censo2024_microdata_manzent_features.parquet", index=False)
    artifacts.zona777_features.to_parquet(out_dir / "censo2024_microdata_zona777_features.parquet", index=False)
    if args.write_household_assignment:
        artifacts.household_assignment.to_parquet(out_dir / "censo2024_microdata_household_assignment.parquet", index=False)

    summary = {
        "n_households": int(len(artifacts.household_base)),
        "n_assigned_households": int(len(artifacts.household_assignment)),
        "n_manzent_features": int(len(artifacts.manzent_features)),
        "n_zona777_features": int(len(artifacts.zona777_features)),
        "tau": float(args.tau),
        "seed": int(args.seed),
        "comunas": [str(c) for c in (args.comunas or [])],
    }
    (out_dir / "censo2024_microdata_zona777_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
