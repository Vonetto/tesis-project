"""
Compare Nested Logit Extended v2 outputs across frameworks (Biogeme vs Larch).

Reads CSV outputs produced by:
- Biogeme: 03_models/biogeme-logit/model_outputs_nl_extended/
- Larch  : 03_models/larch_logit/model_outputs_nl_larch/

Goal: make cross-framework comparisons reproducible and explicit about
nest parameterization differences (Biogeme often uses μ>=1, Larch often uses
dissimilarity λ in (0,1]).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class RunKey:
    partition: str  # e.g. "2025-W17"
    spec: str  # "generic" | "specific"
    mode: str  # "noModeDummies" | "modeDummies"
    sample: str  # e.g. "sample20pct"


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parents]:
        if (p / "config").is_dir() and (p / "lib").is_dir():
            return p
    raise RuntimeError("Could not locate project root (expected 'config' and 'lib' dirs).")


def _biogeme_folder_name(key: RunKey) -> str:
    week = int(key.partition.split("-W")[1])
    if key.spec == "specific":
        return f"W{week:02d}-nested-ext-v2-specific-{key.mode}-{key.sample}"
    return f"W{week:02d}-nested-ext-v2-{key.mode}-{key.sample}"


def _larch_folder_name(key: RunKey) -> str:
    return f"{key.partition}-nested-ext-v2-{key.spec}-{key.mode}-{key.sample}"


def _read_first_csv(folder: Path, glob_pat: str) -> Path:
    files = sorted(folder.glob(glob_pat))
    if not files:
        raise FileNotFoundError(f"No CSV matching {glob_pat} in {folder}")
    return files[0]


def _clean_biogeme_param(name: str, key: RunKey) -> str:
    suffix = (
        f"_ext_v2_specific_{key.mode}_{key.partition}"
        if key.spec == "specific"
        else f"_ext_v2_{key.mode}_{key.partition}"
    )
    if name.endswith(suffix):
        return name[: -len(suffix)]
    # fallback: remove partition tag
    return re.sub(rf"_{re.escape(key.partition)}$", "", name)


def _clean_larch_param(name: str, key: RunKey) -> str:
    return re.sub(rf"_{re.escape(key.partition)}$", "", name)


def _extract_mu_from_params(df_params: pd.DataFrame, name_col: str = "Param") -> float | None:
    if name_col not in df_params.columns:
        return None
    candidates = df_params[df_params[name_col].astype(str).str.fullmatch(r"MU_QR", na=False)]
    if len(candidates) == 1:
        v = candidates.iloc[0].get("Value")
        try:
            return float(v)
        except Exception:
            return None
    # fallback: try startswith
    candidates = df_params[df_params[name_col].astype(str).str.startswith("MU_QR", na=False)]
    if len(candidates) >= 1:
        v = candidates.iloc[0].get("Value")
        try:
            return float(v)
        except Exception:
            return None
    return None


def _filter_params_for_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only behavioral coefficients for the params comparison table.

    The nest parameter `MU_QR` is intentionally excluded because:
    - Biogeme typically reports μ (>=1),
    - Larch typically reports dissimilarity λ in (0,1] but may still name it MU_QR,
    so comparing the raw `MU_QR` values is misleading. We compare the nest parameter in a
    normalized way in the dedicated `nest` section (μ ↔ λ).
    """
    if df is None or len(df) == 0 or "Param" not in df.columns:
        return df
    return df[df["Param"].astype(str) != "MU_QR"].copy()


def _coerce_numeric_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Coerce common numeric columns that sometimes arrive as strings (e.g. "nan", "inf", "BIG").

    We keep non-coercible entries as NaN so comparisons don't crash.
    """
    if df is None or len(df) == 0:
        return df

    def _fix_token(x):
        if not isinstance(x, str):
            return x
        # Some CSVs (notably from larch) may contain non‑breaking spaces around numbers.
        x_clean = x.replace("\xa0", " ").strip()
        t = x_clean.upper()
        if t in {"BIG", "+BIG"}:
            return float("inf")
        if t == "-BIG":
            return float("-inf")
        if t in {"NA", "N/A", "NAN", "NONE", ""}:
            return float("nan")
        return x_clean

    for c in cols:
        if c in df.columns:
            df[c] = df[c].map(_fix_token)
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_biogeme(key: RunKey) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    root = _project_root()
    base = root / "03_models" / "biogeme-logit" / "model_outputs_nl_extended"
    folder = base / _biogeme_folder_name(key)
    if not folder.is_dir():
        raise FileNotFoundError(f"Biogeme folder not found: {folder}")

    params_path = _read_first_csv(folder, "params_*.csv")
    stats_path = _read_first_csv(folder, "stats_*.csv")

    df_params_raw = pd.read_csv(params_path)
    if "Name" not in df_params_raw.columns:
        df_params_raw = pd.read_csv(params_path, index_col=0).reset_index().rename(columns={"index": "Name"})
    df_params = df_params_raw.copy()
    df_params["Param"] = df_params["Name"].astype(str).map(lambda s: _clean_biogeme_param(s, key))
    df_params = _coerce_numeric_cols(df_params, ["Value", "Robust std err.", "Robust t-stat."])

    df_stats = pd.read_csv(stats_path)
    df_stats = _coerce_numeric_cols(
        df_stats,
        [
            "Number of estimated parameters",
            "Sample size",
            "Excluded observations",
            "Init log likelihood",
            "Final log likelihood",
            "Likelihood ratio test for the init. model",
            "Rho-square for the init. model",
            "Rho-square-bar for the init. model",
            "Akaike Information Criterion",
            "Bayesian Information Criterion",
            "Final gradient norm",
            "Wall-clock seconds",
        ],
    )

    mu_biogeme = _extract_mu_from_params(df_params, name_col="Param")
    diag = {
        "folder": folder.name,
        "params_path": str(params_path),
        "stats_path": str(stats_path),
        "mu": mu_biogeme,  # Biogeme μ>=1 (common)
        "lambda": (1.0 / mu_biogeme) if (mu_biogeme is not None and mu_biogeme != 0) else None,
    }
    return df_params, df_stats, diag


def load_larch(key: RunKey) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    root = _project_root()
    base = root / "03_models" / "larch_logit" / "model_outputs_nl_larch"
    folder = base / _larch_folder_name(key)
    if not folder.is_dir():
        raise FileNotFoundError(f"Larch folder not found: {folder}")

    params_path = folder / f"params_nl_ext_v2_{key.spec}_{key.partition}.csv"
    stats_path = folder / f"stats_nl_ext_v2_{key.spec}_{key.partition}.csv"
    if not params_path.exists() or not stats_path.exists():
        raise FileNotFoundError(f"Missing Larch CSVs in {folder}")

    df_params_raw = pd.read_csv(params_path)
    df_params = df_params_raw.copy()
    df_params["Param"] = df_params["Name"].astype(str).map(lambda s: _clean_larch_param(s, key))
    df_params = _coerce_numeric_cols(df_params, ["Value", "Robust std err.", "Robust t-stat."])

    df_stats = pd.read_csv(stats_path)
    df_stats = _coerce_numeric_cols(
        df_stats,
        [
            "Number of estimated parameters",
            "Sample size",
            "Excluded observations",
            "Init log likelihood",
            "Final log likelihood",
            "Likelihood ratio test for the init. model",
            "Rho-square for the init. model",
            "Rho-square-bar for the init. model",
            "Akaike Information Criterion",
            "Bayesian Information Criterion",
            "Final gradient norm",
            "Wall-clock seconds",
        ],
    )

    mu_larch = _extract_mu_from_params(df_params, name_col="Param")
    diag = {
        "folder": folder.name,
        "params_path": str(params_path),
        "stats_path": str(stats_path),
        # Larch often reports dissimilarity λ in (0,1]; we treat MU_QR as λ if <= 1.
        "lambda": mu_larch if (mu_larch is not None and mu_larch <= 1.0) else None,
        "mu": (1.0 / mu_larch) if (mu_larch is not None and mu_larch != 0 and mu_larch <= 1.0) else None,
        "raw_mu_qr": mu_larch,
    }
    return df_params, df_stats, diag


def compare(key: RunKey) -> dict:
    bio_params, bio_stats, bio_diag = load_biogeme(key)
    larch_params, larch_stats, larch_diag = load_larch(key)

    # Stats (single row expected)
    def _stat_row(df: pd.DataFrame) -> dict:
        if len(df) == 0:
            return {}
        return df.iloc[0].to_dict()

    s_b = _stat_row(bio_stats)
    s_l = _stat_row(larch_stats)

    stats_comp = {
        "Partition": key.partition,
        "Spec": key.spec,
        "ModeDummies": key.mode,
        "Sample": key.sample,
        "LL_Final_Biogeme": s_b.get("Final log likelihood"),
        "LL_Final_Larch": s_l.get("Final log likelihood"),
        "AIC_Biogeme": s_b.get("Akaike Information Criterion"),
        "AIC_Larch": s_l.get("Akaike Information Criterion"),
        "BIC_Biogeme": s_b.get("Bayesian Information Criterion"),
        "BIC_Larch": s_l.get("Bayesian Information Criterion"),
        "K_Biogeme": s_b.get("Number of estimated parameters"),
        "K_Larch": s_l.get("Number of estimated parameters"),
        "RhoBar_Biogeme": s_b.get("Rho-square-bar for the init. model"),
        "RhoBar_Larch": s_l.get("Rho-square-bar for the init. model"),
        "GradNorm_Larch": s_l.get("Final gradient norm"),
        "WallClock_s_Biogeme": s_b.get("Wall-clock seconds"),
        "WallClock_s_Larch": s_l.get("Wall-clock seconds"),
    }

    # Params merge
    keep_cols_b = [c for c in ["Param", "Value", "Robust std err.", "Robust t-stat."] if c in bio_params.columns]
    keep_cols_l = [c for c in ["Param", "Value", "Robust std err.", "Robust t-stat."] if c in larch_params.columns]

    b = bio_params[keep_cols_b].rename(
        columns={
            "Value": "Value_Biogeme",
            "Robust std err.": "RobustSE_Biogeme",
            "Robust t-stat.": "RobustT_Biogeme",
        }
    )
    l = larch_params[keep_cols_l].rename(
        columns={
            "Value": "Value_Larch",
            "Robust std err.": "RobustSE_Larch",
            "Robust t-stat.": "RobustT_Larch",
        }
    )

    merged = b.merge(l, on="Param", how="outer")
    merged = _coerce_numeric_cols(merged, ["Value_Biogeme", "Value_Larch", "RobustSE_Biogeme", "RobustT_Biogeme", "RobustSE_Larch", "RobustT_Larch"])
    merged["Delta(Larch-Biogeme)"] = merged["Value_Larch"] - merged["Value_Biogeme"]
    merged = merged.sort_values("Param").reset_index(drop=True)
    merged = _filter_params_for_table(merged)

    # Explicit nest parameter transformation view
    mu_b = bio_diag.get("mu")
    lam_b = bio_diag.get("lambda")
    lam_l = larch_diag.get("lambda")
    mu_l = larch_diag.get("mu")
    nest_comp = {
        "mu_biogeme": mu_b,
        "lambda_from_biogeme": lam_b,
        "raw_MU_QR_larch": larch_diag.get("raw_mu_qr"),
        "lambda_larch_assumed": lam_l,
        "mu_from_larch": mu_l,
        "delta_lambda(larch - 1/mu_biogeme)": (lam_l - lam_b) if (lam_l is not None and lam_b is not None) else None,
        "delta_mu((1/larch) - biogeme)": (mu_l - mu_b) if (mu_l is not None and mu_b is not None) else None,
    }

    return {
        "key": key.__dict__,
        "biogeme": bio_diag,
        "larch": larch_diag,
        "stats": stats_comp,
        "nest": nest_comp,
        "params": merged,
    }


def compare_two(key_biogeme: RunKey, key_larch: RunKey) -> dict:
    """
    Compare outputs where Biogeme and Larch live under different sample folder names.

    This is useful when Larch results come from a benchmark aggregator folder
    (e.g. `...-benchbest`) but Biogeme uses the canonical sample label.
    """
    bio_params, bio_stats, bio_diag = load_biogeme(key_biogeme)
    larch_params, larch_stats, larch_diag = load_larch(key_larch)

    def _stat_row(df: pd.DataFrame) -> dict:
        if len(df) == 0:
            return {}
        return df.iloc[0].to_dict()

    s_b = _stat_row(bio_stats)
    s_l = _stat_row(larch_stats)

    stats_comp = {
        "Partition": key_biogeme.partition,
        "Spec": key_biogeme.spec,
        "ModeDummies": key_biogeme.mode,
        "Biogeme_Sample": key_biogeme.sample,
        "Larch_Sample": key_larch.sample,
        "LL_Final_Biogeme": s_b.get("Final log likelihood"),
        "LL_Final_Larch": s_l.get("Final log likelihood"),
        "AIC_Biogeme": s_b.get("Akaike Information Criterion"),
        "AIC_Larch": s_l.get("Akaike Information Criterion"),
        "BIC_Biogeme": s_b.get("Bayesian Information Criterion"),
        "BIC_Larch": s_l.get("Bayesian Information Criterion"),
        "K_Biogeme": s_b.get("Number of estimated parameters"),
        "K_Larch": s_l.get("Number of estimated parameters"),
        "RhoBar_Biogeme": s_b.get("Rho-square-bar for the init. model"),
        "RhoBar_Larch": s_l.get("Rho-square-bar for the init. model"),
        "GradNorm_Larch": s_l.get("Final gradient norm"),
        "WallClock_s_Biogeme": s_b.get("Wall-clock seconds"),
        "WallClock_s_Larch": s_l.get("Wall-clock seconds"),
    }

    keep_cols_b = [c for c in ["Param", "Value", "Robust std err.", "Robust t-stat."] if c in bio_params.columns]
    keep_cols_l = [c for c in ["Param", "Value", "Robust std err.", "Robust t-stat."] if c in larch_params.columns]

    b = bio_params[keep_cols_b].rename(
        columns={
            "Value": "Value_Biogeme",
            "Robust std err.": "RobustSE_Biogeme",
            "Robust t-stat.": "RobustT_Biogeme",
        }
    )
    l = larch_params[keep_cols_l].rename(
        columns={
            "Value": "Value_Larch",
            "Robust std err.": "RobustSE_Larch",
            "Robust t-stat.": "RobustT_Larch",
        }
    )

    merged = b.merge(l, on="Param", how="outer")
    merged = _coerce_numeric_cols(
        merged,
        ["Value_Biogeme", "Value_Larch", "RobustSE_Biogeme", "RobustT_Biogeme", "RobustSE_Larch", "RobustT_Larch"],
    )
    merged["Delta(Larch-Biogeme)"] = merged["Value_Larch"] - merged["Value_Biogeme"]
    merged = merged.sort_values("Param").reset_index(drop=True)
    merged = _filter_params_for_table(merged)

    mu_b = bio_diag.get("mu")
    lam_b = bio_diag.get("lambda")
    lam_l = larch_diag.get("lambda")
    mu_l = larch_diag.get("mu")
    nest_comp = {
        "mu_biogeme": mu_b,
        "lambda_from_biogeme": lam_b,
        "raw_MU_QR_larch": larch_diag.get("raw_mu_qr"),
        "lambda_larch_assumed": lam_l,
        "mu_from_larch": mu_l,
        "delta_lambda(larch - 1/mu_biogeme)": (lam_l - lam_b) if (lam_l is not None and lam_b is not None) else None,
        "delta_mu((1/larch) - biogeme)": (mu_l - mu_b) if (mu_l is not None and mu_b is not None) else None,
    }

    return {
        "key_biogeme": key_biogeme.__dict__,
        "key_larch": key_larch.__dict__,
        "biogeme": bio_diag,
        "larch": larch_diag,
        "stats": stats_comp,
        "nest": nest_comp,
        "params": merged,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--partition", default="2025-W17")
    ap.add_argument("--spec", choices=["generic", "specific"], default="specific")
    ap.add_argument("--mode", choices=["noModeDummies", "modeDummies"], default="noModeDummies")
    ap.add_argument("--sample", default="sample20pct")
    ap.add_argument("--biogeme-sample", default="", help="Override only the Biogeme sample folder name.")
    ap.add_argument("--larch-sample", default="", help="Override only the Larch sample folder name.")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    sample_b = args.biogeme_sample or args.sample
    sample_l = args.larch_sample or args.sample

    key_b = RunKey(
        partition=args.partition,
        spec=args.spec,
        mode=args.mode,
        sample=sample_b,
    )
    key_l = RunKey(
        partition=args.partition,
        spec=args.spec,
        mode=args.mode,
        sample=sample_l,
    )

    out = compare_two(key_b, key_l) if (sample_b != sample_l) else compare(key_b)

    print("\n=== Nested Ext v2 — Cross-framework Comparison (Biogeme vs Larch) ===")
    print(json.dumps(out["stats"], indent=2, default=str))
    print("\n--- Nest parameter (normalize μ/λ) ---")
    print(json.dumps(out["nest"], indent=2, default=str))
    print("\n--- Params (head) ---")
    with pd.option_context("display.width", 140, "display.max_rows", 40, "display.max_columns", 50):
        print(out["params"].head(40).to_string(index=False))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Save merged params and stats for reproducibility
        pd.DataFrame([out["stats"]]).to_csv(out_path.with_suffix(".stats.csv"), index=False)
        pd.DataFrame([out["nest"]]).to_csv(out_path.with_suffix(".nest.csv"), index=False)
        out["params"].to_csv(out_path.with_suffix(".params.csv"), index=False)
        meta = {
            "key": out.get("key", None),
            "key_biogeme": out.get("key_biogeme", None),
            "key_larch": out.get("key_larch", None),
            "biogeme": out["biogeme"],
            "larch": out["larch"],
        }
        out_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        print(f"\n✅ Saved: {out_path.with_suffix('.stats.csv')}")


if __name__ == "__main__":
    main()
