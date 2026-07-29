"""Diagnóstico de correlación entre los índices de inercia inter vs intra-anual.

Antes de plantear un MNL con AMBOS bloques (inter + intra), hay que saber si
aportan información distinta o si son redundantes. Los índices DSI/TSI/LSI
inter-anuales (2024 vs 2025) e intra-anuales (W15 vs W17 del mismo año) miden el
MISMO constructo (regularidad de hábito) sobre periodos SOLAPADOS (abril 2025
está en ambos), así que es muy probable que correlacionen.

Decisión que informa:
  - r BAJO (< ~0.5): los bloques aportan señal distinta -> modelo conjunto tiene
    sentido (¿persistencia inter-anual aporta MÁS ALLÁ de la regularidad intra?).
  - r ALTO (> ~0.7): redundantes -> reportar ventanas por separado o índice
    combinado; el modelo conjunto sería colineal (coefs inestables).

Cruza por id_tarjeta SOLO el universo común (inner join), que es el que de
verdad usaría un modelo con ambos bloques.

Uso (Mac, larch-env):
  python scripts/user_level/diagnose_inertia_correlation.py

  # comparar inter vs intra-2024 en vez de intra-2025:
  python scripts/user_level/diagnose_inertia_correlation.py --intra intra2024_W15_W17

Output: tmp/audits/user_level_redesign/inertia_correlation_<inter>_vs_<intra>.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.user_level import mnl_prep as mp

OUT_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"


def _load_indices(window_id: str) -> pl.DataFrame:
    """Carga el parquet de índices de una ventana, solo id + los 4 índices."""
    if window_id not in mp.INERTIA_WINDOWS:
        raise ValueError(f"ventana desconocida: {window_id}. "
                         f"Opciones: {sorted(mp.INERTIA_WINDOWS)}")
    path = mp.INERTIA_DIR / mp.INERTIA_WINDOWS[window_id]
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    df = pl.read_parquet(path).select(
        ["id_tarjeta", *mp.INERTIA_INDICES]
    ).with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inter", default="inter_W15_W17",
                    help="ventana inter-anual (default inter_W15_W17)")
    ap.add_argument("--intra", default="intra2025_W15_W17",
                    help="ventana intra-anual (default intra2025_W15_W17)")
    args = ap.parse_args()

    print(f"Cargando índices: inter='{args.inter}' intra='{args.intra}'")
    inter = _load_indices(args.inter)
    intra = _load_indices(args.intra)
    print(f"  inter: {inter.height:,} tarjetas | intra: {intra.height:,} tarjetas")

    # Sufijos para distinguir los bloques tras el join.
    inter = inter.rename({c: f"{c}__inter" for c in mp.INERTIA_INDICES})
    intra = intra.rename({c: f"{c}__intra" for c in mp.INERTIA_INDICES})

    # Universo COMÚN (inner): el que usaría un modelo con ambos bloques.
    common = inter.join(intra, on="id_tarjeta", how="inner")
    n = common.height
    print(f"  universo común (inner): {n:,} tarjetas "
          f"({n/inter.height:.1%} del inter, {n/intra.height:.1%} del intra)")
    if n == 0:
        raise SystemExit("Universo común vacío.")

    # --- Correlación: cada índice consigo mismo (inter vs intra), que es la
    # diagonal de interés (mismo constructo en periodos distintos). Pearson. ---
    pdf = common.to_pandas()
    print("\n=== Correlación inter vs intra del MISMO índice (Pearson) ===")
    print(f"{'índice':<26} {'r (inter,intra)':>16} {'lectura':>12}")
    diag_rows = []
    for idx in mp.INERTIA_INDICES:
        a = pdf[f"{idx}__inter"].to_numpy()
        b = pdf[f"{idx}__intra"].to_numpy()
        mask = ~(np.isnan(a) | np.isnan(b))
        r = float(np.corrcoef(a[mask], b[mask])[0, 1]) if mask.sum() > 1 else np.nan
        lectura = "ALTA" if abs(r) > 0.7 else ("media" if abs(r) > 0.5 else "baja")
        print(f"{idx:<26} {r:>16.4f} {lectura:>12}")
        diag_rows.append({"indice": idx, "r_inter_intra": r, "lectura": lectura})

    # --- Matriz de correlación completa de los 8 (para ver cruces) ---
    cols8 = [f"{c}__inter" for c in mp.INERTIA_INDICES] + \
            [f"{c}__intra" for c in mp.INERTIA_INDICES]
    corr = pdf[cols8].corr()
    print("\n=== Matriz de correlación completa (8 índices) ===")
    with pl.Config(tbl_cols=-1, tbl_rows=-1, fmt_str_lengths=40):
        print(corr.round(3).to_string())

    # Guardar.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    diag_path = OUT_DIR / f"inertia_correlation_{args.inter}_vs_{args.intra}.csv"
    pl.DataFrame(diag_rows).write_csv(diag_path)
    corr_path = OUT_DIR / f"inertia_corrmatrix_{args.inter}_vs_{args.intra}.csv"
    corr.to_csv(corr_path)
    print(f"\n✅ diagonal -> {diag_path}")
    print(f"   matriz   -> {corr_path}")

    # Veredicto rápido.
    rs = [r["r_inter_intra"] for r in diag_rows if not np.isnan(r["r_inter_intra"])]
    rmax = max(abs(x) for x in rs)
    print(f"\nVEREDICTO: |r| máx diagonal = {rmax:.3f} -> ", end="")
    if rmax > 0.7:
        print("REDUNDANTES. Modelo conjunto sería colineal; reportar por separado.")
    elif rmax > 0.5:
        print("correlación media. Modelo conjunto posible pero vigilar VIF/estabilidad.")
    else:
        print("aportan señal distinta. Modelo conjunto tiene sentido.")


if __name__ == "__main__":
    main()
