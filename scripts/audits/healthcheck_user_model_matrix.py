"""Health-check de la matriz usuario-feature supervisada.

Audita user_model_matrix_<...>.parquet para decidir si está sana para
modelar. NO modifica nada: solo lee y escribe reportes CSV/JSON.

Cubre:
  - sanity de versión (columnas nuevas presentes, viejas ausentes);
  - integridad (filas, id única, distribución target vs esperado);
  - por columna: dtype, missing, n_unique, min/max/mean/std, %ceros,
    %moda dominante (degeneradas), outliers |z|>5;
  - colinealidad: pares |r|>UMBRAL entre numéricas;
  - chequeo de leakage: |corr(feature, target)| > 0.99;
  - por feature-set (del JSON): missing máximo, complete-case, columnas que
    requieren imputación, columnas faltantes, constantes;
  - cobertura post-join para variables de carga BIP y franjas etarias censales.

Uso (en la Mac, con larch-env que resuelve el symlink a KINGSTON):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/audits/healthcheck_user_model_matrix.py \
      --scope interannual_ml --variant clean --home-filter alta --min-trips 3

Outputs: tmp/audits/user_level_redesign/healthcheck_user_model_matrix_*.csv|json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

# Esperado según notes.md (panel limpio + home_alta + n_viajes>=3).
EXPECTED_TARGET = {"BIP": 2_082_769, "QR_OTHER": 324_421, "QR_RED": 53_074}
EXPECTED_ROWS = 2_460_264

# Columnas que DEBEN existir en la versión corregida del builder.
VERSION_MARKERS_PRESENT = [
    "hyb_recent_hora_std",
    "hyb_low_intensity_hora_std",
    "hyb_educ_early_late_cont",
    "hyb_oriente_educ_cont",
]
# Columnas de la versión VIEJA que NO deben existir (leakage / renombradas).
VERSION_MARKERS_ABSENT = [
    "service_route_early_late_rcs_imp_median",
    "coarse_route_early_late_rcs_imp_median",
    "service_route_rcs_2024_2025_imp_median",
    "educ_q5",
    "high_hora_std_q4_q5",
    "origin_top1_university_high_dummy",
    "res_share_mujeres_z_winsor_p01_p99",
    "hyb_recent_high_hora_std",
    "hyb_low_intensity_high_hora_std",
    "hyb_oriente_educ_q5",
    "hyb_educ_q5_early_late_rcs",
]

# Columnas no-feature (no auditar como features de modelo).
ID_TARGET = {"id_tarjeta", "tipo_tarjeta", "is_qr", "is_qr_red",
             "is_qr_other", "target_conflict_flag"}
# zona_hogar/origin_zone_top1/activity_zone_top1 son IDs de zona (alta cardinalidad).
ID_ZONES = {"zona_hogar", "origin_zone_top1", "activity_zone_top1"}

COLLIN_THRESHOLD = 0.80
LEAKAGE_THRESHOLD = 0.99
OUTLIER_Z = 5.0


def matrix_path(scope, variant, home_filter, min_trips):
    return USER_DIR / f"user_model_matrix_{scope}_{variant}_{home_filter}_n{min_trips}.parquet"


def feature_sets_path(scope, variant, home_filter, min_trips):
    return USER_DIR / f"user_model_matrix_feature_sets_{scope}_{variant}_{home_filter}_n{min_trips}.json"


def out_path(scope, variant, home_filter, min_trips, stem, ext="csv"):
    return USER_DIR / f"healthcheck_user_model_matrix_{stem}_{scope}_{variant}_{home_filter}_n{min_trips}.{ext}"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def check_version(cols: set[str]) -> list[dict]:
    rows = []
    for c in VERSION_MARKERS_PRESENT:
        rows.append({"marker": c, "kind": "must_be_present",
                     "ok": c in cols, "found": c in cols})
    for c in VERSION_MARKERS_ABSENT:
        rows.append({"marker": c, "kind": "must_be_absent",
                     "ok": c not in cols, "found": c in cols})
    return rows


def column_profile(df: pl.DataFrame, feature_cols: list[str]) -> pl.DataFrame:
    n = df.height
    rows = []
    for c in feature_cols:
        s = df[c]
        dt = str(s.dtype)
        n_missing = int(s.null_count())
        n_unique = int(s.n_unique())
        rec = {
            "feature": c, "dtype": dt, "n_missing": n_missing,
            "missing_rate": n_missing / n, "n_unique": n_unique,
            "is_constant": n_unique <= 1,
        }
        if s.dtype.is_numeric():
            arr = s.drop_nulls().to_numpy().astype(np.float64)
            if arr.size:
                rec["min"] = float(np.min(arr))
                rec["max"] = float(np.max(arr))
                rec["mean"] = float(np.mean(arr))
                rec["std"] = float(np.std(arr))
                rec["pct_zero"] = float(np.mean(arr == 0))
                # moda dominante
                vals, counts = np.unique(arr, return_counts=True)
                rec["mode_share"] = float(counts.max() / arr.size)
                # outliers |z|>OUTLIER_Z
                if rec["std"] and rec["std"] > 0:
                    z = np.abs((arr - rec["mean"]) / rec["std"])
                    rec["n_outliers_z5"] = int(np.sum(z > OUTLIER_Z))
                    rec["outlier_rate_z5"] = float(np.mean(z > OUTLIER_Z))
                else:
                    rec["n_outliers_z5"] = 0
                    rec["outlier_rate_z5"] = 0.0
        rows.append(rec)
    return pl.DataFrame(rows)


def collinearity(df: pl.DataFrame, feature_cols: list[str]) -> pl.DataFrame:
    num = [c for c in feature_cols
           if df[c].dtype.is_numeric() and df[c].n_unique() > 1]
    if len(num) < 2:
        return pl.DataFrame({"feat_a": [], "feat_b": [], "pearson_r": []})
    # Matriz numérica con NaN -> usar pandas para corr pairwise (maneja NaN).
    pdf = df.select(num).to_pandas()
    corr = pdf.corr(method="pearson", numeric_only=True)
    pairs = []
    cols = corr.columns.tolist()
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            r = corr.iloc[i, j]
            if r is not None and not np.isnan(r) and abs(r) >= COLLIN_THRESHOLD:
                pairs.append({"feat_a": cols[i], "feat_b": cols[j],
                              "pearson_r": float(r)})
    pairs.sort(key=lambda d: -abs(d["pearson_r"]))
    return pl.DataFrame(pairs) if pairs else pl.DataFrame(
        {"feat_a": [], "feat_b": [], "pearson_r": []})


def load_feature_sets(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return payload.get("feature_sets", {})


def feature_cols_from_sets(fsets: dict[str, list[str]], cols: set[str]) -> list[str]:
    if not fsets:
        return sorted(cols - ID_TARGET - ID_ZONES)
    return sorted({feature for features in fsets.values() for feature in features if feature in cols})


def leakage_check(df: pl.DataFrame, feature_cols: list[str], target_cols: list[str]) -> pl.DataFrame:
    rows = []
    for target in target_cols:
        if target not in df.columns:
            continue
        y = df[target].to_numpy().astype(np.float64)
        for c in feature_cols:
            if not df[c].dtype.is_numeric():
                continue
            x = df[c].to_numpy().astype(np.float64)
            mask = ~np.isnan(x)
            if mask.sum() < 2:
                continue
            xx, yy = x[mask], y[mask]
            if np.std(xx) == 0:
                continue
            r = np.corrcoef(xx, yy)[0, 1]
            if abs(r) >= LEAKAGE_THRESHOLD:
                rows.append({"target": target, "feature": c, "corr_with_target": float(r)})
    return pl.DataFrame(rows) if rows else pl.DataFrame(
        {"target": [], "feature": [], "corr_with_target": []})


def feature_set_health(df: pl.DataFrame, fsets: dict, cols: set[str]) -> pl.DataFrame:
    n = df.height
    rows = []
    for name, feats in fsets.items():
        present = [f for f in feats if f in cols]
        missing_cols = [f for f in feats if f not in cols]
        needs_imput = []
        max_missing = 0.0
        constants = []
        for f in present:
            s = df[f]
            mr = s.null_count() / n
            if mr > 0:
                needs_imput.append(f)
            max_missing = max(max_missing, mr)
            if s.n_unique() <= 1:
                constants.append(f)
        complete_case_rows = 0
        if present:
            complete_case_rows = int(
                df.select(
                    pl.all_horizontal(*(pl.col(f).is_not_null() for f in present))
                    .sum()
                    .alias("n_complete")
                ).item()
            )
        rows.append({
            "feature_set": name,
            "n_declared": len(feats),
            "n_present": len(present),
            "n_missing_cols": len(missing_cols),
            "missing_cols": ";".join(missing_cols),
            "max_missing_rate": round(max_missing, 4),
            "complete_case_rows": complete_case_rows,
            "complete_case_share": round(complete_case_rows / n, 4),
            "n_cols_need_imputation": len(needs_imput),
            "cols_need_imputation": ";".join(needs_imput),
            "n_constant_cols": len(constants),
            "constant_cols": ";".join(constants),
        })
    return pl.DataFrame(rows)


def join_coverage(df: pl.DataFrame) -> pl.DataFrame:
    groups = {
        "bip_load_access": sorted(c for c in df.columns if "bip_load_" in c),
        "censo_age_bands": sorted(c for c in df.columns if c.startswith("res_age_share_")),
    }
    rows = []
    n = df.height
    for group, cols in groups.items():
        for c in cols:
            n_missing = int(df[c].null_count())
            rows.append(
                {
                    "group": group,
                    "feature": c,
                    "n_missing": n_missing,
                    "missing_rate": n_missing / n,
                    "n_non_missing": n - n_missing,
                    "non_missing_rate": 1 - (n_missing / n),
                }
            )
    return pl.DataFrame(rows) if rows else pl.DataFrame(
        {
            "group": [],
            "feature": [],
            "n_missing": [],
            "missing_rate": [],
            "n_non_missing": [],
            "non_missing_rate": [],
        }
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    args = ap.parse_args()

    mpath = matrix_path(args.scope, args.variant, args.home_filter, args.min_trips)
    fpath = feature_sets_path(args.scope, args.variant, args.home_filter, args.min_trips)
    if not mpath.exists():
        raise FileNotFoundError(f"No existe matriz: {mpath}\n¿KINGSTON montado?")

    df = pl.read_parquet(mpath)
    cols = set(df.columns)
    n = df.height
    if fpath.exists():
        fsets = load_feature_sets(fpath)
    else:
        print(f"⚠️ no se encontró JSON de feature-sets: {fpath.name}")
        fsets = {}
    section(f"MATRIZ: {mpath.name}")
    print(f"filas={n:,}  columnas={len(df.columns)}")

    # --- versión ---
    section("1) SANITY DE VERSIÓN")
    ver = check_version(cols)
    ver_bad = [r for r in ver if not r["ok"]]
    for r in ver:
        flag = "OK " if r["ok"] else "!! "
        print(f"  {flag}{r['kind']:16s} {r['marker']} (found={r['found']})")
    if ver_bad:
        print(f"\n  ⚠️ {len(ver_bad)} marcadores de versión fallan. "
              "¿El parquet es del builder corregido?")
    else:
        print("\n  ✅ Versión consistente con el builder corregido.")

    # --- integridad ---
    section("2) INTEGRIDAD Y TARGET")
    n_unique_id = df["id_tarjeta"].n_unique()
    print(f"  id_tarjeta única: {n_unique_id:,} / {n:,} "
          f"({'OK' if n_unique_id == n else '!! DUPLICADOS'})")
    print(f"  filas esperadas (notes): {EXPECTED_ROWS:,} "
          f"({'OK' if n == EXPECTED_ROWS else 'DIFIERE'})")
    tdist = (df.group_by("tipo_tarjeta").len().sort("tipo_tarjeta"))
    print("  distribución target:")
    target_rows = []
    for row in tdist.iter_rows(named=True):
        k, v = row["tipo_tarjeta"], row["len"]
        exp = EXPECTED_TARGET.get(k)
        match = "OK" if exp == v else f"esperado {exp:,}" if exp else "inesperado"
        print(f"    {k:10s} {v:>10,}  ({match})")
        target_rows.append({"tipo_tarjeta": k, "n": v,
                            "expected": exp, "match": exp == v})

    feature_cols = feature_cols_from_sets(fsets, cols)
    if fsets:
        print(f"  universo de features: union de feature_sets.json ({len(feature_cols)} columnas)")
    else:
        print("  universo de features: fallback a todas las no-target/no-zona")

    # --- perfil por columna ---
    section("3) PERFIL POR COLUMNA")
    prof = column_profile(df, feature_cols)
    n_const = prof.filter(pl.col("is_constant")).height
    n_high_missing = prof.filter(pl.col("missing_rate") > 0.30).height
    n_any_missing = prof.filter(pl.col("missing_rate") > 0).height
    print(f"  features perfiladas: {len(feature_cols)}")
    print(f"  constantes/degeneradas: {n_const}")
    print(f"  con missing>0: {n_any_missing}")
    print(f"  con missing>30%: {n_high_missing}")
    if n_const:
        print("  ⚠️ constantes:",
              prof.filter(pl.col("is_constant"))["feature"].to_list())
    top_missing = prof.sort("missing_rate", descending=True).head(10)
    print("  top-10 missing:")
    for r in top_missing.iter_rows(named=True):
        if r["missing_rate"] > 0:
            print(f"    {r['feature']:45s} {r['missing_rate']:.4f}")

    # --- colinealidad ---
    section(f"4) COLINEALIDAD (|r|>={COLLIN_THRESHOLD})")
    collin = collinearity(df, feature_cols)
    print(f"  pares colineales: {collin.height}")
    for r in collin.head(20).iter_rows(named=True):
        print(f"    {r['feat_a']:38s} ~ {r['feat_b']:38s}  r={r['pearson_r']:+.3f}")
    if collin.height > 20:
        print(f"    ... (+{collin.height - 20} más en el CSV)")

    # --- leakage ---
    target_cols = ["is_qr", "is_qr_other", "is_qr_red"]
    section(f"5) LEAKAGE (|corr con targets|>={LEAKAGE_THRESHOLD})")
    leak = leakage_check(df, feature_cols, target_cols)
    if leak.height == 0:
        print("  ✅ ninguna feature correlaciona casi-perfecto con is_qr/is_qr_other/is_qr_red.")
    else:
        print(f"  ⚠️ {leak.height} features sospechosas de leakage:")
        for r in leak.iter_rows(named=True):
            print(f"    {r['target']:12s} {r['feature']:45s} r={r['corr_with_target']:+.4f}")

    # --- feature sets ---
    section("6) SALUD POR FEATURE-SET")
    fs_health = feature_set_health(df, fsets, cols) if fsets else pl.DataFrame()
    if fs_health.height:
        for r in fs_health.iter_rows(named=True):
            ready = "LISTO logit" if r["max_missing_rate"] == 0 and r["n_constant_cols"] == 0 else "requiere imputación/revisión"
            print(f"  {r['feature_set']:32s} present={r['n_present']:>3}/{r['n_declared']:<3} "
                  f"maxMiss={r['max_missing_rate']:.3f} needImput={r['n_cols_need_imputation']:>2} "
                  f"complete={r['complete_case_share']:.3f} const={r['n_constant_cols']}  -> {ready}")

    # --- cobertura joins ---
    section("7) COBERTURA POST-JOIN BIP / FRANJAS ETARIAS")
    coverage = join_coverage(df)
    if coverage.height == 0:
        print("  ⚠️ no se encontraron columnas *_bip_load_* ni res_age_share_*.")
    else:
        for group in ["bip_load_access", "censo_age_bands"]:
            group_df = coverage.filter(pl.col("group") == group)
            if group_df.height == 0:
                print(f"  {group}: sin columnas")
                continue
            max_row = group_df.sort("missing_rate", descending=True).row(0, named=True)
            print(
                f"  {group}: cols={group_df.height} max_missing={max_row['missing_rate']:.4f} "
                f"({max_row['feature']})"
            )

    # --- escribir CSVs ---
    prof.write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "column_profile"))
    collin.write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "collinearity"))
    leak.write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "leakage"))
    pl.DataFrame(ver).write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "version"))
    pl.DataFrame(target_rows).write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "target"))
    if fs_health.height:
        fs_health.write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "feature_set_health"))
    coverage.write_csv(out_path(args.scope, args.variant, args.home_filter, args.min_trips, "join_coverage"))

    section("RESUMEN")
    verdict_ok = (not ver_bad) and (n_unique_id == n) and (leak.height == 0)
    print(f"  versión OK: {not ver_bad}")
    print(f"  id única:   {n_unique_id == n}")
    print(f"  sin leakage casi-perfecto: {leak.height == 0}")
    print(f"  constantes: {n_const}  |  features con missing: {n_any_missing}  |  pares colineales: {collin.height}")
    print(f"\n  {'✅ MATRIZ SANA (revisar missing/colinealidad para logit)' if verdict_ok else '⚠️ REVISAR BANDERAS ARRIBA'}")
    print(f"\n  CSVs escritos en: {USER_DIR}")


if __name__ == "__main__":
    main()
