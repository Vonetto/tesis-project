from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

import geopandas as gpd
import pandas as pd
import polars as pl

from lib.interannual_offer_context import build_zona777_area_table_from_gdf, ensure_unique_keys


@dataclass(frozen=True)
class OSMTagValueSpec:
    key: str
    value: str
    feature_name: str
    status: str
    notes: str = ""
    transport_like_only: bool = False


TRANSPORT_LIKE_TAG_VALUES = {
    "highway": {"bus_stop", "platform"},
    "public_transport": {"platform", "station", "stop_position"},
    "bus": {"yes", "designated"},
    "railway": {"subway_entrance", "station", "stop", "platform", "halt"},
}


OSM_MICROINFRA_ZONA777_SPECS: tuple[OSMTagValueSpec, ...] = (
    OSMTagValueSpec(
        "shelter",
        "yes",
        "osm_transport_shelter_yes",
        "microinfra_candidate",
        "transport-like objects only; stop waiting quality proxy",
        True,
    ),
    OSMTagValueSpec(
        "bench",
        "yes",
        "osm_transport_bench_yes",
        "microinfra_candidate",
        "transport-like objects only; stop waiting quality proxy",
        True,
    ),
    OSMTagValueSpec(
        "railway",
        "subway_entrance",
        "osm_railway_subway_entrance",
        "microinfra_candidate",
        "metro physical access; check redundancy with metro controls",
    ),
)


DEFAULT_OSM_ZONA777_SPECS: tuple[OSMTagValueSpec, ...] = (
    OSMTagValueSpec("amenity", "school", "osm_amenity_school", "priority"),
    OSMTagValueSpec("amenity", "restaurant", "osm_amenity_restaurant", "priority"),
    OSMTagValueSpec("amenity", "pharmacy", "osm_amenity_pharmacy", "priority"),
    OSMTagValueSpec("amenity", "kindergarten", "osm_amenity_kindergarten", "priority"),
    OSMTagValueSpec("amenity", "clinic", "osm_amenity_clinic", "priority"),
    OSMTagValueSpec("amenity", "university", "osm_amenity_university", "priority", "promoted explicitly"),
    OSMTagValueSpec("shop", "convenience", "osm_shop_convenience", "priority"),
    OSMTagValueSpec("shop", "supermarket", "osm_shop_supermarket", "priority"),
    OSMTagValueSpec("shop", "bakery", "osm_shop_bakery", "priority"),
    OSMTagValueSpec("shop", "hardware", "osm_shop_hardware", "priority"),
    OSMTagValueSpec("shop", "mall", "osm_shop_mall", "priority", "promoted explicitly"),
    OSMTagValueSpec("leisure", "park", "osm_leisure_park", "priority"),
    OSMTagValueSpec("leisure", "playground", "osm_leisure_playground", "priority"),
    OSMTagValueSpec("leisure", "sports_centre", "osm_leisure_sports_centre", "priority"),
    OSMTagValueSpec("office", "company", "osm_office_company", "priority"),
    OSMTagValueSpec("office", "government", "osm_office_government", "priority"),
    OSMTagValueSpec("office", "educational_institution", "osm_office_educational_institution", "priority"),
    OSMTagValueSpec("landuse", "residential", "osm_landuse_residential", "priority", "point-based exploratory version"),
    OSMTagValueSpec("landuse", "industrial", "osm_landuse_industrial", "priority", "point-based exploratory version"),
    OSMTagValueSpec("landuse", "retail", "osm_landuse_retail", "priority", "point-based exploratory version"),
    OSMTagValueSpec("landuse", "commercial", "osm_landuse_commercial", "priority", "point-based exploratory version"),
    OSMTagValueSpec("public_transport", "platform", "osm_public_transport_platform", "observation"),
    OSMTagValueSpec("public_transport", "station", "osm_public_transport_station", "observation"),
    OSMTagValueSpec("public_transport", "stop_position", "osm_public_transport_stop_position", "observation"),
    *OSM_MICROINFRA_ZONA777_SPECS,
)


def load_osm_raw(path: str | Path) -> gpd.GeoDataFrame:
    path = Path(path)
    if path.suffix == ".parquet":
        return gpd.read_parquet(path)
    return gpd.read_file(path)


def prepare_osm_points_for_join(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf = gdf[gdf.geometry.notnull()].copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    gdf = gdf.to_crs(4326)
    gdf["geometry"] = gdf.geometry.representative_point()
    return gdf


def build_osm_spec_table(specs: tuple[OSMTagValueSpec, ...] = DEFAULT_OSM_ZONA777_SPECS) -> pl.DataFrame:
    return pl.DataFrame([asdict(s) for s in specs]).sort(["status", "feature_name"])


def aggregate_osm_point_features_to_zona777(
    gdf_points: gpd.GeoDataFrame,
    gdf_zonas: gpd.GeoDataFrame,
    specs: tuple[OSMTagValueSpec, ...] = DEFAULT_OSM_ZONA777_SPECS,
) -> pl.DataFrame:
    if "ZONA777" not in gdf_zonas.columns:
        raise ValueError("gdf_zonas debe incluir columna ZONA777")
    if gdf_points.crs is None:
        gdf_points = gdf_points.set_crs("EPSG:4326", allow_override=True)
    if gdf_zonas.crs is None:
        gdf_zonas = gdf_zonas.set_crs("EPSG:4674", allow_override=True)

    gdf_points = gdf_points.to_crs(4326)
    gdf_zonas = gdf_zonas.to_crs(4326)

    requested_keys = {s.key for s in specs}
    if any(s.transport_like_only for s in specs):
        requested_keys |= set(TRANSPORT_LIKE_TAG_VALUES)
    needed_keys = sorted(k for k in requested_keys if k in gdf_points.columns)
    joined = gpd.sjoin(
        gdf_points[["geometry"] + needed_keys],
        gdf_zonas[["ZONA777", "geometry"]],
        how="inner",
        predicate="within",
    )

    area_df = build_zona777_area_table_from_gdf(gdf_zonas).rename({"zona_inicio_viaje": "ZONA777"})
    base = (
        pl.from_pandas(gdf_zonas[["ZONA777"]])
        .with_columns(pl.col("ZONA777").cast(pl.Int64, strict=False))
        .drop_nulls()
        .unique()
        .sort("ZONA777")
        .join(area_df, on="ZONA777", how="left")
    )
    ensure_unique_keys(base, ["ZONA777"], "osm_zona777_base")
    for spec in specs:
        base = base.with_columns(
            pl.lit(0).cast(pl.Int64).alias(f"{spec.feature_name}_count"),
            pl.lit(0).cast(pl.Int8).alias(f"{spec.feature_name}_presence"),
            pl.lit(0.0).cast(pl.Float64).alias(f"{spec.feature_name}_density_km2"),
        )

    if joined.empty:
        return base

    out = base
    for spec in specs:
        if spec.key not in joined.columns:
            continue
        sub = joined.loc[joined[spec.key].notna(), ["ZONA777", spec.key]].copy()
        if sub.empty:
            continue
        sub[spec.key] = sub[spec.key].astype("string")
        mask = sub[spec.key] == spec.value
        if spec.transport_like_only:
            transport_like_mask = pd.Series(False, index=joined.index)
            for key, values in TRANSPORT_LIKE_TAG_VALUES.items():
                if key in joined.columns:
                    transport_like_mask |= joined[key].astype("string").isin(values)
            mask &= transport_like_mask.loc[sub.index]
        sub = sub.loc[mask, ["ZONA777"]].copy()
        if sub.empty:
            continue

        df_counts = (
            pl.from_pandas(sub)
            .with_columns(pl.col("ZONA777").cast(pl.Int64, strict=False))
            .group_by("ZONA777")
            .agg(pl.len().alias(f"{spec.feature_name}_count"))
            .sort("ZONA777")
        )
        out = (
            out.join(df_counts, on="ZONA777", how="left")
            .with_columns(
                pl.coalesce(
                    [
                        pl.col(f"{spec.feature_name}_count_right"),
                        pl.col(f"{spec.feature_name}_count"),
                    ]
                )
                .fill_null(0)
                .cast(pl.Int64)
                .alias(f"{spec.feature_name}_count")
            )
            .drop(f"{spec.feature_name}_count_right")
            .with_columns(
                (pl.col(f"{spec.feature_name}_count") > 0)
                .cast(pl.Int8)
                .alias(f"{spec.feature_name}_presence")
            )
            .with_columns(
                pl.when(pl.col("AREA_KM2") > 0)
                .then(pl.col(f"{spec.feature_name}_count") / pl.col("AREA_KM2"))
                .otherwise(None)
                .alias(f"{spec.feature_name}_density_km2")
            )
        )

    return out.sort("ZONA777")


def build_osm_zona777_outputs(
    *,
    osm_raw_path: str | Path,
    zonas_path: str | Path,
    out_dir: str | Path,
    specs: tuple[OSMTagValueSpec, ...] = DEFAULT_OSM_ZONA777_SPECS,
) -> pl.DataFrame:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    gdf_osm_raw = load_osm_raw(osm_raw_path)
    gdf_osm_points = prepare_osm_points_for_join(gdf_osm_raw)

    gdf_zonas = gpd.read_file(zonas_path)[["ZONA777", "geometry"]].copy()
    if gdf_zonas.crs is None:
        gdf_zonas = gdf_zonas.set_crs("EPSG:4674", allow_override=True)
    if gdf_zonas["ZONA777"].duplicated().any():
        gdf_zonas = gdf_zonas.dissolve(by="ZONA777", as_index=False)
        gdf_zonas = gpd.GeoDataFrame(gdf_zonas, geometry="geometry", crs=gdf_zonas.crs)

    df = aggregate_osm_point_features_to_zona777(
        gdf_points=gdf_osm_points,
        gdf_zonas=gdf_zonas,
        specs=specs,
    )
    spec_table = build_osm_spec_table(specs)

    out_features = out_dir / "osm_zona777_features.parquet"
    out_specs = out_dir / "osm_zona777_feature_specs.parquet"
    out_summary = out_dir / "osm_zona777_summary.json"

    df.write_parquet(out_features)
    spec_table.write_parquet(out_specs)
    out_summary.write_text(
        json.dumps(
            {
                "n_zonas": int(df.height),
                "n_specs": int(spec_table.height),
                "n_priority_specs": int(spec_table.filter(pl.col("status") == "priority").height),
                "n_observation_specs": int(spec_table.filter(pl.col("status") == "observation").height),
                "features_path": str(out_features),
                "specs_path": str(out_specs),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return df
