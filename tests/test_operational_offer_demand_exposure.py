from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import polars as pl

from scripts.audits import build_operational_offer_demand_exposure as operational


class OperationalOfferDemandExposureTest(unittest.TestCase):
    def test_percentile_within_groups_ignores_null_values(self) -> None:
        result = (
            pl.DataFrame(
                {
                    "group": ["A", "A", "A"],
                    "value": [1.0, 3.0, None],
                }
            )
            .with_columns(
                operational.percentile_within_groups(
                    "value",
                    ["group"],
                ).alias("percentile")
            )
            .sort("value", nulls_last=True)
        )

        self.assertEqual(result["percentile"].to_list(), [0.5, 1.0, None])

    def test_build_zone_context_materializes_active_stop_density(self) -> None:
        demand = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "zone_id": [1, 2],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_demand_trips_zone_franja_week": [100, 200],
                "op_demand_cards_zone_franja_week": [80, 150],
            }
        )
        bus_offer = pl.DataFrame(
            {
                "partition": ["2025-W17", "2025-W17"],
                "zone_id": [1, 2],
                "franja_v2": ["LAB_PM", "LAB_PM"],
                "op_bus_supply_hours_observed": [5, 5],
                "op_bus_supply_buses_h_zone_franja_mean": [100.0, 100.0],
                "op_bus_supply_buses_h_zone_franja_median": [100.0, 100.0],
                "op_bus_supply_typical_stop_buses_h_zone_franja_mean": [10.0, 20.0],
                "op_bus_supply_typical_stop_buses_h_zone_franja_median": [9.0, 19.0],
                "op_bus_service_directions_zone_franja_mean": [4.0, 8.0],
                "op_bus_stops_with_supply_zone_franja_mean": [10.0, 10.0],
            }
        )
        zone_area = pl.DataFrame(
            {
                "zone_id": [1, 2],
                "AREA_M2": [1_000_000.0, 2_000_000.0],
                "AREA_KM2": [1.0, 2.0],
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            result = operational.build_zone_context(
                demand,
                bus_offer,
                zone_area,
                Path(temp_dir) / "context.parquet",
            ).sort("zone_id")

        self.assertEqual(
            result["op_bus_stops_with_supply_zone_franja_density_km2"].to_list(),
            [10.0, 5.0],
        )
        self.assertEqual(
            result[
                "op_bus_stops_with_supply_zone_franja_density_percentile"
            ].to_list(),
            [1.0, 0.5],
        )

    def test_stop_hour_supply_percentile_is_week_franja_normalized(self) -> None:
        week = "2025-W17"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            frequency_path = temp_path / "frequency.parquet"
            trips_path = temp_path / "trips.parquet"

            pl.DataFrame(
                {
                    "ServicioSentido": ["A-I", "B-I", "C-I"],
                    "Paradero": ["STOP-1", "STOP-2", "STOP-3"],
                    "hour_start": [
                        datetime(2025, 4, 21, 7),
                        datetime(2025, 4, 21, 7),
                        datetime(2025, 4, 26, 7),
                    ],
                    "freq_buses_h": [10.0, 20.0, 5.0],
                }
            ).write_parquet(frequency_path)
            pl.DataFrame(
                {
                    "id_tarjeta": ["CARD-1", "CARD-2"],
                    "zona_inicio_viaje": [1, 2],
                    "paradero_inicio_viaje": ["STOP-1", "STOP-3"],
                    "tiempo_inicio_viaje": [
                        datetime(2025, 4, 21, 7),
                        datetime(2025, 4, 26, 7),
                    ],
                    "tipodia": [0, 1],
                    "tipo_transporte_1": ["1", "1"],
                }
            ).write_parquet(trips_path)

            original_frequency = operational.BUS_FREQUENCIES_BY_WEEK[week]
            original_trips = operational.TRIPS_BY_WEEK[week]
            operational.BUS_FREQUENCIES_BY_WEEK[week] = frequency_path
            operational.TRIPS_BY_WEEK[week] = trips_path
            try:
                result = (
                    operational.bus_stop_hour_context_lf(week)
                    .collect()
                    .sort("stop_id")
                )
            finally:
                operational.BUS_FREQUENCIES_BY_WEEK[week] = original_frequency
                operational.TRIPS_BY_WEEK[week] = original_trips

        self.assertEqual(
            result["op_stop_bus_supply_buses_h_observed_percentile"].to_list(),
            [0.5, 1.0, 1.0],
        )


if __name__ == "__main__":
    unittest.main()
