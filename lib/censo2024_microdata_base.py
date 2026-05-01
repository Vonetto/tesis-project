"""Build a cleaned household-level base from communal Censo 2024 microdata.

Stage 1 of the synthetic-population workflow:
- read personas / hogares / viviendas from the official zipped CSVs
- clean common missing/suppressed codes
- aggregate person-level features to the household key
- merge household and dwelling attributes into a reusable household base
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

HOUSEHOLD_KEY = ["id_vivienda", "id_hogar"]
DWELLING_KEY = ["id_vivienda"]

COMMON_HOUSEHOLD_COLS = [
    "region",
    "provincia",
    "comuna",
    "comuna_bajo_umbral",
    "area",
    "tipo_operativo",
]

PERSONAS_USECOLS = HOUSEHOLD_KEY + [
    "id_persona",
    *COMMON_HOUSEHOLD_COLS,
    "sexo",
    "edad",
    "edad_quinquenal",
    "discapacidad",
    "p37_alfabet",
    "escolaridad",
    "cine11",
    "sit_fuerza_trabajo",
    "p40_cise_rec",
]

HOGARES_USECOLS = HOUSEHOLD_KEY + COMMON_HOUSEHOLD_COLS + [
    "p12_tenencia_viv",
    "p13_comb_cocina",
    "p14_comb_calefaccion",
    "p15a_serv_tel_movil",
    "p15b_serv_compu",
    "p15c_serv_tablet",
    "p15d_serv_internet_fija",
    "p15e_serv_internet_movil",
    "p15f_serv_internet_satelital",
    "tipologia_hogar",
]

VIVIENDAS_USECOLS = DWELLING_KEY + COMMON_HOUSEHOLD_COLS + [
    "cant_hog",
    "cant_per",
    "p2_tipo_vivienda",
    "p3a_estado_ocupacion",
    "p3b_estado_ocupacion",
    "p4a_mat_paredes",
    "p4b_mat_techo",
    "p4c_mat_piso",
    "p5_num_dormitorios",
    "p6_fuente_agua",
    "p7_distrib_agua",
    "p8_serv_hig",
    "p9_fuente_elect",
    "p10_basura",
    "p11a_num_personas",
    "p11b_comparte_gasto",
    "p11c_num_hogar",
    "indice_hacinamiento",
]

STRING_MISSING_CODES = {"", "NA", "-99", "-66"}
NUMERIC_INT_COLS = {
    "region",
    "provincia",
    "comuna",
    "comuna_bajo_umbral",
    "area",
    "tipo_operativo",
    "sexo",
    "edad",
    "edad_quinquenal",
    "discapacidad",
    "p37_alfabet",
    "escolaridad",
    "cine11",
    "sit_fuerza_trabajo",
    "p40_cise_rec",
    "p12_tenencia_viv",
    "p13_comb_cocina",
    "p14_comb_calefaccion",
    "p15a_serv_tel_movil",
    "p15b_serv_compu",
    "p15c_serv_tablet",
    "p15d_serv_internet_fija",
    "p15e_serv_internet_movil",
    "p15f_serv_internet_satelital",
    "tipologia_hogar",
    "cant_hog",
    "cant_per",
    "p2_tipo_vivienda",
    "p3a_estado_ocupacion",
    "p3b_estado_ocupacion",
    "p4a_mat_paredes",
    "p4b_mat_techo",
    "p4c_mat_piso",
    "p5_num_dormitorios",
    "p6_fuente_agua",
    "p7_distrib_agua",
    "p8_serv_hig",
    "p9_fuente_elect",
    "p10_basura",
    "p11a_num_personas",
    "p11b_comparte_gasto",
    "p11c_num_hogar",
}
NUMERIC_FLOAT_COLS = {"indice_hacinamiento"}

HOUSEHOLD_PERSON_COUNT_COLS = [
    "n_personas_hogar",
    "n_personas_0_17",
    "n_edad_18_24",
    "n_edad_25_44",
    "n_edad_45_59",
    "n_edad_60_mas",
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
    "n_cine_nunca_curso_primera_infancia",
    "n_cine_primaria",
    "n_cine_secundaria",
    "n_cine_terciaria_maestria_doctorado",
    "n_cine_especial_diferencial",
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
class MicrodataPaths:
    personas_zip: Path
    hogares_zip: Path
    viviendas_zip: Path
    personas_csv_name: str = "personas_censo2024.csv"
    hogares_csv_name: str = "hogares_censo2024.csv"
    viviendas_csv_name: str = "viviendas_censo2024.csv"


def read_censo_zip_csv(
    zip_path: Path,
    csv_name: str,
    usecols: Sequence[str] | None = None,
) -> pd.DataFrame:
    zip_path = Path(zip_path)
    zip_url = f"zip://{zip_path}!{csv_name}"
    try:
        df = pd.read_csv(
            zip_url,
            sep=";",
            usecols=usecols,
            dtype="string",
            encoding="utf-8-sig",
            keep_default_na=False,
            low_memory=False,
        )
    except Exception:
        import zipfile

        with zipfile.ZipFile(zip_path) as zf:
            with zf.open(csv_name) as fp:
                df = pd.read_csv(
                    fp,
                    sep=";",
                    usecols=usecols,
                    dtype="string",
                    encoding="utf-8-sig",
                    keep_default_na=False,
                    low_memory=False,
                )
    return clean_censo_microdata(df)


def clean_censo_microdata(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_string_dtype(out[col]) or out[col].dtype == object:
            out[col] = out[col].astype("string").str.strip()
            if col not in HOUSEHOLD_KEY + DWELLING_KEY + ["id_persona"]:
                out[col] = out[col].replace(sorted(STRING_MISSING_CODES), pd.NA)

    int_cols = [c for c in out.columns if c in NUMERIC_INT_COLS]
    float_cols = [c for c in out.columns if c in NUMERIC_FLOAT_COLS]

    for col in int_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    for col in float_cols:
        normalized = out[col].astype("string").str.replace(",", ".", regex=False)
        out[col] = pd.to_numeric(normalized, errors="coerce")

    return out


def prepare_personas_microdata(paths: MicrodataPaths) -> pd.DataFrame:
    return read_censo_zip_csv(paths.personas_zip, paths.personas_csv_name, PERSONAS_USECOLS)


def prepare_hogares_microdata(paths: MicrodataPaths) -> pd.DataFrame:
    return read_censo_zip_csv(paths.hogares_zip, paths.hogares_csv_name, HOGARES_USECOLS)


def prepare_viviendas_microdata(paths: MicrodataPaths) -> pd.DataFrame:
    return read_censo_zip_csv(paths.viviendas_zip, paths.viviendas_csv_name, VIVIENDAS_USECOLS)


def _ensure_unique_keys(df: pd.DataFrame, cols: Sequence[str], name: str) -> None:
    if df.duplicated(list(cols)).any():
        raise ValueError(f"{name} contains duplicated keys for {list(cols)}")


def build_person_household_aggregates(personas: pd.DataFrame) -> pd.DataFrame:
    df = personas.copy()

    age = pd.to_numeric(df["edad"], errors="coerce")
    escolaridad = pd.to_numeric(df["escolaridad"], errors="coerce")
    cine = pd.to_numeric(df["cine11"], errors="coerce")

    df["n_personas_hogar"] = 1
    df["n_personas_0_17"] = ((age >= 0) & (age <= 17)).astype("Int64")
    df["n_edad_18_24"] = ((age >= 18) & (age <= 24)).astype("Int64")
    df["n_edad_25_44"] = ((age >= 25) & (age <= 44)).astype("Int64")
    df["n_edad_45_59"] = ((age >= 45) & (age <= 59)).astype("Int64")
    df["n_edad_60_mas"] = (age >= 60).astype("Int64")
    df["n_5_mas"] = (age >= 5).astype("Int64")
    df["n_15_mas"] = (age >= 15).astype("Int64")
    df["n_18_mas"] = (age >= 18).astype("Int64")

    df["n_discapacidad_5mas"] = (((age >= 5) & (df["discapacidad"] == 1))).astype("Int64")
    df["n_analfabet_15mas"] = (((age >= 15) & (df["p37_alfabet"] == 2))).astype("Int64")
    df["n_ocupado_15mas"] = (((age >= 15) & (df["sit_fuerza_trabajo"] == 1))).astype("Int64")
    df["n_desocupado_15mas"] = (((age >= 15) & (df["sit_fuerza_trabajo"] == 2))).astype("Int64")
    df["n_fuera_fuerza_trabajo_15mas"] = (((age >= 15) & (df["sit_fuerza_trabajo"] == 3))).astype("Int64")

    df["n_independiente"] = (df["p40_cise_rec"] == 1).astype("Int64")
    df["n_dependiente"] = (df["p40_cise_rec"] == 2).astype("Int64")
    df["n_no_remunerado"] = (df["p40_cise_rec"] == 3).astype("Int64")

    df["n_cine_nunca_curso_primera_infancia"] = cine.isin([1, 2]).astype("Int64")
    df["n_cine_primaria"] = cine.isin([3, 4, 5]).astype("Int64")
    df["n_cine_secundaria"] = cine.isin([6, 7]).astype("Int64")
    df["n_cine_terciaria_maestria_doctorado"] = cine.isin([8, 9, 10, 11]).astype("Int64")
    df["n_cine_especial_diferencial"] = (cine == 12).astype("Int64")

    # Adult educational composition is a better proxy of socio-economic status
    # than all-age CINE counts when we later derive model features.
    df["n_cine18_nunca_curso_primera_infancia"] = (((age >= 18) & cine.isin([1, 2]))).astype("Int64")
    df["n_cine18_primaria"] = (((age >= 18) & cine.isin([3, 4, 5]))).astype("Int64")
    df["n_cine18_secundaria"] = (((age >= 18) & cine.isin([6, 7]))).astype("Int64")
    df["n_cine18_terciaria_corta"] = (((age >= 18) & (cine == 8))).astype("Int64")
    df["n_cine18_universitaria"] = (((age >= 18) & (cine == 9))).astype("Int64")
    df["n_cine18_universitaria_o_mas"] = (((age >= 18) & cine.isin([9, 10, 11]))).astype("Int64")
    df["n_cine18_postgrado"] = (((age >= 18) & cine.isin([10, 11]))).astype("Int64")
    df["n_cine18_terciaria_maestria_doctorado"] = (((age >= 18) & cine.isin([8, 9, 10, 11]))).astype("Int64")
    df["n_cine18_especial_diferencial"] = (((age >= 18) & (cine == 12))).astype("Int64")

    df["escolaridad_18mas_num"] = escolaridad.where(age >= 18)

    grouped = (
        df.groupby(HOUSEHOLD_KEY, dropna=False)
        .agg(
            {
                **{col: "sum" for col in HOUSEHOLD_PERSON_COUNT_COLS},
                "escolaridad_18mas_num": "mean",
            }
        )
        .reset_index()
    )
    grouped = grouped.rename(columns={"escolaridad_18mas_num": "prom_escolaridad18_micro"})

    return grouped


def build_household_microdata_base(
    personas: pd.DataFrame,
    hogares: pd.DataFrame,
    viviendas: pd.DataFrame,
) -> pd.DataFrame:
    _ensure_unique_keys(hogares, HOUSEHOLD_KEY, "hogares")
    _ensure_unique_keys(viviendas, DWELLING_KEY, "viviendas")

    person_aggs = build_person_household_aggregates(personas)
    _ensure_unique_keys(person_aggs, HOUSEHOLD_KEY, "person_aggs")

    overlapping_vivienda_cols = [
        c for c in viviendas.columns if c in hogares.columns and c not in DWELLING_KEY
    ]
    if overlapping_vivienda_cols:
        viviendas = viviendas.drop(columns=overlapping_vivienda_cols)

    base = hogares.merge(person_aggs, on=HOUSEHOLD_KEY, how="left", validate="one_to_one")
    base = base.merge(viviendas, on=DWELLING_KEY, how="left", validate="many_to_one")

    for col in HOUSEHOLD_PERSON_COUNT_COLS:
        if col in base.columns:
            base[col] = base[col].fillna(0).astype("Int64")

    base["hogar_uid"] = base["id_vivienda"].astype("string") + "-" + base["id_hogar"].astype("string")
    return base


def build_household_microdata_base_from_paths(paths: MicrodataPaths) -> pd.DataFrame:
    personas = prepare_personas_microdata(paths)
    hogares = prepare_hogares_microdata(paths)
    viviendas = prepare_viviendas_microdata(paths)
    return build_household_microdata_base(personas=personas, hogares=hogares, viviendas=viviendas)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas-zip", type=Path, required=True)
    parser.add_argument("--hogares-zip", type=Path, required=True)
    parser.add_argument("--viviendas-zip", type=Path, required=True)
    parser.add_argument("--out-parquet", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    paths = MicrodataPaths(
        personas_zip=args.personas_zip,
        hogares_zip=args.hogares_zip,
        viviendas_zip=args.viviendas_zip,
    )
    out = build_household_microdata_base_from_paths(paths)
    args.out_parquet.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.out_parquet, index=False)
    print(f"Wrote household microdata base: {args.out_parquet} ({len(out):,} rows)")


if __name__ == "__main__":
    main()
