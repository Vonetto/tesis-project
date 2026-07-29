"""Build structural_wide matrices for user-level segmentation.

`structural_wide` is a sensitivity branch built on top of the audited
behavioral_wide v0b feature set. It adds residential context, geography, BIP
access, transport supply, and selected OSM environment variables.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_user_behavioral_segmentation_matrix import (
    BEHAVIORAL_WIDE_BASE_RAW_COLS,
    BEHAVIORAL_WIDE_MAIN_COLS,
    BEHAVIORAL_WIDE_MAIN_METADATA,
    BEHAVIORAL_WIDE_V0B_COLS,
    DAILY_TOUR_ARTIFACT_PATH,
    DAILY_TOUR_MAIN_COLS,
    DEFAULT_OUT_DIR,
    TARGET_CONTEXT_COLS,
    UNIVERSE_PATHS,
    existing_columns,
    impute_feature_nulls,
    upsert_inventory,
)


VARIANT_ID = "structural_wide"

OPTIONAL_METADATA_COLS = [
    "n_viajes",
    "share_trips_2025",
    "home_confidence",
    "home_zone_top_share",
    "zona_hogar",
    "home_zona",
    "origin_zone_top1",
    "origin_zone_top1_share",
    "activity_zone_top1",
    "activity_zone_top1_share",
    "activity_zone_entropy",
]

SOCIO_RESIDENCIAL_COLS = [
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
    "res_share_discapacidad_z",
    "res_share_inmigrantes_z",
    "res_share_asistencia_parv_z",
    "res_age_share_18_24",
    "res_age_share_25_44",
]

SOCIO_RESIDENCIAL_EXTRA_COLS = [
    "res_age_share_60_mas",
    "res_prom_edad_z",
    "res_share_mujeres_z",
]

GEOGRAFIA_RESIDENCIAL_COLS = [
    "home_macro_norte",
    "home_macro_poniente",
    "home_macro_oriente",
    "home_macro_centro",
    "home_macro_sur",
    "home_macro_suroriente",
    "home_macro_externa_especial",
]

GEOGRAFIA_ORIGEN_COLS = [
    "origin_top1_macro_norte",
    "origin_top1_macro_poniente",
    "origin_top1_macro_oriente",
    "origin_top1_macro_centro",
    "origin_top1_macro_sur",
    "origin_top1_macro_suroriente",
    "origin_top1_macro_externa_especial",
]

ACCESO_BIP_COLS = [
    "home_bip_load_density_km2",
    "home_bip_load_dist_nearest_m",
    "origin_top1_bip_load_density_km2",
    "origin_top1_bip_load_dist_nearest_m",
]

ACCESO_BIP_ALL_COLS = [
    "home_bip_load_n_points_zone",
    "home_bip_load_density_km2",
    "home_bip_load_dist_nearest_m",
    "origin_top1_bip_load_n_points_zone",
    "origin_top1_bip_load_density_km2",
    "origin_top1_bip_load_dist_nearest_m",
    "activity_top1_bip_load_n_points_zone",
    "activity_top1_bip_load_density_km2",
    "activity_top1_bip_load_dist_nearest_m",
]

OFERTA_TRANSPORTE_COLS = [
    "offer_log_bus_stop_density_origin_mean",
    "offer_log_metro_station_density_origin_mean",
    "offer_origin_bus_like_share",
    "offer_origin_metro_like_share",
    "offer_bus_origin_headway_all_min_mean",
    "offer_bus_origin_headway_ge10_share",
]

OFERTA_TRANSPORTE_ALL_COLS = [
    "offer_log_demand_origin_franja_mean",
    "offer_log_bus_stop_density_origin_mean",
    "offer_log_metro_station_density_origin_mean",
    "offer_origin_bus_like_share",
    "offer_origin_metro_like_share",
    "offer_bus_origin_headway_all_min_mean",
    "offer_bus_origin_headway_ge10_share",
]

ENTORNO_OSM_COLS = [
    "origin_top1_osm_amenity_school_density_km2_z",
    "origin_top1_osm_amenity_university_density_km2_z",
    "origin_top1_osm_transport_shelter_yes_density_km2_z",
    "origin_top1_osm_railway_subway_entrance_density_km2_z",
]

ENTORNO_OSM_ALL_COLS = [
    "origin_top1_osm_amenity_school_density_km2_z",
    "origin_top1_osm_amenity_university_density_km2_z",
    "origin_top1_osm_leisure_playground_density_km2_z",
    "origin_top1_osm_transport_shelter_yes_density_km2_z",
    "origin_top1_osm_railway_subway_entrance_density_km2_z",
    "activity_top1_osm_leisure_playground_density_km2_z",
    "activity_top1_osm_amenity_school_density_km2_z",
    "activity_top1_osm_amenity_university_density_km2_z",
    "activity_top1_osm_transport_shelter_yes_density_km2_z",
]

RHYTHM_EXTRA_COLS = [
    "rhythm_trips_per_span_day",
    "rhythm_trips_per_active_week",
    "rhythm_has_gap",
    "rhythm_trips_per_active_day",
    "rhythm_active_weeks_rate_scope",
    "rhythm_activity_top1_day_share",
    "rhythm_activity_top2_day_share",
    "rhythm_daily_entropy_norm",
    "rhythm_daily_burstiness",
    "rhythm_n_gap_days",
    "rhythm_median_gap_active_days",
    "rhythm_max_gap_active_days",
    "rhythm_weekly_top1_share",
    "rhythm_weekly_burstiness",
]

TRIP_OBS_COLS = [
    "share_lab_valle",
    "share_trips_solo_metro",
    "n_trasbordos_mean",
    "t_vehiculo_mean_min",
    "t_espera_ini_mean_min",
    "t_espera_trasb_mean_min",
]

CONTEXT_RESIDUAL_COLS = [
    "ctx_mean_gap_active_days_home_zone_resid",
    "ctx_active_day_density_home_zone_resid",
    "ctx_n_viajes_home_zone_pctile",
    "ctx_hora_std_home_zone_resid",
    "ctx_service_route_entropy_origin_zone_resid",
]

HYBRID_DIAGNOSTIC_COLS = [
    "hyb_recent_service_entropy",
    "hyb_recent_low_intensity",
    "hyb_solo2025_low_intensity",
    "hyb_recent_hora_std",
    "hyb_low_intensity_hora_std",
    "hyb_low_intensity_service_entropy",
    "hyb_oriente_educ_cont",
    "hyb_oriente_high_hora_std",
]

SERVICE_CONTEXT_COLS = [
    "service_route_entropy_norm",
    "coarse_route_entropy_norm",
    "service_within_od_top_share_weighted",
    "service_within_od_variability_weighted",
    "top_od_service_top1_share",
    "top_od_service_entropy_norm",
]

ADOPTION_TIMING_COLS = [
    "adopt_trip_growth_log_2025_2024",
    "adopt_active_day_growth_log_2025_2024",
    "adopt_active_week_growth_log_2025_2024",
    "adopt_trips_per_active_day_delta",
    "adopt_hora_mean_delta",
    "adopt_hora_std_delta",
    "adopt_lab_peak_share_delta",
    "adopt_no_lab_share_delta",
    "adopt_solo_bus_share_delta",
    "adopt_solo_metro_share_delta",
    "adopt_metro_bus_share_delta",
    "adopt_transfer_share_delta",
    "adopt_origin_n_unique_delta",
    "adopt_dest_n_unique_delta",
    "adopt_origin_top1_changed",
]

PROTOTYPE_COLS = [
    "proto_commuter_peak_score",
    "proto_late_return_score",
    "proto_low_complexity_score",
    "proto_explorer_score",
    "proto_routine_repeater_score",
    "proto_multimodal_score",
]

FRICTION_COLS = [
    "fric_weighted_bip_dist_log",
    "fric_weighted_bip_density_inv",
    "fric_weighted_bip_dist_x_solo_bus",
    "fric_weighted_bip_dist_x_low_intensity",
    "fric_weighted_bip_dist_x_low_active_density",
    "fric_weighted_bip_density_inv_x_solo_bus",
    "fric_home_no_bip_points_x_solo_bus",
    "fric_origin_bus_like_x_weighted_bip_dist",
    "fric_metro_like_x_weighted_bip_density_inv",
    "fric_weighted_bip_dist_x_peak_share",
]

ROUTINE_ALL_COLS = [
    "routine_combo_top1_share",
    "routine_combo_hhi",
    "routine_od_time_top1_share",
    "routine_od_time_hhi",
    "routine_od_top1_share",
    "routine_od_hhi",
    "routine_zone_top1_usage_share",
    "routine_zone_top2_usage_share",
    "routine_zone_exploration_share",
    "routine_lab_peak_share",
    "routine_main_od_share",
    "routine_main_od_roundtrip_balance",
    "routine_commute_like_score",
    "routine_od_time_n_unique",
    "routine_od_time_entropy_norm",
    "routine_zone_n_unique",
]

DAILY_TOUR_SELECTED_COLS = [
    "tour_last_trip_hour_mean",
    "tour_last_trip_lab_pm_peak_share",
    "tour_day_span_hours_mean",
    "tour_peak_anchor_day_share",
    "tour_workday_commute_like_day_share",
    "tour_first_trip_lab_am_peak_share",
    "tour_complex_day_share",
    "tour_mixed_mode_day_share",
]

STRUCTURAL_BLOCKS = {
    "socio_residencial": SOCIO_RESIDENCIAL_COLS,
    "geografia_residencial": GEOGRAFIA_RESIDENCIAL_COLS,
    "acceso_bip": ACCESO_BIP_COLS,
    "oferta_transporte": OFERTA_TRANSPORTE_COLS,
    "entorno_osm": ENTORNO_OSM_COLS,
}

ALL_CANDIDATE_BLOCKS = {
    "socio_residencial": SOCIO_RESIDENCIAL_COLS + SOCIO_RESIDENCIAL_EXTRA_COLS,
    "geografia_residencial": GEOGRAFIA_RESIDENCIAL_COLS,
    "geografia_origen": GEOGRAFIA_ORIGEN_COLS,
    "acceso_bip": ACCESO_BIP_ALL_COLS,
    "oferta_transporte": OFERTA_TRANSPORTE_ALL_COLS,
    "entorno_osm": ENTORNO_OSM_ALL_COLS,
    "ritmo_extra": RHYTHM_EXTRA_COLS,
    "viaje_observado": TRIP_OBS_COLS,
    "contexto_residual": CONTEXT_RESIDUAL_COLS,
    "hibridos_diagnostico": HYBRID_DIAGNOSTIC_COLS,
    "servicio_red": SERVICE_CONTEXT_COLS,
    "adoption_timing": ADOPTION_TIMING_COLS,
    "prototype": PROTOTYPE_COLS,
    "friccion_bip": FRICTION_COLS,
    "rutina_all": ROUTINE_ALL_COLS,
    "daily_tour_selected": DAILY_TOUR_SELECTED_COLS,
}

STRUCTURAL_WIDE_V1_COLS = (
    BEHAVIORAL_WIDE_V0B_COLS
    + SOCIO_RESIDENCIAL_COLS
    + GEOGRAFIA_RESIDENCIAL_COLS
    + ACCESO_BIP_COLS
    + OFERTA_TRANSPORTE_COLS
    + ENTORNO_OSM_COLS
)

STRUCTURAL_WIDE_V1_NO_MACRO_COLS = (
    BEHAVIORAL_WIDE_V0B_COLS
    + SOCIO_RESIDENCIAL_COLS
    + ACCESO_BIP_COLS
    + OFERTA_TRANSPORTE_COLS
    + ENTORNO_OSM_COLS
)

STRUCTURAL_WIDE_V1_SOCIO_ONLY_COLS = (
    BEHAVIORAL_WIDE_V0B_COLS
    + SOCIO_RESIDENCIAL_COLS
)

ALL_CANDIDATES_V0_COLS = list(
    dict.fromkeys(
        BEHAVIORAL_WIDE_MAIN_COLS
        + [
            c
            for cols_by_block in ALL_CANDIDATE_BLOCKS.values()
            for c in cols_by_block
        ]
        + DAILY_TOUR_MAIN_COLS
    )
)

SPEC_FEATURES = {
    "v1": STRUCTURAL_WIDE_V1_COLS,
    "v1_no_macro": STRUCTURAL_WIDE_V1_NO_MACRO_COLS,
    "v1_socio_only": STRUCTURAL_WIDE_V1_SOCIO_ONLY_COLS,
    "all_candidates_v0": ALL_CANDIDATES_V0_COLS,
}

STRUCTURAL_WIDE_V1_METADATA = [
    {
        **row,
        "block": f"behavioral_{row['block']}",
        "source": f"behavioral_wide:{row['source']}",
    }
    for row in BEHAVIORAL_WIDE_MAIN_METADATA
]
for block, cols in STRUCTURAL_BLOCKS.items():
    for col in cols:
        caveat = "contexto estructural; no define conducta por si solo"
        if col == "res_eod2012_share_hogares_de_income_proxy_z":
            caveat = "concentracion D+E proxy EOD 2012; valores altos no son mayor ingreso"
        STRUCTURAL_WIDE_V1_METADATA.append(
            {
                "block": block,
                "variable": col,
                "source": "model_matrix",
                "caveat": caveat,
            }
        )
for block, cols in ALL_CANDIDATE_BLOCKS.items():
    for col in cols:
        caveat = "stress test all-candidates; revisar redundancia antes de interpretar"
        if col == "res_eod2012_share_hogares_de_income_proxy_z":
            caveat = "concentracion D+E proxy EOD 2012; valores altos no son mayor ingreso"
        if block in {"geografia_origen", "hibridos_diagnostico", "contexto_residual"}:
            caveat = "stress test; posible redundancia/artefacto, no usar causalmente"
        STRUCTURAL_WIDE_V1_METADATA.append(
            {
                "block": block,
                "variable": col,
                "source": "model_matrix",
                "caveat": caveat,
            }
        )

# Keep first metadata entry per variable so audited behavioral labels win when
# a feature appears in both the main behavioral set and an all-candidates block.
STRUCTURAL_WIDE_V1_METADATA = (
    pd.DataFrame(STRUCTURAL_WIDE_V1_METADATA)
    .drop_duplicates(subset=["variable"], keep="first")
    .to_dict("records")
)


def spec_features(spec: str) -> list[str]:
    if spec in SPEC_FEATURES:
        return SPEC_FEATURES[spec]
    raise ValueError(f"Spec desconocida: {spec}")


DERIVED_FEATURE_SOURCES = {
    "log1p_n_viajes": "n_viajes",
    "log1p_rhythm_mean_gap_active_days": "rhythm_mean_gap_active_days",
}


def load_structural_wide_frame(path: Path, spec: str) -> pl.DataFrame:
    cols = existing_columns(path)
    metadata_cols = [c for c in OPTIONAL_METADATA_COLS if c in cols]
    features = spec_features(spec)
    daily_cols = existing_columns(DAILY_TOUR_ARTIFACT_PATH)
    daily_features = [c for c in features if c in daily_cols and c not in cols]
    raw_feature_cols = [
        c
        for c in features
        if c not in DERIVED_FEATURE_SOURCES and c in cols
    ]
    derived_raw_cols = [
        raw_col
        for feature, raw_col in DERIVED_FEATURE_SOURCES.items()
        if feature in features
    ]
    missing_features = [
        c
        for c in features
        if c not in DERIVED_FEATURE_SOURCES and c not in cols and c not in daily_cols
    ]
    if missing_features:
        raise ValueError(f"Features no disponibles en {path.name} ni daily-tour: {missing_features}")
    base_select = list(
        dict.fromkeys(
            ["id_tarjeta"]
            + raw_feature_cols
            + derived_raw_cols
            + TARGET_CONTEXT_COLS
            + metadata_cols
        )
    )
    missing_base = [c for c in base_select if c not in cols]
    if missing_base:
        raise ValueError(f"Faltan columnas base en {path.name}: {missing_base}")

    required_daily = ["id_tarjeta"] + daily_features
    missing_daily = [c for c in required_daily if c not in daily_cols]
    if missing_daily:
        raise ValueError(f"Faltan columnas daily-tour: {missing_daily}")

    base_lf = (
        pl.scan_parquet(path)
        .select(base_select)
        .with_columns(
            [
                pl.col("n_viajes").cast(pl.Float64).log1p().alias("log1p_n_viajes"),
                pl.col("rhythm_mean_gap_active_days")
                .cast(pl.Float64)
                .log1p()
                .alias("log1p_rhythm_mean_gap_active_days"),
            ]
        )
    )
    if daily_features:
        daily_lf = pl.scan_parquet(DAILY_TOUR_ARTIFACT_PATH).select(required_daily)
        return base_lf.join(daily_lf, on="id_tarjeta", how="left").collect()
    return base_lf.collect()


def write_feature_metadata(spec: str, branch_id: str, out_dir: Path) -> None:
    features = set(spec_features(spec))
    metadata = pd.DataFrame(STRUCTURAL_WIDE_V1_METADATA)
    metadata = metadata[metadata["variable"].isin(features)].copy()
    missing_metadata = sorted(features - set(metadata["variable"]))
    if missing_metadata:
        raise ValueError(f"Features sin metadata de bloque: {missing_metadata}")
    metadata["spec"] = spec
    metadata["branch_id"] = branch_id
    metadata["spec_role"] = f"{spec}_main"
    metadata.to_csv(out_dir / f"{branch_id}_feature_metadata.csv", index=False)


def validate_spec(universe: str, spec: str) -> None:
    input_path = UNIVERSE_PATHS[universe]
    if not input_path.exists():
        raise FileNotFoundError(f"No existe universo {universe}: {input_path}")

    cols = set(existing_columns(input_path))
    features = spec_features(spec)
    daily_cols = set(existing_columns(DAILY_TOUR_ARTIFACT_PATH))
    raw_needed = {
        c
        for c in features
        if c not in DERIVED_FEATURE_SOURCES and c not in daily_cols
    }
    raw_needed.update(
        raw_col
        for feature, raw_col in DERIVED_FEATURE_SOURCES.items()
        if feature in features
    )
    raw_missing = sorted(raw_needed - cols)
    target_missing = sorted(set(TARGET_CONTEXT_COLS) - cols)
    daily_needed = {c for c in features if c in daily_cols and c not in cols}
    daily_missing = sorted(daily_needed - daily_cols)
    if raw_missing or target_missing or daily_missing:
        raise ValueError(
            f"Schema incompleto para {universe}: "
            f"raw_missing={raw_missing}, target_missing={target_missing}, daily_missing={daily_missing}"
        )
    print(
        f"[dry-run] {spec}_{universe}: features={len(features)} "
        f"behavioral_v0b={len([c for c in features if c in BEHAVIORAL_WIDE_V0B_COLS])} "
        f"extra={len(features) - len([c for c in features if c in BEHAVIORAL_WIDE_V0B_COLS])}",
        flush=True,
    )


def build_spec(universe: str, spec: str, out_dir: Path, force: bool) -> None:
    input_path = UNIVERSE_PATHS[universe]
    if not input_path.exists():
        raise FileNotFoundError(f"No existe universo {universe}: {input_path}")

    branch_id = f"{spec}_{universe}"
    feature_dir = out_dir / "features" / VARIANT_ID
    feature_dir.mkdir(parents=True, exist_ok=True)
    output_path = feature_dir / f"{branch_id}.parquet"
    if output_path.exists() and not force:
        raise FileExistsError(f"Ya existe {output_path}. Usar --force para sobrescribir.")

    features = spec_features(spec)
    df = load_structural_wide_frame(input_path, spec)
    df, imputation = impute_feature_nulls(df, features)

    output_cols = list(dict.fromkeys(["id_tarjeta"] + features + TARGET_CONTEXT_COLS + OPTIONAL_METADATA_COLS))
    output_cols = [c for c in output_cols if c in df.columns]
    df.select(output_cols).write_parquet(output_path)

    inventory_path = out_dir / "structural_wide_feature_matrix_inventory.csv"
    upsert_inventory(
        {
            "variant_id": VARIANT_ID,
            "branch_id": branch_id,
            "universe": universe,
            "spec": spec,
            "n_rows": df.height,
            "n_features": len(features),
            "features": ",".join(features),
            "feature_path": str(output_path),
        },
        inventory_path,
    )

    imputation_path = out_dir / "features" / VARIANT_ID / f"{branch_id}_imputation_summary.csv"
    imputation.to_csv(imputation_path, index=False)
    write_feature_metadata(spec, branch_id, out_dir)

    run_meta = {
        "variant_id": VARIANT_ID,
        "branch_id": branch_id,
        "universe": universe,
        "spec": spec,
        "input_path": str(input_path),
        "daily_tour_artifact_path": str(DAILY_TOUR_ARTIFACT_PATH),
        "output_path": str(output_path),
        "inventory_path": str(inventory_path),
        "imputation_path": str(imputation_path),
        "features": features,
        "excluded_initially": [
            "zona_hogar raw",
            "home_lon/home_lat",
            "origin/activity lon/lat",
            "tipo_tarjeta/is_qr targets",
            "ctx_qr_like_behavior_residual_score",
            "service_route_early_late_rcs/service_route_rcs_2024_2025",
            "first_trip_year/last_trip_year/share_trips_2025",
        ],
    }
    (out_dir / "features" / VARIANT_ID / f"{branch_id}_run_meta.json").write_text(
        json.dumps(run_meta, indent=2),
        encoding="utf-8",
    )
    print(f"[build] {branch_id}: rows={df.height:,} features={len(features)} -> {output_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build structural_wide segmentation matrices.")
    parser.add_argument("--universe", choices=sorted(UNIVERSE_PATHS), default="alta_n3")
    parser.add_argument("--spec", choices=sorted(SPEC_FEATURES), default="v1")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate source schemas without writing outputs.")
    args = parser.parse_args()

    if args.dry_run:
        validate_spec(args.universe, args.spec)
        return

    args.out_dir.mkdir(parents=True, exist_ok=True)
    build_spec(args.universe, args.spec, args.out_dir, args.force)


if __name__ == "__main__":
    main()
