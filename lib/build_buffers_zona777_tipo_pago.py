import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl

# --- Setup repo imports ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config.constants import GCS_RAW_PATH, USE_LOCAL_PATHS, LOCAL_RAW_PATH  # noqa: E402
from lib.datalake import read_parquet_portable, read_csv_portable  # noqa: E402


DEFAULT_CARACTERIZACION_PERIOD = "202504"
CARACTERIZACION_FILENAME = f"caracterización qr_{DEFAULT_CARACTERIZACION_PERIOD}.csv"
NOTEBOOK_LOCAL_ABSPATH = f"/Volumes/KINGSTON/tesis-project/raw/caracterizacion/{CARACTERIZACION_FILENAME}"


def _infer_partition_label_from_path(path: Path) -> str | None:
    m = re.search(r"(\d{4}-W\d{2})", path.name)
    return m.group(1) if m else None


def _period_from_partition_label(partition_label: str | None) -> str:
    if not partition_label:
        return DEFAULT_CARACTERIZACION_PERIOD
    m = re.match(r"(\d{4})-W\d{2}", partition_label)
    if not m:
        return DEFAULT_CARACTERIZACION_PERIOD
    year = m.group(1)
    return f"{year}04"


def _find_local_caracterizacion(raw_base: Path, period: str) -> str:
    target_suffix = f"qr_{period}.csv"
    base_dir = raw_base / "caracterizacion"
    candidates = sorted(p for p in base_dir.glob(f"*{target_suffix}") if p.is_file())
    if candidates:
        return str(candidates[0])
    return str(base_dir / f"caracterización qr_{period}.csv")


def _resolve_caracterizacion_path(explicit_path: str | None, partition_label: str | None = None) -> str:
    if explicit_path:
        return explicit_path

    period = _period_from_partition_label(partition_label)

    if USE_LOCAL_PATHS:
        notebook_candidate = Path(NOTEBOOK_LOCAL_ABSPATH.replace(DEFAULT_CARACTERIZACION_PERIOD, period))
        if notebook_candidate.exists():
            return str(notebook_candidate)
        return _find_local_caracterizacion(Path(LOCAL_RAW_PATH), period)

    return f"{GCS_RAW_PATH}/caracterizacion/caracterización qr_{period}.csv"


def load_caracterizacion(path: str) -> pl.DataFrame:
    df = read_csv_portable(
        path,
        separator=";",
        try_parse_dates=False,
    )
    if "id_interno" not in df.columns or "tipo_app" not in df.columns:
        raise ValueError(f"Caracterización inválida: faltan columnas en {path!r} (se requieren id_interno, tipo_app).")

    # Guardrail: ensure one row per id_tarjeta_str (avoid silent row-duplication on join).
    df = df.with_columns(
        [
            pl.col("id_interno").cast(pl.Utf8).alias("id_tarjeta_str"),
            pl.col("tipo_app").cast(pl.Utf8).alias("tipo_app"),
        ]
    ).select(["id_tarjeta_str", "tipo_app"])

    # Some IDs may appear multiple times; for our purposes we only need to know if the user is "APP RED".
    return df.group_by("id_tarjeta_str").agg(
        pl.when((pl.col("tipo_app") == "APP RED").any())
        .then(pl.lit("APP RED"))
        .otherwise(pl.lit("OTRA APP"))
        .alias("tipo_app")
    )


def _sum_cols(cols: Iterable[str]) -> pl.Expr:
    exprs = [pl.col(c).fill_null(0) for c in cols]
    if not exprs:
        return pl.lit(0)
    out = exprs[0]
    for e in exprs[1:]:
        out = out + e
    return out


@dataclass(frozen=True)
class BuffersConfig:
    input_path: Path
    output_dir: Path
    partition: str
    buffers: str  # inicio|od|both
    with_p90: bool
    limit_rows: int | None
    sample_fraction: float | None
    sample_seed: int
    drop_null_zones: bool
    caracterizacion_path: str
    allow_missing_caracterizacion: bool


def add_tipo_pago(lf: pl.LazyFrame, df_caracterizacion: pl.DataFrame | None) -> pl.LazyFrame:
    lf = lf.with_columns(
        [
            pl.col("is_qr").cast(pl.Boolean, strict=False).alias("is_qr"),
            pl.col("id_tarjeta").cast(pl.Utf8).alias("id_tarjeta_str"),
        ]
    )

    if df_caracterizacion is not None:
        lf = lf.join(df_caracterizacion.lazy(), on="id_tarjeta_str", how="left")
    else:
        lf = lf.with_columns(pl.lit(None).cast(pl.Utf8).alias("tipo_app"))

    return lf.with_columns(
        pl.when(pl.col("is_qr") == False)
        .then(pl.lit("BIP"))
        .when((pl.col("is_qr") == True) & (pl.col("tipo_app") == "APP RED"))
        .then(pl.lit("QR_RED"))
        .when(pl.col("is_qr") == True)
        .then(pl.lit("QR_OTHER"))
        .otherwise(pl.lit("BIP"))
        .cast(pl.Utf8)
        .alias("tipo_pago")
    )


def derive_metrics(lf: pl.LazyFrame, schema_names: set[str]) -> tuple[pl.LazyFrame, dict[str, str]]:
    te_transfer_cols = [f"te{i}_calculado" for i in range(1, 6)]
    tv_cols = [f"tv{i}_calculado" for i in range(1, 7)]

    missing_required = [c for c in ["te0_calculado", "n_etapas_recon"] if c not in schema_names]
    if missing_required:
        raise ValueError(f"Faltan columnas requeridas en parquet: {missing_required}")

    te_transfer_present = [c for c in te_transfer_cols if c in schema_names]
    tv_present = [c for c in tv_cols if c in schema_names]
    if not tv_present:
        raise ValueError(
            "No se encontraron columnas tv*_calculado para construir t_vehiculo_total_seg_final. "
            "Se esperan tv1_calculado..tv6_calculado en el parquet v2."
        )

    out = lf.with_columns(
        [
            pl.col("te0_calculado").alias("t_espera_inicial_seg"),
            _sum_cols(te_transfer_present).alias("t_espera_trasbordo_seg"),
            pl.col("n_etapas_recon").alias("n_etapas"),
            (pl.col("n_etapas_recon") - 1).clip(lower_bound=0).alias("n_trasbordos"),
        ]
    )

    source = {}
    out = out.with_columns(_sum_cols(tv_present).alias("t_vehiculo_total_seg_final"))
    source["t_vehiculo_total_seg_final"] = "sum(tv1..tv6_calculado)"

    return out, source


def _agg_exprs(metric_cols: list[str], with_p90: bool) -> list[pl.Expr]:
    exprs: list[pl.Expr] = [pl.len().alias("n_viajes")]
    for c in metric_cols:
        exprs.extend(
            [
                pl.col(c).mean().alias(f"{c}_mean"),
                pl.col(c).median().alias(f"{c}_median"),
            ]
        )
        if with_p90:
            exprs.append(pl.col(c).quantile(0.9, interpolation="nearest").alias(f"{c}_p90"))
    return exprs


def _add_minutes_columns(df: pl.DataFrame, time_metric_cols: list[str], with_p90: bool) -> pl.DataFrame:
    cols: list[pl.Expr] = []
    suffixes = ["mean", "median"] + (["p90"] if with_p90 else [])
    for c in time_metric_cols:
        for s in suffixes:
            seg = f"{c}_{s}"
            if seg in df.columns:
                cols.append((pl.col(seg) / 60).alias(f"{c}_{s}_min"))
    return df.with_columns(cols) if cols else df


def compute_sanity(lf_before_filter: pl.LazyFrame, lf_after_filter: pl.LazyFrame, drop_null_zones: bool) -> dict:
    out: dict = {}

    out["n_rows_total"] = (
        lf_before_filter.select(pl.len().alias("n")).collect(engine="streaming").row(0, named=True)["n"]
    )
    out["n_rows_after_filter"] = (
        lf_after_filter.select(pl.len().alias("n")).collect(engine="streaming").row(0, named=True)["n"]
    )

    # Null shares for zones
    cols = [c for c in ["zona_inicio_viaje", "zona_fin_viaje"] if c in lf_before_filter.collect_schema().names()]
    if cols:
        exprs = []
        for c in cols:
            exprs.append(pl.col(c).is_null().mean().alias(f"share_null_{c}"))
        out["null_shares"] = lf_before_filter.select(exprs).collect(engine="streaming").row(0, named=True)
    out["drop_null_zones"] = drop_null_zones

    # tipo_pago distribution and consistency with is_qr
    dist = (
        lf_before_filter.group_by(["tipo_pago", "is_qr"])
        .agg(pl.len().alias("n"))
        .sort(["tipo_pago", "is_qr"])
        .collect(engine="streaming")
    )
    out["tipo_pago_is_qr_counts"] = dist.to_dicts()

    # Coverage of caracterizacion among QR
    schema = set(lf_before_filter.collect_schema().names())
    if "tipo_app" in schema:
        cov = (
            lf_before_filter.select(
                [
                    (pl.col("is_qr") == True).sum().alias("n_qr"),
                    (pl.col("is_qr") & pl.col("tipo_app").is_not_null()).sum().alias("n_qr_con_tipo_app"),
                ]
            )
            .collect(engine="streaming")
            .row(0, named=True)
        )
        out["caracterizacion_qr_coverage"] = cov

    # Quick check: vehicle time vs tv-sum (only if original t_vehiculo_total_seg exists)
    if "t_vehiculo_total_seg" in schema and "t_vehiculo_sum_tv_calculado_seg" in schema:
        df_diff = (
            lf_before_filter.select(
                [
                    (pl.col("t_vehiculo_total_seg") - pl.col("t_vehiculo_sum_tv_calculado_seg"))
                    .abs()
                    .mean()
                    .alias("mean_abs_diff_seg"),
                    (pl.col("t_vehiculo_total_seg") - pl.col("t_vehiculo_sum_tv_calculado_seg"))
                    .abs()
                    .quantile(0.9, interpolation="nearest")
                    .alias("p90_abs_diff_seg"),
                ]
            )
            .collect(engine="streaming")
        )
        out["vehiculo_total_vs_tv_sum"] = df_diff.row(0, named=True)

    return out


def build_buffers(cfg: BuffersConfig) -> None:
    input_path = str(cfg.input_path)
    lf_in = read_parquet_portable(input_path)
    schema_names = set(lf_in.collect_schema().names())

    required_base = {"is_qr", "id_tarjeta", "zona_inicio_viaje", "te0_calculado", "n_etapas_recon"}
    missing = sorted([c for c in required_base if c not in schema_names])
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")

    df_caract = None
    try:
        df_caract = load_caracterizacion(cfg.caracterizacion_path)
        print(f"✅ Caracterización cargada: {df_caract.height:,} usuarios únicos ({cfg.caracterizacion_path})")
    except Exception as e:
        if cfg.allow_missing_caracterizacion:
            print(f"⚠️ No se pudo cargar caracterización ({e}). Se clasifica QR como QR_OTHER.")
            df_caract = None
        else:
            raise

    cols_needed = {
        "zona_inicio_viaje",
        "zona_fin_viaje",
        "is_qr",
        "id_tarjeta",
        "te0_calculado",
        "n_etapas_recon",
        "t_vehiculo_total_seg",
        *[f"te{i}_calculado" for i in range(1, 6)],
        *[f"tv{i}_calculado" for i in range(1, 7)],
    }
    cols_present = [c for c in cols_needed if c in schema_names]
    lf = lf_in.select(cols_present)

    if cfg.limit_rows is not None:
        lf = lf.limit(cfg.limit_rows)

    if cfg.sample_fraction is not None:
        lf = lf.sample(fraction=cfg.sample_fraction, seed=cfg.sample_seed, shuffle=True)

    lf = add_tipo_pago(lf, df_caract)
    lf, veh_source = derive_metrics(lf, schema_names)

    lf_before_filter = lf
    if cfg.drop_null_zones:
        if cfg.buffers in ("inicio", "both"):
            lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null())
        if cfg.buffers in ("od", "both"):
            lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())

    sanity = compute_sanity(lf_before_filter=lf_before_filter, lf_after_filter=lf, drop_null_zones=cfg.drop_null_zones)
    print(f"ℹ️  Sanity: {sanity}")
    print(f"ℹ️  Fuente t_vehiculo_total_seg_final: {veh_source.get('t_vehiculo_total_seg_final')}")

    metric_cols = [
        "t_espera_inicial_seg",
        "t_espera_trasbordo_seg",
        "t_vehiculo_total_seg_final",
        "n_etapas",
        "n_trasbordos",
    ]
    time_metric_cols = [
        "t_espera_inicial_seg",
        "t_espera_trasbordo_seg",
        "t_vehiculo_total_seg_final",
    ]

    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    if cfg.buffers in ("inicio", "both"):
        df_inicio = (
            lf.group_by(["zona_inicio_viaje", "tipo_pago"])
            .agg(_agg_exprs(metric_cols, with_p90=cfg.with_p90))
            .collect(engine="streaming")
        )
        df_inicio = _add_minutes_columns(df_inicio, time_metric_cols, with_p90=cfg.with_p90)
        out_inicio = cfg.output_dir / f"buffers_zona777_inicio_tipo_pago_{cfg.partition}.parquet"
        df_inicio.write_parquet(out_inicio, compression="zstd")
        print(f"✅ Escrito: {out_inicio} ({df_inicio.height:,} filas)")

    if cfg.buffers in ("od", "both"):
        if "zona_fin_viaje" not in schema_names:
            raise ValueError("No existe columna zona_fin_viaje; no se puede construir OD buffers.")
        df_od = (
            lf.group_by(["zona_inicio_viaje", "zona_fin_viaje", "tipo_pago"])
            .agg(_agg_exprs(metric_cols, with_p90=cfg.with_p90))
            .collect(engine="streaming")
        )
        df_od = _add_minutes_columns(df_od, time_metric_cols, with_p90=cfg.with_p90)
        out_od = cfg.output_dir / f"buffers_zona777_od_tipo_pago_{cfg.partition}.parquet"
        df_od.write_parquet(out_od, compression="zstd")
        print(f"✅ Escrito: {out_od} ({df_od.height:,} filas)")


def _parse_args() -> BuffersConfig:
    p = argparse.ArgumentParser(description="Construye buffers agregados por zona777 × tipo_pago.")
    p.add_argument(
        "--input",
        dest="input_path",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "viajes_con_te_calculado_2025-W17.parquet",
        help="Parquet semanal v2 de viajes.",
    )
    p.add_argument(
        "--partition",
        type=str,
        default=None,
        help="Etiqueta de partición (ej. 2025-W17). Si no se entrega, se infiere del nombre del input.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "tmp" / "aggregates",
        help="Directorio de salida (no versionar).",
    )
    p.add_argument(
        "--buffers",
        choices=["inicio", "od", "both"],
        default="inicio",
        help="Qué buffers construir: inicio (A), od (C) o both.",
    )
    p.add_argument("--with-p90", action="store_true", help="Incluye p90 (puede ser más lento).")
    p.add_argument("--limit-rows", type=int, default=None, help="Limita filas (smoke run rápido; toma primeras N).")
    p.add_argument("--sample-fraction", type=float, default=None, help="Fracción de muestra (ej. 0.01).")
    p.add_argument("--sample-seed", type=int, default=42)
    p.add_argument("--keep-null-zones", action="store_true", help="No filtra zonas nulas en llaves del group_by.")
    p.add_argument(
        "--caracterizacion-path",
        type=str,
        default=None,
        help="Ruta explícita a la caracterización (CSV). Si no, usa la lógica de notebooks.",
    )
    p.add_argument(
        "--allow-missing-caracterizacion",
        action="store_true",
        help="Si no se puede cargar caracterización, clasifica QR como QR_OTHER (no recomendado).",
    )

    args = p.parse_args()
    part = args.partition or _infer_partition_label_from_path(args.input_path)
    if not part:
        raise ValueError("No se pudo inferir --partition desde el nombre del input; pásalo explícitamente.")

    return BuffersConfig(
        input_path=args.input_path,
        output_dir=args.output_dir,
        partition=part,
        buffers=args.buffers,
        with_p90=bool(args.with_p90),
        limit_rows=args.limit_rows,
        sample_fraction=args.sample_fraction,
        sample_seed=args.sample_seed,
        drop_null_zones=not bool(args.keep_null_zones),
        caracterizacion_path=_resolve_caracterizacion_path(args.caracterizacion_path, partition),
        allow_missing_caracterizacion=bool(args.allow_missing_caracterizacion),
    )


if __name__ == "__main__":
    build_buffers(_parse_args())
