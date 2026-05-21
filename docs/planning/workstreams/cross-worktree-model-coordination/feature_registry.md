# Feature Registry — Cross-Worktree Coordination

Este archivo registra bloques de variables compartidos y reglas de comparabilidad. No reemplaza los notebooks ni los diccionarios de datos; funciona como contrato mínimo entre worktrees.

## Target Y Alternativas
- Unidad base del modelo econométrico: viaje individual.
- Alternativas:
  - `BIP`: alternativa base/tradicional.
  - `QR_OTHER`: canal QR digital no oficial o externo.
  - `QR_RED`: canal QR digital oficial del sistema Red, interpretado como proxy observable de adopción digital oficial.
- Regla narrativa:
  - no afirmar uso observado de app, consulta de información en tiempo real ni causalidad individual.

## Bloques De Variables

| Bloque | Ejemplos | Uso principal | Regla de comparabilidad |
|---|---|---|---|
| Viaje alternativa-específico | `T_VEH`, `T_ESPERA_INI`, `T_ESPERA_TRASB`, `N_TRASB` | MNL/Nested y benchmark ML | Usar mismas unidades; para odds ratios, tiempos por minuto y transbordos por unidad. |
| Temporal | `ANIO_2025`, `LAB_PM`, `LAB_PT`, `NO_LAB` | Todos los frentes | Variables comunes al viaje; en MNL usar `BIP` como base para comunes. |
| Demanda/oferta | `LOG_DEMAND`, `LOG_BUS_STOP_DENSITY`, `LOG_BUS_LINE_COUNT`, `LOG_METRO_LINE_COUNT` | MNL/Nested y ML | Registrar si la variable es zona/franja/año y si usa `log(1+x)`. |
| Censo / sociodemografía | educación, discapacidad, inmigrantes, mujeres, asistencia parvularia | MNL/Nested, ML, segmentación descriptiva | Interpretar como atributo territorial de zona de origen, no individual. |
| EOD 2012 ingreso | proxies ABC1/D+E continuos o dummies | Sensibilidad sociodemográfica | Usar como proxy territorial, no como ingreso individual observado. |
| OSM / entorno construido | school, university, playground, sports centre, convenience, shelter, subway entrance | MNL/Nested y ML | Registrar redundancias conceptuales antes de decidir modelo final. |
| Macrozonas | oriente, poniente, norte, sur, centro/base | MNL/Nested; posible ML | Definir una base explícita antes de comparar coeficientes territoriales. |
| Segmentación | intensidad de uso, regularidad, temporalidad, multimodalidad, adopción QR | Segmentación | No usar variables que generen circularidad si luego se interpretan diferencias de adopción. |

## Variables Bajo Revisión
- `shelter`: puede capturar calidad de espera, pero puede competir con densidad de paraderos.
- `convenience`: señal empírica útil, pero interpretación sustantiva menos directa.
- `hacinamiento`: puede competir con proxies EOD de ingreso.
- `share_mujeres_z` y `share_asistencia_parv_z`: candidatas sociodemográficas con señal empírica reciente, sujetas a decisión final.
- Proxies EOD 2012 de ingreso: candidatas activas; falta elegir representación continua vs dummy.

## Reglas Para Nuevas Variables
- Toda variable nueva debe registrar:
  - fuente;
  - nivel espacial/temporal;
  - unidad o transformación;
  - si es común o alternativa-específica;
  - interpretación sustantiva;
  - riesgo de colinealidad o redundancia;
  - en qué frentes se usará.
- Ninguna variable se vuelve canónica hasta que tenga definición reproducible y decisión registrada en `notes.md` o en el workstream técnico correspondiente.

