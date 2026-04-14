# Stage 03 — Migración de Dummies Temporales V2

## Resumen

Esta etapa consolidó el cambio metodológico desde las dummies temporales previas a un esquema V2 con base `LAB_VALLE`, alineado con la decisión aprobada por la profesora.

## Objetivo de la etapa

Estandarizar los modelos logit al esquema:

- `DUMMY_LAB_PM`
- `DUMMY_LAB_PT`
- `DUMMY_NO_LAB`

con base omitida `LAB_VALLE`.

## Decisiones metodológicas

- Migrar primero las fuentes activas de Biogeme.
- Usar el script operacional de validación como puente para Larch.
- Registrar explícitamente el gap de fuentes activas para Statsmodels/Larch cuando no existieran notebooks fuente.

## Implementación lograda

- Migración de `01`, `02`, `03` y `tmp/validation/nested_ext_v2_validations.py`.
- Revisión de consistencia entre worktrees.
- Preparación de reruns nested con muestras 20% y 50%.

## Limitaciones o problemas detectados

- Faltaban fuentes activas directas en algunas ramas/frameworks.
- Parte de la etapa quedó abierta en re-estimación y carga de resultados nuevos.

## Outputs/notebooks relevantes

- [`docs/planning/workstreams/time-dummies-v2-migration/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/time-dummies-v2-migration/notes.md)
- [`docs/planning/workstreams/time-dummies-v2-migration/task_plan.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/time-dummies-v2-migration/task_plan.md)

## Fuentes usadas para el backfill

- workstream legacy `time-dummies-v2-migration`
