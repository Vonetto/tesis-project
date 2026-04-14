# Task Plan

## Title
Ordenar estructura de outputs de modelos logit para evitar rutas duplicadas y cargas inconsistentes.

## Goal
Dejar una convención única de carpetas para resultados de Biogeme (base/extended/nested), corregir celdas de carga/guardado para usar esa convención y definir qué carpetas legacy mantener/mover.

## Constraints / Guardrails
- No eliminar resultados sin respaldo explícito.
- Priorizar cambios en rutas de notebooks antes de mover carpetas históricas.
- Mantener compatibilidad con fallback legacy durante transición.
- Usar `viajes_con_te_calculado_2025-W17.parquet` para corridas v2.

## Milestones
- [x] Inventario completo de carpetas y archivos de outputs en `03_models`.
- [x] Diseñar estructura objetivo (canónica) por framework/modelo.
- [x] Ajustar rutas de guardado y carga en notebooks relevantes (extendido v2 Biogeme).
- [x] Migrar carpeta misplaced de extended v2 (`03_models/model_outputs/...`) a ruta canónica.
- [ ] Evaluar limpieza adicional de outputs legacy (sin borrar; solo reubicar/documentar).
- [ ] Validar corrida nueva 20% y 50% en ruta canónica y recargar tablas.
