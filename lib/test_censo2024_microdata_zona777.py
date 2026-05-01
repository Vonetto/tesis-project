import tempfile
import unittest
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

from lib.censo2024_microdata_zona777 import (
    aggregate_microdata_to_zona777,
    build_microdata_manzent_features,
)


class MicrodataZona777FeaturesTest(unittest.TestCase):
    def test_build_microdata_manzent_features_derives_adult_education_and_status_shares(self):
        assigned = pd.DataFrame(
            {
                "CUT_target": ["13101", "13101"],
                "MANZENT": ["m1", "m1"],
                "hogar_uid": ["h1", "h2"],
                "n_personas_hogar": [2, 3],
                "n_5_mas": [2, 3],
                "n_15_mas": [2, 3],
                "n_18_mas": [2, 2],
                "n_discapacidad_5mas": [0, 1],
                "n_analfabet_15mas": [0, 1],
                "n_ocupado_15mas": [2, 1],
                "n_desocupado_15mas": [0, 1],
                "n_fuera_fuerza_trabajo_15mas": [0, 1],
                "n_independiente": [0, 1],
                "n_dependiente": [2, 0],
                "n_no_remunerado": [0, 0],
                "n_cine18_nunca_curso_primera_infancia": [0, 0],
                "n_cine18_primaria": [0, 1],
                "n_cine18_secundaria": [1, 0],
                "n_cine18_terciaria_corta": [1, 0],
                "n_cine18_universitaria": [0, 1],
                "n_cine18_universitaria_o_mas": [0, 1],
                "n_cine18_postgrado": [0, 0],
                "n_cine18_terciaria_maestria_doctorado": [1, 1],
                "n_cine18_especial_diferencial": [0, 0],
                "prom_escolaridad18_micro": [16.0, 10.0],
            }
        )

        out = build_microdata_manzent_features(assigned)
        row = out.iloc[0]
        self.assertEqual(row["n_hog"], 2)
        self.assertEqual(row["n_per"], 5)
        self.assertEqual(row["n_cine18_total_obs"], 4)
        self.assertAlmostEqual(row["prom_escolaridad18_micro"], 13.0)
        self.assertAlmostEqual(row["share_ocupado_15mas_micro"], 3 / 5)
        self.assertAlmostEqual(row["share_dependiente_micro"], 2 / 3)
        self.assertAlmostEqual(row["share_cine18_terciaria_corta_micro"], 1 / 4)
        self.assertAlmostEqual(row["share_cine18_universitaria_micro"], 1 / 4)
        self.assertAlmostEqual(row["share_cine18_universitaria_o_mas_micro"], 1 / 4)
        self.assertAlmostEqual(row["share_cine18_postgrado_micro"], 0.0)
        self.assertAlmostEqual(row["share_cine18_terciaria_micro"], 2 / 4)

    def test_aggregate_microdata_to_zona777_area_weighted(self):
        manzent_features = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["100", "200"],
                "n_hog": [1.0, 1.0],
                "n_per": [2.0, 4.0],
                "n_5_mas": [2.0, 4.0],
                "n_15_mas": [2.0, 4.0],
                "n_18_mas": [2.0, 4.0],
                "n_discapacidad_5mas": [0.0, 1.0],
                "n_analfabet_15mas": [0.0, 1.0],
                "n_ocupado_15mas": [2.0, 2.0],
                "n_desocupado_15mas": [0.0, 1.0],
                "n_fuera_fuerza_trabajo_15mas": [0.0, 1.0],
                "n_independiente": [0.0, 1.0],
                "n_dependiente": [2.0, 1.0],
                "n_no_remunerado": [0.0, 0.0],
                "n_cine18_nunca_curso_primera_infancia": [0.0, 0.0],
                "n_cine18_primaria": [0.0, 1.0],
                "n_cine18_secundaria": [1.0, 1.0],
                "n_cine18_terciaria_corta": [1.0, 0.0],
                "n_cine18_universitaria": [0.0, 1.0],
                "n_cine18_universitaria_o_mas": [0.0, 2.0],
                "n_cine18_postgrado": [0.0, 1.0],
                "n_cine18_terciaria_maestria_doctorado": [1.0, 2.0],
                "n_cine18_especial_diferencial": [0.0, 0.0],
                "n_cine18_total_obs": [2.0, 4.0],
                "prom_escolaridad18_micro": [16.0, 12.0],
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            carto = gpd.GeoDataFrame(
                {
                    "MANZENT": ["100", "200"],
                    "geometry": [
                        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                    ],
                },
                geometry="geometry",
                crs="EPSG:4674",
            )
            zonas = gpd.GeoDataFrame(
                {
                    "ZONA777": [1, 2],
                    "geometry": [
                        Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
                        Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
                    ],
                },
                geometry="geometry",
                crs="EPSG:4674",
            )
            carto_path = tmp / "carto.parquet"
            zonas_path = tmp / "zonas.shp"
            carto.to_parquet(carto_path)
            zonas.to_file(zonas_path)

            out = aggregate_microdata_to_zona777(
                manzent_features=manzent_features,
                carto_parquet=carto_path,
                zonas777_shp=zonas_path,
                area_weighted=True,
            )

            self.assertEqual(set(out["ZONA777"]), {1, 2})
            z1 = out.loc[out["ZONA777"] == 1].iloc[0]
            z2 = out.loc[out["ZONA777"] == 2].iloc[0]
            self.assertAlmostEqual(z1["prom_escolaridad18_micro"], 16.0)
            self.assertAlmostEqual(z2["prom_escolaridad18_micro"], 12.0)
            self.assertAlmostEqual(z1["share_cine18_terciaria_corta_micro"], 0.5)
            self.assertAlmostEqual(z2["share_cine18_universitaria_micro"], 0.25)
            self.assertAlmostEqual(z2["share_cine18_universitaria_o_mas_micro"], 0.5)
            self.assertAlmostEqual(z2["share_cine18_postgrado_micro"], 0.25)
            self.assertAlmostEqual(z1["share_cine18_terciaria_micro"], 0.5)
            self.assertAlmostEqual(z2["share_cine18_terciaria_micro"], 0.5)


if __name__ == "__main__":
    unittest.main()
