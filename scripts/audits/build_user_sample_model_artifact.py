from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PARTITION = "pooled_2024_2025"
ARTIFACTS_DIR = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
OUT_AUDIT_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "user_sample"

CHOICE_LABELS = {
    0: "BIP",
    1: "QR_RED",
    2: "QR_OTHER",
}

TRIP_ALT_ATTR_COLS = [
    "TVH_BIP",
    "TVH_QR_RED",
    "TVH_QR_OTHER",
    "TEI_BIP",
    "TEI_QR_RED",
    "TEI_QR_OTHER",
    "TET_BIP",
    "TET_QR_RED",
    "TET_QR_OTHER",
    "NTR_BIP",
    "NTR_QR_RED",
    "NTR_QR_OTHER",
]


def parse_user_fraction(user_sample_tag: str) -> float:
    if not user_sample_tag.startswith("user") or not user_sample_tag.endswith("pct"):
        raise ValueError(f"user_sample_tag debe tener forma userXpct, recibido: {user_sample_tag}")
    try:
        return int(user_sample_tag.removeprefix("user").removesuffix("pct")) / 100
    except Exception as exc:
        raise ValueError(f"No se pudo parsear user_sample_tag={user_sample_tag!r}") from exc


def source_residence_path(source_sample_tag: str) -> Path:
    return (
        ARTIFACTS_DIR
        / f"{MODEL_PARTITION}-estimation-{source_sample_tag}-residence-censo4-micro-osm-eod2012.parquet"
    )


def output_path(user_sample_tag: str, source_sample_tag: str) -> Path:
    return (
        ARTIFACTS_DIR
        / f"{MODEL_PARTITION}-estimation-{user_sample_tag}-from-{source_sample_tag}-residence-censo4-micro-osm-eod2012.parquet"
    )


def home_alta_output_path(user_sample_tag: str, source_sample_tag: str) -> Path:
    return (
        ARTIFACTS_DIR
        / f"{MODEL_PARTITION}-estimation-{user_sample_tag}-from-{source_sample_tag}-residence-home-alta-censo4-micro-osm-eod2012.parquet"
    )


def add_choice_label(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.col("choice_nested")
        .replace_strict(CHOICE_LABELS, default="UNKNOWN")
        .alias("choice_label")
    )


def select_user_sample(df: pl.DataFrame, *, fraction: float, seed: int) -> pl.DataFrame:
    users = (
        df.select("id_tarjeta")
        .drop_nulls()
        .unique()
        .sample(fraction=fraction, shuffle=True, seed=seed)
        .with_columns(pl.lit(1).cast(pl.Int8).alias("_selected_user"))
    )
    return df.join(users, on="id_tarjeta", how="inner").drop("_selected_user")


def filter_complete_home_alta(df: pl.DataFrame) -> pl.DataFrame:
    return df.filter(
        (pl.col("home_confidence") == "alta")
        & pl.all_horizontal([pl.col(c).is_not_null() for c in TRIP_ALT_ATTR_COLS])
    )


def sample_summary(df: pl.DataFrame, *, label: str, source_rows: int, source_cards: int) -> pl.DataFrame:
    trip_counts = df.group_by("id_tarjeta").agg(pl.len().alias("n_trips_card"))
    return df.select(
        [
            pl.lit(label).alias("sample"),
            pl.len().alias("n_rows"),
            pl.col("id_tarjeta").n_unique().alias("n_cards"),
            pl.col("pk_viaje").n_unique().alias("n_pk_viaje"),
            (pl.col("pk_viaje").n_unique() == pl.len()).alias("pk_viaje_unique"),
            pl.col("zona_hogar").is_not_null().sum().alias("n_rows_with_zona_hogar"),
            (pl.col("home_confidence") == "alta").sum().alias("n_rows_home_alta"),
            (pl.col("home_confidence") == "media").sum().alias("n_rows_home_media"),
            (pl.col("home_confidence") == "baja").sum().alias("n_rows_home_baja"),
            pl.lit(source_rows).alias("source_n_rows"),
            pl.lit(source_cards).alias("source_n_cards"),
            (pl.len() / pl.lit(source_rows)).alias("share_source_rows"),
            (pl.col("id_tarjeta").n_unique() / pl.lit(source_cards)).alias("share_source_cards"),
            pl.lit(trip_counts.select(pl.col("n_trips_card").mean()).item()).alias("mean_trips_per_card"),
            pl.lit(trip_counts.select(pl.col("n_trips_card").median()).item()).alias("median_trips_per_card"),
            pl.lit(trip_counts.select(pl.col("n_trips_card").quantile(0.90)).item()).alias("p90_trips_per_card"),
            pl.lit(trip_counts.select(pl.col("n_trips_card").max()).item()).alias("max_trips_per_card"),
        ]
    )


def choice_summary(df: pl.DataFrame, *, label: str) -> pl.DataFrame:
    return (
        add_choice_label(df)
        .group_by(["choice_nested", "choice_label"])
        .agg([pl.len().alias("n_rows"), pl.col("id_tarjeta").n_unique().alias("n_cards")])
        .with_columns(
            [
                pl.lit(label).alias("sample"),
                (pl.col("n_rows") / pl.col("n_rows").sum()).alias("row_share"),
            ]
        )
        .select(["sample", "choice_nested", "choice_label", "n_rows", "n_cards", "row_share"])
        .sort(["sample", "choice_nested"])
    )


def home_confidence_summary(df: pl.DataFrame, *, label: str) -> pl.DataFrame:
    return (
        df.with_columns(pl.col("home_confidence").fill_null("sin_residencia").alias("home_confidence_label"))
        .group_by("home_confidence_label")
        .agg([pl.len().alias("n_rows"), pl.col("id_tarjeta").n_unique().alias("n_cards")])
        .with_columns(
            [
                pl.lit(label).alias("sample"),
                (pl.col("n_rows") / pl.col("n_rows").sum()).alias("row_share"),
            ]
        )
        .select(["sample", "home_confidence_label", "n_rows", "n_cards", "row_share"])
        .sort(["sample", "home_confidence_label"])
    )


def write_diagnostics(
    *,
    source: pl.DataFrame,
    user_sample: pl.DataFrame,
    user_home_alta: pl.DataFrame,
    user_sample_tag: str,
    source_sample_tag: str,
) -> None:
    out_dir = OUT_AUDIT_DIR / f"{user_sample_tag}-from-{source_sample_tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    source_rows = source.height
    source_cards = source.select(pl.col("id_tarjeta").n_unique()).item()

    pl.concat(
        [
            sample_summary(source, label="source_trip_sample", source_rows=source_rows, source_cards=source_cards),
            sample_summary(user_sample, label="user_sample_all", source_rows=source_rows, source_cards=source_cards),
            sample_summary(user_home_alta, label="user_sample_home_alta", source_rows=source_rows, source_cards=source_cards),
        ],
        how="vertical",
    ).write_csv(out_dir / "sample_summary.csv")

    pl.concat(
        [
            choice_summary(source, label="source_trip_sample"),
            choice_summary(user_sample, label="user_sample_all"),
            choice_summary(user_home_alta, label="user_sample_home_alta"),
        ],
        how="vertical",
    ).write_csv(out_dir / "choice_summary.csv")

    pl.concat(
        [
            home_confidence_summary(source, label="source_trip_sample"),
            home_confidence_summary(user_sample, label="user_sample_all"),
            home_confidence_summary(user_home_alta, label="user_sample_home_alta"),
        ],
        how="vertical",
    ).write_csv(out_dir / "home_confidence_summary.csv")

    if "macro_oriente" in source.columns:
        pl.concat(
            [
                macrozone_summary(source, label="source_trip_sample"),
                macrozone_summary(user_sample, label="user_sample_all"),
                macrozone_summary(user_home_alta, label="user_sample_home_alta"),
            ],
            how="vertical",
        ).write_csv(out_dir / "macrozone_summary.csv")


def macrozone_summary(df: pl.DataFrame, *, label: str) -> pl.DataFrame:
    macro_cols = [
        "macro_norte",
        "macro_poniente",
        "macro_oriente",
        "macro_sur",
        "macro_suroriente",
        "macro_externa_especial",
    ]
    expr = (
        pl.when(pl.col("macro_norte") == 1)
        .then(pl.lit("NORTE"))
        .when(pl.col("macro_poniente") == 1)
        .then(pl.lit("PONIENTE"))
        .when(pl.col("macro_oriente") == 1)
        .then(pl.lit("ORIENTE"))
        .when(pl.col("macro_sur") == 1)
        .then(pl.lit("SUR"))
        .when(pl.col("macro_suroriente") == 1)
        .then(pl.lit("SURORIENTE"))
        .when(pl.col("macro_externa_especial") == 1)
        .then(pl.lit("EXTERNA_ESPECIAL"))
        .otherwise(pl.lit("CENTRO"))
        .alias("macrozone_origin")
    )
    return (
        df.select([*macro_cols])
        .with_columns(expr)
        .group_by("macrozone_origin")
        .agg(pl.len().alias("n_rows"))
        .with_columns(
            [
                pl.lit(label).alias("sample"),
                (pl.col("n_rows") / pl.col("n_rows").sum()).alias("row_share"),
            ]
        )
        .select(["sample", "macrozone_origin", "n_rows", "row_share"])
        .sort(["sample", "macrozone_origin"])
    )


def build_user_sample(
    *,
    user_sample_tag: str,
    source_sample_tag: str,
    seed: int,
    force: bool,
) -> tuple[Path, Path]:
    source_path = source_residence_path(source_sample_tag)
    out_path = output_path(user_sample_tag, source_sample_tag)
    home_alta_path = home_alta_output_path(user_sample_tag, source_sample_tag)
    if out_path.exists() and home_alta_path.exists() and not force:
        print(f"ℹ️ Reusando user-sample existente: {out_path}")
        print(f"ℹ️ Reusando user-sample home_alta existente: {home_alta_path}")
        return out_path, home_alta_path
    if not source_path.exists():
        raise FileNotFoundError(
            f"No existe artefacto residencial fuente: {source_path}. "
            f"Ejecuta `python scripts/audits/build_residence_model_sample.py --sample-tag {source_sample_tag}`."
        )

    fraction = parse_user_fraction(user_sample_tag)
    source = pl.read_parquet(source_path)
    if "id_tarjeta" not in source.columns:
        raise ValueError(f"El artefacto fuente no contiene id_tarjeta: {source_path}")
    if "pk_viaje" not in source.columns:
        raise ValueError(f"El artefacto fuente no contiene pk_viaje: {source_path}")

    user_sample = select_user_sample(source, fraction=fraction, seed=seed)
    user_home_alta = filter_complete_home_alta(user_sample)
    if user_sample.is_empty():
        raise ValueError("La muestra por usuario quedó vacía")
    if user_home_alta.is_empty():
        raise ValueError("La muestra por usuario home_alta quedó vacía")

    user_sample.write_parquet(out_path, compression="zstd")
    user_home_alta.write_parquet(home_alta_path, compression="zstd")
    write_diagnostics(
        source=source,
        user_sample=user_sample,
        user_home_alta=user_home_alta,
        user_sample_tag=user_sample_tag,
        source_sample_tag=source_sample_tag,
    )
    print(f"✅ User-sample escrito en: {out_path}")
    print(f"✅ User-sample home_alta escrito en: {home_alta_path}")
    return out_path, home_alta_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construye sensibilidad de muestra por usuario desde artefacto residencial model-ready."
    )
    parser.add_argument("--user-sample-tag", default="user5pct")
    parser.add_argument("--source-sample-tag", default="sample10pct", choices=["sample2pct", "sample5pct", "sample10pct"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    out_path, home_alta_path = build_user_sample(
        user_sample_tag=args.user_sample_tag,
        source_sample_tag=args.source_sample_tag,
        seed=args.seed,
        force=args.force,
    )
    print(f"- output: {out_path}")
    print(f"- home_alta_output: {home_alta_path}")


if __name__ == "__main__":
    main()
