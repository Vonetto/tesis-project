# Notas — Rediseño A Nivel Tarjeta / Usuario

## 2026-05-27 — Giro Metodologico Post Reunion

El profesor cuestiona la unidad de analisis a nivel viaje: si la pregunta sustantiva es que personas/perfiles son mas propensos a usar QR, el modelo deberia agregarse por `id_tarjeta`.

Nuevo supuesto central:

- `id_tarjeta` se usa como proxy de usuario.
- Una persona podria tener mas de una tarjeta, pero eso no es observable.
- En los datos, un `id_tarjeta` pertenece siempre a un medio de pago: BIP, QR_RED o QR_OTHER. Por eso a nivel tarjeta no corresponde modelar `share_qr` como outcome principal.

Outcome candidato:

- Principal: `QR vs BIP`.
- Extension: `BIP / QR_RED / QR_OTHER`.

Implicancia:

- El modelo deja de ser un MNL de eleccion de medio de pago por viaje.
- El frente main pasa a ser un logit/binomial o multinomial de adopcion/tipo de tarjeta a nivel usuario-tarjeta.

## 2026-05-27 — Respuestas Del Profesor A Preguntas Metodologicas

Respuestas recibidas:

- Usuarios ocasionales: si el objetivo es medir adopcion, no son el foco. Esto respalda filtrar tarjetas con muy pocos viajes.
- Ventana temporal: prefiere usar todo el tiempo posible.
- Infraestructura/oferta: asignarla segun zona de origen mas frecuente es buena idea; tambien sugiere tomar las dos zonas mas frecuentes para simular casa y trabajo/estudio.
- Ponderacion por numero de viajes: si se filtran usuarios/tarjetas ocasionales, ponderar por viajes pierde importancia porque se asume que las tarjetas incluidas adoptaron o no adoptaron la tecnologia.
- Split ML temporal: al notar que hay anos distintos, no dio una regla cerrada. Queda como pregunta abierta de diseno.
- Factorizacion matricial: tenia en mente NMF. Si se parte con NMF basico, agregar dummy para macrozonas porque `X/Y` no se pueden agregar naturalmente.

Lectura de trabajo:

- Usar todo el historial disponible por tarjeta.
- Definir umbral minimo por auditoria de `n_viajes`.
- Construir variables de top zonas de actividad.
- Mantener split aleatorio por tarjeta como evaluacion de perfiles, pero agregar una sensibilidad temporal o controles de cohorte/ano para no ignorar crecimiento QR 2024-2025.
- Dejar NMF para despues de construir matrices base; revisar variantes cuando lleguemos a segmentacion.

## 2026-05-27 — EDA Del Panel Como Hito Obligatorio

Antes de reestimar modelos, se decide agregar un hito explicito de EDA del panel por tarjeta.

Motivacion:

- El rediseño puede fallar silenciosamente si el panel queda dominado por tarjetas con pocos viajes, fuerte sesgo temporal o variables agregadas mal comportadas.
- El umbral minimo de viajes no debe elegirse arbitrariamente; se definira mirando sensibilidad de tarjetas retenidas, viajes retenidos y composicion QR/BIP.
- El EDA tambien debe revisar si multiclase `BIP / QR_RED / QR_OTHER` es viable o si conviene dejarla como sensibilidad.

Tambien se agrega EDA previo a NMF/SVD para evaluar sparsity, columnas raras y si usar conteos, proporciones o transformaciones.

## 2026-05-27 — Bloques De Variables Candidatas

Panel por tarjeta:

- Target: `tipo_tarjeta`, `is_qr`.
- Exposicion: `n_viajes`, dias activos, semanas activas, primera/ultima observacion.
- Temporal: shares por hora/franja, hora media/mediana, dispersion horaria.
- Operacional: medias/medianas/maximos de tiempos, esperas y transbordos.
- Modal: shares bus, metro, metro+bus si estan disponibles.
- Espacial: residencia, macrozona residencia, origen frecuente, destino frecuente, macrozona origen frecuente, macrozona destino frecuente.
- Diversidad: numero de zonas origen/destino, entropias origen/destino.
- Socioeconomico: variables Censo/EOD por residencia.
- Oferta/infraestructura: pendiente decidir si origen frecuente, residencia, destino frecuente o promedio ponderado.

## 2026-05-27 — Smoke Panel `active`

Se construyo un primer panel smoke a nivel `id_tarjeta` con scope `active`:

- Semanas: `2024-W17` y `2025-W17`.
- Script: `scripts/audits/build_user_level_payment_panel.py`.
- Comando: `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_level_payment_panel.py --scope active --force --conflict-policy exclude`.
- Output limpio: `tmp/audits/user_level_redesign/user_level_payment_panel_active_clean.parquet`.
- Output con conflictos: `tmp/audits/user_level_redesign/user_level_payment_panel_active_with_conflicts.parquet`.

Resultados:

- Panel limpio: 4.028.425 tarjetas, 24.030.662 viajes, 149 columnas.
- Panel con conflictos: 4.031.185 tarjetas, 24.062.915 viajes.
- `id_tarjeta` unica en output: sin duplicados.
- Se detectaron 2.760 tarjetas con mas de un `tipo_pago` en el scope.
- Estos conflictos no son BIP vs QR: todos son QR (`is_qr = true`), contrato 102, y cambian entre `QR_RED` y `QR_OTHER` por `tipo_app` (`APP RED` / `OTRA APP`).
- Transiciones observadas: 2.067 tarjetas `QR_RED` 2024-W17 -> `QR_OTHER` 2025-W17; 693 tarjetas `QR_OTHER` 2024-W17 -> `QR_RED` 2025-W17.
- Decision operativa: mantener dos variantes, una limpia excluyendo conflictos y otra con conflictos conservados via `target_conflict_flag` y `tipo_pago_set`.
- Distribucion por tarjeta: BIP 83,96%, QR_OTHER 13,81%, QR_RED 2,24%.
- Distribucion por viaje: BIP 85,30%, QR_OTHER 12,45%, QR_RED 2,25%.
- Missing `zona_hogar`: 13,37%.
- Tarjetas con residencia `alta`: 2.562.138.
- Tarjetas con residencia `alta` o `media`: 2.951.366.

Sensibilidad por umbral:

- `n_viajes >= 3`: retiene 65,91% de tarjetas y 90,28% de viajes.
- `n_viajes >= 5`: retiene 46,57% de tarjetas y 78,75% de viajes.
- `n_viajes >= 10`: retiene 20,29% de tarjetas y 48,99% de viajes.

Lectura:

- El constructor funciona como smoke test.
- Los conflictos de target son muy pocos, pero deben mantenerse como exclusion auditada y no corregirse silenciosamente.
- El umbral `n_viajes >= 3` parece un candidato inicial razonable para EDA porque elimina tarjetas muy ocasionales sin perder muchos viajes.
- Falta construir residencia para semanas adicionales antes de usar scope extendido como candidato main.

## 2026-05-27 — Auditoria De Cobertura `interannual_ml`

Se ejecuto auditoria previa de cobertura para el scope masivo:

- Scope: `interannual_ml`.
- Semanas: `2024-W14`, `2024-W15`, `2024-W16`, `2024-W17`, `2025-W14`, `2025-W15`, `2025-W16`, `2025-W17`.
- Script: `scripts/audits/audit_user_level_scope_coverage.py`.
- Comando: `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/audit_user_level_scope_coverage.py --scope interannual_ml`.

Outputs:

- `tmp/audits/user_level_redesign/scope_coverage_weekly_interannual_ml.csv`.
- `tmp/audits/user_level_redesign/scope_coverage_daily_interannual_ml.csv`.
- `tmp/audits/user_level_redesign/scope_pooled_target_distribution_interannual_ml.csv`.
- `tmp/audits/user_level_redesign/scope_pooled_threshold_sensitivity_interannual_ml.csv`.
- `tmp/audits/user_level_redesign/scope_pooled_target_conflicts_sample_interannual_ml.csv`.

Resultados principales:

- Total pooled: 92.997.475 viajes y 6.360.054 tarjetas.
- Distribucion por tarjeta: BIP 83,20%, QR_OTHER 14,58%, QR_RED 2,13%, conflictos 0,08%.
- Distribucion por viaje: BIP 85,24%, QR_OTHER 12,41%, QR_RED 2,18%, conflictos 0,16%.
- Conflictos pooled: 5.038 tarjetas; siguen siendo `QR_OTHER|QR_RED`, no BIP vs QR.
- Todas las semanas 2024 tienen 7 dias completos.
- `2025-W14` tiene 6 dias: 2025-04-01 a 2025-04-06. Falta 2025-03-31 por estar fuera del mes de abril.
- `2025-W16` tiene 7 dias pero solo dos valores `tipodia`; 2025-04-18 a 2025-04-20 aparecen como no laborales/feriados, consistente con Semana Santa.
- Missing zona origen/destino es cero en 2024 y menor a 0,003% en 2025.
- QR por viaje sube desde aprox 12,8%-12,9% en 2024 a 16,7%-16,9% en 2025.

Sensibilidad por umbral:

- `n_viajes >= 3`: retiene 75,87% de tarjetas y 97,17% de viajes.
- `n_viajes >= 5`: retiene 61,73% de tarjetas y 93,72% de viajes.
- `n_viajes >= 10`: retiene 43,30% de tarjetas y 85,24% de viajes.

Lectura:

- Es valido usar las 8 semanas como pooling masivo a nivel tarjeta, siempre que el modelo controle/describa exposicion (`n_viajes`, `n_dias_activos`, `n_weeks_observed`, `share_trips_2025`) y fraccion no laboral.
- La semana parcial 2025-W14 no es necesariamente un problema porque la unidad es tarjeta, pero debe quedar documentada.
- Los feriados/no laborales no deben eliminarse por defecto; se capturan con `tipodia`/`share_no_lab`.
- Antes de construir el panel masivo con residencia se necesita extender el bridge `proposito` a las semanas faltantes.

Estado operativo:

- `scripts/audits/build_proposito_pk_bridge.py` queda preparado para `--scope interannual_ml`.
- El raw CSV de viajes con `proposito` no esta disponible actualmente en `/Volumes/TOSHIBA EXT/...`; para ejecutar el bridge masivo hay que montar Toshiba o pasar `--raw-viajes-dir` hacia una copia equivalente.

## 2026-05-27 — Frente Main

Modelo candidato:

- Logit binario a nivel tarjeta: `P(QR = 1)`.
- Multinomial a nivel tarjeta como extension: `P(tipo_tarjeta in {BIP, QR_RED, QR_OTHER})`.

Variables:

- Socioeconomia por residencia.
- Macrozonas por residencia y/o origen frecuente.
- Resumenes de comportamiento de viaje.
- No usar `X/Y` en main por interpretabilidad y riesgo de absorber geografia sin lectura clara.

Pendiente:

- Ponderacion por `n_viajes`.
- Umbral minimo de viajes.
- Ventana temporal.

## 2026-05-27 — Frente ML

Modelo candidato:

- XGBoost a nivel tarjeta.
- GPBoost como sensibilidad espacial.

Split:

- Inicialmente aleatorio por `id_tarjeta`, no por viaje.
- Reportar que evalua separacion entre perfiles dentro del periodo observado, no prediccion temporal futura.
- Pendiente agregar sensibilidad temporal o controles de fecha por crecimiento QR 2024-2025.

Variables espaciales ML:

- `X/Y` residencia.
- Posiblemente `X/Y` origen frecuente AM y destino frecuente PM.
- Posiblemente distancias/dispers dispersion espacial.

## 2026-05-27 — Segmentacion Y Factorizacion Matricial

Idea:

- Construir matriz `id_tarjeta x patron_movililidad`.
- Factorizar para obtener perfiles latentes de movilidad.
- Cruzar factores/perfiles con QR/BIP despues.

Matrices candidatas:

- Tarjeta x hora/franja.
- Tarjeta x macrozona origen.
- Tarjeta x macrozona origen + franja.
- Tarjeta x OD macrozona.
- Tarjeta x zona origen/destino si no queda demasiado dispersa.

Tecnicas candidatas:

- NMF para conteos/proporciones no negativas e interpretabilidad.
- SVD/PCA como sensibilidad.

Decision metodologica:

- No incluir target QR/BIP dentro de la factorizacion si el objetivo es segmentacion no supervisada.

## 2026-05-29 — Cierre EDA supervisado usuario/tarjeta hasta bloque 7L

Se extendio el EDA del panel `interannual_ml` con bloques externos y derivados:

- 7G: accesibilidad espacial a puntos de carga BIP por zona777.
- 7H: oferta/demanda y contexto operacional en origen frecuente.
- 7I: inercia/diversidad de rutas por usuario.
- 7J: interacciones/hibridas entre uso, ruta y territorio.
- 7K: evaluacion binaria formal `QR vs BIP`.
- 7L: franjas etarias censales por zona de residencia.

Lectura consolidada:

- La separacion predictiva `QR vs BIP` existe pero es moderada; aun agregando varios bloques, las metricas mejoran de forma acotada. El modelo binario debe leerse como identificacion de perfiles asociados, no como clasificador fuerte.
- `QR_OTHER` parece mas asociado a recencia, baja intensidad, diversidad/inercia de rutas y patrones conductuales.
- `QR_RED` parece mas distinto de `QR_OTHER`, con senal territorial/socioeducativa/macrogeografica y mejor respuesta a interacciones/franjas etarias.
- Accesibilidad espacial a carga BIP y oferta/demanda aportaron poco incrementalmente en las pruebas realizadas.
- Ruta/inercia e hibridas aportaron mas, especialmente en logit y para `QR_OTHER vs BIP`.
- Franjas etarias territoriales aportaron poco para QR general, pero mejoraron la separacion `QR_RED vs QR_OTHER`; candidatas parsimoniosas: `res_age_share_25_44` y `res_age_share_18_24`, con `res_age_share_60_mas` como sensibilidad/descriptiva.

Decision operativa:

- Cerrar EDA exploratorio por ahora.
- Construir una matriz usuario-feature final para modelamiento supervisado antes de pasar a NMF/SVD.
- Mantener `QR vs BIP` como especificacion principal simple por robustez, pero complementar con multiclase o contrastes `QR_OTHER vs BIP` y `QR_RED vs QR_OTHER` para no esconder heterogeneidad.
- Documentar SUBTEL/conectividad digital territorial como hipotesis futura no implementada en esta ronda.

## 2026-05-29 — Matriz usuario-feature supervisada materializada

Se construyo la matriz final de features supervisadas a nivel `id_tarjeta`:

- Script: `scripts/audits/build_user_model_matrix.py`.
- Comando: `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_model_matrix.py --scope interannual_ml --variant clean --home-filter alta --min-trips 3 --force`.
- Output: `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n3.parquet`.
- Feature sets: `tmp/audits/user_level_redesign/user_model_matrix_feature_sets_interannual_ml_clean_alta_n3.json`.
- Auditorias: `user_model_matrix_summary_*`, `user_model_matrix_target_distribution_*`, `user_model_matrix_feature_missing_*`.

Validacion:

- Filas: 2.460.264 tarjetas.
- `id_tarjeta` unica: 2.460.264.
- Columnas: 119.
- Features maximas disponibles: 105.
- Target: BIP 2.082.769, QR_OTHER 324.421, QR_RED 53.074.
- Tasa QR: 15,34%; QR_RED: 2,16%; QR_OTHER: 13,19%.
- Todos los feature sets declarados quedan sin variables faltantes.

Feature sets generados:

- `logit_main`: 34 features.
- `logit_sensitivity_age60`: 35 features.
- `logit_sensitivity_mean_age`: 35 features.
- `logit_sensitivity_route_hybrid`: 41 features.
- `ml_main`: 49 features.
- `ml_wide`: 105 features.
- `binary_ml_main`: 41 features.
- `binary_ml_wide`: 91 features.

Nota tecnica:

- Se corrigio el diseño para evitar leakage/transductive preprocessing: la matriz no incluye imputaciones medianas globales, winsorizaciones globales ni dummies por quantiles globales en los feature sets.
- El contrato del `feature_sets.json` es que imputacion, escalado, winsorizacion y cortes por quantiles deben ajustarse dentro del pipeline train/CV.
- `service_route_early_late_rcs` se mantiene crudo en el set principal junto con `service_route_has_early_late_rcs`; su missing estructural (~31%) debe manejarse en el pipeline del modelo.
- La version interanual `service_route_rcs_2024_2025` se mantiene solo como sensibilidad por su missing alto (~71,5%).
- `feature_sets.json` es la fuente de verdad para construir `X`; no usar "todas las columnas menos target", porque hay columnas de metadata que tambien pueden ser features en algunos sets.
- El directorio `tmp/audits/user_level_redesign` es symlink a `/Volumes/KINGSTON/...`, por lo que escribir la matriz desde Codex requirio permiso elevado.

## 2026-05-28 — Bridge `proposito`/residencia `interannual_ml` completado

Se ejecuto el bridge masivo de `proposito` para el scope `interannual_ml` usando raw CSV en Kingston:

- Raw CSV: `/Volumes/KINGSTON/tesis-project/raw/viajes`.
- Script: `scripts/audits/build_proposito_pk_bridge.py`.
- Comando: `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_proposito_pk_bridge.py --scope interannual_ml --raw-viajes-dir /Volumes/KINGSTON/tesis-project/raw/viajes --force`.
- Semanas: `2024-W14`, `2024-W15`, `2024-W16`, `2024-W17`, `2025-W14`, `2025-W15`, `2025-W16`, `2025-W17`.

Artefactos principales:

- `tmp/audits/proposito_residence/pk_bridge/raw_viajes_proposito_pk_interannual_ml.parquet`.
- `tmp/audits/proposito_residence/pk_bridge/processed_trip_proposito_bridge_interannual_ml.parquet`.
- `tmp/audits/proposito_residence/pk_bridge/user_home_candidates_interannual_ml.parquet`.
- Diagnosticos: `tmp/audits/proposito_residence/pk_bridge/bridge_join_diagnostics_interannual_ml.csv`, `home_confidence_distribution_interannual_ml.csv`, `pk_bridge_summary_interannual_ml.csv`.

Resultados de validacion:

- `processed_rows`: 92.997.475.
- `bridge_matched_rows`: 92.997.475.
- Match procesado -> raw por `pk_viaje`: 100% en las 8 semanas.
- `id_tarjeta_mismatch`: 0.
- `id_viaje_mismatch`: 0.
- `raw_rows`: 164.368.488.
- `raw_unique_pk_rows`: 164.368.488.
- `raw_rows` no son tarjetas; son filas/viajes raw con `pk_viaje` unico.
- Se observaron pequenos `zona_inicio`/`zona_fin` mismatches entre raw y procesado, pero con match perfecto por PK y sin conflicto de tarjeta/viaje.

Residencia inferida:

- Tarjetas procesadas en auditoria previa `interannual_ml`: 6.360.054.
- Tarjetas con alguna residencia inferible: 5.773.880, aprox 90,8% de tarjetas procesadas.
- `home_confidence == alta`: 3.540.483 tarjetas, aprox 55,7% de tarjetas procesadas y 61,3% de tarjetas con residencia inferida.
- `home_confidence == media`: 921.471.
- `home_confidence == baja`: 1.311.926.

Decision metodologica:

- Usar `home_confidence == "alta"` como muestra principal para modelos con covariables socioeconomicas por residencia.
- Justificacion: al asignar educacion, ingreso proxy, edad y otras covariables por `zona_hogar`, una residencia ambigua introduce error de medicion. La muestra `alta` prioriza validez de medicion sobre maxima cobertura.
- `alta+media` queda como sensibilidad, no como especificacion principal inicial.
- La caida porcentual de `alta` frente a scopes mas cortos no implica perdida absoluta de datos: al observar mas semanas aparecen mas zonas hogar, empates y menor concentracion modal. Eso revela ambiguedad residencial que en ventanas cortas podia quedar oculta.

Siguiente paso operativo:

- Habilitar `interannual_ml` en `scripts/audits/build_user_level_payment_panel.py`.
- Generar dos paneles a nivel tarjeta:
  - limpio: excluir tarjetas con conflicto de target.
  - con conflictos: conservarlas con `target_conflict_flag`.
- Luego ejecutar EDA obligatorio del panel antes de modelar.

## 2026-05-28 — Panel `id_tarjeta` `interannual_ml` construido

Se habilito `interannual_ml` en `scripts/audits/build_user_level_payment_panel.py` usando:

- `HOME_CANDIDATES_BY_SCOPE["interannual_ml"] = user_home_candidates_interannual_ml.parquet`.
- Scope: `2024-W14`, `2024-W15`, `2024-W16`, `2024-W17`, `2025-W14`, `2025-W15`, `2025-W16`, `2025-W17`.

Comandos ejecutados:

- `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_level_payment_panel.py --scope interannual_ml --force --conflict-policy exclude`.
- `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_level_payment_panel.py --scope interannual_ml --force --conflict-policy keep`.

Artefactos:

- Principal limpio: `tmp/audits/user_level_redesign/user_level_payment_panel_interannual_ml_clean.parquet`.
- Auditoria con conflictos: `tmp/audits/user_level_redesign/user_level_payment_panel_interannual_ml_with_conflicts.parquet`.
- Diagnosticos principales:
  - `user_level_panel_summary_interannual_ml_clean.csv`.
  - `user_level_panel_target_distribution_interannual_ml_clean.csv`.
  - `user_level_panel_trip_threshold_sensitivity_interannual_ml_clean.csv`.
  - `user_level_panel_missing_summary_interannual_ml_clean.csv`.
  - equivalentes `with_conflicts`.

Resultados panel limpio:

- `n_cards`: 6.355.016.
- `n_trips`: 92.845.168.
- `target_conflict_cards`: 0.
- `excluded_target_conflict_cards`: 5.038.
- `missing_zona_hogar_rate`: 9,22%.
- `home_alta_cards`: 3.538.412.
- `home_alta_media_cards`: 4.458.720.

Distribucion target panel limpio:

- BIP: 5.291.873 tarjetas (83,27%) y 79.275.411 viajes (85,38%).
- QR_OTHER: 927.580 tarjetas (14,60%) y 11.540.168 viajes (12,43%).
- QR_RED: 135.563 tarjetas (2,13%) y 2.029.589 viajes (2,19%).

Resultados panel con conflictos:

- `n_cards`: 6.360.054.
- `n_trips`: 92.997.475.
- `target_conflict_cards`: 5.038.
- `missing_zona_hogar_rate`: 9,22%.
- `home_alta_cards`: 3.540.483.
- `home_alta_media_cards`: 4.461.954.
- Conflictos: 0,079% de tarjetas y 0,164% de viajes.

Decision operativa:

- Usar `user_level_payment_panel_interannual_ml_clean.parquet` como input principal para EDA y modelos.
- Conservar `user_level_payment_panel_interannual_ml_with_conflicts.parquet` solo como artefacto auditado/sensibilidad, porque los conflictos son pocos y corresponden a ambiguedad QR_RED/QR_OTHER, no BIP vs QR.
- Mantener `home_confidence == "alta"` como muestra principal para especificaciones con covariables residenciales; `alta+media` queda para sensibilidad.

Siguiente paso:

- Ejecutar EDA obligatorio del panel antes de estimar modelos.
- En particular, revisar sensibilidad por `n_viajes`, distribucion del target por umbral, cobertura de residencia por target, distribuciones de variables agregadas y relaciones descriptivas con QR/BIP.

## 2026-05-28 — EDA panel: decisiones preliminares Bloques 1-3

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Resultados principales:

- Panel principal limpio: 6.355.016 tarjetas y 92.845.168 viajes.
- Conflictos de target excluidos: 5.038 tarjetas, marginales para la distribucion.
- Distribucion limpia: BIP 83,27%, QR_OTHER 14,60%, QR_RED 2,13%.

Umbral minimo de viajes:

- `n_viajes >= 3` queda como candidato principal.
- Justificacion: retiene 75,9% de tarjetas y 97,2% de viajes en el panel limpio.
- El share QR cae de 16,73% a 15,88%, una caida moderada de 0,85 puntos porcentuales.
- `n_viajes >= 5` y `n_viajes >= 10` quedan como sensibilidades por intensidad de uso.
- `n_viajes >= 10` no se recomienda como main porque cambia demasiado el universo hacia usuarios intensivos.

Exposicion y cohorte temporal:

- QR es mas ocasional/reciente que BIP, especialmente por QR_OTHER.
- En binario, QR tiene mediana `n_viajes = 6` vs BIP `8`.
- QR tiene mayor `share_trips_2025`: media 0,579 vs BIP 0,472.
- QR tiene mayor proporcion de tarjetas solo observadas en 2025: 42,5% vs BIP 35,1%.
- Decision: `share_trips_2025` o flags de cohorte (`solo_2024`, `solo_2025`, `ambos`) deben entrar como control obligatorio en modelos posteriores.

Residencia:

- `home_alta` no sesga sustancialmente el target: retiene 55,8% de BIP, 54,9% de QR_OTHER y 55,9% de QR_RED.
- Sin embargo, `home_alta` mide no ambiguedad modal, no necesariamente alto soporte muestral.
- Dentro de `home_alta`, 46,1% de tarjetas tiene solo 1 viaje HOGAR observado y 57,8% tiene como maximo 2.
- Definicion a usar: `home_alta` = residencia modal no ambigua entre viajes HOGAR observados.
- No decir simplemente "residencia de alta confianza" sin aclarar que la confianza es sobre ambiguedad modal.

Sensibilidad residencial fuerte:

- `home_alta + n_home_dest_trips_card >= 3` aumenta soporte residencial, pero reduce `home_alta` de 3,54M a 1,49M tarjetas.
- Tambien cambia el universo hacia tarjetas mas intensivas: mediana `n_viajes` sube a 20.
- Decision: usarla como sensibilidad fuerte, no como especificacion principal inicial.

Macrozonas residenciales:

- Macrozonas discriminan fuerte el target.
- CENTRO y ORIENTE tienen mayor QR total (~19% y 18,5% respectivamente), mientras SUR y PONIENTE estan cerca de 15%.
- ORIENTE es atipico por QR_RED: 5,53% vs ~1,2% en NORTE/PONIENTE/SUR.
- CENTRO destaca mas por QR_OTHER: 16,88%.
- Decision: incluir macrozona de residencia en modelos main y mantener modelo multiclase como analisis relevante, porque QR_RED y QR_OTHER muestran geografias distintas.

Decision provisional de universo main:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro principal: `home_confidence == "alta"` y `n_viajes >= 3`.
- Target principal: binario `QR vs BIP`.
- Target secundario importante: multiclase `BIP / QR_OTHER / QR_RED`.
- Sensibilidades: `n_viajes >= 5`, `n_viajes >= 10`, `home_alta + n_home_dest_trips_card >= 3`, y `home_alta_media`.

## 2026-05-28 — Convencion modal para panel de usuario

Decision:

- `tipo_transporte = 1` se trata como Bus.
- `tipo_transporte = 3` (Zona Paga) se trata como Bus.
- `tipo_transporte = 2` se trata como Metro.
- `tipo_transporte = 4` (MetroTren) se trata como Metro/ferroviario.

Implicancia:

- Las variables `share_trips_solo_metro` y `share_trips_metro_bus` deben leerse como variables de Metro/MetroTren.
- Se mantiene el nombre corto `metro` en el codigo para no cambiar schemas, pero la lectura metodologica es "modo ferroviario".
- Luego de esta decision hay que regenerar el panel y rerun del Bloque 4, porque las proporciones modales actuales venian de una version con bug de nulos en `tipo_transporte_*` y sin incluir `4` como ferroviario.

## 2026-05-28 — EDA panel Bloque 4: variables agregadas de uso

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Contexto:

- Se regeneraron los paneles `interannual_ml` despues de corregir la logica modal.
- Convencion modal corregida:
  - Bus = `tipo_transporte` 1 o 3 (Zona Paga).
  - Metro/ferroviario = `tipo_transporte` 2 o 4 (MetroTren).
- El bug previo hacia que `share_trips_solo_bus`, `share_trips_solo_metro` y `share_trips_metro_bus` salieran degeneradas por manejo incorrecto de nulos en columnas `tipo_transporte_*`.

Resultados modales corregidos:

- `share_trips_solo_bus`: media 0,389; mediana 0,278.
- `share_trips_solo_metro`: media 0,455; mediana 0,367.
- `share_trips_metro_bus`: media 0,156; mediana 0.
- Lectura: las variables ya son coherentes; existe un subgrupo multimodal relevante, pero la mayoria de tarjetas no tiene viajes metro+bus como patron dominante.

Resultados descriptivos por target:

- Las diferencias visuales entre BIP, QR_OTHER y QR_RED son moderadas; no hay separacion limpia solo con variables de uso.
- QR_RED muestra un perfil algo mas laboral:
  - `share_lab_pm` media 0,200 vs BIP 0,160.
  - `share_lab_pt` media 0,142 vs BIP 0,103.
- QR_OTHER muestra mayor componente no laboral:
  - `share_no_lab` media 0,188 vs BIP 0,166.
- BIP presenta algo mas de transbordo:
  - `share_trips_with_transfer` media 0,411 vs QR_OTHER 0,392 y QR_RED 0,379.
- QR_RED tiene viajes levemente mas cortos:
  - `t_vehiculo_mean_min` media 17,82 vs BIP 18,44.
- En modo:
  - QR_OTHER usa mas solo bus: media 0,413 vs BIP 0,384.
  - QR_RED usa algo mas Metro/MetroTren: media 0,462 vs BIP 0,455.

Colinealidad:

- Hay colinealidad fuerte dentro de familias de variables.
- Pares principales:
  - `n_trasbordos_mean` vs `share_trips_with_transfer`: Spearman 0,967.
  - `t_vehiculo_mean_min` vs `t_vehiculo_median_min`: 0,955.
  - `t_espera_ini_mean_min` vs `t_espera_ini_median_min`: 0,933.
  - `hora_mean` vs `hora_median`: 0,906.
- Las variables modales son composicionales: `solo_bus`, `solo_metro` y `metro_bus` suman 1. No deben entrar las tres juntas en un logit interpretable.

Implicancias de modelamiento:

- Las variables agregadas de uso sirven como controles/perfiles de comportamiento, no como bloque explicativo principal.
- Muchas shares tienen masa en 0 y 1 porque varias tarjetas tienen pocos viajes; esto es esperable y no invalida la variable, pero hace debil una lectura lineal suave.
- Para logit interpretable, considerar tambien versiones binarias tipo `has_*` como sensibilidad: tuvo viaje en punta, tuvo viaje no laboral, tuvo transbordo, tuvo viaje metro/ferroviario.
- `hora_std` tiene missing para tarjetas con un solo viaje. Opcion defendible: imputar 0 y controlar por `n_viajes`, documentando que significa "sin variabilidad horaria observada".
- Winsorizar a p99 tiempos continuos antes de modelar:
  - `t_vehiculo_mean_min`.
  - `t_espera_ini_mean_min`.
  - `t_espera_trasb_mean_min` si se usa en sensibilidad.

Lista candidata reducida para modelo interpretable:

- `hora_mean`.
- `hora_std`.
- `share_lab_pm`.
- `share_lab_pt`.
- `share_no_lab`.
- `share_trips_with_transfer`.
- `t_vehiculo_mean_min`.
- `t_espera_ini_mean_min`.
- `share_trips_solo_metro`.
- `share_trips_metro_bus`.

Variables excluidas de baseline:

- `hora_median`: redundante con `hora_mean`.
- `n_trasbordos_mean`, `n_trasbordos_median`, `n_trasbordos_max`: redundantes con `share_trips_with_transfer`.
- `t_vehiculo_median_min`, `t_vehiculo_max_min`: redundantes con `t_vehiculo_mean_min`.
- `t_espera_ini_median_min`, `t_espera_ini_max_min`: redundantes con `t_espera_ini_mean_min`.
- `t_espera_trasb_*`: muy ligadas mecanicamente a transbordos; quedan como sensibilidad alternativa.
- `share_trips_solo_bus`: base modal implicita si se incluyen `share_trips_solo_metro` y `share_trips_metro_bus`.

Sensibilidades recomendadas:

- Reemplazar `share_trips_with_transfer` por `n_trasbordos_mean`.
- Reemplazar o agregar `t_espera_trasb_mean_min` en una especificacion de friccion de transbordo.
- Probar shares continuas vs dummies `has_*`.
- Probar modelo sin `t_espera_ini_mean_min`, porque esta fuertemente asociada al modo y podria absorber parte de oferta/modalidad.

## 2026-05-28 — EDA panel Bloque 5: geografia y contexto

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Universo:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro: `home_confidence == "alta"` y `n_viajes >= 3`.
- Resultado: 2.460.264 tarjetas y 43.647.285 viajes.
- Share QR total en este universo: 15,34%; QR_OTHER 13,19%; QR_RED 2,16%.

Cobertura geografica:

- Variables geograficas requeridas presentes: sin ausentes.
- Missing bajo:
  - `home_macrozone`: 0,32%.
  - `origin_top1_macrozone`: 0,24%.
  - `origin_top2_macrozone`: 0,52%.
  - `activity_top1_macrozone`: 0,20%.
  - `activity_top2_macrozone`: 0,21%.
- Decision: las variables geograficas se pueden usar sin perdida muestral relevante.

Share QR por macrozona:

- Por residencia:
  - CENTRO: QR 18,01%; QR_OTHER 15,79%; QR_RED 2,22%.
  - ORIENTE: QR 17,32%; QR_OTHER 11,75%; QR_RED 5,57%.
  - SURORIENTE: QR 15,66%.
  - NORTE: QR 14,66%.
  - SUR: QR 14,03%.
  - PONIENTE: QR 13,90%.
- Por origen top-1:
  - ORIENTE: QR 17,35%; QR_RED 4,30%.
  - EXTERNA_ESPECIAL: QR 16,67%, pero con n bajo.
  - CENTRO: QR 16,23%.
  - PONIENTE/SUR: ~14%.
- Por actividad top-1:
  - ORIENTE: QR 17,28%; QR_RED 4,30%.
  - CENTRO: QR 16,03%.
  - SUR/PONIENTE: ~14%.

Lectura geografica:

- La senal geografica aparece en residencia, origen top-1 y actividad top-1.
- Residencia captura mejor la diferencia CENTRO/ORIENTE:
  - CENTRO destaca por QR_OTHER.
  - ORIENTE destaca fuertemente por QR_RED.
- Origen top-1 y actividad top-1 son muy parecidos entre si; para el modelo econometrico basta probar origen top-1 como contexto frecuente de uso.
- ORIENTE como origen frecuente eleva el share QR incluso para residentes de otras macrozonas.

Cruce residencia vs origen top-1:

- La diagonal domina, pero no completamente:
  - ORIENTE -> ORIENTE: 88,9%.
  - PONIENTE -> PONIENTE: 84,8%.
  - NORTE -> NORTE: 82,3%.
  - SURORIENTE -> SURORIENTE: 70,8%.
  - CENTRO -> CENTRO: 66,9%.
  - SUR -> SUR: 66,2%.
- Hay off-diagonal suficiente para que origen top-1 aporte informacion distinta de residencia.
- Casos relevantes:
  - CENTRO -> ORIENTE: QR 19,4%, mayor que CENTRO -> CENTRO 17,8%.
  - SURORIENTE -> ORIENTE: QR 18,7%, mayor que SURORIENTE -> SURORIENTE 14,8%.
  - SUR -> ORIENTE: QR 15,4%, mayor que SUR -> SUR 13,9%.

Estabilidad espacial:

- `origin_zone_top1_share`: media 0,441; mediana 0,444.
- `origin_zone_top2_share`: media 0,298; mediana 0,294.
- Top-1 + top-2 de origen concentra cerca de 74% de los viajes, usando medianas.
- `activity_zone_top1_share`: media 0,401; mediana 0,417.
- `activity_zone_top2_share`: media 0,281; mediana 0,250.
- Top-1 + top-2 de actividad concentra cerca de 67% de los viajes, usando medianas.
- `activity_zone_entropy` es mayor que `origin_zone_entropy`; actividad esta mas dispersa que origen.
- Las distribuciones de entropia y top-share por target se superponen bastante; no separan claramente BIP/QR.

Decision para modelo econometrico:

- Especificacion geografica principal:
  - `home_macrozone`.
  - `origin_top1_macrozone`.
- Sensibilidades:
  - solo `home_macrozone`.
  - solo `origin_top1_macrozone`.
  - `home_macrozone + origin_top1_macrozone + origin_zone_top1_share`.
  - `home_macrozone + origin_top1_macrozone + origin_zone_entropy`.
  - agregar `origin_top2_macrozone` como sensibilidad ampliada, no como main.
- No incluir `activity_top1_macrozone` en el main econometrico inicial porque es conceptualmente cercana a `origin_top1_macrozone` y no aporta una lectura tan directa.

Set espacial completo para ML:

- `home_macrozone`.
- `origin_top1_macrozone`.
- `origin_top2_macrozone`.
- `activity_top1_macrozone`.
- `activity_top2_macrozone`.
- `origin_top1_lon`, `origin_top1_lat`.
- `origin_top2_lon`, `origin_top2_lat`.
- `activity_top1_lon`, `activity_top1_lat`.
- `activity_top2_lon`, `activity_top2_lat`.
- `origin_zone_top1_share`.
- `origin_zone_top2_share`.
- `origin_zone_entropy`.
- `activity_zone_top1_share`.
- `activity_zone_entropy`.

Decision sobre mapas:

- No hacer mapas aun.
- Primero estimar modelos y revisar que zonas/macrozona quedan relevantes; luego mapear solo resultados que aporten a la lectura.

## 2026-05-28 — EDA panel Bloque 6A: socioeconomia residencial

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Universo:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro: `home_confidence == "alta"` y `n_viajes >= 3`.
- Resultado: 2.460.264 tarjetas y 43.647.285 viajes.
- Share QR total: 15,34%; QR_OTHER 13,19%; QR_RED 2,16%.

Cobertura:

- Todas las variables residenciales `res_*` auditadas tienen missing 0,321%.
- Decision: la cobertura es suficiente para usarlas sin perdida muestral relevante.

Variables auditadas:

- `res_share_cine18_universitaria_o_mas_micro_z` como educacion universitaria o mas.
- `res_eod2012_share_hogares_de_income_proxy_z` como concentracion relativa de hogares D+E proxy, no como mayor ingreso.
- `res_prom_edad_z`.
- `res_share_discapacidad_z`.
- `res_share_inmigrantes_z`.
- `res_share_mujeres_z`.
- `res_share_asistencia_parv_z`.

Hallazgos por target:

- QR_RED tiene un perfil residencial claramente distinto a BIP y QR_OTHER:
  - educacion: +0,747 z vs BIP.
  - concentracion D+E proxy: -0,469 z vs BIP.
  - edad promedio: +0,140 z vs BIP.
  - discapacidad: -0,467 z vs BIP.
  - mujeres: +0,267 z vs BIP.
  - asistencia parvular: +0,423 z vs BIP.
- QR_OTHER se parece mucho mas a BIP:
  - educacion: +0,027 z.
  - concentracion D+E proxy: +0,000 z.
  - edad: -0,066 z.
  - discapacidad: -0,037 z.
  - inmigrantes: +0,085 z.
  - mujeres: -0,004 z.
  - asistencia parvular: -0,025 z.

Lectura del proxy EOD:

- `res_eod2012_share_hogares_de_income_proxy_z` mide concentracion relativa de hogares D+E proxy.
- Valores altos significan mayor concentracion D+E, no mayor ingreso.
- Correlaciones:
  - D+E proxy vs educacion: -0,644.
  - D+E proxy vs discapacidad: +0,520.
  - D+E proxy vs mujeres: -0,424.
  - D+E proxy vs asistencia parvular: -0,414.
- Decision: renombrar conceptualmente como `de_income_proxy` o `concentracion_de_proxy` en reportes/modelos, evitando llamarlo simplemente "ingreso".

Auditoria `share_mujeres`:

- `res_share_mujeres_z` tiene un outlier fuerte: minimo -18,515.
- 9.028 tarjetas caen bajo -5 z; 0,368% del universo main.
- Winsorizacion p01-p99:
  - BIP media raw 0,029 -> winsor 0,081.
  - QR_OTHER media raw 0,025 -> winsor 0,083.
  - QR_RED media raw 0,296 -> winsor 0,330.
- La senal de QR_RED con mayor `share_mujeres` sobrevive winsorizacion, pero la variable queda menos limpia para un main econometrico.
- Decision: no incluir `share_mujeres` raw en baseline. Usar `mujeres_winsor_p01_p99` como sensibilidad econometrica y como feature ML.

Cuantiles socioeconomicos:

- Educacion:
  - QR total sube de 13,1% en Q1 a 17,8% en Q5.
  - QR_RED sube de 0,9% en Q1 a 5,0% en Q5.
  - QR_OTHER sube hasta Q4 y baja en Q5.
- D+E proxy:
  - QR total cae de 16,9% en Q1 a 14,2% en Q5.
  - QR_RED cae de 4,46% en menor D+E a 1,18% en mayor D+E.
  - QR_OTHER no cae de forma monotona.
- Edad:
  - QR total cae en zonas mas envejecidas.
  - QR_RED sube levemente con edad.
  - QR_OTHER baja con edad.
- Discapacidad:
  - relacion negativa clara con QR, especialmente QR_RED.
  - QR_RED cae de 4,08% en menor discapacidad a 0,96% en mayor discapacidad.
- Inmigrantes:
  - QR total sube de 13,6% a 16,8%.
  - La senal parece mas asociada a QR_OTHER; QR_RED es no monotonico y cae en Q5.
- Asistencia parvular:
  - QR_RED sube fuerte en Q4-Q5.
  - QR_OTHER baja en Q5.

Colinealidad socioeconomica:

- Educacion vs discapacidad: -0,73.
- Educacion vs D+E proxy: -0,64.
- Educacion vs home_macro_oriente: +0,62.
- D+E proxy vs home_macro_oriente: -0,53.
- Mujeres vs asistencia parvular: +0,52.
- Asistencia parvular vs home_macro_oriente: +0,52.
- Implicancia: educacion, D+E, discapacidad y macrozona Oriente compiten por parte de la misma senal territorial/socioeconomica.

Decision sobre target:

- El binario `QR vs BIP` sigue siendo util como sintesis principal simple.
- El multiclase `BIP / QR_OTHER / QR_RED` queda metodologicamente justificado porque QR_RED y QR_OTHER muestran perfiles residenciales distintos.
- Colapsar QR_RED dentro de QR diluye la senal mas limpia de heterogeneidad, porque QR_OTHER domina el universo QR y se parece mas a BIP.
- En modelos, el multiclase debe evaluarse como analisis explicativo de heterogeneidad, no necesariamente como clasificador duro de QR_RED.

Set socioeconomico candidato para econometrico:

- Baseline parsimonioso:
  - `educacion_univ_mas`.
  - `de_income_proxy` (D+E proxy, con nombre claro).
  - `edad_promedio`.
  - `discapacidad`.
  - `inmigrantes`.
  - `asistencia_parv`.
- Excluir de baseline:
  - `mujeres` raw.
- Sensibilidades:
  - agregar `mujeres_winsor_p01_p99`.
  - probar edad como franjas/quintiles, dado que la relacion con QR_RED y QR_OTHER no es lineal comun.
  - probar sin discapacidad.
  - probar sin D+E proxy.
  - probar sin home_macrozone para ver cuanto absorbe macrozona Oriente.

Set socioeconomico para ML:

- Incluir variables residenciales amplias, con limpieza:
  - educacion.
  - D+E proxy.
  - edad.
  - discapacidad.
  - inmigrantes.
  - mujeres winsorizada.
  - asistencia parvular.
- Permitir que modelos no lineales capturen relaciones no monotonicas y diferencias QR_RED/QR_OTHER.

Bloque futuro de separabilidad:

- Despues de Bloque 6B y 6C, agregar Bloque 7: separabilidad QR_OTHER vs BIP y QR vs BIP.
- Objetivo: buscar variables que separen mejor el binario o particularmente QR_OTHER de BIP.
- Salidas candidatas:
  - diferencias estandarizadas BIP vs QR_OTHER, BIP vs QR_RED y QR vs BIP;
  - univariate AUC/PR-AUC por variable;
  - QR share por deciles;
  - screening simple de interacciones, por ejemplo cohorte x macrozona, modo x macrozona, educacion x D+E.

## 2026-05-28 — EDA panel Bloque 6B: infraestructura/oferta OSM

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Universo:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro: `home_confidence == "alta"` y `n_viajes >= 3`.
- Resultado: 2.460.264 tarjetas y 43.647.285 viajes.
- Share QR total: 15,34%; QR_OTHER 13,19%; QR_RED 2,16%.

Cobertura:

- Variables `origin_top1_osm_*`: missing 0,24%.
- Variables `origin_top2_osm_*`: missing 0,52%.
- Variables `activity_top1_osm_*`: missing 0,20%.
- Decision: la cobertura OSM es suficiente para modelar sin perdida relevante.

Variables auditadas:

- `playground`.
- `school`.
- `university`.
- `shelter`.
- `subway_entrance`.
- Fuentes: `origin_top1`, `origin_top2`, `activity_top1`.

Distribuciones:

- `university` es muy sparse/concentrada:
  - mediana en el minimo para origin top-1, origin top-2 y activity top-1.
  - p99 muy alto, sobre 13 z.
  - no debe usarse como continua raw en econometrico.
- `subway_entrance` tambien tiene masa en minimo y cola alta, pero es mas interpretable como accesibilidad ferroviaria/centralidad.
- `shelter` y `school` son mas universales y mejor comportadas, aunque no necesariamente separan QR.
- `playground` tiene senal moderada, pero lectura conductual menos directa.

Medias por target:

- Las diferencias OSM entre BIP y QR_OTHER son muy pequenas.
- QR_RED se diferencia algo mas, pero menos que en socioeconomia/geografia:
  - mayor `origin_top1_playground`: +0,047 z vs BIP.
  - menor `origin_top1_school`: -0,107 z vs BIP.
  - mayor `origin_top1_university`: +0,091 z vs BIP.
  - menor `origin_top1_shelter`: -0,035 z vs BIP.
  - mayor `origin_top1_subway_entrance`: +0,047 z vs BIP.
- La senal OSM no es suficientemente fuerte para ser bloque central del main econometrico.

Comparacion de fuentes:

- `origin_top1` y `activity_top1` estan muy correlacionados para la misma variable:
  - playground: 0,75.
  - school: 0,74.
  - university: 0,76.
  - shelter: 0,77.
  - subway_entrance: 0,75.
- Decision: no usar `activity_top1_osm_*` junto con `origin_top1_osm_*` en econometrico.
- `origin_top1` y `origin_top2` casi no se correlacionan:
  - correlaciones entre 0,01 y 0,11.
- Interpretacion: top-2 puede aportar informacion distinta, pero su lectura econometrica es mas dificil. Queda para sensibilidad/ML.

Cuantiles origin top-1:

- `shelter`: relacion no monotonica; QR sube en cuantiles medios y baja en Q5.
- `subway_entrance`: no monotona; Q4 sube pero Q3 baja.
- `university`: solo genera dos grupos utiles por empates/sparsity; QR total apenas cambia de 15,2% a 15,9%; QR_RED sube de 2,03% a 2,67%.
- `school`: no monotona; QR_RED baja en cuantiles altos.
- `playground`: senal moderada, no muy interpretable como driver.

Decision econometrica:

- OSM queda fuera del main inicial.
- Sensibilidad OSM acotada:
  - agregar `origin_top1_university_high_dummy` en vez de `origin_top1_university` continua raw.
  - agregar `origin_top1_school`.
- Sensibilidades OSM ampliadas solo si hay tiempo o si ML/SHAP indica valor:
  - `origin_top1_subway_entrance_winsor`.
  - variables `origin_top2_*`.
- No usar `activity_top1_osm_*` en econometrico inicial por redundancia con `origin_top1`.

Decision ML:

- Incluir OSM amplio como features candidatas:
  - `origin_top1_osm_*`.
  - `origin_top2_osm_*`.
  - `activity_top1_osm_*`.
- Crear transformaciones para variables sparse/colas:
  - winsor p99 para `university` y `subway_entrance`.
  - dummies high/presence para `university`.
- No esperar que OSM sea el bloque dominante; usar ML para confirmar si aporta senal no lineal o interacciones.

## 2026-05-28 — EDA panel Bloque 6C: colinealidad conjunta

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Universo:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro: `home_confidence == "alta"` y `n_viajes >= 3`.
- Resultado: 2.460.264 tarjetas y 43.647.285 viajes.
- Share QR total: 15,34%.

Transformaciones fijadas en el bloque:

- `origin_top1_university_high_dummy` usa corte p75 de `origin_top1_university`: 0,328901.
- `res_mujeres_winsor_p01_p99` usa bounds p01=-1,361799 y p99=1,466959.

Cobertura conjunta:

- No hay variables base ausentes.
- Missing socio/macrozona residencia: 0,321%.
- Missing origen top-1/OSM reducido: 0,237%.
- Variables de uso: 0% missing salvo `t_espera_ini_mean_min`, con 0,013%.
- Decision: para logit basta eliminacion de filas con missing; para ML usar imputacion simple/indicador si se requiere.

Colinealidad principal:

- Intensidad/exposicion:
  - `n_viajes` vs `n_dias_activos`: r=0,968.
  - `n_viajes` vs `n_semanas_activas`: r=0,842.
  - `n_dias_activos` vs `n_semanas_activas`: r=0,876.
- Modal/operacional:
  - `t_espera_ini_mean_min` vs `share_trips_solo_metro`: r=-0,900.
- Geografia:
  - `home_macro_poniente` vs `origin_top1_macro_poniente`: r=0,818.
  - `home_macro_oriente` vs `origin_top1_macro_oriente`: r=0,662.
- Socioeconomia:
  - `res_educacion` vs `res_discapacidad`: r=-0,729.
  - `res_educacion` vs `res_de_proxy`: r=-0,644.
  - `res_educacion` vs `home_macro_oriente`: r=0,620.
- Estabilidad espacial:
  - `origin_zone_top1_share` vs `origin_zone_entropy`: r=-0,704.

Diferencias estandarizadas por target:

- Para binario `QR vs BIP`, las diferencias univariadas mas grandes son moderadas:
  - `share_trips_2025`: +0,247.
  - `hora_mean`: +0,140.
  - `n_dias_activos`: -0,129.
  - `res_educacion`: +0,126.
  - `n_viajes`: -0,126.
  - `share_trips_metro_bus`: -0,125.
  - `res_discapacidad`: -0,111.
- Para `QR_OTHER vs BIP`, la separacion es debil y parecida al binario:
  - `share_trips_2025`: +0,245.
  - `n_dias_activos`: -0,148.
  - `n_viajes`: -0,146.
  - `hora_mean`: +0,142.
  - `share_trips_metro_bus`: -0,130.
  - variables socioeconomicas casi no separan, salvo diferencias pequenas en `share_no_lab`, `res_edad` e `inmigrantes`.
- Para `QR_RED vs BIP`, la separacion es mucho mas clara y principalmente socio-geografica:
  - `res_educacion`: +0,734.
  - `home_macro_oriente`: +0,683.
  - `origin_top1_macro_oriente`: +0,561.
  - `res_discapacidad`: -0,532.
  - `res_de_proxy`: -0,527.
  - `res_parv`: +0,442.
- Interpretacion: el binario `QR vs BIP` esta dominado por diferencias temporales/intensidad de uso, mientras que el multiclase revela que `QR_RED` es el grupo con perfil socioeconomico y geografico claramente distinto. `QR_OTHER` sigue siendo el caso dificil de separar de BIP.

Decision econometrica:

- Mantener un main parsimonioso y no probar sensibilidades ilimitadas.
- Exposicion temporal:
  - incluir `share_trips_2025`;
  - incluir solo una medida de intensidad, preferentemente `n_viajes` o `log1p(n_viajes)`;
  - no incluir simultaneamente `n_viajes`, `n_dias_activos` y `n_semanas_activas`.
- Uso/modal:
  - mantener `share_trips_solo_metro` como patron modal;
  - dejar `t_espera_ini_mean_min` como sensibilidad operacional por alta correlacion con modo metro.
- Geografia:
  - mantener main con `home_macrozone + origin_top1_macrozone`;
  - interpretar con cuidado porque residencia y origen frecuente se solapan, especialmente en Poniente y Oriente.
- Socioeconomia:
  - mantener `educacion` y D+E proxy;
  - decidir `discapacidad` segun foco interpretativo: puede quedar en main si se quiere discutir, o como sensibilidad si se busca menor redundancia socioeconomica.
- Target:
  - mantener binario como especificacion principal simple;
  - mantener multiclase como extension necesaria para no ocultar la heterogeneidad fuerte de `QR_RED`.
  - agregar Bloque 7 para buscar senal especifica que separe mejor `QR_OTHER` de `BIP`, porque las diferencias actuales son pequenas.
- Estabilidad espacial:
  - no incluir juntos `origin_zone_top1_share` y `origin_zone_entropy` en main;
  - usar `origin_zone_entropy` como sensibilidad si se quiere capturar dispersion espacial.
- OSM:
  - mantener fuera del main;
  - sensibilidad acotada con `origin_top1_university_high_dummy` y `origin_top1_school`.

Decision ML:

- Mantener set amplio de features, incluyendo variables correlacionadas.
- XGBoost/arboles pueden usar la variable solapada que mas mejora el split, pero la interpretacion variable-a-variable puede volverse inestable.
- Para interpretar ML, preferir SHAP por familias o comparacion por bloques: socioeconomia, uso, geografia, OSM.

Cierre de bloque:

- Bloque 6C documentado.
- Siguiente paso: Bloque 7 de separabilidad para buscar variables que distingan mejor `QR_OTHER` vs `BIP` y `QR` vs `BIP`.

## 2026-05-28 — EDA panel Bloque 7: separabilidad supervisada exploratoria

Notebook:

- `02_eda/eda_user_level_panel.qmd`.

Universo:

- `user_level_payment_panel_interannual_ml_clean.parquet`.
- Filtro: `home_confidence == "alta"` y `n_viajes >= 3`.
- Resultado base: 2.460.264 tarjetas y 43.647.285 viajes.

Subpaneles pairwise:

- `QR vs BIP`: 2.460.264 tarjetas; positivos QR 377.495; prevalencia 15,34%.
- `QR_OTHER vs BIP`: 2.407.190 tarjetas; positivos QR_OTHER 324.421; prevalencia 13,48%.
- `QR_RED vs QR_OTHER`: 377.495 tarjetas; positivos QR_RED 53.074; prevalencia 14,06%.
- `QR_RED vs BIP` diagnostico: 2.135.843 tarjetas; positivos QR_RED 53.074; prevalencia 2,48%.

Ranking univariado:

- Para `QR_OTHER vs BIP`, ninguna variable cruda separa fuerte.
- Mejores senales univariadas:
  - `share_trips_2025`: AUC 0,568; lift top-10 1,17.
  - `n_viajes` invertida: AUC abs 0,551; lift top-10 1,23.
  - `hora_std`: AUC 0,545; lift top-10 1,28.
  - `hora_mean`: AUC 0,541; lift top-10 1,24.
- Para `QR vs BIP`, el patron es casi igual, lo que sugiere que el binario esta dominado por el comportamiento de `QR_OTHER`.
- Para `QR_RED vs QR_OTHER`, la separacion univariada es bastante mayor:
  - `res_educacion`: AUC 0,677; lift top-10 2,55.
  - `res_discapacidad` invertida: AUC abs 0,650; lift top-10 1,83.
  - D+E proxy invertido: AUC abs 0,649; lift top-10 2,24.
  - `home_macro_oriente`: AUC 0,630; lift top-10 2,28.

Redundancia temporal:

- `share_trips_2025` casi no se correlaciona con intensidad:
  - r con `n_viajes`: 0,001.
  - r con `n_dias_activos`: 0,003.
  - r con `n_semanas_activas`: 0,026.
- Decision: `share_trips_2025` debe tratarse como dimension temporal/cohorte distinta, no como proxy de intensidad.
- `n_viajes`, `n_dias_activos` y `n_semanas_activas` si estan fuertemente correlacionadas; usar solo una en logit main.

Bins y franjas:

- Para `QR_OTHER vs BIP`, los bins mejoran la lectura pero no generan separacion fuerte:
  - `share_trips_2025_bin = mayor_2025`: tasa 20,9% vs base 13,5%; lift 1,55; 3,6% de la muestra.
  - `hora_mean_bin = noche`: tasa 19,6%; lift 1,46; 0,6% de la muestra.
  - `hora_std_Q5`: tasa 16,6%; lift 1,23; 19,9% de la muestra.
  - `n_viajes_bin = 03-04`: tasa 16,1%; lift 1,19; 25,3% de la muestra.
- Para `QR_RED vs QR_OTHER`, los bins socioeconomicos muestran separacion clara:
  - `educ_Q5`: tasa QR_RED 28,4% vs base 14,1%; lift 2,01.
  - `de_Q1`: tasa 26,4%; lift 1,88.
  - `disc_Q1`: tasa 24,0%; lift 1,71.

Cruces acotados de bins:

- Para `QR_OTHER vs BIP`, los mejores cruces combinan cohorte/recencia, intensidad y dispersion horaria.
- Segmentos destacados:
  - `mayor_2025 | hora_std_Q4`: tasa 23,5% vs base 13,5%; lift 1,75; 23.570 tarjetas.
  - `mixto | n_viajes 03-04`: tasa 22,1%; lift 1,64; 64.672 tarjetas.
  - `mayor_2025 | n_viajes 10-19`: tasa 21,7%; lift 1,61; 27.368 tarjetas.
  - `solo_2025 | n_viajes 03-04`: tasa 19,0%; lift 1,41; 261.176 tarjetas.
- Lectura exploratoria: `QR_OTHER` parece concentrarse en perfiles recientes/2025, de menor intensidad y mayor dispersion horaria. Es una hipotesis descriptiva, no una conclusion causal.

Probe con arbol interpretable:

- Configuracion:
  - `DecisionTreeClassifier`.
  - `max_depth = 4`.
  - `min_samples_leaf = 20.000`.
  - `class_weight = "balanced"`.
  - Usado solo como diagnostico de separabilidad; no como modelo final.
- Tareas:
  - `QR_OTHER vs BIP`: AUC 0,588; average precision 0,174; base 0,135.
  - `QR vs BIP`: AUC 0,592; average precision 0,198; base 0,153.
  - Multiclase `BIP / QR_OTHER / QR_RED`: balanced accuracy 0,451; macro-F1 0,293; ROC-AUC macro 0,595.
  - `QR_RED vs QR_OTHER`: AUC 0,668; average precision 0,246.
  - `QR_RED vs BIP` diagnostico: AUC 0,701; average precision 0,059; base 0,025.

Importancias del arbol:

- `QR_OTHER vs BIP`:
  - `recent_low_intensity`: 0,366.
  - `high_hora_std_q4_q5`: 0,260.
  - `no_metro_bus`: 0,109.
  - `recent_majority_2025`: 0,084.
  - `recent_high_hora_std`: 0,067.
- `QR vs BIP`:
  - `recent_majority_2025`: 0,350.
  - `high_hora_std_q4_q5`: 0,224.
  - `no_metro_bus`: 0,118.
  - `low_intensity_high_hora_std`: 0,102.
  - `low_intensity_3_9`: 0,097.
- `QR_RED vs BIP` diagnostico:
  - `educ_q5`: 0,663.
  - `high_hora_std_q4_q5`: 0,179.
  - `solo_2025`: 0,074.
  - `home_macro_oriente`: 0,036.
- `QR_RED vs QR_OTHER`:
  - `home_macro_oriente`: 0,877.
  - `pt_bajo_medio`: 0,066.
  - `high_hora_std_q4_q5`: 0,033.

Matriz de confusion multiclase del arbol:

- Verdadero BIP:
  - 39,4% predicho BIP.
  - 43,5% predicho QR_OTHER.
  - 17,1% predicho QR_RED.
- Verdadero QR_OTHER:
  - 30,3% predicho BIP.
  - 52,5% predicho QR_OTHER.
  - 17,2% predicho QR_RED.
- Verdadero QR_RED:
  - 17,8% predicho BIP.
  - 38,8% predicho QR_OTHER.
  - 43,4% predicho QR_RED.
- Lectura exploratoria: el arbol reconoce parcialmente `QR_RED`, pero lo confunde mas con `QR_OTHER` que con BIP. Esto apoya explorar multiclase como heterogeneidad dentro de QR, aunque predictivamente no sea limpio.

Finding exploratorio / hipotesis:

- `QR_OTHER` no presenta una frontera univariada fuerte frente a BIP.
- Las senales mas consistentes para `QR_OTHER` son conductuales-temporales:
  - mayor peso de viajes 2025;
  - baja intensidad de uso;
  - mayor dispersion horaria;
  - menor uso combinado metro-bus.
- `QR_RED` muestra una separacion mas clara y de naturaleza socio-geografica:
  - mayor educacion residencial;
  - menor concentracion D+E proxy;
  - menor discapacidad residencial;
  - fuerte asociacion con macrozona Oriente.
- Esto queda documentado como hipotesis de trabajo del EDA, no como resultado causal ni especificacion final.

Siguientes pasos sugeridos:

- Probar una version logit/probe con estas flags para verificar signos y estabilidad.
- Usar estos hallazgos para definir features candidatas del ML y sensibilidades acotadas del main econometrico.

## 2026-05-28 — EDA breve fuente externa: puntos de carga bip!

Objetivo:

- Evaluar si conviene usar solo `Puntos bip!` o una red completa de carga bip! fisica para construir variables de friccion BIP.

Fuentes oficiales descargadas:

- `puntos_bip`: `/Volumes/KINGSTON/tesis-project/raw/pcma_20240917-oficio-4770_2013.xlsx`.
- `retail`: `/Volumes/KINGSTON/tesis-project/raw/bip_load_points/retail_20240917_oficio-4770_2013.xlsx`.
- `centro_normal`: `/Volumes/KINGSTON/tesis-project/raw/bip_load_points/pcmav-estandar-normal_20240917_oficio-4770_2013.xlsx`.
- `centro_alto`: `/Volumes/KINGSTON/tesis-project/raw/bip_load_points/pcmav-alto-estandar_20240917_oficio-4770_2013.xlsx`.
- `metro`: `/Volumes/KINGSTON/tesis-project/raw/bip_load_points/metro_20240917_oficio-4770_2013.xlsx`.

Lectura de archivos:

- Las planillas son homologables pero tienen encabezados en filas distintas.
- Se usaron solo hojas abiertas/vigentes:
  - `PCMA`.
  - `Abiertos`.
  - `Abierto`.
- Se excluyo hoja `Cerrados` del archivo retail.
- Todas las fuentes tienen coordenadas `LONGITUD`/`LATITUD`.

Conteos normalizados:

- `puntos_bip`: 1.579 registros.
- `retail`: 169 registros.
- `metro`: 143 registros.
- `centro_normal`: 29 registros.
- `centro_alto`: 7 registros.
- Total union raw abierta: 1.927 registros.
- Missing coordenadas: 0.
- Rango coordenadas:
  - lon: -71,220657 a -70,499199.
  - lat: -33,808266 a -33,201782.

Duplicados:

- Por `codigo`:
  - 7 grupos duplicados, 143 filas.
  - 0 grupos cross-type.
  - Interpretacion: no sirve como llave global; en Metro el codigo puede repetirse por linea/estacion.
- Por coordenada exacta a 6 decimales:
  - 23 grupos duplicados, 47 filas.
  - 7 grupos cross-type, 14 filas.
- Por coordenada redondeada a 5 decimales:
  - mismo resultado que 6 decimales.
- Por direccion+comuna:
  - 10 grupos duplicados, 20 filas.
  - 2 grupos cross-type, 4 filas.

Ejemplos de solapamiento cross-type:

- Retail `LIDER HIPER CORDILLERA` y centro normal en `AV. LOS TOROS 5441`, Puente Alto.
- Metro `LOS LEONES L1` y retail `LIDER EXPRESS LYON` en `AV. NUEVA PROVIDENCIA 2249`, Providencia.
- Punto bip `TABAQUERIA 901` y retail `LIDER EXPRESS AV. RECOLETA` en `AV. RECOLETA 901`, Recoleta.
- Punto bip y retail en `AV. AMERICO VESPUCIO 1737`, Huechuraba.

Finding exploratorio:

- Las fuentes son mayoritariamente complementarias.
- El solapamiento exacto entre tipos existe, pero es bajo: 14 filas en grupos cross-type por coordenada exacta sobre 1.927 registros.
- Usar solo `Puntos bip!` captura la mayor parte de registros, pero omite Metro/Retail/Centros, que son puntos relevantes de carga fisica y probablemente importantes para friccion BIP.

Decision provisional:

- Para construir variables de friccion BIP, usar red completa abierta:
  - puntos bip + retail + metro + centros normal + centros alto.
- Deduplicar por coordenada exacta/redondeada antes de calcular densidades/distancias.
- Mantener sensibilidad simple `puntos_bip_only` para verificar si los resultados dependen de incluir retail/metro/centros.
- No sobrecomplejizar por tipo de punto en el main inicial; primero usar:
  - distancia al punto de carga mas cercano;
  - densidad/conteo de puntos de carga en zona o radio;
  - indicador de baja accesibilidad.

Artefacto construido:

- Script: `scripts/audits/build_bip_load_access_zona777.py`.
- Output principal: `tmp/audits/bip_load_access/bip_load_access_by_zona777.parquet`.
- Outputs auxiliares:
  - `tmp/audits/bip_load_access/bip_load_points_raw_open.parquet`.
  - `tmp/audits/bip_load_access/bip_load_physical_locations.parquet`.
  - `tmp/audits/bip_load_access/bip_load_access_summary.json`.
  - `tmp/audits/bip_load_access/bip_load_source_type_counts.csv`.
  - `tmp/audits/bip_load_access/bip_load_zone_summary.csv`.

Construccion del lookup:

- Limpia planillas oficiales.
- Deduplica ubicaciones fisicas por `lon/lat` redondeado a 5 decimales.
- Carga shapefile oficial de zonas 777:
  - `/Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp`.
- Usa CRS zona 777 como `EPSG:4674` y distancias/areas en `EPSG:32719`.
- Spatial join puntos-en-poligono para conteo por zona.
- Distancia nearest calculada desde centroide de zona al punto fisico de carga mas cercano.

Columnas del lookup:

- `ZONA777`.
- `AREA_M2`.
- `AREA_KM2`.
- `bip_load_n_points_zone`.
- `bip_load_has_point_zone`.
- `bip_load_density_km2`.
- `bip_load_location_id`.
- `bip_load_dist_nearest_m`.

Diagnostico del lookup:

- Registros raw abiertos: 1.927.
- Ubicaciones fisicas deduplicadas: 1.903.
- Zonas 777: 803.
- Ubicaciones fuera de zonas 777: 28.
- Ubicaciones asignadas a zonas: 1.875.
- Zonas con al menos un punto de carga: 632 (78,7%).
- Zonas sin punto de carga: 171 (21,3%).
- Maximo de puntos en una zona: 19.
- Distancia centroide-zona al punto mas cercano:
  - mediana: 297 m.
  - p75: 460 m.
  - p90: 730 m.
  - maximo: 4.854 m.

Advertencia metodologica:

- `bip_load_dist_nearest_m` usa centroide de zona como proxy de ubicacion residencial/actividad.
- En zonas grandes, la distancia desde centroide puede ser alta incluso si `bip_load_has_point_zone == 1`.
- Por eso, para modelar friccion espacial conviene usar conjuntamente:
  - distancia al punto mas cercano;
  - dummy de presencia en zona;
  - conteo o densidad como sensibilidad.

## 2026-05-29 - Redundancias exactas en matriz usuario-feature

El `healthcheck_user_model_matrix.py` confirma matriz sana en version/target/id/leakage, pero detecta pares con correlacion exacta o complementaria que deben tratarse antes de logits interpretables:

- `coarse_route_has_early_late_rcs` y `service_route_has_early_late_rcs` son identicas (`r=+1`). Para specs logit conservar `service_route_has_early_late_rcs`, porque acompaña la variable principal `service_route_early_late_rcs`.
- `service_within_od_top_share_weighted` y `service_within_od_variability_weighted` son complementarias exactas (`r=-1`). Para specs logit conservar `service_within_od_top_share_weighted`, por interpretabilidad como stickiness dentro del OD.
- `offer_origin_bus_like_share` y `offer_origin_metro_like_share` son composicionales (`r=-1`). Para specs logit conservar una sola; preferencia actual: `offer_origin_bus_like_share`, dejando metro como base implicita.

Decision:

- No invalida la matriz para ML, pero en logit no deben entrar ambos miembros de cada par.
- Documentar esto como regla de especificacion: remover redundancias exactas/composicionales antes de estimar modelos interpretables.
- `logit_main` actual no incluye los pares 2 y 3, pero las specs wide/sensibilidad si pueden heredarlos; aplicar filtro o lista de exclusion al construir `X`.

## 2026-05-30 - Diagnostico de techo predictivo (XGBoost): gate cerrado

Objetivo: medir CON NUMERO cuanta señal hay en la matriz supervisada para
separar QR de BIP, antes de invertir en bloques nuevos de variables (BIP
friction, digital-territorial, info-need). Responde la duda recurrente de
por que QR_OTHER no se separa de BIP.

Script: `scripts/audits/diagnose_ceiling_xgb_gpboost.py`.
Universo: `interannual_ml_clean + home_alta + n_viajes>=3` (2.460.264 tarjetas).
Modo: XGBoost, `feature-source=contract` (union de feature_sets del JSON,
102 features), submuestra 200k, 150 arboles, 5-fold OOF. Es quick: orden de
magnitud robusto, techo absoluto puede afinarse +-0,01-0,02 al completo.

Tres corridas:

- random (StratifiedKFold por fila = por tarjeta):
  - binario QR vs BIP: AUC 0,671, PR-AUC 0,261.
  - multiclase OvR: BIP 0,672, QR_OTHER 0,671, QR_RED 0,738.
  - PR-AUC OvR: BIP 0,914, QR_OTHER 0,230 (base 0,132), QR_RED 0,077 (base 0,022).
- grouped (GroupKFold por `origin_zone_top1`, generalizacion a zonas no vistas):
  - binario AUC 0,668; QR_OTHER 0,668; QR_RED 0,737.
  - gap random-grouped ~0,003 en todos los frentes.
- ablacion por familia (random, quitando una familia a la vez):
  - drop_use: AUC 0,649 (Δ -0,022). UNICA caida no trivial.
  - drop_geo, drop_socio, drop_route: Δ ~ -0,001.
  - drop_osm, drop_offer, drop_bip, drop_hybrid, drop_cohort: Δ ~ 0.

Hallazgos:

- Techo binario QR vs BIP ~ 0,67 y plano. No es clasificador fuerte; es
  identificacion de perfiles asociados. Confirma con numero la "separacion
  moderada" del cierre de EDA (2026-05-29).
- El OvR de QR_OTHER queda practicamente igual al binario (ambos ~0,67),
  consistente con que QR_OTHER domina el grupo QR (86% del QR). Separar
  QR_OTHER de BIP parece ser el caso dificil que limita el binario entero.
  Respuesta cuantitativa a la duda original.
- QR_RED es el mas separable (OvR 0,738) pero minoritario (2,16%); su señal
  se diluye en el binario.
- Poca evidencia de memorizacion espacial local: gap random-grouped ~0. La
  capacidad predictiva se mantiene al evaluar en zonas origen no observadas,
  lo que sugiere que el desempeño no depende fuertemente de memorizar la zona
  de origen principal.
- Cohorte temporal redundante: drop_cohort no baja el AUC (incluso +0,001).
  `share_trips_2025` era la mejor señal univariada para QR_OTHER en Bloque 7,
  pero su aporte MARGINAL sobre el resto es nulo; esta contenida en otras
  features. Matiza la narrativa "QR_OTHER es puramente temporal".
- Solo la familia conductual `use` aporta señal marginal insustituible
  (-0,022). Todo lo TERRITORIAL (geo, socio, osm, bip, offer) aporta ~0
  marginal sobre el resto.

Decision / gate:

- El cuello de QR_OTHER no parece ser falta de variables territoriales: no
  aparece un perfil territorial suficientemente fuerte como para mejorar el
  techo predictivo flexible. Agregar BIP friction, digital-territorial o un
  bloque espacial fino probablemente no va a separar QR_OTHER de BIP por si
  solo. drop_bip = 0 es evidencia en esa direccion (las 9 features de
  friccion BIP no mueven el AUC).
- Conclusion sustantiva: QR_OTHER es adopcion DIFUSA/transversal, no
  segmentada territorialmente. QR_RED si tiene nicho socio-geografico
  (Oriente, educacion alta). Esto es hallazgo, no fracaso.
- No priorizar bloques externos pendientes con la expectativa de subir AUC o
  separar QR_OTHER. Construirlos solo si tienen valor conceptual, valor
  descriptivo o sirven como sensibilidad especifica. Si en algun momento el
  foco fuera explicar QR_RED, lo territorial tiene un rol menor (drop_socio
  baja su OvR 0,738->0,734; drop_geo ->0,736).
- Caveat: ablacion mide aporte MARGINAL; con familias correlacionadas una
  puede aportar poco marginal aunque tenga señal (otra la cubre). geo/socio
  aportan ~0 marginal en parte porque QR_OTHER domina el binario y no se
  distingue territorialmente, no porque la geografia sea irrelevante en si.

Confirmacion al completo + GPBoost (corrida 2026-05-30, dataset completo
2,46M, 500 arboles XGBoost; GPBoost sobre submuestra 250k con XGBoost de
referencia en la MISMA submuestra/folds):

- XGBoost full al completo: binario AUC 0,681 (vs 0,671 del quick). El techo
  sube ~0,01 al usar 500 arboles y dataset completo, sin cambio cualitativo.
  Ablacion identica: solo `drop_use` baja (-0,019); territorial ~0.
- Bloque GPBoost en submuestra 250k (comparacion limpia):
  - xgb_subsample: AUC 0,669.
  - gpb_boost_only: AUC 0,669 (identico a XGBoost; valida implementaciones).
  - gpb_gp_spatial: AUC 0,658. El termino Gaussian Process espacial RESTA
    0,011, no suma.
  - OvR del GP: QR_RED 0,698 (mejor), QR_OTHER 0,655 (peor).
- Lectura: ni un modelo espacial dedicado (GPBoost, kernel Matern sobre
  coords UTM 19S, gp_approx vecchia 30 vecinos) encuentra estructura
  geografica util para separar QR de BIP. El GP suaviza sobre coordenadas y
  perjudica levemente. Es el cierre mas fuerte del gate: cuatro metodos
  (ablacion, grouped, drop_geo/bip, GP espacial) coinciden en que la
  geografia no separa QR_OTHER de BIP a nivel tarjeta.
- Costo GPBoost: ~16s/fold boost-only, ~90-290s/fold con GP. Para
  produccion masiva el GP no se justifica dado que resta.

Outputs: `tmp/audits/user_level_redesign/ceiling_xgb_*` y `ceiling_gpboost_*`
con sufijo `interannual_ml_clean_alta_n3_contract_{random,grouped}`.

## 2026-05-31 - Sensibilidad universo: soporte minimo de residencia (`home>=3`)

Objetivo: verificar si el techo predictivo cambia al exigir que la residencia
inferida tenga soporte minimo, no solo `home_confidence=alta`. Se agrega el
filtro `n_home_dest_trips_card >= 3` manteniendo `n_viajes >= 3`.

Cambios de codigo:

- `scripts/audits/build_user_model_matrix.py` agrega `--min-home-trips`.
- `scripts/audits/diagnose_ceiling_xgb_gpboost.py` agrega `--min-home-trips`.
- Los artefactos con esta sensibilidad usan sufijo `..._n3_home3` para no
  mezclarse con el universo main.

Matriz:

- Output: `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n3_home3.parquet`.
- Filas: 1.493.677 tarjetas, vs 2.460.264 en el main `n3`.
- Tasa QR baja de 0,1534 a 0,1429:
  - BIP 0,8571.
  - QR_OTHER 0,1204.
  - QR_RED 0,0225.

Diagnostico XGBoost quick (`feature-source=contract`, 200k, 150 arboles, sin GPBoost):

- Random:
  - binario QR vs BIP: AUC 0,6886, PR-AUC 0,2625.
  - multiclase macro OvR: AUC 0,7109.
  - OvR: BIP 0,690; QR_OTHER 0,684; QR_RED 0,759.
  - PR-AUC OvR: BIP 0,925; QR_OTHER 0,223; QR_RED 0,091.
- Grouped por `origin_zone_top1`:
  - binario QR vs BIP: AUC 0,6855, PR-AUC 0,2586.
  - multiclase macro OvR: AUC 0,7088.
  - OvR: BIP 0,687; QR_OTHER 0,681; QR_RED 0,758.
  - PR-AUC OvR: BIP 0,924; QR_OTHER 0,220; QR_RED 0,090.

Lectura:

- Exigir soporte minimo de residencia mejora el AUC binario en torno a +0,017
  respecto del main quick (`~0,671 -> ~0,689`), pero tambien cambia fuerte el
  universo y reduce la tasa QR.
- El gap random-grouped sigue chico (~0,003), por lo que el resultado no parece
  depender de memorizar la zona de origen.
- Esta sensibilidad sugiere que usuarios con residencia mas estable son mas
  separables, pero no cambia la conclusion principal: el techo sigue moderado y
  QR_OTHER continua siendo el caso dificil frente a BIP.

Corrida full XGBoost sobre `home>=3` (contract, random, sin GPBoost;
2026-06-02, paridad con el full main n3):

- full binario AUC 0,7011; PR-AUC 0,2752.
- multiclase macro OvR AUC 0,7229; balanced accuracy 0,3359.
- OvR: BIP 0,701; QR_OTHER 0,697; QR_RED 0,770.
- PR-AUC OvR: BIP 0,929; QR_OTHER 0,236; QR_RED 0,097.
- drop_use: 0,6755 (Δ -0,026). UNICA caida notable.
- drop_geo: 0,6982 (Δ -0,003).
- drop_route, drop_socio: Δ -0,001.
- drop_osm, drop_offer, drop_bip, drop_hybrid, drop_cohort: Δ ~0.

Comparacion contra el full main `home_alta + n_viajes>=3`:

- filas: 2.460.264 -> 1.493.677 (pierde ~39% del universo).
- tasa QR: 0,1534 -> 0,1429.
- binario AUC: 0,6814 -> 0,7011 (Δ +0,0197).
- PR-AUC: 0,2731 -> 0,2752 (Δ +0,0021).
- macro OvR AUC: 0,7064 -> 0,7229 (Δ +0,0165).

Hallazgo clave (descarta artefacto de medicion residencial):

- `drop_socio` sigue ~0 incluso con residencia bien soportada
  (`n_home_dest_trips_card>=3`, mediana n_viajes ~20). En el main `home_alta`
  el 46% de tarjetas tenia 1 solo viaje HOGAR, lo que abria la hipotesis de
  que las variables socio (asignadas por `zona_hogar`) no separaban por
  RESIDENCIA MAL MEDIDA. Al exigir soporte residencial real, las socio SIGUEN
  sin aportar (Δ -0,001). El cuello territorial es ESTRUCTURAL, no de medicion:
  QR_OTHER no tiene perfil socio-residencial distinto de BIP.
- Mismo patron que el main: solo `use` (conductual) aporta; todo lo
  territorial ~0. El hallazgo del gate es robusto a la definicion de universo.
- Grouped full sobre `home>=3`: binario AUC 0,6982; PR-AUC 0,2719; macro OvR
  AUC 0,7201. Gap random-grouped ~0,003, por lo que la mejora no parece venir
  de memorizar zonas.
- GPBoost quick sobre `home>=3`:
  - lonlat: xgb_subsample AUC 0,6760; boost-only 0,6697; GP espacial 0,6286.
  - UTM 19S: xgb_subsample AUC 0,6759; boost-only 0,6700; GP espacial 0,6287.
  - Lectura: la proyeccion no cambia nada; el componente GP espacial empeora
    fuerte en ambas escalas. No se justifica correr GPBoost completo.
- Outputs: `ceiling_xgb_*_interannual_ml_clean_alta_n3_home3_contract_{random,grouped}.csv`
  y `ceiling_gpboost_*_interannual_ml_clean_alta_n3_home3_contract_random*.csv`.

## 2026-06-02 - Cierre sensibilidades de techo predictivo

Objetivo: cerrar el grid minimo de universos para distinguir entre techo
predictivo real, ruido por usuarios poco observados y ruido por residencia.

Matrices disponibles:

- Main conservador:
  `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n3.parquet`
  (2.460.264 tarjetas).
- Soporte residencial:
  `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n3_home3.parquet`
  (1.493.677 tarjetas).
- Intensidad media:
  `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n5.parquet`
  (1.838.455 tarjetas).
- Intensidad alta:
  `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_n10.parquet`
  (1.286.681 tarjetas).
- Cobertura residencial ampliada:
  `tmp/audits/user_level_redesign/user_model_matrix_interannual_ml_clean_alta_media_n3.parquet`
  (3.380.572 tarjetas).

Resumen XGBoost full random, `feature-source=contract`, sin GPBoost:

| universo | filas | tasa QR | AUC binario | PR-AUC binario | macro OvR AUC | lectura |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `alta_n3` | 2.460.264 | 0,1534 | 0,6814 | 0,2731 | 0,7064 | main conservador |
| `alta_n3_home3` | 1.493.677 | 0,1429 | 0,7011 | 0,2752 | 0,7229 | residencia mejor soportada |
| `alta_n5` | 1.838.455 | 0,1452 | 0,6930 | 0,2720 | 0,7159 | usuarios mas observables |
| `alta_n10` | 1.286.681 | 0,1379 | 0,7068 | 0,2730 | 0,7272 | mayor AUC, fuerte seleccion |
| `alta_media_n3` | 3.380.572 | 0,1539 | 0,6867 | 0,2795 | 0,7107 | mas cobertura, no degrada |

Lectura transversal:

- Subir intensidad (`n_viajes>=5`/`>=10`) mejora ROC-AUC, pero no mejora
  sustantivamente PR-AUC. Usuarios mas frecuentes tienen historiales mas
  estables y se ordenan mejor, pero no aparece un segmento QR mucho mas
  concentrado.
- `home>=3` mejora AUC casi tanto como `n>=10` con menos perdida de muestra.
  Esto sugiere que parte del techo estaba limitado por ruido residencial/perfil
  usuario, pero no cambia el mecanismo: la separacion sigue siendo moderada.
- `alta_media_n3` aumenta cobertura 37% y mejora levemente PR-AUC, sin
  degradar AUC. Para modelos predictivos es defendible como sensibilidad de
  mayor cobertura; para interpretacion residencial mantener `home_alta` como
  especificacion conservadora.
- En todos los universos, la ablacion confirma el mismo patron: `drop_use` es
  la unica caida grande (~0,02-0,03 AUC). `geo`, `socio`, `route`, `offer`,
  `bip`, `hybrid`, `osm` y `cohort` tienen aporte marginal bajo.
- Multiclase: `QR_RED` se mantiene mas separable (OvR ~0,76-0,77), pero es
  minoritario (~2,2%). `QR_OTHER` queda cerca del binario (~0,68-0,70) y es el
  caso que limita el problema QR vs BIP.
- GPBoost queda descartado como mejora practica: boost-only valida la
  implementacion, pero el GP espacial resta tanto en main como en `home>=3`, y
  UTM vs lonlat no cambia el resultado.

Artefactos de diagnostico:

- XGBoost: `tmp/audits/user_level_redesign/ceiling_xgb_*_{suffix}.csv`.
- GPBoost: `tmp/audits/user_level_redesign/ceiling_gpboost_*_{suffix}.csv`.
- Feature contracts por matriz:
  `tmp/audits/user_level_redesign/user_model_matrix_feature_sets_{suffix}.json`.
- Sufijos relevantes:
  `interannual_ml_clean_alta_n3_contract_random`,
  `interannual_ml_clean_alta_n3_contract_grouped`,
  `interannual_ml_clean_alta_n3_home3_contract_random`,
  `interannual_ml_clean_alta_n3_home3_contract_grouped`,
  `interannual_ml_clean_alta_n3_home3_contract_random_utm`,
  `interannual_ml_clean_alta_n5_contract_random`,
  `interannual_ml_clean_alta_n10_contract_random`,
  `interannual_ml_clean_alta_media_n3_contract_random`.

Decision operativa:

- Usar `alta_n3` como universo principal conservador para reporte base.
- Usar `alta_n3_home3`, `alta_n10` y `alta_media_n3` como sensibilidades de
  universo.
- No seguir invirtiendo en GPBoost completo ni en bloques territoriales con la
  expectativa de subir el techo QR_OTHER vs BIP.
- Pasar a especificaciones formales: primero benchmark XGBoost/ML final y luego
  logit principal parsimonioso.

## 2026-06-02 - Plan benchmark ML final user-level

Decision: antes del logit formal, cerrar un benchmark ML reproducible sobre las
matrices user-level finales. El diagnostico de techo (`diagnose_ceiling_*`)
sirvio para decidir universos y descartar GPBoost; el benchmark final debe ser
mas limpio para reporte: metricas completas, predicciones OOF y artefactos de
interpretabilidad.

Arquitectura acordada:

- Crear `scripts/audits/run_user_ml_benchmark.py`.
- No mover aun a `tesis-project-ml`: las matrices canonicas, feature contracts
  y auditorias actuales viven en este repo.
- El script debe cargar matrices existentes, seleccionar feature sets, correr
  XGBoost binario/multiclase, guardar predicciones OOF y metricas.
- Un QMD/notebook posterior solo resumira outputs; no entrenara modelos.

Metricas prioritarias:

- Ranking binario: ROC-AUC y PR-AUC. ROC-AUC mide separabilidad promedio;
  PR-AUC es clave por desbalance QR.
- Lift/precision top-k: top 5% y top 10%, porque comunica si el score concentra
  usuarios QR en la cola alta.
- Multiclase: AUC/PR-AUC OvR por clase. `QR_OTHER` es el caso dificil que
  limita QR vs BIP; `QR_RED` es mas separable pero minoritario.
- Log-loss/Brier/calibracion quedan como metricas secundarias, relevantes solo
  si se interpretan probabilidades absolutas.
- Accuracy/balanced accuracy/macro-F1 se reportan como diagnostico secundario,
  no como metrica principal, por desbalance y umbrales arbitrarios.

Feature sets iniciales:

- `usage_cohort` (`usage` queda como alias): bloque conductual + cohorte
  temporal.
- `usage_pure`: bloque conductual excluyendo cohorte temporal.
- `usage_socio_geo`.
- `usage_route`.
- `full_contract`.
- `no_structural_missing`: `full_contract` sin variables RCS/early-late con
  missing estructural alto (`service_route_rcs_2024_2025`,
  `service_route_early_late_rcs`, `coarse_route_early_late_rcs` y sus
  principales hibridas).
- Sensibilidades `no_bip`, `no_offer`, `no_hybrid` solo si se necesita
  trasladar ablations al benchmark final.

Universos/splits:

- Main: `alta_n3` con random y grouped.
- Sensibilidades: `alta_n3_home3` con random y grouped; `alta_n10` random;
  `alta_media_n3` random.

Optuna:

- Fase 2, despues de tener baseline estable.
- Tuning inicial solo en `alta_n3`, `full_contract`.
- Objetivo binario candidato: `pr_auc` o mezcla `0.5*roc_auc + 0.5*pr_auc`.
- Objetivo multiclase candidato: `macro_ovr_auc` o promedio PR-AUC de
  QR_OTHER y QR_RED.
- Hiperparametros tuneados se congelan y luego se aplican a sensibilidades para
  no confundir tuning con cambio de universo.

Outputs planeados:

- Directorio: `tmp/audits/user_level_redesign/ml_benchmark/`.
- `runs.csv`, `metrics.csv`, `oof_predictions_<run_id>.parquet`,
  `lift_<run_id>.csv`, `calibration_<run_id>.csv`,
  `feature_importance_<run_id>.csv`, `family_importance_<run_id>.csv`,
  `config_<run_id>.json` y, si aplica, `optuna_trials_<run_id>.csv`.

Implementacion baseline:

- Se creo `scripts/audits/run_user_ml_benchmark.py`.
- Version inicial: XGBoost binario/multiclase, 5-fold Stratified OOF,
  feature sets desde el contrato JSON o derivados (`usage`,
  `usage_socio_geo`, `usage_route`, `full_contract`, `no_*`), metricas de
  ranking/probabilidad/clasificacion y outputs agregables.
- Smoke tests ejecutados sobre `alta_n3`, `usage`, muestra 20k, 20 arboles:
  - binario OK: AUC 0,6366; PR-AUC 0,2327.
  - multiclase OK: macro OvR AUC 0,6361; balanced accuracy 0,3333.
- Correccion aplicada durante smoke: normalizar probabilidades multiclase antes
  de `log_loss` y mapear importancias XGBoost `f0/f1/...` a nombres reales de
  columnas cuando el input es NumPy.
- Optuna queda pendiente como fase 2.

Revision tecnica post-smoke:

- Se agrego `--run-kind {smoke,benchmark}`. Las corridas `smoke` escriben sus
  artefactos individuales, pero no se append-ean a `runs.csv` ni `metrics.csv`.
- Se agrego validacion explicita de `n_splits`: cada clase debe tener al menos
  `n_splits` observaciones antes de construir folds.
- `no_*` ahora valida que la familia exista; evita corridas silenciosas tipo
  `no_geo2`.
- `select_features` reporta `non_numeric_dropped` si un feature del contrato
  existe pero no es numerico.
- Se agregaron `usage_cohort`, `usage_pure` y `no_structural_missing`.
  Smoke `no_structural_missing` OK sobre muestra 20k: 96 features, binario
  AUC 0,6342; PR-AUC 0,2256. Esta sensibilidad evita que el benchmark wide se
  apoye excesivamente en missingness estructural de variables RCS/early-late.
- Se agrego `--model logit` como benchmark lineal ML. Usa
  `SimpleImputer(strategy=median)` + `StandardScaler` dentro de cada fold para
  evitar leakage de preprocesamiento.
- Smoke `logit`, `full_contract`, muestra 20k, OK: binario AUC 0,6405;
  PR-AUC 0,2307; multiclase macro OvR AUC 0,6618.

## 2026-06-02 - Reapertura del EDA como feature engineering conductual

Despues de la respuesta del profesor, se decide no tratar el bajo techo
predictivo como cierre negativo. La lectura operativa es que el panel todavia
esta capturando variables basicas y proxies territoriales, pero falta una ronda
mas potente de features conductuales.

Decision:

- Usar el mismo notebook `02_eda/eda_user_level_panel.qmd` para continuidad,
  agregando un `Bloque 8` orientado a ingenieria de features.
- Separar esta fase del screening 1-7L: los bloques anteriores auditan fuentes
  y senal inicial; el bloque nuevo debe diseñar variables candidatas para
  mejorar `QR vs BIP`.
- No modificar todavia `build_user_model_matrix.py` hasta tener una tabla corta
  de candidatas con formula, fuente, caveat y criterio de evaluacion.

Familias candidatas:

- Intensidad/frecuencia: viajes por dia activo, por semana activa, concentracion
  de viajes y baja intensidad reciente.
- Regularidad temporal: dispersion horaria, punta/valle, fin de semana, AM/PM.
- Rutina espacial: concentracion OD, diversidad OD, estabilidad de origen y
  destinos frecuentes.
- Modalidad/red: solo bus, solo Metro/MetroTren, Metro-Bus, transbordos,
  exposicion a zonas/estaciones Metro.
- Recencia/cohorte: solo 2025, cambios 2024-2025, recencia x baja intensidad.
- Ruta/inercia: diversidad de servicios, early/late RCS e interacciones
  conductuales acotadas.

## 2026-06-02 - Arquitectura para feature engineering creativo

Se decide estructurar la ronda de feature engineering como paquetes
hipoteticos, no como una grilla de columnas sueltas. El objetivo es probar
representaciones distintas del usuario/tarjeta y evitar repetir la misma prueba
con variaciones marginales.

Capas acordadas:

1. Registro de hipotesis en el Bloque 8:
   `feature_pack | hipotesis | variables candidatas | fuente | caveat |
   prioridad | metrica esperada`.
2. Artefactos intermedios por paquete:
   - `user_behavior_rhythm_features_<suffix>.parquet`
   - `user_behavior_routine_features_<suffix>.parquet`
   - `user_context_residual_features_<suffix>.parquet`
   - `user_friction_features_<suffix>.parquet`
   - `user_behavior_prototype_features_<suffix>.parquet`
3. Feature sets versionados despues de unir al builder:
   - `full_plus_rhythm`
   - `full_plus_routine`
   - `full_plus_context_residual`
   - `full_plus_friction`
   - `full_plus_behavior_all`
4. Evaluacion por etapas:
   - EDA rapido: cobertura, bins/lift, correlaciones y lectura `QR vs BIP`.
   - Benchmark incremental: `usage_cohort` vs `full_contract` vs
     `full_plus_<pack>`.
   - Robustez solo para paquetes que muestren ganancia o lectura clara.

Feature packs:

- `rhythm_pack`: textura temporal de uso. Busca distinguir usuarios steady vs
  burst/ocasionales usando viajes por dia activo, gaps, concentracion temporal
  y actividad por semana.
- `routine_pack`: rutina vs exploracion. Busca medir repeticion OD-franja-modo,
  commuter-like score y viajes fuera de top zonas/OD.
- `context_residual_pack`: desviacion respecto al contexto. Busca separar
  efecto territorial bruto de comportamiento individual relativo a usuarios de
  la misma zona/macro.
- `friction_pack`: friccion efectiva de BIP. Busca condicionar accesibilidad a
  carga BIP por uso real: bus-only, baja intensidad, zonas realmente usadas y
  exposicion Metro.
- `prototype_pack`: perfiles conductuales latentes. Busca usar clusters/NMF o
  distancias a prototipos como scores interpretables posteriores.

Prioridad inicial:

- Partir por `rhythm_pack` y `context_residual_pack`.
- No tocar `build_user_model_matrix.py` hasta que el Bloque 8 tenga una tabla
  corta de variables candidatas y se defina el primer artefacto intermedio.
- Criterio principal: mejorar o explicar `QR vs BIP`; la heterogeneidad
  `QR_RED vs QR_OTHER` se usa como diagnostico secundario.

## 2026-06-02 - Tabla inicial de candidatas Bloque 8

Se agrego al notebook `02_eda/eda_user_level_panel.qmd` una tabla de candidatas
para feature engineering conductual. La tabla queda como backlog metodologico,
no como especificacion cerrada.

Incluye cinco paquetes:

- `rhythm_pack`: `trips_per_active_day`, `active_weeks_rate`,
  `activity_burstiness`, `median_gap_active_days`,
  `weekend_concentration`.
- `routine_pack`: `od_time_mode_top_share`, `commuter_like_score`,
  `exploration_zone_share`, `od_direction_balance`.
- `context_residual_pack`: `n_viajes_home_zone_pctile`,
  `hora_std_home_zone_resid`, `metro_share_origin_zone_resid`,
  `route_entropy_macro_resid`, `qr_like_behavior_residual_score`.
- `friction_pack`: `used_zones_bip_access_weighted`,
  `bus_only_low_bip_access`, `metro_exposure_no_metro_use`,
  `load_opportunity_mismatch`.
- `prototype_pack`: `commuter_distance`, `casual_explorer_distance`,
  `nmf_behavior_components`.

Orden recomendado de implementacion:

1. `rhythm_pack`.
2. `context_residual_pack`.
3. `routine_pack`.
4. `friction_pack`.
5. `prototype_pack`.

Motivo: `rhythm_pack` es barato e interpretable; `context_residual_pack` es el
mas distinto a variables brutas territoriales; `prototype_pack` queda para una
fase posterior conectada a NMF/clustering.

## 2026-06-02 - Implementacion inicial `rhythm_pack`

Se implemento el primer paquete de features conductuales:

- Script: `scripts/audits/build_user_behavior_rhythm_features.py`.
- Comando principal:
  `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_behavior_rhythm_features.py --scope interannual_ml --force`.
- Output:
  `tmp/audits/user_level_redesign/user_behavior_rhythm_features_interannual_ml.parquet`.
- Auditorias:
  - `user_behavior_rhythm_features_summary_interannual_ml.csv`
  - `user_behavior_rhythm_features_missing_interannual_ml.csv`
  - `user_behavior_rhythm_features_consistency_clean_panel_interannual_ml.csv`

Features construidas:

- Intensidad por actividad: `rhythm_trips_per_active_day`,
  `rhythm_trips_per_active_week`, `rhythm_active_weeks_rate_scope`,
  `rhythm_active_day_density_span`, `rhythm_trips_per_span_day`.
- Concentracion diaria: `rhythm_activity_top1_day_share`,
  `rhythm_activity_top2_day_share`, `rhythm_daily_hhi`,
  `rhythm_daily_entropy_norm`, `rhythm_daily_burstiness`,
  `rhythm_single_trip_day_share`.
- Gaps: `rhythm_has_gap`, `rhythm_n_gap_days`,
  `rhythm_median_gap_active_days`, `rhythm_mean_gap_active_days`,
  `rhythm_max_gap_active_days`.
- Concentracion semanal: `rhythm_weekly_top1_share`, `rhythm_weekly_hhi`,
  `rhythm_weekly_entropy_norm`, `rhythm_weekly_burstiness`.

Validacion:

- Smoke `active`: 4.031.185 tarjetas, 26 columnas, sin duplicados.
- Principal `interannual_ml`: 6.360.054 tarjetas, 26 columnas, sin duplicados.
- Consistencia contra panel clean `interannual_ml`: 0 mismatches en
  `n_viajes`, `n_dias_activos` y `n_semanas_activas` para tarjetas presentes
  en panel clean; 5.038 tarjetas del artefacto no estan en clean por conflictos
  de target excluidos.
- Missing principal: gaps tienen 24,95% missing, explicado por tarjetas con un
  solo dia activo; `rhythm_has_gap` y `rhythm_n_gap_days` quedan completos.

Screening rapido terminal sobre matriz `alta_n3`:

- `QR vs BIP`: mejor candidata univariada `rhythm_mean_gap_active_days`
  con AUC ~0,563 y PR-AUC ~0,184; direccionalidad positiva. La tasa base QR es
  ~0,153.
- `QR_OTHER vs BIP`: patron similar; `rhythm_mean_gap_active_days` alcanza
  AUC ~0,571 y PR-AUC ~0,167.
- `QR_RED vs QR_OTHER`: la senal cambia de direccion para gaps; confirma que
  el paquete debe evaluarse principalmente contra `QR vs BIP`.

EDA reproducible:

- Se agrego al Bloque 8 de `02_eda/eda_user_level_panel.qmd` una seccion
  `rhythm_pack` con setup, by-target, univariate ranking, bins y probe
  tree/logit.

Decision 2026-06-02:

- Integrar `rhythm_pack` al builder principal `build_user_model_matrix.py`.
- Mantener `full_contract` como baseline canónico pre-rhythm (`ml_wide`) para
  no contaminar comparaciones historicas.
- Agregar feature sets explicitos:
  - `logit_plus_rhythm`: `logit_main` + subset parsimonioso de ritmo.
  - `ml_plus_rhythm`: `ml_main` + todas las variables rhythm.
  - `binary_ml_plus_rhythm`: `binary_ml_main` + todas las variables rhythm.
  - `full_plus_rhythm`: `ml_wide` + todas las variables rhythm.
- En `run_user_ml_benchmark.py`, `rhythm_*` queda clasificado como familia
  `rhythm` solo cuando se pide un set que lo contiene explicitamente.

Benchmark XGB `full_plus_rhythm`:

| universo | n_cards | QR base | AUC binario | PR-AUC binario | Macro OvR AUC | balAcc multiclase |
|---|---:|---:|---:|---:|---:|---:|
| `alta_n3` | 2.460.264 | 0,1534 | 0,6827 | 0,2748 | 0,7074 | 0,3351 |
| `alta_n5` | 1.838.455 | 0,1452 | 0,6947 | 0,2736 | 0,7171 | 0,3355 |
| `alta_n10` | 1.286.681 | 0,1379 | 0,7085 | 0,2752 | 0,7284 | 0,3358 |
| `alta_n3_home3` | 1.493.677 | 0,1429 | 0,7025 | 0,2771 | 0,7244 | 0,3358 |
| `alta_media_n3` | 3.380.572 | 0,1539 | 0,6881 | 0,2814 | 0,7118 | 0,3354 |
| `alta_media_n5` | 2.750.572 | 0,1484 | 0,6975 | 0,2823 | 0,7196 | 0,3355 |

Run IDs:

- `rhythm_alta_n3_full_interannual_ml_clean_alta_n3_full_plus_rhythm_both_xgb_random_2739f36c`
- `rhythm_alta_n5_full_interannual_ml_clean_alta_n5_full_plus_rhythm_both_xgb_random_e54d6e86`
- `rhythm_alta_n10_full_interannual_ml_clean_alta_n10_full_plus_rhythm_both_xgb_random_895947f9`
- `rhythm_alta_n3_home3_full_interannual_ml_clean_alta_n3_home3_full_plus_rhythm_both_xgb_random_9d096a86`
- `rhythm_alta_media_n3_full_interannual_ml_clean_alta_media_n3_full_plus_rhythm_both_xgb_random_8f269b41`
- `rhythm_alta_media_n5_full_interannual_ml_clean_alta_media_n5_full_plus_rhythm_both_xgb_random_06cfa6e4`

Lectura:

- `rhythm_pack` aporta senal incremental pequena pero consistente. En los
  universos con comparacion directa contra `full_contract`, la mejora es del
  orden de +0,001 a +0,002 en AUC/PR-AUC.
- El mayor cambio no viene del bloque rhythm, sino del soporte de observacion:
  subir de `n_viajes>=3` a `n_viajes>=10` mejora AUC binario de 0,6827 a
  0,7085; exigir `n_home_dest_trips_card>=3` sube a 0,7025.
- Esto sugiere que el problema es mas separable cuando la tarjeta tiene mas
  historia conductual y residencia mas confiable.
- `alta_media` aumenta cobertura y PR-AUC, pero no supera a `alta_n10` o
  `alta_n3_home3` en AUC. Queda como sensibilidad de cobertura, no como
  especificacion principal.
- La balanced accuracy multiclase se mantiene cerca de 1/3; no debe usarse
  como metrica central. Para multiclase conviene mirar Macro OvR AUC y PR-AUC
  por clase.

Decision:

- Mantener `full_plus_rhythm` como benchmark enriquecido, pero no venderlo como
  salto predictivo fuerte.
- Usar el resultado como evidencia de que la textura temporal/intermitencia
  ayuda marginalmente.
- Seguir con `context_residual_pack` y `routine_pack`, porque el cuello de
  botella sigue siendo feature engineering mas estructural.

Decision logit `rhythm_pack`:

- La especificacion principal `logit_plus_rhythm` debe ser parsimoniosa. No
  conviene incluir todo el paquete porque varias variables son transformaciones
  correlacionadas de la misma idea de intensidad, concentracion e
  intermitencia.
- Variables main:
  - `rhythm_mean_gap_active_days`: intermitencia principal.
  - `rhythm_trips_per_span_day`: intensidad distribuida en la ventana.
  - `rhythm_active_day_density_span`: cotidianeidad vs uso esporadico.
  - `rhythm_trips_per_active_week`: frecuencia semanal condicional a actividad.
  - `rhythm_daily_hhi`: concentracion diaria.
  - `rhythm_has_gap`: flag estructural de presencia de gaps.
- Variables de sensibilidad:
  - Alternativas de gap: `rhythm_median_gap_active_days`,
    `rhythm_max_gap_active_days`, `rhythm_n_gap_days`.
  - Alternativas de concentracion diaria: `rhythm_daily_entropy_norm`,
    `rhythm_daily_burstiness`, `rhythm_activity_top1_day_share`,
    `rhythm_activity_top2_day_share`.
  - Bloque semanal: `rhythm_weekly_hhi`, `rhythm_weekly_entropy_norm`,
    `rhythm_weekly_burstiness`, `rhythm_weekly_top1_share`.
  - Variables secundarias/redundantes: `rhythm_trips_per_active_day`,
    `rhythm_single_trip_day_share`.
- Si se evalua sensibilidad en logit, hacer una sola especificacion
  `logit_plus_rhythm_wide`, no multiples variantes pequenas.

## 2026-06-02 - Bloque 8B `context_residual_pack` preparado

Se agrego al notebook `02_eda/eda_user_level_panel.qmd` un bloque exploratorio
para variables residuales relativas al contexto:

- `ctx_n_viajes_home_zone_pctile`: percentil de intensidad dentro de
  `zona_hogar`.
- `ctx_hora_std_home_zone_resid`: desviacion de irregularidad horaria respecto
  a la mediana de la zona hogar.
- `ctx_mean_gap_active_days_home_zone_resid`: gaps medios relativos a zona
  hogar.
- `ctx_active_day_density_home_zone_resid`: densidad de dias activos relativa
  a zona hogar.
- `ctx_metro_like_origin_zone_resid`: share Metro-like relativo a zona de
  origen top-1.
- `ctx_service_route_entropy_origin_zone_resid`: entropia de servicio relativa
  a zona de origen top-1.
- `ctx_qr_like_behavior_residual_score`: score auditable de componentes
  residuales, no variable final cerrada.

Contrato metodologico:

- Umbral minimo de grupo para residuales: 200 tarjetas.
- El bloque es EDA; si alguna variable entra al benchmark/modelo final, las
  medianas/ranks contextuales deben implementarse fold-safe para evitar leakage
  por transformaciones calculadas con test.
- El probe compara `baseline_continuous`, `baseline_plus_rhythm` y
  `baseline_plus_rhythm_context_residual`.

Estado: pendiente de render/ejecucion por el usuario.

## 2026-06-02 - Integracion exploratoria `full_plus_rhythm_context_residual`

Se integro `context_residual_pack` al builder principal
`scripts/audits/build_user_model_matrix.py` como bloque exploratorio.

Feature engineering implementado:

- `ctx_n_viajes_home_zone_pctile`: percentil de `n_viajes` dentro de
  `zona_hogar`.
- `ctx_hora_std_home_zone_resid`: desviacion frente a mediana de `hora_std`
  dentro de `zona_hogar`.
- `ctx_mean_gap_active_days_home_zone_resid`: desviacion frente a mediana de
  `rhythm_mean_gap_active_days` dentro de `zona_hogar`.
- `ctx_active_day_density_home_zone_resid`: desviacion frente a mediana de
  `rhythm_active_day_density_span` dentro de `zona_hogar`.
- `ctx_service_route_entropy_origin_zone_resid`: desviacion frente a mediana de
  `service_route_entropy_norm` dentro de `origin_zone_top1`.
- `ctx_qr_like_behavior_residual_score`: score diagnostico compuesto con
  signos ex ante del EDA.

Feature sets nuevos:

- `logit_plus_rhythm_context_residual`: logit main + rhythm parsimonioso + 4
  componentes contextuales principales.
- `logit_plus_rhythm_context_residual_sensitivity`: agrega entropia residual y
  score compuesto.
- `ml_plus_rhythm_context_residual`: `ml_main` + rhythm + componentes
  contextuales principales.
- `full_plus_rhythm_context_residual`: `ml_wide` + rhythm + componentes
  contextuales principales.
- `full_plus_rhythm_context_residual_sensitivity`: agrega entropia residual y
  score compuesto.
- `binary_ml_plus_rhythm_context_residual`: bloque binario main + rhythm +
  componentes contextuales principales.

Decision:

- `ctx_metro_like_origin_zone_resid` queda fuera del builder por baja senal en
  el EDA.
- Los componentes principales son preferibles al score manual para main.
- El score queda solo en sensibilidad/diagnostico.
- Caveat importante: la implementacion en matriz usa ranks/medianas calculadas
  sobre el universo completo. Esto es aceptable para benchmark exploratorio,
  pero para reporte final debe reimplementarse fold-safe dentro del pipeline si
  se usa como evidencia predictiva formal.

## 2026-06-02 - Bloque 8C `routine_pack` preparado

Se definio el siguiente bloque de feature engineering conductual como regreso
controlado al nivel viaje: no cambia la unidad del modelo, sino que resume
patrones de viaje por `id_tarjeta`.

Artefacto nuevo:

- `scripts/audits/build_user_routine_features.py`
- Salida esperada:
  `tmp/audits/user_level_redesign/user_behavior_routine_features_<scope>.parquet`

Idea metodologica:

- Construir combos `OD x franja horaria x modo` desde viajes.
- Agregar a usuario medidas de concentracion/rutina:
  `routine_combo_top1_share`, `routine_combo_hhi`,
  `routine_od_time_top1_share`, `routine_zone_top2_usage_share`,
  `routine_zone_exploration_share`, `routine_main_od_share` y
  `routine_main_od_roundtrip_balance`.
- Mantener `routine_commute_like_score` solo como sensibilidad exploratoria,
  no como variable principal, porque es un score compuesto con pesos
  arbitrarios.

Criterio de interpretacion:

- `routine_combo_top1_share` mide que porcentaje de viajes cae en el mismo
  combo OD-franja-modo. No conserva granularidad de cada viaje, pero resume
  cuan dominante es una rutina especifica. Si es bajo, el usuario reparte su
  movilidad entre mas contextos; si es alto, tiene una rutina fuerte.
- `routine_zone_top2_usage_share` mide concentracion en dos zonas principales,
  util para perfiles tipo casa-trabajo/estudio.
- `routine_main_od_roundtrip_balance` mide si el OD principal aparece en ambas
  direcciones, no solo como flujo unilateral.

Bloque EDA nuevo:

- Se agrego `8.9-8.10` en `02_eda/eda_user_level_panel.qmd`.
- El probe compara `baseline_plus_rhythm_context_residual` contra versiones
  con `routine_main` y `routine_all`.

Estado: pendiente de que el usuario construya el artefacto y ejecute el bloque
QMD.

## 2026-06-03 - Integracion exploratoria `full_plus_rhythm_context_routine`

Despues del EDA 8C, se integro `routine_main` al builder principal como
feature set exploratorio:

- `full_plus_rhythm_context_routine` =
  `ml_wide + RHYTHM_FEATURES + CONTEXT_RESIDUAL_MAIN_FEATURES + ROUTINE_MAIN_FEATURES`.

Variables `routine_main` integradas:

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

Decision:

- No se integra `routine_commute_like_score` al main porque es un score
  compuesto con pesos arbitrarios y comportamiento no monotono en bins.
- Se mantiene el artefacto `routine_pack` como join opcional: si existe para
  el scope, el builder lo incorpora; si no existe, el feature set reporta
  variables faltantes sin romper otros scopes.
- En `run_user_ml_benchmark.py`, las variables `routine_` se clasifican como
  familia `routine` para importancias agregadas.

Siguiente benchmark:

- Reconstruir solo `interannual_ml clean alta n3`.
- Correr XGB `full_plus_rhythm_context_routine` solo en `alta_n3`.
- Comparar principalmente contra `full_plus_rhythm` y contra
  `full_plus_rhythm_context_residual_sensitivity`. Si no hay mejora material,
  no repetir masivamente en `n10/home3/alta_media`.

## 2026-06-03 - Bloque 8D `daily_tour_pack` preparado

Se agrego un nuevo paquete de feature engineering conductual enfocado en la
estructura intra-dia de los viajes, manteniendo `id_tarjeta` como unidad final.

Artefacto nuevo:

- `scripts/audits/build_user_daily_tour_features.py`
- Salida esperada:
  `tmp/audits/user_level_redesign/user_behavior_daily_tour_features_<scope>.parquet`

Idea metodologica:

- Volver al nivel viaje solo para ordenar viajes dentro de cada
  `id_tarjeta x fecha`.
- Agregar a usuario shares de dias con patrones diarios:
  2 viajes, 3+ viajes, dia complejo, dia que cierra en la zona inicial,
  ida-vuelta aproximada, mismo OD no-direccional, consistencia/mezcla modal,
  primer viaje en punta AM, ultimo viaje en punta PM y dia tipo commute.
- Separar variables principales interpretables de sensibilidades de conteo y
  horario promedio.

Variables principales candidatas:

- `tour_two_trip_day_share`
- `tour_three_plus_trip_day_share`
- `tour_complex_day_share`
- `tour_closed_loop_day_share`
- `tour_reciprocal_od_day_share`
- `tour_same_unordered_od_day_share`
- `tour_mode_consistent_day_share`
- `tour_mixed_mode_day_share`
- `tour_first_trip_lab_am_peak_share`
- `tour_last_trip_lab_pm_peak_share`
- `tour_peak_anchor_day_share`
- `tour_workday_commute_like_day_share`

Caveats:

- No se cambia la especificacion a nivel viaje; este bloque solo agrega
  estructura diaria por usuario.
- `tour_workday_commute_like_day_share` es una regla heuristica, no un score
  final causal.
- Las variables de conteo diario (`distinct_*`, horas promedio, span diario)
  quedan como sensibilidad porque pueden estar correlacionadas con intensidad y
  con variables ya cubiertas por `rhythm_pack`/`routine_pack`.

Bloque EDA nuevo:

- Se agrego `8.11-8.12` en `02_eda/eda_user_level_panel.qmd`.
- El probe compara `baseline_plus_rhythm_context_residual`, `routine_main` si
  esta disponible y versiones con `daily_tour_main`/`daily_tour_all`.

Decision:

- No integrar todavia al builder de matriz principal. Primero revisar salud del
  artefacto, ranking univariado, bins y probe incremental en el QMD.

## 2026-06-03 - Fix modal en `routine_pack` y `daily_tour_pack`

Se corrigio un bug de construccion en las variables modales de los artefactos
conductuales:

- `routine_mode_coarse`
- `tour_mode_coarse`

Root cause:

- Los builders estaban buscando strings tipo `METRO`, `BUS`, `RED` dentro de
  `tipo_transporte_*`.
- En los parquets procesados, `tipo_transporte_*` usa codigos numericos:
  `1=Bus`, `2=Metro`, `3=Zona Paga`, `4=MetroTren`.
- Esto hacia que el modo coarse cayera casi siempre en `other_mode`, dejando
  variables como `tour_mode_consistent_day_share`,
  `tour_mixed_mode_day_share` y `tour_distinct_modes_per_day_mean`
  degeneradas.

Fix:

- Ambos builders ahora usan el mismo contrato que
  `build_user_level_payment_panel.py`:
  `BUS_CODES = ["1", "3"]` y `METRO_CODES = ["2", "4"]`.
- Se agrego test unitario:
  `lib/test_user_behavior_mode_mapping.py`.

Implicancia:

- Los artefactos existentes de `routine_pack` y `daily_tour_pack` quedan
  obsoletos para cualquier lectura modal.
- Las variables no modales ya revisadas en `daily_tour_pack` siguen siendo
  validas, pero conviene reconstruir y rerunear 8C/8D para consistencia.

## 2026-06-03 - Feature set `full_plus_rhythm_context_routine_daily_tour`

Decision:

- Se integra al builder de matriz un contrato combinado:
  `full_plus_rhythm_context_routine_daily_tour`.
- El set usa `ml_wide + rhythm_pack + context_residual_main + routine_selected_main + daily_tour_main`.
- No se cambia el significado de `full_plus_rhythm_context_routine`, porque ya
  fue usado en corridas previas con la seleccion antigua de `routine_main`.

Variables `routine_selected_main`:

- `routine_lab_peak_share`
- `routine_commute_like_score`
- `routine_od_time_n_unique`
- `routine_od_time_entropy_norm`
- `routine_zone_n_unique`

Variables `daily_tour_main`:

- `tour_last_trip_hour_mean`
- `tour_last_trip_lab_pm_peak_share`
- `tour_day_span_hours_mean`
- `tour_peak_anchor_day_share`
- `tour_workday_commute_like_day_share`
- `tour_first_trip_lab_am_peak_share`
- `tour_complex_day_share`
- `tour_mixed_mode_day_share`

Criterio:

- Priorizar senal marginal e interpretabilidad.
- Evitar duplicados fuertes como `mixed_mode` vs `mode_consistent`, pares
  `mean/median`, y familia completa `combo_*`/`od_time_*` en el set principal.
- Mantener variables redundantes para sensibilidad/all, no para el benchmark
  principal.

## 2026-06-03 - Bloque 8E `friction_pack`

Decision:

- Se agrega un paquete de friccion BIP derivado directamente dentro de
  `build_user_model_matrix.py`.
- No se crea artefacto pesado adicional, porque las variables se construyen a
  partir de columnas ya presentes en la matriz: accesibilidad BIP por
  hogar/origen/actividad, oferta modal, uso modal, intensidad y ritmo.
- Las transformaciones son reglas fijas y productos continuos; no usan
  cuantiles ni estadisticos condicionados al target.

Variables principales:

- `fric_weighted_bip_dist_log`: distancia log al punto de carga BIP ponderada
  por residencia, origen top1 y actividad top1.
- `fric_weighted_bip_density_inv`: inverso de densidad BIP ponderada por las
  mismas zonas.
- `fric_weighted_bip_dist_x_solo_bus`: friccion BIP ponderada x uso solo bus.
- `fric_weighted_bip_dist_x_low_intensity`: friccion BIP ponderada x baja
  intensidad de viajes.
- `fric_weighted_bip_dist_x_low_active_density`: friccion BIP ponderada x baja
  densidad de dias activos.
- `fric_weighted_bip_density_inv_x_solo_bus`: baja densidad BIP x solo bus.
- `fric_home_no_bip_points_x_solo_bus`: hogar sin puntos BIP x solo bus.
- `fric_origin_bus_like_x_weighted_bip_dist`: oferta bus-like x friccion BIP.
- `fric_metro_like_x_weighted_bip_density_inv`: oferta metro-like x baja
  densidad BIP ponderada.
- `fric_weighted_bip_dist_x_peak_share`: friccion BIP x uso en franjas punta.

Feature sets:

- `full_plus_rhythm_context_friction`
- `full_plus_rhythm_context_routine_daily_tour_friction`

Bloque EDA:

- Se agrega Bloque 8E en `02_eda/eda_user_level_panel.qmd`.
- El bloque lee la matriz `interannual_ml_clean_alta_n3` reconstruida y su
  contrato JSON, para analizar exactamente las columnas que entraran al
  benchmark.

## 2026-06-03 - Bloque 8F `adoption_timing_pack`

Decision:

- Se inicia `adoption_timing_pack` antes que `prototype_pack`, porque ataca una
  fuente de senal distinta a rutina/friccion: cambio interanual entre las mismas
  semanas de 2024 y 2025.
- Se crea el artifact
  `user_behavior_adoption_timing_features_<scope>.parquet` con unidad
  `id_tarjeta`.
- Las variables de conteo/crecimiento usan cero actividad para años no
  observados; las variables de delta de medias/shares solo se definen para
  tarjetas observadas en ambos años.

Variables principales:

- `adopt_trip_growth_log_2025_2024`
- `adopt_active_day_growth_log_2025_2024`
- `adopt_active_week_growth_log_2025_2024`
- `adopt_trips_per_active_day_delta`
- `adopt_hora_mean_delta`
- `adopt_hora_std_delta`
- `adopt_lab_peak_share_delta`
- `adopt_no_lab_share_delta`
- `adopt_solo_bus_share_delta`
- `adopt_solo_metro_share_delta`
- `adopt_metro_bus_share_delta`
- `adopt_transfer_share_delta`
- `adopt_origin_n_unique_delta`
- `adopt_dest_n_unique_delta`
- `adopt_origin_top1_changed`

Feature sets:

- `full_plus_rhythm_context_adoption_timing`
- `full_plus_rhythm_context_routine_daily_tour_adoption_timing`

Bloque EDA:

- Se agrega Bloque 8F en `02_eda/eda_user_level_panel.qmd`.
- El bloque audita flags de presencia anual (`adopt_has_2024`,
  `adopt_has_2025`, `adopt_both_years`, `adopt_only_2025`,
  `adopt_only_2024`) pero el set principal de modelo usa solo las variables
  incrementales seleccionadas.
- Los flags diagnosticos se leen desde el artifact
  `user_behavior_adoption_timing_features_interannual_ml.parquet`, porque la
  matriz supervisada solo conserva columnas incluidas en algun `feature_set`.
- Criterio de decision: si el probe no mejora sobre
  `full_plus_rhythm_context_routine_daily_tour`, no lanzar XGB completo.

## 2026-06-04 - Bloque 8G `prototype_pack`

Decision:

- Se implementa `prototype_pack` como scores determinísticos e interpretables,
  no como clustering.
- Cada score es el promedio de percentiles globales firmados. Un componente con
  signo positivo aporta mas cuando la tarjeta esta en percentiles altos; un
  componente con signo negativo aporta mas cuando esta en percentiles bajos.
- No usa target, cuantiles por clase ni informacion supervisada.

Scores principales:

- `proto_commuter_peak_score`: similitud con perfil pendular/laboral de punta.
  Componentes altos: `routine_commute_like_score`, `routine_lab_peak_share`,
  `tour_peak_anchor_day_share`, `tour_workday_commute_like_day_share`,
  `tour_first_trip_lab_am_peak_share`, `tour_last_trip_lab_pm_peak_share`.
- `proto_late_return_score`: similitud con actividad de retorno tardio y mayor
  span diario. Componentes altos: `tour_last_trip_hour_mean`,
  `tour_day_span_hours_mean`, `tour_day_span_hours_median`,
  `tour_last_trip_lab_pm_peak_share`, `tour_peak_anchor_day_share`.
- `proto_low_complexity_score`: movilidad simple/local. Componentes altos:
  `tour_two_trip_day_share`; componentes bajos: dias 3+, dias complejos,
  diversidad de zonas/OD y `routine_*_n_unique`.
- `proto_explorer_score`: movilidad diversa. Componentes altos: diversidad de
  zonas/OD/combos, entropia OD y dias complejos.
- `proto_routine_repeater_score`: repeticion de patron. Componentes altos:
  `top1_share`, `hhi`, `main_od_share`; componentes bajos: entropia/diversidad.
- `proto_multimodal_score`: mezcla modal intra-dia. Componentes altos:
  `tour_mixed_mode_day_share`, `tour_distinct_modes_per_day_mean`; componente
  bajo: `tour_mode_consistent_day_share`.

Feature sets:

- `full_plus_rhythm_context_prototype`
- `full_plus_rhythm_context_routine_daily_tour_prototype`

Bloque EDA:

- Se agrega Bloque 8G en `02_eda/eda_user_level_panel.qmd`.
- Criterio de decision: solo lanzar XGB si el tree-logit-probe mejora sobre
  `full_plus_rhythm_context_routine_daily_tour`; si no, dejar como narrativa
  descriptiva de perfiles.

## 2026-06-04 - Prueba metodologica XGBoost con ponderacion de clases

Decision:

- Se agrega `--xgb-class-weight {none,balanced}` a
  `scripts/audits/run_user_ml_benchmark.py`.
- En tarea binaria, `balanced` usa `scale_pos_weight = n_neg / n_pos` calculado
  dentro de cada fold de entrenamiento.
- En tarea multiclase, `balanced` usa `sample_weight` inverso a la frecuencia
  de clase dentro de cada fold de entrenamiento.
- Esto permite descartar si la baja mejora de trees se debe a que XGBoost esta
  sub-atendiendo clases minoritarias, especialmente `QR_RED`.

Validacion:

- Compilacion del script OK.
- Smoke sintetico OK para binario y multiclase; las probabilidades OOF tienen
  dimensiones correctas y suman 1 en multiclase.

## 2026-06-05 - Optuna acotado para XGBoost usuario

Decision:

- Se implementa `scripts/audits/tune_user_xgb_optuna.py` como script separado
  del benchmark principal. Su rol es buscar candidatos de hiperparametros en
  muestra estratificada; no reemplaza la corrida full ni se usa para comparar
  universos.
- `run_user_ml_benchmark.py` se extiende para aceptar los hiperparametros que
  Optuna puede sugerir: `--xgb-min-child-weight`, `--xgb-reg-alpha`,
  `--xgb-gamma` y `--xgb-max-delta-step`.
- El class weighting de XGBoost se suaviza con
  `--xgb-class-weight-power alpha`: `alpha=0` equivale a sin weighting y
  `alpha=1` equivale a balanced completo. El tuner puede dejarlo fijo o
  incluirlo en el search space con `--tune-class-weight-power`.

Uso previsto:

- Primero tunear barato en `alta_n3`, `full_plus_rhythm_context_routine_daily_tour`,
  muestra 300k-500k, 3 folds y 20-40 trials.
- Luego tomar el comando sugerido por el tuner y validarlo en full con
  `run_user_ml_benchmark.py`, 5 folds.
- Si la mejora no sobrevive a la corrida full, se reporta como evidencia de
  techo predictivo, no como modelo final.

Validacion:

- `py_compile` OK para tuner y benchmark.
- Smoke Optuna de 1 trial, 2 folds, muestra 2k OK. Escribio
  `config_<run_id>.json` y `optuna_trials_<run_id>.csv`, y genero comando
  reproducible para el benchmark full.

## 2026-06-08 - Segmentacion NMF `structural_wide_v1` y controles post-hoc QR_RED

Decision:

- Se implementa `structural_wide_v1` como matriz descriptiva de segmentacion
  no supervisada. Combina `behavioral_wide_v0b` con variables socio-
  residenciales, macrozona residencial, acceso BIP, oferta de transporte y
  entorno OSM.
- El NMF estructural se interpreta como tipologia descriptiva, no como modelo
  causal ni como clusterizacion compacta. Las metricas de segmentacion siguen
  siendo moderadas/bajas, pero mejoran respecto del NMF puramente conductual y
  entregan segmentos sustantivamente interpretables.

Resultado principal:

- En `structural_wide_v1`, el NMF con `k=5` identifica un segmento QR_RED alto
  robusto en las sensibilidades:
  - `v1_alta_n3`: segmento de ~14,4% con `QR_RED lift ~= 2,61`.
  - `v1_alta_n5`: segmento de ~14,2% con `QR_RED lift ~= 2,66`.
  - `v1_alta_n10`: segmento de ~11,6% con `QR_RED lift ~= 2,78`.
  - `v1_alta_n3_home3`: segmento de ~13,3% con `QR_RED lift ~= 2,66`.
- El perfil del segmento es consistente: concentracion en macrozona oriente,
  mayor educacion superior residencial, menor concentracion D+E proxy, mayor
  asistencia parvularia y menor presencia relativa de discapacidad e
  inmigrantes.

Diagnostico de controles:

- Se agrega `scripts/audits/diagnose_structural_qr_red_controls.py` para
  estimar modelos logisticos post-hoc de `is_qr_red` con bloques anidados:
  `oriente`, macrozonas, socio core, macro+socio y macro+socio+acceso/oferta.
- El diagnostico es asociativo y post-hoc: QR_RED no se usa para construir el
  NMF, y estos modelos no deben leerse causalmente.
- Resultados sinteticos sobre muestra 1M por universo:
  - `home_macro_oriente` solo tiene asociacion bruta positiva con QR_RED:
    efecto marginal aproximado de `+4` a `+4,3` puntos porcentuales y AUC
    alrededor de `0,62`.
  - El bloque de macrozonas sube el AUC a alrededor de `0,66`.
  - `educacion + D+E proxy` alcanza AUC alrededor de `0,69`, superando a la
    macrozona por si sola.
  - Al agregar `oriente` sobre el bloque socio, el AUC casi no cambia y el
    efecto marginal de `oriente` cae a casi cero.
  - En los modelos completos, el efecto condicional de `oriente` se vuelve
    pequeno o negativo, lo que se interpreta como colinealidad/residuo
    condicional, no como evidencia de que Oriente reduzca QR_RED.
  - La educacion superior residencial permanece positiva y estable en todas
    las sensibilidades. En el modelo completo, su efecto marginal promedio esta
    aproximadamente entre `+1,4` y `+1,9` puntos porcentuales por unidad z.
  - `res_eod2012_share_hogares_de_income_proxy_z` debe leerse como proxy de
    concentracion D+E, no como ingreso alto. Su efecto es pequeno o cercano a
    cero al controlar por educacion y otros atributos socio-territoriales.

Implicancia interpretativa:

- El segmento QR_RED alto no debe describirse como "efecto Oriente" ni como
  evidencia causal territorial.
- La lectura recomendada es: segmento socio-residencial de alta educacion,
  baja concentracion D+E y concentrado territorialmente en Oriente, con fuerte
  sobrerrepresentacion de QR_RED.
- En el reporte, separar dos afirmaciones:
  - descriptiva: el NMF identifica un segmento QR_RED alto localizado en
    Oriente y robusto a filtros de universo;
  - diagnostica: los controles post-hoc sugieren que la asociacion QR_RED se
    explica principalmente por composicion socio-residencial, especialmente
    educacion superior, mas que por una macrozona independiente.

## 2026-06-09 - Backlog ML post-benchmark: thresholds, sampling y MLP

Contexto:

- El XGB usuario agregado entrega senal moderada como ranking/probabilidad,
  pero como clasificador duro multiclass tiende a predecir casi todo como BIP
  bajo `argmax`.
- Class weights aumentan balanced accuracy, pero reducen ranking/calibracion y
  sobre-predicen clases minoritarias cuando el weighting es agresivo.

Decision:

- No implementar thresholds, sampling y MLP como una sola ronda grande.
- Documentarlos como backlog experimental separado y avanzar de a uno.
- Primer experimento: threshold tuning sobre OOF unweighted. Es el mas barato y
  metodologicamente limpio porque no reentrena ni altera las probabilidades del
  modelo principal.

Backlog priorizado:

1. `threshold_tuning`: barrer umbrales sobre OOF existentes.
   - Binario: `p_QR >= t`.
   - Multiclass: reglas con `t_QR_OTHER` y `t_QR_RED`, dejando BIP como clase
     residual.
   - Comparar con `argmax`, `always BIP` y XGB con class weights.
2. `sampling`: random undersampling/oversampling dentro de cada train fold.
   - Probar solo si thresholds no entregan un compromiso razonable.
   - Evitar SMOTE como especificacion principal por baja interpretabilidad de
     perfiles sinteticos con dummies territoriales y variables agregadas.
3. `model_alternatives`: CatBoost y MLP tabular simple.
   - CatBoost se prueba primero porque es comparable a XGBoost en datos
     tabulares y puede capturar no linealidades sin cambiar el diseno de
     features.
   - MLP queda como benchmark flexible adicional.
   - Mantener configuraciones pequenas y misma evaluacion OOF.

Criterio:

- Si thresholds mejoran balanced accuracy sin destruir demasiado precision o
  tasas predichas por clase, se reportan como post-procesamiento opcional.
- Si solo mueven etiquetas a minorias de forma poco realista, mantener XGB
  unweighted como modelo principal y reportar la limitacion de hard-label
  classification.

## 2026-06-09 - Undersampling fold-safe en benchmark XGBoost

Decision:

- Se implementa undersampling aleatorio en `run_user_ml_benchmark.py` con
  `--sampling-strategy undersample`.
- El resampling ocurre solo dentro de cada train fold. Los folds de test y las
  metricas OOF conservan la distribucion real.
- Por ahora se implementa solo para `--model xgb`.

Configuracion:

- Binario: `--undersample-binary-positive-share` define el share objetivo de QR
  en el train fold. Se mantienen todos los QR y se submuestrea BIP.
- Multiclase: `--undersample-multiclass-bip-share` define el share objetivo de
  BIP en el train fold. Se mantienen `QR_OTHER` y `QR_RED`, y se submuestrea
  BIP.
- Los logs por fold imprimen `train_fit` y la distribucion efectiva usada para
  entrenamiento.

Validacion:

- `py_compile` OK.
- Test sintetico OK: binario alcanza `fit_qr_share=0.35`; multiclase alcanza
  `fit_bip=0.60`.
- Smoke benchmark con muestra 5k, 2 folds y 5 arboles OK; test folds se
  mantienen sin resampling y el entrenamiento muestra las proporciones
  esperadas.

## 2026-06-09 - CatBoost como clasificador alternativo acotado

Decision:

- Se agrega `--model catboost` a `run_user_ml_benchmark.py`.
- La prueba inicial debe ser sin resampling ni class weights, para aislar el
  efecto del algoritmo frente al XGB unweighted.
- CatBoost queda como benchmark alternativo; no abre una grilla amplia salvo
  que mejore claramente AUC/PR-AUC o las metricas hard-label relevantes.

Configuracion:

- Flags agregados: `--cat-iterations`, `--cat-learning-rate`, `--cat-depth`,
  `--cat-l2-leaf-reg`.
- Se guardan los mismos artefactos OOF, metricas, calibracion, lift e
  importancias que para XGB/logit.

Validacion:

- `py_compile` OK.
- Smoke sintetico OK para `binary` y `multiclass`: genera OOF con folds
  completos y probabilidades multiclase normalizadas.

Resultados `alta_n3`, `full_plus_rhythm_context_routine_daily_tour`:

- CatBoost 500 iteraciones, lr 0.05, depth 6:
  - Binario: AUC 0.6790, PR-AUC 0.2721.
  - Multiclase: macro OvR AUC 0.7015, balanced accuracy 0.3340.
- CatBoost 1000 iteraciones, lr 0.03, depth 6:
  - Binario: AUC 0.6803, PR-AUC 0.2735.
  - Multiclase: macro OvR AUC 0.7027, balanced accuracy 0.3341.

Lectura:

- La configuracion mas larga mejora levemente al CatBoost corto, pero sigue
  por debajo del XGBoost principal (`AUC=0.6842`, `PR-AUC=0.2771`,
  `macro OvR AUC=0.7090`).
- CatBoost no resuelve el problema de clasificacion dura multiclase; balanced
  accuracy queda practicamente en el baseline de `argmax` dominado por BIP.
- Cierre recomendado: mantener XGBoost unweighted como benchmark principal y
  reportar CatBoost como sensibilidad negativa de algoritmo tabular.

## 2026-06-09 - MLP tabular simple como benchmark flexible

Decision:

- Se agrega `--model mlp` a `run_user_ml_benchmark.py` como prueba exploratoria
  de una red neuronal tabular pequena.
- La MLP usa `SimpleImputer(median)` + `StandardScaler()` + `MLPClassifier`.
- No se implementan importancias para MLP; el foco es comparar metricas OOF,
  no interpretar variables.

Configuracion:

- Flags agregados: `--mlp-hidden-layers`, `--mlp-alpha`,
  `--mlp-learning-rate-init`, `--mlp-batch-size`, `--mlp-max-iter`,
  `--mlp-no-early-stopping`.
- Defaults deliberadamente conservadores: hidden layers `64,32`,
  `max_iter=25`, batch size 4096, early stopping activado.

Criterio:

- Correr primero una muestra (`--sample 500000`, `--n-splits 3`) por costo y
  memoria.
- Solo correr full 5-fold si el smoke/muestra no queda claramente por debajo
  de XGBoost.
- Si no supera AUC/PR-AUC o macro OvR AUC del XGBoost, reportarla como
  sensibilidad negativa y cerrar la busqueda de algoritmos.

Resultado sample 500k, 3 folds, `full_plus_rhythm_context_routine_daily_tour`:

- Binario: AUC 0.6648, PR-AUC 0.2549.
- Multiclase: macro OvR AUC 0.6721, balanced accuracy 0.3335.

Lectura:

- La MLP queda claramente por debajo de XGBoost (`AUC=0.6842`, `PR-AUC=0.2771`,
  `macro OvR AUC=0.7090`) y tambien bajo CatBoost.
- No se recomienda correr full 5-fold; el resultado ya es una sensibilidad
  negativa suficiente salvo que se quiera cerrar formalmente en full data.

Resultado full 5 folds:

- Binario: AUC 0.6742, PR-AUC 0.2659.
- Multiclase: macro OvR AUC 0.6956, balanced accuracy 0.3340.

Lectura full:

- El full mejora respecto de la muestra, pero sigue por debajo de XGBoost y
  CatBoost.
- La MLP no cambia la conclusion sobre clasificacion dura multiclase: balanced
  accuracy sigue dominado por la clase BIP.
- Se cierra MLP como sensibilidad negativa de algoritmo flexible.

## 2026-06-10 - Local QR Exposure Pack fold-safe

Decision:

- Se agrega `--local-qr-exposure` a `run_user_ml_benchmark.py`.
- Este pack no se materializa como columnas fijas de la matriz, porque hacerlo
  antes de CV produciria leakage.
- Las variables se calculan dentro de cada fold usando solo el train fold y se
  aplican al test fold.
- Para las filas de entrenamiento se usa leave-one-out: la tasa local excluye
  la propia observacion antes de alimentar el modelo.

Variables dinamicas:

- `lqe_home_zone_qr_rate`
- `lqe_origin_zone_qr_rate`
- `lqe_activity_zone_qr_rate`
- `lqe_home_origin_zone_qr_rate`
- `lqe_origin_activity_zone_qr_rate`

Interpretacion:

- Si mejora, la lectura correcta es que existe clustering espacial/OD de la
  adopcion QR.
- No debe reportarse como evidencia causal de territorio; es un target encoding
  predictivo y debe quedar separado de las features exogenas o conductuales.

Validacion:

- `py_compile` OK.
- Tests unitarios OK: verifican que test use solo train-fold stats y que train
  use leave-one-out.
- Smoke real OK con sample 5k, 2 folds y 5 arboles; la matriz pasa de 141 a
  146 features por las 5 columnas `lqe_*`.

Resultados `alta_n3`, XGB binario, `full_plus_rhythm_context_routine_daily_tour`:

- Benchmark base sin LQE: AUC 0.6842, PR-AUC 0.2771.
- LQE con `min_count=100`, `smoothing=100`: AUC 0.5482, PR-AUC 0.1700.
- LQE con `min_count=1000`, `smoothing=1000`: AUC 0.5494, PR-AUC 0.1683.

Lectura:

- La prevalencia QR local fold-safe no mejora el modelo; lo degrada de forma
  fuerte y consistente incluso con smoothing alto.
- Se descarta como feature set principal.
- Si se menciona, debe quedar como sensibilidad negativa: el clustering local
  de adopcion QR no generaliza de forma estable en CV o induce splits
  inestables en XGBoost.

## 2026-06-10 - Feedback metodologico profesor: entender poblaciones antes de modelar

Contexto:

- El profesor indico que falta entender mejor como son los datos y que
  diferencia a las poblaciones observadas BIP vs QR.
- Tambien sugirio que puede ser interesante aprovechar la dimension 2024-2025
  para estudiar que zonas residenciales cambiaron mas en adopcion QR.
- Una posibilidad posterior seria probar modelos separados por zonas o grupos
  territoriales, pero no como primer paso.

Decision de proceso:

- Antes de crear un notebook nuevo, se debe acordar que preguntas descriptivas
  queremos responder.
- El siguiente EDA debe partir simple y documentar claramente la unidad de
  analisis: `id_tarjeta` como proxy operacional de usuario.
- Caveat central: una persona podria tener mas de una tarjeta; por lo tanto,
  BIP vs QR compara tarjetas/poblaciones observadas, no necesariamente personas
  unicas.

Preguntas iniciales a responder:

- Tamano y composicion: cuantos `id_tarjeta`, viajes y dias activos hay en BIP,
  QR_OTHER y QR_RED?
- Cohorte temporal: QR se concentra en tarjetas que aparecen en 2025, en ambos
  anos, o tambien esta presente en 2024?
- Intensidad de uso: QR y BIP difieren en numero de viajes, dias activos,
  semanas activas y regularidad?
- Perfil horario: QR y BIP difieren en hora media, dispersion horaria, punta,
  valle o horarios no laborales?
- Perfil modal: QR y BIP difieren en uso de bus, metro, combinaciones y
  transbordos?
- Rutina/regularidad: QR y BIP difieren en repeticion de OD, concentracion de
  zonas, dias complejos o patrones tipo commute?
- Territorio residencial y de origen: QR y BIP se concentran en macrozonas,
  zonas de residencia u origen distintas?
- Socioeconomia territorial: las zonas residenciales de QR y BIP difieren en
  ingreso proxy, educacion, edad, inmigracion u otras variables censales?
- Oferta/acceso: QR y BIP difieren en acceso territorial a puntos BIP, metro,
  buses u oferta de transporte?
- Subpoblaciones QR: QR_RED y QR_OTHER se parecen entre si, o deben tratarse
  como poblaciones distintas?

Preguntas para una segunda etapa, no inmediata:

- Como cambia el share QR por zona residencial entre 2024 y 2025?
- El cambio zonal parece explicado por composicion territorial, oferta,
  variables socioeconomicas o entrada de nuevas tarjetas?
- Tiene sentido estimar regresiones zonales o modelos separados por macrozona
  una vez entendidas las diferencias descriptivas?

## 2026-07-15 - Separacion del EDA exploratorio y la revision profunda

Problema:

- `eda_qr_vs_bip_profiles.qmd` acumulaba bloques antiguos, nuevas preguntas y
  analisis rehechos, lo que dificultaba saber cual era la secuencia vigente.
- La revision se encontraba cerrando el subbloque 4.2; continuar editando el
  mismo archivo aumentaba el riesgo de reutilizar resultados o helpers de
  bloques que ya no respondian al enfoque actual.

Decision:

- El notebook original se conserva sin recortes como archivo exploratorio.
- Se crea `02_eda/eda_qr_vs_bip_profiles_refined.qmd` como version principal.
- La copia refinada termina despues del subbloque 4.2 y no incluye el Bloque 5.
- Se retiraron de la copia las funciones, constantes y dependencias exclusivas
  de los bloques posteriores, incluido el shapefile territorial.

Criterio de trabajo:

- Cada bloque nuevo se agregara solo despues de cerrar la pregunta, la lectura
  descriptiva, las explicaciones alternativas y las limitaciones del anterior.
- La siguiente decision pendiente es cerrar 4.2 antes de definir un Bloque 5.

## 2026-07-15 - EDA refinado Bloque 4: repeticion espacial

Pregunta:

- Cuando una tarjeta vuelve a utilizarse, hasta que punto repite rutas y zonas
  observadas?

Resultados descriptivos:

- En el universo amplio, BIP y QR presentan la misma mediana para el peso del
  OD dirigido principal (25,0%) y de la ruta principal con ida y vuelta
  agrupadas (33,3%).
- Al estratificar por cantidad de viajes, las curvas de ambos medios se
  superponen en gran parte. Las diferencias puntuales cambian de direccion
  entre universos y no forman un ordenamiento general.
- La mediana agregada de zonas distintas es 7 en BIP y 6 en QR, pero esta
  comparacion incorpora diferencias de volumen observado.
- Entre identificadores persistentes, ambos grupos registran una mediana de 9
  zonas distintas; entre los repetidos, ambos registran 11.
- El peso de las dos zonas principales permanece cercano y las diferencias
  observadas en persistentes o repetidos son de alrededor de dos puntos
  porcentuales.

Lectura de trabajo:

- La separacion temporal documentada previamente no aparece con una magnitud
  equivalente en repeticion espacial.
- Condicionadas por rangos comparables de viajes, las distribuciones de rutas y
  zonas de BIP y QR muestran una superposicion considerable.
- Esta lectura describe proximidad entre perfiles y no prueba igualdad.

Limitaciones:

- Contar ZONA777 distintas no mide distancia ni exploracion fisica, porque las
  zonas tienen superficies diferentes.
- Las comparaciones usan medianas y rangos amplios de viajes, que pueden ocultar
  heterogeneidad dentro de cada grupo.
- La unidad sigue siendo el identificador de tarjeta y no la persona.

## 2026-07-15 - EDA refinado Bloque 5: momento de uso

Pregunta general:

- Cuando una tarjeta se utiliza, sus viajes se concentran en los mismos dias y
  franjas horarias?

Subpreguntas implementadas:

- 5.1: Que parte del uso ocurre en dias no laborales?
- 5.2: Como se distribuyen los viajes entre punta AM, punta PM, resto del dia
  laboral y dias no laborales?
- 5.3: Las tarjetas concentran sus viajes en una franja principal o utilizan
  varias franjas?
- 5.4: La lectura se mantiene entre tarjetas persistentes y repetidas?

Definiciones y unidad:

- La unidad de comparacion es `id_tarjeta`; cada tarjeta pesa igual.
- El universo amplio exige al menos tres viajes observados.
- Se reutilizan las definiciones existentes del panel: punta AM laboral
  06:00-08:59, punta PM laboral 18:00-19:59, resto del dia laboral y dia no
  laboral completo.
- `No laboral` proviene de `tipodia`; no debe llamarse fin de semana porque
  puede incluir feriados.

Metricas:

- Share de viajes no laborales por tarjeta.
- Composicion media de los cuatro contextos horarios, con tarjetas ponderadas
  por igual.
- Peso de la franja principal y numero de franjas utilizadas.
- Perfiles de concentracion condicionados por rangos de viajes: 3-5, 6-10,
  11-20 y 21 o mas.

Resguardos metodologicos:

- Las cuatro franjas no tienen la misma duracion. La concentracion describe
  contextos predefinidos y no dispersion continua durante las 24 horas.
- El numero de franjas utilizadas depende mecanicamente del numero de viajes;
  por eso se compara dentro de rangos de viajes.
- Persistente y repetido son universos seleccionados por actividad. Los cambios
  de nivel entre universos no deben interpretarse como cambios conductuales.
- No se escribieron findings anticipados. La interpretacion se hara despues de
  que el usuario ejecute y lea cada subbloque.

Implementacion y validacion:

- Notebook: `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- Celdas: `block5-temporal-setup`, `block5a-laboral-nonlaboral`,
  `block5b-time-band-composition`, `block5c-temporal-concentration` y
  `block5d-temporal-universe-sensitivity`.
- Se comprobo que los shares horarios suman uno, se validaron los rangos de las
  metricas y se ejecutaron aisladamente todas las celdas nuevas.
- No se renderizo el notebook completo.

## 2026-07-16 - Validacion horaria de las franjas laborales

Objetivo:

- Verificar si la composicion observada en 5.2 depende de los cortes horarios
  predefinidos o tambien se observa en el perfil continuo de 24 horas.

Metodo:

- Se restringe a dias laborales (`tipodia == 0`) y a tarjetas con al menos
  tres viajes laborales.
- Para cada tarjeta se calcula la proporcion de viajes que comienza en cada
  hora; las horas sin viajes cuentan como cero.
- Las proporciones se promedian dando igual peso a cada tarjeta.

Ejecucion:

- Celda: `block5b-hourly-labor-profile`.
- Tarjetas incluidas: 3.745.419 BIP y 694.508 QR.
- El perfil horario suma 100% en ambos grupos, como exige la construccion.
- La hora con mayor proporcion promedio es 07:00 para BIP y 18:00 para QR.
- Ambos grupos presentan una forma bimodal similar, con puntas de manana y
  tarde.
- En QR el maximo matinal ocurre una hora mas tarde (08:00 frente a 07:00) y
  la punta de la tarde es mas marcada; BIP mantiene mayor peso relativo entre
  las puntas, aproximadamente entre 09:00 y 16:00.
- Esta redistribucion confirma que el resultado agregado de 5.2 no surge solo
  de los cortes de las franjas.
- Como cada perfil suma 100%, mas peso relativo en las puntas implica menos
  peso en horas intermedias. No corresponde interpretarlo como mayor volumen
  absoluto de viajes ni como evidencia directa del motivo de viaje.

## 2026-07-16 - Bloque 5.3: concentracion temporal

Resultado descriptivo:

- El peso mediano de la franja principal disminuye a medida que aumenta el
  numero de viajes observados.
- La mediana de franjas utilizadas aumenta de 2 a 4 y coincide entre BIP y QR
  en todos los rangos de viajes.
- Las diferencias del peso de la franja principal son pequenas en la mayor
  parte de los rangos; el primer rango (3-5 viajes) presenta la separacion mas
  visible.

Resguardos:

- La menor concentracion y el mayor numero de franjas con mas viajes son en
  parte mecanicos: una tarjeta tiene mas oportunidades de aparecer en otros
  contextos temporales.
- La mediana de franjas es una medida discreta y poco sensible. La
  superposicion de las curvas no prueba que las distribuciones completas sean
  iguales.
- Debe decirse que ambos grupos siguen una secuencia similar, no que aumentan
  "a la misma velocidad", porque los rangos del eje X no tienen igual ancho.

Control agregado:

- Se incorporo `block5c-band-count-distribution` como 5.3.1.
- Muestra, dentro de cada rango de viajes del universo amplio, el porcentaje
  de tarjetas que utiliza 1, 2, 3 o 4 franjas.
- Su objetivo es comprobar si medianas iguales ocultan distribuciones
  diferentes; no reemplaza 5.4, que responde a sensibilidad entre universos.
- Estado: ejecutado e interpretado; el resultado se incorporo al cierre del
  Bloque 5.

## 2026-07-16 - Bloque 5.3.1 y repeticion de franja principal

Resultado de 5.3.1:

- La cantidad de viajes observados domina la amplitud horaria: al aumentar los
  viajes cae la proporcion de tarjetas restringidas a una o dos franjas y
  aumenta la presencia en tres o cuatro.
- Las medianas de 5.3 ocultaban una diferencia moderada de distribucion. Dentro
  de cada rango de viajes, QR presenta menos tarjetas en una sola franja y algo
  mas en tres o cuatro franjas.
- Esto no demuestra menor rutina. Numero de franjas es una medida de amplitud
  observada y aumenta mecanicamente con las oportunidades de observacion.

Control agregado como 5.3.2:

- Celda: `block5c-main-band-persistence`.
- Compara la franja mas utilizada por cada tarjeta en 2024 y 2025 para los
  universos `Persistente` y `Repetido`.
- No se desempatan casos con dos o mas franjas igualmente frecuentes. Se
  reporta la cobertura de tarjetas con una franja principal unica en ambos
  anos y, dentro de ellas, el porcentaje que mantiene la misma franja.
- `Persistente` exige presencia en ambas ventanas y al menos tres viajes en
  total; `Repetido` exige al menos dos semanas activas en cada ano.
- La celda se valido sintacticamente junto a las 38 celdas Python del notebook.
  Una prueba sintetica confirmo la exclusion de empates y el calculo del
  porcentaje de repeticion.
- No se renderizo el notebook completo.

Resultado de 5.3.2:

- La cobertura de tarjetas con una franja principal unica en ambos anos es
  80,1% BIP y 73,5% QR en Persistente; 84,1% BIP y 78,6% QR en Repetido.
- Entre esas tarjetas comparables, mantiene la misma franja principal el 68,5%
  de BIP y 60,0% de QR en Persistente; en Repetido, 72,2% y 64,2%.
- La brecha de repeticion se mantiene cercana a ocho puntos porcentuales al
  exigir actividad repetida.

## 2026-07-16 - Cierre del Bloque 5

Lectura integrada:

- La mayor parte de la actividad BIP y QR ocurre en dias laborales y ambos
  grupos presentan perfiles horarios bimodales similares.
- QR asigna ligeramente mas peso a puntas y dias no laborales; BIP presenta
  mayor peso relativo durante el resto del dia laboral.
- La amplitud horaria depende principalmente de la cantidad de viajes. Dentro
  de rangos comparables, QR presenta algo menos de tarjetas restringidas a una
  franja y algo mas presentes en tres o cuatro.
- La franja principal concentra una proporcion mayor de los viajes BIP y se
  mantiene con mayor frecuencia entre 2024 y 2025. La diferencia de estabilidad
  es cercana a ocho puntos tanto en Persistente como en Repetido.
- La sensibilidad de 5.4 confirma que el patron no desaparece al restringir el
  universo: ambos grupos suelen usar el mismo numero de franjas, pero difieren
  moderadamente en como reparten sus viajes entre ellas.

Conclusion:

- BIP y QR no muestran estructuras temporales completamente distintas. Las
  diferencias son consistentes pero moderadas: QR distribuye su actividad algo
  mas entre contextos temporales, mientras BIP presenta una franja principal
  observada mas dominante y estable.

## 2026-07-16 - Bloque 6.0: definiciones y exposicion semanal

Objetivo:

- Preparar el analisis por dia de semana sin confundir diferencias de uso con
  diferencias en la cobertura del calendario.
- Separar explicitamente el dia calendario de `tipodia`: un feriado puede
  ocurrir de lunes a viernes y seguir siendo un dia no laboral.

Implementacion:

- Celda: `block6-weekday-exposure-audit` en
  `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- El dia se deriva de `tiempo_inicio_viaje` con numeracion ISO: lunes = 1 y
  domingo = 7.
- La tabla reporta, por ano y dia de semana, fechas observadas, fechas
  laborales y fechas no laborales.
- Controles incluidos: presencia de los siete dias en cada ano, igualdad de
  fechas por dia, consistencia de `tipodia` dentro de cada fecha y ausencia de
  fechas repetidas entre archivos semanales.

Validacion aislada:

- Las fuentes de 2024 contienen cuatro fechas de cada dia de semana.
- En 2025 hay tres lunes y cuatro fechas para cada uno de los otros dias. La
  fecha 2025-03-31 no aparece en las fuentes observadas, aunque corresponde al
  lunes de la semana ISO W14.
- No se detectaron fechas con multiples clasificaciones `tipodia` ni fechas
  repetidas entre archivos.
- En 2025 aparece un viernes clasificado como no laboral, evidencia concreta
  de que dia calendario y tipo de dia no son equivalentes.
- Se valido la sintaxis de las 39 celdas Python del notebook. No se renderizo
  el notebook completo.

Estado:

- 6.0 implementado; pendiente de ejecucion y revision por el usuario.
- No se agregaron todavia resultados BIP-QR ni findings del Bloque 6.
- Los analisis posteriores deben normalizar frecuencias por el numero de fechas
  observadas. Los conteos brutos subrepresentarian el lunes de 2025.

## 2026-07-16 - Bloque 6.1: composicion semanal ajustada

Objetivo:

- Comparar como se distribuye el perfil de viajes de una tarjeta entre lunes
  y domingo sin confundir uso con disponibilidad desigual de fechas.

Implementacion:

- Celda: `block6a-weekday-composition` en
  `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- Universo: `Amplio (>=3 viajes)`; unidad de analisis: `id_tarjeta`.
- Para cada tarjeta se cuentan los viajes por dia, se divide cada conteo por
  las fechas observadas de ese dia y se normalizan los siete valores para que
  sumen 100%.
- El resumen promedia esos perfiles dando el mismo peso a cada tarjeta. La
  tabla conserva el numero de fechas utilizado como denominador y el grafico
  compara el perfil lunes-domingo de BIP y QR.

Validacion:

- Las 40 celdas Python del notebook tienen sintaxis valida.
- Una prueba sintetica verifico el ajuste entre 7 lunes y 8 martes: una tarjeta
  con un viaje en cada dia recibe pesos ajustados de 53,3% y 46,7%,
  respectivamente.
- Tambien se verifico que cada perfil agregado suma 100%.
- No se renderizo el notebook completo ni se agregaron findings; queda
  pendiente la ejecucion e interpretacion inicial del usuario.

Resultado de 6.1:

- Las curvas BIP y QR del universo amplio presentan una forma semanal casi
  identica.
- Las diferencias descriptivas son pequenas: BIP muestra 0,5 puntos mas el
  lunes, mientras QR muestra 0,7 puntos mas el sabado y 0,6 el domingo.
- Sabado y domingo suman 14,4% para BIP y 15,7% para QR. Esta comparacion es
  consistente con el Bloque 5, pero no equivale a su mediana de proporcion no
  laboral: 6.1 usa promedios ajustados por exposicion y dias calendario.

## 2026-07-17 - Bloque 6.2: sensibilidad por universo

Objetivo:

- Evaluar si el pequeno mayor peso relativo de QR durante el fin de semana se
  mantiene o aumenta entre tarjetas persistentes y repetidas.

Implementacion:

- Celda: `block6b-weekday-universe-sensitivity`.
- Reutiliza `card_weekday_profile` de 6.1; no vuelve a escanear los archivos
  de viajes.
- Compara `Amplio (>=3 viajes)`, `Persistente` y `Repetido` en tres paneles
  con escala vertical comun.
- La tabla compacta reporta tarjetas y la composicion lunes-viernes versus
  sabado-domingo para cada grupo y universo.

Validacion:

- Las 41 celdas Python del notebook tienen sintaxis valida.
- Una prueba sintetica verifico los filtros de universos, sus denominadores y
  que cada perfil BIP/QR suma 100%.
- No se renderizo el notebook completo.

Resultado:

- El perfil semanal permite distinguir BIP y QR: QR asigna consistentemente
  una mayor proporcion de su actividad al fin de semana, especialmente entre
  tarjetas persistentes y repetidas.
- Ambos conservan la misma estructura semanal general. La diferencia temporal
  es secundaria y no basta por si sola para explicar la menor intensidad total
  de QR.
- Hipotesis derivada: puede existir un segmento estable de uso QR contextual
  fuera de la rutina laboral. Para algunas personas podria complementar a BIP;
  para otras, podria ser el unico medio observado si usan transporte publico
  principalmente en fines de semana u ocasiones especificas.
- El aumento de la diferencia en `Persistente` y `Repetido` sugiere que el
  patron no proviene solo de tarjetas QR breves, pero no prueba el mecanismo.
- Como los perfiles suman 100%, el resultado no implica mayor volumen absoluto
  de viajes QR el fin de semana. Tampoco se observa si una persona posee BIP.
- Contrastes pendientes para evaluar el mecanismo: tasas absolutas ajustadas
  por fecha y persistencia interanual de la orientacion al fin de semana dentro
  de la misma tarjeta.

## 2026-07-17 - Bloque 6.3.1: tasas absolutas por fecha

Objetivo:

- Separar dos mecanismos compatibles con el mayor peso relativo de fin de
  semana en QR: mas viajes absolutos durante sabado/domingo o menos viajes de
  lunes a viernes.

Implementacion:

- Celda: `block6c-absolute-calendar-rates` en
  `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- Unidad: tarjeta; cada tarjeta pesa lo mismo en el promedio.
- Universos: `Amplio (>=3 viajes)`, `Persistente` y `Repetido`.
- Metricas: viajes por fecha observada de lunes-viernes y viajes por fecha
  observada de sabado-domingo.
- La clasificacion es calendario, no `tipodia`; un feriado de viernes se
  mantiene dentro de lunes-viernes.
- El denominador se arma por presencia anual: una tarjeta observada en un solo
  ano usa solo las fechas de esa ventana y una tarjeta presente en ambos usa
  ambas ventanas.

Resguardo metodologico:

- Se considera disponible toda la ventana anual donde la tarjeta registra al
  menos un viaje. No se conoce la fecha real de emision ni si estuvo disponible
  antes de su primera aparicion observada.
- Las tasas permiten distinguir mecanismos descriptivos, pero no identifican
  motivo de viaje ni vinculan tarjetas BIP y QR de una misma persona.

Estado:

- Implementado y ejecutado por el usuario.
- En `Amplio`, QR presenta una tasa menor que BIP tanto de lunes a viernes
  como durante el fin de semana, pero la brecha es mayor en dias laborales.
- En `Persistente`, la tasa de fin de semana se equipara mientras QR mantiene
  una tasa laboral menor. En `Repetido`, QR supera moderadamente a BIP durante
  el fin de semana y permanece debajo en dias laborales.
- El mayor peso relativo del fin de semana en QR no tiene un mecanismo unico:
  en el universo amplio proviene principalmente de menor actividad laboral;
  entre tarjetas mas constantes tambien aparece una diferencia absoluta de
  fin de semana.
- Validacion: las 42 celdas Python tienen sintaxis valida y una prueba
  sintetica confirmo denominadores `20/8` para tarjetas solo 2024, `19/8` para
  solo 2025 y `39/16` para tarjetas presentes en ambos anos.
- Se corrigio el solapamiento de etiquetas del grafico posicionando los
  valores hacia afuera de cada par BIP-QR y ampliando sus margenes.
- No se renderizo el notebook completo.

## 2026-07-17 - Bloque 6.3.2: continuidad del uso de fin de semana

Objetivo:

- Evaluar si el uso de fin de semana reaparece en la misma tarjeta entre 2024
  y 2025, en vez de inferir estabilidad desde composiciones agregadas.

Implementacion:

- Celda: `block6c-weekend-continuity` en
  `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- Universos: `Persistente` y `Repetido`; unidad: `id_tarjeta`.
- Clasifica cada tarjeta en `Ambos anos`, `Solo 2024`, `Solo 2025` o
  `Ningun ano` segun registre al menos un viaje sabado/domingo en cada ventana.
- Calcula por medio de pago
  `P(uso fin de semana 2025 | uso fin de semana 2024)`, usando como denominador
  solo las tarjetas con uso de fin de semana en 2024.
- El grafico combina la composicion de las cuatro trayectorias con una
  comparacion directa de la probabilidad condicional BIP-QR.

Validacion:

- Las 43 celdas Python del notebook tienen sintaxis valida.
- Una prueba sintetica recupero correctamente las cuatro trayectorias, verifico
  que sus shares sumen 100% y obtuvo probabilidades condicionales esperadas de
  100% para BIP y 0% para QR en el ejemplo controlado.
- No se renderizo el notebook completo ni se agrego un finding antes de que el
  usuario ejecute e interprete los resultados reales.

## 2026-07-20 - Bloque 6.3.3: sensibilidad a igual soporte anual

Objetivo:

- Evaluar si las diferencias BIP-QR de uso de fin de semana permanecen al
  comparar tarjetas con el mismo numero de semanas activas en 2024 y 2025.
- Separar una posible diferencia temporal de la seleccion composicional que
  ocurre al exigir mayor actividad.

Decision metodologica:

- Universo: tarjetas presentes en ambos anos y con al menos tres viajes en el
  panel refinado.
- Estratificacion exacta: combinacion de semanas activas 2024 y semanas activas
  2025, con valores de 1 a 4 en cada eje.
- Se prefieren semanas activas a numero total de viajes porque los viajes de
  fin de semana forman parte del resultado que se busca explicar.
- Resultados comparados dentro de cada celda:
  - viajes promedio de fin de semana por fecha disponible;
  - `P(uso fin de semana 2025 | uso fin de semana 2024)`.
- Umbrales visuales: al menos 1.000 tarjetas por medio para la tasa y al menos
  500 tarjetas con uso de fin de semana en 2024 por medio para la continuidad.

Implementacion:

- Celda: `block6c-weekend-equal-support` en
  `02_eda/eda_qr_vs_bip_profiles_refined.qmd`.
- Reutiliza `weekend_continuity_cards`, `lf_temporal_persistent`,
  `lf_broad_cards` y `daily_calendar_audit`; no vuelve a escanear los archivos
  semanales de viajes.
- La tabla conserva los tamanos de cada grupo, las tasas BIP/QR, las bases de
  continuidad y las diferencias `QR - BIP`.
- La figura usa dos matrices 4x4: una para la tasa de fin de semana y otra para
  la continuidad interanual.

Validacion:

- Las 44 celdas Python del notebook tienen sintaxis valida.
- Una prueba sintetica con las 16 combinaciones de soporte valido joins,
  denominadores, diferencias y generacion del grafico.
- No se renderizo el notebook completo.
- Estado: implementado, ejecutado e interpretado con los datos reales.

### Lectura integrada del Bloque 6

Este bloque busca determinar si BIP y QR se utilizan de manera diferente
durante la semana y, en particular, si QR tiene una mayor presencia durante el
fin de semana.

Antes de compararlos se corrigieron las diferencias del calendario observado,
como el lunes faltante de 2025. Asi evitamos atribuir a los medios de pago
diferencias producidas simplemente por tener distinta cantidad de fechas
disponibles.

**1. Ambos medios siguen una estructura semanal similar**

BIP y QR concentran la mayor parte de su actividad entre lunes y viernes. La
actividad disminuye el viernes y cae claramente durante sabado y domingo. Por
tanto, QR no presenta una estructura semanal completamente distinta de BIP.

Sin embargo, el fin de semana representa una parte ligeramente mayor de los
viajes QR:

- BIP: aproximadamente 14,4%.
- QR: aproximadamente 15,7%.

Esta comparacion es relativa: indica como se distribuyen los viajes de cada
tarjeta, pero no implica necesariamente que QR realice mas viajes de fin de
semana.

**2. La mayor proporcion QR se explica inicialmente por su menor actividad laboral**

Para distinguir proporciones de cantidades efectivas, calculamos los viajes
promedio por tarjeta y por fecha disponible:

| Universo amplio | Lunes a viernes | Fin de semana |
|---|---:|---:|
| BIP | 0,64 | 0,22 |
| QR | 0,53 | 0,20 |

En el universo amplio, QR registra menos viajes que BIP tanto durante la
semana como durante el fin de semana. La diferencia es mucho mayor de lunes a
viernes.

Esto explica la aparente contradiccion: el fin de semana representa una
proporcion mayor de los viajes QR, pero no porque estas tarjetas viajen mas
durante esos dias. Ocurre principalmente porque acumulan bastante menos
actividad laboral.

**3. El resultado cambia parcialmente entre las tarjetas mas constantes**

Al concentrarnos en tarjetas observadas en ambos anos, BIP continua mostrando
mas actividad laboral, pero la actividad de fin de semana se equipara:

| Tarjetas observadas en ambos anos | Lunes a viernes | Fin de semana |
|---|---:|---:|
| BIP | 0,66 | 0,21 |
| QR | 0,55 | 0,21 |

Cuando ademas exigimos actividad durante al menos dos semanas de cada ano, la
diferencia laboral permanece, pero QR pasa a registrar ligeramente mas viajes
de fin de semana:

| Sensibilidad de mayor actividad | Lunes a viernes | Fin de semana |
|---|---:|---:|
| BIP | 0,89 | 0,27 |
| QR | 0,78 | 0,30 |

Por tanto, las tasas totales de BIP y QR no se equiparan. BIP sigue registrando
mas actividad de lunes a viernes. Lo que se iguala, y luego se invierte
ligeramente, es solamente la actividad de fin de semana.

**4. La diferencia no depende solo del numero de semanas activas**

Finalmente, comparamos BIP y QR dentro de grupos con exactamente el mismo
numero de semanas activas en 2024 y 2025.

En las 16 combinaciones analizadas, QR presento una tasa de viajes de fin de
semana mayor que BIP. La diferencia fue casi nula entre tarjetas con poca
actividad, pero aumento entre las activas durante mas semanas.

Esto debilita la explicacion de que el resultado se deba unicamente a que BIP
y QR tienen una composicion diferente de semanas activas.

**Conclusion**

BIP y QR conservan una estructura semanal general similar. La menor intensidad
total de QR se concentra principalmente de lunes a viernes.

En el universo completo, su mayor participacion relativa durante el fin de
semana se explica sobre todo por esa menor actividad laboral. Sin embargo,
entre las tarjetas observadas de manera mas constante aparece tambien una
actividad de fin de semana ligeramente mayor y mas persistente en QR.

El resultado es compatible con que exista un subconjunto de tarjetas QR
utilizado regularmente durante el fin de semana. No permite afirmar que sean
viajes recreativos, que QR complemente una tarjeta BIP ni que el medio de pago
produzca ese comportamiento, porque observamos tarjetas y no personas ni
propositos de viaje.

## 2026-07-20 - Bloque 7.0: auditoria modal

Se inicio el bloque de composicion modal en:

- `02_eda/eda_qr_vs_bip_profiles_refined.qmd`

Pregunta general:

- Evaluar si BIP y QR presentan diferencias en la combinacion de modos
  utilizada y si estas diferencias ayudan a caracterizar sus patrones de uso.

Definicion operacional a nivel de viaje:

- `Solo bus`: contiene Bus (`1`) o Zona Paga (`3`) y no contiene modos
  ferroviarios.
- `Solo Metro/ferroviario`: contiene Metro (`2`) o MetroTren (`4`) y no
  contiene bus.
- `Bus + Metro/ferroviario`: contiene al menos una etapa de ambos grupos.
- Se revisan las seis etapas posibles (`tipo_transporte_1` a
  `tipo_transporte_6`), no solo las primeras cuatro.

Implementacion de `block7-modal-coverage-audit`:

- Reconstruye la clasificacion directamente desde los parquets de viajes.
- Restringe la auditoria al universo analitico del notebook.
- Reporta cobertura modal, composicion de las tres categorias, viajes sin
  codigo y codigos inesperados por BIP, QR y total.
- Comprueba adicionalmente que las tres shares agregadas por tarjeta sean
  completas y sumen uno.
- Se agrego `block7-modal-composition-plot`: dos barras horizontales apiladas
  al 100% para comparar la composicion interna BIP/QR. El total se excluye del
  grafico porque mezcla los grupos y queda dominado por el volumen BIP; la
  tabla conserva los conteos y chequeos de cobertura.

Alcance:

- Este sub-bloque solo valida la medicion.
- Los perfiles modales y su interpretacion se dejan para los siguientes
  sub-bloques, despues de revisar conjuntamente el resultado de la auditoria.

### Bloque 7.1 - Composicion modal por tarjeta y por viajes

Se implemento `block7-modal-card-vs-trip-composition` para comparar dos
estimandos sobre el mismo universo `alta_n3`:

- `Cada tarjeta pesa igual`: promedio de los shares modales calculados dentro
  de cada tarjeta. Describe la composicion de una tarjeta promedio.
- `Cada viaje pesa igual`: shares obtenidos al agregar todos los viajes. Las
  tarjetas con mayor actividad tienen mas influencia.

La celda entrega una tabla con ambas ponderaciones y una figura de dos paneles
con la misma escala, orden y colores. El objetivo es observar si el perfil
modal agregado cambia cuando se pondera por intensidad. Una diferencia entre
ambas ponderaciones no se interpretara automaticamente como concentracion en
unas pocas tarjetas; si fuera relevante, requeriria una sensibilidad que
excluya la cola de mayor intensidad.

### Bloque 7.2 - Concentracion modal por tarjeta

Se implementaron tres sub-bloques complementarios:

- `block7-modal-specialization-concentration`: calcula, para cada tarjeta, el
  peso de su categoria modal principal y resume su mediana, rango
  intercuartil, predominio claro y concentracion alta.
- `block7-modal-dominance-type`: clasifica las tarjetas segun predomine solo
  bus, solo Metro/ferroviario, bus + Metro/ferroviario o no exista un
  predominio claro.
- `block7-modal-specialization-trip-sensitivity`: repite la clasificacion para
  tarjetas con `3-5`, `6-10`, `11-20` y `21+` viajes, evitando atribuir al
  medio de pago una concentracion producida mecanicamente por tener pocas
  observaciones.

Definicion usada:

- El modo principal es la categoria con mayor share dentro de la tarjeta.
- Existe predominio claro cuando esa categoria alcanza al menos 50% y no esta
  empatada con otra categoria.
- La concentracion se conserva tambien como medida continua; el umbral de 50%
  se usa solo para construir una clasificacion interpretable.

Alcance:

- La unidad sigue siendo la tarjeta, no la persona.
- La clasificacion describe los viajes observados y no demuestra una
  preferencia modal estable del individuo.
- Los findings se anotaran despues de revisar conjuntamente las tablas y
  figuras resultantes.

### Bloque 7.3 - Intermodalidad dentro y entre viajes

Se implementaron tres sub-bloques en
`02_eda/eda_qr_vs_bip_profiles_refined.qmd`:

- `block7-intermodality-within-trip`: compara el porcentaje de tarjetas con
  al menos un viaje `Bus + Metro/ferroviario`, el peso promedio de esos viajes
  y su mediana condicional cuando existen.
- `block7-intermodality-patterns`: separa cuatro perfiles mutuamente
  excluyentes: un solo modo observado, ambos modos en viajes separados,
  intermodalidad dentro del viaje y coexistencia de ambos patrones.
- `block7-intermodality-trip-sensitivity`: compara la presencia de viajes
  combinados y la diversidad entre viajes dentro de los rangos `3-5`, `6-10`,
  `11-20` y `21+` viajes.

Definiciones:

- Intermodalidad dentro del viaje: al menos un viaje clasificado como `Bus +
  Metro/ferroviario`.
- Diversidad entre viajes: al menos un viaje `Solo bus` y al menos uno `Solo
  Metro/ferroviario` en la misma tarjeta.
- Ambos indicadores pueden coexistir; la tipologia evita contarlos como
  categorias superpuestas.

Alcance:

- La sensibilidad por soporte es necesaria porque la oportunidad de observar
  categorias distintas aumenta mecanicamente con el numero de viajes.
- La unidad sigue siendo la tarjeta y no permite vincular distintos medios de
  pago de una misma persona.
- Los findings se anotaran despues de revisar las salidas con el usuario.

#### 7.3.4 Sensibilidad territorial

- Se agrego `block7-intermodality-od-sensitivity` para comparar la proporcion
  de viajes combinados dentro de pares OD dirigidos compartidos por BIP y QR.
- La comparacion principal exige al menos 100 viajes de cada medio por OD y
  reporta explicitamente la cobertura retenida.
- Se muestran tres niveles: todos los OD validos, los OD compartidos con la
  composicion observada de cada grupo y los mismos OD con una ponderacion
  territorial comun.
- La diferencia entre la brecha observada y la ponderada permite evaluar si la
  composicion territorial explica parte de la intermodalidad agregada. Sigue
  siendo una sensibilidad descriptiva y no una estimacion causal.
- Los findings se anotaran despues de revisar la salida con el usuario.

#### 7.3.5 Sensibilidad al umbral OD

- Se agrego `block7-intermodality-od-threshold-sensitivity` para comprobar que
  el resultado territorial no dependa de elegir arbitrariamente 100 viajes por
  medio en cada OD.
- Se repite la comparacion con soportes minimos de 25, 50, 100, 250 y 500
  viajes BIP y QR por OD.
- Para cada umbral se reportan pares OD retenidos, cobertura de viajes,
  proporciones combinadas observadas y con ponderacion OD comun, y ambas
  brechas BIP - QR.
- Los findings se anotaran despues de revisar la salida con el usuario.

### Bloque 7.4 - Robustez por soporte y continuidad

- Se agrego `block7-modal-equal-support` al cierre del bloque modal.
- Se comparan tres universos: `Amplio (>=3 viajes)`, `Persistente` y
  `Repetido`. Los dos ultimos controlan progresivamente la continuidad
  temporal; `Repetido` se mantiene como sensibilidad por ser un subconjunto
  de `Persistente`.
- Dentro de cada universo se ajustan BIP y QR a una distribucion comun de
  tarjetas en los rangos `3-5`, `6-10`, `11-20` y `21+` viajes. La
  ponderacion comun es el promedio simple de las distribuciones de ambos
  medios, para que el mayor tamano de BIP no determine el estandar.
- Se contrastan antes y despues del ajuste: peso promedio del modo principal,
  porcentaje con un solo modo observado y porcentaje con al menos un viaje
  combinado.
- La tabla conserva los valores absolutos por grupo; la figura resume las
  brechas `QR - BIP` observadas y ajustadas.
- El render verifico que los pesos comunes suman 100% en todos los universos
  y que las 12 celdas universo-rango contienen ambos medios de pago.

Alcance:

- El ajuste reduce la confusión por distinta cantidad de viajes observados,
  pero no controla territorio, recorridos, oferta de transporte ni
  caracteristicas no observadas de las tarjetas.
- Los findings se anotaran despues de revisar conjuntamente la tabla y la
  figura resultantes.

## 2026-07-23 - Cierre integrado del Bloque 7

Decision terminologica:

- Se usara **concentracion modal por tarjeta** en vez de `especializacion
  modal`. La medida describe cuanto pesan los viajes de la categoria principal
  dentro de cada tarjeta; no demuestra una preferencia estable de la persona.
- Los nombres internos de labels y objetos con `specialization` se mantienen
  para no romper la reproducibilidad del notebook.

Findings integrados:

- La cobertura modal es completa y equivalente en BIP y QR. Las diferencias
  posteriores no provienen de viajes sin clasificar.
- Ambos medios tienen una estructura general parecida: predomina
  `Solo Metro/ferroviario`, luego `Solo bus`, y los viajes combinados tienen
  una participacion menor.
- La mayoria de las tarjetas concentra sus viajes en una categoria principal.
  La mediana es 88,5% en BIP y 92,9% en QR. QR presenta una concentracion algo
  mayor, pero existe amplia superposicion entre ambos grupos.
- BIP muestra mas intermodalidad dentro del viaje en el agregado. La brecha de
  viajes combinados baja de 4,7 pp a aproximadamente 0,3-0,6 pp cuando se
  comparan OD compartidos, lo que apunta a un componente territorial
  importante.
- Igualar la cantidad de viajes reduce algunas brechas, pero QR conserva una
  mayor proporcion de tarjetas estrictamente unimodales con 3, 5 y 10 viajes.
  Al controlar tambien por OD principal, la diferencia se atenua fuertemente.
- Dentro de los perfiles de bus, Metro/ferroviario y combinado, QR mantiene un
  peso relativo algo mayor del fin de semana. En tasas absolutas registra
  menos viajes que BIP en ambos grupos de dias, pero la brecha es mucho mayor
  de lunes a viernes. La mezcla modal no explica por si sola el patron semanal
  del bloque 6.

Lectura de cierre:

> Las tarjetas QR presentan una concentracion modal algo mayor y menos viajes
> combinados que BIP en los resultados agregados. No obstante, gran parte de
> estas diferencias se atenua al comparar trayectos similares, lo que apunta
> a una explicacion principalmente composicional. El menor uso QR de lunes a
> viernes permanece dentro de los distintos perfiles modales, por lo que
> tampoco se explica solo por la mezcla entre bus y ferrocarril.

Limitaciones:

- La unidad es la tarjeta, no la persona.
- No se identifica el proposito del viaje.
- Las comparaciones son descriptivas y no permiten atribuir causalidad al
  medio de pago.
- Las sensibilidades por OD retienen una fraccion del universo y se interpretan
  como evidencia sugerente, no definitiva.

## 2026-07-23 - Implementacion del Bloque 8.0

Se inicio el Bloque 8 sobre geografia residencial y de los viajes en
`02_eda/eda_qr_vs_bip_profiles_refined.qmd`.

### Pregunta y unidades

Pregunta general:

- En que territorios se observan las tarjetas BIP y QR y cuanto de las
  diferencias posteriores puede depender de la composicion geografica.

La unidad cambia segun la pregunta:

- `zona_hogar`: tarjeta.
- `zona_inicio_viaje` y `zona_fin_viaje`: viaje.
- soporte: zona.

### Definicion de residencia

`zona_hogar` se reconstruye a partir de viajes con
`proposito_norm == "HOGAR"`:

1. se cuentan los destinos por tarjeta;
2. se elige el destino mas frecuente;
3. se calcula el peso de esa zona entre los viajes `HOGAR`;
4. se asigna confianza alta, media o baja segun concentracion y empates.

No corresponde al centroide, al origen mas frecuente ni a un domicilio
observado. La matriz principal exige confianza alta y `n_viajes >= 3`.

### Auditorias implementadas

`block8-geographic-audit` entrega:

- cobertura de residencia inferida y distribucion de confianza en el panel
  limpio con al menos tres viajes;
- porcentaje retenido por la matriz base;
- reconstruccion anual de `zona_hogar` para 2024 y 2025 con la misma regla;
- porcentaje con residencia anual disponible y de confianza alta en ambos
  anos;
- coincidencia de la zona anual entre tarjetas comparables;
- cobertura de origen, destino y OD en los viajes;
- soporte zonal para residencia, origen y destino, incluyendo umbrales de 25
  y 100 observaciones por medio;
- figura resumida de cobertura residencial y de viajes.

La estabilidad anual es una auditoria de la medicion. Una zona distinta puede
reflejar cobertura limitada de viajes `HOGAR`, cambios del identificador o
movilidad residencial real. No se interpretara como cambio de domicilio.

### Verificacion

- Las 62 celdas Python del QMD pasan parseo sintactico.
- No existen labels de celdas duplicados.
- `block8-geographic-audit` se ejecuto completo con los ocho parquets de
  viajes, la matriz base, el panel interanual y el bridge de proposito.
- Los findings territoriales quedan pendientes de la lectura inicial del
  usuario.
