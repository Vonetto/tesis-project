"""Build user-level mobility pattern matrices for unsupervised segmentation.

The output is intentionally separate from the supervised ML matrix. Target
columns are kept only as metadata for post-hoc profiling and are never included
in the NMF feature inventory.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.od_buffers_nested_logit import add_time_dummies_v2
from scripts.audits.build_user_level_payment_panel import (
    BUS_CODES,
    METRO_CODES,
    PROCESSED_TRIPS_BY_WEEK,
    SCOPE_WEEKS,
    TRANSPORT_COLS,
    build_macrozone_lookup,
)


USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"
OUT_DIR = USER_DIR / "segmentation"

SCOPE_CHOICES = ["active", "ml_2025", "interannual_ml"]
VARIANT_CHOICES = ["clean", "with_conflicts"]
HOME_FILTERS = {"alta", "alta_media", "any"}
MATRIX_SPECS = {"macro_franja_modo"}
NORMALIZATIONS = {"share", "count"}

TARGET_METADATA_COLS = ["tipo_tarjeta", "is_qr", "is_qr_red", "is_qr_other"]
BASE_METADATA_COLS = [
    "id_tarjeta",
    *TARGET_METADATA_COLS,
    "n_viajes",
    "share_trips_2025",
    "home_confidence",
    "zona_hogar",
    "home_macrozone",
    "origin_zone_top1",
    "origin_top1_macrozone",
]
TARGET_LEAKAGE_TOKENS = {
    "tipo_tarjeta",
    "target",
    "qr",
    "bip",
    "payment",
    "pago",
}


def universe_suffix(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> str:
    suffix = f"{scope}_{variant}_{home_filter}_n{min_trips}"
    if min_home_trips > 0:
        suffix += f"_home{min_home_trips}"
    return suffix


def model_matrix_path(scope: str, variant: str, home_filter: str, min_trips: int, min_home_trips: int) -> Path:
    return USER_DIR / f"user_model_matrix_{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}.parquet"


def matrix_stem(
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    matrix_spec: str,
    normalization: str,
) -> str:
    return (
        f"user_mobility_matrix_"
        f"{universe_suffix(scope, variant, home_filter, min_trips, min_home_trips)}_"
        f"{matrix_spec}_{normalization}"
    )


def output_path(
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    matrix_spec: str,
    normalization: str,
) -> Path:
    return OUT_DIR / f"{matrix_stem(scope, variant, home_filter, min_trips, min_home_trips, matrix_spec, normalization)}.parquet"


def inventory_path(out_path: Path) -> Path:
    return out_path.with_name(f"{out_path.stem}_feature_inventory.json")


def audit_path(out_path: Path, stem: str) -> Path:
    return out_path.with_name(f"{out_path.stem}_{stem}.csv")


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def validate_args(scope: str, variant: str, home_filter: str, matrix_spec: str, normalization: str) -> None:
    if scope not in SCOPE_CHOICES:
        raise ValueError(f"Scope no soportado: {scope}")
    if variant not in VARIANT_CHOICES:
        raise ValueError(f"Variant no soportada: {variant}")
    if home_filter not in HOME_FILTERS:
        raise ValueError(f"home_filter no soportado: {home_filter}")
    if matrix_spec not in MATRIX_SPECS:
        raise ValueError(f"matrix_spec no soportado: {matrix_spec}")
    if normalization not in NORMALIZATIONS:
        raise ValueError(f"normalization no soportada: {normalization}")


def assert_inputs(scope: str, universe_path: Path) -> None:
    missing_weeks = [str(PROCESSED_TRIPS_BY_WEEK[w]) for w in SCOPE_WEEKS[scope] if not PROCESSED_TRIPS_BY_WEEK[w].exists()]
    missing = [*missing_weeks]
    if not universe_path.exists():
        missing.append(str(universe_path))
    if missing:
        raise FileNotFoundError(f"Faltan inputs requeridos: {missing}")


def sanitize_token(value: object) -> str:
    text = "unknown" if value is None else str(value).strip().lower()
    text = (
        text.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def feature_name_from_pattern(origin_macrozone: object, time_band: object, mode_coarse: object) -> str:
    return "seg_" + "__".join(
        [
            sanitize_token(origin_macrozone),
            sanitize_token(time_band),
            sanitize_token(mode_coarse),
        ]
    )


def sanitize_token_expr(expr: pl.Expr) -> pl.Expr:
    return (
        expr.cast(pl.Utf8, strict=False)
        .fill_null("unknown")
        .str.to_lowercase()
        .str.replace_all(r"[^a-z0-9]+", "_")
        .str.replace_all(r"_+", "_")
        .str.strip_chars("_")
    )


def any_mode_code_expr(codes: list[str]) -> pl.Expr:
    return pl.any_horizontal(
        [pl.col(c).cast(pl.Utf8, strict=False).is_in(codes).fill_null(False) for c in TRANSPORT_COLS]
    )


def mode_coarse_expr(alias: str = "mode_coarse") -> pl.Expr:
    has_bus = any_mode_code_expr(BUS_CODES)
    has_metro = any_mode_code_expr(METRO_CODES)
    return (
        pl.when(has_bus & has_metro)
        .then(pl.lit("metro_bus"))
        .when(has_metro)
        .then(pl.lit("metro_only"))
        .when(has_bus)
        .then(pl.lit("bus_only"))
        .otherwise(pl.lit("other_mode"))
        .alias(alias)
    )


def time_band_expr(alias: str = "time_band") -> pl.Expr:
    return (
        pl.when(pl.col("DUMMY_LAB_PM") == 1)
        .then(pl.lit("lab_am_peak"))
        .when(pl.col("DUMMY_LAB_PT") == 1)
        .then(pl.lit("lab_pm_peak"))
        .when(pl.col("DUMMY_LAB_VALLE") == 1)
        .then(pl.lit("lab_valle"))
        .when(pl.col("DUMMY_NO_LAB") == 1)
        .then(pl.lit("no_lab"))
        .otherwise(pl.lit("unknown_time"))
        .alias(alias)
    )


def assert_no_target_leakage(feature_cols: Iterable[str]) -> None:
    offenders: list[str] = []
    for col in feature_cols:
        tokens = set(re.split(r"[^a-z0-9]+", col.lower()))
        if tokens & TARGET_LEAKAGE_TOKENS:
            offenders.append(col)
    if offenders:
        raise ValueError(f"Feature inventory contiene posibles leaks de target: {offenders}")


def min_across_columns(df: pl.DataFrame, cols: list[str]) -> float:
    if not cols:
        return 0.0
    values = df.select([pl.col(c).min().alias(c) for c in cols]).row(0, named=False)
    valid = [float(v) for v in values if v is not None]
    return min(valid) if valid else 0.0


def normalize_feature_block(df: pl.DataFrame, feature_cols: list[str], normalization: str) -> pl.DataFrame:
    if normalization == "count":
        return df
    if normalization != "share":
        raise ValueError(f"normalization no soportada: {normalization}")

    row_sum = pl.sum_horizontal([pl.col(c) for c in feature_cols])
    return df.with_columns(row_sum.alias("_seg_row_sum")).with_columns(
        [
            pl.when(pl.col("_seg_row_sum") > 0)
            .then(pl.col(c) / pl.col("_seg_row_sum"))
            .otherwise(0.0)
            .alias(c)
            for c in feature_cols
        ]
    ).drop("_seg_row_sum")


def load_universe_metadata(path: Path) -> pl.DataFrame:
    schema_names = set(pl.scan_parquet(path).collect_schema().names())
    cols = [c for c in BASE_METADATA_COLS if c in schema_names]
    missing = sorted({"id_tarjeta", *TARGET_METADATA_COLS, "n_viajes"} - set(cols))
    if missing:
        raise ValueError(f"Matriz universo sin columnas requeridas: {missing}")
    meta = pl.read_parquet(path, columns=cols).with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
    n_rows = meta.height
    n_unique = meta.select(pl.col("id_tarjeta").n_unique()).item()
    if n_rows != n_unique:
        raise ValueError(f"Universo con id_tarjeta duplicado: {n_unique} de {n_rows}")
    return meta


def scan_week_trips(week: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[week]
    lf = pl.scan_parquet(path)
    schema = set(lf.collect_schema().names())
    required = {"id_tarjeta", "tiempo_inicio_viaje", "tipodia", "zona_inicio_viaje", *TRANSPORT_COLS}
    missing = sorted(required - schema)
    if missing:
        raise ValueError(f"{path.name}: faltan columnas requeridas: {missing}")

    lf = lf.select(
        [
            pl.col("id_tarjeta").cast(pl.Utf8),
            pl.col("tiempo_inicio_viaje").cast(pl.Datetime, strict=False),
            pl.col("tipodia"),
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False),
            *[pl.col(c).cast(pl.Utf8, strict=False) for c in TRANSPORT_COLS],
        ]
    ).drop_nulls(["id_tarjeta", "tiempo_inicio_viaje"])
    lf = add_time_dummies_v2(lf)
    return lf.with_columns([pl.lit(week).alias("partition"), mode_coarse_expr(), time_band_expr()])


def scan_scope_trips(scope: str) -> pl.LazyFrame:
    return pl.concat([scan_week_trips(w) for w in SCOPE_WEEKS[scope]], how="diagonal_relaxed")


def build_pattern_counts(scope: str, eligible_ids: pl.DataFrame) -> pl.DataFrame:
    macro_lookup = (
        build_macrozone_lookup()
        .select(["ZONA777", "macrozone_model"])
        .rename({"ZONA777": "zona_inicio_viaje", "macrozone_model": "origin_macrozone"})
        .lazy()
    )
    trips = (
        scan_scope_trips(scope)
        .join(eligible_ids.lazy().select("id_tarjeta"), on="id_tarjeta", how="inner")
        .join(macro_lookup, on="zona_inicio_viaje", how="left")
        .with_columns(
            [
                pl.col("origin_macrozone").fill_null("UNKNOWN"),
                (
                    pl.lit("seg_")
                    + sanitize_token_expr(pl.col("origin_macrozone"))
                    + pl.lit("__")
                    + sanitize_token_expr(pl.col("time_band"))
                    + pl.lit("__")
                    + sanitize_token_expr(pl.col("mode_coarse"))
                ).alias("seg_pattern"),
            ]
        )
    )
    return collect_streaming(trips.group_by(["id_tarjeta", "seg_pattern"]).agg(pl.len().alias("n_trips_pattern")))


def pivot_counts(counts: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    if counts.is_empty():
        return pl.DataFrame({"id_tarjeta": []}, schema={"id_tarjeta": pl.Utf8}), []
    wide = counts.pivot(
        values="n_trips_pattern",
        index="id_tarjeta",
        on="seg_pattern",
        aggregate_function="sum",
    )
    feature_cols = sorted([c for c in wide.columns if c != "id_tarjeta"])
    wide = wide.select(["id_tarjeta", *feature_cols]).with_columns([pl.col(c).fill_null(0).cast(pl.Float32) for c in feature_cols])
    assert_no_target_leakage(feature_cols)
    return wide, feature_cols


def assemble_matrix(meta: pl.DataFrame, wide: pl.DataFrame, feature_cols: list[str], normalization: str) -> pl.DataFrame:
    matrix = meta.join(wide, on="id_tarjeta", how="left")
    if feature_cols:
        matrix = matrix.with_columns([pl.col(c).fill_null(0).cast(pl.Float32) for c in feature_cols])
        matrix = normalize_feature_block(matrix, feature_cols, normalization)
    return matrix


def write_audits(matrix: pl.DataFrame, feature_cols: list[str], out_path: Path, *, normalization: str, matrix_spec: str) -> None:
    n_rows = matrix.height
    n_features = len(feature_cols)
    if n_features:
        feature_df = matrix.select(feature_cols)
        zero_counts = feature_df.select([(pl.col(c) == 0).sum().alias(c) for c in feature_cols]).row(0, named=False)
        zero_cells = int(sum(zero_counts))
        total_cells = n_rows * n_features
        row_sums = matrix.select(pl.sum_horizontal([pl.col(c) for c in feature_cols]).alias("row_sum"))["row_sum"]
        nnz_by_row = matrix.select(pl.sum_horizontal([(pl.col(c) > 0).cast(pl.Int16) for c in feature_cols]).alias("nnz"))["nnz"]
        zero_mass_cards = int((row_sums == 0).sum())
        sparsity = zero_cells / total_cells if total_cells else 0.0
        row_sum_min = float(row_sums.min() or 0.0)
        row_sum_max = float(row_sums.max() or 0.0)
        nnz_mean = float(nnz_by_row.mean() or 0.0)
    else:
        zero_mass_cards = n_rows
        sparsity = 1.0
        row_sum_min = 0.0
        row_sum_max = 0.0
        nnz_mean = 0.0

    summary = [
        {"metric": "matrix_spec", "value": matrix_spec},
        {"metric": "normalization", "value": normalization},
        {"metric": "n_cards", "value": str(n_rows)},
        {"metric": "n_features", "value": str(n_features)},
        {"metric": "n_duplicate_id_tarjeta", "value": str(n_rows - matrix.select(pl.col("id_tarjeta").n_unique()).item())},
        {"metric": "zero_mass_cards", "value": str(zero_mass_cards)},
        {"metric": "sparsity", "value": f"{sparsity:.8f}"},
        {"metric": "row_sum_min", "value": f"{row_sum_min:.8f}"},
        {"metric": "row_sum_max", "value": f"{row_sum_max:.8f}"},
        {"metric": "nnz_features_per_card_mean", "value": f"{nnz_mean:.8f}"},
    ]
    if "is_qr" in matrix.columns:
        summary.append({"metric": "qr_share", "value": f"{float(matrix['is_qr'].mean()):.8f}"})
    pl.DataFrame(summary).write_csv(audit_path(out_path, "summary"))

    if feature_cols:
        dist = []
        for c in feature_cols:
            s = matrix[c]
            dist.append(
                {
                    "feature": c,
                    "sum": float(s.sum()),
                    "mean": float(s.mean()),
                    "max": float(s.max()),
                    "nonzero_cards": int((s > 0).sum()),
                    "nonzero_share": float((s > 0).mean()),
                }
            )
        pl.DataFrame(dist).sort("sum", descending=True).write_csv(audit_path(out_path, "feature_distribution"))


def write_inventory(
    out_path: Path,
    feature_cols: list[str],
    metadata_cols: list[str],
    *,
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    matrix_spec: str,
    normalization: str,
) -> None:
    payload = {
        "scope": scope,
        "variant": variant,
        "home_filter": home_filter,
        "min_trips": min_trips,
        "min_home_trips": min_home_trips,
        "matrix_spec": matrix_spec,
        "normalization": normalization,
        "matrix_path": str(out_path),
        "feature_cols": feature_cols,
        "metadata_cols": metadata_cols,
        "target_metadata_cols": [c for c in TARGET_METADATA_COLS if c in metadata_cols],
        "target_leakage_policy": "feature_cols must not include target/payment tokens; target columns metadata only",
    }
    inventory_path(out_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_matrix(
    *,
    scope: str,
    variant: str,
    home_filter: str,
    min_trips: int,
    min_home_trips: int,
    matrix_spec: str,
    normalization: str,
    force: bool,
) -> Path:
    validate_args(scope, variant, home_filter, matrix_spec, normalization)
    universe_path = model_matrix_path(scope, variant, home_filter, min_trips, min_home_trips)
    assert_inputs(scope, universe_path)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_path = output_path(scope, variant, home_filter, min_trips, min_home_trips, matrix_spec, normalization)
    if out_path.exists() and not force:
        print(f"OK exists: {out_path}")
        return out_path

    print(f"Construyendo matriz segmentacion {matrix_spec}/{normalization}")
    print(f"Universo: {universe_path}")
    meta = load_universe_metadata(universe_path)
    counts = build_pattern_counts(scope, meta.select("id_tarjeta"))
    wide, feature_cols = pivot_counts(counts)
    matrix = assemble_matrix(meta, wide, feature_cols, normalization)

    n_rows = matrix.height
    n_unique = matrix.select(pl.col("id_tarjeta").n_unique()).item()
    if n_rows != n_unique:
        raise ValueError(f"Output con id_tarjeta duplicado: {n_unique} de {n_rows}")
    if feature_cols:
        min_value = min_across_columns(matrix, feature_cols)
        if min_value < 0:
            raise ValueError(f"Output contiene features negativas: min={min_value}")

    matrix.write_parquet(out_path, compression="zstd")
    write_inventory(
        out_path,
        feature_cols,
        [c for c in matrix.columns if c not in feature_cols],
        scope=scope,
        variant=variant,
        home_filter=home_filter,
        min_trips=min_trips,
        min_home_trips=min_home_trips,
        matrix_spec=matrix_spec,
        normalization=normalization,
    )
    write_audits(matrix, feature_cols, out_path, normalization=normalization, matrix_spec=matrix_spec)
    print(f"OK: {out_path}")
    print(f"rows={matrix.height:,} features={len(feature_cols):,}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build user mobility matrices for NMF/SVD segmentation.")
    parser.add_argument("--scope", choices=SCOPE_CHOICES, default="interannual_ml")
    parser.add_argument("--variant", choices=VARIANT_CHOICES, default="clean")
    parser.add_argument("--home-filter", choices=sorted(HOME_FILTERS), default="alta")
    parser.add_argument("--min-trips", type=int, default=3)
    parser.add_argument("--min-home-trips", type=int, default=0)
    parser.add_argument("--matrix-spec", choices=sorted(MATRIX_SPECS), default="macro_franja_modo")
    parser.add_argument("--normalization", choices=sorted(NORMALIZATIONS), default="share")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    build_matrix(
        scope=args.scope,
        variant=args.variant,
        home_filter=args.home_filter,
        min_trips=args.min_trips,
        min_home_trips=args.min_home_trips,
        matrix_spec=args.matrix_spec,
        normalization=args.normalization,
        force=args.force,
    )


if __name__ == "__main__":
    main()
