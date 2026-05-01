import unittest

import pandas as pd

from lib.censo2024_spatialize_softmax import (
    allocate_group_counts_softmax,
    assign_households_softmax_quota,
    build_scaled_manzent_targets,
    encode_household_softmax_groups,
)


class BuildScaledManzentTargetsTest(unittest.TestCase):
    def test_scales_fine_targets_to_microdata_totals(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3", "h4"],
                "comuna": ["13101"] * 4,
                "p15b_serv_compu": [1, 1, 2, 2],
                "p15d_serv_internet_fija": [1, 2, 2, 2],
                "p15e_serv_internet_movil": [1, 1, 2, 2],
                "p15f_serv_internet_satelital": [2, 2, 2, 2],
                "indice_hacinamiento": [1.0, 1.2, 3.5, 3.8],
                "n_personas_hogar": [2, 3, 5, 6],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["m1", "m2"],
                "n_hog": [2, 4],
                "n_per": [4, 20],
                "n_serv_compu": [2, 1],
                "n_internet": [2, 2],
                "n_viv_hacinadas": [0, 3],
            }
        )

        out = build_scaled_manzent_targets(household_base, manzent_targets)

        self.assertEqual(int(out["quota_hogares_scaled"].sum()), 4)
        self.assertEqual(int(out["obj_n_per_scaled"].sum()), 16)
        self.assertEqual(int(out["obj_compu_scaled"].sum()), 2)
        self.assertEqual(int(out["obj_internet_scaled"].sum()), 2)
        self.assertEqual(int(out["obj_hacin_scaled"].sum()), 2)
        self.assertTrue((out["obj_compu_scaled"] <= out["quota_hogares_scaled"]).all())
        self.assertTrue((out["obj_internet_scaled"] <= out["quota_hogares_scaled"]).all())
        self.assertTrue((out["obj_hacin_scaled"] <= out["quota_hogares_scaled"]).all())

    def test_falls_back_when_cut_has_only_zero_household_targets(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1"],
                "comuna": ["12202"],
                "p15b_serv_compu": [2],
                "p15d_serv_internet_fija": [2],
                "p15e_serv_internet_movil": [2],
                "p15f_serv_internet_satelital": [2],
                "indice_hacinamiento": [1.0],
                "n_personas_hogar": [1],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["12202"],
                "MANZENT": ["m_zero"],
                "n_hog": [0],
                "n_per": [0],
                "n_serv_compu": [0],
                "n_internet": [0],
                "n_viv_hacinadas": [0],
            }
        )

        out = build_scaled_manzent_targets(household_base, manzent_targets)

        self.assertEqual(len(out), 1)
        self.assertEqual(int(out["quota_hogares_scaled"].sum()), 1)
        self.assertEqual(int(out["remaining_capacity"].sum()), 1)


class AllocateGroupCountsSoftmaxTest(unittest.TestCase):
    def test_allocates_exact_group_totals_and_uses_all_capacity(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3", "h4"],
                "comuna": ["13101"] * 4,
                "p15b_serv_compu": [1, 1, 2, 2],
                "p15d_serv_internet_fija": [1, 2, 2, 2],
                "p15e_serv_internet_movil": [1, 1, 2, 2],
                "p15f_serv_internet_satelital": [2, 2, 2, 2],
                "indice_hacinamiento": [1.0, 1.2, 3.5, 3.8],
                "n_personas_hogar": [2, 3, 5, 6],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["m1", "m2"],
                "n_hog": [2, 2],
                "n_per": [5, 11],
                "n_serv_compu": [2, 0],
                "n_internet": [2, 0],
                "n_viv_hacinadas": [0, 2],
            }
        )

        alloc = allocate_group_counts_softmax(household_base, manzent_targets, tau=0.15)
        hh = encode_household_softmax_groups(household_base)
        group_counts = hh["group_code"].value_counts()
        quota_cols = [c for c in alloc.columns if c.startswith("group_quota_")]

        self.assertEqual(int(alloc["remaining_capacity"].sum()), 0)
        self.assertTrue(((alloc[quota_cols].sum(axis=1)) == alloc["quota_hogares_scaled"]).all())
        for code, count in group_counts.items():
            self.assertEqual(int(alloc[f"group_quota_{code}"].sum()), int(count))


class AssignHouseholdsSoftmaxQuotaTest(unittest.TestCase):
    def test_assigns_high_resource_groups_to_high_resource_manzana(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3", "h4"],
                "comuna": ["13101"] * 4,
                "p15b_serv_compu": [1, 1, 2, 2],
                "p15d_serv_internet_fija": [1, 2, 2, 2],
                "p15e_serv_internet_movil": [1, 1, 2, 2],
                "p15f_serv_internet_satelital": [2, 2, 2, 2],
                "indice_hacinamiento": [1.0, 1.2, 3.5, 3.8],
                "n_personas_hogar": [2, 3, 5, 6],
                "n_18_mas": [2, 2, 2, 2],
                "prom_escolaridad18_micro": [18.0, 16.0, 8.0, 7.0],
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
                "n_per": [5, 11],
                "n_serv_compu": [2, 0],
                "n_internet": [2, 0],
                "n_viv_hacinadas": [0, 2],
                "prom_escolaridad18": [17.0, 7.5],
                "n_discapacidad": [0, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 0],
            }
        )

        assigned = assign_households_softmax_quota(household_base, manzent_targets, tau=0.15, seed=7)

        self.assertEqual(set(assigned.loc[assigned["MANZENT"] == "m_high", "hogar_uid"]), {"h1", "h2"})
        self.assertEqual(set(assigned.loc[assigned["MANZENT"] == "m_low", "hogar_uid"]), {"h3", "h4"})


if __name__ == "__main__":
    unittest.main()
