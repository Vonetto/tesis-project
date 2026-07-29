"""Merge de índices de inercia (DSI/TSI/LSI) al sample de NIVEL VIAJE (nb 17).

Análogo a lib/user_level/mnl_prep._merge_inertia, pero para el frente VIAJE,
donde la unidad es el viaje (muchos viajes por tarjeta) y los índices son por
tarjeta. Diferencias clave respecto a nivel tarjeta:

1. UNIDAD: el índice se pega a TODOS los viajes de una tarjeta. El inner join
   subsetea VIAJES (los de tarjetas elegibles). OJO: esto sesga el universo
   hacia usuarios frecuentes (ver measure_inertia_coverage_trips.py: ~18%-41%
   del sample según ventana).

2. ESTANDARIZACIÓN: el z se calcula SOBRE TARJETAS ÚNICAS (no sobre viajes),
   porque estandarizar por viaje sobrepondera a las tarjetas con más viajes y
   sesga media/sd. Se computa media/sd sobre el universo de tarjetas elegibles
   y luego se aplica a cada viaje. Es la sutileza que justifica este módulo.

3. CONJUNTO multi-ventana: igual que a nivel tarjeta, intersección de ventanas
   y columnas con sufijo __inter / __intra2025.

Default de índices: PARSIMONIOSO (sin lsi_origin_zone, r≈0.93 con lsi_origin_stop),
idéntico al frente tarjeta para que las especificaciones sean comparables.
"""
from __future__ import annotations

import polars as pl

from lib.user_level.mnl_prep import (
    INERTIA_DIR,
    INERTIA_INDICES_PARSIMONIOUS,
    INERTIA_WINDOWS,
    _window_tag,
)


def attach_inertia_trips(
    trips: pl.DataFrame,
    windows: str | list[str],
    indices: list[str] | None = None,
    *,
    id_col: str = "id_tarjeta",
) -> tuple[pl.DataFrame, list[str]]:
    """Pega los índices de inercia (en z, estandarizados por TARJETA) al df de
    viajes, vía INNER join por id_tarjeta. Devuelve (df_viajes_filtrado, cols_z).

    windows: str (1 ventana) o list[str] (modelo conjunto = intersección).
    indices: default parsimonioso (DSI, TSI, LSI-paradero).
    """
    if isinstance(windows, str):
        windows = [windows]
    indices = indices or list(INERTIA_INDICES_PARSIMONIOUS)

    trips = trips.with_columns(pl.col(id_col).cast(pl.Utf8))

    # 1) índices por TARJETA: intersección de ventanas + sufijo de etiqueta.
    per_card = None
    raw_cols: list[str] = []
    for w in windows:
        if w not in INERTIA_WINDOWS:
            raise ValueError(f"ventana desconocida: {w!r}. "
                             f"Opciones: {sorted(INERTIA_WINDOWS)}")
        path = INERTIA_DIR / INERTIA_WINDOWS[w]
        if not path.exists():
            raise FileNotFoundError(f"No existe el parquet de inercia: {path}")
        ind = pl.read_parquet(path)
        missing = [c for c in ["id_tarjeta", *indices] if c not in ind.columns]
        if missing:
            raise ValueError(f"Faltan columnas en {path.name}: {missing}")
        tag = _window_tag(w)
        rename = {c: (f"{c}__{tag}" if len(windows) > 1 else c) for c in indices}
        ind = (ind.select(["id_tarjeta", *indices])
                  .with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
                  .rename(rename))
        per_card = ind if per_card is None else per_card.join(
            ind, on="id_tarjeta", how="inner")
        raw_cols.extend(rename.values())

    # 2) z SOBRE TARJETAS ÚNICAS del universo elegible (no sobre viajes).
    #    per_card ya tiene una fila por tarjeta (los parquets de inercia son
    #    1 fila/tarjeta), así que la media/sd aquí es a nivel tarjeta.
    z_exprs = []
    for c in raw_cols:
        mean = per_card[c].mean()
        std = per_card[c].std(ddof=0)
        if std and std > 0:
            z_exprs.append(((pl.col(c) - mean) / std).alias(f"{c}_z"))
        else:
            z_exprs.append(pl.lit(0.0).alias(f"{c}_z"))
    per_card = per_card.with_columns(z_exprs)
    z_cols = [f"{c}_z" for c in raw_cols]
    per_card = per_card.select(["id_tarjeta", *z_cols]).rename(
        {"id_tarjeta": id_col} if id_col != "id_tarjeta" else {})

    # 3) INNER join a los viajes (subsetea viajes de tarjetas elegibles).
    n_trips_before = trips.height
    n_cards_before = trips[id_col].n_unique()
    out = trips.join(per_card, on=id_col, how="inner")
    n_cards_after = out[id_col].n_unique()
    print(f"[inertia_trips] {windows}: {out.height:,} viajes "
          f"({out.height/n_trips_before:.1%} de {n_trips_before:,}) | "
          f"{n_cards_after:,} tarjetas ({n_cards_after/n_cards_before:.1%}).")
    if out.height == 0:
        raise ValueError("El join dejó 0 viajes: ¿ventana/sample incompatibles?")
    return out, z_cols


def inertia_param_tags(z_cols: list[str]) -> dict[str, str]:
    """param_tags (col -> TAG mayúscula) para registrar en el notebook 17,
    igual que PARAM_TAGS. Ej: 'dsi_day_sequence__inter_z' -> 'DSI_DAY_SEQUENCE__INTER_Z'."""
    return {c: c.upper() for c in z_cols}
