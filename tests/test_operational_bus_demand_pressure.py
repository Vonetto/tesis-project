from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import polars as pl

from scripts.audits import build_operational_bus_demand_pressure as bus_pressure


class OperationalBusDemandPressureTest(unittest.TestCase):
    def test_bus_boarding_events_uses_all_bus_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            trips_path = Path(temp_dir) / "trips.parquet"
            data = {
                "pk_viaje": [101, 102],
                "id_tarjeta": ["A", "B"],
                "tipodia": [0, 0],
            }
            for stage in range(1, 7):
                data[f"tipo_transporte_{stage}"] = [None, None]
                data[f"paradero_subida_{stage}"] = [None, None]
                data[f"zona_subida_{stage}"] = [None, None]
                data[f"tiempo_subida_{stage}"] = [None, None]

            data["tipo_transporte_1"] = ["2", "1"]
            data["paradero_subida_1"] = ["METRO", "STOP-2"]
            data["zona_subida_1"] = [10, 20]
            data["tiempo_subida_1"] = [
                "2025-04-21 08:00:00",
                "2025-04-21 18:00:00",
            ]
            data["tipo_transporte_2"] = ["1", None]
            data["paradero_subida_2"] = ["STOP-1", None]
            data["zona_subida_2"] = [11, None]
            data["tiempo_subida_2"] = ["2025-04-21 08:15:00", None]
            pl.DataFrame(data).write_parquet(trips_path)

            result = (
                bus_pressure.bus_boarding_events_lf(
                    "2025-W17",
                    trips_path=trips_path,
                )
                .collect()
                .sort("trip_id")
            )

        self.assertEqual(result.height, 2)
        self.assertEqual(result["stage_number"].to_list(), [2, 1])
        self.assertEqual(result["is_first_stage"].to_list(), [False, True])
        self.assertEqual(result["franja_v2"].to_list(), ["LAB_PM", "LAB_PT"])

    def test_pressure_context_keeps_demand_and_matches_supply(self) -> None:
        demand = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "stop_id": ["A", "B"],
                "hour_start": [
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                ],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_bus_demand_boardings_stop_hour": [20, 10],
                "op_bus_demand_trips_stop_hour": [18, 10],
                "op_bus_demand_cards_stop_hour": [15, 8],
            }
        )
        supply = pl.DataFrame(
            {
                "partition": ["2025-W17"],
                "stop_id": ["A"],
                "hour_start": [datetime(2025, 4, 21, 8)],
                "franja_v2": ["LAB_PM"],
                "op_bus_supply_buses_h_stop_hour": [5.0],
                "op_bus_supply_service_directions_stop_hour": [2.0],
                "op_bus_supply_buses_h_stop_hour_percentile": [0.5],
            }
        )

        result = (
            bus_pressure.pressure_context_lf(
                demand.lazy(),
                supply.lazy(),
                geography="stop",
            )
            .collect()
            .sort("stop_id")
        )

        self.assertEqual(result.height, 2)
        self.assertEqual(
            result["op_bus_pressure_boardings_per_bus_stop_hour"].to_list(),
            [4.0, None],
        )
        self.assertEqual(
            result[
                "op_bus_pressure_boardings_per_scheduled_passage_stop_hour"
            ].to_list(),
            [4.0, None],
        )
        self.assertEqual(
            result["op_has_bus_supply_stop_hour"].to_list(),
            [True, False],
        )

    def test_card_exposure_subtracts_complete_card_contribution(self) -> None:
        events = pl.DataFrame(
            {
                "partition": ["2025-W17"] * 4,
                "id_tarjeta": ["A", "A", "A", "B"],
                "trip_id": [1, 2, 4, 3],
                "stage_number": [1, 2, 1, 1],
                "is_first_stage": [True, False, True, True],
                "stop_id": ["S1", "S1", "S2", "S1"],
                "zone_id": [7, 7, 8, 7],
                "hour_start": [
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                ],
                "franja_v2": ["LAB_PM"] * 4,
            }
        )
        stop_context = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "stop_id": ["S1", "S2"],
                "hour_start": [
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                ],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_bus_demand_boardings_stop_hour": [3, 5],
                "op_bus_demand_trips_stop_hour": [3, 5],
                "op_bus_demand_cards_stop_hour": [2, 5],
                "op_bus_supply_buses_h_stop_hour": [2.0, 2.0],
                "op_bus_supply_buses_h_stop_hour_percentile": [0.5, 1.0],
                "op_bus_demand_boardings_stop_hour_percentile": [0.5, 1.0],
                "op_bus_demand_trips_stop_hour_percentile": [0.5, 1.0],
                "op_bus_demand_cards_stop_hour_percentile": [0.5, 1.0],
                "op_bus_pressure_boardings_per_bus_stop_hour_percentile": [
                    0.5,
                    1.0,
                ],
                "op_bus_pressure_boardings_per_scheduled_passage_stop_hour_percentile": [
                    0.5,
                    1.0,
                ],
            }
        )
        zone_context = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "zone_id": [7, 8],
                "hour_start": [
                    datetime(2025, 4, 21, 8),
                    datetime(2025, 4, 21, 8),
                ],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_bus_demand_boardings_zone_hour": [3, 5],
                "op_bus_demand_trips_zone_hour": [3, 5],
                "op_bus_demand_cards_zone_hour": [2, 5],
                "op_bus_supply_buses_h_zone_hour": [4.0, 2.0],
                "op_bus_supply_buses_h_zone_hour_percentile": [0.5, 1.0],
                "op_bus_demand_boardings_zone_hour_percentile": [0.5, 1.0],
                "op_bus_demand_trips_zone_hour_percentile": [0.5, 1.0],
                "op_bus_demand_cards_zone_hour_percentile": [0.5, 1.0],
                "op_bus_pressure_boardings_per_bus_zone_hour_percentile": [
                    0.5,
                    1.0,
                ],
                "op_bus_pressure_boardings_per_scheduled_passage_zone_hour_percentile": [
                    0.5,
                    1.0,
                ],
            }
        )

        weekly = bus_pressure.card_exposure_week_lf(
            events.lazy(),
            stop_context.lazy(),
            zone_context.lazy(),
        ).collect()
        result = bus_pressure.finalize_card_exposure_lf(weekly.lazy()).collect()
        card_a = result.filter(pl.col("id_tarjeta") == "A").row(0, named=True)

        self.assertEqual(card_a["op_bus_n_boarding_stages"], 3)
        self.assertEqual(
            card_a["op_bus_demand_boardings_excl_card_stop_hour_mean"],
            2.0,
        )
        self.assertEqual(
            card_a["op_bus_pressure_boardings_per_bus_excl_card_stop_hour_mean"],
            1.0,
        )
        self.assertEqual(
            card_a[
                "op_bus_pressure_boardings_per_scheduled_passage_excl_card_stop_hour_cell_weighted_mean"
            ],
            1.25,
        )

    def test_unmapped_supply_audit_recovers_stage_modal_zone(self) -> None:
        week = "2025-W17"
        with tempfile.TemporaryDirectory() as temp_dir:
            frequency_path = Path(temp_dir) / "frequency.parquet"
            pl.DataFrame(
                {
                    "Paradero": ["MAPPED", "UNMAPPED", "UNMAPPED"],
                    "freq_buses_h": [10.0, 3.0, 7.0],
                }
            ).write_parquet(frequency_path)
            events = pl.DataFrame(
                {
                    "stop_id": ["UNMAPPED", "UNMAPPED", "UNMAPPED"],
                    "zone_id": [8, 8, 9],
                }
            )
            mapping = pl.DataFrame(
                {
                    "stop_id": ["MAPPED"],
                    "zone_id": [7],
                }
            )

            original = bus_pressure.BUS_FREQUENCIES_BY_WEEK[week]
            bus_pressure.BUS_FREQUENCIES_BY_WEEK[week] = frequency_path
            try:
                result = bus_pressure.unmapped_supply_stops_lf(
                    week,
                    events.lazy(),
                    mapping,
                ).collect()
            finally:
                bus_pressure.BUS_FREQUENCIES_BY_WEEK[week] = original

        self.assertEqual(result.height, 1)
        self.assertEqual(result["frequency_supply_buses_h"].item(), 10.0)
        self.assertEqual(result["stage_modal_zone_id"].item(), 8)
        self.assertAlmostEqual(result["stage_modal_zone_share"].item(), 2 / 3)


if __name__ == "__main__":
    unittest.main()
