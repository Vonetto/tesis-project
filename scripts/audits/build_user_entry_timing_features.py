"""Feature pack mínimo: TIMING DE ENTRADA al sistema (vía A).

Construye la "semana exacta de primera aparición" de cada id_tarjeta dentro de
los bloques de abril, como señal temporal MÁS FINA que el dummy `solo_2025` /
`share_trips_2025` que el ML ya usa.

MOTIVACIÓN (notes user-level-redesign): el techo predictivo QR-vs-BIP es ~0,68
y robusto a 4 algoritmos y 5 familias de features. `share_trips_2025` es de las
POCAS señales reales (lift 1,55) y es dimensión TEMPORAL pura (no correla con
intensidad). Pero hoy se usa de forma burda (un escalar / dummies). Esta feature
refina la dimensión donde sí hay señal: la SEMANA exacta de aparición dentro del
bloque 2025 (W14-W17), distinguiendo recién-llegados de la cohorte 2025.

ANTI-LEAKAGE: NO usa `tipo_pago` / `is_qr` / target en ningún punto. Mide solo
CUÁNDO aparece la tarjeta, no QUÉ medio de pago usa. El medio de pago es fijo por
tarjeta (una tarjeta = un tipo_pago, ver build_user_level_payment_panel.py), así
que la trayectoria del medio sería leakage; el timing de ENTRADA no lo es.

LIMITACIÓN (documentada): el scope interannual_ml tiene solo 8 semanas en 2
bloques (abril-2024 W14-17, abril-2025 W14-17), con un hueco de ~11 meses. Por
eso la resolución de "entrada" es semanal DENTRO de abril, no fecha real de alta.
Esperar mejora pequeña (centésimas), es refinamiento de una señal existente.

Features (todas SIN target):
- entry_first_iso_week_2025: primera iso_week (14-17) con viaje en 2025;
  null -> se codifica como sentinela.
- entry_recency_2025: (iso_week_first - 14) en [0,3]; MÁS ALTO = aparece MÁS
  TARDE en el bloque = más "nueva". Sentinela -1 si no aparece en 2025.
- entry_appears_2025 / entry_appears_2024: flags 0/1.
- entry_first_iso_week_2024: análogo en 2024 (simetría).
- entry_only_2025 / entry_only_2024 / entry_both_blocks: partición de cohorte
  (derivada de aparición, NO de share de viajes; complementa share_trips_2025).

Uso (Mac, larch-env):
  python scripts/audits/build_user_entry_timing_features.py --scope interannual_ml

Output: tmp/audits/user_level_redesign/user_entry_timing_features_<scope>.parquet
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Reutiliza la carga de viajes del panel (misma fuente, mismo contrato).
from scripts.audits.build_user_level_payment_panel import (  # noqa: E402
    SCOPE_WEEKS,
    trips_lf_for_scope,
)

OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"


def build_entry_timing(scope: str) -> pl.DataFrame:
    weeks = SCOPE_WEEKS[scope]
    lf = trips_lf_for_scope(weeks).select(
        ["id_tarjeta", "trip_year", "iso_week"]
    )

    # primera iso_week por bloque (año), solo viajes de ese año.
    fw_2025 = (
        lf.filter(pl.col("trip_year") == 2025)
        .group_by("id_tarjeta")
        .agg(pl.col("iso_week").min().alias("entry_first_iso_week_2025"))
    )
    fw_2024 = (
        lf.filter(pl.col("trip_year") == 2024)
        .group_by("id_tarjeta")
        .agg(pl.col("iso_week").min().alias("entry_first_iso_week_2024"))
    )
    ids = lf.select("id_tarjeta").unique()

    out = (
        ids.join(fw_2025, on="id_tarjeta", how="left")
        .join(fw_2024, on="id_tarjeta", how="left")
        .collect()
    )

    # flags y recencia. Sentinela -1 para "no aparece en ese bloque".
    block_start = 14  # iso_week de inicio del bloque de abril
    out = out.with_columns(
        [
            pl.col("entry_first_iso_week_2025").is_not_null().cast(pl.Int8)
            .alias("entry_appears_2025"),
            pl.col("entry_first_iso_week_2024").is_not_null().cast(pl.Int8)
            .alias("entry_appears_2024"),
        ]
    ).with_columns(
        [
            # recencia dentro del bloque 2025: 0=W14 (temprano) ... 3=W17 (tarde/nueva)
            pl.when(pl.col("entry_appears_2025") == 1)
            .then(pl.col("entry_first_iso_week_2025") - block_start)
            .otherwise(pl.lit(-1))
            .cast(pl.Int8)
            .alias("entry_recency_2025"),
            # sentinela en las iso_week crudas para que el ML no vea null
            pl.col("entry_first_iso_week_2025").fill_null(-1).cast(pl.Int8),
            pl.col("entry_first_iso_week_2024").fill_null(-1).cast(pl.Int8),
        ]
    ).with_columns(
        [
            ((pl.col("entry_appears_2025") == 1) & (pl.col("entry_appears_2024") == 0))
            .cast(pl.Int8).alias("entry_only_2025"),
            ((pl.col("entry_appears_2024") == 1) & (pl.col("entry_appears_2025") == 0))
            .cast(pl.Int8).alias("entry_only_2024"),
            ((pl.col("entry_appears_2024") == 1) & (pl.col("entry_appears_2025") == 1))
            .cast(pl.Int8).alias("entry_both_blocks"),
        ]
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", default="interannual_ml")
    args = ap.parse_args()

    if args.scope not in SCOPE_WEEKS:
        raise SystemExit(f"scope desconocido: {args.scope}. Opciones: {list(SCOPE_WEEKS)}")

    print(f"Construyendo entry timing para scope={args.scope} "
          f"(semanas: {SCOPE_WEEKS[args.scope]})")
    df = build_entry_timing(args.scope)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"user_entry_timing_features_{args.scope}.parquet"
    df.write_parquet(out_path, compression="zstd")

    # resumen rápido (sin target)
    print(f"\n✅ {df.height:,} tarjetas -> {out_path}")
    print("\nDistribución entry_recency_2025 (0=W14 ... 3=W17, -1=no aparece 2025):")
    print(df["entry_recency_2025"].value_counts().sort("entry_recency_2025"))
    print("\nCohorte por aparición:")
    for c in ["entry_only_2025", "entry_only_2024", "entry_both_blocks"]:
        print(f"  {c}: {df[c].sum():,} ({df[c].mean():.1%})")


if __name__ == "__main__":
    main()
