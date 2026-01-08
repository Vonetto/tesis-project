# Task Plan — Logit Models v2 Alignment

Project: tesis-project
Created: 2026-01-04
Last updated: 2026-01-07
Owner: Vicente + Codex

## Goal

- Align logit model notebooks (Biogeme/Larch/Statsmodels) to the corrected dataset `tmp/viajes_con_te_calculado_2025-W17.parquet` (v2) while preserving existing v1 outputs for comparison.

## Constraints / Guardrails

- Do not overwrite existing (v1) outputs; new outputs must go to `*-v2` folders.
- Keep the current feature set; only swap to corrected columns (`*_calculado`, `n_etapas_recon`) and remove walking time.
- Avoid double counting: initial wait = `te0_calculado`; transfer wait = `te1..te5_calculado` only.
- Statsmodels stays binary (baseline + extended v2); no nested.

## Inputs / Sources of truth

- Corrected parquet (current scope): `tmp/viajes_con_te_calculado_2025-W17.parquet`
- Model notebooks root: `03_models/`

## Milestones

- [x] 1) Create v2 output naming convention (`*-v2`) across frameworks
- [x] 2) Update Biogeme notebooks (baseline, extended, nested) to v2
- [x] 3) Update Larch notebooks (baseline, extended, nested) to v2
- [x] 4) Update Statsmodels notebooks (baseline, extended) to v2
- [x] 5) Add/extend comparison to show v1 vs v2 changes (params + stats + runtime)
- [x] 6) Run a small sanity run (sample) and record results
- [x] 7) Run nested v2 (Biogeme + Larch) and compare (2 variantes: con/sin dummies modales) + diagnóstico colinealidad
- [ ] 8) Validar equivalencia NL entre frameworks (parametrización mu/lambda, mismos datos/muestreo, chequeo MU=1, estabilidad y predicciones)
  - Nota: usar matched sample (`tmp/matched_samples/nested_ext_v2_<partition>_<sample>.parquet`) para eliminar diferencias por muestreo.
  - Script soporte: `tmp/validation/nested_ext_v2_validations.py` (`--run-all` para export+estimate+validate).
  - Estado (2026-01-07): matched sample eliminado como fuente de diferencia; persiste discrepancia en `MU_QR` (y `GradNorm_Larch` alto). Próximo: test `MU_QR=1` (reduce a MNL) + probar métodos de optimización en Larch.
  - Update (2026-01-07): benchmark Larch mostró que `trust-constr` + multi-start encuentra `LL` cercano a Biogeme y `grad` mucho menor → enfocar en “tuning” de Larch si queremos usarlo.

## Files to change (tracked)

- `03_models/biogeme-logit/01_binary_logit_qr_adoption.qmd`
- `03_models/biogeme-logit/02_binary_extended_logit_qr_adoption.qmd`
- `03_models/biogeme-logit/03_nested_logit.qmd`
- `03_models/larch_logit/01_binary_logit_qr_adoption_larch.qmd`
- `03_models/larch_logit/02_binary_extended_logit_qr_adoption_larch.qmd`
- `03_models/larch_logit/03_nested_logit_larch.qmd`
- `03_models/statsmodels_logit/01_binary_logit_qr_adoption_stastsmodel.qmd`
- `03_models/statsmodels_logit/02_binary_extended_logit_qr_adoption_statsmodels.qmd`
- `tmp/plans/tesis-project/models-v2/task_plan.md`
- `tmp/plans/tesis-project/models-v2/notes.md`
- `tmp/validation/nested_ext_v2_validations.py`

## Current Status

- Now: validar Nested Logit v2 cross-framework (Biogeme vs Larch) con **matched sample** y checks de convergencia/parametrización
- Blockers: none
- Next: document interpretation deltas (v1→v2) and decide reporting tables/figures for thesis

## Smoke Run Checklist (v2)

Goal: generate at least one matched pair of outputs (Biogeme + Larch) for baseline + extended, plus Statsmodels for reference.

- Baseline (binary)
  - Biogeme: `03_models/biogeme-logit/01_binary_logit_qr_adoption.qmd` → run the sequential estimation cell (`#|label: sequential-estimation`) with a small `SAMPLE_FRACTION` (e.g. 0.05).
  - Larch: `03_models/larch_logit/01_binary_logit_qr_adoption_larch.qmd` → run `#|label: sequential-estimation-larch` with same sample fraction.
  - Statsmodels: `03_models/statsmodels_logit/01_binary_logit_qr_adoption_stastsmodel.qmd` → run `#|label: sequential-estimation-statsmodels` with same sample fraction.

- Extended (binary)
  - Biogeme: `03_models/biogeme-logit/02_binary_extended_logit_qr_adoption.qmd` → run the v2 sequential estimation cell (the one that writes to `W{week}-extended-v2-*`), start with `sample20pct` or smaller.
  - Larch: `03_models/larch_logit/02_binary_extended_logit_qr_adoption_larch.qmd` → run the v2 estimation cell (writes `W{week}-extended-v2-*`) with matching sample label.
  - Statsmodels: `03_models/statsmodels_logit/02_binary_extended_logit_qr_adoption_statsmodels.qmd` → run `#|label: sequential-estimation-extended-statsmodels` with matching sample label.

Progress (2026-01-04):
- Baseline v2 (full): Biogeme ✅, Larch ✅, Statsmodels ✅

Progress (2026-01-06):
- Extended v2 (sample20pct + sample50pct): Biogeme ✅, Larch ✅, Statsmodels ✅
- Cross-framework comparison (Extended v2): parameters + rho-bar consistent across all three tools ✅

- Nested (optional for smoke)
  - Biogeme: `03_models/biogeme-logit/03_nested_logit.qmd` → base: `#|label: sequential-estimation-nl-base`; extended v2: `#|label: sequential-estimation-nl-extended-v2`.
  - Biogeme (specific): `03_models/biogeme-logit/03_nested_logit.qmd` → `#|label: sequential-estimation-nl-extended-v2-specific` (corre ambos `modeDummies/noModeDummies`).
  - Larch: `03_models/larch_logit/03_nested_logit_larch.qmd` → `#|label: prepare-data-nested-ext-v2-larch` + `#|label: estimate-nested-ext-v2-both-mode-dummy-variants-larch`.
