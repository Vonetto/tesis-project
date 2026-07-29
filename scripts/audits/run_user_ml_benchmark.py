"""Benchmark ML final a nivel id_tarjeta.

Corre XGBoost con predicciones out-of-fold para:
  - binary: QR vs BIP
  - multiclass: BIP / QR_OTHER / QR_RED

Este script es distinto de diagnose_ceiling_xgb_gpboost.py:
  - no corre GPBoost;
  - no hace ablations exploratorias por defecto;
  - guarda metricas, predicciones OOF, lift/calibracion e importancias;
  - esta pensado para reporte/reproducibilidad.

Uso inicial:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/run_user_ml_benchmark.py \
    --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
    --feature-set full_contract --task both
"""
from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
OUT_DIR = USER_DIR / "ml_benchmark"

RANDOM_STATE = 42
CLASS_NAMES = ["BIP", "QR_OTHER", "QR_RED"]
CLASS_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}

COHORT_EXACT = {
    "share_trips_2025",
    "share_trips_2024",
    "first_trip_year",
    "last_trip_year",
    "trip_span_days",
    "recent_majority_2025",
    "solo_2025",
}

STRUCTURAL_MISSING_FEATURES = {
    # Requiere presencia en ambos años; missing estructural ~71%.
    "service_route_rcs_2024_2025",
    # Requiere suficiente soporte early/late; missing estructural ~31%.
    "service_route_early_late_rcs",
    "coarse_route_early_late_rcs",
    "hyb_recent_early_late_rcs",
    "hyb_oriente_early_late_rcs",
    "hyb_educ_early_late_cont",
}


@dataclass
class RunConfig:
    run_id: str
    created_at: str
    scope: str
    variant: str
    home_filter: str
    min_trips: int
    min_home_trips: int
    feature_set: str
    task: str
    model: str
    split: str
    n_splits: int
    xgb_n_estimators: int
    xgb_learning_rate: float
    xgb_max_depth: int
    xgb_min_child_weight: float
    xgb_subsample: float
    xgb_colsample_bytree: float
    xgb_reg_lambda: float
    xgb_reg_alpha: float
    xgb_gamma: float
    xgb_max_delta_step: int
    xgb_class_weight: str
    xgb_class_weight_power: float
    cat_iterations: int
    cat_learning_rate: float
    cat_depth: int
    cat_l2_leaf_reg: float
    mlp_hidden_layers: str
    mlp_alpha: float
    mlp_learning_rate_init: float
    mlp_batch_size: int
    mlp_max_iter: int
    mlp_early_stopping: bool
    local_qr_exposure: bool
    local_qr_exposure_min_count: int
    local_qr_exposure_smoothing: float
    sampling_strategy: str
    undersample_binary_positive_share: float
    undersample_multiclass_bip_share: float
    sample: int
    seed: int
    run_kind: str


@dataclass(frozen=True)
class LocalQrExposureData:
    feature_names: list[str]
    group_values: dict[str, np.ndarray]
    target: np.ndarray


def universe_suffix(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> str:
    suffix = f"{scope}_{variant}_{home_filter}_n{min_trips}"
    if min_home_trips > 0:
        suffix += f"_home{min_home_trips}"
    return suffix


def matrix_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> Path:
    return USER_DIR / f"user_model_matrix_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.parquet"


def feature_sets_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> Path:
    return USER_DIR / f"user_model_matrix_feature_sets_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.json"


def load_feature_contract(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"No existe feature contract: {path}")
    return json.loads(path.read_text())


def classify_family(feature: str) -> str:
    if feature in COHORT_EXACT:
        return "cohort"
    if "_bip_load_" in feature:
        return "bip"
    if feature.startswith("res_"):
        return "socio"
    if "_osm_" in feature:
        return "osm"
    if feature.startswith("offer_"):
        return "offer"
    if feature.startswith(
        (
            "service_route",
            "coarse_route",
            "service_within_od",
            "share_trips_in_multi_route_od",
            "top_od_service",
        )
    ):
        return "route"
    if feature.startswith("hyb_"):
        return "hybrid"
    if feature.startswith("rhythm_"):
        return "rhythm"
    if feature.startswith("eco_"):
        return "ecology"
    if feature.startswith("seq_day_repeat"):
        return "sequence_repeat"
    if feature.startswith("nmf_seq_"):
        return "sequence_embedding"
    if feature.startswith("ctx_"):
        return "context"
    if feature.startswith("routine_"):
        return "routine"
    if feature.startswith("tour_"):
        return "daily_tour"
    if feature.startswith("fric_"):
        return "friction"
    if feature.startswith("adopt_"):
        return "adoption_timing"
    if feature.startswith("proto_"):
        return "prototype"
    if feature.startswith("lqe_"):
        return "local_qr_exposure"
    if (
        feature.startswith(
            (
                "home_macro_",
                "origin_top1_macro_",
                "origin_top2_macro_",
                "dest_top1_macro_",
                "activity_top1_macro_",
                "activity_top2_macro_",
            )
        )
        or feature.endswith(("_lon", "_lat"))
        or "_zone_top" in feature
        or feature.endswith("_zone_entropy")
    ):
        return "geo"
    if feature.startswith(
        (
            "hora_",
            "share_lab_",
            "share_no_lab",
            "share_trips_",
            "n_trasbordos",
            "t_vehiculo_",
            "t_espera_",
            "n_viajes",
            "n_dias_activos",
            "n_semanas_activas",
        )
    ):
        return "use"
    return "other"


def dedupe(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


def contract_union(feature_sets: dict[str, list[str]], *, include_plus_sets: bool = True) -> list[str]:
    out: list[str] = []
    for name, values in feature_sets.items():
        if not include_plus_sets and "_plus_" in name:
            continue
        out.extend(values)
    return dedupe(out)


def baseline_contract_features(feature_sets: dict[str, list[str]]) -> list[str]:
    """Return the canonical pre-rhythm wide contract.

    New additive feature sets such as full_plus_rhythm must be requested
    explicitly; otherwise full_contract would drift whenever a sensitivity set
    is added to the JSON.
    """
    if "ml_wide" in feature_sets:
        return dedupe(feature_sets["ml_wide"])
    return contract_union(feature_sets, include_plus_sets=False)


def select_features(df: pl.DataFrame, contract: dict, feature_set: str) -> list[str]:
    fs = contract["feature_sets"]
    baseline_features = baseline_contract_features(fs)
    if feature_set in fs:
        requested = fs[feature_set]
    elif feature_set == "full_contract":
        requested = baseline_features
    elif feature_set in {"usage", "usage_cohort"}:
        requested = [f for f in baseline_features if classify_family(f) in {"use", "cohort"}]
    elif feature_set == "usage_pure":
        requested = [f for f in baseline_features if classify_family(f) == "use"]
    elif feature_set == "usage_socio_geo":
        requested = [
            f
            for f in baseline_features
            if classify_family(f) in {"use", "cohort", "socio", "geo"}
        ]
    elif feature_set == "usage_route":
        requested = [
            f
            for f in baseline_features
            if classify_family(f) in {"use", "cohort", "route", "hybrid"}
        ]
    elif feature_set == "no_structural_missing":
        requested = [f for f in baseline_features if f not in STRUCTURAL_MISSING_FEATURES]
    elif feature_set.startswith("no_"):
        drop_family = feature_set.removeprefix("no_")
        valid_families = {classify_family(f) for f in baseline_features}
        if drop_family not in valid_families:
            raise ValueError(
                f"feature_set={feature_set} invalido: familia '{drop_family}' no existe. "
                f"Familias disponibles: {sorted(valid_families)}"
            )
        requested = [f for f in baseline_features if classify_family(f) != drop_family]
    else:
        raise ValueError(f"feature_set desconocido: {feature_set}")

    requested_unique = dedupe(requested)
    present = [
        f
        for f in requested_unique
        if f in df.columns and df[f].dtype.is_numeric()
    ]
    missing = [f for f in requested_unique if f not in df.columns]
    non_numeric = [
        f
        for f in requested_unique
        if f in df.columns and not df[f].dtype.is_numeric()
    ]
    if missing:
        print(f"  ⚠️ {len(missing)} features ausentes en matriz: {missing[:10]}")
    if non_numeric:
        print(f"  ⚠️ {len(non_numeric)} features no numericas descartadas: {non_numeric[:10]}")
    if not present:
        raise ValueError(f"feature_set={feature_set} no tiene features numericas presentes.")
    return present


def make_targets(df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    tipo = df["tipo_tarjeta"].to_numpy()
    y_binary = (tipo != "BIP").astype(int)
    y_multi = np.array([CLASS_TO_ID[v] for v in tipo], dtype=np.int64)
    return y_binary, y_multi


def stratified_sample_indices(y: np.ndarray, n: int, seed: int) -> np.ndarray:
    if n <= 0 or len(y) <= n:
        return np.arange(len(y))
    rng = np.random.default_rng(seed)
    idx = []
    for cls in np.unique(y):
        cls_idx = np.where(y == cls)[0]
        take = min(int(round(n * len(cls_idx) / len(y))), len(cls_idx))
        idx.append(rng.choice(cls_idx, size=take, replace=False))
    return np.sort(np.concatenate(idx))


def make_folds(y: np.ndarray, n_splits: int, seed: int) -> list[tuple[np.ndarray, np.ndarray]]:
    values, counts = np.unique(y, return_counts=True)
    too_small = {
        int(value): int(count)
        for value, count in zip(values, counts)
        if count < n_splits
    }
    if too_small:
        raise ValueError(
            f"n_splits={n_splits} requiere al menos {n_splits} observaciones por clase; "
            f"clases insuficientes: {too_small}"
        )
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(splitter.split(np.zeros(len(y)), y))


def prepare_local_qr_exposure_data(
    df: pl.DataFrame,
    y_binary: np.ndarray,
    args: argparse.Namespace,
) -> LocalQrExposureData | None:
    if not args.local_qr_exposure:
        return None

    specs = [
        ("lqe_home_zone_qr_rate", ["zona_hogar"]),
        ("lqe_origin_zone_qr_rate", ["origin_zone_top1"]),
        ("lqe_activity_zone_qr_rate", ["activity_zone_top1"]),
        ("lqe_home_origin_zone_qr_rate", ["zona_hogar", "origin_zone_top1"]),
        ("lqe_origin_activity_zone_qr_rate", ["origin_zone_top1", "activity_zone_top1"]),
    ]
    group_values: dict[str, np.ndarray] = {}
    for feature_name, cols in specs:
        if not set(cols).issubset(df.columns):
            continue
        exprs = [pl.col(col).cast(pl.Utf8).fill_null("__MISSING__") for col in cols]
        group_values[feature_name] = df.select(
            pl.concat_str(exprs, separator="|").alias(feature_name)
        )[feature_name].to_numpy()

    if not group_values:
        raise ValueError(
            "--local-qr-exposure requiere al menos una de estas columnas: "
            "zona_hogar, origin_zone_top1, activity_zone_top1"
        )
    return LocalQrExposureData(
        feature_names=list(group_values),
        group_values=group_values,
        target=y_binary.astype(np.float64),
    )


def local_qr_exposure_fold_features(
    exposure: LocalQrExposureData,
    stats_idx: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray]:
    import pandas as pd

    global_rate = float(np.mean(exposure.target[stats_idx]))
    smoothing = float(args.local_qr_exposure_smoothing)
    min_count = int(args.local_qr_exposure_min_count)
    train_cols = []
    test_cols = []

    for keys in exposure.group_values.values():
        stats = (
            pd.DataFrame({"key": keys[stats_idx], "target": exposure.target[stats_idx]})
            .groupby("key", sort=False)["target"]
            .agg(["sum", "count"])
        )

        train_lookup = pd.Series(keys[train_idx])
        train_sum = train_lookup.map(stats["sum"]).fillna(0.0).to_numpy(dtype=np.float64)
        train_count = train_lookup.map(stats["count"]).fillna(0.0).to_numpy(dtype=np.float64)
        train_sum_loo = train_sum - exposure.target[train_idx]
        train_count_loo = train_count - 1.0
        train_rate = np.full(len(train_idx), global_rate, dtype=np.float64)
        train_mask = train_count_loo >= min_count
        train_rate[train_mask] = (
            train_sum_loo[train_mask] + smoothing * global_rate
        ) / (train_count_loo[train_mask] + smoothing)

        test_lookup = pd.Series(keys[test_idx])
        test_sum = test_lookup.map(stats["sum"]).fillna(0.0).to_numpy(dtype=np.float64)
        test_count = test_lookup.map(stats["count"]).fillna(0.0).to_numpy(dtype=np.float64)
        test_rate = np.full(len(test_idx), global_rate, dtype=np.float64)
        test_mask = test_count >= min_count
        test_rate[test_mask] = (
            test_sum[test_mask] + smoothing * global_rate
        ) / (test_count[test_mask] + smoothing)

        train_cols.append(train_rate)
        test_cols.append(test_rate)

    return np.column_stack(train_cols), np.column_stack(test_cols)


def augment_fold_features(
    X: np.ndarray,
    feature_names: list[str],
    exposure: LocalQrExposureData | None,
    stats_idx: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if exposure is None:
        return X[train_idx], X[test_idx], feature_names
    train_exposure, test_exposure = local_qr_exposure_fold_features(
        exposure,
        stats_idx=stats_idx,
        train_idx=train_idx,
        test_idx=test_idx,
        args=args,
    )
    return (
        np.column_stack([X[train_idx], train_exposure]),
        np.column_stack([X[test_idx], test_exposure]),
        feature_names + exposure.feature_names,
    )


def xgb_params(args: argparse.Namespace, task: str) -> dict:
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


def balanced_sample_weight(y: np.ndarray, power: float = 1.0) -> np.ndarray:
    values, counts = np.unique(y, return_counts=True)
    total = len(y)
    n_classes = len(values)
    weight_by_class = {
        value: (total / (n_classes * count)) ** power
        for value, count in zip(values, counts)
    }
    weights = np.array([weight_by_class[value] for value in y], dtype=np.float64)
    return weights / weights.mean()


def undersample_train_indices(
    y: np.ndarray,
    tr: np.ndarray,
    task: str,
    args: argparse.Namespace,
    fold_number: int,
) -> np.ndarray:
    if args.sampling_strategy == "none":
        return tr
    if args.sampling_strategy != "undersample":
        raise ValueError(f"sampling_strategy no soportado: {args.sampling_strategy}")

    rng = np.random.default_rng(args.seed + 10_000 + fold_number)
    y_tr = y[tr]

    if task == "binary":
        target_pos_share = args.undersample_binary_positive_share
        pos = tr[y_tr == 1]
        neg = tr[y_tr == 0]
        if len(pos) == 0 or len(neg) == 0:
            return tr
        current_pos_share = len(pos) / len(tr)
        if target_pos_share <= current_pos_share:
            return tr
        n_neg_keep = int(np.ceil(len(pos) * (1 - target_pos_share) / target_pos_share))
        n_neg_keep = min(n_neg_keep, len(neg))
        neg_keep = rng.choice(neg, size=n_neg_keep, replace=False)
        out = np.concatenate([pos, neg_keep])
    else:
        target_bip_share = args.undersample_multiclass_bip_share
        bip = tr[y_tr == 0]
        qr = tr[y_tr != 0]
        if len(bip) == 0 or len(qr) == 0:
            return tr
        current_bip_share = len(bip) / len(tr)
        if target_bip_share >= current_bip_share:
            return tr
        n_bip_keep = int(np.ceil(target_bip_share * len(qr) / (1 - target_bip_share)))
        n_bip_keep = min(n_bip_keep, len(bip))
        bip_keep = rng.choice(bip, size=n_bip_keep, replace=False)
        out = np.concatenate([qr, bip_keep])

    rng.shuffle(out)
    return np.sort(out)


def train_oof_xgb(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    feature_names: list[str],
    task: str,
    args: argparse.Namespace,
    exposure: LocalQrExposureData | None = None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    import xgboost as xgb

    if task == "binary":
        oof = np.zeros(len(y), dtype=np.float64)
    else:
        oof = np.zeros((len(y), 3), dtype=np.float64)
    fold_id = np.full(len(y), -1, dtype=np.int16)
    importances: list[dict] = []

    for i, (tr, te) in enumerate(folds, start=1):
        tr_fit = undersample_train_indices(y, tr, task, args, i)
        train_msg = f"  fold {i}/{len(folds)} train={len(tr):,} test={len(te):,}"
        if len(tr_fit) != len(tr):
            train_msg += f" train_fit={len(tr_fit):,}"
            if task == "binary":
                train_msg += f" fit_qr_share={float(np.mean(y[tr_fit] == 1)):.3f}"
            else:
                train_msg += (
                    f" fit_bip={float(np.mean(y[tr_fit] == 0)):.3f}"
                    f" fit_other={float(np.mean(y[tr_fit] == 1)):.3f}"
                    f" fit_red={float(np.mean(y[tr_fit] == 2)):.3f}"
                )
        print(train_msg)
        X_tr, X_te, fold_feature_names = augment_fold_features(
            X,
            feature_names,
            exposure,
            stats_idx=tr,
            train_idx=tr_fit,
            test_idx=te,
            args=args,
        )
        params = xgb_params(args, task)
        fit_kwargs = {}
        if args.xgb_class_weight == "balanced":
            if task == "binary":
                n_pos = int(np.sum(y[tr_fit] == 1))
                n_neg = int(np.sum(y[tr_fit] == 0))
                if n_pos > 0:
                    params["scale_pos_weight"] = (n_neg / n_pos) ** args.xgb_class_weight_power
            else:
                fit_kwargs["sample_weight"] = balanced_sample_weight(
                    y[tr_fit],
                    power=args.xgb_class_weight_power,
                )
        model = xgb.XGBClassifier(**params)
        model.fit(X_tr, y[tr_fit], **fit_kwargs)
        proba = model.predict_proba(X_te)
        if task == "binary":
            oof[te] = proba[:, 1]
        else:
            oof[te] = normalize_rows(proba)
        fold_id[te] = i

        booster = model.get_booster()
        gain = booster.get_score(importance_type="gain")
        weight = booster.get_score(importance_type="weight")
        for feature_idx, feature in enumerate(fold_feature_names):
            # Con inputs NumPy, XGBoost usa claves f0, f1, ... en vez del nombre
            # original de la columna. Mantener este mapeo evita importancias en cero.
            xgb_key = feature if feature in gain or feature in weight else f"f{feature_idx}"
            importances.append(
                {
                    "fold": i,
                    "feature": feature,
                    "family": classify_family(feature),
                    "gain": float(gain.get(xgb_key, 0.0)),
                    "weight": float(weight.get(xgb_key, 0.0)),
                }
            )

    return oof, fold_id, importances


def train_oof_logit(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    feature_names: list[str],
    task: str,
    args: argparse.Namespace,
    exposure: LocalQrExposureData | None = None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    if task == "binary":
        oof = np.zeros(len(y), dtype=np.float64)
    else:
        oof = np.zeros((len(y), 3), dtype=np.float64)
    fold_id = np.full(len(y), -1, dtype=np.int16)
    importances: list[dict] = []

    for i, (tr, te) in enumerate(folds, start=1):
        print(f"  fold {i}/{len(folds)} train={len(tr):,} test={len(te):,}")
        X_tr, X_te, fold_feature_names = augment_fold_features(
            X,
            feature_names,
            exposure,
            stats_idx=tr,
            train_idx=tr,
            test_idx=te,
            args=args,
        )
        clf = LogisticRegression(
            penalty="l2",
            C=args.logit_c,
            solver="saga",
            max_iter=args.logit_max_iter,
            class_weight=args.class_weight,
            n_jobs=args.n_jobs,
            random_state=args.seed + i,
        )
        pipe = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            clf,
        )
        pipe.fit(X_tr, y[tr])
        proba = pipe.predict_proba(X_te)
        if task == "binary":
            oof[te] = proba[:, 1]
            coef = pipe.named_steps["logisticregression"].coef_[0]
            for feature, value in zip(fold_feature_names, coef):
                importances.append(
                    {
                        "fold": i,
                        "feature": feature,
                        "family": classify_family(feature),
                        "coef": float(value),
                        "abs_coef": float(abs(value)),
                    }
                )
        else:
            oof[te] = normalize_rows(proba)
            coef = pipe.named_steps["logisticregression"].coef_
            for class_id, class_name in enumerate(CLASS_NAMES):
                for feature, value in zip(fold_feature_names, coef[class_id]):
                    importances.append(
                        {
                            "fold": i,
                            "class": class_name,
                            "feature": feature,
                            "family": classify_family(feature),
                            "coef": float(value),
                            "abs_coef": float(abs(value)),
                        }
                    )
        fold_id[te] = i

    return oof, fold_id, importances


def train_oof_catboost(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    feature_names: list[str],
    task: str,
    args: argparse.Namespace,
    exposure: LocalQrExposureData | None = None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    try:
        from catboost import CatBoostClassifier
    except ImportError as exc:
        raise ImportError(
            "CatBoost no esta instalado en este entorno. Instalar catboost o usar --model xgb/logit."
        ) from exc

    if task == "binary":
        oof = np.zeros(len(y), dtype=np.float64)
        loss_function = "Logloss"
    else:
        oof = np.zeros((len(y), 3), dtype=np.float64)
        loss_function = "MultiClass"
    fold_id = np.full(len(y), -1, dtype=np.int16)
    importances: list[dict] = []

    for i, (tr, te) in enumerate(folds, start=1):
        print(f"  fold {i}/{len(folds)} train={len(tr):,} test={len(te):,}")
        X_tr, X_te, fold_feature_names = augment_fold_features(
            X,
            feature_names,
            exposure,
            stats_idx=tr,
            train_idx=tr,
            test_idx=te,
            args=args,
        )
        model = CatBoostClassifier(
            iterations=args.cat_iterations,
            learning_rate=args.cat_learning_rate,
            depth=args.cat_depth,
            l2_leaf_reg=args.cat_l2_leaf_reg,
            loss_function=loss_function,
            random_seed=args.seed + i,
            thread_count=args.n_jobs,
            verbose=False,
            allow_writing_files=False,
        )
        model.fit(X_tr, y[tr])
        proba = model.predict_proba(X_te)
        if task == "binary":
            oof[te] = proba[:, 1]
        else:
            oof[te] = normalize_rows(proba)
        fold_id[te] = i

        for feature, value in zip(fold_feature_names, model.get_feature_importance()):
            importances.append(
                {
                    "fold": i,
                    "feature": feature,
                    "family": classify_family(feature),
                    "gain": float(value),
                    "weight": float(value > 0),
                }
            )

    return oof, fold_id, importances


def parse_mlp_hidden_layers(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values or any(value <= 0 for value in values):
        raise ValueError("--mlp-hidden-layers debe ser una lista positiva, por ejemplo 64,32")
    return values


def train_oof_mlp(
    X: np.ndarray,
    y: np.ndarray,
    folds: list[tuple[np.ndarray, np.ndarray]],
    feature_names: list[str],
    task: str,
    args: argparse.Namespace,
    exposure: LocalQrExposureData | None = None,
) -> tuple[np.ndarray, np.ndarray, list[dict]]:
    from sklearn.neural_network import MLPClassifier

    if task == "binary":
        oof = np.zeros(len(y), dtype=np.float64)
    else:
        oof = np.zeros((len(y), 3), dtype=np.float64)
    fold_id = np.full(len(y), -1, dtype=np.int16)
    hidden_layers = parse_mlp_hidden_layers(args.mlp_hidden_layers)

    for i, (tr, te) in enumerate(folds, start=1):
        print(f"  fold {i}/{len(folds)} train={len(tr):,} test={len(te):,}")
        X_tr, X_te, _ = augment_fold_features(
            X,
            feature_names,
            exposure,
            stats_idx=tr,
            train_idx=tr,
            test_idx=te,
            args=args,
        )
        clf = MLPClassifier(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            solver="adam",
            alpha=args.mlp_alpha,
            batch_size=args.mlp_batch_size,
            learning_rate_init=args.mlp_learning_rate_init,
            max_iter=args.mlp_max_iter,
            early_stopping=args.mlp_early_stopping,
            validation_fraction=0.1,
            n_iter_no_change=5,
            random_state=args.seed + i,
            verbose=False,
        )
        pipe = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            clf,
        )
        pipe.fit(X_tr, y[tr])
        proba = pipe.predict_proba(X_te)
        if task == "binary":
            oof[te] = proba[:, 1]
        else:
            oof[te] = normalize_rows(proba)
        fold_id[te] = i

    return oof, fold_id, []


def normalize_rows(proba: np.ndarray) -> np.ndarray:
    proba = np.asarray(proba, dtype=np.float64)
    proba = np.clip(proba, 1e-15, 1.0)
    denom = proba.sum(axis=1, keepdims=True)
    denom = np.where(denom <= 0, 1.0, denom)
    return proba / denom


def topk_metrics(y: np.ndarray, score: np.ndarray, ks: tuple[float, ...] = (0.05, 0.10)) -> list[dict]:
    order = np.argsort(-score)
    base = float(y.mean())
    rows = []
    for k in ks:
        n_top = max(1, int(np.ceil(len(y) * k)))
        top = y[order[:n_top]]
        precision = float(top.mean())
        rows.append(
            {
                "top_share": k,
                "n_top": n_top,
                "base_rate": base,
                "precision": precision,
                "lift": precision / base if base > 0 else np.nan,
            }
        )
    return rows


def calibration_by_decile(y: np.ndarray, score: np.ndarray, n_bins: int = 10) -> list[dict]:
    # qcut puede colapsar bins si hay muchos empates; rank rompe empates de forma estable.
    ranks = pl.Series("rank", score).rank(method="ordinal", descending=False)
    bins = (ranks / (len(score) + 1) * n_bins).ceil().cast(pl.Int64)
    df = pl.DataFrame({"y": y, "score": score, "bin": bins}).with_columns(
        pl.col("bin").clip(1, n_bins)
    )
    return (
        df.group_by("bin")
        .agg(
            n=pl.len(),
            score_mean=pl.col("score").mean(),
            score_min=pl.col("score").min(),
            score_max=pl.col("score").max(),
            observed_rate=pl.col("y").mean(),
        )
        .sort("bin")
        .to_dicts()
    )


def binary_metrics(y: np.ndarray, score: np.ndarray) -> dict:
    pred = (score >= 0.5).astype(int)
    return {
        "roc_auc": roc_auc_score(y, score),
        "pr_auc": average_precision_score(y, score),
        "log_loss": log_loss(y, np.column_stack([1 - score, score]), labels=[0, 1]),
        "brier": brier_score_loss(y, score),
        "base_rate": float(y.mean()),
        "balanced_accuracy_at_050": balanced_accuracy_score(y, pred),
        "macro_f1_at_050": f1_score(y, pred, average="macro"),
        "precision_at_050": precision_score(y, pred, zero_division=0),
    }


def multiclass_metrics(y: np.ndarray, proba: np.ndarray) -> tuple[dict, list[dict]]:
    proba = normalize_rows(proba)
    pred = proba.argmax(axis=1)
    out = {
        "log_loss": log_loss(y, proba, labels=[0, 1, 2]),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro"),
        "auc_macro_ovr": roc_auc_score(y, proba, multi_class="ovr", average="macro"),
        "auc_weighted_ovr": roc_auc_score(y, proba, multi_class="ovr", average="weighted"),
    }
    per_class = []
    for class_id, class_name in enumerate(CLASS_NAMES):
        yb = (y == class_id).astype(int)
        score = proba[:, class_id]
        per_class.append(
            {
                "class": class_name,
                "base_rate": float(yb.mean()),
                "roc_auc_ovr": roc_auc_score(yb, score),
                "pr_auc_ovr": average_precision_score(yb, score),
            }
        )
    return out, per_class


def append_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    df = pl.DataFrame(rows)
    if path.exists():
        old = pl.read_csv(path)
        df = pl.concat([old, df], how="diagonal_relaxed")
    df.write_csv(path)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def save_binary_outputs(
    run_id: str,
    ids: np.ndarray,
    tipo: np.ndarray,
    y: np.ndarray,
    score: np.ndarray,
    fold_id: np.ndarray,
    save_oof: bool,
) -> tuple[list[dict], list[dict]]:
    metrics = [{"metric_scope": "binary", **binary_metrics(y, score)}]
    lift_rows = [{"metric_scope": "binary", **r} for r in topk_metrics(y, score)]
    cal_rows = [{"metric_scope": "binary", **r} for r in calibration_by_decile(y, score)]
    if save_oof:
        pl.DataFrame(
            {
                "id_tarjeta": ids,
                "tipo_tarjeta": tipo,
                "fold_id": fold_id,
                "y_qr": y,
                "p_qr": score,
            }
        ).write_parquet(OUT_DIR / f"oof_predictions_{run_id}_binary.parquet")
    pl.DataFrame(lift_rows).write_csv(OUT_DIR / f"lift_{run_id}_binary.csv")
    pl.DataFrame(cal_rows).write_csv(OUT_DIR / f"calibration_{run_id}_binary.csv")
    return metrics, lift_rows


def save_multiclass_outputs(
    run_id: str,
    ids: np.ndarray,
    tipo: np.ndarray,
    y: np.ndarray,
    proba: np.ndarray,
    fold_id: np.ndarray,
    save_oof: bool,
) -> tuple[list[dict], list[dict], list[dict]]:
    overall, per_class = multiclass_metrics(y, proba)
    metrics = [{"metric_scope": "multiclass", **overall}]
    metrics.extend({"metric_scope": "multiclass_ovr", **r} for r in per_class)

    lift_rows = []
    cal_rows = []
    for class_id, class_name in enumerate(CLASS_NAMES):
        yb = (y == class_id).astype(int)
        score = proba[:, class_id]
        lift_rows.extend(
            {"metric_scope": "multiclass_ovr", "class": class_name, **r}
            for r in topk_metrics(yb, score)
        )
        cal_rows.extend(
            {"metric_scope": "multiclass_ovr", "class": class_name, **r}
            for r in calibration_by_decile(yb, score)
        )

    cm = confusion_matrix(y, proba.argmax(axis=1), labels=[0, 1, 2])
    cm_rows = [
        {
            "true_class": CLASS_NAMES[i],
            "pred_class": CLASS_NAMES[j],
            "n": int(cm[i, j]),
        }
        for i in range(3)
        for j in range(3)
    ]

    if save_oof:
        pl.DataFrame(
            {
                "id_tarjeta": ids,
                "tipo_tarjeta": tipo,
                "fold_id": fold_id,
                "y_class": y,
                "p_BIP": proba[:, 0],
                "p_QR_OTHER": proba[:, 1],
                "p_QR_RED": proba[:, 2],
            }
        ).write_parquet(OUT_DIR / f"oof_predictions_{run_id}_multiclass.parquet")
    pl.DataFrame(lift_rows).write_csv(OUT_DIR / f"lift_{run_id}_multiclass.csv")
    pl.DataFrame(cal_rows).write_csv(OUT_DIR / f"calibration_{run_id}_multiclass.csv")
    pl.DataFrame(cm_rows).write_csv(OUT_DIR / f"confusion_matrix_{run_id}_multiclass.csv")
    return metrics, lift_rows, cm_rows


def summarize_importance(run_id: str, rows: list[dict], task: str) -> None:
    if not rows:
        return
    df = pl.DataFrame(rows).with_columns(
        pl.lit(run_id).alias("run_id"),
        pl.lit(task).alias("task"),
    )
    if "gain" not in df.columns and "abs_coef" in df.columns:
        group_cols = ["run_id", "task", "feature", "family"]
        if "class" in df.columns:
            group_cols.insert(2, "class")
        feature_imp = (
            df.group_by(group_cols)
            .agg(
                coef_mean=pl.col("coef").mean(),
                abs_coef_mean=pl.col("abs_coef").mean(),
                abs_coef_sum=pl.col("abs_coef").sum(),
            )
            .sort("abs_coef_sum", descending=True)
        )
        family_group_cols = ["run_id", "task", "family"]
        if "class" in df.columns:
            family_group_cols.insert(2, "class")
        family_imp = (
            feature_imp.group_by(family_group_cols)
            .agg(
                abs_coef_sum=pl.col("abs_coef_sum").sum(),
                n_features_used=(pl.col("abs_coef_sum") > 0).sum(),
                n_features=pl.len(),
            )
            .with_columns(
                (pl.col("abs_coef_sum") / pl.col("abs_coef_sum").sum().over(
                    [c for c in family_group_cols if c != "family"]
                )).alias("abs_coef_share")
            )
            .sort("abs_coef_sum", descending=True)
        )
        feature_imp.write_csv(OUT_DIR / f"feature_importance_{run_id}_{task}.csv")
        family_imp.write_csv(OUT_DIR / f"family_importance_{run_id}_{task}.csv")
        return

    feature_imp = (
        df.group_by(["run_id", "task", "feature", "family"])
        .agg(
            gain_mean=pl.col("gain").mean(),
            gain_sum=pl.col("gain").sum(),
            weight_mean=pl.col("weight").mean(),
            weight_sum=pl.col("weight").sum(),
        )
        .sort("gain_sum", descending=True)
    )
    family_imp = (
        feature_imp.group_by(["run_id", "task", "family"])
        .agg(
            gain_sum=pl.col("gain_sum").sum(),
            weight_sum=pl.col("weight_sum").sum(),
            n_features_used=(pl.col("gain_sum") > 0).sum(),
            n_features=pl.len(),
        )
        .with_columns(
            (pl.col("gain_sum") / pl.col("gain_sum").sum()).alias("gain_share")
        )
        .sort("gain_sum", descending=True)
    )
    feature_imp.write_csv(OUT_DIR / f"feature_importance_{run_id}_{task}.csv")
    family_imp.write_csv(OUT_DIR / f"family_importance_{run_id}_{task}.csv")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument(
        "--feature-set",
        default="full_contract",
        help=(
            "Nombre del feature_set del JSON, por ejemplo full_plus_rhythm/logit_plus_rhythm, "
            "o derivado: usage/usage_cohort, usage_pure, usage_socio_geo, "
            "usage_route, full_contract, no_structural_missing, no_*."
        ),
    )
    ap.add_argument("--task", choices=["binary", "multiclass", "both"], default="both")
    ap.add_argument("--model", choices=["xgb", "logit", "catboost", "mlp"], default="xgb")
    ap.add_argument("--split", choices=["random"], default="random")
    ap.add_argument("--n-splits", type=int, default=5)
    ap.add_argument("--sample", type=int, default=0, help="Submuestra estratificada para smoke/iteracion.")
    ap.add_argument("--run-kind", choices=["smoke", "benchmark"], default="benchmark")
    ap.add_argument("--run-name", default="", help="Prefijo legible opcional para run_id.")
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
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
    ap.add_argument(
        "--xgb-class-weight",
        choices=["none", "balanced"],
        default="none",
        help=(
            "Para XGB: binary usa scale_pos_weight por fold; multiclass usa sample_weight "
            "inverso a frecuencia de clase por fold."
        ),
    )
    ap.add_argument(
        "--xgb-class-weight-power",
        type=float,
        default=1.0,
        help=(
            "Exponente alpha para suavizar --xgb-class-weight balanced. "
            "0.0 equivale a sin weighting; 1.0 equivale a balanced completo."
        ),
    )
    ap.add_argument("--cat-iterations", type=int, default=500)
    ap.add_argument("--cat-learning-rate", type=float, default=0.05)
    ap.add_argument("--cat-depth", type=int, default=6)
    ap.add_argument("--cat-l2-leaf-reg", type=float, default=3.0)
    ap.add_argument("--mlp-hidden-layers", default="64,32")
    ap.add_argument("--mlp-alpha", type=float, default=1e-4)
    ap.add_argument("--mlp-learning-rate-init", type=float, default=1e-3)
    ap.add_argument("--mlp-batch-size", type=int, default=4096)
    ap.add_argument("--mlp-max-iter", type=int, default=25)
    ap.add_argument("--mlp-no-early-stopping", action="store_true")
    ap.add_argument(
        "--local-qr-exposure",
        action="store_true",
        help=(
            "Agrega target encodings fold-safe de prevalencia QR por zona/origen/actividad. "
            "Se calculan solo con el train fold y con leave-one-out para filas de train."
        ),
    )
    ap.add_argument(
        "--local-qr-exposure-min-count",
        type=int,
        default=100,
        help="Soporte minimo de grupo para usar tasa QR local; grupos chicos caen al promedio train-fold.",
    )
    ap.add_argument(
        "--local-qr-exposure-smoothing",
        type=float,
        default=100.0,
        help="Suavizado hacia el promedio QR del train fold para las tasas locales.",
    )
    ap.add_argument(
        "--sampling-strategy",
        choices=["none", "undersample"],
        default="none",
        help=(
            "Resampling aplicado solo dentro de cada train fold. "
            "El fold de test conserva la distribucion real."
        ),
    )
    ap.add_argument(
        "--undersample-binary-positive-share",
        type=float,
        default=0.35,
        help="Share objetivo de QR en train fold binario al usar --sampling-strategy undersample.",
    )
    ap.add_argument(
        "--undersample-multiclass-bip-share",
        type=float,
        default=0.60,
        help="Share objetivo de BIP en train fold multiclase al usar --sampling-strategy undersample.",
    )
    ap.add_argument("--n-jobs", type=int, default=-1)
    ap.add_argument("--logit-c", type=float, default=1.0)
    ap.add_argument("--logit-max-iter", type=int, default=1000)
    ap.add_argument("--class-weight", choices=["balanced", "none"], default="none")
    ap.add_argument("--no-save-oof", action="store_true")
    ap.add_argument("--quick", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.0 <= args.xgb_class_weight_power <= 1.0:
        raise ValueError("--xgb-class-weight-power debe estar entre 0.0 y 1.0")
    if not 0.0 < args.undersample_binary_positive_share < 1.0:
        raise ValueError("--undersample-binary-positive-share debe estar entre 0.0 y 1.0")
    if not 0.0 < args.undersample_multiclass_bip_share < 1.0:
        raise ValueError("--undersample-multiclass-bip-share debe estar entre 0.0 y 1.0")
    if args.mlp_batch_size <= 0:
        raise ValueError("--mlp-batch-size debe ser positivo")
    if args.mlp_max_iter <= 0:
        raise ValueError("--mlp-max-iter debe ser positivo")
    if args.local_qr_exposure_min_count < 1:
        raise ValueError("--local-qr-exposure-min-count debe ser >= 1")
    if args.local_qr_exposure_smoothing < 0:
        raise ValueError("--local-qr-exposure-smoothing debe ser >= 0")
    args.mlp_early_stopping = not args.mlp_no_early_stopping
    parse_mlp_hidden_layers(args.mlp_hidden_layers)
    if args.sampling_strategy != "none" and args.model != "xgb":
        raise ValueError("Por ahora --sampling-strategy solo esta implementado para --model xgb")
    if args.sampling_strategy != "none" and args.xgb_class_weight != "none":
        print("  ⚠️ Usando sampling y class weights a la vez; interpretar como sensibilidad combinada.")
    if args.quick:
        args.sample = args.sample or 200_000
        args.xgb_n_estimators = min(args.xgb_n_estimators, 150)
        args.cat_iterations = min(args.cat_iterations, 150)
        args.mlp_max_iter = min(args.mlp_max_iter, 10)
        if args.run_kind == "benchmark":
            args.run_kind = "smoke"
        print("[QUICK] sample<=200k, xgb/cat<=150 iter, mlp<=10 iter")
    if args.class_weight == "none":
        args.class_weight = None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = universe_suffix(
        args.scope,
        args.variant,
        args.home_filter,
        args.min_trips,
        args.min_home_trips,
    )
    df_path = matrix_path(args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips)
    print(f"Matriz: {df_path}")
    df = pl.read_parquet(df_path)
    contract = load_feature_contract(
        feature_sets_path(args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips)
    )
    features = select_features(df, contract, args.feature_set)
    y_binary, y_multi = make_targets(df)

    sample_idx = stratified_sample_indices(y_multi, args.sample, args.seed)
    if len(sample_idx) < df.height:
        print(f"Submuestra estratificada: {len(sample_idx):,} de {df.height:,}")
        df = df[sample_idx]
        y_binary = y_binary[sample_idx]
        y_multi = y_multi[sample_idx]

    X = df.select(features).to_numpy().astype(np.float64)
    local_exposure = prepare_local_qr_exposure_data(df, y_binary, args)
    effective_features = features + (local_exposure.feature_names if local_exposure is not None else [])
    ids = df["id_tarjeta"].to_numpy()
    tipo = df["tipo_tarjeta"].to_numpy()
    print(f"Rows={df.height:,} features={len(effective_features)} feature_set={args.feature_set}")
    if local_exposure is not None:
        print(f"Local QR exposure features: {', '.join(local_exposure.feature_names)}")
    print(
        "Base rates:",
        {
            "QR": float(y_binary.mean()),
            "BIP": float(np.mean(y_multi == 0)),
            "QR_OTHER": float(np.mean(y_multi == 1)),
            "QR_RED": float(np.mean(y_multi == 2)),
        },
    )

    run_token = uuid.uuid4().hex[:8]
    run_prefix = f"{args.run_name}_" if args.run_name else ""
    run_id = f"{run_prefix}{suffix}_{args.feature_set}_{args.task}_{args.model}_{args.split}_{run_token}"
    cfg = RunConfig(
        run_id=run_id,
        created_at=datetime.now().isoformat(timespec="seconds"),
        scope=args.scope,
        variant=args.variant,
        home_filter=args.home_filter,
        min_trips=args.min_trips,
        min_home_trips=args.min_home_trips,
        feature_set=args.feature_set,
        task=args.task,
        model=args.model,
        split=args.split,
        n_splits=args.n_splits,
        xgb_n_estimators=args.xgb_n_estimators,
        xgb_learning_rate=args.xgb_learning_rate,
        xgb_max_depth=args.xgb_max_depth,
        xgb_min_child_weight=args.xgb_min_child_weight,
        xgb_subsample=args.xgb_subsample,
        xgb_colsample_bytree=args.xgb_colsample_bytree,
        xgb_reg_lambda=args.xgb_reg_lambda,
        xgb_reg_alpha=args.xgb_reg_alpha,
        xgb_gamma=args.xgb_gamma,
        xgb_max_delta_step=args.xgb_max_delta_step,
        xgb_class_weight=args.xgb_class_weight,
        xgb_class_weight_power=args.xgb_class_weight_power,
        cat_iterations=args.cat_iterations,
        cat_learning_rate=args.cat_learning_rate,
        cat_depth=args.cat_depth,
        cat_l2_leaf_reg=args.cat_l2_leaf_reg,
        mlp_hidden_layers=args.mlp_hidden_layers,
        mlp_alpha=args.mlp_alpha,
        mlp_learning_rate_init=args.mlp_learning_rate_init,
        mlp_batch_size=args.mlp_batch_size,
        mlp_max_iter=args.mlp_max_iter,
        mlp_early_stopping=args.mlp_early_stopping,
        local_qr_exposure=args.local_qr_exposure,
        local_qr_exposure_min_count=args.local_qr_exposure_min_count,
        local_qr_exposure_smoothing=args.local_qr_exposure_smoothing,
        sampling_strategy=args.sampling_strategy,
        undersample_binary_positive_share=args.undersample_binary_positive_share,
        undersample_multiclass_bip_share=args.undersample_multiclass_bip_share,
        sample=args.sample,
        seed=args.seed,
        run_kind=args.run_kind,
    )
    write_json(OUT_DIR / f"config_{run_id}.json", {**asdict(cfg), "features": effective_features})
    if args.run_kind == "benchmark":
        append_csv(OUT_DIR / "runs.csv", [asdict(cfg) | {"n_rows": df.height, "n_features": len(effective_features)}])

    metric_rows: list[dict] = []

    if args.task in {"binary", "both"}:
        print(f"\n[{args.model} binary]")
        folds = make_folds(y_binary, args.n_splits, args.seed)
        trainer = {
            "xgb": train_oof_xgb,
            "logit": train_oof_logit,
            "catboost": train_oof_catboost,
            "mlp": train_oof_mlp,
        }[args.model]
        score, fold_id, imp = trainer(X, y_binary, folds, features, "binary", args, local_exposure)
        summarize_importance(run_id, imp, "binary")
        metrics, _ = save_binary_outputs(
            run_id,
            ids,
            tipo,
            y_binary,
            score,
            fold_id,
            save_oof=not args.no_save_oof,
        )
        metric_rows.extend(metrics)
        print(f"  AUC={metrics[0]['roc_auc']:.4f} PR-AUC={metrics[0]['pr_auc']:.4f}")

    if args.task in {"multiclass", "both"}:
        print(f"\n[{args.model} multiclass]")
        folds = make_folds(y_multi, args.n_splits, args.seed)
        trainer = {
            "xgb": train_oof_xgb,
            "logit": train_oof_logit,
            "catboost": train_oof_catboost,
            "mlp": train_oof_mlp,
        }[args.model]
        proba, fold_id, imp = trainer(X, y_multi, folds, features, "multiclass", args, local_exposure)
        summarize_importance(run_id, imp, "multiclass")
        metrics, _, _ = save_multiclass_outputs(
            run_id,
            ids,
            tipo,
            y_multi,
            proba,
            fold_id,
            save_oof=not args.no_save_oof,
        )
        metric_rows.extend(metrics)
        overall = metrics[0]
        print(f"  macro OvR AUC={overall['auc_macro_ovr']:.4f} balAcc={overall['balanced_accuracy']:.4f}")

    metric_rows = [
        {
            "run_id": run_id,
            "universe": suffix,
            "feature_set": args.feature_set,
            "task_requested": args.task,
            "split": args.split,
            "model": args.model,
            "n_rows": df.height,
            "n_features": len(effective_features),
            **row,
        }
        for row in metric_rows
    ]
    if args.run_kind == "benchmark":
        append_csv(OUT_DIR / "metrics.csv", metric_rows)
    pl.DataFrame(metric_rows).write_csv(OUT_DIR / f"metrics_{run_id}.csv")

    print(f"\nOK run_id={run_id}")
    print(f"Outputs: {OUT_DIR}")


if __name__ == "__main__":
    main()
