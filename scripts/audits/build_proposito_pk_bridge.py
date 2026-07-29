from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_VIAJES_DIR = Path("/Volumes/TOSHIBA EXT/Vicente/tesis-project/raw/raw_csv/viajes")
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "proposito_residence" / "pk_bridge"

ACTIVE_MODEL_WEEKS = {"2024-W17", "2025-W17"}
ML_REFERENCE_WEEKS = {"2025-W14", "2025-W15", "2025-W17"}
INTERANNUAL_ML_WEEKS = {
    "2024-W14",
    "2024-W15",
    "2024-W16",
    "2024-W17",
    "2025-W14",
    "2025-W15",
    "2025-W16",
    "2025-W17",
}
PROCESSED_TRIPS_BY_WEEK = {
    "2024-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W14.parquet",
    "2024-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W15.parquet",
    "2024-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W16.parquet",
    "2024-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2024-W17.parquet",
    "2025-W14": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W14.parquet",
    "2025-W15": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W15.parquet",
    "2025-W16": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W16.parquet",
    "2025-W17": PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W17.parquet",
}

RAW_COLUMNS = [
    "tipodia",
    "tiempo_inicio_viaje",
    "tiempo_subida_1",
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
SCHEMA_OVERRIDES = {c: pl.Utf8 for c in RAW_COLUMNS}

NATURAL_JOIN_KEYS = [
    "id_tarjeta_key",
    "id_viaje_key",
    "ts_inicio_min_key",
    "semana_iso_key",
]


def weeks_for_scope(scope: str) -> set[str]:
    if scope == "active":
        return ACTIVE_MODEL_WEEKS
    if scope == "ml_2025":
        return ML_REFERENCE_WEEKS
    if scope == "active_ml":
        return ACTIVE_MODEL_WEEKS | ML_REFERENCE_WEEKS
    if scope == "interannual_ml":
        return INTERANNUAL_ML_WEEKS
    raise ValueError(f"Scope no soportado: {scope}")


def scope_suffix(scope: str) -> str:
    return scope


def raw_pk_path(scope: str) -> Path:
    return OUT_DIR / f"raw_viajes_proposito_pk_{scope_suffix(scope)}.parquet"


def bridge_path(scope: str) -> Path:
    return OUT_DIR / f"processed_trip_proposito_bridge_{scope_suffix(scope)}.parquet"


def home_candidates_path(scope: str) -> Path:
    return OUT_DIR / f"user_home_candidates_{scope_suffix(scope)}.parquet"


def week_from_filename(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        raise ValueError(f"No se pudo extraer fecha desde {path}")
    day = dt.date.fromisoformat(match.group(1))
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def date_from_filename(path: Path) -> str:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
    if not match:
        raise ValueError(f"No se pudo extraer fecha desde {path}")
    return match.group(1)


def list_raw_files(scope: str, raw_viajes_dir: Path = RAW_VIAJES_DIR) -> pl.DataFrame:
    files = sorted(p for p in raw_viajes_dir.glob("*.viajes.csv") if not p.name.startswith("._"))
    if not files:
        raise FileNotFoundError(f"No se encontraron CSV raw de viajes en {raw_viajes_dir}")
    weeks = weeks_for_scope(scope)

    df = pl.DataFrame(
        [
            {
                "path": str(path),
                "filename": path.name,
                "raw_date": date_from_filename(path),
                "semana_iso": week_from_filename(path),
            }
            for path in files
        ]
    )
    df = df.filter(pl.col("semana_iso").is_in(sorted(weeks))).sort("filename")
    if df.is_empty():
        raise FileNotFoundError(f"No hay CSV raw para scope={scope}: {sorted(weeks)}")
    return df


def fix_ddmmyy_to_iso_expr(expr: pl.Expr) -> pl.Expr:
    s = expr.cast(pl.Utf8).str.strip_chars()
    s = s.str.replace_all(r"^(\d{2})[-/](\d{2})[-/](\d{2})", r"20$3-$2-$1")
    s = s.str.replace_all(r"^(\d{2})[-/](\d{2})[-/](\d{4})", r"$3-$2-$1")
    s = s.str.replace_all(r"\s+", " ")
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ]
    tries = [s.str.strptime(pl.Datetime, format=f, strict=False, exact=False) for f in formats]
    return pl.coalesce(tries)


def norm_ts_min_expr(expr: pl.Expr) -> pl.Expr:
    return fix_ddmmyy_to_iso_expr(expr).dt.strftime("%Y-%m-%d %H:%M")


def normalize_proposito_expr() -> pl.Expr:
    return (
        pl.col("proposito")
        .cast(pl.Utf8)
        .str.strip_chars()
        .str.to_uppercase()
        .str.replace_all(r"\s+", " ")
        .alias("proposito_norm")
    )


def add_pk_viaje_exprs() -> list[pl.Expr]:
    ts_any = pl.coalesce([pl.col("tiempo_inicio_viaje"), pl.col("tiempo_subida_1")])
    return [
        norm_ts_min_expr(ts_any).alias("ts_inicio_min"),
    ]


def add_pk_viaje(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(add_pk_viaje_exprs()).with_columns(
        pl.struct(
            [
                pl.col("id_tarjeta").cast(pl.Utf8, strict=False),
                pl.col("id_viaje").cast(pl.Int64, strict=False),
                pl.col("ts_inicio_min"),
            ]
        )
        .hash(seed=42)
        .alias("pk_viaje")
    )


def read_raw_csv_minimal(path: str, semana_iso: str, raw_date: str) -> pl.DataFrame:
    df = pl.read_csv(
        path,
        separator="|",
        has_header=True,
        null_values=["", "-", "NA", "N/A", "null", "NULL"],
        schema_overrides=SCHEMA_OVERRIDES,
        infer_schema_length=0,
        columns=RAW_COLUMNS,
        low_memory=True,
    ).with_columns(
        [
            pl.lit(raw_date).alias("raw_date"),
            pl.lit(semana_iso).alias("semana_iso"),
            normalize_proposito_expr(),
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_i"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_i"),
            pl.col("id_viaje").cast(pl.Int64, strict=False).alias("id_viaje_i"),
        ]
    )
    return add_pk_viaje(df).select(
        [
            "pk_viaje",
            "id_tarjeta",
            "id_viaje",
            "id_viaje_i",
            "ts_inicio_min",
            "tiempo_inicio_viaje",
            "tiempo_subida_1",
            "zona_inicio_viaje",
            "zona_fin_viaje",
            "zona_inicio_i",
            "zona_fin_i",
            "contrato",
            "proposito",
            "proposito_norm",
            "periodo_inicio_viaje",
            "periodo_fin_viaje",
            "raw_date",
            "semana_iso",
        ]
    )


def write_csv(df: pl.DataFrame, filename: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    df.write_csv(path)
    return path


def build_raw_pk_artifact(file_index: pl.DataFrame, *, scope: str, force: bool) -> Path:
    out_path = raw_pk_path(scope)
    if out_path.exists() and not force:
        print(f"ℹ️ Reusando raw PK existente: {out_path}")
        return out_path

    parts_dir = OUT_DIR / f"raw_viajes_proposito_pk_parts_{scope_suffix(scope)}"
    parts_dir.mkdir(parents=True, exist_ok=True)
    part_paths = []
    for idx, row in enumerate(file_index.iter_rows(named=True), start=1):
        print(f"ℹ️ Leyendo raw y reconstruyendo pk_viaje: {row['filename']}")
        part_path = parts_dir / f"{idx:03d}_{row['raw_date']}.parquet"
        if part_path.exists():
            part_path.unlink()
        read_raw_csv_minimal(row["path"], row["semana_iso"], row["raw_date"]).write_parquet(
            part_path,
            compression="zstd",
        )
        part_paths.append(part_path)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    pl.concat([pl.scan_parquet(p) for p in part_paths], how="diagonal_relaxed").sink_parquet(
        out_path,
        compression="zstd",
    )
    print(f"✅ Raw con pk_viaje escrito en: {out_path}")
    return out_path


def diagnose_raw_pk(raw_path: Path, *, scope: str) -> None:
    key_cols = [
        "id_tarjeta",
        "id_viaje_i",
        "ts_inicio_min",
        "zona_inicio_i",
        "zona_fin_i",
        "proposito_norm",
        "semana_iso",
    ]

    lf_raw = pl.scan_parquet(raw_path)
    df_dup_counts = (
        lf_raw.group_by("pk_viaje")
        .agg(
            [
                pl.len().alias("n_rows"),
                *[pl.col(c).n_unique().alias(f"{c}_n_unique") for c in key_cols],
            ]
        )
        .filter(pl.col("n_rows") > 1)
        .sort("n_rows", descending=True)
        .collect()
    )
    duplicate_filename = f"raw_pk_duplicate_counts_sample_{scope_suffix(scope)}.csv"
    conflict_filename = f"raw_pk_conflicts_sample_{scope_suffix(scope)}.csv"
    write_csv(df_dup_counts.head(1000), duplicate_filename)

    conflict_expr = pl.any_horizontal([pl.col(f"{c}_n_unique") > 1 for c in key_cols])
    df_conflicts = df_dup_counts.filter(conflict_expr)
    write_csv(df_conflicts.head(1000), conflict_filename)
    if scope == "active":
        write_csv(df_dup_counts.head(1000), "raw_pk_duplicate_counts_sample.csv")
        write_csv(df_conflicts.head(1000), "raw_pk_conflicts_sample.csv")
    if df_conflicts.height > 0:
        raise ValueError(
            "Hay pk_viaje duplicadas en raw con conflictos de campos clave. "
            f"Ver {OUT_DIR / conflict_filename}"
        )

    if df_dup_counts.height > 0:
        print(
            "⚠️ Se encontraron pk_viaje duplicadas exactas en raw; "
            "se deduplican conservando una fila por pk_viaje."
        )


def scan_processed_trips(semana_iso: str) -> pl.LazyFrame:
    path = PROCESSED_TRIPS_BY_WEEK[semana_iso]
    if not path.exists():
        raise FileNotFoundError(f"No existe viaje procesado para {semana_iso}: {path}")
    print(f"ℹ️ Leyendo viajes procesados: {path.name}")
    ts_any = pl.coalesce([pl.col("tiempo_inicio_viaje"), pl.col("tiempo_subida_1")])
    return pl.scan_parquet(path).with_columns(
        norm_ts_min_expr(ts_any).alias("ts_inicio_min_processed")
    ).select(
        [
            pl.col("pk_viaje"),
            pl.col("id_tarjeta").cast(pl.Utf8, strict=False).alias("id_tarjeta_processed"),
            pl.col("id_viaje").cast(pl.Int64, strict=False).alias("id_viaje_processed"),
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_processed"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_processed"),
            pl.lit(semana_iso).alias("semana_iso_processed"),
            pl.col("id_tarjeta").cast(pl.Utf8, strict=False).alias("id_tarjeta_key"),
            pl.col("id_viaje").cast(pl.Int64, strict=False).alias("id_viaje_key"),
            pl.col("ts_inicio_min_processed").alias("ts_inicio_min_key"),
            pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_key"),
            pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_key"),
            pl.lit(semana_iso).alias("semana_iso_key"),
        ]
    )


def validate_natural_key_uniqueness(lf: pl.LazyFrame, label: str) -> None:
    duplicate_keys = (
        lf.group_by(NATURAL_JOIN_KEYS)
        .agg(pl.len().alias("n_rows"))
        .filter(pl.col("n_rows") > 1)
        .sort("n_rows", descending=True)
        .collect()
    )
    write_csv(duplicate_keys.head(1000), f"{label}_natural_key_duplicates_sample.csv")
    if duplicate_keys.height > 0:
        raise ValueError(
            f"La llave natural no es unica para {label}; el join podria duplicar filas. "
            f"Ver {OUT_DIR / f'{label}_natural_key_duplicates_sample.csv'}"
        )


def build_bridge_for_week(semana_iso: str, raw_path: Path, *, scope: str, min_match_rate: float) -> Path:
    week_out = OUT_DIR / f"processed_trip_proposito_bridge_{scope_suffix(scope)}_{semana_iso}.parquet"
    scoped_week = f"{scope_suffix(scope)}_{semana_iso}"
    raw_cols = [
        pl.col("pk_viaje").alias("pk_viaje_reconstructed"),
        "id_tarjeta",
        "id_viaje_i",
        "ts_inicio_min",
        "zona_inicio_i",
        "zona_fin_i",
        "proposito",
        "proposito_norm",
        "periodo_inicio_viaje",
        "periodo_fin_viaje",
        "raw_date",
        "semana_iso",
        pl.col("id_tarjeta").cast(pl.Utf8, strict=False).alias("id_tarjeta_key"),
        pl.col("id_viaje_i").cast(pl.Int64, strict=False).alias("id_viaje_key"),
        pl.col("ts_inicio_min").alias("ts_inicio_min_key"),
        pl.col("zona_inicio_i").cast(pl.Int64, strict=False).alias("zona_inicio_key"),
        pl.col("zona_fin_i").cast(pl.Int64, strict=False).alias("zona_fin_key"),
        pl.col("semana_iso").alias("semana_iso_key"),
    ]
    raw_week = (
        pl.scan_parquet(raw_path)
        .filter(pl.col("semana_iso") == semana_iso)
        .select(raw_cols)
        .unique(NATURAL_JOIN_KEYS, keep="first")
    )
    processed_week = scan_processed_trips(semana_iso)
    validate_natural_key_uniqueness(processed_week, f"processed_{scoped_week}")
    validate_natural_key_uniqueness(raw_week, f"raw_{scoped_week}")
    bridge = processed_week.join(raw_week, on=NATURAL_JOIN_KEYS, how="left")

    matched = pl.col("id_tarjeta").is_not_null()
    df_diagnostics = bridge.select(
        [
            pl.len().alias("n_processed_rows"),
            pl.col("pk_viaje").n_unique().alias("n_processed_pk_unique"),
            pl.col("id_tarjeta").is_not_null().sum().alias("n_matched_raw"),
            pl.col("id_tarjeta").is_null().sum().alias("n_unmatched_raw"),
            pl.col("id_tarjeta").is_not_null().mean().alias("match_rate_processed_to_raw"),
            (pl.col("pk_viaje") == pl.col("pk_viaje_reconstructed"))
            .fill_null(False)
            .sum()
            .alias("n_reconstructed_pk_equals_processed_pk"),
            ((pl.col("id_tarjeta_processed") != pl.col("id_tarjeta")).fill_null(False) & matched)
            .sum()
            .alias("n_id_tarjeta_mismatch"),
            ((pl.col("id_viaje_processed") != pl.col("id_viaje_i")).fill_null(False) & matched)
            .sum()
            .alias("n_id_viaje_mismatch"),
            ((pl.col("zona_inicio_processed") != pl.col("zona_inicio_i")).fill_null(False) & matched)
            .sum()
            .alias("n_zona_inicio_mismatch"),
            ((pl.col("zona_fin_processed") != pl.col("zona_fin_i")).fill_null(False) & matched)
            .sum()
            .alias("n_zona_fin_mismatch"),
        ]
    ).collect()
    df_diagnostics = df_diagnostics.with_columns(pl.lit(semana_iso).alias("semana_iso"))
    write_csv(df_diagnostics, f"bridge_join_diagnostics_{scoped_week}.csv")

    match_rate = float(df_diagnostics.get_column("match_rate_processed_to_raw")[0])
    if match_rate < min_match_rate:
        unmatched = bridge.filter(pl.col("id_tarjeta").is_null()).head(1000).collect()
        write_csv(unmatched, f"bridge_unmatched_processed_sample_{scoped_week}.csv")
        raise ValueError(
            f"Match procesado→raw por pk_viaje bajo umbral en {semana_iso}: "
            f"{match_rate:.6%} < {min_match_rate:.6%}. "
            f"Ver {OUT_DIR / f'bridge_unmatched_processed_sample_{scoped_week}.csv'}"
        )
    write_csv(
        bridge.filter(pl.col("id_tarjeta").is_null()).head(0).collect(),
        f"bridge_unmatched_processed_sample_{scoped_week}.csv",
    )

    mismatch_cols = [
        "n_id_tarjeta_mismatch",
        "n_id_viaje_mismatch",
    ]
    mismatch_total = sum(int(df_diagnostics.get_column(c)[0]) for c in mismatch_cols)
    if mismatch_total:
        mismatches = (
            bridge.filter(
                (((pl.col("id_tarjeta_processed") != pl.col("id_tarjeta")).fill_null(False)) & matched)
                | (((pl.col("id_viaje_processed") != pl.col("id_viaje_i")).fill_null(False)) & matched)
            )
            .head(1000)
            .collect()
        )
        write_csv(mismatches, f"bridge_key_mismatches_sample_{scoped_week}.csv")
        raise ValueError(
            f"El join por pk_viaje tiene inconsistencias en campos clave para {semana_iso}. "
            f"Ver {OUT_DIR / f'bridge_key_mismatches_sample_{scoped_week}.csv'}"
        )
    write_csv(
        bridge.filter(
            (((pl.col("id_tarjeta_processed") != pl.col("id_tarjeta")).fill_null(False)) & matched)
            | (((pl.col("id_viaje_processed") != pl.col("id_viaje_i")).fill_null(False)) & matched)
        )
        .head(0)
        .collect(),
        f"bridge_key_mismatches_sample_{scoped_week}.csv",
    )

    zone_mismatch_total = int(df_diagnostics.get_column("n_zona_inicio_mismatch")[0]) + int(
        df_diagnostics.get_column("n_zona_fin_mismatch")[0]
    )
    zone_mismatch_sample = (
        bridge.filter(
            (((pl.col("zona_inicio_processed") != pl.col("zona_inicio_i")).fill_null(False)) & matched)
            | (((pl.col("zona_fin_processed") != pl.col("zona_fin_i")).fill_null(False)) & matched)
        )
        .head(1000 if zone_mismatch_total else 0)
        .collect()
    )
    write_csv(zone_mismatch_sample, f"bridge_zone_mismatches_sample_{scoped_week}.csv")

    if week_out.exists():
        week_out.unlink()
    bridge.sink_parquet(week_out, compression="zstd")
    print(f"✅ Bridge semanal escrito en: {week_out}")
    return week_out


def build_bridge(raw_path: Path, *, scope: str, min_match_rate: float) -> Path:
    weeks = weeks_for_scope(scope)
    week_paths = [
        build_bridge_for_week(semana_iso, raw_path, scope=scope, min_match_rate=min_match_rate)
        for semana_iso in sorted(weeks)
    ]
    out_path = bridge_path(scope)
    if out_path.exists():
        out_path.unlink()
    pl.concat([pl.scan_parquet(p) for p in week_paths], how="diagonal_relaxed").sink_parquet(
        out_path,
        compression="zstd",
    )
    diagnostics = pl.concat(
        [
            pl.read_csv(OUT_DIR / f"bridge_join_diagnostics_{scope_suffix(scope)}_{week}.csv")
            for week in sorted(weeks)
        ],
        how="diagonal_relaxed",
    )
    write_csv(diagnostics, f"bridge_join_diagnostics_{scope_suffix(scope)}.csv")
    if scope == "active":
        write_csv(diagnostics, "bridge_join_diagnostics.csv")
    print(f"✅ Bridge procesado + proposito escrito en: {out_path}")
    return out_path


def build_user_home_candidates(bridge_artifact_path: Path, *, scope: str) -> pl.DataFrame:
    hogar = pl.scan_parquet(bridge_artifact_path).filter(
        (pl.col("proposito_norm") == "HOGAR")
        & pl.col("id_tarjeta").is_not_null()
        & pl.col("zona_fin_i").is_not_null()
    )
    home_counts = hogar.group_by(["id_tarjeta", "zona_fin_i"]).agg(pl.len().alias("n_home_dest_trips"))
    card_totals = hogar.group_by("id_tarjeta").agg(pl.len().alias("n_home_dest_trips_card"))

    ranked = home_counts.sort(
        ["id_tarjeta", "n_home_dest_trips", "zona_fin_i"],
        descending=[False, True, False],
    )
    top = (
        ranked.group_by("id_tarjeta")
        .agg(
            [
                pl.col("zona_fin_i").first().alias("zona_hogar"),
                pl.col("n_home_dest_trips").first().alias("n_home_dest_trips_top"),
                pl.col("zona_fin_i").n_unique().alias("n_home_zones_observed"),
                pl.col("n_home_dest_trips").max().alias("n_home_dest_trips_max"),
                (pl.col("n_home_dest_trips") == pl.col("n_home_dest_trips").max()).sum().alias("n_top_tied_zones"),
            ]
        )
        .join(card_totals, on="id_tarjeta", how="left")
        .with_columns(
            (pl.col("n_home_dest_trips_top") / pl.col("n_home_dest_trips_card")).alias("home_zone_top_share")
        )
        .with_columns((pl.col("n_top_tied_zones") > 1).alias("has_home_zone_tie"))
        .with_columns(
            pl.when(pl.col("has_home_zone_tie"))
            .then(pl.lit("baja"))
            .when((pl.col("n_home_zones_observed") == 1) | (pl.col("home_zone_top_share") >= 0.80))
            .then(pl.lit("alta"))
            .when(pl.col("home_zone_top_share") >= 0.60)
            .then(pl.lit("media"))
            .otherwise(pl.lit("baja"))
            .alias("home_confidence")
        )
        .sort("id_tarjeta")
    )

    top = top.collect()
    out_path = home_candidates_path(scope)
    top.write_parquet(out_path, compression="zstd")
    write_csv(
        top.group_by("home_confidence")
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("n_home_dest_trips_card").sum().alias("n_home_dest_trips"),
                pl.col("home_zone_top_share").mean().alias("mean_top_share"),
                pl.col("home_zone_top_share").median().alias("median_top_share"),
            ]
        )
        .sort("home_confidence"),
        f"home_confidence_distribution_{scope_suffix(scope)}.csv",
    )
    if scope == "active":
        write_csv(
            top.group_by("home_confidence")
            .agg(
                [
                    pl.len().alias("n_cards"),
                    pl.col("n_home_dest_trips_card").sum().alias("n_home_dest_trips"),
                    pl.col("home_zone_top_share").mean().alias("mean_top_share"),
                    pl.col("home_zone_top_share").median().alias("median_top_share"),
                ]
            )
            .sort("home_confidence"),
            "home_confidence_distribution.csv",
        )
    print(f"✅ Candidatos de residencia escritos en: {out_path}")
    return top


def write_summary(raw_path: Path, bridge_artifact_path: Path, home: pl.DataFrame, *, scope: str) -> None:
    raw_counts = pl.scan_parquet(raw_path).select(
        [
            pl.len().alias("raw_rows"),
            pl.col("pk_viaje").n_unique().alias("raw_unique_pk_rows"),
        ]
    ).collect()
    bridge_counts = pl.scan_parquet(bridge_artifact_path).select(
        [
            pl.len().alias("processed_rows"),
            pl.col("id_tarjeta").is_not_null().sum().alias("bridge_matched_rows"),
        ]
    ).collect()
    summary = pl.DataFrame(
        [
            {
                "scope": scope,
                "raw_rows": int(raw_counts.get_column("raw_rows")[0]),
                "raw_unique_pk_rows": int(raw_counts.get_column("raw_unique_pk_rows")[0]),
                "processed_rows": int(bridge_counts.get_column("processed_rows")[0]),
                "bridge_matched_rows": int(bridge_counts.get_column("bridge_matched_rows")[0]),
                "home_candidate_cards": home.height,
                "home_high_confidence_cards": home.filter(pl.col("home_confidence") == "alta").height,
                "home_medium_confidence_cards": home.filter(pl.col("home_confidence") == "media").height,
                "home_low_confidence_cards": home.filter(pl.col("home_confidence") == "baja").height,
            }
        ]
    )
    write_csv(summary, f"pk_bridge_summary_{scope_suffix(scope)}.csv")
    if scope == "active":
        write_csv(summary, "pk_bridge_summary.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruye pk_viaje desde raw CSV y crea bridge auditable con proposito/residencia."
    )
    parser.add_argument("--scope", choices=["active", "ml_2025", "active_ml", "interannual_ml"], default="active")
    parser.add_argument(
        "--raw-viajes-dir",
        type=Path,
        default=RAW_VIAJES_DIR,
        help="Directorio con CSV raw *.viajes.csv que contiene proposito.",
    )
    parser.add_argument("--force", action="store_true", help="Recrear artefactos aunque ya existan.")
    parser.add_argument(
        "--min-match-rate",
        type=float,
        default=0.9999,
        help="Umbral minimo de match procesado→raw por pk_viaje.",
    )
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    file_index = list_raw_files(args.scope, args.raw_viajes_dir)
    write_csv(file_index, f"raw_file_inventory_{scope_suffix(args.scope)}.csv")
    if args.scope == "active":
        write_csv(file_index, "raw_file_inventory_active.csv")

    raw_path = build_raw_pk_artifact(file_index, scope=args.scope, force=args.force)
    diagnose_raw_pk(raw_path, scope=args.scope)
    bridge_artifact_path = build_bridge(raw_path, scope=args.scope, min_match_rate=args.min_match_rate)
    home = build_user_home_candidates(bridge_artifact_path, scope=args.scope)
    write_summary(raw_path, bridge_artifact_path, home, scope=args.scope)

    print("✅ Bypass PK proposito/residencia completado.")
    print(f"- raw_pk: {raw_path}")
    print(f"- bridge: {bridge_artifact_path}")
    print(f"- home:   {home_candidates_path(args.scope)}")
    print(f"- diag:   {OUT_DIR}")


if __name__ == "__main__":
    main()
