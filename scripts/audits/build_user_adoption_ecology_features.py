"""adoption_ecology_pack v2: penetracion QR territorial (agregado de zona) por tarjeta.

Hipotesis (del analisis de errores OOF 2026-06-12): las tarjetas QR que el
modelo binario pierde son conductualmente indistinguibles de BIP (max |d|=0,19
sobre 141 features). Lo que puede distinguir a dos usuarios conductualmente
identicos es su ENTORNO de adopcion: cuanta QR se usa alrededor (visibilidad/
contagio local + habilitacion territorial).

POSTMORTEM v1 (2026-06-12, run 7770b888 INVALIDO): la v1 usaba leave-one-out
(excluir la propia tarjeta del share de zona). Eso introduce LEAKAGE directo:
dentro de una misma zona, el valor difiere segun el target propio
(n_qr-1 vs n_qr en el numerador), y XGBoost identifica la zona con las
features zona-constantes (res_*, bip_load_*, censo) y luego lee el target en
la variacion intra-zona del eco_* (AUC OOF 0,98, artefactual). Regla: si el
valor de una feature cambia al voltear la etiqueta de la propia fila, hay
leakage.

v2: agregado SIMPLE de zona (la propia tarjeta incluida). El valor es
constante para todas las tarjetas de la zona -> cero variacion intra-zona ->
no puede codificar el target individual. La contribucion propia al promedio
es ~1/n_zona (miles de tarjetas por zona777): sesgo transductivo residual
despreciable, documentado.

Variables (por tarjeta, desde el panel clean completo, sin filtros de universo):
  - eco_qr_share_home_zone_smooth:      share de tarjetas QR en la zona_hogar.
  - eco_qr_red_share_home_zone_smooth:  idem solo QR_RED.
  - eco_home_zone_n_cards_log:          soporte log1p(n) de la zona.
  - eco_*_origin_top1_*:                las mismas para origin_zone_top1.

Suavizamiento m-estimate hacia la tasa global del panel:
  smooth = (n_qr + m * p_global) / (n + m),  m = --smoothing-m (100).
Tambien se guarda la version raw (sin suavizar) como columna de auditoria.

CAVEAT METODOLOGICO (mismo contrato exploratorio que context_residual_pack):
  los shares de zona usan los targets del universo completo (incluido el de
  cada tarjeta, diluido 1/n) -> formalmente transductivo, no fold-safe. Para
  reporte final, recalcular los shares dentro de cada train fold.

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/build_user_adoption_ecology_features.py \
    --scope interannual_ml --variant clean --force
"""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

ECOLOGY_COLUMNS = [
    "eco_home_zone_n_cards_log",
    "eco_qr_share_home_zone",
    "eco_qr_share_home_zone_smooth",
    "eco_qr_red_share_home_zone_smooth",
    "eco_origin_top1_n_cards_log",
    "eco_qr_share_origin_top1",
    "eco_qr_share_origin_top1_smooth",
    "eco_qr_red_share_origin_top1_smooth",
]


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def panel_path(scope: str, variant: str) -> Path:
    return USER_DIR / f"user_level_payment_panel_{scope}_{variant}.parquet"


def output_path(scope: str) -> Path:
    return USER_DIR / f"user_adoption_ecology_features_{scope}.parquet"


def _zone_aggregate_features(
    df: pl.DataFrame,
    zone_col: str,
    suffix: str,
    p_global_qr: float,
    p_global_red: float,
    m: float,
) -> pl.DataFrame:
    """Share QR/QR_RED por zona como agregado simple (zona-constante).

    Sin leave-one-out: el valor es identico para todas las tarjetas de la zona,
    independiente de su propio target (ver POSTMORTEM v1 en el docstring).
    """
    stats = (
        df.filter(pl.col(zone_col).is_not_null())
        .group_by(zone_col)
        .agg(
            pl.len().alias("_n_zone"),
            pl.col("_is_qr").sum().alias("_n_qr_zone"),
            pl.col("_is_red").sum().alias("_n_red_zone"),
        )
    )
    out = df.join(stats, on=zone_col, how="left")
    valid = pl.col(zone_col).is_not_null() & pl.col("_n_zone").is_not_null()
    out = out.with_columns(
        pl.when(valid)
        .then((pl.col("_n_zone").cast(pl.Float64) + 1.0).log())
        .otherwise(None)
        .alias(f"eco_{suffix}_n_cards_log"),
        pl.when(valid)
        .then(pl.col("_n_qr_zone").cast(pl.Float64) / pl.col("_n_zone").cast(pl.Float64))
        .otherwise(None)
        .alias(f"eco_qr_share_{suffix}"),
        pl.when(valid)
        .then(
            (pl.col("_n_qr_zone").cast(pl.Float64) + m * p_global_qr)
            / (pl.col("_n_zone").cast(pl.Float64) + m)
        )
        .otherwise(None)
        .alias(f"eco_qr_share_{suffix}_smooth"),
        pl.when(valid)
        .then(
            (pl.col("_n_red_zone").cast(pl.Float64) + m * p_global_red)
            / (pl.col("_n_zone").cast(pl.Float64) + m)
        )
        .otherwise(None)
        .alias(f"eco_qr_red_share_{suffix}_smooth"),
    )
    return out.drop(["_n_zone", "_n_qr_zone", "_n_red_zone"])


def compute_ecology(panel: pl.DataFrame, m: float) -> pl.DataFrame:
    """Calcula las features de ecologia de adopcion para todo el panel.

    `panel` requiere: id_tarjeta, tipo_tarjeta, zona_hogar, origin_zone_top1.
    """
    df = panel.select(["id_tarjeta", "tipo_tarjeta", "zona_hogar", "origin_zone_top1"]).with_columns(
        (pl.col("tipo_tarjeta") != "BIP").cast(pl.Int64).alias("_is_qr"),
        (pl.col("tipo_tarjeta") == "QR_RED").cast(pl.Int64).alias("_is_red"),
    )
    p_global_qr = float(df["_is_qr"].mean())
    p_global_red = float(df["_is_red"].mean())
    log(f"Tasas globales panel: QR={p_global_qr:.5f} | QR_RED={p_global_red:.5f}")

    df = _zone_aggregate_features(df, "zona_hogar", "home_zone", p_global_qr, p_global_red, m)
    df = _zone_aggregate_features(df, "origin_zone_top1", "origin_top1", p_global_qr, p_global_red, m)
    return df.select(["id_tarjeta"] + ECOLOGY_COLUMNS)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    ap.add_argument("--variant", default="clean")
    ap.add_argument("--smoothing-m", type=float, default=100.0)
    ap.add_argument("--force", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    out = output_path(args.scope)
    if out.exists() and not args.force:
        raise SystemExit(f"Ya existe {out}; usar --force para regenerar.")

    src = panel_path(args.scope, args.variant)
    if not src.exists():
        raise SystemExit(f"No existe panel: {src}")
    log(f"Panel: {src}")
    panel = pl.read_parquet(src, columns=["id_tarjeta", "tipo_tarjeta", "zona_hogar", "origin_zone_top1"])
    log(f"Tarjetas panel: {panel.height:,}")
    if panel["id_tarjeta"].n_unique() != panel.height:
        raise ValueError("id_tarjeta no es unico en el panel")

    eco = compute_ecology(panel, m=args.smoothing_m)

    # Auditoria minima
    nulls = eco.null_count()
    log(f"Nulos por columna:\n{nulls}")
    desc = eco.select(
        pl.col("eco_qr_share_home_zone_smooth").mean().alias("mean_home_smooth"),
        pl.col("eco_qr_share_home_zone_smooth").std().alias("std_home_smooth"),
        pl.col("eco_qr_share_origin_top1_smooth").mean().alias("mean_origin_smooth"),
    )
    log(f"Descriptivos: {desc.to_dicts()[0]}")
    for col in ["eco_qr_share_home_zone_smooth", "eco_qr_share_origin_top1_smooth"]:
        mn, mx = float(eco[col].min()), float(eco[col].max())
        if not (0.0 <= mn and mx <= 1.0):
            raise ValueError(f"{col} fuera de [0,1]: min={mn}, max={mx}")

    # Verificacion anti-leakage: el share de zona debe ser identico para
    # tarjetas QR y BIP de la misma zona (cero variacion intra-zona).
    check = (
        eco.join(panel.select(["id_tarjeta", "tipo_tarjeta", "zona_hogar"]), on="id_tarjeta")
        .filter(pl.col("zona_hogar").is_not_null())
        .group_by("zona_hogar")
        .agg(pl.col("eco_qr_share_home_zone_smooth").n_unique().alias("n_vals"))
    )
    max_vals = int(check["n_vals"].max())
    if max_vals != 1:
        raise ValueError(
            f"Leakage check FALLO: hay zonas con {max_vals} valores distintos de "
            "eco_qr_share_home_zone_smooth (debe ser 1 por zona)."
        )
    log("Leakage check OK: share constante dentro de cada zona.")

    eco.write_parquet(out)
    log(f"Output: {out} ({eco.height:,} filas, {len(eco.columns)} cols)")
    log("Listo. Caveat: transductivo (no fold-safe); ver docstring.")


if __name__ == "__main__":
    main()
