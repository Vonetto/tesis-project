"""Diagnóstico: tasa de adopción QR por zona de residencia (2024, 2025, delta).

Pressure-test barato para decidir si vale el pivote a nivel zona sugerido por
el profesor. Responde tres cosas:

  1. Tasa de adopción QR por zona de residencia (zona_hogar) en 2024 y 2025.
  2. Varianza / distribución de esas tasas y del delta entre zonas.
  3. Moran's I (autocorrelación espacial) de las tasas y del delta.

DECISIONES DE DISEÑO (acordadas 2026-06-15):
  - Definición de tasa = "share de tarjetas QR" (no share de viajes). Se replica
    EXACTAMENTE la regla de `is_qr` del panel
    (`build_user_level_payment_panel.build_user_aggregates`):
    una tarjeta es QR-type en un año si usó UN solo `tipo_pago` ese año y ese
    tipo está en {QR_RED, QR_OTHER}. Las tarjetas mixtas del año (varios
    tipo_pago) se excluyen, igual que la variante "clean" del panel.
    La diferencia con el panel: aquí la etiqueta se calcula POR AÑO, para poder
    cortar 2024 vs 2025; el panel trae un solo is_qr interanual.
  - Universo = home_confidence == "alta" por defecto (≈ el estudio previo de
    2,46M tarjetas), para comparabilidad con el techo ~0,67 ya medido.
  - zona_hogar se REUSA del panel ya construido
    (user_level_payment_panel_interannual_ml_clean.parquet): misma asignación
    de residencia validada.
  - Cohorte por año: una tarjeta entra en la tasa de un año solo si tuvo viajes
    ese año (activa en el año). Esto es deliberado: medimos la composición real
    de cada año, no una etiqueta fija proyectada hacia atrás.

NO reinventa nada: importa la carga de viajes y el mapeo tipo_pago del módulo
oficial. Si el panel o el shapefile ZONA777 no existen, falla con mensaje claro.

Salidas (en tmp/audits/user_level_redesign/):
  - qr_adoption_by_residence_zone_<universo>.csv   (una fila por zona)
  - qr_adoption_by_residence_zone_<universo>_summary.json
Y un resumen legible por stdout.

Uso:
    python scripts/audits/qr_adoption_by_residence_zone.py
    python scripts/audits/qr_adoption_by_residence_zone.py --home-filter alta_media --min-n 50
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Reusar la lógica oficial del pipeline (carga viajes + tipo_pago + rutas).
from scripts.audits.build_user_level_payment_panel import (  # noqa: E402
    OUT_DIR,
    SCOPE_WEEKS,
    ZONAS777_SHP,
    panel_path,
    trips_lf_for_scope,
)

QR_TYPES = ["QR_RED", "QR_OTHER"]
HOME_FILTERS = {
    "alta": ["alta"],
    "alta_media": ["alta", "media"],
    "any": None,
}


# --------------------------------------------------------------------------- #
# 1. Etiqueta QR por tarjeta-año + tasa por zona
# --------------------------------------------------------------------------- #
def build_card_year_labels(weeks: list[str], universe: pl.LazyFrame) -> pl.DataFrame:
    """Una fila por (id_tarjeta, año) con la etiqueta QR-type de ese año.

    Replica la regla del panel pero dentro de cada año:
      n_tipo_pago_observed == 1  ->  tipo_tarjeta_year = ese tipo
      is_qr_year = tipo_tarjeta_year in {QR_RED, QR_OTHER}
    """
    trips = trips_lf_for_scope(weeks).join(universe, on="id_tarjeta", how="inner")
    card_year = (
        trips.group_by(["id_tarjeta", "trip_year", "zona_hogar"])
        .agg(
            [
                pl.col("tipo_pago").drop_nulls().n_unique().alias("n_tipo_pago_observed"),
                pl.col("tipo_pago").drop_nulls().first().alias("tipo_first"),
                pl.len().alias("n_viajes_year"),
            ]
        )
        .with_columns(
            [
                (pl.col("n_tipo_pago_observed") == 1).alias("is_pure_year"),
                pl.when(pl.col("n_tipo_pago_observed") == 1)
                .then(pl.col("tipo_first"))
                .otherwise(None)
                .alias("tipo_tarjeta_year"),
            ]
        )
        .with_columns(
            pl.col("tipo_tarjeta_year").is_in(QR_TYPES).cast(pl.Int8).alias("is_qr_year")
        )
    )
    return card_year.collect(engine="streaming")


def zone_year_rates(card_year: pl.DataFrame) -> pl.DataFrame:
    """Tasa de adopción QR por zona y año, sobre tarjetas 'puras' del año."""
    pure = card_year.filter(pl.col("is_pure_year"))
    zy = (
        pure.group_by(["zona_hogar", "trip_year"])
        .agg(
            [
                pl.len().alias("n_cards"),
                pl.col("is_qr_year").sum().alias("n_qr"),
                pl.col("is_qr_year").mean().alias("qr_rate"),
            ]
        )
        .sort(["zona_hogar", "trip_year"])
    )

    def yslice(year: int) -> pl.DataFrame:
        return zy.filter(pl.col("trip_year") == year).select(
            [
                pl.col("zona_hogar"),
                pl.col("n_cards").alias(f"n_cards_{year}"),
                pl.col("n_qr").alias(f"n_qr_{year}"),
                pl.col("qr_rate").alias(f"qr_rate_{year}"),
            ]
        )

    wide = yslice(2024).join(yslice(2025), on="zona_hogar", how="full", coalesce=True)
    wide = wide.with_columns(
        (pl.col("qr_rate_2025") - pl.col("qr_rate_2024")).alias("delta")
    ).sort("zona_hogar")
    return wide


# --------------------------------------------------------------------------- #
# 2. Moran's I (contigüidad queen, row-standardized, test de permutación)
# --------------------------------------------------------------------------- #
def build_queen_neighbors() -> dict[int, list[int]]:
    """Vecindad queen entre zonas ZONA777 a partir del shapefile."""
    import geopandas as gpd

    if not ZONAS777_SHP.exists():
        raise FileNotFoundError(
            f"No existe el shapefile ZONA777 (¿disco externo montado?): {ZONAS777_SHP}"
        )
    gdf = gpd.read_file(ZONAS777_SHP)
    gdf = gdf[["ZONA777", "geometry"]].copy()
    gdf["ZONA777"] = gdf["ZONA777"].astype(int)
    # Una geometría por zona (por si el shapefile trae multi-filas).
    gdf = gdf.dissolve(by="ZONA777", as_index=False)
    # Convención del repo: el shapefile Zonas777 viene sin CRS; se asume
    # EPSG:4674 (SIRGAS 2000 geográfico) y se reproyecta a UTM 19S métrico.
    # Ver lib/censo2024_zona777.py, scripts/audits/build_bip_load_access_zona777.py.
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4674", allow_override=True)
    gdf = gdf.to_crs(epsg=32719)  # UTM 19S, métrico, igual que el resto del repo

    # Auto-join espacial: dos zonas son vecinas si sus geometrías se intersectan
    # (comparten borde o vértice) y no son la misma.
    sj = gpd.sjoin(
        gdf[["ZONA777", "geometry"]],
        gdf[["ZONA777", "geometry"]],
        predicate="intersects",
        how="inner",
    )
    pairs = sj[sj["ZONA777_left"] != sj["ZONA777_right"]]
    neighbors: dict[int, list[int]] = {int(z): [] for z in gdf["ZONA777"]}
    for a, b in zip(pairs["ZONA777_left"], pairs["ZONA777_right"]):
        neighbors[int(a)].append(int(b))
    # dedup
    return {z: sorted(set(nb)) for z, nb in neighbors.items()}


def morans_i(
    values_by_zone: dict[int, float],
    neighbors: dict[int, list[int]],
    n_perm: int = 999,
    seed: int = 0,
) -> dict:
    """Moran's I con W row-standardized + pseudo p-valor por permutación."""
    zones = [
        z
        for z, v in values_by_zone.items()
        if z in neighbors and v is not None and not np.isnan(v) and len(neighbors[z]) > 0
    ]
    idx = {z: i for i, z in enumerate(zones)}
    n = len(zones)
    if n < 3:
        return {"I": None, "p_value": None, "n_zones": n, "note": "insuficientes zonas"}

    x = np.array([values_by_zone[z] for z in zones], dtype=float)
    zdev = x - x.mean()

    W = np.zeros((n, n), dtype=float)
    for z in zones:
        nb = [w for w in neighbors[z] if w in idx]
        for w in nb:
            W[idx[z], idx[w]] = 1.0
    rs = W.sum(axis=1, keepdims=True)
    rs[rs == 0] = 1.0
    W = W / rs  # row-standardized
    S0 = W.sum()

    den = float((zdev**2).sum())
    if den == 0:
        return {"I": None, "p_value": None, "n_zones": n, "note": "varianza nula"}

    def stat(vec: np.ndarray) -> float:
        return (n / S0) * float(vec @ (W @ vec)) / den

    I = stat(zdev)
    rng = np.random.default_rng(seed)
    perm = np.array([stat(rng.permutation(zdev)) for _ in range(n_perm)])
    # p-valor de dos colas práctico según el signo de I
    if I >= 0:
        p = (np.sum(perm >= I) + 1) / (n_perm + 1)
    else:
        p = (np.sum(perm <= I) + 1) / (n_perm + 1)
    expected_I = -1.0 / (n - 1)
    return {
        "I": round(float(I), 5),
        "expected_I": round(expected_I, 5),
        "p_value": round(float(p), 5),
        "n_zones": n,
        "n_perm": n_perm,
    }


# --------------------------------------------------------------------------- #
# 3. Resumen distribucional
# --------------------------------------------------------------------------- #
def dist_stats(series: pl.Series, weights: pl.Series | None = None) -> dict:
    s = series.drop_nulls()
    if s.len() == 0:
        return {}
    arr = s.to_numpy()
    out = {
        "n_zonas": int(s.len()),
        "media": round(float(arr.mean()), 5),
        "std": round(float(arr.std(ddof=1)) if s.len() > 1 else 0.0, 5),
        "var": round(float(arr.var(ddof=1)) if s.len() > 1 else 0.0, 6),
        "min": round(float(arr.min()), 5),
        "p10": round(float(np.percentile(arr, 10)), 5),
        "p50": round(float(np.percentile(arr, 50)), 5),
        "p90": round(float(np.percentile(arr, 90)), 5),
        "max": round(float(arr.max()), 5),
    }
    if weights is not None:
        w = weights.fill_null(0).to_numpy().astype(float)
        if w.sum() > 0:
            out["media_ponderada_por_n"] = round(float(np.average(arr, weights=w)), 5)
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--home-filter", choices=sorted(HOME_FILTERS), default="alta")
    ap.add_argument("--variant", default="clean", help="variante del panel a reusar")
    ap.add_argument("--min-n", type=int, default=30, help="mín. tarjetas/zona-año para Moran")
    ap.add_argument("--n-perm", type=int, default=999)
    args = ap.parse_args()

    weeks = SCOPE_WEEKS["interannual_ml"]

    panel = panel_path("interannual_ml", args.variant)
    if not panel.exists():
        raise FileNotFoundError(
            f"No existe el panel reusable: {panel}\n"
            "Constrúyelo primero con build_user_level_payment_panel.py "
            "o usa otra --variant."
        )

    home_values = HOME_FILTERS[args.home_filter]
    universe = pl.scan_parquet(panel).select(["id_tarjeta", "zona_hogar", "home_confidence"])
    if home_values is not None:
        universe = universe.filter(pl.col("home_confidence").is_in(home_values))
    universe = universe.filter(pl.col("zona_hogar").is_not_null()).select(
        ["id_tarjeta", "zona_hogar"]
    )

    print(f"[1/4] Etiquetando tarjetas por año (universo home={args.home_filter})...")
    card_year = build_card_year_labels(weeks, universe)

    # diagnóstico de cohorte y mezcla
    n_cards_total = card_year["id_tarjeta"].n_unique()
    by_year = card_year.group_by("trip_year").agg(
        [
            pl.len().alias("n_card_year"),
            pl.col("is_pure_year").sum().alias("n_pure"),
            (~pl.col("is_pure_year")).sum().alias("n_mixtas"),
        ]
    ).sort("trip_year")

    print("[2/4] Tasas por zona y año...")
    wide = zone_year_rates(card_year)
    out_dir = Path(OUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / f"qr_adoption_by_residence_zone_{args.home_filter}.csv"
    wide.write_csv(csv_out)

    # tasas pooled (referencia)
    pure = card_year.filter(pl.col("is_pure_year"))
    pooled = (
        pure.group_by("trip_year")
        .agg(pl.col("is_qr_year").mean().alias("qr_rate_pooled"), pl.len().alias("n"))
        .sort("trip_year")
    )

    print("[3/4] Moran's I (puede tardar unos segundos)...")
    neighbors = build_queen_neighbors()
    n_islands = sum(1 for z, nb in neighbors.items() if len(nb) == 0)

    def vmap(rate_col: str, n_col: str) -> dict[int, float]:
        f = wide.filter(pl.col(n_col).fill_null(0) >= args.min_n)
        return dict(zip(f["zona_hogar"].to_list(), f[rate_col].to_list()))

    delta_f = wide.filter(
        (pl.col("n_cards_2024").fill_null(0) >= args.min_n)
        & (pl.col("n_cards_2025").fill_null(0) >= args.min_n)
    )
    moran = {
        "qr_rate_2024": morans_i(vmap("qr_rate_2024", "n_cards_2024"), neighbors, args.n_perm),
        "qr_rate_2025": morans_i(vmap("qr_rate_2025", "n_cards_2025"), neighbors, args.n_perm),
        "delta": morans_i(
            dict(zip(delta_f["zona_hogar"].to_list(), delta_f["delta"].to_list())),
            neighbors,
            args.n_perm,
        ),
    }

    print("[4/4] Resumen distribucional...")
    summary = {
        "universo": args.home_filter,
        "variante_panel": args.variant,
        "min_n_para_moran": args.min_n,
        "n_tarjetas_universo": int(n_cards_total),
        "cohorte_por_anio": by_year.to_dicts(),
        "tasa_pooled_por_anio": pooled.to_dicts(),
        "n_zonas_con_dato": int(wide.height),
        "n_islas_sin_vecinos": int(n_islands),
        "distribucion": {
            "qr_rate_2024": dist_stats(wide["qr_rate_2024"], wide["n_cards_2024"]),
            "qr_rate_2025": dist_stats(wide["qr_rate_2025"], wide["n_cards_2025"]),
            "delta": dist_stats(wide["delta"]),
        },
        "morans_i": moran,
    }
    json_out = out_dir / f"qr_adoption_by_residence_zone_{args.home_filter}_summary.json"
    json_out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print("\n===== RESUMEN =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nCSV por zona : {csv_out}")
    print(f"JSON resumen : {json_out}")


if __name__ == "__main__":
    main()
