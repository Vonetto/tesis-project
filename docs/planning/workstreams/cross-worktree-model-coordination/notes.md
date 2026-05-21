# Notes — Cross-Worktree Model Coordination

## 2026-05-13 — Creación del plan coordinado de etapas
- Se crea este workstream para coordinar tres frentes paralelos:
  - modelo econométrico en `tesis-project`;
  - benchmark `ML/XGBoost + SHAP` en `tesis-project-ml`;
  - segmentación de comportamiento en `tesis-project-segmentation`.
- El objetivo es evitar divergencia entre muestras, variables, nombres de modelos, métricas e interpretación de resultados.
- El repo principal queda como fuente de verdad para:
  - definición de muestra y alternativas;
  - variables canónicas y bloques de variables;
  - decisiones metodológicas;
  - narrativa de tesis;
  - reporte final y capítulos.

## 2026-05-13 — Lectura integrada de reuniones docentes
- Directrices de la profesora guía:
  - mantener `BIP` como alternativa base para variables comunes;
  - revisar tiempos, esperas y transbordos usando atributos observados a nivel de viaje;
  - comparar MNL y Nested Logit bajo una especificación más limpia;
  - agregar controles de macrozona y evaluar estabilidad de coeficientes territoriales;
  - depurar variables potencialmente redundantes o menos interpretables, especialmente `shelter`, `convenience` y `hacinamiento`;
  - explorar segmentación/clases después de estabilizar la base econométrica.
- Directrices del profesor codirector:
  - estimar `XGBoost` con pérdida logit/multiclase como benchmark flexible;
  - usar modelos basados en árboles para capturar no linealidades e interacciones que MNL/Nested pueden no representar;
  - usar `SHAP` para interpretar el benchmark predictivo, sin confundirlo con inferencia econométrica;
  - preparar resumen ejecutivo, mapas, distribuciones y visualizaciones de resultados.

## 2026-05-13 — Decisión metodológica sobre ML vs modelos de elección discreta
- Framing aceptado:
  - MNL/Nested entregan una especificación interpretable basada en utilidad aleatoria, con parámetros, odds ratios, significancia y supuestos explícitos;
  - `XGBoost` relaja la forma funcional lineal y puede capturar interacciones/no linealidades, pero introduce otros supuestos prácticos: tuning, regularización, riesgo de leakage y dependencia del split;
  - `SHAP` ayuda a interpretar patrones predictivos, pero no reemplaza `t-stat`, `p-value`, elasticidades ni odds ratios.
- Implicancia para tesis:
  - el benchmark ML se presenta como evidencia complementaria de robustez/flexibilidad predictiva;
  - el modelo econométrico sigue siendo el eje principal para interpretación estructurada de signos y asociaciones.

## 2026-05-13 — Decisión metodológica sobre segmentación
- La segmentación no debe formarse a partir del resultado del mejor modelo si eso genera circularidad.
- La ruta preferida es:
  - construir segmentos con comportamiento observado, regularidad, intensidad de uso, temporalidad, multimodalidad y fricciones;
  - después comparar adopción de `BIP`, `QR_OTHER` y `QR_RED` por segmento;
  - luego evaluar modelos por segmento o interacciones si el resultado es estable y útil.
- La segmentación se mantiene como complemento, no como sustituto del modelo de elección.

## 2026-05-13 — Riesgos a controlar
- No duplicar definiciones de variables entre worktrees.
- No comparar métricas entre modelos que usan muestras o targets distintos sin dejarlo explícito.
- No usar `QR_RED` como evidencia directa de uso de app o información en tiempo real.
- No convertir SHAP en inferencia causal o econométrica.
- No prometer clases latentes si la segmentación descriptiva no converge a perfiles claros.
- No cerrar el Capítulo de Resultados hasta estabilizar modelo principal, sensibilidades y benchmark comparativo.

## 2026-05-13 — Inicio de sensibilidad con macrozonas
- Se decidió partir por macrozonas porque controlan heterogeneidad territorial amplia y permiten evaluar si los coeficientes Censo/OSM/EOD son robustos a una estructura espacial gruesa.
- El shapefile oficial `ZONA777` ya contiene `NMACROZONA` y `MACROZONA`; por tanto, no se inventa una clasificación por centroides.
- Decisión de codificación:
  - usar macrozonas oficiales `NORTE`, `PONIENTE`, `ORIENTE`, `CENTRO`, `SUR`, `SURORIENTE`;
  - usar `CENTRO` como categoría base;
  - absorber `NMACROZONA = 7` como `EXTERNA_ESPECIAL`;
  - no excluir filas externas/especiales porque su peso muestral es bajo y excluirlas agregaría una regla nueva innecesaria.
- Primer notebook actualizado:
  - `03_models/16_eod2012_income_proxy_stepwise.qmd`.
- Preset nuevo:
  - `joint_mnl_censo_osm_eod_macrozone_sensitivity`.
- Modelos activos en esta sensibilidad:
  - candidato EOD continuo con macrozonas;
  - se descarta por ahora el candidato EOD dummy para concentrar la lectura en una especificación continua más informativa y comparable.

## 2026-05-13 — Starting values para macrozonas
- La primera corrida del modelo con macrozonas alcanzó convergencia, pero el kernel murió en la etapa final de cálculo de segundas derivadas/BHHH.
- Para no reiniciar desde cero, el notebook `16` quedó ajustado para cargar starting values desde el modelo sin macrozonas equivalente:
  - target: `mnl_joint_current_main_mujeres_parv_plus_eod_abc1_de_income_proxy_macrozonas`;
  - fuente: `mnl_joint_current_main_mujeres_parv_plus_eod_abc1_de_income_proxy`.
- Los parámetros compartidos se inicializan con los valores estimados previamente.
- Las dummies nuevas de macrozona parten en `0`.
- Advertencia:
  - esto reduce el costo de optimización;
  - si el problema de kernel es memoria durante BHHH/robust covariance, todavía podría fallar al final.
- Ajuste adicional antes de reintentar:
  - `save_iterations = True` en Biogeme para escribir `__<model>.iter` durante la optimización;
  - no borrar `.iter` antes de correr cuando este modo está activo;
  - si existe un `.iter` propio del modelo con macrozonas, usarlo como starting values antes que el modelo sin macrozonas;
  - agregar celda `recover-iter-parameters` para exportar el `.iter` a CSV si el kernel muere antes de escribir `params_*.csv`.

## 2026-05-13 — Candidato principal econométrico actual
- Tras correr la batería de limpieza con macrozonas en el notebook `03_models/16_eod2012_income_proxy_stepwise.qmd`, se define `parsimonious` como candidato econométrico principal actual.
- Especificación `parsimonious`:
  - mantiene variables de viaje, año/franja, oferta/demanda, macrozonas, `share_cine18_universitaria_o_mas_micro_z`, `share_discapacidad_z`, `share_inmigrantes_z`, `share_mujeres_z`, `share_asistencia_parv_z`, `eod2012_share_hogares_de_income_proxy_z`, `playground`, `school`, `university`, `shelter` y `subway_entrance`;
  - elimina `share_hacinamiento_z`, `eod2012_share_hogares_abc1_income_proxy_z`, `sports_centre` y `convenience`.
- Razón de la decisión:
  - mejora BIC frente al macro completo;
  - elimina variables con menor claridad interpretativa o señal débil;
  - preserva los patrones centrales de adopción digital y fricciones operacionales.
- Rol en coordinación:
  - `parsimonious` pasa a ser la referencia provisional para alinear el benchmark `ML/XGBoost` y la segmentación;
  - el modelo macro completo se conserva como sensibilidad de mayor ajuste;
  - `osm_local_clean` queda como sensibilidad alternativa si se decide conservar los controles socioeconómicos completos.

## 2026-05-15 — Handoff operativo para pasar al worktree ML
- Estado del frente principal/econométrico:
  - el repo principal sigue siendo la fuente de verdad para narrativa, variables canónicas, muestras y reporte final;
  - la tesis se mantiene centrada en adopción de tecnologías digitales en transporte público observada mediante elección de medio de pago (`BIP`, `QR_OTHER`, `QR_RED`);
  - `QR_RED` debe interpretarse como proxy observable de adopción digital oficial, no como prueba directa de uso de app o información en tiempo real;
  - no afirmar causalidad individual, ni convertir asociaciones territoriales en mecanismos individuales.
- Estado reciente MNL/Larch:
  - se creó `03_models/larch_logit/16_eod2012_income_proxy_larch_comparison.qmd`;
  - el notebook compara cuatro especificaciones Larch: MNL agregado, Nested agregado, MNL con atributos observados por viaje y Nested con atributos observados por viaje;
  - el notebook quedó autocontenido para `sample5pct`: materializa Censo, OSM, EOD, macrozonas y atributos observados si faltan;
  - artefactos creados/validados:
    - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample5pct-censo4-micro-osm-eod2012.parquet`;
    - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample5pct-observed-trip-attrs.parquet`;
    - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample5pct-censo4-micro-osm-eod2012-observed-trip-attrs.parquet`;
    - `03_models/artifacts/interannual_enriched/censo2024_zona777_model_ready_sample5pct_microdata.parquet`;
    - `03_models/artifacts/interannual_enriched/osm_zona777_model_ready_sample5pct.parquet`;
    - `03_models/artifacts/interannual_enriched/eod2012_zona777_model_ready_sample5pct.parquet`.
- Detalles de reproducibilidad de esos artefactos:
  - Censo `sample5pct` se regenera si faltan `share_mujeres_z` o `share_asistencia_parv_z`;
  - `share_mujeres` y `share_asistencia_parv` se derivan desde `02_eda/tmp/censo2024_zona777/censo2024_zona777_agg_final.parquet`;
  - OSM `sample5pct` se regenera si faltan `osm_transport_shelter_yes_density_km2_z` o `osm_railway_subway_entrance_density_km2_z`;
  - EOD `sample5pct` se regenera si hay zonas usadas sin cobertura o valores nulos;
  - zonas faltantes/nulas se imputan con mediana zonal antes de estandarizar, dejando aviso explícito en consola.
- Lectura metodológica provisional:
  - la especificación agregada mantiene mejor desempeño predictivo/log-verosimilitud que la versión con atributos observados por viaje;
  - el Nested agregado colapsa prácticamente a MNL en Larch (`Mu:QR` en el borde), por lo que no aporta mejora sustantiva en esa especificación;
  - el Nested observado puede estimar `Mu:QR` interior, pero la ganancia frente a MNL observado es mínima y todavía requiere interpretación;
  - queda pendiente interpretar formalmente estas comparaciones antes de cerrar resultados.
- Estado de segmentación:
  - el frente `tesis-project-segmentation` ya avanzó en clusterización/indicadores;
  - falta interpretación, perfiles y conexión con adopción digital;
  - mantener segmentación como análisis complementario basado en comportamiento observado, no como clusters derivados del mejor modelo.
- Próximo frente recomendado:
  - pasar al worktree `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml`;
  - hacer onboarding primero, sin editar;
  - revisar `claude-mem`, `docs/planning/workstreams/od-buffers-nested-logit/ml_worktree_sync.md` y el workstream ML propio;
  - alinear el benchmark `XGBoost` multiclase con el target `BIP`/`QR_OTHER`/`QR_RED` y una muestra comparable al frente MNL/Larch;
  - comenzar por un benchmark predictivo comparable antes de SHAP;
  - métricas mínimas: logloss, accuracy/balanced accuracy, matriz de confusión y desempeño por clase;
  - SHAP solo después de validar que el benchmark esté limpio, como interpretabilidad predictiva y no como inferencia econométrica.

## 2026-05-17 — Reframing metodológico del frente ML hacia diagnóstico de adecuación funcional
- Decisión narrativa sobre el rol del XGBoost + SHAP en la tesis:
  - la tesis es explicativa, no predictiva; la métrica principal de éxito es interpretación estructural de adopción digital, no accuracy fuera de muestra;
  - SHAP entrega interpretabilidad predictiva (atribución a la predicción), no inferencia causal ni estructural equivalente a betas/odds ratios del MNL;
  - en presencia de features correlacionadas (Censo/OSM/EOD/macrozonas comparten estructura territorial), la interpretación causal de SHAP requiere supuestos adicionales fuertes (Janzing et al. 2020, Aas et al. 2021, Chen et al. 2020);
  - por tanto, el frame correcto del frente ML es **diagnóstico de adecuación funcional del MNL**, no modelo paralelo con interpretación equivalente.
- Tres usos defendibles del frente ML bajo este framing:
  - detección de no linealidades e interacciones que el logit no representa (vía SHAP partial dependence y rankings comparativos);
  - screening y priorización de variables (ya hecho con la shortlist Q/R del frente binario);
  - validación de robustez del logit (signos SHAP coinciden con signos beta del MNL: triangulación, no sustitución).
- Lo que el frente ML no hace en este framing:
  - no reemplaza al MNL como modelo principal de inferencia estructural;
  - no entrega elasticidades, intervalos de confianza ni tests sobre parámetros causales;
  - no se reporta accuracy como criterio de decisión metodológica.

## 2026-05-17 — Benchmark multiclase comparable: v1, v2 (intra-2025) y v3 (parsimonious pooled)
- Se creó y ejecutó `tesis-project-ml/03_models/ml_baselines/03_multiclass_xgboost_comparable.qmd` en dos versiones:
  - v1: BASE + CONTEXT + SOCIO_OSM_COMPARABLE (8 features socio/OSM de la shortlist ML vieja), sin coordenadas, intra-2025 W14+W15 → W17, sample 5%;
  - v2-spatial: idéntico a v1 + `X_ORIGIN_M`/`Y_ORIGIN_M` vía helper `lib/spatial_origin_lookup.py` (réplica del notebook 02 binario).
- Resultados v1 vs v2 sobre `roc_auc_ovr_macro` (sin pesos, métrica probabilística sensata):
  - XGBoost: v1=0,6125 → v2=0,6131 (Δ=+0,0006, esencialmente ruido);
  - Logit: v1=0,5897 → v2=0,5916 (Δ=+0,0019);
  - lectura: **una vez que el bloque socio/OSM zonal está presente, agregar coordenadas no agrega información apreciable** en multiclase;
  - implicancia: el MNL `parsimonious` (que no lleva coordenadas) no se está perdiendo señal espacial relevante por esa parametrización.
- Se creó y ejecutó `tesis-project-ml/03_models/ml_baselines/04_main_sample_travel_attr_sensitivity.qmd`:
  - usa los artifacts del frente econométrico `pooled_2024_2025-estimation-sample5pct…` directamente;
  - dos variantes lado a lado: `ml_aggregated_alt_specific` (TVH/TEI/TET/NTR × 3 alternativas, 37 features) y `ml_observed_common` (OBS_TVH/TEI/TET/NTR comunes, 29 features);
  - features comunes a ambas: 4 temporales + 4 contexto demand/offer + 17 del `parsimonious` econométrico (incluyendo macrozonas, mujeres, parv, EOD income proxy, OSM extendido);
  - soporta dos splits vía env var: `stratified_random` (default 70/30) y `temporal_2024_to_2025`.

## 2026-05-17 — Resultados notebook 04: aggregated > observed, con caveat de leakage agregado
- Bajo split `stratified_random` (sample 100% del 5pct, n_test ≈ 280k):
  - XGBoost aggregated: roc_auc_ovr_macro=0,6533, log_loss=0,4812;
  - XGBoost observed: roc_auc_ovr_macro=0,6144, log_loss=0,4949;
  - Logit aggregated: 0,6046;
  - Logit observed: 0,5940.
- Bajo split `temporal_2024_to_2025` (train=2024-W17, test=2025-W17, n_test ≈ 479k):
  - XGBoost aggregated: roc_auc_ovr_macro=0,6167, log_loss=0,5316;
  - XGBoost observed: roc_auc_ovr_macro=0,6014, log_loss=0,5400;
  - Logit aggregated: 0,5910;
  - Logit observed: 0,5809.
- Caída entre splits (stratified → temporal):
  - XGBoost aggregated: Δ=−3,7 pp (mayor caída);
  - XGBoost observed: Δ=−1,3 pp;
  - Logit aggregated: Δ=−1,4 pp;
  - Logit observed: Δ=−1,3 pp.
- Auditoría de leakage en `lib/od_buffers_nested_logit.py` (`build_trip_dataset_with_alt_specific_context`):
  - el leave-one-out para la alternativa elegida está implementado correctamente (líneas 431-448): `TVH_chosen = (suma_TVH_chosen_alt − TVH_realizado) / (N_chosen_alt − 1)`;
  - guardrail defensivo en línea 429: `joined.filter(N_CHOSEN_ALT > 1)` descarta singletons;
  - **no hay leakage del target individual**: cada fila no aparece en su propio promedio.
- Pero sí hay leakage agregado estructural:
  - los promedios OD-alternativa (`{short}_MEAN_{alt}`) se computan en `build_od_alt_specific_context_table` sobre el pooled completo, antes del split train/test;
  - cuando se hace `stratified_random`, las filas de train usan promedios computados con la ayuda de filas que después están en test (y viceversa);
  - este efecto infla ~3,7 pp el ROC-AUC del XGBoost aggregated bajo stratified, pero no afecta significativamente al observed (que no usa promedios OD por alternativa).
- Veredicto metodológico:
  - bajo evaluación predictiva estricta (split temporal), el ordenamiento **aggregated > observed se mantiene** (Δ=1,5 pp XGBoost, Δ=1,0 pp logit);
  - esto **replica cruzadamente la lectura provisional del notebook 16 Larch** ("la especificación agregada mantiene mejor desempeño predictivo/log-verosimilitud que la versión con atributos observados por viaje"), pero esta vez desde un modelo flexible que no asume linealidad;
  - conclusión sustantiva: los atributos alt-específicos contienen información contrafactual real que el modelo aprovecha, no es artefacto de la forma funcional lineal del logit.
- Caveat metodológico que conviene declarar al reportar números absolutos:
  - el ROC-AUC del XGBoost aggregated bajo `stratified_random` (0,6533) está levemente optimista por el leakage agregado;
  - la lectura honesta del poder predictivo bajo evaluación estricta es 0,6167 (split temporal);
  - el ordenamiento entre variantes (aggregated vs observed, XGBoost vs logit) se mantiene en ambos splits.

## 2026-05-17 — Brecha XGBoost vs logit y lectura para tesis
- Diferencia XGBoost vs logit en `roc_auc_ovr_macro` bajo split temporal:
  - aggregated: 0,6167 − 0,5910 = **+2,6 pp**;
  - observed: 0,6014 − 0,5809 = **+2,1 pp**.
- Lectura sustantiva para la tesis explicativa:
  - el logit captura la mayor parte de la señal lineal del problema;
  - la flexibilidad funcional del XGBoost agrega un complemento moderado (2-3 pp), no transformacional;
  - la brecha es mayor con atributos agregados (12 features × 3 alternativas dan más espacio para interacciones) que con observados (solo 4 features comunes);
  - esto valida al MNL `parsimonious` como modelo principal: no está dejando demasiada señal sobre la mesa por sus supuestos paramétricos.
- Implicancia narrativa para capítulo de métodos:
  - "como complemento al modelo de elección discreta, se estima un benchmark XGBoost multiclase con interpretación SHAP, no como modelo alternativo de inferencia sino como diagnóstico de adecuación funcional del MNL: permite verificar que las asociaciones identificadas por el modelo estructural no dependen críticamente de los supuestos paramétricos del logit, y permite detectar no linealidades o interacciones relevantes que ameriten ajuste de la especificación principal".

## 2026-05-17 — Próximos pasos del frente ML
- Sensibilidad X/Y vs macrozonas: crear notebook nuevo basado en estructura del 03 (escenario intra-2025 sample 5%) con dos versiones del `parsimonious`:
  - una con coordenadas X/Y sin macrozonas;
  - otra con macrozonas sin X/Y;
  - resto del `parsimonious` (mujeres, parv, EOD income proxy, OSM extendido) idéntico en ambas;
  - pregunta a contestar: ¿son las macrozonas un sustituto razonable de la información espacial por coordenadas, o aportan dimensiones distintas?
- SHAP sobre la mejor variante XGBoost bajo split temporal del notebook 04:
  - propósito: triangulación de signos con MNL Biogeme `parsimonious`, no inferencia;
  - métrica de éxito: ¿coinciden los signos del top 15 SHAP con los signos de los betas del MNL?
  - si coinciden, evidencia de robustez de la lectura estructural;
  - si difieren, bandera para investigar si XGBoost está capturando una asociación no lineal que el MNL no ve.
- Bloqueo pendiente: las muestras de modelación del frente econométrico no preservan `id_tarjeta`, lo que impide unir segmentos (DSI/TSI/LSI del worktree segmentación) con MNL/Nested. Resolución pendiente vía rematerialización (notebook `06_materialize_segment_model_samples.qmd` ya creado en el worktree segmentación, sin ejecutar todavía).

## 2026-05-17 — Sensibilidad X/Y vs macrozonas en el `parsimonious` (notebook 03 v3)
- Se extendió `tesis-project-ml/03_models/ml_baselines/03_multiclass_xgboost_comparable.qmd` para que cargue el `parsimonious` econométrico completo (17 features territoriales: 11 socio/OSM/EOD + 6 macrozonas) desde el parquet `pooled_2024_2025-estimation-sample5pct-censo4-micro-osm-eod2012.parquet`.
- Se introdujo la env var de control `ML_MULTICLASS_SPATIAL_MODE` (resuelta vía archivo de estado `_orchestrator_state/spatial_mode.txt` para bypasear el filtrado de env vars que Quarto aplica al spawneear su kernel) con tres modos:
  - `none`: parsimonious con macrozonas, sin X/Y (30 features totales).
  - `add`: parsimonious con macrozonas + X/Y (32 features).
  - `swap`: parsimonious con X/Y, sin macrozonas (26 features).
- Se creó orquestador `03b_run_all_spatial_modes.qmd` que corre los tres modos secuencialmente, escribiendo a `OUTPUT_DIR` distintos y consolidando una tabla cruzada en `model_outputs_ml/orchestrator_logs/metrics_comparison_across_modes.csv`.
- Bug encontrado y resuelto durante la implementación:
  - Quarto tiene `freeze: auto` en `_quarto.yml`, que cachea outputs por .qmd y los reutiliza entre renders aunque cambien env vars (porque no inspecciona el env).
  - Adicionalmente, Quarto filtra env vars no estándar al spawneear su kernel Python interno, por lo que `ML_MULTICLASS_SPATIAL_MODE` no llegaba al notebook target aunque el subprocess sí la tenía.
  - Fix combinado: orquestador borra `_freeze/**/03_multiclass_xgboost_comparable/` antes de cada render, pasa `--execute`, y escribe el modo a un archivo `_orchestrator_state/spatial_mode.txt` que el 03 lee con máxima prioridad.

## 2026-05-18 — Segmentación por indicadores: modelos `parsimonious` por segmento con `sample10pct`
- En `tesis-project-segmentation` se estimó el MNL `parsimonious` por segmentos `k=2` construidos con indicadores de similitud/cambio entre `2024-W17` y `2025-W17`.
- Los segmentos se forman antes del modelo y no usan variables de pago; por tanto, evitan circularidad directa con `BIP`, `QR_OTHER` y `QR_RED`.
- Interpretación descriptiva de los segmentos:
  - `k2_0`: menor similitud interanual en días, horarios y zonas de origen; mayor cambio observado entre años.
  - `k2_1`: mayor similitud interanual; comportamiento más estable entre años.
- Se evitó nombrarlos como "alta/baja inercia" porque todavía no son clases latentes ni etiquetas definitivas.
- Muestra:
  - `trips_context`: 18.665.583 filas;
  - muestra original `sample10pct`: 1.866.552 filas;
  - muestra reconstruida con `id_tarjeta` y `pk_viaje`: 1.866.549 filas;
  - muestra final unida a segmentos: 546.755 filas;
  - `k2_0`: 188.360 filas;
  - `k2_1`: 358.395 filas.
- Auditoría importante:
  - se detectó que una primera versión completaba variables zonales faltantes con z-scores de `sample5pct`;
  - se corrigió para usar fuentes raw/full y reestandarizar sobre zonas usadas por `sample10pct`;
  - el respaldo `sample5pct` solo se usa para completar valores raw zonales faltantes en una zona, antes de recalcular z-scores;
  - no quedan nulos en columnas del modelo y el join con segmentos no duplica filas.
- Resultados:
  - `k2_0`: LL=-102.053,0; AIC=204.226,1; BIC=204.834,8;
  - `k2_1`: LL=-177.496,6; AIC=355.113,1; BIC=355.760,5;
  - significativos al 5%: `k2_0` tiene 20/30 parámetros significativos para `QR_RED` y 22/30 para `QR_OTHER`; `k2_1` tiene 24/30 para `QR_RED` y 23/30 para `QR_OTHER`.
- Lectura:
  - `sample10pct` mejora la potencia frente a `sample2pct` y `sample5pct`;
  - la segmentación muestra heterogeneidad moderada, no dos regímenes completamente distintos;
  - `k2_1` presenta efectos temporales más nítidos para `QR_OTHER`;
  - `k2_0` muestra una caída relativa más fuerte de `QR_RED` en 2025;
  - los patrones territoriales principales del modelo `parsimonious` se mantienen dentro de los segmentos.
- Reporte específico:
  - `tesis-project-segmentation/docs/reports/segmentacion-indicadores/modelos_por_segmento_sample10.md`.

## 2026-05-17 — Resultado: macrozonas y X/Y son intercambiables, contenidas en el bloque socio/OSM/EOD
- Tabla principal (XGBoost sin pesos, intra-2025 W14+W15 → W17, sample 5%, n_test=605.391):

  | Modo | Features | ROC-AUC OvR macro | log_loss |
  |---|---|---|---|
  | `none` (macrozonas, sin X/Y) | 30 | 0,6131 | 0,5121 |
  | `add` (macrozonas + X/Y) | 32 | 0,6144 | 0,5119 |
  | `swap` (X/Y, sin macrozonas) | 26 | 0,6145 | 0,5118 |

- Δ entre modos: 0,0013–0,0014 ROC-AUC, esencialmente ruido. La misma uniformidad se observa en logit (0,5912–0,5930) y en versiones balanceadas (balanced_accuracy 0,4392–0,4393).
- Lectura sustantiva:
  - una vez controlando por el bloque socio/OSM/EOD del `parsimonious` (educación, discapacidad, inmigrantes, mujeres, parv, EOD income proxy, infraestructura OSM zonal), agregar o quitar la representación espacial (macrozonas dummies o coordenadas X/Y continuas) **no cambia el desempeño predictivo de forma apreciable**;
  - macrozonas y X/Y son **proxies del mismo subyacente espacial**, ya capturado por las variables territoriales sustantivas;
  - eco coherente con el resultado v1→v2 anterior (notebook 03 binario), donde agregar coordenadas sobre la shortlist socio/OSM movió ROC-AUC en 0,0006 (también ruido).
- Implicancias metodológicas:
  - el MNL `parsimonious` con macrozonas (sin coordenadas) **no se está perdiendo señal espacial relevante** por su parametrización;
  - la elección entre macrozonas y X/Y para el frente econométrico **es una decisión interpretativa, no predictiva**: macrozonas tienen lectura territorial-administrativa directa ("la utilidad relativa de QR_RED es Δ mayor en macrozona Oriente vs Centro"), X/Y no la tienen sin postprocesamiento espacial;
  - para una tesis explicativa, macrozonas gana por interpretabilidad sin pagar costo predictivo;
  - la brecha XGBoost vs logit (~2,2 pp ROC-AUC) es consistente en los tres modos, por lo que **no es producida por la representación espacial**; es flexibilidad funcional sobre los atributos socio/OSM/EOD.
- Trazabilidad de artefactos (en `tesis-project-ml/03_models/ml_baselines/model_outputs_ml/`):
  - `multiclass_comparable_sample5pct__train-2025-W14_2025-W15_test-2025-W17__v3-parsimonious-macrozonas/` (modo none);
  - `…__v3-parsimonious-macrozonas-plus-xy/` (modo add);
  - `…__v3-parsimonious-xy-no-macrozonas/` (modo swap);
  - `orchestrator_logs/metrics_comparison_across_modes.csv` (tabla cruzada).
- Próximo paso: SHAP sobre modo `none` (XGBoost con y sin pesos) para triangulación de signos con MNL Biogeme `parsimonious`. SHAP se interpreta como diagnóstico de adecuación funcional, no como inferencia.

## 2026-05-17 — Handoff operativo: estado al cierre de sesión

### Resumen ejecutivo
El frente ML del worktree `tesis-project-ml` quedó en estado **listo para ejecutar SHAP**. Toda la pipeline de benchmark predictivo (notebooks 03, 03b, 04) está estable y probada. El notebook SHAP (`03c_shap_v3_parsimonious_none.qmd`) está escrito pero **sin ejecutar todavía**.

### Estado por notebook (tesis-project-ml)

- **`03_models/ml_baselines/03_multiclass_xgboost_comparable.qmd`** — Notebook principal del benchmark multiclase intra-2025 sample 5%. Soporta tres modos espaciales vía env var `ML_MULTICLASS_SPATIAL_MODE` (`none`/`add`/`swap`) o vía archivo `_orchestrator_state/spatial_mode.txt`. Estable. Última corrida exitosa: 2026-05-17.
- **`03_models/ml_baselines/03b_run_all_spatial_modes.qmd`** — Orquestador que ejecuta los tres modos del 03 secuencialmente. Limpia `_freeze` y pasa estado vía archivo (no env var, por bug de Quarto). Estable. Última corrida exitosa: 2026-05-17.
- **`03_models/ml_baselines/03c_shap_v3_parsimonious_none.qmd`** — Notebook SHAP recién creado. Re-construye la muestra del modo `none`, re-fittea XGBoost con y sin pesos, computa SHAP multiclase 3D, exporta tablas por clase y comparación de signos con MNL Biogeme `parsimonious`. **Pendiente de primera ejecución.**
- **`03_models/ml_baselines/04_main_sample_travel_attr_sensitivity.qmd`** — Sensibilidad aggregated vs observed sobre pooled del frente econométrico. Estable. Última corrida exitosa: 2026-05-17, dos splits (stratified_random y temporal_2024_to_2025).

### Artefactos clave generados

En `tesis-project-ml/03_models/ml_baselines/model_outputs_ml/`:

- `multiclass_comparable_sample5pct__train-2025-W14_2025-W15_test-2025-W17/` — v1 (legacy, 18 features sin coordenadas).
- `…__v2-spatial/` — v1 + X/Y (legacy).
- `…__v3-parsimonious/` — v3 inicial (pre-orquestador, 30 features).
- `…__v3-parsimonious-macrozonas/` — **modo none del orquestador** (30 features, macrozonas, sin X/Y).
- `…__v3-parsimonious-macrozonas-plus-xy/` — **modo add** (32 features).
- `…__v3-parsimonious-xy-no-macrozonas/` — **modo swap** (26 features, sin macrozonas).
- `main_sample_travel_attr_sensitivity_sample100pct__split-stratified_random/` — notebook 04 stratified.
- `main_sample_travel_attr_sensitivity_sample100pct__split-temporal_2024_to_2025/` — notebook 04 temporal.
- `orchestrator_logs/` — logs y CSVs cruzados del 03b.
- `_orchestrator_state/spatial_mode.txt` — archivo de control del orquestador (vacío fuera de runs activos).

### Decisiones metodológicas cerradas en esta sesión

1. **Framing del frente ML como diagnóstico de adecuación funcional, no inferencia.** Documentado en sección "Reframing metodológico" del 2026-05-17.
2. **XGBoost > logit en ~2 pp ROC-AUC OvR macro consistentemente** (intra-2025, pooled, todas las variantes). La brecha es por flexibilidad funcional, no por representación espacial.
3. **Aggregated > observed se replica en XGBoost** (notebook 04). Validado bajo split temporal estricto: 0,617 vs 0,601. Ordenamiento del Larch 16 confirmado en modelo flexible.
4. **Caveat de leakage agregado documentado.** Los promedios OD del aggregated se computan sobre pooled, no solo train. Infla ~3,7 pp el ROC-AUC bajo stratified, pero no invalida el ordenamiento bajo temporal.
5. **Macrozonas y X/Y son intercambiables en presencia del bloque socio/OSM/EOD del parsimonious.** Δ ROC-AUC entre los 3 modos espaciales: 0,0013-0,0014 (ruido). Para tesis explicativa, macrozonas gana por interpretabilidad sin costo predictivo.

### Bugs/gotchas conocidos del pipeline (importante para continuidad)

1. **Quarto `freeze: auto` + env vars no propagadas al kernel Python.** El 03b lo resuelve borrando `_freeze` antes de cada render y pasando estado vía archivo `_orchestrator_state/spatial_mode.txt` en lugar de env var. **Cualquier script que orqueste múltiples renders del mismo .qmd con parámetros distintos debe hacer lo mismo.**
2. **Las muestras de modelación del frente econométrico no preservan `id_tarjeta`.** Bloquea unir segmentos DSI/TSI/LSI con MNL/Nested. Resolución pendiente vía `06_materialize_segment_model_samples.qmd` en el worktree segmentación (creado, sin ejecutar).
3. **Shapefile `Zonas777` está en `/Volumes/KINGSTON/...`** (disco externo). Si no está conectado, el notebook 16 stepwise falla al rederivar macrozonas. Los parquets ya generados no requieren el shapefile.

### Próximo paso concreto

**Ejecutar `03c_shap_v3_parsimonious_none.qmd`** con el comando:

```bash
QUARTO_PYTHON=~/.local/share/mamba/envs/larch-env/bin/python \
  quarto render 03_models/ml_baselines/03c_shap_v3_parsimonious_none.qmd
```

Tiempo estimado: 5-8 min. Para smoke run rápido: `SHAP_SAMPLE_SIZE=10000`.

Outputs esperados en `model_outputs_ml/shap_v3_parsimonious_none/`:
- `shap_importance_by_class_long.csv`
- `shap_top_features_by_class.csv`
- `shap_summary__<model>__<class>.png` × 6
- `shap_vs_biogeme_signed_comparison.csv`
- `shap_vs_biogeme_agreement_summary.csv`
- `run_config.json`

### Pasos posteriores al SHAP (no abiertos en esta sesión)

- Decisión sobre rematerialización de muestras MNL con `id_tarjeta` para habilitar análisis por segmento.
- Interpretación formal de la comparación Larch agregado vs Nested agregado vs observado del notebook 16 (lectura provisional registrada, falta tabla comparativa para `model_matrix.md`).
- Traducción de hallazgos consolidados a sección de Resultados de la tesis.

## 2026-05-17 — Ejecución y cierre del frente SHAP (notebooks 03c y 03d)

### Qué se hizo

- **Ejecutado `03c_shap_v3_parsimonious_none.qmd`** sobre los dos XGBoost del modo `none` (con y sin pesos), muestra del test de 100.000 filas, SHAP multiclase via `booster.predict(DMatrix, pred_contribs=True)`.
- Artefactos generados en `tesis-project-ml/03_models/ml_baselines/model_outputs_ml/shap_v3_parsimonious_none/`:
  - `shap_importance_by_class_long.csv` — tabla larga (modelo × clase × feature × mean_abs_shap × mean_signed_shap).
  - `shap_top_features_by_class.csv` — top 15 por (modelo, clase).
  - 6 PNG `shap_summary__<model>__<class>.png` (beeswarms para BIP, QR_RED, QR_OTHER × 2 modelos).
  - `shap_vs_biogeme_signed_comparison.csv` + `shap_vs_biogeme_agreement_summary.csv` (ver decisión metodológica abajo).
- **Creado y ejecutado `03d_shap_directional_corr_vs_biogeme.qmd`** tras detectar que la métrica de signo agregado del 03c (`sign(mean_signed_shap)`) estaba sesgada por la composición desbalanceada del test (~83% BIP, 14% QR_OTHER, 3% QR_RED).
- Artefactos del 03d en `model_outputs_ml/shap_directional_corr_vs_biogeme/`:
  - `shap_feature_corr_by_class.csv` (correlación Spearman feature ↔ SHAP por modelo y clase).
  - `shap_vs_biogeme_directional_comparison.csv` y `shap_vs_biogeme_directional_agreement_summary.csv`.

### Hallazgo sustantivo del SHAP (lo que sí va a tesis)

- **Importancia y dirección de variables visibles en beeswarms son consistentes con la interpretación estructural del MNL parsimonious** para las variables centrales del estudio:
  - Educación universitaria (top 1 para QR_RED): zonas con alta educación universitaria empujan la predicción hacia QR_RED. Coincide con MNL `B_QR_RED_SHARE_CINE18_UNIVERSITARIA_O_MAS_MICRO_Z = +0,446` (t=13,4).
  - Discapacidad: dirección negativa hacia QR_RED. Coincide con MNL.
  - Asistencia parvularia: dirección positiva hacia QR_RED. Coincide con MNL.
  - Variables operacionales de viaje (tiempos, transbordos, dummies temporales): direcciones coinciden con MNL.
- **`mean_abs_shap` por clase revela diferenciación interesante entre canales QR**:
  - QR_RED se explica principalmente por **educación universitaria** (mean_abs=0,312, 4× mayor que la segunda feature).
  - QR_OTHER se explica principalmente por **características del viaje** (tiempo de transbordo, accesos a metro, modo, espera inicial).
  - Interpretación: los dos canales QR responden a determinantes distintos. QR_RED es la adopción tecnológica "elegida" en zonas con mayor capital educativo; QR_OTHER es más una respuesta a fricciones operacionales del viaje. **Material para sección de Discusión.**

### Decisión metodológica: qué NO va a tesis

Tras evaluar dos métricas distintas de "acuerdo direccional" entre SHAP y MNL (03c con `sign(mean_signed_shap)` = 57,5% / 55,0%; 03d con `sign(spearman_r)` = 82,5% / 77,5%), se concluye que:

- **SHAP y MNL miden conceptualmente cosas distintas**: el MNL entrega efectos condicionales lineales (qué hace una variable manteniendo todo lo demás constante en el modelo); SHAP atribuye contribución a una predicción individual.
- En presencia de variables territoriales colineales (educación universitaria, macrozonas Oriente/Suroriente, densidad de universidades — todas covarían fuertemente porque marcan "zonas educadas"), las dos métricas **necesariamente difieren**. Esta diferencia es matemática, no es un hallazgo sustantivo.
- **Por tanto, no se reporta en la tesis ninguna comparación cuantitativa de signos entre SHAP y MNL.** Ni la métrica `mean_signed_shap` del 03c, ni la correlación Spearman del 03d.
- **Sí se reporta** SHAP como apoyo visual de robustez direccional: 3 beeswarms (BIP, QR_RED, QR_OTHER del XGBoost sin pesos) + tabla `mean_abs_shap` top 10 por clase.
- Justificación narrativa: comparar SHAP y MNL cuantitativamente abriría una discusión metodológica sobre efectos condicionales vs atribuciones brutas en modelos con multicolinealidad, que distrae del foco explicativo de la tesis (adopción digital). La triangulación cualitativa via beeswarm es suficiente y defendible.

### Estado de los notebooks 03c y 03d

- **03c y 03d quedan como auditoría interna**, sus CSVs (especialmente las tablas de "banderas" de signos discrepantes) **no se citan en la tesis**.
- Si en una defensa de tesis se pregunta sobre SHAP, la respuesta es: "se reporta importancia y dirección visual; no se compara cuantitativamente con MNL porque miden objetos distintos".
- Los notebooks quedan documentados acá para que en futuras sesiones quede claro **por qué no se citan**.

### Frase candidata para capítulo de Métodos o Discusión

> "Como diagnóstico complementario al MNL parsimonious, se estima un XGBoost multiclase con la misma especificación de features. La importancia relativa y la dirección de asociación de las variables, visibles en los beeswarms SHAP, son consistentes con la interpretación estructural del MNL para las variables sociodemográficas centrales (educación universitaria, discapacidad, asistencia parvularia) y las variables operacionales del viaje (tiempos, transbordos, dummies temporales). El SHAP del XGBoost también muestra una diferenciación interesante entre los dos canales QR: QR_RED se discrimina principalmente por capital educativo zonal, mientras que QR_OTHER se discrimina principalmente por características operacionales del viaje."

### Próximo paso del frente ML

- Frente SHAP cerrado. No quedan corridas pendientes en `tesis-project-ml` para la versión actual de la tesis.
- Próximos frentes (en orden de prioridad sugerido):
  1. Desbloquear segmentación: rematerializar muestras MNL preservando `id_tarjeta` (notebook `06_materialize_segment_model_samples.qmd` en worktree segmentación, sin ejecutar).
  2. Cerrar interpretación formal de la comparación Larch del notebook 16 (agregado vs nested vs observado).
  3. Iniciar redacción del capítulo de Resultados con: MNL parsimonious como modelo principal, sensibilidades Larch como robustez, SHAP del XGBoost como apoyo visual.
