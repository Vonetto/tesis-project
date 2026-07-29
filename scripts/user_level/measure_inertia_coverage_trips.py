"""Mide la cobertura de los índices de inercia sobre el sample del notebook 17.

NO modifica nada: solo cuenta. Responde "¿cuántos viajes (y tarjetas) del sample
de nivel-VIAJE sobreviven el inner join con las tarjetas elegibles de cada
ventana de inercia?". Es el paso previo OBLIGATORIO antes de decidir si vale la
pena integrar la inercia al frente viaje (notebook 17).

Sample del notebook 17: pooled_2024_2025, sample2pct, home_alta. Unidad = viaje
(una fila por viaje), con id_tarjeta. Los índices son por tarjeta -> se pegan a
todos los viajes de esa tarjeta; el inner join subsetea VIAJES de tarjetas
elegibles.

Uso (Mac, larch-env): python scripts/user_level/measure_inertia_coverage_trips.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.user_level import mnl_prep as mp

MODEL_PARTITION = "pooled_2024_2025"
TAG = "sample2pct"
ARTIFACTS = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
SAMPLES = {
    "residence (sin filtro home)":
        ARTIFACTS / f"{MODEL_PARTITION}-estimation-{TAG}-residence-censo4-micro-osm-eod2012.parquet",
    "home_alta":
        ARTIFACTS / f"{MODEL_PARTITION}-estimation-{TAG}-residence-home-alta-censo4-micro-osm-eod2012.parquet",
}

# Ventanas a evaluar (individuales + las combinaciones del modelo conjunto).
WINDOW_SETS = {
    "inter": ["inter_W15_W17"],
    "intra2024": ["intra2024_W15_W17"],
    "intra2025": ["intra2025_W15_W17"],
    "inter+intra2024": ["inter_W15_W17", "intra2024_W15_W17"],
    "inter+intra2025": ["inter_W15_W17", "intra2025_W15_W17"],
    "inter+intra2024+intra2025":
        ["inter_W15_W17", "intra2024_W15_W17", "intra2025_W15_W17"],
}


def eligible_ids(windows: list[str]) -> pl.DataFrame:
    """id_tarjeta elegibles en TODAS las ventanas (intersección)."""
    out = None
    for w in windows:
        path = mp.INERTIA_DIR / mp.INERTIA_WINDOWS[w]
        ids = pl.read_parquet(path, columns=["id_tarjeta"]).with_columns(
            pl.col("id_tarjeta").cast(pl.Utf8)).unique()
        out = ids if out is None else out.join(ids, on="id_tarjeta", how="inner")
    return out


def main():
    for sample_name, sample_path in SAMPLES.items():
        if not sample_path.exists():
            print(f"\n### {sample_name}: NO existe ({sample_path.name}); "
                  f"genéralo con build_residence_model_sample.py")
            continue
        trips = pl.read_parquet(sample_path, columns=["id_tarjeta"]).with_columns(
            pl.col("id_tarjeta").cast(pl.Utf8))
        n_trips = trips.height
        n_cards = trips["id_tarjeta"].n_unique()
        print(f"\n{'='*72}")
        print(f"### Sample: {sample_name}")
        print(f"    viajes (filas): {n_trips:,} | tarjetas únicas: {n_cards:,}")
        print(f"{'='*72}")
        print(f"{'ventana(s)':<30} {'viajes':>12} {'%viajes':>9} "
              f"{'tarjetas':>11} {'%tarj':>8}")
        print("-"*72)
        for name, windows in WINDOW_SETS.items():
            elig = eligible_ids(windows)
            kept = trips.join(elig, on="id_tarjeta", how="inner")
            kt, kc = kept.height, kept["id_tarjeta"].n_unique()
            print(f"{name:<30} {kt:>12,} {kt/n_trips:>8.1%} "
                  f"{kc:>11,} {kc/n_cards:>7.1%}")


if __name__ == "__main__":
    main()
