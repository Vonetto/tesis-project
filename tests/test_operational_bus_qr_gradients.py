from __future__ import annotations

import unittest

import polars as pl

from scripts.audits import audit_operational_bus_qr_gradients as gradients
from scripts.audits import (
    build_operational_bus_qr_gradient_exposure as exposure,
)


class OperationalBusQrGradientExposureTest(unittest.TestCase):
    def test_origin_exposure_uses_density_specific_denominator(self) -> None:
        trips = pl.DataFrame(
            {
                "id_tarjeta": ["A", "A"],
                "partition": ["2025-W17", "2025-W17"],
                "year": [2025, 2025],
                "zone_id": [1, 2],
                "franja_v2": ["LAB_PM", "LAB_PM"],
            }
        )
        context = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "zone_id": [1, 2],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_bus_supply_typical_stop_buses_h_zone_franja_mean": [
                    10.0,
                    20.0,
                ],
                "op_bus_supply_typical_stop_buses_h_zone_franja_percentile": [
                    0.2,
                    0.8,
                ],
                "op_bus_service_directions_zone_franja_mean": [3.0, 5.0],
                "op_bus_service_directions_zone_franja_percentile": [
                    0.3,
                    0.7,
                ],
                "op_bus_stops_with_supply_zone_franja_density_km2": [
                    2.0,
                    None,
                ],
                "op_bus_stops_with_supply_zone_franja_density_percentile": [
                    0.4,
                    None,
                ],
            }
        )

        weekly = exposure.origin_exposure_week_lf(
            trips.lazy(),
            context.lazy(),
        )
        result = exposure.finalize_exposure_lf(
            weekly.with_columns(
                [
                    *[
                        pl.lit(0).alias(column)
                        for column in [
                            "_stop_n_events",
                            "_stop_n_matched",
                            "_stop_sum_external_demand",
                            "_stop_sum_demand_percentile",
                            "_stop_sum_supply_raw",
                            "_stop_sum_supply_percentile",
                            "_stop_sum_external_pressure",
                            "_stop_sum_pressure_percentile",
                            "_stop_sum_diversity_raw",
                            "_zone_n_events",
                            "_zone_n_matched",
                            "_zone_sum_external_demand",
                            "_zone_sum_demand_percentile",
                            "_zone_sum_supply_raw",
                            "_zone_sum_supply_percentile",
                            "_zone_sum_external_pressure",
                            "_zone_sum_pressure_percentile",
                        ]
                    ],
                ]
            )
        ).collect()

        self.assertEqual(result["op_qr_n_origin_density_trips"].item(), 1)
        self.assertEqual(result["op_qr_zone_offer_raw_mean"].item(), 15.0)
        self.assertEqual(result["op_qr_zone_density_raw_mean"].item(), 2.0)

    def test_boarding_exposure_subtracts_complete_card_cell(self) -> None:
        events = pl.DataFrame(
            {
                "id_tarjeta": ["A", "A", "B"],
                "partition": ["2025-W17"] * 3,
                "year": [2025] * 3,
                "stop_id": ["S1"] * 3,
                "hour_start": [1, 1, 1],
                "franja_v2": ["LAB_PM"] * 3,
            }
        )
        context = pl.DataFrame(
            {
                "partition": ["2025-W17"],
                "stop_id": ["S1"],
                "hour_start": [1],
                "franja_v2": ["LAB_PM"],
                "op_bus_demand_boardings_stop_hour": [3],
                "op_bus_demand_boardings_stop_hour_percentile": [0.5],
                "op_bus_supply_buses_h_stop_hour": [2.0],
                "op_bus_supply_buses_h_stop_hour_percentile": [0.5],
                "op_bus_pressure_boardings_per_scheduled_passage_stop_hour_percentile": [
                    0.5
                ],
                "op_bus_supply_service_directions_stop_hour": [2.0],
            }
        )

        result = exposure.boarding_exposure_week_lf(
            events.lazy(),
            context.lazy(),
            geography="stop",
        ).collect()
        card_a = result.filter(pl.col("id_tarjeta") == "A").row(
            0,
            named=True,
        )

        self.assertEqual(card_a["_stop_n_events"], 2)
        self.assertEqual(card_a["_stop_sum_external_demand"], 2)
        self.assertEqual(card_a["_stop_sum_external_pressure"], 1.0)


class OperationalBusQrGradientTest(unittest.TestCase):
    def test_collapse_metric_scope_uses_support_weighting(self) -> None:
        source = pl.DataFrame(
            {
                "id_tarjeta": ["A", "A"],
                "year": [2024, 2025],
                "metric": [1.0, 3.0],
                "support": [1, 3],
            }
        )
        result = gradients.collapse_metric_scope(
            source.lazy(),
            metric_col="metric",
            support_col="support",
            scope_columns=[],
        ).collect()

        self.assertEqual(result["metric_value"].item(), 2.5)

    def test_collapse_metrics_scope_reuses_one_grouping(self) -> None:
        source = pl.DataFrame(
            {
                "id_tarjeta": ["A", "A"],
                "year": [2024, 2025],
                "metric_a": [1.0, 3.0],
                "metric_b": [10.0, None],
                "support": [1, 3],
            }
        )
        result = gradients.collapse_metrics_scope(
            source.lazy(),
            metric_specs=[
                {
                    "metric_col": "metric_a",
                    "support_col": "support",
                },
                {
                    "metric_col": "metric_b",
                    "support_col": "support",
                },
            ],
            scope_columns=[],
        ).collect()

        self.assertEqual(result["metric_a"].item(), 2.5)
        self.assertEqual(result["metric_b"].item(), 2.5)
        self.assertEqual(result["support"].item(), 4)

    def test_gradient_tables_build_equal_size_quintiles(self) -> None:
        source = pl.DataFrame(
            {
                "id_tarjeta": [f"C{i:02d}" for i in range(10)],
                "metric_value": [float(i) for i in range(10)],
                "is_qr": [0, 0, 0, 0, 0, 1, 1, 1, 1, 1],
                "origin_zone_top1": [1, 2] * 5,
            }
        )
        detail, summary = gradients.gradient_tables(
            source.lazy(),
            scope_columns=[],
        )

        self.assertEqual(detail["n_cards"].tolist(), [2, 2, 2, 2, 2])
        self.assertAlmostEqual(summary["q5_minus_q1_pp"].item(), 100.0)
        self.assertAlmostEqual(
            summary["q5_minus_q1_cluster_se_pp"].item(),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
