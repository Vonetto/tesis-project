#!/usr/bin/env python3
"""
Compare model outputs between larch and biogeme.

Scans CSV outputs under:
  - 03_models/larch_logit/model_outputs_larch
  - 03_models/larch_logit/model_outputs_nl_larch
  - 03_models/biogeme-logit/model_outputs
  - 03_models/biogeme-logit/model_outputs_nl_base
  - 03_models/biogeme-logit/model_outputs_nl_extended

Creates two CSVs:
  - comparison_params.csv : parameter-level comparison
  - comparison_stats.csv  : run-level statistics comparison

Nested Logit note:
  Biogeme reports nest scale μ_m (>=1) while larch reports logsum/dissimilarity λ_m (<=1).
  For nest parameters (names starting with 'MU_'), we compare:
      larch_value  vs  lambda_from_biogeme = 1 / biogeme_mu

Variant note:
  Folder names may include a 'v2' token (e.g., W17-baseline-v2, W17-extended-v2-full,
  2025-W17-nested-ext-v2-generic-full). Runs are matched only within the same variant.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


PARTITION_RE = re.compile(r"(?P<year>\d{4})-W(?P<week>\d{2})")


@dataclass(frozen=True)
class RunKey:
    partition: str
    model: str  # binary_baseline, binary_extended, nested_base, nested_ext
    spec: str   # generic/specific for nested_base, "" otherwise
    sample: str  # full, sample20pct, sample50pct, etc.
    variant: str  # v1, v2


@dataclass
class RunMeta:
    package: str  # larch or biogeme
    key: RunKey
    params_path: Path
    stats_path: Optional[Path]


def parse_partition(text: str) -> Optional[str]:
    m = PARTITION_RE.search(text)
    if not m:
        return None
    return f"{m.group('year')}-W{m.group('week')}"


def canonical_sample(raw: Optional[str]) -> str:
    if not raw:
        return "full"
    raw = raw.lower()
    if raw in {"full", "all"}:
        return "full"
    # legacy larch naming: "20pct" / "50pct"
    m_pct = re.fullmatch(r"(\d+)pct", raw)
    if m_pct:
        return f"sample{m_pct.group(1)}pct"
    # biogeme legacy numeric fraction like "0.2"
    m_frac = re.fullmatch(r"0\.(\d+)", raw)
    if m_frac:
        return f"sample{int(float(raw) * 100)}pct"
    if raw.startswith("sample"):
        return raw
    return raw


def guess_stats_path(params_path: Path) -> Optional[Path]:
    if params_path.name.startswith("params"):
        stats_name = params_path.name.replace("params", "stats", 1)
        candidate = params_path.with_name(stats_name)
        if candidate.exists():
            return candidate
    # fallback: any stats*.csv in same dir with same partition label
    part = parse_partition(params_path.name) or parse_partition(str(params_path.parent))
    if part:
        for p in params_path.parent.glob("stats*.csv"):
            if part in p.name:
                return p
    return None


def scan_larch_binary(root: Path) -> List[RunMeta]:
    runs: List[RunMeta] = []
    for params_path in root.glob("**/params*.csv"):
        folder = params_path.parent.name
        parts = folder.split("-")
        if len(parts) < 2 or not parts[0].startswith("W"):
            continue
        try:
            int(parts[0][1:])
        except Exception:
            continue
        kind = parts[1]
        if kind not in {"baseline", "extended"}:
            continue
        idx = 2
        variant = "v1"
        if idx < len(parts) and parts[idx] in {"v1", "v2"}:
            variant = parts[idx]
            idx += 1
        sample_raw = "-".join(parts[idx:]) if idx < len(parts) else None
        sample = canonical_sample(sample_raw)
        partition = parse_partition(params_path.name)
        if not partition:
            continue
        model = f"binary_{kind}"
        key = RunKey(partition=partition, model=model, spec="", sample=sample, variant=variant)
        runs.append(RunMeta("larch", key, params_path, guess_stats_path(params_path)))
    return runs


def scan_larch_nested(root: Path) -> List[RunMeta]:
    runs: List[RunMeta] = []
    for params_path in root.glob("**/params*.csv"):
        folder = params_path.parent.name
        parts = folder.split("-")
        if len(parts) < 5 or parts[2] != "nested":
            continue
        partition = f"{parts[0]}-{parts[1]}"
        nested_kind = parts[3]
        idx = 4
        variant = "v1"
        if idx < len(parts) and parts[idx] in {"v1", "v2"}:
            variant = parts[idx]
            idx += 1
        spec = parts[idx] if idx < len(parts) and parts[idx] in {"generic", "specific"} else ""
        if spec:
            idx += 1
        sample_raw = parts[idx] if idx < len(parts) else None
        sample = canonical_sample(sample_raw)
        model = "nested_base" if nested_kind == "base" else "nested_ext"
        key = RunKey(partition=partition, model=model, spec=spec, sample=sample, variant=variant)
        runs.append(RunMeta("larch", key, params_path, guess_stats_path(params_path)))
    return runs


def scan_biogeme_binary(root: Path) -> List[RunMeta]:
    runs: List[RunMeta] = []
    for params_path in root.glob("**/params*.csv"):
        folder = params_path.parent.name
        parts = folder.split("-")
        if len(parts) < 2 or not parts[0].startswith("W"):
            continue
        try:
            int(parts[0][1:])
        except Exception:
            continue
        kind = parts[1]
        if kind not in {"baseline", "extended"}:
            continue
        idx = 2
        variant = "v1"
        if idx < len(parts) and parts[idx] in {"v1", "v2"}:
            variant = parts[idx]
            idx += 1
        sample_raw = "-".join(parts[idx:]) if idx < len(parts) else None
        sample = canonical_sample(sample_raw)
        partition = parse_partition(params_path.name)
        if not partition:
            continue
        model = f"binary_{kind}"
        key = RunKey(partition=partition, model=model, spec="", sample=sample, variant=variant)
        runs.append(RunMeta("biogeme", key, params_path, guess_stats_path(params_path)))
    return runs


def scan_biogeme_nested(root: Path, kind_default: str) -> List[RunMeta]:
    runs: List[RunMeta] = []
    for params_path in root.glob("**/params*.csv"):
        folder = params_path.parent.name
        parts = folder.split("-")
        if len(parts) < 3 or parts[1] != "nested":
            continue
        nested_kind = parts[2]
        idx = 3
        variant = "v1"
        if idx < len(parts) and parts[idx] in {"v1", "v2"}:
            variant = parts[idx]
            idx += 1
        spec = ""
        if idx < len(parts) and parts[idx] in {"generic", "specific"}:
            spec = parts[idx]
            idx += 1
        sample_raw: Optional[str] = parts[idx] if idx < len(parts) else None
        sample = canonical_sample(sample_raw)
        partition = parse_partition(params_path.name)
        if not partition:
            continue
        model = kind_default
        key = RunKey(partition=partition, model=model, spec=spec, sample=sample, variant=variant)
        runs.append(RunMeta("biogeme", key, params_path, guess_stats_path(params_path)))
    return runs


def read_params(path: Path, spec_to_strip: str = "") -> Dict[str, float]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        params: Dict[str, float] = {}
        for row in reader:
            name = row.get("Name") or row.get("name") or row.get("")
            if not name:
                continue
            if spec_to_strip:
                name = name.replace(f"_{spec_to_strip}_", "_")
            val_str = row.get("Value") or row.get("value")
            try:
                val = float(val_str) if val_str not in (None, "") else float("nan")
            except Exception:
                continue
            params[name] = val
    return params


def read_stats(path: Path) -> Dict[str, str]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return {}


def compare_runs(
    larch_runs: Dict[RunKey, RunMeta],
    biogeme_runs: Dict[RunKey, RunMeta],
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]], List[Tuple[RunKey, str]]]:
    param_rows: List[Dict[str, object]] = []
    stats_rows: List[Dict[str, object]] = []
    missing: List[Tuple[RunKey, str]] = []

    all_keys = sorted(
        set(larch_runs) | set(biogeme_runs),
        key=lambda k: (k.partition, k.model, k.variant, k.spec, k.sample),
    )
    for key in all_keys:
        l_run = larch_runs.get(key)
        b_run = biogeme_runs.get(key)
        if not l_run or not b_run:
            missing.append((key, "larch" if not l_run else "biogeme"))
            continue

        l_params = read_params(l_run.params_path)
        b_params = read_params(b_run.params_path, spec_to_strip=key.spec)

        all_param_names = sorted(set(l_params) | set(b_params))
        for pname in all_param_names:
            l_val = l_params.get(pname)
            b_val = b_params.get(pname)
            row: Dict[str, object] = {
                "partition": key.partition,
                "model": key.model,
                "variant": key.variant,
                "spec": key.spec,
                "sample": key.sample,
                "parameter": pname,
                "larch_value": l_val,
                "biogeme_value": b_val,
                "biogeme_lambda": None,
                "comparison_value": None,
                "diff_larch_minus_biogeme": None,
            }

            if pname.upper().startswith("MU_") and b_val is not None and b_val != 0:
                lam = 1.0 / b_val
                row["biogeme_lambda"] = lam
                row["comparison_value"] = lam
                if l_val is not None:
                    row["diff_larch_minus_biogeme"] = l_val - lam
            else:
                row["comparison_value"] = b_val
                if l_val is not None and b_val is not None:
                    row["diff_larch_minus_biogeme"] = l_val - b_val

            param_rows.append(row)

        if l_run.stats_path and b_run.stats_path:
            l_stats = read_stats(l_run.stats_path)
            b_stats = read_stats(b_run.stats_path)
            # Try to compute numeric diffs when possible
            def _to_float(x: Optional[str]) -> Optional[float]:
                if x in (None, ""):
                    return None
                try:
                    return float(x)
                except Exception:
                    return None

            l_final_ll = _to_float(l_stats.get("Final log likelihood"))
            b_final_ll = _to_float(b_stats.get("Final log likelihood"))
            stats_rows.append(
                {
                    "partition": key.partition,
                    "model": key.model,
                    "variant": key.variant,
                    "spec": key.spec,
                    "sample": key.sample,
                    "larch_sample_size": l_stats.get("Sample size"),
                    "biogeme_sample_size": b_stats.get("Sample size"),
                    "larch_init_ll": l_stats.get("Init log likelihood"),
                    "biogeme_init_ll": b_stats.get("Init log likelihood"),
                    "larch_final_ll": l_stats.get("Final log likelihood"),
                    "biogeme_final_ll": b_stats.get("Final log likelihood"),
                    "diff_final_ll_larch_minus_biogeme": (l_final_ll - b_final_ll) if (l_final_ll is not None and b_final_ll is not None) else None,
                    "larch_rho2": l_stats.get("Rho-square for the init. model"),
                    "biogeme_rho2": b_stats.get("Rho-square for the init. model"),
                }
            )

    return param_rows, stats_rows, missing


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare larch vs biogeme model outputs.")
    parser.add_argument("--out-dir", default="03_models", help="Directory to write comparison CSVs.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    larch_runs = (
        scan_larch_binary(Path("03_models/larch_logit/model_outputs_larch"))
        + scan_larch_nested(Path("03_models/larch_logit/model_outputs_nl_larch"))
    )
    biogeme_runs = (
        scan_biogeme_binary(Path("03_models/biogeme-logit/model_outputs"))
        + scan_biogeme_nested(Path("03_models/biogeme-logit/model_outputs_nl_base"), "nested_base")
        + scan_biogeme_nested(Path("03_models/biogeme-logit/model_outputs_nl_extended"), "nested_ext")
    )

    larch_map = {r.key: r for r in larch_runs}
    biogeme_map = {r.key: r for r in biogeme_runs}

    param_rows, stats_rows, missing = compare_runs(larch_map, biogeme_map)

    write_csv(out_dir / "comparison_params.csv", param_rows)
    write_csv(out_dir / "comparison_stats.csv", stats_rows)

    print(f"✅ Wrote {len(param_rows):,} parameter comparisons to {out_dir / 'comparison_params.csv'}")
    print(f"✅ Wrote {len(stats_rows):,} run statistics comparisons to {out_dir / 'comparison_stats.csv'}")
    if missing:
        print("\n⚠️ Runs without match:")
        for key, side in missing:
            print(f"  - missing {side}: {key}")


if __name__ == "__main__":
    main()
