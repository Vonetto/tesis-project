"""Estima el MNL de adopción QR a nivel id_tarjeta con Biogeme.

Modelo principal del frente econométrico. Replica el patrón del notebook 16
(`03_models/16_eod2012_income_proxy_stepwise.qmd`):
  - 3 alternativas: BIP (referencia, V=0), QR_RED, QR_OTHER.
  - Coeficientes ESPECÍFICOS por alternativa (características del decisor; un
    coeficiente genérico se cancela en las prob. relativas).
  - models.loglogit, bio.BIOGEME.

Los datos vienen de lib/user_level/mnl_prep.prepare_mnl_dataset (idco ya
transformado: log1p, z, winsor, dummies cohorte, dummies macro ref PONIENTE).

Uso (Mac, larch-env con biogeme):
  python scripts/user_level/fit_mnl_biogeme.py --sample-frac 0.04
  python scripts/user_level/fit_mnl_biogeme.py            # full 2,46M
  python scripts/user_level/fit_mnl_biogeme.py --binary   # logit QR vs BIP

Outputs: 03_models/user_level/mnl/outputs/{params,stats}_<label>.csv
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


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.user_level import mnl_prep as mp

OUT_DIR = PROJECT_ROOT / "03_models" / "user_level" / "mnl" / "outputs"

# Códigos de alternativa para Biogeme (deben matchear las claves de V).
CHOICE_BIP, CHOICE_QR_RED, CHOICE_QR_OTHER = 1, 2, 3


def param_tag(col: str) -> str:
    """Nombre de parámetro Biogeme a partir del nombre de columna.
    Mayúsculas, alfanumérico + guion bajo. Ej: 'home_macro_oriente' ->
    'HOME_MACRO_ORIENTE'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", col).strip("_").upper()


def build_and_estimate(pdf: pd.DataFrame, feature_cols: list[str], *,
                       label: str, binary: bool, nested: bool = False):
    import biogeme.biogeme as bio
    import biogeme.biogeme_logging as blog
    import biogeme.database as db
    from biogeme import models, nests
    from biogeme.expressions import Beta, Variable
    from biogeme.results_processing import pandas_output as br

    # Logging de Biogeme: muestra iteraciones del optimizador en consola.
    blog.get_screen_logger(level=blog.INFO)

    # Biogeme convierte TODO el df a float -> pasar SOLO columnas numéricas que
    # usa el modelo (features + choice). Excluir id_tarjeta / tipo_tarjeta (str).
    choice_name = "choice_bin" if binary else "choice"
    model_cols = [c for c in [choice_name, *feature_cols] if c in pdf.columns]
    pdf_num = pdf[model_cols].copy()

    database = db.Database(label, pdf_num)
    CHOICE = Variable("choice")

    def beta(name: str):
        return Beta(name, 0.0, None, None, 0)

    var = {c: Variable(c) for c in feature_cols}
    tags = {c: param_tag(c) for c in feature_cols}

    # ASCs (BIP referencia, ASC_BIP=0 implícito).
    ASC_QR_RED = beta("ASC_QR_RED")
    ASC_QR_OTHER = beta("ASC_QR_OTHER")

    # Betas específicos por alternativa; BIP=0 (referencia).
    b_red = {c: beta(f"B_QR_RED_{tags[c]}") for c in feature_cols}
    b_other = {c: beta(f"B_QR_OTHER_{tags[c]}") for c in feature_cols}

    V_BIP = 0
    V_QR_RED = ASC_QR_RED
    V_QR_OTHER = ASC_QR_OTHER
    for c in feature_cols:
        V_QR_RED = V_QR_RED + b_red[c] * var[c]
        V_QR_OTHER = V_QR_OTHER + b_other[c] * var[c]

    if binary:
        # QR vs BIP: una sola alternativa QR. La columna choice_bin: 1=BIP, 2=QR.
        # Comparten beta (no se distingue RED/OTHER). V_QR con su propio ASC.
        ASC_QR = beta("ASC_QR")
        b_qr = {c: beta(f"B_QR_{tags[c]}") for c in feature_cols}
        V_QR = ASC_QR
        for c in feature_cols:
            V_QR = V_QR + b_qr[c] * var[c]
        V = {1: 0, 2: V_QR}
        av = {1: 1, 2: 1}
        CHOICE = Variable("choice_bin")
    else:
        V = {CHOICE_BIP: V_BIP, CHOICE_QR_RED: V_QR_RED, CHOICE_QR_OTHER: V_QR_OTHER}
        av = {CHOICE_BIP: 1, CHOICE_QR_RED: 1, CHOICE_QR_OTHER: 1}

    if nested and not binary:
        # Sensibilidad IIA: nido (QR_RED, QR_OTHER) vs BIP. MU_QR>=1 acotado;
        # MU_QR≈1 => el nido colapsa al MNL plano (IIA razonable, no hay
        # correlación no observada extra entre los dos QR).
        MU_QR = Beta("MU_QR", 1.5, 1.0, 100.0, 0)
        nest_bip = nests.OneNestForNestedLogit(1.0, [CHOICE_BIP], name="BIP")
        nest_qr = nests.OneNestForNestedLogit(
            MU_QR, [CHOICE_QR_RED, CHOICE_QR_OTHER], name="QR")
        NESTS = nests.NestsForNestedLogit(
            choice_set=[CHOICE_BIP, CHOICE_QR_RED, CHOICE_QR_OTHER],
            tuple_of_nests=(nest_bip, nest_qr),
        )
        logprob = models.lognested(V, av, NESTS, CHOICE)
    else:
        logprob = models.loglogit(V, av, CHOICE)
    biogeme = bio.BIOGEME(database, logprob)
    biogeme.model_name = label
    # generate_html/pickle no son asignables en esta versión; se controlan vía
    # el .toml o el constructor. Se dejan en su default; solo usamos el CSV.

    # Borrar el caché de valores iniciales (__<label>.iter) ANTES de estimar.
    # Biogeme lo lee para "calentar" el optimizador, pero si el modelo cambió
    # (p.ej. se dropeó la cohorte en ventanas intra-anuales) ese .iter queda
    # inconsistente con el set de parámetros actual y la estimación NO converge
    # (Rho² negativo). Es caché regenerable: borrarlo fuerza arrancar de cero.
    # Se busca en el cwd (donde Biogeme lo escribe) incluyendo variantes ~NN.
    from glob import glob as _glob
    for _f in _glob(f"__{label}*.iter"):
        try:
            os.remove(_f)
            _log(f"caché .iter previo borrado: {_f}")
        except OSError:
            pass

    _log(f"BIOGEME listo ({len(pdf_num):,} obs, {len(feature_cols)} feats). "
         "Iniciando estimación...")
    t0 = time.time()
    results = biogeme.estimate()
    _log(f"Estimación terminada en {time.time()-t0:.1f}s")
    stats = results.get_general_statistics()
    params_df = br.get_pandas_estimated_parameters(results)
    return results, stats, params_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument("--sample-frac", type=float, default=0.0,
                    help="fracción estratificada por tipo_tarjeta (0=full).")
    ap.add_argument("--binary", action="store_true",
                    help="logit binario QR vs BIP en vez del MNL 3 alternativas.")
    ap.add_argument("--nested", action="store_true",
                    help="nested logit: nido (QR_RED,QR_OTHER) vs BIP. Sensib. IIA.")
    ap.add_argument("--drop-educ", action="store_true",
                    help="excluye educación del set (sensib.: ¿Oriente se vuelve + sin educación?).")
    ap.add_argument("--inertia-window", action="append", default=None,
                    help="agrega índices DSI/TSI/LSI de esa ventana (ej. inter_W15_W17, "
                         "intra2025_W15_W17). RESTRINGE el universo a tarjetas elegibles. "
                         "REPETIBLE: pasar 2 veces (inter + intra) = modelo CONJUNTO sobre "
                         "el universo común. Default de índices: parsimonioso (sin LSI-zona).")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    if args.nested and args.binary:
        ap.error("--nested y --binary son incompatibles (nested requiere 3 alt).")

    _log("Cargando y preparando matriz...")
    ds = mp.prepare_mnl_dataset(
        scope=args.scope, variant=args.variant, home_filter=args.home_filter,
        min_trips=args.min_trips, min_home_trips=args.min_home_trips,
        inertia_window=args.inertia_window,
    )
    df = ds.df
    features = list(ds.all_features)
    if args.drop_educ:
        educ = [c for c in features if "cine18" in c.lower()]
        features = [c for c in features if c not in educ]
        _log(f"--drop-educ: excluidas {educ} ({len(features)} features restantes)")
    _log(f"Universo: {df.height:,} tarjetas, {len(features)} features")

    # Submuestra DETERMINÍSTICA por id_tarjeta (idéntica entre Biogeme/Larch).
    if args.sample_frac and 0 < args.sample_frac < 1:
        df = mp.stratified_subsample(df, args.sample_frac, seed=args.seed)
        print(f"Submuestra {args.sample_frac:.1%}: {df.height:,} tarjetas")

    pdf = df.to_pandas()
    # columna binaria si aplica: 1=BIP, 2=QR (red u other)
    if args.binary:
        pdf["choice_bin"] = np.where(pdf["choice"] == CHOICE_BIP, 1, 2)

    label = f"mnl_user_{args.scope}_{args.variant}_{args.home_filter}_n{args.min_trips}"
    if args.min_home_trips:
        label += f"_home{args.min_home_trips}"
    if args.sample_frac:
        label += f"_s{int(args.sample_frac*1000):03d}"
    if args.binary:
        label += "_binary"
    if args.nested:
        label += "_nested"
    if args.drop_educ:
        label += "_noeduc"
    if args.inertia_window:
        if len(args.inertia_window) == 1:
            # una sola ventana: nombre completo (compatibilidad con CSV previos)
            label += f"_inertia-{args.inertia_window[0]}"
        else:
            # conjunto: etiquetas cortas unidas por '+' (inter+intra2025)
            tags = "+".join(mp._window_tag(w) for w in args.inertia_window)
            label += f"_inertia-{tags}"

    print(f"Estimando: {label}")
    results, stats, params_df = build_and_estimate(
        pdf, features, label=label, binary=args.binary, nested=args.nested)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    params_path = OUT_DIR / f"params_{label}.csv"
    stats_path = OUT_DIR / f"stats_{label}.csv"
    params_df.to_csv(params_path, index=False)
    pd.DataFrame(
        [{"stat": k, "value": str(v[0]) if isinstance(v, tuple) else str(v)}
         for k, v in stats.items()]
    ).to_csv(stats_path, index=False)

    print(f"\n✅ {label}")
    print(f"   params -> {params_path}")
    print(f"   stats  -> {stats_path}")
    # resumen rápido en consola
    for k, v in stats.items():
        val = v[0] if isinstance(v, tuple) else v
        if any(t in k.lower() for t in ["loglik", "rho", "param", "sample", "observ"]):
            print(f"   {k}: {val}")


if __name__ == "__main__":
    main()
