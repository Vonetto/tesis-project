# Rediseño A Nivel Tarjeta / Usuario

## Objetivo

Reformular los frentes main econometrico, ML y segmentacion desde observaciones a nivel viaje hacia observaciones a nivel `id_tarjeta`, usando `id_tarjeta` como proxy operacional de usuario.

## Decisiones Ya Tomadas

- La unidad de analisis candidata pasa a ser `id_tarjeta`.
- `id_tarjeta` se tratara como proxy de usuario, aclarando que una persona podria tener mas de una tarjeta y eso no es observable.
- El foco conceptual principal sera: que perfiles de uso se asocian a QR.
- Se probara target binario `QR vs BIP` como candidato principal inicial.
- Se probara target multiclase `BIP / QR_RED / QR_OTHER` como extension/sensibilidad.
- La residencia inferida desde `PROPOSITO == HOGAR` sigue siendo la zona correcta para variables socioeconomicas.
- Se usara todo el historial temporal disponible por tarjeta.
- Se filtraran usuarios/tarjetas demasiado ocasionales, porque el foco es adopcion y no uso incidental.
- Para infraestructura/oferta, se usaran zonas frecuentes de actividad: al menos la zona de origen mas frecuente y potencialmente las dos zonas mas frecuentes para aproximar casa y trabajo/estudio.
- Para el modelo principal con covariables socioeconomicas por residencia, se usaran tarjetas con `home_confidence == "alta"` como muestra principal; `alta+media` queda como sensibilidad.
- El universo principal preliminar sera `clean + home_alta + n_viajes >= 3`; `n_viajes >= 5`, `n_viajes >= 10` y `n_home_dest_trips_card >= 3` quedan como sensibilidades.
- `share_trips_2025` o flags de cohorte temporal deberan entrar como control obligatorio en modelos posteriores.
- Para variables agregadas de uso, se usara una lista reducida por colinealidad: `hora_mean`, `hora_std`, `share_lab_pm`, `share_lab_pt`, `share_no_lab`, `share_trips_with_transfer`, `t_vehiculo_mean_min`, `t_espera_ini_mean_min`, `share_trips_solo_metro`, `share_trips_metro_bus`.
- En variables modales, `share_trips_solo_bus` queda como base implicita; `share_trips_solo_metro` debe leerse como Metro/MetroTren.
- Para el modelo econometrico, no se usaran coordenadas `X/Y`; la especificacion geografica principal usara `home_macrozone + origin_top1_macrozone`.
- Como sensibilidades geograficas econometricas, se probaran: solo `home_macrozone`, solo `origin_top1_macrozone`, agregar `origin_zone_top1_share`, agregar `origin_zone_entropy`, y agregar `origin_top2_macrozone`.
- Para socioeconomia residencial, el set econometrico candidato sera educacion, D+E proxy, edad, discapacidad, inmigrantes y asistencia parvular; `mujeres` raw queda fuera del baseline por outlier y solo se probara winsorizada como sensibilidad.
- El binario `QR vs BIP` queda como sintesis principal simple, pero el multiclase queda justificado como analisis de heterogeneidad porque QR_RED y QR_OTHER tienen perfiles socioeconomicos distintos.
- OSM/oferta queda fuera del main econometrico inicial; se probara como sensibilidad acotada con `origin_top1_university_high_dummy` y `origin_top1_school`.
- Bloque 7 de separabilidad queda como hallazgo exploratorio/hipotesis: `QR_OTHER` parece conductual-temporal; `QR_RED` parece socio-geografico.
- Para el main econometrico, se evitara una grilla grande de sensibilidades. Se usara un main parsimonioso y pocas sensibilidades acotadas por bloque.
- Para ML, se permitira un set amplio con variables correlacionadas; la interpretacion se hara por familias/bloques, no solo por importancia individual.
- Para ML, si se podran usar coordenadas `X/Y`; el set espacial completo sera `home_macrozone`, `origin_top1_macrozone`, `origin_top2_macrozone`, `activity_top1_macrozone`, `activity_top2_macrozone`, `origin_top1_lon/lat`, `origin_top2_lon/lat`, `activity_top1_lon/lat`, `activity_top2_lon/lat`, `origin_zone_top1_share`, `origin_zone_top2_share`, `origin_zone_entropy`, `activity_zone_top1_share`, `activity_zone_entropy`.
- GPBoost queda como sensibilidad espacial frente a XGBoost.
- Para segmentacion, la factorizacion matricial se explorara como perfiles latentes de movilidad a nivel tarjeta; el profesor tenia en mente NMF.
- En NMF basico, agregar dummies de macrozona porque `X/Y` no se agregan naturalmente a matrices no negativas de patron.
- El EDA supervisado de bloques 7G-7L queda cerrado como exploracion de seleccion de variables: accesibilidad BIP y oferta/demanda aportan poco incrementalmente; ruta/inercia, hibridas y franjas etarias aportan senal acotada, especialmente para heterogeneidad `QR_RED` vs `QR_OTHER`.
- La especificacion binaria `QR vs BIP` se mantiene como candidata principal por robustez, pero debe reportarse que la separacion predictiva es moderada y que mezcla mecanismos distintos.
- La heterogeneidad `QR_RED` vs `QR_OTHER` debe quedar como analisis complementario/sensibilidad, porque `QR_RED` parece tener perfil territorial/socioeducativo distinto pero es una clase minoritaria.
- Antes de NMF/SVD se debe construir primero una matriz usuario-feature supervisada final para modelos logit/ML; la matriz de movilidad para factorizacion es un frente posterior y no debe incluir el target.

## Preguntas Abiertas Para Profesor

- Definir empiricamente el umbral minimo de viajes por tarjeta.
- Definir exactamente como construir las dos zonas frecuentes: top-2 globales, top origen/destino, o top por periodo AM/PM.
- Definir como manejar evaluacion temporal en ML considerando mezcla 2024-2025 y crecimiento QR.
- Definir variaciones de NMF una vez construido el panel/matrices.

## Hitos

1. Diseñar schema del panel `id_tarjeta`. ✅
2. Construir smoke artifact `active` (`2024-W17` + `2025-W17`). ✅
3. Auditar conflictos, cobertura y umbrales del smoke. ✅
4. Extender bridge `proposito`/residencia a scope `interannual_ml`. ✅
5. Construir artefacto base reproducible `user_level_payment_panel` para scope extendido. ✅
6. Ejecutar EDA obligatorio del panel antes de modelar. ✅ Bloques 1-7L documentados.
7. Decidir umbral minimo de viajes y variables finales a partir del EDA. ✅ Universo principal: `clean + home_alta + n_viajes >= 3`.
8. Construir matriz usuario-feature final para modelos supervisados (`logit_main`, sensibilidades, `ml_main`, `ml_wide`, `binary_ml_main`). ✅
9. Probar ML a nivel tarjeta con XGBoost como benchmark final reproducible. Siguiente.
10. Probar modelos econometricos a nivel tarjeta.
11. Ejecutar EDA de matrices de movilidad antes de factorizacion.
12. Probar matrices de movilidad y NMF/SVD para segmentacion.
13. Integrar resultados en tesis como nuevo enfoque principal.
14. Reabrir EDA como fase de ingenieria de features conductuales para mejorar
    `QR vs BIP` antes de cerrar benchmark ML final. En curso.

## EDA Obligatorio Del Panel

Antes de modelar, revisar:

- Distribucion del target `BIP / QR_RED / QR_OTHER` y `QR vs BIP`.
- Distribucion de `n_viajes` por tarjeta y por clase.
- Tabla de sensibilidad por umbral: `n_viajes >= 1, 3, 5, 10`.
- Cobertura de residencia y confianza residencial.
- Distribucion de primera/ultima fecha observada, semanas activas y proporcion de viajes 2025.
- Top-1 y top-2 zonas frecuentes, y relacion con residencia.
- Distribucion, missing y outliers de variables agregadas.
- QR share descriptivo por macrozona, educacion, edad, ingreso proxy y `n_viajes`.
- Correlaciones entre variables socioeconomicas, territoriales y de uso.

## EDA Obligatorio De Matrices

Antes de NMF/SVD, revisar para cada matriz candidata:

- Numero de tarjetas y columnas.
- Porcentaje de ceros / sparsity.
- Distribucion de suma por fila.
- Columnas muy raras o dominantes.
- Tarjetas con una sola celda activa.
- Comparacion entre conteos brutos, proporciones por tarjeta y transformaciones alternativas.

## EDA De Ingenieria De Features Conductuales

Usar el mismo notebook `02_eda/eda_user_level_panel.qmd`, pero como fase nueva
posterior al screening 1-7L. El objetivo ya no es auditar fuentes, sino diseñar
variables que representen comportamiento de movilidad observable.

Arquitectura de trabajo:

1. Registrar hipotesis antes de implementar:
   `feature_pack | hipotesis | variables candidatas | fuente | caveat |
   prioridad | metrica esperada`.
2. Construir artefactos intermedios por paquete, no meter todo directamente en
   `build_user_model_matrix.py`.
3. Unir solo los paquetes prometedores a la matriz final y exponerlos como
   feature sets versionados.
4. Evaluar primero con EDA supervisado rapido y despues con benchmark
   incremental en `run_user_ml_benchmark.py`.

Candidatas a priorizar:

- Intensidad y frecuencia: viajes por dia activo, viajes por semana activa,
  concentracion de viajes en pocos dias y baja intensidad reciente.
- Regularidad temporal: dispersion horaria, uso punta/valle, uso fin de semana
  y diferencias AM/PM.
- Rutina espacial: concentracion OD, diversidad OD, estabilidad de origen y
  destinos frecuentes.
- Modalidad/red: solo bus, solo Metro/MetroTren, Metro-Bus, transbordos,
  exposicion a zonas/estaciones de Metro.
- Recencia/cohorte: solo 2025, cambios 2024-2025, recencia x baja intensidad.
- Ruta/inercia: diversidad de servicios, early/late RCS e interacciones
  conductuales acotadas.

Feature packs iniciales:

- `rhythm_pack`: textura temporal de uso. Ejemplos: viajes por dia activo,
  viajes por semana activa, concentracion de actividad, gaps entre dias activos,
  burstiness y steady-use score.
- `routine_pack`: rutina vs exploracion. Ejemplos: repeticion OD-franja-modo,
  commuter-like score, exploration score, estabilidad de origen/destino y
  share de viajes fuera de top zonas/OD.
- `context_residual_pack`: desviacion respecto a usuarios comparables.
  Ejemplos: percentil de intensidad dentro de zona hogar, `hora_std` residual
  vs zona/macro, share Metro residual vs zona de origen, route entropy residual.
- `friction_pack`: friccion efectiva de BIP condicionada por comportamiento.
  Ejemplos: baja accesibilidad BIP x bus-only, baja accesibilidad x baja
  intensidad, exposicion Metro vs no uso Metro, carga BIP cercana ponderada por
  zonas realmente usadas.
- `adoption_timing_pack`: cambio interanual 2025 vs 2024. Ejemplos:
  crecimiento log de viajes/dias/semanas activas, cambios en hora media,
  dispersion horaria, uso punta, mezcla modal, transferencias y diversidad de
  zonas.
- `prototype_pack`: representaciones latentes/perfiles. Ejemplos: distancias a
  prototipos commuter/ocasional/explorador/metro-heavy, clusters conductuales o
  componentes NMF usados como scores supervisados posteriores.
- `daily_tour_pack`: estructura intra-dia de movilidad. Ejemplos: dias de 2
  viajes, dias 3+, dias que cierran en la zona inicial, ida-vuelta aproximada,
  mismo OD no-direccional, mezcla modal y anclaje punta AM/PM.

Artefactos intermedios esperados:

- `user_behavior_rhythm_features_<suffix>.parquet`
- `user_behavior_routine_features_<suffix>.parquet`
- `user_behavior_daily_tour_features_<suffix>.parquet`
- `user_context_residual_features_<suffix>.parquet`
- `user_friction_features_<suffix>.parquet`
- `user_behavior_adoption_timing_features_<suffix>.parquet`
- `user_behavior_prototype_features_<suffix>.parquet`

Feature sets posteriores:

- `full_plus_rhythm`
- `full_plus_routine`
- `full_plus_context_residual`
- `full_plus_friction`
- `full_plus_behavior_all`

Regla de entrada a matriz final:

- No agregar features a ciegas. Cada candidata debe tener formula, fuente,
  caveat de missing/leakage, lectura esperada y prueba incremental.
- Priorizar primero `rhythm_pack` y `context_residual_pack`, porque son los mas
  distintos de los bloques ya probados y atacan directamente el problema de
  senal moderada en variables brutas.
- Una familia entra al builder solo si muestra salud de dato razonable y senal
  descriptiva para `QR vs BIP`; `QR_RED vs QR_OTHER` queda como diagnostico
  secundario, no como criterio principal.
- El benchmark incremental debe comparar al menos contra `usage_cohort` y
  `full_contract`; metricas prioritarias: PR-AUC, lift@10 y ROC-AUC.

Estado `rhythm_pack`:

- Builder creado: `scripts/audits/build_user_behavior_rhythm_features.py`.
- Artefacto principal construido:
  `tmp/audits/user_level_redesign/user_behavior_rhythm_features_interannual_ml.parquet`.
- EDA reproducible agregado al Bloque 8 del notebook con setup, tabla por
  target, ranking univariado, bins y probe tree/logit.
- Pendiente: decidir si integrar `rhythm_pack` a `build_user_model_matrix.py`
  como `full_plus_rhythm` despues de revisar resultados del Bloque 8 renderizado.

Estado `daily_tour_pack`:

- Builder creado: `scripts/audits/build_user_daily_tour_features.py`.
- EDA reproducible agregado como Bloque 8D en
  `02_eda/eda_user_level_panel.qmd`.
- Integrado al builder de matriz principal mediante
  `full_plus_rhythm_context_routine_daily_tour`, usando seleccion `main`
  acotada de `routine_pack` y `daily_tour_pack`.
- Proxima validacion: reconstruir matrices y correr XGB primero en
  `interannual_ml clean alta n3`.

Estado `friction_pack`:

- Integrado al builder de matriz principal como variables derivadas fijas
  `fric_*`.
- Feature sets disponibles:
  `full_plus_rhythm_context_friction` y
  `full_plus_rhythm_context_routine_daily_tour_friction`.
- EDA reproducible agregado como Bloque 8E en
  `02_eda/eda_user_level_panel.qmd`.
- Proxima validacion: reconstruir `alta_n3`, correr Bloque 8E y solo despues
  lanzar XGB si la salud del bloque es razonable.

Estado `adoption_timing_pack`:

- Builder creado: `scripts/audits/build_user_adoption_timing_features.py`.
- Integrado al builder de matriz principal mediante:
  `full_plus_rhythm_context_adoption_timing` y
  `full_plus_rhythm_context_routine_daily_tour_adoption_timing`.
- EDA reproducible agregado como Bloque 8F en
  `02_eda/eda_user_level_panel.qmd`.
- Proxima validacion: construir artifact `interannual_ml`, reconstruir
  `alta_n3`, correr Bloque 8F y decidir si merece XGB contra el baseline
  `routine_daily_tour`.

Estado `prototype_pack`:

- Builder creado: `scripts/audits/build_user_prototype_features.py`.
- No usa clustering ni target. Construye scores determinísticos como promedios
  de percentiles firmados de variables de `routine_pack`, `daily_tour_pack` y
  `rhythm_pack`.
- Scores principales:
  `proto_commuter_peak_score`, `proto_late_return_score`,
  `proto_low_complexity_score`, `proto_explorer_score`,
  `proto_routine_repeater_score`, `proto_multimodal_score`.
- Integrado al builder de matriz mediante:
  `full_plus_rhythm_context_prototype` y
  `full_plus_rhythm_context_routine_daily_tour_prototype`.
- EDA reproducible agregado como Bloque 8G en
  `02_eda/eda_user_level_panel.qmd`.
- Proxima validacion: construir artifact `interannual_ml`, reconstruir
  `alta_n3`, correr Bloque 8G y decidir si merece XGB contra
  `routine_daily_tour`.

## No Hacer Todavia

- No reescribir notebooks 16/17 o ML completos hasta validar el panel base.
- No descartar totalmente resultados a nivel viaje; se mantendran como analisis exploratorio historico.
- No usar QR/BIP dentro de la factorizacion matricial si el objetivo es segmentacion no supervisada.

## Plan Benchmark ML Final

Objetivo: pasar del diagnostico de techo predictivo a un benchmark ML final,
reproducible y comparable, usando las matrices user-level canonicas.

Arquitectura:

- Crear `scripts/audits/run_user_ml_benchmark.py`.
- Mantener entrenamiento/evaluacion en script, no en notebook, para evitar
  estado oculto y poder repetir universos/splits.
- Dejar notebooks/QMD solo para resumen visual posterior: tablas finales,
  curvas lift/calibracion y SHAP si corresponde.
- Outputs en `tmp/audits/user_level_redesign/ml_benchmark/`.
- Modelos soportados baseline: `xgb` y `logit`. `logit` usa imputacion mediana
  y estandarizacion ajustadas dentro de cada fold.

Universos iniciales:

- Principal: `alta_n3`.
- Sensibilidades: `alta_n3_home3`, `alta_n10`, `alta_media_n3`.
- Splits: `random` para todos; `grouped` solo para `alta_n3` y
  `alta_n3_home3`.

Tasks:

- `binary`: QR vs BIP.
- `multiclass`: BIP / QR_OTHER / QR_RED.
- `both`: corre ambas tasks con folds y artefactos separados.

Feature sets:

- `usage`: bloque conductual.
- `usage_cohort`: alias explicito para el bloque conductual + cohorte
  temporal; `usage` se mantiene como alias por compatibilidad.
- `usage_pure`: bloque conductual excluyendo cohorte temporal.
- `usage_socio_geo`: uso + socio + geografia.
- `usage_route`: uso + route inertia.
- `full_contract`: union completa del JSON de feature sets.
- `no_structural_missing`: `full_contract` sin variables RCS/early-late con
  missing estructural alto.
- Sensibilidades opcionales: `no_bip`, `no_offer`, `no_hybrid`, si se requiere
  replicar ablations en formato benchmark.

Metric blocks:

- `ranking`: ROC-AUC, PR-AUC, lift@5%, lift@10%, precision@5%,
  precision@10%.
- `probability`: log-loss, brier score, calibracion por deciles.
- `classification`: balanced accuracy, macro-F1 y matriz de confusion. Es
  secundaria por desbalance y umbrales arbitrarios.
- `multiclass_ovr`: AUC/PR-AUC/base rate por clase, especialmente QR_OTHER y
  QR_RED.
- Default: `all`.

Optuna:

- Implementar como modo opcional, no requisito para el primer benchmark.
- Primero correr baseline reproducible con hiperparametros fijos.
- Tuning inicial solo en `alta_n3` y `full_contract`.
- Objetivos candidatos:
  - binario: `pr_auc` o combinacion `0.5 * roc_auc + 0.5 * pr_auc`.
  - multiclase: `macro_ovr_auc` o promedio de PR-AUC de QR_OTHER y QR_RED.
- Luego congelar hiperparametros y evaluar sensibilidades de universo/split.
  No tunear cada universo al principio para no confundir seleccion de muestra
  con optimizacion.

Artefactos esperados:

- `runs.csv`: metadata de cada corrida.
- `metrics.csv`: metricas por run/task/split/feature_set/model.
- `oof_predictions_<run_id>.parquet`: predicciones out-of-fold.
- `lift_<run_id>.csv`.
- `calibration_<run_id>.csv`.
- `feature_importance_<run_id>.csv`.
- `family_importance_<run_id>.csv`.
- `optuna_trials_<run_id>.csv` y `config_<run_id>.json` cuando aplique.

## Rhythm Pack En Matriz ML

Estado: implementado y corrido en XGB para universos principales.

Cambios:

- `build_user_model_matrix.py` ahora requiere y une
  `user_behavior_rhythm_features_<scope>.parquet`.
- Se agregaron feature sets `logit_plus_rhythm`, `ml_plus_rhythm`,
  `binary_ml_plus_rhythm` y `full_plus_rhythm`.
- `run_user_ml_benchmark.py` mantiene `full_contract` como baseline pre-rhythm
  y solo incorpora rhythm al pedir un feature set explicito.

Resultado:

- `full_plus_rhythm` mejora de forma pequena pero consistente sobre
  `full_contract` donde existe comparacion directa.
- El mayor salto viene de universos con mayor soporte conductual:
  `alta_n10` y `alta_n3_home3`.
- Mantener como benchmark enriquecido, no como salto predictivo principal.

Siguiente verificacion opcional:

- Correr `logit_plus_rhythm` en `alta_n3` solo como comparacion interpretable.
- Revisar importancias/family importance de `rhythm_alta_n3_full`.
- Continuar con `context_residual_pack` antes de integrar mas bloques al
  builder.

Decision logit:

- Main `logit_plus_rhythm`: mantener solo 6 variables de ritmo:
  `rhythm_mean_gap_active_days`, `rhythm_trips_per_span_day`,
  `rhythm_active_day_density_span`, `rhythm_trips_per_active_week`,
  `rhythm_daily_hhi`, `rhythm_has_gap`.
- Sensibilidad: si se requiere, crear una sola `logit_plus_rhythm_wide` con el
  paquete completo, evitando muchas variantes pequenas.

## Context Residual Pack EDA

Estado: bloque 8B preparado en `02_eda/eda_user_level_panel.qmd`, pendiente de
ejecucion por el usuario.

Objetivo:

- Evaluar si el comportamiento relativo al contexto residencial/origen agrega
  señal sobre `rhythm_pack`.
- Evitar interpretar el score compuesto como final si sus componentes no tienen
  señal propia.

Criterio de avance:

- Pasar salud de datos: missing razonable y grupos contextuales suficientes.
- Mostrar señal descriptiva en `QR vs BIP`, no solo `QR_RED vs QR_OTHER`.
- En probe, mejorar `baseline_plus_rhythm`, no solo `baseline_continuous`.
- Si sobrevive, materializar como artefacto separado y luego integrar al
  builder con feature set explicito `full_plus_context_residual`.

Resultado:

- Se materializo exploratoriamente en `build_user_model_matrix.py`.
- Feature set principal: `full_plus_rhythm_context_residual`.
- Sensibilidad: `full_plus_rhythm_context_residual_sensitivity`.
- Caveat: no es fold-safe todavia; usar para benchmark exploratorio y luego
  decidir si vale la pena implementar transformacion CV-safe.

Siguiente verificacion:

- Reconstruir matriz `alta_n3`.
- Correr XGB con `full_plus_rhythm_context_residual`.
- Comparar contra `full_plus_rhythm` y no contra `full_contract` directamente.
- Si mejora materialmente, repetir en `alta_n10` y `alta_n3_home3`.

## Routine Pack EDA

Estado: implementado como artefacto y bloque EDA, pendiente de ejecucion por el
usuario.

Objetivo:

- Capturar patrones de rutina que requieren volver a viajes, pero mantener la
  unidad final usuario/tarjeta.
- Evaluar si combos `OD x franja x modo` agregan senal sobre
  `rhythm_pack + context_residual_pack`.

Artefactos:

- `scripts/audits/build_user_routine_features.py`
- `02_eda/eda_user_level_panel.qmd`, bloques `8.9-8.10`.
- Salida esperada:
  `tmp/audits/user_level_redesign/user_behavior_routine_features_interannual_ml.parquet`.

Variables principales:

- `routine_combo_top1_share`
- `routine_combo_hhi`
- `routine_od_time_top1_share`
- `routine_od_time_hhi`
- `routine_od_top1_share`
- `routine_od_hhi`
- `routine_zone_top1_usage_share`
- `routine_zone_top2_usage_share`
- `routine_zone_exploration_share`
- `routine_lab_peak_share`
- `routine_main_od_share`
- `routine_main_od_roundtrip_balance`

Sensibilidad:

- Entropias/n_unique de combo, OD-tiempo, OD y zonas.
- `routine_commute_like_score` solo como diagnostico, no como variable main.

Siguiente accion:

- Usuario corre el builder del `routine_pack`.
- Usuario corre bloques 8C del QMD y entrega `setup`, `by-target`,
  `univariate`, `bins` y `tree-logit-probe`.
- Si el probe mejora de forma no trivial, integrar `routine_main` a
  `build_user_model_matrix.py` como feature set explicito.

Resultado de integracion:

- `routine_main` se integro como `full_plus_rhythm_context_routine`.
- `routine_` se agrego como familia en `run_user_ml_benchmark.py`.
- El primer benchmark debe limitarse a XGB `alta_n3`.

Comandos pendientes:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/build_user_model_matrix.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --force
```

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/run_user_ml_benchmark.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --feature-set full_plus_rhythm_context_routine --task both --model xgb \
  --run-kind benchmark --run-name routine_alta_n3_full
```

## ML Post-Benchmark Experiments

Objetivo:

- Explorar si la baja utilidad como clasificador duro se debe al umbral,
  al desbalance de entrenamiento o a la clase de modelo, sin reabrir la
  ingenieria de features.
- Mantener `full_plus_rhythm_context_routine_daily_tour` XGB unweighted como
  benchmark principal salvo que un experimento mejore de forma robusta en
  validacion full.

Orden de prioridad:

1. Threshold tuning sobre predicciones OOF ya generadas.
   - No reentrena modelos.
   - Sirve para evaluar si el XGB unweighted, que rankea mejor, puede producir
     mejores etiquetas duras ajustando umbrales.
   - Comparar contra `argmax`, `always BIP` y class weights.
2. Subsampling/oversampling dentro de cada fold.
   - Aplicar solo sobre el train fold para evitar leakage.
   - Probar como sensibilidad si thresholds no bastan.
   - No partir con SMOTE; dificil de defender por dummies, zonas y perfiles
     sinteticos no interpretables.
   - Estado: undersampling implementado para XGBoost con
     `--sampling-strategy undersample`.
3. Clasificadores alternativos acotados.
   - Estado: CatBoost implementado como `--model catboost`.
   - Estado: MLP implementada como `--model mlp`.
   - Probar CatBoost primero con la misma matriz y sin resampling.
   - Probar MLP con sample/3-fold antes de full por costo y memoria.
   - Ninguno reemplaza a XGBoost salvo mejora robusta.
4. Local QR exposure fold-safe.
   - Estado: implementado como `--local-qr-exposure` dentro de
     `run_user_ml_benchmark.py`.
   - No se guarda en la matriz para evitar leakage.
   - Calcula tasas QR por zona/origen/actividad usando solo train fold y
     leave-one-out en train.
   - Usarlo como experimento predictivo separado, no como variable causal.

Criterio de cierre:

- Si threshold tuning solo mejora balanced accuracy a costa de predicciones
  minoritarias poco realistas, reportarlo como tradeoff.
- Si sampling o MLP no superan AUC/PR-AUC/macro OvR AUC del XGB principal,
  dejarlos como sensibilidad negativa y cerrar la busqueda de modelos.

## EDA de diferencias BIP vs QR - revision profunda

Estado: Bloque 5 cerrado. Los bloques 1-5 tienen una lectura integrada. Los
subbloques 5.1, 5.2, 5.2.1, 5.3, 5.3.1, 5.3.2 y 5.4 fueron ejecutados e
interpretados, y el notebook contiene un cierre analitico conjunto.

Decision de organizacion:

- Conservar `02_eda/eda_qr_vs_bip_profiles.qmd` como archivo exploratorio y
  fuente de analisis anteriores.
- Usar `02_eda/eda_qr_vs_bip_profiles_refined.qmd` como version principal en
  desarrollo.
- La version refinada contiene composicion, intensidad, continuidad,
  repeticion espacial y el Bloque 5 sobre momento de uso y repeticion horaria.
- El Bloque 5 se organiza en cuatro subpreguntas: uso no laboral, composicion
  por franja, concentracion temporal y sensibilidad entre universos.
- Se agrego 5.2.1 como control del recorte de franjas: compara el perfil
  laboral hora a hora dando igual peso a cada tarjeta.
- 5.3.1 mostro que medianas iguales ocultaban una diferencia moderada: dentro
  de cada rango de viajes, QR presenta menos tarjetas restringidas a una
  franja y algo mas de tarjetas presentes en tres o cuatro franjas.
- Esa diferencia describe amplitud horaria observada, no menor rutina. Para
  separar ambos conceptos se agrego 5.3.2, que compara la franja principal de
  2024 y 2025 en `Persistente` y `Repetido`.
- El cierre del Bloque 5 separa patrones comunes, diferencias descriptivas y
  el efecto mecanico del numero de viajes observados.

Reglas de continuacion:

- Avanzar una pregunta corta por vez y separar observacion de interpretacion.
- Mantener explicito que `id_tarjeta` es una unidad operacional, no una persona
  unica.
- Conservar comparaciones de universos solo cuando cambien o tensionen la
  conclusion principal.
- Evitar reincorporar automaticamente los bloques posteriores del notebook
  exploratorio.

Bloque 6 en desarrollo:

- Pregunta general: identificar si las diferencias temporales entre BIP y QR
  se concentran en determinados dias de la semana.
- `6.0 Definiciones y exposicion observada` implementado en
  `eda_qr_vs_bip_profiles_refined.qmd`.
- El dia de semana se deriva de la fecha de inicio del viaje y se mantiene
  separado de `tipodia`, que distingue dias laborales y no laborales.
- La auditoria encontro cuatro fechas de cada dia en 2024. En 2025 hay tres
  lunes y cuatro fechas para los otros dias; no hay fechas duplicadas entre
  archivos ni clasificaciones `tipodia` inconsistentes.
- `6.1 Composicion semanal ajustada por exposicion` implementado en
  `eda_qr_vs_bip_profiles_refined.qmd`.
- 6.1 usa `Amplio (>=3 viajes)`, da el mismo peso a cada tarjeta, divide los
  conteos diarios por las fechas observadas y normaliza el perfil de cada
  tarjeta a 100% antes de comparar BIP y QR.
- `6.2 Sensibilidad del perfil semanal por universo` implementado. Reutiliza
  los perfiles individuales de 6.1 y compara `Amplio`, `Persistente` y
  `Repetido` con la misma escala vertical.
- `6.2` interpretado: QR asigna consistentemente mayor peso relativo al fin de
  semana y la diferencia es mas visible en `Persistente` y `Repetido`, aunque
  ambos medios mantienen la misma estructura semanal general.
- `6.3.1 Tasas absolutas por fecha observada` implementado. Compara viajes por
  fecha lunes-viernes y por fecha sabado-domingo dando el mismo peso a cada
  tarjeta.
- Los denominadores de 6.3.1 se adaptan a los anos donde cada tarjeta aparece;
  esto evita penalizar a las tarjetas observadas en una sola ventana.
- `6.3.2 Continuidad entre anos` implementado para `Persistente` y `Repetido`.
  Clasifica cada tarjeta segun uso de fin de semana en ambos anos, solo 2024,
  solo 2025 o ninguno, y calcula
  `P(fin de semana 2025 | fin de semana 2024)` por medio de pago.
- `6.3.3 Sensibilidad a igual soporte anual` implementado. Compara BIP y QR
  dentro de las 16 combinaciones exactas de semanas activas en 2024 y 2025,
  usando como resultados la tasa de viajes de fin de semana y la continuidad
  interanual.

Siguiente accion:

- Usuario ejecuta 6.3.3 y entrega la tabla y los dos mapas junto con su lectura
  inicial.
- Evaluar si las diferencias `QR - BIP` mantienen signo y magnitud entre
  combinaciones comparables de soporte anual.
- Cerrar el Bloque 6 distinguiendo entre diferencia temporal robusta,
  composicion por actividad o heterogeneidad concentrada en celdas de soporte
  alto.
- No interpretar continuidad como motivo recreativo ni como comportamiento de
  una persona: la unidad sigue siendo `id_tarjeta`.

## Bloque 8 - Geografia residencial y de los viajes

Estado:

- Los bloques 1-7 de `02_eda/eda_qr_vs_bip_profiles_refined.qmd` estan
  cerrados analiticamente.
- `8.0 Auditoria geografica` esta implementado y validado sobre los artefactos
  actuales.
- Todavia no se anotan findings territoriales: primero se revisaran las
  salidas de la auditoria con el usuario.

Pregunta general:

- Identificar en que territorios se observan las tarjetas BIP y QR y cuanto
  de las diferencias posteriores puede depender de la composicion
  geografica.

Unidades:

- Residencia inferida: tarjeta.
- Origen y destino: viaje.
- Soporte territorial: zona.

Definicion residencial:

- `zona_hogar` es el destino mas frecuente de los viajes clasificados con
  proposito `HOGAR`.
- No es el centroide de los viajes, el origen habitual ni un domicilio
  verificado.
- La matriz base conserva confianza residencial alta y al menos tres viajes.

Contenido de 8.0:

- Cobertura y confianza de `zona_hogar` antes del filtro residencial.
- Fraccion retenida por la matriz principal `alta`, `n>=3`.
- Reconstruccion anual de `zona_hogar` con la misma regla para 2024 y 2025.
- Estabilidad de la zona anual, incluyendo una version restringida a
  confianza alta en ambos anos.
- Cobertura de zonas de origen, destino y OD en los viajes.
- Soporte por zona para residencia, origen y destino con umbrales de 25 y 100
  observaciones por medio.

Siguiente accion:

- Ejecutar 8.0 en el notebook y revisar primero cobertura, estabilidad y
  soporte.
- Solo si la auditoria es suficiente, implementar 8.1 sobre composicion
  residencial.
- Mantener origen y destino en sub-bloques separados; no tratarlos como
  sustitutos de residencia.
- Usar `Persistente` o `Repetido` despues del resultado amplio, solo como
  sensibilidad cuando cambien la lectura territorial.
