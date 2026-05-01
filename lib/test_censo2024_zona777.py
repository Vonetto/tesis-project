import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl
from shapely.geometry import box

from lib.censo2024_zona777 import (
    _add_derived_weight_columns,
    _aggregate_by_zona,
    _apply_area_share_scaling,
    impute_missing_by_neighbor_median,
    sync_final_output_alias,
)


class SyncFinalOutputAliasTest(unittest.TestCase):
    def test_overwrites_stale_final_alias_with_selected_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            preferred = out_dir / "censo2024_zona777_agg_intersects_area.parquet"
            final = out_dir / "censo2024_zona777_agg_final.parquet"

            df_preferred = pl.DataFrame(
                {
                    "ZONA777": [0, 1],
                    "prom_edad": [37.2, 36.5],
                    "prom_escolaridad18": [11.1, 10.7],
                }
            )
            df_stale = pl.DataFrame(
                {
                    "ZONA777": [0, 1],
                    "prom_edad": [2.4, 0.04],
                    "prom_escolaridad18": [0.79, 0.94],
                }
            )

            df_preferred.write_parquet(preferred)
            df_stale.write_parquet(final)

            out = sync_final_output_alias(out_dir, preferred_mode="intersects_area")

            self.assertEqual(out, final)
            self.assertTrue(final.exists())
            self.assertTrue(pl.read_parquet(final).equals(df_preferred))


class AreaWeightedScalingTest(unittest.TestCase):
    def test_weight_columns_are_scaled_only_once(self):
        df_join = pd.DataFrame(
            {
                "ZONA777": [1, 1],
                "area_share": [0.5, 0.25],
                "n_per": [100.0, 80.0],
                "n_hog": [40.0, 20.0],
                "n_internet": [30.0, 10.0],
                "n_ocupado": [60.0, 10.0],
                "n_vp_ocupada": [35.0, 18.0],
                "n_viv_hacinadas": [5.0, 2.0],
                "prom_edad": [40.0, 50.0],
                "prom_escolaridad18": [12.0, 14.0],
                "prom_per_hog": [3.0, 4.0],
            }
        )

        scaled = _apply_area_share_scaling(df_join)
        agg = _aggregate_by_zona(scaled)
        row = agg.iloc[0]

        self.assertAlmostEqual(row["n_per"], 70.0)
        self.assertAlmostEqual(row["n_hog"], 25.0)
        self.assertAlmostEqual(row["n_internet"], 17.5)
        self.assertAlmostEqual(row["share_internet"], 0.7)
        self.assertLessEqual(row["share_internet"], 1.0)
        self.assertAlmostEqual(row["share_ocupado"], 32.5 / 70.0)
        self.assertAlmostEqual(row["prom_edad"], (40.0 * 50.0 + 50.0 * 20.0) / 70.0)

    def test_prom_escolaridad18_uses_18plus_weight(self):
        df_join = pd.DataFrame(
            {
                "ZONA777": [1, 1],
                "area_share": [1.0, 1.0],
                "n_per": [100.0, 100.0],
                "n_hog": [30.0, 30.0],
                "n_internet": [20.0, 20.0],
                "n_edad_18_24": [20.0, 10.0],
                "n_edad_25_44": [30.0, 10.0],
                "n_edad_45_59": [20.0, 10.0],
                "n_edad_60_mas": [10.0, 10.0],
                "prom_escolaridad18": [12.0, 16.0],
            }
        )

        prepared = _add_derived_weight_columns(df_join)
        scaled = _apply_area_share_scaling(prepared)
        agg = _aggregate_by_zona(scaled)
        row = agg.iloc[0]

        expected = (12.0 * 80.0 + 16.0 * 40.0) / (80.0 + 40.0)
        self.assertAlmostEqual(row["prom_escolaridad18"], expected)

    def test_n_18_mas_is_strict_to_missing_age_buckets(self):
        df = pd.DataFrame(
            {
                "n_edad_18_24": [10.0, None],
                "n_edad_25_44": [20.0, 5.0],
                "n_edad_45_59": [30.0, 5.0],
                "n_edad_60_mas": [40.0, 5.0],
            }
        )

        prepared = _add_derived_weight_columns(df)

        self.assertEqual(prepared.loc[0, "n_18_mas"], 100.0)
        self.assertTrue(pd.isna(prepared.loc[1, "n_18_mas"]))


class NeighborMedianImputationTest(unittest.TestCase):
    def test_imputes_missing_zone_from_first_order_neighbors(self):
        gdf = gpd.GeoDataFrame(
            {
                "ZONA777": [1, 2, 3, 4, 5],
                "geometry": [
                    box(0, 1, 1, 2),   # north
                    box(1, 0, 2, 1),   # east
                    box(0, -1, 1, 0),  # south
                    box(-1, 0, 0, 1),  # west
                    box(0, 0, 1, 1),   # center (missing)
                ],
            },
            crs="EPSG:4674",
        )
        df = pd.DataFrame(
            {
                "ZONA777": [1, 2, 3, 4, 5],
                "prom_edad": [30.0, 40.0, 50.0, 60.0, None],
                "share_inmigrantes": [0.10, 0.20, 0.30, 0.40, None],
            }
        )

        out, audit = impute_missing_by_neighbor_median(
            gdf_zonas=gdf,
            df=df,
            columns=["prom_edad", "share_inmigrantes"],
        )

        row = out.loc[out["ZONA777"] == 5].iloc[0]
        self.assertAlmostEqual(row["prom_edad"], 45.0)
        self.assertAlmostEqual(row["share_inmigrantes"], 0.25)
        self.assertEqual(len(audit), 2)

    def test_dissolves_multipart_zone_keys_before_neighbor_imputation(self):
        gdf = gpd.GeoDataFrame(
            {
                "ZONA777": [1, 1, 2, 3, 4, 5],
                "geometry": [
                    box(0, 1, 0.5, 2),   # north-left piece of zone 1
                    box(0.5, 1, 1, 2),   # north-right piece of zone 1
                    box(1, 0, 2, 1),     # east
                    box(0, -1, 1, 0),    # south
                    box(-1, 0, 0, 1),    # west
                    box(0, 0, 1, 1),     # center (missing)
                ],
            },
            crs="EPSG:4674",
        )
        df = pd.DataFrame(
            {
                "ZONA777": [1, 2, 3, 4, 5],
                "prom_edad": [30.0, 40.0, 50.0, 60.0, None],
                "share_inmigrantes": [0.10, 0.20, 0.30, 0.40, None],
            }
        )

        out, audit = impute_missing_by_neighbor_median(
            gdf_zonas=gdf,
            df=df,
            columns=["prom_edad", "share_inmigrantes"],
        )

        row = out.loc[out["ZONA777"] == 5].iloc[0]
        self.assertAlmostEqual(row["prom_edad"], 45.0)
        self.assertAlmostEqual(row["share_inmigrantes"], 0.25)
        self.assertEqual(sorted(audit["n_valid_neighbors"].unique().tolist()), [4])


if __name__ == "__main__":
    unittest.main()
