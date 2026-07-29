"""Modelo zona-nivel — Tier 1: ingreso + educación residencial.

Primer paso del pivote a nivel zona, con entrada JERÁRQUICA de variables
(descomposición de varianza). Unidad = zona de residencia (zona_hogar/ZONA777).

Target (default): share de tarjetas QR en 2025 por zona (qr_rate_2025 del
diagnóstico). Se modela el NIVEL, no el delta (el delta ya mostró estructura
espacial débil).

Bloques Tier 1 (los de mayor confianza), entrando de a uno:
  - M0: solo intercepto (baseline; su residuo = la tasa centrada).
  - M1: + ingreso     (eod2012_ingreso_hogar_median_pct_rank, EOD 2012).
  - M2: + educación   (share_cine18_universitaria_o_mas_micro, Censo 2024).
  - M3: + ingreso + educación.

Para cada modelo reporta: R² y R² ajustado (ponderados), coeficientes
estandarizados con SE/t/p, y el Moran's I de los RESIDUOS. La caída del Moran
de M0 a M3 dice cuánta estructura espacial capturan ingreso+educación; el Moran
residual de M3 dice cuánta queda sin explicar (y si haría falta un modelo
espacial más adelante).

Decisiones (consistentes con 02_eda/eda_qr_vs_bip_profiles.qmd):
  - Mismas variables y fuentes que el EDA (mismos nombres de columna y parquet).
  - WLS ponderado por n_cards del año target: las tasas zonales tienen precisión
    heterocedástica (var ≈ p(1-p)/n); ponderar por n es lo correcto. Se reporta
    también el R² no ponderado como robustez.
  - Solo zonas con n_cards >= --min-n (default 30), igual que el diagnóstico.
  - Ingreso y educación se estandarizan (z) para comparar coeficientes; se
    reporta su correlación y VIF (suelen ser colineales — caveat conocido).

Insumos:
  - <OUT_DIR>/qr_adoption_by_residence_zone_<universo>.csv  (corre antes
    qr_adoption_by_residence_zone.py si no existe).
  - EOD 2012 por zona y Censo 2024 por zona (mismos paths que el EDA).
  - Shapefile ZONA777 (para el Moran, vía build_queen_neighbors del diagnóstico).

Salidas (en <OUT_DIR>):
  - qr_zone_model_tier1_<universo>_<target>.json   (resumen de modelos)
  - qr_zone_model_tier1_<universo>_<target>.csv    (target, covars, fitted, resid)

Uso:
    python scripts/audits/qr_zone_model_tier1.py
    python scripts/audits/qr_zone_model_tier1.py --target qr_rate_2024 --min-n 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_user_level_payment_panel import OUT_DIR  # noqa: E402
from scripts.audits.qr_adoption_by_residence_zone import (  # noqa: E402
    build_queen_neighbors,
    morans_i,
)

# Mismas fuentes y columnas que el EDA (block9-sociodemographic-helpers).
EOD_PATH = PROJECT_ROOT / "data" / "processed" / "eod2012" / "eod2012_zone_features_zona777.parquet"
CENSO_PATH = (
    PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
    / "censo2024_microdata_zona777_model_ready.parquet"
)
INCOME_VAR = "eod2012_ingreso_hogar_median_pct_rank"
EDUCATION_VAR = "share_cine18_universitaria_o_mas_micro"

WEIGHT_FOR_TARGET = {
    "qr_rate_2025": "n_cards_2025",
    "qr_rate_2024": "n_cards_2024",
    "delta": None,  # se maneja aparte (min de ambos años)
}


def wls_fit(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict:
    """WLS por mínimos cuadrados ponderados. X incluye columna de intercepto."""
    from scipy import stats

    sw = np.sqrt(w)
    Xw = X * sw[:, None]
    yw = y * sw
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    yhat = X @ beta
    resid = y - yhat

    wmean = np.average(y, weights=w)
    ss_res = float(np.sum(w * resid**2))
    ss_tot = float(np.sum(w * (y - wmean) ** 2))
    n, k = X.shape
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k) if n > k else np.nan

    sigma2 = ss_res / (n - k) if n > k else np.nan
    XtWX_inv = np.linalg.inv(Xw.T @ Xw)
    se = np.sqrt(np.diag(sigma2 * XtWX_inv))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), df=n - k)

    # R2 NO ponderado (robustez)
    ss_res_u = float(np.sum(resid**2))
    ss_tot_u = float(np.sum((y - y.mean()) ** 2))
    r2_unw = 1 - ss_res_u / ss_tot_u if ss_tot_u > 0 else np.nan

    return {
        "beta": beta, "se": se, "t": t, "p": p,
        "r2": r2, "adj_r2": adj_r2, "r2_unweighted": r2_unw,
        "resid": resid, "yhat": yhat, "n": n, "k": k,
    }


def fmt_model(name: str, feat_names: list[str], fit: dict) -> dict:
    coefs = {}
    names = ["intercept"] + feat_names
    for i, nm in enumerate(names):
        coefs[nm] = {
            "beta": round(float(fit["beta"][i]), 5),
            "se": round(float(fit["se"][i]), 5),
            "t": round(float(fit["t"][i]), 3),
            "p": round(float(fit["p"][i]), 5),
        }
    return {
        "modelo": name,
        "n_zonas": int(fit["n"]),
        "r2": round(float(fit["r2"]), 4),
        "adj_r2": round(float(fit["adj_r2"]), 4),
        "r2_no_ponderado": round(float(fit["r2_unweighted"]), 4),
        "coeficientes": coefs,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--target", default="qr_rate_2025", choices=list(WEIGHT_FOR_TARGET))
    ap.add_argument("--min-n", type=int, default=30)
    ap.add_argument("--n-perm", type=int, default=999)
    args = ap.parse_args()

    import polars as pl

    out_dir = Path(OUT_DIR)
    csv_path = out_dir / f"qr_adoption_by_residence_zone_{args.home_filter}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"No existe el CSV del diagnóstico: {csv_path}\n"
            f"Córrelo primero: python scripts/audits/qr_adoption_by_residence_zone.py "
            f"--home-filter {args.home_filter}"
        )
    for pth, nm in [(EOD_PATH, "EOD 2012"), (CENSO_PATH, "Censo 2024")]:
        if not pth.exists():
            raise FileNotFoundError(f"Falta artefacto {nm}: {pth}")

    rates = pl.read_csv(csv_path)
    eod = pl.scan_parquet(EOD_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(INCOME_VAR).cast(pl.Float64)]
    )
    censo = pl.scan_parquet(CENSO_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(EDUCATION_VAR).cast(pl.Float64)]
    )
    for lf, var in [(eod, INCOME_VAR), (censo, EDUCATION_VAR)]:
        if var not in set(lf.collect_schema().names()):
            raise ValueError(f"Falta columna {var} en su artefacto fuente.")

    df = (
        rates.with_columns(pl.col("zona_hogar").cast(pl.Int64).alias("ZONA777"))
        .join(eod.collect(), on="ZONA777", how="left")
        .join(censo.collect(), on="ZONA777", how="left")
    )

    # Peso según el año del target
    if args.target == "delta":
        df = df.with_columns(
            pl.min_horizontal("n_cards_2024", "n_cards_2025").alias("_w")
        )
        n_ok = (pl.col("n_cards_2024") >= args.min_n) & (pl.col("n_cards_2025") >= args.min_n)
    else:
        wcol = WEIGHT_FOR_TARGET[args.target]
        df = df.with_columns(pl.col(wcol).alias("_w"))
        n_ok = pl.col(wcol) >= args.min_n

    n_total = df.height
    df = df.filter(
        n_ok
        & pl.col(args.target).is_not_null()
        & pl.col(INCOME_VAR).is_not_null()
        & pl.col(EDUCATION_VAR).is_not_null()
    )
    n_used = df.height

    pdf = df.to_pandas()
    y = pdf[args.target].to_numpy(dtype=float)
    w = pdf["_w"].to_numpy(dtype=float)

    def zscore(a):
        return (a - a.mean()) / a.std(ddof=0)

    inc = zscore(pdf[INCOME_VAR].to_numpy(dtype=float))
    edu = zscore(pdf[EDUCATION_VAR].to_numpy(dtype=float))
    ones = np.ones_like(y)

    # Colinealidad ingreso-educación
    r_ie = float(np.corrcoef(inc, edu)[0, 1])
    vif = round(1.0 / (1.0 - r_ie**2), 3) if abs(r_ie) < 1 else None

    # Modelos jerárquicos
    fits = {
        "M0_intercepto": (wls_fit(ones[:, None], y, w), []),
        "M1_ingreso": (wls_fit(np.column_stack([ones, inc]), y, w), ["ingreso_z"]),
        "M2_educacion": (wls_fit(np.column_stack([ones, edu]), y, w), ["educacion_z"]),
        "M3_ingreso_educacion": (
            wls_fit(np.column_stack([ones, inc, edu]), y, w),
            ["ingreso_z", "educacion_z"],
        ),
    }

    # Moran de residuos (baseline M0 vs full M3)
    neighbors = build_queen_neighbors()
    zonas = pdf["ZONA777"].astype(int).tolist()

    def resid_moran(fit):
        vmap = dict(zip(zonas, fit["resid"].tolist()))
        return morans_i(vmap, neighbors, args.n_perm)

    moran_m0 = resid_moran(fits["M0_intercepto"][0])
    moran_m3 = resid_moran(fits["M3_ingreso_educacion"][0])

    summary = {
        "target": args.target,
        "universo": args.home_filter,
        "min_n": args.min_n,
        "n_zonas_total_en_csv": int(n_total),
        "n_zonas_usadas": int(n_used),
        "colinealidad_ingreso_educacion": {"pearson_r": round(r_ie, 4), "vif": vif},
        "modelos": [fmt_model(k, feats, fit) for k, (fit, feats) in fits.items()],
        "moran_residuos": {
            "baseline_M0_(tasa_cruda)": moran_m0,
            "full_M3": moran_m3,
        },
        "fuentes": {
            "target_csv": str(csv_path),
            "ingreso": f"{INCOME_VAR} @ {EOD_PATH.name}",
            "educacion": f"{EDUCATION_VAR} @ {CENSO_PATH.name}",
        },
    }

    json_out = out_dir / f"qr_zone_model_tier1_{args.home_filter}_{args.target}.json"
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # CSV por zona con fitted/resid del modelo full
    m3 = fits["M3_ingreso_educacion"][0]
    pdf_out = pdf[["ZONA777", args.target, "_w", INCOME_VAR, EDUCATION_VAR]].copy()
    pdf_out["fitted_M3"] = m3["yhat"]
    pdf_out["resid_M3"] = m3["resid"]
    csv_out = out_dir / f"qr_zone_model_tier1_{args.home_filter}_{args.target}.csv"
    pdf_out.to_csv(csv_out, index=False)

    print("\n===== MODELO ZONA-NIVEL TIER 1 =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nJSON : {json_out}")
    print(f"CSV  : {csv_out}")


if __name__ == "__main__":
    main()
