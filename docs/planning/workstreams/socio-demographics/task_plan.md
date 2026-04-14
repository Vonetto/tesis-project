# Task Plan — Socio-demographic Integration (Censo/CASEN ↔ Zonas777)

## Goal
Integrate socio-demographic data (Censo 2024; CASEN if needed) with Zonas777 geometry to enrich OD/buffer analyses.

## Constraints / Guardrails
- Prefer the most disaggregated spatial level available (manzana/entidad).
- Use existing Zonas777 geometry.
- Keep outputs in project data folders; planning files stored in 3 locations.
- No interpretations in notes; only objective results.

## Milestones
- [x] Identify official download sources for Censo 2024 cartography + manzana/entidad base (links + file sizes).
- [x] Decide storage path (external drive) and download cartography ZIP.
- [x] Obtain manzana/entidad base table (official zip).
- [x] Download microdatos (personas/hogares/viviendas) + dictionary.
- [x] Inspect variables and pick candidate socio-demographic columns.
- [x] Build a spatial join plan (Zonas777 ↔ manzana/entidad) and aggregation strategy.
- [x] Validate join coverage using **Manzanas cartography + MANZENT** (diagnostics now non‑zero).
- [x] Propose integration paths for origin-only and OD (origin/destination) joins.
- [x] Confirm methodological preference with profesora (prioritize origin; evaluate both).
- [ ] Implement model-ready outputs for both variants (origin-only and OD origin+destination) in OD buffers pipeline.
- [ ] Run comparative estimations with socio-demo variants and archive objective stats/params.
- [x] Definir propuesta metodológica para desagregar microdatos comunales vía `comuna -> manzana-entidad -> ZONA777`.

## Next Actions
- [x] Choose default output: **intersects_area** (due to ~17% multi‑zone).
- [x] Quick sanity: verify shares within [0,1] or document if certain counts can exceed denominators.
- [x] Run buffers ↔ Censo join and validate coverage (pct_missing_censo_*).
- [ ] Attach socio-demo features to Option1 dataset (origin baseline first).
- [x] Attach socio-demo features to Option1 dataset (origin baseline first).
- [ ] Extend notebook section for socio-demo OD variant and side-by-side results.
- [ ] Auditar microdatos comunales `personas/hogares/viviendas` para identificar proxies más finas de ingreso/estatus.
- [x] Caracterizar `escolaridad` vs `prom_escolaridad18` y decidir si conviene derivar shares por tramo educativo.
- [x] Diseñar estrategia de post-procesamiento espacial desde microdatos comunales a manzana/ZONA777 (post de Datagramas / asignación intra-comunal).
- [x] Definir formalmente la **unidad de asignación** de la población sintética (vivienda vs hogar) y las llaves de enlace entre `personas`, `hogares` y `viviendas`.
- [x] Construir shortlist de **variables de calibración** presentes tanto en microdatos comunales como en la base agregada manzana-entidad.
- [x] Construir shortlist de **variables objetivo** a recuperar espacialmente en la primera iteración (`cine11`, `escolaridad`, `sit_fuerza_trabajo`, `p40_cise_rec`).
- [x] Diseñar batería de **validaciones** obligatorias antes de usar outputs en el modelo (`totales comunales`, `fit de restricciones`, `reconstrucción de prom_escolaridad18`, `estabilidad por semilla`).
- [x] Definir comunas del **piloto inicial** (`Vitacura`, `La Pintana`, `Santiago`).
- [x] Definir criterio de éxito del **piloto inicial** antes de intentar una corrida completa.
- [ ] Materializar la corrida completa de la tabla base `vivienda/hogar + personas` y medir tiempo/memoria.
- [x] Etapa 1: ensamblar tabla sintética base `vivienda/hogar + personas` y validar consistencia de llaves/conteos.
- [x] Etapa 2: preparar tabla de restricciones finas a nivel `manzana-entidad` y mapear definiciones comparables con microdatos.
- [x] Implementar baseline tonta de asignación aleatoria con cuotas exactas por `n_hog` dentro de cada comuna piloto.
- [x] Formalizar el criterio de éxito del piloto como “mejorar claramente a la baseline tonta dentro de cada comuna”.
- [x] Etapa 3: implementar **piloto simple y auditable** de asignación `comuna -> manzana-entidad` en pocas comunas.
- [ ] Etapa 4: correr batería de validaciones del piloto (`totales`, `fit`, `holdout`, `semillas`) y decidir si escala.
- [ ] Etapa 5: solo si el piloto simple falla, evaluar refinamiento con heurísticas/optimización más compleja.
- [ ] Gate de uso en modelos: no usar variables spatializadas en `ZONA777` hasta que pasen validación cruzada y estabilidad mínima.
- [ ] Comparar explícitamente `profile_score` vs `profile_discrete` y decidir si el siguiente refinamiento prioriza correlación (`Santiago`/`La Pintana`) o balance de error (`Vitacura`).
- [x] Comparar explícitamente `profile_score`, `profile_discrete` y `softmax_tau003` y decidir cuál será la base del refinamiento con swaps / annealing.
- [x] Implementar variantes conservadoras de energía para el refinamiento (`count`, `share`, `hybrid`) y compararlas en el piloto con la misma inicialización `softmax_tau003`.
- [x] Probar el refinamiento `annealing(share)` sobre `profile_discrete` para verificar si la mejora depende de la solución inicial.
- [ ] Elegir una variante de energía para corridas más largas (`share` por ahora lidera) o mantener `softmax_tau003` como solución principal si el refinamiento no mejora de forma suficientemente uniforme por comuna.
- [x] Implementar pipeline operativo `softmax_tau003 -> MANZENT -> ZONA777` para producir proxies microdato sin pisar el parquet censal agregado existente.
- [x] Crear EDA reproducible para las nuevas variables `ZONA777` derivadas de microdatos y persistir el piloto en `02_eda/tmp`.
- [x] Refinar la desagregación educativa adulta desde `cine11` en `terciaria corta / universitaria / postgrado` y regenerar el piloto `softmax_tau003`.
- [ ] Revisar resultados del nuevo EDA y decidir shortlist final para llevar al modelo.
