# Zonal QR Growth Modeling

## Goal

Build a reproducible modeling workflow for zonal QR growth between 2024 and
2025, using the EDA outputs as inputs and keeping the task predictive-descriptive
rather than causal.

## Guardrails

- Model `Residencia` and `Origen de viaje` separately.
- Use `delta_relative_pp` as the primary outcome unless later evidence suggests
  otherwise.
- Keep `share_qr_2024`, support/volume and macrozone controls in the baseline.
- Treat `share_shift_qr_delta` as a volume complement, not the same question as
  relative growth.
- Do not interpret zonal variables as individual attributes.
- Prefer simple, interpretable models before predictive benchmarks.

## Current Status

- [x] Create modeling notebook skeleton:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- [x] Render notebook once as a sanity check:
  - `03_models/18_zonal_qr_growth_modeling.html`.
- [ ] Persist modeling panel/features from `02_eda/eda_qr_growth_zonal_2024_2025.qmd`.
  - [x] Export cell implemented in EDA (`block8b-export-model-ready-artifacts`).
  - [ ] User runs the export cell and reviews output summary.
  - [ ] Confirm artifacts exist under `03_models/artifacts/zonal_qr_growth_2024_2025/`.
- [ ] Implement baseline models:
  - M0 outcome mean;
  - M1 QR initial;
  - M2 QR initial + support/volume;
  - M3 QR initial + support/volume + macrozone.
- [ ] Add interpretable family models.
- [ ] Add regularized sensitivity models.
- [ ] Add predictive benchmark only after baselines are reviewed.
- [ ] Add diagnostics and robustness.
- [ ] Produce model handoff table for thesis/reporting.

## Immediate Next Step

Persist a model-ready feature matrix with one row per `zone_id` and
`geography_key`, then load it from
`03_models/artifacts/zonal_qr_growth_2024_2025/zonal_qr_growth_feature_matrix.parquet`.
