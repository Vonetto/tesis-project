from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.interannual_offer_context import assert_left_join_preserves_rows, ensure_unique_keys
from lib.od_buffers_nested_logit import (
    ALT_CHOICE_MAP,
    ALT_LEVELS,
    ALT_METRIC_SPECS,
    OD_KEY_COLS,
    OdContextConfig,
    add_time_dummies_v2,
    add_tipo_pago,
    build_od_alt_specific_context_table,
    derive_metrics,
    load_caracterizacion,
    read_parquet_portable,
    resolve_caracterizacion_path,
)


MODEL_PARTITION = "pooled_2024_2025"
ARTIFACTS_DIR = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
PK_BRIDGE_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "pk_bridge"
HOME_CANDIDATES_PATH = PK_BRIDGE_DIR / "user_home_candidates_active.parquet"
FULL_TRIPS_CONTEXT_PATH = ARTIFACTS_DIR / f"trips_context_{MODEL_PARTITION}.parquet"
CENSO_AGG_FINAL_PATH = PROJECT_ROOT / "02_eda" / "tmp" / "censo2024_zona777" / "censo2024_zona777_agg_final.parquet"
CENSO_MODEL_READY_FULL_PATH = ARTIFACTS_DIR / "censo2024_microdata_zona777_model_ready.parquet"
OSM_MODEL_READY_FULL_PATH = ARTIFACTS_DIR / "osm_zona777_model_ready.parquet"
RAW_PARQUET_BY_PARTITION = {
    "2024-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W17.parquet",
    "2025-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W17.parquet",
}
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)

CENSO_COLS = [
    "share_cine18_universitaria_o_mas_micro_z",
    "share_discapacidad_z",
    "share_inmigrantes_z",
    "share_mujeres_z",
    "share_asistencia_parv_z",
    "prom_edad_z",
]
OSM_COLS = [
    "osm_leisure_playground_density_km2_z",
    "osm_amenity_school_density_km2_z",
    "osm_amenity_university_density_km2_z",
    "osm_transport_shelter_yes_density_km2_z",
    "osm_railway_subway_entrance_density_km2_z",
]
EOD_COLS = ["eod2012_share_hogares_de_income_proxy_z"]
EOD_RAW_COLS = ["eod2012_share_hogares_de_income_proxy"]
EOD_MODEL_READY_FULL_PATH = PROJECT_ROOT / "data" / "processed" / "eod2012" / "eod2012_zone_features_zona777.parquet"
RAW_VARS_BY_Z_COL = {c: c.removesuffix("_z") for c in CENSO_COLS + OSM_COLS + EOD_COLS}
MACROZONA_BASE = "CENTRO"
MACROZONA_DUMMY_LEVELS = ["NORTE", "PONIENTE", "ORIENTE", "SUR", "SURORIENTE", "EXTERNA_ESPECIAL"]
MACROZONA_COLS = [
    "macro_norte",
    "macro_poniente",
    "macro_oriente",
    "macro_sur",
    "macro_suroriente",
    "macro_externa_especial",
]
CONTEXT_KEYS = ["partition", "zona_inicio_viaje", "franja_v2"]
CONTEXT_COLS = [
    "N_VIAJES_ZONA_INICIO_FRANJA_RAW",
    "N_VIAJES_ZONA_INICIO_FRANJA",
    "LOG_N_VIAJES_ZONA_INICIO_FRANJA",
    "N_BUS_STOPS",
    "BUS_STOP_DENSITY",
    "LOG_BUS_STOP_DENSITY",
    "N_METRO_STATIONS",
    "METRO_STATION_DENSITY",
    "LOG_METRO_STATION_DENSITY",
    "BUS_LINE_COUNT",
    "LOG_BUS_LINE_COUNT",
    "METRO_LINE_COUNT",
    "LOG_METRO_LINE_COUNT",
]
RESIDENCE_BASE_COLS = [
    "zona_hogar",
    "n_home_dest_trips_top",
    "n_home_zones_observed",
    "n_home_dest_trips_card",
    "home_zone_top_share",
    "has_home_zone_tie",
    "home_confidence",
]


def parse_sample_fraction(sample_tag: str) -> float:
    try:
        return int(sample_tag.removeprefix("sample").removesuffix("pct")) / 100
    except Exception as exc:
        raise ValueError(f"No se pudo parsear sample_tag={sample_tag!r}") from exc


def year_from_partition(partition: str) -> int:
    return int(partition.split("-W")[0])


def stratified_sample_partition_choice(df: pl.DataFrame, *, fraction: float, seed: int = 42) -> pl.DataFrame:
    if not (0 < fraction <= 1):
        raise ValueError(f"fraction debe estar en (0,1], recibido: {fraction}")
    return (
        df.group_by("partition", "choice_nested", maintain_order=True)
        .map_groups(lambda g: g.sample(fraction=fraction, shuffle=True, seed=seed))
        .sort(["partition", "choice_nested"])
    )


def build_trip_dataset_with_ids(
    lf: pl.LazyFrame,
    df_caracterizacion: pl.DataFrame | None,
    df_od_alt_context: pl.DataFrame,
) -> pl.DataFrame:
    schema_names = set(lf.collect_schema().names())
    lf, _ = derive_metrics(lf, schema_names)
    lf = add_time_dummies_v2(lf)
    lf = add_tipo_pago(lf, df_caracterizacion)
    lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
    lf = lf.with_columns(
        pl.when(pl.col("tipo_pago") == "BIP")
        .then(pl.lit(ALT_CHOICE_MAP["BIP"]))
        .when(pl.col("tipo_pago") == "QR_RED")
        .then(pl.lit(ALT_CHOICE_MAP["QR_RED"]))
        .otherwise(pl.lit(ALT_CHOICE_MAP["QR_OTHER"]))
        .alias("choice_nested")
    )

    pass_cols = [
        "pk_viaje",
        "id_tarjeta",
        "id_viaje",
        "tiempo_inicio_viaje",
    ]
    dummy_cols = ["DUMMY_LAB_PM", "DUMMY_LAB_PT", "DUMMY_LAB_VALLE", "DUMMY_NO_LAB"]
    joined = lf.join(df_od_alt_context.lazy(), on=OD_KEY_COLS, how="inner").select(
        [
            *[pl.col(c) for c in pass_cols if c in schema_names],
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_viaje"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_viaje"),
            "choice_nested",
            "t_vehiculo_total_seg_final",
            "t_espera_inicial_seg",
            "t_espera_trasbordo_seg",
            "n_trasbordos",
            "n_alternatives_observed",
            *dummy_cols,
            *[c for c in df_od_alt_context.columns if c not in OD_KEY_COLS + ["n_alternatives_observed"]],
        ]
    )

    fill_cols = [
        c
        for c in df_od_alt_context.columns
        if c not in OD_KEY_COLS + ["n_alternatives_observed"]
    ]
    joined = joined.with_columns([pl.col(c).fill_null(0) for c in fill_cols if c in joined.collect_schema().names()])
    joined = joined.with_columns(
        pl.when(pl.col("choice_nested") == ALT_CHOICE_MAP["BIP"])
        .then(pl.col("N_BIP"))
        .when(pl.col("choice_nested") == ALT_CHOICE_MAP["QR_RED"])
        .then(pl.col("N_QR_RED"))
        .otherwise(pl.col("N_QR_OTHER"))
        .alias("N_CHOSEN_ALT")
    )
    joined = joined.filter(pl.col("N_CHOSEN_ALT") > 1)

    # Alinear con build_trip_dataset_with_alt_specific_context: métricas realizadas nulas
    # producen TEI/TVH/TET/NTR nulos en leave-one-out cuando la alternativa elegida coincide.
    realized_cols = [
        "t_vehiculo_total_seg_final",
        "t_espera_inicial_seg",
        "t_espera_trasbordo_seg",
        "n_trasbordos",
    ]
    joined = joined.with_columns(
        [pl.col(c).fill_null(0) for c in realized_cols if c in joined.collect_schema().names()]
    )

    chosen_metric_map = {
        "TVH": "t_vehiculo_total_seg_final",
        "TEI": "t_espera_inicial_seg",
        "TET": "t_espera_trasbordo_seg",
        "NTR": "n_trasbordos",
    }
    loo_exprs = []
    for short, realized_col in chosen_metric_map.items():
        for alt in ALT_LEVELS:
            choice_code = ALT_CHOICE_MAP[alt]
            loo_exprs.append(
                pl.when((pl.col("choice_nested") == choice_code) & (pl.col(f"N_{alt}") > 1))
                .then((pl.col(f"{short}_SUM_{alt}") - pl.col(realized_col)) / (pl.col(f"N_{alt}") - 1))
                .otherwise(pl.col(f"{short}_MEAN_{alt}"))
                .alias(f"{short}_{alt}")
            )
    joined = joined.with_columns(loo_exprs)

    out_cols = [
        *[c for c in pass_cols if c in schema_names],
        "zona_inicio_viaje",
        "zona_fin_viaje",
        "choice_nested",
        *dummy_cols,
        "N_BIP",
        "N_QR_RED",
        "N_QR_OTHER",
        "N_CHOSEN_ALT",
        *[f"{short}_{alt}" for short in chosen_metric_map for alt in ALT_LEVELS],
    ]
    return joined.select(out_cols).collect()


def build_partition_model_frame(partition: str) -> pl.DataFrame:
    parquet_path = RAW_PARQUET_BY_PARTITION[partition]
    if not parquet_path.exists():
        raise FileNotFoundError(f"No existe parquet procesado {partition}: {parquet_path}")
    od_config = OdContextConfig(
        include_time_dummies=False,
        time_dummy_variant="v2",
        mean_mode="leave_one_out",
        require_all_alternatives=True,
    )
    lf = read_parquet_portable(str(parquet_path))
    df_caract = load_caracterizacion(resolve_caracterizacion_path(None, partition))
    df_od_alt = build_od_alt_specific_context_table(lf, df_caracterizacion=df_caract, config=od_config)
    df = build_trip_dataset_with_ids(lf, df_caract, df_od_alt)
    year = year_from_partition(partition)
    return df.with_columns(
        [
            pl.lit(partition).alias("partition"),
            pl.lit(year).alias("year"),
            (pl.lit(year) == 2025).cast(pl.Int8).alias("DUMMY_ANIO_2025"),
            pl.when(pl.col("DUMMY_LAB_PM") == 1)
            .then(pl.lit("LAB_PM"))
            .when(pl.col("DUMMY_LAB_PT") == 1)
            .then(pl.lit("LAB_PT"))
            .when(pl.col("DUMMY_LAB_VALLE") == 1)
            .then(pl.lit("LAB_VALLE"))
            .otherwise(pl.lit("NO_LAB"))
            .alias("franja_v2"),
        ]
    )


def add_context_controls(df: pl.DataFrame) -> pl.DataFrame:
    if not FULL_TRIPS_CONTEXT_PATH.exists():
        raise FileNotFoundError(f"No existe full trips context: {FULL_TRIPS_CONTEXT_PATH}")
    df_context = pl.scan_parquet(FULL_TRIPS_CONTEXT_PATH).select(CONTEXT_KEYS + CONTEXT_COLS).unique().collect()
    ensure_unique_keys(df_context, CONTEXT_KEYS, "context_controls")
    before_rows = df.height
    out = df.join(df_context, on=CONTEXT_KEYS, how="left")
    assert_left_join_preserves_rows(before_rows, out.height, "join context_controls")
    missing = out.select(pl.any_horizontal([pl.col(c).is_null() for c in CONTEXT_COLS]).mean()).item()
    if missing != 0:
        raise ValueError(f"Join context_controls dejó faltantes: {missing:.6%}")
    return out


def add_zone_controls(df: pl.DataFrame, zone_path: Path, cols: list[str], context_name: str) -> pl.DataFrame:
    if not zone_path.exists():
        raise FileNotFoundError(f"No existe {context_name}: {zone_path}")
    df_zone = read_zone_controls(zone_path, cols, context_name)
    ensure_unique_keys(df_zone, ["ZONA777"], context_name)
    before_rows = df.height
    out = (
        df.with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777"))
        .join(df_zone, on="ZONA777", how="left")
        .drop("ZONA777")
    )
    assert_left_join_preserves_rows(before_rows, out.height, f"join {context_name}")
    missing = out.select(pl.any_horizontal([pl.col(c).is_null() for c in cols]).mean()).item()
    if missing != 0:
        raise ValueError(f"Join {context_name} dejó faltantes: {missing:.6%}")
    return out


def read_zone_controls(zone_path: Path, cols: list[str], context_name: str) -> pl.DataFrame:
    df_zone = pl.read_parquet(zone_path)
    missing = sorted(set(cols) - set(df_zone.columns))
    if missing:
        raise ValueError(f"Faltan columnas {missing} en {context_name}: {zone_path}")
    return df_zone.select(["ZONA777", *cols])


def standardize_over_used_zones(
    df_zone_model_ready: pl.DataFrame,
    df_est_base: pl.DataFrame,
    raw_vars: list[str],
) -> pl.DataFrame:
    df_used_zones = (
        df_est_base
        .select(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777"))
        .drop_nulls()
        .unique()
    )
    df_used = df_zone_model_ready.join(df_used_zones, on="ZONA777", how="inner")
    df_out = df_zone_model_ready
    for raw_var in raw_vars:
        mu = df_used.select(pl.col(raw_var).mean()).item()
        sd = df_used.select(pl.col(raw_var).std()).item()
        if mu is None:
            raise ValueError(f"No se pudo calcular media para {raw_var} sobre zonas usadas")
        if sd is None or sd == 0:
            sd = 1.0
        df_out = df_out.with_columns(
            ((pl.col(raw_var) - pl.lit(float(mu))) / pl.lit(float(sd))).alias(f"{raw_var}_z")
        )
    return df_out


def augment_censo_zone_sources(df_zone: pl.DataFrame, raw_vars: list[str]) -> pl.DataFrame:
    missing = set(raw_vars) - set(df_zone.columns)
    if not missing:
        return df_zone
    if not CENSO_AGG_FINAL_PATH.exists():
        return df_zone

    dependencies_by_var = {
        "share_mujeres": {"n_mujeres", "n_per"},
        "share_asistencia_parv": {"n_asistencia_parv", "n_edad_0_5"},
    }
    direct_from_agg = {
        raw_var
        for raw_var in missing
        if raw_var not in dependencies_by_var
    }
    dependency_cols = {
        dep
        for raw_var in missing
        for dep in dependencies_by_var.get(raw_var, set())
    }
    required = {"ZONA777"} | direct_from_agg | dependency_cols
    df_agg = pl.read_parquet(CENSO_AGG_FINAL_PATH)
    available = required.intersection(df_agg.columns)
    if "ZONA777" not in available:
        return df_zone

    derived_exprs = []
    if "share_mujeres" in missing and {"n_mujeres", "n_per"}.issubset(df_agg.columns):
        derived_exprs.append(
            (pl.col("n_mujeres") / pl.when(pl.col("n_per") != 0).then(pl.col("n_per"))).alias("share_mujeres")
        )
    if "share_asistencia_parv" in missing and {"n_asistencia_parv", "n_edad_0_5"}.issubset(df_agg.columns):
        derived_exprs.append(
            (
                pl.col("n_asistencia_parv")
                / pl.when(pl.col("n_edad_0_5") != 0).then(pl.col("n_edad_0_5"))
            ).alias("share_asistencia_parv")
        )

    df_derived = df_agg.select(sorted(available))
    if derived_exprs:
        df_derived = df_derived.with_columns(derived_exprs)
    add_cols = [c for c in raw_vars if c in missing and c in df_derived.columns]
    if not add_cols:
        return df_zone
    return df_zone.join(df_derived.select(["ZONA777", *add_cols]), on="ZONA777", how="left")


def fill_missing_raw_with_median(df_zone: pl.DataFrame, raw_vars: list[str], context_name: str) -> pl.DataFrame:
    exprs = []
    for col in raw_vars:
        if col not in df_zone.columns:
            continue
        median_value = df_zone.select(pl.col(col).median()).item()
        if median_value is None:
            continue
        missing_count = df_zone.select(pl.col(col).is_null().sum()).item()
        if missing_count:
            print(
                f"ℹ️ Imputando {missing_count} zonas sin {col} "
                f"con mediana {context_name}/ZONA777 ({median_value:.6f})."
            )
        exprs.append(pl.col(col).fill_null(median_value).alias(col))
    if not exprs:
        return df_zone
    return df_zone.with_columns(exprs)


def complete_used_zones_with_medians(
    df_zone: pl.DataFrame,
    df_est_base: pl.DataFrame,
    raw_vars: list[str],
    context_name: str,
) -> pl.DataFrame:
    df_zone_min = df_zone.select(["ZONA777", *raw_vars])
    df_used_zones = (
        df_est_base
        .select(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777"))
        .drop_nulls()
        .unique()
    )
    df_missing_zones = df_used_zones.join(df_zone_min.select("ZONA777"), on="ZONA777", how="anti")
    if df_missing_zones.is_empty():
        return df_zone_min

    median_exprs = []
    for col in raw_vars:
        median_value = df_zone_min.select(pl.col(col).median()).item()
        if median_value is None:
            raise ValueError(f"No se pudo imputar {col} en {context_name}: mediana nula")
        median_exprs.append(pl.lit(float(median_value)).alias(col))
    print(
        f"ℹ️ Imputando {df_missing_zones.height} zonas usadas sin fila {context_name} "
        "con medianas zonales antes de estandarizar."
    )
    df_imputed = df_missing_zones.with_columns(median_exprs)
    return pl.concat([df_zone_min, df_imputed], how="vertical")


def ensure_zone_model_ready_std(
    *,
    sample_tag: str,
    baseline_path: Path,
    zone_model_ready_full_path: Path,
    zone_model_ready_std_path: Path,
    z_cols: list[str],
    context_name: str,
) -> Path:
    raw_vars = [RAW_VARS_BY_Z_COL[c] for c in z_cols]
    required_cols = {"ZONA777", *raw_vars, *z_cols}
    if zone_model_ready_std_path.exists():
        existing_cols = set(pl.scan_parquet(zone_model_ready_std_path).collect_schema().names())
        missing_cols = sorted(required_cols - existing_cols)
        missing_values = 0.0
        if not missing_cols:
            missing_values = (
                pl.scan_parquet(zone_model_ready_std_path)
                .select(pl.any_horizontal([pl.col(c).is_null() for c in z_cols]).mean().alias("pct"))
                .collect()
                .item()
            )
        if not missing_cols and missing_values == 0:
            return zone_model_ready_std_path
        print(
            f"ℹ️ Re-materializando {context_name} model-ready std para {sample_tag}: "
            f"faltan columnas {missing_cols}, missing_values={missing_values:.6%}"
        )
        zone_model_ready_std_path.unlink()

    if not baseline_path.exists():
        raise FileNotFoundError(f"No existe baseline sample para estandarizar {context_name}: {baseline_path}")
    if not zone_model_ready_full_path.exists():
        raise FileNotFoundError(f"No existe {context_name} model-ready full: {zone_model_ready_full_path}")

    df_base = pl.read_parquet(baseline_path)
    df_zone_full = pl.read_parquet(zone_model_ready_full_path)
    if context_name == "Censo":
        df_zone_full = augment_censo_zone_sources(df_zone_full, raw_vars)
    missing_raw = sorted(set(raw_vars) - set(df_zone_full.columns))
    if missing_raw:
        raise ValueError(f"Faltan variables raw {context_name}: {missing_raw}")
    df_zone_full = fill_missing_raw_with_median(df_zone_full, raw_vars, context_name)
    df_zone_full = complete_used_zones_with_medians(df_zone_full, df_base, raw_vars, context_name)
    df_zone_std = standardize_over_used_zones(df_zone_full, df_base, raw_vars)
    df_zone_std.write_parquet(zone_model_ready_std_path, compression="zstd")
    print(f"✅ {context_name} model-ready std escrito en: {zone_model_ready_std_path}")
    return zone_model_ready_std_path


def ensure_eod_model_ready_std(sample_tag: str, baseline_path: Path) -> Path:
    eod_path = ARTIFACTS_DIR / f"eod2012_zona777_model_ready_{sample_tag}.parquet"
    required_cols = {"ZONA777", *EOD_RAW_COLS, *EOD_COLS}
    if eod_path.exists():
        existing_cols = set(pl.scan_parquet(eod_path).collect_schema().names())
        if required_cols.issubset(existing_cols):
            return eod_path
        print(f"ℹ️ Re-materializando EOD model-ready std: faltan {sorted(required_cols - existing_cols)}")
        eod_path.unlink()
    if not baseline_path.exists():
        raise FileNotFoundError(f"No existe baseline sample para estandarizar EOD: {baseline_path}")
    if not EOD_MODEL_READY_FULL_PATH.exists():
        raise FileNotFoundError(f"No existe EOD model-ready full: {EOD_MODEL_READY_FULL_PATH}")
    df_base = pl.read_parquet(baseline_path)
    df_eod_full = pl.read_parquet(EOD_MODEL_READY_FULL_PATH)
    missing_raw = sorted(set(EOD_RAW_COLS) - set(df_eod_full.columns))
    if missing_raw:
        raise ValueError(f"Faltan variables raw EOD: {missing_raw}")
    df_eod_full = fill_missing_raw_with_median(df_eod_full, EOD_RAW_COLS, "EOD")
    df_eod_full = complete_used_zones_with_medians(df_eod_full, df_base, EOD_RAW_COLS, "EOD")
    df_eod_std = standardize_over_used_zones(df_eod_full, df_base, EOD_RAW_COLS)
    df_eod_std.write_parquet(eod_path, compression="zstd")
    print(f"✅ EOD model-ready std escrito en: {eod_path}")
    return eod_path


def build_macrozone_lookup() -> pl.DataFrame:
    if not ZONAS777_SHP.exists():
        raise FileNotFoundError(f"No existe shapefile ZONA777: {ZONAS777_SHP}")
    gdf = gpd.read_file(ZONAS777_SHP)[["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA"]].copy()
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="coerce")
    gdf = gdf[gdf["ZONA777"].notna()].copy()
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)
    gdf["NMACROZONA"] = pd.to_numeric(gdf["NMACROZONA"], errors="coerce").astype("Int64")
    attrs = gdf.drop_duplicates(["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA"]).copy()
    inconsistent = attrs.groupby("ZONA777").size()
    inconsistent = inconsistent[inconsistent.gt(1)]
    if not inconsistent.empty:
        raise ValueError(f"ZONA777 con macrozona inconsistente: {sorted(map(int, inconsistent.index.tolist()))}")
    attrs = attrs.drop_duplicates("ZONA777").copy()
    attrs["macrozone_model"] = attrs["MACROZONA"].astype(str)
    attrs.loc[attrs["NMACROZONA"].eq(7), "macrozone_model"] = "EXTERNA_ESPECIAL"
    observed = set(attrs["macrozone_model"].dropna().unique())
    expected = set(MACROZONA_DUMMY_LEVELS + [MACROZONA_BASE])
    unexpected = sorted(observed - expected)
    if unexpected:
        raise ValueError(f"Macrozonas no esperadas: {unexpected}")
    for level in MACROZONA_DUMMY_LEVELS:
        attrs[f"macro_{level.lower()}"] = attrs["macrozone_model"].eq(level).astype(float)
    return pl.from_pandas(attrs[["ZONA777", *MACROZONA_COLS]])


def add_macrozone_controls(df: pl.DataFrame) -> pl.DataFrame:
    df_macro = build_macrozone_lookup()
    ensure_unique_keys(df_macro, ["ZONA777"], "macrozone_lookup")
    before_rows = df.height
    out = (
        df.with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777"))
        .join(df_macro, on="ZONA777", how="left")
        .drop("ZONA777")
    )
    assert_left_join_preserves_rows(before_rows, out.height, "join macrozone_lookup")
    missing = out.select(pl.any_horizontal([pl.col(c).is_null() for c in MACROZONA_COLS]).mean()).item()
    if missing != 0:
        raise ValueError(f"Join macrozone_lookup dejó faltantes: {missing:.6%}")
    return out


def add_home_candidates(df: pl.DataFrame) -> pl.DataFrame:
    if not HOME_CANDIDATES_PATH.exists():
        raise FileNotFoundError(
            "No existe artefacto de residencia. Ejecuta primero "
            "`python scripts/audits/build_proposito_pk_bridge.py --scope active`."
        )
    home = pl.read_parquet(HOME_CANDIDATES_PATH).select(["id_tarjeta", *RESIDENCE_BASE_COLS])
    ensure_unique_keys(home, ["id_tarjeta"], "home_candidates")
    before_rows = df.height
    out = df.join(home, on="id_tarjeta", how="left")
    assert_left_join_preserves_rows(before_rows, out.height, "join home_candidates")
    return out


def add_residence_controls(df: pl.DataFrame, zone_path: Path, cols: list[str], context_name: str) -> pl.DataFrame:
    if not zone_path.exists():
        raise FileNotFoundError(f"No existe {context_name}: {zone_path}")
    context_label = context_name.lower()
    imputed_flag_col = f"res_{context_label}_zone_imputed"
    rename_map = {c: f"res_{c}" for c in cols}
    df_zone = read_zone_controls(zone_path, cols, context_name).rename(rename_map)
    res_cols = list(rename_map.values())

    df_home_zones = (
        df.select(pl.col("zona_hogar").cast(pl.Int64, strict=False).alias("ZONA777"))
        .drop_nulls()
        .unique()
    )
    df_missing_home_zones = df_home_zones.join(df_zone.select("ZONA777"), on="ZONA777", how="anti")
    df_zone = df_zone.with_columns(pl.lit(0).cast(pl.Int8).alias(imputed_flag_col))
    if not df_missing_home_zones.is_empty():
        median_exprs = []
        for col in res_cols:
            median_value = df_zone.select(pl.col(col).median()).item()
            if median_value is None:
                raise ValueError(f"No se pudo imputar {col} en residencia {context_name}: mediana nula")
            median_exprs.append(pl.lit(float(median_value)).alias(col))
        print(
            f"ℹ️ Imputando {df_missing_home_zones.height} zonas hogar sin fila {context_name} "
            "con medianas zonales para controles residenciales."
        )
        df_imputed_zones = df_missing_home_zones.with_columns(
            [*median_exprs, pl.lit(1).cast(pl.Int8).alias(imputed_flag_col)]
        )
        df_zone = pl.concat([df_zone, df_imputed_zones], how="vertical")

    ensure_unique_keys(df_zone, ["ZONA777"], f"{context_name}_residence")
    before_rows = df.height
    out = (
        df.with_columns(pl.col("zona_hogar").cast(pl.Int64, strict=False).alias("ZONA777"))
        .join(df_zone, on="ZONA777", how="left")
        .drop("ZONA777")
    )
    assert_left_join_preserves_rows(before_rows, out.height, f"join {context_name}_residence")
    missing_with_home = out.select(
        (pl.any_horizontal([pl.col(c).is_null() for c in res_cols]) & pl.col("zona_hogar").is_not_null())
        .sum()
        .alias("n")
    ).item()
    if missing_with_home:
        raise ValueError(
            f"Join {context_name}_residence dejó {missing_with_home:,} filas con zona_hogar "
            "pero controles residenciales faltantes"
        )
    return out


def write_csv(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)


def write_diagnostics(df: pl.DataFrame, out_dir: Path, sample_tag: str) -> None:
    res_check_cols = [f"res_{c}" for c in CENSO_COLS + EOD_COLS]
    write_csv(
        df.select(
            [
                pl.len().alias("n_rows"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("zona_hogar").is_not_null().sum().alias("n_rows_with_zona_hogar"),
                pl.col("home_confidence").is_not_null().sum().alias("n_rows_with_home_confidence"),
                (pl.col("home_confidence") == "alta").sum().alias("n_rows_home_alta"),
                (pl.col("home_confidence") == "media").sum().alias("n_rows_home_media"),
                (pl.col("home_confidence") == "baja").sum().alias("n_rows_home_baja"),
                (pl.any_horizontal([pl.col(c).is_null() for c in res_check_cols]) & pl.col("zona_hogar").is_not_null())
                .sum()
                .alias("n_rows_res_controls_missing_with_home"),
                pl.col("res_censo_zone_imputed").sum().alias("n_rows_res_censo_zone_imputed"),
                pl.col("res_eod_zone_imputed").sum().alias("n_rows_res_eod_zone_imputed"),
            ]
        ),
        out_dir / f"residence_model_sample_summary_{sample_tag}.csv",
    )
    write_csv(
        df.group_by(["home_confidence", "choice_nested"])
        .agg([pl.len().alias("n_rows"), pl.col("id_tarjeta").n_unique().alias("n_cards")])
        .sort(["home_confidence", "choice_nested"], nulls_last=True),
        out_dir / f"residence_model_sample_choice_by_confidence_{sample_tag}.csv",
    )


def build_sample(sample_tag: str, *, seed: int, force: bool) -> Path:
    fraction = parse_sample_fraction(sample_tag)
    baseline_path = ARTIFACTS_DIR / f"{MODEL_PARTITION}-estimation-{sample_tag}.parquet"
    if not baseline_path.exists():
        raise FileNotFoundError(f"No existe baseline sample para inferir fracción efectiva: {baseline_path}")
    out_path = ARTIFACTS_DIR / f"{MODEL_PARTITION}-estimation-{sample_tag}-residence-censo4-micro-osm-eod2012.parquet"
    if out_path.exists() and not force:
        print(f"ℹ️ Reusando muestra por residencia existente: {out_path}")
        return out_path

    frames = []
    for partition in RAW_PARQUET_BY_PARTITION:
        print(f"ℹ️ Reconstruyendo frame model-ready con ids: {partition}")
        frames.append(build_partition_model_frame(partition))
        gc.collect()
    df_full = pl.concat(frames, how="diagonal_relaxed")

    lf_full_context = pl.scan_parquet(FULL_TRIPS_CONTEXT_PATH)
    valid_origins = (
        lf_full_context.select(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False))
        .drop_nulls()
        .unique()
        .collect()
        .get_column("zona_inicio_viaje")
        .to_list()
    )
    df_full = df_full.with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False)).filter(
        pl.col("zona_inicio_viaje").is_in(valid_origins)
    )
    full_context_n = lf_full_context.select(pl.len()).collect().item()
    if df_full.height != full_context_n:
        raise ValueError(
            "La reconstrucción con ids no replica trips_context full: "
            f"with_ids={df_full.height:,}, full_context={full_context_n:,}"
        )

    baseline_n = pl.scan_parquet(baseline_path).select(pl.len()).collect().item()
    effective_fraction = baseline_n / full_context_n
    sample_fraction = round(effective_fraction, 3)
    if abs(sample_fraction - fraction) > 1e-6:
        print(
            "ℹ️ La fracción efectiva difiere del tag: "
            f"tag={fraction:.6%}, efectiva={effective_fraction:.6%}. "
            f"Se usa {sample_fraction:.3%} para replicar el muestreo."
        )

    df = stratified_sample_partition_choice(df_full, fraction=sample_fraction, seed=seed)
    df = add_context_controls(df)

    censo_path = ensure_zone_model_ready_std(
        sample_tag=sample_tag,
        baseline_path=baseline_path,
        zone_model_ready_full_path=CENSO_MODEL_READY_FULL_PATH,
        zone_model_ready_std_path=ARTIFACTS_DIR / f"censo2024_zona777_model_ready_{sample_tag}_microdata.parquet",
        z_cols=CENSO_COLS,
        context_name="Censo",
    )
    osm_path = ensure_zone_model_ready_std(
        sample_tag=sample_tag,
        baseline_path=baseline_path,
        zone_model_ready_full_path=OSM_MODEL_READY_FULL_PATH,
        zone_model_ready_std_path=ARTIFACTS_DIR / f"osm_zona777_model_ready_{sample_tag}.parquet",
        z_cols=OSM_COLS,
        context_name="OSM",
    )
    eod_path = ensure_eod_model_ready_std(sample_tag, baseline_path)
    df = add_zone_controls(df, censo_path, CENSO_COLS, "Censo origen")
    df = add_zone_controls(df, osm_path, OSM_COLS, "OSM origen")
    df = add_zone_controls(df, eod_path, EOD_COLS, "EOD origen")
    df = add_macrozone_controls(df)
    df = add_home_candidates(df)
    df = add_residence_controls(df, censo_path, CENSO_COLS, "Censo")
    df = add_residence_controls(df, eod_path, EOD_COLS, "EOD")

    df.write_parquet(out_path, compression="zstd")
    write_diagnostics(df, PK_BRIDGE_DIR, sample_tag)
    print(f"✅ Muestra model-ready por residencia escrita en: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construye una muestra model-ready con residencia inferida y controles residenciales."
    )
    parser.add_argument("--sample-tag", default="sample2pct", choices=["sample2pct", "sample5pct", "sample10pct"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    out_path = build_sample(args.sample_tag, seed=args.seed, force=args.force)
    print(f"- output: {out_path}")


if __name__ == "__main__":
    main()
