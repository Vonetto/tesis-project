import unittest

import pandas as pd

from lib.censo2024_spatialize_profile_discrete import (
    PROFILE_CODES,
    allocate_profile_counts_to_manzanas,
    assign_households_profile_discrete_quota,
    encode_household_profiles,
    scale_integer_quotas_capped,
)


class ScaleIntegerQuotasCappedTest(unittest.TestCase):
    def test_scales_to_exact_total_without_exceeding_caps(self):
        weights = pd.Series([4.0, 2.0, 1.0], index=["a", "b", "c"])
        caps = pd.Series([2, 3, 10], index=["a", "b", "c"])
        out = scale_integer_quotas_capped(weights, target_total=5, caps=caps)

        self.assertEqual(int(out.sum()), 5)
        self.assertTrue((out <= caps).all())
        self.assertEqual(out.to_dict(), {"a": 2, "b": 2, "c": 1})


class AllocateProfileCountsToManzanasTest(unittest.TestCase):
    def test_allocates_exact_profile_totals_and_fills_capacity(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": [f"h{i}" for i in range(1, 7)],
                "comuna": ["13101"] * 6,
                "p15b_serv_compu": [1, 1, 2, 2, 2, 1],
                "p15d_serv_internet_fija": [1, 2, 2, 2, 2, 2],
                "p15e_serv_internet_movil": [1, 1, 2, 2, 2, 1],
                "p15f_serv_internet_satelital": [2, 2, 2, 2, 2, 2],
                "indice_hacinamiento": [1.0, 1.0, 3.0, 3.2, 1.2, 1.1],
                "n_personas_hogar": [2, 2, 5, 6, 3, 2],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["m1", "m2"],
                "n_hog": [3, 3],
                "n_per": [6, 15],
                "n_internet": [3, 1],
                "n_serv_compu": [3, 0],
                "n_viv_hacinadas": [0, 2],
                "prom_escolaridad18": [16.0, 8.0],
                "n_discapacidad": [0, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 0],
            }
        )

        alloc = allocate_profile_counts_to_manzanas(household_base, manzent_targets)
        profile_cols = [c for c in alloc.columns if c.startswith("profile_quota_")]
        hh_profiles = encode_household_profiles(household_base)["profile_code"].value_counts()

        self.assertEqual(int(alloc["quota_hogares_scaled"].sum()), len(household_base))
        self.assertEqual(int(alloc["remaining_capacity"].sum()), 0)
        for code in PROFILE_CODES:
            self.assertEqual(int(alloc[f"profile_quota_{code}"].sum()), int(hh_profiles.get(code, 0)))
        self.assertTrue(((alloc[profile_cols].sum(axis=1)) == alloc["quota_hogares_scaled"]).all())


class AssignHouseholdsProfileDiscreteQuotaTest(unittest.TestCase):
    def test_assigns_actual_households_with_exact_profile_counts(self):
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
                "n_internet": [2, 0],
                "n_serv_compu": [2, 0],
                "n_viv_hacinadas": [0, 2],
                "prom_escolaridad18": [17.0, 7.5],
                "n_discapacidad": [0, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 0],
            }
        )

        assigned = assign_households_profile_discrete_quota(household_base, manzent_targets, seed=7)
        assigned_profiles = encode_household_profiles(assigned)[["hogar_uid", "profile_code"]]
        assigned_counts = (
            assigned.groupby("MANZENT", dropna=False)["assigned_profile_code"]
            .value_counts()
            .unstack(fill_value=0)
        )

        self.assertEqual(int(assigned.groupby("MANZENT").size().sum()), 4)
        self.assertEqual(set(assigned.loc[assigned["MANZENT"] == "m_high", "hogar_uid"]), {"h1", "h2"})
        self.assertEqual(set(assigned.loc[assigned["MANZENT"] == "m_low", "hogar_uid"]), {"h3", "h4"})
        self.assertEqual(
            assigned_profiles.set_index("hogar_uid").loc["h1", "profile_code"],
            assigned.set_index("hogar_uid").loc["h1", "assigned_profile_code"],
        )
        self.assertEqual(int(assigned_counts.loc["m_high"].sum()), 2)
        self.assertEqual(int(assigned_counts.loc["m_low"].sum()), 2)


if __name__ == "__main__":
    unittest.main()
