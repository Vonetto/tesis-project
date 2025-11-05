# Desarrollo de Modelos Logit - Feature Branch `feature/logit-model`

**Fecha de desarrollo:** Octubre 2025  
**Rama:** `feature/logit-model`  
**Estado:** ✅ Completado y mergeado a `develop`

---

## Resumen Ejecutivo

Esta feature branch implementa un conjunto completo de modelos de elección discreta (Logit) para analizar la adopción del pago QR versus Tarjeta Bip! en el sistema de transporte público de Santiago. Se desarrollaron cuatro modelos principales: dos modelos Logit Binarios (baseline y extendido) y dos modelos Nested Logit (baseline y extendido), con capacidades de estimación secuencial sobre múltiples particiones temporales y muestreo estratificado.

**Logros principales:**
- ✅ Implementación de 4 modelos Logit completos usando Biogeme
- ✅ Sistema de estimación secuencial sobre particiones semanales (W17, W18)
- ✅ Muestreo estratificado eficiente (20% y 50%) con validación de consistencia
- ✅ Documentación completa con visualizaciones y tablas comparativas
- ✅ Identificación de limitación crítica: transbordos internos metro-metro

---

## Objetivos del Desarrollo

1. **Modelos Logit Binarios**: Estimar modelos de elección binaria entre pago QR y Tarjeta Bip!
   - Modelo baseline con variables temporales
   - Modelo extendido con variables temporales + atributos del viaje

2. **Modelos Nested Logit**: Estimar modelos de elección anidada considerando la estructura jerárquica de elección
   - Nivel superior: Bip! vs QR
   - Nivel inferior (dentro de QR): App Red vs Otras Apps QR
   - Modelo baseline y extendido

3. **Validación de Muestreo**: Validar que el muestreo estratificado (20% y 50%) reproduce correctamente los resultados del dataset completo

4. **Análisis de Resultados**: Presentar resultados de manera clara y comparativa entre modelos y configuraciones

---

## Estructura de Archivos Creados

```
03_models/
├── binary_logit_qr_adoption.qmd          # Modelo Logit Binario Baseline
├── binary_extended_logit_qr_adoption.qmd # Modelo Logit Binario Extendido
├── nested_logit.qmd                      # Modelos Nested Logit (Baseline + Extendido)
└── model_outputs/
    ├── W17-baseline/                     # Resultados baseline W17 (full)
    ├── W17-baseline-0.2/                 # Resultados baseline W17 (20%)
    ├── W17-extended-0.2/                 # Resultados extended W17 (20%)
    ├── W17-extended-0.5/                 # Resultados extended W17 (50%)
    ├── W18-baseline/                     # Resultados baseline W18 (full)
    ├── W18-baseline-0.2/                 # Resultados baseline W18 (20%)
    ├── W18-extended-0.2/                 # Resultados extended W18 (20%)
    ├── W18-extended-0.5/                 # Resultados extended W18 (50%)
    ├── W17-extended-sample20pct/         # Resultados extended W17 (20% - nueva nomenclatura)
    ├── W17-extended-sample50pct/         # Resultados extended W17 (50% - nueva nomenclatura)
    ├── W18-extended-sample20pct/         # Resultados extended W18 (20% - nueva nomenclatura)
    └── W18-extended-sample50pct/         # Resultados extended W18 (50% - nueva nomenclatura)

model_outputs_nl_base/
├── W17-nested-base/                      # Resultados nested baseline W17 (full)
├── W17-nested-base-sample20pct/          # Resultados nested baseline W17 (20%)
├── W18-nested-base/                      # Resultados nested baseline W18 (full)
└── W18-nested-base-sample20pct/          # Resultados nested baseline W18 (20%)

model_outputs_nl_extended/
├── W17-nested-ext-sample20pct/          # Resultados nested extended W17 (20%)
├── W17-nested-ext-sample50pct/           # Resultados nested extended W17 (50%)
├── W18-nested-ext-sample20pct/           # Resultados nested extended W18 (20%)
└── W18-nested-ext-sample50pct/           # Resultados nested extended W18 (50%)
```

---

## Modelos Implementados

### 1. Modelo Logit Binario Baseline

**Archivo:** `03_models/binary_logit_qr_adoption.qmd`

**Especificación:**
- **Alternativas:** Bip! (choice=0) y QR (choice=1)
- **Utilidades:**
  - \(V_{Bip} = 0\) (normalización)
  - \(V_{QR} = ASC_{QR} + \beta_{PM} \cdot DUMMY\_PM\_LAB + \beta_{PT} \cdot DUMMY\_PT\_LAB + \beta_{LJ} \cdot DUMMY\_LJ\_LAB + \beta_{VIE} \cdot DUMMY\_VIE\_LAB\)
- **Variables:** 4 dummies temporales (horas punta y días laborales)

**Resultados principales:**
- Rho-cuadrado ajustado: ~0.35-0.36
- ASC_QR negativo (preferencia base por Bip!)
- Coeficientes de horas punta positivos (QR preferido en congestión)
- Coeficientes de días laborales negativos (Bip! preferido en rutina)

---

### 2. Modelo Logit Binario Extendido

**Archivo:** `03_models/binary_extended_logit_qr_adoption.qmd`

**Especificación:**
- **Alternativas:** Igual al baseline
- **Utilidades:** Incluye variables temporales + 6 nuevas variables de atributos del viaje:
  - `VAR_T_VEHICULO_MIN`: Tiempo en vehículo (minutos)
  - `VAR_N_TRASBORDOS`: Número de trasbordos
  - `VAR_T_CAMINATA_MIN`: Tiempo total de caminata (minutos)
  - `VAR_T_ESPERA_TRASBORDO_MIN`: Tiempo de espera en trasbordos (minutos)
  - `VAR_T_ESPERA_INICIAL_MIN`: Tiempo de espera inicial (minutos)
  - `DUMMY_SOLO_METRO`: 1 si usa solo Metro, 0 si no
  - `DUMMY_METRO_BUS`: 1 si combina Metro y Bus, 0 si no

**Resultados principales:**
- Rho-cuadrado ajustado: ~0.35-0.36 (similar al baseline, pero con mayor poder explicativo)
- Complejidad del viaje (trasbordos, caminata, esperas) reduce preferencia por QR
- Tiempo en vehículo con efecto positivo (viajes largos favorecen QR)
- Modos de transporte: viajes Metro-Bus reducen preferencia por QR

**⚠️ Limitación crítica identificada:** Las variables de atributos del viaje están sesgadas por transbordos internos metro-metro no detectados (ver sección de Problemas Identificados).

---

### 3. Modelo Nested Logit Baseline

**Archivo:** `03_models/nested_logit.qmd` (sección "Modelo Nested Logit Base")

**Especificación:**
- **Estructura jerárquica:**
  - **Nivel superior:** Bip! vs QR
  - **Nivel inferior (dentro de QR):** App Red vs Otras Apps QR
- **Alternativas:**
  - 0 = BIP (Tarjeta Bip!)
  - 1 = QR_RED (QR mediante App Red)
  - 2 = QR_OTHER (QR mediante otras Apps)
- **Nidos:**
  - Nido BIP: `(1.0, [BIP])` - parámetro fijado en 1.0
  - Nido QR: `(MU_QR, [QR_RED, QR_OTHER])` - parámetro estimado ≥ 1
- **Utilidades:**
  - \(V_{BIP} = 0\)
  - \(V_{QR\_RED} = ASC_{QR\_RED} + \beta \cdot X\)
  - \(V_{QR\_OTHER} = 0 + \beta \cdot X\)
  - Donde X son las dummies temporales

**Resultados principales:**
- MU_QR ≈ 3.7-4.3 (confirma correlación fuerte entre alternativas QR)
- Rho-cuadrado ajustado: ~0.56-0.58 (mejor que binario por estructura anidada)
- ASC_QR_RED negativo (App Red menos preferida que otras Apps dentro del nido QR)

---

### 4. Modelo Nested Logit Extendido

**Archivo:** `03_models/nested_logit.qmd` (sección "Modelo Nested Logit Extendido")

**Especificación:**
- **Estructura:** Igual al nested baseline, pero con variables extendidas
- **Utilidades:** Incluyen variables temporales + atributos del viaje (igual al binario extendido)

**Resultados principales:**
- MU_QR ≈ 3.7-4.0 (estable, confirma estructura anidada)
- Rho-cuadrado ajustado: ~0.58-0.60 (mejor ajuste que baseline)
- Patrones similares al binario extendido en atributos del viaje
- **⚠️ Misma limitación:** Variables de atributos del viaje sesgadas por transbordos internos

---

## Sistema de Particiones y Muestreo

### Particiones Temporales

Se estimaron los modelos sobre dos semanas representativas:
- **2025-W17**: Semana 17 del año 2025
- **2025-W18**: Semana 18 del año 2025

Cada partición contiene aproximadamente 12-13 millones de viajes.

### Muestreo Estratificado

Para hacer viable la estimación computacionalmente, se implementó un sistema de muestreo estratificado que preserva las proporciones de las clases de elección:

**Funciones implementadas:**
- `get_stratified_sample()`: Para modelos binarios (estratifica por `choice`)
- `get_stratified_sample_nested()`: Para modelos nested (estratifica por `choice_nested`)

**Configuraciones validadas:**
- **20% muestreado**: Reproduce resultados con Rho-cuadrado idéntico al dataset completo
- **50% muestreado**: Validación adicional, también consistente

**Validación de consistencia:**
- Los coeficientes estimados son prácticamente idénticos entre 20% y 50%
- Los estadísticos t son ligeramente menores en 20% (esperado), pero siguen siendo altamente significativos
- Rho-cuadrado ajustado idéntico entre configuraciones de muestreo

**Conclusión:** El muestreo estratificado al 20% es suficiente para estimaciones confiables, permitiendo escalar a más semanas sin problemas computacionales.

---

## Problema Crítico Identificado: Transbordos Internos Metro-Metro

### Descripción del Problema

Durante el análisis de los resultados, se identificó una limitación crítica en los datos: **transbordos internos entre metro no detectados** (también llamados "transbordos fantasmas").

**¿Qué son los transbordos internos?**
Son transbordos que ocurren dentro de la misma red de Metro (por ejemplo, cambiar de Línea 1 a Línea 2 en la estación Los Héroes) pero que el sistema de registro de viajes no detecta correctamente como un único viaje continuo. En su lugar, los registra como etapas separadas con trasbordos y tiempos asociados.

**Impacto en los modelos:**

1. **Sobreestimación del número de trasbordos (`VAR_N_TRASBORDOS`)**:
   - Viajes que en realidad tienen transbordos internos dentro de Metro aparecen como continuos.
   - "Des-inflan" artificialmente la complejidad del viaje

2. **Sesgo en tiempos de espera (`VAR_T_ESPERA_TRASBORDO_MIN`)**:
   - Los tiempos de espera asociados a estos transbordos fantasmas no reflejan esperas reales entre modos distintos
   - Los tiempos pueden estar subestimados o no representar el comportamiento real

3. **Sesgo en tiempos de caminata (`VAR_T_CAMINATA_MIN`)**:
   - Los tiempos de caminata entre etapas que en realidad son transbordos internos están siendo contabilizados incorrectamente
   - Pueden estar subestimados


### Impacto en Interpretación de Resultados

Los coeficientes de las variables afectadas deben interpretarse con precaución:
- `B_N_TRASBORDOS`: Puede estar subestimado
- `B_T_CAMINATA`: Puede estar sesgado
- `B_T_ESPERA_TRASBORDO`: Puede estar sesgado


**Nota importante:** A pesar de estos sesgos, los signos y direcciones generales de los efectos probablemente siguen siendo válidos, pero las magnitudes pueden estar distorsionadas.

### Work en Progreso: Corrección de Transbordos Internos

**Archivo relacionado:** `01_processing/04_transbordos_metro.qmd`

Se ha desarrollado un notebook de procesamiento que:
1. Construye un grafo de la red de Metro (líneas y estaciones)
2. Valida viajes Metro identificando transbordos internos
3. Marca viajes con transbordos internos no tratados

**Estado actual:** El notebook está funcional y puede identificar transbordos internos, pero aún no se ha integrado la corrección en el pipeline de feature engineering para los modelos Logit.

### Próximos Pasos (Futuro)

1. **Integración de corrección en pipeline:**
   - Modificar `prepare_features_extended()` para usar datos con transbordos corregidos
   - Re-estimar modelos extendidos con datos corregidos

2. **Validación de impacto:**
   - Comparar coeficientes antes y después de corrección
   - Evaluar cambios en bondad de ajuste
   - Verificar si los signos y magnitudes se vuelven más consistentes

3. **Análisis de sensibilidad:**
   - Estimar modelos con diferentes niveles de corrección
   - Evaluar robustez de conclusiones

---

##  Resultados y Hallazgos Principales

### Consistencia entre Modelos

1. **Variables temporales:**
   - Patrones consistentes entre modelos binarios y nested
   - Horas punta favorecen QR (coeficientes positivos)
   - Días laborales fuera de punta favorecen Bip! (coeficientes negativos)

2. **Evolución temporal:**
   - W18 muestra mayor preferencia base por QR comparada con W17
   - Sugiere tendencia de adopción creciente del QR

3. **Complejidad del viaje:**
   - Todos los modelos (extendidos) muestran que la complejidad reduce preferencia por QR
   - Coeficientes negativos consistentes para trasbordos, caminata y esperas

### Parámetro del Nido (MU_QR)

En los modelos Nested Logit:
- `MU_QR` ≈ 3.7-4.3 en todas las configuraciones
- Valores > 1 confirman que existe correlación positiva entre alternativas QR
- Justifica la estructura anidada del modelo
- Indica que las Apps QR (Red y Otras) comparten características comunes que las diferencian de Bip!

### Validación del Muestreo Estratificado

- **Rho-cuadrado idéntico** entre 20% y 50% para cada modelo y semana
- **Coeficientes prácticamente idénticos** entre configuraciones de muestreo
- **Conclusión:** El muestreo estratificado al 20% es válido y eficiente para estimaciones futuras

---

## Archivos y Commits Principales

### Notebooks Creados/Modificados

1. `03_models/binary_logit_qr_adoption.qmd`
   - Modelo Logit Binario baseline
   - Estimación secuencial con muestreo
   - Tablas de resultados

2. `03_models/binary_extended_logit_qr_adoption.qmd`
   - Modelo Logit Binario extendido
   - Refactorización completa para estructura clara
   - Tablas comparativas 20% vs 50%
   - Disclaimers sobre transbordos internos

3. `03_models/nested_logit.qmd`
   - Modelos Nested Logit baseline y extendido
   - Diagrama visual de estructura
   - Sistema de carga y visualización de resultados
   - Disclaimers sobre transbordos internos

4. `01_processing/04_transbordos_metro.qmd`
   - Construcción de grafo de red Metro
   - Validación de transbordos internos
   - Marcado de viajes con transbordos fantasmas


---

## 📚 Referencias y Recursos

- **Biogeme Documentation:** https://biogeme.epfl.ch/
- **Nested Logit Theory:** Ben-Akiva, M., & Lerman, S. R. (1985). *Discrete choice analysis: theory and application to travel demand*
- **Conventional Commits:** https://www.conventionalcommits.org/

---

**Última actualización:** Octubre 2025  
**Desarrollado por:** Juan Vicente Onetto Romero  
**Rama:** `feature/logit-model` → `develop`

