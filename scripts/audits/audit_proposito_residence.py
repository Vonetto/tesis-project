from __future__ import annotations

import datetime as dt
import re
import argparse
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_VIAJES_DIR = Path("/Volumes/TOSHIBA EXT/Vicente/tesis-project/raw/raw_csv/viajes")
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence"

ACTIVE_MODEL_WEEKS = {"2024-W17", "2025-W17"}
ML_REFERENCE_WEEKS = {"2025-W14", "2025-W15", "2025-W17"}
MIN_HOME_TRIPS_PER_CARD = 1

READ_COLUMNS = [
    "tipodia",
    "tiempo_inicio_viaje",
    "periodo_inicio_viaje",
    "periodo_fin_viaje",
    "id_tarjeta",
    "id_viaje",
    "contrato",
    "zona_inicio_viaje",
    "zona_fin_viaje",
    "comuna_inicio_viaje",
    "comuna_fin_viaje",
    "proposito",
]

SCHEMA_OVERRIDES = {c: pl.Utf8 for c in READ_COLUMNS}


def week_from_filename(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        raise ValueError(f"No se pudo extraer fecha desde {path}")
    day = dt.date.fromisoformat(match.group(1))
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def list_raw_files() -> pl.DataFrame:
    files = sorted(RAW_VIAJES_DIR.glob("*.viajes.csv"))
    if not files:
        raise FileNotFoundError(f"No se encontraron CSV raw de viajes en {RAW_VIAJES_DIR}")
    return pl.DataFrame(
        [
            {
                "path": str(path),
                "filename": path.name,
                "date": path.name.split(".")[0],
                "semana_iso": week_from_filename(path),
            }
            for path in files
        ]
    )


def scan_files(paths: list[str]) -> pl.LazyFrame:
    return pl.scan_csv(
        paths,
        separator="|",
        has_header=True,
        null_values=["", "-", "NA", "N/A", "null", "NULL"],
        schema_overrides=SCHEMA_OVERRIDES,
        infer_schema_length=0,
    ).select([pl.col(c) for c in READ_COLUMNS])


def read_raw_csv_minimal(path: str, semana_iso: str) -> pl.DataFrame:
    return (
        pl.read_csv(
            path,
            separator="|",
            has_header=True,
            null_values=["", "-", "NA", "N/A", "null", "NULL"],
            schema_overrides=SCHEMA_OVERRIDES,
            infer_schema_length=0,
            columns=READ_COLUMNS,
            low_memory=True,
        )
        .with_columns(pl.lit(semana_iso).alias("semana_iso"))
        .with_columns(
            [
                normalize_proposito_expr(),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_i"),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_i"),
                pl.col("contrato")
                .cast(pl.Utf8)
                .str.strip_chars()
                .is_in(["171", "102"])
                .alias("is_qr"),
            ]
        )
    )


def materialize_compact_cache(file_index: pl.DataFrame, scope: str) -> list[Path]:
    cache_dir = OUT_DIR / f"cache_{scope}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for row in file_index.sort("filename").iter_rows(named=True):
        out = cache_dir / f"{Path(row['filename']).stem}.parquet"
        outputs.append(out)
        if out.exists():
            continue
        print(f"Cacheando columnas minimas: {row['filename']}")
        df = read_raw_csv_minimal(row["path"], row["semana_iso"])
        df.write_parquet(out, compression="zstd")
    return outputs


def normalize_proposito_expr() -> pl.Expr:
    return (
        pl.col("proposito")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.to_uppercase()
        .str.replace_all(r"\s+", " ")
        .alias("proposito_norm")
    )


def add_basic_fields(lf: pl.LazyFrame, week_map: pl.DataFrame) -> pl.LazyFrame:
    # scan_csv no preserva el nombre de archivo; se procesa por semana desde listas filtradas.
    return lf.with_columns(
        [
            normalize_proposito_expr(),
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_i"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_i"),
            pl.col("contrato")
            .cast(pl.Utf8)
            .str.strip_chars()
            .is_in(["171", "102"])
            .alias("is_qr"),
        ]
    )


def build_week_lazyframes(file_index: pl.DataFrame) -> list[pl.LazyFrame]:
    frames = []
    for row in file_index.group_by("semana_iso").agg(pl.col("path")).iter_rows(named=True):
        lf = scan_files(row["path"]).with_columns(pl.lit(row["semana_iso"]).alias("semana_iso"))
        frames.append(add_basic_fields(lf, file_index))
    return frames


def write_csv(df: pl.DataFrame, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    df.write_csv(path)
    return path


def summarize_proposito(lf_all: pl.LazyFrame) -> dict[str, Path]:
    summary_by_week = (
        lf_all.group_by("semana_iso")
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("proposito_norm").is_null().sum().alias("n_proposito_null"),
                (pl.col("proposito_norm").is_null().mean() * 100).alias("pct_proposito_null"),
                (pl.col("proposito_norm") == "HOGAR").sum().alias("n_hogar"),
                ((pl.col("proposito_norm") == "HOGAR").mean() * 100).alias("pct_hogar"),
                pl.col("zona_inicio_i").is_null().sum().alias("n_zona_inicio_null"),
                pl.col("zona_fin_i").is_null().sum().alias("n_zona_fin_null"),
            ]
        )
        .sort("semana_iso")
        .collect()
    )

    prop_counts = (
        lf_all.group_by(["semana_iso", "proposito_norm"])
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
            ]
        )
        .with_columns((pl.col("n_trips") / pl.col("n_trips").sum().over("semana_iso") * 100).alias("pct_trips_week"))
        .sort(["semana_iso", "n_trips"], descending=[False, True])
        .collect()
    )

    return {
        "summary_by_week": write_csv(summary_by_week, "proposito_summary_by_week.csv"),
        "proposito_counts": write_csv(prop_counts, "proposito_counts_by_week.csv"),
    }


def summarize_home_candidate(lf_scope: pl.LazyFrame, label: str) -> dict[str, Path]:
    hogar = lf_scope.filter(
        (pl.col("proposito_norm") == "HOGAR")
        & pl.col("id_tarjeta").is_not_null()
        & pl.col("zona_fin_i").is_not_null()
    )
    home_counts = (
        hogar.group_by(["id_tarjeta", "zona_fin_i"])
        .agg(pl.len().alias("n_home_dest_trips"))
        .sort(["id_tarjeta", "n_home_dest_trips", "zona_fin_i"], descending=[False, True, False])
    )
    card_totals = hogar.group_by("id_tarjeta").agg(pl.len().alias("n_home_dest_trips_card"))
    top_home = (
        home_counts.group_by("id_tarjeta")
        .agg(
            [
                pl.col("zona_fin_i").first().alias("home_zone_candidate"),
                pl.col("n_home_dest_trips").first().alias("n_home_dest_trips_top"),
                pl.col("zona_fin_i").n_unique().alias("n_home_zones_observed"),
            ]
        )
        .join(card_totals, on="id_tarjeta", how="left")
        .with_columns(
            (
                pl.col("n_home_dest_trips_top") / pl.col("n_home_dest_trips_card")
            ).alias("home_zone_top_share")
        )
    )

    all_cards = lf_scope.select(pl.col("id_tarjeta")).filter(pl.col("id_tarjeta").is_not_null()).unique()
    coverage = (
        all_cards.join(top_home.lazy(), on="id_tarjeta", how="left")
        .select(
            [
                pl.len().alias("n_cards"),
                pl.col("home_zone_candidate").is_not_null().sum().alias("n_cards_with_home_candidate"),
                (pl.col("home_zone_candidate").is_not_null().mean() * 100).alias("pct_cards_with_home_candidate"),
                (pl.col("n_home_zones_observed") == 1).sum().alias("n_cards_single_home_zone"),
                ((pl.col("n_home_zones_observed") == 1).mean() * 100).alias("pct_cards_single_home_zone"),
                (pl.col("home_zone_top_share") >= 0.8).sum().alias("n_cards_top_share_ge_80pct"),
                ((pl.col("home_zone_top_share") >= 0.8).mean() * 100).alias("pct_cards_top_share_ge_80pct"),
            ]
        )
        .collect()
    )

    top_home_summary = (
        top_home.lazy()
        .select(
            [
                pl.len().alias("n_cards_with_home_candidate"),
                pl.col("n_home_dest_trips_card").mean().alias("mean_hogar_dest_trips_per_card"),
                pl.col("n_home_dest_trips_card").median().alias("median_hogar_dest_trips_per_card"),
                pl.col("n_home_zones_observed").mean().alias("mean_home_zones_observed"),
                pl.col("n_home_zones_observed").median().alias("median_home_zones_observed"),
                pl.col("home_zone_top_share").mean().alias("mean_home_zone_top_share"),
                pl.col("home_zone_top_share").median().alias("median_home_zone_top_share"),
            ]
        )
        .collect()
    )

    home_zone_distribution = (
        top_home.group_by("home_zone_candidate")
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("n_home_dest_trips_card").sum().alias("n_hogar_dest_trips"),
            ]
        )
        .sort("n_cards", descending=True)
        .collect()
    )

    ambiguous_cards_sample = (
        top_home.filter(pl.col("n_home_zones_observed") > 1)
        .sort(["n_home_zones_observed", "n_home_dest_trips_card"], descending=[True, True])
        .head(100)
        .collect()
    )

    return {
        f"{label}_home_candidate_coverage": write_csv(coverage, f"{label}_home_candidate_coverage.csv"),
        f"{label}_home_candidate_summary": write_csv(top_home_summary, f"{label}_home_candidate_summary.csv"),
        f"{label}_home_zone_distribution": write_csv(home_zone_distribution, f"{label}_home_zone_distribution.csv"),
        f"{label}_ambiguous_cards_sample": write_csv(ambiguous_cards_sample, f"{label}_ambiguous_cards_sample.csv"),
    }


def build_home_candidates(lf_scope: pl.LazyFrame) -> pl.LazyFrame:
    hogar = lf_scope.filter(
        (pl.col("proposito_norm") == "HOGAR")
        & pl.col("id_tarjeta").is_not_null()
        & pl.col("zona_fin_i").is_not_null()
    )
    home_counts = (
        hogar.group_by(["id_tarjeta", "zona_fin_i"])
        .agg(pl.len().alias("n_home_dest_trips"))
        .sort(["id_tarjeta", "n_home_dest_trips", "zona_fin_i"], descending=[False, True, False])
    )
    card_totals = hogar.group_by("id_tarjeta").agg(pl.len().alias("n_home_dest_trips_card"))
    return (
        home_counts.group_by("id_tarjeta")
        .agg(
            [
                pl.col("zona_fin_i").first().alias("home_zone_candidate"),
                pl.col("n_home_dest_trips").first().alias("n_home_dest_trips_top"),
                pl.col("zona_fin_i").n_unique().alias("n_home_zones_observed"),
            ]
        )
        .join(card_totals, on="id_tarjeta", how="left")
        .with_columns(
            (
                pl.col("n_home_dest_trips_top") / pl.col("n_home_dest_trips_card")
            ).alias("home_zone_top_share")
        )
    )


def validate_home_candidate_by_purpose(lf_scope: pl.LazyFrame, label: str) -> dict[str, Path]:
    home_candidates = build_home_candidates(lf_scope)
    joined = lf_scope.join(home_candidates, on="id_tarjeta", how="inner")
    purpose_validation = (
        joined.group_by("proposito_norm")
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                (pl.col("zona_inicio_i") == pl.col("home_zone_candidate")).mean().alias("pct_origin_equals_home"),
                (pl.col("zona_fin_i") == pl.col("home_zone_candidate")).mean().alias("pct_dest_equals_home"),
                pl.col("zona_inicio_i").is_null().mean().alias("pct_origin_null"),
                pl.col("zona_fin_i").is_null().mean().alias("pct_dest_null"),
            ]
        )
        .sort("n_trips", descending=True)
        .collect()
    )
    return {
        f"{label}_home_candidate_by_purpose": write_csv(
            purpose_validation, f"{label}_home_candidate_by_purpose.csv"
        )
    }


def compare_home_origin_relation(lf_scope: pl.LazyFrame, label: str) -> dict[str, Path]:
    # Diagnostico: en viajes con proposito HOGAR, cuantas veces el destino vs origen
    # parece candidato a residencia, solo usando distribuciones directas.
    hogar = lf_scope.filter(pl.col("proposito_norm") == "HOGAR")
    diagnostics = (
        hogar.select(
            [
                pl.len().alias("n_hogar_trips"),
                pl.col("zona_inicio_i").is_null().mean().alias("pct_origin_null"),
                pl.col("zona_fin_i").is_null().mean().alias("pct_dest_null"),
                (pl.col("zona_inicio_i") == pl.col("zona_fin_i")).mean().alias("pct_same_origin_dest"),
            ]
        )
        .collect()
    )
    by_period = (
        hogar.group_by("periodo_inicio_viaje")
        .agg(
            [
                pl.len().alias("n_hogar_trips"),
                pl.col("id_tarjeta").n_unique().alias("n_cards"),
                pl.col("zona_fin_i").n_unique().alias("n_dest_zones"),
            ]
        )
        .sort("n_hogar_trips", descending=True)
        .collect()
    )
    return {
        f"{label}_hogar_trip_diagnostics": write_csv(diagnostics, f"{label}_hogar_trip_diagnostics.csv"),
        f"{label}_hogar_by_period": write_csv(by_period, f"{label}_hogar_by_period.csv"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita proposito y factibilidad de zona de residencia.")
    parser.add_argument(
        "--scope",
        choices=["active", "active_ml", "all"],
        default="active",
        help=(
            "active: 2024-W17 y 2025-W17; "
            "active_ml: active + semanas ML 2025-W14/W15; "
            "all: todos los CSV raw disponibles."
        ),
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    file_index = list_raw_files()
    write_csv(file_index, "raw_file_inventory.csv")

    if args.scope == "active":
        weeks_to_scan = ACTIVE_MODEL_WEEKS
    elif args.scope == "active_ml":
        weeks_to_scan = ACTIVE_MODEL_WEEKS | ML_REFERENCE_WEEKS
    else:
        weeks_to_scan = set(file_index["semana_iso"].to_list())

    file_index = file_index.filter(pl.col("semana_iso").is_in(sorted(weeks_to_scan)))
    if file_index.is_empty():
        raise ValueError(f"No hay archivos para scope={args.scope} y semanas={sorted(weeks_to_scan)}")

    cache_paths = materialize_compact_cache(file_index, args.scope)
    lf_all = pl.scan_parquet([str(p) for p in cache_paths])

    outputs: dict[str, Path] = {}
    outputs.update(summarize_proposito(lf_all))

    scope_labels = {"scanned_weeks": set(file_index["semana_iso"].to_list())}
    if args.scope in {"active_ml", "all"}:
        scope_labels["active_model_weeks"] = ACTIVE_MODEL_WEEKS
        scope_labels["ml_reference_weeks"] = ML_REFERENCE_WEEKS
    if args.scope == "all":
        scope_labels["all_raw_weeks"] = set(file_index["semana_iso"].to_list())

    for label, weeks in scope_labels.items():
        lf_scope = lf_all.filter(pl.col("semana_iso").is_in(sorted(weeks)))
        outputs.update(summarize_home_candidate(lf_scope, label))
        outputs.update(compare_home_origin_relation(lf_scope, label))
        outputs.update(validate_home_candidate_by_purpose(lf_scope, label))

    print("Auditoria escrita en:")
    for key, path in outputs.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()
