import unittest

from lib.transbordos_metro.reconstruction import sync_trip_level_terminals_from_legs


class SyncTripLevelTerminalsFromLegsTest(unittest.TestCase):
    def test_recomputes_trip_level_fields_from_reconstructed_legs(self):
        out = {
            "paradero_inicio_viaje": "T-20-193-NS-45",
            "zona_inicio_viaje": "999",
            "paradero_fin_viaje": "OLD_END",
            "zona_fin_viaje": "998",
        }
        legs_out = [
            {
                "paradero_subida": "SAN PABLO",
                "paradero_bajada": "SANTA ANA",
                "zona_subida": "280",
                "zona_bajada": None,
            },
            {
                "paradero_subida": "SANTA ANA",
                "paradero_bajada": "UNIVERSIDAD DE CHILE",
                "zona_subida": None,
                "zona_bajada": "755",
            },
        ]

        fixed = sync_trip_level_terminals_from_legs(out, legs_out)

        self.assertEqual(fixed["paradero_inicio_viaje"], "SAN PABLO")
        self.assertEqual(fixed["zona_inicio_viaje"], "280")
        self.assertEqual(fixed["paradero_fin_viaje"], "UNIVERSIDAD DE CHILE")
        self.assertEqual(fixed["zona_fin_viaje"], "755")


if __name__ == "__main__":
    unittest.main()
