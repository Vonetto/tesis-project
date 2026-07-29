"""Modelo espacial zona-nivel — SAR (lag) y SEM (error) sobre la adopción QR.

Cierra el arco del pivote: el modelo socioeconómico (educación) deja un Moran
residual ~0.34 fuerte y significativo. Acá estimamos modelos espaciales que
meten esa dependencia dentro del modelo.

Qué corre, sobre share QR 2025 por zona (zona_hogar), con covariables
ingreso_z + educacion_z (estandarizadas) y la W de contigüidad queen:

  1. OLS con diagnósticos espaciales:
       - Moran's I de residuos,
       - tests Lagrange Multiplier (LM-lag, LM-error y sus versiones robustas),
         que indican qué forma espacial prefieren los datos.
  2. SAR / ML_Lag: y = rho*W*y + Xb + e  (difusión: la adopción de una zona
     depende de la de sus vecinas).
  3. SEM / ML_Error: y = Xb + u, u = lambda*W*u + e  (variable omitida
     espacialmente suave; corrige inferencia).

Reporta rho/lambda con su p, los betas corregidos, pseudo-R², AIC y log-lik
para comparar, y el efecto total aproximado de educación en SAR
(beta_edu / (1 - rho)).

NOTA de método: los modelos ML aquí son NO ponderados (a diferencia de la WLS
del modelo no-espacial); se restringe a zonas con n >= --min-n para acotar la
heterocedasticidad por tamaño. El R² no ponderado del modelo no-espacial era
casi igual al ponderado (0.179 vs 0.187), así que el sesgo de no ponderar es
menor; lo central acá es rho/lambda y la caída del Moran residual.

Requiere: pip install libpysal spreg   (no están en requirements.txt).

Insumos: mismos que qr_zone_model_hierarchical.py (CSV diagnóstico + EOD + Censo
+ shapefile ZONA777 para la W).

Salida: <OUT_DIR>/qr_zone_model_spatial_<universo>_<target>.json

Uso:
    pip install libpysal spreg
    python scripts/audits/qr_zone_model_spatial.py
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
from scripts.audits.qr_adoption_by_residence_zone import build_queen_neighbors  # noqa: E402
from scripts.audits.qr_zone_model_tier1 import (  # noqa: E402
    CENSO_PATH,
    EDUCATION_VAR,
    EOD_PATH,
    INCOME_VAR,
)

WEIGHT_FOR_TARGET = {"qr_rate_2025": "n_cards_2025", "qr_rate_2024": "n_cards_2024", "delta": None}


def aligned_queen_w(zonas: list[int]):
    """W queen de libpysal alineada al subconjunto de zonas (sin islas)."""
    import libpysal

    neigh_all = build_queen_neighbors()
    zonas = [int(z) for z in zonas]
    while True:
        zset = set(zonas)
        neigh = {z: sorted(nb for nb in neigh_all.get(z, []) if nb in zset) for z in zonas}
        islands = [z for z in zonas if not neigh[z]]
        if not islands:
            break
        drop = set(islands)
        zonas = [z for z in zonas if z not in drop]
    w = libpysal.weights.W(neigh, id_order=zonas, silence_warnings=True)
    w.transform = "r"
    return w, zonas


def extract_coefs(model, xnames: list[str], spatial_name: str) -> dict:
    betas = np.asarray(model.betas)
    stats = getattr(model, "z_stat", None) or getattr(model, "t_stat", None)
    m = betas.shape[0]
    names = ["CONSTANT"] + xnames
    if m == len(names) + 1:
        names = names + [spatial_name]
    out = {}
    for i in range(m):
        p = float(stats[i][1]) if stats is not None and i < len(stats) else None
        out[names[i] if i < len(names) else f"b{i}"] = {
            "beta": round(float(betas[i][0]), 5),
            "p": round(p, 5) if p is not None else None,
        }
    return out


def diag_pair(model, attr: str) -> dict | None:
    v = getattr(model, attr, None)
    if v is None:
        return None
    return {"stat": round(float(v[0]), 4), "p": round(float(v[1]), 5)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--target", default="qr_rate_2025", choices=list(WEIGHT_FOR_TARGET))
    ap.add_argument("--min-n", type=int, default=30)
    args = ap.parse_args()

    try:
        from spreg import OLS, ML_Error, ML_Lag
    except ImportError as exc:
        raise SystemExit(
            "Faltan librerías espaciales. Instalá en tu venv:\n"
            "    pip install libpysal spreg\n"
            f"(detalle: {exc})"
        )
    import polars as pl

    out_dir = Path(OUT_DIR)
    csv_path = out_dir / f"qr_adoption_by_residence_zone_{args.home_filter}.csv"
    for pth, nm in [(csv_path, "CSV diagnóstico"), (EOD_PATH, "EOD"), (CENSO_PATH, "Censo")]:
        if not pth.exists():
            raise FileNotFoundError(f"Falta {nm}: {pth}")

    rates = pl.read_csv(csv_path)
    eod = pl.scan_parquet(EOD_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(INCOME_VAR).cast(pl.Float64)]
    ).collect()
    censo = pl.scan_parquet(CENSO_PATH).select(
        [pl.col("ZONA777").cast(pl.Int64), pl.col(EDUCATION_VAR).cast(pl.Float64)]
    ).collect()

    df = (
        rates.with_columns(pl.col("zona_hogar").cast(pl.Int64).alias("ZONA777"))
        .join(eod, on="ZONA777", how="left")
        .join(censo, on="ZONA777", how="left")
    )
    wcol = WEIGHT_FOR_TARGET[args.target]
    cond = (pl.col(wcol) >= args.min_n) & pl.col(args.target).is_not_null()
    cond = cond & pl.col(INCOME_VAR).is_not_null() & pl.col(EDUCATION_VAR).is_not_null()
    df = df.filter(cond)

    pdf = df.to_pandas()

    # W alineada (puede dropear islas); reordenar pdf al id_order de la W.
    w, zonas = aligned_queen_w(pdf["ZONA777"].astype(int).tolist())
    pdf = pdf.set_index("ZONA777").loc[zonas].reset_index()
    n_used = len(pdf)

    def z(col):
        a = pdf[col].to_numpy(dtype=float)
        return (a - a.mean()) / a.std(ddof=0)

    y = pdf[args.target].to_numpy(dtype=float).reshape(-1, 1)
    X = np.column_stack([z(INCOME_VAR), z(EDUCATION_VAR)])
    xnames = ["ingreso_z", "educacion_z"]

    results: dict = {
        "target": args.target,
        "universo": args.home_filter,
        "min_n": args.min_n,
        "n_zonas_usadas": int(n_used),
        "covariables": xnames,
    }

    # 1) OLS + diagnósticos espaciales
    ols = OLS(y, X, w=w, spat_diag=True, moran=True,
              name_y=args.target, name_x=xnames, name_w="queen")
    moran = getattr(ols, "moran_res", None)
    results["ols"] = {
        "r2": round(float(ols.r2), 4),
        "coeficientes": extract_coefs(ols, xnames, "n/a"),
        "moran_residuos": (
            {"I": round(float(moran[0]), 5), "p": round(float(moran[2]), 5)} if moran else None
        ),
        "tests_LM": {
            "lm_lag": diag_pair(ols, "lm_lag"),
            "rlm_lag_robusto": diag_pair(ols, "rlm_lag"),
            "lm_error": diag_pair(ols, "lm_error"),
            "rlm_error_robusto": diag_pair(ols, "rlm_error"),
        },
    }

    # 2) SAR (ML_Lag)
    try:
        lag = ML_Lag(y, X, w=w, name_y=args.target, name_x=xnames)
        rho = float(getattr(lag, "rho", lag.betas[-1][0]))
        coefs = extract_coefs(lag, xnames, "rho")
        beta_edu = coefs.get("educacion_z", {}).get("beta")
        results["sar_lag"] = {
            "rho": round(rho, 5),
            "coeficientes": coefs,
            "pseudo_r2": round(float(getattr(lag, "pr2", float("nan"))), 4),
            "logll": round(float(getattr(lag, "logll", float("nan"))), 2),
            "aic": round(float(getattr(lag, "aic", float("nan"))), 2),
            "efecto_total_educacion_aprox": (
                round(beta_edu / (1 - rho), 5) if beta_edu is not None and rho != 1 else None
            ),
        }
    except Exception as exc:  # noqa: BLE001
        results["sar_lag"] = {"error": str(exc)}

    # 3) SEM (ML_Error)
    try:
        err = ML_Error(y, X, w=w, name_y=args.target, name_x=xnames)
        lam = float(getattr(err, "lam", err.betas[-1][0]))
        results["sem_error"] = {
            "lambda": round(lam, 5),
            "coeficientes": extract_coefs(err, xnames, "lambda"),
            "pseudo_r2": round(float(getattr(err, "pr2", float("nan"))), 4),
            "logll": round(float(getattr(err, "logll", float("nan"))), 2),
            "aic": round(float(getattr(err, "aic", float("nan"))), 2),
        }
    except Exception as exc:  # noqa: BLE001
        results["sem_error"] = {"error": str(exc)}

    # Recomendación simple según LM robustos
    rlag = results["ols"]["tests_LM"]["rlm_lag_robusto"]
    rerr = results["ols"]["tests_LM"]["rlm_error_robusto"]
    rec = "indeterminado"
    if rlag and rerr:
        lag_sig = rlag["p"] < 0.05
        err_sig = rerr["p"] < 0.05
        if lag_sig and not err_sig:
            rec = "SAR (difusión): el LM-lag robusto es significativo y el de error no."
        elif err_sig and not lag_sig:
            rec = "SEM (error): el LM-error robusto es significativo y el de lag no."
        elif lag_sig and err_sig:
            rec = "ambos significativos: comparar por AIC (menor es mejor) y teoría."
        else:
            rec = "ninguno significativo: la estructura espacial residual no calza claramente con lag ni error."
    results["recomendacion_LM"] = rec

    json_out = out_dir / f"qr_zone_model_spatial_{args.home_filter}_{args.target}.json"
    json_out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print("\n===== MODELO ESPACIAL (SAR / SEM) =====")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nJSON : {json_out}")


if __name__ == "__main__":
    main()
