"""Valida el MNL de adopción QR estimándolo en Larch (vs Biogeme).

Replica EXACTAMENTE el MNL de scripts/user_level/fit_mnl_biogeme.py:
3 alternativas (BIP referencia con V=0, QR_RED, QR_OTHER), coeficientes
específicos por alternativa, mismos datos de lib/user_level/mnl_prep. El
objetivo es confirmar que los coeficientes coinciden entre Larch y Biogeme
(validación cruzada de implementación).

Patrón Larch del notebook 14 (03_models/larch_logit/): lx.Dataset.construct.
from_idco, m.utility_co[alt], beta()/x() para variables.

Uso (Mac, larch-env):
  python scripts/user_level/fit_mnl_larch.py --sample-frac 0.3

Output: 03_models/user_level/mnl/outputs/params_larch_<label>.csv
        + comparación con Biogeme si existe el params_<label>.csv equivalente.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/xdg-cache")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.user_level import mnl_prep as mp

OUT_DIR = PROJECT_ROOT / "03_models" / "user_level" / "mnl" / "outputs"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def param_tag(col: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", col).strip("_").upper()


def build_and_estimate_larch(pdf: pd.DataFrame, feature_cols: list[str], *, label: str):
    import larch as lx
    from larch import P, X

    # choice debe ser 1/2/3 (idco). Larch espera la columna de elección.
    ds = lx.Dataset.construct.from_idco(
        pdf, alts={1: "BIP", 2: "QR_RED", 3: "QR_OTHER"})
    m = lx.Model(ds)
    m.title = label
    m.compute_engine = "numba"
    m.choice_co_code = "choice"
    m.availability_co_vars = {1: 1, 2: 1, 3: 1}

    tags = {c: param_tag(c) for c in feature_cols}

    # BIP referencia: V=0. QR_RED y QR_OTHER con ASC + betas específicos.
    v_red = P("ASC_QR_RED")
    v_other = P("ASC_QR_OTHER")
    for c in feature_cols:
        v_red = v_red + P(f"B_QR_RED_{tags[c]}") * X(c)
        v_other = v_other + P(f"B_QR_OTHER_{tags[c]}") * X(c)

    m.utility_co[1] = 0  # BIP
    m.utility_co[2] = v_red
    m.utility_co[3] = v_other
    m.initialize_graph(alternative_codes=[1, 2, 3],
                       alternative_names=["BIP", "QR_RED", "QR_OTHER"])

    _log(f"Larch listo ({len(pdf):,} obs, {len(feature_cols)} feats). Estimando...")
    t0 = time.time()
    result = m.maximize_loglike()
    _log(f"Estimación Larch terminada en {time.time()-t0:.1f}s")

    # Extraer parámetros estimados.
    params = m.pf  # parameter frame
    rows = []
    for name in params.index:
        rows.append({
            "Name": name,
            "Value": float(params.loc[name, "value"]),
            "Std err.": float(params.loc[name, "std_err"]) if "std_err" in params.columns else None,
        })
    params_df = pd.DataFrame(rows)
    return m, result, params_df


def compare_with_biogeme(params_larch: pd.DataFrame, label: str):
    """Si existe el params de Biogeme equivalente, compara coef por coef."""
    bio_path = OUT_DIR / f"params_{label}.csv"
    if not bio_path.exists():
        print(f"\n(no hay params Biogeme en {bio_path.name} para comparar)")
        return
    bio = pd.read_csv(bio_path)
    bio = bio.rename(columns={"Value": "bio_value"})[["Name", "bio_value"]]
    lar = params_larch.rename(columns={"Value": "larch_value"})[["Name", "larch_value"]]
    merged = bio.merge(lar, on="Name", how="outer")
    merged["abs_diff"] = (merged["bio_value"] - merged["larch_value"]).abs()
    merged = merged.sort_values("abs_diff", ascending=False)
    print("\n=== Comparación Biogeme vs Larch (top diferencias) ===")
    print(merged.head(15).to_string(index=False))
    max_diff = merged["abs_diff"].max()
    print(f"\nMáxima diferencia absoluta: {max_diff:.6f}")
    if max_diff < 0.01:
        print("✅ Coeficientes COINCIDEN (max diff < 0.01) — validación OK.")
    else:
        print("⚠️ Diferencias > 0.01 — revisar especificación.")
    merged.to_csv(OUT_DIR / f"compare_biogeme_larch_{label}.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument("--sample-frac", type=float, default=0.0)
    ap.add_argument("--inertia-window", action="append", default=None,
                    help="agrega índices DSI/TSI/LSI de esa ventana (igual que Biogeme). "
                         "REPETIBLE: 2 ventanas = modelo conjunto inter+intra.")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    _log("Cargando y preparando matriz...")
    ds = mp.prepare_mnl_dataset(
        scope=args.scope, variant=args.variant, home_filter=args.home_filter,
        min_trips=args.min_trips, min_home_trips=args.min_home_trips,
        inertia_window=args.inertia_window,
    )
    df = ds.df
    _log(f"Universo: {df.height:,} tarjetas, {len(ds.all_features)} features")

    # Submuestra DETERMINÍSTICA por id_tarjeta (idéntica a la de Biogeme).
    if args.sample_frac and 0 < args.sample_frac < 1:
        df = mp.stratified_subsample(df, args.sample_frac, seed=args.seed)
        print(f"Submuestra {args.sample_frac:.1%}: {df.height:,} tarjetas")

    # Larch necesita las features + choice como columnas numéricas.
    keep = ["choice", *ds.all_features]
    pdf = df.select(keep).to_pandas()

    label = f"mnl_user_{args.scope}_{args.variant}_{args.home_filter}_n{args.min_trips}"
    if args.min_home_trips:
        label += f"_home{args.min_home_trips}"
    if args.sample_frac:
        label += f"_s{int(args.sample_frac*1000):03d}"
    if args.inertia_window:
        if len(args.inertia_window) == 1:
            label += f"_inertia-{args.inertia_window[0]}"
        else:
            tags = "+".join(mp._window_tag(w) for w in args.inertia_window)
            label += f"_inertia-{tags}"

    m, result, params_df = build_and_estimate_larch(pdf, ds.all_features, label=label)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    params_df.to_csv(OUT_DIR / f"params_larch_{label}.csv", index=False)
    print(f"\n✅ Larch params -> {OUT_DIR / f'params_larch_{label}.csv'}")
    try:
        print(f"   LogLik: {m.loglike():.1f}")
    except Exception:
        pass

    compare_with_biogeme(params_df, label)


if __name__ == "__main__":
    main()
