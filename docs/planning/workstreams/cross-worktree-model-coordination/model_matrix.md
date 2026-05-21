# Model Matrix — Cross-Worktree Coordination

Esta matriz es el registro vivo de modelos y experimentos comparables entre frentes. Debe actualizarse cuando un modelo se corre, se descarta o cambia de rol metodológico.

## Modelos Activos

| Frente | Worktree | Modelo / familia | Rol | Estado | Métricas mínimas | Artefactos esperados |
|---|---|---|---|---|---|---|
| MNL/Nested | `tesis-project` | MNL territorial actual con `BIP` base | Línea econométrica principal provisional | En revisión post-reunión | `LL`, `AIC`, `BIC`, rho-square, convergencia, odds ratios, `t`, `p` | Tablas wide, anexos, reporte logit, capítulo resultados |
| MNL/Nested | `tesis-project` | MNL con atributos observados + macrozonas | Candidato econométrico actualizado | Pendiente | `LL`, `AIC`, `BIC`, cambios de signos, odds ratios, estabilidad territorial | Notebook, tabla de comparación, decisión de variables |
| MNL/Nested | `tesis-project` | MNL `parsimonious` con EOD continuo + macrozonas | Candidato econométrico principal provisional | Corrido y seleccionado provisionalmente | `LL=-232214,2`, `AIC=464556,5`, `BIC=465263,9`, estabilidad de signos, odds ratios pendientes | Notebook `16`, tablas wide/odds ratios pendientes |
| MNL/Nested | `tesis-project` | MNL macro completo con EOD continuo + macrozonas | Sensibilidad de mayor ajuste | Corrido | `LL=-232189,9`, `AIC=464523,8`, `BIC=465319,6`, cambios en Censo/OSM/EOD | Resultados del preset `joint_mnl_censo_osm_eod_macrozone_sensitivity` |
| MNL/Nested | `tesis-project` | MNL `osm_local_clean` con EOD continuo + macrozonas | Sensibilidad parsimoniosa alternativa | Corrido | `LL=-232200,6`, `AIC=464537,2`, `BIC=465288,8`, estabilidad al retirar `sports_centre`/`convenience` | Notebook `16`, comparación con `parsimonious` |
| MNL/Nested | `tesis-project` | Nested Logit comparable | Sensibilidad estructural | Pendiente | `LL`, `AIC`, `BIC`, parámetro de nido, mejora vs MNL | Tabla MNL vs Nested, decisión sobre uso del nido |
| ML/XGBoost | `tesis-project-ml` | XGBoost multiclase comparable | Benchmark predictivo flexible | Pendiente de realinear con target/muestra final | logloss, accuracy, balanced accuracy, macro-F1, calibración si aplica | Notebook, métricas, SHAP global/local |
| Segmentación | `tesis-project-segmentation` | Clustering de comportamiento | Complemento descriptivo/heterogeneidad | En curso | estabilidad de clusters, perfiles, adopción por segmento | Tabla de segmentos, perfiles, comparación de adopción |

## Criterios De Comparación
- Comparar MNL/Nested y `XGBoost` solo si usan la misma variable objetivo y muestra comparable.
- Si un frente usa más features que otro, registrarlo como diferencia de diseño y no como comparación pura.
- Para modelos econométricos, priorizar interpretabilidad, signos, significancia, odds ratios y ajuste parsimonioso.
- Para ML, priorizar desempeño fuera de muestra, estabilidad del split, ausencia de leakage e interpretación SHAP.
- Para segmentación, priorizar estabilidad, interpretabilidad y utilidad narrativa, no performance predictiva.

## Estado De Decisión
- Modelo econométrico final: pendiente; candidato principal provisional `parsimonious`.
- Benchmark ML final: pendiente.
- Segmentos finales: pendiente.
- Resultados listos para tesis: parcialmente, solo capítulos intro/literatura/métodos y reporte logit territorial como insumo.
