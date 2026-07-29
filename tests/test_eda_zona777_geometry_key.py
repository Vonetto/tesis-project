from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = PROJECT_ROOT / "02_eda" / "eda_qr_vs_bip_profiles.qmd"


def load_notebook_zone_loader():
    notebook = NOTEBOOK_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"(def load_zona777_geometries_lonlat\(.*?\n    return zones\n)",
        notebook,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError("No se encontro load_zona777_geometries_lonlat en el notebook.")

    namespace = {
        "Path": Path,
        "gpd": gpd,
        "pd": pd,
        "ZONAS777_SHP": Path("unused.shp"),
    }
    exec(match.group(1), namespace)
    return namespace["load_zona777_geometries_lonlat"]


class Zona777GeometryKeyTest(unittest.TestCase):
    def test_zone_id_uses_zona777_field_not_internal_id(self) -> None:
        zones = gpd.GeoDataFrame(
            {
                "ID": [900, 901],
                "ZONA777": [56, 57],
                "COMUNA": ["RENCA", "RENCA"],
                "MACROZONA": ["NORTE", "NORTE"],
                "NMACROZONA": [1, 1],
            },
            geometry=[Point(-70.7, -33.4), Point(-70.69, -33.4)],
            crs="EPSG:4326",
        )
        loader = load_notebook_zone_loader()

        with patch.object(gpd, "read_file", return_value=zones):
            loaded = loader(Path("synthetic.shp"))

        self.assertEqual(set(loaded["zone_id"]), {56, 57})


if __name__ == "__main__":
    unittest.main()
