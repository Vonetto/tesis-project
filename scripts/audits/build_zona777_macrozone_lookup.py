"""Materializa el lookup ZONA777 -> macrozona (7 niveles) como parquet chico.

Reusa build_macrozone_lookup() de build_user_level_payment_panel.py (requiere
geopandas + shapefile ZONAS777_SHP). Se corre UNA VEZ; el output (777 filas)
queda disponible para joins simples sin depender de geopandas en cada corrida
(p.ej. build_user_sequence_embedding_features.py para la Etapa A/B del
sequence_repeat_pack -> sequence_embedding_pack, 2026-06-13).

Uso:
  /Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
    scripts/audits/build_zona777_macrozone_lookup.py --force
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from build_user_level_payment_panel import MACROZONA_COLS, build_macrozone_lookup  # noqa: E402

OUT_PATH = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "zona777_macrozone_lookup.parquet"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if OUT_PATH.exists() and not args.force:
        print(f"OK exists: {OUT_PATH}")
        return

    lookup = build_macrozone_lookup().select(["ZONA777", "macrozone_model", *MACROZONA_COLS])
    if lookup.select(pl.col("ZONA777").n_unique()).item() != lookup.height:
        raise ValueError("ZONA777 no es unico en el lookup de macrozonas")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lookup.write_parquet(OUT_PATH)
    print(f"OK: {OUT_PATH}")
    print(f"rows={lookup.height} cols={len(lookup.columns)}")
    print(lookup.group_by("macrozone_model").len().sort("macrozone_model"))


if __name__ == "__main__":
    main()
