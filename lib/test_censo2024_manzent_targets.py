import tempfile
import unittest
import zipfile
from pathlib import Path

import pandas as pd

from lib.censo2024_manzent_targets import build_manzent_target_table


class BuildManzentTargetTableTest(unittest.TestCase):
    def test_reads_selected_columns_and_derives_strict_n18mas(self):
        csv_text = "\n".join(
            [
                "COD_REGION;REGION;PROVINCIA;CUT;COMUNA;AREA_C;MANZENT;COD_DISTRITO;COD_LOCALIDAD;COD_ZONA;COD_ENTIDAD;COD_MANZANA;n_per;n_hog;n_edad_18_24;n_edad_25_44;n_edad_45_59;n_edad_60_mas;prom_escolaridad18;n_discapacidad;n_analfabet",
                "13;Metropolitana;Santiago;13101;Santiago;1;1310101001;1;1;1;1;1;100;40;10;20;30;40;12,5;5;3",
                "13;Metropolitana;Santiago;13101;Santiago;1;1310101002;1;1;1;1;2;80;30;5;10;;15;11,0;4;2",
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = Path(tmpdir) / "Base_manzana_entidad_CPV24.zip"
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Base_manzana_entidad_CPV24.csv", csv_text)

            out = build_manzent_target_table(
                base_zip=zip_path,
                variables=[
                    "n_per",
                    "n_hog",
                    "n_edad_18_24",
                    "n_edad_25_44",
                    "n_edad_45_59",
                    "n_edad_60_mas",
                    "prom_escolaridad18",
                    "n_discapacidad",
                    "n_analfabet",
                ],
            )

        self.assertEqual(len(out), 2)
        self.assertAlmostEqual(out.loc[0, "prom_escolaridad18"], 12.5)
        self.assertEqual(out.loc[0, "n_18_mas"], 100.0)
        self.assertTrue(pd.isna(out.loc[1, "n_18_mas"]))
        self.assertEqual(out.loc[0, "MANZENT"], "1310101001")


if __name__ == "__main__":
    unittest.main()
