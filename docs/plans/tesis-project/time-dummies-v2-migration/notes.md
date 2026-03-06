# Notes — Migración Dummies Temporales V2

## 2026-02-18 — Inicio
- Usuario solicita migrar todos los modelos logit a dummies V2 aprobadas por profesora.
- Criterio V2:
  - `DUMMY_LAB_PM` = laboral punta mañana
  - `DUMMY_LAB_PT` = laboral punta tarde
  - `DUMMY_NO_LAB` = no laboral
  - Base omitida = `LAB_VALLE` (laboral fuera de punta)

## 2026-02-18 — Hallazgos de inventario
- Archivos fuente con dummies V1 detectados:
  - `03_models/01_binary_logit_qr_adoption.qmd`
  - `03_models/02_binary_extended_logit_qr_adoption.qmd`
  - `03_models/03_nested_logit.qmd`
  - `tmp/validation/nested_ext_v2_validations.py`
- En repo actual no se detectan notebooks/scripts fuente activos para estimación en:
  - `03_models/larch_logit/`
  - `03_models/statsmodels_logit/`
- Esas carpetas contienen outputs CSV, pero no código fuente de estimación a migrar.

## 2026-02-18 — Decisión operativa
- Migrar inmediatamente los archivos fuente disponibles.
- Dejar explícito en plan/notas el gap de fuentes Larch/Statsmodels para resolver luego (restaurar notebooks o definir nuevo script unificado).

## 2026-02-18 — Cambios aplicados (objetivos)
- `03_models/01_binary_logit_qr_adoption.qmd`
  - Dummies temporales migradas a V2 en helpers y celdas activas de estimación.
  - Especificación binaria actualizada a `B_LAB_PM`, `B_LAB_PT`, `B_NO_LAB` (base `LAB_VALLE`).
  - Texto de interpretación alineado a V2.
- `03_models/02_binary_extended_logit_qr_adoption.qmd`
  - Dummies temporales migradas a V2 en preparación y estimación (simple + extendido secuencial).
  - Ecuación de utilidad extendida actualizada a `LAB_PM`, `LAB_PT`, `NO_LAB`.
  - Mapeo de carga de resultados ampliado para nuevos nombres de betas.
- `03_models/03_nested_logit.qmd`
  - Baseline y extendido migrados a V2 en preparación y especificación de utilidades.
  - Secciones de comparación/resumen actualizadas a nombres V2.
- `tmp/validation/nested_ext_v2_validations.py`
  - Construcción de dataset migrada a `DUMMY_LAB_PM`, `DUMMY_LAB_PT`, `DUMMY_NO_LAB`.
  - Especificaciones Biogeme/Larch (generic y specific) migradas a betas temporales V2.
  - Checks/required columns y diagnósticos ajustados a V2.

## 2026-02-18 — Estado de fuentes por framework
- **Biogeme**: migración aplicada en notebooks fuente activos (`01/02/03`).
- **Larch**: migración aplicada en script operacional de validación (`tmp/validation/nested_ext_v2_validations.py`).
- **Statsmodels**: sin notebooks/scripts fuente activos detectados en repo actual (solo outputs en `03_models/statsmodels_logit/model_outputs_sm/`).

## 2026-02-25 — Reparación de divergencia de worktrees (Biogeme)
- Problema detectado: notebooks  de Biogeme estaban desalineados entre:
  -  (ruta: )
  -  (ruta: )
- Acción tomada:
  - Se sincronizaron , ,  entre ambos worktrees.
  - Se verificó igualdad de contenido archivo-a-archivo ( sin diferencias).
- Decisión implementada para extendido ():
  -  por defecto.
  - Path V2 robusto con override () y búsqueda de candidatos.
  - Con V2 activo, corrida secuencial se restringe a .
  - Carga de datos y corrida secuencial usan  cuando V2 está activo.
  - Carpeta de salida secuencial agrega sufijo .
- Resultado: comportamiento consistente con la decisión metodológica vigente (usar parquet V2 W17).

## 2026-02-25 — Nested (setup de re-estimación)
- Archivo actualizado: `03_models/03_nested_logit.qmd`.
- Cambios:
  - `SAMPLE_CONFIGS` quedó en `{sample20pct: 0.20, sample50pct: 0.50}`.
  - Driver extendido específico ahora corre 20% y 50% (`run-nl-extended-specific-sample20-50`).
- Objetivo: alinear nested con la estrategia de comparación 20% vs 50% usada en el extended binario.
- Ajuste adicional aplicado en nested:
  - Driver `run-nl-extended-specific-then-generic` ahora recorre todas las muestras en `SAMPLE_CONFIGS` (20% y 50%) para ambos specs (`specific`, `generic`).
  - Evita omitir el caso `generic + 50%`.
- Se agregó sección de análisis para NL base en `03_models/03_nested_logit.qmd`:
  - `6.1` Diagnóstico de convergencia (`generic` vs `specific`).
  - `6.2` Comparación de parámetros `specific` (20% vs 40%).
  - `6.3` Interpretación y criterio de reporte (priorizar `specific`).
- Se reforzó la interpretación en NL base con lenguaje sustantivo ("uso de QR_RED/QR_OTHER más probable en...") y chequeo explícito de esquema de dummies cargado (V2 vs legacy) en sección 5.5.
