import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import geopandas as gpd
import polars as pl
from shapely.geometry import Polygon

from lib.interannual_offer_context import (
    assert_left_join_preserves_rows,
    build_zona777_area_table_from_gdf,
    ensure_unique_keys,
    filter_to_valid_origin_zones,
    load_trip_zone_context,
)


class BuildZona777AreaTableFromGdfTest(unittest.TestCase):
    def test_collapses_multiple_parts_of_same_zone(self):
        gdf = gpd.GeoDataFrame(
            {
                "ZONA777": [493, 493, 777],
                "geometry": [
                    Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]),
                    Polygon([(20, 0), (40, 0), (40, 10), (20, 10)]),
                    Polygon([(0, 20), (10, 20), (10, 30), (0, 30)]),
                ],
            },
            crs="EPSG:32719",
        )

        out = build_zona777_area_table_from_gdf(gdf)

        self.assertEqual(out.filter(pl.col("zona_inicio_viaje") == 493).height, 1)
        zone_493 = out.filter(pl.col("zona_inicio_viaje") == 493).to_dicts()[0]
        self.assertAlmostEqual(zone_493["AREA_M2"], 300.0)
        self.assertAlmostEqual(zone_493["AREA_KM2"], 0.0003)


class OfferContextValidationTest(unittest.TestCase):
    def test_ensure_unique_keys_raises_on_duplicates(self):
        df = pl.DataFrame(
            {
                "zona_inicio_viaje": [493, 493],
                "AREA_M2": [100.0, 200.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "no es unico por"):
            ensure_unique_keys(df, ["zona_inicio_viaje"], "zona_area")

    def test_assert_left_join_preserves_rows_raises_on_row_inflation(self):
        with self.assertRaisesRegex(ValueError, "cambio el numero de filas"):
            assert_left_join_preserves_rows(10, 12, "join de oferta")

    def test_filter_to_valid_origin_zones_drops_null_and_out_of_scope_codes(self):
        df = pl.DataFrame(
            {
                "zona_inicio_viaje": [100, 849, None, 200],
                "value": [1, 2, 3, 4],
            }
        )
        valid_zonas = pl.DataFrame({"zona_inicio_viaje": [100, 200]})

        filtered, diag = filter_to_valid_origin_zones(df, valid_zonas, "df_trips")

        self.assertEqual(filtered.height, 2)
        self.assertEqual(filtered["zona_inicio_viaje"].to_list(), [100, 200])
        self.assertEqual(diag["rows_before"], 4)
        self.assertEqual(diag["rows_after"], 2)
        self.assertEqual(diag["rows_dropped"], 2)
        self.assertEqual(diag["null_rows_dropped"], 1)
        self.assertEqual(diag["invalid_non_null_rows_dropped"], 1)
        self.assertEqual(diag["invalid_zone_keys"], [849])

    def test_load_trip_zone_context_reads_and_casts_unique_origin_zones(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "trips.parquet"
            pl.DataFrame(
                {
                    "partition": ["2024-W17", "2024-W17", "2025-W17"],
                    "franja_v2": ["LAB_PM", "LAB_PM", "NO_LAB"],
                    "zona_inicio_viaje": ["100", "100", "200"],
                    "other": [1, 2, 3],
                }
            ).write_parquet(path)

            df_trips_keys, df_trip_zones = load_trip_zone_context(path)

            self.assertEqual(df_trips_keys.columns, ["partition", "franja_v2", "zona_inicio_viaje"])
            self.assertEqual(df_trips_keys["zona_inicio_viaje"].dtype, pl.Int64)
            self.assertEqual(df_trips_keys.height, 3)
            self.assertEqual(df_trip_zones.columns, ["zona_inicio_viaje"])
            self.assertEqual(df_trip_zones["zona_inicio_viaje"].to_list(), [100, 200])


if __name__ == "__main__":
    unittest.main()
