"""Etapa A (sequence_embedding_pack, 2026-06-13): secuencia de tokens de viaje por tarjeta.

Contexto: el "paso 1" (sequence_repeat_pack, seq_day_repeat_share) midio
repeticion dia-a-dia del patron OD+hora y no aporto senal (AUC 0.6846 vs
baseline 0.6842). Antes de descartar la dimension de "secuencia" por completo,
el "paso 2" construye un embedding simple (NMF sobre n-gramas de tokens) que
podria capturar estructura de orden que el resumen de repeticion no ve.

Esta etapa A solo construye las SECUENCIAS (no el embedding). Cada viaje se
reduce a un token discreto:

    token = (macro_origen, macro_destino, banda_horaria, modo_coarse)

  - macro_origen/macro_destino: una de las 7 macrozonas (zona777_macrozone_lookup,
    ver build_zona777_macrozone_lookup.py). Se usan macrozonas en vez de las
    777 zonas para mantener el vocabulario de n-gramas manejable
    (7*7*5*4 = 980 tokens posibles antes de bigramas).
  - banda_horaria: routine_time_band (lab_am_peak, lab_pm_peak, lab_midday,
    lab_other, no_lab) -- igual que routine_pack.
  - modo_coarse: routine_mode_coarse (metro_bus, metro_only, bus_only,
    other_mode) -- igual que routine_pack.

Output: por id_tarjeta, lista de tokens ordenada por routine_trip_ts (un
string por token, separador "|"). La etapa B consume esto para contar
n-gramas.

Caveat: igual que routine_pack/sequence_repeat_pack, opera sobre el panel
clean completo del scope, sin filtros de universo.

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/build_user_sequence_tokens.py --scope interannual_ml --force
"""
from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl

from build_user_routine_features import (
    OUT_DIR,
    SCOPE_WEEKS,
    assert_unique_key,
    collect_streaming,
    trips_lf_for_scope,
    validate_inputs,
)

MACROZONE_LOOKUP_PATH = OUT_DIR / "zona777_macrozone_lookup.parquet"

TOKEN_SEP = "|"
MAX_SEQ_LEN = 500  # tope defensivo; tarjetas con mas viajes se truncan a los ultimos MAX_SEQ_LEN


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_sequence_tokens_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_sequence_tokens_{stem}_{scope}.csv"


def load_macrozone_lookup() -> pl.DataFrame:
    if not MACROZONE_LOOKUP_PATH.exists():
        raise FileNotFoundError(
            f"Falta {MACROZONE_LOOKUP_PATH}. Correr build_zona777_macrozone_lookup.py primero."
        )
    return pl.read_parquet(MACROZONE_LOOKUP_PATH).select(
        pl.col("ZONA777").cast(pl.Int64),
        pl.col("macrozone_model"),
    )


def build_token_base(base: pl.DataFrame, macrozone: pl.DataFrame) -> pl.DataFrame:
    """Agrega macro_origen/macro_destino y construye el token por viaje."""
    origin_lookup = macrozone.rename({"ZONA777": "zona_inicio_viaje", "macrozone_model": "macro_origen"})
    dest_lookup = macrozone.rename({"ZONA777": "zona_fin_viaje", "macrozone_model": "macro_destino"})

    df = (
        base.join(origin_lookup, on="zona_inicio_viaje", how="left")
        .join(dest_lookup, on="zona_fin_viaje", how="left")
        .with_columns(
            pl.when(
                pl.col("macro_origen").is_not_null()
                & pl.col("macro_destino").is_not_null()
                & pl.col("routine_time_band").is_not_null()
                & pl.col("routine_mode_coarse").is_not_null()
            )
            .then(
                pl.concat_str(
                    [
                        pl.col("macro_origen"),
                        pl.col("macro_destino"),
                        pl.col("routine_time_band"),
                        pl.col("routine_mode_coarse"),
                    ],
                    separator="__",
                )
            )
            .otherwise(None)
            .alias("seq_token")
        )
    )
    return df


def build_sequences(token_base: pl.DataFrame) -> pl.DataFrame:
    """Por id_tarjeta: lista de tokens ordenada por routine_trip_ts (sin nulls)."""
    seqs = (
        token_base.lazy()
        .filter(pl.col("seq_token").is_not_null())
        .sort(["id_tarjeta", "routine_trip_ts"])
        .group_by("id_tarjeta", maintain_order=True)
        .agg(
            pl.col("seq_token").alias("seq_tokens"),
            pl.len().alias("seq_n_tokens_total"),
        )
        .with_columns(
            pl.col("seq_tokens").list.tail(MAX_SEQ_LEN),
        )
        .with_columns(
            pl.col("seq_tokens").list.len().alias("seq_n_tokens"),
        )
        .collect()
    )
    return seqs


def build_sequence_tokens(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo sequence_tokens scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    base = collect_streaming(trips_lf)
    macrozone = load_macrozone_lookup()

    token_base = build_token_base(base, macrozone)
    seqs = build_sequences(token_base)

    assert_unique_key(seqs, "id_tarjeta", "sequence_tokens")
    seqs.write_parquet(out_path, compression="zstd")
    write_audits(token_base, seqs, scope)
    print(f"OK: {out_path}")
    print(f"rows={seqs.height:,} cols={len(seqs.columns):,}")
    return out_path


def write_audits(token_base: pl.DataFrame, seqs: pl.DataFrame, scope: str) -> None:
    n_total = token_base.height
    n_missing_token = token_base.select(pl.col("seq_token").is_null().sum()).item()

    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(seqs.height)},
        {"metric": "n_trips_total", "value": str(n_total)},
        {"metric": "n_trips_missing_token", "value": str(n_missing_token)},
        {"metric": "missing_token_rate", "value": f"{n_missing_token / n_total:.6f}"},
        {
            "metric": "n_distinct_tokens",
            "value": str(
                token_base.filter(pl.col("seq_token").is_not_null())
                .select(pl.col("seq_token").n_unique())
                .item()
            ),
        },
        {
            "metric": "mean_seq_n_tokens",
            "value": f"{seqs.select(pl.col('seq_n_tokens').mean()).item():.4f}",
        },
        {
            "metric": "median_seq_n_tokens",
            "value": f"{seqs.select(pl.col('seq_n_tokens').median()).item():.4f}",
        },
        {
            "metric": "max_seq_n_tokens",
            "value": str(seqs.select(pl.col("seq_n_tokens").max()).item()),
        },
        {
            "metric": "n_cards_truncated",
            "value": str(seqs.filter(pl.col("seq_n_tokens_total") > MAX_SEQ_LEN).height),
        },
        {
            "metric": "n_cards_seq_len_1_or_less",
            "value": str(seqs.filter(pl.col("seq_n_tokens") <= 1).height),
        },
    ]
    pl.DataFrame(summary_rows).write_csv(audit_path(scope, "summary"))

    top_tokens = (
        token_base.filter(pl.col("seq_token").is_not_null())
        .group_by("seq_token")
        .len()
        .sort("len", descending=True)
        .head(30)
    )
    top_tokens.write_csv(audit_path(scope, "top_tokens"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sequence_tokens for sequence_embedding_pack.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_sequence_tokens(args.scope, force=args.force)


if __name__ == "__main__":
    main()
