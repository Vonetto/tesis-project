"""Tests del sequence_repeat_pack (paso 1: repeticion dia-a-dia de OD+hora).

Correr:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
    lib/test_user_sequence_repeat.py -q
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "audits"))
from build_user_sequence_repeat_features import compute_sequence_repeat  # noqa: E402


def _row(id_tarjeta: str, ts: str, od_time: str | None) -> dict:
    return {
        "id_tarjeta": id_tarjeta,
        "routine_trip_ts": datetime.fromisoformat(ts),
        "routine_od_time": od_time,
    }


def make_base() -> pl.DataFrame:
    rows = []

    # Tarjeta "rigid": dos lunes consecutivos con el MISMO patron exacto.
    # Lunes 2025-04-07 y lunes 2025-04-14 (7 dias de diferencia).
    for d in ["2025-04-07", "2025-04-14"]:
        rows += [
            _row("rigid", f"{d}T08:00:00", "A->B__lab_am_peak"),
            _row("rigid", f"{d}T18:00:00", "B->A__lab_pm_peak"),
        ]

    # Tarjeta "varies": dos lunes consecutivos con patrones DISJUNTOS.
    rows += [
        _row("varies", "2025-04-07T08:00:00", "A->B__lab_am_peak"),
        _row("varies", "2025-04-14T08:00:00", "C->D__lab_am_peak"),
    ]

    # Tarjeta "single": un solo dia activo -> sin pares.
    rows += [
        _row("single", "2025-04-07T08:00:00", "A->B__lab_am_peak"),
    ]

    # Tarjeta "gap_too_far": dos lunes con 21 dias de diferencia (> 14) -> sin pares.
    rows += [
        _row("gap_too_far", "2025-04-07T08:00:00", "A->B__lab_am_peak"),
        _row("gap_too_far", "2025-04-28T08:00:00", "A->B__lab_am_peak"),
    ]

    # Tarjeta "null_pattern": routine_od_time nulo -> se descarta del set del dia.
    rows += [
        _row("null_pattern", "2025-04-07T08:00:00", None),
        _row("null_pattern", "2025-04-14T08:00:00", "A->B__lab_am_peak"),
    ]

    return pl.DataFrame(rows)


@pytest.fixture()
def features() -> pl.DataFrame:
    return compute_sequence_repeat(make_base())


def row(features: pl.DataFrame, card: str) -> dict:
    return features.filter(pl.col("id_tarjeta") == card).to_dicts()[0]


def test_rigid_card_full_repeat(features: pl.DataFrame) -> None:
    r = row(features, "rigid")
    assert r["seq_day_repeat_n_active_days"] == 2
    assert r["seq_day_repeat_n_pairs"] == 1
    assert r["seq_day_repeat_share"] == pytest.approx(1.0)


def test_varies_card_zero_repeat(features: pl.DataFrame) -> None:
    r = row(features, "varies")
    assert r["seq_day_repeat_n_active_days"] == 2
    assert r["seq_day_repeat_n_pairs"] == 1
    assert r["seq_day_repeat_share"] == pytest.approx(0.0)


def test_single_day_no_pairs(features: pl.DataFrame) -> None:
    r = row(features, "single")
    assert r["seq_day_repeat_n_active_days"] == 1
    assert r["seq_day_repeat_n_pairs"] == 0
    assert r["seq_day_repeat_share"] is None


def test_gap_too_far_no_pairs(features: pl.DataFrame) -> None:
    r = row(features, "gap_too_far")
    assert r["seq_day_repeat_n_active_days"] == 2
    assert r["seq_day_repeat_n_pairs"] == 0
    assert r["seq_day_repeat_share"] is None


def test_null_pattern_day_excluded(features: pl.DataFrame) -> None:
    # El dia con routine_od_time nulo no genera un day_pattern_set (vacio),
    # por lo que solo hay 1 dia activo real y no hay pares.
    r = row(features, "null_pattern")
    assert r["seq_day_repeat_n_active_days"] == 1
    assert r["seq_day_repeat_n_pairs"] == 0


def test_output_contract(features: pl.DataFrame) -> None:
    assert features["id_tarjeta"].n_unique() == features.height
    assert set(features.columns) == {
        "id_tarjeta",
        "seq_day_repeat_share",
        "seq_day_repeat_n_pairs",
        "seq_day_repeat_n_active_days",
    }
    for v in features["seq_day_repeat_n_pairs"].to_list():
        assert v >= 0
    for v in features["seq_day_repeat_share"].drop_nulls().to_list():
        assert 0.0 <= v <= 1.0
