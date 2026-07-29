# Scripts de auditoría

Esta carpeta contiene scripts reproducibles para validar supuestos de datos antes de integrarlos al pipeline principal de modelación.

## `build_operational_offer_demand_exposure.py`

Reconstruye demanda observada y oferta bus para ocho semanas, y materializa
exposiciones a nivel tarjeta sin depender de las variables operacionales históricas.

### Comando

```bash
python scripts/audits/build_operational_offer_demand_exposure.py --force
```

### Variables normalizadas de oferta

- `op_bus_stops_with_supply_zone_franja_density_km2`: paraderos activos por km2
  para cada zona, semana y franja con geometría ZONA777.
- `op_bus_stops_with_supply_zone_franja_density_percentile`: percentil de esa
  densidad entre zonas de la misma semana-franja.
- `op_bus_stops_with_supply_zone_franja_density_percentile_mean`: promedio del
  percentil sobre los viajes con geometría de cada tarjeta.
- `op_stop_bus_supply_buses_h_observed_percentile`: percentil de buses/h entre
  observaciones únicas paradero-hora de la misma semana-franja.
- `op_stop_bus_supply_buses_h_observed_percentile_mean`: promedio sobre los
  viajes bus-like con match paradero-hora de cada tarjeta.

Los percentiles están en `[0, 1]`. Las zonas sin geometría se mantienen en las
variables que no requieren área, pero se excluyen de la densidad.

## `build_operational_bus_demand_pressure.py`

Construye la demanda bus específica desde todas las etapas de subida con modo
bus o zona paga (`1` o `3`). Agrega subidas, viajes y tarjetas por
`paradero-hora` y `zona-hora`, y las compara con buses/h programados en el mismo
grano.

```bash
python scripts/audits/build_operational_bus_demand_pressure.py --force
```

Las exposiciones por tarjeta usan demanda leave-one-card-out. Se materializan
dos ponderaciones: por subida observada y con igual peso por tarjeta-celda. Los
cocientes se denominan presión observada y se leen como subidas o tarjetas por
pasada bus programada equivalente. En zona, el denominador suma pasadas
bus-paradero y no vehículos únicos.

El script también escribe `operational_bus_unmapped_supply_stops.parquet`, que
cuantifica y localiza cuando es posible los paraderos de frecuencia excluidos
del denominador zonal. Ninguna presión mide ocupación, capacidad, congestión,
espera real ni el servicio efectivamente abordado.

## `audit_operational_bus_extremes_stability.py`

Contiene las funciones usadas por el bloque 13J del notebook para auditar las
variables bus antes de cruzarlas con QR/BIP:

- agrega las celdas con subidas observadas a
  `paradero x hora del día x semana x franja`;
- identifica extremos recurrentes dentro de cada semana-franja;
- compara rankings entre semanas adyacentes y la misma semana entre años;
- cuantifica cambios de quintil y sensibilidad raw versus percentil.

La escala paradero-hora está condicionada a celdas con demanda observada. No
representa todos los paraderos programados de la red. El módulo no materializa
nuevos datos: consume los artefactos construidos por los dos scripts
operacionales anteriores y entrega tablas compactas al notebook.

## Gradientes QR/BIP de las variables bus

`build_operational_bus_qr_gradient_exposure.py` materializa exposiciones por
`tarjeta x año x franja` para las familias de oferta, demanda bus específica y
relación demanda-oferta. Mantiene los numeradores de soporte para que el
resultado pooled pueda reconstruirse como promedio ponderado por viajes o
subidas:

```bash
python scripts/audits/build_operational_bus_qr_gradient_exposure.py --force
```

La salida es
`operational_bus_qr_gradient_exposure_year_franja.parquet`. El módulo
`audit_operational_bus_qr_gradients.py` construye quintiles de igual número de
tarjetas, calcula Q5-Q1 y monotonicidad, y estima intervalos agrupados por la
zona modal de origen. El bloque 13K del notebook compara percentiles
semana-franja como especificación principal, valores raw como sensibilidad y
robustez por año y franja.

La etiqueta `is_qr` es global a la tarjeta. Los cortes temporales caracterizan
la estabilidad de sus exposiciones operacionales y no deben leerse como estado
de adopción QR contemporáneo.

## `build_proposito_pk_bridge.py`

Reconstruye un puente entre los CSV raw de viajes, que conservan `proposito`, y los viajes procesados usados en modelación. El objetivo es habilitar una inferencia auditable de residencia por `id_tarjeta` sin reingestar todo el pipeline Bronze/Silver.

### Comando

```bash
python scripts/audits/build_proposito_pk_bridge.py --scope active
```

Para el frente ML intra-2025 (`W14 + W15 -> W17`):

```bash
python scripts/audits/build_proposito_pk_bridge.py --scope ml_2025
```

### Alcance actual

`--scope active` usa solo las semanas activas del frente econométrico:

- `2024-W17`
- `2025-W17`

`--scope ml_2025` usa las semanas del frente ML intra-2025:

- `2025-W14`
- `2025-W15`
- `2025-W17`

No procesa todos los CSV raw disponibles. En la ejecución validada, el script leyó `42.412.448` filas raw de esas semanas y enlazó `24.062.915` viajes procesados:

- `11.931.489` viajes procesados en `2024-W17`
- `12.131.426` viajes procesados en `2025-W17`

### Entradas

- CSV raw locales: `/Volumes/TOSHIBA EXT/Vicente/tesis-project/raw/raw_csv/viajes`
- Viajes procesados:
  - `tmp/viajes_con_te_calculado_2024-W17.parquet`
  - `tmp/viajes_con_te_calculado_2025-W17.parquet`

### Salidas principales

Los artefactos se escriben en `tmp/audits/proposito_residence/pk_bridge/`:

- `raw_viajes_proposito_pk_active.parquet`: raw compacto con `proposito`, zonas, `id_tarjeta`, `id_viaje`, timestamp normalizado y `pk_viaje` reconstruida.
- `processed_trip_proposito_bridge_active.parquet`: viajes procesados enlazados con `proposito`.
- `user_home_candidates_active.parquet`: candidatos de residencia por `id_tarjeta`, con `zona_hogar`, conteos, proporción modal y `home_confidence`.
- `bridge_join_diagnostics.csv`: cobertura del enlace y chequeos de consistencia.
- `home_confidence_distribution.csv`: distribución de confianza residencial.

Para otros scopes se usa el mismo patrón con sufijo, por ejemplo:

- `raw_viajes_proposito_pk_ml_2025.parquet`
- `processed_trip_proposito_bridge_ml_2025.parquet`
- `user_home_candidates_ml_2025.parquet`
- `bridge_join_diagnostics_ml_2025.csv`
- `home_confidence_distribution_ml_2025.csv`

### Regla de residencia

`zona_hogar` se define como la moda de `zona_fin_viaje` entre viajes con `proposito_norm == "HOGAR"` para cada `id_tarjeta`.

La confianza se clasifica como:

- `alta`: una sola zona hogar observada, o zona modal con participación `>= 0.80`, sin empate.
- `media`: zona modal con participación `>= 0.60`, sin empate.
- `baja`: empate o baja concentración modal.

### Validaciones

La ejecución validada obtuvo:

- `100%` de match entre viajes procesados y raw/proposito para `2024-W17` y `2025-W17`.
- `0` inconsistencias en `id_tarjeta`.
- `0` inconsistencias en `id_viaje`.
- Drift menor entre zonas raw y procesadas, guardado en `bridge_zone_mismatches_sample_*.csv`.

Nota técnica: la `pk_viaje` reconstruida con la fórmula documentada no coincide con la `pk_viaje` histórica ya materializada, probablemente por diferencia de versión o semántica del hash de Polars. Por eso el script conserva la `pk_viaje` procesada, pero realiza el enlace por llave natural estable: `id_tarjeta`, `id_viaje`, `ts_inicio_min` y `semana_iso`.

### Ejecución validada para ML intra-2025

Comando validado:

```bash
python scripts/audits/build_proposito_pk_bridge.py --scope ml_2025
```

El script leyó `61.458.133` filas raw de `2025-W14`, `2025-W15` y `2025-W17`, y enlazó `34.653.211` viajes procesados con `100%` de match por llave natural:

- `2025-W14`: `10.276.858 / 10.276.858`.
- `2025-W15`: `12.244.927 / 12.244.927`.
- `2025-W17`: `12.131.426 / 12.131.426`.

Validaciones:

- `0` inconsistencias en `id_tarjeta`.
- `0` inconsistencias en `id_viaje`.
- Drift de zonas raw/procesadas bajo y auditado en `bridge_zone_mismatches_sample_ml_2025_*.csv`.

Candidatos de residencia `ml_2025`:

- total tarjetas con candidato hogar: `3.275.630`.
- confianza `alta`: `2.239.973` tarjetas.
- confianza `media`: `445.005` tarjetas.
- confianza `baja`: `590.652` tarjetas.

## `audit_commute_home_vs_proposito.py`

Audita una definición alternativa de zona residencial basada en patrón AM/PM de
viajes y la compara contra `zona_hogar` inferida desde `proposito_norm == "HOGAR"`.
Esto permite testear la observación metodológica de que `proposito` podría estar
estimado indirectamente por permanencia y no ser una señal independiente perfecta de
residencia.

### Comando

Para el frente ML intra-2025:

```bash
python scripts/audits/audit_commute_home_vs_proposito.py --scope ml_2025
```

Para el frente econométrico interanual:

```bash
python scripts/audits/audit_commute_home_vs_proposito.py --scope active
```

Parámetros horarios por defecto:

- mañana: `05:00-12:00`, usando la moda de `zona_inicio_viaje`;
- tarde: `15:00-22:00`, usando la moda de `zona_fin_viaje`.

Opcionalmente se puede restringir a lunes-viernes:

```bash
python scripts/audits/audit_commute_home_vs_proposito.py --scope ml_2025 --weekday-only
```

### Regla alternativa

Para cada `id_tarjeta`, el script calcula:

- `am_origin_zone`: zona de origen más frecuente en viajes de la mañana;
- `pm_dest_zone`: zona de destino más frecuente en viajes de la tarde;
- `commute_zona_hogar_consensus`: zona residencial solo si `am_origin_zone == pm_dest_zone`;
- `commute_zona_hogar_modal`: moda combinada de eventos tipo hogar
  (`origen AM` + `destino PM`).

La comparación principal contra `zona_hogar` actual se reporta tanto para la moda
combinada como para el consenso estricto AM=PM.

### Salidas

Los artefactos se escriben en `tmp/audits/proposito_residence/commute_home/`:

- `commute_home_candidates_<scope>.parquet`: candidatos AM/PM por tarjeta.
- `commute_vs_proposito_home_<scope>.parquet`: comparación tarjeta a tarjeta contra
  `user_home_candidates_<scope>.parquet`.
- `commute_vs_proposito_summary_<scope>.csv`: cobertura y tasas globales de
  coincidencia.
- `commute_vs_proposito_by_home_confidence_<scope>.csv`: coincidencia por confianza
  de la residencia basada en `proposito`.
- `commute_vs_proposito_by_commute_confidence_<scope>.csv`: coincidencia por
  confianza del candidato AM/PM.
- `commute_vs_proposito_by_confidence_cross_<scope>.csv`: cruce de ambas
  confianzas.
- `commute_vs_proposito_mismatch_sample_<scope>.csv`: muestra de discrepancias.
- `commute_vs_proposito_zone_pairs_top_<scope>.csv`: pares de zonas
  `proposito` vs AM/PM más frecuentes.

Si se usan ventanas horarias no estándar o `--weekday-only`, el sufijo del archivo
incluye la configuración para no sobreescribir la corrida base.

## `build_residence_model_sample.py`

Construye una muestra model-ready separada que conserva identificadores de viaje/usuario, agrega residencia inferida y añade controles sociodemográficos por `zona_hogar`.

### Comando

```bash
python scripts/audits/build_residence_model_sample.py --sample-tag sample2pct
# o, para una muestra mayor antes de filtrar residencia:
python scripts/audits/build_residence_model_sample.py --sample-tag sample10pct
```

### Dependencia previa

Antes debe existir el artefacto de residencia:

```bash
python scripts/audits/build_proposito_pk_bridge.py --scope active
```

### Salida principal

```text
03_models/artifacts/interannual_enriched/
  pooled_2024_2025-estimation-sample2pct-residence-censo4-micro-osm-eod2012.parquet
```

La muestra conserva las columnas model-ready actuales por origen y agrega:

- `pk_viaje`, `id_tarjeta`, `id_viaje`, `tiempo_inicio_viaje`;
- `zona_hogar`, métricas de candidato hogar y `home_confidence`;
- controles residenciales con prefijo `res_`, por ejemplo `res_share_cine18_universitaria_o_mas_micro_z` y `res_eod2012_share_hogares_de_income_proxy_z`.
- banderas `res_censo_zone_imputed` y `res_eod_zone_imputed`, que identifican viajes cuya `zona_hogar` no existe en el artefacto zonal y por tanto recibió medianas zonales para controles residenciales.

Las variables OSM, oferta/demanda, macrozona y tiempos permanecen asociadas al origen/contexto del viaje.

### Ejecución validada

Para `sample2pct`, la ejecución validada produjo:

- `466.636` filas;
- `466.636` `pk_viaje` únicos;
- `423.034` tarjetas;
- `446.811` filas con `zona_hogar`;
- `283.810` filas con residencia de confianza `alta`;
- `77.433` filas con confianza `media`;
- `85.568` filas con confianza `baja`.
- `274` filas con controles residenciales Censo/EOD imputados por zona hogar faltante;
- `0` filas con `zona_hogar` válida y controles residenciales faltantes.

Para `sample10pct`, la ejecución validada produjo:

- `1.866.556` filas;
- `1.866.556` `pk_viaje` únicos;
- `1.322.123` tarjetas;
- `1.786.960` filas con `zona_hogar`;
- `1.134.502` filas con residencia de confianza `alta`;
- `307.663` filas con confianza `media`;
- `344.795` filas con confianza `baja`.
- `1.201` filas con controles residenciales Censo/EOD imputados por zona hogar faltante;
- `0` filas con `zona_hogar` válida y controles residenciales faltantes.

En `sample10pct`, algunos artefactos zonales Censo/OSM existentes eran anteriores al set actual de variables. El script no completa desde `sample2pct`: re-materializa los artefactos zonales del `sample_tag` desde las fuentes full. Para Censo, combina `censo2024_microdata_zona777_model_ready.parquet` con `censo2024_zona777_agg_final.parquet` cuando faltan variables crudas como edad, mujeres, inmigración, discapacidad o asistencia parvularia. Para OSM, re-estandariza desde `osm_zona777_model_ready.parquet`. EOD se crea desde su fuente full si no existe.

Diagnósticos:

- `tmp/audits/proposito_residence/pk_bridge/residence_model_sample_summary_sample2pct.csv`
- `tmp/audits/proposito_residence/pk_bridge/residence_model_sample_choice_by_confidence_sample2pct.csv`
- `tmp/audits/proposito_residence/pk_bridge/residence_model_sample_summary_sample10pct.csv`
- `tmp/audits/proposito_residence/pk_bridge/residence_model_sample_choice_by_confidence_sample10pct.csv`

## `audit_residence_origin_model_inputs.py`

Audita si las variables sociodemográficas medidas en `zona_inicio_viaje` son comparables con sus equivalentes residenciales `res_*`. El objetivo es decidir qué variables deben entrar al modelo por origen y cuáles por residencia antes de estimar sensibilidades.

### Comando

```bash
python scripts/audits/audit_residence_origin_model_inputs.py --sample-tag sample10pct
```

### Salidas

Los CSV se escriben en `tmp/audits/proposito_residence/model_input_audit/<sample-tag>/`:

- `choice_by_home_confidence.csv`: composición de elección por calidad de residencia.
- `origin_vs_residence_variable_comparison.csv`: correlaciones origen-residencia, diferencias absolutas y proporción de diferencias mayores a 0,5 o 1 desviación estándar.
- `origin_vs_residence_means_by_choice.csv`: medias de variables de origen y residencia por alternativa elegida.
- `residence_zone_imputation_summary.csv`: zonas hogar imputadas por falta de fila Censo/EOD.

### Lectura validada para `sample10pct`

- La distribución de elección cambia poco al filtrar residencia: en confianza `alta`, `QR_RED` representa `2,65%` y `QR_OTHER` `12,65%`.
- Origen y residencia no son equivalentes para variables sociodemográficas: en confianza `alta`, las correlaciones origen-residencia están aproximadamente entre `0,35` y `0,50`.
- Las mayores diferencias promedio aparecen en inmigración, educación universitaria, asistencia parvularia, edad e ingreso proxy.
- Para `QR_RED` con residencia `alta`, educación universitaria sigue alta en residencia (`1,03` desviaciones estándar), pero menor que la medida por origen (`1,26`), lo que refuerza la necesidad de separar ambas lecturas.

## `compare_origin_residence_mnl_params.py`

Compara los parámetros estimados del MNL parsimonioso anterior, con variables sociodemográficas medidas en zona de origen, contra la sensibilidad MNL parsimoniosa con residencia de confianza `alta`.

### Comando

```bash
python scripts/audits/compare_origin_residence_mnl_params.py
```

### Modelos comparados

- Origen: `mnl_joint_current_main_mujeres_parv_plus_eod_de_income_proxy_macro_parsimonious_plus_prom_edad`
- Origen filtrado `home_alta`, si ya fue estimado: `mnl_origin_home_alta_parsimonious`
- Residencia: `mnl_residence_home_alta_parsimonious`

### Salidas

Los CSV se escriben en `tmp/audits/proposito_residence/parameter_comparison/sample2pct/`:

- `origin_vs_home_alta_parsimonious_new_variables.csv`: comparación variable a variable para controles sociodemográficos, OSM y macrozonas.
- `origin_vs_home_alta_parsimonious_base_variables.csv`: comparación para constantes, franjas, oferta/demanda y atributos de viaje.
- `origin_vs_home_alta_parsimonious_change_summary.csv`: conteo de cambios de signo y significancia por grupo de variables y alternativa.
- `origin_full_vs_home_alta_origin_parsimonious_*`: A vs B, solo si `mnl_origin_home_alta_parsimonious` ya existe.
- `home_alta_origin_vs_home_alta_residence_parsimonious_*`: B vs C, solo si `mnl_origin_home_alta_parsimonious` ya existe.
- `abc_model_summary_key_variables.csv`: resumen A/B/C con ajuste y variables clave.
- `abc_model_summary_key_variables.md`: version legible del resumen A/B/C.
- `README.md`: lectura metodológica de la comparación y validación pendiente.

La comparación usa `BIP` como base y reporta cambios para `QR_RED` y `QR_OTHER`: beta de origen, beta de residencia, delta, p-values, significancia, cambios de signo y pérdida/ganancia de significancia al 5%.

### Cuidado metodológico

La comparación origen vs `home_alta` es una sensibilidad válida, pero no aísla un único cambio. Al mismo tiempo cambia la medición territorial de variables sociodemográficas y cambia la muestra al filtrar usuarios con residencia de confianza alta. Para separar efectos, queda pendiente estimar un modelo intermedio: parsimonious anterior restringido a `home_alta`, manteniendo sociodemográficas por origen.

## `build_user_sample_model_artifact.py`

Construye una sensibilidad de diseño muestral por usuario desde un artefacto residencial model-ready existente. En vez de muestrear viajes, selecciona `id_tarjeta` con semilla fija y conserva todos sus viajes disponibles en la muestra fuente.

### Comando

```bash
python scripts/audits/build_user_sample_model_artifact.py \
  --user-sample-tag user20pct \
  --source-sample-tag sample10pct
```

### Entradas

```text
03_models/artifacts/interannual_enriched/
  pooled_2024_2025-estimation-sample10pct-residence-censo4-micro-osm-eod2012.parquet
```

### Salidas

```text
03_models/artifacts/interannual_enriched/
  pooled_2024_2025-estimation-user5pct-from-sample10pct-residence-censo4-micro-osm-eod2012.parquet
  pooled_2024_2025-estimation-user5pct-from-sample10pct-residence-home-alta-censo4-micro-osm-eod2012.parquet
  pooled_2024_2025-estimation-user10pct-from-sample10pct-residence-censo4-micro-osm-eod2012.parquet
  pooled_2024_2025-estimation-user10pct-from-sample10pct-residence-home-alta-censo4-micro-osm-eod2012.parquet
  pooled_2024_2025-estimation-user20pct-from-sample10pct-residence-censo4-micro-osm-eod2012.parquet
  pooled_2024_2025-estimation-user20pct-from-sample10pct-residence-home-alta-censo4-micro-osm-eod2012.parquet
```

Diagnósticos:

```text
tmp/audits/proposito_residence/user_sample/user5pct-from-sample10pct/
  sample_summary.csv
  choice_summary.csv
  home_confidence_summary.csv
  macrozone_summary.csv
tmp/audits/proposito_residence/user_sample/user10pct-from-sample10pct/
  sample_summary.csv
  choice_summary.csv
  home_confidence_summary.csv
  macrozone_summary.csv
tmp/audits/proposito_residence/user_sample/user20pct-from-sample10pct/
  sample_summary.csv
  choice_summary.csv
  home_confidence_summary.csv
  macrozone_summary.csv
```

### Ejecución validada

Desde `sample10pct`, `user5pct` seleccionó `66.106` tarjetas (`5,00%`) y produjo:

- `93.386` viajes en la muestra por usuario completa;
- `56.895` viajes en la submuestra `home_alta`;
- `40.733` tarjetas en `home_alta`;
- `pk_viaje` único en todas las filas;
- composición de alternativas casi idéntica a la fuente: `QR_RED` alrededor de `2,6%` y `QR_OTHER` alrededor de `12,8%`.

`user10pct` seleccionó `132.212` tarjetas (`10,00%`) y produjo:

- `186.343` viajes en la muestra por usuario completa;
- `113.409` viajes en la submuestra `home_alta`;
- `81.630` tarjetas en `home_alta`;
- `pk_viaje` único en todas las filas;
- composición de alternativas casi idéntica a la fuente: en `home_alta`, `BIP` `84,65%`, `QR_RED` `2,69%`, `QR_OTHER` `12,67%`.

`user20pct` seleccionó `264.424` tarjetas (`20,00%`) y produjo:

- `373.162` viajes en la muestra por usuario completa;
- `226.476` viajes en la submuestra `home_alta`;
- `162.765` tarjetas en `home_alta`;
- `pk_viaje` único en todas las filas;
- composición de alternativas casi idéntica a la fuente: en `home_alta`, `BIP` `84,62%`, `QR_RED` `2,72%`, `QR_OTHER` `12,66%`.

`user20pct` queda como default operativo del notebook `03_models/17b_user_sample_residence_sensitivity.qmd`, porque produce una muestra `home_alta` mas comparable al modelo por viaje (`226k` vs `280k` filas) sin cambiar la especificacion de utilidad.

### Resultado MNL `user20pct`

El modelo `mnl_residence_home_alta_user20pct_from_sample10pct_parsimonious` converge correctamente:

- muestra: `226.476` viajes;
- parametros: `66`;
- `ll_final`: `-110.864,8`;
- `ll_per_obs`: `-0,489521`;
- gradiente relativo YAML: `4,3e-06`;
- algoritmo: Newton with trust region.

Esta estimacion se documenta como sensibilidad de muestreo por usuario, no como reemplazo automatico del modelo principal por residencia. La especificacion principal sigue siendo el MNL residencial por viaje, salvo decision posterior del profesor.

Lectura de robustez:

- `macro_oriente` para `QR_RED` sigue positivo y significativo.
- educacion universitaria residencial sigue positiva fuerte para `QR_RED` y `QR_OTHER`.
- discapacidad residencial sigue positiva para `QR_OTHER` y negativa para `QR_RED`.
- edad residencial sigue negativa y robusta para `QR_OTHER`, pero no es robusta para `QR_RED`.
- `T_ESPERA_INI` sigue negativo y significativo para todas las alternativas.
- ingreso proxy, inmigrantes, mujeres, demanda/oferta y `T_VEH` son mas sensibles al diseno muestral y deben interpretarse como controles o senales secundarias.
