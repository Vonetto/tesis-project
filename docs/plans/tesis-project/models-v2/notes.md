# Notes — Logit Models v2 Alignment

Project: tesis-project

## Decisions (dated)

- 2026-01-04 — Keep v1 outputs intact; write new v2 outputs to `*-v2` folders for side-by-side comparison.
- 2026-01-04 — Use corrected parquet as canonical input for v2: `tmp/viajes_con_te_calculado_2025-W17.parquet`.
- 2026-01-04 — Remove walking time from v2 (no `VAR_T_CAMINATA_MIN`).
- 2026-01-04 — Avoid double counting waits: `te0_calculado` = initial wait; `te1..te5_calculado` = transfer waits.
- 2026-01-04 — Statsmodels: baseline + extended only; nested handled by Biogeme + Larch.
- 2026-01-06 — Align mode dummies across frameworks in v2: keep MetroTren (4) separate and exclude it from `DUMMY_SOLO_METRO` / `DUMMY_METRO_BUS` (only recode ZonaPaga(3)→Bus(1)).
- 2026-01-06 — Nested v2: correr y guardar **dos variantes** del modelo (con y sin `DUMMY_SOLO_METRO` / `DUMMY_METRO_BUS`) por recomendación de la profesora (posible colinealidad / medición imperfecta de modo).

## Findings

- Parquet v2 schema (quick scan): 132 columns; present: `is_qr`, `tiempo_inicio_viaje`, `tipodia`, `n_etapas_recon`, `tipo_transporte_1..4`.
- `*_calculado` columns present: `te0..te5_calculado`, `tv1..tv6_calculado`, `tc2_calculado`, `tc3_calculado` (no `tc1_calculado`).
- 2026-01-04 — Patched Biogeme extended v2 to compute transfer wait from `te1..te5_calculado` only (no `te0` in transfer wait).
- 2026-01-04 — Patched Biogeme baseline notebook to support v2 parquet input + `*-v2` output folders via `USE_V2_PARQUET` and `OUTPUT_SUFFIX`.
- 2026-01-04 — Patched Biogeme nested notebook: (a) extended v2 transfer-wait uses `te1..te5_calculado`, (b) base nested estimation can read v2 parquet and writes to `nested-base-v2-*` folders.
- 2026-01-04 — Patched Larch binary baseline to support v2 parquet input + `*-v2` output folders via `USE_V2_PARQUET`/`OUTPUT_SUFFIX`.
- 2026-01-04 — Patched Larch extended + nested v2 to compute transfer wait from `te1..te5_calculado` only (no `te0` in transfer wait).
- 2026-01-04 — Patched Larch nested base sequential/covers checks to optionally read v2 parquet and write to `nested-base-v2-*` folders.
- 2026-01-04 — Patched Statsmodels baseline to support v2 parquet input + `*-v2` output folders via `USE_V2_PARQUET`/`OUTPUT_SUFFIX`.
- 2026-01-04 — Patched Statsmodels extended to v2: uses `n_etapas_recon`, `tv*_calculado`, `te*_calculado`, no walking, transfer wait = `te1..te5_calculado`, outputs under `model_outputs_sm/W17-extended-v2-*`.
- 2026-01-06 — Nested (QR_RED vs QR_OTHER) depende de la tabla de caracterización `caracterización qr_202504.csv` para poblar `tipo_app`; si `df_caracterizacion=None`, todos los QR quedan como `QR_OTHER` y el nested pierde sentido (QR_RED sin observaciones).

## Commands / Repro

- Inspect v2 schema:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/venv/bin/python -c "import polars as pl; print(len(pl.scan_parquet('tmp/viajes_con_te_calculado_2025-W17.parquet').collect_schema().names()))"`

- 2026-01-04 — Suggested smoke run (v2): start with small samples (e.g. baseline 5%, extended 5–20%) to confirm outputs land under `*-v2` folders before running heavier configs.
- 2026-01-04 — Biogeme baseline v2 executed for 2025-W17 (full): output in `03_models/biogeme-logit/model_outputs/W17-baseline-v2/` with sample size 12,168,854 and rho-bar ≈ 0.351 (wall-clock ~1497.5s).
- 2026-01-04 — Larch baseline v2 executed for 2025-W17 (full): output in `03_models/larch_logit/model_outputs_larch/W17-baseline-v2/` with sample size 12,168,854 and rho-bar ≈ 0.351 (wall-clock ~21.3s).
- 2026-01-04 — Statsmodels baseline v2 executed for 2025-W17 (full): output in `03_models/statsmodels_logit/model_outputs_sm/W17-baseline-v2/` with sample size 12,168,854 and rho-bar ≈ 0.351 (wall-clock ~3.1s).
- 2026-01-04 — Ran `03_models/compare_larch_biogeme.py` and wrote comparison CSVs to `tmp/compare/` including a matched `binary_baseline` row for `2025-W17` `variant=v2` `sample=full`.
- 2026-01-04 — Gotcha: `03_models/larch_logit/02_binary_extended_logit_qr_adoption_larch.qmd` still starts with a v1 (silver) load cell; v2 uses `#|label: prepare-extended-model-data-v2-larch` + `#|label: estimate-extended-v2-2025W17-larch` reading `tmp/viajes_con_te_calculado_2025-W17.parquet` directly.

## Progress log (dated)

- 2026-01-06 — Extended v2 estimates produced for W17 using `sample20pct` and `sample50pct` in all three frameworks:
  - Larch: `03_models/larch_logit/model_outputs_larch/W17-extended-v2-sample{20,50}pct/`
  - Statsmodels: `03_models/statsmodels_logit/model_outputs_sm/W17-extended-v2-sample{20,50}pct/`
  - Biogeme: `03_models/biogeme-logit/model_outputs/W17-extended-v2-sample{20,50}pct/`
- 2026-01-06 — Verified cross-framework consistency (Extended v2, W17 sample20pct): parameters and Biogeme-style rho-bar match closely across Biogeme/Larch/Statsmodels.
- 2026-01-06 — Biogeme “load results” gotcha: CSV names are `params_ext_v2_<partition>.csv` and `stats_ext_v2_<partition>.csv` and paths depend on CWD; use `PROJECT_ROOT/03_models/biogeme-logit/model_outputs` as base.
- 2026-01-06 — Biogeme API gotcha: en algunos entornos `results.data` no existe (AttributeError). Usar `getattr(results, "data", None)` o asumir convergencia si `estimate()` devuelve sin excepción.
- 2026-01-06 — Prepared Nested Logit Extended v2 to run both variants (`noModeDummies` + `modeDummies`) without overwriting outputs:
  - Larch: `03_models/larch_logit/03_nested_logit_larch.qmd` → `#|label: estimate-nested-ext-v2-both-mode-dummy-variants-larch`.
  - Biogeme: `03_models/biogeme-logit/03_nested_logit.qmd` → `#|label: sequential-estimation-nl-extended-v2` + `#|label: sequential-estimation-nl-extended-v2-specific`.
- 2026-01-06 — Nested v2 (Biogeme, W17 sample20pct) ejecutado, cargado y diagnosticado:
  - Folders canónicos: `03_models/biogeme-logit/model_outputs_nl_extended/W17-nested-ext-v2-{modeDummies|noModeDummies}-sample20pct/` y `.../W17-nested-ext-v2-specific-{modeDummies|noModeDummies}-sample20pct/`.
  - Selección preliminar: `specific` domina a `generic` por AIC/BIC; `MU_QR` en `specific` ≈ 2 (estable), mientras `generic` mostró `MU_QR` muy grande (sensibilidad/identificación).
  - Diagnóstico colinealidad (muestra 2%): `corr(DUMMY_METRO_BUS, VAR_N_TRASBORDOS)≈0.63`, `corr(DUMMY_METRO_BUS, VAR_T_ESPERA_TRASB)≈0.43`, `corr(DUMMY_SOLO_METRO, VAR_T_ESPERA_INICIAL)≈-0.63`.
- 2026-01-06 — Agregado loader v2 en Larch nested:
  - `03_models/larch_logit/03_nested_logit_larch.qmd` → `#|label: load-results-nested-ext-v2-larch` + celdas `display-nested-ext-v2-*` para mostrar stats y betas (generic/specific) por `ModeDummies`.
- 2026-01-06 — Nested v2 (Larch, W17 sample20pct) ejecutado (noModeDummies):
  - Generic: `LL_final≈-1.266337e6`, `AIC≈2.532695e6`, `MU_QR≈0.014` (muy cerca del bound inferior; fuerte anidamiento / posible degeneración en generic).
  - Specific: `LL_final≈-1.265740e6`, `AIC≈2.531518e6`, `BIC≈2.531759e6`, `MU_QR≈0.866` con t-stat vs 1 ≈ −1.27 (anidamiento débil/no significativo en esta especificación).

## Nested Logit — Validación Biogeme vs Larch (2026-01-07)

### Qué debería “ser igual”

- Para MNL/binario (sin nidos): con **misma muestra/filas**, **mismas variables**, **misma codificación** y **misma normalización**, Biogeme/Larch/Statsmodels deberían dar betas y `LL_final` prácticamente idénticos (solo diferencias numéricas). Esto ya se verificó en extended v2.

### Qué NO es comparable 1:1

- En Nested Logit, `MU_QR` puede estar definido como:
  - **dissimilarity** `λ ∈ (0,1]` (común en varios paquetes), o
  - **inversa** `μ = 1/λ ≥ 1` (común en otras implementaciones).
- Por eso, al comparar entre frameworks conviene transformar:
  - `λ_impl = 1 / μ_biogeme` (si Biogeme usa `μ`)
  - `μ_impl = 1 / λ_larch` (si Larch reporta `λ`)
- Señal de que Larch está testeando `μ=1`: el “Robust t-stat.” de `MU_QR` suele corresponder a `(MU_QR - 1) / SE` (en tu output, `0.014` con t≈−39 calza con esto).

### Protocolo para decidir si Larch es confiable para NL

1) **Misma muestra exacta**
   - Reusar el mismo set de `case_id`/filas para Biogeme y Larch (no solo mismo `seed`; idealmente persistir índices).
2) **Chequeo MU=1 (reduce a MNL)**
   - Fijar `MU_QR = 1` en ambos frameworks y verificar que betas/`LL_final` coincidan (si no coinciden, hay mismatch en especificación o datos).
3) **Liberar MU y comparar en “espacio común”**
   - Comparar `LL_final`, AIC/BIC y luego comparar `λ_impl`/`μ_impl` tras transformar.
4) **Estabilidad**
   - Probar 2–3 inicializaciones distintas (o reutilizar `iter`/starting values) y verificar que converge al mismo óptimo.
5) **Predicciones**
   - Comparar shares predichos por alternativa (BIP/QR_RED/QR_OTHER) y, si es posible, correlación de probabilidades por caso (en una muestra chica).

### Herramientas agregadas en el repo

- Script reproducible: `03_models/compare_nested_ext_v2_frameworks.py`
  - Lee outputs desde:
    - `03_models/biogeme-logit/model_outputs_nl_extended/`
    - `03_models/larch_logit/model_outputs_nl_larch/`
  - Entrega tabla de stats, transformación `μ↔λ` y merge de parámetros.
- Celdas en notebooks (runpy):
  - `03_models/biogeme-logit/03_nested_logit.qmd` → `#|label: compare-nested-ext-v2-biogeme-vs-larch`
  - `03_models/larch_logit/03_nested_logit_larch.qmd` → `#|label: compare-nested-ext-v2-larch-vs-biogeme`
- Script de validación rápida: `tmp/validation/nested_ext_v2_validations.py`
  - Valida existencia de outputs y compara Biogeme vs Larch (LL/AIC/BIC, μ↔λ, grad norm Larch).
  - Además soporta **exportar matched sample** + **estimar** (Biogeme/Larch) + **validar** en un solo comando (`--run-all`).
  - Comando recomendado (specific + noModeDummies):
    - `python3 tmp/validation/nested_ext_v2_validations.py --run-all --spec specific --mode noModeDummies --sample sample20pct-matched`
  - Para testear “reduce a MNL”, agrega `--run-mu1` (corre también `sample...-mu1` con `MU_QR=1` fijo en ambos frameworks):
    - `python3 tmp/validation/nested_ext_v2_validations.py --run-all --run-mu1 --spec specific --mode noModeDummies --sample sample20pct-matched`
  - Notas:
    - Para Biogeme puede ser necesario pasar `--biogeme-python` apuntando al venv donde está instalado.
    - Para Larch usa `--larch-python` o se auto-detecta `larch-env`; setea caches en `tmp/` para evitar errores de Numba.

### Benchmark Larch (multi-start/multi-method)

- Para diagnosticar optimización de `MU_QR` en Larch, se agregó un benchmark que corre múltiples inicializaciones y métodos y guarda:
  - `...-<sample>-bench/` con `runs_<spec>_<partition>.csv`
  - `...-<sample>-benchbest/` con outputs estándar (para comparar con Biogeme)
  - `...-<sample>-benchmu1/` con outputs estándar con `MU_QR=1` (MNL)
- Comando sugerido (usa matched sample existente):
  - `python3 tmp/validation/nested_ext_v2_validations.py --benchmark-larch --partition 2025-W17 --spec specific --mode noModeDummies --sample sample20pct-matched --larch-maxiter 400 --larch-methods slsqp,trust-constr --larch-mu-starts 0.2,0.35,0.5,0.65,0.8,0.9 --larch-quiet`
  - Nota: el benchmark ahora ejecuta **cada corrida en un proceso separado** (subprocess) y fuerza threads a 1 para evitar crashes tipo “heap corruption” en stacks OpenMP/Numba.
- Resultado (2026-01-07, W17, specific, noModeDummies, sample20pct-matched):
  - Referencia MU=1 (slsqp): `LL≈-1265554.757`, `grad≈1449.6`
  - Mejor corrida libre encontrada: `trust-constr` con `mu_init=0.5` → `LL≈-1265507.391`, `MU_QR≈0.456`, `grad≈21.8`
  - Interpretación: Larch **sí puede** llegar a un óptimo comparable a Biogeme; el problema era la optimización (método/inicialización), no el modelo en sí.

### Matched sample (para eliminar diferencias por muestreo)

- Larch: `03_models/larch_logit/03_nested_logit_larch.qmd`
  - Variables:
    - `USE_MATCHED_SAMPLE_FILE_EXT_V2_NL`
    - `EXPORT_MATCHED_SAMPLE_FILE_EXT_V2_NL`
    - `MATCHED_SAMPLE_PATH_EXT_V2_NL` (default: `tmp/matched_samples/nested_ext_v2_2025-W17_sample20pct.parquet`)
  - Idea: guardar el dataset *ya con features* (choice_nested + variables) y reutilizarlo en Biogeme.
- Biogeme: `03_models/biogeme-logit/03_nested_logit.qmd`
  - Variables:
    - `USE_MATCHED_SAMPLE_FILE_NL_EXT_V2`
    - `MATCHED_SAMPLE_PATH_NL_EXT_V2` (mismo default)
  - Si el archivo existe, omite la preparación/sampling y usa esas mismas filas.

### Interpretación preliminar de lo observado

- El caso *generic* cuadra bien si se interpreta `μ_biogeme ≈ 65  →  λ ≈ 0.015`, consistente con `MU_QR_larch ≈ 0.014` (cerca del bound inferior).
- La discrepancia más importante está en *specific*, donde Larch sugiere `λ` más cercano a 1 (anidamiento débil) y Biogeme sugiere anidamiento más fuerte; esto puede venir de:
  - diferencias sutiles de especificación (qué betas son alt-específicas, normalización de constantes),
  - bounds distintos para el parámetro del nido,
  - sensibilidad/no-identificación (colinealidad con dummies modales y atributos).

### Run-all matched sample (2026-01-07)

- Se ejecutó `--run-all` en matched sample (W17, specific, noModeDummies, sample20pct-matched):
  - Biogeme output: `03_models/biogeme-logit/model_outputs_nl_extended/W17-nested-ext-v2-specific-noModeDummies-sample20pct-matched`
  - Larch output: `03_models/larch_logit/model_outputs_nl_larch/2025-W17-nested-ext-v2-specific-noModeDummies-sample20pct-matched`
- Resultado clave (misma muestra exacta, mismas features):
  - `LL_final` muy cercano (Δ≈50), pero **parámetro del nido** difiere:
    - Biogeme: `MU_QR≈2.004` → `λ=1/μ≈0.499`
    - Larch: `MU_QR≈0.766` (interpretado como `λ`)
  - `GradNorm_Larch≈1260` (alta; sugiere que el óptimo de larch puede no estar bien resuelto o MU es débilmente identificado).
- Test MU=1 (“reduce a MNL”, 2026-01-07):
  - Larch reportó `LL(mu=1)` **mejor** que `LL(mu libre)` (lo cual no debería ocurrir si ambos óptimos están bien resueltos) → fuerte indicio de **problema de optimización/convergencia** en Larch para el caso NL.
- Gotcha corregido: algunos CSV de Larch traen números con `\xa0` (non-breaking space). Se parchó `03_models/compare_nested_ext_v2_frameworks.py` para coerción numérica robusta.
- Comparación formal con best-run de Larch (benchmark):
  - Comando: `python3 03_models/compare_nested_ext_v2_frameworks.py --partition 2025-W17 --spec specific --mode noModeDummies --biogeme-sample sample20pct-matched --larch-sample sample20pct-matched-benchbest --out tmp/compare/nl_ext_v2_W17_specific_noModeDummies_matched_vs_larchbenchbest`
  - Reporte: `tmp/compare/nl_ext_v2_W17_specific_noModeDummies_matched_vs_larchbenchbest.md`
