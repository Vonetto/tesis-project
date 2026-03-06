"""Join Censo 2024 Zonas777 aggregates to buffer tables.

Outputs:
 - Buffer A (inicio): add censo_* columns by zona_inicio_viaje
 - Buffer OD: add censo_o_* and censo_d_* columns by zona_inicio_viaje/zona_fin_viaje
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Tuple

import polars as pl


def _load_censo(path: Path) -> pl.DataFrame:
    df = pl.read_parquet(path)
    df = df.with_columns(pl.col("ZONA777").cast(pl.Int64, strict=False))
    cols = [c for c in df.columns if c != "ZONA777"]
    rename = {c: f"censo_{c}" for c in cols}
    return df.rename(rename)


def _join_inicio(df_buf: pl.DataFrame, df_censo: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, float]]:
    df = df_buf.with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777"))
    df_join = df.join(df_censo, on="ZONA777", how="left").drop("ZONA777")
    # diagnostics based on censo_n_per
    key = "censo_n_per"
    if key in df_join.columns:
        missing = df_join.select(pl.col(key).is_null().mean()).item()
    else:
        missing = None
    diag = {
        "rows": df_join.height,
        "pct_missing_censo_inicio": float(missing) if missing is not None else None,
    }
    return df_join, diag


def _join_od(df_buf: pl.DataFrame, df_censo: pl.DataFrame) -> Tuple[pl.DataFrame, Dict[str, float]]:
    df = df_buf.with_columns(
        [
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("ZONA777_O"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("ZONA777_D"),
        ]
    )
    censo_cols = [c for c in df_censo.columns if c != "ZONA777"]
    censo_o = df_censo.rename({c: c.replace("censo_", "censo_o_") for c in censo_cols})
    censo_d = df_censo.rename({c: c.replace("censo_", "censo_d_") for c in censo_cols})

    df_join = (
        df.join(censo_o, left_on="ZONA777_O", right_on="ZONA777", how="left")
        .join(censo_d, left_on="ZONA777_D", right_on="ZONA777", how="left", suffix="_d")
        .drop(["ZONA777_O", "ZONA777_D"])
    )

    key_o = "censo_o_n_per"
    key_d = "censo_d_n_per"
    miss_o = df_join.select(pl.col(key_o).is_null().mean()).item() if key_o in df_join.columns else None
    miss_d = df_join.select(pl.col(key_d).is_null().mean()).item() if key_d in df_join.columns else None
    diag = {
        "rows": df_join.height,
        "pct_missing_censo_origen": float(miss_o) if miss_o is not None else None,
        "pct_missing_censo_destino": float(miss_d) if miss_d is not None else None,
    }
    return df_join, diag


def run(
    buffers_inicio: Path,
    buffers_od: Path,
    censo_parquet: Path,
    out_dir: Path,
) -> Dict[str, Dict[str, float]]:
    out_dir.mkdir(parents=True, exist_ok=True)

    df_censo = _load_censo(censo_parquet)

    df_inicio = pl.read_parquet(buffers_inicio)
    df_inicio_join, diag_inicio = _join_inicio(df_inicio, df_censo)
    out_inicio = out_dir / f"{buffers_inicio.stem}_censo.parquet"
    df_inicio_join.write_parquet(out_inicio)

    df_od = pl.read_parquet(buffers_od)
    df_od_join, diag_od = _join_od(df_od, df_censo)
    out_od = out_dir / f"{buffers_od.stem}_censo.parquet"
    df_od_join.write_parquet(out_od)

    return {
        "inicio": {**diag_inicio, "path": str(out_inicio)},
        "od": {**diag_od, "path": str(out_od)},
    }


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Join Censo 2024 aggregates to Zonas777 buffers")
    p.add_argument("--buffers-inicio", required=True)
    p.add_argument("--buffers-od", required=True)
    p.add_argument("--censo", required=True)
    p.add_argument("--out-dir", required=True)
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    diag = run(
        buffers_inicio=Path(args.buffers_inicio),
        buffers_od=Path(args.buffers_od),
        censo_parquet=Path(args.censo),
        out_dir=Path(args.out_dir),
    )
    print("OK", diag)


if __name__ == "__main__":
    main()
