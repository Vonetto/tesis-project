"""Identifica qué ZONA777 quedan sin macrozona en la matriz del MNL.

Contexto: ~12% de las tarjetas tienen zona_hogar / origin_zone_top1 presente
pero sin macrozona asignada (las 6 dummies one-hot en 0). La zona existe en
los datos de viaje pero no está en el shapefile Zonas777_V07_04_2014 que
asigna macrozona. Antes de decidir el tratamiento en el MNL, hay que saber:
¿el gap es sistemático (un grupo identificable de zonas) o aleatorio?

Este script, desde la matriz:
  - lista las ZONA777 sin macrozona (home y origin), con cuántas tarjetas;
  - rango de códigos (¿son códigos altos/periféricos?);
  - compara la distribución del target QR entre con-macro vs sin-macro
    (¿las zonas sin macro tienen QR distinto? si sí, excluirlas sesga);
  - chequea si las socio (res_*) están presentes en las filas sin macro
    (si tienen socio pero no macro, la zona existe en censo pero no en shapefile).

Uso (Mac, larch-env):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/user_level/identify_zones_without_macro.py

Output: tmp/audits/user_level_redesign/zones_without_macro_<suffix>.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

LEVELS = ["norte", "poniente", "oriente", "sur", "suroriente", "externa_especial"]
HOME_DUMMIES = [f"home_macro_{l}" for l in LEVELS]
ORIGIN_DUMMIES = [f"origin_top1_macro_{l}" for l in LEVELS]
EDUC = "res_share_cine18_universitaria_o_mas_micro_z"


def matrix_path(scope, variant, home_filter, min_trips):
    return USER_DIR / f"user_model_matrix_{scope}_{variant}_{home_filter}_n{min_trips}.parquet"


def no_macro_mask(df, dummies):
    """True donde las 6 dummies suman 0 (tratando null como 0)."""
    return df.select(
        pl.sum_horizontal([pl.col(c).fill_null(0) for c in dummies]).alias("s")
    )["s"] == 0


def analyze(df, prefix, zone_col, dummies):
    print(f"\n{'='*64}\n{prefix}: zonas sin macrozona\n{'='*64}")
    mask = no_macro_mask(df, dummies)
    sub = df.filter(mask)
    n_sub = sub.height
    print(f"tarjetas sin macrozona: {n_sub:,} ({n_sub/df.height:.2%})")

    # Zonas distintas sin macro y volumen por zona.
    by_zone = (sub.group_by(zone_col).len().sort("len", descending=True))
    n_zones = by_zone.height
    print(f"ZONA777 distintas sin macrozona: {n_zones}")
    zarr = sub[zone_col].drop_nulls().to_numpy()
    if zarr.size:
        print(f"rango de códigos ZONA777 sin macro: min={zarr.min()} max={zarr.max()}")
    print("top 15 zonas sin macro (por nº tarjetas):")
    for r in by_zone.head(15).iter_rows(named=True):
        print(f"  ZONA777={r[zone_col]:>8}  {r['len']:>8,} tarjetas")

    # ¿Tienen socio (censo) aunque no macro?
    if EDUC in df.columns:
        socio_present = int((~sub[EDUC].is_null()).sum())
        print(f"de las sin-macro, con socio res_educacion presente: "
              f"{socio_present:,} ({socio_present/n_sub:.1%})")
        print("  (si alto -> zona existe en censo pero no en shapefile macro)")

    # ¿QR distinto entre con-macro y sin-macro? (sesgo si excluimos)
    if "is_qr" in df.columns:
        qr_no = float(sub["is_qr"].mean())
        qr_yes = float(df.filter(~mask)["is_qr"].mean())
        print(f"tasa QR  sin-macro={qr_no:.4f}  con-macro={qr_yes:.4f}  "
              f"(dif={qr_no-qr_yes:+.4f})")
        if "is_qr_red" in df.columns:
            print(f"  QR_RED sin-macro={float(sub['is_qr_red'].mean()):.4f}  "
                  f"con-macro={float(df.filter(~mask)['is_qr_red'].mean()):.4f}")
    return by_zone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    args = ap.parse_args()

    mpath = matrix_path(args.scope, args.variant, args.home_filter, args.min_trips)
    if not mpath.exists():
        raise FileNotFoundError(f"No existe matriz: {mpath}\n¿KINGSTON montado?")
    df = pl.read_parquet(mpath)
    print(f"Matriz: {df.height:,} filas")

    home_zones = analyze(df, "HOME", "zona_hogar", HOME_DUMMIES)
    origin_zones = analyze(df, "ORIGIN", "origin_zone_top1", ORIGIN_DUMMIES)

    # ¿Las mismas zonas faltan en home y origin? (gap del shapefile, no del dato)
    hz = set(home_zones["zona_hogar"].to_list())
    oz = set(origin_zones["origin_zone_top1"].to_list())
    inter = hz & oz
    print(f"\n{'='*64}")
    print(f"ZONA777 sin macro en HOME: {len(hz)} | en ORIGIN: {len(oz)} | "
          f"en AMBOS: {len(inter)}")
    print("Si la mayoría coincide -> el gap es del shapefile (zonas fijas "
          "sin macrozona), no del tipo de uso. Consistente con problema de cobertura.")

    suffix = f"{args.scope}_{args.variant}_{args.home_filter}_n{args.min_trips}"
    union_zones = sorted(hz | oz)
    pl.DataFrame({"zona777_sin_macro": union_zones}).write_csv(
        USER_DIR / f"zones_without_macro_{suffix}.csv")
    print(f"\n✅ {len(union_zones)} ZONA777 sin macro escritas en "
          f"zones_without_macro_{suffix}.csv")


if __name__ == "__main__":
    main()
