"""Preparación de datos para el MNL de adopción QR a nivel id_tarjeta.

Patrón: funciones de preparación (como lib/od_buffers_nested_logit.py para el
nivel viaje), NO clase fiteable. El modelo es DESCRIPTIVO (sin holdout), así que
las transformaciones se aplican sobre el universo completo: no hay folds ni
leakage que evitar.

Responsabilidad: tomar la matriz supervisada cruda
(user_model_matrix_*.parquet) y dejar las columnas listas para el MNL, aplicando
las transformaciones que el builder NO hizo (por contrato deja crudo):
  - log1p de n_viajes,
  - winsor p1-p99 de inmigrantes / parv (colas pesadas),
  - estandarización a z de las 2 franjas etarias (vienen crudas),
  - dummies de cohorte temporal (solo_2024 / mixta / solo_2025),
  - dummies de macrozona con referencia PONIENTE (drop de la dummy base),
  - drop de redundancias exactas r=±1.

Las socio que ya vienen en z (educación, de_proxy, etc.) y las shares de uso se
estandarizan aquí también para que todas las continuas queden en z comparable.

Salida: DataFrame idco (una fila por id_tarjeta) con x_i transformado + la
columna `choice` (1=BIP, 2=QR_RED, 3=QR_OTHER), consumible por
`lx.Dataset.construct.from_idco(...)` y por `biogeme.Database`.

Ver docs/planning/workstreams/user-level-econometric/{task_plan,notes}.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

# lib/user_level/mnl_prep.py -> parents[2] es la raíz del repo (parents[1]=lib/).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
USER_DIR = PROJECT_ROOT / "tmp" / "audits" / "user_level_redesign"

# --- Indicadores de inercia/regularidad (DSI/TSI/LSI de Lizana et al. 2023) ---
# Generados por scripts/audits/segmentation_window_sensitivity.py. Son índices
# de SIMILITUD intra-persona ENTRE dos ventanas (base vs eval), valor en [0,1]
# (1 = patrón idéntico). Existen SOLO para tarjetas activas en ambas ventanas
# (≥3 viajes y ≥2 días activos en cada lado): incorporarlos restringe el
# universo a usuarios recurrentes. Se mergean por id_tarjeta y se estandarizan.
INERTIA_DIR = PROJECT_ROOT / "tmp" / "audits" / "segmentation_window_sensitivity"
INERTIA_INDICES = [
    "dsi_day_sequence",       # regularidad de qué DÍAS viaja
    "tsi_time_distribution",  # regularidad de a qué HORA viaja
    "lsi_origin_zone",        # regularidad de desde qué ZONA sale
    "lsi_origin_stop",        # regularidad del PARADERO exacto (más granular)
]
# Set parsimonioso (DEFAULT): se DROPEA lsi_origin_zone porque correla r≈0.93
# con lsi_origin_stop (diagnóstico inertia_correlation 2026-06): meter ambos
# mete multicolinealidad. lsi_origin_stop es la versión más fina y se queda.
INERTIA_INDICES_PARSIMONIOUS = [
    "dsi_day_sequence",
    "tsi_time_distribution",
    "lsi_origin_stop",
]
# window_id -> parquet de indicadores. inter = 2024 vs 2025; intra = mismo año.
INERTIA_WINDOWS = {
    "inter_W15_W17": "indicators_W15_W17_clean_nonconsecutive.parquet",
    "inter_W17": "indicators_W17_baseline.parquet",
    "intra2024_W15_W17": "indicators_intra2024_W15_W17.parquet",
    "intra2025_W15_W17": "indicators_intra2025_W15_W17.parquet",
}

# Codificación de alternativas (BIP referencia, V=0).
ALT_MAP = {1: "BIP", 2: "QR_RED", 3: "QR_OTHER"}
TIPO_TARJETA_TO_CHOICE = {"BIP": 1, "QR_RED": 2, "QR_OTHER": 3}

# Macrozona de referencia (se DROPea su dummy). Divergente del nivel viaje
# (CENTRO): a nivel tarjeta la macrozona es residencia y PONIENTE domina (27%).
MACRO_REF = "poniente"
MACRO_LEVELS = ["norte", "poniente", "oriente", "centro", "sur", "suroriente",
                "externa_especial"]

# --- Definición del set x_i del main (nombres en la matriz cruda) ---
# Exposición / cohorte.
N_VIAJES_RAW = "n_viajes"            # -> log1p + z
SHARE_2025_RAW = "share_trips_2025"  # -> 3 dummies de cohorte

# Uso / conductual (todas a z).
USE_SHARES = [
    "share_lab_pm", "share_lab_pt", "share_no_lab",
    "share_trips_with_transfer", "share_trips_solo_metro", "share_trips_metro_bus",
]
USE_HORA = ["hora_mean", "hora_std"]            # a z
USE_TIEMPOS = ["t_vehiculo_mean_min", "t_espera_ini_mean_min"]  # winsor p99 + z

# Socio residencial.
SOCIO_ALREADY_Z = [
    "res_share_cine18_universitaria_o_mas_micro_z",   # educación
    "res_eod2012_share_hogares_de_income_proxy_z",    # D+E proxy
]
SOCIO_AGE_BANDS_RAW = ["res_age_share_25_44", "res_age_share_18_24"]  # crudas -> z
SOCIO_WINSOR = ["res_share_inmigrantes_z", "res_share_asistencia_parv_z"]  # winsor p1-p99 + z

# Redundancias exactas r=±1 (acordadas; se eliminan para identificación).
DROP_REDUNDANT = {
    "coarse_route_has_early_late_rcs",
    "service_within_od_variability_weighted",
    "offer_origin_metro_like_share",
}


def matrix_path(scope="interannual_ml", variant="clean", home_filter="alta",
                min_trips=3, min_home_trips=0) -> Path:
    suffix = f"{scope}_{variant}_{home_filter}_n{min_trips}"
    if min_home_trips > 0:
        suffix += f"_home{min_home_trips}"
    return USER_DIR / f"user_model_matrix_{suffix}.parquet"


# --------------------------------------------------------------------------
# Transformaciones atómicas (sobre el universo completo)
# --------------------------------------------------------------------------
def _zscore_expr(col: str, out: str | None = None) -> pl.Expr:
    out = out or col
    mean = pl.col(col).mean()
    std = pl.col(col).std(ddof=0)
    # std==0 -> deja 0 (constante); evita división por cero.
    return (
        pl.when(std == 0)
        .then(pl.lit(0.0))
        .otherwise((pl.col(col) - mean) / std)
        .alias(out)
    )


def _winsor_zscore_expr(col: str, p_lo: float, p_hi: float, out: str | None = None) -> pl.Expr:
    """Winsoriza a [p_lo, p_hi] y luego estandariza. Cuantiles sobre el universo."""
    out = out or col
    lo = pl.col(col).quantile(p_lo)
    hi = pl.col(col).quantile(p_hi)
    clipped = pl.col(col).clip(lo, hi)
    mean = clipped.mean()
    std = clipped.std(ddof=0)
    return (
        pl.when(std == 0)
        .then(pl.lit(0.0))
        .otherwise((clipped - mean) / std)
        .alias(out)
    )


# --------------------------------------------------------------------------
# Bloques de features
# --------------------------------------------------------------------------
def _build_cohort_dummies(df: pl.DataFrame) -> tuple[pl.DataFrame, list[str]]:
    """3 dummies de cohorte desde share_trips_2025 (bimodal). Referencia
    implícita: solo_2024 (se omite). Activas: mixta, solo_2025."""
    s = pl.col(SHARE_2025_RAW)
    df = df.with_columns([
        (s <= 0.0).cast(pl.Int8).alias("cohort_solo_2024"),
        ((s > 0.0) & (s < 1.0)).cast(pl.Int8).alias("cohort_mixta"),
        (s >= 1.0).cast(pl.Int8).alias("cohort_solo_2025"),
    ])
    # Referencia = solo_2024 (se omite del set). Activas:
    active = ["cohort_mixta", "cohort_solo_2025"]
    return df, active


def _macro_active_cols(prefix: str) -> list[str]:
    """Columnas de dummies de macrozona ACTIVAS (todas menos la referencia)."""
    return [f"{prefix}_macro_{lvl}" for lvl in MACRO_LEVELS if lvl != MACRO_REF]


def _merge_inertia(
    df: pl.DataFrame, windows: list[str], indices: list[str],
) -> tuple[pl.DataFrame, list[str]]:
    """INNER join de los índices de UNA o VARIAS ventanas de inercia.

    INNER (no left) porque incorporar los índices REDEFINE el universo a las
    tarjetas elegibles: no se imputa, se subsetea. Con VARIAS ventanas el
    universo es la INTERSECCIÓN (tarjeta elegible en todas) — para el modelo
    conjunto inter+intra. Cada ventana renombra sus índices con sufijo de
    etiqueta (`__inter`, `__intra2025`, ...) para que no colisionen.

    La estandarización z se hace AL FINAL, sobre el universo común resultante
    de todas las ventanas (no sobre el universo de cada parquet por separado),
    para que todas las columnas queden en z respecto a la misma población.

    Devuelve (df_filtrado_con_indices_z, [columnas_z finales]).
    """
    df = df.with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
    raw_cols: list[str] = []  # nombres crudos (con sufijo) antes del z

    for window_id in windows:
        if window_id not in INERTIA_WINDOWS:
            raise ValueError(
                f"window_id de inercia desconocido: {window_id!r}. "
                f"Opciones: {sorted(INERTIA_WINDOWS)}")
        path = INERTIA_DIR / INERTIA_WINDOWS[window_id]
        if not path.exists():
            raise FileNotFoundError(
                f"No existe el parquet de inercia: {path}\n"
                f"Genéralo con scripts/audits/segmentation_window_sensitivity.py "
                f"--window-id {window_id}")
        ind = pl.read_parquet(path)
        missing = [c for c in ["id_tarjeta", *indices] if c not in ind.columns]
        if missing:
            raise ValueError(f"Faltan columnas en {path.name}: {missing}")
        # etiqueta de bloque para los nombres (solo si hay >1 ventana, para no
        # romper compatibilidad con corridas de una sola ventana).
        tag = _window_tag(window_id)
        rename = {c: (f"{c}__{tag}" if len(windows) > 1 else c) for c in indices}
        ind = (ind.select(["id_tarjeta", *indices])
                  .with_columns(pl.col("id_tarjeta").cast(pl.Utf8))
                  .rename(rename))
        before = df.height
        df = df.join(ind, on="id_tarjeta", how="inner")
        print(f"[mnl_prep] inercia '{window_id}': {df.height:,} tarjetas tras join "
              f"(de {before:,} — {df.height/before:.1%})")
        if df.height == 0:
            raise ValueError(
                "El join de inercia dejó 0 tarjetas: "
                "¿ventana/universo incompatibles?")
        raw_cols.extend(rename.values())

    # z AL FINAL, sobre el universo común (intersección de todas las ventanas).
    z_exprs = [_zscore_expr(c, f"{c}_z") for c in raw_cols]
    df = df.with_columns(z_exprs)
    inertia_cols = [f"{c}_z" for c in raw_cols]
    if len(windows) > 1:
        print(f"[mnl_prep] modelo conjunto: {len(windows)} ventanas "
              f"{windows} -> {len(inertia_cols)} índices, "
              f"universo común {df.height:,} tarjetas.")
    return df, inertia_cols


def _window_tag(window_id: str) -> str:
    """Etiqueta corta para nombrar columnas de bloque (inter / intra2025 / ...).
    'inter_W15_W17' -> 'inter'; 'intra2025_W15_W17' -> 'intra2025'."""
    return window_id.split("_W")[0]


@dataclass
class MNLDataset:
    """Resultado de la preparación: idco listo para el MNL."""
    df: pl.DataFrame                 # una fila por id_tarjeta, x_i + choice
    choice_col: str                  # "choice"
    alt_map: dict                    # {1:BIP, 2:QR_RED, 3:QR_OTHER}
    feature_blocks: dict             # bloque -> [columnas finales]
    all_features: list[str] = field(default_factory=list)


def prepare_mnl_dataset(
    scope="interannual_ml", variant="clean", home_filter="alta",
    min_trips=3, min_home_trips=0, drop_no_macro=True,
    inertia_window: str | list[str] | None = None,
    inertia_indices: list[str] | None = None,
) -> MNLDataset:
    """Carga la matriz cruda y devuelve el idco transformado para el MNL main.

    drop_no_macro: si True, excluye las ~0,3% tarjetas sin macrozona real
    (las 6 dummies en 0). Son poquísimas y no representan una macrozona.

    inertia_window: str (una ventana) o list[str] (modelo CONJUNTO inter+intra).
    Mergea los índices DSI/TSI/LSI de esa(s) ventana(s) por INNER join. Con
    varias, el universo es la INTERSECCIÓN y cada ventana etiqueta sus columnas
    (`__inter`, `__intra2025`, ...). Ej.: ['inter_W15_W17','intra2025_W15_W17'].
    OJO: restringe el universo a tarjetas elegibles en TODAS las ventanas.

    inertia_indices: cuáles índices usar. DEFAULT = INERTIA_INDICES_PARSIMONIOUS
    (sin lsi_origin_zone, que correla r≈0.93 con lsi_origin_stop). Pasar
    list(INERTIA_INDICES) para los 4.
    """
    path = matrix_path(scope, variant, home_filter, min_trips, min_home_trips)
    if not path.exists():
        raise FileNotFoundError(f"No existe la matriz: {path}\n¿KINGSTON montado?")
    df = pl.read_parquet(path)

    # --- choice ---
    df = df.with_columns(
        pl.col("tipo_tarjeta").replace_strict(TIPO_TARJETA_TO_CHOICE,
                                              return_dtype=pl.Int8).alias("choice")
    )

    # --- exposición ---
    df = df.with_columns(
        (pl.col(N_VIAJES_RAW).log1p()).alias("log1p_n_viajes")
    )
    df = df.with_columns(_zscore_expr("log1p_n_viajes", "log1p_n_viajes_z"))
    exposure_cols = ["log1p_n_viajes_z"]

    # --- cohorte ---
    df, cohort_cols = _build_cohort_dummies(df)

    # --- uso: shares + hora a z; tiempos winsor p99 + z ---
    z_exprs = [_zscore_expr(c, f"{c}_z") for c in USE_SHARES + USE_HORA]
    z_exprs += [_winsor_zscore_expr(c, 0.0, 0.99, f"{c}_w99z") for c in USE_TIEMPOS]
    df = df.with_columns(z_exprs)
    use_cols = (
        [f"{c}_z" for c in USE_SHARES]
        + [f"{c}_z" for c in USE_HORA]
        + [f"{c}_w99z" for c in USE_TIEMPOS]
    )

    # --- socio ---
    # ya en z: se re-estandarizan sobre el universo main para consistencia
    # (vienen z respecto al universo del builder, no necesariamente al main).
    socio_z_exprs = [_zscore_expr(c, f"{c}_main") for c in SOCIO_ALREADY_Z]
    socio_z_exprs += [_zscore_expr(c, f"{c}_z") for c in SOCIO_AGE_BANDS_RAW]
    socio_z_exprs += [_winsor_zscore_expr(c, 0.01, 0.99, f"{c}_w") for c in SOCIO_WINSOR]
    df = df.with_columns(socio_z_exprs)
    socio_cols = (
        [f"{c}_main" for c in SOCIO_ALREADY_Z]
        + [f"{c}_z" for c in SOCIO_AGE_BANDS_RAW]
        + [f"{c}_w" for c in SOCIO_WINSOR]
    )

    # --- geografía: dummies macro (ref PONIENTE), home + origin_top1 ---
    home_macro = _macro_active_cols("home")
    origin_macro = _macro_active_cols("origin_top1")
    geo_cols = home_macro + origin_macro

    # opcionalmente excluir tarjetas sin macrozona real (6 dummies en 0)
    if drop_no_macro:
        home_all = [f"home_macro_{lvl}" for lvl in MACRO_LEVELS]
        origin_all = [f"origin_top1_macro_{lvl}" for lvl in MACRO_LEVELS]
        home_sum = pl.sum_horizontal([pl.col(c).fill_null(0) for c in home_all])
        origin_sum = pl.sum_horizontal([pl.col(c).fill_null(0) for c in origin_all])
        before = df.height
        df = df.filter((home_sum > 0) & (origin_sum > 0))
        n_dropped = before - df.height
        if n_dropped:
            print(f"[mnl_prep] excluidas {n_dropped:,} tarjetas sin macrozona "
                  f"(home u origin) — {n_dropped/before:.2%}")

    # --- inercia (opcional): merge índices DSI/TSI/LSI, restringe universo ---
    inertia_cols: list[str] = []
    if inertia_window is not None:
        # normalizar a lista (acepta str o list[str] para modelo conjunto)
        windows = [inertia_window] if isinstance(inertia_window, str) else list(inertia_window)
        # default parsimonioso: sin lsi_origin_zone (r≈0.93 con lsi_origin_stop)
        indices = inertia_indices or list(INERTIA_INDICES_PARSIMONIOUS)
        df, inertia_cols = _merge_inertia(df, windows, indices)

    # --- cohorte: chequeo de degeneración ---
    # En ventanas INTRA-anuales (base y eval del mismo año), la categoría de
    # referencia solo_2024 puede quedar VACÍA (toda tarjeta elegible viajó en
    # ese año), volviendo cohort_mixta + cohort_solo_2025 perfectamente
    # colineales con la constante (ASC). Eso hace el modelo NO identificado
    # (Larch explota a ±1e7, Biogeme lo amortigua a ~0). Si la referencia
    # quedó vacía, se DROPEA el bloque cohorte (no aplica intra-anual).
    ref_count = (df.select(
        ((pl.col("cohort_mixta") == 0) & (pl.col("cohort_solo_2025") == 0))
        .sum().alias("n_ref")
    ).item())
    if ref_count == 0 and cohort_cols:
        print(f"[mnl_prep] cohorte de referencia (solo_2024) VACÍA en este "
              f"universo (ventana intra-anual): se DROPEA el bloque cohorte "
              f"({cohort_cols}) para evitar no-identificación.")
        cohort_cols = []

    # --- ensamblar bloques y seleccionar ---
    feature_blocks = {
        "exposure": exposure_cols,
        "cohort": cohort_cols,
        "use": use_cols,
        "socio": socio_cols,
        "geo": geo_cols,
    }
    if inertia_cols:
        feature_blocks["inertia"] = inertia_cols
    all_features = [c for block in feature_blocks.values() for c in block]
    # quitar redundancias r=1 por si alguna se colara (no deberían estar en x_i main)
    all_features = [c for c in all_features if c not in DROP_REDUNDANT]

    keep = ["id_tarjeta", "tipo_tarjeta", "choice", *all_features]
    keep = list(dict.fromkeys(keep))  # dedupe preservando orden
    missing = [c for c in keep if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas esperadas en la matriz: {missing}")
    out = df.select(keep)

    # Listwise deletion: el logit no acepta NaN. Excluir filas con NaN en
    # cualquier feature del main (missing residual de socio/tiempos, ~0,3%).
    before = out.height
    out = out.drop_nulls(subset=all_features)
    n_nan = before - out.height
    if n_nan:
        print(f"[mnl_prep] excluidas {n_nan:,} tarjetas con NaN en features "
              f"(listwise deletion) — {n_nan/before:.2%}")

    return MNLDataset(
        df=out,
        choice_col="choice",
        alt_map=ALT_MAP,
        feature_blocks=feature_blocks,
        all_features=all_features,
    )


def stratified_subsample(df: pl.DataFrame, frac: float, seed: int = 42) -> pl.DataFrame:
    """Submuestra estratificada por tipo_tarjeta, DETERMINÍSTICA por id_tarjeta.

    Usa el hash del id_tarjeta (no rng.choice) para que la selección sea idéntica
    independiente del orden de iteración o del estado del RNG. Esto permite que
    Biogeme y Larch usen EXACTAMENTE las mismas tarjetas (validación cruzada).

    Mantiene la proporción por clase: incluye una tarjeta si
    hash(id, seed) mod 1_000_000 < frac*1_000_000, aplicado por estrato.
    """
    if not (0 < frac < 1):
        return df
    threshold = int(frac * 1_000_000)
    # hash determinístico del id concatenado con el seed
    keyed = df.with_columns(
        (pl.col("id_tarjeta").cast(pl.Utf8) + f"_{seed}").hash().alias("_h")
    )
    # módulo 1e6 del hash; selecciona si cae bajo el umbral
    keyed = keyed.with_columns((pl.col("_h") % 1_000_000).alias("_hm"))
    out = keyed.filter(pl.col("_hm") < threshold).drop(["_h", "_hm"])
    return out
