from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/external/eod2012/raw_csv"
OUT = ROOT / "data/processed/eod2012"
EOD_ZONES = Path("/Users/vicenteonetto/Downloads/Zonificacion_EOD-2012_Santiago/Zonificacion_EOD2012.shp")


def safe_div(num: pd.Series, den: pd.Series) -> pd.Series:
    return num.divide(den.where(den.ne(0)))


def weighted_mean(x: pd.Series, w: pd.Series) -> float:
    mask = x.notna() & w.notna() & w.gt(0)
    if not mask.any():
        return np.nan
    return float(np.average(x[mask], weights=w[mask]))


def weighted_median(x: pd.Series, w: pd.Series) -> float:
    mask = x.notna() & w.notna() & w.gt(0)
    if not mask.any():
        return np.nan
    xx = x[mask].to_numpy()
    ww = w[mask].to_numpy()
    order = np.argsort(xx)
    xx = xx[order]
    ww = ww[order]
    cutoff = ww.sum() / 2
    return float(xx[np.searchsorted(np.cumsum(ww), cutoff)])


def weighted_quantiles(x: pd.Series, w: pd.Series, qs: list[float]) -> dict[float, float]:
    mask = x.notna() & w.notna() & w.gt(0)
    if not mask.any():
        return {q: np.nan for q in qs}
    xx = x[mask].to_numpy()
    ww = w[mask].to_numpy()
    order = np.argsort(xx)
    xx = xx[order]
    ww = ww[order]
    cdf = np.cumsum(ww) / ww.sum()
    return {q: float(xx[np.searchsorted(cdf, q)]) for q in qs}


def parse_hour(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, format="%m/%d/%y %H:%M:%S", errors="coerce")
    return dt.dt.hour + dt.dt.minute / 60.0


def aggregate_hogar(hogar: pd.DataFrame) -> pd.DataFrame:
    h = hogar.copy()
    h["Zona"] = pd.to_numeric(h["Zona"], errors="coerce").astype("Int64")
    h["Factor"] = pd.to_numeric(h["Factor"], errors="coerce")
    h["IngresoHogar"] = pd.to_numeric(h["IngresoHogar"], errors="coerce")
    h["NumVeh"] = pd.to_numeric(h["NumVeh"], errors="coerce")
    h["NumPer"] = pd.to_numeric(h["NumPer"], errors="coerce")

    h["w"] = h["Factor"]
    income_cuts = weighted_quantiles(h["IngresoHogar"], h["w"], [0.10, 0.45, 0.70, 0.90])
    p10 = income_cuts[0.10]
    p45 = income_cuts[0.45]
    p70 = income_cuts[0.70]
    p90 = income_cuts[0.90]
    h["w_income_low_abs2012"] = h["w"] * h["IngresoHogar"].le(400_000)
    h["w_income_mid_abs2012"] = h["w"] * h["IngresoHogar"].between(400_001, 1_600_000)
    h["w_income_high_abs2012"] = h["w"] * h["IngresoHogar"].gt(1_600_000)
    h["w_income_proxy_e"] = h["w"] * h["IngresoHogar"].le(p10)
    h["w_income_proxy_d"] = h["w"] * h["IngresoHogar"].gt(p10) * h["IngresoHogar"].le(p45)
    h["w_income_proxy_c3"] = h["w"] * h["IngresoHogar"].gt(p45) * h["IngresoHogar"].le(p70)
    h["w_income_proxy_c2"] = h["w"] * h["IngresoHogar"].gt(p70) * h["IngresoHogar"].le(p90)
    h["w_income_proxy_abc1"] = h["w"] * h["IngresoHogar"].gt(p90)
    h["w_income_proxy_de"] = h["w_income_proxy_e"] + h["w_income_proxy_d"]
    h["w_no_vehicle"] = h["w"] * h["NumVeh"].fillna(0).eq(0)
    h["w_income"] = h["w"] * h["IngresoHogar"]
    h["w_numveh"] = h["w"] * h["NumVeh"]
    h["w_numper"] = h["w"] * h["NumPer"]

    base = (
        h.groupby("Zona", dropna=True)
        .agg(
            eod2012_hogares_w=("w", "sum"),
            eod2012_share_hogares_ingreso_bajo_abs2012_num=("w_income_low_abs2012", "sum"),
            eod2012_share_hogares_ingreso_medio_abs2012_num=("w_income_mid_abs2012", "sum"),
            eod2012_share_hogares_ingreso_alto_abs2012_num=("w_income_high_abs2012", "sum"),
            eod2012_share_hogares_e_income_proxy_num=("w_income_proxy_e", "sum"),
            eod2012_share_hogares_d_income_proxy_num=("w_income_proxy_d", "sum"),
            eod2012_share_hogares_c3_income_proxy_num=("w_income_proxy_c3", "sum"),
            eod2012_share_hogares_c2_income_proxy_num=("w_income_proxy_c2", "sum"),
            eod2012_share_hogares_abc1_income_proxy_num=("w_income_proxy_abc1", "sum"),
            eod2012_share_hogares_de_income_proxy_num=("w_income_proxy_de", "sum"),
            eod2012_share_hogares_sin_auto_num=("w_no_vehicle", "sum"),
            eod2012_ingreso_hogar_mean_num=("w_income", "sum"),
            eod2012_numveh_mean_num=("w_numveh", "sum"),
            eod2012_numper_hogar_mean_num=("w_numper", "sum"),
            eod2012_hogares_sample=("Hogar", "count"),
        )
        .reset_index()
    )
    den = base["eod2012_hogares_w"]
    base["eod2012_share_hogares_ingreso_bajo_abs2012"] = safe_div(
        base["eod2012_share_hogares_ingreso_bajo_abs2012_num"], den
    )
    base["eod2012_share_hogares_ingreso_medio_abs2012"] = safe_div(
        base["eod2012_share_hogares_ingreso_medio_abs2012_num"], den
    )
    base["eod2012_share_hogares_ingreso_alto_abs2012"] = safe_div(
        base["eod2012_share_hogares_ingreso_alto_abs2012_num"], den
    )
    for col in [
        "eod2012_share_hogares_e_income_proxy",
        "eod2012_share_hogares_d_income_proxy",
        "eod2012_share_hogares_c3_income_proxy",
        "eod2012_share_hogares_c2_income_proxy",
        "eod2012_share_hogares_abc1_income_proxy",
        "eod2012_share_hogares_de_income_proxy",
    ]:
        base[col] = safe_div(base[f"{col}_num"], den)
    base["eod2012_share_hogares_sin_auto"] = safe_div(
        base["eod2012_share_hogares_sin_auto_num"], den
    )
    base["eod2012_ingreso_hogar_mean"] = safe_div(base["eod2012_ingreso_hogar_mean_num"], den)
    base["eod2012_numveh_mean"] = safe_div(base["eod2012_numveh_mean_num"], den)
    base["eod2012_numper_hogar_mean"] = safe_div(base["eod2012_numper_hogar_mean_num"], den)

    med = (
        h.groupby("Zona", dropna=True)
        .apply(lambda g: weighted_median(g["IngresoHogar"], g["w"]), include_groups=False)
        .rename("eod2012_ingreso_hogar_median")
        .reset_index()
    )
    base = base.merge(med, on="Zona", how="left")
    base["eod2012_ingreso_hogar_mean_pct_rank"] = base["eod2012_ingreso_hogar_mean"].rank(
        pct=True
    )
    base["eod2012_ingreso_hogar_median_pct_rank"] = base[
        "eod2012_ingreso_hogar_median"
    ].rank(pct=True)

    keep = ["Zona"] + [c for c in base.columns if c.startswith("eod2012_") and not c.endswith("_num")]
    return base[keep]


def aggregate_persona(persona: pd.DataFrame, hogar: pd.DataFrame) -> pd.DataFrame:
    p = persona.merge(hogar[["Hogar", "Zona"]], on="Hogar", how="left", validate="many_to_one")
    p["Zona"] = pd.to_numeric(p["Zona"], errors="coerce").astype("Int64")
    p["Factor"] = pd.to_numeric(p["Factor"], errors="coerce")
    p["Sexo"] = pd.to_numeric(p["Sexo"], errors="coerce")
    p["Actividad"] = p["Actividad"].astype("string")
    p["Estudios"] = pd.to_numeric(p["Estudios"], errors="coerce")
    p["JornadaTrabajo"] = pd.to_numeric(p["JornadaTrabajo"], errors="coerce")
    p["AnoNac"] = pd.to_numeric(p["AnoNac"], errors="coerce")
    p["edad_2012_aprox"] = 2012 - p["AnoNac"]

    p["w"] = p["Factor"]
    p["w_mujer"] = p["w"] * p["Sexo"].eq(2)
    # Actividad is stored as multiselect letters in Persona (A, B, A;B, ...).
    # The observed pattern and survey labels indicate A=trabaja, B=estudia.
    p["act_trabaja"] = p["Actividad"].str.contains("A", na=False)
    p["act_estudia"] = p["Actividad"].str.contains("B", na=False)
    p["w_trabaja"] = p["w"] * p["act_trabaja"]
    p["w_estudia"] = p["w"] * p["act_estudia"]
    p["w_universitaria"] = p["w"] * p["Estudios"].eq(11)
    p["w_superior"] = p["w"] * p["Estudios"].isin([9, 10, 11])
    p["w_trabaja_jornada_completa"] = p["w"] * (p["act_trabaja"] & p["JornadaTrabajo"].eq(1))
    p["w_trabaja_jornada_parcial"] = p["w"] * (p["act_trabaja"] & p["JornadaTrabajo"].eq(2))
    p["w_edad"] = p["w"] * p["edad_2012_aprox"]

    out = (
        p.groupby("Zona", dropna=True)
        .agg(
            eod2012_personas_w=("w", "sum"),
            eod2012_personas_sample=("Persona", "count"),
            eod2012_share_mujeres_num=("w_mujer", "sum"),
            eod2012_share_trabaja_num=("w_trabaja", "sum"),
            eod2012_share_estudia_num=("w_estudia", "sum"),
            eod2012_share_educ_universitaria_num=("w_universitaria", "sum"),
            eod2012_share_educ_superior_num=("w_superior", "sum"),
            eod2012_share_trabaja_jornada_completa_num=("w_trabaja_jornada_completa", "sum"),
            eod2012_share_trabaja_jornada_parcial_num=("w_trabaja_jornada_parcial", "sum"),
            eod2012_edad_mean_num=("w_edad", "sum"),
        )
        .reset_index()
    )
    den = out["eod2012_personas_w"]
    workers = out["eod2012_share_trabaja_num"]
    for col in [
        "eod2012_share_mujeres",
        "eod2012_share_trabaja",
        "eod2012_share_estudia",
        "eod2012_share_educ_universitaria",
        "eod2012_share_educ_superior",
    ]:
        out[col] = safe_div(out[f"{col}_num"], den)
    out["eod2012_share_trabaja_jornada_completa"] = safe_div(
        out["eod2012_share_trabaja_jornada_completa_num"], workers
    )
    out["eod2012_share_trabaja_jornada_parcial"] = safe_div(
        out["eod2012_share_trabaja_jornada_parcial_num"], workers
    )
    out["eod2012_edad_mean"] = safe_div(out["eod2012_edad_mean_num"], den)

    keep = ["Zona"] + [c for c in out.columns if c.startswith("eod2012_") and not c.endswith("_num")]
    return out[keep]


def aggregate_viaje(viaje: pd.DataFrame) -> pd.DataFrame:
    v = viaje.copy()
    v["Zona"] = pd.to_numeric(v["ZonaOrigen"], errors="coerce").astype("Int64")
    v["FactorLaboralNormal"] = pd.to_numeric(v["FactorLaboralNormal"], errors="coerce")
    v["PropositoAgregado"] = pd.to_numeric(v["PropositoAgregado"], errors="coerce")
    v["Proposito"] = pd.to_numeric(v["Proposito"], errors="coerce")
    v["ModoPriPub"] = pd.to_numeric(v["ModoPriPub"], errors="coerce")
    v["Periodo"] = pd.to_numeric(v["Periodo"], errors="coerce")
    v["HoraIniNum"] = parse_hour(v["HoraIni"])

    # Use normal weekday expansion for temporal/work-pattern features.
    v = v[v["FactorLaboralNormal"].notna()].copy()
    v["w"] = v["FactorLaboralNormal"]
    v["is_work"] = v["PropositoAgregado"].eq(1)
    v["is_study"] = v["PropositoAgregado"].eq(2)
    v["is_to_work"] = v["Proposito"].eq(1)
    v["is_to_study"] = v["Proposito"].eq(3)
    v["is_public_transport"] = v["ModoPriPub"].eq(2)
    v["is_peak_am"] = v["Periodo"].isin([1, 2])
    v["is_peak_pm"] = v["Periodo"].eq(4)
    v["is_night"] = v["Periodo"].eq(6)

    for flag in [
        "is_work",
        "is_study",
        "is_to_work",
        "is_to_study",
        "is_public_transport",
        "is_peak_am",
        "is_peak_pm",
        "is_night",
    ]:
        v[f"w_{flag}"] = v["w"] * v[flag]
    v["w_work_peak_am"] = v["w"] * (v["is_work"] & v["is_peak_am"])
    v["w_work_peak_pm"] = v["w"] * (v["is_work"] & v["is_peak_pm"])
    v["w_study_peak_am"] = v["w"] * (v["is_study"] & v["is_peak_am"])
    v["w_to_work_peak_am"] = v["w"] * (v["is_to_work"] & v["is_peak_am"])
    v["w_to_study_peak_am"] = v["w"] * (v["is_to_study"] & v["is_peak_am"])

    out = (
        v.groupby("Zona", dropna=True)
        .agg(
            eod2012_viajes_laboral_w=("w", "sum"),
            eod2012_viajes_laboral_sample=("Viaje", "count"),
            eod2012_share_viajes_trabajo_num=("w_is_work", "sum"),
            eod2012_share_viajes_estudio_num=("w_is_study", "sum"),
            eod2012_share_viajes_al_trabajo_num=("w_is_to_work", "sum"),
            eod2012_share_viajes_al_estudio_num=("w_is_to_study", "sum"),
            eod2012_share_viajes_transporte_publico_num=("w_is_public_transport", "sum"),
            eod2012_share_viajes_punta_manana_num=("w_is_peak_am", "sum"),
            eod2012_share_viajes_punta_tarde_num=("w_is_peak_pm", "sum"),
            eod2012_share_viajes_noche_num=("w_is_night", "sum"),
            eod2012_share_viajes_trabajo_punta_manana_num=("w_work_peak_am", "sum"),
            eod2012_share_viajes_trabajo_punta_tarde_num=("w_work_peak_pm", "sum"),
            eod2012_share_viajes_estudio_punta_manana_num=("w_study_peak_am", "sum"),
            eod2012_share_viajes_al_trabajo_punta_manana_num=("w_to_work_peak_am", "sum"),
            eod2012_share_viajes_al_estudio_punta_manana_num=("w_to_study_peak_am", "sum"),
        )
        .reset_index()
    )
    den = out["eod2012_viajes_laboral_w"]
    work_den = out["eod2012_share_viajes_trabajo_num"]
    study_den = out["eod2012_share_viajes_estudio_num"]
    to_work_den = out["eod2012_share_viajes_al_trabajo_num"]
    to_study_den = out["eod2012_share_viajes_al_estudio_num"]
    for col in [
        "eod2012_share_viajes_trabajo",
        "eod2012_share_viajes_estudio",
        "eod2012_share_viajes_al_trabajo",
        "eod2012_share_viajes_al_estudio",
        "eod2012_share_viajes_transporte_publico",
        "eod2012_share_viajes_punta_manana",
        "eod2012_share_viajes_punta_tarde",
        "eod2012_share_viajes_noche",
    ]:
        out[col] = safe_div(out[f"{col}_num"], den)
    out["eod2012_share_viajes_trabajo_punta_manana"] = safe_div(
        out["eod2012_share_viajes_trabajo_punta_manana_num"], work_den
    )
    out["eod2012_share_viajes_trabajo_punta_tarde"] = safe_div(
        out["eod2012_share_viajes_trabajo_punta_tarde_num"], work_den
    )
    out["eod2012_share_viajes_estudio_punta_manana"] = safe_div(
        out["eod2012_share_viajes_estudio_punta_manana_num"], study_den
    )
    out["eod2012_share_viajes_al_trabajo_punta_manana"] = safe_div(
        out["eod2012_share_viajes_al_trabajo_punta_manana_num"], to_work_den
    )
    out["eod2012_share_viajes_al_estudio_punta_manana"] = safe_div(
        out["eod2012_share_viajes_al_estudio_punta_manana_num"], to_study_den
    )

    work = v[v["is_work"]].groupby("Zona").apply(
        lambda g: weighted_mean(g["HoraIniNum"], g["w"]), include_groups=False
    ).rename("eod2012_hora_inicio_trabajo_mean")
    study = v[v["is_study"]].groupby("Zona").apply(
        lambda g: weighted_mean(g["HoraIniNum"], g["w"]), include_groups=False
    ).rename("eod2012_hora_inicio_estudio_mean")
    to_work = v[v["is_to_work"]].groupby("Zona").apply(
        lambda g: weighted_mean(g["HoraIniNum"], g["w"]), include_groups=False
    ).rename("eod2012_hora_inicio_al_trabajo_mean")
    to_study = v[v["is_to_study"]].groupby("Zona").apply(
        lambda g: weighted_mean(g["HoraIniNum"], g["w"]), include_groups=False
    ).rename("eod2012_hora_inicio_al_estudio_mean")
    out = out.merge(work.reset_index(), on="Zona", how="left").merge(
        study.reset_index(), on="Zona", how="left"
    )
    out = out.merge(to_work.reset_index(), on="Zona", how="left").merge(
        to_study.reset_index(), on="Zona", how="left"
    )

    keep = ["Zona"] + [c for c in out.columns if c.startswith("eod2012_") and not c.endswith("_num")]
    return out[keep]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    hogar = pd.read_csv(RAW / "Hogar.csv")
    persona = pd.read_csv(RAW / "Persona.csv")
    viaje = pd.read_csv(RAW / "Viaje.csv")
    h_income = hogar.copy()
    h_income["Factor"] = pd.to_numeric(h_income["Factor"], errors="coerce")
    h_income["IngresoHogar"] = pd.to_numeric(h_income["IngresoHogar"], errors="coerce")
    cuts = weighted_quantiles(h_income["IngresoHogar"], h_income["Factor"], [0.10, 0.45, 0.70, 0.90])
    pd.DataFrame(
        [
            {"group": "E", "percentile_min": 0, "percentile_max": 10, "income_max_2012": cuts[0.10]},
            {"group": "D", "percentile_min": 10, "percentile_max": 45, "income_max_2012": cuts[0.45]},
            {"group": "C3", "percentile_min": 45, "percentile_max": 70, "income_max_2012": cuts[0.70]},
            {"group": "C2", "percentile_min": 70, "percentile_max": 90, "income_max_2012": cuts[0.90]},
            {"group": "ABC1_proxy", "percentile_min": 90, "percentile_max": 100, "income_max_2012": pd.NA},
        ]
    ).to_csv(OUT / "eod2012_income_proxy_cutpoints.csv", index=False)
    zones = gpd.read_file(EOD_ZONES)[["Zona", "Com", "Comuna", "AREA", "geometry"]]
    zones["Zona"] = pd.to_numeric(zones["Zona"], errors="coerce").astype("Int64")

    df = zones.drop(columns="geometry").merge(aggregate_hogar(hogar), on="Zona", how="left")
    df = df.merge(aggregate_persona(persona, hogar[["Hogar", "Zona"]]), on="Zona", how="left")
    df = df.merge(aggregate_viaje(viaje), on="Zona", how="left")

    df = df.sort_values("Zona")
    df.to_parquet(OUT / "eod2012_zone_features_eodzone.parquet", index=False)
    df.to_csv(OUT / "eod2012_zone_features_eodzone.csv", index=False)

    feature_cols = [c for c in df.columns if c.startswith("eod2012_")]
    summary = (
        df[feature_cols]
        .agg(["count", "mean", "std", "min", "median", "max"])
        .T.reset_index()
        .rename(columns={"index": "variable"})
    )
    summary.to_csv(OUT / "eod2012_zone_features_summary.csv", index=False)

    print(f"wrote: {OUT / 'eod2012_zone_features_eodzone.parquet'}")
    print(f"zones: {len(df):,}")
    print(f"feature_cols: {len(feature_cols):,}")
    print(df[["Zona", "Comuna", *feature_cols[:8]]].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
