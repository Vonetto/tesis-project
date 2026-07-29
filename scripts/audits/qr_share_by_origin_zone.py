"""Diagnóstico: share de pagos QR por zona de ORIGEN de viaje (2024, 2025, delta).

Complemento al diagnóstico de residencia. Acá la pregunta NO es "qué población
adopta" sino "DÓNDE ocurren los pagos QR" — la geografía transaccional. Es la
unidad correcta para variables de oferta/infraestructura de transporte y para
testear la hipótesis de que la huella de QR está mandada por dónde se usa
(origen/red), no por dónde vive la gente.

Unidad = zona de inicio de viaje (zona_inicio_viaje -> ZONA777), nivel VIAJE
(cada validación es una transacción con su tipo_pago). Universo = TODOS los
viajes (no se filtra por residencia del titular): es una medida transaccional.

Definición: share QR = (viajes QR_RED + QR_OTHER) / viajes totales de la zona,
por año. Mismo criterio que scripts/figures/make_payment_adoption_maps.py
(trip-level, n_qr/n_trips), extendido a 2024 vs 2025 sobre la ventana completa
(scope interannual_ml: W14-W17 de cada año).

Reusa la carga oficial de viajes (tipo_pago) y el Moran de contigüidad del
diagnóstico de residencia.

Salidas (en <OUT_DIR>):
  - qr_share_by_origin_zone.csv            (una fila por zona de origen)
  - qr_share_by_origin_zone_summary.json   (distribución + Moran)

Uso:
    python scripts/audits/qr_share_by_origin_zone.py
    python scripts/audits/qr_share_by_origin_zone.py --min-n 100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from scripts.audits.build_user_level_payment_panel import (  # noqa: E402
    OUT_DIR,
    SCOPE_WEEKS,
    trips_lf_for_scope,
)
from scripts.audits.qr_adoption_by_residence_zone import (  # noqa: E402
    QR_TYPES,
    build_queen_neighbors,
    dist_stats,
    morans_i,
)


def origin_year_shares(weeks):
    import polars as pl

    trips = trips_lf_for_scope(weeks).filter(
        pl.col("zona_inicio_viaje").is_not_null()
        & (pl.col("zona_inicio_viaje") > 0)
        & pl.col("trip_year").is_in([2024, 2025])
    )
    zy = (
        trips.group_by(["zona_inicio_viaje", "trip_year"])
        .agg(
            [
                pl.len().alias("n_trips"),
                pl.col("tipo_pago").is_in(QR_TYPES).sum().alias("n_qr"),
                pl.col("tipo_pago").is_in(QR_TYPES).mean().alias("qr_share"),
            ]
        )
        .collect(engine="streaming")
    )

    def yslice(year):
        return zy.filter(pl.col("trip_year") == year).select(
            [
                pl.col("zona_inicio_viaje").alias("ZONA777"),
                pl.col("n_trips").alias(f"n_trips_{year}"),
                pl.col("n_qr").alias(f"n_qr_{year}"),
                pl.col("qr_share").alias(f"qr_share_{year}"),
            ]
        )

    wide = yslice(2024).join(yslice(2025), on="ZONA777", how="full", coalesce=True)
    wide = wide.with_columns(
        (pl.col("qr_share_2025") - pl.col("qr_share_2024")).alias("delta")
    ).sort("ZONA777")
    return wide


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-n", type=int, default=50, help="mín. viajes/zona-año")
    ap.add_argument("--n-perm", type=int, default=999)
    args = ap.parse_args()

    import polars as pl

    weeks = SCOPE_WEEKS["interannual_ml"]
    print("[1/3] Agregando viajes por zona de origen y año...")
    wide = origin_year_shares(weeks)

    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / "qr_share_by_origin_zone.csv"
    wide.write_csv(csv_out)

    # share pooled por año (referencia)
    print("[2/3] Moran's I...")
    neighbors = build_queen_neighbors()
    n_islands = sum(1 for _, nb in neighbors.items() if len(nb) == 0)

    def vmap(share_col, n_col):
        f = wide.filter(pl.col(n_col).fill_null(0) >= args.min_n)
        return dict(zip(f["ZONA777"].to_list(), f[share_col].to_list()))

    delta_f = wide.filter(
        (pl.col("n_trips_2024").fill_null(0) >= args.min_n)
        & (pl.col("n_trips_2025").fill_null(0) >= args.min_n)
    )
    moran = {
        "qr_share_2024": morans_i(vmap("qr_share_2024", "n_trips_2024"), neighbors, args.n_perm),
        "qr_share_2025": morans_i(vmap("qr_share_2025", "n_trips_2025"), neighbors, args.n_perm),
        "delta": morans_i(
            dict(zip(delta_f["ZONA777"].to_list(), delta_f["delta"].to_list())),
            neighbors, args.n_perm,
        ),
    }

    print("[3/3] Resumen...")
    summary = {
        "unidad": "zona_inicio_viaje (origen), nivel viaje",
        "universo": "todos los viajes (transaccional, sin filtro de residencia)",
        "ventana": "interannual_ml (W14-W17 por año)",
        "min_n_viajes": args.min_n,
        "n_zonas_con_dato": int(wide.height),
        "n_islas_sin_vecinos": int(n_islands),
        "share_pooled": {
            "2024": round(
                float(wide["n_qr_2024"].sum() / wide["n_trips_2024"].sum()), 5
            ),
            "2025": round(
                float(wide["n_qr_2025"].sum() / wide["n_trips_2025"].sum()), 5
            ),
        },
        "distribucion": {
            "qr_share_2024": dist_stats(wide["qr_share_2024"], wide["n_trips_2024"]),
            "qr_share_2025": dist_stats(wide["qr_share_2025"], wide["n_trips_2025"]),
            "delta": dist_stats(wide["delta"]),
        },
        "morans_i": moran,
    }
    json_out = out_dir / "qr_share_by_origin_zone_summary.json"
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n===== SHARE QR POR ZONA DE ORIGEN =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nCSV  : {csv_out}")
    print(f"JSON : {json_out}")


if __name__ == "__main__":
    main()
