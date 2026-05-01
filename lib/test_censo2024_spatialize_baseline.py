import unittest

import pandas as pd

from lib.censo2024_spatialize_baseline import (
    aggregate_assignment_to_manzent,
    assign_households_random_quota,
    evaluate_assignment,
    scale_integer_quotas,
)


class ScaleIntegerQuotasTest(unittest.TestCase):
    def test_scales_weights_to_exact_total(self):
        weights = pd.Series([2.0, 1.0, 1.0], index=["a", "b", "c"])
        out = scale_integer_quotas(weights, target_total=10)
        self.assertEqual(int(out.sum()), 10)
        self.assertEqual(out.to_dict(), {"a": 5, "b": 3, "c": 2})

    def test_zero_weight_fallback_still_hits_exact_total(self):
        weights = pd.Series([0.0, 0.0], index=["a", "b"])
        out = scale_integer_quotas(weights, target_total=5)
        self.assertEqual(int(out.sum()), 5)
        self.assertEqual(out.to_dict(), {"a": 3, "b": 2})


class AssignHouseholdsRandomQuotaTest(unittest.TestCase):
    def test_assigns_exact_scaled_household_quotas_within_each_commune(self):
        household_base = pd.DataFrame(
            {
                "hogar_uid": [f"h{i}" for i in range(6)],
                "comuna": ["13132", "13132", "13132", "13112", "13112", "13112"],
                "n_personas_hogar": [2, 1, 3, 2, 2, 1],
                "n_18_mas": [2, 1, 2, 2, 1, 1],
                "prom_escolaridad18_micro": [18.0, 17.0, 16.0, 8.0, 9.0, 10.0],
                "n_cine_terciaria_maestria_doctorado": [2, 1, 2, 0, 0, 0],
                "n_cine_nunca_curso_primera_infancia": [0, 0, 0, 0, 0, 0],
                "n_cine_primaria": [0, 0, 0, 1, 1, 0],
                "n_cine_secundaria": [0, 0, 0, 1, 0, 1],
                "n_cine_especial_diferencial": [0, 0, 0, 0, 0, 0],
                "n_discapacidad_5mas": [0, 0, 0, 0, 1, 0],
                "n_analfabet_15mas": [0, 0, 0, 0, 0, 1],
                "n_ocupado_15mas": [2, 1, 2, 1, 1, 1],
                "n_desocupado_15mas": [0, 0, 0, 1, 0, 0],
                "n_fuera_fuerza_trabajo_15mas": [0, 0, 0, 0, 0, 0],
                "n_independiente": [0, 0, 0, 1, 0, 0],
                "n_dependiente": [2, 1, 2, 0, 1, 1],
                "n_no_remunerado": [0, 0, 0, 0, 0, 0],
            }
        )
        manzent_targets = pd.DataFrame(
            {
                "CUT": ["13132", "13132", "13112", "13112"],
                "MANZENT": ["m1", "m2", "m3", "m4"],
                "n_hog": [10, 20, 10, 20],
                "n_per": [0, 0, 0, 0],
                "n_cine_terciaria_maestria_doctorado": [0, 0, 0, 0],
            }
        )

        assigned = assign_households_random_quota(household_base, manzent_targets, seed=123)
        counts = assigned.groupby(["CUT_target", "MANZENT"]).size().to_dict()

        self.assertEqual(counts, {("13112", "m3"): 1, ("13112", "m4"): 2, ("13132", "m1"): 1, ("13132", "m2"): 2})


class EvaluateAssignmentTest(unittest.TestCase):
    def test_evaluates_prom_escolaridad18_and_cine_share(self):
        assigned = pd.DataFrame(
            {
                "CUT_target": ["13132", "13132"],
                "MANZENT": ["m1", "m1"],
                "hogar_uid": ["h1", "h2"],
                "n_personas_hogar": [2, 1],
                "n_18_mas": [2, 1],
                "prom_escolaridad18_micro": [18.0, 12.0],
                "n_discapacidad_5mas": [0, 0],
                "n_analfabet_15mas": [0, 0],
                "n_ocupado_15mas": [2, 1],
                "n_desocupado_15mas": [0, 0],
                "n_fuera_fuerza_trabajo_15mas": [0, 0],
                "n_independiente": [0, 0],
                "n_dependiente": [2, 1],
                "n_no_remunerado": [0, 0],
                "n_cine_nunca_curso_primera_infancia": [0, 0],
                "n_cine_primaria": [0, 0],
                "n_cine_secundaria": [0, 1],
                "n_cine_terciaria_maestria_doctorado": [2, 0],
                "n_cine_especial_diferencial": [0, 0],
            }
        )
        agg = aggregate_assignment_to_manzent(assigned)
        targets = pd.DataFrame(
            {
                "CUT": ["13132"],
                "MANZENT": ["m1"],
                "n_per": [3],
                "prom_escolaridad18": [16.0],
                "n_cine_terciaria_maestria_doctorado": [1],
            }
        )

        merged, metrics = evaluate_assignment(agg, targets)

        self.assertAlmostEqual(merged.loc[0, "prom_escolaridad18_recon"], 16.0)
        self.assertAlmostEqual(merged.loc[0, "share_cine_terciaria_recon"], 2 / 3)
        self.assertEqual(metrics["prom_escolaridad18_mae"], 0.0)
        self.assertAlmostEqual(metrics["share_cine_terciaria_mae"], abs((2 / 3) - (1 / 3)))


if __name__ == "__main__":
    unittest.main()
