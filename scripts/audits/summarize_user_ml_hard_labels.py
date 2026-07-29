"""Summarize hard-label metrics from saved user-level ML OOF predictions."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.audits.run_user_ml_benchmark import CLASS_NAMES, OUT_DIR  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", action="append", default=[], help="run_id explicito; repetible.")
    ap.add_argument(
        "--run-id-prefix",
        action="append",
        default=[],
        help="Prefijo de run_id a buscar en config_<run_id>.json; repetible.",
    )
    ap.add_argument("--task", choices=["binary", "multiclass", "both"], default="both")
    ap.add_argument("--out-name", default="", help="Sufijo legible para el CSV de salida.")
    ap.add_argument(
        "--benchmark-dir",
        type=Path,
        default=None,
        help="Directorio ml_benchmark alternativo; util si tmp/audits/user_level_redesign es un symlink roto.",
    )
    return ap.parse_args()


def run_id_from_artifact(path: Path) -> str | None:
    name = path.name
    if name.startswith("config_") and name.endswith(".json"):
        return name.removeprefix("config_").removesuffix(".json")
    if name.startswith("metrics_") and name.endswith(".csv"):
        return name.removeprefix("metrics_").removesuffix(".csv")
    if name.startswith("oof_predictions_") and name.endswith("_binary.parquet"):
        return name.removeprefix("oof_predictions_").removesuffix("_binary.parquet")
    if name.startswith("oof_predictions_") and name.endswith("_multiclass.parquet"):
        return name.removeprefix("oof_predictions_").removesuffix("_multiclass.parquet")
    return None


def collect_run_ids(args: argparse.Namespace) -> list[str]:
    run_ids = list(args.run_id)
    for prefix in args.run_id_prefix:
        patterns = [
            f"config_{prefix}*.json",
            f"metrics_{prefix}*.csv",
            f"oof_predictions_{prefix}*_binary.parquet",
            f"oof_predictions_{prefix}*_multiclass.parquet",
        ]
        for pattern in patterns:
            for path in sorted(OUT_DIR.glob(pattern)):
                run_id = run_id_from_artifact(path)
                if run_id is not None:
                    run_ids.append(run_id)
    seen = set()
    out = []
    for run_id in run_ids:
        if run_id not in seen:
            seen.add(run_id)
            out.append(run_id)
    if not out:
        raise ValueError(
            "No se encontraron run_ids. Usa --run-id o --run-id-prefix. "
            f"OUT_DIR={OUT_DIR} exists={OUT_DIR.exists()} resolved={OUT_DIR.resolve(strict=False)}"
        )
    return out


def read_config(run_id: str) -> dict:
    path = OUT_DIR / f"config_{run_id}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def metric_rows(run_id: str) -> dict[str, dict]:
    path = OUT_DIR / f"metrics_{run_id}.csv"
    if not path.exists():
        return {}
    rows = pl.read_csv(path).to_dicts()
    return {row["metric_scope"]: row for row in rows}


def add_config_fields(row: dict, cfg: dict, metrics_by_scope: dict[str, dict]) -> dict:
    metric_scope = row["metric_scope"]
    metrics = metrics_by_scope.get(metric_scope, {})
    row.update(
        {
            "feature_set": cfg.get("feature_set"),
            "sampling_strategy": cfg.get("sampling_strategy", "none"),
            "undersample_binary_positive_share": cfg.get("undersample_binary_positive_share"),
            "undersample_multiclass_bip_share": cfg.get("undersample_multiclass_bip_share"),
            "xgb_class_weight": cfg.get("xgb_class_weight", "none"),
            "xgb_class_weight_power": cfg.get("xgb_class_weight_power"),
            "roc_auc": metrics.get("roc_auc"),
            "pr_auc": metrics.get("pr_auc"),
            "auc_macro_ovr": metrics.get("auc_macro_ovr"),
            "auc_weighted_ovr": metrics.get("auc_weighted_ovr"),
            "log_loss": metrics.get("log_loss"),
        }
    )
    return row


def binary_summary(run_id: str, cfg: dict, metrics_by_scope: dict[str, dict]) -> dict | None:
    path = OUT_DIR / f"oof_predictions_{run_id}_binary.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    y = df["y_qr"].to_numpy()
    pred = (df["p_qr"].to_numpy() >= 0.5).astype(int)
    labels = [0, 1]
    precision = precision_score(y, pred, labels=labels, average=None, zero_division=0)
    recall = recall_score(y, pred, labels=labels, average=None, zero_division=0)
    row = {
        "run_id": run_id,
        "metric_scope": "binary",
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
        "BIP_precision": precision[0],
        "BIP_recall": recall[0],
        "QR_precision": precision[1],
        "QR_recall": recall[1],
        "pred_BIP_share": float(np.mean(pred == 0)),
        "pred_QR_share": float(np.mean(pred == 1)),
        "true_BIP_share": float(np.mean(y == 0)),
        "true_QR_share": float(np.mean(y == 1)),
    }
    return add_config_fields(row, cfg, metrics_by_scope)


def multiclass_summary(run_id: str, cfg: dict, metrics_by_scope: dict[str, dict]) -> dict | None:
    path = OUT_DIR / f"oof_predictions_{run_id}_multiclass.parquet"
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    y = df["y_class"].to_numpy()
    proba = df.select(["p_BIP", "p_QR_OTHER", "p_QR_RED"]).to_numpy()
    pred = np.argmax(proba, axis=1)
    labels = [0, 1, 2]
    precision = precision_score(y, pred, labels=labels, average=None, zero_division=0)
    recall = recall_score(y, pred, labels=labels, average=None, zero_division=0)
    row = {
        "run_id": run_id,
        "metric_scope": "multiclass",
        "accuracy": accuracy_score(y, pred),
        "balanced_accuracy": balanced_accuracy_score(y, pred),
        "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
    }
    for class_id, class_name in enumerate(CLASS_NAMES):
        row[f"{class_name}_precision"] = precision[class_id]
        row[f"{class_name}_recall"] = recall[class_id]
        row[f"pred_{class_name}_share"] = float(np.mean(pred == class_id))
        row[f"true_{class_name}_share"] = float(np.mean(y == class_id))
    return add_config_fields(row, cfg, metrics_by_scope)


def main() -> None:
    global OUT_DIR
    args = parse_args()
    if args.benchmark_dir is not None:
        OUT_DIR = args.benchmark_dir
    run_ids = collect_run_ids(args)
    rows = []
    for run_id in run_ids:
        cfg = read_config(run_id)
        metrics_by_scope = metric_rows(run_id)
        if args.task in {"binary", "both"}:
            row = binary_summary(run_id, cfg, metrics_by_scope)
            if row is not None:
                rows.append(row)
        if args.task in {"multiclass", "both"}:
            row = multiclass_summary(run_id, cfg, metrics_by_scope)
            if row is not None:
                rows.append(row)
    if not rows:
        raise ValueError(
            "No se encontraron OOF predictions para los run_ids indicados. "
            f"OUT_DIR={OUT_DIR} exists={OUT_DIR.exists()} resolved={OUT_DIR.resolve(strict=False)}"
        )

    df = pl.DataFrame(rows)
    sort_cols = [c for c in ["metric_scope", "undersample_binary_positive_share", "undersample_multiclass_bip_share"] if c in df.columns]
    if sort_cols:
        df = df.sort(sort_cols, nulls_last=True)

    suffix = args.out_name or "hard_label_summary"
    out_path = OUT_DIR / f"hard_label_summary_{suffix}.csv"
    df.write_csv(out_path)
    print(f"OK: {out_path}")
    print(df)


if __name__ == "__main__":
    main()
