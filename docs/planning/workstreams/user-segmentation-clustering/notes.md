# User Segmentation and Clustering Notes

## 2026-05-01 - Apertura del workstream

Se decide abrir un frente separado de segmentación/clustering para recuperar el foco de la propuesta inicial de tesis.

### Motivación

La propuesta original no se limitaba a estimar modelos logit de elección de medio de pago. También planteaba caracterizar comportamientos de usuarios, identificar perfiles o segmentos y estudiar cómo esos perfiles se relacionan con la adopción de tecnologías digitales en transporte público.

El trabajo reciente avanzó fuertemente en la especificación MNL territorial e infraestructura de acceso, pero dejó pendiente esta capa de segmentación. Este workstream busca reconectar ambos frentes sin desordenar la rama principal.

### Decisión de organización

- Se creó el worktree:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-segmentation`
- Se creó la rama:
  - `feature/user-segmentation-clustering`
- La rama parte desde:
  - `feature/od-buffers-enriched-controls`
  - commit `26ac0b7`
- La rama fue publicada en `origin`.

### Decisión metodológica inicial

La segmentación no debe partir asumiendo que `id_tarjeta` identifica usuarios.

Razones:

- `pk_viaje` es una llave primaria de viaje, generada a partir de `id_tarjeta`, `id_viaje` y el timestamp normalizado de inicio;
- `id_tarjeta` identifica una credencial/medio de pago, no necesariamente una persona;
- un mismo usuario podría viajar con tarjeta BIP física y luego con QR, apareciendo como identificadores distintos;
- `is_qr` se deriva operativamente desde `id_contrato`/`contrato`, con contratos `171` y `102` marcados como QR;
- ya existe una advertencia metodológica en `02_eda/eda_trips_overview.qmd`: cada `id_tarjeta` puede ser BIP o QR, por lo que el share QR por `id_tarjeta` no debe interpretarse como adopción gradual de una misma persona.

Por lo tanto, el primer paso del workstream es auditar identificadores y decidir si la segmentación será:

- por credencial/medio de pago;
- por viaje agrupado a nivel de tarjeta;
- por usuario real, solo si existe una llave que permita vincular BIP y QR para la misma persona;
- o por perfiles de uso agregados sin afirmar identidad individual.

### Rol respecto al modelo MNL

La segmentación se tratará como una capa complementaria:

- primero se construyen perfiles de comportamiento;
- luego se evalúa si esos perfiles ayudan a interpretar diferencias en adopción de `QR_RED` y `QR_OTHER`;
- finalmente se decide si los segmentos entran al modelo como interacciones, como modelos separados por segmento o como análisis descriptivo paralelo.

No se asume de entrada que el modelo MNL final deba reemplazarse por un modelo segmentado.

### Preguntas iniciales

- ¿Existe una llave de usuario real que vincule BIP y QR para una misma persona?
- ¿Qué representa exactamente `id_contrato` y si permite distinguir canales QR sin identificar personas?
- ¿Cuál es la unidad disponible y estable entre 2024 y 2025?
- ¿Qué ventana temporal usar para construir perfiles?
- ¿Se segmenta usando solo comportamiento de viaje o también contexto territorial?
- ¿La adopción QR debe ser una variable usada para formar segmentos o una variable usada para describir segmentos?
- ¿Conviene separar primero credenciales frecuentes de credenciales esporádicas?
- ¿Qué hacemos con identificadores observados en solo un año?

### Primer enfoque recomendado

Partir con una auditoría de identificadores y luego, si corresponde, una tabla agregada por la unidad elegida:

- número de viajes observados;
- share de viajes por medio de pago;
- indicador de adopción QR;
- diversidad de horarios/franjas;
- frecuencia de uso en días laborales/no laborales;
- tiempos promedio y dispersión de viaje;
- transbordos promedio;
- uso de metro/bus o combinaciones modales;
- diversidad espacial de zonas de origen/destino;
- contexto territorial promedio o dominante de origen.

Luego hacer EDA antes de aplicar clustering.

### Riesgos

- Confundir segmentos de comportamiento con segmentos socioeconómicos.
- Crear clusters dominados solo por intensidad de uso.
- Incluir adopción QR en el clustering y luego interpretar mecánicamente que los clusters explican adopción QR.
- Forzar demasiados clusters sin estabilidad ni interpretación clara.

## 2026-05-01 - Auditoría preliminar de identificadores

Se creó el notebook:

- `03_models/user_segmentation/01_identifier_audit.qmd`

El notebook parte desde los parquets finales con tiempos de espera recalculados:

- `tmp/viajes_con_te_calculado_2024-W17.parquet`
- `tmp/viajes_con_te_calculado_2025-W17.parquet`

Como esos parquets no están versionados, el notebook usa el worktree principal `tesis-project` como fallback cuando se ejecuta desde `tesis-project-segmentation`.

### Hallazgos preliminares

Auditoría rápida ejecutada con el Python de `larch-env`:

- `2024-W17`:
  - `n_rows = 11,931,489`
  - `n_pk_viaje = 11,931,489`
  - `n_id_tarjeta = 2,422,283`
  - `n_qr_rows = 1,544,389`
  - `share_qr_rows = 0.1294`
  - `n_cards_has_qr_and_bip = 0`
- `2025-W17`:
  - `n_rows = 12,131,426`
  - `n_pk_viaje = 12,131,426`
  - `n_id_tarjeta = 2,451,340`
  - `n_qr_rows = 2,020,511`
  - `share_qr_rows = 0.1666`
  - `n_cards_has_qr_and_bip = 0`
- Interanual:
  - `n_cards_all = 4,031,185`
  - `n_cards_in_both_partitions = 842,438`
  - `n_cards_has_qr_and_bip_all = 0`

### Lectura metodológica

- `pk_viaje` funciona como llave de viaje: es único por fila en ambas particiones.
- `id_tarjeta` permite agrupar viajes por credencial, pero no debe interpretarse como usuario/persona.
- Ningún `id_tarjeta` mezcla viajes QR y no QR, ni dentro de cada semana ni al juntar 2024-W17 con 2025-W17.
- Esto confirma que no corresponde medir adopción QR como proporción QR por `id_tarjeta`.
- Si no se encuentra una llave persona-equivalente adicional, el framing debe cambiar desde "segmentación de usuarios" hacia "segmentación de credenciales/perfiles de uso observados".

## 2026-05-01 - Tabla de features por credencial

Se creó el notebook:

- `03_models/user_segmentation/02_credential_feature_table.qmd`

El notebook construye una tabla agregada por `id_tarjeta`, interpretada explícitamente como **credencial observada**, no como persona/usuario.

### Output

El notebook escribe:

- `03_models/artifacts/user_segmentation/credential_features_pooled_2024_2025.parquet`

Este parquet queda ignorado por git por ser artifact local.

### Sanidad del output

Resultados de ejecución:

- `n_credentials = 4,031,185`
- `n_trip_rows_recovered = 24,062,915`
- `n_unique_trips_recovered = 24,062,915`
- `n_qr_credentials = 649,026`
- `share_qr_credentials = 0.1610`
- `n_credentials_mixed_qr_state = 0`
- `n_credentials_multi_contract = 38,778`
- `median_trips = 4`
- `p90_trips = 13`
- `p99_trips = 24`

### Umbrales de actividad evaluados

- `min_trips >= 1`:
  - `4,031,185` credenciales
  - `100%` de viajes
  - `share_qr_credentials = 0.1610`
- `min_trips >= 3`:
  - `2,657,784` credenciales
  - `90.3%` de viajes
  - `share_qr_credentials = 0.1493`
- `min_trips >= 5`:
  - `1,878,549` credenciales
  - `78.8%` de viajes
  - `share_qr_credentials = 0.1425`
- `min_trips >= 10`:
  - `818,781` credenciales
  - `49.0%` de viajes
  - `share_qr_credentials = 0.1363`

### Decisión preliminar

Para clustering inicial, no usar `is_qr_credential`, `contrato` ni derivados de pago como features formadoras.

Usarlas después para describir clusters:

- composición QR/no QR;
- contratos dominantes;
- diferencias de adopción por perfil de uso.

El siguiente paso debe ser un EDA de esta tabla para decidir:

- filtro mínimo de actividad;
- transformaciones (`log1p` para conteos/intensidad);
- variables altamente correlacionadas;
- outliers que podrían dominar `k-means`;
- si conviene clusterizar todas las credenciales elegibles juntas o separar primero por baja/alta frecuencia.

## 2026-05-01 - EDA de features por credencial

Se creó el notebook:

- `03_models/user_segmentation/03_credential_feature_eda.qmd`

El notebook carga la tabla de features por credencial y evalúa umbrales de actividad, transformaciones, distribuciones, missingness, outliers y correlaciones antes de correr clustering.

### Umbral principal

La decisión preliminar es usar `min_trips >= 5` como muestra principal:

- `1,878,549` credenciales observadas.
- `46.6%` de las credenciales.
- `78.8%` de los viajes.
- `share_qr_credentials = 0.1425`.

Este umbral reduce ruido de credenciales con actividad muy baja, pero conserva la mayoría de los viajes observados. Como sensibilidad, conviene comparar luego con `min_trips >= 3` y `min_trips >= 10`.

### Transformaciones

- Conteos e intensidad: `log1p`.
- Tiempos: conversión de segundos a minutos.
- Shares: escala original `[0, 1]`.
- Variables de pago: se excluyen del clustering inicial y se reservan para caracterizar clusters ex post.

### Variables recomendadas para el primer clustering

- `log1p_n_trips`
- `log1p_n_active_days`
- `log1p_trips_per_active_day`
- `n_partitions`
- `share_lab_pm`
- `share_lab_pt`
- `share_no_lab`
- `log1p_n_origin_stops`
- `log1p_n_destination_stops`
- `median_total_time_min`
- `mean_initial_wait_min`
- `mean_transfer_wait_min`
- `share_with_transfer`
- `share_with_metro`

### Variables excluidas de la primera especificación

- `share_lab_valle`: queda implícita al incluir las demás shares temporales.
- `log1p_n_origin_zones` y `log1p_n_destination_zones`: muy correlacionadas con diversidad de paraderos.
- `mean_vehicle_time_min`: muy correlacionada con `median_total_time_min`.
- `mean_n_transfers`: muy correlacionada con `share_with_transfer`.
- `is_qr_credential`, `n_qr_states`, `n_contracts`, `first_observed_contract`: se reservan para descripción posterior, no para formar clusters.

### Correlaciones relevantes

- `log1p_n_origin_zones` vs. `log1p_n_origin_stops`: `0.951`.
- `log1p_n_destination_zones` vs. `log1p_n_destination_stops`: `0.938`.
- `median_total_time_min` vs. `mean_vehicle_time_min`: `0.934`.
- `mean_n_transfers` vs. `share_with_transfer`: `0.886`.
- `log1p_n_trips` vs. `log1p_n_active_days`: `0.853`.

### Siguiente paso

Crear un notebook de clustering base con `k-means` sobre la muestra principal `min_trips >= 5`, estandarizando features y comparando valores de `k` entre 3 y 8. Luego describir los clusters usando variables no formadoras, especialmente composición QR/no QR y contrato.

## 2026-05-01 - Notebook de clustering base preparado

Se creó el notebook:

- `03_models/user_segmentation/04_credential_clustering_baselines.qmd`

El notebook implementa una primera comparación de `k-means` usando `MiniBatchKMeans`, por el tamaño de la muestra principal (`1,878,549` credenciales para `min_trips >= 5`). La configuración base es:

- `MAIN_MIN_TRIPS = 5`
- `K_VALUES = 3..8`
- `SELECTED_K = 5` como solución candidata solo para perfilar, no como decisión final.
- `SAMPLE_METRICS_N = 5,000` para calcular silhouette sobre una submuestra.
- variables de pago excluidas de la formación de clusters.

El notebook reporta:

- métricas por `k`: inertia, Davies-Bouldin, Calinski-Harabasz, silhouette en muestra, share mínimo y máximo de cluster;
- perfil del `SELECTED_K`: tamaño, intensidad de uso, temporalidad, diversidad de paraderos, tiempos, transbordos, uso de Metro y composición QR;
- contratos dominantes por cluster;
- centroides desestandarizados en escala transformada.

Se hizo una prueba reducida exitosa con `min_trips >= 20`, `k=3`, `SAMPLE_METRICS_N=1000` y sin guardar artefactos. Falta ejecutar el notebook completo con la configuración principal y analizar los resultados.

## 2026-05-01 - Resultado preliminar del clustering base

El notebook `04_credential_clustering_baselines.qmd` se ejecutó con `min_trips >= 5` y `K_VALUES = 3..8`. La solución `k=4` quedó como candidato principal preliminar:

- mejor `silhouette_sample` entre los valores probados: `0.138`.
- mejor `davies_bouldin`: `1.945`.
- clusters balanceados: entre `24.1%` y `25.6%` de las credenciales elegibles.
- evita la fragmentación de `k >= 5`.

Los perfiles interpretables para `k=4` fueron:

- `cluster 0`: viajes largos multietapa con alta presencia de Metro/transbordo y menor QR.
- `cluster 1`: credenciales más intensivas/diversas.
- `cluster 2`: viajes cortos, alta presencia Metro y baja espera.
- `cluster 3`: baja presencia Metro y alta espera inicial, perfil más bus-dependiente.

La composición QR no define los clusters; se interpreta solo como descriptor posterior. Esto es consistente con la decisión metodológica de excluir variables de pago de la formación de clusters.

## 2026-05-01 - Notebook de sensibilidad de clusters preparado

Se creó el notebook:

- `03_models/user_segmentation/05_credential_cluster_sensitivity_and_description.qmd`

El notebook fija `k=4` y estima la misma especificación de clustering para tres umbrales de actividad:

- `min_trips >= 3`
- `min_trips >= 5`
- `min_trips >= 10`

La comparación no asume que los números de cluster sean directamente comparables entre corridas. Para facilitar la lectura se agrega una etiqueta semántica heurística a partir del perfil de cada cluster:

- `long_multistage_metro`
- `intensive_diverse`
- `short_metro_direct`
- `bus_high_wait`

El objetivo es verificar si los perfiles sustantivos reaparecen al cambiar el filtro de actividad, antes de avanzar hacia interpretaciones fuertes o hacia integración con modelos logit.

## 2026-05-02 - Decisión preliminar y próximos pasos

La sensibilidad de `k=4` fue ejecutada para `min_trips >= 3`, `>= 5` y `>= 10`.

### Resultado preliminar

Se deja como especificación principal preliminar:

- unidad: credencial observada (`id_tarjeta`), no persona;
- muestra principal: `min_trips >= 5`;
- método: `MiniBatchKMeans`;
- número de clusters: `k=4`;
- variables formadoras: 14 variables de comportamiento, temporalidad, diversidad de paraderos, tiempos, transbordos y Metro;
- variables de pago: excluidas del clustering y usadas solo para descripción posterior.

### Lectura de sensibilidad

- `min_trips >= 3`: reaparecen los cuatro perfiles esperados, con tamaños razonables.
- `min_trips >= 5`: queda como punto principal por balance entre cobertura de viajes, reducción de ruido e interpretabilidad.
- `min_trips >= 10`: cambia la población hacia credenciales intensivas; tres clusters se vuelven más difíciles de etiquetar con las reglas heurísticas, por lo que se interpreta como sensibilidad de población intensiva y no como reemplazo de la especificación principal.

### Perfiles preliminares

- viajes largos multietapa con alta presencia de Metro/transbordo y menor QR;
- credenciales intensivas/diversas;
- viajes cortos con alta presencia de Metro y baja espera;
- viajes de baja presencia Metro y alta espera inicial, más bus-dependientes.

### Próxima fase

Antes de probar otros modelos de clustering, se prioriza mejorar la tabla de features por credencial. Variables candidatas:

- proporción de viajes con espera inicial alta (`te0_calculado > 10 min`);
- proporción de viajes con dos o más transbordos;
- percentiles altos o dispersión de tiempo total (`p75`, `p90`, IQR);
- proporción de viajes con Metro y transbordo simultáneamente;
- concentración espacial de origen/destino, por ejemplo share del origen dominante o entropía simple;
- diferencias de fricción por franja horaria si son fáciles de construir.

Después de enriquecer features, se re-estima `k-means` con el mismo diseño (`min_trips >= 5`, `k=3..8`, sensibilidad `3/10`). Solo después se evaluarán alternativas como GMM, clustering jerárquico o LCA.
