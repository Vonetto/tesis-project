"""Analisis SHAP del benchmark ML a nivel id_tarjeta.

Entrena XGBoost con los MISMOS hiperparametros default del benchmark
(`run_user_ml_benchmark.py`) sobre una muestra estratificada, y calcula
SHAP (TreeSHAP nativo de XGBoost via pred_contribs; el paquete `shap` se usa
solo para el beeswarm) sobre un holdout estratificado para:
  - binary: QR vs BIP
  - multiclass: BIP / QR_OTHER / QR_RED

Reusa del benchmark (import directo, sin duplicar logica):
  - matrix_path / feature_sets_path / universe_suffix
  - load_feature_contract / select_features
  - make_targets / stratified_sample_indices
  - classify_family (agregacion por familias)

Diferencia metodologica vs benchmark: aqui NO hay OOF 5-fold; se entrena un
solo modelo train/holdout para poder explicarlo. Las metricas del holdout se
reportan como sanity check de que el modelo explicado es comparable al
benchmark (~AUC 0.68 binario), no como metricas oficiales.

Uso (presentacion, muestra 500k):
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/run_user_shap_analysis.py \
    --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
    --feature-set full_plus_rhythm_context_routine_daily_tour \
    --task both --train-sample 500000 --shap-sample 50000

Requiere `shap` en el env:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/pip install shap
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

# Reusar contratos del benchmark (misma carpeta; no es package).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_user_ml_benchmark as bench  # noqa: E402

CLASS_NAMES = bench.CLASS_NAMES  # ["BIP", "QR_OTHER", "QR_RED"]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def xgb_params_like_benchmark(args: argparse.Namespace, task: str) -> dict:
    """Replica xgb_params() del benchmark con los mismos defaults."""
    common = {
        "n_estimators": args.xgb_n_estimators,
        "learning_rate": args.xgb_learning_rate,
        "max_depth": args.xgb_max_depth,
        "min_child_weight": args.xgb_min_child_weight,
        "subsample": args.xgb_subsample,
        "colsample_bytree": args.xgb_colsample_bytree,
        "reg_lambda": args.xgb_reg_lambda,
        "reg_alpha": args.xgb_reg_alpha,
        "gamma": args.xgb_gamma,
        "max_delta_step": args.xgb_max_delta_step,
        "tree_method": "hist",
        "n_jobs": args.n_jobs,
        "random_state": args.seed,
    }
    if task == "binary":
        return {"objective": "binary:logistic", "eval_metric": "logloss", **common}
    return {
        "objective": "multi:softprob",
        "num_class": 3,
        "eval_metric": "mlogloss",
        **common,
    }


def contribs_to_shap(contribs, n_features: int, n_classes: int) -> np.ndarray:
    """Normaliza la salida de Booster.predict(pred_contribs=True) a (n, features, clases).

    TreeSHAP nativo de XGBoost (mismo algoritmo que shap.TreeExplainer, pero sin
    parsear el modelo, lo que evita incompatibilidades de version shap<->xgboost).
    Formas posibles segun version/task:
      - binario:    (n, f+1)                      [ultima col = bias]
      - multiclase: (n, c, f+1)                   [xgboost >= 1.4]
      - multiclase: (n, c*(f+1))  [versiones antiguas] -> reshape
    """
    arr = np.asarray(contribs)
    if arr.ndim == 2 and n_classes > 1 and arr.shape[1] == n_classes * (n_features + 1):
        arr = arr.reshape(arr.shape[0], n_classes, n_features + 1)
    if arr.ndim == 2:
        arr = arr[:, None, :]  # binario -> (n, 1, f+1)
    if arr.ndim != 3 or arr.shape[1] != n_classes or arr.shape[2] != n_features + 1:
        raise ValueError(
            f"Forma pred_contribs inesperada: {np.asarray(contribs).shape} "
            f"(esperaba clases={n_classes}, features+bias={n_features + 1})"
        )
    arr = arr[:, :, :-1]  # descartar columna bias
    return np.transpose(arr, (0, 2, 1))  # (n, f, c)


def holdout_metrics(task: str, y_true: np.ndarray, proba: np.ndarray) -> dict:
    if task == "binary":
        p1 = proba[:, 1]
        return {
            "roc_auc": float(roc_auc_score(y_true, p1)),
            "pr_auc": float(average_precision_score(y_true, p1)),
        }
    out: dict = {}
    aucs = []
    for k, name in enumerate(CLASS_NAMES):
        y_k = (y_true == k).astype(int)
        auc = float(roc_auc_score(y_k, proba[:, k]))
        out[f"ovr_auc_{name}"] = auc
        out[f"ovr_pr_auc_{name}"] = float(average_precision_score(y_k, proba[:, k]))
        aucs.append(auc)
    out["macro_ovr_auc"] = float(np.mean(aucs))
    return out


def shap_tables(
    shap_arr: np.ndarray,
    features: list[str],
    class_labels: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """mean |SHAP| por feature y agregado por familia (suma de features)."""
    rows = []
    for j, feat in enumerate(features):
        row = {"feature": feat, "family": bench.classify_family(feat)}
        for c, label in enumerate(class_labels):
            row[f"mean_abs_shap_{label}"] = float(np.abs(shap_arr[:, j, c]).mean())
        rows.append(row)
    feat_df = pd.DataFrame(rows)
    value_cols = [f"mean_abs_shap_{label}" for label in class_labels]
    feat_df["mean_abs_shap_total"] = feat_df[value_cols].sum(axis=1)
    feat_df = feat_df.sort_values("mean_abs_shap_total", ascending=False).reset_index(drop=True)

    fam_df = feat_df.groupby("family", as_index=False)[value_cols].sum()
    for col in value_cols:
        total = fam_df[col].sum()
        fam_df[f"{col.replace('mean_abs_shap', 'share')}"] = (
            fam_df[col] / total if total > 0 else 0.0
        )
    fam_df = fam_df.sort_values(value_cols[-1], ascending=False).reset_index(drop=True)
    return feat_df, fam_df


def plot_bar_top_features(
    feat_df: pd.DataFrame,
    value_col: str,
    title: str,
    out_path: Path,
    top_n: int,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = feat_df.nlargest(top_n, value_col).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, max(4, 0.32 * top_n)))
    ax.barh(top["feature"], top[value_col], color="#4C72B0")
    ax.set_xlabel("mean |SHAP|")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    log(f"  figura: {out_path}")


def plot_beeswarm(
    shap_2d: np.ndarray,
    X_df: pd.DataFrame,
    title: str,
    out_path: Path,
    top_n: int,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import shap as shap_lib

    plt.figure()
    shap_lib.summary_plot(shap_2d, X_df, max_display=top_n, show=False)
    plt.title(title)
    plt.gcf().tight_layout()
    plt.gcf().savefig(out_path, dpi=200)
    plt.close("all")
    log(f"  figura: {out_path}")


def plot_family_comparison(
    fam_tables: dict[str, pd.DataFrame],
    out_path: Path,
) -> None:
    """Barras agrupadas: share de |SHAP| por familia para binario y clases QR."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = {}
    if "binary" in fam_tables:
        series["QR vs BIP (binario)"] = fam_tables["binary"].set_index("family")["share_QR"]
    if "multiclass" in fam_tables:
        fam = fam_tables["multiclass"].set_index("family")
        series["QR_OTHER (multiclase)"] = fam["share_QR_OTHER"]
        series["QR_RED (multiclase)"] = fam["share_QR_RED"]
    if not series:
        return
    comp = pd.DataFrame(series).fillna(0.0)
    comp = comp.loc[comp.max(axis=1).sort_values(ascending=False).index]

    x = np.arange(len(comp))
    width = 0.8 / len(comp.columns)
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4C72B0", "#DD8452", "#C44E52"]
    for i, col in enumerate(comp.columns):
        ax.bar(x + i * width, comp[col], width, label=col, color=colors[i % len(colors)])
    ax.set_xticks(x + width * (len(comp.columns) - 1) / 2)
    ax.set_xticklabels(comp.index, rotation=45, ha="right")
    ax.set_ylabel("share de mean |SHAP| (suma por familia)")
    ax.set_title("Importancia SHAP por familia: binario vs clases multiclase")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    log(f"  figura: {out_path}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument(
        "--feature-set", default="full_plus_rhythm_context_routine_daily_tour"
    )
    ap.add_argument("--task", choices=["binary", "multiclass", "both"], default="both")
    ap.add_argument(
        "--train-sample",
        type=int,
        default=500_000,
        help="Muestra estratificada total (train+holdout). 0 = universo completo.",
    )
    ap.add_argument(
        "--holdout-frac",
        type=float,
        default=0.2,
        help="Fraccion estratificada reservada como holdout para SHAP/metricas.",
    )
    ap.add_argument(
        "--shap-sample",
        type=int,
        default=50_000,
        help="Maximo de filas del holdout usadas para SHAP. 0 = holdout completo.",
    )
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=bench.RANDOM_STATE)
    ap.add_argument("--n-jobs", type=int, default=-1)
    # Hiperparametros XGB: mismos defaults que run_user_ml_benchmark.py.
    ap.add_argument("--xgb-n-estimators", type=int, default=500)
    ap.add_argument("--xgb-learning-rate", type=float, default=0.05)
    ap.add_argument("--xgb-max-depth", type=int, default=6)
    ap.add_argument("--xgb-min-child-weight", type=float, default=1.0)
    ap.add_argument("--xgb-subsample", type=float, default=0.8)
    ap.add_argument("--xgb-colsample-bytree", type=float, default=0.8)
    ap.add_argument("--xgb-reg-lambda", type=float, default=1.0)
    ap.add_argument("--xgb-reg-alpha", type=float, default=0.0)
    ap.add_argument("--xgb-gamma", type=float, default=0.0)
    ap.add_argument("--xgb-max-delta-step", type=int, default=0)
    # Overrides para smoke test con artefactos sinteticos.
    ap.add_argument("--matrix-path", default="", help="Override del parquet de matriz.")
    ap.add_argument("--feature-sets-path", default="", help="Override del JSON de contrato.")
    ap.add_argument("--out-dir", default="", help="Override del directorio de salida.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.0 < args.holdout_frac < 1.0:
        raise ValueError("--holdout-frac debe estar entre 0 y 1")
    try:
        import shap  # noqa: F401  (solo para el beeswarm; los valores son nativos XGB)
    except ImportError as exc:
        raise SystemExit(
            "Falta `shap` en el env. Instalar con:\n"
            "  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/pip install shap"
        ) from exc
    import xgboost as xgb

    suffix = bench.universe_suffix(
        args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips
    )
    df_path = (
        Path(args.matrix_path)
        if args.matrix_path
        else bench.matrix_path(
            args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips
        )
    )
    contract_path = (
        Path(args.feature_sets_path)
        if args.feature_sets_path
        else bench.feature_sets_path(
            args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips
        )
    )
    out_dir = Path(args.out_dir) if args.out_dir else bench.OUT_DIR / "shap"
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    log(f"Matriz: {df_path}")
    df = pl.read_parquet(df_path)
    contract = bench.load_feature_contract(contract_path)
    features = bench.select_features(df, contract, args.feature_set)
    y_binary, y_multi = bench.make_targets(df)
    log(f"Universo: {df.height:,} filas, {len(features)} features ({args.feature_set})")

    # Muestra estratificada por clase multiclase (misma funcion del benchmark).
    sample_idx = bench.stratified_sample_indices(y_multi, args.train_sample, args.seed)
    if len(sample_idx) < df.height:
        df = df[sample_idx]
        y_binary = y_binary[sample_idx]
        y_multi = y_multi[sample_idx]
        log(f"Submuestra estratificada: {df.height:,} filas")

    X = df.select(features).to_numpy().astype(np.float64)
    base_rates = {
        "QR": float(y_binary.mean()),
        "BIP": float(np.mean(y_multi == 0)),
        "QR_OTHER": float(np.mean(y_multi == 1)),
        "QR_RED": float(np.mean(y_multi == 2)),
    }
    log(f"Base rates: { {k: round(v, 4) for k, v in base_rates.items()} }")

    # Split unico train/holdout, estratificado por multiclase para que ambos
    # tasks usen exactamente las mismas filas (comparabilidad SHAP).
    idx_all = np.arange(len(y_multi))
    idx_tr, idx_ho = train_test_split(
        idx_all,
        test_size=args.holdout_frac,
        random_state=args.seed,
        stratify=y_multi,
    )
    log(f"Train: {len(idx_tr):,} | Holdout: {len(idx_ho):,}")

    # Subconjunto del holdout para SHAP (estratificado por multiclase).
    if args.shap_sample > 0 and args.shap_sample < len(idx_ho):
        rel = bench.stratified_sample_indices(y_multi[idx_ho], args.shap_sample, args.seed)
        idx_shap = idx_ho[rel]
    else:
        idx_shap = idx_ho
    log(f"Filas para SHAP: {len(idx_shap):,}")
    X_shap_df = pd.DataFrame(X[idx_shap], columns=features)

    tasks = ["binary", "multiclass"] if args.task == "both" else [args.task]
    summary: dict = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "suffix": suffix,
        "feature_set": args.feature_set,
        "n_features": len(features),
        "train_rows": int(len(idx_tr)),
        "holdout_rows": int(len(idx_ho)),
        "shap_rows": int(len(idx_shap)),
        "base_rates": base_rates,
        "seed": args.seed,
        "xgb_params": {
            "n_estimators": args.xgb_n_estimators,
            "learning_rate": args.xgb_learning_rate,
            "max_depth": args.xgb_max_depth,
            "subsample": args.xgb_subsample,
            "colsample_bytree": args.xgb_colsample_bytree,
        },
        "tasks": {},
    }
    fam_tables: dict[str, pd.DataFrame] = {}

    for task in tasks:
        log(f"=== Task: {task} ===")
        y = y_binary if task == "binary" else y_multi
        params = xgb_params_like_benchmark(args, task)
        model = xgb.XGBClassifier(**params)
        log(f"Entrenando XGB ({params['n_estimators']} arboles)...")
        model.fit(X[idx_tr], y[idx_tr])

        proba = model.predict_proba(X[idx_ho])
        metrics = holdout_metrics(task, y[idx_ho], proba)
        log(f"Metricas holdout: { {k: round(v, 4) for k, v in metrics.items()} }")

        log("Calculando SHAP (TreeSHAP nativo XGBoost, pred_contribs)...")
        # DMatrix desde numpy: el booster fue entrenado sin feature_names (sklearn
        # API sobre numpy); pasar un DataFrame con nombres daria mismatch.
        n_classes = 1 if task == "binary" else 3
        dmat = xgb.DMatrix(X_shap_df.to_numpy())
        contribs = model.get_booster().predict(dmat, pred_contribs=True)
        shap_arr = contribs_to_shap(contribs, n_features=len(features), n_classes=n_classes)
        class_labels = ["QR"] if task == "binary" else CLASS_NAMES

        feat_df, fam_df = shap_tables(shap_arr, features, class_labels)
        feat_path = out_dir / f"shap_features_{task}_{suffix}_{args.feature_set}.csv"
        fam_path = out_dir / f"shap_families_{task}_{suffix}_{args.feature_set}.csv"
        feat_df.to_csv(feat_path, index=False)
        fam_df.to_csv(fam_path, index=False)
        log(f"  tabla features: {feat_path}")
        log(f"  tabla familias: {fam_path}")
        fam_tables[task] = fam_df

        if task == "binary":
            plot_beeswarm(
                shap_arr[..., 0],
                X_shap_df,
                "SHAP — QR vs BIP (binario)",
                fig_dir / f"shap_beeswarm_binary_{suffix}.png",
                args.top_n,
            )
            plot_bar_top_features(
                feat_df,
                "mean_abs_shap_QR",
                "Top features SHAP — QR vs BIP (binario)",
                fig_dir / f"shap_bar_binary_{suffix}.png",
                args.top_n,
            )
        else:
            for k, name in enumerate(CLASS_NAMES):
                if name == "BIP":
                    continue  # BIP es la clase residual; reportar solo clases QR.
                plot_bar_top_features(
                    feat_df,
                    f"mean_abs_shap_{name}",
                    f"Top features SHAP — clase {name} (multiclase)",
                    fig_dir / f"shap_bar_multiclass_{name}_{suffix}.png",
                    args.top_n,
                )
                plot_beeswarm(
                    shap_arr[..., k],
                    X_shap_df,
                    f"SHAP — clase {name} (multiclase)",
                    fig_dir / f"shap_beeswarm_multiclass_{name}_{suffix}.png",
                    args.top_n,
                )

        summary["tasks"][task] = {
            "holdout_metrics": metrics,
            "top10_features": {
                label: feat_df.nlargest(10, f"mean_abs_shap_{label}")["feature"].tolist()
                for label in class_labels
            },
        }

    if len(fam_tables) > 1:
        plot_family_comparison(
            fam_tables, fig_dir / f"shap_family_comparison_{suffix}.png"
        )

    summary_path = out_dir / f"shap_summary_{suffix}_{args.feature_set}.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    log(f"Resumen: {summary_path}")
    log("Listo.")


if __name__ == "__main__":
    main()
