"""Modelo zona-nivel — entrada jerárquica de bloques (Tier 1 + Tier 2).

Generaliza qr_zone_model_tier1.py: agrega los bloques de variables de a uno y
mide, en cada paso, cuánto suma (ΔR²) y cuánta estructura espacial queda
(Moran's I de residuos). Reproduce los números del Tier 1 como subconjunto.

Unidad = zona de residencia (zona_hogar/ZONA777). Target default = share QR 2025.
WLS ponderado por n de tarjetas; solo zonas con n >= --min-n.

Orden de bloques (de mayor a menor confianza):
  - Tier 1: ingreso (EOD), educación (Censo).
  - Tier 2: acceso BIP — distancia al punto más cercano (peor acceso si sube) y
            densidad de puntos por km2 (mejor acceso si sube), del artefacto
            oficial bip_load_access_by_zona777 (infraestructura cruda, NO fric_*).

Modelos cumulativos:
  M0 intercepto -> M1 +ingreso -> M2 +educación -> M3 +acceso_bip.

Reporta por modelo: R²/adjR² (ponderados y no), ΔR² vs paso previo, coeficientes
estandarizados con SE/t/p, y Moran de residuos. Además VIF de cada predictor en
el modelo completo (multicolinealidad).

Hipótesis Tier 2: si QR sustituye la carga física BIP, esperaríamos coeficiente
POSITIVO en distancia (peor acceso -> más QR) y NEGATIVO en densidad.

Insumos (mismos paths/columnas que 02_eda/eda_qr_vs_bip_profiles.qmd):
  - <OUT_DIR>/qr_adoption_by_residence_zone_<universo>.csv  (target).
  - EOD 2012, Censo 2024, y bip_load_access_by_zona777 por ZONA777.
  - Shapefile ZONA777 (Moran, vía build_queen_neighbors).

Salidas (en <OUT_DIR>):
  - qr_zone_model_hier_<universo>_<target>.json
  - qr_zone_model_hier_<universo>_<target>.csv   (target, covars, fitted, resid del full)

Uso:
    python scripts/audits/qr_zone_model_hierarchical.py
    python scripts/audits/qr_zone_model_hierarchical.py --min-n 50
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
from scripts.audits.qr_zone_model_tier1 import (  # noqa: E402
    CENSO_PATH,
    EDUCATION_VAR,
    EOD_PATH,
    INCOME_VAR,
    fmt_model,
    wls_fit,
)

BIP_PATH = PROJECT_ROOT / "tmp" / "audits" / "bip_load_access" / "bip_load_access_by_zona777.parquet"
BIP_DIST_VAR = "bip_load_dist_nearest_m"
BIP_DENSITY_VAR = "bip_load_density_km2"

WEIGHT_FOR_TARGET = {
    "qr_rate_2025": "n_cards_2025",
    "qr_rate_2024": "n_cards_2024",
    "delta": None,
}

# Bloques en orden de entrada: (etiqueta, [(nombre_z, columna_fuente), ...])
BLOCKS = [
    ("ingreso", [("ingreso_z", INCOME_VAR)]),
    ("educacion", [("educacion_z", EDUCATION_VAR)]),
    ("acceso_bip", [("bip_dist_z", BIP_DIST_VAR), ("bip_density_z", BIP_DENSITY_VAR)]),
]


def vif_table(P: np.ndarray, names: list[str]) -> dict:
    """VIF de cada columna estandarizada P[:,j] regresada sobre las demás."""
    out = {}
    n, k = P.shape
    for j in range(k):
        others = np.delete(P, j, axis=1)
        X = np.column_stack([np.ones(n), others])
        beta, *_ = np.linalg.lstsq(X, P[:, j], rcond=None)
        resid = P[:, j] - X @ beta
        ss_res = float(np.sum(resid**2))
        ss_tot = float(np.sum((P[:, j] - P[:, j].mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
        out[names[j]] = round(1.0 / (1.0 - r2), 3) if r2 < 1 else None
    return out


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
    for pth, nm in [
        (csv_path, "CSV diagnóstico"), (EOD_PATH, "EOD 2012"),
        (CENSO_PATH, "Censo 2024"), (BIP_PATH, "acceso BIP"),
    ]:
        if not pth.exists():
            raise FileNotFoundError(f"Falta {nm}: {pth}")

    rates = pl.read_csv(csv_path)
    eod = pl.scan_parquet(EOD_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(INCOME_VAR).cast(pl.Float64)]
    ).collect()
    censo = pl.scan_parquet(CENSO_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(EDUCATION_VAR).cast(pl.Float64)]
    ).collect()
    bip = pl.scan_parquet(BIP_PATH).select(
        [
            pl.col("ZONA777").cast(pl.Int64),
            pl.col(BIP_DIST_VAR).cast(pl.Float64),
            pl.col(BIP_DENSITY_VAR).cast(pl.Float64),
        ]
    ).collect()

    df = (
        rates.with_columns(pl.col("zona_hogar").cast(pl.Int64).alias("ZONA777"))
        .join(eod, on="ZONA777", how="left")
        .join(censo, on="ZONA777", how="left")
        .join(bip, on="ZONA777", how="left")
    )

    all_source_cols = [INCOME_VAR, EDUCATION_VAR, BIP_DIST_VAR, BIP_DENSITY_VAR]
    if args.target == "delta":
        df = df.with_columns(pl.min_horizontal("n_cards_2024", "n_cards_2025").alias("_w"))
        n_ok = (pl.col("n_cards_2024") >= args.min_n) & (pl.col("n_cards_2025") >= args.min_n)
    else:
        wcol = WEIGHT_FOR_TARGET[args.target]
        df = df.with_columns(pl.col(wcol).alias("_w"))
        n_ok = pl.col(wcol) >= args.min_n

    n_total = df.height
    cond = n_ok & pl.col(args.target).is_not_null()
    for c in all_source_cols:
        cond = cond & pl.col(c).is_not_null()
    df = df.filter(cond)
    n_used = df.height

    pdf = df.to_pandas()
    y = pdf[args.target].to_numpy(dtype=float)
    w = pdf["_w"].to_numpy(dtype=float)
    ones = np.ones_like(y)

    def zscore(col):
        a = pdf[col].to_numpy(dtype=float)
        return (a - a.mean()) / a.std(ddof=0)

    # Estandarizar todos los predictores fuente
    z = {zname: zscore(src) for _, feats in BLOCKS for (zname, src) in feats}

    neighbors = build_queen_neighbors()
    zonas = pdf["ZONA777"].astype(int).tolist()

    def resid_moran(fit):
        return morans_i(dict(zip(zonas, fit["resid"].tolist())), neighbors, args.n_perm)

    # Modelos cumulativos
    cum_feats: list[str] = []
    models_out = []
    prev_r2 = 0.0
    fits_cache = {}
    # M0
    f0 = wls_fit(ones[:, None], y, w)
    m0 = fmt_model("M0_intercepto", [], f0)
    m0["delta_r2"] = 0.0
    m0["moran_residuos"] = resid_moran(f0)
    models_out.append(m0)
    fits_cache["full"] = f0

    for label, feats in BLOCKS:
        cum_feats += [zn for (zn, _) in feats]
        X = np.column_stack([ones] + [z[zn] for zn in cum_feats])
        fit = wls_fit(X, y, w)
        name = f"M{len(models_out)}_+{label}"
        md = fmt_model(name, cum_feats, fit)
        md["delta_r2"] = round(float(fit["r2"] - prev_r2), 4)
        md["moran_residuos"] = resid_moran(fit)
        models_out.append(md)
        prev_r2 = fit["r2"]
        fits_cache["full"] = fit

    # Colinealidad / VIF del modelo completo
    full_names = cum_feats
    P = np.column_stack([z[zn] for zn in full_names])
    vifs = vif_table(P, full_names)
    corr = np.corrcoef(P, rowvar=False)
    corr_dict = {
        full_names[i]: {full_names[j]: round(float(corr[i, j]), 3) for j in range(len(full_names))}
        for i in range(len(full_names))
    }

    summary = {
        "target": args.target,
        "universo": args.home_filter,
        "min_n": args.min_n,
        "n_zonas_total_en_csv": int(n_total),
        "n_zonas_usadas": int(n_used),
        "modelos_cumulativos": models_out,
        "vif_modelo_completo": vifs,
        "correlacion_predictores": corr_dict,
        "hipotesis_tier2": "dist_nearest: coef esperado +; density: coef esperado -",
        "fuentes": {
            "ingreso": f"{INCOME_VAR} @ {EOD_PATH.name}",
            "educacion": f"{EDUCATION_VAR} @ {CENSO_PATH.name}",
            "acceso_bip": f"{BIP_DIST_VAR}, {BIP_DENSITY_VAR} @ {BIP_PATH.name}",
        },
    }

    json_out = out_dir / f"qr_zone_model_hier_{args.home_filter}_{args.target}.json"
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    full = fits_cache["full"]
    pdf_out = pdf[["ZONA777", args.target, "_w"] + all_source_cols].copy()
    pdf_out["fitted_full"] = full["yhat"]
    pdf_out["resid_full"] = full["resid"]
    csv_out = out_dir / f"qr_zone_model_hier_{args.home_filter}_{args.target}.csv"
    pdf_out.to_csv(csv_out, index=False)

    print("\n===== MODELO ZONA-NIVEL JERÁRQUICO (Tier 1 + Tier 2) =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nJSON : {json_out}")
    print(f"CSV  : {csv_out}")


if __name__ == "__main__":
    main()
