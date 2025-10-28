# Documentación: Proceso de Limpieza y Detección de Anomalías en Datos de Viajes

**Autor:** Juan Vicente Onetto Romero  
**Fecha:** 23 de Octubre de 2025  
**Basado en:** Informe de C. Núñez (2015) y notebooks 02_data_quality.qmd, 03_feature_engineering.qmd.

---

## 1. Objetivo General

El objetivo de este proceso es limpiar los datos brutos de viajes (`viajes_enriquecidos`) y aplicar filtros para identificar y marcar viajes anómalos, basándose en criterios de calidad de datos fundamentales y en las reglas de anomalías comportamentales definidas por Núñez (2015).

El resultado final son dos datasets: uno con todos los viajes y flags de anomalía (`viajes_con_indicadores`) y otro que contiene únicamente los viajes considerados válidos (`viajes_filtrados`).

---

## 2. Fase 1: Análisis de Calidad y Limpieza Básica

Esta fase se centra en analizar la integridad de los datos de entrada (`viajes_enriquecidos`) y aplicar filtros básicos para eliminar registros lógicamente inválidos, antes de evaluar anomalías comportamentales.

### 2.1. Análisis Realizados (Sin Filtrar)

#### Análisis de Tiempos (Sección 3)

- **Unidades:** Se verificó que, a pesar de la documentación inicial, todas las columnas de tiempo (`tv*`, `tc*`, `te*`, `entrada`, `egreso`, `tviaje2`) están efectivamente en **segundos**.
- **Cálculo de Componentes:** Se crearon columnas sumando los componentes individuales para obtener tiempos totales por categoría: `t_vehiculo_total_seg`, `t_espera_total_seg`, `t_caminata_total_seg`, `t_acceso_egreso_total_seg`.
- **Consistencia `tviaje2`:** Se recalculó el tiempo total (`t_total_calculado_seg`) sumando los componentes anteriores y se comparó con `tviaje2`. Se encontró que **`tviaje2` es consistente** con la suma de sus partes (0.00% de inconsistencias).
- **Tiempos Inválidos:** Se identificaron viajes con `t_vehiculo_total_seg <= 0` o `t_total_calculado_seg <= 0`. Estos representan datos corruptos o imposibles.

#### Análisis de Distancias (Sección 4 y 6.1)

- **Cálculo de Componentes:** Se crearon `d_vehiculo_ruta_total_m` (suma de `dveh_ruta*`) y `d_caminata_total_m` (suma de `dt*`).
- **Consistencia `dveh_rutafinal` vs Componentes:** Se validó que `dveh_rutafinal` es **altamente consistente** (solo 0.09% de inconsistencias) con la suma de los componentes `dveh_ruta*`.
- **Consistencia `distancia_ruta` vs Componentes:** Se validó que `distancia_ruta` **NO es consistente** (86.78% de inconsistencias) con la suma de `dveh_ruta*`.
- **Conclusión sobre Distancias:** Se concluyó que `dveh_rutafinal` (y sus componentes `dveh_ruta*`) **parecen ser incorrectos o deprecados**. Por lo tanto, se decidió **adoptar `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta (DR) del vehículo**.

### 2.2. Filtros Básicos Aplicados

Se aplica la siguiente secuencia de filtros para generar `viajes_limpios`:

1. **Filtrado por Tiempos:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple:
   - `t_vehiculo_total_seg <= 0` (Tiempo en vehículo debe ser positivo).
   - `t_total_calculado_seg <= 0` (Tiempo total del viaje debe ser positivo).

2. **Filtrado por Paraderos:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple:
   - `paradero_inicio_viaje IS NULL`.
   - `paradero_fin_viaje IS NULL`.

3. **Imputación y Filtrado por Distancias:** Se aplica la siguiente lógica:
   - **Imputar `dveh_eucfinal`:** Si `dveh_eucfinal` es nulo, se reemplaza con `d_vehiculo_eucl_total_m` (suma de `dveh_euc*`).
   - **Filtrar:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple *después* de la imputación:
     - `distancia_ruta IS NULL` o `distancia_ruta <= 0` (Se usa `distancia_ruta` como DR principal).
     - `distancia_eucl IS NULL` o `distancia_eucl <= 0`.
     - `dveh_eucfinal` (imputado) `IS NULL` o `dveh_eucfinal <= 0`.

### 2.3. Output

- `viajes_limpios`: Dataset que contiene solo los viajes que pasan los filtros básicos de calidad, con las columnas de tiempo validadas y `distancia_ruta` seleccionada como la métrica principal de distancia en ruta.

---

## 3. Fase 2: Feature Engineering y Detección de Anomalías

Esta fase toma los datos limpios (`viajes_limpios`), calcula las métricas necesarias y aplica los filtros de anomalías comportamentales basados en el informe de Núñez.

### 3.1. Feature Engineering (Sección 3)

Se calculan las siguientes métricas clave, usando las columnas correctas identificadas en la Fase 1:

- **`velocidad_vehiculo_kmhr` (VR):** `distancia_ruta_m / tiempo_vehiculo_seg`. **Importante:** Se utiliza `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta del vehículo, según la conclusión de la Fase 1.
- **`velocidad_eucl_kmhr` (VE):** `distancia_euc_OD_m / tiempo_vehiculo_seg`. Usa la distancia euclidiana O-D (`distancia_eucl`) y el tiempo *solo en vehículo*, lo cual es correcto según el informe.
- **`dr_de`:** `distancia_ruta_m / distancia_euc_OD_m`. Utiliza `distancia_ruta` como DR, consistente con la decisión anterior.

### 3.2. Filtros de Anomalías Aplicados (Sección 5)

Se implementaron los siguientes criterios del informe de Núñez (Capítulo 4.2), creando flags booleanos individuales (`anom_*`) y un flag general (`is_anomalo`):

- **`anom_a1_od_viaje`, `anom_a1_od_etapa*`:** Verifica si el paradero de subida es igual al de bajada. *Justificación:* Indica viajes circulares o errores de estimación.
- **`anom_b1_dr_min`:** Verifica si `distancia_ruta_m < 350`. *Justificación:* Elimina viajes extremadamente cortos, usando `distancia_ruta` como la DR del vehículo.
- **`anom_b2_de_max`:** Verifica si `distancia_euc_OD_m > 50000` (50 km). *Justificación:* Elimina viajes con distancias euclidianas irrealmente largas.
- **`anom_b3_dur_min`:** Verifica si `tiempo_total_seg < 35`. *Justificación:* Elimina viajes con duración total extremadamente corta.
- **`anom_c1_vr_baja`:** Verifica si `velocidad_vehiculo_kmhr < 4`. *Justificación:* Elimina viajes donde la velocidad *en vehículo* (calculada con `distancia_ruta`) es menor a una caminata.
- **`anom_c2_ve_alta`:** Verifica si `velocidad_eucl_kmhr > 70`. *Justificación:* Detecta velocidades promedio en línea recta excesivamente altas.
- **`anom_c3_vr_alta_dr_corto`:** Verifica si `velocidad_vehiculo_kmhr > 60` Y `distancia_ruta_m < 5000`. *Justificación:* Detecta velocidades altas anómalas en viajes cortos.
- **`anom_c4_vr_alta_dr_largo`:** Verifica si `velocidad_vehiculo_kmhr > 70` Y `distancia_ruta_m >= 5000`. *Justificación:* Detecta velocidades altas anómalas en viajes largos.

### 3.3. Outputs

- `viajes_con_indicadores`: Dataset `viajes_limpios` + columnas de indicadores (`dr_de`, velocidades) + flags de anomalías (`anom_*`, `is_anomalo`).
- `viajes_filtrados`: Subconjunto de `viajes_con_indicadores` donde `is_anomalo == False`.

---

## 4. Resumen de Resultados Cuantitativos

### 4.1. Resultados de Limpieza Básica (Fase 1)

*(Estos resultados provendrían de la ejecución del script `batch_process_data_quality.py` o la Sección 6 del notebook 02)*

- **Viajes Iniciales:** 268,765,696
- **Filtrados por Tiempos:** 108,338,569 (40.31%)
- **Filtrados por Paraderos:** 42,636 (0.02%)
- **Filtrados por Distancias:** 1,938,125 (0.72%)
- **Viajes Finales (`viajes_limpios`):** 158,446,366 (58.96%)

**Nota:** Los filtros son acumulativos - un viaje puede ser filtrado por multiples criterios simultanemente. Los porcentajes muestran el impacto de cada filtro sobre el total inicial.

**Ubicación de salida:**
gs: //tesis-vonetto-datalake/lake/silver/viajes_limpios/iso_year=YYYY/iso_week=ww/data-0.parquet

### 4.2. Resultados de Detección de Anomalías (Fase 2)

*(Basado en la imagen proporcionada de la Sección 5.1 del notebook 03)*

- **Total de Viajes Analizados (`viajes_limpios`):** 158,446,366 (calculado: 152,055,374 + 6,390,992)
- **Viajes Marcados como Anómalos (`is_anomalo == True`):** 6,390,992 (**4.03%**)
- **Viajes Válidos (`is_anomalo == False`, en `viajes_filtrados`):** 152,055,374 (**95.97%**)

#### Desglose por Filtro (Impacto Individual, ordenado):

- `anom_c4_vr_alta_dr_largo` (VR > 70 km/h, DR ≥ 5km): 5,142,943 (3.25%)
- `anom_c2_ve_alta` (VE > 70 km/h): 3,723,974 (2.35%)
- `anom_b1_dr_min` (Distancia ruta < 350m): 779,776 (0.49%)
- `anom_c1_vr_baja` (VR < 4 km/h): 384,788 (0.24%)
- `anom_c3_vr_alta_dr_corto` (VR > 60 km/h, DR < 5km): 184,317 (0.12%)
- `anom_b3_dur_min` (Duración < 35 seg): 57,621 (0.04%)
- `anom_a1_od_viaje` (O/D iguales viaje): 84 (0.00%)
- Otros filtros (`anom_a1_od_etapa*`, `anom_b2_de_max`): 0 impacto (0.00%)

*(Nota: El total de anómalos (4.03%) es menor que la suma de los porcentajes individuales porque un viaje puede ser marcado por múltiples filtros)*.

**Ubicación de salida:**
gs: //tesis-vonetto-datalake/lake/silver/viajes_con_indicadores/iso_year=YYYY/iso_week=ww/data-0.parquet
gs: //tesis-vonetto-datalake/lake/silver/viajes_filtrados/iso_year=YYYY/iso_week=ww/data-0.parquet

---

## 5. Conclusión

El proceso implementado realiza una limpieza fundamental de los datos, eliminando registros inválidos y validando la consistencia interna. Una **investigación detallada de las columnas de distancia** llevó a la conclusión de que `dveh_rutafinal` era probablemente incorrecta, y se decidió usar `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta del vehículo. Posteriormente, se aplicó un subconjunto significativo de los filtros de anomalías comportamentales propuestos por Núñez (2015), utilizando métricas calculadas correctamente basadas en esta decisión (especialmente las velocidades basadas en tiempo en vehículo y `distancia_ruta`). Se validó además que `tipo_transporte == 3` corresponde a Zonas Pagas.

El resultado es un dataset (`viajes_filtrados`) considerablemente más limpio y confiable, adecuado para análisis posteriores, aunque se debe tener en cuenta que aún no se han implementado todos los filtros de anomalías del informe (notablemente, los criterios DR/DE complejos) y existe una incertidumbre documentada sobre la precisión absoluta de `distancia_ruta` como distancia exclusiva del vehículo.
