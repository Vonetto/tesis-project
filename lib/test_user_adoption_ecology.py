"""Tests del adoption_ecology_pack v2 (agregado de zona, sin LOO).

El test critico es test_no_within_zone_variation: el share de zona debe ser
IDENTICO para tarjetas QR y BIP de la misma zona. La v1 (leave-one-out)
fallaba esto y filtraba el target (ver POSTMORTEM en el builder).

Correr:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
    lib/test_user_adoption_ecology.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "audits"))
from build_user_adoption_ecology_features import ECOLOGY_COLUMNS, compute_ecology  # noqa: E402


def make_panel() -> pl.DataFrame:
    # Zona A: 3 tarjetas (a=QR_RED, b=QR_OTHER, c=BIP) -> share QR = 2/3.
    # Zona B: 1 tarjeta QR (d) -> smooth muy tirado hacia p_global.
    # Tarjeta e: zona_hogar null -> bloque home null; origin A.
    return pl.DataFrame(
        {
            "id_tarjeta": ["a", "b", "c", "d", "e"],
            "tipo_tarjeta": ["QR_RED", "QR_OTHER", "BIP", "QR_OTHER", "BIP"],
            "zona_hogar": ["A", "A", "A", "B", None],
            "origin_zone_top1": ["A", "A", "A", "B", "A"],
        }
    )


@pytest.fixture()
def eco() -> pl.DataFrame:
    return compute_ecology(make_panel(), m=2.0)


def row(eco: pl.DataFrame, card: str) -> dict:
    return eco.filter(pl.col("id_tarjeta") == card).to_dicts()[0]


def test_no_within_zone_variation(eco: pl.DataFrame) -> None:
    """ANTI-LEAKAGE: mismo valor para QR y BIP de la misma zona."""
    for col in ECOLOGY_COLUMNS:
        if "home_zone" in col:
            vals = {row(eco, c)[col] for c in ["a", "b", "c"]}  # zona A: QR, QR, BIP
            assert len(vals) == 1, f"{col} varia dentro de la zona: {vals}"


def test_zone_share_raw(eco: pl.DataFrame) -> None:
    # Zona A: 2 QR de 3 tarjetas -> 2/3 para todas, incluida la BIP.
    for card in ["a", "b", "c"]:
        assert row(eco, card)["eco_qr_share_home_zone"] == pytest.approx(2 / 3)


def test_smoothing_formula(eco: pl.DataFrame) -> None:
    # p_global_qr = 3/5 = 0.6; m=2. Zona A: (2 + 2*0.6) / (3 + 2) = 0.64.
    assert row(eco, "a")["eco_qr_share_home_zone_smooth"] == pytest.approx(0.64)
    # QR_RED: p_global_red = 0.2. Zona A: (1 + 2*0.2) / (3 + 2) = 0.28.
    assert row(eco, "c")["eco_qr_red_share_home_zone_smooth"] == pytest.approx(0.28)


def test_singleton_zone_shrinks_to_global(eco: pl.DataFrame) -> None:
    # Zona B (n=1, QR): raw = 1.0; smooth = (1 + 2*0.6)/(1+2) = 0.7333.
    r = row(eco, "d")
    assert r["eco_qr_share_home_zone"] == pytest.approx(1.0)
    assert r["eco_qr_share_home_zone_smooth"] == pytest.approx(2.2 / 3)
    # soporte: log(1 + 1) = log 2.
    assert r["eco_home_zone_n_cards_log"] == pytest.approx(0.6931, abs=1e-3)


def test_null_zone(eco: pl.DataFrame) -> None:
    r = row(eco, "e")
    assert r["eco_qr_share_home_zone"] is None
    assert r["eco_qr_share_home_zone_smooth"] is None
    assert r["eco_home_zone_n_cards_log"] is None
    # bloque origin (zona A tiene 4 tarjetas: a,b,c,e; QR = a,b -> 2/4).
    assert r["eco_qr_share_origin_top1"] == pytest.approx(0.5)


def test_output_contract(eco: pl.DataFrame) -> None:
    assert eco.height == 5
    assert eco["id_tarjeta"].n_unique() == 5
    assert eco.columns == ["id_tarjeta"] + ECOLOGY_COLUMNS
    for col in ECOLOGY_COLUMNS:
        vals = [v for v in eco[col].to_list() if v is not None]
        assert all(v >= 0 for v in vals), col
