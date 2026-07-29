"""Build Censo 2024 age-band features by ZONA777.

This writes a narrow lookup used by the user-level EDA. It does not overwrite
the canonical censo2024_zona777_agg_final.parquet artifact.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.censo2024_zona777 import AGE_18_PLUS_BUCKETS, JoinConfig, run


BASE_ZIP = Path("/Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip")
CARTO_MZ = Path(
    "/Volumes/KINGSTON/tesis-project/raw/censo2024/"
    "cartografia_parquet/Cartografia_censo2024_Pais_Manzanas.parquet"
)
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)

OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "censo_age_bands_zona777"
OUT_PATH = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "censo_age_bands_zona777.parquet"


def _safe_share(num: str, den: str, alias: str) -> pl.Expr:
    return (
        pl.col(num)
        / pl.when(pl.col(den) != 0).then(pl.col(den))
    ).alias(alias)


def build(force: bool = False) -> Path:
    if OUT_PATH.exists() and not force:
        print(f"OK exists: {OUT_PATH}")
        return OUT_PATH

    for path in [BASE_ZIP, CARTO_MZ, ZONAS777_SHP]:
        if not path.exists():
            raise FileNotFoundError(path)

    cfg = JoinConfig(
        base_zip=BASE_ZIP,
        base_csv_name="Base_manzana_entidad_CPV24.csv",
        carto_parquet=CARTO_MZ,
        zonas777_shp=ZONAS777_SHP,
        out_dir=OUT_DIR,
        use_centroid=False,
        compute_intersects=True,
        filter_mode="intersects",
        area_weighted=True,
    )
    df_agg, diag = run(cfg, variables=["n_per", "prom_edad", *AGE_18_PLUS_BUCKETS])
    print("Diagnostics:", diag)

    df = pl.from_pandas(df_agg)
    required = {"ZONA777", "n_per", *AGE_18_PLUS_BUCKETS}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Faltan columnas esperadas en agregado censal: {missing}")

    df_lookup = (
        df
        .with_columns(
            _safe_share("n_edad_18_24", "n_per", "share_edad_18_24"),
            _safe_share("n_edad_25_44", "n_per", "share_edad_25_44"),
            _safe_share("n_edad_45_59", "n_per", "share_edad_45_59"),
            _safe_share("n_edad_60_mas", "n_per", "share_edad_60_mas"),
            (
                (pl.col("n_edad_18_24") + pl.col("n_edad_25_44"))
                / pl.when(pl.col("n_per") != 0).then(pl.col("n_per"))
            ).alias("share_edad_18_44"),
        )
        .select(
            "ZONA777",
            "n_per",
            "prom_edad",
            *AGE_18_PLUS_BUCKETS,
            "share_edad_18_24",
            "share_edad_25_44",
            "share_edad_45_59",
            "share_edad_60_mas",
            "share_edad_18_44",
        )
        .sort("ZONA777")
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_lookup.write_parquet(OUT_PATH, compression="zstd")
    print(f"OK: {OUT_PATH}")
    print(f"rows={df_lookup.height} cols={len(df_lookup.columns)}")
    return OUT_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(force=args.force)


if __name__ == "__main__":
    main()
