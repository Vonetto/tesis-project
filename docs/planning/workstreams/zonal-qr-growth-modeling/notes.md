# Zonal QR Growth Modeling Notes

## 2026-07-06 — Notebook skeleton created

- Created:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Rendered:
  - `03_models/18_zonal_qr_growth_modeling.html`.
- Purpose:
  - start the zonal modeling stage from the EDA findings without turning the EDA
    notebook into a modeling notebook;
  - define outcomes, weights, feature families, validation, baselines,
    interpretable models, regularization, benchmarks, diagnostics, robustness
    and final handoff structure.
- Key design decisions:
  - primary outcome: `delta_relative_pp`;
  - secondary outcomes: `delta_pp`, `share_shift_qr_delta`,
    `delta_logit_qr_share_smooth`;
  - model `residence` and `origin_trip` separately;
  - baseline controls must include QR initial, support/volume and macrozone;
  - predictive benchmarks come after interpretable baselines.
- Verification:
  - rendered with:
    `/usr/bin/env QUARTO_PYTHON=/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python quarto render 03_models/18_zonal_qr_growth_modeling.qmd --to html`;
  - all 15 cells executed successfully;
  - notebook currently renders even when the model panel parquet does not yet
    exist.
- Next action:
  - export or build the model-ready feature matrix from
    `02_eda/eda_qr_growth_zonal_2024_2025.qmd` into
    `03_models/artifacts/zonal_qr_growth_2024_2025/`.

## 2026-07-06 — Export cell added to EDA, not executed

- Updated:
  - `02_eda/eda_qr_growth_zonal_2024_2025.qmd`.
- Added final section:
  - `11.7 Export model-ready artifacts`;
  - code cell label: `block8b-export-model-ready-artifacts`.
- Intended outputs, once the user runs the cell:
  - `03_models/artifacts/zonal_qr_growth_2024_2025/zonal_qr_growth_model_panel.parquet`;
  - `03_models/artifacts/zonal_qr_growth_2024_2025/zonal_qr_growth_feature_matrix.parquet`;
  - `03_models/artifacts/zonal_qr_growth_2024_2025/zonal_qr_growth_feature_metadata.csv`;
  - `03_models/artifacts/zonal_qr_growth_2024_2025/zonal_qr_growth_export_summary.csv`.
- Important:
  - the cell was intentionally not executed or rendered by Codex;
  - user will run it from the IDE and share/review the output before modeling.
- Export design:
  - uses `block3_zone_contrib` as model panel base;
  - uses `block4_feature_values` to pivot candidate variables wide;
  - adds stable aliases expected by `03_models/18_zonal_qr_growth_modeling.qmd`;
  - preserves original source columns alongside aliases.

## 2026-07-07 — Modeling design cautions before baselines

- The exported panel loaded correctly in
  `03_models/18_zonal_qr_growth_modeling.qmd`:
  - residence: 627 zones with base support;
  - origin_trip: 793 zones with base support;
  - `macrozone_group` is currently the only categorical predictor.
- Support and volume variables should not enter linear models raw:
  - use `log1p(support_min)` and `log1p(n_2025)` or equivalent aliases;
  - scale numeric predictors inside the modeling pipeline.
- Keep a clear distinction between descriptive and predictive specifications:
  - `n_2025` is acceptable for descriptive decomposition of observed 2024--2025
    growth;
  - strict prediction of 2025 using prior information should avoid `n_2025`
    and prefer pre-period volume/support variables such as `n_2024` or
    historical support.
- Treat macrozone validation carefully:
  - `KFold` with `macrozone_group` is the main internal/descriptive baseline;
  - `GroupKFold` by macrozone is a territorial stress test, not a direct
    replacement for ordinary KFold;
  - when the held-out fold is an entire macrozone, fixed effects for
    `macrozone_group` do not transfer in the usual way. Prefer reporting
    `GroupKFold` without macrozone as the main transfer check, or show the
    macrozone version only as a sensitivity.
- If `GroupKFold` performs much worse, interpret it as evidence that part of
  the signal is territorial and does not extrapolate cleanly across macrozones,
  not automatically as model failure.

## 2026-07-07 — Baseline execution cells added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added:
  - `block0b-prepare-model-features`: creates `log1p` aliases for
    `support_min`, `n_2024` and `n_2025`;
  - `block5b-baseline-validation-plan`: defines the three baseline validation
    readings;
  - `block5c-baseline-modeling-helpers`: modular pipeline, CV, weighting and
    metric helpers;
  - `block5d-run-baseline-models`: executes M0--M3 for `residence` and
    `origin_trip`, then writes fold-level and summary CSVs.
- Design choices:
  - linear baseline specs now use `support_min_log` and `n_2025_log` instead
    of raw support/volume variables;
  - `GroupKFold` by macrozone drops `macrozone_group` as a predictor and is
    treated as a territorial stress test;
  - `support_min` and `n_2025` remain available as weighting variables.
- Verification:
  - did not render or execute the notebook, per user preference;
  - performed static Python parsing of 19 QMD code cells successfully.
- User run order after this edit:
  - rerun from `block0b-prepare-model-features` through
    `block5d-run-baseline-models`, because `MODEL_SPECS` now expects the log
    aliases.

## 2026-07-07 — Baseline model findings

- User executed baseline blocks successfully after exporting the feature matrix:
  - full feature matrix loaded with 1,596 rows and 82 columns;
  - base modeling samples: residence 627 zones, origin_trip 793 zones.
- Baseline findings:
  - the baseline has signal, but is not enough as final model;
  - with zones weighted equally, the best base model reaches only about
    `R2 = 0.113` for origin_trip and `R2 = 0.122` for residence;
  - adding macrozone is the main baseline improvement:
    - origin_trip: `M2 R2 = 0.014` to `M3 R2 = 0.113`;
    - residence: `M2 R2 = 0.027` to `M3 R2 = 0.122`;
  - weighting by support makes the signal much stronger, especially for
    origin_trip:
    - origin_trip `M3` weighted by support: `R2 = 0.352`;
    - residence `M3` weighted by support: `R2 = 0.160`;
  - `GroupKFold` by macrozone is weak/negative for both geographies, consistent
    with limited transfer across macrozones rather than simple model failure.
- Interpretation:
  - macrozone and operational weight matter materially;
  - origin_trip is more promising than residence under support weighting;
  - the next modeling step should test whether candidate families add
    information over the baseline, especially operational variables for
    origin_trip and socio-demographic/urban variables for residence.

## 2026-07-07 — Family model execution cells added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added:
  - `block6b-build-family-model-specs`: converts the family contract into
    executable model specs;
  - `block6c-run-family-models`: runs family models and reports incremental
    performance against `R1_base` or `O1_base`.
- Design choices:
  - the family `base` used for `R1_base`/`O1_base` is aligned with baseline
    `M3`: `qr_share_2024`, `support_min_log`, `n_2025_log`,
    `macrozone_group`;
  - `n_2024_log` and `logit_qr_share_2024_smooth` remain available for later
    sensitivity/predictive-strict variants but are not part of the default
    family baseline;
  - family model summaries include `delta_r2_vs_base`,
    `delta_rmse_pp_vs_base` and `delta_mae_pp_vs_base`;
  - the same validation plan as baseline is reused, with `macrozone_group`
    dropped under `GroupKFold`.
- Verification:
  - did not execute or render the notebook;
  - static Python parsing passed for 21 QMD code cells.
- Next action:
  - user should run `block6b-build-family-model-specs` and
    `block6c-run-family-models`, then review whether candidate families improve
    on base models.

## 2026-07-07 — Regularization cells added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added:
  - support for `RidgeCV`, `LassoCV` and `ElasticNetCV` in the estimator helper;
  - `block7b-run-regularized-family-models`, which runs regularized versions
    of the family models and compares them to `R1_base`/`O1_base`.
- Design choices:
  - `RidgeCV` is the primary regularization check because it handles
    collinearity without hard variable selection;
  - `LassoCV` and `ElasticNetCV` are exploratory sensitivity checks;
  - base models are not rerun as regularized specs; regularization is applied
    only to the expanded family models.
- Verification:
  - did not execute or render the notebook;
  - static Python parsing passed for 22 QMD code cells.
- Next action:
  - user should run `block7b-run-regularized-family-models` and compare
    regularized deltas against the unregularized family results.

## 2026-07-07 — Regularization delta reference fixed

- User ran the regularization block and the model metrics printed correctly, but
  `delta_r2_vs_base`, `delta_rmse_pp_vs_base` and `delta_mae_pp_vs_base`
  appeared as `NaN`.
- Cause:
  - `add_delta_vs_base()` used only the summary passed to it;
  - the regularized summary does not include `R1_base`/`O1_base` rows, so the
    base reference could not be found.
- Fix:
  - `add_delta_vs_base()` now accepts an optional `base_reference`;
  - regularized summaries use `family_summary` as the reference for
    `R1_base`/`O1_base`.
- Verification:
  - did not execute or render;
  - static Python parsing passed for 22 QMD code cells.

## 2026-07-07 — Regularization findings

- User reran `block7b-run-regularized-family-models` after fixing the delta
  reference. Deltas against `R1_base`/`O1_base` now print correctly.
- Main findings:
  - regularization does not materially change the family-model story;
  - for origin_trip, operation variables add only marginally under equal-zone
    KFold:
    - `O2` regularized: about `+0.008` to `+0.010` R2 vs base;
    - under support weighting, `O2` is below base by about `-0.017` to `-0.019`;
  - adding OSM/BIP in origin (`O3`) is generally worse than base;
  - for residence, socio-demographics are the clearest regularized signal:
    - `R2_base_socio__RidgeCV` under support weighting reaches `R2 = 0.179`,
      about `+0.019` over base;
    - in `GroupKFold`, socio-demographics improve the stress test by about
      `+0.146`, but the absolute R2 remains negative;
  - residence OSM/BIP (`R3`) does not improve over socio-demographics and often
    worsens performance.
- Interpretation:
  - the weak incremental performance of candidate families is not only an OLS
    collinearity artifact;
  - linear/regularized models suggest low-to-moderate predictive ceiling with
    current features;
  - a non-linear benchmark is justified as a ceiling check for interactions or
    thresholds, not as causal evidence.

## 2026-07-07 — Non-linear benchmark cells added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added:
  - `RandomForestRegressor` support in the estimator helper;
  - optional `XGBoostRegressor` support when `xgboost` is installed;
  - tree-aware preprocessing: impute numeric features but do not scale them for
    tree models;
  - `block8b-run-nonlinear-benchmark`.
- Benchmark design:
  - runs non-linear models only on the full family specification for each
    geography:
    - residence: `R3_base_socio_osm_bip`;
    - origin_trip: `O3_base_ops_osm_bip`;
  - compares results against `R1_base`/`O1_base` via the same
    `delta_*_vs_base` metrics;
  - skips and reports XGBoost if the package is unavailable.
- Verification:
  - did not execute or render;
  - static Python parsing passed for 23 QMD code cells.
- Next action:
  - user should run `block8b-run-nonlinear-benchmark` and review whether trees
    materially improve over the linear/regularized ceiling.

## 2026-07-07 — Outcome audit block added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added new section:
  - `12) Audit de outcomes`.
- Added cells:
  - `block9a-outcome-audit-targets`;
  - `block9b-outcome-audit-target-summary`;
  - `block9c-run-continuous-outcome-audit`;
  - `block9d-run-top-growth-classification-audit`;
  - `block9e-outcome-audit-reading-template`.
- Outcomes audited:
  - `delta_relative_pp`;
  - `delta_relative_pp_shrunk_support`;
  - `delta_pp`;
  - `delta_pp_shrunk_support`;
  - `delta_logit_qr_share_smooth`;
  - `share_shift_qr_delta`;
  - `top20_delta_relative_pp`.
- Design choices:
  - shrinkage uses `support_min / (support_min + BASE_MIN_SUPPORT)`;
  - `delta_relative_pp_shrunk_support` shrinks toward zero, consistent with
    the global-relative interpretation;
  - `delta_pp_shrunk_support` shrinks toward the global delta of the geography;
  - continuous outcomes compare base, interpretable family, full linear and
    optional XGBoost specs;
  - top-20 classification compares logistic regression and random forest specs
    using ROC-AUC, average precision and precision-at-observed-positive-count.
- Verification:
  - did not execute or render the notebook, per user preference;
  - static Python parsing passed for 28 QMD code cells.
- Next action:
  - user should run the new outcome audit blocks and compare whether the zonal
    modeling problem is better framed as regression on rate, smoothed rate,
    volume contribution or top-growth classification.

## 2026-07-07 — Outcome audit label collision fixed

- User reported a `KeyError: "['label'] not in index"` in
  `block9c-run-continuous-outcome-audit`.
- Cause:
  - the CV summary already used `label` for the model label;
  - merging outcome metadata with another `label` column caused Pandas to
    suffix/rename the columns, so the display column `label` no longer existed.
- Fix:
  - rename model `label` to `model_label` before merging outcome metadata;
  - rename outcome metadata `label` to `outcome_label`;
  - update display and sort columns accordingly.
- Verification:
  - static Python parsing passed for 28 QMD code cells;
  - a minimal merge/display reproduction passed in the Quarto Python
    environment.

## 2026-07-07 — Compact outcome audit display added

- User ran `block9c-run-continuous-outcome-audit`; the output completed but was
  truncated by notebook display because it has 96 rows.
- Added:
  - `block9c2-continuous-outcome-audit-compact-summary`.
- Purpose:
  - preserve the full CSV output from `block9c`;
  - add a reader-facing compact view with the best model by geography,
    validation and outcome;
  - add a short comparison of the three key framings:
    `delta_relative_pp`, `delta_relative_pp_shrunk_support` and
    `share_shift_qr_delta`.
- Verification:
  - did not execute or render the notebook;
  - static Python parsing passed for 29 QMD code cells.

## 2026-07-07 — Fine signal residual audit added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added new section:
  - `13) Audit de señal fina: residuos del baseline territorial`.
- Added cells:
  - `block10a-residualized-outcome-contract`;
  - `block10b-build-territorial-baseline-residuals`;
  - `block10c-residual-feature-screening`;
  - `block10d-residual-fine-signal-reading-template`.
- Design choices:
  - residualize `delta_relative_pp` and `delta_relative_pp_shrunk_support`
    against the territorial baseline:
    `qr_share_2024 + support_min_log + n_2025_log + macrozone_group`;
  - use out-of-fold residuals from KFold zones and support-weighted KFold;
  - screen candidate families against residuals using Spearman correlation,
    weighted Pearson correlation and Q5-Q1 residual gaps;
  - postpone manual interaction terms until there is evidence of residual
    signal, because tree models already tested non-linear/interacting
    structure at a broad level.
- Verification:
  - did not execute or render the notebook;
  - static Python parsing passed for 33 QMD code cells.
- Next action:
  - user should run `block10a` through `block10d` and inspect whether any
    candidate family survives after removing the baseline territorial signal.

## 2026-07-07 — Within/between macrozone audit added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added new section:
  - `14) Audit within/between macrozona`.
- Added cells:
  - `block11a-build-within-between-macrozone-features`;
  - `block11b-within-macrozone-residual-screening`;
  - `block11c-within-between-reading-template`.
- Purpose:
  - separate candidate predictors into macrozone-level (`between`) and
    within-macrozone deviations;
  - test whether fine residual signal remains after removing broad territorial
    structure;
  - distinguish variables that mainly proxy macrozone differences from
    variables that still order zones inside each macrozone.
- Output artifacts:
  - `03_models/results/18_zonal_qr_growth_modeling/within_between_macrozone_feature_metadata.csv`;
  - `03_models/results/18_zonal_qr_growth_modeling/within_between_macrozone_residual_screening.csv`.
- Cleanup:
  - removed an accidental duplicate diagnostics block;
  - restored sequential section numbering after the new audit.
- Verification:
  - did not execute or render the notebook, per user preference;
  - static Python parsing passed for 36 QMD code cells.
- Next action:
  - user should run `block11a`, `block11b` and `block11c`, then compare raw vs
    within-macrozone residual correlations.

## 2026-07-07 — Within/between macrozone audit reading

- User ran the within/between macrozone residual screening.
- Main conclusion:
  - centering variables within macrozone does not reveal a strong hidden local
    signal;
  - after the territorial baseline, residual associations remain weak.
- Quantitative reading:
  - origin-trip max within signal is about `|corr| = 0.09-0.13` weighted
    Pearson and `0.12-0.16` Spearman;
  - residence max within signal is about `|corr| = 0.09-0.14` weighted Pearson
    and `0.09-0.11` Spearman.
- Variable-level reading:
  - origin trip: `bus_stop_hour_supply` is the most consistent residual signal;
    in equal-zone KFold it reaches Spearman within `+0.155`, weighted Pearson
    within `+0.127` and Q5-Q1 residual gap around `+0.455 pp`;
  - origin trip: `bus_pressure_demand_supply`, OSM variables and BIP access
    remain weak or mixed;
  - residence: residual signals point more to age structure
    (`population_60_plus`, `age_mean_z`, `population_25_44`) than to education
    or OSM centrality;
  - BIP access remains a low-signal control, not a central mechanism.
- Modeling implication:
  - do not make within-macrozone centered variables the main modeling path
    unless a later feature set improves signal;
  - use this audit as evidence that the current zonal model is mostly capturing
    territorial structure, support and volume, with limited local fine-grained
    explanatory signal from available variables.

## 2026-07-07 — Zone-week panel feasibility audit added, not rendered

- Updated:
  - `03_models/18_zonal_qr_growth_modeling.qmd`.
- Added new section:
  - `19) Factibilidad panel zona-semana`.
- Added cells:
  - `block19a-zone-week-panel-contract`;
  - `block19b-build-zone-week-panel`;
  - `block19c-zone-week-panel-support-audit`;
  - `block19d-zone-week-temporal-stability`;
  - `block19e-zone-week-panel-decision-template`.
- Design:
  - build a comparable weekly panel using W14-W17 of 2024 and W14-W17 of 2025;
  - construct two geographies:
    - origin trip: trips by `zona_inicio_viaje x week_pair`;
    - residence: active cards by `zona_hogar x week_pair`;
  - compute weekly analogues of `delta_pp`, `delta_relative_pp`,
    `share_shift_qr_delta`, volume component and smoothed logit delta;
  - audit support, zone completeness, week-to-week rank stability and top-growth
    persistence before redesigning the model.
- Expected outputs:
  - `03_models/results/18_zonal_qr_growth_modeling/zone_week_panel_feasibility/zone_week_panel_long.parquet`;
  - `03_models/results/18_zonal_qr_growth_modeling/zone_week_panel_feasibility/zone_week_pair_growth_panel.parquet`;
  - support/completeness/stability CSV summaries in the same folder.
- Verification:
  - did not execute or render the notebook, per user preference;
  - static Python parsing passed for 41 QMD code cells.
- Next action:
  - user should run blocks `19a` through `19e` and inspect whether coverage and
    temporal stability justify a panel model.
