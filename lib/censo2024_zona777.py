"""Censo 2024 manzana-entidad -> Zonas777 spatial join + aggregation.

Default strategy:
- Join base (CSV) to cartography (Manzanas) by MANZENT
- Assign Zonas777 by centroid within
- Aggregate socio-demo variables per ZONA777 (sums, weighted means, shares)
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import box

# ----------------------------
# Config
# ----------------------------

DEFAULT_VARS = [
    "n_per",
    "n_hombres",
    "n_mujeres",
    "prom_edad",
    "n_inmigrantes",
    "n_pueblos_orig",
    "n_afrodescendencia",
    "n_dificultad_ver",
    "n_dificultad_oir",
    "n_dificultad_mover",
    "n_dificultad_cogni",
    "n_dificultad_cuidado",
    "n_dificultad_comunic",
    "n_discapacidad",
    "prom_escolaridad18",
    "n_analfabet",
    "n_ocupado",
    "n_desocupado",
    "n_transporte_publico",
    "n_hog",
    "prom_per_hog",
    "n_serv_tel_movil",
    "n_serv_compu",
    "n_internet",
    "n_vp_ocupada",
    "n_viv_hacinadas",
]

# Counts: sum
COUNT_VARS = [
    "n_per",
    "n_hombres",
    "n_mujeres",
    "n_inmigrantes",
    "n_pueblos_orig",
    "n_afrodescendencia",
    "n_dificultad_ver",
    "n_dificultad_oir",
    "n_dificultad_mover",
    "n_dificultad_cogni",
    "n_dificultad_cuidado",
    "n_dificultad_comunic",
    "n_discapacidad",
    "n_analfabet",
    "n_ocupado",
    "n_desocupado",
    "n_transporte_publico",
    "n_hog",
    "n_serv_tel_movil",
    "n_serv_compu",
    "n_internet",
    "n_vp_ocupada",
    "n_viv_hacinadas",
]

# Weighted means: (var * weight) / sum(weight)
WEIGHTED_MEANS = {
    "prom_edad": "n_per",
    # prom_escolaridad18 ideally weighted by pop 18+, but not provided here; use n_per as proxy
    "prom_escolaridad18": "n_per",
    "prom_per_hog": "n_hog",
}

# Shares derived after aggregation
SHARES = {
    "share_inmigrantes": ("n_inmigrantes", "n_per"),
    "share_pueblos_orig": ("n_pueblos_orig", "n_per"),
    "share_afrodescendencia": ("n_afrodescendencia", "n_per"),
    "share_discapacidad": ("n_discapacidad", "n_per"),
    "share_analfabet": ("n_analfabet", "n_per"),
    "share_ocupado": ("n_ocupado", "n_per"),
    "share_desocupado": ("n_desocupado", "n_per"),
    "share_transporte_publico": ("n_transporte_publico", "n_ocupado"),
    "share_internet": ("n_internet", "n_hog"),
    "share_serv_tel_movil": ("n_serv_tel_movil", "n_hog"),
    "share_serv_compu": ("n_serv_compu", "n_hog"),
    "share_hacinamiento": ("n_viv_hacinadas", "n_vp_ocupada"),
}

KEY_COLS = [
    "COD_REGION",
    "MANZENT",
    "ID_ENTIDAD",
    "COD_ENTIDAD",
    "COD_MANZANA",
    "COD_ZONA",
    "COD_DISTRITO",
    "CUT",
    "COMUNA",
]


def _normalize_key(series: pd.Series) -> pd.Series:
    """Normalize join keys across CSV/parquet (handles scientific notation)."""
    import pandas as pd

    s = series
    if pd.api.types.is_numeric_dtype(s):
        s_num = pd.to_numeric(s, errors="coerce").round()
        s_out = s_num.astype("Int64").astype("string")
        return s_out.replace("<NA>", pd.NA)

    s = s.astype("string")
    # normalize decimal comma to dot
    s = s.str.replace(",", ".", regex=False)
    # try numeric conversion (scientific notation)
    num = pd.to_numeric(s, errors="coerce")
    s_num = num.round().astype("Int64").astype("string")
    # fallback: keep digits only
    s_digits = s.str.replace(r"\\D", "", regex=True)
    s_out = s_num.where(num.notna(), s_digits)
    s_out = s_out.replace("", pd.NA)
    return s_out


@dataclass
class JoinConfig:
    base_zip: Path
    base_csv_name: str
    carto_parquet: Path
    zonas777_shp: Path
    out_dir: Path
    use_centroid: bool = True
    compute_intersects: bool = True
    filter_mode: str = "none"  # none | bbox | region | both | intersects
    area_weighted: bool = False  # if True, use polygon overlay with area shares
    join_key: str = "MANZENT"


# ----------------------------
# Helpers
# ----------------------------

def _read_base_csv(cfg: JoinConfig, variables: List[str]) -> pd.DataFrame:
    usecols = list(dict.fromkeys(KEY_COLS + variables + [cfg.join_key]))
    dtype = {k: "string" for k in KEY_COLS}

    # Prefer reading via zip:// but fall back to a local temp extraction if needed.
    zip_path = Path(cfg.base_zip)
    if zip_path.exists():
        # fsspec zip URL format (note the single '!' separator)
        zip_url = f"zip://{zip_path}!{cfg.base_csv_name}"
        try:
            df = pd.read_csv(
                zip_url,
                sep=";",
                usecols=lambda c: c in usecols,
                dtype=dtype,
                encoding="utf-8-sig",
                low_memory=False,
            )
        except Exception:
            # fallback: extract to out_dir/tmp and read from disk
            import zipfile

            tmp_dir = cfg.out_dir / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_csv = tmp_dir / cfg.base_csv_name
            if not tmp_csv.exists():
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extract(cfg.base_csv_name, path=tmp_dir)
            df = pd.read_csv(
                tmp_csv,
                sep=";",
                usecols=lambda c: c in usecols,
                dtype=dtype,
                encoding="utf-8-sig",
                low_memory=False,
            )
    else:
        raise FileNotFoundError(f"Base zip not found: {zip_path}")

    # normalize key types
    for k in KEY_COLS:
        if k in df.columns:
            df[k] = df[k].astype("string")
    # normalize join key for consistency
    if cfg.join_key in df.columns:
        df[cfg.join_key] = _normalize_key(df[cfg.join_key])
    # cast variable columns to numeric (handle decimal comma)
    for v in variables:
        if v in df.columns:
            col = df[v]
            if pd.api.types.is_string_dtype(col) or col.dtype == object:
                col = col.astype("string").str.replace(",", ".", regex=False)
            df[v] = pd.to_numeric(col, errors="coerce")
    return df


def _read_carto(carto_parquet: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_parquet(carto_parquet)
    # normalize key type for join
    # (will be applied later once join_key is known)
    # ensure geometry column exists
    if "geometry" not in gdf.columns:
        if "SHAPE" in gdf.columns:
            gdf = gdf.set_geometry("SHAPE")
            gdf = gdf.rename_geometry("geometry")
        else:
            raise ValueError(f"No geometry column found in cartography parquet: {list(gdf.columns)[:20]}")
    # ensure CRS
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    # keep only key candidates + geometry (+ COD_REGION for filtering)
    keep_cols = ["geometry"]
    for k in ["MANZENT", "ID_ENTIDAD", "COD_ENTIDAD"]:
        if k in gdf.columns:
            keep_cols.append(k)
    if "COD_REGION" in gdf.columns:
        keep_cols.append("COD_REGION")
    gdf = gdf[keep_cols].copy()
    return gdf


def _read_zonas777(zonas777_shp: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(zonas777_shp)
    if "ZONA777" not in gdf.columns:
        raise ValueError("Zonas777 shapefile missing ZONA777 column")
    # enforce CRS to match Censo cartography
    gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    # keep only ZONA777 + geometry
    return gdf[["ZONA777", "geometry"]].copy()


def _spatial_assign_zona777(
    gdf_ent: gpd.GeoDataFrame, gdf_zonas: gpd.GeoDataFrame, use_centroid: bool
) -> gpd.GeoDataFrame:
    if use_centroid:
        # compute centroids in a projected CRS to avoid warnings, then reproject back
        proj_epsg = 32719  # UTM 19S covers Santiago area
        gdf_cent = gdf_ent.to_crs(epsg=proj_epsg).copy()
        gdf_cent["geometry"] = gdf_cent.geometry.centroid
        gdf_cent = gdf_cent.to_crs(gdf_zonas.crs)
        joined = gpd.sjoin(gdf_cent, gdf_zonas, how="left", predicate="within")
    else:
        # intersects (may duplicate rows); kept for area-weighted overlay if needed
        joined = gpd.sjoin(gdf_ent, gdf_zonas, how="left", predicate="intersects")
    return joined


def _diagnostics(
    gdf_ent: gpd.GeoDataFrame,
    gdf_zonas: gpd.GeoDataFrame,
    join_key: str,
) -> Dict[str, float]:
    # centroid outside (computed in projected CRS)
    proj_epsg = 32719
    gdf_cent = gdf_ent.to_crs(epsg=proj_epsg).copy()
    gdf_cent["geometry"] = gdf_cent.geometry.centroid
    gdf_cent = gdf_cent.to_crs(gdf_zonas.crs)
    cent_join = gpd.sjoin(gdf_cent, gdf_zonas, how="left", predicate="within")
    pct_centroid_out = float(cent_join["ZONA777"].isna().mean())

    # entities intersecting multiple zones
    inter = gpd.sjoin(gdf_ent, gdf_zonas, how="left", predicate="intersects")
    key = join_key if join_key in inter.columns else "ID_ENTIDAD"
    counts = inter.groupby(key)["ZONA777"].nunique(dropna=True)
    pct_multi = float((counts > 1).mean())

    return {
        "pct_centroid_outside_zonas777": pct_centroid_out,
        "pct_entities_intersect_multiple_zonas777": pct_multi,
    }


def _filter_by_mode(
    df_base: pd.DataFrame,
    gdf_ent: gpd.GeoDataFrame,
    gdf_zonas: gpd.GeoDataFrame,
    mode: str,
    join_key: str,
) -> Tuple[pd.DataFrame, gpd.GeoDataFrame]:
    mode = mode.lower().strip()
    if mode not in {"none", "bbox", "region", "both", "intersects"}:
        raise ValueError(f"Unknown filter_mode: {mode}")

    # region filter (RM = 13)
    if mode in {"region", "both"}:
        if "COD_REGION" in df_base.columns:
            df_base = df_base[df_base["COD_REGION"].astype(str) == "13"].copy()
        if "COD_REGION" in gdf_ent.columns:
            gdf_ent = gdf_ent[gdf_ent["COD_REGION"].astype(str) == "13"].copy()

    # bbox filter from Zonas777
    if mode in {"bbox", "both"}:
        minx, miny, maxx, maxy = gdf_zonas.total_bounds
        bbox = gpd.GeoSeries([box(minx, miny, maxx, maxy)], crs=gdf_zonas.crs)
        gdf_ent = gdf_ent[gdf_ent.intersects(bbox.iloc[0])].copy()
        # keep base rows that are in filtered entidades
        if join_key in df_base.columns and join_key in gdf_ent.columns:
            df_base = df_base[df_base[join_key].isin(gdf_ent[join_key])].copy()

    # precise intersects against Zonas777 polygons
    if mode == "intersects":
        zonas_union = gdf_zonas.unary_union
        gdf_ent = gdf_ent[gdf_ent.intersects(zonas_union)].copy()
        if join_key in df_base.columns and join_key in gdf_ent.columns:
            df_base = df_base[df_base[join_key].isin(gdf_ent[join_key])].copy()

    return df_base, gdf_ent


def _overlay_area_weighted(
    gdf_ent: gpd.GeoDataFrame, gdf_zonas: gpd.GeoDataFrame, join_key: str
) -> gpd.GeoDataFrame:
    # project to compute areas reliably
    proj_epsg = 32719  # UTM 19S
    ent_p = gdf_ent.to_crs(epsg=proj_epsg).copy()
    zon_p = gdf_zonas.to_crs(epsg=proj_epsg).copy()
    ent_p["ent_area"] = ent_p.geometry.area

    inter = gpd.overlay(ent_p, zon_p, how="intersection")
    inter["inter_area"] = inter.geometry.area
    inter["area_share"] = inter["inter_area"] / inter["ent_area"]
    # drop invalid/zero
    inter = inter[inter["area_share"] > 0].copy()
    # keep original CRS for downstream joins
    inter = inter.to_crs(gdf_zonas.crs)
    keep = [join_key, "ZONA777", "area_share", "geometry"]
    return inter[keep]


def _aggregate_by_zona(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    # sum counts
    agg_dict = {v: "sum" for v in COUNT_VARS if v in df.columns}
    if not agg_dict:
        raise ValueError(f"No count variables found in df columns. cols={list(df.columns)[:50]}")
    # enforce numeric to avoid string arithmetic
    numeric_cols = set(agg_dict.keys()) | set(WEIGHTED_MEANS.keys()) | set(WEIGHTED_MEANS.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    grouped = df.groupby("ZONA777", dropna=True).agg(agg_dict)

    # weighted means
    for var, w in WEIGHTED_MEANS.items():
        if var in df.columns and w in df.columns:
            num = (df[var] * df[w]).groupby(df["ZONA777"]).sum()
            den = df[w].groupby(df["ZONA777"]).sum()
            den_safe = den.where(den != 0)
            grouped[var] = num.divide(den_safe)

    # shares
    for out, (num, den) in SHARES.items():
        if num in grouped.columns and den in grouped.columns:
            den_safe = grouped[den].where(grouped[den] != 0)
            grouped[out] = grouped[num].divide(den_safe)

    grouped = grouped.reset_index()
    return grouped


def run(cfg: JoinConfig, variables: List[str] | None = None) -> Tuple[pd.DataFrame, Dict[str, float]]:
    variables = variables or DEFAULT_VARS
    cfg.out_dir.mkdir(parents=True, exist_ok=True)

    # read base + cartography + zonas
    df_base = _read_base_csv(cfg, variables)
    gdf_ent = _read_carto(cfg.carto_parquet)
    gdf_zonas = _read_zonas777(cfg.zonas777_shp)

    # normalize join key on cartography
    if cfg.join_key not in gdf_ent.columns:
        raise ValueError(f"Join key '{cfg.join_key}' missing in cartography columns: {list(gdf_ent.columns)}")
    gdf_ent[cfg.join_key] = _normalize_key(gdf_ent[cfg.join_key])

    # optional filtering (region/bbox) before join/diagnostics
    df_base, gdf_ent = _filter_by_mode(df_base, gdf_ent, gdf_zonas, cfg.filter_mode, cfg.join_key)

    # join base to entities geometry
    if cfg.join_key not in df_base.columns or cfg.join_key not in gdf_ent.columns:
        raise ValueError(f"Join key '{cfg.join_key}' missing in base or cartography")
    # key overlap diagnostics before merge
    base_keys = df_base[cfg.join_key].dropna()
    carto_keys = gdf_ent[cfg.join_key].dropna()
    overlap_base = float(base_keys.isin(set(carto_keys)).mean()) if len(base_keys) else 0.0
    overlap_carto = float(carto_keys.isin(set(base_keys)).mean()) if len(carto_keys) else 0.0
    gdf = gdf_ent.merge(df_base, on=cfg.join_key, how="left")

    # diagnostics
    diag = _diagnostics(gdf_ent, gdf_zonas, cfg.join_key) if cfg.compute_intersects else {}
    diag.update(
        {
            "pct_base_keys_in_carto": overlap_base,
            "pct_carto_keys_in_base": overlap_carto,
        }
    )
    # merge coverage diagnostic
    if "n_per" in gdf.columns:
        diag["pct_rows_with_n_per"] = float(gdf["n_per"].notna().mean())

    # spatial assign to ZONA777
    if cfg.area_weighted:
        gdf_inter = _overlay_area_weighted(gdf, gdf_zonas, cfg.join_key)
        df_join = pd.DataFrame(gdf_inter.drop(columns="geometry")).merge(
            df_base, on=cfg.join_key, how="left"
        )
        # apply area share to count vars and weights
        for v in COUNT_VARS:
            if v in df_join.columns:
                df_join[v] = df_join[v] * df_join["area_share"]
        # also scale weight variables used in weighted means / shares
        for w in set(WEIGHTED_MEANS.values()):
            if w in df_join.columns:
                df_join[w] = df_join[w] * df_join["area_share"]
        # keep area_share for diagnostics if needed
    else:
        gdf_join = _spatial_assign_zona777(gdf, gdf_zonas, use_centroid=cfg.use_centroid)
        df_join = pd.DataFrame(gdf_join.drop(columns="geometry"))

    # drop rows without ZONA777
    df_join = df_join[df_join["ZONA777"].notna()].copy()
    df_join["ZONA777"] = df_join["ZONA777"].astype(int)

    # aggregate
    df_agg = _aggregate_by_zona(df_join)

    # outputs
    suffix = f"{cfg.filter_mode}{'_area' if cfg.area_weighted else ''}"
    out_parquet = cfg.out_dir / f"censo2024_zona777_agg_{suffix}.parquet"
    out_diag = cfg.out_dir / f"censo2024_zona777_diag_{suffix}.json"
    df_agg.to_parquet(out_parquet, index=False)
    if diag:
        import json

        out_diag.write_text(json.dumps(diag, indent=2))

    return df_agg, diag


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Censo 2024 -> Zonas777 spatial join + aggregation")
    p.add_argument("--base-zip", required=True, help="Path to Base_manzana_entidad_CPV24.zip")
    p.add_argument("--base-csv-name", default="Base_manzana_entidad_CPV24.csv")
    p.add_argument("--carto-parquet", required=True, help="Path to Cartografia_censo2024_Pais_Manzanas.parquet")
    p.add_argument("--zonas777-shp", required=True, help="Path to Zonas777 shapefile")
    p.add_argument("--out-dir", required=True, help="Output directory")
    p.add_argument("--no-centroid", action="store_true", help="Use intersects instead of centroid")
    p.add_argument("--skip-diagnostics", action="store_true")
    return p


def main() -> None:
    args = build_arg_parser().parse_args()
    cfg = JoinConfig(
        base_zip=Path(args.base_zip),
        base_csv_name=args.base_csv_name,
        carto_parquet=Path(args.carto_parquet),
        zonas777_shp=Path(args.zonas777_shp),
        out_dir=Path(args.out_dir),
        use_centroid=not args.no_centroid,
        compute_intersects=not args.skip_diagnostics,
    )
    df_agg, diag = run(cfg)
    print("OK rows:", len(df_agg))
    if diag:
        print("Diagnostics:", diag)


if __name__ == "__main__":
    main()
