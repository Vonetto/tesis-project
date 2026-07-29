"""Build the supervised user-level feature matrix for logit/ML.

The output is a reproducible id_tarjeta-level matrix assembled from already
materialized EDA artifacts. It is intentionally separate from future mobility
pattern matrices for unsupervised NMF/SVD segmentation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
BIP_ACCESS_PATH = PROJECT_ROOT / "tmp" / "audits" / "bip_load_access" / "bip_load_access_by_zona777.parquet"

SCOPE_CHOICES = ["active", "ml_2025", "interannual_ml"]
VARIANT_CHOICES = ["clean", "with_conflicts"]
HOME_FILTERS = {
    "alta": ["alta"],
    "alta_media": ["alta", "media"],
    "any": None,
}

ID_TARGET_COLS = [
    "id_tarjeta",
    "tipo_tarjeta",
    "is_qr",
    "is_qr_red",
    "is_qr_other",
    "target_conflict_flag",
]

USER_METADATA_COLS = [
    "n_viajes",
    "n_dias_activos",
    "n_semanas_activas",
    "first_trip_year",
    "last_trip_year",
    "share_trips_2025",
    "zona_hogar",
    "home_confidence",
    "home_zone_top_share",
    "n_home_dest_trips_card",
    "origin_zone_top1",
    "origin_zone_top1_share",
    "origin_zone_entropy",
    "activity_zone_top1",
    "activity_zone_top1_share",
    "activity_zone_entropy",
]

USAGE_FEATURES = [
    "share_trips_2025",
    "n_viajes",
    "n_dias_activos",
    "n_semanas_activas",
    "hora_mean",
    "hora_std",
    "share_lab_pm",
    "share_lab_pt",
    "share_no_lab",
    "share_trips_with_transfer",
    "share_trips_solo_metro",
    "share_trips_metro_bus",
]

USAGE_EXTENDED_FEATURES = [
    "share_lab_valle",
    "share_trips_solo_bus",
    "n_trasbordos_mean",
    "t_vehiculo_mean_min",
    "t_espera_ini_mean_min",
    "t_espera_trasb_mean_min",
]

SOCIO_TERRITORIAL_FEATURES = [
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
    "res_share_discapacidad_z",
    "res_share_inmigrantes_z",
    "res_share_asistencia_parv_z",
    "res_age_share_25_44",
    "res_age_share_18_24",
]

SOCIO_SENSITIVITY_FEATURES = [
    "res_prom_edad_z",
    "res_age_share_60_mas",
    "res_share_mujeres_z",
]

HOME_MACRO_FEATURES = [
    "home_macro_norte",
    "home_macro_poniente",
    "home_macro_oriente",
    "home_macro_centro",
    "home_macro_sur",
    "home_macro_suroriente",
    "home_macro_externa_especial",
]

ORIGIN_MACRO_FEATURES = [
    "origin_top1_macro_norte",
    "origin_top1_macro_poniente",
    "origin_top1_macro_oriente",
    "origin_top1_macro_centro",
    "origin_top1_macro_sur",
    "origin_top1_macro_suroriente",
    "origin_top1_macro_externa_especial",
]

SPATIAL_ML_FEATURES = [
    "home_lon",
    "home_lat",
    "origin_top1_lon",
    "origin_top1_lat",
    "origin_top2_lon",
    "origin_top2_lat",
    "activity_top1_lon",
    "activity_top1_lat",
    "activity_top2_lon",
    "activity_top2_lat",
    "origin_zone_top1_share",
    "origin_zone_entropy",
    "activity_zone_top1_share",
    "activity_zone_entropy",
]

ROUTE_CORE_FEATURES = [
    "service_route_entropy_norm",
    "service_route_early_late_rcs",
    "service_route_has_early_late_rcs",
]

ROUTE_SENSITIVITY_FEATURES = [
    "service_route_rcs_2024_2025",
    "coarse_route_entropy_norm",
    "coarse_route_early_late_rcs",
    "coarse_route_has_early_late_rcs",
    "service_within_od_top_share_weighted",
    "share_trips_in_multi_route_od",
    "service_within_od_variability_weighted",
    "top_od_service_top1_share",
    "top_od_service_entropy_norm",
]

HYBRID_FEATURES = [
    "hyb_recent_service_entropy",
    "hyb_recent_low_intensity",
    "hyb_solo2025_low_intensity",
    "hyb_recent_hora_std",
    "hyb_low_intensity_hora_std",
    "hyb_low_intensity_service_entropy",
    "hyb_oriente_educ_cont",
]

HYBRID_SENSITIVITY_FEATURES = [
    "hyb_recent_early_late_rcs",
    "hyb_oriente_early_late_rcs",
    "hyb_educ_early_late_cont",
    "hyb_oriente_high_hora_std",
]

OSM_REDUCED_FEATURES = [
    "origin_top1_osm_amenity_school_density_km2_z",
    "origin_top1_osm_amenity_university_density_km2_z",
]

OSM_WIDE_FEATURES = [
    "origin_top1_osm_leisure_playground_density_km2_z",
    "origin_top1_osm_amenity_university_density_km2_z",
    "origin_top1_osm_transport_shelter_yes_density_km2_z",
    "origin_top1_osm_railway_subway_entrance_density_km2_z",
    "activity_top1_osm_leisure_playground_density_km2_z",
    "activity_top1_osm_amenity_school_density_km2_z",
    "activity_top1_osm_amenity_university_density_km2_z",
    "activity_top1_osm_transport_shelter_yes_density_km2_z",
]

BIP_ACCESS_FEATURES = [
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

OFFER_DEMAND_FEATURES = [
    "offer_log_demand_origin_franja_mean",
    "offer_log_bus_stop_density_origin_mean",
    "offer_log_metro_station_density_origin_mean",
    "offer_origin_bus_like_share",
    "offer_origin_metro_like_share",
    "offer_bus_origin_headway_all_min_mean",
    "offer_bus_origin_headway_ge10_share",
]

RHYTHM_FEATURES = [
    "rhythm_trips_per_active_day",
    "rhythm_trips_per_active_week",
    "rhythm_active_weeks_rate_scope",
    "rhythm_active_day_density_span",
    "rhythm_trips_per_span_day",
    "rhythm_activity_top1_day_share",
    "rhythm_activity_top2_day_share",
    "rhythm_daily_hhi",
    "rhythm_daily_entropy_norm",
    "rhythm_daily_burstiness",
    "rhythm_single_trip_day_share",
    "rhythm_has_gap",
    "rhythm_n_gap_days",
    "rhythm_median_gap_active_days",
    "rhythm_mean_gap_active_days",
    "rhythm_max_gap_active_days",
    "rhythm_weekly_top1_share",
    "rhythm_weekly_hhi",
    "rhythm_weekly_entropy_norm",
    "rhythm_weekly_burstiness",
]

RHYTHM_LOGIT_FEATURES = [
    "rhythm_mean_gap_active_days",
    "rhythm_trips_per_span_day",
    "rhythm_active_day_density_span",
    "rhythm_trips_per_active_week",
    "rhythm_daily_hhi",
    "rhythm_has_gap",
]

CONTEXT_MIN_GROUP_CARDS = 200

CONTEXT_RESIDUAL_MAIN_FEATURES = [
    "ctx_mean_gap_active_days_home_zone_resid",
    "ctx_active_day_density_home_zone_resid",
    "ctx_n_viajes_home_zone_pctile",
    "ctx_hora_std_home_zone_resid",
]

CONTEXT_RESIDUAL_SENSITIVITY_FEATURES = [
    "ctx_service_route_entropy_origin_zone_resid",
    "ctx_qr_like_behavior_residual_score",
]

CONTEXT_RESIDUAL_FEATURES = CONTEXT_RESIDUAL_MAIN_FEATURES + CONTEXT_RESIDUAL_SENSITIVITY_FEATURES

ROUTINE_MAIN_FEATURES = [
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
]

ROUTINE_SELECTED_MAIN_FEATURES = [
    "routine_lab_peak_share",
    "routine_commute_like_score",
    "routine_od_time_n_unique",
    "routine_od_time_entropy_norm",
    "routine_zone_n_unique",
]

DAILY_TOUR_MAIN_FEATURES = [
    "tour_last_trip_hour_mean",
    "tour_last_trip_lab_pm_peak_share",
    "tour_day_span_hours_mean",
    "tour_peak_anchor_day_share",
    "tour_workday_commute_like_day_share",
    "tour_first_trip_lab_am_peak_share",
    "tour_complex_day_share",
    "tour_mixed_mode_day_share",
]

ECOLOGY_MAIN_FEATURES = [
    # adoption_ecology_pack v2: penetracion QR por zona como agregado SIMPLE
    # (sin leave-one-out: la v1 LOO filtraba el target intra-zona; run
    # 7770b888 invalido). Valor constante por zona -> sin leakage individual.
    # CAVEAT: transductivo (targets del universo completo, diluidos 1/n);
    # para reporte final recalcular dentro de folds.
    "eco_qr_share_home_zone_smooth",
    "eco_qr_red_share_home_zone_smooth",
    "eco_home_zone_n_cards_log",
    "eco_qr_share_origin_top1_smooth",
    "eco_qr_red_share_origin_top1_smooth",
    "eco_origin_top1_n_cards_log",
]

SEQ_REPEAT_MAIN_FEATURES = [
    # sequence_repeat_pack (paso 1, 2026-06-13): repeticion dia-a-dia del
    # patron OD+hora (Jaccard entre dias comparables, mismo dia de semana,
    # <=14 dias de diferencia). n_pairs/n_active_days dan contexto de
    # confiabilidad del share (muchas tarjetas tienen 0 pares).
    "seq_day_repeat_share",
    "seq_day_repeat_n_pairs",
    "seq_day_repeat_n_active_days",
]

# sequence_embedding_pack (Etapa B, 2026-06-13): componentes NMF sobre la
# matriz tarjeta x top-300 bigramas de tokens de viaje (macro_origen,
# macro_destino, banda_horaria, modo_coarse). Tres variantes por numero de
# componentes (k=10/15/20); Etapa C decide via benchmark cual (si alguna)
# se incluye en un feature set definitivo.
SEQ_EMBED_K10_FEATURES = [f"nmf_seq_k10_c{j}" for j in range(10)]
SEQ_EMBED_K15_FEATURES = [f"nmf_seq_k15_c{j}" for j in range(15)]
SEQ_EMBED_K20_FEATURES = [f"nmf_seq_k20_c{j}" for j in range(20)]

FRICTION_MAIN_FEATURES = [
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

ADOPTION_TIMING_MAIN_FEATURES = [
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

PROTOTYPE_MAIN_FEATURES = [
    "proto_commuter_peak_score",
    "proto_late_return_score",
    "proto_low_complexity_score",
    "proto_explorer_score",
    "proto_routine_repeater_score",
    "proto_multimodal_score",
]


def panel_path(scope: str, variant: str) -> Path:
    return USER_DIR / f"user_level_payment_panel_{scope}_{variant}.parquet"


def route_path(scope: str) -> Path:
    return USER_DIR / f"user_route_inertia_{scope}.parquet"


def offer_path(scope: str) -> Path:
    return USER_DIR / f"user_offer_demand_exposure_{scope}.parquet"


def rhythm_path(scope: str) -> Path:
    return USER_DIR / f"user_behavior_rhythm_features_{scope}.parquet"


def routine_path(scope: str) -> Path:
    return USER_DIR / f"user_behavior_routine_features_{scope}.parquet"


def daily_tour_path(scope: str) -> Path:
    return USER_DIR / f"user_behavior_daily_tour_features_{scope}.parquet"


def adoption_timing_path(scope: str) -> Path:
    return USER_DIR / f"user_behavior_adoption_timing_features_{scope}.parquet"


def prototype_path(scope: str) -> Path:
    return USER_DIR / f"user_behavior_prototype_features_{scope}.parquet"


def ecology_path(scope: str) -> Path:
    return USER_DIR / f"user_adoption_ecology_features_{scope}.parquet"


def sequence_repeat_path(scope: str) -> Path:
    return USER_DIR / f"user_sequence_repeat_features_{scope}.parquet"


def sequence_embedding_path(scope: str, k: int) -> Path:
    return USER_DIR / f"user_sequence_embedding_features_k{k}_{scope}.parquet"


def age_path() -> Path:
    return USER_DIR / "censo_age_bands_zona777.parquet"


def universe_suffix(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> str:
    suffix = f"{scope}_{variant}_{home_filter}_n{min_trips}"
    if min_home_trips > 0:
        suffix += f"_home{min_home_trips}"
    return suffix


def output_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> Path:
    return USER_DIR / f"user_model_matrix_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.parquet"


def feature_sets_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> Path:
    return USER_DIR / f"user_model_matrix_feature_sets_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.json"


def audit_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int, stem: str) -> Path:
    return USER_DIR / f"user_model_matrix_{stem}_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.csv"


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def assert_exists(paths: Iterable[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Faltan artefactos requeridos: {missing}")


def check_unique_key(path: Path, key: str) -> None:
    check = (
        pl.scan_parquet(path)
        .select([pl.len().alias("n_rows"), pl.col(key).n_unique().alias("n_unique")])
        .collect()
    )
    n_rows = check.item(0, "n_rows")
    n_unique = check.item(0, "n_unique")
    if n_rows != n_unique:
        raise ValueError(f"{path.name}: {key} no es unico ({n_unique} de {n_rows})")


def bip_access_for_join(zone_col: str, prefix: str) -> pl.LazyFrame:
    return (
        pl.scan_parquet(BIP_ACCESS_PATH)
        .select(
            [
                "ZONA777",
                "bip_load_n_points_zone",
                "bip_load_has_point_zone",
                "bip_load_density_km2",
                "bip_load_dist_nearest_m",
            ]
        )
        .rename(
            {
                "ZONA777": zone_col,
                "bip_load_n_points_zone": f"{prefix}_bip_load_n_points_zone",
                "bip_load_has_point_zone": f"{prefix}_bip_load_has_point_zone",
                "bip_load_density_km2": f"{prefix}_bip_load_density_km2",
                "bip_load_dist_nearest_m": f"{prefix}_bip_load_dist_nearest_m",
            }
        )
    )


def age_bands_for_residence() -> pl.LazyFrame:
    return (
        pl.scan_parquet(age_path())
        .select(
            [
                "ZONA777",
                "share_edad_18_24",
                "share_edad_25_44",
                "share_edad_45_59",
                "share_edad_60_mas",
                "share_edad_18_44",
            ]
        )
        .rename(
            {
                "ZONA777": "zona_hogar",
                "share_edad_18_24": "res_age_share_18_24",
                "share_edad_25_44": "res_age_share_25_44",
                "share_edad_45_59": "res_age_share_45_59",
                "share_edad_60_mas": "res_age_share_60_mas",
                "share_edad_18_44": "res_age_share_18_44",
            }
        )
    )


def build_base_lf(
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
) -> tuple[pl.LazyFrame, dict]:
    panel = panel_path(scope, variant)
    route = route_path(scope)
    offer = offer_path(scope)
    rhythm = rhythm_path(scope)
    routine = routine_path(scope)
    daily_tour = daily_tour_path(scope)
    adoption_timing = adoption_timing_path(scope)
    prototype = prototype_path(scope)
    ecology = ecology_path(scope)
    sequence_repeat = sequence_repeat_path(scope)
    sequence_embed_k10 = sequence_embedding_path(scope, 10)
    sequence_embed_k15 = sequence_embedding_path(scope, 15)
    sequence_embed_k20 = sequence_embedding_path(scope, 20)
    assert_exists([panel, route, offer, rhythm, BIP_ACCESS_PATH, age_path()])
    for path in [panel, route, offer, rhythm]:
        check_unique_key(path, "id_tarjeta")
    if routine.exists():
        check_unique_key(routine, "id_tarjeta")
    if daily_tour.exists():
        check_unique_key(daily_tour, "id_tarjeta")
    if adoption_timing.exists():
        check_unique_key(adoption_timing, "id_tarjeta")
    if prototype.exists():
        check_unique_key(prototype, "id_tarjeta")
    if ecology.exists():
        check_unique_key(ecology, "id_tarjeta")
    if sequence_repeat.exists():
        check_unique_key(sequence_repeat, "id_tarjeta")
    for sequence_embed in [sequence_embed_k10, sequence_embed_k15, sequence_embed_k20]:
        if sequence_embed.exists():
            check_unique_key(sequence_embed, "id_tarjeta")
    check_unique_key(BIP_ACCESS_PATH, "ZONA777")
    check_unique_key(age_path(), "ZONA777")

    lf = pl.scan_parquet(panel)
    if variant == "with_conflicts":
        lf = lf.filter(pl.col("target_conflict_flag") == 0)
    lf = lf.filter(pl.col("n_viajes") >= min_trips)
    if min_home_trips > 0:
        lf = lf.filter(pl.col("n_home_dest_trips_card") >= min_home_trips)
    home_values = HOME_FILTERS[home_filter]
    if home_values is not None:
        lf = lf.filter(pl.col("home_confidence").is_in(home_values))

    lf = (
        lf.join(pl.scan_parquet(route), on="id_tarjeta", how="left")
        .join(pl.scan_parquet(offer), on="id_tarjeta", how="left")
        .join(pl.scan_parquet(rhythm), on="id_tarjeta", how="left")
        .join(bip_access_for_join("zona_hogar", "home"), on="zona_hogar", how="left")
        .join(bip_access_for_join("origin_zone_top1", "origin_top1"), on="origin_zone_top1", how="left")
        .join(bip_access_for_join("activity_zone_top1", "activity_top1"), on="activity_zone_top1", how="left")
        .join(age_bands_for_residence(), on="zona_hogar", how="left")
    )
    if routine.exists():
        lf = lf.join(pl.scan_parquet(routine), on="id_tarjeta", how="left")
    if daily_tour.exists():
        lf = lf.join(pl.scan_parquet(daily_tour), on="id_tarjeta", how="left")
    if adoption_timing.exists():
        lf = lf.join(pl.scan_parquet(adoption_timing), on="id_tarjeta", how="left")
    if prototype.exists():
        lf = lf.join(pl.scan_parquet(prototype), on="id_tarjeta", how="left")
    if ecology.exists():
        # adoption_ecology_pack incluye columnas raw de auditoria; al
        # modelo solo entran las de ECOLOGY_MAIN_FEATURES via feature set.
        lf = lf.join(
            pl.scan_parquet(ecology).select(["id_tarjeta"] + ECOLOGY_MAIN_FEATURES),
            on="id_tarjeta",
            how="left",
        )
    if sequence_repeat.exists():
        lf = lf.join(
            pl.scan_parquet(sequence_repeat).select(["id_tarjeta"] + SEQ_REPEAT_MAIN_FEATURES),
            on="id_tarjeta",
            how="left",
        )
    for sequence_embed, embed_features in (
        (sequence_embed_k10, SEQ_EMBED_K10_FEATURES),
        (sequence_embed_k15, SEQ_EMBED_K15_FEATURES),
        (sequence_embed_k20, SEQ_EMBED_K20_FEATURES),
    ):
        if sequence_embed.exists():
            lf = lf.join(
                pl.scan_parquet(sequence_embed).select(["id_tarjeta"] + embed_features),
                on="id_tarjeta",
                how="left",
            )

    return lf, {}


def null_if_small_group(expr: pl.Expr, group_count_col: str, group_key_col: str) -> pl.Expr:
    return (
        pl.when(
            (pl.col(group_count_col) >= CONTEXT_MIN_GROUP_CARDS)
            & pl.col(group_key_col).is_not_null()
        )
        .then(expr)
        .otherwise(pl.lit(None, dtype=pl.Float64))
    )


def global_z_score(col: str, *, sign: float = 1.0) -> pl.Expr:
    denom = pl.when(pl.col(col).std() == 0).then(None).otherwise(pl.col(col).std())
    return sign * ((pl.col(col) - pl.col(col).mean()) / denom)


def nonnegative(col: str) -> pl.Expr:
    return pl.when(pl.col(col) < 0).then(0.0).otherwise(pl.col(col))


def log1p_nonnegative(col: str) -> pl.Expr:
    return nonnegative(col).log1p()


def nonnegative_weight(col: str) -> pl.Expr:
    return (
        pl.when(pl.col(col).is_null() | (pl.col(col) < 0))
        .then(0.0)
        .otherwise(pl.col(col))
    )


def add_derived_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    home_w = nonnegative_weight("home_zone_top_share")
    origin_w = nonnegative_weight("origin_zone_top1_share")
    activity_w = nonnegative_weight("activity_zone_top1_share")
    bip_access_weight_sum = home_w + origin_w + activity_w
    weighted_bip_dist_log = (
        home_w * log1p_nonnegative("home_bip_load_dist_nearest_m")
        + origin_w * log1p_nonnegative("origin_top1_bip_load_dist_nearest_m")
        + activity_w * log1p_nonnegative("activity_top1_bip_load_dist_nearest_m")
    ) / bip_access_weight_sum
    weighted_bip_density = (
        home_w * nonnegative("home_bip_load_density_km2")
        + origin_w * nonnegative("origin_top1_bip_load_density_km2")
        + activity_w * nonnegative("activity_top1_bip_load_density_km2")
    ) / bip_access_weight_sum
    return (
        lf.with_columns(
            [
                (pl.col("share_trips_2025") >= 0.75).cast(pl.Int8).alias("recent_majority_2025"),
                (pl.col("share_trips_2025") >= 0.999).cast(pl.Int8).alias("solo_2025"),
                pl.col("n_viajes").is_between(3, 9, closed="both").cast(pl.Int8).alias("low_intensity_3_9"),
                (
                    (pl.col("home_macro_oriente") == 1)
                    | (pl.col("origin_top1_macro_oriente") == 1)
                )
                .cast(pl.Int8)
                .alias("oriente_res_or_origin"),
            ]
        )
        .with_columns(
            [
                (pl.col("recent_majority_2025") * pl.col("low_intensity_3_9")).alias(
                    "hyb_recent_low_intensity"
                ),
                (pl.col("solo_2025") * pl.col("low_intensity_3_9")).alias("hyb_solo2025_low_intensity"),
                (pl.col("recent_majority_2025") * pl.col("hora_std")).alias("hyb_recent_hora_std"),
                (pl.col("low_intensity_3_9") * pl.col("hora_std")).alias("hyb_low_intensity_hora_std"),
                (pl.col("recent_majority_2025") * pl.col("service_route_entropy_norm")).alias(
                    "hyb_recent_service_entropy"
                ),
                (pl.col("low_intensity_3_9") * pl.col("service_route_entropy_norm")).alias(
                    "hyb_low_intensity_service_entropy"
                ),
                (pl.col("recent_majority_2025") * pl.col("service_route_early_late_rcs")).alias(
                    "hyb_recent_early_late_rcs"
                ),
                (pl.col("oriente_res_or_origin") * pl.col("service_route_early_late_rcs")).alias(
                    "hyb_oriente_early_late_rcs"
                ),
                (
                    pl.col("res_share_cine18_universitaria_o_mas_micro_z")
                    * pl.col("service_route_early_late_rcs")
                ).alias(
                    "hyb_educ_early_late_cont"
                ),
                (
                    pl.col("oriente_res_or_origin")
                    * pl.col("res_share_cine18_universitaria_o_mas_micro_z")
                ).alias(
                    "hyb_oriente_educ_cont"
                ),
                (pl.col("oriente_res_or_origin") * pl.col("hora_std")).alias("hyb_oriente_high_hora_std"),
            ]
        )
        .with_columns(
            [
                pl.when(bip_access_weight_sum > 0)
                .then(weighted_bip_dist_log)
                .otherwise(pl.lit(None, dtype=pl.Float64))
                .alias("fric_weighted_bip_dist_log"),
                pl.when(bip_access_weight_sum > 0)
                .then(1.0 / (1.0 + weighted_bip_density))
                .otherwise(pl.lit(None, dtype=pl.Float64))
                .alias("fric_weighted_bip_density_inv"),
            ]
        )
        .with_columns(
            [
                (pl.col("fric_weighted_bip_dist_log") * pl.col("share_trips_solo_bus")).alias(
                    "fric_weighted_bip_dist_x_solo_bus"
                ),
                (pl.col("fric_weighted_bip_dist_log") * pl.col("low_intensity_3_9")).alias(
                    "fric_weighted_bip_dist_x_low_intensity"
                ),
                (
                    pl.col("fric_weighted_bip_dist_log")
                    * (1.0 - pl.col("rhythm_active_day_density_span"))
                ).alias("fric_weighted_bip_dist_x_low_active_density"),
                (pl.col("fric_weighted_bip_density_inv") * pl.col("share_trips_solo_bus")).alias(
                    "fric_weighted_bip_density_inv_x_solo_bus"
                ),
                (
                    (pl.col("home_bip_load_n_points_zone").fill_null(0) == 0).cast(pl.Int8)
                    * pl.col("share_trips_solo_bus")
                ).alias("fric_home_no_bip_points_x_solo_bus"),
                (
                    log1p_nonnegative("home_bip_load_dist_nearest_m")
                    * pl.col("share_trips_solo_bus")
                ).alias("fric_home_bip_dist_x_solo_bus"),
                (
                    pl.col("offer_origin_bus_like_share")
                    * pl.col("fric_weighted_bip_dist_log")
                ).alias("fric_origin_bus_like_x_weighted_bip_dist"),
                (
                    pl.col("offer_origin_metro_like_share")
                    * pl.col("fric_weighted_bip_density_inv")
                ).alias("fric_metro_like_x_weighted_bip_density_inv"),
                (
                    pl.col("fric_weighted_bip_dist_log")
                    * (pl.col("share_lab_pm").fill_null(0.0) + pl.col("share_lab_pt").fill_null(0.0))
                ).alias("fric_weighted_bip_dist_x_peak_share"),
            ]
        )
        .with_columns(
            [
                pl.len().over("zona_hogar").alias("ctx_home_zone_n_cards"),
                pl.len().over("origin_zone_top1").alias("ctx_origin_zone_n_cards"),
            ]
        )
        .with_columns(
            [
                null_if_small_group(
                    pl.col("n_viajes").rank("average").over("zona_hogar")
                    / pl.col("ctx_home_zone_n_cards"),
                    "ctx_home_zone_n_cards",
                    "zona_hogar",
                ).alias("ctx_n_viajes_home_zone_pctile"),
                null_if_small_group(
                    pl.col("hora_std") - pl.col("hora_std").median().over("zona_hogar"),
                    "ctx_home_zone_n_cards",
                    "zona_hogar",
                ).alias("ctx_hora_std_home_zone_resid"),
                null_if_small_group(
                    pl.col("rhythm_mean_gap_active_days")
                    - pl.col("rhythm_mean_gap_active_days").median().over("zona_hogar"),
                    "ctx_home_zone_n_cards",
                    "zona_hogar",
                ).alias("ctx_mean_gap_active_days_home_zone_resid"),
                null_if_small_group(
                    pl.col("rhythm_active_day_density_span")
                    - pl.col("rhythm_active_day_density_span").median().over("zona_hogar"),
                    "ctx_home_zone_n_cards",
                    "zona_hogar",
                ).alias("ctx_active_day_density_home_zone_resid"),
                null_if_small_group(
                    pl.col("service_route_entropy_norm")
                    - pl.col("service_route_entropy_norm").median().over("origin_zone_top1"),
                    "ctx_origin_zone_n_cards",
                    "origin_zone_top1",
                ).alias("ctx_service_route_entropy_origin_zone_resid"),
            ]
        )
        .with_columns(
            [
                (
                    global_z_score("ctx_n_viajes_home_zone_pctile", sign=-1.0)
                    + global_z_score("ctx_hora_std_home_zone_resid")
                    + global_z_score("ctx_mean_gap_active_days_home_zone_resid")
                    + global_z_score("ctx_service_route_entropy_origin_zone_resid")
                    + global_z_score("ctx_active_day_density_home_zone_resid", sign=-1.0)
                ).alias("ctx_qr_like_behavior_residual_score")
            ]
        )
    )


def raw_feature_sets() -> dict[str, list[str]]:
    socio_macro = SOCIO_TERRITORIAL_FEATURES + HOME_MACRO_FEATURES + ORIGIN_MACRO_FEATURES
    logit_main = USAGE_FEATURES + socio_macro + ROUTE_CORE_FEATURES
    ml_main = (
        USAGE_FEATURES
        + USAGE_EXTENDED_FEATURES
        + socio_macro
        + ROUTE_CORE_FEATURES
        + HYBRID_FEATURES
        + OSM_REDUCED_FEATURES
    )
    ml_wide = (
        USAGE_FEATURES
        + USAGE_EXTENDED_FEATURES
        + SOCIO_TERRITORIAL_FEATURES
        + SOCIO_SENSITIVITY_FEATURES
        + HOME_MACRO_FEATURES
        + ORIGIN_MACRO_FEATURES
        + SPATIAL_ML_FEATURES
        + ROUTE_CORE_FEATURES
        + ROUTE_SENSITIVITY_FEATURES
        + HYBRID_FEATURES
        + HYBRID_SENSITIVITY_FEATURES
        + OSM_REDUCED_FEATURES
        + OSM_WIDE_FEATURES
        + BIP_ACCESS_FEATURES
        + OFFER_DEMAND_FEATURES
    )
    binary_ml_main = USAGE_FEATURES + socio_macro + ROUTE_CORE_FEATURES + HYBRID_FEATURES
    binary_ml_wide = (
        USAGE_FEATURES
        + USAGE_EXTENDED_FEATURES
        + socio_macro
        + SOCIO_SENSITIVITY_FEATURES
        + ROUTE_CORE_FEATURES
        + ROUTE_SENSITIVITY_FEATURES
        + HYBRID_FEATURES
        + HYBRID_SENSITIVITY_FEATURES
        + OSM_REDUCED_FEATURES
        + OSM_WIDE_FEATURES
        + BIP_ACCESS_FEATURES
        + OFFER_DEMAND_FEATURES
    )
    return {
        "logit_main": logit_main,
        "logit_plus_rhythm": logit_main + RHYTHM_LOGIT_FEATURES,
        "logit_plus_rhythm_context_residual": (
            logit_main + RHYTHM_LOGIT_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES
        ),
        "logit_plus_rhythm_context_residual_sensitivity": (
            logit_main + RHYTHM_LOGIT_FEATURES + CONTEXT_RESIDUAL_FEATURES
        ),
        "logit_sensitivity_age60": logit_main + ["res_age_share_60_mas"],
        "logit_sensitivity_mean_age": logit_main + ["res_prom_edad_z"],
        "logit_sensitivity_route_hybrid": logit_main + HYBRID_FEATURES,
        "ml_main": ml_main,
        "ml_plus_rhythm": ml_main + RHYTHM_FEATURES,
        "ml_plus_rhythm_context_residual": ml_main + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES,
        "ml_wide": ml_wide,
        "full_plus_rhythm": ml_wide + RHYTHM_FEATURES,
        "full_plus_rhythm_context_residual": ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES,
        "full_plus_rhythm_context_residual_sensitivity": (
            ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_FEATURES
        ),
        "full_plus_rhythm_context_adoption_timing": (
            ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES + ADOPTION_TIMING_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_prototype": (
            ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES + PROTOTYPE_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_friction": (
            ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES + FRICTION_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine": (
            ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES + ROUTINE_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_adoption_timing": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + ADOPTION_TIMING_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_prototype": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + PROTOTYPE_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_friction": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + FRICTION_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_ecology": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + ECOLOGY_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_seq_repeat": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + SEQ_REPEAT_MAIN_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_seq_embed_k10": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + SEQ_EMBED_K10_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_seq_embed_k15": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + SEQ_EMBED_K15_FEATURES
        ),
        "full_plus_rhythm_context_routine_daily_tour_seq_embed_k20": (
            ml_wide
            + RHYTHM_FEATURES
            + CONTEXT_RESIDUAL_MAIN_FEATURES
            + ROUTINE_SELECTED_MAIN_FEATURES
            + DAILY_TOUR_MAIN_FEATURES
            + SEQ_EMBED_K20_FEATURES
        ),
        "binary_ml_main": binary_ml_main,
        "binary_ml_plus_rhythm": binary_ml_main + RHYTHM_FEATURES,
        "binary_ml_plus_rhythm_context_residual": (
            binary_ml_main + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES
        ),
        "binary_ml_wide": binary_ml_wide,
    }


def dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def materialize_matrix(
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    *,
    force: bool,
) -> Path:
    out_path = output_path(scope, variant, home_filter, min_trips, min_home_trips)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    lf, preprocessing_stats = build_base_lf(scope, variant, home_filter, min_trips, min_home_trips)
    lf = add_derived_features(lf)
    schema = set(lf.collect_schema().names())

    requested_sets = raw_feature_sets()
    available_sets = {
        name: dedupe([feature for feature in features if feature in schema])
        for name, features in requested_sets.items()
    }
    missing_sets = {
        name: [feature for feature in dedupe(features) if feature not in schema]
        for name, features in requested_sets.items()
    }

    feature_cols = dedupe(feature for features in available_sets.values() for feature in features)
    metadata_cols = [c for c in USER_METADATA_COLS if c in schema]
    select_cols = dedupe(ID_TARGET_COLS + metadata_cols + feature_cols)

    matrix = collect_streaming(lf.select(select_cols))
    n_rows = matrix.height
    n_unique = matrix.select(pl.col("id_tarjeta").n_unique()).item()
    if n_rows != n_unique:
        raise ValueError(f"Matriz tiene id_tarjeta duplicadas: {n_unique} unicas vs {n_rows} filas")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    matrix.write_parquet(out_path, compression="zstd")

    write_audits(
        matrix,
        scope=scope,
        variant=variant,
        home_filter=home_filter,
        min_trips=min_trips,
        min_home_trips=min_home_trips,
        feature_cols=feature_cols,
    )
    write_feature_sets(
        scope=scope,
        variant=variant,
        home_filter=home_filter,
        min_trips=min_trips,
        min_home_trips=min_home_trips,
        preprocessing_stats=preprocessing_stats,
        available_sets=available_sets,
        missing_sets=missing_sets,
        output=out_path,
    )

    print(f"OK: {out_path}")
    print(f"rows={n_rows:,} cols={len(matrix.columns):,}")
    return out_path


def write_audits(
    matrix: pl.DataFrame,
    *,
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    feature_cols: list[str],
) -> None:
    n_rows = matrix.height
    target = (
        matrix.group_by("tipo_tarjeta")
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("n_viajes").sum().alias("n_trips"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_cards") / n_rows).alias("card_share"),
                (pl.col("n_trips") / pl.col("n_trips").sum()).alias("trip_share"),
            ]
        )
        .sort("tipo_tarjeta")
    )
    target.write_csv(audit_path(scope, variant, home_filter, min_trips, min_home_trips, "target_distribution"))

    summary = pl.DataFrame(
        [
            {"metric": "scope", "value": scope},
            {"metric": "variant", "value": variant},
            {"metric": "home_filter", "value": home_filter},
            {"metric": "min_trips", "value": str(min_trips)},
            {"metric": "min_home_trips", "value": str(min_home_trips)},
            {"metric": "n_cards", "value": str(n_rows)},
            {"metric": "n_features", "value": str(len(feature_cols))},
            {"metric": "n_cols", "value": str(len(matrix.columns))},
            {"metric": "n_duplicate_id_tarjeta", "value": str(n_rows - matrix["id_tarjeta"].n_unique())},
            {"metric": "qr_share", "value": f"{matrix['is_qr'].mean():.8f}"},
            {"metric": "qr_red_share", "value": f"{matrix['is_qr_red'].mean():.8f}"},
            {"metric": "qr_other_share", "value": f"{matrix['is_qr_other'].mean():.8f}"},
        ]
    )
    summary.write_csv(audit_path(scope, variant, home_filter, min_trips, min_home_trips, "summary"))

    missing = matrix.select([pl.col(c).is_null().sum().alias(c) for c in feature_cols])
    missing_long = (
        missing.transpose(include_header=True, header_name="feature", column_names=["n_missing"])
        .with_columns((pl.col("n_missing") / n_rows).alias("missing_rate"))
        .sort("missing_rate", descending=True)
    )
    missing_long.write_csv(audit_path(scope, variant, home_filter, min_trips, min_home_trips, "feature_missing"))


def write_feature_sets(
    *,
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    preprocessing_stats: dict,
    available_sets: dict[str, list[str]],
    missing_sets: dict[str, list[str]],
    output: Path,
) -> None:
    payload = {
        "scope": scope,
        "variant": variant,
        "home_filter": home_filter,
        "min_trips": min_trips,
        "min_home_trips": min_home_trips,
        "universe": (
            f"{variant} + home_{home_filter} + n_viajes>={min_trips}"
            + (f" + n_home_dest_trips_card>={min_home_trips}" if min_home_trips > 0 else "")
        ),
        "output_path": str(output),
        "preprocessing_contract": (
            "Feature sets generally contain raw or fixed-rule variables only. "
            "Imputation, scaling, winsorization, and quantile-derived flags "
            "must be fitted inside the train/CV pipeline to avoid test-set leakage. "
            "Feature sets with context_residual are exploratory: they use "
            "universe-level group ranks/medians in this matrix and should be "
            "reimplemented fold-safe before final reporting."
        ),
        "precomputed_distribution_stats": {
            k: float(v) if v is not None else None
            for k, v in preprocessing_stats.items()
        },
        "metadata_columns": USER_METADATA_COLS,
        "feature_sets": available_sets,
        "missing_features": missing_sets,
    }
    feature_sets_path(scope, variant, home_filter, min_trips, min_home_trips).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=SCOPE_CHOICES, default="interannual_ml")
    parser.add_argument("--variant", choices=VARIANT_CHOICES, default="clean")
    parser.add_argument("--home-filter", choices=sorted(HOME_FILTERS), default="alta")
    parser.add_argument("--min-trips", type=int, default=3)
    parser.add_argument("--min-home-trips", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    materialize_matrix(
        scope=args.scope,
        variant=args.variant,
        home_filter=args.home_filter,
        min_trips=args.min_trips,
        min_home_trips=args.min_home_trips,
        force=args.force,
    )


if __name__ == "__main__":
    main()
