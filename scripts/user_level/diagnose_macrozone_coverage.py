"""Diagnóstico de cobertura de macrozona en la matriz del MNL.

Resuelve la contradicción: el Bloque 5 reportó ~0,32% missing de
home_macrozone (columna string), pero el conteo de dummies one-hot da
~11,6% de filas sin ninguna macrozona asignada. Este script cruza ambas
representaciones para identificar la causa antes de decidir el tratamiento.

Chequea, para home y origin_top1:
  - missing de la columna string *_macrozone (si existe en la matriz);
  - filas con las 6 dummies todas en 0;
  - filas con las 6 dummies todas null;
  - cruce string-vs-dummies (¿coinciden los faltantes?);
  - relación con zona_hogar / origin_zone_top1 null (zona faltante upstream).

Uso (Mac, larch-env):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/user_level/diagnose_macrozone_coverage.py

No escribe nada; solo imprime. Diagnóstico puro.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

LEVELS = ["norte", "poniente", "oriente", "sur", "suroriente", "externa_especial"]
GROUPS = {
    "home": ("home_macrozone", "zona_hogar", [f"home_macro_{l}" for l in LEVELS]),
    "origin_top1": ("origin_top1_macrozone", "origin_zone_top1",
                    [f"origin_top1_macro_{l}" for l in LEVELS]),
}


def matrix_path(scope, variant, home_filter, min_trips):
    return USER_DIR / f"user_model_matrix_{scope}_{variant}_{home_filter}_n{min_trips}.parquet"


def diagnose_group(df, prefix, str_col, zone_col, dummy_cols):
    n = df.height
    print(f"\n{'='*64}\nGRUPO: {prefix}\n{'='*64}")
    present_dummies = [c for c in dummy_cols if c in df.columns]
    print(f"dummies presentes: {len(present_dummies)}/6")

    # ¿existe la columna string?
    if str_col in df.columns:
        miss_str = df[str_col].null_count()
        print(f"{str_col} (string) missing: {miss_str:,} ({miss_str/n:.2%})")
        # distribución de valores string
        vc = df.group_by(str_col).len().sort("len", descending=True)
        print(f"  valores string distintos: {vc.height}")
    else:
        print(f"⚠️ columna string {str_col} NO está en la matriz "
              "(la geografía vive solo como dummies).")

    if not present_dummies:
        print("⚠️ no hay dummies para analizar.")
        return

    # suma horizontal de dummies (ignora nulls como 0 si usamos fill_null).
    sum_raw = df.select(
        pl.sum_horizontal([pl.col(c) for c in present_dummies]).alias("s")
    )["s"]
    # filas donde todas las dummies son null
    all_null = df.select(
        pl.all_horizontal([pl.col(c).is_null() for c in present_dummies]).alias("an")
    )["an"]
    n_all_null = int(all_null.sum())
    # filas donde la suma (tratando null como 0) es exactamente 0 pero no todas null
    sum_filled = df.select(
        pl.sum_horizontal([pl.col(c).fill_null(0) for c in present_dummies]).alias("s")
    )["s"]
    n_sum_zero = int((sum_filled == 0).sum())
    n_sum_one = int((sum_filled == 1).sum())
    n_sum_gt1 = int((sum_filled > 1).sum())

    print(f"filas suma_dummies==1 (bien asignada): {n_sum_one:,} ({n_sum_one/n:.2%})")
    print(f"filas suma_dummies==0 (sin macrozona): {n_sum_zero:,} ({n_sum_zero/n:.2%})")
    print(f"  de esas, TODAS las dummies null: {n_all_null:,} ({n_all_null/n:.2%})")
    print(f"  (suma 0 con dummies=0 no-null): {n_sum_zero - n_all_null:,}")
    if n_sum_gt1:
        print(f"⚠️ filas suma_dummies>1 (mal, doble asignación): {n_sum_gt1:,}")

    # ¿la zona upstream está null?
    if zone_col in df.columns:
        zmiss = int(df[zone_col].null_count())
        print(f"{zone_col} null (zona faltante upstream): {zmiss:,} ({zmiss/n:.2%})")
        # cruce: de las filas sin macrozona, ¿cuántas tienen zona null?
        mask_no_macro = (sum_filled == 0)
        zone_null_among_no_macro = int(
            df.filter(mask_no_macro)[zone_col].null_count()
        )
        n_no_macro = int(mask_no_macro.sum())
        if n_no_macro:
            print(f"  de las {n_no_macro:,} sin macrozona, {zone_null_among_no_macro:,} "
                  f"({zone_null_among_no_macro/n_no_macro:.1%}) tienen {zone_col} null")
            print(f"  -> {n_no_macro - zone_null_among_no_macro:,} tienen zona PRESENTE "
                  "pero sin macrozona en el lookup (zona fuera de cobertura macro).")


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
    print(f"Matriz: {df.height:,} filas, {len(df.columns)} cols")
    # listar columnas relacionadas a macrozona/zona para contexto
    rel = [c for c in df.columns if "macro" in c or "zona" in c or "zone" in c]
    print(f"columnas geo/zona en la matriz: {rel}")

    for prefix, (str_col, zone_col, dummy_cols) in GROUPS.items():
        diagnose_group(df, prefix, str_col, zone_col, dummy_cols)


if __name__ == "__main__":
    main()
