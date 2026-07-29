"""Choropleth interactivo: composición BIP/QR por zona de residencia, 2024 vs 2025.

EDA del pivote a nivel zona. Mapa Leaflet (folium) con tres capas toggleables:
  - share de tarjetas QR por zona777 en 2024,
  - idem 2025 (misma escala de color que 2024, para comparar),
  - delta (2025 - 2024), escala divergente centrada en 0.

NOTAS DE DISEÑO (acordadas 2026-06-15):
  - Ventana = W14-W17 de cada año (scope interannual_ml), igual que el
    diagnóstico, así que REUSA su CSV y los números coinciden exactos. No
    recomputa nada.
  - Composición = share de tarjetas QR-type (tipo_tarjeta es FIJO por tarjeta;
    el cambio entre años es composicional, entran/salen tarjetas, no
    conversión). Ver memoria adopcion_qr_por_zona_diagnostico.
  - Zonas con menos de --min-n tarjetas en el año se pintan en gris ("dato
    insuficiente") y se excluyen del rango de color, para no dejar que zonas
    chicas con tasas 0/1 dominen la escala.

Insumos:
  - CSV del diagnóstico: <OUT_DIR>/qr_adoption_by_residence_zone_<universo>.csv
    (córrelo antes con qr_adoption_by_residence_zone.py si no existe).
  - Shapefile ZONA777 (mismo que usa el resto del repo).

Salida:
  - <OUT_DIR>/qr_composition_choropleth_<universo>.html

Uso:
    python scripts/audits/qr_composition_choropleth.py
    python scripts/audits/qr_composition_choropleth.py --home-filter alta --min-n 30
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_user_level_payment_panel import OUT_DIR, ZONAS777_SHP  # noqa: E402


def robust_range(values: np.ndarray, lo_pct: float = 2, hi_pct: float = 98) -> tuple[float, float]:
    v = values[~np.isnan(values)]
    if v.size == 0:
        return 0.0, 1.0
    return float(np.percentile(v, lo_pct)), float(np.percentile(v, hi_pct))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home-filter", default="alta", help="universo del CSV del diagnóstico")
    ap.add_argument("--min-n", type=int, default=30, help="mín. tarjetas/zona-año para colorear")
    args = ap.parse_args()

    import branca.colormap as cm
    import folium
    import geopandas as gpd
    import pandas as pd

    out_dir = Path(OUT_DIR)
    csv_path = out_dir / f"qr_adoption_by_residence_zone_{args.home_filter}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"No existe el CSV del diagnóstico: {csv_path}\n"
            "Córrelo primero:\n"
            f"    python scripts/audits/qr_adoption_by_residence_zone.py --home-filter {args.home_filter}"
        )
    rates = pd.read_csv(csv_path)

    # --- geometría ZONA777 ---
    if not ZONAS777_SHP.exists():
        raise FileNotFoundError(
            f"No existe el shapefile ZONA777 (¿disco externo montado?): {ZONAS777_SHP}"
        )
    cols = ["ZONA777", "geometry"]
    gdf_raw = gpd.read_file(ZONAS777_SHP)
    for extra in ("COMUNA", "MACROZONA", "NMACROZONA"):
        if extra in gdf_raw.columns:
            cols.insert(-1, extra)
    gdf = gdf_raw[cols].copy()
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)
    gdf = gdf.dissolve(by="ZONA777", as_index=False, aggfunc="first")
    # Convención del repo: shapefile sin CRS -> EPSG:4674 (SIRGAS 2000).
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    gdf = gdf.to_crs(epsg=4326)  # folium/Leaflet trabaja en lon/lat WGS84

    gdf = gdf.merge(rates, left_on="ZONA777", right_on="zona_hogar", how="left")

    # --- columnas de color ---
    # Enmascarar zonas con poca muestra (rate ruidoso) en cada año.
    rate24 = np.where(gdf["n_cards_2024"].fillna(0) >= args.min_n, gdf["qr_rate_2024"], np.nan)
    rate25 = np.where(gdf["n_cards_2025"].fillna(0) >= args.min_n, gdf["qr_rate_2025"], np.nan)
    delta_mask = (gdf["n_cards_2024"].fillna(0) >= args.min_n) & (
        gdf["n_cards_2025"].fillna(0) >= args.min_n
    )
    delta = np.where(delta_mask, gdf["delta"], np.nan)
    gdf["rate24"] = rate24
    gdf["rate25"] = rate25
    gdf["delta_m"] = delta

    # Escala COMPARTIDA para 2024 y 2025 (mismo rango -> comparables a ojo).
    levels = np.concatenate([rate24, rate25])
    vmin, vmax = robust_range(levels)
    cmap_levels = cm.LinearColormap(
        ["#fff5eb", "#fd8d3c", "#7f2704"], vmin=vmin, vmax=vmax,
        caption="Share de tarjetas QR (2024 y 2025, escala compartida)",
    )
    # Escala divergente y simétrica para el delta.
    dabs = np.nanpercentile(np.abs(delta), 98) if np.any(~np.isnan(delta)) else 0.1
    dabs = max(dabs, 1e-6)
    cmap_delta = cm.LinearColormap(
        ["#2166ac", "#f7f7f7", "#b2182b"], vmin=-dabs, vmax=dabs,
        caption="Delta share QR (2025 - 2024)",
    )

    GRAY = "#d9d9d9"

    def color_for(value, cmap):
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return GRAY
        return cmap(value)

    gdf["color_2024"] = [color_for(v, cmap_levels) for v in gdf["rate24"]]
    gdf["color_2025"] = [color_for(v, cmap_levels) for v in gdf["rate25"]]
    gdf["color_delta"] = [color_for(v, cmap_delta) for v in gdf["delta_m"]]

    # Strings legibles para tooltip.
    def pct(x):
        return "s/d" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x*100:.1f}%"

    gdf["t_2024"] = [pct(x) for x in gdf["qr_rate_2024"]]
    gdf["t_2025"] = [pct(x) for x in gdf["qr_rate_2025"]]
    gdf["t_delta"] = [
        "s/d" if (isinstance(x, float) and np.isnan(x)) else f"{x*100:+.1f} pp" for x in gdf["delta"]
    ]
    gdf["n24"] = gdf["n_cards_2024"].fillna(0).astype(int)
    gdf["n25"] = gdf["n_cards_2025"].fillna(0).astype(int)
    if "COMUNA" not in gdf.columns:
        gdf["COMUNA"] = ""

    # --- mapa ---
    # Solo las columnas necesarias para el GeoJson (evita serializar NaN/ruido).
    keep = [
        "geometry", "ZONA777", "COMUNA",
        "color_2024", "color_2025", "color_delta",
        "t_2024", "t_2025", "t_delta", "n24", "n25",
    ]
    gdf_plot = gdf[keep].copy()

    # Centroides en CRS proyectado (UTM 19S) para evitar el warning de
    # geometrías geográficas, luego de vuelta a lon/lat.
    cent = gdf_plot.to_crs(epsg=32719).geometry.centroid.to_crs(epsg=4326)
    center = [cent.y.mean(), cent.x.mean()]
    m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")

    def add_layer(name: str, color_col: str, tip_fields: list[str], tip_alias: list[str], show: bool):
        folium.GeoJson(
            gdf_plot,
            name=name,
            show=show,
            style_function=lambda feat, c=color_col: {
                "fillColor": feat["properties"][c],
                "color": "#666666",
                "weight": 0.3,
                "fillOpacity": 0.75,
            },
            highlight_function=lambda feat: {"weight": 2, "color": "black"},
            tooltip=folium.GeoJsonTooltip(fields=tip_fields, aliases=tip_alias, localize=True),
        ).add_to(m)

    add_layer(
        "Share QR 2024", "color_2024",
        ["ZONA777", "COMUNA", "t_2024", "n24"],
        ["Zona", "Comuna", "Share QR 2024", "n tarjetas 2024"],
        show=True,
    )
    add_layer(
        "Share QR 2025", "color_2025",
        ["ZONA777", "COMUNA", "t_2025", "n25"],
        ["Zona", "Comuna", "Share QR 2025", "n tarjetas 2025"],
        show=False,
    )
    add_layer(
        "Delta 2025-2024", "color_delta",
        ["ZONA777", "COMUNA", "t_delta", "t_2024", "t_2025"],
        ["Zona", "Comuna", "Delta", "QR 2024", "QR 2025"],
        show=False,
    )

    cmap_levels.add_to(m)
    cmap_delta.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    n_gris_24 = int(np.isnan(rate24).sum())
    title = (
        f"<div style='position:fixed;top:10px;left:60px;z-index:9999;background:white;"
        f"padding:6px 10px;border:1px solid #999;border-radius:4px;font-family:sans-serif;"
        f"font-size:12px'><b>Composición QR por zona de residencia</b><br>"
        f"Universo home_{args.home_filter} · ventana W14-W17 · gris = n&lt;{args.min_n} "
        f"({n_gris_24} zonas en 2024)</div>"
    )
    m.get_root().html.add_child(folium.Element(title))

    out_html = out_dir / f"qr_composition_choropleth_{args.home_filter}.html"
    m.save(str(out_html))
    print(f"Zonas en el mapa : {len(gdf)}")
    print(f"Rango color niveles (p2-p98): [{vmin:.3f}, {vmax:.3f}]")
    print(f"Delta |p98| simétrico: ±{dabs:.3f}")
    print(f"HTML guardado en : {out_html}")


if __name__ == "__main__":
    main()
