# Stage 04 — Cleanup de Outputs y Estructura

## Resumen

Esta etapa ordenó la estructura de outputs de modelos logit para eliminar rutas duplicadas, reducir confusión entre notebooks y fijar rutas canónicas de guardado/carga.

## Objetivo de la etapa

Definir una convención única para outputs de Biogeme y dejar compatibilidad con rutas legacy donde fuera necesario.

## Decisiones metodológicas

- Priorizar la corrección de rutas en notebooks antes de mover carpetas históricas.
- Mantener fallback legacy durante la transición.
- Fijar rutas canónicas distintas para corridas base/extended y nested.

## Implementación lograda

- Inventario de rutas existentes en `03_models`.
- Reasignación de la carpeta misplaced `03_models/model_outputs/...`.
- Actualización del notebook extendido v2 para usar la ruta canónica.

## Limitaciones o problemas detectados

- Persistía limpieza adicional por hacer en outputs legacy.
- Parte del estado dependía de validar nuevas corridas en la ruta canónica.

## Outputs/notebooks relevantes

- [`docs/planning/workstreams/outputs-structure-cleanup/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/outputs-structure-cleanup/notes.md)
- [`docs/planning/workstreams/outputs-structure-cleanup/task_plan.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/outputs-structure-cleanup/task_plan.md)

## Fuentes usadas para el backfill

- workstream legacy `outputs-structure-cleanup`
