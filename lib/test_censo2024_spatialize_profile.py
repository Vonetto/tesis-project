import unittest

import pandas as pd

from lib.censo2024_spatialize_profile import (
    add_household_profile_features,
    add_manzent_profile_features,
    assign_households_profile_quota,
    summarize_eval_by_cut,
)


class HouseholdProfileFeaturesTest(unittest.TestCase):
    def test_household_profile_score_ranks_better_equipped_households_higher(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3"],
                "comuna": ["13101", "13101", "13101"],
                "p15b_serv_compu": [1, 2, 2],
                "p15d_serv_internet_fija": [1, 2, 2],
                "p15e_serv_internet_movil": [1, 2, 2],
                "p15f_serv_internet_satelital": [2, 2, 2],
                "indice_hacinamiento": [1.0, 3.0, 1.5],
                "n_personas_hogar": [2, 5, 4],
            }
        )

        out = add_household_profile_features(household_base)
        scores = out.set_index("hogar_uid")["household_profile_score"]

        self.assertGreater(scores["h1"], scores["h3"])
        self.assertGreater(scores["h3"], scores["h2"])


class ManzentProfileFeaturesTest(unittest.TestCase):
    def test_manzent_profile_score_ranks_advantaged_manzanas_higher(self):
        targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101", "13101"],
                "MANZENT": ["m1", "m2", "m3"],
                "n_hog": [10, 10, 10],
                "n_per": [20, 45, 35],
                "n_internet": [10, 2, 6],
                "n_serv_compu": [9, 1, 5],
                "n_viv_hacinadas": [0, 5, 2],
            }
        )

        out = add_manzent_profile_features(targets)
        scores = out.set_index("MANZENT")["manzent_profile_score"]

        self.assertGreater(scores["m1"], scores["m3"])
        self.assertGreater(scores["m3"], scores["m2"])


class AssignHouseholdsProfileQuotaTest(unittest.TestCase):
    def test_assigns_high_profile_households_to_high_profile_manzanas(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3", "h4"],
                "comuna": ["13101", "13101", "13101", "13101"],
                "p15b_serv_compu": [1, 1, 2, 2],
                "p15d_serv_internet_fija": [1, 2, 2, 2],
                "p15e_serv_internet_movil": [1, 1, 2, 2],
                "p15f_serv_internet_satelital": [2, 2, 2, 2],
                "indice_hacinamiento": [1.0, 1.2, 3.5, 4.0],
                "n_personas_hogar": [2, 3, 5, 6],
                "n_18_mas": [2, 2, 2, 2],
                "prom_escolaridad18_micro": [18.0, 16.0, 8.0, 7.0],
                "n_personas_hogar": [2, 3, 5, 6],
                "n_discapacidad_5mas": [0, 0, 0, 1],
                "n_analfabet_15mas": [0, 0, 1, 1],
                "n_ocupado_15mas": [2, 2, 1, 0],
                "n_desocupado_15mas": [0, 0, 1, 0],
                "n_fuera_fuerza_trabajo_15mas": [0, 0, 0, 1],
                "n_independiente": [0, 0, 0, 0],
                "n_dependiente": [2, 2, 1, 0],
                "n_no_remunerado": [0, 0, 0, 0],
                "n_cine_nunca_curso_primera_infancia": [0, 0, 0, 0],
                "n_cine_primaria": [0, 0, 1, 1],
                "n_cine_secundaria": [0, 1, 1, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 1, 0, 0],
                "n_cine_especial_diferencial": [0, 0, 0, 0],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["m_high", "m_low"],
                "n_hog": [2, 2],
                "n_per": [4, 11],
                "n_internet": [2, 0],
                "n_serv_compu": [2, 0],
                "n_viv_hacinadas": [0, 2],
                "prom_escolaridad18": [17.0, 7.5],
                "n_discapacidad": [0, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 0],
            }
        )

        assigned = assign_households_profile_quota(household_base, manzent_targets, seed=7)
        got = assigned.groupby("MANZENT")["hogar_uid"].apply(list).to_dict()

        self.assertEqual(set(got["m_high"]), {"h1", "h2"})
        self.assertEqual(set(got["m_low"]), {"h3", "h4"})


class SummarizeEvalByCutTest(unittest.TestCase):
    def test_summarizes_metrics_for_each_cut(self):
        merged = pd.DataFrame(
            {
                "CUT": ["13101", "13101", "13112"],
                "prom_escolaridad18": [10.0, 12.0, 8.0],
                "prom_escolaridad18_recon": [11.0, 12.0, 7.0],
                "share_cine_terciaria_target": [0.5, 0.3, 0.1],
                "share_cine_terciaria_recon": [0.4, 0.3, 0.2],
            }
        )

        out = summarize_eval_by_cut(merged)
        self.assertEqual(list(out["CUT"]), ["13101", "13112"])
        self.assertAlmostEqual(
            float(out.loc[out["CUT"] == "13101", "prom_escolaridad18_mae"].iloc[0]),
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
