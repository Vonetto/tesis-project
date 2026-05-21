from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ORIGIN_RESULTS_DIR = (
    PROJECT_ROOT
    / "03_models"
    / "biogeme-logit"
    / "results"
    / "16_eod2012_income_proxy_stepwise"
    / "pooled_2024_2025-biogeme-sample2pct"
)
RESIDENCE_RESULTS_DIR = (
    PROJECT_ROOT
    / "03_models"
    / "biogeme-logit"
    / "results"
    / "17_residence_socio_mnl_sensitivity"
    / "pooled_2024_2025-biogeme-sample2pct"
)
OUT_DIR = (
    PROJECT_ROOT
    / "tmp"
    / "audits"
    / "proposito_residence"
    / "parameter_comparison"
    / "sample2pct"
)

ORIGIN_MODEL = "mnl_joint_current_main_mujeres_parv_plus_eod_de_income_proxy_macro_parsimonious_plus_prom_edad"
HOME_ALTA_ORIGIN_MODEL = "mnl_origin_home_alta_parsimonious"
RESIDENCE_MODEL = "mnl_residence_home_alta_parsimonious"
RESIDENCE_ALTA_MEDIA_MODEL = "mnl_residence_home_alta_media_parsimonious"

VARIABLE_MAP = [
    (
        "socio_residencia",
        "educ_univ_o_mas",
        "share_cine18_universitaria_o_mas_micro_z",
        "res_share_cine18_universitaria_o_mas_micro_z",
    ),
    ("socio_residencia", "discapacidad", "share_discapacidad_z", "res_share_discapacidad_z"),
    ("socio_residencia", "inmigrantes", "share_inmigrantes_z", "res_share_inmigrantes_z"),
    ("socio_residencia", "mujeres", "share_mujeres_z", "res_share_mujeres_z"),
    (
        "socio_residencia",
        "asistencia_parv",
        "share_asistencia_parv_z",
        "res_share_asistencia_parv_z",
    ),
    ("socio_residencia", "edad_promedio", "prom_edad_z", "res_prom_edad_z"),
    (
        "socio_residencia",
        "income_proxy_de",
        "eod2012_share_hogares_de_income_proxy_z",
        "res_eod2012_share_hogares_de_income_proxy_z",
    ),
    (
        "entorno_origen",
        "osm_playground",
        "osm_leisure_playground_density_km2_z",
        "osm_leisure_playground_density_km2_z",
    ),
    (
        "entorno_origen",
        "osm_school",
        "osm_amenity_school_density_km2_z",
        "osm_amenity_school_density_km2_z",
    ),
    (
        "entorno_origen",
        "osm_university",
        "osm_amenity_university_density_km2_z",
        "osm_amenity_university_density_km2_z",
    ),
    (
        "entorno_origen",
        "osm_transport_shelter",
        "osm_transport_shelter_yes_density_km2_z",
        "osm_transport_shelter_yes_density_km2_z",
    ),
    (
        "entorno_origen",
        "osm_subway_entrance",
        "osm_railway_subway_entrance_density_km2_z",
        "osm_railway_subway_entrance_density_km2_z",
    ),
    ("macrozona_origen", "macro_norte", "macro_norte", "macro_norte"),
    ("macrozona_origen", "macro_poniente", "macro_poniente", "macro_poniente"),
    ("macrozona_origen", "macro_oriente", "macro_oriente", "macro_oriente"),
    ("macrozona_origen", "macro_sur", "macro_sur", "macro_sur"),
    ("macrozona_origen", "macro_suroriente", "macro_suroriente", "macro_suroriente"),
    (
        "macrozona_origen",
        "macro_externa_especial",
        "macro_externa_especial",
        "macro_externa_especial",
    ),
]

ORIGIN_IDENTITY_MAP = [
    (
        "socio_origen" if group == "socio_residencia" else group,
        concept,
        origin_var,
        origin_var,
    )
    for group, concept, origin_var, _ in VARIABLE_MAP
]

KEY_VARIABLES = [
    ("macro_oriente", "macro_oriente"),
    ("educ_univ_o_mas", "share_cine18_universitaria_o_mas_micro_z"),
    ("res_educ_univ_o_mas", "res_share_cine18_universitaria_o_mas_micro_z"),
    ("edad_promedio", "prom_edad_z"),
    ("res_edad_promedio", "res_prom_edad_z"),
    ("income_proxy_de", "eod2012_share_hogares_de_income_proxy_z"),
    ("res_income_proxy_de", "res_eod2012_share_hogares_de_income_proxy_z"),
    ("discapacidad", "share_discapacidad_z"),
    ("res_discapacidad", "res_share_discapacidad_z"),
    ("inmigrantes", "share_inmigrantes_z"),
    ("res_inmigrantes", "res_share_inmigrantes_z"),
]

MODEL_SUMMARY_SPECS = [
    {
        "model_code": "A",
        "model_label": "A_origen_full",
        "model": ORIGIN_MODEL,
        "results_dir": ORIGIN_RESULTS_DIR,
        "socio_measure": "origen",
        "sample_definition": "muestra completa",
        "main_comparison_role": "baseline historico",
    },
    {
        "model_code": "B",
        "model_label": "B_origen_home_alta",
        "model": HOME_ALTA_ORIGIN_MODEL,
        "results_dir": RESIDENCE_RESULTS_DIR,
        "socio_measure": "origen",
        "sample_definition": "home_alta",
        "main_comparison_role": "efecto filtro muestra",
    },
    {
        "model_code": "C",
        "model_label": "C_residencia_home_alta",
        "model": RESIDENCE_MODEL,
        "results_dir": RESIDENCE_RESULTS_DIR,
        "socio_measure": "residencia",
        "sample_definition": "home_alta",
        "main_comparison_role": "efecto residencia",
    },
]


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)


def load_model_params(path: Path, model: str) -> pd.DataFrame:
    require_file(path)
    df = pd.read_csv(path)
    out = df[df["model"] == model].copy()
    if out.empty:
        available = ", ".join(sorted(df["model"].dropna().unique()))
        raise ValueError(f"No se encontró modelo {model!r} en {path}. Disponibles: {available}")
    return out


def try_load_model_params(path: Path, model: str) -> pd.DataFrame | None:
    require_file(path)
    df = pd.read_csv(path)
    out = df[df["model"] == model].copy()
    if out.empty:
        return None
    return out


def load_convergence_row(results_dir: Path, model: str) -> pd.Series:
    path = results_dir / "convergence_summary.csv"
    require_file(path)
    df = pd.read_csv(path)
    out = df[df["model"] == model]
    if out.empty:
        available = ", ".join(sorted(df["model"].dropna().unique()))
        raise ValueError(f"No se encontró modelo {model!r} en {path}. Disponibles: {available}")
    return out.iloc[0]


def significance(p: float) -> str:
    if pd.isna(p):
        return "normalized_or_missing"
    if p < 0.01:
        return "p<0.01"
    if p < 0.05:
        return "p<0.05"
    if p < 0.10:
        return "p<0.10"
    return "ns"


def sign_label(beta: float) -> str:
    if pd.isna(beta):
        return "missing"
    if beta > 0:
        return "positive"
    if beta < 0:
        return "negative"
    return "zero"


def compare_params(
    origin: pd.DataFrame,
    residence: pd.DataFrame,
    variable_map: list[tuple[str, str, str, str]],
) -> pd.DataFrame:
    rows = []
    origin_idx = origin.set_index(["variable", "alternative"])
    residence_idx = residence.set_index(["variable", "alternative"])
    for group, concept, origin_var, residence_var in variable_map:
        for alternative in ["QR_RED", "QR_OTHER"]:
            if (origin_var, alternative) not in origin_idx.index:
                raise ValueError(f"Falta variable origen: {origin_var} / {alternative}")
            if (residence_var, alternative) not in residence_idx.index:
                raise ValueError(f"Falta variable residencia: {residence_var} / {alternative}")
            o = origin_idx.loc[(origin_var, alternative)]
            r = residence_idx.loc[(residence_var, alternative)]
            beta_origin = float(o["beta"])
            beta_residence = float(r["beta"])
            p_origin = float(o["robust_p"])
            p_residence = float(r["robust_p"])
            sign_origin = sign_label(beta_origin)
            sign_residence = sign_label(beta_residence)
            sig_origin = significance(p_origin)
            sig_residence = significance(p_residence)
            rows.append(
                {
                    "group": group,
                    "concept": concept,
                    "alternative": alternative,
                    "origin_variable": origin_var,
                    "residence_variable": residence_var,
                    "beta_origin": beta_origin,
                    "t_origin": o["robust_t"],
                    "p_origin": p_origin,
                    "sig_origin": sig_origin,
                    "beta_residence": beta_residence,
                    "t_residence": r["robust_t"],
                    "p_residence": p_residence,
                    "sig_residence": sig_residence,
                    "delta_beta_res_minus_origin": beta_residence - beta_origin,
                    "abs_delta_beta": abs(beta_residence - beta_origin),
                    "sign_origin": sign_origin,
                    "sign_residence": sign_residence,
                    "sign_change": sign_origin != sign_residence,
                    "loses_5pct_significance": p_origin < 0.05 and p_residence >= 0.05,
                    "gains_5pct_significance": p_origin >= 0.05 and p_residence < 0.05,
                }
            )
    return pd.DataFrame(rows).sort_values(["group", "concept", "alternative"])


def compare_base_params(origin: pd.DataFrame, residence: pd.DataFrame) -> pd.DataFrame:
    origin_key = origin.set_index(["variable", "alternative"])
    residence_key = residence.set_index(["variable", "alternative"])
    common_keys = sorted(set(origin_key.index) & set(residence_key.index))
    rows = []
    for variable, alternative in common_keys:
        o = origin_key.loc[(variable, alternative)]
        r = residence_key.loc[(variable, alternative)]
        beta_origin = float(o["beta"])
        beta_residence = float(r["beta"])
        p_origin = float(o["robust_p"])
        p_residence = float(r["robust_p"])
        rows.append(
            {
                "variable": variable,
                "alternative": alternative,
                "beta_origin": beta_origin,
                "t_origin": o["robust_t"],
                "p_origin": p_origin,
                "sig_origin": significance(p_origin),
                "beta_residence": beta_residence,
                "t_residence": r["robust_t"],
                "p_residence": p_residence,
                "sig_residence": significance(p_residence),
                "delta_beta_res_minus_origin": beta_residence - beta_origin,
                "abs_delta_beta": abs(beta_residence - beta_origin),
                "sign_origin": sign_label(beta_origin),
                "sign_residence": sign_label(beta_residence),
                "sign_change": sign_label(beta_origin) != sign_label(beta_residence),
                "loses_5pct_significance": p_origin < 0.05 and p_residence >= 0.05,
                "gains_5pct_significance": p_origin >= 0.05 and p_residence < 0.05,
            }
        )
    return pd.DataFrame(rows).sort_values(["variable", "alternative"])


def param_lookup(params: pd.DataFrame, variable: str, alternative: str) -> tuple[float | None, float | None]:
    subset = params[(params["variable"] == variable) & (params["alternative"] == alternative)]
    if subset.empty:
        return None, None
    row = subset.iloc[0]
    return float(row["beta"]), float(row["robust_p"])


def format_beta_p(beta: float | None, p_value: float | None) -> str:
    if beta is None or p_value is None or pd.isna(beta) or pd.isna(p_value):
        return ""
    return f"{beta:.3f}{significance_stars(p_value)}"


def significance_stars(p_value: float) -> str:
    if pd.isna(p_value):
        return ""
    if p_value < 0.01:
        return "***"
    if p_value < 0.05:
        return "**"
    if p_value < 0.10:
        return "*"
    return ""


def build_abc_summary_table() -> pd.DataFrame:
    rows = []
    for spec in MODEL_SUMMARY_SPECS:
        convergence = load_convergence_row(spec["results_dir"], spec["model"])
        new_params = load_model_params(spec["results_dir"] / "new_variable_parameters_long.csv", spec["model"])
        row = {
            "model_code": spec["model_code"],
            "model_label": spec["model_label"],
            "model": spec["model"],
            "sample_definition": spec["sample_definition"],
            "socio_measure": spec["socio_measure"],
            "main_comparison_role": spec["main_comparison_role"],
            "sample_size": int(float(convergence["sample_size"])),
            "n_params": int(float(convergence["n_params"])),
            "ll_final": float(convergence["ll_final"]),
            "aic": float(convergence["aic"]),
            "bic": float(convergence["bic"]),
            "status": convergence["status"],
        }
        for concept, variable in KEY_VARIABLES:
            for alternative in ["QR_RED", "QR_OTHER"]:
                beta, p_value = param_lookup(new_params, variable, alternative)
                row[f"{concept}_{alternative}_beta"] = beta
                row[f"{concept}_{alternative}_p"] = p_value
                row[f"{concept}_{alternative}"] = format_beta_p(beta, p_value)
        rows.append(row)
    return pd.DataFrame(rows)


def write_abc_summary() -> None:
    df = build_abc_summary_table()
    csv_path = OUT_DIR / "abc_model_summary_key_variables.csv"
    md_path = OUT_DIR / "abc_model_summary_key_variables.md"

    key_display_cols = [
        "model_code",
        "sample_definition",
        "socio_measure",
        "sample_size",
        "n_params",
        "ll_final",
        "aic",
        "bic",
        "macro_oriente_QR_RED",
        "educ_univ_o_mas_QR_RED",
        "res_educ_univ_o_mas_QR_RED",
        "edad_promedio_QR_RED",
        "res_edad_promedio_QR_RED",
        "income_proxy_de_QR_RED",
        "res_income_proxy_de_QR_RED",
        "discapacidad_QR_RED",
        "res_discapacidad_QR_RED",
        "inmigrantes_QR_RED",
        "res_inmigrantes_QR_RED",
        "macro_oriente_QR_OTHER",
    ]
    display_df = df[key_display_cols].copy()
    display_df["ll_final"] = display_df["ll_final"].round(1)
    display_df["aic"] = display_df["aic"].round(1)
    display_df["bic"] = display_df["bic"].round(1)

    df.to_csv(csv_path, index=False)
    md_path.write_text(
        "# Resumen A/B/C: ajuste y variables clave\n\n"
        "Celdas de coeficientes: `beta` con estrellas de significancia robusta "
        "(`***` p<0,01; `**` p<0,05; `*` p<0,10).\n\n"
        + display_df.to_markdown(index=False)
        + "\n",
        encoding="utf-8",
    )
    print(f"✅ Resumen A/B/C CSV: {csv_path}")
    print(f"✅ Resumen A/B/C Markdown: {md_path}")


def write_comparison_bundle(
    *,
    new_left: pd.DataFrame,
    new_right: pd.DataFrame,
    base_left: pd.DataFrame,
    base_right: pd.DataFrame,
    variable_map: list[tuple[str, str, str, str]],
    file_prefix: str,
) -> None:
    new_comparison = compare_params(new_left, new_right, variable_map)
    base_comparison = compare_base_params(base_left, base_right)

    new_path = OUT_DIR / f"{file_prefix}_new_variables.csv"
    base_path = OUT_DIR / f"{file_prefix}_base_variables.csv"
    summary_path = OUT_DIR / f"{file_prefix}_change_summary.csv"

    new_comparison.to_csv(new_path, index=False)
    base_comparison.to_csv(base_path, index=False)
    (
        new_comparison.groupby(["group", "alternative"], as_index=False)
        .agg(
            n_variables=("concept", "count"),
            n_sign_changes=("sign_change", "sum"),
            n_loses_5pct=("loses_5pct_significance", "sum"),
            n_gains_5pct=("gains_5pct_significance", "sum"),
            mean_abs_delta_beta=("abs_delta_beta", "mean"),
            max_abs_delta_beta=("abs_delta_beta", "max"),
        )
        .to_csv(summary_path, index=False)
    )

    print(f"✅ Comparación variables nuevas: {new_path}")
    print(f"✅ Comparación variables base: {base_path}")
    print(f"✅ Resumen de cambios: {summary_path}")


def write_outputs() -> None:
    origin_new = load_model_params(ORIGIN_RESULTS_DIR / "new_variable_parameters_long.csv", ORIGIN_MODEL)
    residence_new = load_model_params(
        RESIDENCE_RESULTS_DIR / "new_variable_parameters_long.csv", RESIDENCE_MODEL
    )
    origin_base = load_model_params(ORIGIN_RESULTS_DIR / "base_parameters_long.csv", ORIGIN_MODEL)
    residence_base = load_model_params(RESIDENCE_RESULTS_DIR / "base_parameters_long.csv", RESIDENCE_MODEL)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_comparison_bundle(
        new_left=origin_new,
        new_right=residence_new,
        base_left=origin_base,
        base_right=residence_base,
        variable_map=VARIABLE_MAP,
        file_prefix="origin_vs_home_alta_parsimonious",
    )
    write_abc_summary()

    home_origin_new = try_load_model_params(
        RESIDENCE_RESULTS_DIR / "new_variable_parameters_long.csv",
        HOME_ALTA_ORIGIN_MODEL,
    )
    home_origin_base = try_load_model_params(
        RESIDENCE_RESULTS_DIR / "base_parameters_long.csv",
        HOME_ALTA_ORIGIN_MODEL,
    )
    if home_origin_new is None or home_origin_base is None:
        print(
            "ℹ️ Modelo B todavía no está disponible en resultados. "
            f"Se omiten comparaciones A vs B y B vs C: {HOME_ALTA_ORIGIN_MODEL}"
        )
        return

    write_comparison_bundle(
        new_left=origin_new,
        new_right=home_origin_new,
        base_left=origin_base,
        base_right=home_origin_base,
        variable_map=ORIGIN_IDENTITY_MAP,
        file_prefix="origin_full_vs_home_alta_origin_parsimonious",
    )
    write_comparison_bundle(
        new_left=home_origin_new,
        new_right=residence_new,
        base_left=home_origin_base,
        base_right=residence_base,
        variable_map=VARIABLE_MAP,
        file_prefix="home_alta_origin_vs_home_alta_residence_parsimonious",
    )


if __name__ == "__main__":
    write_outputs()
