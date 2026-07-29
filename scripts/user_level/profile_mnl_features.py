"""Perfilado descriptivo de las variables del MNL main a nivel id_tarjeta.

Objetivo: mostrar la DISTRIBUCIÓN de cada variable del set x_i, sin proponer
transformaciones. Las transformaciones se deciden mirando este reporte en
conjunto (usuario + análisis), no con reglas automáticas. El script solo
describe; no fija ni sugiere nada.

Set x_i del MNL main (cerrado con el usuario, 2026-06-02):
  - Exposición/cohorte: n_viajes, share_trips_2025
  - Uso/conductual: hora_mean, hora_std, share_lab_pm, share_lab_pt,
    share_no_lab, share_trips_with_transfer, share_trips_solo_metro,
    share_trips_metro_bus, t_vehiculo_mean_min, t_espera_ini_mean_min
  - Geografía: home_macrozone, origin_top1_macrozone (categóricas)
  - Socio (ya en z): res_share_cine18_universitaria_o_mas_micro_z (educación),
    res_eod2012_share_hogares_de_income_proxy_z (D+E), res_age_share_25_44,
    res_age_share_18_24, res_share_asistencia_parv_z (parv),
    res_share_inmigrantes_z

Universo: interannual_ml_clean + home_alta + n_viajes>=3 (matriz main).

Uso (en la Mac con larch-env; el symlink a KINGSTON se resuelve allí):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/user_level/profile_mnl_features.py

Output: tmp/audits/user_level_redesign/mnl_feature_profile_<suffix>.csv
        tmp/audits/user_level_redesign/mnl_feature_profile_macrozona_<suffix>.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import polars as pl
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

EXPOSURE = ["n_viajes", "share_trips_2025"]
USE_SHARES = [
    "share_lab_pm", "share_lab_pt", "share_no_lab",
    "share_trips_with_transfer", "share_trips_solo_metro", "share_trips_metro_bus",
]
USE_HORA = ["hora_mean", "hora_std"]
USE_TIEMPOS = ["t_vehiculo_mean_min", "t_espera_ini_mean_min"]
SOCIO_Z = [
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
    "res_age_share_25_44", "res_age_share_18_24",
    "res_share_asistencia_parv_z", "res_share_inmigrantes_z",
]
# La geografía está one-hot en la matriz (dummies 0/1), no como categórica.
# CENTRO (NMACROZONA=4, comuna Santiago) se agregó al builder el 2026-06-02;
# antes faltaba y dejaba ~12% de tarjetas sin dummy.
MACRO_LEVELS = ["norte", "poniente", "oriente", "centro", "sur", "suroriente", "externa_especial"]
MACRO_DUMMY_GROUPS = {
    "home_macro": [f"home_macro_{lvl}" for lvl in MACRO_LEVELS],
    "origin_top1_macro": [f"origin_top1_macro_{lvl}" for lvl in MACRO_LEVELS],
}

# Familia a la que pertenece cada variable, solo para ordenar el reporte.
FAMILY = {}
for v in EXPOSURE:
    FAMILY[v] = "exposicion"
for v in USE_SHARES:
    FAMILY[v] = "uso_share"
for v in USE_HORA:
    FAMILY[v] = "uso_hora"
for v in USE_TIEMPOS:
    FAMILY[v] = "uso_tiempo"
for v in SOCIO_Z:
    FAMILY[v] = "socio_z"

NUMERIC_VARS = EXPOSURE + USE_SHARES + USE_HORA + USE_TIEMPOS + SOCIO_Z


def matrix_path(scope, variant, home_filter, min_trips):
    return USER_DIR / f"user_model_matrix_{scope}_{variant}_{home_filter}_n{min_trips}.parquet"


def text_histogram(arr, bins=20, width=50):
    """Histograma ASCII para ver la forma de la distribución en consola."""
    lo, hi = np.min(arr), np.max(arr)
    if lo == hi:
        return [f"  [todo en {lo:.4g}]"]
    counts, edges = np.histogram(arr, bins=bins)
    peak = counts.max() or 1
    lines = []
    for i in range(bins):
        bar = "#" * int(round(width * counts[i] / peak))
        lines.append(f"  {edges[i]:>9.3g}|{bar} {counts[i]}")
    return lines


def profile_numeric(df, name):
    s = df[name]
    n = df.height
    n_missing = int(s.null_count())
    arr = s.drop_nulls().to_numpy().astype(np.float64)
    if arr.size == 0:
        return None, None
    qs = np.percentile(arr, [0, 1, 5, 25, 50, 75, 95, 99, 100])
    rec = {
        "variable": name,
        "familia": FAMILY.get(name, "?"),
        "n_missing": n_missing,
        "missing_rate": round(n_missing / n, 4),
        "n_unique": int(np.unique(arr).size),
        "min": round(float(qs[0]), 4), "p1": round(float(qs[1]), 4),
        "p5": round(float(qs[2]), 4), "p25": round(float(qs[3]), 4),
        "median": round(float(qs[4]), 4), "p75": round(float(qs[5]), 4),
        "p95": round(float(qs[6]), 4), "p99": round(float(qs[7]), 4),
        "max": round(float(qs[8]), 4),
        "mean": round(float(np.mean(arr)), 4), "std": round(float(np.std(arr)), 4),
        "frac_zero": round(float(np.mean(arr == 0)), 4),
        "frac_one": round(float(np.mean(arr == 1)), 4),
        "skew": round(float(stats.skew(arr)) if arr.size > 2 else 0.0, 3),
        "kurtosis": round(float(stats.kurtosis(arr)) if arr.size > 2 else 0.0, 2),
    }
    return rec, arr


def profile_macro_group(df, group_name, dummy_cols):
    """Cuenta volumen por macrozona sumando dummies one-hot 0/1.
    Devuelve (group_name, [(nivel, n, share)]) ordenado por volumen, o None."""
    present = [c for c in dummy_cols if c in df.columns]
    if not present:
        return None
    n = df.height
    rows = []
    for c in present:
        cnt = int(df[c].sum())
        lvl = c.rsplit("_", 1)[-1] if not c.endswith("externa_especial") else "externa_especial"
        # nombre legible: lo que sigue al prefijo del grupo
        lvl = c[len(group_name) + 1:]
        rows.append((lvl, cnt, round(cnt / n, 4)))
    rows.sort(key=lambda r: -r[1])
    # cuántas filas no caen en ninguna dummy (NaN/missing macrozona)
    total_assigned = sum(r[1] for r in rows)
    if total_assigned < n:
        rows.append(("(sin_macrozona)", n - total_assigned, round((n - total_assigned) / n, 4)))
    return group_name, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--no-hist", action="store_true", help="omitir histogramas ASCII")
    args = ap.parse_args()

    mpath = matrix_path(args.scope, args.variant, args.home_filter, args.min_trips)
    if not mpath.exists():
        raise FileNotFoundError(f"No existe matriz: {mpath}\n¿KINGSTON montado?")
    df = pl.read_parquet(mpath)
    print(f"Matriz: {df.height:,} filas, {len(df.columns)} cols\n")

    rows = []
    missing_vars = []
    for name in NUMERIC_VARS:
        if name not in df.columns:
            missing_vars.append(name)
            continue
        rec, arr = profile_numeric(df, name)
        if rec:
            rows.append(rec)
            print("=" * 72)
            print(f"{rec['variable']}  [{rec['familia']}]")
            print(f"  missing={rec['missing_rate']:.2%}  n_unique={rec['n_unique']}  "
                  f"skew={rec['skew']}  kurt={rec['kurtosis']}")
            print(f"  frac_0={rec['frac_zero']:.2%}  frac_1={rec['frac_one']:.2%}  "
                  f"mean={rec['mean']}  std={rec['std']}")
            print(f"  min={rec['min']}  p1={rec['p1']}  p25={rec['p25']}  "
                  f"med={rec['median']}  p75={rec['p75']}  p99={rec['p99']}  max={rec['max']}")
            if not args.no_hist:
                for line in text_histogram(arr):
                    print(line)
            print()

    if missing_vars:
        print(f"⚠️ Variables del set NO presentes en la matriz: {missing_vars}\n")

    print("=" * 72)
    print("MACROZONA — volumen por nivel (dummies one-hot; para elegir referencia)")
    print("=" * 72)
    cat_rows = []
    for group_name, dummy_cols in MACRO_DUMMY_GROUPS.items():
        res = profile_macro_group(df, group_name, dummy_cols)
        if res is None:
            print(f"  ⚠️ {group_name}_* no está en la matriz")
            continue
        gname, levels = res
        print(f"\n{gname}_*:")
        for lvl, cnt, frac in levels:
            print(f"  {str(lvl):20s} {cnt:>10,}  {frac:.2%}")
            cat_rows.append({"variable": gname, "level": str(lvl), "n": cnt, "share": frac})

    USER_DIR.mkdir(parents=True, exist_ok=True)
    suffix = f"{args.scope}_{args.variant}_{args.home_filter}_n{args.min_trips}"
    pl.DataFrame(rows).write_csv(USER_DIR / f"mnl_feature_profile_{suffix}.csv")
    if cat_rows:
        pl.DataFrame(cat_rows).write_csv(USER_DIR / f"mnl_feature_profile_macrozona_{suffix}.csv")
    print(f"\n✅ Perfil descriptivo escrito en {USER_DIR}")


if __name__ == "__main__":
    main()
