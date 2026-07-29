from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
import polars as pl
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.interannual_offer_context import build_zona777_area_table_from_gdf


KINGSTON_ROOT = Path("/Volumes/KINGSTON/tesis-project")

DEFAULT_ZONAS777_SHP = (
    KINGSTON_ROOT
    / "raw"
    / "zonas777"
    / "Zonas777-04-04-2014"
    / "Shape"
    / "Zonas777_V07_04_2014.shp"
)

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "bip_load_access"


SOURCES = {
    "puntos_bip": {
        "path": KINGSTON_ROOT
        / "raw"
        / "bip_load_points"
        / "pcma_20240917-oficio-4770_2013.xlsx",
        "sheets": ["PCMA"],
    },
    "retail": {
        "path": KINGSTON_ROOT
        / "raw"
        / "bip_load_points"
        / "retail_20240917_oficio-4770_2013.xlsx",
        "sheets": ["Abiertos"],
    },
    "centro_normal": {
        "path": KINGSTON_ROOT
        / "raw"
        / "bip_load_points"
        / "pcmav-estandar-normal_20240917_oficio-4770_2013.xlsx",
        "sheets": ["Abierto"],
    },
    "centro_alto": {
        "path": KINGSTON_ROOT
        / "raw"
        / "bip_load_points"
        / "pcmav-alto-estandar_20240917_oficio-4770_2013.xlsx",
        "sheets": ["Abiertos"],
    },
    "metro": {
        "path": KINGSTON_ROOT
        / "raw"
        / "bip_load_points"
        / "metro_20240917_oficio-4770_2013.xlsx",
        "sheets": ["Abiertos"],
    },
}


def _norm_col(value: object) -> str:
    text = str(value).strip().lower()
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)
    )
    return text.replace(" ", "_").replace("!", "").replace(".", "")


def _clean_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    return " ".join(str(value).strip().upper().split())


def _find_header_row(path: Path, sheet: str) -> int:
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    for i in range(len(raw)):
        vals = {_norm_col(v) for v in raw.iloc[i].tolist() if pd.notna(v)}
        if {"codigo", "comuna", "longitud", "latitud"}.issubset(vals):
            return i
    raise ValueError(f"No se encontro encabezado en {path.name}::{sheet}")


def read_source(source_type: str, path: Path, sheets: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for sheet in sheets:
        header_row = _find_header_row(path, sheet)
        df = pd.read_excel(path, sheet_name=sheet, header=header_row)
        df.columns = [_norm_col(c) for c in df.columns]
        df = df.dropna(how="all")

        colmap = {
            "codigo": "codigo",
            "entidad": "entidad",
            "nombre_de_fantasia": "nombre_fantasia",
            "nombre_fantasia": "nombre_fantasia",
            "direccion": "direccion",
            "comuna": "comuna",
            "horario_referencial": "horario",
            "horario": "horario",
            "este": "este",
            "norte": "norte",
            "longitud": "lon",
            "latitud": "lat",
        }
        present = {c: colmap[c] for c in df.columns if c in colmap}
        out = df[list(present)].rename(columns=present)
        for col in [
            "codigo",
            "entidad",
            "nombre_fantasia",
            "direccion",
            "comuna",
            "horario",
            "este",
            "norte",
            "lon",
            "lat",
        ]:
            if col not in out.columns:
                out[col] = None

        out = out[
            [
                "codigo",
                "entidad",
                "nombre_fantasia",
                "direccion",
                "comuna",
                "horario",
                "este",
                "norte",
                "lon",
                "lat",
            ]
        ].copy()
        out["source_type"] = source_type
        out["source_sheet"] = sheet
        out["source_file"] = path.name
        frames.append(out)

    return pd.concat(frames, ignore_index=True)


def load_bip_load_points() -> pd.DataFrame:
    frames = []
    for source_type, spec in SOURCES.items():
        path = spec["path"]
        if not path.exists():
            raise FileNotFoundError(path)
        frames.append(read_source(source_type, path, spec["sheets"]))

    df = pd.concat(frames, ignore_index=True)
    for col in ["este", "norte", "lon", "lat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["codigo", "entidad", "nombre_fantasia", "direccion", "comuna", "horario"]:
        df[col] = df[col].map(_clean_text)

    df = df.dropna(subset=["lon", "lat"]).copy()
    df["coord_key_5"] = df.apply(lambda r: f"{r['lon']:.5f},{r['lat']:.5f}", axis=1)
    df["coord_key_6"] = df.apply(lambda r: f"{r['lon']:.6f},{r['lat']:.6f}", axis=1)
    return df


def deduplicate_physical_locations(df_raw: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df_raw.groupby("coord_key_5", dropna=False)
        .agg(
            lon=("lon", "mean"),
            lat=("lat", "mean"),
            n_raw_records=("coord_key_5", "size"),
            n_source_types=("source_type", "nunique"),
            source_types=("source_type", lambda s: "|".join(sorted(set(s)))),
            example_name=("nombre_fantasia", lambda s: next((x for x in s if pd.notna(x)), None)),
            example_address=("direccion", lambda s: next((x for x in s if pd.notna(x)), None)),
            example_comuna=("comuna", lambda s: next((x for x in s if pd.notna(x)), None)),
        )
        .reset_index()
    )
    grouped["bip_load_location_id"] = range(1, len(grouped) + 1)
    return grouped[
        [
            "bip_load_location_id",
            "coord_key_5",
            "lon",
            "lat",
            "n_raw_records",
            "n_source_types",
            "source_types",
            "example_name",
            "example_address",
            "example_comuna",
        ]
    ]


def build_zone_lookup(
    df_locations: pd.DataFrame,
    zonas777_shp: Path,
) -> tuple[pl.DataFrame, dict[str, object], pd.DataFrame]:
    gdf_zonas = gpd.read_file(zonas777_shp)[["ZONA777", "geometry"]].copy()
    if gdf_zonas.crs is None:
        gdf_zonas = gdf_zonas.set_crs("EPSG:4674", allow_override=True)

    gdf_points = gpd.GeoDataFrame(
        df_locations.copy(),
        geometry=[Point(xy) for xy in zip(df_locations["lon"], df_locations["lat"])],
        crs="EPSG:4326",
    )

    gdf_zonas_wgs = gdf_zonas.to_crs("EPSG:4326")
    joined = gpd.sjoin(
        gdf_points,
        gdf_zonas_wgs[["ZONA777", "geometry"]],
        how="left",
        predicate="within",
    )

    area_df = build_zona777_area_table_from_gdf(gdf_zonas).rename(
        {"zona_inicio_viaje": "ZONA777"}
    )
    base = (
        pl.from_pandas(gdf_zonas[["ZONA777"]])
        .with_columns(pl.col("ZONA777").cast(pl.Int64, strict=False))
        .drop_nulls()
        .unique()
        .sort("ZONA777")
        .join(area_df, on="ZONA777", how="left")
    )

    counts = (
        pl.from_pandas(joined[["ZONA777"]].dropna())
        .with_columns(pl.col("ZONA777").cast(pl.Int64, strict=False))
        .group_by("ZONA777")
        .agg(pl.len().alias("bip_load_n_points_zone"))
    )
    lookup = (
        base.join(counts, on="ZONA777", how="left")
        .with_columns(
            pl.col("bip_load_n_points_zone").fill_null(0).cast(pl.Int64),
            (pl.col("bip_load_n_points_zone").fill_null(0) > 0)
            .cast(pl.Int8)
            .alias("bip_load_has_point_zone"),
        )
        .with_columns(
            pl.when(pl.col("AREA_KM2") > 0)
            .then(pl.col("bip_load_n_points_zone") / pl.col("AREA_KM2"))
            .otherwise(None)
            .alias("bip_load_density_km2")
        )
    )

    # Nearest point distance from zone centroid in metric CRS.
    gdf_zones_metric = gdf_zonas[["ZONA777", "geometry"]].to_crs(epsg=32719).copy()
    gdf_points_metric = gdf_points.to_crs(epsg=32719).copy()
    centroids = gdf_zones_metric.copy()
    centroids["geometry"] = centroids.geometry.centroid
    nearest = gpd.sjoin_nearest(
        centroids[["ZONA777", "geometry"]],
        gdf_points_metric[["bip_load_location_id", "geometry"]],
        how="left",
        distance_col="bip_load_dist_nearest_m",
    )
    nearest_df = (
        nearest[["ZONA777", "bip_load_location_id", "bip_load_dist_nearest_m"]]
        .sort_values(["ZONA777", "bip_load_dist_nearest_m"])
        .drop_duplicates("ZONA777")
    )
    nearest_pl = (
        pl.from_pandas(nearest_df)
        .with_columns(
            pl.col("ZONA777").cast(pl.Int64, strict=False),
            pl.col("bip_load_location_id").cast(pl.Int64, strict=False),
            pl.col("bip_load_dist_nearest_m").cast(pl.Float64),
        )
    )
    lookup = lookup.join(nearest_pl, on="ZONA777", how="left").sort("ZONA777")

    diagnostics = {
        "raw_rows": int(df_locations["n_raw_records"].sum()),
        "unique_locations": int(len(df_locations)),
        "zones_total": int(base.height),
        "locations_outside_zones": int(joined["ZONA777"].isna().sum()),
        "zones_with_point": int(
            lookup.filter(pl.col("bip_load_has_point_zone") == 1).height
        ),
        "zones_without_point": int(
            lookup.filter(pl.col("bip_load_has_point_zone") == 0).height
        ),
        "max_points_zone": int(lookup["bip_load_n_points_zone"].max()),
        "median_dist_nearest_m": float(lookup["bip_load_dist_nearest_m"].median()),
        "p90_dist_nearest_m": float(
            lookup.select(pl.col("bip_load_dist_nearest_m").quantile(0.90)).item()
        ),
        "max_dist_nearest_m": float(lookup["bip_load_dist_nearest_m"].max()),
    }
    return lookup, diagnostics, joined.drop(columns="geometry")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zonas777-shp", type=Path, default=DEFAULT_ZONAS777_SHP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw = load_bip_load_points()
    locations = deduplicate_physical_locations(raw)
    lookup, diagnostics, joined = build_zone_lookup(locations, args.zonas777_shp)

    raw_out = args.output_dir / "bip_load_points_raw_open.parquet"
    loc_out = args.output_dir / "bip_load_physical_locations.parquet"
    lookup_out = args.output_dir / "bip_load_access_by_zona777.parquet"
    diag_out = args.output_dir / "bip_load_access_summary.json"
    type_counts_out = args.output_dir / "bip_load_source_type_counts.csv"
    zone_summary_out = args.output_dir / "bip_load_zone_summary.csv"

    pl.from_pandas(raw).write_parquet(raw_out)
    pl.from_pandas(locations).write_parquet(loc_out)
    lookup.write_parquet(lookup_out)
    type_counts = raw.groupby("source_type").size().reset_index(name="n_raw_records")
    type_counts.to_csv(type_counts_out, index=False)
    (
        lookup.select(
            [
                "ZONA777",
                "AREA_KM2",
                "bip_load_n_points_zone",
                "bip_load_has_point_zone",
                "bip_load_density_km2",
                "bip_load_dist_nearest_m",
                "bip_load_location_id",
            ]
        )
        .sort("bip_load_dist_nearest_m", descending=True)
        .head(50)
        .write_csv(zone_summary_out)
    )

    diagnostics["outputs"] = {
        "raw_open": str(raw_out),
        "physical_locations": str(loc_out),
        "lookup": str(lookup_out),
        "source_type_counts": str(type_counts_out),
        "zone_summary": str(zone_summary_out),
    }
    with diag_out.open("w", encoding="utf-8") as f:
        json.dump(diagnostics, f, indent=2, ensure_ascii=False)

    print(json.dumps(diagnostics, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
