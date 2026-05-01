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
- [x] Revisar resultados preliminares del nuevo EDA y traducirlos a una shortlist inicial de variables para modelación.
- [x] Preparar en `03_models/08_nested_logit_enriched_interannual_censo.qmd` la ruta Biogeme `Censo + microdatos spatialized`, incluyendo construcción del parquet full `ZONA777` si falta, estandarización sobre zonas usadas y outputs específicos de estimación.
- [x] Ejecutar una primera ronda de modelos en `03_models/08_nested_logit_enriched_interannual_censo.qmd` con variables microdato educativas probadas **de a poco**:
  - `share_cine18_universitaria_micro` ✓
  - `share_cine18_terciaria_corta_micro` ✓
  - `share_cine18_postgrado_micro` ✓
- [x] Comparar resultados de la primera ronda microdato contra:
  - `mnl_interannual_censo_prom_escolaridad18` ✓
  - combinaciones controladas con `prom_escolaridad18` ✓ (no convergieron)
  - combo `universitaria + terciaria_corta` ✓ (no convergió)
- [ ] Revisar los resultados del resto de variables censo ya corridas (`prom_edad`, `share_inmigrantes`, `share_hacinamiento`, `share_internet`, `share_serv_compu`, `share_serv_tel_movil`, `share_discapacidad`, `share_analfabet`) y sus combos con `prom_escolaridad18`.
- [ ] Analizar `mnl_interannual_censo_full` (todas las variables censo juntas) y observar su comportamiento respecto a las especificaciones individuales.
- [x] Decidir cierre final de etapa para proxy educativa principal:
  - `share_cine18_universitaria_o_mas_micro` queda como candidata principal por coherencia metodológica e interpretabilidad;
  - `prom_escolaridad18` queda como benchmark agregado explícito;
  - `share_cine18_postgrado_micro` queda como sensibilidad;
  - no seguir abriendo más proxies educativas en esta rama.
- [x] Reabrir la decisión metodológica por definición del proxy educativo:
  - si la pregunta es “nivel académico como proxy de ingreso”, conviene construir una variable de **al menos universitaria**;
  - se define `share_cine18_universitaria_o_mas_micro = cine11 in [9, 10, 11]` para 18+;
  - queda implementada de punta a punta en `lib`, `02_eda` y `03_models/08`.
- [ ] Evaluar si vale la pena incorporar `share_independiente_micro` como variable laboral secundaria en una segunda ronda.
- [x] Cerrar shortlist final de proxies educativas para llevar al modelo principal y documentar qué variables se descartan por redundancia.
- [x] Correr EDA + primera estimación de `share_cine18_universitaria_o_mas_micro` y compararla contra:
  - `share_cine18_universitaria_micro`;
  - `prom_escolaridad18`;
  - `share_cine18_postgrado_micro`.
- [ ] Integrar al frente principal del modelo `share_cine18_universitaria_o_mas_micro`, manteniendo `prom_escolaridad18` como benchmark explícito y `share_cine18_postgrado_micro` como sensibilidad.
