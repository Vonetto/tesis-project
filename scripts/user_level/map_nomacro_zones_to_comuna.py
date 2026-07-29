"""Mapea las ZONA777 sin macrozona a su COMUNA, para nombrar el 'cajón'.

Contexto: las ~53 zonas sin macrozona (rango 262-309 principalmente) están
fuera del shapefile de macrozonas, pero existen en otras fuentes. Este script
intenta nombrarlas — saber a qué comuna(s) pertenecen — para que la dummy
'sin_macrozona' del MNL tenga interpretación geográfica.

Estrategia (intenta en orden, usa la primera disponible):
  1. Shapefile Zonas777 (tiene ZONA777 + COMUNA). OJO: si la zona no está en
     el shapefile justamente por eso no tiene macro, este lookup puede no
     cubrirlas — el script reporta cuáles sí/no aparecen.
  2. Lee la lista de zonas sin macro desde el CSV ya generado
     (zones_without_macro_*.csv).

Requiere el shapefile en KINGSTON (se resuelve solo en la Mac).

Uso (Mac, larch-env):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/user_level/map_nomacro_zones_to_comuna.py

Output: tmp/audits/user_level_redesign/nomacro_zones_comuna_<suffix>.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    args = ap.parse_args()

    suffix = f"{args.scope}_{args.variant}_{args.home_filter}_n{args.min_trips}"
    zlist_path = USER_DIR / f"zones_without_macro_{suffix}.csv"
    if not zlist_path.exists():
        raise FileNotFoundError(
            f"No existe {zlist_path}. Corre antes identify_zones_without_macro.py")
    nomacro = pl.read_csv(zlist_path)["zona777_sin_macro"].to_list()
    print(f"Zonas sin macro a mapear: {len(nomacro)}")
    print(f"rango: {min(nomacro)}–{max(nomacro)}")

    if not ZONAS777_SHP.exists():
        print(f"\n⚠️ Shapefile no accesible: {ZONAS777_SHP}")
        print("¿KINGSTON montado? Sin shapefile no se puede mapear a comuna aquí.")
        return

    import geopandas as gpd
    cols = ["ZONA777", "COMUNA", "NMACROZONA", "MACROZONA"]
    gdf = gpd.read_file(ZONAS777_SHP)
    have = [c for c in cols if c in gdf.columns]
    print(f"columnas del shapefile presentes: {have}")
    gdf = gdf[have].copy()
    import pandas as pd
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="coerce")
    gdf = gdf[gdf["ZONA777"].notna()]
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)

    shp_zonas = set(gdf["ZONA777"].tolist())
    en_shp = [z for z in nomacro if z in shp_zonas]
    fuera_shp = [z for z in nomacro if z not in shp_zonas]
    print(f"\nde las {len(nomacro)} zonas sin macro:")
    print(f"  presentes en el shapefile: {len(en_shp)}")
    print(f"  AUSENTES del shapefile:    {len(fuera_shp)}")
    if fuera_shp:
        print(f"  -> {sorted(fuera_shp)[:30]}{'...' if len(fuera_shp)>30 else ''}")
        print("  (estas zonas existen en los datos de viaje/censo pero NO en el "
              "shapefile 2014; por eso no tienen macrozona)")

    # Para las que SÍ están en el shapefile, ver su comuna y por qué no tienen macro.
    if en_shp and "COMUNA" in gdf.columns:
        sub = gdf[gdf["ZONA777"].isin(en_shp)]
        print("\ncomunas de las zonas sin macro que SÍ están en el shapefile:")
        vc = sub["COMUNA"].value_counts()
        for comuna, cnt in vc.items():
            print(f"  {comuna}: {cnt} zonas")
        if "NMACROZONA" in gdf.columns:
            print("\nNMACROZONA de esas zonas (para ver por qué quedaron sin macro):")
            print(sub["NMACROZONA"].value_counts(dropna=False).to_string())
        sub_out = pl.from_pandas(sub)
        sub_out.write_csv(USER_DIR / f"nomacro_zones_comuna_{suffix}.csv")
        print(f"\n✅ escrito nomacro_zones_comuna_{suffix}.csv")
    else:
        print("\n⚠️ ninguna zona sin macro está en el shapefile, o falta COMUNA.")
        print("Mapear desde otra fuente (censo zona777->comuna) si se necesita el nombre.")


if __name__ == "__main__":
    main()
