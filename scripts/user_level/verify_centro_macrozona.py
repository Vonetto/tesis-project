"""Verifica el valor STRING MACROZONA de las zonas sin macro (presunto CENTRO).

El builder hace: macrozone_model = MACROZONA.astype(str); dummies se prenden
solo si ese string está en [NORTE, PONIENTE, ORIENTE, SUR, SURORIENTE,
EXTERNA_ESPECIAL]. Las 48 zonas de comuna SANTIAGO con NMACROZONA=4 quedan
sin dummy. Este script imprime el valor LITERAL de MACROZONA de esas zonas
para confirmar (no inferir) qué string es — y así nombrar bien la dummy y
diseñar el fix del builder.

Uso (Mac, larch-env):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/user_level/verify_centro_macrozona.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)
BUILDER_LEVELS = ["NORTE", "PONIENTE", "ORIENTE", "SUR", "SURORIENTE", "EXTERNA_ESPECIAL"]


def main():
    import geopandas as gpd

    if not ZONAS777_SHP.exists():
        print(f"⚠️ shapefile no accesible: {ZONAS777_SHP} (¿KINGSTON montado?)")
        return

    # zonas sin macro detectadas antes
    zlist = USER_DIR / "zones_without_macro_interannual_ml_clean_alta_n3.csv"
    nomacro = set(pd.read_csv(zlist)["zona777_sin_macro"].tolist()) if zlist.exists() else set()
    print(f"zonas sin macro conocidas: {len(nomacro)}")

    gdf = gpd.read_file(ZONAS777_SHP)[["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA"]].copy()
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="coerce")
    gdf = gdf[gdf["ZONA777"].notna()]
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)

    print("\n=== Valores STRING únicos de MACROZONA en TODO el shapefile ===")
    print("(para ver qué valores existen y cuáles NO están en BUILDER_LEVELS)")
    vc = gdf["MACROZONA"].astype(str).value_counts(dropna=False)
    for val, cnt in vc.items():
        flag = "OK (tiene dummy)" if val in BUILDER_LEVELS else ">>> SIN DUMMY <<<"
        print(f"  MACROZONA={val!r:24}  NMACROZONA?  {cnt:>4} zonas   {flag}")

    print("\n=== cruce MACROZONA <-> NMACROZONA en el shapefile ===")
    print(gdf.groupby(["NMACROZONA", "MACROZONA"], dropna=False).size().to_string())

    if nomacro:
        sub = gdf[gdf["ZONA777"].isin(nomacro)]
        print(f"\n=== Las {len(sub)} zonas sin macro: su MACROZONA/NMACROZONA/COMUNA ===")
        print(sub.groupby(["MACROZONA", "NMACROZONA", "COMUNA"], dropna=False).size().to_string())
        print("\n-> El string MACROZONA de estas zonas es lo que hay que agregar a "
              "MACROZONA_DUMMY_LEVELS (o mapear) en el builder.")


if __name__ == "__main__":
    main()
