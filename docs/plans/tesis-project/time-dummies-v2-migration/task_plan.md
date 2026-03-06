# Task Plan — Migración de Dummies Temporales a V2 (todos los modelos logit)

## Goal
Estandarizar los modelos logit al esquema temporal V2:
- `DUMMY_LAB_PM`
- `DUMMY_LAB_PT`
- `DUMMY_NO_LAB`
con base implícita `LAB_VALLE`.

## Scope
- Modelos Biogeme base/extendido/nested.
- Pipeline de validación/benchmark nested que alimenta Larch.
- Dejar documentado el estado de fuentes Statsmodels/Larch (si faltan notebooks/scripts).

## Inventory (detected)
- [x] `03_models/01_binary_logit_qr_adoption.qmd`
- [x] `03_models/02_binary_extended_logit_qr_adoption.qmd`
- [x] `03_models/03_nested_logit.qmd`
- [x] `tmp/validation/nested_ext_v2_validations.py` (fuente operacional para comparaciones Larch)

## Blockers / Gaps
- [x] No aparecen notebooks/scripts fuente activos de estimación Statsmodels/Larch en el repo actual (`03_models/statsmodels_logit/` y `03_models/larch_logit/` contienen outputs, no código de estimación).

## Plan
- [x] Actualizar construcción de dummies (V2) en helpers/celdas de preparación.
- [x] Actualizar especificaciones/utilidades (reemplazar LJ/VIE por NO_LAB y base LAB_VALLE).
- [x] Actualizar secciones de carga/normalización de parámetros para nuevos nombres.
- [x] Ejecutar chequeo sintáctico de scripts Python modificados.
- [ ] Dejar instrucciones de re-estimación por notebook.

## Status
- Current: migración aplicada en fuentes disponibles (Biogeme + validación operacional Larch); pendiente validación de ejecución y re-estimación.

## Update (2026-02-25) — Consistencia entre worktrees
- [x] Definir fuente canónica de notebooks Biogeme: worktree .
- [x] Sincronizar  de Biogeme hacia worktree  para eliminar divergencia.
- [x] Unificar  para usar V2 por defecto () y fallback a .
- [x] Mantener salida con sufijo  en corrida secuencial extendida cuando .

## Update (2026-02-25) — Nested re-estimation prep
- [x] Ajustar `03_models/03_nested_logit.qmd` para corrida secuencial con muestras `sample20pct` y `sample50pct`.
- [x] Renombrar driver extendido específico a `run-nl-extended-specific-sample20-50`.
- [ ] Re-estimar nested base y nested extended (generic + specific) para `2025-W17`.
- [ ] Validar y cargar resultados nuevos evitando mezcla con runs legacy.
