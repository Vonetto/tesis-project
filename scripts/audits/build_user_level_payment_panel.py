from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.od_buffers_nested_logit import (  # noqa: E402
    add_time_dummies_v2,
    add_tipo_pago,
    derive_metrics,
    load_caracterizacion,
    resolve_caracterizacion_path,
)


ARTIFACTS_DIR = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
PK_BRIDGE_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "pk_bridge"
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)

PROCESSED_TRIPS_BY_WEEK = {
    "2024-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W14.parquet",
    "2024-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W15.parquet",
    "2024-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W16.parquet",
    "2024-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W17.parquet",
    "2025-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W14.parquet",
    "2025-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W15.parquet",
    "2025-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W16.parquet",
    "2025-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W17.parquet",
}
SCOPE_WEEKS = {
    "active": ["2024-W17", "2025-W17"],
    "ml_2025": ["2025-W14", "2025-W15", "2025-W17"],
    "interannual_ml": [
        "2024-W14",
        "2024-W15",
        "2024-W16",
        "2024-W17",
        "2025-W14",
        "2025-W15",
        "2025-W16",
        "2025-W17",
    ],
}
HOME_CANDIDATES_BY_SCOPE = {
    "active": PK_BRIDGE_DIR / "user_home_candidates_active.parquet",
    "ml_2025": PK_BRIDGE_DIR / "user_home_candidates_ml_2025.parquet",
    "interannual_ml": PK_BRIDGE_DIR / "user_home_candidates_interannual_ml.parquet",
}

CENSO_COLS = [
    "share_cine18_universitaria_o_mas_micro_z",
    "share_discapacidad_z",
    "share_inmigrantes_z",
    "share_mujeres_z",
    "share_asistencia_parv_z",
    "prom_edad_z",
]
EOD_COLS = ["eod2012_share_hogares_de_income_proxy_z"]
OSM_COLS = [
    "osm_leisure_playground_density_km2_z",
    "osm_amenity_school_density_km2_z",
    "osm_amenity_university_density_km2_z",
    "osm_transport_shelter_yes_density_km2_z",
    "osm_railway_subway_entrance_density_km2_z",
]
# NMACROZONA del shapefile Zonas777_V07_04_2014: 1=NORTE, 2=PONIENTE, 3=ORIENTE,
# 4=CENTRO, 5=SUR, 6=SURORIENTE, 7=EXTERNA (string "EXTERNA NORTE/PONIENTE/SUR").
# CENTRO (string exacto "CENTRO", NMACROZONA=4, comuna Santiago) faltaba aquí, lo
# que dejaba ~12% de tarjetas (centro de Santiago, QR_OTHER alto) con las dummies
# de macrozona en 0. Se agrega para que CENTRO tenga su propia dummy.
MACROZONA_DUMMY_LEVELS = ["NORTE", "PONIENTE", "ORIENTE", "CENTRO", "SUR", "SURORIENTE", "EXTERNA_ESPECIAL"]
MACROZONA_COLS = [
    "macro_norte",
    "macro_poniente",
    "macro_oriente",
    "macro_centro",
    "macro_sur",
    "macro_suroriente",
    "macro_externa_especial",
]
TRANSPORT_COLS = [f"tipo_transporte_{i}" for i in range(1, 7)]
# docs/diccionario_viajes.txt: 1=Bus, 2=Metro, 3=Zona Paga, 4=MetroTren.
# Zona Paga is bus-like; MetroTren is rail-like for coarse modal shares.
BUS_CODES = ["1", "3"]
METRO_CODES = ["2", "4"]


def panel_path(scope: str, variant: str) -> Path:
    return OUT_DIR / f"user_level_payment_panel_{scope}_{variant}.parquet"


def csv_path(scope: str, stem: str, variant: str | None = None) -> Path:
    suffix = f"{scope}_{variant}" if variant else scope
    return OUT_DIR / f"{stem}_{suffix}.csv"


def validate_scope(scope: str) -> list[str]:
    if scope not in SCOPE_WEEKS:
        raise ValueError(f"Scope no soportado: {scope}")
    return SCOPE_WEEKS[scope]


def assert_inputs(scope: str, weeks: list[str]) -> None:
    missing = [str(PROCESSED_TRIPS_BY_WEEK[w]) for w in weeks if not PROCESSED_TRIPS_BY_WEEK[w].exists()]
    if missing:
        raise FileNotFoundError(f"Faltan parquets procesados para scope={scope}: {missing}")
    home_path = HOME_CANDIDATES_BY_SCOPE[scope]
    if not home_path.exists():
        raise FileNotFoundError(f"No existe bridge de residencia para scope={scope}: {home_path}")
    required_zone_files = [
        ARTIFACTS_DIR / "censo2024_zona777_model_ready_sample5pct_microdata.parquet",
        ARTIFACTS_DIR / "eod2012_zona777_model_ready_sample5pct.parquet",
        ARTIFACTS_DIR / "osm_zona777_model_ready_sample5pct.parquet",
    ]
    missing_zone = [str(p) for p in required_zone_files if not p.exists()]
    if missing_zone:
        raise FileNotFoundError(f"Faltan lookups zonales: {missing_zone}")
    if not ZONAS777_SHP.exists():
        raise FileNotFoundError(f"No existe shapefile ZONA777 para macrozonas: {ZONAS777_SHP}")


def ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def _any_code_expr(codes: list[str]) -> pl.Expr:
    return pl.any_horizontal(
        [pl.col(c).cast(pl.Utf8, strict=False).is_in(codes).fill_null(False) for c in TRANSPORT_COLS]
    )


def load_week_lf(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema_names = set(lf.collect_schema().names())
    required = {
        "id_tarjeta",
        "is_qr",
        "tiempo_inicio_viaje",
        "fecha",
        "semana_iso",
        "iso_year",
        "iso_week",
        "zona_inicio_viaje",
        "zona_fin_viaje",
        "tipodia",
        "te0_calculado",
        "n_etapas_recon",
        *TRANSPORT_COLS,
    }
    missing = sorted(required - schema_names)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    lf, _ = derive_metrics(lf, schema_names)
    lf = add_time_dummies_v2(lf)
    df_caracterizacion = load_caracterizacion(resolve_caracterizacion_path(None, week))
    lf = add_tipo_pago(lf, df_caracterizacion)

    has_bus = _any_code_expr(BUS_CODES)
    has_metro = _any_code_expr(METRO_CODES)
    return (
        lf.with_columns(
            [
                pl.lit(week).alias("partition"),
                pl.col("id_tarjeta").cast(pl.Utf8).alias("id_tarjeta"),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_viaje"),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_viaje"),
                pl.col("tiempo_inicio_viaje").dt.date().alias("trip_date"),
                pl.col("iso_year").cast(pl.Int16, strict=False).alias("trip_year"),
                has_bus.alias("has_bus"),
                has_metro.alias("has_metro"),
            ]
        )
        .with_columns(
            [
                (pl.col("has_bus") & ~pl.col("has_metro")).cast(pl.Int8).alias("trip_solo_bus"),
                (pl.col("has_metro") & ~pl.col("has_bus")).cast(pl.Int8).alias("trip_solo_metro"),
                (pl.col("has_bus") & pl.col("has_metro")).cast(pl.Int8).alias("trip_metro_bus"),
            ]
        )
        .select(
            [
                "partition",
                "id_tarjeta",
                "tipo_pago",
                "tiempo_inicio_viaje",
                "trip_date",
                "semana_iso",
                "trip_year",
                "iso_week",
                "zona_inicio_viaje",
                "zona_fin_viaje",
                "hora",
                "DUMMY_LAB_PM",
                "DUMMY_LAB_PT",
                "DUMMY_LAB_VALLE",
                "DUMMY_NO_LAB",
                "t_vehiculo_total_seg_final",
                "t_espera_inicial_seg",
                "t_espera_trasbordo_seg",
                "n_trasbordos",
                "trip_solo_bus",
                "trip_solo_metro",
                "trip_metro_bus",
            ]
        )
    )


def trips_lf_for_scope(weeks: list[str]) -> pl.LazyFrame:
    return pl.concat([load_week_lf(w) for w in weeks], how="diagonal_relaxed")


def build_user_aggregates(trips_lf: pl.LazyFrame) -> pl.DataFrame:
    aggregated = trips_lf.group_by("id_tarjeta").agg(
        [
            pl.len().alias("n_viajes"),
            pl.col("tipo_pago").drop_nulls().n_unique().alias("n_tipo_pago_observed"),
            pl.col("tipo_pago").drop_nulls().first().alias("tipo_tarjeta_first"),
            pl.col("tipo_pago").drop_nulls().unique().sort().alias("tipo_pago_values"),
            pl.col("trip_date").n_unique().alias("n_dias_activos"),
            pl.col("semana_iso").n_unique().alias("n_semanas_activas"),
            pl.col("tiempo_inicio_viaje").min().alias("first_trip_ts"),
            pl.col("tiempo_inicio_viaje").max().alias("last_trip_ts"),
            pl.col("trip_year").min().alias("first_trip_year"),
            pl.col("trip_year").max().alias("last_trip_year"),
            (pl.col("trip_year") == 2025).mean().alias("share_trips_2025"),
            pl.col("hora").mean().alias("hora_mean"),
            pl.col("hora").median().alias("hora_median"),
            pl.col("hora").std().alias("hora_std"),
            pl.col("DUMMY_LAB_PM").mean().alias("share_lab_pm"),
            pl.col("DUMMY_LAB_PT").mean().alias("share_lab_pt"),
            pl.col("DUMMY_LAB_VALLE").mean().alias("share_lab_valle"),
            pl.col("DUMMY_NO_LAB").mean().alias("share_no_lab"),
            pl.col("trip_solo_bus").mean().alias("share_trips_solo_bus"),
            pl.col("trip_solo_metro").mean().alias("share_trips_solo_metro"),
            pl.col("trip_metro_bus").mean().alias("share_trips_metro_bus"),
            pl.col("n_trasbordos").mean().alias("n_trasbordos_mean"),
            pl.col("n_trasbordos").median().alias("n_trasbordos_median"),
            pl.col("n_trasbordos").max().alias("n_trasbordos_max"),
            (pl.col("n_trasbordos") > 0).mean().alias("share_trips_with_transfer"),
            (pl.col("t_vehiculo_total_seg_final") / 60).mean().alias("t_vehiculo_mean_min"),
            (pl.col("t_vehiculo_total_seg_final") / 60).median().alias("t_vehiculo_median_min"),
            (pl.col("t_vehiculo_total_seg_final") / 60).min().alias("t_vehiculo_min_min"),
            (pl.col("t_vehiculo_total_seg_final") / 60).max().alias("t_vehiculo_max_min"),
            (pl.col("t_espera_inicial_seg") / 60).mean().alias("t_espera_ini_mean_min"),
            (pl.col("t_espera_inicial_seg") / 60).median().alias("t_espera_ini_median_min"),
            (pl.col("t_espera_inicial_seg") / 60).max().alias("t_espera_ini_max_min"),
            (pl.col("t_espera_trasbordo_seg") / 60).mean().alias("t_espera_trasb_mean_min"),
            (pl.col("t_espera_trasbordo_seg") / 60).median().alias("t_espera_trasb_median_min"),
            (pl.col("t_espera_trasbordo_seg") / 60).max().alias("t_espera_trasb_max_min"),
        ]
    )
    return (
        aggregated.with_columns(
            [
                pl.when(pl.col("n_tipo_pago_observed") == 1)
                .then(pl.col("tipo_tarjeta_first"))
                .otherwise(pl.lit("CONFLICT"))
                .alias("tipo_tarjeta"),
                (pl.col("n_tipo_pago_observed") > 1).cast(pl.Int8).alias("target_conflict_flag"),
                (pl.col("last_trip_ts") - pl.col("first_trip_ts")).dt.total_days().alias("trip_span_days"),
            ]
        )
        .with_columns(
            [
                pl.col("tipo_pago_values").list.join("|").alias("tipo_pago_set"),
                pl.col("tipo_tarjeta").is_in(["QR_RED", "QR_OTHER"]).cast(pl.Int8).alias("is_qr"),
                (pl.col("tipo_tarjeta") == "QR_RED").cast(pl.Int8).alias("is_qr_red"),
                (pl.col("tipo_tarjeta") == "QR_OTHER").cast(pl.Int8).alias("is_qr_other"),
                (1 - pl.col("share_trips_2025")).alias("share_trips_2024"),
            ]
        )
        .drop(["tipo_tarjeta_first", "tipo_pago_values"])
        .collect()
    )


def _rank_zone_counts(counts: pl.DataFrame, *, zone_col: str, prefix: str) -> pl.DataFrame:
    if counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8})
    ranked = (
        counts.sort(["id_tarjeta", "n_zone_trips", zone_col], descending=[False, True, False])
        .with_columns((pl.int_range(pl.len()).over("id_tarjeta") + 1).alias("rank"))
        .filter(pl.col("rank") <= 2)
    )
    totals = counts.group_by("id_tarjeta").agg(
        [
            pl.col("n_zone_trips").sum().alias("n_total_zone_events"),
            pl.len().alias(f"n_{prefix}_zones"),
        ]
    )
    entropy = (
        counts.join(totals.select(["id_tarjeta", "n_total_zone_events"]), on="id_tarjeta", how="left")
        .with_columns((pl.col("n_zone_trips") / pl.col("n_total_zone_events")).alias("p_zone"))
        .with_columns((-(pl.col("p_zone") * pl.col("p_zone").log())).alias("entropy_part"))
        .group_by("id_tarjeta")
        .agg(pl.col("entropy_part").sum().alias(f"{prefix}_zone_entropy"))
    )
    wide_parts = [totals.drop("n_total_zone_events"), entropy]
    for rank in [1, 2]:
        part = (
            ranked.filter(pl.col("rank") == rank)
            .join(totals.select(["id_tarjeta", "n_total_zone_events"]), on="id_tarjeta", how="left")
            .select(
                [
                    "id_tarjeta",
                    pl.col(zone_col).alias(f"{prefix}_zone_top{rank}"),
                    (pl.col("n_zone_trips") / pl.col("n_total_zone_events")).alias(
                        f"{prefix}_zone_top{rank}_share"
                    ),
                    pl.col("n_zone_trips").alias(f"{prefix}_zone_top{rank}_n"),
                ]
            )
        )
        wide_parts.append(part)
    out = wide_parts[0]
    for part in wide_parts[1:]:
        out = out.join(part, on="id_tarjeta", how="left")
    return out


def build_zone_features(trips_lf: pl.LazyFrame) -> pl.DataFrame:
    origin_counts = (
        trips_lf.filter(pl.col("zona_inicio_viaje").is_not_null())
        .group_by(["id_tarjeta", "zona_inicio_viaje"])
        .agg(pl.len().alias("n_zone_trips"))
        .collect()
    )
    dest_counts = (
        trips_lf.filter(pl.col("zona_fin_viaje").is_not_null())
        .group_by(["id_tarjeta", "zona_fin_viaje"])
        .agg(pl.len().alias("n_zone_trips"))
        .collect()
    )
    activity_counts = (
        pl.concat(
            [
                trips_lf.select(["id_tarjeta", pl.col("zona_inicio_viaje").alias("activity_zone")]),
                trips_lf.select(["id_tarjeta", pl.col("zona_fin_viaje").alias("activity_zone")]),
            ],
            how="diagonal_relaxed",
        )
        .filter(pl.col("activity_zone").is_not_null())
        .group_by(["id_tarjeta", "activity_zone"])
        .agg(pl.len().alias("n_zone_trips"))
        .collect()
    )

    out = _rank_zone_counts(origin_counts, zone_col="zona_inicio_viaje", prefix="origin")
    for part in [
        _rank_zone_counts(dest_counts, zone_col="zona_fin_viaje", prefix="dest"),
        _rank_zone_counts(activity_counts, zone_col="activity_zone", prefix="activity"),
    ]:
        out = out.join(part, on="id_tarjeta", how="full", coalesce=True)
    return out


def ensure_unique_key(df: pl.DataFrame, key: str, name: str) -> None:
    n_rows = df.height
    n_unique = df.select(pl.col(key).n_unique()).item()
    if n_rows != n_unique:
        raise ValueError(f"{name}: llave {key} no es única ({n_unique} únicos vs {n_rows} filas)")


def build_zone_lookup() -> pl.DataFrame:
    censo = pl.read_parquet(
        ARTIFACTS_DIR / "censo2024_zona777_model_ready_sample5pct_microdata.parquet"
    ).select(["ZONA777", *CENSO_COLS])
    eod = pl.read_parquet(ARTIFACTS_DIR / "eod2012_zona777_model_ready_sample5pct.parquet").select(
        ["ZONA777", *EOD_COLS]
    )
    osm = pl.read_parquet(ARTIFACTS_DIR / "osm_zona777_model_ready_sample5pct.parquet").select(
        ["ZONA777", *OSM_COLS]
    )
    for name, df in [("censo", censo), ("eod", eod), ("osm", osm)]:
        ensure_unique_key(df, "ZONA777", name)
    return censo.join(eod, on="ZONA777", how="left").join(osm, on="ZONA777", how="left")


def build_macrozone_lookup() -> pl.DataFrame:
    import geopandas as gpd

    gdf = gpd.read_file(ZONAS777_SHP)[["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA", "geometry"]].copy()
    if gdf.crs is None:
        # El shapefile histórico viene sin .prj, pero sus bounds están en lon/lat Santiago.
        gdf = gdf.set_crs(4326)
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="coerce")
    gdf = gdf[gdf["ZONA777"].notna()].copy()
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)
    gdf["NMACROZONA"] = pd.to_numeric(gdf["NMACROZONA"], errors="coerce").astype("Int64")
    gdf_metric = gdf.to_crs(32719)
    centroids = gdf_metric.geometry.centroid.to_crs(gdf.crs)
    attrs = gdf.drop(columns=["geometry"]).drop_duplicates(["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA"]).copy()
    inconsistent = attrs.groupby("ZONA777").size()
    inconsistent = inconsistent[inconsistent.gt(1)]
    if not inconsistent.empty:
        raise ValueError(f"ZONA777 con macrozona inconsistente: {sorted(map(int, inconsistent.index.tolist()))}")
    attrs = attrs.drop_duplicates("ZONA777").copy()
    attrs["macrozone_model"] = attrs["MACROZONA"].astype(str)
    attrs.loc[attrs["NMACROZONA"].eq(7), "macrozone_model"] = "EXTERNA_ESPECIAL"
    for level in MACROZONA_DUMMY_LEVELS:
        attrs[f"macro_{level.lower()}"] = attrs["macrozone_model"].eq(level).astype(float)
    centroid_df = pd.DataFrame(
        {
            "ZONA777": gdf["ZONA777"].to_numpy(),
            "zone_lon": centroids.x.to_numpy(),
            "zone_lat": centroids.y.to_numpy(),
        }
    ).drop_duplicates("ZONA777")
    attrs = attrs.merge(centroid_df, on="ZONA777", how="left")
    return pl.from_pandas(attrs[["ZONA777", "macrozone_model", "zone_lon", "zone_lat", *MACROZONA_COLS]])


def _rename_zone_lookup(df: pl.DataFrame, prefix: str, cols: list[str]) -> pl.DataFrame:
    return df.select(["ZONA777", *cols]).rename({c: f"{prefix}_{c}" for c in cols})


def _rename_macro_lookup(df: pl.DataFrame, prefix: str) -> pl.DataFrame:
    rename = {"macrozone_model": f"{prefix}_macrozone", "zone_lon": f"{prefix}_lon", "zone_lat": f"{prefix}_lat"}
    rename.update({c: f"{prefix}_{c}" for c in MACROZONA_COLS})
    return df.rename(rename)


def join_context_lookups(panel: pl.DataFrame, scope: str) -> pl.DataFrame:
    before_rows = panel.height
    home = pl.read_parquet(HOME_CANDIDATES_BY_SCOPE[scope]).select(
        [
            "id_tarjeta",
            "zona_hogar",
            "n_home_dest_trips_top",
            "n_home_zones_observed",
            "n_home_dest_trips_card",
            "home_zone_top_share",
            "has_home_zone_tie",
            "home_confidence",
        ]
    )
    ensure_unique_key(home, "id_tarjeta", "home_candidates")
    panel = panel.join(home, on="id_tarjeta", how="left")

    zone_lookup = build_zone_lookup()
    macro_lookup = build_macrozone_lookup()
    ensure_unique_key(zone_lookup, "ZONA777", "zone_lookup")
    ensure_unique_key(macro_lookup, "ZONA777", "macrozone_lookup")

    socio_cols = CENSO_COLS + EOD_COLS
    for zone_col, prefix, cols in [
        ("zona_hogar", "res", socio_cols),
        ("origin_zone_top1", "origin_top1", OSM_COLS),
        ("origin_zone_top2", "origin_top2", OSM_COLS),
        ("activity_zone_top1", "activity_top1", OSM_COLS),
    ]:
        lookup = _rename_zone_lookup(zone_lookup, prefix, cols)
        panel = (
            panel.with_columns(pl.col(zone_col).cast(pl.Int64, strict=False).alias("ZONA777"))
            .join(lookup, on="ZONA777", how="left")
            .drop("ZONA777")
        )

    for zone_col, prefix in [
        ("zona_hogar", "home"),
        ("origin_zone_top1", "origin_top1"),
        ("origin_zone_top2", "origin_top2"),
        ("dest_zone_top1", "dest_top1"),
        ("activity_zone_top1", "activity_top1"),
        ("activity_zone_top2", "activity_top2"),
    ]:
        lookup = _rename_macro_lookup(macro_lookup, prefix)
        panel = (
            panel.with_columns(pl.col(zone_col).cast(pl.Int64, strict=False).alias("ZONA777"))
            .join(lookup, on="ZONA777", how="left")
            .drop("ZONA777")
        )

    if panel.height != before_rows:
        raise ValueError(f"Los joins contextuales cambiaron filas: {before_rows} -> {panel.height}")
    return panel


def write_diagnostics(
    panel: pl.DataFrame,
    scope: str,
    *,
    variant: str | None = None,
    excluded_target_conflicts: int = 0,
) -> None:
    total_cards = panel.height
    total_trips = panel.select(pl.col("n_viajes").sum()).item()
    summary = pl.DataFrame(
        [
            {"metric": "scope", "value": scope},
            {"metric": "n_cards", "value": str(total_cards)},
            {"metric": "n_trips", "value": str(total_trips)},
            {
                "metric": "target_conflict_cards",
                "value": str(panel.select(pl.col("target_conflict_flag").sum()).item()),
            },
            {"metric": "excluded_target_conflict_cards", "value": str(excluded_target_conflicts)},
            {
                "metric": "missing_zona_hogar_rate",
                "value": f"{panel.select(pl.col('zona_hogar').is_null().mean()).item():.8f}",
            },
            {
                "metric": "home_alta_cards",
                "value": str(panel.filter(pl.col("home_confidence") == "alta").height),
            },
            {
                "metric": "home_alta_media_cards",
                "value": str(panel.filter(pl.col("home_confidence").is_in(["alta", "media"])).height),
            },
        ]
    )
    summary.write_csv(csv_path(scope, "user_level_panel_summary", variant))

    (
        panel.group_by("tipo_tarjeta")
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("n_viajes").sum().alias("n_trips"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_cards") / total_cards).alias("card_share"),
                (pl.col("n_trips") / total_trips).alias("trip_share"),
            ]
        )
        .sort("tipo_tarjeta")
        .write_csv(csv_path(scope, "user_level_panel_target_distribution", variant))
    )

    threshold_rows = []
    for threshold in [1, 3, 5, 10, 20, 50]:
        subset = panel.filter(pl.col("n_viajes") >= threshold)
        n_cards = subset.height
        n_trips = subset.select(pl.col("n_viajes").sum()).item() if n_cards else 0
        base = {
            "min_n_viajes": threshold,
            "n_cards": n_cards,
            "card_share": n_cards / total_cards if total_cards else math.nan,
            "n_trips": n_trips,
            "trip_share": n_trips / total_trips if total_trips else math.nan,
        }
        target_counts = subset.group_by("tipo_tarjeta").agg(pl.len().alias("n")).to_dicts()
        for row in target_counts:
            base[f"card_share_{row['tipo_tarjeta']}"] = row["n"] / n_cards if n_cards else math.nan
        threshold_rows.append(base)
    pl.DataFrame(threshold_rows).write_csv(
        csv_path(scope, "user_level_panel_trip_threshold_sensitivity", variant)
    )

    conflicts = panel.filter(pl.col("target_conflict_flag") == 1).head(1000)
    if not (excluded_target_conflicts and conflicts.is_empty()):
        conflicts.write_csv(csv_path(scope, "user_level_panel_target_conflicts_sample", variant))

    pl.DataFrame(
        [
            {
                "scope": scope,
                "exclusion": "target_conflict_flag",
                "n_cards": excluded_target_conflicts,
                "reason": "Una misma id_tarjeta aparece con mas de un tipo_pago en el scope.",
            }
        ]
    ).write_csv(csv_path(scope, "user_level_panel_exclusions", variant))

    key_cols = [
        "tipo_tarjeta",
        "zona_hogar",
        "home_confidence",
        "origin_zone_top1",
        "dest_zone_top1",
        "activity_zone_top1",
        "res_share_cine18_universitaria_o_mas_micro_z",
        "res_eod2012_share_hogares_de_income_proxy_z",
        "origin_top1_osm_transport_shelter_yes_density_km2_z",
        "home_macrozone",
        "origin_top1_macrozone",
    ]
    missing_summary = panel.select(
        [
            pl.col(c).is_null().sum().alias(c)
            for c in key_cols
            if c in panel.columns
        ]
    ).transpose(include_header=True, header_name="column", column_names=["n_missing"])
    missing_summary = missing_summary.with_columns((pl.col("n_missing") / total_cards).alias("missing_rate"))
    missing_summary.write_csv(csv_path(scope, "user_level_panel_missing_summary", variant))


def conflict_variant(conflict_policy: str) -> str:
    if conflict_policy == "exclude":
        return "clean"
    if conflict_policy == "keep":
        return "with_conflicts"
    return "audit"


def build_panel(scope: str, *, force: bool, conflict_policy: str) -> Path:
    weeks = validate_scope(scope)
    assert_inputs(scope, weeks)
    ensure_out_dir()
    out_path = panel_path(scope, conflict_variant(conflict_policy))
    if out_path.exists() and not force:
        print(f"ℹ️ Reusando panel existente: {out_path}")
        return out_path

    print(f"ℹ️ Construyendo panel usuario-tarjeta scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    panel = build_user_aggregates(trips_lf)
    zone_features = build_zone_features(trips_lf)
    panel = panel.join(zone_features, on="id_tarjeta", how="left")
    panel = join_context_lookups(panel, scope)

    duplicate_ids = panel.select((pl.len() - pl.col("id_tarjeta").n_unique()).alias("n_duplicates")).item()
    if duplicate_ids:
        raise ValueError(f"Output con id_tarjeta duplicadas: {duplicate_ids}")
    n_conflicts = panel.select(pl.col("target_conflict_flag").sum()).item()
    if n_conflicts:
        panel.filter(pl.col("target_conflict_flag") == 1).head(1000).write_csv(
            csv_path(scope, "user_level_panel_target_conflicts_sample", conflict_variant(conflict_policy))
        )
        if conflict_policy == "fail":
            write_diagnostics(panel, scope, variant=conflict_variant(conflict_policy))
            raise ValueError(f"Hay {n_conflicts} id_tarjeta con más de un tipo_pago. Revisar conflicts sample.")
        if conflict_policy == "keep":
            print(f"⚠️ Manteniendo {n_conflicts} id_tarjeta con más de un tipo_pago con target_conflict_flag=1.")
        elif conflict_policy == "exclude":
            print(f"⚠️ Excluyendo {n_conflicts} id_tarjeta con más de un tipo_pago.")
            panel = panel.filter(pl.col("target_conflict_flag") == 0)
        else:
            raise ValueError(f"Política de conflictos no soportada: {conflict_policy}")

    panel.write_parquet(out_path, compression="zstd")
    excluded_conflicts = n_conflicts if conflict_policy == "exclude" else 0
    write_diagnostics(
        panel,
        scope,
        variant=conflict_variant(conflict_policy),
        excluded_target_conflicts=excluded_conflicts,
    )
    print(f"✅ Panel escrito: {out_path}")
    return out_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="ml_2025")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--conflict-policy",
        choices=["fail", "exclude", "keep"],
        default="fail",
        help=(
            "Qué hacer si una misma id_tarjeta aparece con más de un tipo_pago: "
            "fail audita y falla; exclude escribe variante clean; keep escribe variante with_conflicts."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_panel(args.scope, force=args.force, conflict_policy=args.conflict_policy)


if __name__ == "__main__":
    main()
