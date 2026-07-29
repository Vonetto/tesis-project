from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from lib.od_buffers_nested_logit import add_time_dummies_v2  # noqa: E402


ARTIFACTS_DIR = PROJECT_ROOT / "03_models" / "artifacts" / "interannual_enriched"
OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

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

BUS_FREQUENCIES_BY_WEEK = {
    week: PROJECT_ROOT / "tmp" / f"frecuencias_buses_{week}.parquet"
    for week in PROCESSED_TRIPS_BY_WEEK
}

SCOPE_WEEKS = {
    "active": ["2024-W17", "2025-W17"],
    "ml_2025": ["2025-W14", "2025-W15", "2025-W17"],
    "interannual_ml": [
        "2024-W14",
        "2024-W15",
        "2024-W16",
        "2024-W17",
        "2025-W14",
        "2025-W15",
        "2025-W16",
        "2025-W17",
    ],
}

BUS_CODES = ["1", "3"]  # bus, zona paga
METRO_CODES = ["2", "4"]  # metro, metrotren


def output_path(scope: str) -> Path:
    return OUT_DIR / f"user_offer_demand_exposure_{scope}.parquet"


def collect_streaming(lf: pl.LazyFrame) -> pl.DataFrame:
    try:
        return lf.collect(engine="streaming")
    except TypeError:
        return lf.collect(streaming=True)


def validate_inputs(scope: str, weeks: list[str]) -> None:
    if scope not in SCOPE_WEEKS:
        raise ValueError(f"Scope no soportado: {scope}")

    missing_trips = [str(PROCESSED_TRIPS_BY_WEEK[w]) for w in weeks if not PROCESSED_TRIPS_BY_WEEK[w].exists()]
    if missing_trips:
        raise FileNotFoundError(f"Faltan viajes procesados: {missing_trips}")

    missing_freq = [str(BUS_FREQUENCIES_BY_WEEK[w]) for w in weeks if not BUS_FREQUENCIES_BY_WEEK[w].exists()]
    if missing_freq:
        raise FileNotFoundError(f"Faltan frecuencias de bus: {missing_freq}")

    required = [
        ARTIFACTS_DIR / "bus_stop_density_zona_2024_2025.parquet",
        ARTIFACTS_DIR / "metro_station_density_zona_2024_2025.parquet",
    ]
    missing_offer = [str(p) for p in required if not p.exists()]
    if missing_offer:
        raise FileNotFoundError(f"Faltan artefactos de oferta estructural: {missing_offer}")

    for path in required:
        key_check = (
            pl.scan_parquet(path)
            .select(pl.col("zona_inicio_viaje").cast(pl.Int64))
            .group_by("zona_inicio_viaje")
            .len()
            .select(pl.col("len").max().alias("max_rows_per_zone"))
            .collect()
        )
        max_rows = key_check.item(0, "max_rows_per_zone")
        if max_rows != 1:
            raise ValueError(f"{path} no es unico por zona_inicio_viaje; max filas por zona={max_rows}")


def add_franja_v2(lf: pl.LazyFrame) -> pl.LazyFrame:
    return add_time_dummies_v2(lf).with_columns(
        pl.when(pl.col("DUMMY_LAB_PM") == 1)
        .then(pl.lit("LAB_PM"))
        .when(pl.col("DUMMY_LAB_PT") == 1)
        .then(pl.lit("LAB_PT"))
        .when(pl.col("DUMMY_LAB_VALLE") == 1)
        .then(pl.lit("LAB_VALLE"))
        .otherwise(pl.lit("NO_LAB"))
        .alias("franja_v2")
    )


def load_static_offer() -> tuple[pl.LazyFrame, pl.LazyFrame]:
    bus = pl.scan_parquet(ARTIFACTS_DIR / "bus_stop_density_zona_2024_2025.parquet").select(
        [
            pl.col("zona_inicio_viaje").cast(pl.Int64),
            pl.col("N_BUS_STOPS").cast(pl.Float64),
            pl.col("BUS_STOP_DENSITY").cast(pl.Float64),
            pl.col("LOG_BUS_STOP_DENSITY").cast(pl.Float64),
        ]
    )
    metro = pl.scan_parquet(ARTIFACTS_DIR / "metro_station_density_zona_2024_2025.parquet").select(
        [
            pl.col("zona_inicio_viaje").cast(pl.Int64),
            pl.col("N_METRO_STATIONS").cast(pl.Float64),
            pl.col("METRO_STATION_DENSITY").cast(pl.Float64),
            pl.col("LOG_METRO_STATION_DENSITY").cast(pl.Float64),
        ]
    )
    return bus, metro


def bus_frequency_context_for_week(week: str) -> pl.LazyFrame:
    return (
        pl.scan_parquet(BUS_FREQUENCIES_BY_WEEK[week])
        .select(
            [
                pl.col("Paradero").cast(pl.Utf8).alias("origin_stop"),
                pl.col("ServicioSentido").cast(pl.Utf8).alias("service_direction"),
                pl.col("hour_start"),
                pl.col("freq_buses_h").cast(pl.Float64),
            ]
        )
        .drop_nulls(["origin_stop", "hour_start", "freq_buses_h"])
        .group_by(["origin_stop", "hour_start"])
        .agg(
            [
                pl.col("freq_buses_h").sum().alias("bus_origin_freq_all_h"),
                pl.col("service_direction").n_unique().cast(pl.Float64).alias("bus_origin_n_services_h"),
            ]
        )
        .with_columns(
            (3600.0 / pl.col("bus_origin_freq_all_h"))
            .alias("bus_origin_headway_all_s")
        )
    )


def trip_context_for_week(week: str, bus_static: pl.LazyFrame, metro_static: pl.LazyFrame) -> pl.LazyFrame:
    lf = (
        pl.scan_parquet(PROCESSED_TRIPS_BY_WEEK[week])
        .select(
            [
                pl.col("id_tarjeta").cast(pl.Utf8),
                pl.col("zona_inicio_viaje").cast(pl.Int64, strict=False),
                pl.col("tiempo_inicio_viaje"),
                pl.col("tipodia"),
                pl.col("tipo_transporte_1").cast(pl.Utf8),
                pl.col("paradero_inicio_viaje").cast(pl.Utf8).alias("origin_stop"),
            ]
        )
        .drop_nulls(["id_tarjeta", "zona_inicio_viaje", "tiempo_inicio_viaje"])
        .with_columns(pl.lit(week).alias("partition"))
    )
    lf = add_franja_v2(lf)

    demand = (
        lf.group_by(["partition", "zona_inicio_viaje", "franja_v2"])
        .agg(pl.len().alias("N_VIAJES_ZONA_INICIO_FRANJA_RAW"))
    )

    lf = (
        lf.join(demand, on=["partition", "zona_inicio_viaje", "franja_v2"], how="left")
        .with_columns(
            (pl.col("N_VIAJES_ZONA_INICIO_FRANJA_RAW").fill_null(0) - 1)
            .clip(lower_bound=0)
            .alias("N_VIAJES_ZONA_INICIO_FRANJA")
        )
        .with_columns(
            pl.col("N_VIAJES_ZONA_INICIO_FRANJA")
            .log1p()
            .alias("LOG_N_VIAJES_ZONA_INICIO_FRANJA")
        )
        .join(bus_static, on="zona_inicio_viaje", how="left")
        .join(metro_static, on="zona_inicio_viaje", how="left")
        .with_columns(
            [
                pl.col("tiempo_inicio_viaje").dt.truncate("1h").alias("hour_start"),
                pl.col("tipo_transporte_1").is_in(BUS_CODES).alias("is_origin_bus_like"),
                pl.col("tipo_transporte_1").is_in(METRO_CODES).alias("is_origin_metro_like"),
            ]
        )
        .join(bus_frequency_context_for_week(week), on=["origin_stop", "hour_start"], how="left")
    )
    return lf


def aggregate_week(week: str, bus_static: pl.LazyFrame, metro_static: pl.LazyFrame) -> pl.DataFrame:
    lf = trip_context_for_week(week, bus_static, metro_static)

    bus_matched = pl.col("is_origin_bus_like") & pl.col("bus_origin_freq_all_h").is_not_null()
    bus_high_headway = bus_matched & ((pl.col("bus_origin_headway_all_s") / 60.0) >= 10.0)

    agg = (
        lf.group_by("id_tarjeta")
        .agg(
            [
                pl.len().alias("offer_n_trips"),
                pl.col("LOG_N_VIAJES_ZONA_INICIO_FRANJA").sum().alias("sum_log_demand_origin_franja"),
                pl.col("LOG_BUS_STOP_DENSITY").fill_null(0.0).sum().alias("sum_log_bus_stop_density_origin"),
                pl.col("LOG_METRO_STATION_DENSITY").fill_null(0.0).sum().alias("sum_log_metro_station_density_origin"),
                pl.col("is_origin_bus_like").sum().alias("n_origin_bus_like"),
                pl.col("is_origin_metro_like").sum().alias("n_origin_metro_like"),
                bus_matched.sum().alias("n_origin_bus_freq_matched"),
                pl.when(bus_matched).then(pl.col("bus_origin_freq_all_h")).otherwise(None).sum().alias("sum_bus_origin_freq_all_h"),
                pl.when(bus_matched).then(pl.col("bus_origin_n_services_h")).otherwise(None).sum().alias("sum_bus_origin_n_services_h"),
                pl.when(bus_matched).then(pl.col("bus_origin_headway_all_s") / 60.0).otherwise(None).sum().alias("sum_bus_origin_headway_all_min"),
                bus_high_headway.sum().alias("n_bus_origin_headway_ge10"),
            ]
        )
        .with_columns(pl.lit(week).alias("partition"))
    )
    return collect_streaming(agg)


def finalize(weekly: list[pl.DataFrame]) -> pl.DataFrame:
    df = pl.concat(weekly, how="diagonal_relaxed")
    out = (
        df.group_by("id_tarjeta")
        .agg(
            [
                pl.col("offer_n_trips").sum(),
                pl.col("sum_log_demand_origin_franja").sum(),
                pl.col("sum_log_bus_stop_density_origin").sum(),
                pl.col("sum_log_metro_station_density_origin").sum(),
                pl.col("n_origin_bus_like").sum(),
                pl.col("n_origin_metro_like").sum(),
                pl.col("n_origin_bus_freq_matched").sum(),
                pl.col("sum_bus_origin_freq_all_h").sum(),
                pl.col("sum_bus_origin_n_services_h").sum(),
                pl.col("sum_bus_origin_headway_all_min").sum(),
                pl.col("n_bus_origin_headway_ge10").sum(),
            ]
        )
        .with_columns(
            [
                (pl.col("sum_log_demand_origin_franja") / pl.col("offer_n_trips")).alias("offer_log_demand_origin_franja_mean"),
                (pl.col("sum_log_bus_stop_density_origin") / pl.col("offer_n_trips")).alias("offer_log_bus_stop_density_origin_mean"),
                (pl.col("sum_log_metro_station_density_origin") / pl.col("offer_n_trips")).alias("offer_log_metro_station_density_origin_mean"),
                (pl.col("n_origin_bus_like") / pl.col("offer_n_trips")).alias("offer_origin_bus_like_share"),
                (pl.col("n_origin_metro_like") / pl.col("offer_n_trips")).alias("offer_origin_metro_like_share"),
                pl.when(pl.col("n_origin_bus_like") > 0)
                .then(pl.col("n_origin_bus_freq_matched") / pl.col("n_origin_bus_like"))
                .otherwise(None)
                .alias("offer_bus_freq_match_share"),
                pl.when(pl.col("n_origin_bus_freq_matched") > 0)
                .then(pl.col("sum_bus_origin_freq_all_h") / pl.col("n_origin_bus_freq_matched"))
                .otherwise(None)
                .alias("offer_bus_origin_freq_all_h_mean"),
                pl.when(pl.col("n_origin_bus_freq_matched") > 0)
                .then(pl.col("sum_bus_origin_n_services_h") / pl.col("n_origin_bus_freq_matched"))
                .otherwise(None)
                .alias("offer_bus_origin_n_services_h_mean"),
                pl.when(pl.col("n_origin_bus_freq_matched") > 0)
                .then(pl.col("sum_bus_origin_headway_all_min") / pl.col("n_origin_bus_freq_matched"))
                .otherwise(None)
                .alias("offer_bus_origin_headway_all_min_mean"),
                pl.when(pl.col("n_origin_bus_freq_matched") > 0)
                .then(pl.col("n_bus_origin_headway_ge10") / pl.col("n_origin_bus_freq_matched"))
                .otherwise(None)
                .alias("offer_bus_origin_headway_ge10_share"),
            ]
        )
        .select(
            [
                "id_tarjeta",
                "offer_n_trips",
                "offer_log_demand_origin_franja_mean",
                "offer_log_bus_stop_density_origin_mean",
                "offer_log_metro_station_density_origin_mean",
                "offer_origin_bus_like_share",
                "offer_origin_metro_like_share",
                "offer_bus_freq_match_share",
                "offer_bus_origin_freq_all_h_mean",
                "offer_bus_origin_n_services_h_mean",
                "offer_bus_origin_headway_all_min_mean",
                "offer_bus_origin_headway_ge10_share",
            ]
        )
        .sort("id_tarjeta")
    )
    if out["id_tarjeta"].n_unique() != out.height:
        raise ValueError("Salida no es unica por id_tarjeta")
    if (out["offer_n_trips"] <= 0).any():
        raise ValueError("Salida contiene tarjetas sin viajes agregados")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=sorted(SCOPE_WEEKS), default="interannual_ml")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    weeks = SCOPE_WEEKS[args.scope]
    out_path = output_path(args.scope)
    if out_path.exists() and not args.force:
        print(f"✅ Ya existe: {out_path}")
        return

    validate_inputs(args.scope, weeks)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"ℹ️ Construyendo exposición oferta/demanda scope={args.scope}: {weeks}")
    bus_static, metro_static = load_static_offer()
    weekly = []
    for week in weeks:
        print(f"  - {week}")
        weekly.append(aggregate_week(week, bus_static, metro_static))

    df = finalize(weekly)
    df.write_parquet(out_path)
    print(f"✅ Exposición escrita: {out_path}")
    print(df.select([pl.len().alias("n_cards"), pl.col("offer_n_trips").sum().alias("n_trips")]))


if __name__ == "__main__":
    main()
