# Notes

## 2026-02-25
- Usuario pide ordenar outputs porque hay carpetas duplicadas/confusas (p.ej. `03_models/model_outputs` vs `03_models/biogeme-logit/model_outputs`).
- Objetivo inmediato: unificar para modelo extendido v2 y revisar árbol completo.

### Inventario (03_models)
- Biogeme binario: `03_models/biogeme-logit/model_outputs`.
- Biogeme nested base: `03_models/biogeme-logit/model_outputs_nl_base`.
- Biogeme nested extended: `03_models/biogeme-logit/model_outputs_nl_extended`.
- Larch binario/extended: `03_models/larch_logit/model_outputs_larch`.
- Larch nested: `03_models/larch_logit/model_outputs_nl_larch`.
- Statsmodels: `03_models/statsmodels_logit/model_outputs_sm`.
- Carpeta misplaced detectada: `03_models/model_outputs/W17-extended-v2-sample20pct`.

### Decisiones
- Ruta canónica para corridas Biogeme base/extended: `03_models/biogeme-logit/model_outputs`.
- Mantener `model_outputs_nl_base` y `model_outputs_nl_extended` para modelos nested.
- Mantener fallback de carga a rutas legacy para no romper análisis previos.

### Cambios aplicados
- Notebook actualizado: `03_models/02_binary_extended_logit_qr_adoption.qmd`.
  - `BASE_OUTPUT_DIR_EXT_V2` ahora apunta a `PROJECT_ROOT / "03_models" / "biogeme-logit" / "model_outputs"`.
  - Carga de resultados prioriza ruta canónica y usa fallback legacy.
  - Show params v2 prioriza ruta canónica y busca el archivo más reciente como fallback.
- Migración de outputs:
  - Movido `03_models/model_outputs/W17-extended-v2-sample20pct` -> `03_models/biogeme-logit/model_outputs/W17-extended-v2-sample20pct`.
  - Eliminada carpeta `03_models/model_outputs` al quedar vacía.
- Sync de notebook equivalente al worktree `tesis-project-logit-model`.

### Pendiente inmediato
- Reestimar también `sample50pct` con spec nuevo y confirmar que la tabla comparativa ya no mezcle parámetros legacy (`B_LJ_LAB`, `B_VIE_LAB`) con nuevos (`B_NO_LAB`).
- Limpieza adicional aplicada:
  - Movido `03_models/model_outputs/W17-extended-v2-sample50pct` (contenía solo `__logit_qr_bip_ext_v2_2025-W17.iter`) a `03_models/biogeme-logit/model_outputs/W17-extended-v2-sample50pct`.
  - Eliminada `03_models/model_outputs` al quedar vacía.
