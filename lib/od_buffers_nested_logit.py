from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import HORAS_PUNTA_MANANA, HORAS_PUNTA_TARDE  # noqa: E402
from config.constants import GCS_RAW_PATH, USE_LOCAL_PATHS, LOCAL_RAW_PATH  # noqa: E402
from lib.datalake import read_csv_portable, read_parquet_portable  # noqa: E402


CARACTERIZACION_FILENAME = "caracterización qr_202504.csv"
NOTEBOOK_LOCAL_ABSPATH = "/Volumes/KINGSTON/tesis-project/raw/caracterizacion/caracterización qr_202504.csv"


def _infer_partition_label_from_path(path: Path) -> str | None:
    m = re.search(r"(\d{4}-W\d{2})", path.name)
    return m.group(1) if m else None


def resolve_caracterizacion_path(explicit_path: str | None) -> str:
    if explicit_path:
        return explicit_path

    if USE_LOCAL_PATHS:
        if Path(NOTEBOOK_LOCAL_ABSPATH).exists():
            return NOTEBOOK_LOCAL_ABSPATH
        candidate = Path(LOCAL_RAW_PATH) / "caracterizacion" / CARACTERIZACION_FILENAME
        return str(candidate)

    return f"{GCS_RAW_PATH}/caracterizacion/{CARACTERIZACION_FILENAME}"


def load_caracterizacion(path: str) -> pl.DataFrame:
    df = read_csv_portable(
        path,
        separator=";",
        try_parse_dates=False,
    )
    if "id_interno" not in df.columns or "tipo_app" not in df.columns:
        raise ValueError(
            f"Caracterización inválida: faltan columnas en {path!r} (se requieren id_interno, tipo_app)."
        )

    df = df.with_columns(
        [
            pl.col("id_interno").cast(pl.Utf8).alias("id_tarjeta_str"),
            pl.col("tipo_app").cast(pl.Utf8).alias("tipo_app"),
        ]
    ).select(["id_tarjeta_str", "tipo_app"])

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


def add_time_dummies(lf: pl.LazyFrame) -> pl.LazyFrame:
    lf = lf.with_columns(
        [
            pl.col("tiempo_inicio_viaje").dt.replace_time_zone("America/Santiago", ambiguous="earliest").alias("ts_local"),
        ]
    ).with_columns(
        [
            pl.col("ts_local").dt.hour().alias("hora"),
            pl.col("ts_local").dt.weekday().alias("dia_semana"),
            (pl.col("tipodia").cast(pl.Int8, strict=False) == 0).alias("is_laboral"),
        ]
    ).with_columns(
        [
            pl.col("hora").is_in(HORAS_PUNTA_MANANA).alias("punta_manana"),
            pl.col("hora").is_in(HORAS_PUNTA_TARDE).alias("punta_tarde"),
            (pl.col("dia_semana") == 5).alias("es_viernes"),
            pl.col("dia_semana").is_between(1, 4, closed="both").alias("es_lun_jue"),
        ]
    ).with_columns(
        [
            (pl.col("punta_manana") & pl.col("is_laboral")).cast(pl.Int8).alias("DUMMY_PM_LAB"),
            (pl.col("punta_tarde") & pl.col("is_laboral")).cast(pl.Int8).alias("DUMMY_PT_LAB"),
            (pl.col("es_lun_jue") & pl.col("is_laboral")).cast(pl.Int8).alias("DUMMY_LJ_LAB"),
            (pl.col("es_viernes") & pl.col("is_laboral")).cast(pl.Int8).alias("DUMMY_VIE_LAB"),
        ]
    )
    return lf


def add_time_dummies_v2(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Version 2: dummies exclusivas para facilitar interpretación.

    - DUMMY_LAB_PM: laboral punta mañana
    - DUMMY_LAB_PT: laboral punta tarde
    - DUMMY_LAB_VALLE: laboral fuera de punta
    - DUMMY_NO_LAB: no laboral
    """
    lf = lf.with_columns(
        [
            pl.col("tiempo_inicio_viaje").dt.replace_time_zone("America/Santiago", ambiguous="earliest").alias("ts_local"),
        ]
    ).with_columns(
        [
            pl.col("ts_local").dt.hour().alias("hora"),
            (pl.col("tipodia").cast(pl.Int8, strict=False) == 0).alias("is_laboral"),
        ]
    ).with_columns(
        [
            pl.col("hora").is_in(HORAS_PUNTA_MANANA).alias("punta_manana"),
            pl.col("hora").is_in(HORAS_PUNTA_TARDE).alias("punta_tarde"),
        ]
    ).with_columns(
        [
            (pl.col("is_laboral") & pl.col("punta_manana")).cast(pl.Int8).alias("DUMMY_LAB_PM"),
            (pl.col("is_laboral") & pl.col("punta_tarde")).cast(pl.Int8).alias("DUMMY_LAB_PT"),
            (pl.col("is_laboral") & (~pl.col("punta_manana")) & (~pl.col("punta_tarde"))).cast(pl.Int8).alias("DUMMY_LAB_VALLE"),
            (~pl.col("is_laboral")).cast(pl.Int8).alias("DUMMY_NO_LAB"),
        ]
    )
    return lf


@dataclass(frozen=True)
class OdContextConfig:
    include_time_dummies: bool = False
    time_dummy_variant: str = "v2"
    mean_mode: str = "leave_one_out"  # "inclusive" o "leave_one_out"
    require_all_alternatives: bool = True


OD_KEY_COLS = ["zona_inicio_viaje", "zona_fin_viaje"]
ALT_LEVELS = ["BIP", "QR_RED", "QR_OTHER"]
ALT_CHOICE_MAP = {"BIP": 0, "QR_RED": 1, "QR_OTHER": 2}
ALT_METRIC_SPECS = {
    "t_vehiculo_total_seg_final": "TVH",
    "t_espera_inicial_seg": "TEI",
    "t_espera_trasbordo_seg": "TET",
    "n_trasbordos": "NTR",
}


def build_od_context_table(
    lf: pl.LazyFrame,
    *,
    config: OdContextConfig | None = None,
) -> pl.DataFrame:
    cfg = config or OdContextConfig()
    schema_names = set(lf.collect_schema().names())
    # Traer columnas mínimas + calculadas necesarias (si existen)
    base_cols = [
        "tiempo_inicio_viaje",
        "tipodia",
        "te0_calculado",
        "n_etapas_recon",
        "is_qr",
        "id_tarjeta",
    ]
    te_transfer_cols = [f"te{i}_calculado" for i in range(1, 6)]
    tv_cols = [f"tv{i}_calculado" for i in range(1, 7)]
    cols_needed = OD_KEY_COLS + base_cols + te_transfer_cols + tv_cols
    lf = lf.select([c for c in cols_needed if c in schema_names])
    # Recalcular schema tras el select para evitar referencias a columnas no incluidas
    schema_names = set(lf.collect_schema().names())

    lf, _ = derive_metrics(lf, schema_names)
    if cfg.time_dummy_variant == "v2":
        lf = add_time_dummies_v2(lf)
    else:
        lf = add_time_dummies(lf)

    metric_cols = ["t_vehiculo_total_seg_final", "t_espera_inicial_seg", "t_espera_trasbordo_seg", "n_trasbordos"]
    agg_exprs = [pl.len().alias("od_n_viajes")]
    for c in metric_cols:
        agg_exprs.append(pl.col(c).mean().alias(f"OD_{c}_mean"))
        agg_exprs.append(pl.col(c).sum().alias(f"OD_{c}_sum"))

    if cfg.include_time_dummies:
        if cfg.time_dummy_variant == "v2":
            for d in ["DUMMY_LAB_PM", "DUMMY_LAB_PT", "DUMMY_LAB_VALLE", "DUMMY_NO_LAB"]:
                agg_exprs.append(pl.col(d).mean().alias(f"OD_{d}_mean"))
        else:
            for d in ["DUMMY_PM_LAB", "DUMMY_PT_LAB", "DUMMY_LJ_LAB", "DUMMY_VIE_LAB"]:
                agg_exprs.append(pl.col(d).mean().alias(f"OD_{d}_mean"))

    df_od = (
        lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
        .group_by(OD_KEY_COLS)
        .agg(agg_exprs)
    )
    df_od = df_od.collect()

    if cfg.mean_mode == "inclusive":
        # mantener OD_*_mean tal cual
        return df_od

    # leave-one-out: mantener OD_*_mean y OD_*_sum para cálculo posterior
    return df_od


def _pivot_alt_values(
    df_alt: pl.DataFrame,
    value_col: str,
    out_prefix: str,
) -> pl.DataFrame:
    wide = df_alt.pivot(values=value_col, index=OD_KEY_COLS, on="tipo_pago")
    for alt in ALT_LEVELS:
        if alt not in wide.columns:
            wide = wide.with_columns(pl.lit(None).alias(alt))
    return wide.rename({alt: f"{out_prefix}_{alt}" for alt in ALT_LEVELS})


def build_od_alt_specific_context_table(
    lf: pl.LazyFrame,
    df_caracterizacion: pl.DataFrame | None,
    *,
    config: OdContextConfig | None = None,
) -> pl.DataFrame:
    cfg = config or OdContextConfig()
    schema_names = set(lf.collect_schema().names())
    lf, _ = derive_metrics(lf, schema_names)
    lf = add_tipo_pago(lf, df_caracterizacion)

    df_alt = (
        lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
        .group_by(OD_KEY_COLS + ["tipo_pago"])
        .agg(
            [pl.len().alias("alt_n_viajes")]
            + [
                expr
                for metric in ALT_METRIC_SPECS
                for expr in (
                    pl.col(metric).mean().alias(f"{metric}_mean"),
                    pl.col(metric).sum().alias(f"{metric}_sum"),
                )
            ]
        )
        .collect()
    )

    df_od_counts = (
        df_alt.group_by(OD_KEY_COLS)
        .agg(pl.len().alias("n_alternatives_observed"))
    )
    if cfg.require_all_alternatives:
        df_od_counts = df_od_counts.filter(pl.col("n_alternatives_observed") == len(ALT_LEVELS))
        df_alt = df_alt.join(df_od_counts.select(OD_KEY_COLS), on=OD_KEY_COLS, how="inner")

    pieces = [
        df_od_counts,
        _pivot_alt_values(df_alt, "alt_n_viajes", "N"),
    ]
    for metric, short in ALT_METRIC_SPECS.items():
        pieces.append(_pivot_alt_values(df_alt, f"{metric}_mean", f"{short}_MEAN"))
        pieces.append(_pivot_alt_values(df_alt, f"{metric}_sum", f"{short}_SUM"))

    out = pieces[0]
    for piece in pieces[1:]:
        out = out.join(piece, on=OD_KEY_COLS, how="left")
    return out


def build_trip_dataset_with_alt_specific_context(
    lf: pl.LazyFrame,
    df_caracterizacion: pl.DataFrame | None,
    df_od_alt_context: pl.DataFrame,
    *,
    time_dummy_variant: str = "v2",
    mean_mode: str = "leave_one_out",
    drop_chosen_singletons: bool = True,
) -> pl.DataFrame:
    schema_names = set(lf.collect_schema().names())
    lf, _ = derive_metrics(lf, schema_names)
    if time_dummy_variant == "v2":
        lf = add_time_dummies_v2(lf)
        dummy_cols = [
            "DUMMY_LAB_PM",
            "DUMMY_LAB_PT",
            "DUMMY_LAB_VALLE",
            "DUMMY_NO_LAB",
        ]
    else:
        lf = add_time_dummies(lf)
        dummy_cols = [
            "DUMMY_PM_LAB",
            "DUMMY_PT_LAB",
            "DUMMY_LJ_LAB",
            "DUMMY_VIE_LAB",
        ]
    lf = add_tipo_pago(lf, df_caracterizacion)

    lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())
    lf = lf.with_columns(
        pl.when(pl.col("tipo_pago") == "BIP")
        .then(pl.lit(ALT_CHOICE_MAP["BIP"]))
        .when(pl.col("tipo_pago") == "QR_RED")
        .then(pl.lit(ALT_CHOICE_MAP["QR_RED"]))
        .otherwise(pl.lit(ALT_CHOICE_MAP["QR_OTHER"]))
        .alias("choice_nested")
    )

    joined = (
        lf.join(df_od_alt_context.lazy(), on=OD_KEY_COLS, how="inner")
        .select(
            [
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_viaje"),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_viaje"),
                "choice_nested",
                "t_vehiculo_total_seg_final",
                "t_espera_inicial_seg",
                "t_espera_trasbordo_seg",
                "n_trasbordos",
                "n_alternatives_observed",
            ]
            + dummy_cols
            + [c for c in df_od_alt_context.columns if c not in OD_KEY_COLS]
        )
        .fill_null(0)
    )

    joined = joined.with_columns(
        pl.when(pl.col("choice_nested") == ALT_CHOICE_MAP["BIP"])
        .then(pl.col("N_BIP"))
        .when(pl.col("choice_nested") == ALT_CHOICE_MAP["QR_RED"])
        .then(pl.col("N_QR_RED"))
        .otherwise(pl.col("N_QR_OTHER"))
        .alias("N_CHOSEN_ALT")
    )

    if mean_mode == "leave_one_out" and drop_chosen_singletons:
        joined = joined.filter(pl.col("N_CHOSEN_ALT") > 1)

    loo_exprs = []
    chosen_metric_map = {
        "TVH": "t_vehiculo_total_seg_final",
        "TEI": "t_espera_inicial_seg",
        "TET": "t_espera_trasbordo_seg",
        "NTR": "n_trasbordos",
    }
    use_leave_one_out = mean_mode == "leave_one_out"
    for short, realized_col in chosen_metric_map.items():
        for alt in ALT_LEVELS:
            choice_code = ALT_CHOICE_MAP[alt]
            loo_exprs.append(
                pl.when((pl.col("choice_nested") == choice_code) & (pl.col(f"N_{alt}") > 1) & pl.lit(use_leave_one_out))
                .then((pl.col(f"{short}_SUM_{alt}") - pl.col(realized_col)) / (pl.col(f"N_{alt}") - 1))
                .otherwise(pl.col(f"{short}_MEAN_{alt}"))
                .alias(f"{short}_{alt}")
            )
    joined = joined.with_columns(loo_exprs)

    out_cols = [
        "zona_inicio_viaje",
        "zona_fin_viaje",
        "choice_nested",
    ] + dummy_cols + [
        "N_BIP",
        "N_QR_RED",
        "N_QR_OTHER",
        "N_CHOSEN_ALT",
    ] + [
        f"{short}_{alt}"
        for short in chosen_metric_map
        for alt in ALT_LEVELS
    ]

    return joined.select(out_cols).collect()


def build_trip_dataset_with_context(
    lf: pl.LazyFrame,
    df_caracterizacion: pl.DataFrame | None,
    df_od_context: pl.DataFrame,
    *,
    time_dummy_variant: str = "v2",
    mean_mode: str = "leave_one_out",
) -> pl.DataFrame:
    schema_names = set(lf.collect_schema().names())
    lf, _ = derive_metrics(lf, schema_names)
    if time_dummy_variant == "v2":
        lf = add_time_dummies_v2(lf)
        dummy_cols = [
            "DUMMY_LAB_PM",
            "DUMMY_LAB_PT",
            "DUMMY_LAB_VALLE",
            "DUMMY_NO_LAB",
        ]
    else:
        lf = add_time_dummies(lf)
        dummy_cols = [
            "DUMMY_PM_LAB",
            "DUMMY_PT_LAB",
            "DUMMY_LJ_LAB",
            "DUMMY_VIE_LAB",
        ]
    lf = add_tipo_pago(lf, df_caracterizacion)

    lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())

    lf = lf.with_columns(
        pl.when(pl.col("tipo_pago") == "BIP")
        .then(pl.lit(0))
        .when(pl.col("tipo_pago") == "QR_RED")
        .then(pl.lit(1))
        .otherwise(pl.lit(2))
        .alias("choice_nested")
    )

    joined = (
        lf.join(df_od_context.lazy(), on=OD_KEY_COLS, how="left")
        .select(
            [
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False).alias("zona_inicio_viaje"),
                pl.col("zona_fin_viaje").cast(pl.Int64, strict=False).alias("zona_fin_viaje"),
                "choice_nested",
            ]
            + dummy_cols
            + [
                "t_vehiculo_total_seg_final",
                "t_espera_inicial_seg",
                "t_espera_trasbordo_seg",
                "n_trasbordos",
                "od_n_viajes",
            ]
            + [c for c in df_od_context.columns if c.startswith("OD_")]
        )
        .fill_null(0)
    )

    if mean_mode != "inclusive":
        # Recalcular OD_*_mean como leave-one-out
        joined = joined.with_columns(
            [
                pl.when(pl.col("od_n_viajes") > 1)
                .then((pl.col("OD_t_vehiculo_total_seg_final_sum") - pl.col("t_vehiculo_total_seg_final")) / (pl.col("od_n_viajes") - 1))
                .otherwise(pl.col("OD_t_vehiculo_total_seg_final_mean"))
                .alias("OD_t_vehiculo_total_seg_final_mean"),
                pl.when(pl.col("od_n_viajes") > 1)
                .then((pl.col("OD_t_espera_inicial_seg_sum") - pl.col("t_espera_inicial_seg")) / (pl.col("od_n_viajes") - 1))
                .otherwise(pl.col("OD_t_espera_inicial_seg_mean"))
                .alias("OD_t_espera_inicial_seg_mean"),
                pl.when(pl.col("od_n_viajes") > 1)
                .then((pl.col("OD_t_espera_trasbordo_seg_sum") - pl.col("t_espera_trasbordo_seg")) / (pl.col("od_n_viajes") - 1))
                .otherwise(pl.col("OD_t_espera_trasbordo_seg_mean"))
                .alias("OD_t_espera_trasbordo_seg_mean"),
                pl.when(pl.col("od_n_viajes") > 1)
                .then((pl.col("OD_n_trasbordos_sum") - pl.col("n_trasbordos")) / (pl.col("od_n_viajes") - 1))
                .otherwise(pl.col("OD_n_trasbordos_mean"))
                .alias("OD_n_trasbordos_mean"),
            ]
        )

    return joined.collect()


def build_od_aggregated_dataset(
    lf: pl.LazyFrame,
    df_caracterizacion: pl.DataFrame | None,
    df_od_context: pl.DataFrame,
) -> pl.DataFrame:
    lf = add_tipo_pago(lf, df_caracterizacion)
    lf = lf.filter(pl.col("zona_inicio_viaje").is_not_null() & pl.col("zona_fin_viaje").is_not_null())

    df_counts = (
        lf.group_by(OD_KEY_COLS + ["tipo_pago"])
        .agg(pl.len().alias("n_viajes"))
    )
    df_counts = df_counts.collect()
    df_counts = df_counts.pivot(values="n_viajes", index=OD_KEY_COLS, on="tipo_pago").fill_null(0)

    df_wide = df_counts.join(df_od_context, on=OD_KEY_COLS, how="left")

    rows = []
    for alt, choice_val in [("BIP", 0), ("QR_RED", 1), ("QR_OTHER", 2)]:
        rows.append(
            df_wide.select(
                OD_KEY_COLS
                + [pl.lit(choice_val).alias("choice_nested")]
                + [pl.col(alt).alias("weight")]
                + [c for c in df_od_context.columns if c.startswith("OD_")]
            )
        )

    df_long = pl.concat(rows).filter(pl.col("weight") > 0).fill_null(0)
    return df_long


__all__ = [
    "OdContextConfig",
    "resolve_caracterizacion_path",
    "load_caracterizacion",
    "build_od_context_table",
    "build_od_alt_specific_context_table",
    "build_trip_dataset_with_context",
    "build_trip_dataset_with_alt_specific_context",
    "build_od_aggregated_dataset",
    "read_parquet_portable",
    "add_time_dummies_v2",
]
