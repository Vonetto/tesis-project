from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "02_eda" / "eda_qr_vs_bip_profiles.qmd"


def cell_source(label: str) -> str:
    text = NOTEBOOK_PATH.read_text(encoding="utf-8")
    match = re.search(
        rf"```\{{python\}}\n#\| label: {re.escape(label)}\n(.*?)\n```",
        text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"No se encontro la celda {label}")
    return match.group(1)


class OperationalNotebookContractTest(unittest.TestCase):
    def test_initial_report_figures_use_larger_title_subtitle_gap(self) -> None:
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")
        title_helper = notebook.split(
            "def add_figure_title(",
            maxsplit=1,
        )[1].split("def payment_legend_handles(", maxsplit=1)[0]
        composition_plot = notebook.split(
            "def plot_composition_donuts(",
            maxsplit=1,
        )[1].split("def plot_intensity_dumbbells(", maxsplit=1)[0]
        intensity_percentile_plot = notebook.split(
            "def plot_intensity_percentile_profiles(",
            maxsplit=1,
        )[1].split("def plot_regularidad_ecdf(", maxsplit=1)[0]
        cohort_plot = notebook.split(
            "def plot_cohort_stacked_bars(",
            maxsplit=1,
        )[1].split("def plot_segmented_bars(", maxsplit=1)[0]

        self.assertTrue(
            "subtitle_gap: float = 0.055" in title_helper,
            "add_figure_title debe exponer subtitle_gap con default compacto",
        )
        self.assertTrue(
            "subtitle_gap=0.08" in composition_plot,
            "plot_composition_donuts debe separar mas titulo y subtitulo",
        )
        self.assertTrue(
            "subtitle_gap=0.08" in intensity_percentile_plot,
            "plot_intensity_percentile_profiles debe separar mas titulo y subtitulo",
        )
        self.assertTrue(
            "subtitle_gap=0.08" in cohort_plot,
            "plot_cohort_stacked_bars debe separar mas titulo y subtitulo",
        )

    def test_regularity_threshold_heatmap_uses_larger_title_subtitle_gap(
        self,
    ) -> None:
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")
        regularity_threshold_heatmap = notebook.split(
            "def plot_regularity_threshold_heatmap(",
            maxsplit=1,
        )[1].split("def plot_timing_density(", maxsplit=1)[0]

        self.assertTrue(
            "subtitle_gap=0.08" in regularity_threshold_heatmap,
            "plot_regularity_threshold_heatmap debe separar mas titulo y subtitulo",
        )

    def test_13b_documents_absolute_and_normalized_stop_density(self) -> None:
        source = cell_source("block13b-operational-variable-definitions")
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn(
            '"variable": "op_bus_stops_with_supply_zone_franja_density_km2_mean"',
            source,
        )
        self.assertIn('"familia": "Densidad bus zonal normalizada"', source)
        self.assertNotIn('"familia": "Extension bus zonal normalizada"', source)
        self.assertRegex(
            notebook,
            r"La comparacion de 13D confirma que\s+leave-one-card-out",
        )
        self.assertNotIn(
            "Antes de tratarla como contexto externo se debera comparar",
            notebook,
        )

    def test_13c_covers_new_supports_and_explains_trip_difference(self) -> None:
        source = cell_source("block13c-operational-accounting-sanity")

        self.assertIn("op_bus_stops_density_context_trip_share", source)
        self.assertIn(
            "op_bus_stops_with_supply_zone_franja_density_percentile_mean",
            source,
        )
        self.assertIn(
            "op_stop_bus_supply_buses_h_observed_percentile_mean",
            source,
        )
        self.assertIn("Viajes excluidos por zona de origen nula", source)
        self.assertIn(
            "Las filas extra de oferta son combinaciones validas sin demanda observada.",
            source,
        )
        self.assertIn(
            "Afecta la asignacion zonal de oferta, no el matching paradero-hora.",
            source,
        )

    def test_13d_compares_stop_hour_normalization_and_updates_density_decision(
        self,
    ) -> None:
        source = cell_source("block13d-operational-measurement-validity")

        self.assertIn(
            'comparison="Oferta paradero-hora: raw vs percentil semana-franja"',
            source,
        )
        self.assertIn('"dimension": "Densidad de paraderos activos"', source)
        self.assertIn(
            "El conteo raw queda como diagnostico; usar paraderos activos por km2",
            source,
        )

    def test_13i_separates_bus_demand_from_observed_pressure(self) -> None:
        definitions = cell_source(
            "block13i-operational-bus-demand-definitions"
        )
        accounting = cell_source(
            "block13i-operational-bus-demand-accounting"
        )
        plausibility = cell_source(
            "block13i-operational-bus-demand-plausibility"
        )

        self.assertIn("cada etapa de subida", NOTEBOOK_PATH.read_text())
        self.assertIn(
            "op_bus_demand_boardings_excl_card_*_boarding_weighted_mean",
            definitions,
        )
        self.assertIn(
            "excl_card_zone_hour_*_weighted_mean",
            definitions,
        )
        self.assertIn("igual peso por celda", definitions)
        self.assertIn("demanda total de la celda", definitions)
        self.assertIn("No mide", definitions.replace("no_mide", "No mide"))
        self.assertIn("frequency_supply_share_mapped", accounting)
        self.assertIn("OP_BUS_UNMAPPED_SUPPLY_STOPS_PATH", accounting)
        self.assertIn("Percentiles dentro de [0,1]", accounting)
        self.assertIn("share_change_quintile", plausibility)
        self.assertIn("spearman_demand_pressure", plausibility)

    def test_13j_audits_extremes_and_rank_stability_at_two_scales(
        self,
    ) -> None:
        definitions = cell_source(
            "block13j-operational-bus-extremes-stability-definitions"
        )
        extremes = cell_source(
            "block13j-operational-bus-recurrent-extremes"
        )
        stability = cell_source(
            "block13j-operational-bus-ranking-stability"
        )
        normalization = cell_source(
            "block13j-operational-bus-normalization-sensitivity"
        )

        self.assertIn("ZONA777-semana-franja", definitions)
        self.assertIn("Paradero-hora-semana", definitions)
        self.assertIn("aggregate_stop_hour_week", definitions)
        self.assertIn("Relacion demanda-oferta observada", definitions)
        self.assertIn("summarize_recurrent_extremes", extremes)
        self.assertIn("op_bus_supply_match_share_stop_hour_week", extremes)
        self.assertIn("demand_component", extremes)
        self.assertIn("supply_component", extremes)
        self.assertIn("summarize_rank_stability", stability)
        self.assertIn("share_change_quintile", stability)
        self.assertIn(
            "misma semana entre 2024 y 2025",
            NOTEBOOK_PATH.read_text(),
        )
        self.assertIn("summarize_normalization_sensitivity", normalization)
        self.assertIn(
            "op_bus_stops_with_supply_zone_franja_density_percentile",
            normalization,
        )

    def test_13j_imports_audit_helpers_from_notebook_directory(
        self,
    ) -> None:
        definitions = cell_source(
            "block13j-operational-bus-extremes-stability-definitions"
        )
        import_prefix = definitions.split(
            "OP_BUS_13J_ZONE_SPECS =",
            maxsplit=1,
        )[0]
        code = "\n".join(
            [
                "from pathlib import Path",
                f"PROJECT_ROOT = Path({str(PROJECT_ROOT)!r})",
                import_prefix,
            ]
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = ""

        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=PROJECT_ROOT / "02_eda",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_13k_builds_clustered_qr_gradients_by_time_and_scale(
        self,
    ) -> None:
        definitions = cell_source(
            "block13k-operational-bus-qr-gradient-definitions"
        )
        pooled = cell_source(
            "block13k-operational-bus-qr-gradient-pooled"
        )
        robustness = cell_source(
            "block13k-operational-bus-qr-gradient-robustness"
        )
        raw = cell_source(
            "block13k-operational-bus-qr-gradient-raw-sensitivity"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "operational_bus_qr_gradient_exposure_year_franja.parquet",
            definitions,
        )
        self.assertIn("collapse_metric_scope", definitions)
        self.assertIn("gradient_tables", definitions)
        self.assertIn("origin_zone_top1", definitions)
        self.assertIn("Relacion derivada", definitions)
        self.assertIn("q5_minus_q1_pp", pooled)
        self.assertIn('("Ano", ["year"])', robustness)
        self.assertIn('("Franja", ["franja_v2"])', robustness)
        self.assertIn("OP_BUS_13K_RAW_SPECS", raw)
        self.assertIn(
            "no una adopcion QR contemporanea",
            notebook,
        )

    def test_13l_closes_metro_inputs_before_variable_construction(
        self,
    ) -> None:
        inventory = cell_source(
            "block13l-operational-metro-source-inventory"
        )
        support = cell_source(
            "block13l-operational-metro-stage-support"
        )
        mapping = cell_source(
            "block13l-operational-metro-station-mapping"
        )
        decisions = cell_source(
            "block13l-operational-metro-mapping-decisions"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn('OP_METRO_MODE_CODE = "2"', inventory)
        self.assertIn('OP_METROTREN_MODE_CODE = "4"', inventory)
        self.assertIn("GTFS_20240210", inventory)
        self.assertIn("GTFS_20250412", inventory)
        self.assertIn("Proxy anticipado", inventory)
        self.assertIn("metro_headways_master.parquet", inventory)
        self.assertIn("n_trips_first_stage", support)
        self.assertIn("first_stage_zone_share", support)
        self.assertIn("op_metro_unique_station_names_for_mode", mapping)
        self.assertIn("load_zona777_geometries_lonlat", mapping)
        self.assertIn("Geometria GTFS como principal", decisions)
        self.assertIn("MetroTren / ferroviario", decisions)
        self.assertIn("13L solo fija el", notebook)

    def test_13m_builds_metro_contexts_and_accounting_contract(
        self,
    ) -> None:
        definitions = cell_source(
            "block13m-operational-metro-variable-definitions"
        )
        build = cell_source(
            "block13m-operational-metro-context-build"
        )
        accounting = cell_source(
            "block13m-operational-metro-accounting-sanity"
        )
        coverage = cell_source(
            "block13m-operational-metro-coverage-scope"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn("op_metro_supply_trains_h_station_hour", definitions)
        self.assertIn("op_metro_demand_entries_station_hour", definitions)
        self.assertIn(
            "op_metro_pressure_entries_per_scheduled_train_station_passage_*",
            definitions,
        )
        self.assertIn("No se interpreta ningun cociente como ocupacion", notebook)
        self.assertIn("op_metro_first_stage_events_lf", build)
        self.assertIn("op_stage_mode_expr(1, OP_METRO_MODE_CODE)", build)
        self.assertIn("operational_metro_station_hour_context.parquet", definitions)
        self.assertIn("operational_metro_zone_franja_context.parquet", definitions)
        self.assertIn("operational_metro_card_support.parquet", definitions)
        self.assertIn("Cierre entradas primera etapa", accounting)
        self.assertIn("Percentiles dentro de [0,1]", accounting)
        self.assertIn("share_cards_with_first_stage_metro", coverage)
        self.assertIn("13N debe auditar", notebook)

    def test_13n_audits_metro_extremes_stability_and_normalization(
        self,
    ) -> None:
        definitions = cell_source(
            "block13n-operational-metro-plausibility-definitions"
        )
        extremes = cell_source(
            "block13n-operational-metro-recurrent-extremes"
        )
        stability = cell_source(
            "block13n-operational-metro-ranking-stability"
        )
        normalization = cell_source(
            "block13n-operational-metro-normalization-sensitivity"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn("op_metro_aggregate_station_hour_week", definitions)
        self.assertIn("OP_METRO_13N_ZONE_SPECS", definitions)
        self.assertIn("OP_METRO_13N_STATION_SPECS", definitions)
        self.assertIn("Estacion-hora-semana", definitions)
        self.assertIn("n_entities", definitions)
        self.assertIn("summarize_recurrent_extremes", extremes)
        self.assertIn("threshold=0.01", extremes)
        self.assertIn(
            "op_metro_supply_match_share_station_hour_week",
            extremes,
        )
        self.assertIn("summarize_rank_stability", stability)
        self.assertIn("share_change_quintile", stability)
        self.assertIn("summarize_normalization_sensitivity", normalization)
        self.assertIn("raw_column", normalization)
        self.assertIn("normalized_column", normalization)
        self.assertIn("13O puede estudiar gradientes QR/BIP", notebook)

    def test_13o_builds_metro_qr_gradients_and_sensitivities(
        self,
    ) -> None:
        definitions = cell_source(
            "block13o-operational-metro-qr-gradient-definitions"
        )
        pooled = cell_source(
            "block13o-operational-metro-qr-gradient-pooled"
        )
        curves = cell_source(
            "block13o-operational-metro-qr-gradient-curves"
        )
        robustness = cell_source(
            "block13o-operational-metro-qr-gradient-robustness"
        )
        raw = cell_source(
            "block13o-operational-metro-qr-gradient-raw-sensitivity"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "operational_metro_qr_gradient_exposure_year_franja.parquet",
            definitions,
        )
        self.assertIn("op_metro_13o_build_exposure_lf", definitions)
        self.assertIn("OP_METRO_13O_NORMALIZED_SPECS", definitions)
        self.assertIn("OP_METRO_13O_RAW_SPECS", definitions)
        self.assertIn("Lineas Metro en zona", definitions)
        self.assertIn("Densidad de estaciones", definitions)
        self.assertIn("gradient_tables", definitions)
        self.assertIn("q5_minus_q1_pp", pooled)
        self.assertIn("Gradientes QR por quintil operacional Metro", curves)
        self.assertIn('("Ano", ["year"])', robustness)
        self.assertIn('("Franja", ["franja_v2"])', robustness)
        self.assertIn("q5_q1_percentile_pp", raw)
        self.assertIn("q5_q1_raw_pp", raw)
        self.assertIn("No mide ocupacion", raw)
        self.assertIn("avanza a 13P", notebook)

    def test_13p_audits_joint_socio_territorial_attenuation(
        self,
    ) -> None:
        definitions = cell_source(
            "block13p-operational-socio-territorial-definitions"
        )
        coverage = cell_source(
            "block13p-operational-socio-territorial-coverage"
        )
        attenuation = cell_source(
            "block13p-operational-socio-territorial-attenuation"
        )
        detail = cell_source(
            "block13p-operational-socio-territorial-strata-detail"
        )
        decision = cell_source(
            "block13p-operational-socio-territorial-decision"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn(
            "operational_bus_qr_gradient_exposure_year_franja.parquet",
            definitions,
        )
        self.assertIn(
            "operational_metro_qr_gradient_exposure_year_franja.parquet",
            definitions,
        )
        self.assertIn("OP_13P_BUS_SPECS", definitions)
        self.assertIn("OP_13P_METRO_SPECS", definitions)
        self.assertIn("home_macrozone", definitions)
        self.assertIn("origin_macrozone", definitions)
        self.assertIn("education_tertile", definitions)
        self.assertIn("income_de_tertile", definitions)
        self.assertIn("modal_profile", definitions)
        self.assertIn("No mide ocupacion", definitions)
        self.assertIn("op_13p_metric_coverage_rows", coverage)
        self.assertIn("support_share", coverage)
        self.assertIn("scope_universe", coverage)
        self.assertIn("matrix_support_share", coverage)
        self.assertIn("gradient_tables", definitions)
        self.assertIn("weighted_adjusted_q5_q1_pp", attenuation)
        self.assertIn("retained_share", attenuation)
        self.assertIn("abs(crude_value) >= 0.50", attenuation)
        self.assertIn("sign_flip", attenuation)
        self.assertIn("same_sign_weighted_share", detail)
        self.assertIn("OP_13P_CRITICAL_STRATA", decision)
        self.assertIn("Avanza a 13Q", decision)
        self.assertIn("composicion socio-territorial", decision)
        self.assertIn("No reemplaza el screening modelistico de 13Q", notebook)
        self.assertIn("En ningun caso 13P convierte", notebook)

    def test_13q_screens_main_and_sensitivity_operational_candidates(
        self,
    ) -> None:
        definitions = cell_source(
            "block13q-operational-model-screening-definitions"
        )
        frame = cell_source(
            "block13q-operational-model-frame"
        )
        individual = cell_source(
            "block13q-operational-individual-model-screening"
        )
        bundle = cell_source(
            "block13q-operational-bundle-model-screening"
        )
        decision = cell_source(
            "block13q-operational-final-decision"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn("OP_13Q_CANDIDATES", definitions)
        self.assertIn('"role_13q": "principal"', definitions)
        self.assertIn('"role_13q": "sensibilidad"', definitions)
        self.assertIn("bus_density", definitions)
        self.assertIn("bus_stop_pressure", definitions)
        self.assertIn("metro_station_count", definitions)
        self.assertIn("metro_zone_lines", definitions)
        self.assertIn("metro_station_pressure", definitions)
        self.assertIn("bus_stop_supply", definitions)
        self.assertIn("metro_station_supply", definitions)
        self.assertIn("metric_col", definitions)
        self.assertIn("model_col", definitions)
        self.assertIn("OP_13Q_INPUT_SCALE", definitions)
        self.assertIn("expected_sign_strength", definitions)
        self.assertIn("OP_13Q_DESCRIPTIVE_NOT_MODELED", definitions)
        self.assertIn("Oferta media por paradero activo", definitions)
        self.assertIn("Demanda Metro zonal", definitions)
        self.assertIn("LogisticRegression", definitions)
        self.assertIn("OP_13Q_BASE_NUMERIC_COLS", definitions)
        self.assertIn("OP_13Q_BASE_CATEGORICAL_COLS", definitions)
        self.assertIn("op_13q_collect_model_frame", frame)
        self.assertIn("matrix_support_share", frame)
        self.assertIn("op_13q_fit_screen", individual)
        self.assertIn("log_loss_gain_bps", individual)
        self.assertIn("delta_auc_bps", individual)
        self.assertIn("coef_sign_aligned", individual)
        self.assertIn("Bundle principales 13P", bundle)
        self.assertIn("Bundle principales + sensibilidad", bundle)
        self.assertIn("Principal para 13Q final", decision)
        self.assertIn("Sensibilidad modelistica", decision)
        self.assertIn("No inferir causalidad", decision)
        self.assertIn("no es el modelo de eleccion final", notebook)

    def test_13r_visualizes_payment_distributions_from_13q_frame(self) -> None:
        distributions = cell_source(
            "block13r-operational-payment-distributions"
        )
        quintiles = cell_source(
            "block13r-operational-payment-quintile-gradients"
        )
        maps = cell_source(
            "block13r-operational-origin-zone-maps"
        )
        rescaled_maps = cell_source(
            "block13r-operational-origin-zone-maps-rescaled"
        )
        synthesis = cell_source(
            "block13r-operational-visual-synthesis-matrix"
        )
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn("op_13r_candidate_distribution_specs", distributions)
        self.assertIn("op_13r_ecdf_rows", distributions)
        self.assertIn("plot_13r_payment_ecdfs", distributions)
        self.assertIn("op_13q_model_frame", distributions)
        self.assertIn("OP_13R_ECDF_GRID", distributions)
        self.assertIn("PAYMENT_ORDER", distributions)
        self.assertIn("PAYMENT_COLORS", distributions)
        self.assertIn("p50_qr_minus_bip", distributions)
        self.assertIn("max_abs_ecdf_diff", distributions)
        self.assertIn("OP_13R_TITLE_Y", distributions)
        self.assertIn("OP_13R_LEGEND_Y", distributions)
        self.assertIn("OP_13R_PANEL_TOP", distributions)
        self.assertNotIn("bbox_to_anchor=(0.5, 0.955)", distributions)
        self.assertIn("Distribuciones operacionales por medio de pago", notebook)
        self.assertIn("Esta figura no selecciona variables", notebook)
        self.assertIn("op_13r_rank_quintiles", quintiles)
        self.assertIn("op_13r_quintile_gradient_rows", quintiles)
        self.assertIn("plot_13r_quintile_gradients", quintiles)
        self.assertIn("OP_13R_QUINTILE_LABELS", quintiles)
        self.assertIn("q5_minus_q1_pp", quintiles)
        self.assertIn("q5_minus_q1_ci_low_pp", quintiles)
        self.assertIn("q5_minus_q1_ci_high_pp", quintiles)
        self.assertIn("Gradiente QR por quintil operacional", notebook)
        self.assertIn("Quintiles rank-based", notebook)
        self.assertIn("op_13r_origin_zone_summary", maps)
        self.assertIn("op_13r_prepare_origin_zone_map_gdf", maps)
        self.assertIn("op_13r_origin_zone_map_summary", maps)
        self.assertIn("plot_13r_origin_zone_maps", maps)
        self.assertIn("origin_zone_top1", maps)
        self.assertIn("load_zona777_geometries", maps)
        self.assertIn("OP_13R_MAP_MIN_N", maps)
        self.assertIn("qr_share_zona", maps)
        self.assertIn("Geografia operacional por zona de origen habitual", notebook)
        self.assertIn("La unidad sigue siendo tarjeta", notebook)
        self.assertIn("op_13r_add_origin_zone_deviation_columns", rescaled_maps)
        self.assertIn("plot_13r_origin_zone_deviation_maps", rescaled_maps)
        self.assertIn("OP_13R_MAP_RESCALE_LOW_Q", rescaled_maps)
        self.assertIn("OP_13R_MAP_RESCALE_HIGH_Q", rescaled_maps)
        self.assertIn("delta_median_pp", rescaled_maps)
        self.assertIn("TwoSlopeNorm", rescaled_maps)
        self.assertIn("color_low_pp", rescaled_maps)
        self.assertIn("color_high_pp", rescaled_maps)
        self.assertIn("Desviaciones operacionales por zona de origen habitual", notebook)
        self.assertIn("Rangos de color fijados con p5-p95 zonal", notebook)
        self.assertIn("op_13r_visual_synthesis_rows", synthesis)
        self.assertIn("op_13r_normalized_synthesis_matrix", synthesis)
        self.assertIn("plot_13r_visual_synthesis_matrix", synthesis)
        self.assertIn("OP_13R_SYNTHESIS_COLUMNS", synthesis)
        self.assertIn("payment_median_qr_minus_bip_ppctl", synthesis)
        self.assertIn("spatial_p95_p05_ppctl", synthesis)
        self.assertIn("model_logloss_gain_bps", synthesis)
        self.assertIn("op_13q_individual_screen", synthesis)
        self.assertIn("Sintesis visual de senales operacionales QR/BIP", notebook)
        self.assertIn("No aplica umbrales de seleccion", notebook)

    def test_14a_defines_interannual_zone_change_contract(self) -> None:
        source = cell_source("block14a-interannual-zone-change-maps")
        notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")

        self.assertIn("INTERANNUAL_YEARS = [2024, 2025]", source)
        self.assertIn("INTERANNUAL_MAP_MIN_N", source)
        self.assertIn("interannual_trip_lazyframe", source)
        self.assertIn("interannual_card_year_residence_rates", source)
        self.assertIn("interannual_trip_origin_rates", source)
        self.assertIn("interannual_wide_zone_rates", source)
        self.assertIn("interannual_zone_summary", source)
        self.assertIn("prepare_interannual_map_gdf", source)
        self.assertIn("plot_interannual_zone_change_maps", source)
        self.assertIn('"delta_pp"', source)
        self.assertIn('"support_min"', source)
        self.assertIn('"residence"', source)
        self.assertIn('"origin_trip"', source)
        self.assertIn("# 14) Cambio interanual zonal QR/BIP", notebook)
        self.assertIn("## 14A) Mapas base: nivel 2024, nivel 2025 y delta", notebook)
        self.assertIn("2024-W14", notebook)
        self.assertIn("2025-W17", notebook)
        self.assertIn("tarjeta-año", notebook)
        self.assertIn("share QR 2025 - share QR 2024", notebook)

    def test_13r_synthesis_matrix_preserves_values_with_label_index(self) -> None:
        synthesis = cell_source(
            "block13r-operational-visual-synthesis-matrix"
        )
        start = synthesis.index("OP_13R_SYNTHESIS_COLUMNS")
        end = synthesis.index("\n\ndef plot_13r_visual_synthesis_matrix")
        namespace = {"pd": pd}
        exec(synthesis[start:end], namespace)

        sample = pd.DataFrame(
            {
                "synthesis_label": ["Fila A", "Fila B"],
                "payment_median_qr_minus_bip_ppctl": [-1.0, 2.0],
                "quintile_q5_minus_q1_pp": [-0.5, 1.0],
                "spatial_p95_p05_ppctl": [10.0, None],
                "model_auc_gain_bps": [5.0, -2.5],
                "model_logloss_gain_bps": [0.2, 0.4],
            }
        )

        value_matrix, annotation_matrix = namespace[
            "op_13r_normalized_synthesis_matrix"
        ](sample)

        self.assertEqual(list(value_matrix.index), ["Fila A", "Fila B"])
        self.assertFalse(value_matrix.isna().all().all())
        self.assertAlmostEqual(
            value_matrix.loc["Fila A", "Mediana QR-BIP\n(pp percentil)"],
            -0.5,
        )
        self.assertEqual(
            annotation_matrix.loc["Fila B", "Mediana QR-BIP\n(pp percentil)"],
            "+2.0",
        )


if __name__ == "__main__":
    unittest.main()
