# ML Worktree Sync — `tesis-project-ml`

## Propósito

Este archivo registra, desde el repo principal `tesis-project`, los avances del worktree paralelo:

- [`/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml)

La idea **no** es duplicar su bitácora completa, sino dejar una síntesis ordenada de:

- qué decisiones se tomaron allá;
- qué artefactos relevantes se generaron;
- y cómo esos hallazgos impactan la línea principal de este repo.

La fuente canónica del frente ML sigue siendo:

- [`tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/notes.md)
- [`tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/task_plan.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/task_plan.md)

## Relación con este workstream

El frente `ml-baselines-shap` existe para complementar, no reemplazar, la línea principal:

- screening flexible de señal;
- comparación incremental de bloques de variables;
- interpretabilidad con `SHAP`;
- validación de si nuevos controles valen la pena antes de llevarlos al frente econométrico.

Por eso su punto de contacto principal en este repo es:

- [`docs/planning/workstreams/od-buffers-nested-logit/`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/od-buffers-nested-logit/)

## Ruta de decisiones relevante

### 1. Apertura del frente ML

- Se definió el framing correcto como **`ML baselines + interpretability`**, no predicción por la predicción.
- Se abrió un worktree separado para evitar contaminar la línea principal econométrica.
- Se decidió partir por un problema binario simple de adopción QR para validar:
  - pipeline,
  - métricas,
  - y `SHAP`.

Artefactos principales:

- [`03_models/ml_baselines/01_qr_adoption_baselines.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/03_models/ml_baselines/01_qr_adoption_baselines.qmd)
- [`03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd)

### 2. Alineación metodológica con el repo principal

En el worktree ML se cerraron varios problemas de consistencia con la línea principal:

- codificación modal alineada a `v2`;
- decisión explícita de trabajar **sin caminata**;
- abandono de `silver/viajes_filtrados` como input principal;
- migración a los parquets `tmp/viajes_con_te_calculado_*`, igual que el frente principal.

Implicancia para este repo:

- los resultados ML útiles para leer aquí son solo los posteriores a esa alineación;
- los artefactos antiguos con caminata o datasets viejos deben leerse como históricos/provisorios.

### 3. Resultado del baseline binario

El notebook `01_qr_adoption_baselines.qmd` dejó una lectura estable:

- hay señal predictiva, pero moderada;
- `XGBoost` mejora solo marginalmente a `RandomForest` y `LogisticRegression`;
- las variables más fuertes siguen siendo fricciones del viaje y dummies temporales/laborales;
- la codificación modal correcta mejora la interpretación, pero no cambia drásticamente la historia predictiva.

Lectura útil para este repo:

- el frente ML no contradice al logit/binario del repo principal;
- más bien refuerza que el bloque base ya tiene señal, pero no extremadamente alta;
- y ayuda a distinguir variables con señal real de variables que parecen importantes solo por especificación.

### 4. Apertura del notebook espacial/enriquecido

El segundo notebook ML (`02_qr_adoption_spatial_enriched.qmd`) se diseñó para responder:

- cuánto agrega la geografía residual;
- cuánto agregan demanda y oferta;
- cuánto absorben esos bloques del efecto espacial;
- y si la señal espacial sobrevive a validación más dura.

Decisiones relevantes:

- usar coordenadas de origen `x/y`;
- separar bloques:
  - baseline;
  - espacial;
  - demanda;
  - oferta;
  - combinaciones.

### 5. Validación espacial

Uno de los aportes metodológicos más útiles del worktree ML fue agregar validación espacial tipo `GroupKFold`.

Hallazgo relevante:

- el bloque espacial (`x/y`) sí mejora respecto del baseline incluso bajo bloqueo espacial;
- por tanto, la señal geográfica residual no parece ser solo memorizar zonas locales del train.

Implicancia para este repo:

- refuerza que sí vale la pena discutir y testear contexto/origen geográfico en la línea principal;
- y que el efecto espacial residual merece ser interpretado frente a demanda/oferta, no descartado a priori.

### 6. Rol del worktree ML respecto de OD-buffers

La decisión metodológica correcta quedó así:

- el worktree ML sirve para **screening** y **lectura incremental por bloques**;
- la línea principal de tesis sigue cerrándose en este repo con:
  - `MNL`,
  - OD-buffers,
  - interanual,
  - Censo / socio-demografía.

En otras palabras:

- `ML` ayuda a priorizar y ordenar;
- `tesis-project` sigue siendo el lugar donde se decide la especificación estructural final.

### 7. Resultado de la ronda socio/OSM en el worktree ML

En `tesis-project-ml`, el notebook:

- [`03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd)

se usó para hacer screening flexible de bloques `Censo + microdata + OSM` sobre el problema binario de adopción QR.

La lógica de esa ronda fue:

- primero correr bloques amplios temáticos y un bloque full interpretable:
  - `O_SOCIO_OSM_FULL`
  - `P_SPATIAL_SOCIO_OSM_FULL`
- luego construir una shortlist parsimoniosa:
  - `Q_SHORTLIST_SOCIO_OSM`
  - `R_SPATIAL_SHORTLIST_SOCIO_OSM`

Hallazgo principal:

- `R_SPATIAL_SHORTLIST_SOCIO_OSM` retuvo casi todo el desempeño de `P_SPATIAL_SOCIO_OSM_FULL` con mucha menos complejidad;
- por eso quedó como especificación compacta principal del frente ML;
- el bloque completo `O/P` sirvió para screening, pero no quedó como forma preferida de cerrar la historia.

Shortlist final retenida por el frente ML:

- `share_cine18_postgrado_micro`
- `share_cine18_universitaria_o_mas_micro`
- `osm_amenity_university`
- `share_discapacidad`
- `share_inmigrantes`
- `prom_edad`
- `osm_office_company`

Lectura SHAP final en el frente ML:

- la variable nueva más fuerte fue `share_cine18_postgrado_micro`;
- después sobrevivieron de forma consistente:
  - `osm_amenity_university`
  - `share_discapacidad`
  - `share_cine18_universitaria_o_mas_micro`
  - `share_inmigrantes`
  - `prom_edad`
  - `osm_office_company`
- varias variables que parecían fuertes al mirar bloques aislados perdieron peso al competir en el bloque full y frente a `x/y`, por ejemplo:
  - `share_hacinamiento`
  - `share_analfabet`
  - `share_internet`
  - `share_serv_compu`
  - `share_serv_tel_movil`
  - buena parte del bloque OSM comercial/recreativo más amplio

Referencia SHAP exacta más útil:

- `Q_SHORTLIST_SOCIO_OSM`:
  - `share_cine18_postgrado_micro = 0.087395`
  - `osm_amenity_university = 0.037523`
  - `share_discapacidad = 0.033763`
  - `share_cine18_universitaria_o_mas_micro = 0.030238`
  - `share_inmigrantes = 0.023758`
  - `prom_edad = 0.018722`
  - `osm_office_company = 0.014293`
- `R_SPATIAL_SHORTLIST_SOCIO_OSM`:
  - `share_cine18_postgrado_micro = 0.074255`
  - `osm_amenity_university = 0.029954`
  - `share_discapacidad = 0.022553`
  - `share_cine18_universitaria_o_mas_micro = 0.020094`
  - `share_inmigrantes = 0.014540`
  - `prom_edad = 0.013512`
  - `osm_office_company = 0.013216`

Implicancia para este repo:

- las variables de Censo y OSM ya estaban justificadas como candidatas desde sus workstreams propios;
- el frente ML agregó evidencia de **priorización relativa**:
  - qué variables sobreviven cuando compiten juntas;
  - cuáles siguen aportando aun controlando por `x/y`;
  - y cuáles se debilitan por redundancia o por actuar solo como proxies espaciales gruesos.

Conclusión puente útil para `tesis-project`:

- si se quiere una ruta parsimoniosa de integración de nuevos controles territoriales en la línea principal, la mejor base hoy no es el bloque socio/OSM completo, sino la shortlist anterior;
- además, el mapa espacial del frente ML sugiere que esa shortlist explica una parte importante de la geografía, pero no la agota por completo.

### 8. Tuning XGBoost sobre la shortlist

El frente ML también probó tuning espacial solo sobre:

- `R_SPATIAL_SHORTLIST_SOCIO_OSM`

Resultado:

- `spatial CV` seleccionó la configuración `medium_strict`;
- esa configuración mejoró la validación espacial interna;
- pero empeoró el holdout temporal `W17`.

Lectura puente:

- el tuning más conservador sirve como sensibilidad anti-overfit espacial;
- pero no cambia la decisión principal del worktree ML:
  - usar `R` base como especificación compacta principal;
  - y no leer el tuned como modelo final preferido.

### 9. Prueba conjunta de shortlist con demanda/oferta

Después de cerrar `Q/R`, el frente ML abrió una prueba adicional para no dejar separadas dos familias de variables que se habían evaluado en etapas distintas:

- `S_DEMAND_OFFER_SHORTLIST_SOCIO_OSM = baseline + demand/offer + shortlist`
- `T_SPATIAL_DEMAND_OFFER_SHORTLIST_SOCIO_OSM = baseline + x/y + demand/offer + shortlist`

Hallazgo principal:

- la prueba `S/T` sugiere que no hay reemplazo completo entre la shortlist territorial y el bloque `demanda + oferta`;
- hay evidencia de complementariedad parcial, especialmente por:
  - `LOG_DEMAND`
  - `LOG_BUS_LINE_COUNT`
  - `LOG_BUS_STOP_DENSITY`

SHAP exacto más útil:

- `S_DEMAND_OFFER_SHORTLIST_SOCIO_OSM`:
  - `share_cine18_postgrado_micro = 0.101788`
  - `share_discapacidad = 0.038907`
  - `LOG_DEMAND = 0.038193`
  - `osm_amenity_university = 0.025429`
  - `share_inmigrantes = 0.021535`
  - `share_cine18_universitaria_o_mas_micro = 0.017853`
  - `LOG_BUS_LINE_COUNT = 0.014470`
  - `LOG_BUS_STOP_DENSITY = 0.012767`
  - `osm_office_company = 0.011699`
  - `prom_edad = 0.011039`
  - `LOG_METRO_LINE_COUNT = 0.009598`
- `T_SPATIAL_DEMAND_OFFER_SHORTLIST_SOCIO_OSM`:
  - `share_cine18_postgrado_micro = 0.075058`
  - `Y_ORIGIN_M = 0.043995`
  - `LOG_DEMAND = 0.035600`
  - `X_ORIGIN_M = 0.034868`
  - `share_discapacidad = 0.024265`
  - `share_cine18_universitaria_o_mas_micro = 0.021920`
  - `osm_amenity_university = 0.017180`
  - `share_inmigrantes = 0.015499`
  - `LOG_BUS_LINE_COUNT = 0.012719`
  - `LOG_BUS_STOP_DENSITY = 0.008995`
  - `prom_edad = 0.008208`
  - `osm_office_company = 0.008158`
  - `LOG_METRO_LINE_COUNT = 0.002610`

Lectura puente:

- `LOG_DEMAND` sí sobrevive incluso cuando compite con la shortlist y con `x/y`;
- la oferta bus también sigue viva, aunque con menor peso;
- `LOG_METRO_LINE_COUNT` queda muy débil en esta combinación;
- por tanto, si la línea principal quiere una ruta parsimoniosa conjunta, el frente ML ahora sugiere mirar con más atención:
  - shortlist socio/OSM
  - `LOG_DEMAND`
  - `LOG_BUS_LINE_COUNT`
  - `LOG_BUS_STOP_DENSITY`

## Artefactos a mirar si hay que reconstruir el puente

### Bitácora canónica ML

- [`tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/notes.md)
- [`tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/task_plan.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/task_plan.md)

### Notebooks ML

- [`tesis-project-ml/03_models/ml_baselines/01_qr_adoption_baselines.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/03_models/ml_baselines/01_qr_adoption_baselines.qmd)
- [`tesis-project-ml/03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-ml/03_models/ml_baselines/02_qr_adoption_spatial_enriched.qmd)

### Repo principal afectado

- [`docs/planning/workstreams/od-buffers-nested-logit/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/od-buffers-nested-logit/notes.md)
- [`docs/planning/workstreams/od-buffers-nested-logit/task_plan.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/od-buffers-nested-logit/task_plan.md)
- [`docs/planning/workstreams/socio-demographics/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/socio-demographics/notes.md)

## Regla práctica de uso

Si una decisión nació en `tesis-project-ml` y afecta la línea principal:

1. la decisión detallada queda en el workstream canónico ML;
2. aquí se deja una síntesis puente si tiene impacto real en `od-buffers` o `socio-demographics`;
3. la especificación final y su interpretación siguen cerrándose en `tesis-project`.
