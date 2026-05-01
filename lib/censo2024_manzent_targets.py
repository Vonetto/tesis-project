"""Prepare a manzana-entidad target table for communal-microdata spatialization."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import pandas as pd

KEY_COLS = [
    "COD_REGION",
    "REGION",
    "PROVINCIA",
    "CUT",
    "COMUNA",
    "AREA_C",
    "MANZENT",
    "COD_DISTRITO",
    "COD_LOCALIDAD",
    "COD_ZONA",
    "COD_ENTIDAD",
    "COD_MANZANA",
]

AGE_18_PLUS_BUCKETS = [
    "n_edad_18_24",
    "n_edad_25_44",
    "n_edad_45_59",
    "n_edad_60_mas",
]

DEFAULT_TARGET_VARS = [
    "n_per",
    "n_hog",
    *AGE_18_PLUS_BUCKETS,
    "n_discapacidad",
    "n_analfabet",
    "n_internet",
    "n_serv_compu",
    "n_viv_hacinadas",
    "prom_escolaridad18",
    "n_ocupado",
    "n_desocupado",
    "n_fuera_fuerza_trabajo",
    "n_cise_rec_independientes",
    "n_cise_rec_dependientes",
    "n_cise_rec_trabajador_no_remunerado",
    "n_cine_nunca_curso_primera_infancia",
    "n_cine_primaria",
    "n_cine_secundaria",
    "n_cine_terciaria_maestria_doctorado",
    "n_cine_especial_diferencial",
]


def _read_base_csv(
    base_zip: Path,
    base_csv_name: str,
    usecols: Sequence[str],
) -> pd.DataFrame:
    zip_url = f"zip://{Path(base_zip)}!{base_csv_name}"
    try:
        df = pd.read_csv(
            zip_url,
            sep=";",
            usecols=lambda c: c in set(usecols),
            dtype="string",
            encoding="utf-8-sig",
            low_memory=False,
        )
    except Exception:
        import zipfile

        with zipfile.ZipFile(base_zip) as zf:
            with zf.open(base_csv_name) as fp:
                df = pd.read_csv(
                    fp,
                    sep=";",
                    usecols=lambda c: c in set(usecols),
                    dtype="string",
                    encoding="utf-8-sig",
                    low_memory=False,
                )
    return df


def _expand_target_vars(variables: Sequence[str]) -> list[str]:
    expanded = list(dict.fromkeys(variables))
    if "prom_escolaridad18" in expanded:
        expanded = list(dict.fromkeys(expanded + AGE_18_PLUS_BUCKETS))
    return expanded


def build_manzent_target_table(
    base_zip: Path,
    base_csv_name: str = "Base_manzana_entidad_CPV24.csv",
    variables: Sequence[str] | None = None,
) -> pd.DataFrame:
    target_vars = _expand_target_vars(variables or DEFAULT_TARGET_VARS)
    df = _read_base_csv(base_zip=base_zip, base_csv_name=base_csv_name, usecols=KEY_COLS + target_vars)

    for col in KEY_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string")

    for col in target_vars:
        if col in df.columns:
            normalized = df[col].astype("string").str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(normalized, errors="coerce")

    if set(AGE_18_PLUS_BUCKETS).issubset(df.columns):
        df["n_18_mas"] = df[AGE_18_PLUS_BUCKETS].sum(axis=1, min_count=len(AGE_18_PLUS_BUCKETS))

    return df


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-zip", type=Path, required=True)
    parser.add_argument("--out-parquet", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    df = build_manzent_target_table(base_zip=args.base_zip)
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.out_parquet, index=False)
    print(f"Wrote manzent target table: {args.out_parquet} ({len(df):,} rows)")


if __name__ == "__main__":
    main()
