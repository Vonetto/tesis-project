"""Tests de lib/user_level/mnl_prep.py.

Dos niveles:
  - SINTÉTICOS (siempre corren): validan la lógica de transformación con un
    mini-DataFrame controlado, sin depender de la matriz real (KINGSTON).
  - INTEGRACIÓN (skip si no está la matriz): corre prepare_mnl_dataset sobre el
    parquet real y verifica invariantes.

Correr:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
      lib/user_level/test_mnl_prep.py -v
"""
from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from lib.user_level import mnl_prep as mp


# --------------------------------------------------------------------------
# Helpers sintéticos
# --------------------------------------------------------------------------
def _synthetic_matrix(n=400, seed=0) -> pl.DataFrame:
    """Mini-matriz con las columnas que prepare_mnl_dataset necesita."""
    rng = np.random.default_rng(seed)
    macro_levels = mp.MACRO_LEVELS

    def onehot(prefix):
        idx = rng.integers(0, len(macro_levels), size=n)
        cols = {}
        for j, lvl in enumerate(macro_levels):
            cols[f"{prefix}_macro_{lvl}"] = (idx == j).astype(np.int8)
        return cols

    tipo = rng.choice(["BIP", "QR_RED", "QR_OTHER"], size=n, p=[0.83, 0.03, 0.14])
    share2025 = rng.choice([0.0, 0.5, 1.0], size=n, p=[0.36, 0.28, 0.36])

    data = {
        "id_tarjeta": [f"T{i}" for i in range(n)],
        "tipo_tarjeta": tipo,
        "n_viajes": rng.integers(3, 200, size=n).astype(np.float64),
        "share_trips_2025": share2025,
    }
    for c in mp.USE_SHARES:
        data[c] = rng.beta(0.5, 0.5, size=n)
    data["hora_mean"] = rng.normal(13, 2, size=n)
    data["hora_std"] = np.abs(rng.normal(3.8, 1.5, size=n))
    data["t_vehiculo_mean_min"] = np.abs(rng.normal(18, 11, size=n))
    data["t_espera_ini_mean_min"] = np.abs(rng.normal(5, 4, size=n))
    for c in mp.SOCIO_ALREADY_Z:
        data[c] = rng.normal(0, 1, size=n)
    for c in mp.SOCIO_AGE_BANDS_RAW:
        data[c] = rng.uniform(0.05, 0.5, size=n)
    for c in mp.SOCIO_WINSOR:
        data[c] = rng.normal(0, 1.2, size=n)
    data.update(onehot("home"))
    data.update(onehot("origin_top1"))
    return pl.DataFrame(data)


# --------------------------------------------------------------------------
# Tests sintéticos de las piezas
# --------------------------------------------------------------------------
def test_zscore_expr_mean0_std1():
    df = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0]})
    out = df.with_columns(mp._zscore_expr("x", "z"))
    z = out["z"].to_numpy()
    assert abs(z.mean()) < 1e-9
    assert abs(z.std(ddof=0) - 1.0) < 1e-9


def test_zscore_constant_is_zero():
    df = pl.DataFrame({"x": [7.0, 7.0, 7.0]})
    out = df.with_columns(mp._zscore_expr("x", "z"))
    assert out["z"].to_list() == [0.0, 0.0, 0.0]


def test_winsor_caps_tails():
    x = list(np.arange(0, 100, dtype=float)) + [1000.0]  # outlier alto
    df = pl.DataFrame({"x": x})
    out = df.with_columns(mp._winsor_zscore_expr("x", 0.01, 0.99, "w"))
    # tras winsor, el max estandarizado no debe estar dominado por el 1000
    w = out["w"].to_numpy()
    # el outlier no puede ser el único valor extremo gigante
    assert w.max() < 5.0


def test_cohort_dummies_partition():
    df = pl.DataFrame({"share_trips_2025": [0.0, 0.3, 1.0, 0.0, 1.0]})
    out, active = mp._build_cohort_dummies(df)
    assert active == ["cohort_mixta", "cohort_solo_2025"]
    # cada fila cae en exactamente una cohorte
    s = (out["cohort_solo_2024"] + out["cohort_mixta"] + out["cohort_solo_2025"])
    assert s.to_list() == [1, 1, 1, 1, 1]
    assert out["cohort_solo_2024"].to_list() == [1, 0, 0, 1, 0]
    assert out["cohort_solo_2025"].to_list() == [0, 0, 1, 0, 1]


def test_macro_active_excludes_reference():
    active = mp._macro_active_cols("home")
    assert "home_macro_poniente" not in active        # PONIENTE es referencia
    assert "home_macro_centro" in active              # CENTRO sí (post-fix)
    assert len(active) == len(mp.MACRO_LEVELS) - 1     # 6 activas de 7


# --------------------------------------------------------------------------
# Test de integración del flujo completo vía parquet temporal
# --------------------------------------------------------------------------
def test_prepare_full_flow_synthetic(tmp_path, monkeypatch):
    """Escribe la matriz sintética a un parquet temporal y corre
    prepare_mnl_dataset apuntando ahí."""
    df = _synthetic_matrix(n=500)
    fake = tmp_path / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
    df.write_parquet(fake)
    monkeypatch.setattr(mp, "matrix_path", lambda *a, **k: fake)

    ds = mp.prepare_mnl_dataset()

    # choice codificado 1/2/3
    assert set(ds.df["choice"].unique().to_list()) <= {1, 2, 3}
    # idco: una fila por tarjeta
    assert ds.df["id_tarjeta"].n_unique() == ds.df.height
    # bloques presentes
    assert set(ds.feature_blocks) == {"exposure", "cohort", "use", "socio", "geo"}
    # referencia PONIENTE ausente de geo
    assert "home_macro_poniente" not in ds.all_features
    assert "origin_top1_macro_poniente" not in ds.all_features
    # CENTRO presente
    assert "home_macro_centro" in ds.all_features
    # todas las features finales existen en el df
    for c in ds.all_features:
        assert c in ds.df.columns, c
    # exposición estandarizada
    z = ds.df["log1p_n_viajes_z"].to_numpy()
    assert abs(z.mean()) < 1e-6


def test_prepare_drops_no_macro(tmp_path, monkeypatch):
    df = _synthetic_matrix(n=300, seed=1)
    # forzar 10 filas sin macrozona (todas las dummies home en 0)
    home_cols = [f"home_macro_{lvl}" for lvl in mp.MACRO_LEVELS]
    zeros = {c: df[c].to_list() for c in home_cols}
    for c in home_cols:
        vals = zeros[c]
        for i in range(10):
            vals[i] = 0
        zeros[c] = vals
    df = df.with_columns([pl.Series(c, zeros[c]) for c in home_cols])
    fake = tmp_path / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
    df.write_parquet(fake)
    monkeypatch.setattr(mp, "matrix_path", lambda *a, **k: fake)

    ds_drop = mp.prepare_mnl_dataset(drop_no_macro=True)
    ds_keep = mp.prepare_mnl_dataset(drop_no_macro=False)
    assert ds_drop.df.height < ds_keep.df.height


# --------------------------------------------------------------------------
# Inercia (DSI/TSI/LSI): merge inner + subset + z
# --------------------------------------------------------------------------
def _synthetic_inertia(ids: list[str], seed=7) -> pl.DataFrame:
    """Parquet de indicadores sintético para un subconjunto de ids."""
    rng = np.random.default_rng(seed)
    n = len(ids)
    data = {"id_tarjeta": ids}
    for c in mp.INERTIA_INDICES:
        data[c] = rng.uniform(0, 1, size=n)
    return pl.DataFrame(data)


def test_inertia_merge_subsets_and_standardizes(tmp_path, monkeypatch):
    """El merge de inercia hace INNER join (subset al universo elegible),
    agrega el bloque 'inertia' y estandariza los índices a z."""
    df = _synthetic_matrix(n=500, seed=3)
    fake = tmp_path / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
    df.write_parquet(fake)
    monkeypatch.setattr(mp, "matrix_path", lambda *a, **k: fake)

    # Indicadores SOLO para las primeras 200 tarjetas -> elegibles = 200.
    eligible_ids = df["id_tarjeta"].to_list()[:200]
    ind = _synthetic_inertia(eligible_ids)
    ind_path = tmp_path / "indicators_fake.parquet"
    ind.write_parquet(ind_path)
    monkeypatch.setitem(mp.INERTIA_WINDOWS, "fake_win", "indicators_fake.parquet")
    monkeypatch.setattr(mp, "INERTIA_DIR", tmp_path)

    ds_base = mp.prepare_mnl_dataset()
    ds_in = mp.prepare_mnl_dataset(inertia_window="fake_win")

    # El universo se restringe a las elegibles (<= 200, puede bajar por
    # drop_no_macro/listwise, pero nunca supera 200 ni iguala al base).
    assert ds_in.df.height <= 200
    assert ds_in.df.height < ds_base.df.height
    # bloque inertia presente. DEFAULT = parsimonioso (sin lsi_origin_zone).
    assert "inertia" in ds_in.feature_blocks
    expected_z = [f"{c}_z" for c in mp.INERTIA_INDICES_PARSIMONIOUS]
    assert ds_in.feature_blocks["inertia"] == expected_z
    # lsi_origin_zone NO debe estar (es la redundante que se dropea por default)
    assert "lsi_origin_zone_z" not in ds_in.all_features
    for c in expected_z:
        assert c in ds_in.df.columns
        assert c in ds_in.all_features
    # estandarización: media ~0 sobre el universo elegible final
    z = ds_in.df[expected_z[0]].to_numpy()
    assert abs(z.mean()) < 1e-6
    # todas las tarjetas resultantes están en el set elegible
    assert set(ds_in.df["id_tarjeta"].to_list()) <= set(eligible_ids)


def test_inertia_joint_two_windows(tmp_path, monkeypatch):
    """Modelo CONJUNTO: 2 ventanas -> intersección de universos + columnas con
    sufijo de etiqueta (__win_a / __win_b), todas en el bloque inertia."""
    df = _synthetic_matrix(n=600, seed=11)
    fake = tmp_path / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
    df.write_parquet(fake)
    monkeypatch.setattr(mp, "matrix_path", lambda *a, **k: fake)

    ids = df["id_tarjeta"].to_list()
    # ventana A elegible para las primeras 300; ventana B para 150..450.
    # intersección = ids[150:300] = 150 tarjetas.
    a_ids, b_ids = ids[:300], ids[150:450]
    pl_a = _synthetic_inertia(a_ids, seed=1)
    pl_b = _synthetic_inertia(b_ids, seed=2)
    pl_a.write_parquet(tmp_path / "ind_a.parquet")
    pl_b.write_parquet(tmp_path / "ind_b.parquet")
    monkeypatch.setattr(mp, "INERTIA_DIR", tmp_path)
    monkeypatch.setitem(mp.INERTIA_WINDOWS, "win_a", "ind_a.parquet")
    monkeypatch.setitem(mp.INERTIA_WINDOWS, "win_b", "ind_b.parquet")

    ds = mp.prepare_mnl_dataset(inertia_window=["win_a", "win_b"])

    # intersección: <= 150 (puede bajar por drops, nunca superarlo)
    assert ds.df.height <= 150
    assert ds.df.height > 0
    # columnas con sufijo de etiqueta para cada ventana (parsimonioso x2 = 6)
    expected = ([f"{c}__win_a_z" for c in mp.INERTIA_INDICES_PARSIMONIOUS]
                + [f"{c}__win_b_z" for c in mp.INERTIA_INDICES_PARSIMONIOUS])
    assert ds.feature_blocks["inertia"] == expected
    for c in expected:
        assert c in ds.df.columns
    # las tarjetas resultantes están en AMBOS sets (intersección real)
    got = set(ds.df["id_tarjeta"].to_list())
    assert got <= (set(a_ids) & set(b_ids))


def test_inertia_unknown_window_raises(tmp_path, monkeypatch):
    df = _synthetic_matrix(n=100)
    fake = tmp_path / "user_model_matrix_interannual_ml_clean_alta_n3.parquet"
    df.write_parquet(fake)
    monkeypatch.setattr(mp, "matrix_path", lambda *a, **k: fake)
    with pytest.raises(ValueError, match="desconocido"):
        mp.prepare_mnl_dataset(inertia_window="no_existe")


# --------------------------------------------------------------------------
# Integración con la matriz REAL (skip si no está)
# --------------------------------------------------------------------------
def test_real_matrix_if_available():
    path = mp.matrix_path()
    if not path.exists():
        pytest.skip(f"matriz real no disponible: {path}")
    ds = mp.prepare_mnl_dataset()
    assert ds.df.height > 1_000_000
    assert "home_macro_centro" in ds.all_features
    assert "home_macro_poniente" not in ds.all_features
    assert set(ds.df["choice"].unique().to_list()) <= {1, 2, 3}
