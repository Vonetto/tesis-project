import unittest

import pandas as pd

from lib.censo2024_microdata_base import (
    build_household_microdata_base,
    build_person_household_aggregates,
    clean_censo_microdata,
)


class CleanCensoMicrodataTest(unittest.TestCase):
    def test_replaces_common_missing_codes_and_casts_numeric_columns(self):
        raw = pd.DataFrame(
            {
                "id_vivienda": ["1"],
                "id_hogar": ["1"],
                "edad": ["40"],
                "escolaridad": ["-99"],
                "cine11": ["9"],
                "indice_hacinamiento": ["1,5"],
                "tipologia_hogar": ["NA"],
            }
        )

        out = clean_censo_microdata(raw)

        self.assertEqual(out.loc[0, "edad"], 40)
        self.assertTrue(pd.isna(out.loc[0, "escolaridad"]))
        self.assertEqual(out.loc[0, "cine11"], 9)
        self.assertAlmostEqual(out.loc[0, "indice_hacinamiento"], 1.5)
        self.assertTrue(pd.isna(out.loc[0, "tipologia_hogar"]))


class BuildPersonHouseholdAggregatesTest(unittest.TestCase):
    def test_aggregates_person_features_at_household_level(self):
        personas = clean_censo_microdata(
            pd.DataFrame(
                {
                    "id_vivienda": ["1", "1", "1"],
                    "id_hogar": ["1", "1", "2"],
                    "id_persona": ["1", "2", "3"],
                    "edad": ["40", "17", "70"],
                    "discapacidad": ["2", "2", "1"],
                    "p37_alfabet": ["1", "1", "2"],
                    "escolaridad": ["16", "11", "8"],
                    "cine11": ["9", "6", "4"],
                    "sit_fuerza_trabajo": ["1", "NA", "3"],
                    "p40_cise_rec": ["2", "NA", "NA"],
                }
            )
        )

        out = build_person_household_aggregates(personas)

        h1 = out.loc[(out["id_vivienda"] == "1") & (out["id_hogar"] == "1")].iloc[0]
        self.assertEqual(h1["n_personas_hogar"], 2)
        self.assertEqual(h1["n_personas_0_17"], 1)
        self.assertEqual(h1["n_edad_25_44"], 1)
        self.assertEqual(h1["n_18_mas"], 1)
        self.assertEqual(h1["n_ocupado_15mas"], 1)
        self.assertEqual(h1["n_dependiente"], 1)
        self.assertEqual(h1["n_cine_secundaria"], 1)
        self.assertEqual(h1["n_cine_terciaria_maestria_doctorado"], 1)
        self.assertEqual(h1["n_cine18_secundaria"], 0)
        self.assertEqual(h1["n_cine18_terciaria_corta"], 0)
        self.assertEqual(h1["n_cine18_universitaria"], 1)
        self.assertEqual(h1["n_cine18_universitaria_o_mas"], 1)
        self.assertEqual(h1["n_cine18_postgrado"], 0)
        self.assertEqual(h1["n_cine18_terciaria_maestria_doctorado"], 1)
        self.assertAlmostEqual(h1["prom_escolaridad18_micro"], 16.0)

        h2 = out.loc[(out["id_vivienda"] == "1") & (out["id_hogar"] == "2")].iloc[0]
        self.assertEqual(h2["n_personas_hogar"], 1)
        self.assertEqual(h2["n_edad_60_mas"], 1)
        self.assertEqual(h2["n_discapacidad_5mas"], 1)
        self.assertEqual(h2["n_analfabet_15mas"], 1)
        self.assertEqual(h2["n_fuera_fuerza_trabajo_15mas"], 1)
        self.assertEqual(h2["n_cine_primaria"], 1)
        self.assertEqual(h2["n_cine18_primaria"], 1)
        self.assertEqual(h2["n_cine18_terciaria_corta"], 0)
        self.assertEqual(h2["n_cine18_universitaria"], 0)
        self.assertEqual(h2["n_cine18_universitaria_o_mas"], 0)
        self.assertEqual(h2["n_cine18_postgrado"], 0)
        self.assertAlmostEqual(h2["prom_escolaridad18_micro"], 8.0)


class BuildHouseholdMicrodataBaseTest(unittest.TestCase):
    def test_merges_households_with_person_and_dwelling_attributes(self):
        personas = clean_censo_microdata(
            pd.DataFrame(
                {
                    "id_vivienda": ["1", "1", "1"],
                    "id_hogar": ["1", "1", "2"],
                    "id_persona": ["1", "2", "3"],
                    "edad": ["40", "17", "70"],
                    "discapacidad": ["2", "2", "1"],
                    "p37_alfabet": ["1", "1", "2"],
                    "escolaridad": ["16", "11", "8"],
                    "cine11": ["9", "6", "4"],
                    "sit_fuerza_trabajo": ["1", "NA", "3"],
                    "p40_cise_rec": ["2", "NA", "NA"],
                }
            )
        )
        hogares = clean_censo_microdata(
            pd.DataFrame(
                {
                    "id_vivienda": ["1", "1"],
                    "id_hogar": ["1", "2"],
                    "region": ["5", "5"],
                    "provincia": ["58", "58"],
                    "comuna": ["5802", "5802"],
                    "comuna_bajo_umbral": ["2", "2"],
                    "area": ["1", "1"],
                    "tipo_operativo": ["2", "2"],
                    "p15a_serv_tel_movil": ["1", "2"],
                    "p15b_serv_compu": ["2", "1"],
                    "tipologia_hogar": ["5", "1"],
                }
            )
        )
        viviendas = clean_censo_microdata(
            pd.DataFrame(
                {
                    "id_vivienda": ["1"],
                    "cant_hog": ["2"],
                    "cant_per": ["3"],
                    "p2_tipo_vivienda": ["1"],
                    "indice_hacinamiento": ["1,5"],
                }
            )
        )

        out = build_household_microdata_base(personas=personas, hogares=hogares, viviendas=viviendas)

        self.assertEqual(len(out), 2)
        self.assertIn("hogar_uid", out.columns)
        self.assertEqual(out.loc[out["id_hogar"] == "1", "hogar_uid"].iloc[0], "1-1")
        self.assertIn("comuna", out.columns)
        self.assertNotIn("comuna_x", out.columns)
        self.assertEqual(out.loc[out["id_hogar"] == "1", "n_personas_hogar"].iloc[0], 2)
        self.assertEqual(out.loc[out["id_hogar"] == "2", "n_discapacidad_5mas"].iloc[0], 1)
        self.assertEqual(out.loc[out["id_hogar"] == "1", "cant_hog"].iloc[0], 2)
        self.assertAlmostEqual(out.loc[out["id_hogar"] == "1", "indice_hacinamiento"].iloc[0], 1.5)


if __name__ == "__main__":
    unittest.main()
