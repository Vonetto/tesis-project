import unittest

import pandas as pd

from lib.censo2024_spatialize_anneal import (
    build_commune_state,
    manzana_energy,
    refine_assignment_with_annealing,
    total_energy,
)


class AnnealRefinementTest(unittest.TestCase):
    def _toy_inputs(self):
        assigned = pd.DataFrame(
            {
                "hogar_uid": ["h1", "h2", "h3", "h4"],
                "CUT_target": ["13101"] * 4,
                "MANZENT": ["m_low", "m_low", "m_high", "m_high"],
                "n_personas_hogar_num": [2.0, 3.0, 5.0, 6.0],
                "has_compu": [1, 1, 0, 0],
                "has_internet_any": [1, 1, 0, 0],
                "is_hacinado": [0, 0, 1, 1],
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
        scaled_targets = pd.DataFrame(
            {
                "CUT": ["13101", "13101"],
                "MANZENT": ["m_high", "m_low"],
                "quota_hogares_scaled": [2, 2],
                "obj_n_per_scaled": [5, 11],
                "obj_compu_scaled": [2, 0],
                "obj_internet_scaled": [2, 0],
                "obj_hacin_scaled": [0, 2],
            }
        )
        return assigned, scaled_targets

    def test_energy_modes_differ_on_same_toy_state(self):
        assigned, scaled_targets = self._toy_inputs()

        state = build_commune_state(assigned, scaled_targets, energy_mode="count")

        count_e = total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode="count")
        share_e = total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode="share")
        hybrid_e = total_energy(state.current, state.target, state.denom, state.quota_hogares, energy_mode="hybrid")

        self.assertGreater(count_e, 0.0)
        self.assertGreater(share_e, 0.0)
        self.assertGreater(hybrid_e, 0.0)
        self.assertNotAlmostEqual(count_e, share_e)
        self.assertNotAlmostEqual(count_e, hybrid_e)
        self.assertNotAlmostEqual(share_e, hybrid_e)

        with self.assertRaises(ValueError):
            manzana_energy(state.current[0], state.target[0], state.denom, state.quota_hogares[0], energy_mode="bad")

    def test_refinement_improves_simple_toy_assignment(self):
        assigned, scaled_targets = self._toy_inputs()

        for energy_mode in ("count", "share", "hybrid"):
            state_before = build_commune_state(assigned, scaled_targets, energy_mode=energy_mode)
            initial_energy = total_energy(
                state_before.current,
                state_before.target,
                state_before.denom,
                state_before.quota_hogares,
                energy_mode=energy_mode,
            )

            refined, stats = refine_assignment_with_annealing(
                assigned=assigned,
                scaled_targets=scaled_targets,
                n_iter=200,
                seed=7,
                init_temp=0.0,
                alpha=1.0,
                sample_size=2,
                energy_mode=energy_mode,
            )

            state_after = build_commune_state(refined, scaled_targets, energy_mode=energy_mode)
            final_energy = total_energy(
                state_after.current,
                state_after.target,
                state_after.denom,
                state_after.quota_hogares,
                energy_mode=energy_mode,
            )

            self.assertLess(final_energy, initial_energy)
            self.assertEqual(set(refined.loc[refined["MANZENT"] == "m_high", "hogar_uid"]), {"h1", "h2"})
            self.assertEqual(set(refined.loc[refined["MANZENT"] == "m_low", "hogar_uid"]), {"h3", "h4"})
            self.assertGreaterEqual(int(stats["accepted_swaps"].sum()), 1)


if __name__ == "__main__":
    unittest.main()
