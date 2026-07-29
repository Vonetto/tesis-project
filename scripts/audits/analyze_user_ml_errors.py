"""Analisis de errores del benchmark ML binario (QR vs BIP) sobre predicciones OOF.

Pregunta: ¿que tarjetas QR NO logra rankear el modelo, y en que se diferencian
(o no) de las QR que si captura y del BIP tipico?

Grupos definidos sobre el score OOF `p_qr`:
  - QR_caught:  tarjetas QR con p_qr >= cuantil 75 de los scores QR.
  - QR_missed:  tarjetas QR con p_qr <= cuantil 25 de los scores QR
                (falsos negativos profundos).
  - QR_mid:     resto de las QR.
  - BIP_typical: BIP con p_qr <= mediana de los scores BIP.
  - BIP_fp:      BIP en el 5% superior de scores BIP (falsos positivos).

Salidas (en ml_benchmark/error_analysis/<run_id>/):
  - groups_summary.csv: tamano y composicion (QR_RED/QR_OTHER) por grupo.
  - decile_profile.csv: por decil de p_qr, tasa QR, composicion y medias de
    features clave.
  - diffs_caught_vs_missed.csv: diferencia estandarizada (d) por feature entre
    QR capturadas y QR perdidas. Si hay |d| grandes -> ahi hay senal no usada.
  - diffs_missed_vs_biptypical.csv: idem entre QR perdidas y BIP tipico. Si
    todos los |d| son chicos -> esas QR son indistinguibles con las features
    actuales (evidencia de techo).
  - figures/: histograma de p_qr por clase, top |d| de ambos contrastes.

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/analyze_user_ml_errors.py --run-id <run_id>

  Si no se pasa --run-id, usa el oof_predictions_*_binary.parquet mas reciente.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_user_ml_benchmark as bench  # noqa: E402

# Features de lectura rapida para el perfil por decil (si existen en la matriz).
DECILE_PROFILE_FEATURES = [
    "n_viajes",
    "share_trips_2025",
    "hora_mean",
    "hora_std",
    "share_no_lab",
    "share_trips_with_transfer",
    "share_trips_solo_metro",
    "res_share_cine18_universitaria_o_mas_micro_z",
    "res_eod2012_share_hogares_de_income_proxy_z",
    "home_macro_oriente",
    "rhythm_active_day_density_span",
    "routine_lab_peak_share",
]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def find_latest_binary_oof(out_dir: Path) -> Path:
    candidates = sorted(
        out_dir.glob("oof_predictions_*_binary.parquet"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise SystemExit(f"No hay oof_predictions_*_binary.parquet en {out_dir}")
    return candidates[-1]


def run_id_from_oof_path(path: Path) -> str:
    name = path.name
    return name.removeprefix("oof_predictions_").removesuffix("_binary.parquet")


def load_run_features(out_dir: Path, run_id: str) -> list[str] | None:
    cfg = out_dir / f"config_{run_id}.json"
    if not cfg.exists():
        return None
    payload = json.loads(cfg.read_text())
    return payload.get("features")


def standardized_diffs(
    df: pl.DataFrame,
    mask_a: np.ndarray,
    mask_b: np.ndarray,
    features: list[str],
    label_a: str,
    label_b: str,
) -> pl.DataFrame:
    """d = (mean_a - mean_b) / sd_pooled, ignorando NaN. Positivo = mayor en A."""
    rows = []
    for feat in features:
        x = df[feat].to_numpy().astype(np.float64)
        xa, xb = x[mask_a], x[mask_b]
        ma, mb = np.nanmean(xa), np.nanmean(xb)
        sa, sb = np.nanstd(xa), np.nanstd(xb)
        pooled = np.sqrt((sa**2 + sb**2) / 2)
        d = (ma - mb) / pooled if pooled > 0 else 0.0
        rows.append(
            {
                "feature": feat,
                "family": bench.classify_family(feat),
                f"mean_{label_a}": float(ma),
                f"mean_{label_b}": float(mb),
                "d": float(d),
                "abs_d": float(abs(d)),
            }
        )
    return pl.DataFrame(rows).sort("abs_d", descending=True)


def plot_score_hist(df: pl.DataFrame, out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = {"BIP": "#4C72B0", "QR_OTHER": "#DD8452", "QR_RED": "#C44E52"}
    bins = np.linspace(0, float(df["p_qr"].max()), 60)
    for tipo, color in colors.items():
        vals = df.filter(pl.col("tipo_tarjeta") == tipo)["p_qr"].to_numpy()
        if len(vals):
            ax.hist(vals, bins=bins, density=True, histtype="step",
                    linewidth=2, label=f"{tipo} (n={len(vals):,})", color=color)
    ax.set_xlabel("score OOF p_qr")
    ax.set_ylabel("densidad")
    ax.set_title("Distribución del score binario por tipo de tarjeta")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    log(f"  figura: {out_path}")


def plot_top_diffs(diffs: pl.DataFrame, title: str, out_path: Path, top_n: int = 20) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = diffs.head(top_n).reverse()
    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * top_n)))
    colors = ["#C44E52" if v > 0 else "#4C72B0" for v in top["d"].to_list()]
    ax.barh(top["feature"].to_list(), top["d"].to_list(), color=colors)
    ax.axvline(0, color="#646E7B", linewidth=0.8)
    ax.set_xlabel("diferencia estandarizada d")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)
    log(f"  figura: {out_path}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="", help="run_id del benchmark; default: OOF binario mas reciente.")
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--home-filter", default="alta")
    ap.add_argument("--min-trips", type=int, default=3)
    ap.add_argument("--min-home-trips", type=int, default=0)
    ap.add_argument("--missed-quantile", type=float, default=0.25)
    ap.add_argument("--caught-quantile", type=float, default=0.75)
    ap.add_argument("--out-dir", default="", help="Override del directorio de salida.")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    if not 0.0 < args.missed_quantile < args.caught_quantile < 1.0:
        raise ValueError("Se requiere 0 < missed_quantile < caught_quantile < 1")

    bench_dir = bench.OUT_DIR
    if args.run_id:
        oof_path = bench_dir / f"oof_predictions_{args.run_id}_binary.parquet"
        if not oof_path.exists():
            raise SystemExit(f"No existe {oof_path}")
        run_id = args.run_id
    else:
        oof_path = find_latest_binary_oof(bench_dir)
        run_id = run_id_from_oof_path(oof_path)
    log(f"OOF: {oof_path}")

    out_dir = Path(args.out_dir) if args.out_dir else bench_dir / "error_analysis" / run_id
    fig_dir = out_dir / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    oof = pl.read_parquet(oof_path).with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
    log(f"OOF filas: {oof.height:,}")

    matrix = pl.read_parquet(
        bench.matrix_path(args.scope, args.variant, args.home_filter, args.min_trips, args.min_home_trips)
    ).with_columns(pl.col("id_tarjeta").cast(pl.Utf8))

    features = load_run_features(bench_dir, run_id)
    if features is None:
        log("⚠️ Sin config del run; uso todas las columnas numericas de la matriz como features.")
        features = [
            c for c in matrix.columns
            if c != "id_tarjeta" and matrix[c].dtype.is_numeric()
        ]
    features = [f for f in features if f in matrix.columns]
    log(f"Features para contrastes: {len(features)}")

    keep_cols = ["id_tarjeta"] + [
        c for c in dict.fromkeys(features + DECILE_PROFILE_FEATURES) if c in matrix.columns
    ]
    df = oof.join(matrix.select(keep_cols), on="id_tarjeta", how="inner")
    if df.height < oof.height:
        log(f"⚠️ Join perdio filas: {oof.height - df.height:,} (¿matriz regenerada despues del run?)")
    log(f"Dataset analisis: {df.height:,} filas")

    p = df["p_qr"].to_numpy()
    is_qr = (df["tipo_tarjeta"] != "BIP").to_numpy()
    tipo = df["tipo_tarjeta"].to_numpy()

    q_missed = float(np.quantile(p[is_qr], args.missed_quantile))
    q_caught = float(np.quantile(p[is_qr], args.caught_quantile))
    bip_median = float(np.median(p[~is_qr]))
    bip_p95 = float(np.quantile(p[~is_qr], 0.95))

    mask_missed = is_qr & (p <= q_missed)
    mask_caught = is_qr & (p >= q_caught)
    mask_mid = is_qr & ~mask_missed & ~mask_caught
    mask_bip_typ = (~is_qr) & (p <= bip_median)
    mask_bip_fp = (~is_qr) & (p >= bip_p95)

    log(
        f"Umbrales: missed p<={q_missed:.4f} | caught p>={q_caught:.4f} | "
        f"mediana BIP {bip_median:.4f} | p95 BIP {bip_p95:.4f}"
    )

    # --- resumen de grupos
    group_rows = []
    for name, mask in [
        ("QR_missed", mask_missed),
        ("QR_mid", mask_mid),
        ("QR_caught", mask_caught),
        ("BIP_typical", mask_bip_typ),
        ("BIP_fp", mask_bip_fp),
    ]:
        n = int(mask.sum())
        group_rows.append(
            {
                "group": name,
                "n": n,
                "share_qr_red": float(np.mean(tipo[mask] == "QR_RED")) if n else 0.0,
                "share_qr_other": float(np.mean(tipo[mask] == "QR_OTHER")) if n else 0.0,
                "p_qr_mean": float(np.mean(p[mask])) if n else 0.0,
                "p_qr_median": float(np.median(p[mask])) if n else 0.0,
            }
        )
    # ¿Cuan profundo es el miss? QR bajo la mediana del BIP.
    deep = is_qr & (p <= bip_median)
    group_rows.append(
        {
            "group": "QR_below_bip_median",
            "n": int(deep.sum()),
            "share_qr_red": float(np.mean(tipo[deep] == "QR_RED")) if deep.any() else 0.0,
            "share_qr_other": float(np.mean(tipo[deep] == "QR_OTHER")) if deep.any() else 0.0,
            "p_qr_mean": float(np.mean(p[deep])) if deep.any() else 0.0,
            "p_qr_median": float(np.median(p[deep])) if deep.any() else 0.0,
        }
    )
    groups = pl.DataFrame(group_rows)
    groups.write_csv(out_dir / "groups_summary.csv")
    log(f"  tabla: {out_dir / 'groups_summary.csv'}")
    print(groups)

    # --- perfil por decil de score
    decile_feats = [f for f in DECILE_PROFILE_FEATURES if f in df.columns]
    df_dec = df.with_columns(
        ((pl.col("p_qr").rank("ordinal") - 1) * 10 // pl.len()).cast(pl.Int8).alias("decile")
    )
    decile_profile = df_dec.group_by("decile").agg(
        [
            pl.len().alias("n"),
            (pl.col("tipo_tarjeta") != "BIP").mean().alias("qr_rate"),
            (pl.col("tipo_tarjeta") == "QR_RED").mean().alias("qr_red_rate"),
            (pl.col("tipo_tarjeta") == "QR_OTHER").mean().alias("qr_other_rate"),
            pl.col("p_qr").mean().alias("p_qr_mean"),
        ]
        + [pl.col(f).mean().alias(f"mean_{f}") for f in decile_feats]
    ).sort("decile")
    decile_profile.write_csv(out_dir / "decile_profile.csv")
    log(f"  tabla: {out_dir / 'decile_profile.csv'}")

    # --- contrastes estandarizados
    diffs_cm = standardized_diffs(df, mask_caught, mask_missed, features, "caught", "missed")
    diffs_cm.write_csv(out_dir / "diffs_caught_vs_missed.csv")
    log(f"  tabla: {out_dir / 'diffs_caught_vs_missed.csv'}")

    diffs_mb = standardized_diffs(df, mask_missed, mask_bip_typ, features, "missed", "bip_typical")
    diffs_mb.write_csv(out_dir / "diffs_missed_vs_biptypical.csv")
    log(f"  tabla: {out_dir / 'diffs_missed_vs_biptypical.csv'}")

    # --- figuras
    plot_score_hist(df, fig_dir / "score_hist_by_class.png")
    plot_top_diffs(
        diffs_cm,
        "QR capturadas vs QR perdidas: top diferencias (d>0 = mayor en capturadas)",
        fig_dir / "top_diffs_caught_vs_missed.png",
    )
    plot_top_diffs(
        diffs_mb,
        "QR perdidas vs BIP típico: top diferencias (d>0 = mayor en QR perdidas)",
        fig_dir / "top_diffs_missed_vs_biptypical.png",
    )

    # --- resumen ejecutivo en JSON
    summary = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "rows": int(df.height),
        "thresholds": {
            "q_missed": q_missed,
            "q_caught": q_caught,
            "bip_median": bip_median,
            "bip_p95": bip_p95,
        },
        "n_qr_missed": int(mask_missed.sum()),
        "n_qr_below_bip_median": int(deep.sum()),
        "max_abs_d_caught_vs_missed": float(diffs_cm["abs_d"][0]),
        "max_abs_d_missed_vs_biptypical": float(diffs_mb["abs_d"][0]),
        "top10_caught_vs_missed": diffs_cm.head(10)["feature"].to_list(),
        "top10_missed_vs_biptypical": diffs_mb.head(10)["feature"].to_list(),
    }
    (out_dir / "error_analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )
    log(f"Resumen: {out_dir / 'error_analysis_summary.json'}")
    log("Listo.")


if __name__ == "__main__":
    main()
