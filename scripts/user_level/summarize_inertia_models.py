"""Consolida los coeficientes de inercia de los 6 modelos en una tabla única.

Lee los params_*.csv de Biogeme de cada especificación (individuales y
conjuntas) y arma un CSV largo con: modelo, alternativa, índice, ventana,
valor, t-stat robusto. Base para la sección de tesis y para notes.md.

Uso (Mac): python scripts/user_level/summarize_inertia_models.py
Output: 03_models/user_level/mnl/outputs/SUMMARY_inertia_coefs.csv
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "03_models" / "user_level" / "mnl" / "outputs"

# label_suffix -> (nombre legible del modelo, sample usado)
MODELS = {
    "mnl_user_interannual_ml_clean_alta_n3_s500_inertia-inter_W15_W17":
        ("inter (individual)", "0.5"),
    "mnl_user_interannual_ml_clean_alta_n3_s500_inertia-intra2024_W15_W17":
        ("intra2024 (individual)", "0.5"),
    "mnl_user_interannual_ml_clean_alta_n3_s500_inertia-intra2025_W15_W17":
        ("intra2025 (individual)", "0.5"),
    "mnl_user_interannual_ml_clean_alta_n3_inertia-inter+intra2025":
        ("inter+intra2025 (conjunto)", "full~180K"),
    "mnl_user_interannual_ml_clean_alta_n3_inertia-inter+intra2024":
        ("inter+intra2024 (conjunto)", "full~182K"),
    "mnl_user_interannual_ml_clean_alta_n3_inertia-inter+intra2024+intra2025":
        ("inter+intra2024+intra2025 (3 ventanas)", "full~128K"),
}

# fallback: si la individual a s500 no existe, probar s300
FALLBACKS = {
    "mnl_user_interannual_ml_clean_alta_n3_s500_inertia-inter_W15_W17":
        "mnl_user_interannual_ml_clean_alta_n3_s300_inertia-inter_W15_W17",
}


def parse_name(name: str):
    """B_QR_RED_DSI_DAY_SEQUENCE_INTER_Z -> (QR_RED, DSI, INTER)."""
    m = re.match(r"B_(QR_RED|QR_OTHER)_(.+)", name)
    if not m:
        return None
    alt, rest = m.group(1), m.group(2)
    idx = None
    for key in ("DSI_DAY_SEQUENCE", "TSI_TIME_DISTRIBUTION",
                "LSI_ORIGIN_STOP", "LSI_ORIGIN_ZONE"):
        if rest.startswith(key):
            idx = key
            rest = rest[len(key):]
            break
    if idx is None:
        return None
    win = "single"
    wm = re.search(r"(INTER|INTRA2024|INTRA2025)", rest)
    if wm:
        win = wm.group(1)
    return alt, idx, win


def main():
    rows = []
    for lab, (pretty, sample) in MODELS.items():
        f = OUT / f"params_{lab}.csv"
        if not f.exists() and lab in FALLBACKS:
            f = OUT / f"params_{FALLBACKS[lab]}.csv"
        if not f.exists():
            print(f"(falta {f.name}) -> modelo '{pretty}' omitido")
            continue
        df = pd.read_csv(f)
        tcol = next((c for c in df.columns if "Rob" in c and "t-test" in c.lower()), None) \
            or next((c for c in df.columns if "t-test" in c.lower()), None)
        for _, r in df.iterrows():
            parsed = parse_name(str(r["Name"]))
            if not parsed:
                continue
            alt, idx, win = parsed
            rows.append({
                "modelo": pretty,
                "sample": sample,
                "alternativa": alt,
                "indice": idx,
                "ventana": win,
                "valor": round(float(r["Value"]), 4),
                "t_rob": round(float(r[tcol]), 2) if tcol else None,
                "sig": "***" if tcol and abs(float(r[tcol])) > 2.58 else
                       ("**" if tcol and abs(float(r[tcol])) > 1.96 else
                        ("*" if tcol and abs(float(r[tcol])) > 1.64 else "")),
            })
    out = pd.DataFrame(rows)
    dest = OUT / "SUMMARY_inertia_coefs.csv"
    out.to_csv(dest, index=False)
    print(f"\n✅ {len(out)} coeficientes -> {dest}\n")
    # vista pivote para inspección rápida: índice x ventana, por modelo y alt
    for alt in ["QR_RED", "QR_OTHER"]:
        print(f"\n===== {alt} =====")
        sub = out[out["alternativa"] == alt]
        piv = sub.pivot_table(index=["modelo"], columns=["indice", "ventana"],
                              values="valor", aggfunc="first")
        print(piv.to_string())


if __name__ == "__main__":
    main()
