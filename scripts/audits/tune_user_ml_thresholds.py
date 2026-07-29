"""Tune decision thresholds on saved OOF predictions.

This script does not train models. It reads OOF predictions produced by
run_user_ml_benchmark.py and evaluates hard-label rules for imbalanced
classification diagnostics.
"""
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
    ap.add_argument("--run-id", required=True, help="run_id generado por run_user_ml_benchmark.py")
    ap.add_argument("--task", choices=["binary", "multiclass"], required=True)
    ap.add_argument(
        "--metric",
        choices=["balanced_accuracy", "macro_f1"],
        default="balanced_accuracy",
        help="Metrica para escoger el mejor umbral.",
    )
    ap.add_argument("--threshold-min", type=float, default=0.01)
    ap.add_argument("--threshold-max", type=float, default=0.50)
    ap.add_argument("--threshold-step", type=float, default=0.01)
    ap.add_argument(
        "--multiclass-rule",
        choices=["red_first", "other_first"],
        default="red_first",
        help="Prioridad cuando QR_RED y QR_OTHER superan sus umbrales.",
    )
    return ap.parse_args()


def threshold_grid(lo: float, hi: float, step: float) -> np.ndarray:
    if step <= 0:
        raise ValueError("--threshold-step debe ser positivo")
    if not 0 <= lo <= hi <= 1:
        raise ValueError("Los thresholds deben cumplir 0 <= min <= max <= 1")
    n = int(np.floor((hi - lo) / step)) + 1
    return np.round(lo + step * np.arange(n), 10)


def binary_rows(y: np.ndarray, score: np.ndarray, thresholds: np.ndarray) -> list[dict]:
    rows: list[dict] = []
    for t in thresholds:
        pred = (score >= t).astype(int)
        rows.append(
            {
                "task": "binary",
                "threshold_qr": float(t),
                "balanced_accuracy": balanced_accuracy_score(y, pred),
                "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
                "accuracy": accuracy_score(y, pred),
                "qr_precision": precision_score(y, pred, zero_division=0),
                "qr_recall": recall_score(y, pred, zero_division=0),
                "pred_qr_share": float(np.mean(pred == 1)),
                "true_qr_share": float(np.mean(y == 1)),
            }
        )
    return rows


def multiclass_predict(
    p_other: np.ndarray,
    p_red: np.ndarray,
    t_other: float,
    t_red: float,
    rule: str,
) -> np.ndarray:
    pred = np.zeros(len(p_other), dtype=np.int64)
    other_hit = p_other >= t_other
    red_hit = p_red >= t_red
    if rule == "red_first":
        pred[other_hit] = 1
        pred[red_hit] = 2
    elif rule == "other_first":
        pred[red_hit] = 2
        pred[other_hit] = 1
    else:
        raise ValueError(f"Regla multiclass no soportada: {rule}")
    return pred


def multiclass_rows(
    y: np.ndarray,
    p_other: np.ndarray,
    p_red: np.ndarray,
    thresholds: np.ndarray,
    rule: str,
) -> list[dict]:
    rows: list[dict] = []
    for t_other in thresholds:
        for t_red in thresholds:
            pred = multiclass_predict(p_other, p_red, t_other, t_red, rule)
            recalls = recall_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
            precisions = precision_score(y, pred, labels=[0, 1, 2], average=None, zero_division=0)
            rows.append(
                {
                    "task": "multiclass",
                    "threshold_qr_other": float(t_other),
                    "threshold_qr_red": float(t_red),
                    "rule": rule,
                    "balanced_accuracy": balanced_accuracy_score(y, pred),
                    "macro_f1": f1_score(y, pred, average="macro", zero_division=0),
                    "accuracy": accuracy_score(y, pred),
                    "BIP_recall": recalls[0],
                    "QR_OTHER_recall": recalls[1],
                    "QR_RED_recall": recalls[2],
                    "BIP_precision": precisions[0],
                    "QR_OTHER_precision": precisions[1],
                    "QR_RED_precision": precisions[2],
                    "pred_BIP_share": float(np.mean(pred == 0)),
                    "pred_QR_OTHER_share": float(np.mean(pred == 1)),
                    "pred_QR_RED_share": float(np.mean(pred == 2)),
                    "true_BIP_share": float(np.mean(y == 0)),
                    "true_QR_OTHER_share": float(np.mean(y == 1)),
                    "true_QR_RED_share": float(np.mean(y == 2)),
                }
            )
    return rows


def best_row(rows: list[dict], metric: str) -> dict:
    if not rows:
        raise ValueError("No hay filas de thresholds para evaluar")
    return max(rows, key=lambda row: row[metric])


def main() -> None:
    args = parse_args()
    thresholds = threshold_grid(args.threshold_min, args.threshold_max, args.threshold_step)
    oof_path = OUT_DIR / f"oof_predictions_{args.run_id}_{args.task}.parquet"
    if not oof_path.exists():
        raise FileNotFoundError(f"No existe OOF: {oof_path}")

    df = pl.read_parquet(oof_path)
    if args.task == "binary":
        rows = binary_rows(
            df["y_qr"].to_numpy(),
            df["p_qr"].to_numpy(),
            thresholds,
        )
    else:
        rows = multiclass_rows(
            df["y_class"].to_numpy(),
            df["p_QR_OTHER"].to_numpy(),
            df["p_QR_RED"].to_numpy(),
            thresholds,
            args.multiclass_rule,
        )

    best = best_row(rows, args.metric)
    out_csv = OUT_DIR / f"threshold_tuning_{args.run_id}_{args.task}.csv"
    out_json = OUT_DIR / f"threshold_tuning_best_{args.run_id}_{args.task}.json"
    pl.DataFrame(rows).write_csv(out_csv)
    out_json.write_text(json.dumps(best, indent=2, ensure_ascii=False))

    print(f"OK: {out_csv}")
    print(f"Best by {args.metric}:")
    print(json.dumps(best, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
