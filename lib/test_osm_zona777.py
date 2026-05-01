import unittest

import geopandas as gpd
import polars as pl
from shapely.geometry import Point, Polygon

from lib.osm_zona777 import OSMTagValueSpec, aggregate_osm_point_features_to_zona777


class AggregateOsmPointFeaturesToZona777Test(unittest.TestCase):
    def test_builds_count_presence_and_density_by_zone(self):
        gdf_zonas = gpd.GeoDataFrame(
            {
                "ZONA777": [100, 200],
                "geometry": [
                    Polygon([(0, 0), (100, 0), (100, 100), (0, 100)]),
                    Polygon([(200, 0), (300, 0), (300, 100), (200, 100)]),
                ],
            },
            crs="EPSG:32719",
        )

        gdf_points = gpd.GeoDataFrame(
            {
                "amenity": ["school", "school", "restaurant", "school"],
                "shop": ["mall", None, "mall", None],
                "geometry": [
                    Point(10, 10),
                    Point(20, 20),
                    Point(250, 50),
                    Point(1000, 1000),
                ],
            },
            crs="EPSG:32719",
        )

        specs = (
            OSMTagValueSpec("amenity", "school", "osm_amenity_school", "priority"),
            OSMTagValueSpec("shop", "mall", "osm_shop_mall", "priority"),
        )

        out = aggregate_osm_point_features_to_zona777(
            gdf_points=gdf_points,
            gdf_zonas=gdf_zonas,
            specs=specs,
        )

        self.assertEqual(out.height, 2)
        zone_100 = out.filter(pl.col("ZONA777") == 100).to_dicts()[0]
        zone_200 = out.filter(pl.col("ZONA777") == 200).to_dicts()[0]

        self.assertEqual(zone_100["osm_amenity_school_count"], 2)
        self.assertEqual(zone_100["osm_amenity_school_presence"], 1)
        self.assertEqual(zone_100["osm_shop_mall_count"], 1)
        self.assertEqual(zone_100["osm_shop_mall_presence"], 1)

        self.assertEqual(zone_200["osm_amenity_school_count"], 0)
        self.assertEqual(zone_200["osm_amenity_school_presence"], 0)
        self.assertEqual(zone_200["osm_shop_mall_count"], 1)
        self.assertEqual(zone_200["osm_shop_mall_presence"], 1)

        self.assertAlmostEqual(zone_100["AREA_M2"], 10000.0, places=4)
        self.assertAlmostEqual(zone_100["AREA_KM2"], 0.01, places=8)
        self.assertAlmostEqual(zone_100["osm_amenity_school_density_km2"], 200.0)
        self.assertAlmostEqual(zone_100["osm_shop_mall_density_km2"], 100.0)
        self.assertAlmostEqual(zone_200["osm_shop_mall_density_km2"], 100.0)

    def test_keeps_zones_with_zero_matches(self):
        gdf_zonas = gpd.GeoDataFrame(
            {
                "ZONA777": [100],
                "geometry": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])],
            },
            crs="EPSG:32719",
        )
        gdf_points = gpd.GeoDataFrame(
            {
                "amenity": ["restaurant"],
                "geometry": [Point(5, 5)],
            },
            crs="EPSG:32719",
        )
        specs = (OSMTagValueSpec("amenity", "school", "osm_amenity_school", "priority"),)

        out = aggregate_osm_point_features_to_zona777(
            gdf_points=gdf_points,
            gdf_zonas=gdf_zonas,
            specs=specs,
        )
        row = out.to_dicts()[0]
        self.assertEqual(row["osm_amenity_school_count"], 0)
        self.assertEqual(row["osm_amenity_school_presence"], 0)
        self.assertAlmostEqual(row["osm_amenity_school_density_km2"], 0.0)

    def test_transport_like_only_filters_non_transport_matches(self):
        gdf_zonas = gpd.GeoDataFrame(
            {
                "ZONA777": [100],
                "geometry": [Polygon([(0, 0), (100, 0), (100, 100), (0, 100)])],
            },
            crs="EPSG:32719",
        )
        gdf_points = gpd.GeoDataFrame(
            {
                "shelter": ["yes", "yes", "yes"],
                "highway": ["bus_stop", None, None],
                "public_transport": ["platform", None, None],
                "amenity": [None, "taxi", "restaurant"],
                "geometry": [Point(10, 10), Point(20, 20), Point(30, 30)],
            },
            crs="EPSG:32719",
        )
        specs = (
            OSMTagValueSpec(
                "shelter",
                "yes",
                "osm_transport_shelter_yes",
                "microinfra_candidate",
                transport_like_only=True,
            ),
        )

        out = aggregate_osm_point_features_to_zona777(
            gdf_points=gdf_points,
            gdf_zonas=gdf_zonas,
            specs=specs,
        )
        row = out.to_dicts()[0]
        self.assertEqual(row["osm_transport_shelter_yes_count"], 1)
        self.assertEqual(row["osm_transport_shelter_yes_presence"], 1)
        self.assertAlmostEqual(row["osm_transport_shelter_yes_density_km2"], 100.0)


if __name__ == "__main__":
    unittest.main()
