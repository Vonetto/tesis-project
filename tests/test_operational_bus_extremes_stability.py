from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path

import polars as pl

from scripts.audits import audit_operational_bus_extremes_stability as audit


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OperationalBusExtremesStabilityTest(unittest.TestCase):
    def test_scripts_audits_is_explicit_local_package(self) -> None:
        self.assertTrue((PROJECT_ROOT / "scripts" / "__init__.py").exists())
        self.assertTrue(
            (PROJECT_ROOT / "scripts" / "audits" / "__init__.py").exists()
        )
        self.assertIn(
            str(PROJECT_ROOT / "scripts" / "audits"),
            str(Path(audit.__file__).resolve().parent),
        )

    def test_partition_pairs_include_adjacent_and_same_week_years(
        self,
    ) -> None:
        pairs = audit.build_partition_pairs(
            [
                "2024-W14",
                "2024-W15",
                "2025-W14",
                "2025-W15",
            ]
        )

        self.assertEqual(
            sum(pair["comparison"] == "Semanas adyacentes" for pair in pairs),
            2,
        )
        self.assertEqual(
            sum(
                pair["comparison"] == "Misma semana entre anos"
                for pair in pairs
            ),
            2,
        )

    def test_stop_hour_week_aggregation_uses_only_matched_demand_in_pressure(
        self,
    ) -> None:
        source = pl.DataFrame(
            {
                "partition": ["2025-W17"] * 3,
                "stop_id": ["S1"] * 3,
                "hour_start": [
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 22, 8),
                    datetime(2025, 4, 23, 8),
                ],
                "franja_v2": ["LAB_PM"] * 3,
                "op_bus_demand_boardings_stop_hour": [10, 20, 30],
                "op_bus_demand_trips_stop_hour": [9, 18, 27],
                "op_bus_demand_cards_stop_hour": [8, 16, 24],
                "op_bus_supply_buses_h_stop_hour": [5.0, 10.0, None],
                "op_bus_supply_service_directions_stop_hour": [
                    2.0,
                    3.0,
                    None,
                ],
                "op_bus_supply_buses_h_stop_hour_percentile": [
                    0.3,
                    0.6,
                    None,
                ],
                "op_bus_demand_boardings_stop_hour_percentile": [
                    0.2,
                    0.5,
                    0.8,
                ],
                "op_bus_pressure_boardings_per_scheduled_passage_stop_hour_percentile": [
                    0.4,
                    0.4,
                    None,
                ],
            }
        )

        result = audit.aggregate_stop_hour_week(source).collect()
        row = result.row(0, named=True)

        self.assertEqual(row["n_observed_days"], 3)
        self.assertAlmostEqual(
            row["op_bus_supply_match_share_stop_hour_week"],
            2 / 3,
        )
        self.assertAlmostEqual(
            row[
                "op_bus_pressure_boardings_per_scheduled_passage_"
                "stop_hour_week"
            ],
            2.0,
        )

    def test_rank_stability_detects_preserved_order(self) -> None:
        source = pl.DataFrame(
            {
                "partition": [
                    "2025-W14",
                    "2025-W14",
                    "2025-W15",
                    "2025-W15",
                ],
                "franja_v2": ["LAB_PM"] * 4,
                "zone_id": [1, 2, 1, 2],
                "metric_value": [1.0, 2.0, 10.0, 20.0],
            }
        )

        result = audit.summarize_rank_stability(
            source,
            scale="Zona",
            entity_columns=["zone_id"],
            metric_specs=[
                {"metric": "Metrica", "column": "metric_value"}
            ],
        )

        self.assertEqual(result.height, 1)
        self.assertAlmostEqual(result["spearman_r"].item(), 1.0)
        self.assertAlmostEqual(result["share_change_quintile"].item(), 0.0)

    def test_recurrent_extremes_prioritize_repeated_entity(self) -> None:
        source = pl.DataFrame(
            {
                "partition": [
                    "2025-W14",
                    "2025-W14",
                    "2025-W15",
                    "2025-W15",
                ],
                "franja_v2": ["LAB_PM"] * 4,
                "zone_id": [1, 2, 1, 2],
                "metric_value": [100.0, 1.0, 90.0, 2.0],
            }
        )

        result = audit.summarize_recurrent_extremes(
            source,
            scale="Zona",
            entity_columns=["zone_id"],
            metric_specs=[
                {
                    "metric": "Metrica",
                    "column": "metric_value",
                    "expected": "Mayor es mas",
                }
            ],
            component_columns=["metric_value"],
            threshold=0.50,
            top_n=1,
        )
        high = result.filter(pl.col("extreme") == "Alto")

        self.assertEqual(high["zone_id"].item(), 1)
        self.assertEqual(high["n_extreme_cells"].item(), 2)

    def test_common_floor_is_not_labeled_as_point_five_percent_extreme(
        self,
    ) -> None:
        source = pl.DataFrame(
            {
                "partition": ["2025-W14"] * 1_000,
                "franja_v2": ["LAB_PM"] * 1_000,
                "entity_id": list(range(1_000)),
                "metric_value": [
                    *([1.0] * 20),
                    *[float(value) for value in range(2, 982)],
                ],
            }
        )

        result = audit.summarize_recurrent_extremes(
            source,
            scale="Paradero-hora",
            entity_columns=["entity_id"],
            metric_specs=[
                {
                    "metric": "Metrica",
                    "column": "metric_value",
                    "expected": "Mayor es mas",
                }
            ],
            component_columns=["metric_value"],
            threshold=0.005,
            top_n=1,
        )

        self.assertEqual(
            result.filter(pl.col("extreme") == "Bajo").height,
            0,
        )


if __name__ == "__main__":
    unittest.main()
