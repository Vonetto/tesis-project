from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(__file__).resolve().parents[2] / ".matplotlib-cache"),
)
os.environ.setdefault(
    "XDG_CACHE_HOME",
    str(Path(__file__).resolve().parents[2] / ".cache"),
)

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
import pandas as pd
import polars as pl
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_PATH = (
    PROJECT_ROOT
    / "03_models"
    / "artifacts"
    / "interannual_enriched"
    / "pooled_2024_2025-estimation-sample5pct-censo4-micro-osm-eod2012.parquet"
)
ZONAS777_SHP = Path(
    "/Volumes/KINGSTON/tesis-project/raw/zonas777/"
    "Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp"
)
OUT_DIR = PROJECT_ROOT / "docs" / "thesis" / "figures" / "payment_adoption_maps"
MIN_ZONE_TRIPS = 50


MAP_SPECS = [
    {
        "column": "share_qr_red",
        "title": "Share QR_RED",
        "filename": "zona777_share_qr_red_sample5pct.png",
        "cmap": "YlOrRd",
    },
    {
        "column": "share_qr_other",
        "title": "Share QR_OTHER",
        "filename": "zona777_share_qr_other_sample5pct.png",
        "cmap": "PuBuGn",
    },
    {
        "column": "share_digital",
        "title": "Share digital (QR_RED + QR_OTHER)",
        "filename": "zona777_share_digital_sample5pct.png",
        "cmap": "BuPu",
    },
]

BIVARIATE_COLORS = {
    (0, 0): "#f2f2f2",
    (1, 0): "#f6b6a6",
    (2, 0): "#e34a33",
    (0, 1): "#b7d4ea",
    (1, 1): "#b58cc8",
    (2, 1): "#88419d",
    (0, 2): "#2b8cbe",
    (1, 2): "#6a51a3",
    (2, 2): "#3f007d",
}


def _validate_inputs() -> None:
    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(f"No existe sample: {SAMPLE_PATH}")
    if not ZONAS777_SHP.exists():
        raise FileNotFoundError(f"No existe shapefile ZONA777: {ZONAS777_SHP}")


def build_zone_payment_shares() -> pd.DataFrame:
    # Also pull territorial covariates that exist in the sample parquet (already _z suffix).
    df = (
        pl.scan_parquet(SAMPLE_PATH)
        .select(
            [
                pl.col("zona_inicio_viaje").cast(pl.Int64).alias("ZONA777"),
                pl.col("choice_nested").cast(pl.Int64),
                pl.col("prom_escolaridad18_z"),
                pl.col("share_cine18_universitaria_o_mas_micro_z"),
            ]
        )
        .group_by("ZONA777")
        .agg(
            [
                pl.len().alias("n_trips"),
                (pl.col("choice_nested") == 0).sum().alias("n_bip"),
                (pl.col("choice_nested") == 1).sum().alias("n_qr_red"),
                (pl.col("choice_nested") == 2).sum().alias("n_qr_other"),
                pl.col("prom_escolaridad18_z").mean().alias("prom_escolaridad18_z"),
                pl.col("share_cine18_universitaria_o_mas_micro_z").mean().alias(
                    "share_cine18_universitaria_o_mas_micro_z"
                ),
            ]
        )
        .with_columns(
            [
                (pl.col("n_qr_red") / pl.col("n_trips")).alias("share_qr_red"),
                (pl.col("n_qr_other") / pl.col("n_trips")).alias("share_qr_other"),
                ((pl.col("n_qr_red") + pl.col("n_qr_other")) / pl.col("n_trips")).alias(
                    "share_digital"
                ),
            ]
        )
        .sort("ZONA777")
        .collect()
    )
    return df.to_pandas()


def load_zone_geometries() -> gpd.GeoDataFrame:
    gdf = gpd.read_file(ZONAS777_SHP)[
        ["ZONA777", "NMACROZONA", "MACROZONA", "COMUNA", "geometry"]
    ].copy()
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    if gdf["ZONA777"].duplicated().any():
        gdf = gdf.dissolve(by="ZONA777", as_index=False)
    gdf["ZONA777"] = pd.to_numeric(gdf["ZONA777"], errors="raise").astype("int64")
    return gdf


def make_map_data() -> gpd.GeoDataFrame:
    shares = build_zone_payment_shares()
    shares_path = OUT_DIR / "zona777_payment_shares_sample5pct.csv"
    shares.to_csv(shares_path, index=False)

    gdf = load_zone_geometries().merge(shares, on="ZONA777", how="left")
    gdf["is_low_n_or_missing"] = gdf["n_trips"].fillna(0) < MIN_ZONE_TRIPS
    return gdf


def _plot_single_map(
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str,
    cmap: str,
    ax: plt.Axes,
    extent_gdf: gpd.GeoDataFrame | None = None,
) -> None:
    plot_gdf = gdf.loc[~gdf["is_low_n_or_missing"]].copy()
    low_n_gdf = gdf.loc[gdf["is_low_n_or_missing"]].copy()
    vmax = float(plot_gdf[column].quantile(0.99))
    vmax = max(vmax, 0.01)

    low_n_gdf.plot(ax=ax, color="#eeeeee", edgecolor="#ffffff", linewidth=0.15)
    plot_gdf.plot(
        ax=ax,
        column=column,
        cmap=cmap,
        vmin=0,
        vmax=vmax,
        edgecolor="#ffffff",
        linewidth=0.12,
        legend=False,
    )
    gdf.boundary.plot(ax=ax, color="#4d4d4d", linewidth=0.08, alpha=0.35)

    sm = ScalarMappable(norm=Normalize(vmin=0, vmax=vmax), cmap=cmap)
    sm.set_array([])
    cbar = ax.figure.colorbar(sm, ax=ax, fraction=0.036, pad=0.01)
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter(xmax=1.0))
    cbar.ax.tick_params(labelsize=8)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=8)
    ax.set_axis_off()
    ax.set_aspect("equal")
    if extent_gdf is not None and not extent_gdf.empty:
        xmin, ymin, xmax, ymax = extent_gdf.total_bounds
        xpad = (xmax - xmin) * 0.08
        ypad = (ymax - ymin) * 0.08
        ax.set_xlim(xmin - xpad, xmax + xpad)
        ax.set_ylim(ymin - ypad, ymax + ypad)


def save_three_panel_map(gdf: gpd.GeoDataFrame) -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=False)
    for ax, spec in zip(axes, MAP_SPECS, strict=True):
        _plot_single_map(
            gdf,
            column=spec["column"],
            title=spec["title"],
            cmap=spec["cmap"],
            ax=ax,
        )
    fig.suptitle(
        "Adopcion observada de medios de pago digitales por zona de origen (ZONA777)",
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )
    fig.text(
        0.01,
        0.02,
        (
            "Fuente: muestra pooled 2024-2025 5%. "
            f"Zonas en gris: menos de {MIN_ZONE_TRIPS} viajes en la muestra. "
            "Escalas de color independientes por panel."
        ),
        fontsize=9,
        color="#444444",
    )
    fig.subplots_adjust(left=0.01, right=0.98, top=0.84, bottom=0.12, wspace=0.12)
    out = OUT_DIR / "zona777_payment_share_maps_3panel_sample5pct.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def save_oriente_zoom_map(gdf: gpd.GeoDataFrame) -> Path:
    oriente = gdf.loc[gdf["MACROZONA"].astype(str).str.upper() == "ORIENTE"].copy()
    if oriente.empty:
        raise ValueError("No se encontraron zonas con MACROZONA == ORIENTE")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=False)
    for ax, spec in zip(axes, MAP_SPECS, strict=True):
        _plot_single_map(
            gdf,
            column=spec["column"],
            title=spec["title"],
            cmap=spec["cmap"],
            ax=ax,
            extent_gdf=oriente,
        )
        oriente.boundary.plot(ax=ax, color="#111111", linewidth=0.35, alpha=0.9)

    fig.suptitle(
        "Zoom Macrozona Oriente: adopcion observada de medios de pago digitales",
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )
    fig.text(
        0.01,
        0.02,
        (
            "Fuente: muestra pooled 2024-2025 5%. "
            f"Zonas en gris: menos de {MIN_ZONE_TRIPS} viajes en la muestra. "
            "Contorno negro: zonas clasificadas como Macrozona Oriente."
        ),
        fontsize=9,
        color="#444444",
    )
    fig.subplots_adjust(left=0.01, right=0.98, top=0.84, bottom=0.12, wspace=0.12)
    out = OUT_DIR / "zona777_payment_share_maps_3panel_oriente_zoom_sample5pct.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def _quantile_class(series: pd.Series, quantiles: tuple[float, float]) -> pd.Series:
    q1, q2 = quantiles
    return pd.cut(
        series,
        bins=[-float("inf"), q1, q2, float("inf")],
        labels=[0, 1, 2],
        include_lowest=True,
    ).astype("Int64")


def _add_bivariate_legend(
    fig: plt.Figure,
    title: str,
    qr_red_labels: tuple[str, str, str],
    qr_other_labels: tuple[str, str, str],
    xlabel: str = "QR_RED",
    ylabel: str = "QR_OTHER",
) -> None:
    legend_ax = fig.add_axes([0.75, 0.18, 0.14, 0.24])
    for i in range(3):
        for j in range(3):
            legend_ax.add_patch(
                plt.Rectangle(
                    (i, j),
                    1,
                    1,
                    facecolor=BIVARIATE_COLORS[(i, j)],
                    edgecolor="#ffffff",
                    linewidth=1.0,
                )
            )
    legend_ax.set_xlim(0, 3)
    legend_ax.set_ylim(0, 3)
    legend_ax.set_xticks([0.5, 1.5, 2.5])
    legend_ax.set_yticks([0.5, 1.5, 2.5])
    legend_ax.set_xticklabels(qr_red_labels, fontsize=8)
    legend_ax.set_yticklabels(qr_other_labels, fontsize=8)
    legend_ax.set_xlabel(xlabel, fontsize=9, fontweight="bold")
    legend_ax.set_ylabel(ylabel, fontsize=9, fontweight="bold")
    legend_ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    legend_ax.tick_params(length=0)
    for spine in legend_ax.spines.values():
        spine.set_visible(False)


def save_oriente_bivariate_qr_map(gdf: gpd.GeoDataFrame) -> Path:
    oriente = gdf.loc[gdf["MACROZONA"].astype(str).str.upper() == "ORIENTE"].copy()
    if oriente.empty:
        raise ValueError("No se encontraron zonas con MACROZONA == ORIENTE")

    valid = oriente.loc[~oriente["is_low_n_or_missing"]].copy()
    qr_red_q = tuple(valid["share_qr_red"].quantile([1 / 3, 2 / 3]).to_numpy())
    qr_other_q = tuple(valid["share_qr_other"].quantile([1 / 3, 2 / 3]).to_numpy())

    bivar = gdf.copy()
    bivar["qr_red_class"] = _quantile_class(bivar["share_qr_red"], qr_red_q)
    bivar["qr_other_class"] = _quantile_class(bivar["share_qr_other"], qr_other_q)
    bivar["bivar_color"] = [
        BIVARIATE_COLORS.get((int(r), int(o)), "#eeeeee")
        if not pd.isna(r) and not pd.isna(o) and not low_n
        else "#eeeeee"
        for r, o, low_n in zip(
            bivar["qr_red_class"],
            bivar["qr_other_class"],
            bivar["is_low_n_or_missing"],
            strict=True,
        )
    ]

    fig, ax = plt.subplots(1, 1, figsize=(11.0, 8.5), constrained_layout=False)
    bivar.plot(ax=ax, color=bivar["bivar_color"], edgecolor="#ffffff", linewidth=0.12)
    oriente.boundary.plot(ax=ax, color="#111111", linewidth=0.45, alpha=0.9)
    xmin, ymin, xmax, ymax = oriente.total_bounds
    xpad = (xmax - xmin) * 0.08
    ypad = (ymax - ymin) * 0.08
    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(ymin - ypad, ymax + ypad)
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_title(
        "Zoom Oriente: composicion de adopcion QR por zona de origen",
        fontsize=15,
        fontweight="bold",
        pad=12,
    )
    fig.text(
        0.02,
        0.05,
        (
            "Mapa bivariado con terciles calculados sobre zonas de Oriente con "
            f"al menos {MIN_ZONE_TRIPS} viajes. Gris: baja muestra o sin viajes."
        ),
        fontsize=9,
        color="#444444",
    )
    fig.text(
        0.02,
        0.025,
        (
            "Lectura: rojo = mayor QR_RED relativo; azul = mayor QR_OTHER relativo; "
            "morado oscuro = ambos altos."
        ),
        fontsize=9,
        color="#444444",
    )
    _add_bivariate_legend(
        fig,
        "Terciles",
        qr_red_labels=("bajo", "medio", "alto"),
        qr_other_labels=("bajo", "medio", "alto"),
    )
    out = OUT_DIR / "zona777_bivariate_qr_red_qr_other_oriente_zoom_sample5pct.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def save_full_bivariate_qr_map(gdf: gpd.GeoDataFrame) -> Path:
    valid = gdf.loc[~gdf["is_low_n_or_missing"]].copy()
    qr_red_q = tuple(valid["share_qr_red"].quantile([1 / 3, 2 / 3]).to_numpy())
    qr_other_q = tuple(valid["share_qr_other"].quantile([1 / 3, 2 / 3]).to_numpy())

    bivar = gdf.copy()
    bivar["qr_red_class"] = _quantile_class(bivar["share_qr_red"], qr_red_q)
    bivar["qr_other_class"] = _quantile_class(bivar["share_qr_other"], qr_other_q)
    bivar["bivar_color"] = [
        BIVARIATE_COLORS.get((int(r), int(o)), "#eeeeee")
        if not pd.isna(r) and not pd.isna(o) and not low_n
        else "#eeeeee"
        for r, o, low_n in zip(
            bivar["qr_red_class"],
            bivar["qr_other_class"],
            bivar["is_low_n_or_missing"],
            strict=True,
        )
    ]

    fig, ax = plt.subplots(1, 1, figsize=(11.0, 8.5), constrained_layout=False)
    bivar.plot(ax=ax, color=bivar["bivar_color"], edgecolor="#ffffff", linewidth=0.12)
    bivar.boundary.plot(ax=ax, color="#4d4d4d", linewidth=0.08, alpha=0.35)
    
    xmin, ymin, xmax, ymax = bivar.total_bounds
    xpad = (xmax - xmin) * 0.08
    ypad = (ymax - ymin) * 0.08
    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(ymin - ypad, ymax + ypad)
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_title(
        "Composición de adopción QR por zona de origen (toda RM)",
        fontsize=15,
        fontweight="bold",
        pad=12,
    )
    fig.text(
        0.02,
        0.05,
        (
            "Mapa bivariado con terciles calculados sobre todas las zonas con "
            f"al menos {MIN_ZONE_TRIPS} viajes. Gris: baja muestra o sin viajes."
        ),
        fontsize=9,
        color="#444444",
    )
    fig.text(
        0.02,
        0.025,
        (
            "Lectura: rojo = mayor QR_RED relativo; azul = mayor QR_OTHER relativo; "
            "morado oscuro = ambos altos."
        ),
        fontsize=9,
        color="#444444",
    )
    _add_bivariate_legend(
        fig,
        "Terciles",
        qr_red_labels=("bajo", "medio", "alto"),
        qr_other_labels=("bajo", "medio", "alto"),
    )
    out = OUT_DIR / "zona777_bivariate_qr_red_qr_other_full_sample5pct.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def save_full_bivariate_qr_vs_education_map(gdf: gpd.GeoDataFrame) -> Path:
    """Bivariado: share_qr_red vs proxy de capital educativo (share_cine18_universitaria_o_mas_micro_z)."""
    valid = gdf.loc[~gdf["is_low_n_or_missing"]].copy()
    qr_red_q = tuple(valid["share_qr_red"].quantile([1 / 3, 2 / 3]).to_numpy())
    edu_q = tuple(valid["share_cine18_universitaria_o_mas_micro_z"].quantile([1 / 3, 2 / 3]).to_numpy())

    bivar = gdf.copy()
    bivar["qr_red_class"] = _quantile_class(bivar["share_qr_red"], qr_red_q)
    bivar["edu_class"] = _quantile_class(
        bivar["share_cine18_universitaria_o_mas_micro_z"], edu_q
    )
    bivar["bivar_color"] = [
        BIVARIATE_COLORS.get((int(r), int(e)), "#eeeeee")
        if not pd.isna(r) and not pd.isna(e) and not low_n
        else "#eeeeee"
        for r, e, low_n in zip(
            bivar["qr_red_class"],
            bivar["edu_class"],
            bivar["is_low_n_or_missing"],
            strict=True,
        )
    ]

    fig, ax = plt.subplots(1, 1, figsize=(11.0, 8.5), constrained_layout=False)
    bivar.plot(ax=ax, color=bivar["bivar_color"], edgecolor="#ffffff", linewidth=0.12)
    gdf.boundary.plot(ax=ax, color="#4d4d4d", linewidth=0.08, alpha=0.35)

    xmin, ymin, xmax, ymax = gdf.total_bounds
    xpad = (xmax - xmin) * 0.08
    ypad = (ymax - ymin) * 0.08
    ax.set_xlim(xmin - xpad, xmax + xpad)
    ax.set_ylim(ymin - ypad, ymax + ypad)
    ax.set_axis_off()
    ax.set_aspect("equal")
    ax.set_title(
        "Composición QR_RED vs capital educativo (ZONA777)",
        fontsize=15,
        fontweight="bold",
        pad=12,
    )
    fig.text(
        0.02,
        0.05,
        (
            "Mapa bivariado: terciles de `share_qr_red` (x) y proporción universitaria (y). "
            f"Solo zonas con ≥ {MIN_ZONE_TRIPS} viajes muestran valores. Gris: baja muestra o sin viajes."
        ),
        fontsize=9,
        color="#444444",
    )
    _add_bivariate_legend(
        fig,
        "Terciles",
        qr_red_labels=("bajo", "medio", "alto"),
        qr_other_labels=("bajo", "medio", "alto"),
        xlabel="QR_RED",
        ylabel="Share univ. (18+)",
    )
    out = OUT_DIR / "zona777_bivariate_qr_red_edu_full_sample5pct.png"
    fig.savefig(out, dpi=220, bbox_inches="tight")
    plt.close(fig)
    return out


def save_individual_maps(gdf: gpd.GeoDataFrame) -> list[Path]:
    outputs = []
    for spec in MAP_SPECS:
        fig, ax = plt.subplots(1, 1, figsize=(6.2, 7.2), constrained_layout=True)
        _plot_single_map(
            gdf,
            column=spec["column"],
            title=spec["title"],
            cmap=spec["cmap"],
            ax=ax,
        )
        fig.text(
            0.01,
            0.01,
            (
                "Fuente: muestra pooled 2024-2025 5%. "
                f"Gris: menos de {MIN_ZONE_TRIPS} viajes."
            ),
            fontsize=8,
            color="#444444",
        )
        out = OUT_DIR / spec["filename"]
        fig.savefig(out, dpi=220, bbox_inches="tight")
        plt.close(fig)
        outputs.append(out)
    return outputs


def save_readme(outputs: list[Path]) -> None:
    readme = OUT_DIR / "README.md"
    lines = [
        "# Mapas de adopcion de medios de pago digitales",
        "",
        "Artefactos generados desde `scripts/figures/make_payment_adoption_maps.py`.",
        "",
        "Fuente de datos:",
        f"- Sample: `{SAMPLE_PATH.relative_to(PROJECT_ROOT)}`",
        f"- Geometria: `{ZONAS777_SHP}`",
        "",
        "Definiciones:",
        "- `share_qr_red = n(choice_nested == 1) / n_trips`.",
        "- `share_qr_other = n(choice_nested == 2) / n_trips`.",
        "- `share_digital = share_qr_red + share_qr_other`.",
        f"- Zonas grises: menos de {MIN_ZONE_TRIPS} viajes en la muestra.",
        "",
        "Outputs:",
        *[f"- `{p.name}`" for p in outputs],
        "- `zona777_payment_shares_sample5pct.csv`",
        "",
    ]
    readme.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _validate_inputs()
    gdf = make_map_data()
    outputs = [
        save_three_panel_map(gdf),
        save_oriente_zoom_map(gdf),
        save_oriente_bivariate_qr_map(gdf),
        save_full_bivariate_qr_map(gdf),
        save_full_bivariate_qr_vs_education_map(gdf),
        *save_individual_maps(gdf),
    ]
    save_readme(outputs)
    print("Outputs:")
    for output in outputs:
        print(output)
    print(OUT_DIR / "zona777_payment_shares_sample5pct.csv")


if __name__ == "__main__":
    main()
