"""Tests del sequence_embedding_pack - Etapa A (tokens y secuencias por tarjeta).

Correr:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
    lib/test_user_sequence_tokens.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "audits"))
from build_user_sequence_tokens import (  # noqa: E402
    MAX_SEQ_LEN,
    build_sequences,
    build_token_base,
)


def make_macrozone() -> pl.DataFrame:
    # Zona 1 -> NORTE, Zona 2 -> SUR, Zona 3 -> sin macrozona (no aparece en lookup).
    return pl.DataFrame(
        {
            "ZONA777": [1, 2],
            "macrozone_model": ["NORTE", "SUR"],
        }
    ).with_columns(pl.col("ZONA777").cast(pl.Int64))


def _row(
    id_tarjeta: str,
    ts: str,
    zona_inicio: int | None,
    zona_fin: int | None,
    time_band: str | None,
    mode_coarse: str | None,
) -> dict:
    return {
        "id_tarjeta": id_tarjeta,
        "routine_trip_ts": datetime.fromisoformat(ts),
        "zona_inicio_viaje": zona_inicio,
        "zona_fin_viaje": zona_fin,
        "routine_time_band": time_band,
        "routine_mode_coarse": mode_coarse,
    }


def make_base() -> pl.DataFrame:
    rows = [
        # Tarjeta "two_trips": 2 viajes validos, orden cronologico claro.
        _row("two_trips", "2025-04-07T08:00:00", 1, 2, "lab_am_peak", "metro_only"),
        _row("two_trips", "2025-04-07T18:00:00", 2, 1, "lab_pm_peak", "bus_only"),
        # Tarjeta "with_missing": 1 viaje valido + 1 con zona sin macrozona (token nulo).
        _row("with_missing", "2025-04-07T08:00:00", 1, 2, "lab_am_peak", "metro_only"),
        _row("with_missing", "2025-04-07T09:00:00", 3, 2, "lab_midday", "bus_only"),
        # Tarjeta "out_of_order": filas insertadas fuera de orden cronologico.
        _row("out_of_order", "2025-04-07T18:00:00", 2, 1, "lab_pm_peak", "bus_only"),
        _row("out_of_order", "2025-04-07T08:00:00", 1, 2, "lab_am_peak", "metro_only"),
    ]
    return pl.DataFrame(rows)


@pytest.fixture()
def token_base() -> pl.DataFrame:
    return build_token_base(make_base(), make_macrozone())


@pytest.fixture()
def seqs(token_base: pl.DataFrame) -> pl.DataFrame:
    return build_sequences(token_base)


def row(seqs: pl.DataFrame, card: str) -> dict:
    return seqs.filter(pl.col("id_tarjeta") == card).to_dicts()[0]


def test_token_format(token_base: pl.DataFrame) -> None:
    first = token_base.filter(
        (pl.col("id_tarjeta") == "two_trips") & (pl.col("routine_trip_ts").dt.hour() == 8)
    ).to_dicts()[0]
    assert first["seq_token"] == "NORTE__SUR__lab_am_peak__metro_only"


def test_two_trips_sequence_order(seqs: pl.DataFrame) -> None:
    r = row(seqs, "two_trips")
    assert r["seq_tokens"] == [
        "NORTE__SUR__lab_am_peak__metro_only",
        "SUR__NORTE__lab_pm_peak__bus_only",
    ]
    assert r["seq_n_tokens"] == 2
    assert r["seq_n_tokens_total"] == 2


def test_missing_macrozone_excluded(seqs: pl.DataFrame) -> None:
    r = row(seqs, "with_missing")
    # El segundo viaje (zona 3 -> sin macrozona) debe quedar fuera de la secuencia.
    assert r["seq_tokens"] == ["NORTE__SUR__lab_am_peak__metro_only"]
    assert r["seq_n_tokens"] == 1


def test_out_of_order_input_gets_sorted(seqs: pl.DataFrame) -> None:
    r = row(seqs, "out_of_order")
    assert r["seq_tokens"] == [
        "NORTE__SUR__lab_am_peak__metro_only",
        "SUR__NORTE__lab_pm_peak__bus_only",
    ]


def test_truncation_keeps_seq_n_tokens_consistent() -> None:
    """seq_n_tokens debe ser el largo de seq_tokens DESPUES de truncar a
    MAX_SEQ_LEN, no el largo original (bug detectado 2026-06-13: una
    tarjeta con 544 tokens quedo con seq_tokens truncado a 500 pero
    seq_n_tokens=544, lo que rompia explode en la etapa de bigramas)."""
    macrozone = make_macrozone()
    rows = [
        _row("many_trips", f"2025-04-07T{(i % 23):02d}:00:00", 1, 2, "lab_am_peak", "metro_only")
        for i in range(MAX_SEQ_LEN + 44)
    ]
    base = pl.DataFrame(rows)
    token_base = build_token_base(base, macrozone)
    seqs = build_sequences(token_base)

    r = row(seqs, "many_trips")
    assert r["seq_n_tokens_total"] == MAX_SEQ_LEN + 44
    assert r["seq_n_tokens"] == MAX_SEQ_LEN
    assert len(r["seq_tokens"]) == MAX_SEQ_LEN
    assert r["seq_n_tokens"] == len(r["seq_tokens"])


def test_output_contract(seqs: pl.DataFrame) -> None:
    assert seqs["id_tarjeta"].n_unique() == seqs.height
    assert set(seqs.columns) == {
        "id_tarjeta",
        "seq_tokens",
        "seq_n_tokens_total",
        "seq_n_tokens",
    }
    for v in seqs["seq_n_tokens"].to_list():
        assert v <= MAX_SEQ_LEN
        assert v >= 0
