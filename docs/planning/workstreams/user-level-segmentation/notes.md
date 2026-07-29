# Notas — Segmentacion User-Level / NMF

Bitacora del frente de segmentacion/perfilamiento a nivel `id_tarjeta`.
Para EDA, panel, matrices supervisadas y benchmark ML, ver:

- `docs/planning/workstreams/user-level-redesign/notes.md`
- `docs/planning/workstreams/user-level-redesign/task_plan.md`

## 2026-06-03 — Inicio del workstream de segmentacion user-level

Se crea un frente persistente separado para avanzar la linea que el profesor
habia sugerido como alternativa no predictiva: segmentar usuarios/tarjetas por
patrones de movilidad y luego evaluar si esos perfiles difieren en uso de
QR/BIP.

Motivacion:

- El set de variables supervisadas del ML sigue abierto por feature engineering.
- La segmentacion no debe depender de cerrar ese set.
- El objetivo no es maximizar AUC, sino obtener perfiles latentes estables,
  interpretables y asociados descriptivamente a adopcion QR.

Decision:

- Usar `id_tarjeta` como unidad.
- Usar NMF como metodo principal por interpretabilidad y no negatividad.
- Mantener QR/BIP fuera de la factorizacion.
- Cruzar perfiles con QR/BIP solo despues.

## 2026-06-03 — Arquitectura v1 acordada

Se acuerda partir con una matriz `macro_franja_modo`:

- `origin_macrozone`: macrozona de `zona_inicio_viaje`.
- `time_band`: franja laboral punta mañana, punta tarde, valle laboral y no
  laboral, siguiendo dummies V2 ya usadas en el proyecto.
- `mode_coarse`: `bus_only`, `metro_only`, `metro_bus`, `other_mode`, usando
  codigos corregidos del diccionario de viajes (`1/3` bus-like, `2/4`
  metro-like).

Razonamiento:

- Menor sparsity que matrices por `zona777`.
- Mas interpretable que una matriz OD detallada inicial.
- Alineada con NMF porque produce conteos/proporciones no negativas.
- Permite expandir luego a `od_macro`, `macro_franja`, `zona777_franja` o
  matrices de rutina si la v1 es saludable.

Normalizacion v1:

- Principal: `row-share`, suma 1 por tarjeta.
- Lectura: mezcla de patron de uso, no intensidad total.
- Intensidad (`n_viajes`) se conserva como metadata externa.

## 2026-06-03 — Validacion esperada de NMF

La seleccion de `k` no debe usar QR/BIP. Criterios:

- Error de reconstruccion y codo.
- Estabilidad entre semillas.
- Tamaños de segmentos.
- Entropia/concentracion de asignacion.
- Interpretabilidad de componentes por top features.
- Diferencias post-hoc en QR/BIP, solo despues de elegir/justificar `k`.

Lectura post-hoc:

- Tasa `QR vs BIP` por segmento.
- Tasa `QR_OTHER` y `QR_RED` por segmento.
- Lift vs tasa base.
- Chi-square/Cramer's V para asociacion segmento-target.
- Descriptivos externos: `n_viajes`, cohorte temporal, residencia/macrozonas y
  variables de ritmo/rutina cuando existan como metadata.

## 2026-06-03 — Relacion con ML y `prototype_pack`

Este frente queda desacoplado del benchmark ML. Los componentes NMF no entran
automaticamente a `build_user_model_matrix.py`.

Regla:

- Primero demostrar matriz sana + componentes estables + lectura interpretable.
- Luego, si aporta, exportar scores como `user_behavior_prototype_features_*`.
- Solo despues evaluar si esos scores se integran como `prototype_pack` en ML.

## 2026-06-03 — Caveats metodologicos

- `id_tarjeta` es proxy de usuario; una persona podria tener mas de una tarjeta.
- La segmentacion describe perfiles de movilidad, no causas de adopcion.
- NMF requiere inputs no negativos; no usar z-scores, residuales centrados ni
  variables con valores negativos.
- No usar QR/BIP dentro del input NMF.
- Un segmento pequeño solo es defendible si es estable e interpretable.
- Los resultados deben reportarse como asociaciones descriptivas.

## 2026-06-03 — Implementacion v1

Se implementa la primera arquitectura del frente:

- `scripts/audits/build_user_mobility_segmentation_matrix.py`
  - Construye matriz user-level `macro_franja_modo`.
  - Toma el universo desde `user_model_matrix_*` para heredar filtros
    `scope/variant/home_filter/min_trips`.
  - Construye patrones desde viajes procesados por semana.
  - Une macrozona de origen via lookup ZONA777.
  - Usa franja V2: `lab_am_peak`, `lab_pm_peak`, `lab_valle`, `no_lab`.
  - Usa modo corregido: `1/3` bus-like, `2/4` metro-like.
  - Guarda inventario de features para evitar leakage de target.

- `scripts/audits/run_user_nmf_segmentation.py`
  - Corre NMF para rango de `k`.
  - Repite semillas para medir estabilidad por ARI entre asignaciones.
  - Guarda metricas, top features por componente, asignaciones y scores.
  - Default `--fit-sample-size 300000`: ajusta en muestra y transforma todas
    las tarjetas para escalar al universo principal.

- `scripts/audits/summarize_user_nmf_segments.py`
  - Une asignaciones con metadata.
  - Produce tasa QR/BIP, QR_RED, QR_OTHER y lift por segmento.
  - Calcula asociacion segmento-target con chi-square y Cramer's V.
  - Resume distribuciones categoricas externas por segmento.

- `02_eda/eda_user_level_segmentation.qmd`
  - Notebook de lectura, no de entrenamiento pesado.
  - Imprime comandos reproducibles.
  - Lee auditorias, metricas NMF, top features y post-hoc si existen.

Verificacion realizada sin ejecutar datos reales:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m py_compile \
  scripts/audits/build_user_mobility_segmentation_matrix.py \
  scripts/audits/run_user_nmf_segmentation.py \
  scripts/audits/summarize_user_nmf_segments.py \
  lib/test_user_segmentation_nmf.py

/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python -m pytest \
  lib/test_user_segmentation_nmf.py lib/test_user_behavior_mode_mapping.py -q
```

Resultado: `13 passed`.

No se corrio el builder ni NMF sobre parquets reales en esta implementacion.

## 2026-06-03 — Resultado real builder `macro_franja_modo/share`

Comando corrido por usuario:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/build_user_mobility_segmentation_matrix.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --matrix-spec macro_franja_modo --normalization share --force
```

Resultado:

- Output:
  `tmp/audits/user_level_redesign/segmentation/user_mobility_matrix_interannual_ml_clean_alta_n3_macro_franja_modo_share.parquet`.
- Filas: 2.460.264 tarjetas.
- Features `seg_*`: 88.
- Duplicados `id_tarjeta`: 0.
- Tarjetas con masa cero: 0.
- Sparsity: 0,94204777.
- Row-sum min/max: 0,99999982 / 1,00000024.
- Features no-cero promedio por tarjeta: 5,0998.
- QR share: 0,15343679.

Lectura:

- La matriz v1 es saludable para NMF: universo completo, sin masa cero, shares
  normalizados y dimensionalidad moderada.
- Sparsity alta pero esperable para una matriz de patrones
  `macrozone x franja x modo`; 88 columnas es manejable.
- El top de masa esta dominado por patrones Metro/Bus en valle laboral de
  ORIENTE, CENTRO, PONIENTE y SURORIENTE.

Patch posterior:

- Se corrigio el warning de `DataFrame.pivot(columns=...)` usando `on=...`.
- Se limpio el prefijo de nombres futuros de features de `seg__oriente...` a
  `seg_oriente...`.
- La matriz ya construida sigue siendo usable; si se quiere eliminar warning y
  nombres antiguos, reconstruir con el mismo comando.

## 2026-06-03 — Resultado real NMF `k=2..8`

Comando corrido por usuario:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/run_user_nmf_segmentation.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --matrix-spec macro_franja_modo --normalization share \
  --k-range 2-8 --n-runs 10 --seed 20260527
```

Output:

`tmp/audits/user_level_redesign/segmentation/nmf/user_mobility_matrix_interannual_ml_clean_alta_n3_macro_franja_modo_share/`

Resumen de metricas:

- `fit_sample_n`: 300.000 tarjetas.
- `k=2`: recon 294,978; estabilidad ARI 0,846; segmentos 31,9% / 68,1%.
- `k=3`: recon 282,551; estabilidad ARI 0,565; segmento minimo 25,3%.
- `k=4`: recon 271,094; estabilidad ARI 0,653; segmento minimo 14,9%;
  segmento maximo 35,7%.
- `k=5`: recon 261,967; estabilidad ARI 0,673; segmento minimo 12,7%.
- `k=6`: recon 253,665; estabilidad ARI 0,652; segmento minimo 8,9%.
- `k=7`: recon 245,463; estabilidad ARI 0,664; segmento minimo 8,0%.
- `k=8`: recon 237,368; estabilidad ARI 0,660; segmento minimo 6,7%.

El `run_meta.json` reporta:

- `elbow_d2_k = 4`
- `elbow_segment_k = 4`
- `elbow_consensus_k = 4`

Lectura preliminar antes de mirar QR/BIP:

- `k=4` queda como candidato principal v1 por codo consenso, tamaños razonables
  e interpretabilidad inicial.
- `k=5` queda como sensibilidad natural: estabilidad levemente mejor y mejora
  reconstruccion, pero mayor complejidad.
- `k>=6` no se descarta, pero empieza a fragmentar segmentos y requiere mayor
  justificacion interpretativa.
- `k=3` es menos atractivo por estabilidad baja.

Top features `k=4` sugieren perfiles distinguibles:

- Poniente bus laboral/valle.
- Oriente bus/mixto.
- Oriente Metro.
- Centro/Poniente Metro.

Siguiente paso: correr post-hoc QR/BIP para todos los `k`, pero interpretar
primero `k=4` y usar `k=5` como sensibilidad.

## 2026-06-03 — Post-hoc QR/BIP de segmentos NMF

Comando corrido:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/summarize_user_nmf_segments.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --matrix-spec macro_franja_modo --normalization share --k all
```

Patch posterior:

- Se corrigio `pivot(columns=...)` a `pivot(on=...)`.
- Se corrigio `segment_qr_summary.csv` para usar una columna comun `segment`
  al concatenar multiples `k`, en vez de dejar `segment_k2`, `segment_k3`, etc.
- Verificacion: `lib/test_user_segmentation_nmf.py` queda en `13 passed`.

Lectura de asociacion post-hoc:

- La asociacion segmento-target existe, pero es moderada.
- Cramer's V para `tipo_tarjeta`:
  - `k=4`: 0,0337.
  - `k=5`: 0,0461.
  - `k=8`: 0,0504.
- Cramer's V para `is_qr`:
  - `k=4`: 0,0255.
  - `k=5`: 0,0344.
  - `k=8`: 0,0380.

Interpretacion:

- No conviene elegir `k` maximizando asociacion con QR, porque QR/BIP es
  target post-hoc y no debe guiar la factorizacion.
- `k=4` sigue siendo candidato principal v1 por el codo no supervisado
  (`elbow_consensus_k=4`), tamaños razonables e interpretabilidad.
- `k=5` queda como sensibilidad fuerte porque mejora la separacion descriptiva
  de QR/QR_RED con complejidad aun manejable.
- `k>=6` aumenta asociacion post-hoc, pero fragmenta mas; se debe usar solo si
  los componentes tienen una interpretacion substantiva clara.

Resumen `k=4`:

- Segmento 0: 367.732 tarjetas, 14,95% del universo, QR lift 0,935,
  QR_RED lift 0,541, QR_OTHER lift 0,999.
- Segmento 1: 675.024 tarjetas, 27,44%, QR lift 1,036, QR_RED lift 1,239,
  QR_OTHER lift 1,002.
- Segmento 2: 538.708 tarjetas, 21,90%, QR lift 1,086, QR_RED lift 1,382,
  QR_OTHER lift 1,037.
- Segmento 3: 878.800 tarjetas, 35,72%, QR lift 0,947, QR_RED lift 0,775,
  QR_OTHER lift 0,976.

Resumen `k=5`:

- Segmento 4 concentra la mayor señal QR: 312.405 tarjetas, 12,70% del universo,
  QR lift 1,158, QR_RED lift 1,744, QR_OTHER lift 1,062.
- Segmento 0 tambien tiene alta señal QR_RED: 423.729 tarjetas, 17,22%,
  QR lift 1,093, QR_RED lift 1,564.
- El resto de segmentos queda bajo o cerca de la tasa base QR.

Decision practica:

- Reportar `k=4` como especificacion principal no supervisada.
- Reportar `k=5` como sensibilidad interpretativa si los top features permiten
  nombrar claramente el segmento con lift QR_RED alto.
- Siguiente paso: construir etiquetas humanas para componentes/segmentos
  `k=4` y `k=5`, usando top features y perfiles externos.

## 2026-06-03 — Reencuadre del frente: de NMF unico a pipeline analitico

Se acuerda que el frente no debe seguir como una secuencia de scripts, sino
como un flujo analitico de segmentacion:

1. Exprimir la prueba NMF existente `macro_franja_modo/share`.
2. Armar catalogo de variables por rol analitico.
3. Auditar factibilidad de variables candidatas.
4. Construir una matriz `behavioral_wide`.
5. Usar PCA como diagnostico de ejes y redundancias.
6. Usar sparse k-means como selector/validador de variables conductuales fuertes.
7. Probar `structural_wide` solo como sensibilidad socio-territorial.
8. Comparar soluciones para decidir narrativa final.

Integracion con lo ya hecho:

- El NMF actual no se descarta. Queda como baseline interpretable de movilidad
  `macro-franja-modo`.
- `k=4` se mantiene como especificacion principal de ese baseline.
- `k=5` se mantiene como sensibilidad con mayor separacion QR/QR_RED.
- Las nuevas matrices no reemplazan automaticamente a NMF; deben demostrar que
  agregan interpretabilidad, estabilidad o una lectura substantiva mas clara.

Decisiones para el catalogo:

- Variables de uso, socio-demografia, geografia, oferta/acceso, rhythm, routine
  y daily_tour deben aparecer en el catalogo.
- No todas las variables entran al clustering principal.
- La matriz `behavioral_wide` debe separar conducta de estructura territorial.
- La matriz `structural_wide` puede incluir socio/geografia/oferta, pero se debe
  interpretar como perfil usuario-contexto, no como conducta pura.
- Sparse k-means y PCA se usaran como herramientas de diagnostico/seleccion, no
  como autoridad automatica para definir la segmentacion final.

## 2026-06-03 — Cierre provisional Fase 1: mini-validacion NMF

Esta lectura se documenta como **primera prueba / version baseline**, no como
resultado final de segmentacion.

Objeto probado:

- Matriz: `macro_franja_modo/share`.
- Unidad: `id_tarjeta`.
- Algoritmo: NMF.
- Universo: `interannual_ml + clean + home_filter=alta + min_trips=3`.
- Input: patron espacio-franja-modo; no incluye uso agregado, socio-demografia,
  oferta/acceso, rhythm, routine ni daily_tour como variables de clustering.

Decision de lectura:

- `k=4` queda como baseline de esta primera prueba.
- `k=5` queda como sensibilidad interpretable.
- No se elige `k` maximizando QR/BIP; QR/BIP se usa solo post-hoc.

Lectura sintetica `k=4`:

- Segmento 0: perfil Poniente Bus laboral/valle; QR y especialmente QR_RED por
  debajo de la base.
- Segmento 1: perfil Oriente/Suro Bus laboral/valle; QR levemente sobre base y
  QR_RED sobre base.
- Segmento 2: perfil Oriente Metro laboral; mayor QR y QR_RED dentro de `k=4`.
- Segmento 3: perfil Centro/Poniente Metro; QR y QR_RED bajo base.

Lectura sintetica `k=5`:

- Separa mejor el eje Oriente:
  - Oriente Metro.
  - Oriente Bus.
- Ambos perfiles Oriente tienen QR_RED alto, especialmente Oriente Bus.
- Esto sugiere que la señal QR_RED capturada por esta matriz no es puramente
  modal; combina geografia frecuente de uso y modo.

Conclusion provisional:

- La segmentacion espacio-franja-modo **si produce perfiles claros e
  interpretables**.
- La asociacion QR/BIP existe, pero es moderada; no debe venderse como
  predictor fuerte.
- `QR_RED` aparece mas asociado a perfiles Oriente Metro/Bus.
- `QR_OTHER` se mueve poco y sigue siendo mas dificil de distinguir de BIP con
  esta matriz.
- Siguiente paso analitico: pasar al catalogo de variables para decidir que
  bloques entran a `behavioral_wide` y cuales quedan como perfil externo o
  sensibilidad estructural.

## 2026-06-03 — Inicio catalogo: auditoria bloque intensidad

Se crea un notebook separado para no contaminar el EDA user-level principal ni
el notebook de lectura NMF:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo del notebook:

- Auditar bloques candidatos para segmentacion user-level.
- Empezar por intensidad / soporte de uso.
- Producir evidencia para decidir variables, no tomar decisiones automaticas.

Variables candidatas iniciales del bloque intensidad:

- `log1p(n_viajes)`: exposicion/intensidad total.
- `log1p(n_dias_activos)`: persistencia temporal.
- `log1p(n_semanas_activas)`: cobertura semanal.
- `rhythm_active_day_density_span`: densidad de dias activos dentro del span.
- `rhythm_trips_per_active_week`: frecuencia semanal condicional a actividad.
- `rhythm_trips_per_span_day`: intensidad distribuida por dia del span.

Auditorias incluidas:

- Concepto y caveat por variable.
- Missing, varianza y cuantiles por universo (`alta_n3`, `alta_n5`,
  `alta_n10`, `alta_n3_home3`).
- Correlacion interna en universo principal.
- PCA diagnostico del bloque.
- Prueba de representatividad de representantes candidatos:
  `log1p_n_viajes` y `rhythm_active_day_density_span`.
  - R2 de reconstruccion lineal de las seis variables estandarizadas del bloque.
  - Correlacion de los representantes con PC1 y PC2.
- QR/BIP post-hoc por cuantiles como contexto externo, no como criterio de
  seleccion.

Decisiones explicitamente pendientes:

- Representante de intensidad total.
- Representante de densidad/cotidianeidad.
- Si `rhythm_trips_per_active_week` agrega una dimension no redundante.

## 2026-06-03 — Cierre bloque intensidad del catalogo

Se crea el archivo:

- `docs/planning/workstreams/user-level-segmentation/variable_catalog.md`

Decision del bloque intensidad:

- `log1p_n_viajes` queda como `input_behavioral/main`.
  - Concepto: exposicion/intensidad total observada.
  - Evidencia: representa PC1 de volumen/soporte observado; correlacion con PC1
    = 0,94.
- `rhythm_active_day_density_span` queda como `input_behavioral/main`.
  - Concepto: densidad/cotidianeidad de actividad dentro del span observado.
  - Evidencia: representa PC2; correlacion con PC2 = 0,86.
- `log1p_n_dias_activos` queda como `posthoc_only/sensitivity`.
  - Razon: redundante con `log1p_n_viajes`; Spearman 0,968; R2 0,948 desde
    representantes.
- `log1p_n_semanas_activas` queda como `posthoc_only/sensitivity`.
  - Razon: cobertura semanal discreta, con solo 8 valores unicos; R2 0,882
    desde representantes.
- `rhythm_trips_per_span_day` queda como `input_behavioral/sensitivity`.
  - Razon: casi redundante con `rhythm_active_day_density_span`; Spearman 0,982.
- `rhythm_trips_per_active_week` queda como `input_behavioral/sensitivity`.
  - Razon: mezcla intensidad y densidad; R2 0,815 desde representantes.

Conclusion:

- El bloque intensidad queda representado parsimoniosamente por dos variables
  main.
- La seleccion no se basa en QR/BIP. QR/BIP queda como lectura post-hoc.
- Siguiente bloque sugerido: horario/franja y variabilidad horaria, porque es
  cercano al bloque de uso agregado y antes de entrar a rhythm/routine mas
  complejos.

## 2026-06-03 — Inicio bloque horario/franja del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Variables candidatas:

- `hora_mean`: hora promedio de inicio de viajes.
- `hora_std`: variabilidad horaria de los viajes.
- `share_lab_pm`: proporcion en punta laboral mañana.
- `share_lab_pt`: proporcion en punta laboral tarde.
- `share_lab_valle`: proporcion en valle laboral.
- `share_no_lab`: proporcion en periodo no laboral.

Caveats a revisar antes de decidir:

- Las cuatro variables de shares son composicionales y pueden ser redundantes
  entre si.
- `hora_mean` puede ser fragil si un usuario tiene patrones bimodales
  mañana/tarde; no representa bien circularidad horaria.
- `hora_std` puede mezclar dispersion real con bajo soporte de viajes.
- La seleccion debe basarse en estructura del bloque, calidad y no redundancia;
  QR/BIP se mantiene solo como lectura post-hoc.

Estado:

- Bloque horario/franja preparado para correr celdas de calidad, correlacion,
  PCA diagnostico y QR post-hoc.
- No hay decision de catalogo cerrada aun.

Prueba de reconstruccion agregada:

- Label: `time-representative-retention`.
- Representantes v1: `hora_mean`, `hora_std`, `share_lab_pm`,
  `share_no_lab`.
- Objetivo: medir R2 de reconstruccion de las seis variables del bloque y
  correlacion de los representantes con PC1-PC3.
- Razon: el PCA del bloque horario/franja requiere tres ejes para superar 80%
  de varianza acumulada, por lo que no basta revisar PC1-PC2.

Prueba de reconstruccion v2 agregada:

- Label: `time-representative-retention-v2`.
- Representantes v2: `hora_mean`, `hora_std`, `share_lab_pm`, `share_lab_pt`,
  `share_no_lab`.
- Hipotesis: agregar `share_lab_pt` podria corregir la baja reconstruccion de
  punta tarde observada en v1, dejando `share_lab_valle` como referencia
  composicional implicita.

## 2026-06-03 — Cierre bloque horario/franja del catalogo

Decision del bloque horario/franja:

- `hora_mean` queda como `input_behavioral/main`.
  - Concepto: centralidad horaria promedio.
  - Evidencia: representa PC2 del bloque; abs corr con PC2 = 0,823.
- `hora_std` queda como `input_behavioral/main`.
  - Concepto: dispersion/variabilidad horaria.
  - Evidencia: no es redundante con `hora_mean` (Spearman 0,022) y aporta al
    eje de puntas/dispersion.
- `share_lab_pm` queda como `input_behavioral/main`.
  - Concepto: punta laboral mañana.
  - Evidencia: mejor representante de PC1; abs corr con PC1 = 0,801.
- `share_lab_pt` queda como `input_behavioral/main`.
  - Concepto: punta laboral tarde.
  - Evidencia: en el set v1 quedaba mal reconstruida (R2 = 0,310); al agregarla
    el set v2 reconstruye todo el bloque.
- `share_no_lab` queda como `input_behavioral/main`.
  - Concepto: uso no laboral.
  - Evidencia: mejor representante de PC3; abs corr con PC3 = 0,829.
- `share_lab_valle` queda como `posthoc_only/sensitivity`.
  - Razon: es redundante por composicionalidad si entran `share_lab_pm`,
    `share_lab_pt` y `share_no_lab`; queda como categoria base implicita.

Conclusion:

- El bloque horario/franja queda representado por cinco variables principales.
- No se elige por QR/BIP; el post-hoc solo muestra que el bloque tiene señal
  descriptiva.
- Caveat pendiente: al construir `behavioral_wide`, escalar por bloque para que
  el conjunto de cinco variables de horario no domine sobre intensidad u otros
  bloques por cantidad de columnas.

## 2026-06-03 — Inicio bloque regularidad/ritmo temporal del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Evaluar variables de textura temporal que no sean solo intensidad total ni
  franja horaria.
- Separar tres subfamilias: gaps/intermitencia, concentracion diaria y
  concentracion semanal.

Variables candidatas:

- Gaps/intermitencia:
  - `rhythm_has_gap`
  - `rhythm_n_gap_days`
  - `rhythm_median_gap_active_days`
  - `rhythm_mean_gap_active_days`
  - `rhythm_max_gap_active_days`
- Concentracion diaria:
  - `rhythm_activity_top1_day_share`
  - `rhythm_activity_top2_day_share`
  - `rhythm_daily_hhi`
  - `rhythm_daily_entropy_norm`
  - `rhythm_daily_burstiness`
  - `rhythm_single_trip_day_share`
- Concentracion semanal:
  - `rhythm_weekly_top1_share`
  - `rhythm_weekly_hhi`
  - `rhythm_weekly_entropy_norm`
  - `rhythm_weekly_burstiness`

Decision de alcance:

- No repetir en este bloque variables ya clasificadas como intensidad/densidad:
  `rhythm_active_day_density_span`, `rhythm_trips_per_span_day` y
  `rhythm_trips_per_active_week`.
- Tampoco se decide por QR/BIP; el post-hoc queda como lectura externa.

Estado:

- Bloque preparado para correr calidad, correlacion, PCA diagnostico y QR
  post-hoc.
- No hay decision de catalogo cerrada aun.

Pruebas de reconstruccion agregadas:

- Label: `rhythm-regularity-representative-retention-v1`.
- Representantes v1: `rhythm_mean_gap_active_days`, `rhythm_daily_hhi`,
  `rhythm_single_trip_day_share`, `rhythm_weekly_hhi`.
- Label: `rhythm-regularity-representative-retention-v2`.
- Representantes v2: v1 + `rhythm_weekly_entropy_norm`.
- Objetivo: medir si un set parsimonioso reconstruye las 15 variables del
  bloque y cubre PC1-PC5 antes de decidir variables main.
- Labels adicionales:
  - `rhythm-regularity-representative-retention-v3a`: v2 +
    `rhythm_max_gap_active_days`.
  - `rhythm-regularity-representative-retention-v3b`: v2 +
    `rhythm_n_gap_days`.
- Objetivo adicional: evaluar si una variable de gap/extremo captura el PC3 que
  v1/v2 no cubren bien.

## 2026-06-03 — Cierre bloque regularidad/ritmo temporal del catalogo

Decision del bloque regularidad/ritmo:

- `rhythm_mean_gap_active_days` queda como `input_behavioral/main`.
  - Concepto: intermitencia promedio entre dias activos.
  - Evidencia: representa PC2 del bloque; abs corr con PC2 = 0,958.
  - Caveat: cola larga y 6,1% missing en `alta_n3`; al construir matriz final
    considerar `log1p`/imputacion explicita.
- `rhythm_daily_hhi` queda como `input_behavioral/main`.
  - Concepto: concentracion diaria de viajes.
  - Evidencia: mejor representante de PC1; abs corr con PC1 = 0,944.
- `rhythm_single_trip_day_share` queda como `input_behavioral/main`.
  - Concepto: proporcion de dias activos simples/de un viaje.
  - Evidencia: representa PC5; abs corr con PC5 = 0,822.
- `rhythm_weekly_hhi` queda como `input_behavioral/main`.
  - Concepto: concentracion semanal de viajes.
  - Evidencia: reconstruye bien top1 semanal y cubre concentracion semanal.
- `rhythm_weekly_entropy_norm` queda como `input_behavioral/main`.
  - Concepto: dispersion semanal normalizada.
  - Evidencia: v2 mejora R2 promedio del bloque de 0,811 a 0,886 y R2 mediano
    de 0,835 a 0,971 frente a v1.
- `rhythm_max_gap_active_days` queda como `input_behavioral/sensitivity`.
  - Razon: v3a mejora PC3 de 0,279 a 0,515, pero el maximo gap puede capturar
    extremos/salto interanual mas que regularidad cotidiana.
- `rhythm_n_gap_days` queda como `posthoc_only/diagnostic`.
  - Razon: v3b mejora reconstruccion levemente, pero esta muy contaminada por
    soporte/dias activos y correlaciona casi perfectamente con concentracion
    diaria.
- `rhythm_has_gap` queda fuera del input principal.
  - Razon: casi constante en universos con mayor soporte.

Conclusion:

- Para `behavioral_wide_main`, usar el set v2:
  `rhythm_mean_gap_active_days`, `rhythm_daily_hhi`,
  `rhythm_single_trip_day_share`, `rhythm_weekly_hhi`,
  `rhythm_weekly_entropy_norm`.
- No se fuerza captura total de PC3 porque los representantes de ese eje tienen
  caveats mas fuertes que su ganancia marginal.
- No se elige por QR/BIP; el post-hoc solo confirma que el bloque tiene señal
  descriptiva.

## 2026-06-03 — Inicio bloque modo/transbordo/complejidad modal del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Evaluar si variables agregadas de composicion modal y transbordo deben entrar
  al `behavioral_wide`.
- Mantener separada esta lectura de la matriz `macro_franja_modo`, porque si
  luego usamos scores NMF con modo incluido podria haber redundancia.

Variables candidatas:

- Composicion modal:
  - `share_trips_solo_bus`
  - `share_trips_solo_metro`
  - `share_trips_metro_bus`
- Transbordo:
  - `share_trips_with_transfer`
  - `n_trasbordos_mean`
- Complejidad OD/ruta:
  - `share_trips_in_multi_route_od`

Chequeos agregados:

- Calidad por universo.
- Chequeo de suma de shares modales (`solo_bus + solo_metro + metro_bus`).
- Correlacion interna.
- PCA diagnostico.
- QR/BIP post-hoc descriptivo.

Chequeo tecnico preliminar:

- En `alta_n3`, `share_trips_solo_bus + share_trips_solo_metro +
  share_trips_metro_bus = 1` para el 100% de las tarjetas.
- Implicacion: las tres shares modales son una composicion cerrada; si entran
  como input no deberian entrar las tres sin definir una categoria de referencia
  o transformacion composicional.
- El post-hoc QR/BIP salio vacio inicialmente porque `pd.qcut` falla en
  variables con muchos empates cuando `duplicates="drop"` reduce el numero de
  bins pero se entregan cinco labels fijos. Se ajusto el helper para usar
  codigos numericos y generar labels segun los bins efectivos.
- Se agregaron pruebas de reconstruccion:
  - `modal-complexity-representative-retention-v1`: `share_trips_solo_bus`,
    `share_trips_with_transfer`, `share_trips_in_multi_route_od`.
  - `modal-complexity-representative-retention-v2`: v1 +
    `share_trips_metro_bus`.

Decision de alcance:

- No incluir aun `service_route_entropy_norm` ni `coarse_route_entropy_norm`;
  esas variables parecen pertenecer a un bloque posterior de diversidad de
  rutas/servicios, no al primer bloque modal/transbordo.
- No cerrar decision hasta leer outputs. Posibles resultados esperados:
  - dejar una o dos variables como `input_behavioral/main`;
  - dejar el bloque completo como sensibilidad si queda redundante con NMF;
  - dejar `share_trips_in_multi_route_od` solo como post-hoc si su definicion
    resulta mas estructural/oferta que conductual.

## 2026-06-03 — Cierre bloque modo/transbordo/complejidad modal del catalogo

Decision del bloque modo/transbordo:

- `share_trips_solo_bus` queda como `input_behavioral/main`.
  - Concepto: eje bus vs metro, dejando metro como referencia implicita.
  - Evidencia: las tres shares modales son composicion cerrada; usar
    `solo_bus` + `metro_bus` evita meter tres variables redundantes.
- `share_trips_metro_bus` queda como `input_behavioral/main`.
  - Concepto: intermodalidad especifica metro-bus.
  - Evidencia: set v1 reconstruye mal esta variable (R2 = 0,332); v2 la agrega
    y sube R2 promedio del bloque a 0,974.
- `share_trips_with_transfer` queda como `input_behavioral/main`.
  - Concepto: transbordo general.
  - Evidencia: representa PC1/transbordo; `n_trasbordos_mean` es casi
    redundante (Spearman 0,960) y queda reconstruido con R2 = 0,846 desde v2.
- `share_trips_in_multi_route_od` queda como `input_behavioral/main` con caveat
  fuerte.
  - Concepto: complejidad OD/ruta.
  - Evidencia: aporta eje propio; mejor representante de PC3 con abs corr =
    0,610.
  - Caveat: puede capturar red/oferta/soporte observado mas que conducta pura.
- `share_trips_solo_metro` queda como `posthoc_only/sensitivity`.
  - Razon: queda implicita por composicion si entran `solo_bus` y `metro_bus`.
- `n_trasbordos_mean` queda como `posthoc_only/sensitivity`.
  - Razon: redundante con `share_trips_with_transfer`, pero util para describir
    intensidad de transfer.

Conclusion:

- Para `behavioral_wide_main`, usar el set v2:
  `share_trips_solo_bus`, `share_trips_metro_bus`,
  `share_trips_with_transfer`, `share_trips_in_multi_route_od`.
- Mantener caveat de redundancia con matriz/scores `macro_franja_modo`: si esa
  representacion entra al mismo clustering, este bloque debe ponderarse o
  moverse a sensibilidad.
- No se elige por QR/BIP; el post-hoc solo queda como lectura descriptiva.

## 2026-06-03 — Inicio bloque espacial/OD/zonas del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Evaluar variables de concentracion/diversidad espacial observada sin mezclar
  geografia residencial, coordenadas ni oferta/acceso.
- Separar subfamilias: origen/actividad zonal, diversidad zonal, diversidad OD
  y OD principal/reciprocidad.

Variables candidatas:

- Origen/actividad zonal:
  - `origin_zone_top1_share`
  - `origin_zone_entropy`
  - `activity_zone_top1_share`
  - `activity_zone_entropy`
- Diversidad/concentracion zonal:
  - `routine_zone_n_unique`
  - `routine_zone_top1_usage_share`
  - `routine_zone_exploration_share`
- OD dirigido:
  - `routine_od_top1_share`
  - `routine_od_hhi`
- OD principal no dirigido:
  - `routine_main_od_share`
  - `routine_main_od_roundtrip_balance`

Exclusiones deliberadas:

- `home_macro_*`, `origin_top1_macro_*`, `origin_top1_lon/lat`: sensibilidad
  estructural/geografica.
- `offer_*`, `osm_*`, `bip_load_*`: oferta/acceso.
- `service_route_*`, `top_od_service_*`: bloque posterior de diversidad de
  rutas/servicios.
- `routine_od_entropy_norm` y `routine_od_n_unique` no estan disponibles en la
  matriz `user_model_matrix_interannual_ml_clean_alta_n3.parquet` actual; no se
  reemplazan por `routine_od_time_*` para no mezclar OD puro con franja temporal.

Estado:

- Bloque preparado para correr calidad, correlacion, PCA diagnostico y QR/BIP
  post-hoc.
- No hay decision de catalogo cerrada aun.
- Se agregaron pruebas de reconstruccion:
  - `spatial-od-zone-representative-retention-v1`: `activity_zone_entropy`,
    `routine_od_hhi`, `routine_main_od_roundtrip_balance`,
    `origin_zone_top1_share`.
  - `spatial-od-zone-representative-retention-v2`: v1 +
    `routine_main_od_share`.

## 2026-06-03 — Cierre bloque espacial/OD/zonas del catalogo

Decision del bloque espacial/OD/zonas:

- `activity_zone_entropy` queda como `input_behavioral/main`.
  - Concepto: diversidad espacial general considerando origenes y destinos.
  - Evidencia: mejor representante de PC1; abs corr con PC1 = 0,948.
- `routine_od_hhi` queda como `input_behavioral/main`.
  - Concepto: concentracion en pares OD dirigidos.
  - Evidencia: representa concentracion OD; `routine_od_top1_share` es
    redundante y queda reconstruido con R2 = 0,931 en v2.
- `routine_main_od_share` queda como `input_behavioral/main`.
  - Concepto: peso del OD principal no dirigido.
  - Evidencia: v2 mejora R2 promedio de 0,873 a 0,904 y cubre mejor PC4
    (0,167 -> 0,402).
- `routine_main_od_roundtrip_balance` queda como `input_behavioral/main`.
  - Concepto: reciprocidad ida/vuelta del OD principal.
  - Evidencia: representa PC2; abs corr con PC2 = 0,806.
- `origin_zone_top1_share` queda como `input_behavioral/main`.
  - Concepto: anclaje/concentracion de zona de origen.
  - Evidencia: captura ejes residuales PC3/PC5 no cubiertos por diversidad
    general.
- `routine_zone_top1_usage_share` queda como `exclude/drop`.
  - Razon: duplicada exacta de `activity_zone_top1_share`.
- `activity_zone_top1_share`, `origin_zone_entropy`,
  `routine_zone_exploration_share`, `routine_zone_n_unique` y
  `routine_od_top1_share` quedan como posthoc/sensibilidad.

Conclusion:

- Para `behavioral_wide_main`, usar el set v2:
  `activity_zone_entropy`, `routine_od_hhi`, `routine_main_od_share`,
  `routine_main_od_roundtrip_balance`, `origin_zone_top1_share`.
- Caveat: el bloque tiene un PC1 dominante de diversidad/anclaje espacial; debe
  escalarse o ponderarse por bloque para no dominar el clustering final.
- No se elige por QR/BIP; el post-hoc solo confirma que el eje espacial tiene
  lectura descriptiva.

## 2026-06-03 — Inicio bloque rutina/repeticion de patrones del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Evaluar repeticion de patrones combinados, no solo concentracion espacial.
- Separar la rutina de OD/franja/modo del bloque espacial/OD/zonas ya cerrado.
- Mantener abierto si este bloque entra como input principal, sensibilidad o
  solo post-hoc, porque puede solaparse con bloques de modo, horario y OD.

Variables candidatas:

- Patron OD + franja + modo:
  - `routine_combo_top1_share`
  - `routine_combo_hhi`
- Patron OD + franja:
  - `routine_od_time_top1_share`
  - `routine_od_time_hhi`
  - `routine_od_time_entropy_norm`
  - `routine_od_time_n_unique`
- Anclaje laboral / commute-like:
  - `routine_lab_peak_share`
  - `routine_commute_like_score`

Exclusiones deliberadas:

- `routine_od_hhi`, `routine_main_od_share`,
  `routine_main_od_roundtrip_balance`, `routine_zone_*`: ya auditadas en el
  bloque espacial/OD/zonas.
- `routine_combo_entropy_norm`, `routine_combo_n_unique`,
  `routine_od_entropy_norm`, `routine_od_n_unique`: no estan disponibles en la
  matriz `user_model_matrix_*` actual.

Estado:

- Bloque preparado para correr calidad, correlacion, PCA diagnostico y QR/BIP
  post-hoc.
- Se agregaron pruebas de reconstruccion:
  - `routine-pattern-representative-retention-v1`: `routine_od_time_hhi`,
    `routine_lab_peak_share`, `routine_od_time_entropy_norm`.
  - `routine-pattern-representative-retention-v2`: v1 +
    `routine_commute_like_score`.
- Aun no hay decision de catalogo cerrada.
- Posible caveat principal: si entran variables de horario, modo y OD por
  separado, este bloque puede duplicar estructura ya incorporada.

## 2026-06-03 — Cierre bloque rutina/repeticion de patrones del catalogo

Decision del bloque rutina/repeticion:

- `routine_od_time_hhi` queda como `input_behavioral/main`.
  - Concepto: concentracion de patrones OD + franja.
  - Evidencia: mejor representante de PC1; abs corr con PC1 = 0,949.
  - Razon adicional: evita reintroducir modo, que ya tiene bloque propio.
- `routine_lab_peak_share` queda como `input_behavioral/main` con caveat
  cross-block.
  - Concepto: anclaje laboral/punta.
  - Evidencia: mejor representante de PC2; abs corr con PC2 = 0,742.
  - Caveat: puede duplicar variables de franja horaria.
- `routine_od_time_entropy_norm` queda como `input_behavioral/main`.
  - Concepto: dispersion normalizada de patrones OD + franja.
  - Evidencia: captura parte de PC3; abs corr con PC3 = 0,513.
- `routine_commute_like_score` queda como `posthoc_only/sensitivity`.
  - Razon: v2 mejora R2 promedio de 0,840 a 0,919, pero principalmente porque
    el score compuesto se reconstruye a si mismo.
  - Caveat: es un indice construido manualmente y demasiado prescriptivo para
    input main inicial.
- `routine_od_time_n_unique` queda como `posthoc_only/sensitivity`.
  - Razon: es el residual peor reconstruido (R2 = 0,576), pero depende mucho de
    soporte/intensidad.
- `routine_combo_top1_share` y `routine_combo_hhi` quedan como `exclude/drop`
  para el input principal.
  - Razon: duplican casi exactamente sus equivalentes OD-franja
    (`top1`: Spearman 0,995; `hhi`: Spearman 0,998) y ademas reintroducen modo.

Conclusion:

- Para `behavioral_wide_main` provisional, usar:
  `routine_od_time_hhi`, `routine_lab_peak_share`,
  `routine_od_time_entropy_norm`.
- Sensibilidad/post-hoc: agregar o perfilar con `routine_commute_like_score`.
- Caveat transversal: antes de construir `behavioral_wide`, revisar redundancia
  cross-block con horario, modo y espacial/OD. Si duplica demasiado, este bloque
  podria bajar a sensibilidad.
- No se elige por QR/BIP; el post-hoc solo queda como lectura descriptiva.

## 2026-06-03 — Inicio bloque daily tour/estructura diaria del catalogo

Se agrega al notebook de auditoria el bloque:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Evaluar como se organizan los viajes dentro del dia activo: simpleza,
  complejidad, cierre/pendularidad, anclaje horario diario y diversidad diaria.
- Separar estructura diaria de rutina/repeticion: daily-tour pregunta por la
  forma del dia, no por repetir el mismo patron OD-franja.

Decision tecnica:

- El `user_model_matrix_*` actual solo trae 8 variables `tour_*`.
- El artefacto `user_behavior_daily_tour_features_interannual_ml.parquet`
  contiene 21 variables `tour_*`.
- Para el catalogo se audita el artefacto completo y se filtra por los mismos
  universos (`alta_n3`, `alta_n5`, `alta_n10`, `alta_n3_home3`) usando
  `id_tarjeta`.

Variables candidatas:

- Complejidad diaria:
  - `tour_two_trip_day_share`
  - `tour_three_plus_trip_day_share`
  - `tour_complex_day_share`
- Cierre/pendularidad:
  - `tour_closed_loop_day_share`
  - `tour_reciprocal_od_day_share`
  - `tour_same_unordered_od_day_share`
  - `tour_workday_commute_like_day_share`
- Modalidad diaria:
  - `tour_mode_consistent_day_share`
  - `tour_mixed_mode_day_share`
  - `tour_distinct_modes_per_day_mean`
- Anclaje horario diario:
  - `tour_first_trip_lab_am_peak_share`
  - `tour_last_trip_lab_pm_peak_share`
  - `tour_peak_anchor_day_share`
  - `tour_day_span_hours_mean`
  - `tour_day_span_hours_median`
  - `tour_first_trip_hour_mean`
  - `tour_last_trip_hour_mean`
- Diversidad diaria:
  - `tour_distinct_zones_per_day_mean`
  - `tour_distinct_zones_per_day_median`
  - `tour_distinct_od_per_day_mean`
  - `tour_distinct_unordered_od_per_day_mean`

Estado:

- Bloque preparado para correr calidad, correlacion, PCA diagnostico y QR/BIP
  post-hoc.
- Se agregaron pruebas de reconstruccion:
  - `daily-tour-representative-retention-v1`: `tour_three_plus_trip_day_share`,
    `tour_reciprocal_od_day_share`, `tour_closed_loop_day_share`,
    `tour_mixed_mode_day_share`, `tour_day_span_hours_mean`.
  - `daily-tour-representative-retention-v2`: v1 +
    `tour_first_trip_lab_am_peak_share`,
    `tour_last_trip_lab_pm_peak_share`.
- Aun no hay decision de catalogo cerrada.
- Caveat principal: este bloque probablemente tendra redundancia cross-block
  con horario, modo, espacial/OD, intensidad y rutina.

## 2026-06-03 — Cierre bloque daily tour/estructura diaria del catalogo

Decision del bloque daily-tour:

- `tour_three_plus_trip_day_share` queda como `input_behavioral/main`.
  - Concepto: complejidad diaria por dias con tres o mas viajes.
  - Evidencia: mejor representante de PC1 en v2; abs corr con PC1 = 0,807.
  - Caveat: puede solaparse con intensidad y con
    `rhythm_single_trip_day_share`.
- `tour_reciprocal_od_day_share` queda como `input_behavioral/main`.
  - Concepto: pendularidad/reciprocidad OD dentro del dia.
  - Evidencia: retiene muy bien `tour_same_unordered_od_day_share`
    (R2 = 0,978 en v2).
  - Caveat: se parece conceptualmente a variables espaciales/OD de OD principal.
- `tour_closed_loop_day_share` queda como `input_behavioral/main`.
  - Concepto: dias que cierran ciclo o vuelven al origen inicial.
  - Evidencia: captura PC3 mejor que las otras variables estructurales
    seleccionadas; abs corr con PC3 = 0,634.
  - Caveat: puede solaparse parcialmente con pendularidad OD.
- `tour_mixed_mode_day_share` queda como `input_behavioral/main` con caveat
  cross-block.
  - Concepto: mezcla modal dentro del dia activo.
  - Evidencia: captura PC4; abs corr con PC4 = 0,521.
  - Caveat: duplica informacion del bloque modal; si domina la redundancia,
    puede bajar a sensibilidad.
- `tour_day_span_hours_mean` queda como `input_behavioral/main`.
  - Concepto: extension temporal del dia activo.
  - Evidencia: mejor representante de PC2; abs corr con PC2 = 0,923.
  - Caveat: puede solaparse con variables de horario, pero resume amplitud
    diaria mas que hora puntual.
- `tour_first_trip_lab_am_peak_share` queda como `input_behavioral/main` con
  caveat cross-block.
  - Concepto: anclaje de primer viaje en punta AM laboral.
  - Evidencia: al agregar anclajes laborales en v2, `tour_peak_anchor_day_share`
    sube a R2 = 0,855 y `tour_first_trip_hour_mean` a R2 = 0,659.
  - Caveat: puede duplicar el bloque horario/franja.
- `tour_last_trip_lab_pm_peak_share` queda como `input_behavioral/main` con
  caveat cross-block.
  - Concepto: anclaje de ultimo viaje en punta PM laboral.
  - Evidencia: mejora la captura de PC5 (abs corr = 0,550) y
    `tour_last_trip_hour_mean` sube a R2 = 0,640.
  - Caveat: puede duplicar el bloque horario/franja.

Variables no main:

- `tour_workday_commute_like_day_share` queda como `posthoc_only/sensitivity`.
  - Razon: es un score compuesto que combina cierre, reciprocidad y anclaje
    laboral. v2 lo reconstruye razonablemente (R2 = 0,635), pero usarlo como
    input main seria mas prescriptivo.
- `tour_complex_day_share` queda como `posthoc_only/sensitivity`.
  - Razon: casi replica `tour_three_plus_trip_day_share` (Spearman 0,987;
    R2 = 0,977 en v2).
- `tour_same_unordered_od_day_share` queda como `posthoc_only/sensitivity`.
  - Razon: casi replica `tour_reciprocal_od_day_share` (Spearman 0,988;
    R2 = 0,978 en v2).
- `tour_mode_consistent_day_share` queda como `exclude/drop` para el input
  principal.
  - Razon: es deterministico frente a `tour_mixed_mode_day_share`
    (Spearman = -1).
- `tour_distinct_modes_per_day_mean` queda como `posthoc_only/sensitivity`.
  - Razon: casi se reconstruye desde `tour_mixed_mode_day_share`
    (R2 = 0,903 en v2).
- `tour_peak_anchor_day_share`, `tour_day_span_hours_median`,
  `tour_first_trip_hour_mean` y `tour_last_trip_hour_mean` quedan como
  `posthoc_only/sensitivity`.
  - Razon: aportan lectura horaria descriptiva, pero duplican parcialmente los
    anclajes laborales y la amplitud diaria.
- `tour_distinct_zones_per_day_mean`,
  `tour_distinct_zones_per_day_median`,
  `tour_distinct_od_per_day_mean` y
  `tour_distinct_unordered_od_per_day_mean` quedan como
  `posthoc_only/sensitivity`.
  - Razon: son utiles para diversidad diaria descriptiva, pero solapan con el
    bloque espacial/OD y algunas quedan peor reconstruidas
    (`tour_distinct_zones_per_day_median` R2 = 0,562 en v2).
- `tour_two_trip_day_share` queda como `exclude/drop`.
  - Razon: es el complemento conductual de complejidad diaria y queda
    moderadamente reconstruido por el set main (R2 = 0,733 en v2).

Conclusion:

- Para `behavioral_wide_main` provisional, usar:
  `tour_three_plus_trip_day_share`, `tour_reciprocal_od_day_share`,
  `tour_closed_loop_day_share`, `tour_mixed_mode_day_share`,
  `tour_day_span_hours_mean`, `tour_first_trip_lab_am_peak_share`,
  `tour_last_trip_lab_pm_peak_share`.
- Se elige v2 sobre v1 porque mejora R2 promedio 0,730 -> 0,864 y sube el peor
  R2 0,264 -> 0,562, principalmente recuperando anclaje horario diario.
- Caveat transversal: antes de armar `behavioral_wide`, revisar redundancia
  cross-block. En particular, `tour_mixed_mode_day_share` puede duplicar modo,
  `tour_first_trip_lab_am_peak_share` y `tour_last_trip_lab_pm_peak_share`
  pueden duplicar horario, y las variables OD/pendulares pueden duplicar el
  bloque espacial/OD. Si el bloque pesa demasiado, esas variables deben pasar a
  sensibilidad.
- No se elige por QR/BIP; el post-hoc queda solo como lectura descriptiva.

## 2026-06-04 — Inicio ensamble behavioral_wide v0

Se agrega al notebook de auditoria una seccion de ensamble conductual:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Juntar todas las variables marcadas como `input_behavioral/main` en el
  catalogo.
- Revisar calidad conjunta por universo.
- Revisar correlaciones altas entre bloques.
- Correr PCA diagnostico global.
- Focalizar los caveats cross-block antes de persistir una matriz final.

Decision tecnica:

- `log1p_n_viajes` se deriva desde `n_viajes` dentro del notebook.
- `log1p_rhythm_mean_gap_active_days` se deriva desde
  `rhythm_mean_gap_active_days` dentro del notebook, respetando la decision del
  catalogo de usar transformacion `log1p` por cola larga.
- Las variables `tour_*` del set main se cargan desde
  `user_behavior_daily_tour_features_interannual_ml.parquet`, aunque algunas
  existan en `user_model_matrix_*`, para mantener consistencia con el bloque
  daily-tour completo.
- El ensamble mantiene por ahora las 31 variables main provisionales.

Salidas agregadas:

- `behavioral-wide-main-inventory`
- `behavioral-wide-quality-by-universe`
- `behavioral-wide-correlation-main`
- `behavioral-wide-high-correlation-pairs`
- `behavioral-wide-pca-diagnostic`
- `behavioral-wide-pca-loading-summary`
- `behavioral-wide-caveat-pair-check`
- `behavioral-wide-decision-template`

Estado:

- Seccion preparada para ejecucion.
- Falta leer resultados y decidir si se cierra `behavioral_wide_v0` o si se
  crea una version reducida `v0b` bajando variables con redundancia cross-block
  a sensibilidad.

## 2026-06-04 — Lectura calidad behavioral_wide v0

Resultado de `behavioral-wide-quality-by-universe`:

- Ensamble con 31 variables main y 4 universos (`alta_n3`, `alta_n5`,
  `alta_n10`, `alta_n3_home3`).
- No hay variables con desviacion estandar cero.
- No hay variables con cardinalidad degenerada (`n_unique <= 2`).
- `daily_tour`, `horario` e `intensidad` no presentan missing.
- Missing microscopico en variables OD/modal/rutina (`~1e-6`) no representa
  problema operativo.
- El unico missing relevante es
  `log1p_rhythm_mean_gap_active_days`:
  - `alta_n3`: 6,06%.
  - `alta_n5`: 0,32%.
  - `alta_n10`: ~0%.
  - `alta_n3_home3`: 0%.

Decision:

- La calidad de `behavioral_wide v0` pasa para continuar con correlaciones
  cross-block y PCA global.
- Para `log1p_rhythm_mean_gap_active_days`, mantener imputacion explicita en
  diagnosticos/modelado porque el missing corresponde conceptualmente a tarjetas
  sin gaps suficientes entre dias activos.
- No bajar variables por calidad estadistica en esta etapa; las bajas deben
  venir de redundancia cross-block o dominancia en PCA, no de missing/varianza.

## 2026-06-04 — Prueba behavioral_wide v0b preparada

Se agrega una seccion `behavioral_wide v0b` al notebook de auditoria:

- `02_eda/eda_user_level_segmentation_block_audit.qmd`

Objetivo:

- Mantener `behavioral_wide v0` como benchmark completo.
- Probar una version reducida que baja a sensibilidad cinco variables con
  redundancia cross-block clara.
- Repetir los mismos diagnosticos de `v0`: calidad, correlacion, pares de alta
  correlacion, PCA, loadings, caveats focalizados y comparacion directa.

Variables bajadas a sensibilidad en `v0b`:

- `log1p_rhythm_mean_gap_active_days`: casi redundante con
  `rhythm_active_day_density_span`.
- `tour_first_trip_lab_am_peak_share`: redundante con `share_lab_pm` y con
  lectura de rutina peak.
- `rhythm_daily_hhi`: redundante con soporte/intensidad (`log1p_n_viajes`).
- `routine_od_hhi`: redundante con `routine_od_time_hhi`.
- `tour_reciprocal_od_day_share`: redundante con
  `routine_main_od_roundtrip_balance`.

Salidas nuevas:

- `behavioral-wide-v0b-main-inventory`
- `behavioral-wide-v0b-quality-by-universe`
- `behavioral-wide-v0b-correlation-main`
- `behavioral-wide-v0b-high-correlation-pairs`
- `behavioral-wide-v0b-pca-diagnostic`
- `behavioral-wide-v0b-pca-loading-summary`
- `behavioral-wide-v0b-caveat-pair-check`
- `behavioral-wide-v0-v0b-comparison`

Estado:

- La seccion esta preparada para ejecucion.
- Decision pendiente: usar `v0b` como candidato principal solo si reduce pares
  cross-block altos y mantiene ejes sustantivos interpretables frente a `v0`.

## 2026-06-04 — Resultado render behavioral_wide v0b

Comando ejecutado:

- `/usr/bin/env QUARTO_PYTHON=/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python quarto render 02_eda/eda_user_level_segmentation_block_audit.qmd`

Render:

- Completo, 84/84 celdas ejecutadas.
- Output: `02_eda/eda_user_level_segmentation_block_audit.html`.
- Se ajustaron los saves `to_csv`/`to_html` de `behavioral_wide` para pasar
  rutas como `str(...)`; evita un `InterruptedError` intermitente de pandas al
  manejar objetos `Path`.

Comparacion `v0` vs `v0b`:

- Variables: 31 -> 26.
- PCs necesarios para 80% de varianza: 9 -> 9.
- PC1 explained variance: 0,193 -> 0,186.
- Varianza acumulada PC1-PC4: 0,571 -> 0,552.
- Pares con `abs(corr) >= 0,75`: 10 -> 2.
- Pares cross-block con `abs(corr) >= 0,75`: 7 -> 1.

Pares altos restantes en `v0b`:

- Cross-block: `log1p_n_viajes` vs `rhythm_weekly_hhi`, Spearman = -0,831.
- Mismo bloque: `activity_zone_entropy` vs `routine_main_od_share`,
  Spearman = -0,806.

Lectura:

- `v0b` logra el objetivo operativo: reduce fuertemente redundancia cross-block
  sin colapsar la estructura PCA.
- Aun falta lectura sustantiva de los loadings `v0b`, pero la evidencia
  cuantitativa favorece usar `v0b` como candidato principal para clustering y
  mantener `v0` como sensibilidad completa.

## 2026-06-04 — Matriz v0b materializada y primera corrida PCA/sparse

Decision operativa:

- Usar script para PCA, KMeans y sparse k-means.
- Mantener notebook solo para auditoria/lectura y para consumir resultados.
- Razon: sparse k-means requiere grillas, seeds, asignaciones y multiples
  artefactos; meterlo en el QMD de auditoria haria cada render caro y fragil.

Builder creado:

- `scripts/audits/build_user_behavioral_segmentation_matrix.py`

Comando builder:

- `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_behavioral_segmentation_matrix.py --universe alta_n3 --spec v0b --force`

Output matriz:

- `tmp/audits/user_level_redesign/segmentation/features/behavioral_wide/v0b_alta_n3.parquet`
- Filas: 2.460.264.
- Features: 26.
- Columnas totales: 35, incluyendo metadata/targets post-hoc.
- Features con null despues de imputacion: 0.
- Imputacion usada: mediana por feature. En `v0b`, solo afecto missing
  microscopicos de variables OD/rutina/modal (`~1e-6`).
- Inventario:
  `tmp/audits/user_level_redesign/segmentation/behavioral_wide_feature_matrix_inventory.csv`

PCA + KMeans sobre PCs:

- Comando:
  `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/run_segmentation_pca.py --variant-id behavioral_wide --branch-id v0b_alta_n3 --input-dir tmp/audits/user_level_redesign/segmentation/features --inventory-path tmp/audits/user_level_redesign/segmentation/behavioral_wide_feature_matrix_inventory.csv --out-dir tmp/audits/user_level_redesign/segmentation/models --sample-size 300000 --plot-sample 50000 --silhouette-sample 50000 --with-kmeans --k-min 2 --k-max 8 --feature-tag pca_v0b --random-seed 20260527`
- Output:
  `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__pca_v0b/pca`
- PCA: 9 componentes para 80,8% de varianza acumulada.
- KMeans sobre PCs:
  - `k=2`: silhouette 0,153; min cluster share 43,6%.
  - `k=3`: silhouette 0,174; min cluster share 15,0%.
  - `k=4`: silhouette 0,155; min cluster share 14,6%.
  - `k=5`: silhouette 0,154; min cluster share 13,9%.
  - Codo consenso: `k=4`.

Lectura PCA+KMeans:

- `k=3` es el mejor por silhouette.
- `k=4` es defendible por codo y por continuidad con la narrativa previa NMF
  `k=4`.
- Proxima lectura debe perfilar `k=3` y `k=4` contra medias de features,
  tamanos y QR/BIP post-hoc, sin elegir aun por QR.

Sparse k-means primera pasada:

- Corridas para `k=2`, `k=3` y `k=4`.
- Sample size: 100.000.
- `s_grid`: 1,2 a 5,0.
- `n_perm=0`; no se uso gap permutation todavia.
- Outputs:
  - `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__sparse_v0b_k2/sparse_kmeans`
  - `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__sparse_v0b_k3/sparse_kmeans`
  - `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__sparse_v0b_k4/sparse_kmeans`

Lectura sparse inicial:

- Las soluciones muy sparse no mejoran la separacion.
- Las mejores silhouettes aparecen con `s` altos, donde el modelo deja de ser
  realmente sparse:
  - `k=3, s=5,0`: silhouette 0,116 con 26/26 variables activas.
  - `k=2, s=4,5`: silhouette 0,114 con 25/26 variables activas.
  - `k=4, s=4,0/5,0`: silhouette 0,097 con 26/26 variables activas.
- Como solucion de clustering, sparse k-means no supera PCA+KMeans en esta
  primera pasada.
- Como selector diagnostico, las variables fuertes en puntos intermedios
  (`s=2,5`/`s=3,0`) son principalmente:
  `rhythm_weekly_entropy_norm`, `rhythm_weekly_hhi`, `log1p_n_viajes`,
  `routine_od_time_entropy_norm`, `rhythm_active_day_density_span`,
  `activity_zone_entropy`, `routine_od_time_hhi`, `routine_main_od_share` y,
  segun `k`, `tour_three_plus_trip_day_share` / `tour_day_span_hours_mean`.

Decision provisional:

- Usar PCA+KMeans sobre `v0b` como rama principal de clustering conductual.
- Mantener sparse k-means como selector/validador de variables fuertes.
- Siguiente paso: construir resumen interpretativo de soluciones `k=3` y `k=4`
  de PCA+KMeans, y luego decidir si correr sparse con permutaciones solo sobre
  un `k`/rango `s` seleccionado.

## 2026-06-04 — Comparacion sparse k-means v0 vs v0b

Pregunta:

- Que pasa si corremos sparse k-means sobre `v0` completo y lo comparamos con
  `v0b` reducido.

Comandos:

- Se materializo `v0_alta_n3`:
  `/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python scripts/audits/build_user_behavioral_segmentation_matrix.py --universe alta_n3 --spec v0 --force`
- Se corrio sparse k-means para `v0`, `k=2/3/4`, misma muestra, semilla y
  `s_grid` que `v0b`.

Outputs:

- `tmp/audits/user_level_redesign/segmentation/features/behavioral_wide/v0_alta_n3.parquet`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0_alta_n3__sparse_v0_k2/sparse_kmeans`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0_alta_n3__sparse_v0_k3/sparse_kmeans`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0_alta_n3__sparse_v0_k4/sparse_kmeans`
- Comparacion agregada:
  `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/sparse_v0_vs_v0b_comparison`

Mejores resultados por `k`:

- `k=2`: `v0b` gana levemente.
  - `v0`: best silhouette 0,112 con 30/31 variables activas.
  - `v0b`: best silhouette 0,114 con 25/26 variables activas.
- `k=3`: `v0` gana muy levemente si se permite modelo denso.
  - `v0`: best silhouette 0,120 con 31/31 variables activas.
  - `v0b`: best silhouette 0,116 con 26/26 variables activas.
- `k=4`: `v0` gana numericamente si se permite modelo denso.
  - `v0`: best silhouette 0,106 con 31/31 variables activas.
  - `v0b`: best silhouette 0,097 con 26/26 variables activas.

Lectura en puntos intermedios (`s=2,5`/`s=3,0`):

- La diferencia no favorece claramente a `v0`.
- `v0` usa mas variables o reintroduce proxies redundantes para obtener mejoras
  pequenas.
- En `k=4, s=2,0`, `v0` mejora silhouette pero deja un cluster minimo de 6,1%,
  senal de posible solucion mas nicho/inestable.

Pesos de variables que `v0b` habia bajado:

- `k=2, s=2,5`: `tour_first_trip_lab_am_peak_share` queda como mayor peso
  (`0,619`) junto a `share_lab_pm`; suma de variables bajadas = 0,675.
- `k=3, s=2,5`: `rhythm_daily_hhi` entra fuerte (`0,374`) junto a
  `log1p_n_viajes` y regularidad semanal; suma de variables bajadas = 0,409.
- `k=4, s=2,5`: `rhythm_daily_hhi` entra fuerte (`0,373`) y `routine_od_hhi`
  aparece como duplicado de rutina OD-tiempo; suma de variables bajadas = 0,398.
- `k=4, s=3,0`: `rhythm_daily_hhi` y `routine_od_hhi` entran con pesos altos;
  suma de variables bajadas = 0,567.

Conclusion:

- Correr sparse sobre `v0` confirma la razon del recorte `v0b`: el algoritmo
  tiende a seleccionar variables redundantes que ya tenian representantes en
  `v0b`.
- `v0` solo mejora marginalmente algunas metricas cuando deja de ser sparse
  y usa casi todas las variables.
- Recomendacion: mantener `v0b` como especificacion principal. Usar `v0` como
  sensibilidad para demostrar que la historia no depende del recorte, no como
  input principal de sparse k-means.

## 2026-06-04 — Contrato de transformacion NMF para `behavioral_wide v0b`

Pregunta:

- Antes de correr NMF sobre `behavioral_wide`, definir como transformar cada
  variable. El contrato de PCA/sparse k-means usa variables estandarizadas, pero
  eso no sirve para NMF porque NMF requiere inputs no negativos y es sensible a
  escala.

Decision principal:

- Usar `behavioral_wide v0b` como input principal de NMF.
- No usar z-score, residualizacion centrada ni variables negativas.
- No usar QR/BIP ni derivados como input.
- Transformar cada variable con `winsor p01-p99 + minmax [0,1]`, calculado en
  el universo de entrenamiento (`alta_n3` para la primera prueba).
- Aplicar clipping final a `[0,1]`.
- Aplicar ponderacion por bloque `1 / sqrt(n_variables_bloque)` despues del
  minmax.

Razon:

- Las variables vienen en escalas distintas: horas, entropias, HHI, shares,
  logs e indices con techos. En crudo, NMF quedaria dominado por unidades y
  niveles base.
- Z-score crea valores negativos y rompe la interpretacion aditiva de NMF.
- Rank/percentile scaling es una sensibilidad posible, pero no debe ser la
  primera opcion porque destruye parte de la interpretacion de ceros, techos y
  magnitud efectiva.
- `winsor p01-p99 + minmax` conserva orden y no negatividad, reduce colas y
  usa el rango empirico robusto de cada variable.
- La ponderacion por bloque evita que un bloque pese mas solo por tener mas
  columnas. No fuerza igualdad perfecta de energia, pero corrige dominancia
  dimensional.

Reglas por tipo de variable:

- Variables continuas/log/horarias (`log1p_n_viajes`, `hora_mean`, `hora_std`,
  `activity_zone_entropy`, `tour_day_span_hours_mean`): winsorizar p01-p99 y
  escalar minmax.
- Shares/proporciones en `[0,1]`: usar tambien winsor p01-p99 + minmax. Si
  `p01=0` y `p99=1`, equivale practicamente a identidad; si no, ajusta el rango
  util observado.
- HHI, entropias e indices normalizados: mantener orientacion natural y aplicar
  el mismo escalamiento robusto. No invertir variables por defecto.
- Variables con techo frecuente en 1 (`routine_od_time_entropy_norm`,
  `tour_closed_loop_day_share`, etc.): mantenerlas, pero revisar despues si
  dominan componentes por saturacion.
- Variables composicionales: usar la version ya reducida en `v0b`; no
  reintroducir categorias base implicitas.

Bloques y ponderadores para `v0b`:

| block | n_variables | block_weight |
|---|---:|---:|
| `intensidad` | 2 | 0.7071 |
| `horario` | 5 | 0.4472 |
| `regularidad` | 3 | 0.5774 |
| `modal` | 4 | 0.5000 |
| `espacial_od` | 4 | 0.5000 |
| `rutina` | 3 | 0.5774 |
| `daily_tour` | 5 | 0.4472 |

Variables `v0b` y transformacion base:

| block | variable | transformacion NMF |
|---|---|---|
| `intensidad` | `log1p_n_viajes` | `clip(p01,p99) + minmax + block_weight` |
| `intensidad` | `rhythm_active_day_density_span` | `clip(p01,p99) + minmax + block_weight` |
| `horario` | `hora_mean` | `clip(p01,p99) + minmax + block_weight` |
| `horario` | `hora_std` | `clip(p01,p99) + minmax + block_weight` |
| `horario` | `share_lab_pm` | `clip(p01,p99) + minmax + block_weight` |
| `horario` | `share_lab_pt` | `clip(p01,p99) + minmax + block_weight` |
| `horario` | `share_no_lab` | `clip(p01,p99) + minmax + block_weight` |
| `regularidad` | `rhythm_single_trip_day_share` | `clip(p01,p99) + minmax + block_weight` |
| `regularidad` | `rhythm_weekly_hhi` | `clip(p01,p99) + minmax + block_weight` |
| `regularidad` | `rhythm_weekly_entropy_norm` | `clip(p01,p99) + minmax + block_weight` |
| `modal` | `share_trips_solo_bus` | `clip(p01,p99) + minmax + block_weight` |
| `modal` | `share_trips_metro_bus` | `clip(p01,p99) + minmax + block_weight` |
| `modal` | `share_trips_with_transfer` | `clip(p01,p99) + minmax + block_weight` |
| `modal` | `share_trips_in_multi_route_od` | `clip(p01,p99) + minmax + block_weight` |
| `espacial_od` | `activity_zone_entropy` | `clip(p01,p99) + minmax + block_weight` |
| `espacial_od` | `routine_main_od_share` | `clip(p01,p99) + minmax + block_weight` |
| `espacial_od` | `routine_main_od_roundtrip_balance` | `clip(p01,p99) + minmax + block_weight` |
| `espacial_od` | `origin_zone_top1_share` | `clip(p01,p99) + minmax + block_weight` |
| `rutina` | `routine_od_time_hhi` | `clip(p01,p99) + minmax + block_weight` |
| `rutina` | `routine_lab_peak_share` | `clip(p01,p99) + minmax + block_weight` |
| `rutina` | `routine_od_time_entropy_norm` | `clip(p01,p99) + minmax + block_weight` |
| `daily_tour` | `tour_three_plus_trip_day_share` | `clip(p01,p99) + minmax + block_weight` |
| `daily_tour` | `tour_closed_loop_day_share` | `clip(p01,p99) + minmax + block_weight` |
| `daily_tour` | `tour_mixed_mode_day_share` | `clip(p01,p99) + minmax + block_weight` |
| `daily_tour` | `tour_day_span_hours_mean` | `clip(p01,p99) + minmax + block_weight` |
| `daily_tour` | `tour_last_trip_lab_pm_peak_share` | `clip(p01,p99) + minmax + block_weight` |

Caveat de interpretacion:

- NMF sobre `behavioral_wide` debe leerse como mezcla de prototipos conductuales,
  no como clusters geometricamente separados necesariamente.
- Las asignaciones duras por componente maximo son utiles para tablas, pero se
  deben revisar tambien los scores/membresias y la entropia de asignacion.
- Si los componentes quedan dominados por variables de baseline alto
  (`entropy_norm`, `closed_loop`, etc.), la primera sensibilidad sera repetir
  NMF sin block weighting o con percentile/rank scaling, no volver a `v0`.

Plan de modelado:

- Crear una matriz transformada reproducible para NMF, guardando parametros
  p01/p99 y ponderadores.
- Correr NMF `k=2..8` con multiples semillas.
- Evaluar reconstruccion, estabilidad, tamanos de segmentos, entropia de
  membresia y top variables por componente.
- Usar QR/BIP solo post-hoc despues de seleccionar candidatos por criterios no
  supervisados.

## 2026-06-04 — Primera corrida NMF sobre `behavioral_wide v0b`

Scripts agregados:

- `scripts/audits/run_behavioral_wide_nmf.py`
  - Lee la matriz `behavioral_wide`.
  - Aplica `clip(p01,p99) + minmax [0,1] + block_weight`.
  - Reutiliza la logica NMF existente de estabilidad, asignaciones y top
    features.
- `scripts/audits/summarize_behavioral_wide_nmf_segments.py`
  - Cruza asignaciones con QR/BIP.
  - Genera perfiles medios de features por segmento.

Comando NMF inicial:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/run_behavioral_wide_nmf.py \
  --branch-id v0b_alta_n3 \
  --k-range 2-8 \
  --n-runs 5 \
  --fit-sample-size 300000 \
  --feature-tag nmf_v0b_robust_minmax_block \
  --no-save-scores
```

Comando post-hoc:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/summarize_behavioral_wide_nmf_segments.py \
  --branch-id v0b_alta_n3 \
  --feature-tag nmf_v0b_robust_minmax_block \
  --k all
```

Outputs:

- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/nmf_metrics.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/nmf_top_features.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/nmf_assignments.parquet`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/nmf_transform_parameters.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/posthoc/segment_qr_summary.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/posthoc/segment_target_association.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/posthoc/segment_feature_profile.csv`

Metricas principales:

| k | relative_recon | stability_ari | min_segment_share | max_segment_share |
|---:|---:|---:|---:|---:|
| 2 | 0.492 | 0.880 | 0.218 | 0.782 |
| 3 | 0.440 | 0.688 | 0.133 | 0.526 |
| 4 | 0.395 | 0.543 | 0.160 | 0.381 |
| 5 | 0.365 | 0.405 | 0.073 | 0.343 |
| 6 | 0.339 | 0.385 | 0.037 | 0.431 |
| 7 | 0.315 | 0.298 | 0.002 | 0.278 |
| 8 | 0.293 | 0.220 | 0.00004 | 0.411 |

El `run_meta.json` reporta:

- `elbow_d2_k = 4`
- `elbow_segment_k = 4`
- `elbow_consensus_k = 4`

Lectura no supervisada:

- `k=4` queda como candidato principal inicial: codo consenso, segmentos sin
  nichos extremos y componentes interpretables.
- `k=5` mejora reconstruccion y revela un segmento pequeno interpretable, pero
  baja estabilidad y tiene segmento minimo de 7,3%; queda como sensibilidad.
- `k>=6` no conviene como primera lectura: estabilidad baja y aparecen
  segmentos muy pequenos. `k=7` y `k=8` fragmentan de forma no defendible para
  una segmentacion principal.
- Hubo una advertencia de convergencia en una semilla de `k=6`; no afecta al
  candidato principal `k=4`, pero refuerza no priorizar `k>=6` aun.

Componentes `k=4`:

- Componente 0: cierre/pendularidad y reciprocidad.
  - Top: `routine_main_od_roundtrip_balance`,
    `tour_closed_loop_day_share`, `rhythm_weekly_entropy_norm`,
    `routine_od_time_entropy_norm`, `routine_main_od_share`.
- Componente 1: alta intensidad + anclaje laboral/peak.
  - Top: `log1p_n_viajes`, `routine_lab_peak_share`,
    `tour_last_trip_lab_pm_peak_share`, `hora_std`,
    `tour_day_span_hours_mean`, `share_lab_pm`.
- Componente 2: actividad densa/concentrada semanalmente y dias complejos.
  - Top: `rhythm_active_day_density_span`, `rhythm_weekly_hhi`,
    `routine_od_time_entropy_norm`, `routine_od_time_hhi`,
    `tour_three_plus_trip_day_share`.
- Componente 3: diversidad/dispersión con bus y baja reciprocidad.
  - Top: `rhythm_weekly_entropy_norm`, `routine_od_time_entropy_norm`,
    `share_trips_solo_bus`, `rhythm_single_trip_day_share`,
    `activity_zone_entropy`.

Post-hoc QR/BIP:

- En `k=4`, la asociacion con QR existe pero es baja:
  - Cramer's V `is_qr`: 0,018.
  - Cramer's V `tipo_tarjeta`: 0,024.
- Segmentos `k=4`:
  - Segmento 0: 38,1%, QR lift 1,028, QR_RED lift 0,934.
  - Segmento 1: 27,7%, QR lift 0,932, QR_RED lift 1,223.
  - Segmento 2: 16,0%, QR lift 1,004, QR_RED lift 0,939.
  - Segmento 3: 18,2%, QR lift 1,040, QR_RED lift 0,852.
- En `k=5`, aparece un segmento pequeno con mayor senal QR:
  - Segmento 4: 7,3%, QR lift 1,323, QR_RED lift 1,640,
    QR_OTHER lift 1,272.
  - Perfil: mayor `routine_lab_peak_share`, `tour_last_trip_lab_pm_peak_share`,
    `share_lab_pm`, `share_lab_pt`, `routine_od_time_hhi`, `hora_std` y
    `tour_day_span_hours_mean`; menor intensidad total que el promedio.

Decision provisional:

- Usar `k=4` como candidato NMF principal para `behavioral_wide v0b`.
- Usar `k=5` como sensibilidad sustantiva porque separa un grupo pequeno de
  anclaje laboral/peak con alta adopcion QR, pero no elegirlo por QR.
- Siguiente paso: correr una segunda pasada con mas semillas para `k=4` y
  `k=5`, idealmente guardando scores/membresias para evaluar entropia de
  asignacion y perfiles mixtos.

## 2026-06-04 — Paquete visual para revisar NMF `behavioral_wide v0b`

Script agregado:

- `scripts/audits/visualize_behavioral_wide_nmf.py`
  - Lee los outputs NMF y post-hoc ya generados.
  - Produce figuras de seleccion de `k`, composicion de componentes, perfiles
    medios por segmento y lifts QR/BIP.
  - Genera un HTML compacto para revisar la interpretacion sin depender de
    tablas largas.

Output principal:

- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/behavioral_wide_nmf_review.html`

Figuras principales:

- `figures/nmf_model_selection.png`
- `figures/nmf_k4_components_heatmap.png`
- `figures/nmf_k4_segment_profile_heatmap.png`
- `figures/nmf_k4_qr_lifts.png`
- `figures/nmf_k5_qr_lifts.png`

Lectura operativa para revisar juntos:

- `k=4` es el candidato principal no supervisado: codo consenso, segmentos de
  tamano defendible y perfiles interpretables.
- `k=5` no debe elegirse por QR, pero es una sensibilidad util porque separa un
  nicho pequeno de anclaje laboral/peak con mayor lift QR.
- Los componentes NMF deben leerse como prototipos conductuales aditivos, no
  como ejes ortogonales ni como clusters puros.
- La asignacion dura de segmentos es una simplificacion: conviene revisar luego
  scores/membresias para detectar usuarios mixtos o asignaciones de baja
  dominancia.
- La asociacion QR/BIP sigue siendo post-hoc y descriptiva.

## 2026-06-04 — Validacion interna de segmentos duros NMF

Script agregado:

- `scripts/audits/evaluate_behavioral_wide_nmf_quality.py`
  - Reconstruye la transformacion NMF robusta.
  - Evalua asignaciones duras `segment_k*` sobre muestra reproducible.
  - Calcula silhouette euclidiano, silhouette coseno, Calinski-Harabasz y
    Davies-Bouldin.

Output:

- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/nmf_hard_segment_quality.csv`

Metricas principales:

| k | silhouette_euclidean | silhouette_cosine | Davies-Bouldin | stability ARI | relative recon |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.206 | 0.340 | 1.947 | 0.880 | 0.492 |
| 3 | 0.166 | 0.300 | 1.929 | 0.688 | 0.440 |
| 4 | 0.135 | 0.255 | 1.955 | 0.543 | 0.395 |
| 5 | 0.126 | 0.233 | 2.030 | 0.405 | 0.365 |
| 6 | 0.104 | 0.178 | 2.082 | 0.385 | 0.339 |
| 7 | 0.037 | 0.056 | 2.085 | 0.298 | 0.315 |
| 8 | 0.076 | 0.087 | 2.123 | 0.220 | 0.293 |

Lectura:

- Las metricas de separacion dura son bajas/moderadas; no hay evidencia de
  clusters compactos y claramente separados.
- `k=2` y `k=3` son mejores si el unico criterio fuera separacion interna, pero
  son mas gruesos y menos utiles narrativamente.
- `k=4` es un tradeoff: peor separacion que `k=2/3`, pero mejor
  reconstruccion, tamanos defendibles e interpretacion conductual mas rica.
- `k=5` mejora reconstruccion y separa un nicho QR, pero empeora estabilidad,
  Davies-Bouldin y tamanos; por eso debe quedar como sensibilidad.
- La conclusion metodologica correcta es presentar NMF como perfiles/prototipos
  latentes interpretables, no como clusters duros de alta separacion geometrica.

## 2026-06-04 — Post-hoc binario QR vs BIP dentro de segmentos NMF

Se agregan salidas para distinguir dos objetos metodologicamente distintos:

- Los componentes NMF y los perfiles de segmento se estiman antes de usar medio
  de pago; por lo tanto no cambian al mirar QR/BIP.
- La comparacion QR vs BIP dentro de cada segmento es post-hoc y sirve para
  revisar si, dado un mismo perfil latente, los usuarios QR tienen conducta
  distinta de los BIP.

Scripts actualizados:

- `scripts/audits/summarize_behavioral_wide_nmf_segments.py`
  - Agrega `segment_binary_payment_feature_profile.csv`.
  - Agrega `segment_qr_vs_bip_feature_diff.csv`.
- `scripts/audits/visualize_behavioral_wide_nmf.py`
  - Agrega figuras binarias QR/BIP por segmento.
  - Agrega heatmaps de diferencias conductuales QR vs BIP dentro de segmento.

Outputs nuevos:

- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/posthoc/segment_binary_payment_feature_profile.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/posthoc/segment_qr_vs_bip_feature_diff.csv`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/figures/nmf_k4_qr_vs_bip_feature_diff_heatmap.png`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3__nmf_v0b_robust_minmax_block/nmf/figures/nmf_k5_qr_vs_bip_feature_diff_heatmap.png`

Lectura inicial k=5:

- En el segmento 4, que tiene mayor lift QR, las diferencias internas QR vs BIP
  no son extremas.
- Esto sugiere que el lift QR del segmento 4 viene principalmente de que el
  segmento completo captura un perfil laboral/peak con mayor adopcion QR, no de
  que los QR dentro del segmento tengan una conducta radicalmente distinta a los
  BIP del mismo segmento.
- Para tesis, conviene separar: perfil conductual del segmento versus
  composicion de medio de pago dentro del segmento.

## 2026-06-05 — Sensibilidad NMF `behavioral_wide v0b` por universo

Se materializaron y corrieron matrices `v0b` adicionales para evaluar si el
resultado principal de `alta_n3` depende del universo de usuarios:

- `v0b_alta_n5`
- `v0b_alta_n10`
- `v0b_alta_n3_home3`

Comandos conceptuales:

- Builder: `build_user_behavioral_segmentation_matrix.py --spec v0b`
- NMF: `run_behavioral_wide_nmf.py --k-range 4,5 --n-runs 5`
- Post-hoc: `summarize_behavioral_wide_nmf_segments.py`
- Calidad: `evaluate_behavioral_wide_nmf_quality.py`
- Visual: `visualize_behavioral_wide_nmf.py`

Outputs:

- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n5__nmf_v0b_robust_minmax_block/nmf/behavioral_wide_nmf_review.html`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n10__nmf_v0b_robust_minmax_block/nmf/behavioral_wide_nmf_review.html`
- `tmp/audits/user_level_redesign/segmentation/models/behavioral_wide/v0b_alta_n3_home3__nmf_v0b_robust_minmax_block/nmf/behavioral_wide_nmf_review.html`

Resumen de calidad interna:

| branch | k | n | min share | max share | sil cosine | relative recon | stability ARI |
|---|---:|---:|---:|---:|---:|---:|---:|
| `v0b_alta_n3` | 4 | 2460264 | 0.160 | 0.381 | 0.255 | 0.395 | 0.543 |
| `v0b_alta_n3` | 5 | 2460264 | 0.073 | 0.343 | 0.233 | 0.365 | 0.405 |
| `v0b_alta_n5` | 4 | 1838455 | 0.094 | 0.438 | 0.195 | 0.385 | 0.436 |
| `v0b_alta_n5` | 5 | 1838455 | 0.141 | 0.230 | 0.124 | 0.354 | 0.324 |
| `v0b_alta_n10` | 4 | 1286681 | 0.082 | 0.403 | 0.109 | 0.378 | 0.281 |
| `v0b_alta_n10` | 5 | 1286681 | 0.081 | 0.419 | 0.095 | 0.347 | 0.369 |
| `v0b_alta_n3_home3` | 4 | 1493677 | 0.108 | 0.444 | 0.184 | 0.373 | 0.289 |
| `v0b_alta_n3_home3` | 5 | 1493677 | 0.041 | 0.377 | 0.157 | 0.343 | 0.311 |

Lectura:

- La sensibilidad confirma que NMF no produce clusters duros geometricamente
  fuertes. Los silhouettes coseno caen respecto al caso base `alta_n3`,
  especialmente en `alta_n10`.
- El patron QR-heavy de `k=5` si se mantiene en todos los universos, aunque
  cambia el tamano del segmento: 7.3% en `alta_n3`, 20.2% en `alta_n5`, 41.9%
  en `alta_n10`, 7.9% en `alta_n3_home3`.
- En todos los universos, el segmento QR-heavy tiene lift QR y QR_RED mayor a
  1: `alta_n3` QR 1.323 / QR_RED 1.640; `alta_n5` QR 1.284 / QR_RED 1.605;
  `alta_n10` QR 1.233 / QR_RED 1.375; `alta_n3_home3` QR 1.390 / QR_RED 1.764.
- El comportamiento del segmento QR-heavy es estable: mayor presencia en
  periodo punta/laboral, mayor `routine_lab_peak_share`, mayor
  `routine_od_time_hhi`, mayor `routine_main_od_share`, menor `share_no_lab`,
  menor `tour_three_plus_trip_day_share` y menor `tour_mixed_mode_day_share`.
- La interpretacion defensible es que la señal QR post-hoc aparece asociada a
  un perfil laboral/peak rutinario y concentrado. No debe presentarse como una
  clusterizacion natural fuerte ni como efecto causal del medio de pago.

Caveat:

- `alta_n10` tuvo warnings de convergencia en algunas corridas `k=4`, aunque
  los outputs se generaron. Si se quiere usar `alta_n10` como sensibilidad
  formal, conviene repetir con mas iteraciones antes de congelar tablas.
