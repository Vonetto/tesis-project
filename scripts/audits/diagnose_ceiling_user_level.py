"""Diagnóstico de techo predictivo a nivel id_tarjeta.

Mide cuánta señal hay realmente en el panel actual para separar:
  - BINARIO:   BIP vs QR   (QR = QR_RED + QR_OTHER)
  - MULTICLASE: BIP / QR_RED / QR_OTHER

Para cada target corre:
  - full:        todas las features
  - no_cohort:   sin variables de cohorte/temporalidad
  - ablación:    quitando cada familia (use, geo, socio, osm) una a la vez

Objetivo: decidir CON NÚMERO (gate) si vale la pena construir bloques
nuevos de variables (BIP friction, digital-territorial) antes de invertir
en lookups espaciales. Si el techo es bajo y la familia socio-territorial
no aporta, esos bloques no van a separar QR_OTHER de BIP.

Modelo: HistGradientBoostingClassifier (sklearn). Rápido, multiclase
nativo, maneja NaN sin imputar. Equivalente en techo a XGBoost/LightGBM.

Evaluación: K-fold estratificado. Como la unidad de fila YA es id_tarjeta
(una fila = una tarjeta), un split aleatorio de filas es split por tarjeta.
Métricas reportadas son out-of-fold (OOF).

Uso (en la Mac, con larch-env que sí resuelve el symlink a KINGSTON):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
      scripts/audits/diagnose_ceiling_user_level.py

Outputs: tmp/audits/user_level_redesign/ceiling_diagnosis_*.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PANEL_PATH = (
    PROJECT_ROOT
    / "tmp"
    / "audits"
    / "user_level_redesign"
    / "user_level_payment_panel_interannual_ml_clean.parquet"
)
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

# Filtro main acordado.
HOME_CONFIDENCE_KEEP = ["alta"]
MIN_N_VIAJES = 3

N_SPLITS = 5
RANDOM_STATE = 42

# Hiperparámetros del booster. Fijos y razonables para un techo; no se
# tunea grid porque buscamos orden de magnitud del AUC, no el último 0,005.
HGB_KWARGS = dict(
    max_iter=400,
    learning_rate=0.05,
    max_depth=None,
    max_leaf_nodes=63,
    min_samples_leaf=200,
    l2_regularization=1.0,
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=20,
    random_state=RANDOM_STATE,
)

# --------------------------------------------------------------------------
# Columnas a EXCLUIR de features (target, IDs, leakage, metadata)
# --------------------------------------------------------------------------
# Leakage / target: cualquier cosa que codifique tipo_pago.
TARGET_LEAKAGE = {
    "tipo_tarjeta",
    "tipo_pago_set",
    "is_qr",
    "is_qr_red",
    "is_qr_other",
    "target_conflict_flag",
    "n_tipo_pago_observed",
}
# IDs y llaves de zona crudas (alta cardinalidad; ya resumidas en
# macrozona/share/entropy). zona_hogar es el filtro de residencia.
IDS_AND_RAW_ZONES = {
    "id_tarjeta",
    "zona_hogar",
    "origin_zone_top1",
    "origin_zone_top2",
    "dest_zone_top1",
    "dest_zone_top2",
    "activity_zone_top1",
    "activity_zone_top2",
}
# Metadata no-feature.
METADATA = {
    "first_trip_ts",
    "last_trip_ts",
    "home_confidence",
    "home_zone_top_share",
    "has_home_zone_tie",
    "n_home_dest_trips_top",
    "n_home_zones_observed",
    "n_home_dest_trips_card",
    "home_macrozone",
    "origin_top1_macrozone",
    "origin_top2_macrozone",
    "dest_top1_macrozone",
    "activity_top1_macrozone",
    "activity_top2_macrozone",
}
EXCLUDE_ALWAYS = TARGET_LEAKAGE | IDS_AND_RAW_ZONES | METADATA

# --------------------------------------------------------------------------
# Familias de features (para ablación y para identificar cohorte)
# Se definen por prefijo/sufijo y se materializan contra columnas presentes.
# --------------------------------------------------------------------------
# Cohorte / temporalidad: lo que captura "cuándo" y no "cómo viaja".
COHORT_EXACT = {
    "share_trips_2025",
    "share_trips_2024",
    "first_trip_year",
    "last_trip_year",
    "trip_span_days",
}


def classify_families(feature_cols: list[str]) -> dict[str, list[str]]:
    """Asigna cada feature a una familia. Una feature está en exactamente una."""
    fam: dict[str, list[str]] = {
        "cohort": [],
        "use": [],
        "geo": [],
        "socio": [],
        "osm": [],
        "other": [],
    }
    for c in feature_cols:
        if c in COHORT_EXACT:
            fam["cohort"].append(c)
        elif c.startswith("res_"):
            fam["socio"].append(c)
        elif "_osm_" in c:
            fam["osm"].append(c)
        elif (
            c.startswith(("home_macro_", "origin_top1_macro_", "origin_top2_macro_",
                          "dest_top1_macro_", "activity_top1_macro_", "activity_top2_macro_"))
            or c.endswith(("_lon", "_lat"))
            or "_zone_top" in c
            or c.endswith("_zone_entropy")
            or c.startswith("n_origin_zones")
            or c.startswith("n_dest_zones")
            or c.startswith("n_activity_zones")
        ):
            fam["geo"].append(c)
        elif c.startswith(("hora_", "share_lab_", "share_no_lab", "share_trips_",
                           "n_trasbordos", "t_vehiculo_", "t_espera_",
                           "n_viajes", "n_dias_activos", "n_semanas_activas")):
            fam["use"].append(c)
        else:
            fam["other"].append(c)
    return fam


# --------------------------------------------------------------------------
# Carga y preparación
# --------------------------------------------------------------------------
def load_main_panel() -> pl.DataFrame:
    if not PANEL_PATH.exists():
        raise FileNotFoundError(
            f"No se encuentra el panel: {PANEL_PATH}\n"
            "¿Está montado KINGSTON? El symlink tmp/audits/user_level_redesign "
            "apunta al disco externo."
        )
    lf = pl.scan_parquet(PANEL_PATH)
    lf = lf.filter(
        pl.col("home_confidence").is_in(HOME_CONFIDENCE_KEEP)
        & (pl.col("n_viajes") >= MIN_N_VIAJES)
    )
    df = lf.collect()
    print(f"Panel main: {df.height:,} tarjetas (home_alta, n_viajes>={MIN_N_VIAJES})")
    return df


def select_feature_columns(df: pl.DataFrame) -> list[str]:
    """Todas las columnas numéricas salvo exclusiones. Booster aprovecha
    redundancia: para el techo se incluye casi todo (las podas de parsimonia
    del Bloque 6C aplican al logit interpretable, no al techo)."""
    numeric = {
        c for c, dt in df.schema.items()
        if dt.is_numeric() and c not in EXCLUDE_ALWAYS
    }
    return sorted(numeric)


def make_targets(df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """y_bin: 1=QR (red u other), 0=BIP. y_multi: 0=BIP,1=QR_OTHER,2=QR_RED."""
    tt = df["tipo_tarjeta"].to_numpy()
    y_bin = np.where(tt == "BIP", 0, 1).astype(int)
    multi_map = {"BIP": 0, "QR_OTHER": 1, "QR_RED": 2}
    y_multi = np.array([multi_map[v] for v in tt], dtype=int)
    return y_bin, y_multi


# --------------------------------------------------------------------------
# Evaluación OOF
# --------------------------------------------------------------------------
def eval_binary(X: np.ndarray, y: np.ndarray) -> dict:
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    oof = np.zeros(len(y), dtype=float)
    for tr, te in skf.split(X, y):
        clf = HistGradientBoostingClassifier(**HGB_KWARGS)
        clf.fit(X[tr], y[tr])
        oof[te] = clf.predict_proba(X[te])[:, 1]
    return {
        "auc": roc_auc_score(y, oof),
        "pr_auc": average_precision_score(y, oof),
        "base_rate": float(y.mean()),
    }


def eval_multiclass(X: np.ndarray, y: np.ndarray) -> dict:
    skf = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    classes = np.array([0, 1, 2])
    oof_proba = np.zeros((len(y), 3), dtype=float)
    oof_pred = np.zeros(len(y), dtype=int)
    for tr, te in skf.split(X, y):
        clf = HistGradientBoostingClassifier(**HGB_KWARGS)
        clf.fit(X[tr], y[tr])
        proba = clf.predict_proba(X[te])
        # Reordenar columnas a [0,1,2] por si una clase falta en un fold.
        proba_full = np.zeros((len(te), 3))
        for j, cls in enumerate(clf.classes_):
            proba_full[:, cls] = proba[:, j]
        oof_proba[te] = proba_full
        oof_pred[te] = proba_full.argmax(axis=1)
    # AUC one-vs-rest por clase.
    ovr = {}
    for cls, name in [(0, "BIP"), (1, "QR_OTHER"), (2, "QR_RED")]:
        y_bin = (y == cls).astype(int)
        ovr[f"auc_ovr_{name}"] = roc_auc_score(y_bin, oof_proba[:, cls])
    return {
        "balanced_accuracy": balanced_accuracy_score(y, oof_pred),
        "macro_f1": f1_score(y, oof_pred, average="macro"),
        "auc_macro_ovr": roc_auc_score(y, oof_proba, multi_class="ovr", average="macro"),
        **ovr,
    }


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
def build_runs(all_feats: list[str], fam: dict[str, list[str]]) -> dict[str, list[str]]:
    """Define los conjuntos de features de cada corrida."""
    runs = {"full": all_feats}
    # Sin cohorte.
    runs["no_cohort"] = [c for c in all_feats if c not in set(fam["cohort"])]
    # Ablación: quitar una familia a la vez (solo familias no vacías y no triviales).
    for famname in ["use", "geo", "socio", "osm", "cohort"]:
        drop = set(fam[famname])
        if not drop:
            continue
        runs[f"drop_{famname}"] = [c for c in all_feats if c not in drop]
    return runs


def main() -> None:
    df = load_main_panel()
    feats = select_feature_columns(df)
    fam = classify_families(feats)

    print("\nFamilias de features:")
    for k, v in fam.items():
        print(f"  {k:8s}: {len(v):3d}")
    print(f"  TOTAL   : {len(feats):3d}")
    if fam["other"]:
        print(f"\n⚠️ Features sin familia clara (revisar): {fam['other']}")

    X_full = df.select(feats).to_numpy().astype(np.float64)
    y_bin, y_multi = make_targets(df)

    print(f"\nBinario BIP vs QR — base rate QR: {y_bin.mean():.4f}")
    print(f"Multiclase — BIP {np.mean(y_multi==0):.4f} | "
          f"QR_OTHER {np.mean(y_multi==1):.4f} | QR_RED {np.mean(y_multi==2):.4f}")

    runs = build_runs(feats, fam)
    feat_index = {c: i for i, c in enumerate(feats)}

    rows_bin = []
    rows_multi = []
    for run_name, run_feats in runs.items():
        cols_idx = [feat_index[c] for c in run_feats]
        X = X_full[:, cols_idx]
        print(f"\n=== RUN: {run_name} ({len(run_feats)} features) ===")

        rb = eval_binary(X, y_bin)
        rb = {"run": run_name, "n_features": len(run_feats), **rb}
        rows_bin.append(rb)
        print(f"  [binario]   AUC={rb['auc']:.4f}  PR-AUC={rb['pr_auc']:.4f}")

        rm = eval_multiclass(X, y_multi)
        rm = {"run": run_name, "n_features": len(run_feats), **rm}
        rows_multi.append(rm)
        print(f"  [multi] balAcc={rm['balanced_accuracy']:.4f} "
              f"macroF1={rm['macro_f1']:.4f} AUCmacro={rm['auc_macro_ovr']:.4f}")
        print(f"          AUC-OvR  BIP={rm['auc_ovr_BIP']:.4f} "
              f"QR_OTHER={rm['auc_ovr_QR_OTHER']:.4f} QR_RED={rm['auc_ovr_QR_RED']:.4f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pl.DataFrame(rows_bin).write_csv(OUT_DIR / "ceiling_diagnosis_binary.csv")
    pl.DataFrame(rows_multi).write_csv(OUT_DIR / "ceiling_diagnosis_multiclass.csv")
    # Guardar el mapa de familias para trazabilidad.
    fam_rows = [{"family": k, "feature": c} for k, v in fam.items() for c in v]
    pl.DataFrame(fam_rows).write_csv(OUT_DIR / "ceiling_diagnosis_feature_families.csv")

    print("\n✅ Resultados escritos en:")
    print(f"   {OUT_DIR / 'ceiling_diagnosis_binary.csv'}")
    print(f"   {OUT_DIR / 'ceiling_diagnosis_multiclass.csv'}")
    print(f"   {OUT_DIR / 'ceiling_diagnosis_feature_families.csv'}")


if __name__ == "__main__":
    sys.exit(main())
