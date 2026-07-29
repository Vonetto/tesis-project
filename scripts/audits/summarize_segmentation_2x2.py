from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


KEY_INDICATORS = [
    "dsi_day_sequence",
    "tsi_time_distribution",
    "lsi_origin_zone",
    "lsi_origin_stop",
]


def variant_order() -> list[str]:
    return [
        "A_weekdays_W15_W17_N10",
        "A_weekdays_W15_W16_N9_no_good_friday",
        "B_calendar_W15_W17_N14",
        "B_calendar_W15_W16_N14",
    ]


def variant_labels() -> dict[str, str]:
    return {
        "A_weekdays_W15_W17_N10": "A W15+W17 N10",
        "A_weekdays_W15_W16_N9_no_good_friday": "A W15+W16 N9",
        "B_calendar_W15_W17_N14": "B W15+W17 N14",
        "B_calendar_W15_W16_N14": "B W15+W16 N14",
    }


def write_distribution_focus(out_dir: Path) -> pd.DataFrame:
    df = pd.read_csv(out_dir / "segmentation_2x2_indicator_distribution.csv")
    focus = df[df["feature"].isin(KEY_INDICATORS)].copy()
    focus["variant_label"] = focus["variant_id"].map(variant_labels())
    focus["variant_id"] = pd.Categorical(focus["variant_id"], categories=variant_order(), ordered=True)
    focus = focus.sort_values(["variant_id", "feature"])
    cols = [
        "variant_id",
        "variant_label",
        "feature",
        "n",
        "mean",
        "std",
        "p10",
        "p25",
        "median",
        "p75",
        "p90",
    ]
    focus[cols].to_csv(out_dir / "segmentation_2x2_distribution_focus.csv", index=False)
    return focus


def write_channel_focus(out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    auc = pd.read_csv(out_dir / "segmentation_2x2_channel_separation.csv")
    auc["variant_label"] = auc["variant_id"].map(variant_labels())
    auc["variant_id"] = pd.Categorical(auc["variant_id"], categories=variant_order(), ordered=True)
    auc = auc.sort_values("variant_id")
    auc_cols = [
        "variant_id",
        "variant_label",
        "n",
        "qr_prevalence",
        "roc_auc_indicators_predict_channel_mean",
        "roc_auc_indicators_predict_channel_std",
    ]
    auc[auc_cols].to_csv(out_dir / "segmentation_2x2_channel_auc_focus.csv", index=False)

    assoc = pd.read_csv(out_dir / "segmentation_2x2_indicator_channel_association.csv")
    assoc = assoc[assoc["feature"].isin(KEY_INDICATORS)].copy()
    assoc["variant_label"] = assoc["variant_id"].map(variant_labels())
    assoc["variant_id"] = pd.Categorical(assoc["variant_id"], categories=variant_order(), ordered=True)
    assoc = assoc.sort_values(["variant_id", "feature"])
    assoc_cols = [
        "variant_id",
        "variant_label",
        "feature",
        "mean_qr",
        "mean_bip",
        "standardized_mean_diff_qr_minus_bip",
        "pearson_with_channel",
        "spearman_with_channel",
    ]
    assoc[assoc_cols].to_csv(out_dir / "segmentation_2x2_channel_indicator_focus.csv", index=False)
    return auc, assoc


def plot_indicator_means(out_dir: Path, focus: pd.DataFrame) -> None:
    labels = variant_labels()
    pivot = focus.pivot(index="variant_id", columns="feature", values="mean").loc[variant_order()]
    ax = pivot.plot(kind="bar", figsize=(11, 5), width=0.82)
    ax.set_title("Segmentation 2x2: indicator means")
    ax.set_xlabel("")
    ax.set_ylabel("Mean")
    ax.set_xticklabels([labels[x.get_text()] for x in ax.get_xticklabels()], rotation=25, ha="right")
    ax.legend(title="Indicator", loc="lower right")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_dir / "segmentation_2x2_indicator_means.png", dpi=160)
    plt.close()


def plot_channel_smd(out_dir: Path, assoc: pd.DataFrame) -> None:
    labels = variant_labels()
    pivot = assoc.pivot(
        index="variant_id",
        columns="feature",
        values="standardized_mean_diff_qr_minus_bip",
    ).loc[variant_order()]
    ax = pivot.plot(kind="bar", figsize=(11, 5), width=0.82)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("QR vs BIP standardized mean differences")
    ax.set_xlabel("")
    ax.set_ylabel("SMD (QR - BIP)")
    ax.set_xticklabels([labels[x.get_text()] for x in ax.get_xticklabels()], rotation=25, ha="right")
    ax.legend(title="Indicator", loc="lower left")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_dir / "segmentation_2x2_channel_smd.png", dpi=160)
    plt.close()


def write_markdown(out_dir: Path, focus: pd.DataFrame, auc: pd.DataFrame, assoc: pd.DataFrame) -> None:
    indicator_table = (
        focus.pivot(index="variant_id", columns="feature", values="mean")
        .loc[variant_order()]
        .rename(index=variant_labels())
        .round(3)
    )
    auc_table = (
        auc.set_index("variant_id")
        .loc[variant_order(), ["n", "qr_prevalence", "roc_auc_indicators_predict_channel_mean"]]
        .rename(index=variant_labels())
        .rename(
            columns={
                "qr_prevalence": "qr_prevalence",
                "roc_auc_indicators_predict_channel_mean": "channel_auc",
            }
        )
    )
    auc_table["qr_prevalence"] = auc_table["qr_prevalence"].round(3)
    auc_table["channel_auc"] = auc_table["channel_auc"].round(3)

    max_abs_smd = (
        assoc.assign(abs_smd=assoc["standardized_mean_diff_qr_minus_bip"].abs())
        .groupby("variant_id", observed=True)["abs_smd"]
        .max()
        .loc[variant_order()]
        .rename(index=variant_labels())
        .round(3)
    )

    lines = [
        "# Segmentation 2x2: distribution and channel audit",
        "",
        "## Indicator Means",
        "",
        indicator_table.to_markdown(),
        "",
        "## QR/BIP Separability",
        "",
        auc_table.to_markdown(),
        "",
        "Max absolute SMD among DSI/TSI/LSI indicators:",
        "",
        max_abs_smd.to_frame("max_abs_smd").to_markdown(),
        "",
        "## Initial Reading",
        "",
        "- Calendar variants raise DSI relative to weekdays variants, mainly because weekends add repeated inactivity/activity structure.",
        "- TSI is very stable across the four quadrants; differences are small in mean level.",
        "- LSI is lower in calendar variants than weekdays variants, which suggests weekend origins/stops add location variability.",
        "- Channel separability is weak: AUC stays near 0.55 and the largest QR-BIP standardized mean differences for DSI/TSI/LSI are around 0.15, not a deterministic QR/BIP proxy.",
        "- QR users are consistently less stable in DSI and LSI than BIP users, but the effect size is small-to-moderate, not enough to define clusters by channel alone.",
        "",
    ]
    (out_dir / "segmentation_2x2_analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("tmp/audits/segmentation_2x2_w15w17_w15w16"),
    )
    args = parser.parse_args()

    focus = write_distribution_focus(args.out_dir)
    auc, assoc = write_channel_focus(args.out_dir)
    plot_indicator_means(args.out_dir, focus)
    plot_channel_smd(args.out_dir, assoc)
    write_markdown(args.out_dir, focus, auc, assoc)
    print(args.out_dir.resolve())


if __name__ == "__main__":
    main()
