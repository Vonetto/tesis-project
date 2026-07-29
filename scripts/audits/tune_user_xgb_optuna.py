"""Tune XGBoost hyperparameters for the user-level ML benchmark with Optuna.

This script is intentionally separate from run_user_ml_benchmark.py. It is an
exploratory tuner used to find a small set of candidate hyperparameters on a
subsample. The selected configuration should then be validated with the main
benchmark script on the full matrix.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audits.run_user_ml_benchmark import (  # noqa: E402
    CLASS_NAMES,
    OUT_DIR,
    RANDOM_STATE,
    balanced_sample_weight,
    binary_metrics,
    feature_sets_path,
    load_feature_contract,
    make_folds,
    make_targets,
    matrix_path,
    multiclass_metrics,
    normalize_rows,
    select_features,
    stratified_sample_indices,
    universe_suffix,
)


@dataclass
class TuneConfig:
    run_id: str
    created_at: str
    scope: str
    variant: str
    home_filter: str
    min_trips: int
    min_home_trips: int
    feature_set: str
    task: str
    objective: str
    sample: int
    n_trials: int
    n_splits: int
    timeout: int
    seed: int
    xgb_class_weight: str
    xgb_class_weight_power: float
    tune_class_weight_power: bool
    n_jobs: int


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument("--feature-set", default="full_plus_rhythm_context_routine_daily_tour")
    ap.add_argument("--task", choices=["binary", "multiclass"], default="binary")
    ap.add_argument(
        "--objective",
        choices=[
            "binary_pr_auc",
            "binary_roc_auc",
            "binary_mix",
            "multiclass_macro_auc",
            "multiclass_qr_pr_auc",
        ],
        default="binary_pr_auc",
    )
    ap.add_argument("--sample", type=int, default=500_000)
    ap.add_argument("--n-trials", type=int, default=30)
    ap.add_argument("--n-splits", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=0, help="Timeout en segundos; 0 = sin limite.")
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    ap.add_argument("--run-name", default="", help="Prefijo legible opcional para run_id.")
    ap.add_argument("--n-jobs", type=int, default=-1)
    ap.add_argument(
        "--xgb-class-weight",
        choices=["none", "balanced"],
        default="none",
        help="Weighting fijo. Por defecto no usa pesos de clase.",
    )
    ap.add_argument(
        "--xgb-class-weight-power",
        type=float,
        default=1.0,
        help="Alpha fijo si --xgb-class-weight=balanced.",
    )
    ap.add_argument(
        "--tune-class-weight-power",
        action="store_true",
        help="Incluye alpha de class weighting en el search space, entre 0 y 1.",
    )
    return ap.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.task == "binary" and not args.objective.startswith("binary_"):
        raise ValueError("--task binary requiere objective binary_*")
    if args.task == "multiclass" and not args.objective.startswith("multiclass_"):
        raise ValueError("--task multiclass requiere objective multiclass_*")
    if args.sample <= 0:
        raise ValueError("--sample debe ser positivo para tuning exploratorio")
    if args.n_trials <= 0:
        raise ValueError("--n-trials debe ser positivo")
    if args.n_splits < 2:
        raise ValueError("--n-splits debe ser >= 2")
    if not 0.0 <= args.xgb_class_weight_power <= 1.0:
        raise ValueError("--xgb-class-weight-power debe estar entre 0.0 y 1.0")


def load_sample(args: argparse.Namespace) -> tuple[np.ndarray, np.ndarray, list[str], str]:
    suffix = universe_suffix(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
    )
    df_path = matrix_path(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
    )
    contract_path = feature_sets_path(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
    )
    print(f"Matriz: {df_path}")
    df = pl.read_parquet(df_path)
    contract = load_feature_contract(contract_path)
    features = select_features(df, contract, args.feature_set)
    y_binary, y_multi = make_targets(df)
    y = y_binary if args.task == "binary" else y_multi

    sample_idx = stratified_sample_indices(y, args.sample, args.seed)
    if len(sample_idx) < df.height:
        print(f"Submuestra estratificada: {len(sample_idx):,} de {df.height:,}")
        df = df[sample_idx]
        y = y[sample_idx]

    X = df.select(features).to_numpy().astype(np.float64)
    print(f"Rows={len(y):,} features={len(features)} feature_set={args.feature_set}")
    if args.task == "binary":
        print("Base rate QR:", float(np.mean(y == 1)))
    else:
        print(
            "Base rates:",
            {name: float(np.mean(y == i)) for i, name in enumerate(CLASS_NAMES)},
        )
    return X, y, features, suffix


def suggest_xgb_params(trial, args: argparse.Namespace, task: str) -> tuple[dict, float | None]:
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 300, 1200, step=100),
        "learning_rate": trial.suggest_float("learning_rate", 0.02, 0.12, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 8),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 30.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 30.0, log=True),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        "max_delta_step": trial.suggest_int("max_delta_step", 0, 5),
        "tree_method": "hist",
        "n_jobs": args.n_jobs,
        "random_state": args.seed,
    }
    if task == "binary":
        params |= {"objective": "binary:logistic", "eval_metric": "logloss"}
    else:
        params |= {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
        }

    weight_power = None
    if args.tune_class_weight_power:
        weight_power = trial.suggest_float("class_weight_power", 0.0, 1.0)
    elif args.xgb_class_weight == "balanced":
        weight_power = args.xgb_class_weight_power
    return params, weight_power


def fit_predict_oof(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    params: dict,
    task: str,
    weight_power: float | None,
) -> np.ndarray:
    import xgboost as xgb

    if task == "binary":
        oof = np.zeros(len(y), dtype=np.float64)
    else:
        oof = np.zeros((len(y), 3), dtype=np.float64)

    for fold_id, (tr, te) in enumerate(folds, start=1):
        print(f"    fold {fold_id}/{len(folds)}", flush=True)
        fold_params = dict(params)
        fit_kwargs = {}
        if weight_power is not None:
            if task == "binary":
                n_pos = int(np.sum(y[tr] == 1))
                n_neg = int(np.sum(y[tr] == 0))
                if n_pos > 0:
                    fold_params["scale_pos_weight"] = (n_neg / n_pos) ** weight_power
            else:
                fit_kwargs["sample_weight"] = balanced_sample_weight(y[tr], power=weight_power)

        model = xgb.XGBClassifier(**fold_params)
        model.fit(X[tr], y[tr], **fit_kwargs)
        proba = model.predict_proba(X[te])
        if task == "binary":
            oof[te] = proba[:, 1]
        else:
            oof[te] = normalize_rows(proba)
    return oof


def metric_value(args: argparse.Namespace, y: np.ndarray, pred: np.ndarray) -> tuple[float, dict]:
    if args.task == "binary":
        metrics = binary_metrics(y, pred)
        if args.objective == "binary_pr_auc":
            return metrics["pr_auc"], metrics
        if args.objective == "binary_roc_auc":
            return metrics["roc_auc"], metrics
        if args.objective == "binary_mix":
            return 0.5 * metrics["roc_auc"] + 0.5 * metrics["pr_auc"], metrics
        raise ValueError(f"Objetivo binario no soportado: {args.objective}")

    overall, per_class = multiclass_metrics(y, pred)
    metrics = dict(overall)
    for row in per_class:
        prefix = row["class"]
        metrics[f"{prefix}_roc_auc_ovr"] = row["roc_auc_ovr"]
        metrics[f"{prefix}_pr_auc_ovr"] = row["pr_auc_ovr"]
    if args.objective == "multiclass_macro_auc":
        return metrics["auc_macro_ovr"], metrics
    if args.objective == "multiclass_qr_pr_auc":
        value = 0.5 * metrics["QR_OTHER_pr_auc_ovr"] + 0.5 * metrics["QR_RED_pr_auc_ovr"]
        return value, metrics
    raise ValueError(f"Objetivo multiclase no soportado: {args.objective}")


def build_benchmark_command(args: argparse.Namespace, best_params: dict, run_name: str) -> str:
    parts = [
        "/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python",
        "scripts/audits/run_user_ml_benchmark.py",
        f"--scope {args.scope}",
        f"--variant {args.variant}",
        f"--home-filter {args.home_filter}",
        f"--min-trips {args.min_trips}",
    ]
    if args.min_home_trips > 0:
        parts.append(f"--min-home-trips {args.min_home_trips}")
    parts.extend(
        [
            f"--feature-set {args.feature_set}",
            f"--task {args.task}",
            "--model xgb",
            f"--xgb-n-estimators {int(best_params['n_estimators'])}",
            f"--xgb-max-depth {int(best_params['max_depth'])}",
            f"--xgb-min-child-weight {best_params['min_child_weight']:.8g}",
            f"--xgb-learning-rate {best_params['learning_rate']:.8g}",
            f"--xgb-subsample {best_params['subsample']:.8g}",
            f"--xgb-colsample-bytree {best_params['colsample_bytree']:.8g}",
            f"--xgb-reg-lambda {best_params['reg_lambda']:.8g}",
            f"--xgb-reg-alpha {best_params['reg_alpha']:.8g}",
            f"--xgb-gamma {best_params['gamma']:.8g}",
            f"--xgb-max-delta-step {int(best_params['max_delta_step'])}",
            f"--run-kind benchmark",
            f"--run-name {run_name}",
        ]
    )
    if args.xgb_class_weight == "balanced" or args.tune_class_weight_power:
        power = best_params.get("class_weight_power", args.xgb_class_weight_power)
        parts.extend(
            [
                "--xgb-class-weight balanced",
                f"--xgb-class-weight-power {power:.6g}",
            ]
        )
    return " \\\n  ".join(parts)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    args = parse_args()
    validate_args(args)

    import optuna

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    X, y, features, suffix = load_sample(args)
    folds = make_folds(y, args.n_splits, args.seed)

    run_token = uuid.uuid4().hex[:8]
    run_prefix = f"{args.run_name}_" if args.run_name else ""
    # Keep file names below macOS path component limits; full feature_set lives in config.
    run_id = f"{run_prefix}{suffix}_{args.task}_{args.objective}_optuna_{run_token}"
    cfg = TuneConfig(
        run_id=run_id,
        created_at=datetime.now().isoformat(timespec="seconds"),
        scope=args.scope,
        variant=args.variant,
        home_filter=args.home_filter,
        min_trips=args.min_trips,
        min_home_trips=args.min_home_trips,
        feature_set=args.feature_set,
        task=args.task,
        objective=args.objective,
        sample=args.sample,
        n_trials=args.n_trials,
        n_splits=args.n_splits,
        timeout=args.timeout,
        seed=args.seed,
        xgb_class_weight=args.xgb_class_weight,
        xgb_class_weight_power=args.xgb_class_weight_power,
        tune_class_weight_power=args.tune_class_weight_power,
        n_jobs=args.n_jobs,
    )

    def objective(trial) -> float:
        params, weight_power = suggest_xgb_params(trial, args, args.task)
        print(f"\ntrial {trial.number} params={params}", flush=True)
        if weight_power is not None:
            print(f"  class_weight_power={weight_power:.4f}", flush=True)
        pred = fit_predict_oof(X, y, folds, params, args.task, weight_power)
        value, metrics = metric_value(args, y, pred)
        trial.set_user_attr("objective_value", value)
        for key, metric in metrics.items():
            if isinstance(metric, (int, float, np.floating)):
                trial.set_user_attr(key, float(metric))
        print(f"  {args.objective}={value:.6f}", flush=True)
        return value

    sampler = optuna.samplers.TPESampler(seed=args.seed)
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name=run_id)
    study.optimize(
        objective,
        n_trials=args.n_trials,
        timeout=args.timeout or None,
        gc_after_trial=True,
    )

    trial_rows = []
    for trial in study.trials:
        row = {
            "run_id": run_id,
            "trial": trial.number,
            "state": trial.state.name,
            "value": trial.value,
        }
        row.update({f"param_{k}": v for k, v in trial.params.items()})
        row.update({f"metric_{k}": v for k, v in trial.user_attrs.items()})
        trial_rows.append(row)
    trials_path = OUT_DIR / f"optuna_trials_{run_id}.csv"
    pl.DataFrame(trial_rows).write_csv(trials_path)

    best_params = dict(study.best_trial.params)
    config_payload = {
        **asdict(cfg),
        "features": features,
        "best_trial": study.best_trial.number,
        "best_value": study.best_value,
        "best_params": best_params,
    }
    write_json(OUT_DIR / f"config_{run_id}.json", config_payload)

    benchmark_run_name = f"{args.run_name}_tuned" if args.run_name else f"optuna_{args.objective}_tuned"
    print(f"\nOK run_id={run_id}")
    print(f"Best trial={study.best_trial.number} value={study.best_value:.6f}")
    print("Best params:")
    print(json.dumps(best_params, indent=2, ensure_ascii=False))
    print(f"Trials: {trials_path}")
    print(f"Config: {OUT_DIR / f'config_{run_id}.json'}")
    print("\nBenchmark full sugerido:")
    print(build_benchmark_command(args, best_params, benchmark_run_name))


if __name__ == "__main__":
    main()
