from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
OUT_BASE_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "model_input_audit"
MODEL_PARTITION = "pooled_2024_2025"

CHOICE_LABELS = {
    0: "BIP",
    1: "QR_RED",
    2: "QR_OTHER",
}

VARIABLE_PAIRS = [
    (
        "educ_univ_o_mas",
        "share_cine18_universitaria_o_mas_micro_z",
        "res_share_cine18_universitaria_o_mas_micro_z",
    ),
    ("discapacidad", "share_discapacidad_z", "res_share_discapacidad_z"),
    ("inmigrantes", "share_inmigrantes_z", "res_share_inmigrantes_z"),
    ("mujeres", "share_mujeres_z", "res_share_mujeres_z"),
    ("asistencia_parv", "share_asistencia_parv_z", "res_share_asistencia_parv_z"),
    ("edad_promedio", "prom_edad_z", "res_prom_edad_z"),
    (
        "income_proxy_de",
        "eod2012_share_hogares_de_income_proxy_z",
        "res_eod2012_share_hogares_de_income_proxy_z",
    ),
]

QUALITY_FILTERS = {
    "all_rows": pl.lit(True),
    "with_home": pl.col("zona_hogar").is_not_null(),
    "home_alta": pl.col("home_confidence") == "alta",
    "home_alta_media": pl.col("home_confidence").is_in(["alta", "media"]),
    "home_baja": pl.col("home_confidence") == "baja",
    "sin_residencia": pl.col("zona_hogar").is_null(),
}


def sample_path(sample_tag: str) -> Path:
    return ARTIFACTS_DIR / f"{MODEL_PARTITION}-estimation-{sample_tag}-residence-censo4-micro-osm-eod2012.parquet"


def write_csv(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_csv(path)


def add_labels(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        [
            pl.col("choice_nested")
            .replace_strict(CHOICE_LABELS, default="UNKNOWN")
            .alias("choice_label"),
            pl.col("home_confidence").fill_null("sin_residencia").alias("home_confidence_label"),
            (
                pl.when(pl.col("home_confidence") == "alta")
                .then(pl.lit("alta"))
                .when(pl.col("home_confidence") == "media")
                .then(pl.lit("media"))
                .when(pl.col("home_confidence") == "baja")
                .then(pl.lit("baja"))
                .otherwise(pl.lit("sin_residencia"))
            ).alias("home_confidence_group"),
        ]
    )


def build_sample_summary(df: pl.DataFrame) -> pl.DataFrame:
    total_rows = df.height
    return (
        df.group_by(["home_confidence_group", "choice_nested", "choice_label"])
        .agg(
            [
                pl.len().alias("n_rows"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("res_censo_zone_imputed").fill_null(0).sum().alias("n_res_censo_zone_imputed"),
                pl.col("res_eod_zone_imputed").fill_null(0).sum().alias("n_res_eod_zone_imputed"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_rows") / pl.lit(total_rows)).alias("row_share_total"),
                (pl.col("n_rows") / pl.col("n_rows").sum().over("home_confidence_group")).alias(
                    "choice_share_within_confidence"
                ),
            ]
        )
        .sort(["home_confidence_group", "choice_nested"])
    )


def build_variable_pair_comparison(df: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for filter_name, filter_expr in QUALITY_FILTERS.items():
        df_filter = df.filter(filter_expr)
        if df_filter.is_empty():
            continue
        for variable, origin_col, residence_col in VARIABLE_PAIRS:
            if origin_col not in df_filter.columns or residence_col not in df_filter.columns:
                continue
            pair_df = df_filter.select([origin_col, residence_col]).drop_nulls()
            if pair_df.is_empty():
                continue
            stats = pair_df.select(
                [
                    pl.len().alias("n_rows"),
                    pl.corr(origin_col, residence_col).alias("corr_origin_residence"),
                    pl.col(origin_col).mean().alias("mean_origin"),
                    pl.col(residence_col).mean().alias("mean_residence"),
                    (pl.col(residence_col) - pl.col(origin_col)).mean().alias("mean_res_minus_origin"),
                    (pl.col(residence_col) - pl.col(origin_col)).abs().mean().alias("mean_abs_diff"),
                    (pl.col(residence_col) - pl.col(origin_col)).abs().median().alias("median_abs_diff"),
                    (pl.col(residence_col) - pl.col(origin_col)).abs().quantile(0.90).alias("p90_abs_diff"),
                    ((pl.col(residence_col) - pl.col(origin_col)).abs() > 0.5).mean().alias("share_abs_diff_gt_0_5sd"),
                    ((pl.col(residence_col) - pl.col(origin_col)).abs() > 1.0).mean().alias("share_abs_diff_gt_1sd"),
                ]
            ).row(0, named=True)
            rows.append(
                {
                    "filter": filter_name,
                    "variable": variable,
                    "origin_col": origin_col,
                    "residence_col": residence_col,
                    **stats,
                }
            )
    return pl.DataFrame(rows)


def build_variable_means_by_choice(df: pl.DataFrame) -> pl.DataFrame:
    frames = []
    for filter_name, filter_expr in QUALITY_FILTERS.items():
        df_filter = df.filter(filter_expr)
        if df_filter.is_empty():
            continue
        for variable, origin_col, residence_col in VARIABLE_PAIRS:
            if origin_col not in df_filter.columns or residence_col not in df_filter.columns:
                continue
            frames.append(
                df_filter.group_by(["choice_nested", "choice_label"])
                .agg(
                    [
                        pl.len().alias("n_rows"),
                        pl.col("id_tarjeta").n_unique().alias("n_cards"),
                        pl.col(origin_col).mean().alias("mean_origin"),
                        pl.col(residence_col).mean().alias("mean_residence"),
                        (pl.col(residence_col) - pl.col(origin_col)).mean().alias("mean_res_minus_origin"),
                    ]
                )
                .with_columns(
                    [
                        pl.lit(filter_name).alias("filter"),
                        pl.lit(variable).alias("variable"),
                        pl.lit(origin_col).alias("origin_col"),
                        pl.lit(residence_col).alias("residence_col"),
                    ]
                )
            )
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="vertical").select(
        [
            "filter",
            "variable",
            "origin_col",
            "residence_col",
            "choice_nested",
            "choice_label",
            "n_rows",
            "n_cards",
            "mean_origin",
            "mean_residence",
            "mean_res_minus_origin",
        ]
    ).sort(["filter", "variable", "choice_nested"])


def build_imputation_summary(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.group_by(["zona_hogar", "home_confidence_group"])
        .agg(
            [
                pl.len().alias("n_rows"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("res_censo_zone_imputed").fill_null(0).max().alias("res_censo_zone_imputed"),
                pl.col("res_eod_zone_imputed").fill_null(0).max().alias("res_eod_zone_imputed"),
            ]
        )
        .filter((pl.col("res_censo_zone_imputed") == 1) | (pl.col("res_eod_zone_imputed") == 1))
        .sort(["zona_hogar", "home_confidence_group"])
    )


def run_audit(sample_tag: str) -> Path:
    path = sample_path(sample_tag)
    if not path.exists():
        raise FileNotFoundError(f"No existe muestra por residencia: {path}")

    out_dir = OUT_BASE_DIR / sample_tag
    df = add_labels(pl.read_parquet(path))

    write_csv(build_sample_summary(df), out_dir / "choice_by_home_confidence.csv")
    write_csv(build_variable_pair_comparison(df), out_dir / "origin_vs_residence_variable_comparison.csv")
    write_csv(build_variable_means_by_choice(df), out_dir / "origin_vs_residence_means_by_choice.csv")
    write_csv(build_imputation_summary(df), out_dir / "residence_zone_imputation_summary.csv")

    print(f"✅ Auditoría origen vs residencia escrita en: {out_dir}")
    return out_dir


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audita diferencias entre variables de zona de origen y zona de residencia."
    )
    parser.add_argument("--sample-tag", default="sample10pct", choices=["sample2pct", "sample5pct", "sample10pct"])
    args = parser.parse_args()
    run_audit(args.sample_tag)


if __name__ == "__main__":
    main()
