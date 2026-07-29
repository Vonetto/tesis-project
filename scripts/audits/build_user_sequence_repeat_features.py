"""sequence_repeat_pack: repeticion dia-a-dia del patron OD+hora por tarjeta.

Motivacion (2026-06-13): las variables routine_* miden concentracion/entropia
de patrones (OD, OD+hora_banda, OD+hora+modo) sobre TODA la ventana, sin
distinguir el ORDEN temporal. Dos tarjetas pueden tener la misma entropia
global pero una repite exactamente el mismo patron semana a semana (rutina
rigida) y la otra varia sus patrones de semana a semana aunque elija siempre
entre el mismo conjunto reducido de combinaciones (entropia baja igual).

Esta es la prueba barata del "paso 1" antes de evaluar embeddings de
secuencias de viajes (paso 2/3): si esta señal de repeticion dia-a-dia no
aporta nada al binario por encima de routine_od_time_entropy_norm y similares,
es evidencia de que un embedding de secuencias tampoco aportaria mucho, porque
la informacion de orden temporal ya estaria bien resumida por los agregados
existentes.

Definicion:
  - Por tarjeta y por dia calendario (fecha de routine_trip_ts), se construye
    el conjunto de valores routine_od_time observados ese dia (drop nulls).
  - Para cada dia activo D con dia-de-semana W, se compara contra el dia
    activo INMEDIATAMENTE ANTERIOR con el mismo dia-de-semana W (dentro de la
    ventana de la tarjeta). No exige que sea exactamente 7 dias antes: es el
    dia comparable mas reciente disponible.
  - Jaccard(set_D, set_prev) = |interseccion| / |union|, solo si ambos sets son
    no vacios.
  - seq_day_repeat_share: promedio de esos Jaccard por tarjeta (0..1, mayor =
    mas repetitivo dia-a-dia).
  - seq_day_repeat_n_pairs: cantidad de pares validos usados en el promedio
    (para detectar baja confiabilidad en tarjetas con pocos dias activos).
  - seq_day_repeat_n_active_days: cantidad de dias activos totales (denominador
    informativo, no usado en el promedio).

Caveat: igual que routine_pack, opera sobre el panel clean completo del scope,
sin filtros de universo (el filtro de universo se aplica al hacer join en
build_user_model_matrix.py).

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/build_user_sequence_repeat_features.py \
    --scope interannual_ml --force
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
    panel_path,
    trips_lf_for_scope,
    validate_inputs,
)

SEQ_REPEAT_FEATURES = [
    "seq_day_repeat_share",
    "seq_day_repeat_n_pairs",
    "seq_day_repeat_n_active_days",
]


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_sequence_repeat_features_{scope}.parquet"


def audit_path(scope: str, stem: str) -> Path:
    return OUT_DIR / f"user_sequence_repeat_features_{stem}_{scope}.csv"


def compute_day_sets(base: pl.DataFrame) -> pl.DataFrame:
    """Por (id_tarjeta, fecha): set de routine_od_time observados ese dia.

    Devuelve una fila por (id_tarjeta, fecha) con:
      - weekday (1..7, lunes=1)
      - day_pattern_set: lista ordenada y deduplicada de routine_od_time (sin nulls)
    """
    return (
        base.lazy()
        .filter(pl.col("routine_od_time").is_not_null())
        .with_columns(pl.col("routine_trip_ts").dt.date().alias("trip_date"))
        .select(["id_tarjeta", "trip_date", "routine_od_time"])
        .unique()
        .group_by(["id_tarjeta", "trip_date"])
        .agg(pl.col("routine_od_time").alias("day_pattern_set"))
        .with_columns(
            pl.col("trip_date").dt.weekday().alias("weekday"),
            pl.col("day_pattern_set").list.len().alias("day_pattern_n"),
        )
        .collect()
    )


def jaccard_expr(set_a: str, set_b: str) -> pl.Expr:
    inter = pl.col(set_a).list.set_intersection(pl.col(set_b)).list.len()
    union = pl.col(set_a).list.set_union(pl.col(set_b)).list.len()
    return pl.when(union > 0).then(inter.cast(pl.Float64) / union.cast(pl.Float64)).otherwise(None)


def compute_sequence_repeat(base: pl.DataFrame) -> pl.DataFrame:
    """Calcula seq_day_repeat_* por id_tarjeta a partir del panel de viajes crudo (base)."""
    day_sets = compute_day_sets(base)

    n_active_days = day_sets.group_by("id_tarjeta").agg(
        pl.len().alias("seq_day_repeat_n_active_days")
    )

    # Por (id_tarjeta, weekday), ordenar por fecha y comparar contra el dia
    # comparable anterior (mismo weekday) via shift.
    paired = (
        day_sets.sort(["id_tarjeta", "weekday", "trip_date"])
        .with_columns(
            pl.col("day_pattern_set").shift(1).over(["id_tarjeta", "weekday"]).alias("prev_pattern_set"),
            pl.col("trip_date").shift(1).over(["id_tarjeta", "weekday"]).alias("prev_trip_date"),
        )
        .filter(pl.col("prev_pattern_set").is_not_null())
        # Acotar a comparaciones "semana siguiente disponible": evita que el
        # shift cruce el salto interanual (2024-W17 -> 2025-W14, ~10 meses).
        .filter((pl.col("trip_date") - pl.col("prev_trip_date")).dt.total_days() <= 14)
        .with_columns(jaccard_expr("day_pattern_set", "prev_pattern_set").alias("jaccard"))
        .filter(pl.col("jaccard").is_not_null())
    )

    repeat_agg = paired.group_by("id_tarjeta").agg(
        pl.col("jaccard").mean().alias("seq_day_repeat_share"),
        pl.len().alias("seq_day_repeat_n_pairs"),
    )

    out = (
        n_active_days.join(repeat_agg, on="id_tarjeta", how="left")
        .with_columns(pl.col("seq_day_repeat_n_pairs").fill_null(0))
        .select(["id_tarjeta", *SEQ_REPEAT_FEATURES])
    )
    return out


def build_sequence_repeat_features(scope: str, *, force: bool) -> Path:
    weeks = SCOPE_WEEKS[scope]
    validate_inputs(scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo sequence_repeat_pack scope={scope}: {weeks}")
    trips_lf = trips_lf_for_scope(weeks)
    base = collect_streaming(trips_lf)

    features = compute_sequence_repeat(base)

    assert_unique_key(features, "id_tarjeta", "sequence_repeat_features")
    features.write_parquet(out_path, compression="zstd")
    write_audits(features, scope)
    print(f"OK: {out_path}")
    print(f"rows={features.height:,} cols={len(features.columns):,}")
    return out_path


def write_audits(features: pl.DataFrame, scope: str) -> None:
    n_rows = features.height
    summary_rows = [
        {"metric": "scope", "value": scope},
        {"metric": "n_cards", "value": str(n_rows)},
        {
            "metric": "n_duplicate_id_tarjeta",
            "value": str(n_rows - features.select(pl.col("id_tarjeta").n_unique()).item()),
        },
        {
            "metric": "share_zero_pairs",
            "value": f"{features.select((pl.col('seq_day_repeat_n_pairs') == 0).mean()).item():.6f}",
        },
        {
            "metric": "mean_seq_day_repeat_share",
            "value": f"{features.select(pl.col('seq_day_repeat_share').mean()).item():.6f}",
        },
        {
            "metric": "mean_seq_day_repeat_n_pairs",
            "value": f"{features.select(pl.col('seq_day_repeat_n_pairs').mean()).item():.6f}",
        },
        {
            "metric": "mean_seq_day_repeat_n_active_days",
            "value": f"{features.select(pl.col('seq_day_repeat_n_active_days').mean()).item():.6f}",
        },
    ]
    pl.DataFrame(summary_rows).write_csv(audit_path(scope, "summary"))

    missing = (
        features.select(
            [pl.col(c).is_null().sum().alias(c) for c in SEQ_REPEAT_FEATURES]
        )
        .transpose(include_header=True, header_name="feature", column_names=["n_missing"])
        .with_columns((pl.col("n_missing") / n_rows).alias("missing_rate"))
        .sort("missing_rate", descending=True)
    )
    missing.write_csv(audit_path(scope, "missing"))

    clean_panel = panel_path(scope, "clean")
    if clean_panel.exists():
        panel = pl.scan_parquet(clean_panel).select(["id_tarjeta", pl.col("n_viajes").alias("panel_n_viajes")])
        consistency = (
            features.lazy()
            .join(panel, on="id_tarjeta", how="left")
            .select(
                [
                    pl.len().alias("n_seq_rows"),
                    pl.col("panel_n_viajes").is_null().sum().alias("n_missing_clean_panel"),
                ]
            )
            .collect()
        )
        consistency.write_csv(audit_path(scope, "consistency_clean_panel"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build sequence_repeat_pack user-level features.")
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_sequence_repeat_features(args.scope, force=args.force)


if __name__ == "__main__":
    main()
