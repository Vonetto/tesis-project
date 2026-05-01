from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import geopandas as gpd
import polars as pl


def ensure_unique_keys(df: pl.DataFrame, keys: Sequence[str], name: str) -> None:
    dup = df.group_by(list(keys)).len().filter(pl.col("len") > 1)
    if dup.height > 0:
        preview = dup.head(5).to_dicts()
        raise ValueError(f"{name} no es unico por {list(keys)}; ejemplos: {preview}")


def assert_left_join_preserves_rows(before_rows: int, after_rows: int, name: str) -> None:
    if before_rows != after_rows:
        raise ValueError(
            f"{name} cambio el numero de filas: before={before_rows}, after={after_rows}"
        )


def ensure_columns_non_null(df: pl.DataFrame, columns: Sequence[str], name: str) -> None:
    bad = {}
    for col in columns:
        nulls = df.select(pl.col(col).is_null().sum().alias("n")).item()
        if nulls:
            bad[col] = int(nulls)
    if bad:
        raise ValueError(f"{name} dejo columnas nulas inesperadas: {bad}")


def load_trip_zone_context(
    trips_context_path: str | Path,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    df_trips_keys = (
        pl.read_parquet(
            trips_context_path,
            columns=["partition", "franja_v2", "zona_inicio_viaje"],
        )
        .with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False))
    )
    df_trip_zones = (
        df_trips_keys.select("zona_inicio_viaje")
        .drop_nulls()
        .unique()
        .sort("zona_inicio_viaje")
    )
    ensure_unique_keys(df_trip_zones, ["zona_inicio_viaje"], "df_trip_zones")
    return df_trips_keys, df_trip_zones


def filter_to_valid_origin_zones(
    df: pl.DataFrame,
    valid_zonas: pl.DataFrame,
    name: str,
) -> tuple[pl.DataFrame, dict[str, object]]:
    if "zona_inicio_viaje" not in df.columns:
        raise ValueError(f"{name} no tiene columna zona_inicio_viaje")
    if "zona_inicio_viaje" not in valid_zonas.columns:
        raise ValueError("valid_zonas no tiene columna zona_inicio_viaje")

    valid_df = (
        valid_zonas.select(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False))
        .drop_nulls()
        .unique()
        .sort("zona_inicio_viaje")
    )
    ensure_unique_keys(valid_df, ["zona_inicio_viaje"], "valid_zonas")
    valid_zone_values = valid_df.get_column("zona_inicio_viaje").to_list()

    df_cast = df.with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False))
    null_rows = df_cast.filter(pl.col("zona_inicio_viaje").is_null()).height
    invalid_non_null = (
        df_cast
        .filter(
            pl.col("zona_inicio_viaje").is_not_null()
            & (~pl.col("zona_inicio_viaje").is_in(valid_zone_values))
        )
    )
    filtered = df_cast.filter(
        pl.col("zona_inicio_viaje").is_not_null()
        & pl.col("zona_inicio_viaje").is_in(valid_zone_values)
    )
    diag: dict[str, object] = {
        "rows_before": int(df.height),
        "rows_after": int(filtered.height),
        "rows_dropped": int(df.height - filtered.height),
        "null_rows_dropped": int(null_rows),
        "invalid_non_null_rows_dropped": int(invalid_non_null.height),
        "invalid_zone_keys": invalid_non_null.select("zona_inicio_viaje")
        .unique()
        .sort("zona_inicio_viaje")
        .get_column("zona_inicio_viaje")
        .to_list(),
    }
    return filtered, diag


def build_zona777_area_table_from_gdf(gdf: gpd.GeoDataFrame) -> pl.DataFrame:
    if "ZONA777" not in gdf.columns:
        raise ValueError(f"GeoDataFrame ZONA777 sin columna ZONA777: {list(gdf.columns)}")
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)

    gdf_utm = gdf[["ZONA777", "geometry"]].to_crs(epsg=32719).copy()
    gdf_utm["AREA_M2"] = gdf_utm.geometry.area

    df = (
        pl.from_pandas(
            gdf_utm[["ZONA777", "AREA_M2"]].rename(columns={"ZONA777": "zona_inicio_viaje"})
        )
        .with_columns(pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False))
        .group_by("zona_inicio_viaje")
        .agg(pl.col("AREA_M2").sum().alias("AREA_M2"))
        .with_columns((pl.col("AREA_M2") / 1_000_000.0).alias("AREA_KM2"))
        .sort("zona_inicio_viaje")
    )
    ensure_unique_keys(df, ["zona_inicio_viaje"], "zona_area")
    return df
