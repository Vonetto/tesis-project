# Notes — Nested Logit con Buffers OD (Option1 alt-specific)

## 2026-02-17 — Resolución metodológica con profesora
- Respuesta validada:
  - **Buffers**: usar **Origen-Destino (OD)**.
  - **Unidad de estimación principal**: **Opción 1** (viaje individual + contexto OD).
  - **Dummies temporales**: migrar a esquema **V2** (exclusivas).
  - **Socio-demográficas**: probar ambas formas (origen y OD), priorizando origen.
- Implicancia operativa:
  - En notebook `05_nested_logit_od_buffers.qmd` el flujo por defecto queda en **Option1 + V2**.
  - `Option1 V1` y `Option2` se mantienen como comparación/sensibilidad, no como especificación principal.
  - `leave_one_out` se mantiene como default para promedios OD.

## 2026-02-28 — Decisión final de especificación con profesora
- Queda validado usar **solo pares OD con las 3 alternativas observadas** (`BIP`, `QR_RED`, `QR_OTHER`).
- Queda validado usar **coeficientes distintos por alternativa** para tiempos de vehículo, espera inicial, espera de trasbordo y número de trasbordos.
- Implicancia metodológica:
  - la especificación principal deja de ser un modelo reducido con contexto OD pooled;
  - pasa a ser un nested logit **plenamente alternativo-específico** con atributos construidos a nivel **OD x tipo_pago**;
  - `V_BIP` debe incluir atributos propios, manteniendo solo `ASC_BIP = 0` por identificación.
- Las dummies temporales V2 se mantienen como **interacciones diferenciales por alternativa** (`QR_RED`, `QR_OTHER`), con `BIP` como base.
- Esta decisión reemplaza la necesidad de seguir comparando contra `Option2` como camino operativo.

## 2026-02-28 — Smoke test de validez de especificación
- Se agregó una celda `smoke-test-option1-v2-spec` en `03_models/05_nested_logit_od_buffers.qmd`.
- Valida antes de estimar completo:
  - que `df_od_context` solo tenga OD con 3 alternativas observadas;
  - que `df_trips_v2` tenga todas las columnas alternativo-especificas esperadas;
  - que cada fila caiga en exactamente un regimen temporal V2;
  - que las columnas `TVH/TEI/TET/NTR` efectivamente varien entre alternativas;
  - y que una micro-estimacion (sample chica, `quick=True`) compile y corra sin error.
- Objetivo: detectar fallas de construccion/identificacion antes de lanzar la corrida larga.

## 2026-03-03 — Revisión minuciosa del modelo principal (Option1 alt-specific)
- No se detectaron bugs evidentes en:
  - filtro a OD con 3 alternativas;
  - construcción de columnas `TVH/TEI/TET/NTR` por alternativa;
  - codificación de `choice_nested`;
  - exclusividad de dummies V2;
  - `leave_one_out` solo para la alternativa elegida.
- Riesgo metodológico principal:
  - las variables alternativo-especificas se construyen con promedios observados por `OD x tipo_pago`, no con atributos exogenos/contrafactuales de nivel de servicio. Por tanto, el modelo compara medias de viajes realizados por alternativa, no un set exogeno de atributos disponibles.
- Riesgo de identificacion:
  - al permitir coeficientes distintos por alternativa para `TVH/TEI/TET/NTR`, la matriz de regresores queda fuertemente correlacionada entre alternativas. Diagnostico rapido en parquet construido:
    - corr(`TVH_BIP`,`TVH_QR_OTHER`) ≈ 0.984
    - corr(`TVH_BIP`,`TVH_QR_RED`) ≈ 0.951
    - corr(`NTR_BIP`,`NTR_QR_OTHER`) ≈ 0.985
    - corr(`NTR_BIP`,`NTR_QR_RED`) ≈ 0.954
  - esto probablemente explica varios coeficientes no significativos o con signo inestable.
- Riesgo de interpretacion de muestras 30/40/60%:
  - el notebook construye primero el contexto OD x tipo_pago y el `leave_one_out` sobre toda la semana, y solo despues submuestrea filas para estimar.
  - por tanto, las corridas sampleadas no son una “estimacion puramente sampleada”; usan regresores construidos con informacion del dataset completo de W17.
- Proximo diagnostico recomendado:
  - estimar la misma especificacion como MNL (sin nido) antes de seguir con socio-demo, dado que `MU_QR` quedo en el bound inferior (`1.0`) en 30% y 40%.

## 2026-03-03 — Preparación para corrida full
- Se cambió `SAMPLE_FRACTION = None` en `03_models/05_nested_logit_od_buffers.qmd` para probar la especificación sobre el total de observaciones válidas.
- Se fijó `number_of_threads = 1` en:
  - `biogeme.toml`
  - `03_models/biogeme.toml`
- Motivo: bajar presión de RAM sin cambiar la lógica econométrica del modelo.

## 2026-03-03 — Viabilidad en Larch
- Se revisó documentación oficial de Larch (`larch.newman.me`) y la instalación local en `larch-env`.
- Conclusión:
  - Larch sí soporta esta especificación con datos **idco** (case-only) usando `Dataset.from_idco(...)`.
  - La elección observada puede definirse con `Model.choice_co_code`.
  - Las utilidades alternativo-específicas deben ir en `Model.utility_co` (dict por alternativa).
  - La estructura nested se define con `NestingTree`.
- Implicancia:
  - Para replicar el modelo actual de buffers en Larch, conviene usar un notebook separado para no mezclar sintaxis/diagnósticos con Biogeme.

## 2026-03-03 — Notebook separado de réplica en Larch
- Se creó `03_models/larch_logit/05_nested_logit_od_buffers_larch.qmd`.
- Decisiones de implementación:
  - reusar el mismo pipeline de datos desde `lib/od_buffers_nested_logit.py`;
  - remapear alternativas de `choice_nested = {0,1,2}` a `choice_larch = {1,2,3}` porque `Larch` usa `root_id=0` en el `NestingTree`;
  - usar `Dataset.construct.from_idco(...)`, `Model.choice_co_code`, `Model.utility_co` y `graph.new_node(...)`;
  - fijar `compute_engine = "numba"` y `method = "slsqp"` para que el parámetro del nido respete sus bounds;
  - castear columnas numéricas a `int32/float64` antes de estimar para evitar errores de tipos.
- Validación rápida:
  - smoke real sobre `trips_context_v2_2025-W17.parquet` con 15k filas corrió sin error;
  - el parámetro `Mu:QR` quedó dentro de bounds (`0.01 <= Mu:QR <= 1.0`) usando `slsqp`;
  - con `bhhh` el parámetro podía violar los bounds, por eso el notebook quedó alineado a `slsqp`.
- Ajuste posterior:
  - se corrigieron imports del `setup` para esta rama/repositorio:
    - `resolve_caracterizacion_path` y `read_parquet_portable` se importan desde `lib.od_buffers_nested_logit`;
    - `SEED` queda definido localmente como `42`;
  - motivo: `config.paths`, `config.constants.SEED` y `lib.data_loading` no existen en esta rama.

## 2026-03-03 — Decisión de benchmark principal: MNL
- Después de replicar la especificación alt-specific en **Biogeme** y **Larch**, el patrón es estable:
  - el ajuste global se mantiene cercano a `Rho^2 ~= 0.509`;
  - el parámetro del nido colapsa sistemáticamente al borde:
    - **Biogeme**: `MU_QR = 1`
    - **Larch**: `Mu:QR = 1`
- Conclusión operativa:
  - el siguiente benchmark principal debe ser **MNL con exactamente la misma especificación**;
  - el nested se mantiene como resultado de contraste/metodológico, no como especificación principal para interpretación sustantiva.
- Próximo trabajo explícito:
  - implementar MNL en `Larch`;
  - implementar MNL en `Biogeme`;
  - comparar `nested vs MNL` y documentar si el nido agrega (o no) valor empírico.

## 2026-03-03 — Contraste empírico final: nested vs MNL
- El contraste ya quedó cerrado en ambos frameworks con la misma especificación alt-specific.
- **Larch full**
  - `MNL`: `LL = -5,183,641`, `Rho^2 = 0.508443`, `20` parámetros.
  - `Nested`: `LL = -5,183,720`, `Rho^2 = 0.508435`, `21` parámetros.
  - `Mu:QR = 1.0` (`Active bound = True`).
  - Conclusión: el **MNL domina levemente** al nested con un parámetro menos.
- **Biogeme sample60pct**
  - `MNL`: `LL = -3,107,303`, `Rho^2 = 0.509`, `20` parámetros.
  - `Nested`: `LL = -3,107,303`, `Rho^2 = 0.509`, `21` parámetros.
  - `MU_QR = 1.0`.
  - Conclusión: el nested no mejora en nada al MNL.
- Implicancia metodológica:
  - el modelo principal para interpretación pasa a ser el **MNL alt-specific**;
  - el nested se mantiene solo como contraste para documentar que el nido QR no agrega estructura empírica en esta base.

## 2026-03-03 — Diagnóstico de estabilidad y colinealidad del MNL alt-specific
- Se compararon parámetros entre:
  - `Larch MNL full`;
  - `Biogeme MNL sample50pct`;
  - `Biogeme MNL sample60pct`.
- Bloques que aparecen **estables** entre frameworks/muestras:
  - `ASC_QR_RED`, `ASC_QR_OTHER` (negativos y de magnitud similar);
  - `B_QR_RED_LAB_PM`, `B_QR_RED_LAB_PT` (positivos y estables);
  - `B_QR_OTHER_LAB_PM`, `B_QR_OTHER_LAB_PT`, `B_QR_OTHER_NO_LAB` (positivos y estables);
  - `B_BIP_T_ESPERA_INI`, `B_BIP_T_ESPERA_TRASB`, `B_QR_RED_T_ESPERA_INI`, `B_QR_OTHER_T_ESPERA_INI`, `B_QR_OTHER_T_ESPERA_TRASB` (negativos y estables).
- Coeficientes que muestran **problemas persistentes de interpretación**:
  - `B_BIP_T_VEH > 0`;
  - `B_QR_RED_T_VEH > 0`;
  - `B_QR_OTHER_T_VEH > 0`;
  - `B_QR_RED_T_ESPERA_TRASB > 0`;
  - `B_BIP_N_TRASB` cambia de signo entre frameworks;
  - `B_QR_RED_NO_LAB` cambia de signo entre frameworks.
- Diagnóstico cuantitativo sobre el parquet `trips_context_v2_2025-W17.parquet` (sample de 500k filas):
  - **Correlación entre alternativas para la misma métrica**:
    - `corr(TVH_BIP, TVH_QR_OTHER) ~= 0.984`
    - `corr(TVH_BIP, TVH_QR_RED) ~= 0.952`
    - `corr(TEI_BIP, TEI_QR_OTHER) ~= 0.951`
    - `corr(TET_BIP, TET_QR_OTHER) ~= 0.917`
    - `corr(NTR_BIP, NTR_QR_OTHER) ~= 0.985`
  - **Correlación dentro de alternativa**:
    - `corr(TET_BIP, NTR_BIP) ~= 0.651`
    - `corr(TET_QR_RED, NTR_QR_RED) ~= 0.590`
    - `corr(TET_QR_OTHER, NTR_QR_OTHER) ~= 0.628`
  - **Dispersión relativa dentro del choice set**:
    - `TVH`: `mean_rel_range ~= 0.113`
    - `TEI`: `mean_rel_range ~= 0.254`
    - `TET`: `mean_rel_range ~= 1.249`
    - `NTR`: `mean_rel_range ~= 1.115`
- Lectura:
  - `TVH` y `TEI` tienen bastante componente común entre alternativas dentro del mismo OD;
  - `TET` y `NTR` muestran mayor dispersión relativa, pero también están moderadamente solapados dentro de cada alternativa;
  - esto apunta a un problema de **sobrecarga paramétrica** más que a un bug de implementación.

## 2026-03-03 — Ruta de refinamiento propuesta
- Mantener por ahora:
  - el benchmark principal como **MNL alt-specific**;
  - las dummies temporales V2;
  - los atributos construidos a nivel `OD x tipo_pago`;
  - el filtro a OD con las 3 alternativas observadas.
- Refinamiento sugerido en orden:
  1. **Simplificar el bloque de trasbordos**:
     - probar primero una especificación que conserve `TEI` y `TVH`, pero deje solo **una** de estas dos:
       - `TET` (espera de trasbordo), o
       - `NTR` (número de trasbordos).
     - motivo: `TET` y `NTR` están moderadamente correlacionadas y hoy parecen estar compitiendo por el mismo componente de fricción.
  2. **Evaluar una reparametrización relativa dentro del choice set**:
     - construir versiones centradas o diferenciales por alternativa (`x_alt - promedio_del_choice_set` o diferencias respecto a `BIP`) para separar mejor:
       - componente común del corredor OD;
       - ventaja/desventaja relativa de cada alternativa.
     - motivo: los signos positivos persistentes en `T_VEH` sugieren que el nivel común del corredor se está mezclando con la comparación entre alternativas.
  3. **Solo si sigue habiendo mala identificación**, discutir si conviene relajar la exigencia de coeficientes totalmente separados para todos los atributos.
- Criterio para elegir refinamientos:
  - priorizar signos plausibles y estabilidad entre frameworks;
  - no agregar complejidad adicional antes de cerrar una versión parsimoniosa del MNL.

## 2026-03-04 — Notebook separado de refinamiento MNL
- Se creó `03_models/06_mnl_refinement_diagnostics.qmd` para aislar el trabajo de refinamiento sin mezclarlo con notebooks principales.
- Contenido del notebook:
  - reconstrucción de `df_trips` con el mismo pipeline del modelo principal;
  - diagnóstico de colinealidad/dispersión (`cross-alternative`, `within-alternative`, rango relativo por choice set);
  - ejecución opcional de variantes MNL en **Biogeme** y **Larch**;
  - comparación consolidada por framework/variante.
- Variantes iniciales definidas (sin podar por signo):
  - `full`: bloque completo (`TVH`, `TEI`, `TET`, `NTR`);
  - `no_ntr`: elimina solo `NTR` en las tres alternativas;
  - `no_tet`: elimina solo `TET` en las tres alternativas.
- Objetivo explícito:
  - evaluar parsimonia e identificación del bloque de trasbordos antes de pasar a reparametrizaciones más complejas.

## 2026-03-04 — Ampliación de variantes de refinamiento (identificación cross-alternative)
- Se amplió `06_mnl_refinement_diagnostics.qmd` para soportar modos adicionales, ejecutables tanto en Biogeme como en Larch:
  - `generic`: coeficientes comunes por métrica (`TVH`, `TEI`, `TET`, `NTR`) con valores alt-specific.
  - `mixed_tei_specific`: `TVH/TET/NTR` genéricos y `TEI` alt-specific.
  - `diff_vs_bip`: utilidades QR definidas con diferencias respecto de BIP (`x_QR - x_BIP`) y `V_BIP = 0`.
- Se mantuvieron también las variantes previas:
  - `full`, `no_ntr`, `no_tet`.
- Se añadió celda `compare-params-by-variant` para comparar, por framework:
  - valores de parámetros por variante;
  - significancia (`p < 0.05`) por variante.
- Criterio reforzado:
  - decidir simplificación por estabilidad/identificación/parsimonia y no por “signo esperado”.

## 2026-01-20 — Planificación inicial
**Objetivo:** comparar dos enfoques para incorporar buffers OD en modelos nested logit (BIP/QR_RED/QR_OTHER).

**Opción 1 (micro + contexto):**
- Observación = viaje individual.
- Se agregan variables de contexto OD (promedios) calculadas sobre **todos** los viajes del OD (sin separar por tipo_pago).

**Opción 2 (agregado por OD):**
- Observación = OD×alternativa con pesos (n_viajes).
- Se usa likelihood ponderada vía fórmula de peso en Biogeme.

**Guardrails:**
- Usar columnas finales (v2) y omitir caminata.
- Evitar leakage temporal si hay train/test.
- Documentar outputs objetivos (stats/params) por opción.

---

## 2026-01-20 — Implementación base
**Archivos creados:**
- `lib/od_buffers_nested_logit.py`
- `03_models/05_nested_logit_od_buffers.qmd`

**Salidas intermedias previstas:**
- `03_models/tmp/od_buffers_nested_logit/od_context_<PARTITION>.parquet`
- `03_models/tmp/od_buffers_nested_logit/trips_context_<PARTITION>.parquet`
- `03_models/tmp/od_buffers_nested_logit/od_long_<PARTITION>.parquet`

**Config actual:**
- Partición: 2025-W17 (full)
- INCLUDE_OD_TIME_SHARES = False
- SAMPLE_FRACTION = 0.3

---

## 2026-01-20 — Opción 1 dataset generado
- `od_context_2025-W17.parquet` creado
- `trips_context_2025-W17.parquet` creado

---

## 2026-01-20 — Opción 1 (Nested Logit, specific) — Resultados objetivos
**Stats**
- Number of estimated parameters: 23
- Sample size: 3,650,532
- Excluded observations: 0
- Init log likelihood: -4,010,519
- Final log likelihood: -1,897,231
- Likelihood ratio test for the init. model: 4,226,577
- Rho-square for the init. model: 0.527
- Rho-square-bar for the init. model: 0.527
- AIC: 3,794,508
- BIC: 3,794,809
- Final gradient norm: 6.5836E+02
- Bootstrapping time: None

**Parameters (Value, Robust std err., Robust t-stat., Robust p-value)**
- ASC_QR_RED: -2.382508, 0.162316, -14.678176, 0.0
- B_QR_RED_PM_LAB: 0.236449, 0.015563, 15.192982, 0.0
- B_QR_RED_PT_LAB: 0.316247, 0.015418, 20.511056, 0.0
- B_QR_RED_LJ_LAB: -0.132774, 0.012665, -10.483383, 0.0
- B_QR_RED_VIE_LAB: -0.137034, 0.010598, -12.929767, 0.0
- B_QR_RED_T_VEH: -0.000052, 0.000007, -7.912129, 2.442491e-15
- B_QR_RED_N_TRASB: -0.156560, 0.006693, -23.390074, 0.0
- B_QR_RED_T_ESPERA_INI: -0.000079, 0.000012, -6.598030, 4.166578e-11
- B_QR_RED_T_ESPERA_TRASB: -0.000056, 0.000012, -4.715310, 2.413426e-06
- B_OD_T_VEH: 0.000046, 0.000005, 9.730450, 0.0
- B_OD_N_TRASB: 0.023052, 0.006369, 3.619663, 2.949867e-04
- B_OD_T_ESPERA_INI: -0.000144, 0.000007, -19.372917, 0.0
- B_OD_T_ESPERA_TRASB: -0.000090, 0.000013, -7.100800, 1.240341e-12
- MU_QR: 1.915150, 0.309297, 6.191950, 5.942422e-10
- ASC_QR_OTHER: -1.472210, 0.014327, -102.755329, 0.0
- B_QR_OTHER_PM_LAB: 0.128854, 0.004610, 27.948662, 0.0
- B_QR_OTHER_PT_LAB: 0.219310, 0.005136, 42.703414, 0.0
- B_QR_OTHER_LJ_LAB: -0.209194, 0.004876, -42.905352, 0.0
- B_QR_OTHER_VIE_LAB: -0.190015, 0.005571, -34.109643, 0.0
- B_QR_OTHER_T_VEH: -0.000015, 0.000004, -3.427938, 6.081850e-04
- B_QR_OTHER_N_TRASB: -0.129896, 0.005749, -22.595335, 0.0
- B_QR_OTHER_T_ESPERA_INI: -0.000002, 0.000006, -0.424557, 6.711593e-01
- B_QR_OTHER_T_ESPERA_TRASB: -0.000068, 0.000010, -7.084039, 1.400213e-12

---

## 2026-01-20 — Opción 2 (Nested Logit, specific con pesos) — Resultados objetivos
**Stats**
- Number of estimated parameters: 11
- Sample size: 473,035
- Excluded observations: 0
- Init log likelihood: -1.33684e+07
- Final log likelihood: -6,339,065
- Likelihood ratio test for the init. model: 1.405867e+07
- Rho-square for the init. model: 0.526
- Rho-square-bar for the init. model: 0.526
- AIC: 1.267815e+07
- BIC: 1.267827e+07
- Final gradient norm: 1.5719E+08
- Bootstrapping time: None

**Parameters (Value, Robust std err., Robust t-stat., Robust p-value)**
- ASC_QR_RED: -2.348439, 2.744663e-02, -85.563845, 0.000000
- B_QR_RED_OD_T_VEH: 0.000003, 1.089137e-06, 3.164989, 0.001551
- B_QR_RED_OD_N_TRASB: -0.133161, 9.226438e-04, -144.325158, 0.000000
- B_QR_RED_OD_T_ESPERA_INI: -0.000289, 4.022650e-06, -71.884477, 0.000000
- B_QR_RED_OD_T_ESPERA_TRASB: -0.000148, 4.814820e-06, -30.647570, 0.000000
- MU_QR: 1.986136, 6.277427e-02, 31.639329, 0.000000
- ASC_QR_OTHER: -1.596348, 3.324068e-03, -480.239449, 0.000000
- B_QR_OTHER_OD_T_VEH: 0.000035, 5.107979e-07, 68.516892, 0.000000
- B_QR_OTHER_OD_N_TRASB: -0.103771, 6.657213e-04, -155.877904, 0.000000
- B_QR_OTHER_OD_T_ESPERA_INI: -0.000142, 1.338565e-06, -106.396518, 0.000000
- B_QR_OTHER_OD_T_ESPERA_TRASB: -0.000161, 2.779850e-06, -57.865510, 0.000000

---

## 2026-01-26 — Decisiones teóricas (buffers OD)
- **Dummies temporales V2 (exclusivas)**: usar `DUMMY_LAB_PM`, `DUMMY_LAB_PT`, `DUMMY_NO_LAB` con **base implícita `LAB_VALLE`**.
- **Mantener V1 y V2** en el notebook para comparación; V1 = dummies solapadas (PM/PT/LJ/VIE), V2 = exclusivas.
- **Promedios OD** por defecto en modo **`leave_one_out`** (reduce endogeneidad mecánica).
- **Opción 2** separada en V1/V2:
  - V1 usa solo variables OD continuas.
  - V2 puede incluir *shares OD* de tiempo **solo si** `INCLUDE_OD_TIME_SHARES=True`.
- **Outputs separados** por variante (carpetas `option2-v1-*` y `option2-v2-*`) para evitar mezcla.
- **Checks de base**: añadir celdas de verificación de base efectiva de dummies (V1 y V2) antes de estimar.

## 2026-02-27 — Limpieza de notebook (solo especificación principal)
- Se limpió `03_models/05_nested_logit_od_buffers.qmd` para evitar confusión operativa:
  - Se eliminó del flujo visible la estimación `Option1 V1` y toda `Option2`.
  - Se dejó únicamente `Option1 V2` como pipeline activo (dataset, check base, estimación, carga de resultados).
  - `run-all` quedó simplificado al flujo principal `Option1 V2`.
- Motivo: alinear notebook con decisión metodológica vigente (profesora: OD + Option1 + dummies V2).

## 2026-02-27 — Re-run limpio sin warm-start
- Se agregó en `03_models/05_nested_logit_od_buffers.qmd` el switch `CLEAN_RUN_NO_ITER=True`.
- Antes de estimar, el notebook elimina `__nested_logit_od_context_v2_<PARTITION>.iter` (si existe) en rutas candidatas (`cwd`, raíz proyecto, `03_models/`).
- Objetivo: forzar estimación desde cero (sin arrastre de valores iniciales previos).

## 2026-02-27 — Cierre analítico del notebook OD buffers
- Se añadió sección final en `03_models/05_nested_logit_od_buffers.qmd`:
  - `6.1` interpretación sustantiva de `Option1 V2`.
  - `6.2` explicación explícita de qué aporta usar buffers OD frente al nested anterior.
  - `6.3` celda de resumen automático de stats/coeficientes clave para reporte.

## 2026-02-27 — Integración socio-demo (origen) en Option1 V2
- Se implementó en `03_models/05_nested_logit_od_buffers.qmd` el bloque `7.x`:
  - `7.1` configuración socio (path + variables seleccionadas).
  - `7.2` join de Censo por `zona_inicio_viaje` sobre dataset `Option1 V2`.
  - `7.3` estimación `Option1 V2 + socio origen` con betas `B_SOC_O_*`.
  - `7.4` comparación objetiva baseline vs socio-origen.
- Se ajustó `lib/od_buffers_nested_logit.py` para conservar `zona_inicio_viaje` y `zona_fin_viaje` en `build_trip_dataset_with_context`, habilitando el join socio sin hacks.

- 2026-02-27: Se robustecio `compare-option1-v2-vs-socio-origen` para persistir `stats_socio/params_socio` desde memoria si el modelo converge pero los CSV aun no existen en disco.

- 2026-02-27: Se agrego recuperacion de modelos socio desde `.iter` en `05_nested_logit_od_buffers.qmd` (`read_biogeme_iter_file`, `SOCIO_RESUME_FROM_ITER`, `SOCIO_ESTIMATION_MODE`). Si la RAM vuelve a caer, usar `SOCIO_ESTIMATION_MODE = "quick"` como rescate de LL/params sin SE robustos.

- 2026-02-27: La celda `estimate-option1-v2-socio-origen` ahora define un fallback local de `read_biogeme_iter_file` si no se re-ejecuta `setup`, evitando `NameError` por orden de celdas.

- 2026-02-27: Nueva observacion metodologica tras reunion. El `Option1 V2` actual en `05_nested_logit_od_buffers.qmd` usa (i) variables realizadas del viaje elegido y (ii) contexto OD pooled (`B_OD_*`) comun a QR_RED y QR_OTHER, con `V_BIP = 0`. Esto es un modelo reducido de adopcion/uso de QR, pero no un modelo plenamente alternativo-especifico por tipo de pago. Queda pendiente redisenar el dataset/utilidades para usar atributos por alternativa (`OD x tipo_pago`) en `V_BIP`, `V_QR_RED`, `V_QR_OTHER`, idealmente con leave-one-out solo en la alternativa elegida.

- 2026-02-27: Se implemento redisenio principal de `Option1 V2` en `05_nested_logit_od_buffers.qmd` y `lib/od_buffers_nested_logit.py`: (i) atributos OD x tipo_pago en wide, (ii) filtro a OD con 3 alternativas observadas, (iii) `leave_one_out` solo en la alternativa elegida, (iv) `V_BIP` con atributos propios, y (v) coeficientes alternativo-especificos para tiempos/esperas/transbordos.

- 2026-03-03: Se agrego el benchmark **MNL** con exactamente la misma utilidad alt-specific en ambos notebooks:
  - `03_models/larch_logit/05_nested_logit_od_buffers_larch.qmd` ahora tiene:
    - `estimate_larch_mnl_option1_alt_specific(...)`,
    - carpeta de outputs separada para MNL,
    - comparacion `compare-larch-mnl-vs-nested`.
  - `03_models/05_nested_logit_od_buffers.qmd` ahora tiene:
    - `estimate_mnl_option1_alt_specific(...)`,
    - celda `estimate-mnl-option1-v2`,
    - switch MNL en `run-all`,
    - carga y comparacion `compare-option1-v2-mnl-vs-nested`.
  - Pendiente: correr ambos MNL y contrastar ajuste/signos frente al nested.

- 2026-03-03: Se corrigio un problema de warm-start en Biogeme: `model_name` ya incluye `sample_tag` (`sample30pct`, `sample50pct`, `full`, etc.) tanto en nested como en MNL y en `run-all`. Esto evita reutilizar el mismo archivo `__*.iter` entre corridas con muestras distintas y corrige estadisticas engañosas tipo `Init log likelihood = Final log likelihood`.

- 2026-03-04: Se agregaron variantes adicionales en `06_mnl_refinement_diagnostics.qmd`: `generic_no_tet` y `diff_vs_bip_no_tet` para probar parsimonia adicional del bloque de trasbordos en modos `generic` y `diff_vs_bip`.

## 2026-03-05 — Resultados de refinamiento MNL (20% y 60%)

### Nested vs MNL (hallazgo principal)
- En ambas implementaciones (Biogeme y Larch), el nested colapsa al borde (`MU_QR = 1`), por lo que en la practica no aporta sobre MNL en esta especificacion OD-buffers alt-specific.
- Se adopta MNL como benchmark principal para refinamiento e interpretacion.

### Corridas de refinamiento ejecutadas
- Notebook: `03_models/06_mnl_refinement_diagnostics.qmd`.
- Frameworks: Biogeme y Larch.
- Variantes ejecutadas: `full`, `generic`, `mixed_tei_specific` (ademas se exploraron `no_ntr`, `no_tet`, `diff_vs_bip`, etc. en corridas previas).

### Resumen comparativo (muestra 60%)
- Fit:
  - `full` logra mejor ajuste (mayor LL, menor AIC/BIC), como esperable por mayor flexibilidad.
  - `mixed_tei_specific` queda intermedio.
  - `generic` es el mas parsimonioso con pequena perdida de ajuste.
- Identificacion y estabilidad cross-framework:
  - `full`: mayor inestabilidad entre Biogeme/Larch (`mean_rel_diff_pct ~ 35.85`, 12 parametros con diferencia relativa >10%).
  - `generic`: mas estable (`mean_rel_diff_pct ~ 20.36`, solo 2 parametros >10%).
  - `mixed_tei_specific`: mejor estabilidad del grupo (`mean_rel_diff_pct ~ 17.90`, solo 2 parametros >10%).
- Parametros fragiles persistentes:
  - `B_QR_RED_NO_LAB` sigue inestable (incluso cambio de signo entre frameworks en variantes parsimoniosas).
  - `B_N_TRASB` muestra diferencias relevantes pero sin cambios sistematicos de signo.

### Conclusiones metodologicas registradas
- El problema central no es solo tamano muestral; persiste una dificultad estructural de identificacion para algunos efectos (especialmente QR_RED en no laboral).
- El trade-off actual es:
  - `full`: mejor fit, peor robustez.
  - `generic` / `mixed_tei_specific`: menor fit pero mayor interpretabilidad/estabilidad.
- Decision de trabajo: priorizar lectura por estabilidad de parametros y dejar `full` como sensibilidad.

## 2026-03-06 — Cambio de foco tras reunion con profesora

### Feedback metodologico recibido
- La prioridad deja de estar en `MU`, en la seleccion fina de `betas`, o en cerrar ahora mismo la discusion `nested vs MNL`.
- La prioridad pasa a **controlar mejor el comportamiento observado** agregando nuevas variables explicativas.
- Hipotesis de trabajo acordada: al enriquecer la especificacion con mejores controles, parte de los problemas actuales de identificacion/colinealidad deberia atenuarse o volverse mas interpretable.

### Nueva direccion de modelamiento
- Mantener como base operativa el **MNL alt-specific OD-buffers** ya implementado.
- Dejar **pausado** el refinamiento centrado solo en:
  - colinealidad entre bloques actuales,
  - decision final entre `full` / `generic` / `mixed_tei_specific`,
  - reintento inmediato del nested sobre esas variantes.
- Retomar esa rama solo despues de probar una especificacion enriquecida.

### Nuevos bloques de variables priorizados
- **Demanda / intensidad de uso**:
  - numero de viajes por zona,
  - idealmente version ponderada o segmentada por franja horaria.
- **Oferta / servicio por zona**:
  - numero de paraderos,
  - numero de lineas/servicios,
  - cercania al metro mas cercano.
- **Socio-demografia**:
  - retomar integracion de Censo 2024 como bloque principal de controles.
- **Comparacion temporal / interanual**:
  - agregar la misma semana ISO de 2024 junto con 2025,
  - evaluar `dummy` de anio y/o pooling `W17-2024 + W17-2025`.

### Decision operativa
- Se deja registrado que el trabajo de correcciones/parsimonia actual queda **estacionado, no descartado**.
- La siguiente etapa activa es construir y evaluar una especificacion enriquecida antes de seguir afinando nested, signos o colinealidad residual.

## 2026-03-06 — Ordenamiento de ramas, commits y merge

### Commits modulares creados en `feature/buffers`
- `32c41d1` — `feat(biogeme): migrate core QR notebooks to v2 time dummies`
- `bc2e598` — `docs(planning): record OD-buffers modeling decisions`
- `7ade5c3` — `feat(od-buffers): add alt-specific OD buffers model pipeline`
- `60df84c` — `feat(refinement): add OD-buffers MNL diagnostics notebook`
- `f8b563d` — `feat(censo): add zona777 census utilities and EDA notebooks`
- `0d42d21` — `docs(planning): add historical thesis workstream plans`
- `aefc3ca` — `chore(gitignore): ignore local planning and model output directories`

### Decisiones sobre ramas
- `feature/buffers` se toma como rama canonica/base para el trabajo consolidado hasta esta etapa.
- Se auditó `feature/logit-model` y se decidió **no mergearla**:
  - divergía de `feature/buffers`,
  - arrastraba una estructura antigua/paralela de notebooks,
  - cualquier rescate futuro desde esa rama debe hacerse **archivo por archivo** o con `cherry-pick` muy selectivo, no con merge completo.

### Integracion a `develop`
- Se hizo merge de `feature/buffers` a `develop` con commit:
  - `19b0ba9` — `Merge branch 'feature/buffers' into develop`
- Con esto, `develop` queda como baseline consolidado de:
  - migracion V2,
  - OD-buffers alt-specific,
  - benchmark MNL / refinement,
  - utilidades y EDA inicial de Censo,
  - documentacion de decisiones.

### Nueva rama activa
- Se creó `feature/od-buffers-enriched-controls` desde `feature/buffers`.
- Luego se fast-forwardeó con `develop`, quedando alineada al merge commit `19b0ba9`.
- Esta rama pasa a ser la rama activa para la siguiente etapa: enriquecimiento del modelo con nuevas variables de control y comparacion 2024/2025.
