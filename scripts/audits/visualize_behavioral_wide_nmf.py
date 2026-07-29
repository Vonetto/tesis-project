"""Create visual review pack for behavioral_wide NMF outputs."""
from __future__ import annotations

import argparse
import html
import os
import sys
import textwrap
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns


SEG_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign" / "segmentation"
DEFAULT_MODEL_DIR = (
    SEG_DIR
    / "models"
    / "behavioral_wide"
    / "v0b_alta_n3__nmf_v0b_robust_minmax_block"
    / "nmf"
)

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
BLUE = {"xlight": "#EAF1FE", "light": "#CEDFFE", "base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780"}
GOLD = {"xlight": "#FFF4C2", "base": "#FFE15B", "mid": "#B8A037", "dark": "#736422"}
ORANGE = {"xlight": "#FFEDDE", "light": "#FFBDA1", "base": "#F0986E", "mid": "#CC6F47", "dark": "#804126"}
OLIVE = {"xlight": "#D8ECBD", "base": "#A3D576", "mid": "#71B436", "dark": "#386411"}
PINK = {"xlight": "#FCDAD6", "base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F"}


def setup_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "grid.color": TOKENS["grid"],
            "text.color": TOKENS["ink"],
            "font.family": ["Aptos", "Inter", "Segoe UI", "DejaVu Sans", "Arial", "sans-serif"],
            "axes.titleweight": "bold",
        }
    )


def add_header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.01, 0.98, title, ha="left", va="top", fontsize=15, fontweight="bold", color=TOKENS["ink"])
    fig.text(0.01, 0.94, subtitle, ha="left", va="top", fontsize=10, color=TOKENS["muted"])


def savefig(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=TOKENS["surface"])
    plt.close(fig)


FEATURE_LABELS = {
    "log1p_n_viajes": "log viajes",
    "rhythm_active_day_density_span": "densidad dias activos",
    "hora_mean": "hora_mean",
    "hora_std": "hora_std",
    "share_lab_pm": "share PM laboral",
    "share_lab_pt": "share punta laboral",
    "share_no_lab": "share no laboral",
    "log1p_rhythm_mean_gap_active_days": "log gap dias activos",
    "rhythm_mean_gap_active_days": "gap dias activos",
    "rhythm_daily_hhi": "concentracion diaria",
    "rhythm_single_trip_day_share": "dias 1 viaje",
    "rhythm_weekly_hhi": "concentracion semanal",
    "rhythm_weekly_entropy_norm": "entropia semanal",
    "share_trips_solo_bus": "solo bus",
    "share_trips_solo_metro": "solo metro",
    "share_trips_metro_bus": "metro + bus",
    "share_trips_with_transfer": "con transbordo",
    "share_trips_in_multi_route_od": "OD multi-ruta",
    "n_trasbordos_mean": "transbordos promedio",
    "origin_zone_top1_share": "zona origen principal",
    "origin_zone_entropy": "entropia origen",
    "activity_zone_top1_share": "zona actividad principal",
    "activity_zone_entropy": "entropia actividad",
    "routine_zone_n_unique": "zonas rutina distintas",
    "routine_zone_top1_usage_share": "zona rutina principal",
    "routine_zone_exploration_share": "exploracion zonas",
    "routine_od_top1_share": "OD rutina principal",
    "routine_od_hhi": "concentracion OD",
    "routine_main_od_share": "share OD principal",
    "routine_main_od_roundtrip_balance": "balance ida/vuelta OD",
    "routine_combo_top1_share": "combo rutina principal",
    "routine_combo_hhi": "concentracion combo",
    "routine_od_time_top1_share": "OD-hora principal",
    "routine_od_time_hhi": "concentracion OD-hora",
    "routine_od_time_entropy_norm": "entropia OD-hora",
    "routine_od_time_n_unique": "OD-hora distintos",
    "routine_lab_peak_share": "rutina punta laboral",
    "routine_commute_like_score": "score commute",
    "tour_two_trip_day_share": "dias 2 viajes",
    "tour_three_plus_trip_day_share": "dias 3+ viajes",
    "tour_complex_day_share": "dias complejos",
    "tour_closed_loop_day_share": "dias circuito cerrado",
    "tour_reciprocal_od_day_share": "dias OD reciproco",
    "tour_same_unordered_od_day_share": "dias mismo OD",
    "tour_mode_consistent_day_share": "dias modo unico",
    "tour_mixed_mode_day_share": "dias modo mixto",
    "tour_first_trip_lab_am_peak_share": "inicio AM laboral",
    "tour_last_trip_lab_pm_peak_share": "cierre PM laboral",
    "tour_peak_anchor_day_share": "dias anclaje punta",
    "tour_workday_commute_like_day_share": "dias commute laboral",
    "tour_distinct_zones_per_day_mean": "zonas por dia",
    "tour_distinct_zones_per_day_median": "zonas mediana",
    "tour_distinct_od_per_day_mean": "OD por dia",
    "tour_distinct_unordered_od_per_day_mean": "OD unord por dia",
    "tour_distinct_modes_per_day_mean": "modos por dia",
    "tour_day_span_hours_mean": "duracion dia",
    "tour_day_span_hours_median": "duracion mediana",
    "tour_first_trip_hour_mean": "hora primer viaje",
    "tour_last_trip_hour_mean": "hora ultimo viaje",
    "res_share_cine18_universitaria_o_mas_micro_z": "educacion superior hogar",
    "res_eod2012_share_hogares_de_income_proxy_z": "D+E proxy hogar",
    "res_share_discapacidad_z": "discapacidad hogar",
    "res_share_inmigrantes_z": "inmigrantes hogar",
    "res_share_asistencia_parv_z": "asistencia parvularia",
    "res_age_share_18_24": "edad 18-24 hogar",
    "res_age_share_25_44": "edad 25-44 hogar",
    "home_macro_norte": "hogar macro norte",
    "home_macro_poniente": "hogar macro poniente",
    "home_macro_oriente": "hogar macro oriente",
    "home_macro_centro": "hogar macro centro",
    "home_macro_sur": "hogar macro sur",
    "home_macro_suroriente": "hogar macro suroriente",
    "home_macro_externa_especial": "hogar macro externa",
    "home_bip_load_density_km2": "carga BIP hogar",
    "home_bip_load_dist_nearest_m": "distancia BIP hogar",
    "origin_top1_bip_load_density_km2": "carga BIP origen",
    "origin_top1_bip_load_dist_nearest_m": "distancia BIP origen",
    "offer_log_bus_stop_density_origin_mean": "densidad paraderos",
    "offer_log_metro_station_density_origin_mean": "densidad metro",
    "offer_origin_bus_like_share": "oferta bus origen",
    "offer_origin_metro_like_share": "oferta metro origen",
    "offer_bus_origin_headway_all_min_mean": "headway bus origen",
    "offer_bus_origin_headway_ge10_share": "headway bus ge10",
    "origin_top1_osm_amenity_school_density_km2_z": "colegios entorno origen",
    "origin_top1_osm_amenity_university_density_km2_z": "universidades entorno origen",
    "origin_top1_osm_transport_shelter_yes_density_km2_z": "refugios entorno origen",
    "origin_top1_osm_railway_subway_entrance_density_km2_z": "entradas metro entorno",
}


def feature_label(name: str) -> str:
    return FEATURE_LABELS.get(name, name.replace("_", " "))


def short_feature(name: str) -> str:
    return "\n".join(textwrap.wrap(feature_label(name), width=16))


def plot_model_selection(metrics: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    add_header(
        fig,
        "Seleccion de modelo NMF: k=4 es el candidato no supervisado",
        "behavioral_wide v0b, minmax robusto + ponderacion por bloque; muestra de ajuste n=300k, 5 semillas por k.",
    )
    axes[0].plot(metrics["k"], metrics["relative_best_reconstruction_error"], marker="o", color=BLUE["mid"])
    axes[0].axvline(4, color=TOKENS["muted"], ls="--", lw=1)
    axes[0].set_title("La reconstruccion mejora con k")
    axes[0].set_xlabel("k")
    axes[0].set_ylabel("Error relativo de reconstruccion")
    axes[0].yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))

    axes[1].plot(metrics["k"], metrics["stability_pairwise_ari_mean"], marker="o", color=OLIVE["mid"])
    axes[1].axvline(4, color=TOKENS["muted"], ls="--", lw=1)
    axes[1].set_title("La estabilidad cae despues de k=4")
    axes[1].set_xlabel("k")
    axes[1].set_ylabel("ARI entre semillas")
    axes[1].set_ylim(0, max(0.95, metrics["stability_pairwise_ari_mean"].max() + 0.05))

    axes[2].plot(metrics["k"], metrics["full_min_segment_share"], marker="o", color=ORANGE["mid"], label="min")
    axes[2].plot(metrics["k"], metrics["full_max_segment_share"], marker="o", color=ORANGE["light"], label="max")
    axes[2].axvline(4, color=TOKENS["muted"], ls="--", lw=1)
    axes[2].set_title("Los segmentos se fragmentan con k alto")
    axes[2].set_xlabel("k")
    axes[2].set_ylabel("Participacion en el universo")
    axes[2].yaxis.set_major_formatter(mticker.PercentFormatter(1))
    axes[2].legend(frameon=False, loc="upper right")
    for ax in axes:
        ax.grid(axis="y", alpha=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    savefig(fig, out_path)


def plot_qr_lifts(qr: pd.DataFrame, k: int, out_path: Path, title_suffix: str) -> None:
    data = qr.loc[qr["k"] == k].copy()
    long = data.melt(
        id_vars=["segment", "segment_share"],
        value_vars=["qr_lift_vs_base", "qr_red_lift_vs_base", "qr_other_lift_vs_base"],
        var_name="metric",
        value_name="lift",
    )
    metric_labels = {
        "qr_lift_vs_base": "QR",
        "qr_red_lift_vs_base": "QR_RED",
        "qr_other_lift_vs_base": "QR_OTHER",
    }
    long["metric"] = long["metric"].map(metric_labels)
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    add_header(
        fig,
        f"Indices QR por segmento NMF ({title_suffix})",
        "Indice respecto a la tasa base del universo; QR es post-hoc y no se uso para elegir k.",
    )
    sns.barplot(
        data=long,
        x="segment",
        y="lift",
        hue="metric",
        palette={"QR": BLUE["base"], "QR_RED": ORANGE["base"], "QR_OTHER": OLIVE["base"]},
        edgecolor=TOKENS["axis"],
        ax=ax,
    )
    ax.axhline(1.0, color=TOKENS["muted"], lw=1, ls="--")
    ax.set_xlabel("Segmento")
    ax.set_ylabel("Indice vs base")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.legend(title="", frameon=False, ncol=3, loc="upper left")
    for i, row in data.iterrows():
        ax.text(
            int(row["segment"]),
            0.04,
            f"{row['segment_share']:.1%}",
            ha="center",
            va="bottom",
            fontsize=9,
            color=TOKENS["muted"],
        )
    ax.spines[["top", "right"]].set_visible(False)
    savefig(fig, out_path)


def plot_component_heatmap(top: pd.DataFrame, k: int, out_path: Path) -> None:
    data = top.loc[top["k"] == k].copy()
    selected = (
        data.sort_values(["component", "rank"])
        .groupby("component")
        .head(6)["feature"]
        .drop_duplicates()
        .tolist()
    )
    pivot = (
        data.loc[data["feature"].isin(selected)]
        .pivot_table(index="component", columns="feature", values="weight_share_component", aggfunc="sum")
        .fillna(0.0)
    )
    pivot = pivot[selected]
    fig, ax = plt.subplots(figsize=(14, 5.8))
    add_header(
        fig,
        "Composicion de cada componente k=4",
        "Las celdas muestran la participacion de cada variable dentro de los pesos del componente.",
    )
    sns.heatmap(
        pivot,
        cmap=sns.light_palette(BLUE["mid"], as_cmap=True),
        linewidths=0.5,
        linecolor=TOKENS["grid"],
        cbar_kws={"label": "Participacion en pesos"},
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("Componente")
    ax.set_xticklabels([short_feature(c) for c in pivot.columns], rotation=45, ha="right")
    savefig(fig, out_path)


def plot_segment_profile_heatmap(profile: pd.DataFrame, k: int, out_path: Path, title_suffix: str) -> None:
    data = profile.loc[profile["k"] == k].copy()
    data["pct_delta"] = data["mean_lift"] - 1.0
    selected = (
        data.assign(abs_delta=lambda d: d["pct_delta"].abs())
        .sort_values(["segment", "abs_delta"], ascending=[True, False])
        .groupby("segment")
        .head(5)["feature"]
        .drop_duplicates()
        .tolist()
    )
    pivot = (
        data.loc[data["feature"].isin(selected)]
        .pivot_table(index="segment", columns="feature", values="pct_delta", aggfunc="first")
        .fillna(0.0)
    )
    pivot = pivot[selected].clip(-1.0, 1.5)
    fig, ax = plt.subplots(figsize=(15, 5.8))
    add_header(
        fig,
        f"Como difieren los segmentos {title_suffix} del universo",
        "El mapa muestra el indice medio menos 1.0; los valores se recortan a [-100%, +150%] para legibilidad.",
    )
    cmap = sns.diverging_palette(240, 30, s=70, l=55, center="light", as_cmap=True)
    sns.heatmap(
        pivot,
        cmap=cmap,
        center=0,
        vmin=-1,
        vmax=1.5,
        linewidths=0.5,
        linecolor=TOKENS["grid"],
        cbar_kws={"label": "Indice medio - 1"},
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("Segmento")
    ax.set_xticklabels([short_feature(c) for c in pivot.columns], rotation=45, ha="right")
    savefig(fig, out_path)


def plot_binary_qr_lifts(binary_qr: pd.DataFrame, k: int, out_path: Path, title_suffix: str) -> None:
    data = binary_qr.loc[binary_qr["k"] == k].copy()
    long = data.melt(
        id_vars=["segment", "segment_share"],
        value_vars=["qr_lift_vs_base", "bip_lift_vs_base"],
        var_name="metric",
        value_name="lift",
    )
    long["metric"] = long["metric"].map(
        {
            "qr_lift_vs_base": "QR",
            "bip_lift_vs_base": "BIP",
        }
    )
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    add_header(
        fig,
        f"Indices binarios QR vs BIP por segmento NMF ({title_suffix})",
        "Indice respecto a la tasa base del universo; QR/BIP es post-hoc y no se uso para elegir k.",
    )
    sns.barplot(
        data=long,
        x="segment",
        y="lift",
        hue="metric",
        palette={"QR": BLUE["base"], "BIP": GOLD["base"]},
        edgecolor=TOKENS["axis"],
        ax=ax,
    )
    ax.axhline(1.0, color=TOKENS["muted"], lw=1, ls="--")
    ax.set_xlabel("Segmento")
    ax.set_ylabel("Indice vs base")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    ax.legend(title="", frameon=False, ncol=2, loc="upper left")
    for _, row in data.iterrows():
        ax.text(
            int(row["segment"]),
            0.04,
            f"{row['segment_share']:.1%}",
            ha="center",
            va="bottom",
            fontsize=9,
            color=TOKENS["muted"],
        )
    ax.spines[["top", "right"]].set_visible(False)
    savefig(fig, out_path)


def plot_qr_vs_bip_feature_diff_heatmap(diff: pd.DataFrame, k: int, out_path: Path, title_suffix: str) -> None:
    data = diff.loc[diff["k"] == k].copy()
    data = data.replace([np.inf, -np.inf], np.nan).dropna(subset=["qr_vs_bip_lift_minus_1"])
    selected = (
        data.sort_values(["segment", "abs_qr_vs_bip_lift_minus_1"], ascending=[True, False])
        .groupby("segment")
        .head(5)["feature"]
        .drop_duplicates()
        .tolist()
    )
    pivot = (
        data.loc[data["feature"].isin(selected)]
        .pivot_table(index="segment", columns="feature", values="qr_vs_bip_lift_minus_1", aggfunc="first")
        .fillna(0.0)
    )
    pivot = pivot[selected].clip(-1.0, 1.5)
    fig, ax = plt.subplots(figsize=(15, 5.8))
    add_header(
        fig,
        f"Diferencias conductuales QR vs BIP dentro de segmento ({title_suffix})",
        "Valores positivos indican que usuarios QR tienen mayor promedio de la variable que usuarios BIP del mismo segmento.",
    )
    cmap = sns.diverging_palette(240, 30, s=70, l=55, center="light", as_cmap=True)
    sns.heatmap(
        pivot,
        cmap=cmap,
        center=0,
        vmin=-1,
        vmax=1.5,
        linewidths=0.5,
        linecolor=TOKENS["grid"],
        cbar_kws={"label": "Indice medio QR/BIP - 1"},
        ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel("Segmento")
    ax.set_xticklabels([short_feature(c) for c in pivot.columns], rotation=45, ha="right")
    savefig(fig, out_path)


def build_binary_qr_summary(qr: pd.DataFrame) -> pd.DataFrame:
    out = qr.copy()
    base_qr = out["qr_rate"] / out["qr_lift_vs_base"]
    out["base_qr_rate"] = base_qr
    out["bip_rate"] = 1.0 - out["qr_rate"]
    out["base_bip_rate"] = 1.0 - out["base_qr_rate"]
    out["bip_lift_vs_base"] = out["bip_rate"] / out["base_bip_rate"]
    base_odds = out["base_qr_rate"] / out["base_bip_rate"]
    segment_odds = out["qr_rate"] / out["bip_rate"]
    out["qr_vs_bip_odds_ratio_vs_base"] = segment_odds / base_odds
    return out[
        [
            "k",
            "segment",
            "n_cards",
            "segment_share",
            "qr_rate",
            "bip_rate",
            "qr_lift_vs_base",
            "bip_lift_vs_base",
            "qr_vs_bip_odds_ratio_vs_base",
            "n_viajes_mean",
        ]
    ]


def build_profile_top_lifts(profile: pd.DataFrame, ks: list[int], top_n: int = 6) -> pd.DataFrame:
    data = profile.loc[profile["k"].isin(ks)].copy()
    data["mean_lift_minus_1"] = data["mean_lift"] - 1.0
    frames: list[pd.DataFrame] = []
    for (k, segment), group in data.groupby(["k", "segment"], sort=True):
        high = group.sort_values("mean_lift_minus_1", ascending=False).head(top_n).copy()
        high["direction"] = "sobre_promedio"
        low = group.sort_values("mean_lift_minus_1", ascending=True).head(top_n).copy()
        low["direction"] = "bajo_promedio"
        frames.extend([high, low])
    out = pd.concat(frames, ignore_index=True)
    out["rank"] = out.groupby(["k", "segment", "direction"]).cumcount() + 1
    return out[
        [
            "k",
            "segment",
            "direction",
            "rank",
            "feature",
            "mean",
            "overall_mean",
            "mean_lift",
            "mean_lift_minus_1",
        ]
    ]


TABLE_LABELS = {
    "k": "k",
    "relative_best_reconstruction_error": "error recon. relativo",
    "stability_pairwise_ari_mean": "ARI estabilidad",
    "full_min_segment_share": "share min segmento",
    "full_max_segment_share": "share max segmento",
    "target": "objetivo",
    "cramers_v": "V de Cramer",
    "n": "n",
    "segment": "segmento",
    "n_cards": "tarjetas",
    "segment_share": "share segmento",
    "qr_rate": "tasa QR",
    "bip_rate": "tasa BIP",
    "qr_lift_vs_base": "indice QR",
    "bip_lift_vs_base": "indice BIP",
    "qr_red_lift_vs_base": "indice QR_RED",
    "qr_other_lift_vs_base": "indice QR_OTHER",
    "qr_vs_bip_odds_ratio_vs_base": "odds QR/BIP vs base",
    "n_viajes_mean": "viajes promedio",
    "direction": "direccion",
    "rank": "ranking",
    "feature": "variable",
    "mean_lift_minus_1": "indice medio - 1",
    "mean": "media segmento",
    "overall_mean": "media universo",
    "qr_mean": "media QR",
    "bip_mean": "media BIP",
    "qr_minus_bip": "QR - BIP",
    "qr_vs_bip_lift_minus_1": "indice QR/BIP - 1",
}


def table_html(df: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    out = df[columns].copy()
    if "feature" in out.columns:
        out["feature"] = out["feature"].map(feature_label)
    out = out.rename(columns=TABLE_LABELS)
    if max_rows is not None:
        out = out.head(max_rows)
    return out.to_html(index=False, classes="data-table", float_format=lambda x: f"{x:.3f}")


def build_html_report(model_dir: Path, fig_dir: Path, out_path: Path) -> None:
    metrics = pd.read_csv(model_dir / "nmf_metrics.csv")
    qr = pd.read_csv(model_dir / "posthoc" / "segment_qr_summary.csv")
    binary_qr = pd.read_csv(model_dir / "posthoc" / "segment_qr_binary_summary.csv")
    top_lifts = pd.read_csv(model_dir / "posthoc" / "segment_profile_top_lifts.csv")
    payment_diff = pd.read_csv(model_dir / "posthoc" / "segment_qr_vs_bip_feature_diff.csv")
    assoc = pd.read_csv(model_dir / "posthoc" / "segment_target_association.csv")
    k4 = qr.loc[qr["k"] == 4].copy()
    k5 = qr.loc[qr["k"] == 5].copy()
    binary_k4 = binary_qr.loc[binary_qr["k"] == 4].copy()
    binary_k5 = binary_qr.loc[binary_qr["k"] == 5].copy()
    top_k5 = top_lifts.loc[top_lifts["k"] == 5].copy()
    payment_diff_k5 = (
        payment_diff.loc[payment_diff["k"] == 5]
        .replace([np.inf, -np.inf], np.nan)
        .dropna(subset=["qr_vs_bip_lift_minus_1"])
        .sort_values(["segment", "abs_qr_vs_bip_lift_minus_1"], ascending=[True, False])
        .groupby("segment")
        .head(6)
        .reset_index(drop=True)
    )
    image_names = [
        "nmf_model_selection.png",
        "nmf_k4_qr_lifts.png",
        "nmf_k4_binary_qr_lifts.png",
        "nmf_k4_components_heatmap.png",
        "nmf_k4_segment_profile_heatmap.png",
        "nmf_k4_qr_vs_bip_feature_diff_heatmap.png",
        "nmf_k5_qr_lifts.png",
        "nmf_k5_binary_qr_lifts.png",
        "nmf_k5_segment_profile_heatmap.png",
        "nmf_k5_qr_vs_bip_feature_diff_heatmap.png",
    ]
    imgs = "\n".join(
        f'<figure><img src="figures/{name}" alt="{html.escape(name)}"></figure>'
        for name in image_names
    )
    content = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Revision NMF behavioral_wide v0b</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1F2430; background: #FCFCFD; }}
h1, h2 {{ margin-bottom: 0.2rem; }}
p {{ color: #4D5566; line-height: 1.45; max-width: 980px; }}
figure {{ margin: 28px 0; }}
img {{ max-width: 100%; border: 1px solid #E6E8F0; border-radius: 10px; background: white; }}
.data-table {{ border-collapse: collapse; margin: 14px 0 28px 0; font-size: 13px; }}
.data-table th, .data-table td {{ border: 1px solid #E6E8F0; padding: 6px 9px; text-align: right; }}
.data-table th:first-child, .data-table td:first-child {{ text-align: left; }}
.callout {{ background: #EAF1FE; border-left: 4px solid #5477C4; padding: 12px 16px; max-width: 980px; }}
</style>
</head>
<body>
<h1>Revision NMF behavioral_wide v0b</h1>
<p>Transformacion: clip p01-p99 + minmax [0,1] + ponderacion por bloque. QR/BIP se usa solo post-hoc.</p>
<div class="callout">
<strong>Lectura principal:</strong> k=4 es el candidato no supervisado por codo, tamanos e interpretabilidad. k=5 queda como sensibilidad porque separa un segmento pequeno con mayor indice QR/QR_RED, pero con menor estabilidad.
</div>
<h2>Seleccion de modelo</h2>
{table_html(metrics, ["k", "relative_best_reconstruction_error", "stability_pairwise_ari_mean", "full_min_segment_share", "full_max_segment_share"])}
<h2>Asociacion post-hoc</h2>
{table_html(assoc, ["k", "target", "cramers_v", "n"])}
<h2>Segmentos k=4</h2>
{table_html(k4, ["segment", "n_cards", "segment_share", "qr_lift_vs_base", "qr_red_lift_vs_base", "qr_other_lift_vs_base", "n_viajes_mean"])}
<h2>QR binario k=4</h2>
{table_html(binary_k4, ["segment", "n_cards", "segment_share", "qr_rate", "bip_rate", "qr_lift_vs_base", "bip_lift_vs_base", "qr_vs_bip_odds_ratio_vs_base", "n_viajes_mean"])}
<h2>Segmentos k=5 sensibilidad</h2>
{table_html(k5, ["segment", "n_cards", "segment_share", "qr_lift_vs_base", "qr_red_lift_vs_base", "qr_other_lift_vs_base", "n_viajes_mean"])}
<h2>QR binario k=5 sensibilidad</h2>
{table_html(binary_k5, ["segment", "n_cards", "segment_share", "qr_rate", "bip_rate", "qr_lift_vs_base", "bip_lift_vs_base", "qr_vs_bip_odds_ratio_vs_base", "n_viajes_mean"])}
<h2>Variables que mas separan k=5</h2>
{table_html(top_k5, ["segment", "direction", "rank", "feature", "mean_lift_minus_1", "mean", "overall_mean"], max_rows=60)}
<h2>Diferencias conductuales QR vs BIP dentro de segmentos k=5</h2>
{table_html(payment_diff_k5, ["segment", "feature", "qr_mean", "bip_mean", "qr_minus_bip", "qr_vs_bip_lift_minus_1"], max_rows=60)}
<h2>Figuras</h2>
{imgs}
</body>
</html>
"""
    out_path.write_text(content, encoding="utf-8")


def run(args: argparse.Namespace) -> Path:
    setup_style()
    model_dir = args.model_dir
    posthoc_dir = model_dir / "posthoc"
    fig_dir = model_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(model_dir / "nmf_metrics.csv")
    top = pd.read_csv(model_dir / "nmf_top_features.csv")
    qr = pd.read_csv(posthoc_dir / "segment_qr_summary.csv")
    profile = pd.read_csv(posthoc_dir / "segment_feature_profile.csv")
    payment_diff = pd.read_csv(posthoc_dir / "segment_qr_vs_bip_feature_diff.csv")
    build_binary_qr_summary(qr).to_csv(posthoc_dir / "segment_qr_binary_summary.csv", index=False)
    build_profile_top_lifts(profile, ks=[4, 5]).to_csv(
        posthoc_dir / "segment_profile_top_lifts.csv",
        index=False,
    )

    plot_model_selection(metrics, fig_dir / "nmf_model_selection.png")
    plot_qr_lifts(qr, 4, fig_dir / "nmf_k4_qr_lifts.png", "k=4 principal")
    binary_qr = build_binary_qr_summary(qr)
    plot_binary_qr_lifts(binary_qr, 4, fig_dir / "nmf_k4_binary_qr_lifts.png", "k=4 principal")
    plot_component_heatmap(top, 4, fig_dir / "nmf_k4_components_heatmap.png")
    plot_segment_profile_heatmap(profile, 4, fig_dir / "nmf_k4_segment_profile_heatmap.png", "k=4")
    plot_qr_vs_bip_feature_diff_heatmap(
        payment_diff,
        4,
        fig_dir / "nmf_k4_qr_vs_bip_feature_diff_heatmap.png",
        "k=4",
    )
    plot_qr_lifts(qr, 5, fig_dir / "nmf_k5_qr_lifts.png", "k=5 sensibilidad")
    plot_binary_qr_lifts(binary_qr, 5, fig_dir / "nmf_k5_binary_qr_lifts.png", "k=5 sensibilidad")
    plot_segment_profile_heatmap(profile, 5, fig_dir / "nmf_k5_segment_profile_heatmap.png", "k=5")
    plot_qr_vs_bip_feature_diff_heatmap(
        payment_diff,
        5,
        fig_dir / "nmf_k5_qr_vs_bip_feature_diff_heatmap.png",
        "k=5",
    )
    report_path = model_dir / "behavioral_wide_nmf_review.html"
    build_html_report(model_dir, fig_dir, report_path)
    print(f"OK report: {report_path}", flush=True)
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize behavioral_wide NMF outputs.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
