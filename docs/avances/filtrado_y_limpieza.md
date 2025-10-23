
## ## Documentación: Proceso de Limpieza y Detección de Anomalías en Datos de Viajes

**Autor:** Juan Vicente Onetto Romero
**Fecha:** 23 de Octubre de 2025
[cite_start]**Basado en:** Informe "Cálculo de indicadores de calidad de servicio..." (C. Núñez, 2015) [cite: 223-2176] y notebooks `02_data_quality.qmd`, `03_feature_engineering.qmd`.

---
### ### 1. Objetivo General 🎯

[cite_start]El objetivo de este proceso es limpiar los datos brutos de viajes (`viajes_enriquecidos`) y aplicar filtros para identificar y marcar viajes anómalos, basándose en criterios de calidad de datos fundamentales y en las reglas de anomalías comportamentales definidas por Núñez (2015) [cite: 223-2176]. El resultado final son dos datasets: uno con todos los viajes y flags de anomalía (`viajes_con_indicadores`) y otro que contiene únicamente los viajes considerados válidos (`viajes_filtrados`).

---
### ### 2. Fase 1: Análisis de Calidad y Limpieza Básica (`02_data_quality.qmd`, `batch_process_data_quality.py`) 🔬🧹

[cite_start]Esta fase se centra en analizar la integridad de los datos de entrada (`viajes_enriquecidos`) [cite: 56] y aplicar filtros básicos para eliminar registros lógicamente inválidos, antes de evaluar anomalías comportamentales.

**2.1. Análisis Realizados (Sin Filtrar):**

* [cite_start]**Análisis de Tiempos (Sección 3) [cite: 73-85]:**
    * [cite_start]**Unidades:** Se verificó que, a pesar de la documentación inicial, todas las columnas de tiempo (`tv*`, `tc*`, `te*`, `entrada`, `egreso`, `tviaje2`) están efectivamente en **segundos**[cite: 73].
    * [cite_start]**Cálculo de Componentes:** Se crearon columnas sumando los componentes individuales para obtener tiempos totales por categoría: `t_vehiculo_total_seg`, `t_espera_total_seg`, `t_caminata_total_seg`, `t_acceso_egreso_total_seg` [cite: 75-77].
    * **Consistencia `tviaje2`:** Se recalculó el tiempo total (`t_total_calculado_seg`) sumando los componentes anteriores y se comparó con `tviaje2`. [cite_start]Se encontró que **`tviaje2` es consistente** con la suma de sus partes (0.00% de inconsistencias) [cite: 77-79, 84].
    * [cite_start]**Tiempos Inválidos:** Se identificaron viajes con `t_vehiculo_total_seg <= 0` o `t_total_calculado_seg <= 0` [cite: 79-80]. Estos representan datos corruptos o imposibles.
    * [cite_start]**Verificación Correcciones Metro (Sección 7) [cite: 118-125][cite_start]:** Se realizó una verificación indirecta comparando los tiempos de caminata (`tc1`) en transbordos desde/hacia Metro con los valores esperados si las correcciones del informe (Sección 4.1.1 [cite: 950-965]) estuvieran aplicadas. [cite_start]Los resultados (ej. `tc1` promedio de ~249s para Bus->Metro) **sugieren fuertemente que los tiempos de acceso/egreso de Metro ya están incorporados** en los datos de entrada [cite: 119-125].

* [cite_start]**Análisis de Distancias (Sección 4 y 6.1) [cite: 86-105]:**
    * [cite_start]**Cálculo de Componentes:** Se crearon `d_vehiculo_ruta_total_m` (suma de `dveh_ruta*`) y `d_caminata_total_m` (suma de `dt*`) [cite: 89-91].
    * [cite_start]**Consistencia `dveh_rutafinal` vs Componentes:** Se validó que `dveh_rutafinal` es **altamente consistente** (solo 0.09% de inconsistencias) con la suma de los componentes `dveh_ruta*` [cite: 91-93].
    * [cite_start]**Consistencia `distancia_ruta` vs Componentes:** Se validó que `distancia_ruta` **NO es consistente** (86.78% de inconsistencias) con la suma de `dveh_ruta*`[cite: 93].
    * **Verificación `distancia_ruta` vs `dveh_rutafinal` (Sección 6.1):** Una comparación directa entre `distancia_ruta` y `dveh_rutafinal` reveló **inconsistencias masivas** (82.41% de los viajes con diferencias > 1km), con diferencias grandes y erráticas (positivas y negativas). Los ejemplos, especialmente en viajes de 1 etapa, mostraron que `dveh_rutafinal` a menudo tenía valores irrealmente altos en comparación con `distancia_ruta`.
    * **Conclusión sobre Distancias:** Se concluyó que `dveh_rutafinal` (y sus componentes `dveh_ruta*`) **parecen ser incorrectos o deprecados**. Por lo tanto, se decidió **adoptar `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta (DR) del vehículo**, documentando esta decisión y la incertidumbre asociada.
    * [cite_start]**Consistencia `dveh_eucfinal`:** Se validó que `dveh_eucfinal` es **altamente consistente** con la suma de los componentes `dveh_euc*` [cite: 94-96].
    * [cite_start]**Valores Inválidos:** Se analizaron nulos, ceros y **valores negativos** en las columnas clave (`distancia_ruta`, `distancia_eucl`, `dveh_rutafinal`, `dveh_eucfinal`), confirmando la necesidad de filtrar valores no positivos [cite: 97-103].

* [cite_start]**Análisis de Paraderos (Sección 5) [cite: 105-118]:**
    * [cite_start]Se cuantificó la presencia de **valores nulos** en `paradero_inicio_viaje` y `paradero_fin_viaje` [cite: 105-107].
    * [cite_start]Se estableció la relación entre paraderos nulos y la ausencia de `distancia_eucl` [cite: 112-114].

* [cite_start]**Validación `tipo_transporte == 3` (Sección 2.2) [cite: 66-73]:**
    * [cite_start]Se cruzaron los paraderos de etapas con `tipo_transporte == 3` con un archivo maestro externo de paraderos [cite: 66-70].
    * [cite_start]Se encontró una **tasa de confirmación superior al 90%** [cite: 70-72], validando con alta probabilidad que **`tipo_transporte == 3` corresponde a "Zona Paga"** en estos datos.

**2.2. [cite_start]Filtros Básicos Aplicados (Sección 6 del Notebook / `batch_process_data_quality.py`) [cite: 126-162]:**

Se aplica la siguiente secuencia de filtros para generar `viajes_limpios`:

1.  [cite_start]**Filtrado por Tiempos:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple [cite: 127-129]:
    * `t_vehiculo_total_seg <= 0` (Tiempo en vehículo debe ser positivo).
    * `t_total_calculado_seg <= 0` (Tiempo total del viaje debe ser positivo).
2.  [cite_start]**Filtrado por Paraderos:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple [cite: 129-133]:
    * `paradero_inicio_viaje IS NULL`.
    * `paradero_fin_viaje IS NULL`.
3.  [cite_start]**Imputación y Filtrado por Distancias:** Se aplica la siguiente lógica [cite: 133-147]:
    * [cite_start]**Imputar `dveh_eucfinal`:** Si `dveh_eucfinal` es nulo, se reemplaza con `d_vehiculo_eucl_total_m` (suma de `dveh_euc*`) [cite: 138-139].
    * [cite_start]**Filtrar:** Se eliminan viajes si CUALQUIERA de las siguientes condiciones se cumple *después* de la imputación [cite: 140-144]:
        * `distancia_ruta IS NULL` o `distancia_ruta <= 0` (Se usa `distancia_ruta` como DR principal).
        * `distancia_eucl IS NULL` o `distancia_eucl <= 0`.
        * `dveh_eucfinal` (imputado) `IS NULL` o `dveh_eucfinal <= 0`.
    * **Nota:** `dveh_rutafinal` **no se usa** para filtrar ni se imputa, ya que se consideró poco confiable.

**2.3. Output:**

* [cite_start]`viajes_limpios`: Dataset que contiene solo los viajes que pasan los filtros básicos de calidad, con las columnas de tiempo validadas y `distancia_ruta` seleccionada como la métrica principal de distancia en ruta [cite: 164-165].

---
### ### 3. Fase 2: Feature Engineering y Detección de Anomalías (`03_feature_engineering.qmd`) 🔧🚩

[cite_start]Esta fase toma los datos limpios (`viajes_limpios`) [cite: 5][cite_start], calcula las métricas necesarias y aplica los filtros de anomalías comportamentales basados en el informe de Núñez[cite: 2].

**3.1. [cite_start]Feature Engineering (Sección 3) [cite: 14-17]:**

Se calculan las siguientes métricas clave, usando las columnas correctas identificadas en la Fase 1:

* **`velocidad_vehiculo_kmhr` (VR):** `distancia_ruta_m / tiempo_vehiculo_seg`. [cite_start]**Importante:** Se utiliza `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta del vehículo, según la conclusión de la Fase 1[cite: 15].
* **`velocidad_eucl_kmhr` (VE):** `distancia_euc_OD_m / tiempo_vehiculo_seg`. [cite_start]Usa la distancia euclidiana O-D (`distancia_eucl`) y el tiempo *solo en vehículo*, lo cual es correcto según el informe [cite: 16, 1360-1372].
* **`dr_de`:** `distancia_ruta_m / distancia_euc_OD_m`. [cite_start]Utiliza `distancia_ruta` como DR, consistente con la decisión anterior [cite: 15, 1164-1187].

**3.2. [cite_start]Filtros de Anomalías Aplicados (Sección 5) [cite: 24-35]:**

[cite_start]Se implementaron los siguientes criterios del informe de Núñez (Capítulo 4.2) [cite: 1124-1126], creando flags booleanos individuales (`anom_*`) y un flag general (`is_anomalo`):

* [cite_start]✅ **`anom_a1_od_viaje`, `anom_a1_od_etapa*`:** Verifica si el paradero de subida es igual al de bajada [cite: 24-25, 1140-1144]. *Justificación:* Indica viajes circulares o errores de estimación.
* [cite_start]✅ **`anom_b1_dr_min`:** Verifica si `distancia_ruta_m < 350`[cite: 25]. [cite_start]*Justificación:* Elimina viajes extremadamente cortos, usando `distancia_ruta` como la DR del vehículo [cite: 1154-1156].
* [cite_start]✅ **`anom_b2_de_max`:** Verifica si `distancia_euc_OD_m > 50000` (50 km) [cite: 25, 1157-1159]. *Justificación:* Elimina viajes con distancias euclidianas irrealmente largas.
* [cite_start]✅ **`anom_b3_dur_min`:** Verifica si `tiempo_total_seg < 35` [cite: 25, 1160-1163]. *Justificación:* Elimina viajes con duración total extremadamente corta.
* [cite_start]✅ **`anom_c1_vr_baja`:** Verifica si `velocidad_vehiculo_kmhr < 4` [cite: 26, 1140-1142]. *Justificación:* Elimina viajes donde la velocidad *en vehículo* (calculada con `distancia_ruta`) es menor a una caminata.
* [cite_start]✅ **`anom_c2_ve_alta`:** Verifica si `velocidad_eucl_kmhr > 70` [cite: 26, 1143-1145, 1170]. *Justificación:* Detecta velocidades promedio en línea recta excesivamente altas.
* [cite_start]✅ **`anom_c3_vr_alta_dr_corto`:** Verifica si `velocidad_vehiculo_kmhr > 60` Y `distancia_ruta_m < 5000`[cite: 26, 1170]. *Justificación:* Detecta velocidades altas anómalas en viajes cortos.
* [cite_start]✅ **`anom_c4_vr_alta_dr_largo`:** Verifica si `velocidad_vehiculo_kmhr > 70` Y `distancia_ruta_m >= 5000`[cite: 26, 1170]. *Justificación:* Detecta velocidades altas anómalas en viajes largos.

**3.3. Filtros del Informe NO Implementados:**

Los siguientes criterios de anomalía del informe **no fueron implementados** en esta versión:

* [cite_start]❌ **`4.2.2: Unidad de negocio repetida`** [cite: 1145-1151]
* [cite_start]❌ **`4.2.5: Relación DR/DE`** (Criterios complejos de Tabla 4.1) [cite: 1164-1187]
* [cite_start]❌ **`4.2.7: Viajes de 4 etapas`** [cite: 1171-1245]
* [cite_start]❌ **`4.2.8: Etapa redundante`** [cite: 1246-1267]
* [cite_start]❌ **`4.2.9: Ciclo en etapa intermedia`** [cite: 1268-1285]

**3.4. Outputs:**

* [cite_start]`viajes_con_indicadores`: Dataset `viajes_limpios` + columnas de indicadores (`dr_de`, velocidades) + flags de anomalías (`anom_*`, `is_anomalo`) [cite: 5, 52-53].
* [cite_start]`viajes_filtrados`: Subconjunto de `viajes_con_indicadores` donde `is_anomalo == False` [cite: 6, 53-54].

---
### ### 4. Resumen de Resultados Cuantitativos 📊

**4.1. Resultados de Limpieza Básica (Fase 1):**

*(Estos resultados provendrían de la ejecución del script `batch_process_data_quality.py` o la Sección 6 del notebook 02)*

* **Viajes Iniciales:** `X`
* **Filtrados por Tiempos:** `Y` (`Z%`)
* **Filtrados por Paraderos:** `A` (`B%`)
* **Filtrados por Distancias:** `C` (`D%`)
* **Total Filtrados (Básicos):** `T_basico` (`P_basico%`)
* **Viajes Finales (`viajes_limpios`):** `N_limpios` (`P_retenido%`)

*(Nota: Reemplaza X, Y, Z, A, B, C, D, T_basico, P_basico, N_limpios, P_retenido con los valores numéricos obtenidos al ejecutar el script/notebook)*

**4.2. Resultados de Detección de Anomalías (Fase 2):**

*(Basado en la imagen proporcionada de la Sección 5.1 del notebook 03)*

* **Total de Viajes Analizados (`viajes_limpios`):** 158,446,366 (calculado: 152,055,374 + 6,390,992)
* **Viajes Marcados como Anómalos (`is_anomalo == True`):** 6,390,992 (**4.03%**)
* **Viajes Válidos (`is_anomalo == False`, en `viajes_filtrados`):** 152,055,374 (**95.97%**)

* **Desglose por Filtro (Impacto Individual, ordenado):**
    * `anom_c4_vr_alta_dr_largo` (VR > 70 km/h, DR ≥ 5km): 5,142,943 (3.25%)
    * `anom_c2_ve_alta` (VE > 70 km/h): 3,723,974 (2.35%)
    * `anom_b1_dr_min` (Distancia ruta < 350m): 779,776 (0.49%)
    * `anom_c1_vr_baja` (VR < 4 km/h): 384,788 (0.24%)
    * `anom_c3_vr_alta_dr_corto` (VR > 60 km/h, DR < 5km): 184,317 (0.12%)
    * `anom_b3_dur_min` (Duración < 35 seg): 57,621 (0.04%)
    * `anom_a1_od_viaje` (O/D iguales viaje): 84 (0.00%)
    * Otros filtros (`anom_a1_od_etapa*`, `anom_b2_de_max`): 0 impacto (0.00%)

*(Nota: El total de anómalos (4.03%) es menor que la suma de los porcentajes individuales porque un viaje puede ser marcado por múltiples filtros)*.

---
### ### 5. Conclusión ✅

El proceso implementado realiza una limpieza fundamental de los datos, eliminando registros inválidos y validando la consistencia interna. Una **investigación detallada de las columnas de distancia** llevó a la conclusión de que `dveh_rutafinal` era probablemente incorrecta, y se decidió usar `distancia_ruta` como la mejor estimación disponible de la Distancia en Ruta del vehículo. [cite_start]Posteriormente, se aplicó un subconjunto significativo de los filtros de anomalías comportamentales propuestos por Núñez (2015) [cite: 223-2176], utilizando métricas calculadas correctamente basadas en esta decisión (especialmente las velocidades basadas en tiempo en vehículo y `distancia_ruta`). Se validó además que `tipo_transporte == 3` corresponde a Zonas Pagas.

El resultado es un dataset (`viajes_filtrados`) considerablemente más limpio y confiable, adecuado para análisis posteriores, aunque se debe tener en cuenta que aún no se han implementado todos los filtros de anomalías del informe (notablemente, los criterios DR/DE complejos) y existe una incertidumbre documentada sobre la precisión absoluta de `distancia_ruta` como distancia exclusiva del vehículo.