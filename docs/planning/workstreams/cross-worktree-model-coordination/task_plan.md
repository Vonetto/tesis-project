# Task Plan — Cross-Worktree Model Coordination

## Goal
Coordinar los tres frentes activos de la tesis para que el modelo econométrico, el benchmark `ML/XGBoost` y la segmentación usen una base metodológica comparable y alimenten una narrativa única de adopción digital en transporte público.

## Worktrees
- Principal / econométrico / escritura: `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project`
- Benchmark ML + SHAP: `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml`
- Segmentación de comportamiento: `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-segmentation`
- Fuera del plan activo por ahora: `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-logit-model`

## Guardrails
- El repo principal es la fuente de verdad para muestra objetivo, variables canónicas, decisiones metodológicas, escritura y reporte final.
- `XGBoost + SHAP` se trata como benchmark predictivo flexible, no como reemplazo automático del modelo econométrico.
- `SHAP` entrega interpretabilidad predictiva, no inferencia econométrica equivalente a `t-stat`, `p-value` u odds ratios.
- La segmentación no debe depender del mejor modelo predictivo para formar grupos; los segmentos se construyen con comportamiento observado y luego se usan para interpretar adopción/modelos.
- `QR_RED` se interpreta como proxy observable de adopción digital oficial, no como prueba directa de uso de app o información en tiempo real.
- No afirmar causalidad individual si el diseño no la identifica.

## Stage Plan
- [x] Crear workstream de coordinación cross-worktree.
- [x] Registrar reglas compartidas y roles de cada worktree.
- [x] Crear matriz inicial de modelos y entregables.
- [x] Crear registro inicial de variables y contrato de comparabilidad.
- [ ] Cerrar especificación canónica mínima de muestra y target para comparar MNL/Nested vs `XGBoost`.
- [x] Actualizar matriz de modelos cuando se definan macrozonas y nueva especificación econométrica.
- [ ] Usar `parsimonious` como referencia provisional para sincronizar variables con `tesis-project-ml`.
- [x] Usar `parsimonious` como referencia provisional para evaluar diferencias de adopción por segmento en `tesis-project-segmentation`.
- [ ] Sincronizar el frente `ML/XGBoost` con la variable objetivo y bloques finales del frente MNL/Nested.
- [ ] Sincronizar el frente de segmentación con los indicadores de comportamiento y la estrategia de conexión con modelos de elección.
- [ ] Preparar resumen ejecutivo de una página para profesores con frentes, resultados listos y experimentos pendientes.
- [ ] Convertir resultados finales a insumos del Capítulo 4 — Resultados y Capítulo 5 — Discusión.

## Current Priorities
1. Iniciar onboarding en `tesis-project-ml` y alinear el benchmark `XGBoost` multiclase con el target `BIP`/`QR_OTHER`/`QR_RED`.
2. Usar como referencia comparativa los artefactos `sample5pct` autocontenidos creados desde el notebook Larch `03_models/larch_logit/16_eod2012_income_proxy_larch_comparison.qmd`.
3. Mantener segmentación como análisis complementario basado en comportamiento observado; ya existe una sensibilidad `parsimonious` por segmentos `k=2` con `sample10pct`.
4. Interpretar después los resultados Larch/MNL/Nested, benchmark ML y segmentación antes de cerrar Resultados/Discusión.
5. Traducir hallazgos consolidados a escritura de tesis solo cuando estén cerrados o claramente marcados como sensibilidad.

## Linked Files
- `notes.md`: decisiones, contexto de reunión y criterios narrativos.
- `model_matrix.md`: matriz viva de modelos, objetivos, estado y métricas.
- `feature_registry.md`: registro de variables, bloques y contrato de comparabilidad.
- `tesis-project-segmentation/docs/reports/segmentacion-indicadores/modelos_por_segmento_sample10.md`: reporte de sensibilidad `parsimonious` por segmentos `k=2` con `sample10pct`.
