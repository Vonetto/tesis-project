from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/eod2012"
EOD_FEATURES = OUT / "eod2012_zone_features_eodzone.parquet"
EOD_ZONES = Path("/Users/vicenteonetto/Downloads/Zonificacion_EOD-2012_Santiago/Zonificacion_EOD2012.shp")
ZONA777 = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)


def clean_geometries(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    out = gdf.copy()
    out["geometry"] = out.geometry.make_valid()
    return out[~out.geometry.is_empty & out.geometry.notna()].copy()


def build_crosswalk() -> pd.DataFrame:
    eod = gpd.read_file(EOD_ZONES)[["Zona", "geometry"]]
    eod["Zona"] = pd.to_numeric(eod["Zona"], errors="coerce")
    eod = eod[eod["Zona"].notna()].copy()
    eod["Zona"] = eod["Zona"].astype(int)
    eod = clean_geometries(eod)
    eod = eod.dissolve(by="Zona", as_index=False)

    z777 = gpd.read_file(ZONA777)[["ZONA777", "COMUNA", "geometry"]]
    z777["ZONA777"] = pd.to_numeric(z777["ZONA777"], errors="coerce")
    z777 = z777[z777["ZONA777"].notna()].copy()
    z777["ZONA777"] = z777["ZONA777"].astype(int)

    # The shapefile has lon/lat coordinates but no .prj/CRS metadata.
    z777 = z777.set_crs("EPSG:4326", allow_override=True).to_crs(eod.crs)
    z777 = clean_geometries(z777)
    z777 = z777.dissolve(by="ZONA777", as_index=False, aggfunc={"COMUNA": "first"})
    z777["zona777_area_m2"] = z777.geometry.area

    inter = gpd.overlay(
        z777[["ZONA777", "zona777_area_m2", "geometry"]],
        eod[["Zona", "geometry"]],
        how="intersection",
        keep_geom_type=True,
    )
    inter["inter_area_m2"] = inter.geometry.area
    inter = inter[inter["inter_area_m2"].gt(1)].copy()

    denom = inter.groupby("ZONA777")["inter_area_m2"].transform("sum")
    inter["area_weight"] = inter["inter_area_m2"] / denom
    inter["area_coverage"] = denom / inter["zona777_area_m2"]

    return inter[
        [
            "ZONA777",
            "Zona",
            "zona777_area_m2",
            "inter_area_m2",
            "area_weight",
            "area_coverage",
        ]
    ].sort_values(["ZONA777", "area_weight"], ascending=[True, False])


def weighted_feature_average(crosswalk: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        c
        for c in features.columns
        if c.startswith("eod2012_") and not c.endswith("_sample") and not c.endswith("_w")
    ]
    merged = crosswalk.merge(features[["Zona", *feature_cols]], on="Zona", how="left")

    rows = []
    for zona777, group in merged.groupby("ZONA777", sort=True):
        row = {
            "ZONA777": int(zona777),
            "eod2012_area_coverage": float(group["area_coverage"].iloc[0]),
            "eod2012_n_eod_zones_intersected": int(group["Zona"].nunique()),
        }
        for col in feature_cols:
            valid = group[col].notna()
            if valid.any():
                weights = group.loc[valid, "area_weight"]
                row[col] = float((group.loc[valid, col] * weights).sum() / weights.sum())
            else:
                row[col] = pd.NA
        rows.append(row)

    return pd.DataFrame(rows)


def add_high_income_proxy_dummies(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    specs = [
        (
            "eod2012_share_hogares_abc1_income_proxy",
            "eod2012_dummy_high_abc1_income_proxy",
        ),
        (
            "eod2012_share_hogares_de_income_proxy",
            "eod2012_dummy_high_de_income_proxy",
        ),
    ]
    for source_col, dummy_col in specs:
        cutoff = out[source_col].quantile(0.75)
        out[dummy_col] = (out[source_col] >= cutoff).astype("Int64")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    crosswalk = build_crosswalk()
    features = pd.read_parquet(EOD_FEATURES)
    features["Zona"] = pd.to_numeric(features["Zona"], errors="coerce").astype("Int64")

    z777_features = add_high_income_proxy_dummies(weighted_feature_average(crosswalk, features))
    feature_cols = [c for c in z777_features.columns if c.startswith("eod2012_")]
    summary = (
        z777_features[feature_cols]
        .agg(["count", "mean", "std", "min", "median", "max"])
        .T.reset_index()
        .rename(columns={"index": "variable"})
    )

    crosswalk.to_csv(OUT / "eod2012_to_zona777_area_crosswalk.csv", index=False)
    z777_features.to_parquet(OUT / "eod2012_zone_features_zona777.parquet", index=False)
    z777_features.to_csv(OUT / "eod2012_zone_features_zona777.csv", index=False)
    summary.to_csv(OUT / "eod2012_zone_features_zona777_summary.csv", index=False)

    print(f"wrote: {OUT / 'eod2012_zone_features_zona777.parquet'}")
    print(f"zona777: {len(z777_features):,}")
    print(f"feature_cols: {len(feature_cols):,}")
    print(
        crosswalk.groupby("ZONA777")
        .agg(
            area_coverage=("area_coverage", "first"),
            n_eod_zones=("Zona", "nunique"),
        )
        .describe()
        .to_string()
    )


if __name__ == "__main__":
    main()
