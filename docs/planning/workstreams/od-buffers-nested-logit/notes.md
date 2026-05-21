# Notes — Nested Logit con Buffers OD (Option1 alt-specific)

## 2026-05-13 — Reuniones con profesores: reordenamiento metodológico y próximos frentes
- Se registran dos reuniones docentes con énfasis complementarios:
  - la profesora guía enfocó la discusión en la validez y depuración del modelo de elección discreta;
  - el profesor codirector enfatizó comparación predictiva flexible, visualizaciones y síntesis comunicable de resultados.

### Directrices metodológicas de la profesora
- Revisar la especificación actual de tiempos y transbordos:
  - sacar promedios zonales de variables como tiempos de viaje, esperas y número de transbordos cuando corresponda;
  - estimar MNL y Nested Logit usando valores observados a nivel de viaje;
  - mantener `BIP` como alternativa base para variables comunes.
- Agregar controles de macrozona como variables dummy:
  - ejemplos: sector oriente, poniente, sur y norte;
  - definir explícitamente una macrozona base;
  - evaluar cómo cambian los coeficientes territoriales después de controlar por macrozona.
- Depurar variables potencialmente redundantes o menos interpretables:
  - `shelter` podría competir con densidad de paraderos;
  - `convenience` puede ser difícil de interpretar sustantivamente;
  - `hacinamiento` puede competir con los proxies EOD de ingreso;
  - la depuración debe hacerse después de observar la estabilidad de signos al controlar por macrozona.
- Explorar segmentación y clases latentes:
  - revisar el paper de inercia de la profesora como referencia metodológica;
  - revisar el paper local:
    - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/papers/1-s2.0-S2214367X23000716-main.pdf`;
  - considerar indicadores `DSI`, `LSI` y `TSI` como base para segmentación;
  - usar segmentos para correr modelos separados o, si es factible, avanzar hacia clases latentes.

### Directrices metodológicas del profesor codirector
- Estimar un modelo `XGBoost` con función de pérdida logit como benchmark flexible:
  - motivación: los modelos de elección discreta tradicionales imponen supuestos y requisitos que los datos pueden no cumplir;
  - los modelos basados en árboles relajan varios de esos supuestos y pueden mejorar flexibilidad/accuracy;
  - la pérdida de interpretabilidad puede compensarse parcialmente con `SHAP`.
- Preparar un resumen de una página con:
  - resultados experimentales ya listos;
  - experimentos faltantes;
  - ejemplo: qué modelos logit ya se estimaron, qué modelos quedan por contrastar y qué análisis predictivos faltan.
- Incorporar visualizaciones de datos y resultados:
  - mapas de variables territoriales;
  - mapas de patrones observados de uso de `BIP`, `QR_OTHER` y `QR_RED`;
  - distribuciones de tiempos, esperas y transbordos por alternativa;
  - visualizaciones de resultados espaciales y, eventualmente, `SHAP`.
- Avanzar en escritura:
  - redactar un abstract preliminar con potenciales conclusiones;
  - comenzar a bosquejar discusión y conclusiones si los resultados centrales ya permiten una narrativa defendible.

### Lectura integrada y priorización
- Las directrices no son contradictorias, pero sí deben ordenarse para evitar dispersión.
- Prioridad metodológica inmediata:
  - estabilizar el modelo econométrico base con valores observados a nivel de viaje;
  - agregar macrozonas como controles territoriales amplios;
  - comparar MNL vs Nested bajo esta especificación;
  - recién después depurar variables redundantes.
- Prioridad comparativa:
  - usar `XGBoost + SHAP` como benchmark predictivo flexible, no como reemplazo inmediato del logit;
  - presentar la comparación como contraste entre interpretación estructural y flexibilidad predictiva.
- Prioridad exploratoria:
  - dejar segmentación/clases latentes como segunda fase, después de estabilizar el modelo base;
  - comenzar por indicadores descriptivos de inercia/regularidad (`DSI`, `LSI`, `TSI`) antes de saltar a clases latentes completas.
- Prioridad comunicacional:
  - producir visualizaciones espaciales y de distribución;
  - preparar resumen ejecutivo de una página;
  - redactar abstract preliminar y posibles conclusiones.

### Decisiones provisionales
- La especificación territorial con Censo, OSM y EOD sigue siendo útil como línea de trabajo, pero debe contrastarse contra una versión con atributos observados de viaje y macrozonas.
- Los proxies EOD de ingreso quedan activos como variables candidatas, no como cierre definitivo.
- `eod2012_numveh_mean_z` queda como sensibilidad diagnóstica, no como variable central junto con ingreso por colinealidad conceptual y empírica.
- El frente `XGBoost + SHAP` se tratará como benchmark externo de robustez/predicción.
- La segmentación por inercia/clases latentes queda priorizada después de cerrar una especificación MNL/Nested más limpia.

## 2026-04-29 — Decisión editorial para reporte informal del modelo logit territorial
- Se decidió preparar un reporte LaTeX independiente e informal, separado del manuscrito principal de tesis.
- Ubicación acordada dentro de este repo:
  - `docs/reports/modelo-logit-territorial/reporte_modelo_logit.tex`
- Decisión de organización:
  - crear un reporte autónomo dentro de `docs/reports/`;
  - no usar la carpeta externa de Seminario Tesis para este entregable;
  - no agregar portada ni índice.
- Estructura acordada del reporte:
  - descripción del problema y alternativas (`BIP`, `QR_RED`, `QR_OTHER`);
  - especificación MNL y función de utilidad;
  - variables base, Censo, OSM y microinfraestructura, con definiciones;
  - estrategia de estimación y muestra;
  - tabla de ajuste/convergencia del modelo elegido;
  - tabla wide de parámetros;
  - interpretación de signos/significancia por alternativa;
  - decisión de modelo principal y sensibilidades.
- Modelo principal a reportar:
  - `mnl_joint_censo_main_4_plus_osm_main_plus_subway_entrance`
- Sensibilidad a reportar:
  - `mnl_joint_censo_main_4_plus_osm_main_plus_transport_shelter_subway_entrance`

## 2026-04-29 — Decisión sobre microinfraestructura OSM en modelos conjuntos `Censo + OSM`
- Notebook operativo:
  - [`03_models/14_territorial_stepwise_mnl_nested.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/14_territorial_stepwise_mnl_nested.qmd)
- Contexto:
  - tras cerrar el bloque conjunto `Censo main_4 + OSM main`, se exploró si OSM podía aportar variables más accionables para política pública relacionadas con infraestructura/acceso a paraderos y estaciones;
  - se auditó `OSM Map Features` y el export local OSM de `ZONA777` antes de incluir variables nuevas.
- Variables auditadas:
  - `shelter=yes`
  - `bench=yes`
  - `wheelchair=yes`
  - `railway=subway_entrance`
  - `highway=crossing`
  - `crossing=traffic_signals`
  - `highway=traffic_signals`
  - `highway=elevator`
  - `shop=ticket`
  - `amenity=bus_station`
- Decisión de construcción:
  - no usar `wheelchair=yes` cruda porque solo una parte menor de los objetos era claramente transport-like;
  - no usar cruces/semaforos en el modelo principal porque son demasiado transversales y no específicos de experiencia de pago/acceso al transporte;
  - no usar `shop=ticket` ni `amenity=bus_station` por baja cobertura y mezcla conceptual;
  - construir versiones filtradas para infraestructura de espera:
    - `osm_transport_shelter_yes_density_km2_z`
    - `osm_transport_bench_yes_density_km2_z`
  - usar directamente:
    - `osm_railway_subway_entrance_density_km2_z`
- Definición práctica de `shelter`:
  - en OSM, `shelter=yes` indica que el objeto tiene una estructura física de resguardo/cubierta asociada a otro elemento, comúnmente `highway=bus_stop` o `public_transport=platform`;
  - en este proyecto se usa filtrado a objetos transport-like, por lo que `osm_transport_shelter_yes_density_km2_z` debe interpretarse como densidad zonal estandarizada de paraderos/plataformas con refugio/cubierta reportada en OSM;
  - es proxy de calidad básica de espera, no de calidad completa del paradero: no garantiza banca, iluminación, información al usuario ni estado físico.
- Ronda incremental inicial sobre `Censo main_4 + OSM main` (`sample2pct`, Biogeme):
  - `+ transport_shelter`: `LL = -232278.4`, `AIC = 464676.7`, `BIC = 465339.9`.
  - `+ transport_shelter + transport_bench`: `LL = -232272.2`, `AIC = 464670.5`, `BIC = 465366.9`.
  - `+ transport_shelter + transport_bench + subway_entrance`: `LL = -232252.1`, `AIC = 464636.3`, `BIC = 465365.8`.
  - benchmark `Censo main_4 + OSM main`: `LL = -232294.6`, `AIC = 464703.1`, `BIC = 465333.2`.
- Lectura de la ronda incremental:
  - las tres variantes mejoran `LL` y `AIC`;
  - `BIC` no mejora en las variantes incrementales que incluyen `shelter`/`bench` bajo esa ruta;
  - `bench` queda relegada por menor parsimonia y señal menos necesaria;
  - `subway_entrance` aparece como la candidata más fuerte, por lo que se corrieron checks directos sin `bench`.
- Checks directos agregados:
  - `mnl_joint_censo_main_4_plus_osm_main_plus_subway_entrance`
  - `mnl_joint_censo_main_4_plus_osm_main_plus_transport_shelter_subway_entrance`
- Resultados de checks directos (`sample2pct`, Biogeme):
  - `main + subway_entrance`: `LL = -232268.5`, `AIC = 464657.0`, `BIC = 465320.2`, convergencia YAML verdadera.
  - `main + shelter + subway_entrance`: `LL = -232257.1`, `AIC = 464640.2`, `BIC = 465336.6`, convergencia YAML verdadera.
- Comparación contra benchmark `main`:
  - `main + subway_entrance` mejora simultáneamente `LL`, `AIC` y `BIC`:
    - `Delta LL ≈ +26.1`
    - `Delta AIC ≈ -46.1`
    - `Delta BIC ≈ -13.0`
  - `main + shelter + subway_entrance` mejora más `LL` y `AIC`, pero queda levemente peor que el benchmark en `BIC`:
    - `Delta LL ≈ +37.5`
    - `Delta AIC ≈ -62.9`
    - `Delta BIC ≈ +3.4`
- Parámetros clave:
  - En `main + subway_entrance`, `osm_railway_subway_entrance_density_km2_z`:
    - `BIP`: positivo y significativo (`beta ≈ 0.0167`, `t ≈ 6.76`);
    - `QR_OTHER`: prácticamente cero y no significativo;
    - `QR_RED`: negativo y significativo (`beta ≈ -0.0166`, `t ≈ -3.78`).
  - En `main + shelter + subway_entrance`, `osm_railway_subway_entrance_density_km2_z` mantiene el patrón:
    - `BIP`: positivo y significativo;
    - `QR_OTHER`: no significativo;
    - `QR_RED`: negativo y significativo.
  - En `main + shelter + subway_entrance`, `osm_transport_shelter_yes_density_km2_z`:
    - `BIP`: no significativo;
    - `QR_OTHER`: negativo y significativo;
    - `QR_RED`: positivo y significativo.
- Lectura sustantiva:
  - `subway_entrance` capta acceso físico/centralidad de Metro y desplaza utilidad hacia `BIP` más que hacia `QR_RED`;
  - `shelter` capta infraestructura de espera de superficie y tiene una lectura de política pública más accionable, favoreciendo `QR_RED` frente a `QR_OTHER`;
  - agregar `shelter` no desordena fuertemente parámetros base ni parámetros territoriales principales: tiempos, transbordos, demanda, educación, discapacidad, hacinamiento e inmigrantes mantienen signos y magnitudes razonables.
- Decisión:
  - actualizar el candidato principal conjunto a:
    - `mnl_joint_censo_main_4_plus_osm_main_plus_subway_entrance`
  - mantener como sensibilidad/política pública:
    - `mnl_joint_censo_main_4_plus_osm_main_plus_transport_shelter_subway_entrance`
  - no incluir `transport_bench` en el modelo principal;
  - reportar `shelter` con cautela: es conceptualmente valiosa y accionable, pero no gana la comparación de parsimonia por `BIC` frente al modelo con solo `subway_entrance`.

## 2026-04-28 — Decisión sobre auditoría Larch para modelos conjuntos `Censo + OSM`
- Notebook de auditoría:
  - [`03_models/larch_logit/14_territorial_stepwise_mnl_larch.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/larch_logit/14_territorial_stepwise_mnl_larch.qmd)
- Modelos auditados:
  - `mnl_larch_joint_censo_main_4`
  - `mnl_larch_joint_censo_main_4_plus_osm_main`
  - `mnl_larch_joint_censo_main_4_compu_plus_osm_main`
- Evidencia de ajuste en Larch:
  - `sample2pct` (`n = 466639`): `LL/caso = -0.498009`, `-0.497804`, `-0.497760`, respectivamente.
  - `sample5pct` (`n = 933276`): `LL/caso = -0.497631`, `-0.497421`, `-0.497389`, respectivamente.
  - `sample10pct` (`n = 1866552`): `LL/caso = -0.497666`, `-0.497471`, `-0.497448`, respectivamente.
- Lectura:
  - el ranking de ajuste es estable en los tres tamaños muestrales: `compu + osm_main` mejora más, `osm_main` queda segundo y `censo_main_4` funciona como benchmark conservador;
  - los niveles de `LL/caso` son prácticamente invariantes entre `2pct`, `5pct` y `10pct`, por lo que no hay señal de que el resultado dependa críticamente del sampleo;
  - Larch permitió escalar hasta `sample10pct` sin el crash de RAM observado en Biogeme, por lo que sirve como chequeo fuerte de factibilidad computacional y estabilidad de ranking;
  - los betas son razonablemente comparables en signo y magnitud con Biogeme, especialmente para la estructura principal del modelo, pero la inferencia de Larch no es suficientemente confiable para reportar.
- Problema de inferencia en Larch:
  - varias variables territoriales tuvieron errores estándar robustos nulos o faltantes, y la inferencia clásica tampoco resolvió limpiamente el problema;
  - esto es consistente con una debilidad de identificación/covarianza para variables territoriales comunes a todas las alternativas dentro de una observación, estimadas con coeficientes alternativo-específicos;
  - por lo tanto, Larch no se usará para decidir significancia estadística ni para reemplazar las tablas principales de Biogeme.
- Decisión:
  - usar Biogeme como fuente canónica para parámetros, errores robustos, `t` y `p`;
  - usar Larch como confirmación externa de ranking, estabilidad muestral y factibilidad de memoria;
  - no seguir insistiendo en corregir la inferencia de Larch para esta etapa, porque no cambia la decisión sustantiva y puede consumir tiempo sin aportar una tabla reportable;
  - mantener como modelo conjunto principal `mnl_joint_censo_main_4_plus_osm_main`;
  - mantener `mnl_joint_censo_main_4_compu_plus_osm_main` como sensibilidad ampliada y `mnl_joint_censo_main_4` como benchmark conservador.
- Nota posterior:
  - esta decisión fue actualizada el `2026-04-29` tras la ronda de microinfraestructura OSM;
  - el nuevo candidato principal conjunto pasa a ser `mnl_joint_censo_main_4_plus_osm_main_plus_subway_entrance`.

## 2026-04-27 — Primeros modelos conjuntos `Censo + OSM` y ajuste de memoria en notebook `14`
- Corrida conjunta `joint_mnl_censo_to_osm_route_a` en `sample5pct` cayó por RAM en:
  - `mnl_joint_censo_main_4_plus_sports_convenience_playground`
- Modelos alcanzados antes del crash:
  - `mnl_joint_censo_main_4`: `LL = -464427.2`, `AIC = 928938.4`, `BIC = 929431.8`.
  - `mnl_joint_censo_main_4_plus_sports`: `LL = -464396.4`, `AIC = 928882.7`, `BIC = 929411.3`.
  - `mnl_joint_censo_main_4_plus_sports_convenience`: `LL = -464386.7`, `AIC = 928869.4`, `BIC = 929433.2`.
- Lectura:
  - el primer modelo conjunto replica exactamente el `Censo main_4`, por lo que la muestra conjunta no cambió la base efectiva;
  - agregar `sports_centre` sobre Censo mejora claramente el ajuste (`Delta LL = +30.8`, `Delta AIC = -55.7`, `Delta BIC = -20.5`);
  - agregar `convenience` sobre `Censo + sports` mejora poco en LL/AIC (`Delta LL = +9.7`, `Delta AIC = -13.3`) pero empeora BIC (`Delta BIC = +21.9`), por lo que su retención queda pendiente de los modelos con `playground`, `school` y `university`.
- Diagnóstico técnico:
  - el crash probablemente fue amplificado por `run-screening`, que cacheaba una muestra pandas distinta por cada conjunto de variables;
  - en rutas stepwise, cada especificación tiene `extra_cols` distinto, por lo que el notebook podía mantener varias copias grandes en memoria.
- Cambio aplicado:
  - `run-screening` ya no usa `sample_cache`;
  - cada modelo carga su muestra pandas, estima, escribe artefactos y libera objetos antes del siguiente modelo;
  - se agregó `ACTIVE_PRESET = "joint_mnl_censo_to_osm_route_a_missing"` para correr solo los 5 modelos pendientes.
- Decisión operativa:
  - no bajar todavía el sampleo;
  - primero reintentar `sample5pct` con el preset de faltantes y el uso de memoria corregido;
  - si vuelve a caer, pasar a correr los pendientes de a uno o bajar muestra como último recurso.
- Actualización tras reintento:
  - el kernel volvió a caer en el mismo modelo (`mnl_joint_censo_main_4_plus_sports_convenience_playground`);
  - no quedaron artefactos parciales para ese modelo;
  - por lo tanto, el problema ya no parece ser acumulación por cache entre modelos, sino memoria pico dentro de la estimación de Biogeme para especificaciones conjuntas más anchas en `sample5pct`.
- Decisión operativa actualizada:
  - rehacer la ruta conjunta completa en `sample2pct` con el mismo optimizador (`automatic` + derivadas analíticas), para mantener comparabilidad interna entre los 8 modelos conjuntos;
  - no mezclar los 3 resultados `sample5pct` con los 5 resultados pendientes en `sample2pct`;
  - si `sample2pct` converge y ordena claramente los candidatos, usarlo como screening conjunto y dejar `sample5pct` como evidencia de que los primeros modelos son estables;
  - si hace falta una estimación final de un candidato grande en `sample5pct`, considerar correr solo ese modelo en una máquina con más RAM o como sensibilidad con optimizador sin Hessiana, dejando explícito el cambio metodológico.
- Auditoría Larch:
  - se agregó `03_models/larch_logit/14_territorial_stepwise_mnl_larch.qmd` como réplica MNL específica para la ruta conjunta A;
  - usa la misma muestra `sample2pct-censo4-micro-osm`, las mismas variables y coeficientes territoriales para `BIP`, `QR_RED` y `QR_OTHER`;
  - quedó configurado por defecto para correr solo los tres modelos de auditoría final: `main_4`, `main_4 + osm_main` y `main_4 + compu + osm_main`;
  - su propósito es auditar robustez/ranking y factibilidad de memoria, no reemplazar automáticamente a Biogeme, porque auditorías previas ya mostraron diferencias framework/optimización en modelos más simples.

## 2026-04-27 — Cierre provisional bloque OSM en notebook territorial `14`
- Notebook operativo:
  - [`03_models/14_territorial_stepwise_mnl_nested.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/14_territorial_stepwise_mnl_nested.qmd)
- Decisión:
  - usar como candidato OSM principal el bloque:
    - `osm_leisure_sports_centre_density_km2_z`
    - `osm_shop_convenience_density_km2_z`
    - `osm_leisure_playground_density_km2_z`
    - `osm_amenity_school_density_km2_z`
    - `osm_amenity_university_density_km2_z`
  - mantener como sensibilidad parsimoniosa:
    - `osm_leisure_sports_centre_density_km2_z`
    - `osm_shop_convenience_density_km2_z`
    - `osm_amenity_school_density_km2_z`
    - `osm_amenity_university_density_km2_z`
  - no incluir `osm_office_company_density_km2_z` en el candidato principal OSM, aunque queda como sensibilidad conceptual por su aparición en el frente ML.
- Evidencia `sample5pct`:
  - antiguo mejor OSM de primera ronda (`sports + convenience + office + playground + school`): `LL = -466590.0`, `AIC = 933270.0`, `BIC = 933798.6`.
  - nuevo candidato principal (`sports + convenience + playground + school + university`): `LL = -466387.0`, `AIC = 932864.0`, `BIC = 933392.6`.
  - sensibilidad parsimoniosa (`sports + convenience + school + university`): `LL = -466477.2`, `AIC = 933038.3`, `BIC = 933531.7`.
- Lectura:
  - `university` no reemplaza a `convenience`, pero sí aporta fuertemente sobre la ruta OSM ya fuerte;
  - `office_company` queda débil/inestable cuando compite con `university`, especialmente frente a QR_RED;
  - `school` aporta una señal territorial distinta, con signo opuesto al bloque de centralidad/actividad;
  - las variables base del modelo (`T_ESPERA_*`, `N_TRASB`, `LOG_BUS_STOP_DENSITY`, `LOG_DEMAND`) se mantienen razonablemente estables, por lo que el bloque OSM no parece romper la especificación.
- Variables OSM descartadas o relegadas:
  - `restaurant`: muy competitivo en univariados, pero la ruta `convenience` domina al pasar a stepwise;
  - `office_company`: sensibilidad, no principal;
  - `mall`, `supermarket`, `pharmacy`, `government`, `park`: no prioritarias para la primera especificación conjunta.
- Siguiente paso operativo:
  - preparar modelos conjuntos `Censo + OSM` usando:
    - Censo principal: `mnl_censo_stepwise_main_4`;
    - Censo sensibilidad: `mnl_censo_connectivity_main_4_plus_compu`;
    - OSM principal: `sports + convenience + playground + school + university`;
    - OSM sensibilidad: `sports + convenience + school + university`.

## 2026-04-26 — Cierre provisional bloque Censo en notebook territorial `14`
- Notebook operativo:
  - [`03_models/14_territorial_stepwise_mnl_nested.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/14_territorial_stepwise_mnl_nested.qmd)
- Decisión:
  - usar `mnl_censo_stepwise_main_4` como candidato Censo principal;
  - mantener `mnl_censo_connectivity_main_4_plus_compu` como sensibilidad Censo;
  - descartar `share_internet_z` como extensión principal del bloque Censo por baja señal marginal.
- Especificación Censo principal (`main_4`):
  - `share_cine18_universitaria_o_mas_micro_z`
  - `share_hacinamiento_z`
  - `share_discapacidad_z`
  - `share_inmigrantes_z`
- Resultado principal `sample5pct`:
  - `main_4`: `LL = -464427.2`, `AIC = 928938.4`, `BIC = 929431.8`, convergencia Biogeme YAML verdadera.
  - `main_4 + compu`: `LL = -464395.4`, `AIC = 928880.9`, `BIC = 929409.5`, convergencia Biogeme YAML verdadera.
- Lectura:
  - `main_4 + compu` mejora AIC/BIC y `share_serv_compu_z` tiene señal robusta para `QR_RED` y `QR_OTHER`;
  - pero también mueve la interpretación de `hacinamiento`/`discapacidad`, probablemente por solapamiento socioeconómico;
  - por eso queda como sensibilidad, no como reemplazo automático del candidato principal.
- Modelos alternativos sin educación estimados como chequeo:
  - `compu + hacinamiento + discapacidad + inmigrantes`: `LL = -464906.5`, `AIC = 929897.0`, `BIC = 930390.3`.
  - `internet + hacinamiento + discapacidad + inmigrantes`: `LL = -465087.0`, `AIC = 930257.9`, `BIC = 930751.3`.
  - ambos quedan claramente por debajo de `main_4`, lo que refuerza que la señal de educación debe mantenerse en el bloque Censo.
- Siguiente paso operativo:
  - pasar a OSM univariado MNL en `sample5pct`, con coeficientes para `BIP`, `QR_RED` y `QR_OTHER`, antes de construir un bloque OSM stepwise.

## 2026-04-23 — Síntesis puente actualizada desde `tesis-project-ml` para variables Censo + OSM
- Se revisó el estado del worktree paralelo `tesis-project-ml` y se actualizó la síntesis puente de sus hallazgos más recientes en:
  - [`docs/planning/workstreams/od-buffers-nested-logit/ml_worktree_sync.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/od-buffers-nested-logit/ml_worktree_sync.md)
- Confirmación importante:
  - las variables de Censo y OSM ya estaban documentadas por separado en este repo;
  - lo que faltaba dejar explícito era la lectura integrada desde el frente ML sobre cuáles sobreviven cuando compiten juntas y frente a `x/y`.
- Hallazgo puente principal desde `tesis-project-ml`:
  - el bloque amplio `O/P` sirvió para screening;
  - pero la especificación compacta preferida quedó en `R_SPATIAL_SHORTLIST_SOCIO_OSM`.
- Shortlist final retenida por el frente ML:
  - `share_cine18_postgrado_micro`
  - `share_cine18_universitaria_o_mas_micro`
  - `osm_amenity_university`
  - `share_discapacidad`
  - `share_inmigrantes`
  - `prom_edad`
  - `osm_office_company`
- SHAP exacto relevante en la ronda final del frente ML:
  - bloque `Q_SHORTLIST_SOCIO_OSM` (`mean_abs_shap`):
    - `share_cine18_postgrado_micro = 0.087395`
    - `osm_amenity_university = 0.037523`
    - `share_discapacidad = 0.033763`
    - `share_cine18_universitaria_o_mas_micro = 0.030238`
    - `share_inmigrantes = 0.023758`
    - `prom_edad = 0.018722`
    - `osm_office_company = 0.014293`
  - bloque `R_SPATIAL_SHORTLIST_SOCIO_OSM` (`mean_abs_shap`):
    - `share_cine18_postgrado_micro = 0.074255`
    - `Y_ORIGIN_M = 0.046112`
    - `X_ORIGIN_M = 0.036493`
    - `osm_amenity_university = 0.029954`
    - `share_discapacidad = 0.022553`
    - `share_cine18_universitaria_o_mas_micro = 0.020094`
    - `share_inmigrantes = 0.014540`
    - `prom_edad = 0.013512`
    - `osm_office_company = 0.013216`
- SHAP del bloque full también dejó una referencia útil:
  - en `O_SOCIO_OSM_FULL`, las variables nuevas más altas fueron:
    - `share_cine18_postgrado_micro = 0.083165`
    - `osm_amenity_university = 0.023519`
    - `share_discapacidad = 0.022670`
    - `share_inmigrantes = 0.020604`
    - `share_cine18_universitaria_o_mas_micro = 0.018527`
    - `osm_office_company = 0.017213`
    - `osm_amenity_pharmacy = 0.015367`
  - en `P_SPATIAL_SOCIO_OSM_FULL`, las variables nuevas que mejor sobrevivieron frente a `x/y` fueron:
    - `share_cine18_postgrado_micro = 0.080821`
    - `osm_amenity_university = 0.019936`
    - `share_discapacidad = 0.012169`
    - `share_inmigrantes = 0.011890`
    - `prom_edad = 0.010929`
    - `osm_office_company = 0.010760`
    - `share_cine18_universitaria_o_mas_micro = 0.010445`
- Lectura útil para este repo:
  - `share_cine18_postgrado_micro` emerge como la señal nueva más fuerte;
  - `osm_amenity_university` también sobrevive de manera consistente;
  - varias variables que parecían prometedoras en screening aislado pierden fuerza en el bloque full, especialmente:
    - `share_hacinamiento`
    - `share_analfabet`
    - `share_internet`
    - `share_serv_compu`
    - `share_serv_tel_movil`
    - varias OSM comerciales/recreativas secundarias
- Implicancia metodológica:
  - si la línea principal quiere una ruta parsimoniosa de integración territorial, hoy la mejor base puente no es el bloque socio/OSM completo sino esta shortlist priorizada;
  - aun así, el frente ML sigue mostrando residuo espacial después de controlar por esa shortlist, así que no conviene sobreleerla como explicación exhaustiva de la geografía.
- Resultado adicional del tuning en ML:
  - el tuning espacial de `R` mejoró `spatial CV`, pero empeoró el holdout temporal `W17`;
  - por tanto, en el frente ML quedó solo como sensibilidad anti-overfit espacial, no como especificación principal.
- Resultado adicional más reciente del frente ML:
  - se probó explícitamente la combinación conjunta:
    - `S_DEMAND_OFFER_SHORTLIST_SOCIO_OSM = baseline + demand/offer + shortlist`
    - `T_SPATIAL_DEMAND_OFFER_SHORTLIST_SOCIO_OSM = baseline + x/y + demand/offer + shortlist`
  - SHAP exacto relevante en `S`:
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
  - SHAP exacto relevante en `T`:
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
  - lectura puente:
    - `LOG_DEMAND` sí sobrevive al competir con la shortlist, incluso con `x/y`;
    - la oferta bus también sobrevive, especialmente vía `LOG_BUS_LINE_COUNT`;
    - `LOG_METRO_LINE_COUNT` queda mucho más débil en la combinación conjunta;
    - por tanto, ya no corresponde decir simplemente que “queda pendiente ver si demanda/oferta deben mantenerse”: el frente ML ahora sugiere complementariedad parcial entre shortlist y bloque `demanda + oferta`, sobre todo por el lado de demanda y bus.

## 2026-04-14 — Sincronización explícita con worktree `tesis-project-ml`
- Se formalizó el puente documental con el worktree paralelo de ML:
  - [`docs/planning/workstreams/od-buffers-nested-logit/ml_worktree_sync.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/od-buffers-nested-logit/ml_worktree_sync.md)
- Propósito:
  - dejar reconstruible, desde este repo, qué decisiones nacieron en `tesis-project-ml` y cómo impactan la línea principal;
  - evitar duplicar toda la bitácora ML dentro de `tesis-project`;
  - mantener una separación clara entre:
    - fuente canónica del frente ML (`tesis-project-ml/docs/planning/workstreams/ml-baselines-shap/`);
    - síntesis puente de implicancias para `od-buffers` y la tesis principal.
- Regla acordada:
  - las decisiones detalladas de ML viven en el otro worktree;
  - este repo solo registra la síntesis de impacto metodológico cuando afecte la línea principal.

## 2026-03-31 — Investigación preliminar de variable de ingresos
- Se revisó el diccionario local del Censo 2024 ya integrado al proyecto:
  - `tmp/censo2024/diccionario_variables_glosas_censo2024.csv`
  - `docs/diccionario_censo2024_vars.md`
- Hallazgo:
  - el bloque disponible contiene variables de vivienda, hogar, educación, migración, discapacidad, alfabetización, empleo y TIC;
  - no aparece ninguna variable directa de ingreso, renta, sueldo, salario o ingreso monetario del hogar/persona.
- Se contrastó con la documentación oficial del cuestionario Censo 2024:
  - `https://censo2024.ine.gob.cl/cuestionario-censal/`
  - el cuestionario menciona empleo/ocupación, vivienda, servicios, educación, discapacidad, migración, etc., pero no ingresos.
- Se investigó la ESI como fuente alternativa oficial de ingresos:
  - la documentación metodológica oficial de la serie ENE-ESI indica que en las bases existe información de comuna de residencia/trabajo, pero la encuesta **no tiene representatividad comunal**; sus dominios oficiales son nacional, nacional urbano/rural y regional urbano/rural.
  - fuente: `https://www.ine.gob.cl/docs/default-source/encuesta-suplementaria-de-ingresos/metodologia/documento-metodol%C3%B3gico/documento-metodol%C3%B3gico---esi-2023.pdf` (pp. 82-83 aprox., líneas 3319-3325 en extractor web).
- Implicancia metodológica:
  - no es válido hacer un join "directo" ESI -> `ZONA777` para construir una variable de ingresos observada por zona;
  - si se quiere usar ESI, tendría que ser como insumo para una estrategia de **small-area estimation** o para calibrar un **proxy/factor socioeconómico** construido con Censo.
- Alternativa oficial complementaria revisada:
  - la EPF sí mide ingresos del hogar, pero su cobertura oficial es hogares urbanos de capitales regionales y zonas conurbadas; tampoco entrega una vía directa limpia para `ZONA777`.

## 2026-03-31 — Validez de la agregación Censo -> ZONA777 vs método de asignación comunal a celdas
- Se revisó el post de Eduardo Graells-Garrido:
  - `https://datagramas.cl/2026/01/cuando-los-datos-no-tienen-ubicación-un-método-para-asignar-viviendas-censales/`
- Distinción metodológica clave:
  - el post resuelve un problema de **microdatos comunales sin ubicación intra-comunal**, asignando viviendas a celdas mediante una heurística con capacidad, atributos y simulated annealing;
  - nuestro pipeline `lib/censo2024_zona777.py` resuelve un problema más simple: **interpolación areal** desde entidades/manzanas censales ya georreferenciadas a polígonos `ZONA777`.
- Qué hace hoy el pipeline:
  - une indicadores censales agregados por `MANZENT` con cartografía;
  - intersecta esas geometrías con `ZONA777`;
  - reparte conteos/denominadores por `area_share`;
  - luego reconstruye medias ponderadas y shares a nivel `ZONA777`.
- Lectura:
  - para variables ya disponibles como indicadores georreferenciados por entidad/manzana (educación, internet, computador, hacinamiento, etc.), nuestra aproximación sigue siendo razonable como interpolación areal, con el caveat estándar de homogeneidad intra-polígono;
  - para variables **no disponibles** a ese nivel y solo observables en microdatos comunales, el post sí ofrece una ruta más válida que una distribución uniforme;
  - para variables de ingreso provenientes de **encuestas externas** como ESI/CASEN, el post no aplica directamente: ahí el problema ya no es "asignar microdatos del mismo censo usando restricciones por manzana", sino hacer `small-area estimation` o microsimulación con otra fuente.

## 2026-03-31 — Inventario de microdatos Censo 2024 vs agregado espacial
- Se inspeccionaron los headers de los zips ya descargados en `/Volumes/KINGSTON/tesis-project/raw/censo2024/`.
- Confirmación:
  - `personas`, `hogares` y `viviendas` traen solo `region`, `provincia`, `comuna`;
  - no traen `MANZENT` ni otra llave espacial fina.
- Se creó un resumen reusable en:
  - [`docs/censo2024_microdatos_vs_agregados.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/censo2024_microdatos_vs_agregados.md)
- Hallazgos principales:
  - varias variables ya usadas (`escolaridad`, `discapacidad`, `internet`, `compu`, `hacinamiento`) están representadas en el agregado `manzana-entidad`;
  - hay candidatas nuevas solo visibles en microdatos comunales o no explotadas aún (`tenencia`, `materialidad`, `agua`, `saneamiento`, `tipologia_hogar`, `llegada_periodo`, `nacionalidad`, etc.);
  - no aparecen variables directas de ingreso en estos microdatos.

## 2026-03-31 — ¿Vale la pena aplicar el método de asignación comunal a celdas?
- Revisión del diccionario completo del agregado `manzana-entidad` muestra que todavía quedan muchas variables útiles **ya disponibles sin asignación heurística**:
  - composición de hogar: `n_hog_unipersonales`, `n_hog_60`, `n_hog_menores`
  - acceso digital más fino: `n_serv_internet_fija`, `n_serv_internet_movil`, `n_serv_internet_satelital`, `n_serv_tablet`
  - calidad/vulnerabilidad habitacional: `n_viv_irrecuperables`, `n_hog_allegados`, `n_nucleos_hacinados_allegados`, `n_viv_no_ampliables`
  - inserción laboral: `n_fuera_fuerza_trabajo`, `n_ciuo_*`, `n_caenes_*`
  - patrón modal laboral: `n_transporte_auto`, `n_transporte_bicicleta`, `n_transporte_camina`, `n_transporte_publico`
  - tenencia y servicios básicos: `n_tenencia_*`, `n_fuente_agua_*`, `n_serv_hig_*`, `n_fuente_elect_*`, `n_basura_*`
- Juicio metodológico:
  - **todavía no vale la pena** abrir el frente de asignación heurística comuna -> celdas/ZONA777;
  - primero conviene explotar mejor el agregado manzana-entidad, porque evita una capa extra de error de modelación espacial.
- Solo tendría sentido usar el método del post si aparece una variable **realmente prioritaria** y **solo disponible** en microdatos comunales, por ejemplo:
  - `p26_llegada_periodo` (recencia migratoria)
  - `p27_nacionalidad` detallada
  - `tipologia_hogar`
  - alguna otra no representada en el agregado espacial.

## 2026-03-25 — Fix a terminals stale tras reconstrucción Metro
- Root cause confirmado en `01_processing/04_transbordos_metro.qmd`:
  - la reconstrucción rehacía las patas `paradero_*_i`, `srv_i`, `tipo_transporte_i`, `zona_*_i`, `tiempo_*_i`;
  - pero dejaba stale los campos agregados de viaje:
    - `paradero_inicio_viaje`
    - `paradero_fin_viaje`
    - `zona_inicio_viaje`
    - `zona_fin_viaje`
- Se implementó un fix mínimo con helper nueva:
  - `lib/transbordos_metro/reconstruction.py`
  - `sync_trip_level_terminals_from_legs(...)`
- Integración del fix:
  - `01_processing/04_transbordos_metro.qmd`
  - `lib/transbordos_metro/__init__.py`
- Regression test agregado:
  - `lib/test_transbordos_metro_reconstruction.py`
  - validación: `python -m unittest lib.test_transbordos_metro_reconstruction`
- Impacto medido en parquets ya generados (sin reprocesar todavía):
  - `2024-W17`: `410,046` filas cambiarían algún terminal de viaje (`9.503%` de flagged; `3.437%` del total)
  - `2025-W14`: `332,516` filas (`9.264%` de flagged; `3.236%` del total)
  - `2025-W15`: `387,529` filas (`9.107%` de flagged; `3.165%` del total)
  - `2025-W17`: `383,651` filas (`9.114%` de flagged; `3.162%` del total)
- Lectura:
  - el problema en `paradero_inicio_viaje` / `paradero_fin_viaje` es material;
  - el problema en `zona_inicio_viaje` / `zona_fin_viaje` es menor en magnitud, pero sí alcanza a artefactos espaciales aguas abajo.
- Implicancia metodológica:
  - impacto potencial fuerte en OD-buffers (`zona_inicio_viaje`, `zona_fin_viaje`);
  - impacto localizado pero real en el modelo interanual enriquecido actual, porque usa `zona_inicio_viaje` para demanda/oferta.

## 2026-03-25 — Snapshot archivado de resultados OD-buffers pre-fix
- Se revisó qué resultados OD-buffers habían quedado **formalmente reportados** en esta bitácora antes del fix de terminales stale.
- Decisión: el baseline pre-fix a preservar no será “el artefacto más nuevo en disco”, sino la última foto que sí quedó cerrada en la narrativa del proyecto.
- Snapshot archivado en:
  - `03_models/archives/pre_fix_buffers_2026-03-25/`
- Resultados incluidos:
  - `Biogeme sample60pct`:
    - `03_models/archives/pre_fix_buffers_2026-03-25/biogeme/2025-W17-option1-v2-sample60pct`
    - `03_models/archives/pre_fix_buffers_2026-03-25/biogeme/2025-W17-mnl-option1-v2-sample60pct`
  - `Larch full`:
    - `03_models/archives/pre_fix_buffers_2026-03-25/larch/2025-W17-nested-od-buffers-option1-v2-full`
    - `03_models/archives/pre_fix_buffers_2026-03-25/larch/2025-W17-mnl-od-buffers-option1-v2-full`
- Razón de selección:
  - estos cuatro resultados son los que quedaron documentados explícitamente en la entrada `2026-03-03 — Contraste empírico final: nested vs MNL`;
  - existen otros artefactos posteriores en disco (por ejemplo `Biogeme sample10pct` nested), pero no quedaron formalizados como baseline final y no deben confundirse con la foto cerrada pre-fix.
- Lectura rápida de consistencia de estos cuatro resultados:
  - `Biogeme sample60pct`: `MNL` y `Nested` tienen el mismo `LL = -3,107,303`, mismo `Rho^2 = 0.509`; `Nested` agrega un parámetro (`21` vs `20`) y `MU_QR = 1.0`, por lo que tiene sentido como evidencia pre-fix de que el nido no aporta.
  - `Larch full`: `MNL` mejora levemente a `Nested` (`LL = -5,183,641` vs `-5,183,720`; `Rho^2 = 0.508443` vs `0.508435`); `Mu:QR = 1.0`. También tiene sentido como baseline pre-fix del mismo mensaje metodológico.
- Conclusión:
  - estos cuatro artefactos son una **buena foto final pre-fix** para mostrar o comparar contra los reruns post-fix;
  - no deben interpretarse como resultados vigentes una vez reprocesadas las semanas afectadas.

## 2026-03-25 — Primer snapshot OD-buffers post-fix (Biogeme)
- Se archivó un primer snapshot post-fix en:
  - `03_models/archives/post_fix_buffers_2026-03-25/`
- Por ahora contiene:
  - `Biogeme sample10pct nested`
    - `03_models/archives/post_fix_buffers_2026-03-25/biogeme/2025-W17-option1-v2-sample10pct`
  - `Biogeme sample10pct MNL`
    - `03_models/archives/post_fix_buffers_2026-03-25/biogeme/2025-W17-mnl-option1-v2-sample10pct`
- Comparación preliminar contra el baseline pre-fix archivado:
  - `MNL sample10pct` post-fix queda muy alineado con `Biogeme sample60pct` pre-fix:
    - `Rho^2 = 0.509` en ambos;
    - `ASC_QR_RED`, `ASC_QR_OTHER`, `T_VEH`, `T_ESPERA_INI` y `N_TRASB` cambian muy poco en magnitud;
    - por lo tanto, el fix no parece alterar materialmente la historia sustantiva del `MNL` principal.
  - `Nested sample10pct` post-fix:
    - empata exactamente el `LL` del `MNL`;
    - `MU_QR = 1.0` (`Active bound = True`);
    - `AIC/BIC` peores que `MNL`;
    - por lo tanto, mantiene intacta la conclusión pre-fix de que el nested no agrega valor.
- Salvedad:
  - este snapshot post-fix todavía es **parcial**: falta completar el rerun de `Larch full` para cerrar la comparación formal `post-fix vs pre-fix` sobre la misma foto archivada.

## 2026-03-25 — Snapshot OD-buffers post-fix completado con Larch full
- Se completó el snapshot post-fix en:
  - `03_models/archives/post_fix_buffers_2026-03-25/`
- Resultados agregados:
  - `Larch full nested`
    - `03_models/archives/post_fix_buffers_2026-03-25/larch/2025-W17-nested-od-buffers-option1-v2-full`
  - `Larch full MNL`
    - `03_models/archives/post_fix_buffers_2026-03-25/larch/2025-W17-mnl-od-buffers-option1-v2-full`

## 2026-03-25 — Refactor de estructura en `03_models`
- Se ordenó la estructura de outputs/artefactos para evitar seguir sobrecargando `03_models/tmp`.
- Nueva convención:
  - artefactos compartidos de datos:
    - `03_models/artifacts/od_buffers/`
    - `03_models/artifacts/interannual_enriched/`
  - resultados de estimación por framework:
    - `03_models/biogeme-logit/results/05_od_buffers/`
    - `03_models/biogeme-logit/results/06_mnl_refinement/`
    - `03_models/biogeme-logit/results/07_interannual_enriched/`
    - `03_models/larch_logit/results/05_od_buffers/`
    - `03_models/larch_logit/results/06_mnl_refinement/`
    - `03_models/larch_logit/results/07_interannual_enriched/`
  - snapshots / archivos históricos:
    - `03_models/archives/pre_fix_buffers_2026-03-25/`
    - `03_models/archives/post_fix_buffers_2026-03-25/`
- Los notebooks activos (`05`, `05_larch`, `06`, `07`, `07_larch`) fueron actualizados para usar estas rutas nuevas.
- Implicancia operativa:
  - los parquets de contexto OD y pooled interanual ya no se consideran “tmp”, sino artefactos reproducibles compartidos;
  - los resultados de estimación quedan separados por framework y notebook;
  - los snapshots pre/post-fix quedan aislados como archivos históricos.
- Comparación rápida contra el baseline pre-fix archivado:
  - `Larch MNL full`
    - pre-fix: `LL = -5,183,641`, `Rho^2 = 0.508443`
    - post-fix: `LL = -5,177,408`, `Rho^2 = 0.508531`
    - lectura: mejora leve de ajuste, sin cambiar la historia cualitativa de signos y magnitudes principales.
  - `Larch nested full`
    - pre-fix: `LL = -5,183,720`, `Rho^2 = 0.508435`, `Mu:QR = 1.0`
    - post-fix: `LL = -5,177,316`, `Rho^2 = 0.508539`, `Mu:QR = 1.0`
    - lectura: el nested mejora levemente al `MNL` en ajuste (`ΔLL ≈ 92` a favor del nested), pero el parámetro del nido sigue pegado al bound (`Mu:QR = 1`), por lo que la estructura nested continúa sin verse identificada de manera sustantiva.
- Hallazgo a seguir mirando:
  - en `Larch` post-fix, `B_BIP_N_TRASB` queda positivo tanto en `MNL` como en `Nested`, a diferencia de `Biogeme`; esto sugiere que persiste una divergencia de framework en ese coeficiente puntual, aunque la narrativa global `nested vs MNL` no cambia.
- Conclusión provisional post-fix:
  - en ambos frameworks, el fix no parece alterar de forma fuerte la historia sustantiva principal del bloque OD-buffers;
  - el punto metodológico central sigue siendo el mismo: el nested no muestra una ganancia clara y robusta frente al `MNL`.

## 2026-03-25 — Semana `2025-W15` habilitada con proxy GTFS temporal
- Se auditó la cobertura GTFS local y se confirmó un hueco entre `2025-03-01` y `2025-04-11`, que impedía procesar `2025-W15` con feeds "limpios".
- Se descartó `GTFS_20250111` como proxy para abril:
  - aunque su `feed_info` cubría `2025-01-11` a `2025-02-28`, su estructura operativa no resultó compatible como aproximación segura para `2025-W15`.
- Se optó por usar `GTFS_20250412` como base de un proxy temporal, porque:
  - es el snapshot más cercano a `2025-W15`;
  - la validación previa mostró que rebajar/extender solo la envolvente temporal no altera el cálculo si se reutiliza el mismo grafo Metro guardado.
- Se creó un proxy temporal sin tocar los feeds originales:
  - `tmp/gtfs_proxy_2025-W15/GTFS/GTFS_20250407_PROXY`
  - `tmp/gtfs_proxy_2025-W15/metro_graphs/`
  - con `feed_info.txt` y `calendar.txt` ajustados para cubrir `2025-04-07` a `2025-04-13`.
- Se evitó reconstruir el grafo desde cero para el proxy:
  - se reutilizó/copió el grafo guardado de `GTFS_20250412` bajo alias `GTFS_20250407_PROXY`;
  - motivo: la reconstrucción del grafo mostró diferencias espurias en `tv` que no provenían del GTFS proxy sino del proceso de build del grafo.
- Se parcheó el pipeline para soportar overrides temporales de GTFS/grafos:
  - `01_processing/04_transbordos_metro.qmd`
  - `01_processing/06_recalculo_tiempos_espera.qmd`
  - `scripts/recalculo_tiempos_espera_optimized.py`
  - nuevos overrides: `GTFS_ROOT_OVERRIDE`, `METRO_GRAPH_DIR_OVERRIDE`, `--gtfs-root`, `--graph-dir`.
- Flujo ejecutado para `2025-W15`:
  - `04_transbordos_metro.qmd` con el proxy, generando:
    - `01_processing/tmp/etapas_reconstruidas_2025-W15.parquet`
  - `05_transbordos_bus.qmd`, generando:
    - `tmp/frecuencias_buses_2025-W15.parquet`
  - `scripts/recalculo_tiempos_espera_optimized.py --partition 2025-W15 --gtfs-root ... --graph-dir ...`, generando:
    - `tmp/viajes_con_te_calculado_2025-W15.parquet`
- Resultado del runner optimizado:
  - filas input `04`: `12,280,951`
  - filas filtradas no model-ready: `36,024`
  - filas output final: `12,244,927`
  - desglose drops:
    - `missing_srv = 25,112`
    - `non_contiguous = 0`
    - `block_mismatch = 190`
    - `orig_gt4 = 250`
    - `recon_gt4 = 10,902`
- Validación técnica final sobre `tmp/viajes_con_te_calculado_2025-W15.parquet`:
  - `rows_missing_srv_block = 0`
  - `rows_non_contiguous = 0`
  - `rows_block_mismatch = 0`
  - `metro_variant_conflict_1..6 = 0`
  - sin tiempos calculados negativos
  - sin outliers duros (`te > 2h`, `tv > 3h`)
  - cobertura de cálculo en etapas existentes:
    - etapa 1: `TE 98.49%`, `TV 99.16%`
    - etapa 2: `TE 97.36%`, `TV 97.71%`
    - etapa 3: `TE 97.63%`, `TV 98.28%`
    - etapa 4: `TE 96.82%`, `TV 98.72%`
  - nulls Metro bajos por etapa:
    - etapa 1: `0.761%`
    - etapa 2: `1.080%`
    - etapa 3: `1.037%`
    - etapa 4: `1.218%`
- Decisión operativa:
  - `2025-W15` queda incorporada como semana usable aguas abajo, con nota metodológica explícita:
    - **`2025-W15` procesada con GTFS proxy basado en `GTFS_20250412`**.

## 2026-03-25 — Semana `2025-W14` habilitada con proxy GTFS temporal
- Se reutilizó el mismo enfoque validado para `2025-W15`, pero con una ventana temporal desplazada a:
  - `2025-03-31` a `2025-04-06`
- Se creó un nuevo proxy temporal sin tocar los feeds originales:
  - `tmp/gtfs_proxy_2025-W14/GTFS/GTFS_20250331_PROXY`
  - `tmp/gtfs_proxy_2025-W14/metro_graphs/`
  - basado en `GTFS_20250412`, ajustando solo `feed_info.txt` y `calendar.txt`.
- Se volvió a reutilizar/copiar el grafo guardado de abril bajo alias `GTFS_20250331_PROXY`, manteniendo el mismo criterio adoptado en `W15`.
- Flujo ejecutado para `2025-W14`:
  - `04_transbordos_metro.qmd` con el proxy;
  - `05_transbordos_bus.qmd`;
  - `scripts/recalculo_tiempos_espera_optimized.py --partition 2025-W14 --gtfs-root ... --graph-dir ...`
- Resultado del runner optimizado:
  - filas input: `10,307,831`
  - filas filtradas no model-ready: `30,973`
  - filas output final: `10,276,858`
  - desglose drops:
    - `missing_srv = 21,419`
    - `non_contiguous = 0`
    - `block_mismatch = 161`
    - `orig_gt4 = 208`
    - `recon_gt4 = 9,548`
- Validación técnica final sobre `tmp/viajes_con_te_calculado_2025-W14.parquet`:
  - `rows_missing_srv_block = 0`
  - `rows_non_contiguous = 0`
  - `rows_block_mismatch = 0`
  - `metro_variant_conflict_1..6 = 0`
  - sin tiempos calculados negativos
  - sin outliers duros (`te > 2h`, `tv > 3h`)
  - cobertura de cálculo en etapas existentes:
    - etapa 1: `TE 98.35%`, `TV 99.03%`
    - etapa 2: `TE 97.16%`, `TV 97.49%`
    - etapa 3: `TE 97.50%`, `TV 98.12%`
    - etapa 4: `TE 96.70%`, `TV 98.60%`
  - nulls Metro bajos por etapa:
    - etapa 1: `0.958%`
    - etapa 2: `1.370%`
    - etapa 3: `1.306%`
    - etapa 4: `1.558%`
- Decisión operativa:
  - `2025-W14` queda incorporada como semana usable aguas abajo, con nota metodológica explícita:
    - **`2025-W14` procesada con GTFS proxy basado en `GTFS_20250412`**.

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

## 2026-03-13 — Primer nested interanual enriquecido (decisión de especificación)
- Para el notebook nuevo `03_models/07_nested_logit_enriched_interannual.qmd` se decidió **preservar la misma especificación nested base** del notebook `05`:
  - mismas utilidades `V_BIP`, `V_QR_RED`, `V_QR_OTHER`;
  - mismas dummies temporales V2 (`LAB_PM`, `LAB_PT`, `NO_LAB`, con `LAB_VALLE` como base);
  - mismos bloques alt-specific `TVH`, `TEI`, `TET`, `NTR`;
  - `n_trasbordos` sigue derivándose desde `n_etapas_recon - 1`.
- En esta primera prueba interanual, sin socio-demo, se agregan solo dos controles:
  - `DUMMY_ANIO_2025`
  - `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
- Ambos controles entran **diferencialmente solo en `QR_RED` y `QR_OTHER` respecto de `BIP`**, no como términos comunes:
  - `B_QR_RED_ANIO_2025 * DUMMY_ANIO_2025`
  - `B_QR_OTHER_ANIO_2025 * DUMMY_ANIO_2025`
  - `B_QR_RED_LOG_DEMAND * LOG_N_VIAJES_ZONA_INICIO_FRANJA`
  - `B_QR_OTHER_LOG_DEMAND * LOG_N_VIAJES_ZONA_INICIO_FRANJA`
- Justificación:
  - `DUMMY_ANIO_2025` captura un shift interanual global relativo a la base `BIP`;
  - `LOG_N_VIAJES_ZONA_INICIO_FRANJA` captura heterogeneidad contextual local de demanda por `zona_inicio_viaje × franja_V2 × año`;
  - mantenerlos diferenciales respecto de `BIP` preserva la lógica identificacional del notebook base y evita reparametrizar la utilidad base en esta primera prueba.

## 2026-03-13 — Muestreo de estimación interanual en Biogeme
- El pooled `2024+2025` tiene `18.67M` filas alt-specific, demasiado grande para correrlo completo en Biogeme de forma estable en este entorno.
- Se decidió usar una **submuestra estratificada por `partition × choice_nested`** con la **misma fracción en todos los estratos**, partiendo con `SAMPLE_FRACTION_ESTIMATION = 0.30`.
- Justificación:
  - preserva simultáneamente la composición por año (`2024-W17` vs `2025-W17`) y por alternativa (`BIP`, `QR_RED`, `QR_OTHER`);
  - evita sobremuestrear alternativas escasas como `QR_RED`, lo que habría requerido corrección por `choice-based sampling`;
  - mantiene una muestra `self-weighting`, por lo que no requiere ponderaciones adicionales en esta primera estimación.

## 2026-03-13 — Réplica Larch del modelo enriquecido interanual
- Se creó `03_models/larch_logit/07_nested_logit_enriched_interannual_larch.qmd`.
- La réplica Larch usa:
  - el mismo parquet pooled `03_models/artifacts/interannual_enriched/trips_context_pooled_2024_2025.parquet`;
  - la misma submuestra estratificada por `partition × choice_nested` con `SAMPLE_FRACTION_ESTIMATION = 0.30`;
  - la misma especificación alt-specific base del notebook `05`;
  - los mismos controles nuevos `DUMMY_ANIO_2025` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA`, entrando diferencialmente solo en `QR_RED` y `QR_OTHER`.
- Alcance:
  - `nested` principal en Larch para comparación con Biogeme;
  - `MNL` de contraste en celda separada.

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
- `03_models/artifacts/od_buffers/od_context_<PARTITION>.parquet`
- `03_models/artifacts/od_buffers/trips_context_<PARTITION>.parquet`
- `03_models/artifacts/od_buffers/od_long_<PARTITION>.parquet`

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

## 2026-03-06 — Validacion comparativa del paso 4 (Metro reconstruction) para W17-2024 vs W17-2025

### Objetivo
- Antes de avanzar con la dummy de año, se revisó si la inconsistencia detectada en `n_etapas_recon` para `2024-W17` era un problema nuevo o si ya existía en `2025-W17`.

### Archivos comparados
- `01_processing/tmp/etapas_reconstruidas_2024-W17.parquet`
- `01_processing/tmp/etapas_reconstruidas_2025-W17.parquet`

### Resultados objetivos
- `2024-W17`
  - filas totales: `11,970,788`
  - filas inconsistentes (`n_etapas_recon` vs columnas `srv_i` pobladas, para `<=6` etapas): `21,901`
  - porcentaje inconsistente: `0.1830%`
  - viajes `transbordo_interno_no_id = True`: `5,613,089`
  - `delta_etapas`: `min=-3`, `max=3`, `p50=0`, `p95=2`
  - `neg_delta_count`: `16,031`
- `2025-W17`
  - filas totales: `12,168,854`
  - filas inconsistentes (`n_etapas_recon` vs columnas `srv_i` pobladas, para `<=6` etapas): `26,100`
  - porcentaje inconsistente: `0.2145%`
  - viajes `transbordo_interno_no_id = True`: `4,221,020`
  - `delta_etapas`: `min=-2`, `max=3`, `p50=1`, `p95=2`
  - `neg_delta_count`: `2,619`

### Decision de trabajo
- La inconsistencia **no es exclusiva de 2024**; tambien esta presente en `2025-W17`.
- Por ahora se interpreta como un comportamiento **transversal del paso 4** (`04_transbordos_metro.qmd`), no como blocker para continuar el pipeline 2024.
- Se deja como caveat metodologico de comparabilidad entre años:
  - el porcentaje total de inconsistencia es bajo y del mismo orden en ambos años,
  - pero el patron interno de `delta_etapas` no es identico entre `2024-W17` y `2025-W17`.

## 2026-03-07 — Bugs estructurales detectados en pipeline Metro 2024/2025

### Hallazgo 1: nombres de estaciones de combinacion no canonicos en GTFS 2024
- Se verifico que el grafo `GTFS_20240210` usa nodos como:
  - `SANTA ANA (L2 L5)`
  - `UNIVERSIDAD DE CHILE (L3 L1)`
- En cambio, el dataset reconstruido trae estaciones como:
  - `SANTA ANA`
  - `UNIVERSIDAD DE CHILE`
- Eso hace que `shortest_path_with_line(...)` no encuentre nodos exactos para varias etapas Metro flaggeadas como `transbordo_interno_no_id = True`, por lo que quedan viajes imposibles sin corregir en `04_transbordos_metro.qmd`.
- Se corrigio la normalizacion en:
  - `lib/transbordos_metro/metro_graph_builder.py`
  - `01_processing/04_transbordos_metro.qmd`
- Smoke test:
  - `SANTA ANA (L2 L5) -> SANTA ANA`
  - `UNIVERSIDAD DE CHILE (L3 L1) -> UNIVERSIDAD DE CHILE`
  - `ESTACION CENTRAL (L1) -> ESTACION CENTRAL`
- Implicancia operativa: para que surta efecto, hay que **reconstruir el grafo** `metro_graph_GTFS_20240210.gpickle` y luego rerunear `04_transbordos_metro.qmd`.

### Hallazgo 2: esperas Metro subestimadas por no filtrar `service_id` por fecha
- En `06_recalculo_tiempos_espera.qmd`, la logica de headway equivalente Metro estaba combinando filas de `frequencies.txt` sin filtrar por `calendar.txt/calendar_dates.txt`.
- Esto mezclaba servicios `L`, `S` y `D` en la misma hora y reducia artificialmente el headway equivalente.
- Smoke test sobre ambos GTFS:
  - `GTFS_20240210`, lunes `2024-04-22`: `L1_all = [D, L, S]`, `L1_active = [L]`
  - `GTFS_20250412`, lunes `2025-04-21`: `L1_all = [D, L, S]`, `L1_active = [L]`
- Se corrigio `01_processing/06_recalculo_tiempos_espera.qmd` para:
  - cargar `calendar.txt` y `calendar_dates.txt`,
  - inferir fecha de servicio por fila,
  - filtrar `service_id` activos antes de buscar headways equivalentes.
- Este bug era **transversal**: ya afectaba tambien a `2025-W17`, aunque recien ahora quedo aislado con claridad.

### Decision de trabajo
- Antes de usar `W17-2024` y `W17-2025` en el modelo con dummy de año, hay que rerunear:
  1. `build_artifacts.py` / regeneracion del grafo para `GTFS_20240210`
  2. `01_processing/04_transbordos_metro.qmd` para `2024-W17`
  3. `01_processing/06_recalculo_tiempos_espera.qmd` para `2024-W17`
  4. idealmente `01_processing/06_recalculo_tiempos_espera.qmd` para `2025-W17`, porque el filtro por calendario tambien corrige ese año

## 2026-03-07 — Auditoria adicional del pipeline 04/05/06 (errores silenciosos)

### Findings nuevos
- `06_recalculo_tiempos_espera.qmd`: el indice de frecuencias de bus descarta la fecha y conserva solo `(Paradero, ServicioSentido, hour)`.
  - Resultado: cuando la tabla `frecuencias_buses_*.parquet` tiene la misma hora para varios dias, el diccionario sobrescribe silenciosamente valores y termina usando una frecuencia arbitraria del ultimo dia iterado.
  - Cuantificacion:
    - `2024-W17`: `803,102` claves multi-dia (`4,236,982` filas afectadas)
    - `2025-W17`: `826,435` claves multi-dia (`4,386,794` filas afectadas)
- `06_recalculo_tiempos_espera.qmd` + `metro_graph_builder.py`: `tv*_calculado` para Metro usa `shortest_path_with_line(...)`, que permite aristas de transferencia.
  - Resultado: una etapa Metro individual imposible puede recibir un tiempo positivo via otro tramo + trasbordo.
  - Smoke test en grafo `GTFS_20250412`:
    - `SANTA ANA (L5) -> ESCUELA MILITAR` devuelve ruta via `L5 -> L1`
    - `UNIVERSIDAD DE CHILE (L3) -> ESTACION CENTRAL` devuelve ruta via `L3 -> L1`
- `04_transbordos_metro.qmd`: al reconstruir etapas, se copian primero todas las columnas originales y luego solo se sobreescriben `paradero_subida_i`, `paradero_bajada_i`, `srv_i`, `tipo_transporte_i`.
  - `tiempo_subida_i`, `tiempo_bajada_i`, `zona_subida_i`, `zona_bajada_i` quedan con valores originales aunque la etapa haya cambiado.
  - Implicancia: el paso 6 puede usar timestamps "viejos" sobre etapas reconstruidas nuevas.
- `06_recalculo_tiempos_espera.qmd`: la estimacion de `tc*_calculado` esta corrida respecto de la semantica original de `tc1/tc2/tc3`.
  - El notebook documenta que `tc1, tc2, tc3` son caminatas previas a etapas `2, 3, 4`.
  - Pero el update crea `tc2_calculado` desde `tc2` para `etapa_origen = 1`, en vez de mapear el transbordo despues de etapa 1 al `tc1` observado.

### Riesgos secundarios
- `05_transbordos_bus.qmd`: `freq_buses_h` usa `n_eventos` y no `n_buses_unicos`.
  - No parece un bug masivo, pero hay ~`39k` claves por semana donde `n_eventos > n_buses_unicos`, con ratio maximo observado entre `3x` y `4x`.
- `04_transbordos_metro.qmd`: el flag `metro_any` queda mal para parte de los viajes no corregidos (`metro_any = tipo_transporte_1 == "2"`).
  - En `2024-W17` se observaron `503,784` viajes con Metro en etapas posteriores y `metro_any = False`.
  - Parece afectar principalmente diagnosticos, no la logica principal.

## 2026-03-07 — Correcciones aplicadas al pipeline 04/05/06

### Codigo corregido
- `lib/transbordos_metro/metro_graph_builder.py`
  - se agrego `shortest_path_same_line(...)` para calcular `tv*_calculado` de una etapa Metro **sin permitir transbordos**;
  - se amplió la normalizacion de estaciones de combinacion para soportar variantes tipo `SANTA ANA (L2-L5)` y `BAQUEDANO (L1-L5)`.
- `01_processing/04_transbordos_metro.qmd`
  - la reconstruccion ya no deja pegados `tiempo_subida_i`, `tiempo_bajada_i`, `zona_subida_i`, `zona_bajada_i` viejos sobre etapas nuevas;
  - en piernas reconstruidas solo se conservan anclas observadas razonables:
    - `tiempo_subida` / `zona_subida` en la primera pierna,
    - `tiempo_bajada` / `zona_bajada` en la ultima;
  - para etapas vaciadas se nulean explicitamente tiempos y zonas;
  - `metro_any` deja de recomputarse como `tipo_transporte_1 == "2"` y se preserva / rellena correctamente.
- `01_processing/06_recalculo_tiempos_espera.qmd`
  - el indice de frecuencias de bus ahora usa clave `(Paradero, ServicioSentido, Fecha, Hora)`;
  - el calculo de `te*_calculado` Metro ya filtra `service_id` activos por fecha real (`calendar.txt` + `calendar_dates.txt`);
  - `tv*_calculado` Metro usa `shortest_path_same_line(...)` en vez de `shortest_path_with_line(...)`;
  - la imputacion secuencial de horas de etapa ahora trabaja con `datetime` reales para no perder la fecha en bus.

### Artefactos regenerados
- Se regeneraron los grafos Metro y tablas de aristas con:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.transbordos_metro.build_artifacts --gtfs-root config/GTFS --output-dir 01_processing/metro_graphs --transfer-penalty 5.86`
- Smoke tests relevantes:
  - `GTFS_20240210`: `SANTA ANA` y `UNIVERSIDAD DE CHILE` ya aparecen como nodos canonicos del grafo.
  - `shortest_path_same_line(G, "SANTA ANA", "L5", "ESCUELA MILITAR") -> None`
  - `shortest_path_with_line(G, "UNIVERSIDAD DE CHILE", "L3", "ESTACION CENTRAL") -> ~10.14 min`
  - Esto confirma la separacion correcta entre:
    - reconstruccion de viaje completo (permite transferencias)
    - tiempo en vehiculo de una sola etapa (no permite transferencias)

### Segunda pasada tecnica: bug adicional encontrado y corregido
- `01_processing/06_recalculo_tiempos_espera.qmd`
  - el diccionario `trip_ids_by_route_service` estaba indexado solo por `(route_id, service_id)`, sin `direction_id`;
  - eso mezclaba simultaneamente las dos direcciones de una misma linea al calcular headways Metro;
  - evidencia directa:
    - para `route_id = L1`, `service_id = L`, `07:00-09:00`, aparecian dos filas en `frequencies.txt`:
      - `L1-I-L-M02` (`direction_id = 0`)
      - `L1-R-L-M02` (`direction_id = 1`)
  - esto seguia duplicando frecuencia incluso despues del fix de calendario.
- Correccion aplicada:
  - el indice ahora es `(route_id, service_id, direction_id)`;
  - `headway_equiv_minutes(...)` recolecta `trip_id` solo de las direcciones validas para la etapa.
- Validacion:
  - despues de separar por `direction_id`, no quedan duplicados en `frequencies.txt` por grupo
    `(route_id, service_id, direction_id, start_time, end_time, headway_secs)`:
    - `GTFS_20240210`: `0`
    - `GTFS_20250412`: `0`

### Riesgo residual aclarado
- `01_processing/04_transbordos_metro.qmd`
  - se fijo `OUT_PATH` a `PROJECT_ROOT / "01_processing" / "tmp" / ...` para evitar que el parquet reconstruido cambie de carpeta segun el cwd del notebook.
  - Esto era una fuente de ambigüedad reproducible entre `tmp/...` y `01_processing/tmp/...`.

### Riesgo residual abierto
- `01_processing/04_transbordos_metro.qmd`
  - `tiempo_imputado` sigue acumulando el `weight` del grafo reconstruido;
  - como las aristas de `transfer` usan `TRANSFER_PENALTY_MIN`, la columna mezcla tiempo de viaje Metro con penalizacion de enrutamiento;
  - esto **no afecta** los modelos actuales (no usan `tc*_calculado` ni `tiempo_imputado` como regresores), pero puede sesgar validaciones o comparaciones manuales si se interpreta como tiempo fisico puro.
- Decision por ahora:
  - dejarlo documentado como `routing_cost` implícito del paso 4;
  - no cambiarlo todavia hasta decidir si se quiere que represente:
    - tiempo puro en vehiculo Metro reconstruido,
    - tiempo total Metro incluyendo transbordos internos,
    - o solo costo de enrutamiento para la reconstruccion.

## 2026-03-07 — Tercera pasada tecnica

### Hallazgo 1: riesgo de desalineacion silenciosa entre `GTFS_VERSION` manual y `manifest`
- `01_processing/06_recalculo_tiempos_espera.qmd`
  - el notebook seguia cargando `routes/trips/frequencies/calendar/stop_times/stops` desde un `GTFS_VERSION` hardcodeado;
  - pero el grafo Metro se seleccionaba aparte via `manifest` + `pick_version_for_date(...)`;
  - eso podia dejar el grafo en una version GTFS y las tablas de headway en otra distinta sin lanzar error.
- Correccion aplicada:
  - se elimino la dependencia operativa de `GTFS_VERSION`;
  - `06_recalculo_tiempos_espera.qmd` ahora selecciona la version GTFS desde el `manifest` antes de cargar las tablas;
  - el `GTFS_DIR` usado para leer `routes/trips/frequencies/...` sale de `version_for_date.path`, igual que el grafo.

### Hallazgo 2: extension silenciosa de versiones GTFS mas alla de `feed_end_date`
- `lib/gtfs_manifest.py`
  - el manifest extendia `valid_to` hasta el dia anterior del siguiente snapshot, incluso si eso sobrepasaba `original_valid_to`;
  - ejemplo observado antes del fix:
    - `GTFS_20240210` quedaba valido hasta `2025-04-11`, aunque su `feed_end_date` declarado era `2024-12-31`.
- Riesgo:
  - cualquier semana sin snapshot intermedio podia usar un GTFS ya vencido sin aviso.
- Correccion aplicada:
  - `valid_to` ahora nunca excede `original_valid_to`;
  - si hay huecos reales entre snapshots, el pipeline falla en vez de extrapolar silenciosamente un feed obsoleto.

### Hallazgo 3: semanas que cruzan cambio de GTFS
- `01_processing/04_transbordos_metro.qmd`
- `01_processing/06_recalculo_tiempos_espera.qmd`
  - ambos notebooks asumian implicitamente una sola version GTFS por semana;
  - si una semana cruza un cambio de snapshot, usar la version del lunes para todos los dias es metodologicamente incorrecto.
- Correccion aplicada:
  - ambos notebooks ahora verifican todas las fechas de la semana ISO;
  - si la semana cruza multiples carpetas GTFS, lanzan `ValueError` explicito en vez de seguir con una version unica incorrecta.
- Validacion:
  - `2024-W17` usa solo `GTFS_20240210`;
  - `2025-W17` usa solo `GTFS_20250412`.

### Aclaracion metodologica: espera bus `3600 / f`
- `01_processing/05_transbordos_bus.qmd`
- `01_processing/06_recalculo_tiempos_espera.qmd`
  - se reviso la formula de espera bus y **no** se marca como bug;
  - el notebook la documenta explicitamente como:
    - `WT_desag = 60 / f_l` minutos
  - y por eso en `06` se usa `wt_bus_seconds(freq_h) = 3600 / freq_h`.
- Respaldo en paper:
  - `papers/1-s2.0-S0968090X2100454X-main.pdf`
  - pagina 4:
    - para cada linea de bus, si el headway sigue una distribucion exponencial, el tiempo de espera se calcula como `60 / f`;
  - pagina 5:
    - `alpha = 1` cuando se asume distribucion exponencial de interarribos;
    - `alpha = 0.5` cuando se asumen headways constantes;
    - el paper usa `alpha = 1` para Santiago porque reporta headways irregulares en buses y modela llegadas bajo un supuesto tipo Poisson.
- Lectura aplicada a este pipeline:
  - mantener `3600 / f` para buses es consistente con tratar el servicio bus como irregular / headway-based;
  - esto no implica automaticamente que Metro deba usar la misma formula, porque el propio paper sugiere que Metro es mas regular que buses.
- Decision:
  - mantenerla como supuesto metodologico heredado del paper / estrategia desagregada;
  - no cambiarla a `headway/2` sin una decision metodologica explicita aparte.

## 2026-03-07 — Analisis de variantes Metro `R/V` (L2, L4, L5)

### Como las trata hoy el pipeline
- En `01_processing/06_recalculo_tiempos_espera.qmd`:
  - `variants_covering(...)` expande una linea base como `L2` a todas sus variantes `route_id` que empiezan con esa base:
    - `L2`, `L2R`, `L2V`
    - `L4`, `L4R`, `L4V`
    - `L5`, `L5R`, `L5V`
  - luego `valid_directions_by_order(...)` y `headway_equiv_minutes(...)` filtran por:
    - cobertura efectiva de estaciones,
    - direccion valida,
    - `service_id` activo en la fecha/hora.
- Esta parte esta **bien encaminada** para calcular `te*_calculado` cuando:
  - un tramo es servido por una sola variante activa;
  - o cuando varias variantes activas sirven el mismo tramo y el pasajero puede tomar la primera que llegue.

### Problema residual importante
- En `lib/transbordos_metro/metro_graph_builder.py`, el grafo de tiempos de viaje agrupa por `route_short_name`, no por `route_id`:
  - `L2`, `L2R` y `L2V` colapsan todos en la linea `L2`;
  - lo mismo ocurre con `L4/L4R/L4V` y `L5/L5R/L5V`.
- Consecuencia:
  - `tv*_calculado` y la reconstruccion de `04_transbordos_metro.qmd` operan sobre una **linea sintetica agregada** que mezcla:
    - variantes expresas de punta,
    - y variantes base/locales del snapshot.
- Esto puede crear caminos viables en el grafo que no corresponden a una variante activa real a esa hora.

### Ejemplos concretos verificados en `GTFS_20250412` para lunes 08:00
- Variantes activas:
  - `L2`: solo `L2R` y `L2V` (no `L2`)
  - `L4`: solo `L4R` y `L4V` (no `L4`)
  - `L5`: solo `L5R` y `L5V` (no `L5`)
- Pares de estaciones que hoy quedan inconsistentes:
  - `L2`: `DORSAL -> EINSTEIN`
    - `variants_covering`: solo `L2`
    - `headway_eq`: `None` (porque `L2` no esta activa a esa hora)
    - `tv`: `78 s` via grafo agregado de `L2`
  - `L4`: `LAS MERCEDES -> GRECIA`
    - `headway_eq`: `None`
    - `tv`: `1305 s`
  - `L5`: `BARRANCAS -> CUMMING`
    - `headway_eq`: `None`
    - `tv`: `~585 s`

### Interpretacion
- La logica actual es **razonable para espera** en tramos comunes o tramos servidos por una variante activa.
- Pero el tratamiento no es completamente consistente para viajes que, en punta, requieren combinar `R` y `V` dentro de la misma linea:
  - `te` se queda sin variante activa que cubra ambas estaciones;
  - `tv` usa igual una ruta en la linea agregada.

### Decision pendiente
- Hay que decidir explicitamente una de estas 3 estrategias:
  1. **Conservadora**:
     - si no existe una sola variante activa que cubra ambas estaciones, dejar `te` y `tv` como no identificados / `NULL`.
  2. **Mas fiel a operacion real**:
     - modelar el cambio `R <-> V` como un transbordo interno dentro de la misma linea y dividir la etapa Metro.
  3. **Aproximacion agregada**:
     - seguir usando linea agregada para `tv`, pero aceptar que eso representa una simplificacion operativa y no una variante real unica.
- Por ahora, la evidencia tecnica sugiere que la opcion `3` es la que el pipeline implementa de facto para `tv`, mientras que `te` sigue una logica mas cercana a `1`.

### Orden de magnitud del problema
- En `tmp/viajes_con_te_calculado_2025-W17.parquet`:
  - etapas totales: `19,561,428`
  - etapas Metro: `11,554,109`
  - etapas Metro en `L2/L4/L5`: `6,197,244`
- O sea, estas tres lineas representan aproximadamente `53.6%` de todas las etapas Metro observadas en `2025-W17`.
- Ademas, al evaluar los pares observados de `L2/L4/L5` contra lunes `2025-04-21 08:00`:
  - `1,188` pares origen-destino quedaron en la situacion inconsistente:
    - `te`: sin variante activa unica que cubra el tramo
    - `tv`: con camino positivo en el grafo agregado
  - esos pares suman un techo de `357,736` etapas observadas en el parquet semanal.
- Ese conteo es un **upper bound**:
  - no todas esas etapas ocurren efectivamente en punta;
  - pero muestra que el fenomeno no es marginal y si vale la pena decidir un tratamiento explicito antes de cerrar el pipeline.

### Correccion implementada (2026-03-10)
- Se implemento un arreglo conservador en `06_recalculo_tiempos_espera.qmd`:
  - `te` sigue calculandose con variantes activas reales (`route_id`) filtradas por cobertura, direccion y calendario;
  - `tv` ya no usa la linea agregada sintetica, sino un promedio ponderado por frecuencia sobre variantes activas reales;
  - cuando no hay ninguna variante activa real que cubra la etapa, `tv*_calculado = NULL` y se marca `metro_variant_conflict_i = True`.
- Smoke test verificado sobre `GTFS_20250412`, lunes `2025-04-21 08:00`:
  - `L2`, `DORSAL -> EINSTEIN`: `tv = NULL`, sin variantes activas validas;
  - `L2`, `SANTA ANA -> LOS HEROES`: variantes activas `L2R` y `L2V`, `tv ≈ 107 s`;
  - `L4`, `TOBALABA -> GRECIA`: variante activa `L4V`, `tv ≈ 723 s`;
  - `L5`, `SANTA ANA -> PLAZA DE ARMAS`: variantes activas `L5R` y `L5V`, `tv ≈ 76 s`.
- En `lib/transbordos_metro/metro_graph_builder.py` el grafo ahora preserva `route_id` (`L2R`, `L2V`, etc.) y deja `route_short_name` solo como `line_base`.
- Caveat residual:
  - `04_transbordos_metro.qmd` sigue siendo estructural y no condicionado a hora/fecha;
  - por lo tanto la reconstruccion puede seguir apoyandose en una variante base `L2/L4/L5` del snapshot si existe en GTFS, aunque luego `06` invalide el `tv` para una hora punta especifica.
  - El control operativo final de consistencia temporal ahora vive en `06`.
  - Ademas, tras rerunear `2024-W17`, quedaron `28,086` filas (`~0.23%`) donde `n_etapas_recon` no coincide con la cantidad efectiva de `srv_1..srv_6` no nulos.
  - No parece bloquear `06`, pero conviene dejar como follow-up recalcular `n_etapas_recon` directamente desde las columnas finales `srv_1..srv_6` pobladas.

## 2026-03-07 — Auditoria de `n_eventos` vs `n_buses_unicos`

### Metodo
- Se replico exactamente la logica de `ts_ref` y `hour_start` de `01_processing/05_transbordos_bus.qmd`.
- Se auditaron las particiones raw:
  - `/Volumes/KINGSTON/tesis-project/lake/bronze/perfiles_de_carga_consolidados/iso_year=2024/iso_week=17/data-0.parquet`
  - `/Volumes/KINGSTON/tesis-project/lake/bronze/perfiles_de_carga_consolidados/iso_year=2025/iso_week=17/data-0.parquet`
- Nota operativa:
  - el glob del directorio contiene `._data-0.parquet` (metadata macOS) que rompe `scan_parquet`; para la auditoria se uso el archivo valido explicito `data-0.parquet`.

### Resultados agregados
- `2024-W17`
  - claves totales `(ServicioSentido, Paradero, hour_start)`: `4,440,875`
  - claves con `n_eventos > n_buses_unicos`: `39,203` (`0.883%`)
  - exceso medio condicional: `1.424`
  - ratio medio condicional `n_eventos / n_buses_unicos`: `1.303`
  - ratio maximo observado: `4.0`
- `2025-W17`
  - claves totales: `4,624,911`
  - claves con `n_eventos > n_buses_unicos`: `39,849` (`0.862%`)
  - exceso medio condicional: `1.429`
  - ratio medio condicional: `1.310`
  - ratio maximo observado: `3.0`

### Repeticion de la misma patente dentro de la misma clave-hora
- `2024-W17`
  - claves `(ServicioSentido, Paradero, hour_start, Patente)` repetidas: `54,758`
  - media de eventos por patente repetida: `2.019`
  - `span` medio entre primer y ultimo `ts_ref`: `1,974.7 s`
  - `span` mediano: `2,100 s`
  - `span > 30 min`: `33,607`
- `2025-W17`
  - claves repetidas: `55,661`
  - media de eventos por patente repetida: `2.023`
  - `span` medio: `1,979.8 s`
  - `span` mediano: `2,101 s`
  - `span > 30 min`: `34,646`

### Lectura metodologica
- El fenomeno existe, pero es **raro** a nivel de clave-hora (<1%).
- No se reduce a un solo mecanismo:
  - hay duplicados exactos reales:
    - ejemplo `2024`: `T807 00I`, paradero `I-6-454-PO-24`, patente `STHK-28`, con dos filas en `11:09:25` y dos en `11:51:56`;
  - y tambien hay la misma patente reapareciendo en tiempos distintos dentro de la misma hora:
    - ejemplo `2025`: `T1120 00I`, paradero `T-17-12-SN-40`, patente `SKPJ-80`, con eventos en `10:01`, `10:18`, `10:31`, `10:46`.
- Conclusion provisoria:
  - **no conviene cambiar automaticamente a `n_buses_unicos`**;
  - hacerlo eliminaria tanto duplicados verdaderos como posibles llegadas efectivas repetidas del mismo bus al mismo paradero dentro de la hora.
- Siguiente decision metodologica razonable:
  - primero definir una regla de deduplicacion de eventos exactos / casi exactos en `05_transbordos_bus.qmd`;
  - recien despues reevaluar si `freq_buses_h` debe seguir siendo `n_eventos` o una version depurada.

## 2026-03-11 - Runner externo optimizado para `06_recalculo_tiempos_espera`

### Motivacion
- La version notebook de `06_recalculo_tiempos_espera.qmd` seguia siendo demasiado lenta para `W17-2024` (~12M filas), incluso despues de corregir bugs metodologicos.
- El cuello principal sigue siendo `add_te_calculado(...)`:
  - `iter_rows(named=True)` sobre millones de filas;
  - consultas Polars repetidas dentro del loop;
  - recalculo redundante de cobertura/direcciones/variantes Metro;
  - construccion repetida de rutas Metro por la misma pareja `(route_id, origen, destino)`.

### Implementacion
- Se creo `scripts/recalculo_tiempos_espera_optimized.py`.
- Mantiene la misma logica metodologica actual de `06`, pero acelera el motor de ejecucion:
  - procesa por batches;
  - evita `dict(row)` y trabaja con tuplas + indices de columna;
  - preconstruye indices GTFS de cobertura, orden y frecuencias por variante/direccion;
  - cachea estructura de etapa Metro por `(subida, bajada, servicio)`;
  - cachea estado temporal Metro por `(subida, bajada, servicio, second_of_day, fecha)`;
  - cachea `tv` de Metro por `(route_id, origen, destino)`;
  - conserva lookup bus por `(Paradero, ServicioSentido, fecha, hora)`.

### Smoke test
- Ejecutado con `larch-env`:
  - `~/.local/share/mamba/envs/larch-env/bin/python scripts/recalculo_tiempos_espera_optimized.py --partition 2024-W17 --limit 2000 --batch-size 1000 --output-path tmp/viajes_con_te_calculado_2024-W17_smoke.parquet --temp-dir tmp/viajes_con_te_calculado_2024-W17_smoke_batches`
- Resultado:
  - corrida exitosa;
  - escritura correcta de parquet;
  - ~`18k-20k` filas/s en smoke;
  - columnas `te*_calculado`, `tv*_calculado` y `metro_variant_conflict_*` presentes;
  - primeras filas consistentes con ejemplos del notebook.

### Uso esperado
- Este runner pasa a ser el camino recomendado para reprocesar `W17-2024` y luego `W17-2025` en el paso equivalente a `06`.
- No reemplaza aun el notebook como documentacion/analisis, pero si como motor de produccion para el recalculo pesado.

### Ajustes posteriores a la revision de equivalencia
- Se corrigio `scripts/recalculo_tiempos_espera_optimized.py` para mantener dos resguardos del notebook:
  - `24:00:00` en `frequencies.txt` ahora se trata como `23:59:59`, igual que en `06_recalculo_tiempos_espera.qmd`;
  - el runner ahora falla explicitamente si una semana ISO cruza multiples snapshots GTFS, en vez de usar silenciosamente la version del lunes.

### Persistencia y reanudacion
- Se agrego soporte de persistencia por batches en `scripts/recalculo_tiempos_espera_optimized.py`:
  - `manifest.json` dentro de `tmp/viajes_con_te_calculado_<partition>_batches/`;
  - `--resume` para continuar desde el ultimo `offset` confirmado;
  - `--finalize-only` para unir batches ya escritos sin recalcular.
- Smoke test de reanudacion:
  - corrida inicial `limit=1000`, luego `--resume` hasta `limit=2000`, y luego `--finalize-only`;
  - resultado correcto: `2` batch files y parquet final de `2000` filas.

### Rescate parcial desde el notebook
- La corrida interactiva de `06_recalculo_tiempos_espera.qmd` para `2024-W17` se interrumpio con avance parcial:
  - `offset = 9,600,000`
  - `n_batches = 48`
  - `filas acumuladas = 9,600,000`
- Se rescataron los batches vivos en memoria del kernel sin concatenar todo en RAM.
- Parquet parcial escrito:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/tmp/viajes_con_te_calculado_2024-W17_partial.parquet`
- Este archivo puede servir despues para:
  - comparar salidas notebook vs runner externo;
  - inspeccionar casos concretos ya calculados;
  - o validar que el runner reproduce el comportamiento esperado sin depender de reruns completos del notebook.

## 2026-03-11 - Validacion post-run completa (`viajes_con_te_calculado_2024-W17.parquet`)

### Integridad estructural
- Archivo final confirmado:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/tmp/viajes_con_te_calculado_2024-W17.parquet`
- Filas output = `11,970,788`, igual que `etapas_reconstruidas_2024-W17.parquet`.
- Columnas calculadas presentes:
  - `te0..te5_calculado`, `tv1..tv6_calculado`, `metro_variant_conflict_1..6`.

### Cobertura y sanity global (`srv_i` no nulo como base)
- Etapa 1: `te=98.23%`, `tv=99.01%`, `tv=0` en `43` filas, sin negativos.
- Etapa 2: `te=96.97%`, `tv=97.41%`, `tv=0` en `238` filas, sin negativos.
- Etapa 3: `te=97.12%`, `tv=97.89%`, `tv=0` en `32` filas, sin negativos.
- Etapa 4: `te=96.39%`, `tv=98.36%`, `tv=0` en `4` filas, sin negativos.
- Etapa 5: `te=93.54%`, `tv=97.90%`, `tv=0` en `1` fila, sin negativos.
- Etapa 6: `te=96.46%`, `tv=99.56%`, `tv=0` en `0` filas, sin negativos.
- `metro_variant_conflict_1..6`: todos en `0`.

### Coherencia Metro (combinaciones observadas)
- Revisado con `WaitTimeEngine.stage_structure(...)` en combos observados por etapa.
- Resultado: `bad_rows = 0` y `bad_combos = 0` para etapas `1..6`.
- Implica que, en output final, no quedaron etapas Metro estructuralmente imposibles por `(srv_i, subida_i, bajada_i)`.

### Confirmacion clave bus con fecha (fix critico)
- Se comparo `te*_calculado` vs `3600/freq_buses_h` usando join por:
  - `(srv_i, paradero_subida_i, fecha(tiempo_subida_i), hora(tiempo_subida_i))`.
- Resultado:
  - coincidencia exacta `100%` sobre filas con match en tabla de frecuencias (etapas `1..6`);
  - `diff = 0` en todas las etapas.
- Con esto se confirma que el bug antiguo de lookup bus sin fecha no esta presente en este output.

### Lectura de nulos remanentes (esperables)
- Bus: nulos de `te` coinciden con ausencia de clave en frecuencias para ese `(servicio, paradero, fecha, hora)`.
- Metro: parte de los `te/tv` nulos ocurren por ausencia de intervalos activos GTFS para la variante declarada en esa fecha/hora (ejemplo observado: `L5R` en sabado `2024-04-27`).

### Observacion pendiente (ya conocida)
- `n_etapas_recon` vs conteo de `srv_1..srv_6` no nulos:
  - mismatch `28,089` filas (`0.2346%`).
- Mantener pendiente:
  - recalcular `n_etapas_recon` desde `srv_1..srv_6` finales al cerrar limpieza.

## 2026-03-11 - Auditoria de `n_etapas_recon` inconsistente

### Resultado principal
- El mismatch `n_etapas_recon` vs `count_non_null(srv_1..srv_6)` en `etapas_reconstruidas_2024-W17.parquet` es de `28,089` filas.
- Descomposicion:
  - `28,087` filas (`99.99%`) **no** fueron reconstruidas (`transbordo_interno_no_id = False`);
  - solo `2` filas vienen realmente del paso 4 reconstruido.

### Origen real del problema
- La gran mayoria del problema es **heredada** desde `viajes_filtrados`:
  - en `/Volumes/KINGSTON/tesis-project/lake/silver/viajes_filtrados/iso_year=2024/iso_week=17/data-0.parquet`
  - ya existen `49,473` filas donde `n_etapas != count_non_null(srv_1..srv_4)`.
- De las `28,089` inconsistencias del parquet reconstruido:
  - `28,087` ya eran inconsistentes en el input original.

### Patron observado
- Distribucion del delta `n_etapas_recon - srv_count`:
  - `+1`: `27,963` filas
  - `+2`: `120`
  - `+3`: `6`
- Patrones mas frecuentes:
  - `n_etapas_recon = 2`, `srv_count = 1` con presencia `1_____`: `11,493`
  - `n_etapas_recon = 2`, `srv_count = 1` con presencia `_2____`: `10,203`
  - `n_etapas_recon = 3`, `srv_count = 2` con presencia `12____`: `3,052`
  - `n_etapas_recon = 3`, `srv_count = 2` con presencia `_23___`: `1,688`
  - `n_etapas_recon = 3`, `srv_count = 2` con presencia `1_3___`: `1,189`
- Interpretacion:
  - no es solo un problema de contador;
  - hay muchas filas con etapas corridas o con huecos internos.

### Filas realmente atribuibles al paso 4
- Hay `2` filas reconstruidas con:
  - `n_etapas_recon = 7`
  - pero solo `6` o `4` columnas `srv_i` disponibles.
- Esto si es bug del paso 4:
  - `n_etapas_recon` se calcula antes de truncar a `MAX_ETAPAS = 6`.
  - referencia:
    - `01_processing/04_transbordos_metro.qmd` lineas donde se hace:
      - `n_etapas_recon = len(legs_out)`
      - luego `legs_out = legs_out[:MAX_ETAPAS]`

### Implicancia para modelos
- Si se quiere usar numero de etapas / transbordos como regresor, **no conviene usar `n_etapas_recon` tal como esta**.
- Minimo aceptable:
  - recalcular una variable derivada como `count_non_null(srv_1..srv_6)`.
- Pero si el modelo depende del orden de etapas, hay que tener presente que existen `13,308` filas con huecos internos (`srv_1 = NULL` y `srv_2` no nulo, `srv_2 = NULL` y `srv_3` no nulo, etc.).
- Por lo tanto, para una version realmente robusta convendria:
  - crear una version compactada de etapas sin huecos,
  - y derivar desde ahi el contador final de etapas.

## 2026-03-11 - Refinamiento de la auditoria: `srv` faltante no implica etapa ausente

### Hallazgo clave
- La mayoria de las inconsistencias originales (`n_etapas` vs `count_non_null(srv_i)`) **no** son huecos de etapa vacia.
- En los patrones dominantes, la etapa existe como bloque casi completo y lo unico faltante es `srv_i`.
- Ejemplos reales:
  - `pk_viaje = 944295436757459450`
    - `n_etapas = 2`
    - `srv_1 = L5`
    - `srv_2 = NULL`
    - pero la etapa 2 tiene `tipo_transporte_2`, `paradero_subida_2`, `paradero_bajada_2`, `tiempo_subida_2`, `tiempo_bajada_2`, `zona_subida_2`, `zona_bajada_2`.
  - `pk_viaje = 16136477210057800651`
    - `n_etapas = 2`
    - `srv_1 = NULL`
    - `srv_2 = L5`
    - la etapa 1 tambien existe como bloque observacional, pero sin servicio identificado.

### Interpretacion
- Para estas filas, `n_etapas` / `n_etapas_recon` puede estar **bien** como conteo de etapas observadas.
- El error es que `srv_count` subcuenta porque `srv_i` no esta siempre poblado aunque la etapa si exista.
- Por eso, eliminar todas las filas donde `n_etapas_recon != count_non_null(srv_i)` seria demasiado agresivo.

### Criterio estructural mas seguro para modelacion
- Definir `block_i` (etapa presente) si al menos una de las columnas del bloque de etapa `i` esta poblada:
  - `srv_i`, `tipo_transporte_i`, `paradero_subida_i`, `paradero_bajada_i`, `tiempo_subida_i`, `tiempo_bajada_i`, `zona_subida_i`, `zona_bajada_i`.
- En el parquet final `etapas_reconstruidas_2024-W17.parquet`:
  - filas totales: `11,970,788`
  - filas con `n_etapas_recon == block_count` y bloques contiguos: `11,970,636`
  - filas realmente inseguras bajo este criterio: `152`
- Es decir:
  - para conteos de etapas/transbordos, el problema real de seguridad no es `28,089` filas sino `152`.

### Recomendacion actual
- Para modelos donde importa `N_transbordos = n_etapas - 1`:
  - derivar `n_etapas_model = block_count`
  - derivar `n_transbordos_model = n_etapas_model - 1`
  - excluir solo filas donde:
    - `n_etapas_recon != block_count`
    - o los bloques no sean contiguos
- Caveat:
  - esto es seguro para el **conteo de etapas**;
  - no resuelve automaticamente el problema de `srv_i` faltante si luego se necesitan atributos por etapa basados en servicio (`te/tv` de esa etapa, linea, modo, etc.).

## 2026-03-11 - Implicancia para modelos: drop de filas con bloque presente pero srv faltante

### Hallazgo sobre el pipeline de modelos
- Los modelos principales no usan solo `N_transbordos`; tambien usan tiempos derivados del mismo parquet v2.
- En `lib/od_buffers_nested_logit.py` y `lib/build_buffers_zona777_tipo_pago.py`:
  - `t_espera_trasbordo_seg` se construye con suma de `te1..te5_calculado` usando `fill_null(0)`.
  - `t_vehiculo_total_seg_final` se construye con suma de `tv1..tv6_calculado` usando `fill_null(0)`.
  - `n_trasbordos` se construye como `n_etapas_recon - 1`.
- Por lo tanto, si se conserva una fila donde existe una etapa bus estructural pero `srv_i` esta faltante, esa etapa:
  - cuenta para `n_trasbordos` / `n_etapas_recon`,
  - pero aporta `NULL` a `te_i_calculado` y `tv_i_calculado`, que luego se convierten en 0 en las sumas.
- Eso induce una incoherencia teorica: mas etapas/trasbordos con menos tiempo total del realmente observado/imputable.

### Cuantificacion 2024-W17
- Filas con al menos un bloque de etapa presente pero `srv_i` faltante: `27,945` (`0.2334%` del total).
- De ellas, `27,937` son estructuralmente contiguas y `8` se superponen con filas estructuralmente inseguras.
- Todas las etapas con `srv_i` faltante en esta auditoria corresponden a `tipo_transporte_i = 1` (bus).
- Distribucion por posicion de etapa faltante:
  - etapa 1: `12,030`
  - etapa 2: `12,762`
  - etapa 3: `3,181`
  - etapa 4: `86`
- Sobrerrepresentacion temporal moderada:
  - laboral (`tipodia=0`): tasa drop ~ `0.19%`
  - sabado (`tipodia=1`): tasa drop ~ `0.34%`
  - domingo/festivo (`tipodia=2`): tasa drop ~ `0.99%`
- Por medio de pago, la tasa es muy parecida:
  - BIP: ~`0.238%`
  - QR: ~`0.204%`

### Decision metodologica sugerida
- Para estimacion de modelos, es mas defensable **excluir** estas filas de la muestra analitica que conservarlas con `N_transbordos` corregido pero tiempos submedidos.
- No borrar del parquet canonico; crear un filtro/model-view reproducible:
  - `row_stage_service_complete = True` si todo bloque de etapa presente tiene `srv_i` no nulo y la estructura es contigua.
  - usar solo `row_stage_service_complete = True` en modelos que incluyan `te/tv`, `N_transbordos`, o variables derivadas de servicio/linea.
- Justificacion:
  - el sesgo de seleccion esperado es pequeno por tamano (`0.23%` de filas),
  - mientras que el error de medicion al conservarlas es sistematico y con direccion conocida (subestimacion de tiempos en viajes con etapas bus incompletas).

## 2026-03-11 - Implementacion del filtro model-ready en paso 06
- Se implemento el filtro directamente en:
  - `scripts/recalculo_tiempos_espera_optimized.py`
  - `01_processing/06_recalculo_tiempos_espera.qmd`
- Regla aplicada al output final de `viajes_con_te_calculado_*`:
  - drop si existe algun bloque de etapa presente con `srv_i` nulo;
  - drop si la estructura de bloques no es contigua.
- El script ahora reporta por batch y acumulado:
  - `drop_missing_stage_service`
  - `drop_non_contiguous_stage_blocks`
  - `rows_dropped_total`
- Importante: no reanudar (`--resume`) sobre un `temp_dir` generado antes de este cambio, porque mezclaría batches filtrados y no filtrados.

## 2026-03-11 - Ajuste final del filtro model-ready
- Se agrego una tercera condicion de exclusion en el paso 06:
  - drop si `block_count != n_etapas_recon`.
- Motivacion:
  - aun despues de filtrar etapas con `srv_i` faltante, quedaban `144` filas en `2024-W17` con sobreconteo de etapas/transbordos pero tiempos observados/calculados presentes.
  - Para los modelos, eso tambien rompe la coherencia entre `n_trasbordos` y `te/tv`.
- Implicancia esperada para `2024-W17`:
  - drop total esperado: `28,089`
  - filas output esperadas: `11,942,699`

## 2026-03-11 - Validacion post-fix del parquet final 2024-W17
- Archivo validado: `tmp/viajes_con_te_calculado_2024-W17.parquet`
- Filas finales: `11,942,699`

### Checks resueltos
- Calidad estructural final:
  - `rows_missing_srv_block = 0`
  - `rows_non_contiguous = 0`
  - `rows_block_mismatch = 0`
- Metro impossible stages (definidos como ausencia de camino `same-line` en cualquier variante candidata):
  - etapas 1..6: `0` filas imposibles
  - etapas 1..6: `0` filas imposibles con `tv*_calculado` no nulo
- Ejemplos historicos problematicos ya no aparecen:
  - `L5: SANTA ANA -> ESCUELA MILITAR`: `0` filas
  - `L3: UNIVERSIDAD DE CHILE -> ESTACION CENTRAL`: `0` filas
- Bus por fecha real:
  - para todas las etapas bus, `te*_calculado` coincide exactamente con `3600/freq_buses_h` cuando existe match exacto por `(Paradero, ServicioSentido, fecha, hora)`
  - mismatches exactos observados: `0` en etapas 1..6
- Variantes Metro:
  - `metro_variant_conflict_1..6 = 0`
  - recomputacion puntual de muestra (`80` casos en familias L2/L4/L5 con variantes punta): `0` fallas

### Riesgo residual observado
- En etapas bus sigue habiendo filas sin match exacto en tabla de frecuencias por fecha/hora:
  - etapa 1: `5,771,208 / 5,863,974` con match
  - etapa 2: `1,057,890 / 1,082,149`
  - etapa 3: `449,612 / 461,499`
  - etapa 4: `106,902 / 110,979`
  - etapa 5: `7,872 / 8,361`
  - etapa 6: `194 / 201`
- Esto no contradice el fix de clave temporal; solo indica cobertura incompleta de la tabla de frecuencias para una fraccion menor de etapas bus.

## 2026-03-11 - Fourth technical review of 04/05/06 + optimized script

New findings after reviewing pipeline code against the already-validated 2024-W17 final parquet:

- High: `04_transbordos_metro.qmd` still reconstructs flagged trips by iterating original stages `1..4` only (`for i in range(1, 5)` around line 1094), even though `MAX_ETAPAS = 6`. This means support for 5th/6th original stages is only partial. On 2024-W17 there are 60 flagged rows with `n_etapas > 4`, and 11,200 flagged rows end up with `n_etapas_recon > 4`, so the notebook currently mixes 4-stage logic with 6-stage output schema.
- High: `04_transbordos_metro.qmd` computes `n_etapas_recon = len(legs_out)` before truncating `legs_out[:MAX_ETAPAS]` (around lines 1153-1160). This is the direct source of the later `block_count_mismatch` rows that 06/script now filter out. Intermediate parquet from 04 remains internally inconsistent until 06 drops those rows.
- Medium: `05_transbordos_bus.qmd` still defines `freq_buses_h = n_eventos`, not `n_buses_unicos` (around lines 137-144). 2024-W17 audit: 39,203 / 4,440,875 keys have `n_eventos > n_buses_unicos`, mean overcount ratio 1.303x, max 4.0x, mean excess 1.424 events. This remains a live modeling assumption/risk distinct from the already-fixed date-key issue.
- Medium: `04_transbordos_metro.qmd` still contains many diagnostics/coverage checks hard-coded to stages 1..4 (e.g. lines ~291, 358, 632, 648, 1294, 1385). Even if the final schema has 6 stages, these checks can under-report residual issues on stages 5/6.
- Consistency check: `06_recalculo_tiempos_espera.qmd` and `scripts/recalculo_tiempos_espera_optimized.py` are aligned on the important logic: GTFS-week guard, bus frequency keyed by full date+hour, Metro wait/travel by active real variants, `same-line` vehicle time, and model-ready row filtering.
- Final 2024-W17 parquet still passes the previously critical bug checks after the new filtering: zero Metro impossible stages, zero `same-line` infeasible Metro stages with non-null `tv`, zero remaining `missing_srv_block`, zero non-contiguous stage rows, zero remaining block-count mismatches, and zero exact-join bus wait mismatches where a date-hour frequency match exists.

Implication:
- The final 2024-W17 output used for models is in good shape.
- The remaining concerns are upstream notebook correctness / reproducibility (`04`) and the unresolved event-vs-unique-bus assumption in `05`.

- 2026-03-11 decision: final model-ready filtering in 06/script now also excludes `n_etapas > 4 OR n_etapas_recon > 4`. Measured on final 2024-W17 parquet before applying the new rule: `orig_gt4=60`, `recon_gt4=11,198`, union `11,210`. Rationale: use the union to respect both the observed-trip validity rule discussed with advisor and the reconstructed-trip complexity limit used in the thesis.

- 2026-03-11 decision on bus frequency counting: keep `freq_buses_h = n_eventos` for now. We evaluated a cleaner alternative `n_unique(Patente, ts_ref)` (deduplicate exact repeated passes while preserving real multiple passes of the same bus within the hour). Impact on 2024-W17 is very small globally: 491 / 4,440,875 frequency keys change (0.011%), affecting 5,181 / 7,393,678 bus stages with calculated wait in the final parquet (0.070%). On affected rows the change is meaningful (mean abs delta wait ~418s), but aggregate impact is negligible. If refined later, prefer `n_unique(Patente, ts_ref)` over `n_buses_unicos`.

- 2026-03-11 new high-severity theoretical bug: in both `06_recalculo_tiempos_espera.qmd` and `scripts/recalculo_tiempos_espera_optimized.py`, when `tiempo_subida_i` is missing for stage `i>1`, the code imputes `stage_time_i = stage_time_{i-1} + wait_{i-1} + travel_{i-1}`. This is conceptually wrong: the pre-boarding wait of stage `i-1` happened before `stage_time_{i-1}` and should not be added. The relevant post-boarding component is transfer/walk time (`tc1/tc2/tc3` when observed, or an internal transfer proxy), plus previous in-vehicle time. Quantification on final 2024-W17 parquet: missing `tiempo_subida_2` for 2,752,141 rows, `tiempo_subida_3` for 1,044,838, `tiempo_subida_4` for 95,462; all are Metro stages. Among those, observed transfer walks exist for 327,802 stage-2 rows, 78,604 stage-3 rows, and 612 stage-4 rows. In those rows, `prev_wait - tc` has mean about -92s / -89s / -72s for stages 2/3/4 respectively, so the current imputed lookup time is systematically misaligned relative to observed transfer time. This can silently bias later-stage Metro wait lookup and active variant selection.

- 2026-03-11 low-severity temporal edge case: both notebook and script fold GTFS times `>24:00:00` with `%24` logic (script `parse_hms_to_seconds`, notebook GTFS load only special-cases exact `24:00:00`). GTFS_20240210 has 1,192 `end_time` values >=24h in `frequencies.txt`. This can misplace post-midnight service intervals, although 2024-W17 has almost no observed Metro boardings before 05:00, so materiality for this week appears low.

- 2026-03-11 operational bug: optimized script resume manifest only tracks `model_ready_filter=True`, not a filter/version hash. Since filter logic changed multiple times, `--resume` can silently accept old partial batches generated under previous filtering semantics.

- 2026-03-12 implementation: fixed later-stage time imputation in `06_recalculo_tiempos_espera.qmd` and `scripts/recalculo_tiempos_espera_optimized.py`. New rule: when `tiempo_subida_i` is missing for stage `i>1`, impute `stage_time_i = stage_time_{i-1} + tv_{i-1} + transfer_seconds`, where `transfer_seconds = tc{i-1}` if observed and positive, otherwise `170s` fallback (chosen from the observed median transfer-walk time measured on 2024-W17). This replaces the previous incorrect `prev_wait + prev_travel` logic.

- 2026-03-12 impact audit before rerun of the stage-time fix: the new later-stage timing rule potentially applies to 3,482,214 / 11,942,699 final rows in 2024-W17 (29.16%), defined as rows with a present stage 2-4 but missing `tiempo_subida_i`. Breakdown: stage 2 = 2,752,141 rows (327,802 with observed `tc1`, 2,424,339 fallback), stage 3 = 1,044,838 (78,603 with observed `tc2`, 966,235 fallback), stage 4 = 95,462 (612 with observed `tc3`, 94,850 fallback).
- 2026-03-12 sample impact audit on 50,000 potentially affected rows: 385 rows (0.77%) changed at least one `te/tv` value under the new timing rule. Most changes concentrate in `te1_calculado` (252 rows) and `te2_calculado` (114 rows). Max absolute change observed: 436.5s in `te1/te2`; `tv` changes are rare and small (max ~18.54s in `tv2/tv3`, ~8.38s in `tv4`). Interpretation: the bug is theoretically important, but effective output changes appear localized rather than massive.

## 2026-03-12 - Cuarta pasada tecnica adicional (hallazgos nuevos abiertos)
- `04_transbordos_metro.qmd` sigue teniendo soporte parcial de 6 etapas: la reconstruccion principal itera etapas originales `1..4` (`for i in range(1, 5)`), aunque `MAX_ETAPAS=6`. Esto es distinto del filtro analitico `>4` ya resuelto en 06/script; es un bug aguas arriba de soporte/validacion incompleta.
- `04_transbordos_metro.qmd` calcula `n_etapas_recon = len(legs_out)` antes de truncar a `MAX_ETAPAS`, por lo que sigue pudiendo escribir parquet intermedio inconsistente, aunque 06/script ahora filtren esos casos.
- `06_recalculo_tiempos_espera.qmd` sigue sobrescribiendo el parquet final en una segunda pasada para agregar `tc2_calculado..tc6_calculado` (celdas cerca de lineas 2285-2324). Esto diverge del script optimizado y contradice la decision metodologica vigente de no usar caminatas en modelos. Riesgo: si alguien usa el notebook end-to-end, obtiene un artefacto distinto al del script.
- `recalculo_tiempos_espera_optimized.py` mantiene un guardrail insuficiente para `--resume`: el manifest no versiona realmente la semantica del filtro/lógica, solo checks basicos (`model_ready_filter=True`). Reanudar sobre batches viejos puede mezclar salidas de semantica distinta.
- Edge case bajo impacto: parser de horas GTFS >24h sigue plegando con `%24` en notebook/script; materialidad baja para 2024-W17 pero teoricamente incorrecto para servicio post-medianoche.

## 2026-03-12 - Fixes aplicados tras nueva pasada tecnica
- `06_recalculo_tiempos_espera.qmd`: se blindó la sección de caminatas internas para que no vuelva a sobrescribir `viajes_con_te_calculado_*.parquet`. La estimación de `tc*_calculado` queda solo como análisis exploratorio en el notebook.
- `04_transbordos_metro.qmd`: se separó `MAX_ETAPAS_INPUT = 4` (schema observado original) de `MAX_ETAPAS_RECON = 6` (buffer técnico de salida). La reconstrucción principal ahora usa explícitamente el límite de input y `n_etapas_recon` se calcula después del truncado final, evitando outputs intermedios inconsistentes.
- `recalculo_tiempos_espera_optimized.py`: se endureció `--resume` agregando `logic_hash` y `logic_semantics` al manifest. Reanudar sobre batches de semántica antigua ahora debe fallar.
- Validación: `python -m py_compile scripts/recalculo_tiempos_espera_optimized.py` OK tras los cambios.

## 2026-03-12 - Revision final completa del flujo (abiertos)
- `04_transbordos_metro.qmd`: para `df_good` sigue definiendo `n_etapas_recon = n_etapas` en vez de recalcularlo desde los bloques finales. Como `n_etapas` upstream puede venir stale, `etapas_reconstruidas_*` sigue pudiendo arrastrar conteos inconsistentes si alguien consume directamente el output de 04. El parquet final de 06/script lo corrige por filtrado, pero aguas arriba sigue abierto.
- `04_transbordos_metro.qmd`: varias validaciones/metricas siguen hardcodeadas a etapas `1..4`, por lo que hay puntos ciegos de diagnostico para etapas 5/6 reconstruidas.
- `scripts/recalculo_tiempos_espera_optimized.py`: `--resume` ya quedó protegido por `logic_hash`, pero `--finalize-only` sigue fusionando batches existentes sin validar manifest/hash/logica. Riesgo operativo si alguien finaliza un temp_dir viejo o mezclado.
- Edge case bajo impacto: notebook/script siguen parseando horarios GTFS >24h con plegado `%24` (salvo manejo parcial de `24:00:00`), teoricamente incorrecto para servicio post-medianoche.

## 2026-03-12 - Validacion final 2024-W17 post-rerun completo
- Parquet final validado: `tmp/viajes_con_te_calculado_2024-W17.parquet`
- Filas finales: 11,931,489 (pk_viaje unicos: 11,931,489).
- Reaplicar `filter_model_ready_rows` sobre el parquet final da `rows_dropped=0`.
- Desglose final de drop al producir el parquet: 39,299 = missing_srv 27,945 + non_contiguous 0 + block_mismatch 150 + orig_gt4 210 + recon_gt4 11,350 (con solapamientos ya absorbidos por la union del filtro).
- Cobertura final por etapa:
  - E1 base 11,931,489 | te 98.235% | tv 99.010%
  - E2 base 5,520,109 | te 96.973% | tv 97.411%
  - E3 base 1,545,314 | te 97.136% | tv 97.905%
  - E4 base 197,181 | te 96.385% | tv 98.420%
  - E5/E6 base 0 tras filtro >4.
- Sanity: sin negativos en `te*`/`tv*`; ceros en `tv`: E1 42, E2 237, E3 31, E4 4.
- `metro_variant_conflict_1..6 = 0`.
- Auditoria final de combos Metro sobre el parquet final: `impossible_combos=0`, `impossible_rows=0`, `impossible_rows_with_tv=0`.
- Medias globales utiles del parquet final: `n_etapas_mean=1.286`, `n_etapas_recon_mean=1.609`, `te0_mean=354.37s`, `te1_mean=191.13s`, `tv1_mean=788.18s`, `tv2_mean=689.56s`.

## 2026-03-12 - Bug especifico detectado en 2025-W17 y fix aplicado
- El rerun inicial de `scripts/recalculo_tiempos_espera_optimized.py` para `2025-W17` resultó invalido: las etapas Metro quedaron con `te/tv = NULL` en 100% por un bug de normalizacion de `stop_name` GTFS.
- Causa: `station_from_stop_name()` en el script cortaba literal `" DIRECCION"`, pero `GTFS_20250412` trae `"Dirección"` con acento; `coverage_by_route_dir` y `order_by_route_dir_station` quedaron indexados con sufijos de dirección embebidos.
- Fix: `station_from_stop_name()` ahora usa normalizacion accent-insensitive y regex para remover `DIRECCION` / `DIR` antes de `normalize_station_name()`.
- Se actualizó `logic_hash` (version semantica `v5`) para invalidar `--resume` sobre batches viejos.
- Smoke test post-fix OK en 2025-W17:
  - `ESTACION CENTRAL -> UNIVERSIDAD DE CHILE (L1)` recupera `valid_dirs=(0,)` y `h_eq=1.7167`.
  - `LOS HEROES -> PARQUE OHIGGINS (L2/L2R)` recupera variantes y `h_eq` no nulo.
- Implicancia operativa: para 2025-W17 hay que rerunear solo el script desde cero; `04` y `05` no necesitan repetirse por este bug.

## 2026-03-12 - Cierre de reprocesamiento y validacion final 2025-W17
- `04_transbordos_metro.qmd` reruneado para `2025-W17`:
  - output: `01_processing/tmp/etapas_reconstruidas_2025-W17.parquet`
  - cobertura de estaciones/grafo completa
  - `Etapas metro aún imposibles (sin transfer): 0`
- `05_transbordos_bus.qmd` reruneado para `2025-W17`:
  - output: `tmp/frecuencias_buses_2025-W17.parquet`
  - filas consolidadas vs CSV fuente: `22,076,070 == 22,076,070`
  - filas de tabla de frecuencias: `4,624,911`
  - clave unica por `(ServicioSentido, Paradero, hour_start)` y cobertura horaria `0..23`
- `scripts/recalculo_tiempos_espera_optimized.py` reruneado desde cero para `2025-W17` tras el fix de normalizacion GTFS:
  - output final: `tmp/viajes_con_te_calculado_2025-W17.parquet`
  - filas finales: `12,131,426`
  - drop total: `37,428`
    - `missing_srv=25,909`
    - `non_contiguous=0`
    - `block_mismatch=204`
    - `orig_gt4=267`
    - `recon_gt4=11,511`

### Validacion final 2025-W17
- `pk_viaje` unicos: `12,131,426`
- Reaplicar `filter_model_ready_rows` sobre el parquet final da `rows_dropped=0`
- Cobertura final por etapa:
  - E1 base `12,131,426` | `te 98.443%` | `tv 99.107%`
  - E2 base `5,573,573` | `te 97.352%` | `tv 97.704%`
  - E3 base `1,548,693` | `te 97.647%` | `tv 98.284%`
  - E4 base `198,794` | `te 96.814%` | `tv 98.703%`
  - E5/E6 base `0` tras el filtro `>4`
- Sanity:
  - `metro_variant_conflict_1..6 = 0`
  - `impossible_combos=0`
  - `impossible_rows=0`
  - `impossible_rows_with_tv=0`
  - sin negativos en `te*`/`tv*`
  - `tv=0` muy bajos: E1 `26`, E2 `235`, E3 `30`, E4 `3`
- Medias globales:
  - `n_etapas_mean=1.290`
  - `n_etapas_recon_mean=1.603`
  - `te0_mean=380.85s`
  - `te1_mean=203.57s`
  - `tv1_mean=808.40s`
  - `tv2_mean=714.06s`

## 2026-03-12 - Comparacion final entre semanas reprocesadas 2024-W17 vs 2025-W17
- Archivos comparados:
  - `tmp/viajes_con_te_calculado_2024-W17.parquet`
  - `tmp/viajes_con_te_calculado_2025-W17.parquet`
- Ambos outputs quedaron alineados bajo el mismo pipeline corregido:
  - `metro_variant_conflict_* = 0`
  - filtros `model-ready` limpios al reaplicarse (`rows_dropped=0`)
  - sin etapas Metro imposibles ni `tv` Metro incompatibles con `same-line`
- Comparacion agregada:
  - filas finales: `11,931,489` (2024) vs `12,131,426` (2025)
  - `n_etapas_mean`: `1.286` vs `1.290`
  - `n_etapas_recon_mean`: `1.609` vs `1.603`
  - `te0_mean`: `354.37s` vs `380.85s`
  - `te1_mean`: `191.13s` vs `203.57s`
  - `tv1_mean`: `788.18s` vs `808.40s`
  - `tv2_mean`: `689.56s` vs `714.06s`
- Comparacion por modo (`bus = tipo 1/3`, `metro = tipo 2`):
  - Bus:
    - `te_mean`: `639.28s` (2024) vs `681.31s` (2025)
    - `tv_mean`: `1034.85s` vs `1056.01s`
    - `te_cov`: `98.23%` vs `98.54%`
    - `tv_cov`: `100%` en ambos
  - Metro:
    - `te_mean`: `80.92s` (2024) vs `79.66s` (2025)
    - `tv_mean`: `550.61s` vs `565.01s`
    - `te_cov`: `98.83%` vs `99.08%`
    - `tv_cov`: `98.83%` vs `99.08%`
- Juicio final: ambos parquets finales son comparables y plausibles para pasar a modelacion. Las diferencias 2024/2025 se ven de magnitud razonable y no muestran ruptura metodologica del pipeline.

## 2026-03-12 - Cierre de incorporacion de 2024-W17 al pipeline final
- Se da por cerrada la incorporacion de `2024-W17` al flujo final corregido.
- Estado final:
  - `2024-W17` y `2025-W17` quedaron reprocesadas y validadas bajo el mismo pipeline.
  - Los artefactos canonicos para modelacion son los parquets finales `tmp/viajes_con_te_calculado_2024-W17.parquet` y `tmp/viajes_con_te_calculado_2025-W17.parquet`.
  - Los outputs intermedios de `04`/`05` se mantienen como artefactos tecnicos, no como fuente para modelacion.
- Foco siguiente:
  - volver a la tarea principal del proyecto: enriquecimiento y reestimacion de los modelos OD-buffers usando estos parquets finales ya estabilizados.

## 2026-03-12 - Arranque del modelo interanual enriquecido
- Se confirmó que existe caracterización QR para ambos años en raw:
  - `raw/caracterizacion/caracterización qr_202404.csv`
  - `raw/caracterizacion/caracterización qr_202504.csv`
- Hallazgo importante: la librería estaba hardcodeada a `caracterización qr_202504.csv`, por lo que cualquier corrida de `2024-W17` en modelos hubiera usado mal la caracterización 2025.
- Fix aplicado:
  - `lib/od_buffers_nested_logit.py`
  - `lib/build_buffers_zona777_tipo_pago.py`
  - `resolve_caracterizacion_path(..., partition_label)` y `_resolve_caracterizacion_path(..., partition_label)` ahora eligen `202404` o `202504` según la partición; si no se pasa partición, conservan el default `202504` para no romper notebooks viejos.
- Se creó un notebook nuevo para no contaminar el flujo anterior:
  - `03_models/07_nested_logit_enriched_interannual.qmd`
- El notebook nuevo ya deja lista la base metodológica:
  - carga `2024-W17` y `2025-W17`
  - usa caracterización correcta por partición
  - construye `od_context` y `trips_context` alt-specific pooled
  - agrega `partition`, `year` y `DUMMY_ANIO_2025`
  - mantiene la lógica base del OD-buffers anterior, incluyendo `n_trasbordos = n_etapas_recon - 1`
- Decisión metodológica explícita de esta versión:
  - partir con Nested Logit
  - no incorporar aún socio-demo
  - agregar primero `dummy_anio` y luego bloques de demanda/oferta

## 2026-03-13 - Primera prueba de control de demanda para el modelo interanual
- Se definió el primer bloque nuevo a probar como:
  - `DUMMY_ANIO_2025`
  - `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
- Decisiones metodológicas de esta primera prueba:
  - usar `zona_inicio_viaje` solamente, no destino ni OD completo;
  - construir la demanda por `zona_inicio_viaje × franja_V2 × año/partición`;
  - usar las cuatro franjas V2 ya consistentes con el modelo base:
    - `LAB_PM`
    - `LAB_PT`
    - `LAB_VALLE`
    - `NO_LAB`
  - ingresar la variable como `log1p(n_viajes)` y no en nivel crudo.
- Rationale:
  - `DUMMY_ANIO_2025` captura un shift interanual global;
  - `LOG_N_VIAJES_ZONA_INICIO_FRANJA` captura heterogeneidad local/contextual de demanda;
  - si el conteo no se construye por año, se mezclan intensidades de 2024 y 2025 y la dummy anual tendría que absorber también diferencias locales;
  - partir solo con origen minimiza solapamiento con los atributos `OD × tipo_pago` ya presentes en el modelo base.
- Se posterga para iteraciones siguientes:
  - controles por destino;
  - controles por OD completo;
  - uso de hora exacta en vez de franja V2;
  - socio-demo.
- Implementación inicial realizada en `03_models/07_nested_logit_enriched_interannual.qmd`:
  - se deriva `franja_v2` desde las dummies V2 del viaje;
  - se cuenta demanda por `partition × zona_inicio_viaje × franja_v2`;
  - se agrega `N_VIAJES_ZONA_INICIO_FRANJA` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA` al `trips_context` pooled.
- Smoke test sobre muestra limitada de ambas particiones:
  - pooling exitoso con `share_nonnull_demand = 1.0`;
  - celdas observadas por partición/franja consistentes en la muestra.

## 2026-03-13 - MNL enriquecido en el mismo notebook interanual
- Se decidió correr el `MNL` enriquecido en el mismo notebook `03_models/07_nested_logit_enriched_interannual.qmd`.
- Rationale:
  - mantener exactamente el mismo `pooled`, la misma muestra estratificada y los mismos controles que el nested;
  - permitir comparación limpia `nested vs MNL` sin divergencias silenciosas de datos o sample;
  - mantener consistencia con la réplica en Larch, que ya usa el mismo dataset pooled.
- Implementación:
  - se agregó `estimate_mnl_option1_alt_specific_enriched(...)` con la misma especificación alt-specific del nested enriquecido;
  - se agregaron celdas `mnl-full`, `mnl-summary` y `compare-nested-vs-mnl`.

## 2026-03-13 - Redefinición del control de demanda para que represente contexto local real
- Se corrigió la definición de `LOG_N_VIAJES_ZONA_INICIO_FRANJA` en `03_models/07_nested_logit_enriched_interannual.qmd`.
- Problema detectado:
  - la versión inicial contaba demanda sobre `df_trips`, que ya estaba filtrado a OD con 3 alternativas observadas y sin singletons de la alternativa elegida;
  - por tanto, la variable medía intensidad dentro de la muestra elegible del experimento y no demanda local general del sistema;
  - además, incluía a la propia observación en el conteo.
- Nueva definición:
  - base de demanda construida desde **todos los viajes finales model-ready** de cada partición (`viajes_con_te_calculado_*.parquet`);
  - agregación por `zona_inicio_viaje × franja_v2 × partition`;
  - join posterior al dataset alt-specific;
  - leave-one-out a nivel observación:
    - `N_VIAJES_ZONA_INICIO_FRANJA = max(N_RAW - 1, 0)`
    - `LOG_N_VIAJES_ZONA_INICIO_FRANJA = log1p(N_VIAJES_ZONA_INICIO_FRANJA)`
- Rationale:
  - ahora la variable sí representa contexto local de demanda del sistema en origen/franja/año;
  - el leave-one-out evita autocontaminación mecánica de la observación en su propio control contextual.

## 2026-03-16 - Resultados del modelo enriquecido interanual (sin cerrar aún la decisión final)
- Se corrieron especificaciones enriquecidas interanuales sobre pooled `2024-W17 + 2025-W17` con:
  - `DUMMY_ANIO_2025`
  - `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
- Biogeme, nested enriquecido:
  - volvió a pegar `MU_QR = 1.0`;
  - con la redefinición corregida de demanda, el nested no mostró mejora sustantiva respecto de MNL;
  - la señal de los controles nuevos se mantuvo:
    - `B_QR_RED_ANIO_2025 > 0`
    - `B_QR_OTHER_ANIO_2025 > 0`
    - `B_QR_RED_LOG_DEMAND > 0`
    - `B_QR_OTHER_LOG_DEMAND ≈ 0`
- Biogeme, MNL enriquecido:
  - convergió limpiamente;
  - parámetros principales:
    - `B_QR_RED_ANIO_2025 ≈ 0.225`
    - `B_QR_OTHER_ANIO_2025 ≈ 0.295`
    - `B_QR_RED_LOG_DEMAND ≈ 0.121`
    - `B_QR_OTHER_LOG_DEMAND ≈ -0.002`
- Larch, nested enriquecido:
  - `Mu:QR = 1.0` en el bound activo, consistente con colapso del nido;
  - la dirección de los coeficientes nuevos fue consistente con Biogeme, aunque con magnitudes distintas.
- Larch, MNL enriquecido:
  - replicó bien la señal principal observada en Biogeme;
  - parámetros principales:
    - `B_QR_RED_ANIO_2025 ≈ 0.242`
    - `B_QR_OTHER_ANIO_2025 ≈ 0.296`
    - `B_QR_RED_LOG_DEMAND ≈ 0.109`
    - `B_QR_OTHER_LOG_DEMAND ≈ 0.001` (no significativo)
- Conclusión empírica provisional:
  - los resultados nuevos son estables cross-framework;
  - el nested no muestra evidencia clara de aportar estructura útil;
  - pero **no** se cierra aún la decisión de “modelo final”, porque queda pendiente conversarlo con la profesora.
- Hallazgo persistente:
  - los coeficientes de `T_VEH` siguen saliendo positivos en varias especificaciones, por lo que los nuevos controles no resolvieron ese punto interpretativo.

## 2026-03-16 - Próximo bloque: controles de oferta separados para bus y metro
- Se decidió que el siguiente bloque a explorar no será socio-demo todavía, sino controles de oferta operativa por separado:
  - `OFERTA_BUS_ZONA_INICIO_FRANJA`
  - `OFERTA_METRO_ZONA_INICIO_FRANJA`
- Decisión metodológica:
  - no partir solo con bus, para no dejar un control de oferta asimétrico;
  - primero construir ambas medidas por separado y recién después evaluar si conviene también una agregada de oferta total.
- Base propuesta para el mapeo espacial:
  - usar las columnas observadas de viajes:
    - `paradero_subida_i`, `zona_subida_i`
    - `paradero_bajada_i`, `zona_bajada_i`
  - construir crosswalks empíricos:
    - `bus_stop -> zona`
    - `metro_station -> zona`
- Auditoría requerida antes de usar estos crosswalks en el modelo:
  - cobertura de stops/estaciones;
  - número de zonas distintas por stop/estación;
  - zona modal y share modal;
  - identificación de casos ambiguos.
- Rationale:
  - antes de construir oferta por zona/franja, hay que verificar que el mapping `paradero/estación -> zona` sea suficientemente limpio y estable;
  - si el mapping es ambiguo, la variable de oferta quedaría mal definida y mezclaría zonas.

## 2026-03-16 - Auditoría empírica del mapeo `paradero/estación -> zona`
- Se auditó el crosswalk usando ambos parquets finales:
  - `tmp/viajes_con_te_calculado_2024-W17.parquet`
  - `tmp/viajes_con_te_calculado_2025-W17.parquet`
- Definición:
  - `bus_stop -> zona`: observaciones con `tipo_transporte in {1, 3}`, usando subida y bajada;
  - `metro_station -> zona`: observaciones con `tipo_transporte = 2`, usando subida y bajada;
  - asignación candidata = `zona` modal por `stop/estación`.
- Resultado bus:
  - `30,628,445` pares `stop-zona` observados;
  - `11,932` paraderos únicos;
  - `11,926` (`99.95%`) quedan en una sola zona observada;
  - `11,927` (`99.96%`) tienen `modal_share >= 0.95`;
  - solo `6` paraderos muestran dos zonas observadas;
  - solo `5` (`0.04%`) tienen `modal_share < 0.80`;
  - para los stops presentes en ambos años, la `zona` modal coincide en `99.95%`.
- Resultado metro:
  - `30,640,674` pares `stop-zona` observados;
  - `132` estaciones únicas;
  - `132` (`100%`) quedan en una sola zona observada;
  - `132` (`100%`) tienen `modal_share >= 0.95`;
  - consistencia entre `2024` y `2025`: `100%`.
- Implicancia:
  - el mapeo observado es suficientemente limpio para construir una primera versión de:
    - `OFERTA_BUS_ZONA_INICIO_FRANJA`
    - `OFERTA_METRO_ZONA_INICIO_FRANJA`
  - en bus, la primera versión pooled de oferta excluirá los `5` paraderos con `modal_share < 0.80`.
  - se materializó un primer crosswalk de trabajo en:
    - `03_models/artifacts/interannual_enriched/bus_stop_zona_modal_crosswalk_2024_2025.parquet`
    - incluye `zona_modal`, `modal_share`, `n_zonas` y flag `is_ambiguous_for_offer`.
  - y una versión lista para oferta en:
    - `03_models/artifacts/interannual_enriched/bus_stop_zona_modal_crosswalk_2024_2025_offer_ready.parquet`
    - excluye esos `5` paraderos ambiguos.

## 2026-03-16 - Primera construcción de `OFERTA_BUS_ZONA_INICIO_FRANJA`
- Ya se materializó una primera tabla pooled en:
  - `03_models/artifacts/interannual_enriched/bus_offer_zona_inicio_franja_2024_2025.parquet`
- Definición usada:
  - partir de `frecuencias_buses_{partition}.parquet`;
  - mapear `Paradero -> zona_modal` usando el crosswalk `offer-ready`;
  - agrupar por `zona_inicio_viaje × franja_v2 × hour_start` y sumar `freq_buses_h` para obtener `oferta_bus_hora`;
  - luego promediar `oferta_bus_hora` dentro de cada `zona_inicio_viaje × franja_v2 × partition`.
- Variables resultantes:
  - `OFERTA_BUS_ZONA_INICIO_FRANJA`
  - `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
- Supuesto temporal explícito:
  - para clasificar `hour_start` en `franja_v2`, se tomó `tipodia = 0` para lunes-viernes y `tipodia = 1` para sábado-domingo.
- Resumen rápido:
  - `799` celdas `zona × franja` por partición;
  - medias por franja razonables y muy similares entre `2024` y `2025`;
  - orden estable:
    - `LAB_PT` y `LAB_PM` con oferta más alta;
    - `LAB_VALLE` intermedio;
    - `NO_LAB` más bajo.

## 2026-03-16 - Primera construcción de `OFERTA_METRO_ZONA_INICIO_FRANJA`
- Ya se materializó el crosswalk metro en:
  - `03_models/artifacts/interannual_enriched/metro_station_zona_modal_crosswalk_2024_2025.parquet`
- Y la primera tabla pooled de oferta metro en:
  - `03_models/artifacts/interannual_enriched/metro_offer_zona_inicio_franja_2024_2025.parquet`
- Definición usada:
  - partir del GTFS válido para cada partición según `gtfs_manifest`;
  - usar `frequencies.txt` + `calendar.txt` + `calendar_dates.txt` para obtener servicios activos por fecha real;
  - construir frecuencia por estación y hora sumando `freq_trains_h = 3600 / headway_secs` sobre variantes y direcciones activas que cubren esa estación;
  - mapear `station_norm -> zona_modal`;
  - promediar esa oferta horaria por `zona_inicio_viaje × franja_v2 × partition`.
- Variables resultantes:
  - `OFERTA_METRO_ZONA_INICIO_FRANJA`
  - `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
- Resumen rápido:
  - `112` celdas `zona × franja` por partición;
  - orden por franja razonable y estable:
    - `LAB_PT` y `LAB_PM` más altos;
    - `LAB_VALLE` intermedio;
    - `NO_LAB` más bajo.
- Observación:
  - en esta primera construcción, `2024` y `2025` quedaron con el mismo agregado medio por franja; antes de interpretarlo sustantivamente, conviene verificar si responde a una oferta Metro prácticamente idéntica entre snapshots o a una agregación demasiado gruesa.

## 2026-03-17 - Decisión de densificación para oferta Metro
- Se validó el join de oferta sobre `df_trips_pooled`.
- Resultado:
  - `OFERTA_BUS_*` cubre `100%` de las filas y de las claves `partition × zona_inicio_viaje × franja_v2`;
  - `OFERTA_METRO_*` cubre solo las zonas con presencia Metro local, lo que equivale a:
    - `72.16%` de las filas;
    - `14.41%` de las claves únicas;
    - `112` zonas con oferta Metro por partición, frente a `780-783` zonas presentes en los viajes.
- Decisión metodológica:
  - densificar `OFERTA_METRO_ZONA_INICIO_FRANJA` y `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA` a `0` al integrarlas al `trips_context_pooled`;
  - interpretación explícita:
    - `0` = ausencia estructural de oferta Metro en la zona/franja de origen bajo este mapeo;
    - no = missing estadístico.
- Implicancia:
  - el parquet `trips_context_pooled_2024_2025.parquet` ya quedó reescrito con:
    - `OFERTA_BUS_ZONA_INICIO_FRANJA`
    - `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
    - `OFERTA_METRO_ZONA_INICIO_FRANJA`
    - `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
  - y sin nulls en estas columnas de oferta.

## 2026-03-17 - Oferta integrada a la especificación de estimación
- Tras la auditoría técnica del notebook interanual, se detectó un bug silencioso:
  - las variables `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA` y `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA` ya estaban construidas e integradas al pooled, pero todavía no entraban a las utilidades de Biogeme ni Larch.
- Se corrigió la especificación en:
  - `03_models/07_nested_logit_enriched_interannual.qmd`
  - `03_models/larch_logit/07_nested_logit_enriched_interannual_larch.qmd`
- Decisión de especificación:
  - ambas variables de oferta entran como variables `case-specific` de forma diferencial solo en `QR_RED` y `QR_OTHER`, respecto de `BIP`;
  - se mantienen separadas:
    - `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
    - `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
- También se agregó un guard explícito en el join de oferta del notebook Biogeme:
  - si `OFERTA_BUS_ZONA_INICIO_FRANJA` queda nula tras el join, el notebook ahora levanta error en vez de rellenar con `0`;
  - `0` solo se sigue usando para Metro cuando la ausencia de oferta es estructural en la zona/franja de origen.

## 2026-03-18 - Variantes MNL separadas para oferta en Biogeme
- Se dejaron preparadas en `03_models/07_nested_logit_enriched_interannual.qmd` dos variantes adicionales del `MNL` enriquecido para diagnosticar si `LOG_OFERTA_BUS` y `LOG_OFERTA_METRO` se están pisando entre sí:
  - `mnl_enriched_interannual_bus_only`
    - mantiene `DUMMY_ANIO_2025` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
    - incluye `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
    - excluye `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
  - `mnl_enriched_interannual_metro_only`
    - mantiene `DUMMY_ANIO_2025` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
    - incluye `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
    - excluye `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
- Ambas variantes quedaron:
  - con `model_name` propio;
  - con CSVs de salida propios en `BIOGEME_RESULTS_DIR`;
  - con celdas `load-results`, `summary` y `full-results` separadas;
  - sin sobrescribir la corrida `MNL full` ya existente.

## 2026-03-18 - Variantes Nested separadas para oferta en Biogeme
- Se dejó el mismo experimento separado también para `Nested Logit` en `03_models/07_nested_logit_enriched_interannual.qmd`:
  - `nested_enriched_interannual_bus_only`
    - mantiene `DUMMY_ANIO_2025` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
    - incluye `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
    - excluye `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
  - `nested_enriched_interannual_metro_only`
    - mantiene `DUMMY_ANIO_2025` y `LOG_N_VIAJES_ZONA_INICIO_FRANJA`
    - incluye `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA`
    - excluye `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA`
- Ambas variantes quedaron con:
  - `model_name` propio;
  - CSVs separados en `BIOGEME_RESULTS_DIR`;
  - celdas `load-results`, `summary` y `full-results` propias;
  - sin sobrescribir la corrida `Nested full` ya existente.

## 2026-03-19 - Notebooks diagnósticos livianos para Biogeme
- Se crearon dos notebooks temporales para evitar que el notebook interanual monolítico acumule en RAM el pooled completo, el sample estratificado y múltiples copias pandas/objetos Biogeme en una misma sesión:
  - `03_models/07a_biogeme_mnl_offer_diagnostics.qmd`
  - `03_models/07b_biogeme_nested_offer_diagnostics.qmd`
- Ambos notebooks:
  - cargan el pooled ya escrito en `03_models/artifacts/interannual_enriched/trips_context_pooled_2024_2025.parquet`;
  - construyen o reutilizan una muestra estratificada persistida en parquet;
  - corren una sola variante por sesión mediante `VARIANT = "full" | "bus_only" | "metro_only"`;
  - guardan CSVs en directorios separados por familia (`mnl` / `nested`) y `sample_tag`.
- También se agregó un helper compartido:
  - `03_models/biogeme_offer_diagnostics.py`
  que centraliza:
  - sampleo estratificado persistido;
  - carga de muestra a pandas;
  - estimadores Biogeme `MNL` y `Nested`;
  - guardado/carga de resultados.
- Decisión práctica:
  - para `Nested`, la ruta recomendada pasa a ser el notebook `07b`, una sola estimación por kernel y muestra persistida compartida con `07a`;
  - esto no elimina el costo intrínseco de Biogeme al final de la estimación, pero sí reduce el riesgo de crash por acumulación innecesaria de objetos en memoria dentro del notebook grande.
 - Limpieza posterior:
   - una vez corridos los diagnósticos `bus_only` / `metro_only` y guardados sus CSVs/resultados, estos notebooks temporales y el helper `03_models/biogeme_offer_diagnostics.py` se eliminaron para no dejar scaffolding transitorio en el repo.

## 2026-03-19 - Diagnóstico Biogeme `full` vs `bus_only` vs `metro_only`
- Se corrieron variantes separadas de oferta en notebooks livianos Biogeme, sobre la misma muestra persistida al `15%` (`2,801,234` observaciones), tanto para `MNL` como para `Nested`.
- Resultados `MNL`:
  - `full`
    - `LL = -1,404,108`
    - `AIC = 2,808,271`
  - `bus_only`
    - `LL = -1,404,131`
    - `AIC = 2,808,314`
  - `metro_only`
    - `LL = -1,404,168`
    - `AIC = 2,808,389`
- Lectura de ajuste:
  - `full` sigue siendo el mejor;
  - `bus_only` queda bastante más cerca del `full` que `metro_only`;
  - por lo tanto, remover `LOG_OFERTA_METRO` cuesta menos ajuste que remover `LOG_OFERTA_BUS`, lo que sugiere que `bus_offer` aporta más al ajuste global del bloque contextual.
- Lectura de coeficientes `MNL`:
  - `QR_RED`
    - `LOG_OFERTA_BUS`: nulo / no significativo;
    - `LOG_OFERTA_METRO`: negativo y robusto.
  - `QR_OTHER`
    - `LOG_OFERTA_BUS`: positivo y robusto;
    - `LOG_OFERTA_METRO`: pequeño / no robusto.
  - `LOG_N_VIAJES`
    - robustamente positivo para `QR_RED`;
    - débilmente negativo o casi nulo para `QR_OTHER`, dependiendo de si se deja `bus_offer` o `metro_offer`.
- Resultados `Nested`:
  - `bus_only` y `metro_only` replican prácticamente la misma historia coeficiente por coeficiente que sus equivalentes `MNL`;
  - pero en ambos casos:
    - `MU_QR = 1`
    - `Active bound = True`
    - gradientes finales todavía altos;
  - por lo tanto, el nested no agrega información sustantiva adicional y sigue siendo un vehículo peor para interpretar el bloque de oferta.
- Conclusión metodológica provisional:
  - el experimento `bus_only` / `metro_only` no apunta a que ambas ofertas se “maten” entre sí por completo;
  - más bien cada variable parece estar capturando señal distinta por alternativa:
    - `bus_offer` para `QR_OTHER`
    - `metro_offer` para `QR_RED`
  - la interpretación sustantiva pendiente es por qué `LOG_OFERTA_METRO` aparece con signo negativo para `QR_RED`.

## 2026-03-26 - Reunion con profesora: oferta e incorporacion de contexto zonal
- Se conversó el bloque de controles contextuales del notebook `03_models/07_nested_logit_enriched_interannual.qmd`.
- Observación metodológica principal de la profesora:
  - la definición actual de oferta basada en frecuencias por `zona_inicio_viaje × franja_v2` puede estar demasiado cerca de los `TEI`, porque ambos usan frecuencias del sistema;
  - por eso conviene evaluar una definición de oferta más estructural y menos operativa.
- Sugerencia explícita de la profesora para redefinir oferta:
  - usar algo del tipo:
    - `numero de paraderos de bus / area de la zona`
    - `numero de estaciones de metro / area de la zona`
  - o, más generalmente, una medida de densidad de infraestructura de transporte por zona.
- Lectura registrada:
  - esta nueva definición no reemplaza necesariamente el concepto de oferta operativa actual, pero puede ser mejor variable contextual para explicar heterogeneidad espacial;
  - además reduce el solapamiento conceptual con los tiempos de espera calculados a partir de frecuencias.
- Segundo feedback metodológico de la profesora:
  - falta incorporar mejor **contextualización de zonas** en los modelos;
  - no basta con demanda/oferta operativa: hay que sumar variables que caractericen la zona misma.
- Dirección de trabajo sugerida tras la reunión:
  - priorizar variables de contexto zonal antes de seguir afinando el bloque actual de oferta;
  - partir por variables del **Censo 2024** ya preparadas o accesibles por zona;
  - complementar con variables simples de infraestructura/built environment;
  - dejar variables de `OpenStreetMap` como bloque posterior o complementario, no necesariamente como primer paso.
- Traducción operativa preliminar:
  - revisar si conviene reemplazar o complementar `LOG_OFERTA_BUS_ZONA_INICIO_FRANJA` y `LOG_OFERTA_METRO_ZONA_INICIO_FRANJA` con medidas de densidad de infraestructura por zona;
  - priorizar la incorporación de controles zonales de Censo + infraestructura antes de seguir iterando sobre significancia marginal de las ofertas actuales.

## 2026-03-26 - Decisiones de redefinicion del bloque de oferta/contexto de transporte
- Se decidió reemplazar la definición anterior de oferta basada en frecuencias agregadas por un bloque con dos tipos de variables:
  - **infraestructura física** por zona;
  - **variedad de oferta operativa** por `partition × zona_inicio_viaje × franja_v2`.
- Variables nuevas acordadas:
  - `BUS_STOP_DENSITY`
  - `METRO_STATION_DENSITY`
  - `BUS_LINE_COUNT`
  - `METRO_LINE_COUNT`
- Decisión sobre identificación de línea en bus:
  - usar **`ServicioUsuario`** como proxy de “línea” para `BUS_LINE_COUNT`;
  - no usar `ServicioSentido`, porque sobrecuenta al mezclar sentidos, variantes y códigos operacionales finos.
- Evidencia revisada sobre `ServicioUsuario`:
  - en `2024-W17`, `2025-W14`, `2025-W15` y `2025-W17`, cada `ServicioSentido` mapea a un solo `ServicioUsuario`;
  - en cambio, cada `ServicioUsuario` agrupa varios `ServicioSentido` (mediana ≈ `4`, máximo `15`);
  - el conjunto de `ServicioUsuario` es estable entre semanas y su formato está limpio;
  - por lo tanto, `ServicioUsuario` se considera la mejor aproximación disponible a línea percibida por el usuario.

## 2026-04-17 - Apertura de rama OSM / built environment
- Se retoma explícitamente la idea de incorporar variables de `OpenStreetMap`, pero **no** partiendo por variables ya definidas.
- Decisión metodológica:
  - antes de diseñar proxies, primero auditar qué keys/tags existen realmente en el área de estudio;
  - no descartar tempranamente familias como `landuse`, `historic`, `highway`, `place`, `office`, `shop`, etc.;
  - hacer primero un inventario amplio y solo después un screening por cobertura, masa e interpretabilidad.
- Se creó un notebook nuevo para esta etapa:
  - `02_eda/eda_osm_zona777.qmd`
- Alcance del notebook:
  - cargar `ZONA777`;
  - consultar o reusar un export `OSM` raw;
  - inventariar keys principales;
  - inventariar `key=value`;
  - medir cobertura por `ZONA777`;
  - y dejar una shortlist preliminar posterior.
- Families incluidas inicialmente en la auditoría:
  - `amenity`
  - `shop`
  - `office`
  - `leisure`
  - `tourism`
  - `historic`
  - `landuse`
  - `building`
  - `place`
  - `highway`
  - `railway`
  - `public_transport`
  - `aeroway`
  - `natural`
  - `man_made`
- Estado actual:
  - rama abierta en modo **EDA/inventario**, todavía no en modo modelación.
- Decisión sobre granularidad temporal:
  - `BUS_STOP_DENSITY` y `METRO_STATION_DENSITY` quedan **estáticas por zona**;
  - `BUS_LINE_COUNT` y `METRO_LINE_COUNT` se construirán por `partition × zona_inicio_viaje × franja_v2`, como **promedio de líneas únicas por hora** dentro de cada franja.
- Rationale:
  - las densidades miden cobertura física y no dependen de franja;
  - los `LINE_COUNT` sí representan variedad operativa y conviene alinearlos con la estructura temporal V2 del modelo;
  - esta redefinición separa mejor infraestructura / variedad de oferta / LOS y reduce el solapamiento conceptual con `TEI`.
- Implementación:
  - `03_models/07_nested_logit_enriched_interannual.qmd` quedó migrado para construir e integrar:
    - `BUS_STOP_DENSITY`
    - `METRO_STATION_DENSITY`
    - `BUS_LINE_COUNT`
    - `METRO_LINE_COUNT`
  - se removió del notebook el bloque anterior de oferta por frecuencia agregada;
  - `03_models/larch_logit/07_nested_logit_enriched_interannual_larch.qmd` quedó alineado con las mismas cuatro variables.

## 2026-03-28 - Nuevas variantes MNL parsimoniosas del bloque contextual en 07
- Tras revisar resultados `full`, `bus_only` y `metro_only` con el nuevo bloque contextual, se concluyó que:
  - el bloque bus parece estable y útil;
  - el bloque metro está más colineado internamente, sobre todo entre `METRO_STATION_DENSITY` y `METRO_LINE_COUNT`.
- Se confirmó que la especificación **solo densidades** no había sido corrida antes en `03_models/07_nested_logit_enriched_interannual.qmd`:
  - no existían celdas dedicadas;
  - no existían CSVs previos con ese `model_name` en `03_models/biogeme-logit/results/07_interannual_enriched/...`.
- Se decidió agregar dos variantes nuevas **solo para MNL** en el notebook:
  - `mnl_enriched_interannual_bus_plus_metro_station`
    - incluye:
      - `BUS_STOP_DENSITY`
      - `BUS_LINE_COUNT`
      - `METRO_STATION_DENSITY`
    - excluye:
      - `METRO_LINE_COUNT`
  - `mnl_enriched_interannual_density_only`
    - incluye:
      - `BUS_STOP_DENSITY`
      - `METRO_STATION_DENSITY`
    - excluye:
      - `BUS_LINE_COUNT`
      - `METRO_LINE_COUNT`
- Posteriormente se agregó una tercera variante MNL parsimoniosa para cerrar la comparación entre “qué variable metro conservar”:
  - `mnl_enriched_interannual_bus_plus_metro_line`
    - incluye:
      - `BUS_STOP_DENSITY`
      - `BUS_LINE_COUNT`
      - `METRO_LINE_COUNT`
    - excluye:
      - `METRO_STATION_DENSITY`
- Implementación realizada en `03_models/07_nested_logit_enriched_interannual.qmd`:
  - la función `estimate_mnl_option1_alt_specific_enriched(...)` ahora admite toggles finos por componente:
    - `include_bus_stop_density`
    - `include_bus_line_count`
    - `include_metro_station_density`
    - `include_metro_line_count`
  - se agregaron `model_name`, rutas CSV, `load-results`, `summary` y `full-results` propios para ambas variantes.
- Propósito metodológico:
  - probar una especificación más parsimoniosa que mantenga el bloque bus completo;
  - probar por separado cuál variable metro es mejor candidata a quedar sola junto al bloque bus (`METRO_STATION_DENSITY` vs `METRO_LINE_COUNT`);
  - y además una versión todavía más austera basada solo en densidades;
  - comparar todas contra `mnl-full`, `mnl-bus-only` y `mnl-metro-only` antes de cerrar especificación final.
- Resultados comparativos observados en `sample12pct`:
  - `mnl-full` sigue siendo el benchmark de mejor ajuste agregado;
  - entre las variantes parsimoniosas, `mnl_enriched_interannual_bus_plus_metro_line` queda prácticamente empatada con `mnl-full` y mejora claramente sobre:
    - `mnl_enriched_interannual_bus_plus_metro_station`
    - `mnl_enriched_interannual_density_only`
  - `mnl_enriched_interannual_density_only` pierde demasiado al sacar `BUS_LINE_COUNT`, por lo que deja de ser candidata principal.
- Lectura provisional centrada en parámetros, no solo en `LL/AIC/BIC`:
  - `BUS_STOP_DENSITY` y `BUS_LINE_COUNT` se mantienen estables y robustamente significativas a través de las variantes más relevantes;
  - `METRO_STATION_DENSITY` aparece más frágil y probablemente más redundante con el resto del contexto;
  - `METRO_LINE_COUNT` parece retener mejor una señal metro propia, sobre todo para `QR_OTHER`.
- Hipótesis de trabajo registrada, no como hecho cerrado:
  - **bus pareciera requerir dos dimensiones** en esta familia de modelos:
    - una de cobertura física (`BUS_STOP_DENSITY`)
    - y otra de variedad operativa (`BUS_LINE_COUNT`)
  - **metro pareciera no requerir ambas simultáneamente**, posiblemente porque su red es más pequeña y más rígida, y porque `METRO_STATION_DENSITY` parece ser en gran parte redundante con `METRO_LINE_COUNT`.
- Decisión provisional de especificación parsimoniosa preferida:
  - quedarse, por ahora, con:
    - `BUS_STOP_DENSITY`
    - `BUS_LINE_COUNT`
    - `METRO_LINE_COUNT`
  - manteniendo `mnl-full` como benchmark rico para comparación.

## 2026-03-29 - Bug en `zona777_area` que invalida artifacts/resultados recientes de `07`
- Se confirmó un bug real en el bloque interanual enriquecido de `03_models/07_nested_logit_enriched_interannual.qmd`.
- Root cause:
  - `build_zona777_area_table(...)` estaba escribiendo una fila por geometría del shapefile, no una fila por `zona_inicio_viaje`;
  - en el shapefile real, la zona `493` aparece multipartida en dos geometrías;
  - por eso el artifact `03_models/artifacts/interannual_enriched/zona777_area_2024_2025.parquet` quedó con `804` filas y una única zona duplicada (`493`), en vez de `803` filas únicas por zona.
- Evidencia reproducida:
  - `zona_inicio_viaje = 493` aparecía dos veces en `zona777_area_2024_2025.parquet`, con:
    - `AREA_KM2 = 0.505938`
    - `AREA_KM2 = 1.990125`
  - el helper corregido sobre el shapefile real devuelve una sola fila para `493` con:
    - `AREA_KM2 = 2.496063`
  - `bus_stop_density_zona_2024_2025.parquet` también quedó duplicado para `493`, con dos valores distintos de `BUS_STOP_DENSITY` / `LOG_BUS_STOP_DENSITY`;
  - `metro_station_density_zona_2024_2025.parquet` quedó duplicado para `493` también, aunque con valor `0` en ambas filas;
  - `trips_context_pooled_2024_2025.parquet` quedó contaminado:
    - para `2024-W17` y `2025-W17`, en las 4 franjas, la zona `493` aparece con dos valores distintos de `LOG_BUS_STOP_DENSITY`;
    - la muestra de estimación `pooled_2024_2025-estimation-sample12pct.parquet` también conserva esa contaminación.
- Impacto:
  - el join de `df_bus_infra`/`df_metro_infra` en `add_origin_offer_controls(...)` puede inflar filas si alguna tabla de infraestructura no es única por `zona_inicio_viaje`;
  - por lo tanto, las corridas recientes del notebook `07` basadas en esos artifacts deben considerarse **inválidas / stale** hasta rehacer:
    - `zona777_area_2024_2025.parquet`
    - `bus_stop_density_zona_2024_2025.parquet`
    - `metro_station_density_zona_2024_2025.parquet`
    - `trips_context_pooled_2024_2025.parquet`
    - `pooled_2024_2025-estimation-sample*.parquet`
    - y los modelos Biogeme/Larch que usaron ese pooled.
- Fix aplicado en código:
  - se creó `lib/interannual_offer_context.py` con:
    - colapso de áreas por zona (`build_zona777_area_table_from_gdf`)
    - validación de unicidad de llaves
    - guard contra inflación de filas en joins
    - chequeo de columnas nulas inesperadas en joins de infraestructura
  - `03_models/07_nested_logit_enriched_interannual.qmd` ahora:
    - agrega las áreas por `zona_inicio_viaje`;
    - exige unicidad en `zona_area`, `df_bus_infra`, `df_metro_infra`, `df_bus_line_count` y `df_metro_line_count`;
    - falla explícitamente si el join de oferta cambia el número de filas.
- Segundo bug destapado por esos guardrails al rehacer el pooled:
  - `df_trips_pooled` todavía estaba dejando pasar viajes con `zona_inicio_viaje` fuera de la cobertura real de `ZONA777`;
  - se identificaron códigos especiales `848`–`853` y además un `null` en `2025-W17`;
  - estos casos representan ~`0.12%` de `2024-W17` y ~`0.17%` de `2025-W17`;
  - la tabla de áreas corregida cubre zonas `0..847`, por lo que esas llaves nunca podrán recibir infraestructura zonal válida;
  - el notebook `07` ahora filtra explícitamente `df_trips_pooled` y `df_demand_base_pooled` a `zona_inicio_viaje` válidas antes de construir demanda/oferta, en vez de dejar que el problema quede oculto por `fill_null(0)`.

## 2026-03-30 - Conclusión provisional post-fix del bloque contextual de `07` sobre pooled limpio
- Se rehízo la comparación MNL en `sample12pct` después de corregir:
  - el colapso de `zona777_area` por `zona_inicio_viaje`;
  - y la exclusión explícita de `zona_inicio_viaje` fuera de la cobertura real de `ZONA777` (`848`–`853` y `null`).
- La muestra limpia quedó en `2,239,867` observaciones de estimación.
- Resultados relevantes comparados:
  - `mnl-full`
  - `mnl_enriched_interannual_bus_plus_metro_station`
  - `mnl_enriched_interannual_density_only`
  - `mnl_enriched_interannual_bus_plus_metro_line`
- Lectura centrada en parámetros:
  - `BUS_STOP_DENSITY` se mantiene **negativo y significativo** para `QR_RED` y `QR_OTHER` en las especificaciones relevantes;
  - `BUS_LINE_COUNT` se mantiene **positivo y significativo** para `QR_RED` y `QR_OTHER` donde entra;
  - esto refuerza la hipótesis de que el bloque bus capta dos dimensiones distintas y útiles:
    - cobertura/densidad física
    - variedad operativa
  - `METRO_STATION_DENSITY` se debilitó respecto de las corridas contaminadas:
    - en `bus_plus_metro_station`, queda solo marginal para `QR_RED` y no significativa para `QR_OTHER`;
    - en `density_only`, queda significativa para `QR_RED` pero no para `QR_OTHER`;
    - por lo tanto, su señal no parece lo bastante estable como para preferirla como variable metro única;
  - `METRO_LINE_COUNT`, en cambio, queda mejor parado en la corrida limpia `bus_plus_metro_line`:
    - `QR_RED × METRO_LINE_COUNT = -0.0399`, significativo (`p ≈ 0.029`);
    - `QR_OTHER × METRO_LINE_COUNT = +0.0665`, significativo;
    - esta fue la principal mejora respecto de la versión pre-fix contaminada, donde el efecto en `QR_RED` era más débil/marginal.
- Conclusión provisional post-fix:
  - se mantiene y se **refuerza** la preferencia parsimoniosa por:
    - `BUS_STOP_DENSITY`
    - `BUS_LINE_COUNT`
    - `METRO_LINE_COUNT`
  - `mnl-full` se conserva como benchmark rico;
  - `bus_plus_metro_station` y `density_only` pierden atractivo como especificaciones principales después del rerun limpio.
- Importante:
  - esta decisión sigue escrita como **conclusión provisional de trabajo**, no como cierre metodológico definitivo;
  - la justificación principal descansa en:
    - estabilidad de parámetros,
    - significancia robusta,
    - y mejor lectura conceptual del bloque bus + `METRO_LINE_COUNT` frente a las alternativas limpias ya comparadas.

## 2026-03-30 - Nuevo EDA clean antes de integrar Censo a `07`
- Antes de meter variables socio al modelo interanual enriquecido, se decidió abrir un notebook EDA separado y limpio para entender completamente:
  - la naturaleza del agregado `Censo 2024 -> ZONA777`;
  - la validez del parquet final;
  - y la corrección del join hacia el pooled limpio de `07`.
- Se creó:
  - `02_eda/eda_censo2024_zona777_model_join.qmd`
- Alcance del notebook:
  - comparar outputs espaciales disponibles (`bbox`, `region`, `intersects`, `intersects_area`);
  - confirmar que `censo2024_zona777_agg_final.parquet` sea único por `ZONA777`;
  - construir un diccionario de variables del parquet final, cruzando:
    - el diccionario oficial exportado del Censo;
    - y las reglas de agregación del script (`sum`, `weighted_mean`, `derived_share`);
  - medir cobertura exacta contra `trips_context_pooled_2024_2025.parquet`;
  - simular explícitamente el `left join` sobre `zona_inicio_viaje`;
  - medir preservación de filas, nulos post-join y cobertura en la muestra de estimación;
  - auditar rangos plausibles de las variables candidatas.
- Hallazgo metodológico ya confirmado y que justifica este EDA antes de modelar:
  - `share_internet` no está limpia para usarse “tal cual”:
    - `370` zonas del parquet final tienen `share_internet > 1`;
    - `357` de esas zonas sí aparecen en el pooled limpio de `07`;
  - `share_ocupado` también tiene algunos casos > `1`:
    - `4` zonas en total;
    - `2` de ellas sí aparecen en el pooled limpio;
  - además existe al menos una zona usada por el pooled (`ZONA777 = 528`) con todos los socio nulos.
- Implicancia:
  - no conviene integrar Censo “tal cual” al modelo sin una auditoría previa de rangos, nulos y decisiones explícitas de transformación/imputación.

## 2026-03-30 - Regeneración y validación post-fix de parquets Censo ZONA777
- Se revisó desde `lib/censo2024_zona777.py` cómo se construyen los parquets `bbox`, `region`, `intersects` e `intersects_area`:
  - lectura de base `Base_manzana_entidad_CPV24.csv` desde zip;
  - lectura de cartografía de manzanas y shapefile `ZONA777`;
  - normalización del join key `MANZENT`;
  - merge base-cartografía;
  - asignación espacial a `ZONA777`:
    - centroid/bbox/region/intersects para los modos simples;
    - `overlay` con `area_share` para `intersects_area`;
  - agregación por `ZONA777` con:
    - sumas para conteos;
    - medias ponderadas para `prom_edad`, `prom_escolaridad18`, `prom_per_hog`;
    - shares derivados sobre el agregado.
- Se confirmó que el problema real era un alias stale:
  - `censo2024_zona777_agg_final.parquet` no coincidía con `censo2024_zona777_agg_intersects_area.parquet`;
  - diferían casi completamente en:
    - `prom_edad`
    - `prom_escolaridad18`
    - `prom_per_hog`
- Fix aplicado:
  - helper `sync_final_output_alias(...)` en `lib/censo2024_zona777.py`;
  - el notebook `02_eda/eda_censo2024_zona777.qmd` ahora re-sincroniza explícitamente `agg_final` desde `agg_intersects_area`;
  - el notebook `02_eda/eda_censo2024_zona777_model_join.qmd` ahora falla si `agg_final` vuelve a divergir de `agg_intersects_area`.
- Regeneración efectuada el `2026-03-30`:
  - `bbox`
  - `region`
  - `intersects`
  - `intersects_area`
  - y resync de `agg_final`
- Validación post-regeneración:
  - `agg_final == agg_intersects_area` luego de ordenar por `ZONA777`: `True`;
  - `agg_final` y `intersects_area` quedaron con:
    - `803` filas
    - `803` zonas únicas
    - sin `ZONA777` nulas
    - rango `0..847`
- Estado actual:
  - el alias `agg_final` vuelve a ser confiable como mirror de `intersects_area`;
  - las decisiones pendientes ya no son de consistencia del parquet, sino de selección/transformación de variables Censo antes de integrarlas al modelo.

## 2026-03-30 - Bug en `intersects_area`: doble escalamiento de denominadores
- Al auditar por qué varios `share_*` quedaban `> 1`, se confirmó que:
  - los valores base del CSV eran internamente consistentes;
  - `MANZENT` era único tanto en base como en cartografía;
  - la inflación no venía del merge base-cartografía.
- La causa real estaba en `lib/censo2024_zona777.py`, rama `area_weighted`:
  - los `COUNT_VARS` se escalaban por `area_share`;
  - luego los pesos de `WEIGHTED_MEANS` (`n_per`, `n_hog`) se volvían a escalar por `area_share`;
  - como `n_per` y `n_hog` ya pertenecen a `COUNT_VARS`, quedaban multiplicados dos veces.
- Efectos:
  - `share_ocupado`, `share_internet`, `share_serv_tel_movil`, `share_serv_compu` podían quedar artificialmente `> 1`;
  - `prom_edad`, `prom_escolaridad18` y `prom_per_hog` también quedaban mal ponderadas (`area_share^2`).
- Fix aplicado:
  - helper `_apply_area_share_scaling(...)`;
  - los conteos/denominadores ahora se escalan una sola vez;
  - test nuevo en `lib/test_censo2024_zona777.py` para capturar esta regresión.
- Post-fix y regeneración:
  - `share_ocupado`: `max = 0.8744`, `gt1 = 0`
  - `share_internet`: `max = 1.0`, `gt1 = 0`
  - `share_serv_tel_movil`: `max = 1.0`, `gt1 = 0`
  - `share_serv_compu`: `max = 0.9591`, `gt1 = 0`
  - `share_hacinamiento`: sigue en rango válido
- Conclusión:
  - el problema de validez matemática por agregación espacial quedó resuelto;
  - siguen pendientes solo los caveats de universo/interpretación de algunas shares, especialmente `share_ocupado`.

## 2026-03-30 - EDA Censo acotado a primera ronda de variables seguras
- Se ajustó `02_eda/eda_censo2024_zona777_model_join.qmd` para que la exploración activa use solo:
  - `prom_edad`
  - `prom_escolaridad18`
  - `share_inmigrantes`
  - `share_hacinamiento`
- `share_ocupado` y `share_internet` quedaron explícitamente postergadas a una segunda ronda:
  - se mantienen visibles en el notebook solo como estado resumido;
  - no participan en la exploración principal, join-quality ni resúmenes trip-weighted de esta primera pasada.

## 2026-03-30 - Fix de `prom_escolaridad18` con ponderador `18+`
- Se revisó si `prom_escolaridad18` podía reconstruirse con el universo correcto:
  - el CSV base sí trae los buckets:
    - `n_edad_18_24`
    - `n_edad_25_44`
    - `n_edad_45_59`
    - `n_edad_60_mas`
  - por lo tanto se puede construir:
    - `n_18_mas = suma de esos 4 buckets`
- Riesgos auditados antes del fix:
  - solo `5` filas tenían suma de buckets etarios distinta de `n_per`, explicado por faltantes parciales;
  - solo `3` filas tenían `prom_escolaridad18` no nulo con algún bucket `18+` faltante;
  - a nivel `ZONA777`, no aparecieron zonas con `prom_escolaridad18` observable pero peso `18+` agregado igual a `0`.
- Decisión implementada:
  - `prom_escolaridad18` ahora se agrega usando `n_18_mas` como ponderador, no `n_per`;
  - `n_18_mas` se construye con regla estricta:
    - si falta cualquier bucket `18+`, `n_18_mas` queda `NA`;
    - no se usan sumas parciales.
- Cambios en código:
  - `WEIGHTED_MEANS['prom_escolaridad18'] = 'n_18_mas'`
  - helper `_expand_required_variables(...)`
  - helper `_add_derived_weight_columns(...)`
  - `_apply_area_share_scaling(...)` ahora también escala pesos requeridos que no estén en `COUNT_VARS`
- Verificación:
  - tests en `lib/test_censo2024_zona777.py`: `4/4 OK`
  - parquets regenerados:
    - `bbox`
    - `region`
    - `intersects`
    - `intersects_area`
    - `agg_final` resincronizado
  - `agg_final == agg_intersects_area`: `True`
- Impacto cuantificado:
  - diferencia absoluta entre ponderar `prom_escolaridad18` por `n_per` versus por `n_18_mas` en zonas usadas por el modelo:
    - mediana: `0.0071`
    - p90: `0.0314`
    - máximo: `0.2153`
  - o sea, el cambio no revienta la variable, pero sí la deja conceptualmente mejor cerrada.

## 2026-03-30 - Política de imputación espacial model-ready para `ZONA777 = 528`
- Se decidió no alterar el parquet crudo `censo2024_zona777_agg_final.parquet`.
- La imputación queda en una capa separada `model-ready`, construida desde el EDA / futura integración a `07`.
- Implementación reusable en `lib/censo2024_zona777.py`:
  - helper `impute_missing_by_neighbor_median(...)`
  - usa vecinos contiguos de primer orden (`geometry.touches`)
  - imputa por mediana de vecinos válidos
  - falla explícitamente si no hay vecinos válidos para una variable faltante
- Motivación:
  - `ZONA777 = 528` sí aparece en `7,178` filas del pooled;
  - tiene `11` vecinos directos con dato válido en las 4 variables activas;
  - la mediana local difiere de forma no trivial de la mediana global, por lo que la imputación espacial es más defendible que una global.

## 2026-03-30 - Notebook nuevo `08` para integrar Censo sin seguir creciendo `07`
- Se creó `03_models/08_nested_logit_enriched_interannual_censo.qmd`.
- Decisión de diseño:
  - `07` queda como notebook de baseline transport-only;
  - `08` monta el bloque Censo de origen encima de la baseline ya cerrada:
    - `BUS_STOP_DENSITY`
    - `BUS_LINE_COUNT`
    - `METRO_LINE_COUNT`
- `08` construye y escribe artifacts separados:
  - `03_models/artifacts/interannual_enriched/censo2024_zona777_model_ready.parquet`
  - `03_models/artifacts/interannual_enriched/censo2024_zona777_model_ready_sample12pct.parquet`
  - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample12pct-censo4.parquet`
- El orden de corrida quedó:
  - `MNL baseline`
  - `MNL + bloque Censo completo`
  - `MNL + desgloses`
  - `Nested baseline`
  - `Nested + bloque Censo completo`
- Sanity check externo al notebook:
  - join sobre la muestra `sample12pct` preserva `2,239,867` filas;
  - audit de imputación: `4` filas (las 4 variables en `ZONA777 = 528`);
  - `missing_ratio_z = 0.0` tras el join Censo.

## 2026-03-31 - Réplica Larch de `08` enfocada en MNL
- Se creó `03_models/larch_logit/08_nested_logit_enriched_interannual_censo_larch.qmd`.
- Alcance:
  - `MNL baseline`;
  - `MNL + Censo full`;
  - desgloses `MNL` por:
    - `prom_edad`;
    - `prom_escolaridad18`;
    - `share_inmigrantes`;
    - `share_hacinamiento`;
  - variante candidata `prom_escolaridad18 + share_hacinamiento`.
- La réplica reutiliza el mismo pipeline de `08` para:
  - construir `censo2024_zona777_model_ready.parquet`;
  - estandarizar sobre zonas usadas por la muestra;
  - construir `pooled_2024_2025-estimation-sample{X}pct-censo4.parquet`;
  - derivar muestras baseline menores desde una muestra mayor disponible si falta la exacta.
- Configuración inicial:
  - `SAMPLE_FRACTION_ESTIMATION = 0.05`;
  - `LARCH_METHOD = slsqp`;
  - `LARCH_MAX_CAP = 20.0`.
- Validación práctica:
  - setup/config/helpers ejecutados con `larch-env` (`Larch 6.0.41`);
  - `build-censo-model-ready` y `build-estimation-sample-censo` corrieron sin error;
  - smoke MNL con `prom_escolaridad18_z` sobre `5,000` filas reales del parquet final también corrió sin error.
- Mejora posterior:
  - el helper `materialize_baseline_sample_if_needed(...)` de la réplica Larch ahora puede derivar la muestra baseline directamente desde `trips_context_pooled_2024_2025.parquet` si no existe una muestra exacta ni una mayor disponible;
  - con eso se validó `SAMPLE_FRACTION_ESTIMATION = 0.20`:
    - se escribió `pooled_2024_2025-estimation-sample20pct.parquet`;
    - se escribió `pooled_2024_2025-estimation-sample20pct-censo4.parquet`;
    - tamaño baseline resultante: `3,733,116` filas.
- Nota:
  - `quarto render --execute false` no pudo usarse como parser porque el `python3` por defecto del sistema no tiene `yaml/jupyter`; la validación se hizo ejecutando bloques del `.qmd` con `~/.local/share/mamba/envs/larch-env/bin/python`.

## 2026-03-31 - Notebook de auditoría cross-framework para el interanual
- Se creó `03_models/09_interannual_framework_audit.qmd`.
- Foco de la auditoría:
  - comparabilidad de muestra entre Biogeme y Larch;
  - estabilidad de coeficientes entre frameworks;
  - detección de flips de signo y diferencias relativas grandes.
- Estado inicial auditado:
  - `Biogeme`: `sample5pct`;
  - `Larch`: `sample20pct`.
- Resultado preliminar sobre `baseline`:
  - la comparación actual **no es una auditoría pura** porque mezcla framework con muestra (`sample5pct` vs `sample20pct`);
  - aun así, la divergencia es fuerte:
    - `n_common_params = 30`;
    - `n_sign_flips = 5`;
    - `median_rel_diff_pct ~ 27.82`;
    - `24` parámetros con diferencia relativa > `10%`.
- Flips de signo detectados en baseline:
  - `B_QR_RED_NO_LAB`;
  - `B_QR_RED_LOG_DEMAND`;
  - `B_QR_RED_LOG_METRO_LINE_COUNT`;
  - `B_QR_OTHER_LOG_DEMAND`;
  - `B_QR_OTHER_LOG_BUS_LINE_COUNT`.
- Lectura registrada:
  - con este estado no corresponde “creerle” ciegamente a Biogeme ni a Larch;
  - hace falta una auditoría estricta sobre **misma muestra exacta** antes de interpretar betas finamente;
  - por ahora, conviene privilegiar especificaciones más parsimoniosas y parámetros estables entre frameworks/muestras.

## 2026-03-31 - Auditoría baseline estricta `sample5pct` vs `sample5pct`
- Se corrió `Larch baseline` sobre la **misma muestra exacta** de `Biogeme`:
  - `03_models/larch_logit/results/08_interannual_censo/pooled_2024_2025-larch-sample5pct/`
- Resultado:
  - la divergencia **persiste aun con la misma muestra**;
  - baseline:
    - `n_common_params = 30`;
    - `n_sign_flips = 4`;
    - `median_rel_diff_pct ~ 27.83`;
    - `23` parámetros con diferencia relativa > `10%`.
- Flips de signo en baseline `sample5pct` vs `sample5pct`:
  - `B_QR_RED_NO_LAB`;
  - `B_QR_RED_LOG_DEMAND`;
  - `B_QR_RED_LOG_METRO_LINE_COUNT`;
  - `B_QR_OTHER_LOG_DEMAND`.
- Se añadió un chequeo de `LL` manual externo en `03_models/09_interannual_framework_audit.qmd` para baseline.
- Hallazgo crítico:
  - `Biogeme params` sobre la muestra común reproducen su `LL` reportado casi exactamente:
    - reportado: `-467338.700000`
    - manual: `-467338.693686`
  - `Larch params` sobre la misma muestra también reproducen exactamente su `LL` reportado:
    - reportado: `-467659.000515`
    - manual: `-467659.000515`
- Interpretación:
  - esto descarta un bug grueso de lectura de datos o de fórmula manual en la auditoría;
  - ambos vectores se están evaluando sobre la misma función de utilidad baseline;
  - pero `Larch` queda con un `LL` claramente peor (`ΔLL ≈ 320.3`) en una baseline `MNL`.
- Lectura metodológica provisional:
  - en un `MNL` lineal bien alineado, esta diferencia no debería persistir si ambos optimizadores llegan al óptimo;
  - por tanto, la sospecha principal pasa a ser **convergencia/optimización subóptima en la configuración actual de Larch**, no un problema de muestra;
  - mientras no se cierre esa brecha, no corresponde usar los coeficientes Larch baseline como evidencia de estabilidad fina.

## 2026-03-31 - Lectura dirigida de Larch 6 y corrección del diagnóstico de warm start
- Se revisó la instalación local `larch 6.0.41` y la documentación pública oficial (`larch.newman.me`).
- Hallazgo importante de versión:
  - la documentación pública sigue describiendo sobre todo la API `v5.x` (`larch.numba.Model`);
  - en la instalación local actual, `larch.Model` vive en `larch/model/jaxmodel.py` y mezcla `NumbaModel` con `OptimizeMixin`;
  - en nuestra réplica `08_larch`, el notebook fija explícitamente:
    - `m.compute_engine = "numba"`
  - por tanto, la ruta efectiva de optimización es la de `larch/model/numbamodel.py` + `larch/model/optimization.py`, no la JAX.
- Se confirmó en código local que:
  - el start real del optimizador sale de `model.pvals`;
  - `Model.set_values(...)` está deprecado en v6 y solo delega a `model.pvals = ...`;
  - `maximize_loglike(..., method='slsqp')` termina llamando a `scipy.optimize.minimize(model.logloss, model.pvals, jac=model.d_logloss, ...)`.
- Se corrigió la lectura del experimento de warm start:
  - el intento anterior de inyectar parámetros de Biogeme en Larch **no era válido** porque los nombres no coincidían;
  - Biogeme guardaba nombres con sufijo:
    - `_pooled_2024_2025`
  - Larch usa nombres sin ese sufijo.
- Una vez normalizados los nombres, el warm start sí funcionó correctamente:
  - `model.pvals = biogeme_params_normalized` deja el baseline Larch en:
    - `LL = -467338.693686`
  - ese valor coincide con el `LL` manual/auditado del baseline Biogeme sobre la misma muestra `sample5pct`;
  - al correr `maximize_loglike(method='slsqp', maxiter=5)` desde ese start, Larch se queda en ese mismo punto.
- Implicancia:
  - el problema ya no parece ser una diferencia de objetivo o de datos entre frameworks;
  - Larch puede evaluar y sostener el punto de Biogeme en la misma muestra;
  - la brecha observada al partir desde nulo apunta más bien al recorrido/tolerancias del optimizador desde ese start.
- También se corrigió una interpretación errónea de la gradiente:
  - `model.d_loglike()` devuelve la gradiente del **log-likelihood agregado**;
  - el optimizador usa `model.d_logloss()`, que es:
    - `-d_loglike / total_weight`
  - por eso una norma grande de `d_loglike` puede corresponder a una norma pequeña de `d_logloss`.
- En la baseline `sample5pct` de Larch desde nulo:
  - `result['d_logloss']` al terminar `SLSQP` es pequeña:
    - `||jac||_2 ≈ 0.00933`
  - y eso es consistente con el criterio de convergencia de SciPy;
  - no correspondía interpretar directamente `||d_loglike|| ≈ 8000` como “no convergió”.
- Lectura corregida:
  - el diagnóstico fuerte ahora es:
    - `SLSQP` desde nulo en Larch converge a una solución peor que el punto Biogeme, aun cuando Larch puede sostener el punto Biogeme si parte ahí;
  - esto sigue sugiriendo un problema de optimización práctica/tolerancias/start, pero no un bug demostrado en la función objetivo ni en la inyección correcta de parámetros.

## 2026-03-31 - Benchmark de optimización baseline en Larch (`sample5pct`)
- Se corrió el baseline `MNL` de Larch sobre la misma muestra `sample5pct` cambiando solo método/tolerancias de SciPy.
- Resultado clave:
  - `SLSQP` con opciones más estrictas sí recupera esencialmente el óptimo de Biogeme desde start nulo:
    - método: `slsqp`
    - opciones: `{'maxiter': 500, 'ftol': 1e-12}`
    - `LL = -467338.693683`
    - gradiente `d_logloss` final:
      - `||jac||_2 ≈ 4.34e-08`
      - `maxabs ≈ 3.25e-08`
  - ese `LL` coincide prácticamente con el de Biogeme auditado:
    - `-467338.693686`
- Contraste:
  - `SLSQP` con configuración default usada en el notebook:
    - `LL ≈ -467659.000515`
    - o sea, una solución claramente peor;
  - `L-BFGS-B` con `maxiter=500`, `ftol=1e-12`, `gtol=1e-8` no resolvió el problema:
    - terminó en `LL ≈ -470292.358481`
    - `success = False`
    - `message = STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT`
- Interpretación fuerte:
  - la divergencia baseline `Biogeme vs Larch` no se debe a una función objetivo distinta;
  - tampoco a una falla del warm start una vez corregidos los nombres;
  - el problema real es que la configuración default de `SLSQP` en Larch, al optimizar `logloss` promedio por caso, es demasiado laxa para nuestro modelo;
  - al endurecer `ftol` y permitir más iteraciones, Larch sí llega al mismo óptimo práctico que Biogeme.

## 2026-03-31 - Regeneración limpia de `sample15pct` para la réplica Larch de `08`
- Al preparar la muestra `15%` para correr los desgloses en `08_larch`, el join con Censo falló con:
  - `Join Censo dejó filas con socio faltante: 0.120770%`
- Diagnóstico:
  - el parquet baseline existente `pooled_2024_2025-estimation-sample15pct.parquet` era un artifact stale;
  - contenía zonas de origen fuera del soporte Censo ZONA777:
    - `849`, `850`, `851`, `852`, `853`
  - eso no era un problema del parquet Censo ni de la imputación, sino de la muestra baseline.
- Se parcheó `03_models/larch_logit/08_nested_logit_enriched_interannual_censo_larch.qmd` para aceptar:
  - `LARCH_FORCE_REBUILD_SAMPLE=1`
  - y así poder regenerar una muestra exacta aunque ya exista en disco.
- Luego se reconstruyó `sample15pct` desde la muestra baseline válida `sample20pct` con ratio estratificado `0.75`.
- Resultado:
  - nuevo baseline `sample15pct`: `2,799,836` filas;
  - se escribió correctamente:
    - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample15pct.parquet`
    - `03_models/artifacts/interannual_enriched/censo2024_zona777_model_ready_sample15pct.parquet`
    - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample15pct-censo4.parquet`
- Conclusión:
  - la muestra `15%` ya quedó limpia y reutilizable;
  - el rerun de desgloses en `08_larch` puede hacerse sobre ese artifact sin volver a forzar rebuild.

## 2026-03-31 - Extensión del EDA Censo para una segunda ronda de variables
- Se extendió `02_eda/eda_censo2024_zona777_model_join.qmd` para mantener intacta la primera ronda y agregar una segunda ronda paralela para:
  - `share_internet`
  - `share_serv_compu`
  - `share_serv_tel_movil`
  - `share_discapacidad`
  - `share_analfabet`
- En `setup` se agregaron:
  - `SECOND_ROUND_SOCIO_VARS`
  - helpers reutilizables para:
    - resumen de calidad;
    - construcción `model-ready` con imputación espacial;
    - mapas espaciales;
    - matriz de correlación.
- Al final del notebook quedaron nuevas secciones para la ronda 2:
  - diccionario conceptual;
  - quality summary;
  - zonas problemáticas;
  - impacto de esas zonas en `trips_context`;
  - imputación espacial `model-ready`;
  - mapas;
  - correlaciones;
  - join check model-ready;
  - resúmenes trip-weighted;
  - cobertura sobre la muestra de estimación.
- Verificación liviana:
  - las columnas nuevas sí existen en `censo2024_zona777_agg_final.parquet`;
  - el render completo con `quarto` no pudo validarse usando el Python del sistema porque carece de `yaml/jupyter`, pero no hubo señal de columnas faltantes ni labels duplicados.

## 2026-03-31 - Fix de dependencia oculta en la ronda 2 del EDA Censo
- Al correr `second-round-problematic-zones-used-in-trips` directamente, el notebook falló con:
  - `NameError: name 'df_trip_zones' is not defined`
- Root cause:
  - la ronda 2 reutilizaba `df_trip_zones` y `df_trips_keys` creados en una celda de la ronda 1;
  - por tanto, las nuevas celdas no eran autosuficientes y dependían del orden de ejecución.
- Fix aplicado:
  - se agregó `load_trip_zone_context(...)` en `lib/interannual_offer_context.py`;
  - se añadió un test unitario para ese helper en `lib/test_interannual_offer_context.py`;
  - en el notebook se agregó `ensure_trip_zone_context_loaded()` en `setup`;
  - las celdas:
    - `second-round-problematic-zones-used-in-trips`
    - `second-round-explicit-join-check-model-ready`
    ahora reconstruyen el contexto de trips si no existe en memoria.
- Verificación:
  - `python -m unittest lib.test_interannual_offer_context` -> `5 tests OK`
  - smoke sobre el parquet real:
    - `rows = 18,665,583`
    - `n_zonas = 784`

## 2026-03-31 - Screening de segunda ronda habilitado en `08_larch`
- Se amplió `03_models/larch_logit/08_nested_logit_enriched_interannual_censo_larch.qmd` para no podar ex ante ninguna variable de la ronda 2.
- El artifact `sample + censo` ahora incorpora y estandariza también:
  - `share_internet`
  - `share_serv_compu`
  - `share_serv_tel_movil`
  - `share_discapacidad`
  - `share_analfabet`
- El `full` original se mantiene igual:
  - sigue usando solo las 4 variables de la primera ronda.
- Nuevas corridas `MNL` standalone agregadas en Larch:
  - `mnl_interannual_censo_share_internet_larch`
  - `mnl_interannual_censo_share_serv_compu_larch`
  - `mnl_interannual_censo_share_serv_tel_movil_larch`
  - `mnl_interannual_censo_share_discapacidad_larch`
  - `mnl_interannual_censo_share_analfabet_larch`
- También quedaron agregadas las combinaciones con `prom_escolaridad18` para la ronda 2:
  - `mnl_interannual_censo_escolaridad_internet_larch`
  - `mnl_interannual_censo_escolaridad_serv_compu_larch`
  - `mnl_interannual_censo_escolaridad_serv_tel_movil_larch`
  - `mnl_interannual_censo_escolaridad_discapacidad_larch`
  - `mnl_interannual_censo_escolaridad_analfabet_larch`
- Implicancia operativa:
  - para usar estas corridas, hay que rerunear en `08_larch` al menos:
    - `build-censo-model-ready`
    - `build-estimation-sample-censo`
  - luego ya se pueden ejecutar las nuevas celdas de estimación/resultados.

## 2026-03-31 - Paridad de screening ronda 2 en `08` Biogeme
- Se amplió `03_models/08_nested_logit_enriched_interannual_censo.qmd` con la misma lógica de screening que ya existía en `08_larch`.
- El artifact `sample + censo` de `08` ahora también incorpora y estandariza las variables de ronda 2.
- Se agregaron corridas `MNL` standalone para:
  - `share_internet`
  - `share_serv_compu`
  - `share_serv_tel_movil`
  - `share_discapacidad`
  - `share_analfabet`
- Y también las combinaciones:
  - `prom_escolaridad18 + share_internet`
  - `prom_escolaridad18 + share_serv_compu`
  - `prom_escolaridad18 + share_serv_tel_movil`
  - `prom_escolaridad18 + share_discapacidad`
  - `prom_escolaridad18 + share_analfabet`
- El `full` viejo y el bloque `nested` no se redefinieron; siguen usando la primera ronda.

## 2026-04-17 - Auditoría OSM amplia y cierre de shortlist inicial por familia/tag
- Se abrió la rama `OpenStreetMap / built environment` en:
  - `02_eda/eda_osm_zona777.qmd`
- La lógica acordada fue:
  - no definir variables OSM ex ante;
  - primero inventariar qué `keys` y `key=value` existen realmente en el soporte `ZONA777`;
  - luego filtrar por:
    - masa;
    - cobertura territorial;
    - interpretabilidad;
    - y no redundancia obvia con bloques ya existentes.
- Para evitar una consulta única demasiado pesada a Overpass, el notebook quedó configurado en modo `per_key`, con:
  - logging por familia;
  - checkpoints reutilizables en `02_eda/tmp/osm_zona777/raw_by_key/`;
  - y export raw consolidado en parquet:
    - `02_eda/tmp/osm_zona777/osm_zona777_raw.parquet`
- Resultado de la auditoría amplia:
  - objetos raw concatenados antes de dedupe: `652,460`
  - objetos tras dedupe por `element/id`: `629,152`
  - columnas raw observadas: `1,421`
- Familias con mayor masa observada:
  - `highway`
  - `building`
  - `natural`
  - `amenity`
  - `leisure`
  - `landuse`
  - `shop`
  - `public_transport`
- Conclusión metodológica de esa primera pasada:
  - `highway`, `building` y `natural` no se descartan, pero se dejan para una segunda fase por requerir tratamiento geométrico más fino;
  - para una primera ronda de construcción por zona se priorizan familias más interpretables y agregables por conteo/presencia.

## 2026-04-17 - Shortlist OSM inicial cerrada para segunda etapa
- Tras revisar:
  - `osm-key-inventory`
  - `osm-tagvalue-inventory`
  - `osm-zona-key-coverage`
  - `osm-shortlist-tagvalue-coverage`
  - `osm-shortlist-tagvalue-screening`
  se cerró una shortlist inicial de familias OSM para pasar a construcción de variables candidatas.
- Familias retenidas:
  - `amenity`
  - `shop`
  - `leisure`
  - `public_transport`
  - `office`
  - `landuse`
- Decisión importante:
  - `public_transport=*` queda en observación por posible solapamiento con variables de infraestructura de transporte ya presentes en el modelo;
  - aun así se mantiene auditada, no descartada.
- Dentro de esa shortlist, las candidatas prioritarias quedan así:
  - `amenity=school`
  - `amenity=restaurant`
  - `amenity=pharmacy`
  - `amenity=kindergarten`
  - `amenity=clinic`
  - `amenity=university`
  - `shop=convenience`
  - `shop=supermarket`
  - `shop=bakery`
  - `shop=hardware`
  - `shop=mall`
  - `leisure=park`
  - `leisure=playground`
  - `leisure=sports_centre`
  - `office=company`
  - `office=government`
  - `office=educational_institution`
  - `landuse=residential`
  - `landuse=industrial`
  - `landuse=retail`
  - `landuse=commercial`
- Se deja explícitamente documentado que:
  - `amenity=university` debe entrar sí o sí como candidata, aunque no sea de las más masivas;
  - `shop=mall` también debe entrar sí o sí, por su interpretación de centralidad comercial mayor.
- Variables `public_transport` que quedan en observación:
  - `public_transport=platform`
  - `public_transport=station`
  - `public_transport=stop_position`
  Motivo:
  - pueden pisarse con:
    - `BUS_STOP_DENSITY`
    - `BUS_LINE_COUNT`
    - `METRO_LINE_COUNT`
    - y otras proxies de infraestructura ya integradas.
- Descartes claros en esta etapa:
  - valores genéricos `*=yes`
  - y tags semánticamente poco útiles para modelación zonal inicial, por ejemplo:
    - `amenity=bench`
    - `amenity=parking_space`
    - `amenity=waste_basket`
    - `amenity=parking_entrance`
    - `amenity=bicycle_parking`
    - `amenity=toilets`
    - `amenity=fountain`
    - `amenity=recycling`
- Nota metodológica especial:
  - `landuse` parece prometedora, pero la versión actual vía punto representativo es solo exploratoria;
  - si sobrevive a la siguiente ronda, convendrá reconstruirla por área intersectada con `ZONA777` en vez de conteo por punto.
- Conclusión:
  - la etapa de auditoría OSM amplia queda cerrada;
  - el siguiente paso ya no es más screening general, sino construir un bloque `OSM -> ZONA777 model-ready` para esta shortlist inicial.

## 2026-04-17 - Primera ronda OSM fijada para modelación
- Tras construir el primer bloque `OSM -> ZONA777` en:
  - `lib/osm_zona777.py`
  - `02_eda/eda_osm_zona777_model_join.qmd`
  se definió una **primera ronda corta de modelación** con variables OSM prioritarias.
- Variables OSM elegidas para esa primera ronda:
  - `osm_leisure_park`
  - `osm_amenity_school`
  - `osm_shop_supermarket`
  - `osm_amenity_restaurant`
  - `osm_shop_mall`
  - `osm_amenity_university`
  - `osm_amenity_pharmacy`
- Criterio de selección:
  - mantener una primera ronda corta y altamente interpretable;
  - combinar:
    - espacio público / recreación (`park`);
    - equipamiento educativo (`school`, `university`);
    - equipamiento/comercio cotidiano (`supermarket`, `restaurant`, `pharmacy`);
    - centralidad comercial mayor (`mall`);
  - evitar en esta primera ronda variables OSM que puedan pisarse más directamente con el bloque ya existente de infraestructura de transporte.
- Decisión explícita:
  - `osm_amenity_university` y `osm_shop_mall` quedan retenidas sí o sí en esta primera ronda, no solo en rondas posteriores.
- Variables OSM que quedan para rondas siguientes:
  - `osm_amenity_kindergarten`
  - `osm_amenity_clinic`
  - `osm_shop_convenience`
  - `osm_shop_bakery`
  - `osm_shop_hardware`
  - `osm_leisure_playground`
  - `osm_leisure_sports_centre`
  - `osm_office_company`
  - `osm_office_government`
  - `osm_office_educational_institution`
  - y `landuse=*` como rama más exploratoria.
- `public_transport=*` se mantiene fuera de la primera ronda de modelación por ahora, en observación, debido a posible redundancia con:
  - `BUS_STOP_DENSITY`
  - `BUS_LINE_COUNT`
  - `METRO_LINE_COUNT`
  - y otros controles estructurales ya presentes en el modelo.

## 2026-04-19 - Segunda ronda OSM fijada para screening univariado
- Tras revisar la primera ronda OSM, se cerró una **segunda ronda corta** enfocada en dimensiones complementarias de actividad económica y equipamiento barrial.
- Variables elegidas para esta segunda ronda:
  - `osm_shop_convenience`
  - `osm_leisure_playground`
  - `osm_office_company`
  - `osm_leisure_sports_centre`
  - `osm_office_government`
- Orden operativo sugerido:
  - `shop_convenience`
  - `leisure_playground`
  - `office_company`
  - `leisure_sports_centre`
  - `office_government`
- Criterio:
  - complementar la primera ronda con medidas de:
    - comercio cotidiano barrial (`shop_convenience`);
    - equipamiento recreativo fino (`playground`, `sports_centre`);
    - actividad económica / institucional (`office_company`, `office_government`);
  - evitar por ahora nuevas variables `public_transport=*` y `landuse=*`, por mayor riesgo de redundancia o de tratamiento geométrico insuficiente.
- Decisión operativa:
  - esta segunda ronda entra a `03_models/10_nested_logit_enriched_interannual_osm.qmd` como **screening univariado adicional**;
  - no se define todavía una nueva ruta multivariada con estas variables hasta ver sus univariados.

## 2026-04-19 - Cierre metodológico de la rama OSM tras screening MNL
- La rama OSM queda cerrada, por ahora, como **exploración estructurada de built environment**, ya con:
  - auditoría amplia;
  - shortlist por `key=value`;
  - bloque `OSM -> ZONA777 model-ready`;
  - y screening MNL en `03_models/10_nested_logit_enriched_interannual_osm.qmd`.
- Resultado general:
  - varias variables OSM muestran señal interpretable en corridas univariadas;
  - pero los bloques OSM multivariados se vuelven numéricamente inestables muy rápido, incluso en combinaciones de a dos.
- Balance de la primera ronda OSM:
  - fuertes y limpios:
    - `osm_amenity_school`
    - `osm_shop_supermarket`
  - útiles / defendibles:
    - `osm_shop_mall`
    - `osm_amenity_university`
    - `osm_amenity_pharmacy`
  - débil:
    - `osm_leisure_park`
  - prometedora pero inestable:
    - `osm_amenity_restaurant`
- Balance de la segunda ronda OSM:
  - fuertes y estables:
    - `osm_leisure_sports_centre`
    - `osm_leisure_playground`
  - fuertes pero inestables:
    - `osm_shop_convenience`
    - `osm_office_company`
    - `osm_office_government`
- Combinaciones OSM probadas:
  - `school + supermarket` fue el mejor par, pero con gradiente todavía alto;
  - `school + mall` y `supermarket + mall` no quedaron utilizables;
  - no se justifica seguir forzando bloques OSM multivariados grandes en esta etapa.
- Decisión metodológica:
  - OSM sí aporta variables candidatas útiles e interpretables;
  - pero, por ahora, debe quedar como:
    - screening exploratorio;
    - comparación sustantiva de proxies de built environment;
    - y reserva de candidatas puntuales para etapas posteriores;
  - no como un bloque multivariado OSM consolidado dentro del frente principal del modelo.
- Variables OSM que merecen quedar retenidas con mejor evidencia empírica hasta ahora:
  - `osm_amenity_school`
  - `osm_shop_supermarket`
  - `osm_leisure_sports_centre`
  - `osm_leisure_playground`
- Variables OSM que conviene mantener en observación, pero con cautela numérica:
  - `osm_shop_mall`
  - `osm_amenity_university`
  - `osm_amenity_pharmacy`
  - `osm_shop_convenience`
  - `osm_office_company`
  - `osm_office_government`

## 2026-04-23 - Reunión con profesora y rediseño del flujo territorial
- Se revisó el notebook-resumen `03_models/11_screening_territorial_summary.qmd` con la profesora y se concluyó que **no sirve como artefacto de reporte**.
- Críticas principales al `11`:
  - mezcla demasiados bloques en una sola narrativa;
  - presenta resultados de forma incompleta o inconsistente entre secciones;
  - no deja ver con suficiente claridad el rol de `BIP`;
  - y no organiza las tablas como reporte formal de resultados econométricos.
- Decisión:
  - `11` no se usará como documento final de presentación;
  - puede quedar como memo técnico interno, pero no como output a mostrar ni como base de escritura.

### Cambio de criterio de lectura para selección de variables
- La profesora sugirió una lógica más simple y operativa para el screening:
  - agregar variables **una a una**;
  - revisar sobre todo si la variable estimada tiene `t-value` defendible (`|t| >= 1.96` como regla práctica);
  - no sobrerreaccionar, en esta etapa, a pequeñas variaciones de `rho²`, `LL`, `AIC` o gradiente si la variable nueva está entrando con señal clara.
- Precisión metodológica interna:
  - este consejo no elimina la importancia de la convergencia;
  - pero sí obliga a no usar como criterio principal de descarte comparaciones demasiado globales entre bloques antes de revisar parámetro por parámetro.

### Nueva exigencia de especificación y reporte
- La profesora indicó que **deben estimarse también los coeficientes para `BIP`** cuando sea posible.
- Implicancia:
  - el protocolo anterior, centrado en mostrar principalmente `QR_RED` y `QR_OTHER`, queda incompleto;
  - las nuevas corridas y tablas deben reportar, por variable:
    - `beta_bip`, `t-value`, `p-value`
    - `beta_qr_red`, `t-value`, `p-value`
    - `beta_qr_other`, `t-value`, `p-value`
- Esto aplica tanto para variables de `Censo` como de `OSM`.

### Sospecha metodológica crítica: la no convergencia es anómala
- La profesora consideró **sumamente extraño** que tantos `MNL` no estén convergiendo, especialmente bajo configuraciones básicas y con muchas iteraciones disponibles.
- Hipótesis a revisar:
  - presencia de `NaN` o `null` en artifacts/model-ready/samples;
  - joins defectuosos o pérdida silenciosa de filas;
  - variables constantes o casi constantes;
  - estandarización con problemas;
  - especificación incorrecta de utilidades al integrar bloques nuevos;
  - o algún bug metodológico que hoy esté contaminando varios resultados.
- Decisión:
  - abrir una tarea separada y prioritaria de **diagnóstico de convergencia**;
  - no seguir tomando la no convergencia como un mero hecho empírico sin auditarla.

### Nueva secuencia de trabajo acordada
- No corregir `11`.
- Rediseñar el flujo en etapas separadas:
  1. diagnóstico de convergencia;
  2. rerun de screening `Censo` variable por variable, ahora incluyendo `BIP`;
  3. rerun de screening `OSM` variable por variable, ahora incluyendo `BIP`;
  4. integración acumulativa por bloque:
     - `Censo`
     - `OSM`
  5. corrida conjunta final:
     - `Censo + OSM`
- La lógica cambia desde “cerrar rápidamente shortlist por comparaciones globales” a “integrar disciplinadamente y revisar parámetro a parámetro”.

### Entregable final esperado
- La profesora pidió un **informe/reporte estilo paper**, siguiendo como referencia:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/papers/1-s2.0-S0968090X2100454X-main.pdf`
- Ese reporte debe incluir:
  - metodología;
  - función de utilidad;
  - definición de todas las variables;
  - y tablas de resultados con formato horizontal por alternativa:
    - `beta_bip`, `t-value`, `p-error`
    - `beta_qr_red`, `t-value`, `p-error`
    - `beta_qr_other`, `t-value`, `p-error`
- Decisión documental:
  - **no se abre un workstream nuevo**;
  - esto sigue perteneciendo a `od-buffers-nested-logit`, pero entra a una nueva fase metodológica post-reunión.

## 2026-04-23 - Diagnóstico de convergencia MNL y mini experimento de optimización Biogeme
- Se creó `03_models/12_mnl_convergence_diagnostics.qmd` para auditar por separado:
  - integridad de muestras;
  - `nulls`;
  - columnas degeneradas;
  - extremos luego de estandarización;
  - correlaciones simples;
  - y la especificación efectiva que se estaba estimando.
- Hallazgos del diagnóstico de datos:
  - no aparecieron `nulls` silenciosos en las muestras `Censo` ni `OSM`;
  - no hubo evidencia de joins defectuosos o pérdida rara de filas;
  - no aparecieron columnas constantes;
  - en `Censo`, el problema principal parece ser redundancia/colinealidad entre proxies socioeducativas;
  - en `OSM`, además de redundancia interna, hay colas/extremos mucho más pesados y fuerte concentración espacial en variables como:
    - `osm_shop_mall_density_km2_z`
    - `osm_amenity_university_density_km2_z`
    - `osm_amenity_pharmacy_density_km2_z`
    - `osm_office_government_density_km2_z`
    - `osm_amenity_restaurant_density_km2_z`
- Hallazgo metodológico clave del diagnóstico:
  - las variables territoriales nuevas en `08` y `10` hoy entran solo en `QR_RED` y `QR_OTHER`;
  - no entran en `BIP`;
  - esto confirma el gap de especificación que la profesora marcó en la reunión.

### Mini experimento de optimización Biogeme
- Se creó `03_models/13_biogeme_optimizer_mini_experiment.qmd` para aislar una duda puntual:
  - mantener fija la utilidad `MNL`;
  - variar solo la configuración del optimizador en `Biogeme`;
  - comparar modelos `Censo` y `OSM`, tanto univariados como multivariados.
- Configuraciones comparadas:
  - `current_bfgs_never`
    - `simple_bounds_BFGS`
    - `calculating_second_derivatives = never`
  - `simple_bounds_no_hessian`
    - `simple_bounds`
    - `calculating_second_derivatives = never`
  - `simple_bounds_analytical`
    - `simple_bounds`
    - `calculating_second_derivatives = analytical`
  - `automatic_default`
    - `optimization_algorithm = automatic`
    - `calculating_second_derivatives = analytical`
- Modelos usados en el barrido:
  - `Censo` univariado:
    - `share_cine18_universitaria_o_mas_micro_z`
  - `Censo` multivariado parsimonioso:
    - `share_cine18_universitaria_o_mas_micro_z`
    - `share_hacinamiento_z`
    - `share_discapacidad_z`
    - `share_inmigrantes_z`
  - `OSM` univariado:
    - `osm_amenity_school_density_km2_z`
  - `OSM` multivariado corto:
    - `school + supermarket`
  - `OSM` multivariado `full` primera ronda.

### Resultado principal del experimento
- Quedó refutada la regla práctica que veníamos usando:
  - `Final gradient norm <= 50 => converge`
- Esa regla era una heurística nuestra, no el criterio de `Biogeme`.
- `Biogeme` reporta convergencia usando:
  - `convergence`
  - `Cause of termination`
  - `Relative gradient`
  - y el detalle de iteraciones/evaluaciones
  en el `YAML` del resultado.
- Resultado empírico:
  - `automatic_default` y `simple_bounds_analytical` dieron resultados idénticos en los 5 modelos probados;
  - `current_bfgs_never` y `simple_bounds_no_hessian` dieron resultados idénticos entre sí.
- Lectura:
  - en estos modelos, `automatic_default` cae efectivamente en la familia Newton/trust-region con Hessiana;
  - y las variantes sin Hessiana quedan en la familia `BFGS` con trust region.

### Qué cambió en la lectura de convergencia
- Para modelos univariados simples:
  - `BFGS + no Hessian` sí puede converger;
  - por ejemplo:
    - `censo_uni_universitaria_o_mas`
    - `osm_uni_school`
- Para modelos multivariados territoriales:
  - `BFGS + no Hessian` falla con frecuencia vía:
    - `Maximum number of iterations reached`
  - mientras que `automatic_default` / `simple_bounds_analytical` sí convergen limpiamente.
- Casos más importantes:
  - `censo_multi_parsimonioso`
    - con `current_bfgs_never`: `convergence = false`, `Maximum number of iterations reached`
    - con `automatic_default`: `convergence = true`
  - `osm_multi_school_supermarket`
    - con `current_bfgs_never`: `convergence = false`
    - con `automatic_default`: `convergence = true`
  - `osm_multi_full_r1`
    - con `current_bfgs_never`: `convergence = false`, `LL = -233248.7`, `AIC = 466585.3`
    - con `automatic_default`: `convergence = true`, `LL = -233236.4`, `AIC = 466560.9`
- Este último caso es especialmente importante:
  - no es solo un problema de criterio de parada;
  - la configuración antigua estaba llegando a una solución peor.

### Decisión metodológica nueva
- A partir de ahora, no corresponde seguir usando `Final gradient norm <= 50` como sello de convergencia en `Censo` u `OSM`.
- El criterio correcto a reportar para `Biogeme` pasa a ser:
  - `yaml_convergence`
  - `yaml_cause_of_termination`
  - `yaml_relative_gradient`
  - y solo de apoyo `Final gradient norm`
- Configuración por defecto recomendada para el rerun stepwise:
  - `automatic_default`
- `simple_bounds_analytical` queda como configuración equivalente/consistente para chequeos de sensibilidad.
- La configuración antigua:
  - `simple_bounds_BFGS`
  - `calculating_second_derivatives = never`
  deja de ser el default para modelos multivariados territoriales.

## 2026-04-23 - Nuevo notebook operativo para screening territorial con MNL y Nested
- Se creó `03_models/14_territorial_stepwise_mnl_nested.qmd` como reemplazo operativo del notebook `11`.
- Alcance del nuevo notebook:
  - estimación `MNL` y `Nested` dentro del mismo flujo;
  - convergencia reportada desde `YAML`, no desde umbrales ad hoc sobre `Final gradient norm`;
  - variables territoriales nuevas entrando en:
    - `BIP`
    - `QR_RED`
    - `QR_OTHER`
  - screening univariado por bloque;
  - bloque `Censo full`;
  - bloque `OSM full`;
  - bloque conjunto `Censo + OSM`.
- Decisión de diseño:
  - no se modifica `11`;
  - `11` queda como memo exploratorio viejo;
  - `14` pasa a ser el artefacto operativo para la fase post-reunión con la profesora.
- Decisión operativa:
  - el notebook nuevo queda con `RUN_ESTIMATION = False` por defecto;
  - permite correr subconjuntos vía `ACTIVE_MODEL_LABELS`;
  - usa `automatic_default` como configuración base de `Biogeme`;
  - y deja una tabla horizontal por variable con:
    - `beta_bip`, `t_bip`, `p_bip`
    - `beta_qr_red`, `t_qr_red`, `p_qr_red`
    - `beta_qr_other`, `t_qr_other`, `p_qr_other`
  - además de una tabla separada para `MU_QR` en los modelos `Nested`.

## 2026-04-29 - Duda metodológica sobre variables comunes y reestimación para reporte

- En el reporte informal del modelo logit territorial se dejó explícito el problema de identificación para variables comunes al viaje/zona:
  - año, franja, demanda, oferta agregada, Censo y OSM tienen el mismo valor para todas las alternativas de un viaje;
  - en MNL solo se identifican diferencias de utilidad, no niveles absolutos de coeficientes comunes.
- Se documentaron dos opciones para discutir con la profesora:
  - Opción A: `BIP` como base para variables comunes, con coeficientes solo para `QR_RED` y `QR_OTHER`.
  - Opción B: efectos reportables para `BIP`, `QR_RED` y `QR_OTHER` usando una restricción de identificación, inicialmente suma cero.
- Se creó `03_models/15_mnl_common_variable_parametrization_options.qmd` como notebook separado para no mezclar esta duda metodológica con el notebook operativo `14`:
  - nuevo preset `joint_mnl_censo_osm_method_options`;
  - nuevo campo de especificación `common_variable_parametrization`;
  - modos disponibles:
    - `current`: comportamiento previo, controles comunes base normalizados contra `BIP` y `extra_cols` con tres betas libres;
    - `bip_base`: Opción A, variables comunes y `extra_cols` normalizadas contra `BIP`;
    - `sum_zero`: Opción B, variables comunes y `extra_cols` con coeficiente `BIP` derivado como `-(QR_RED + QR_OTHER)`.
- El notebook `14` se mantuvo como frente operativo principal de screening territorial, sin los cambios específicos de Opción A/B.
- Modelos preparados para reestimación metodológica:
  - `mnl_joint_censo_main_4_plus_osm_main_plus_transport_shelter_subway_entrance_option_a_bip_only_alt_specific`;
  - `mnl_joint_censo_main_4_plus_osm_main_plus_transport_shelter_subway_entrance_option_b_bip_reportable_sum_zero`.
- Se decidió no correr la variante `main + subway_entrance` en este notebook metodológico; la comparación se concentra solo en `main + shelter + subway_entrance`.

## 2026-04-30 - Cierre del reporte informal del modelo logit territorial

- Estado final: **tarea cerrada**.
- Reporte LaTeX finalizado en:
  - `docs/reports/modelo-logit-territorial/reporte_modelo_logit.tex`
  - `docs/reports/modelo-logit-territorial/reporte_modelo_logit.pdf`
- Estructura final del reporte:
  - nota inicial e índice;
  - sección 1: descripción del problema y alternativas (`BIP`, `QR_RED`, `QR_OTHER`);
  - sección 2: especificación MNL/RUM, función de utilidad y duda metodológica sobre variables comunes;
  - sección 3: variables del modelo, incluyendo viaje, temporalidad, demanda/oferta, Censo y OSM;
  - sección 4: estrategia de estimación y muestra;
  - sección 5: ajuste y convergencia;
  - sección 6: parámetros en formato wide para Opción A y Opción B;
  - sección 7: interpretación de signos y significancia;
  - sección 8: decisión de modelo principal y sensibilidades;
  - anexos: tablas extendidas con errores estándar robustos.
- Se incorporaron los resultados finales de `03_models/15_mnl_common_variable_parametrization_options.qmd` para el modelo `main + shelter + subway_entrance`:
  - Opción A: `bip_only_alt_specific`;
  - Opción B: `bip_reportable_sum_zero`;
  - ambas con 52 parámetros, 466,639 observaciones, `LL final = -232257.1`, `AIC = 464618.2`, `BIC = 465193.0`.
- Decisión metodológica documentada:
  - Opción A mantiene `BIP` como referencia para variables comunes;
  - Opción B reporta coeficientes para tres alternativas mediante restricción de suma cero;
  - ambas representan el mismo contenido empírico y tienen el mismo ajuste global;
  - queda como decisión abierta cuál usar como reporte principal tras feedback docente.
- Correcciones finales aplicadas antes del cierre:
  - la función de utilidad se corrigió para distinguir variables alternativa-específicas `X_{kni}` y variables comunes `Z_{mn}`;
  - la referencia a E. Graells-Garrido se reformuló como inspiración metodológica, con nota al pie y aclaración de que se implementó una versión simplificada/operacional;
  - se agregó una nota inicial indicando que el reporte es un documento de trabajo y no la versión definitiva del modelo de tesis.
- Verificación:
  - comando usado:
    - `latexmk -g -pdf -interaction=nonstopmode -halt-on-error reporte_modelo_logit.tex`
  - directorio:
    - `docs/reports/modelo-logit-territorial/`
  - resultado:
    - PDF compila correctamente.
- Riesgo residual conocido:
  - persisten warnings menores de `Overfull \hbox` en la tabla resumen de variables de la sección 3;
  - no bloquean la compilación ni afectan las tablas principales/anexos;
  - se pueden corregir si se quiere pulir visualmente antes de una entrega más formal.
- Follow-ups después del envío:
  - recibir feedback de profesoras/profesores;
  - decidir entre Opción A y Opción B para la especificación principal;
  - evaluar nuevas variables de infraestructura/acceso, seguridad, puntos de carga/pago y confiabilidad operacional para futuras iteraciones.

## 2026-05-05 - Feedback docente post-reporte y reordenamiento de próximos pasos

- La reunión posterior al envío del reporte aclaró la duda metodológica sobre variables comunes:
  - la profesora cuestionó la motivación de la parametrización con restricción de suma cero;
  - para variables alternativa-específicas, como tiempos y transbordos, los coeficientes por alternativa son identificables porque los atributos se calculan para cada método de pago;
  - para variables comunes al viaje o a la zona, como `ANIO_2025`, demanda/oferta zonal, Censo u OSM, corresponde fijar una alternativa base y estimar las otras alternativas respecto de esa base;
  - lectura operacional: la **Opción A** (`BIP` como referencia para variables comunes) queda como especificación principal provisional.
- Decisión metodológica provisional:
  - modelo principal: `MNL` con observación a nivel de viaje individual;
  - variables comunes: `BIP` se mantiene como alternativa base, y se estiman coeficientes para `QR_OTHER` y `QR_RED` respecto de `BIP`;
  - variables alternativa-específicas: tiempos y transbordos mantienen coeficientes estimados por alternativa cuando son identificables;
  - la Opción B con suma cero queda como ejercicio metodológico no principal, útil solo para mostrar equivalencia de ajuste si se requiere.
- Interpretación sustantiva destacada por la profesora:
  - el resultado de `T_ESPERA_TRASB` para `QR_RED`, cercano a cero y no significativo, puede ser informativo;
  - hipótesis sugerida: usuarios de app Red podrían presentar menor desutilidad por espera en transbordo porque la información disponible les permite anticipar la espera o usar ese tiempo en otra actividad;
  - este punto requiere una discusión cuidadosa, no tratarse simplemente como ausencia de efecto.
- Nuevos requerimientos para el reporte/modelo:
  - agregar `odds ratios` para mejorar la interpretación de coeficientes logit;
  - buscar literatura sobre educación, adopción digital, herramientas de pago/app y brecha digital en transporte público;
  - en particular, respaldar el resultado asociado a `share_cine18_universitaria_o_mas_micro_z` y su relación con mayor probabilidad de usar herramientas digitales como app Red;
  - evaluar nuevas variables censales o proxies territoriales: ingreso/bajo ingreso, porcentaje de mujeres, niños en sala cuna y estudiantes escolares.
- Sobre la sensibilidad "sin `ZONA777`":
  - se discutió probar una versión del modelo sin la agregación por `ZONA777`;
  - al revisar la factibilidad, se concluye que no debe correrse por ahora con la especificación final, porque Censo, OSM, demanda y oferta final dependen de la zona de origen;
  - omitir `ZONA777` implicaría omitir precisamente las variables territoriales finales o construir un pipeline distinto basado en buffers/coordenadas;
  - decisión actual: dejar esta sensibilidad en pausa hasta definir si vale la pena desarrollar un pipeline no zonal específico.
- Próximos pasos inmediatos:
  - corregir el reporte para dejar la Opción A como especificación principal;
  - generar tabla de odds ratios para el modelo principal;
  - iniciar búsqueda bibliográfica sobre educación/adopción digital/mobile ticketing/app de transporte;
  - auditar disponibilidad y construcción de nuevas variables censales candidatas antes de integrarlas al modelo.

## 2026-05-05 - Literatura efectivamente analizada sobre adopción digital y transporte

- Se creó un memo de revisión bibliográfica en:
  - `docs/reports/modelo-logit-territorial/literatura_adopcion_digital.md`
- Se creó un memo de análisis profundo en:
  - `docs/reports/modelo-logit-territorial/literatura_adopcion_digital_analisis_profundo.md`
- Estos documentos registran los papers revisados y considerados más útiles para interpretar los resultados actuales, pero **no constituyen una selección definitiva ni exhaustiva de literatura**. Otros papers identificados o futuras búsquedas pueden seguir siendo útiles para el marco teórico, discusión de resultados o anexos.
- Rama educación, nivel socioeconómico y brecha digital:
  - Durand et al. (2021), `Access denied? Digital inequality in transport services`.
  - Boyko y Schaefer (2026), `Smartphone apps for mobility access from a social inequality perspective`.
  - Brakewood y Kocur (2013), `Unbanked Transit Riders and Open Payment Fare Collection`.
- Rama mobile ticketing y pago digital en transporte público:
  - Owusu-Agyemang et al. (2024), `Transit made Easy: Examining the adoption and impact of mobile fare payment technology among bus riders`.
  - Brakewood et al. (2020), `An evaluation of the benefits of mobile fare payment technology from the user and operator perspectives`.
  - Wani et al. (2025), `Digital payment adoption in public transportation: Mediating role of mode choice segments in developing cities`.
- Rama apps, información en tiempo real y valor de la espera:
  - Watkins et al. (2011), `Where Is My Bus? Impact of mobile real-time information on the perceived and actual wait time of transit riders`.
  - Brakewood y Watkins (2019), `A literature review of the passenger benefits of real-time transit information`.
  - Kaplan et al. (2017), `The role of information systems in non-routine transit use of university students: Evidence from Brazil and Denmark`.
- Lectura sustantiva provisional:
  - `share_cine18_universitaria_o_mas_micro_z` puede discutirse como proxy territorial de capital educativo/digital, acceso financiero y capacidad de adopción de herramientas digitales, sin interpretarlo causalmente a nivel individual.
  - `QR_RED` debe tratarse como alternativa tecnológicamente mediada: combina pago, app oficial, posible acceso a información, familiaridad digital y menor fricción de uso.
  - El resultado de `T_ESPERA_TRASB` para `QR_RED` puede presentarse como compatible con literatura sobre información en tiempo real y menor espera percibida, pero solo como hipótesis interpretativa porque el modelo no observa directamente uso efectivo de información en tiempo real.

## 2026-05-06 - Sensibilidades sociodemográficas: mujeres y asistencia parvularia

- Se evaluaron nuevas variables censales sugeridas en reunión docente, manteniendo la especificación principal provisional:
  - `MNL` con observación a nivel de viaje individual;
  - `BIP` como referencia para variables comunes (`bip_only_alt_specific`);
  - modelo base actual entendido como `Censo main 4 + OSM main + shelter + subway_entrance`.
- Variables evaluadas:
  - `share_mujeres_z`: proporción de mujeres en la zona, estandarizada;
  - `share_asistencia_parv_z`: proporción de población de 0 a 5 años que asiste a educación parvularia en la zona, estandarizada.
- Para poder evaluar `share_asistencia_parv_z` se regeneró el agregado Censo final desde el Kingston:
  - cartografía: `/Volumes/KINGSTON/tesis-project/raw/censo2024/cartografia_parquet/Cartografia_censo2024_Pais_Manzanas.parquet`;
  - zonas: `/Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp`;
  - salida final: `02_eda/tmp/censo2024_zona777/censo2024_zona777_agg_final.parquet`;
  - el agregado regenerado contiene `share_asistencia_parv`, `n_asistencia_parv` y `n_edad_0_5`.
- Resultados de ajuste global frente al main actual sin estas dos variables:
  - main actual: `LL = -232257.1`, `AIC = 464618.2`, `BIC = 465193.0`, `n_params = 52`;
  - `main + share_mujeres_z`: `LL = -232253.4`, `AIC = 464614.8`, `BIC = 465211.7`, `n_params = 54`;
  - `main + share_asistencia_parv_z`: `LL = -232250.6`, `AIC = 464609.3`, `BIC = 465206.2`, `n_params = 54`;
  - `main + share_mujeres_z + share_asistencia_parv_z`: `LL = -232247.7`, `AIC = 464607.5`, `BIC = 465226.5`, `n_params = 56`.
- Lectura de ajuste:
  - las extensiones mejoran `LL` y `AIC`;
  - `BIC` sube por la penalización adicional de parámetros, especialmente en el modelo combinado;
  - el tradeoff queda documentado: mejora incremental e interpretabilidad versus parsimonia.
- Resultados sustantivos para `share_mujeres_z`:
  - modelo `main + mujeres`: `QR_RED = 0.024475`, `t = 2.649`, `p = 0.0081`; `QR_OTHER` no significativo;
  - modelo combinado: `QR_RED = 0.021419`, `t = 2.403`, `p = 0.0162`; `QR_OTHER` no significativo;
  - interpretación provisional: zonas con mayor proporción de mujeres se asocian con mayor utilidad relativa de `QR_RED` frente a `BIP`, pero no con `QR_OTHER`.
- Resultados sustantivos para `share_asistencia_parv_z`:
  - modelo `main + asistencia_parv`: `QR_RED = 0.051579`, `t = 3.456`, `p = 0.00055`; `QR_OTHER` no significativo;
  - modelo combinado: `QR_RED = 0.048482`, `t = 3.223`, `p = 0.00127`; `QR_OTHER` no significativo;
  - interpretación provisional: zonas con mayor asistencia parvularia relativa se asocian con mayor utilidad relativa de `QR_RED` frente a `BIP`, y la señal se mantiene incluso controlando por `share_mujeres_z`.
- Decisión de trabajo:
  - integrar ambas variables como extensión sociodemográfica candidata, porque aportan interpretación y ambas sobreviven en el modelo combinado;
  - `share_asistencia_parv_z` es la señal más robusta;
  - `share_mujeres_z` aporta una señal secundaria pero consistente para `QR_RED`;
  - reportar explícitamente que el modelo combinado mejora `LL/AIC` pero empeora `BIC`, para no ocultar el costo de parsimonia.
- Riesgo interpretativo:
  - ambas variables son características territoriales de origen y no atributos individuales observados;
  - deben interpretarse como asociaciones contextuales con la elección de medio de pago, no como efectos causales individuales.

## 2026-05-07 - EOD Santiago 2012 como fuente externa potencial

- Se revisaron archivos locales de la Encuesta Origen Destino Santiago 2012:
  - informes: `/Users/vicenteonetto/Downloads/Informe_EOD-2012_Santiago`;
  - zonificación: `/Users/vicenteonetto/Downloads/Zonificacion_EOD-2012_Santiago`;
  - base Access: `/Users/vicenteonetto/Downloads/base_datos_eodStgo_2012.accdb`.
- Hallazgos preliminares:
  - la zonificación EOD 2012 es un shapefile con 866 zonas, 45 comunas y CRS `EPSG:32719`;
  - la base `.accdb` contiene señales claras de tablas/campos `Hogar`, `Persona`, `Viaje`, `Etapa`, `IngresoHogar`, `Sexo`, `Estudios`, `Actividad`, `Numveh` y `Factor`;
  - los informes documentan imputación de ingresos individuales y agregación a ingreso total del hogar;
  - el informe define estratos de ingreso de hogar:
    - bajo: hasta `$400.000`;
    - medio: `$400.001` a `$1.600.000`;
    - alto: más de `$1.600.000`;
  - el ingreso de hogar imputado aparece prácticamente completo en el informe (`99,82%` de hogares con ingreso completo).
- Variables potencialmente útiles si se habilita lectura de la base:
  - `share_hogares_ingreso_bajo_eod2012`;
  - `ingreso_medio_hogar_eod2012`;
  - `share_sin_auto_eod2012` o tasa de motorización;
  - composición por edad, sexo, estudios, actividad o estudiantes, agregadas territorialmente.
- Limitaciones metodológicas:
  - la EOD 2012 es muy anterior al período de modelación 2024-2025;
  - no puede interpretarse como condición socioeconómica contemporánea sin cautela;
  - podría servir como proxy territorial histórico/persistente o como validación externa, no como variable principal sin justificación adicional;
  - para usarla en el modelo actual se requeriría un cruce espacial entre zonas EOD 2012 y `ZONA777`, probablemente por intersección/área;
  - el entorno actual no tiene `mdbtools`, `LibreOffice`, `ODBC` ni `pyodbc`, por lo que todavía no se pudo exportar/inventariar la base `.accdb` completa.
- Decisión actual:
  - dejar la EOD 2012 en pausa como camino potencial;
  - no integrarla todavía al modelo;
  - retomarla solo si se decide construir una variable de ingreso/bajo ingreso territorial y se resuelve la lectura/exportación de la base Access.

## 2026-05-11 - EOD 2012 retomada como sensibilidad territorial histórica

- Se decidió explorar la EOD Santiago 2012 como fuente de variables territoriales históricas/persistentes, no como indicador contemporáneo directo.
- Motivación:
  - aunque la encuesta está desactualizada para 2024-2025, algunas señales podrían ser relativamente persistentes a escala territorial;
  - especialmente ranking/percentil de ingresos por zona, motorización, estructura horaria de viajes al trabajo/estudio y composición socioeconómica.
- Se instaló `mdbtools` vía Homebrew para poder leer/exportar la base Access:
  - input: `/Users/vicenteonetto/Downloads/base_datos_eodStgo_2012.accdb`;
  - tablas exportadas a CSV en `data/external/eod2012/raw_csv/`;
  - tablas principales exportadas: `Hogar`, `Persona`, `Viaje`;
  - lookups exportados: `TramoIngreso`, `JornadaTrabajo`, `Sexo`, `Estudios`, `Actividad`, `Ocupación`, `Periodo`, `Proposito`, `PropositoAgregado`, `Modo`, `ModoPriPub`, `ModoMotor`.
- Se creó el script reproducible:
  - `scripts/build_eod2012_zone_features.py`.
- Salidas creadas:
  - `data/processed/eod2012/eod2012_zone_features_eodzone.parquet`;
  - `data/processed/eod2012/eod2012_zone_features_eodzone.csv`;
  - `data/processed/eod2012/eod2012_zone_features_summary.csv`.
- Cobertura base:
  - zonificación EOD: 866 zonas, CRS `EPSG:32719`;
  - `Hogar`: 18.264 registros;
  - `Persona`: 60.054 registros;
  - `Viaje`: 113.591 registros;
  - dataset zonal EOD generado: 866 zonas y 41 variables `eod2012_*`.
- Variables candidatas generadas:
  - ingreso de hogar medio/mediano 2012 y sus percentiles zonales (`*_pct_rank`) para evitar lectura nominal afectada por inflación;
  - proporción de hogares de ingreso bajo/medio/alto según tramos absolutos 2012;
  - proporción de hogares sin auto y vehículos promedio;
  - composición de personas por sexo, educación superior/universitaria, trabajo y estudio;
  - jornada laboral completa/parcial entre personas trabajadoras;
  - proporción de viajes laborales en transporte público;
  - distribución horaria de viajes, incluyendo `al trabajo` y `al estudio` en punta mañana;
  - hora media de inicio para viajes `al trabajo` y `al estudio`.
- Ajuste importante:
  - `Persona.Actividad` no usa códigos numéricos sino letras multiselección (`A`, `B`, `A;B`, etc.);
  - se interpretó `A = trabaja` y `B = estudia`, consistente con presencia de `JornadaTrabajo` y `Ocupacion`;
  - el script usa esa codificación para las variables laborales/estudiantiles.
- Diagnóstico preliminar de variables:
  - `eod2012_ingreso_hogar_mean` tiene cobertura en 790 de 866 zonas;
  - `eod2012_ingreso_hogar_mean_pct_rank` es preferible a pesos nominales para modelación;
  - `eod2012_share_hogares_sin_auto` tiene señal territorial interpretable;
  - `eod2012_share_viajes_al_trabajo_punta_manana` tiene cobertura en 767 zonas, media `0,615`;
  - `eod2012_hora_inicio_al_trabajo_mean` tiene cobertura en 767 zonas, media `9,15` y mediana `8,84`;
  - `eod2012_share_viajes_transporte_publico` tiene cobertura en 846 zonas.
- Decisión metodológica provisional:
  - usar EOD 2012 solo como sensibilidad histórica/contextual;
  - priorizar variables relativas o estructurales, no valores monetarios absolutos;
  - no integrarla al modelo principal hasta cruzarla correctamente con `ZONA777` y revisar correlación con Censo/OSM actuales.
- Siguiente paso:
  - construir crosswalk espacial `EOD2012 zona -> ZONA777` por intersección/área cuando esté disponible el shapefile ZONA777 local;
  - luego transferir features EOD a ZONA777 y evaluar correlaciones/cobertura sobre la muestra de estimación.

## 2026-05-11 - EOD 2012 transferida a ZONA777 por intersección espacial

- Se montó Kingston y se encontró el shapefile ZONA777 usado por el proyecto:
  - `/Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp`.
- Diagnóstico de insumos espaciales:
  - `ZONA777`: 804 geometrías, 803 códigos `ZONA777` únicos, CRS no declarado pero coordenadas lon/lat;
  - `EOD 2012`: 866 zonas, CRS `EPSG:32719`;
  - el campo `Z_EOD` en ZONA777 existe, pero no se usó como llave principal porque contiene códigos compuestos y zonas externas; se prefirió cruce espacial por área.
- Se creó el script:
  - `scripts/build_eod2012_zona777_features.py`.
- Decisiones técnicas del script:
  - asigna `EPSG:4326` al shapefile ZONA777 y reproyecta a `EPSG:32719`;
  - corrige geometrías inválidas con `make_valid`;
  - disuelve el duplicado de `ZONA777 = 493`;
  - calcula intersecciones EOD2012 x ZONA777;
  - normaliza pesos por área intersectada dentro de cada ZONA777;
  - transfiere variables `eod2012_*` como promedios ponderados por área.
- Salidas creadas:
  - `data/processed/eod2012/eod2012_to_zona777_area_crosswalk.csv`;
  - `data/processed/eod2012/eod2012_zone_features_zona777.parquet`;
  - `data/processed/eod2012/eod2012_zone_features_zona777.csv`;
  - `data/processed/eod2012/eod2012_zone_features_zona777_summary.csv`.
- Cobertura espacial:
  - 803 zonas ZONA777 generadas;
  - cobertura media de área: `0,999741`;
  - cobertura mínima: `0,970190`;
  - ninguna ZONA777 quedó sin intersección EOD;
  - cada ZONA777 intersecta en promedio `4,93` zonas EOD.
- Cobertura en muestra de estimación `sample2pct`:
  - la muestra usa 772 zonas de origen;
  - solo `ZONA777 = 831` queda sin variables EOD de hogar/persona;
  - esto afecta aproximadamente `0,0334%` de filas;
  - la misma zona sí tiene variables EOD de viajes.
- Variables candidatas con buena cobertura ya disponibles en ZONA777:
  - `eod2012_ingreso_hogar_mean_pct_rank`;
  - `eod2012_ingreso_hogar_median_pct_rank`;
  - `eod2012_share_hogares_sin_auto`;
  - `eod2012_share_viajes_al_trabajo_punta_manana`;
  - `eod2012_hora_inicio_al_trabajo_mean`;
  - `eod2012_share_viajes_transporte_publico`;
  - `eod2012_share_educ_superior`.
- Decisión metodológica provisional:
  - la EOD 2012 queda técnicamente lista para análisis exploratorio y sensibilidad histórica;
  - antes de integrarla a modelos, falta revisar correlaciones con variables Censo/OSM actuales y decidir una estrategia de imputación para el caso `ZONA777 = 831`.

## 2026-05-11 - Proxy de grupo de ingreso EOD 2012 por percentiles ponderados

- Se decidió construir un proxy de grupos de ingreso usando solo `IngresoHogar` de la EOD 2012.
- No se debe presentar como clasificación socioeconómica oficial `ABC1/C2/C3/D/E`, porque esa clasificación incorpora más dimensiones que ingreso.
- Nombre conceptual recomendado:
  - `income_proxy`;
  - `ABC1_proxy` solo como etiqueta operativa para el tramo superior de ingreso.
- Construcción:
  - se clasifican hogares EOD según percentiles de `IngresoHogar`;
  - los percentiles se calculan ponderados por `Factor`, es decir, usando el peso de expansión muestral de cada hogar;
  - luego se agregan a zona como proporción ponderada de hogares en cada grupo.
- Cortes ponderados obtenidos en pesos 2012:
  - `E`: percentil 0-10, hasta `$158.533`;
  - `D`: percentil 10-45, hasta `$470.000`;
  - `C3`: percentil 45-70, hasta `$800.000`;
  - `C2`: percentil 70-90, hasta `$1.456.668`;
  - `ABC1_proxy`: percentil 90-100.
- Variables agregadas al pipeline:
  - `eod2012_share_hogares_e_income_proxy`;
  - `eod2012_share_hogares_d_income_proxy`;
  - `eod2012_share_hogares_c3_income_proxy`;
  - `eod2012_share_hogares_c2_income_proxy`;
  - `eod2012_share_hogares_abc1_income_proxy`;
  - `eod2012_share_hogares_de_income_proxy`.
- Scripts actualizados:
  - `scripts/build_eod2012_zone_features.py`;
  - `scripts/build_eod2012_zona777_features.py` no requirió cambios lógicos, pero se regeneraron sus salidas.
- Salidas nuevas/relevantes:
  - `data/processed/eod2012/eod2012_income_proxy_cutpoints.csv`;
  - `data/processed/eod2012/eod2012_income_proxy_validation.csv`;
  - `data/processed/eod2012/eod2012_zone_features_eodzone.parquet`;
  - `data/processed/eod2012/eod2012_zone_features_zona777.parquet`.
- Validación contra Censo 2024 y consistencia interna:
  - `ABC1_proxy` vs `share_cine18_universitaria_o_mas_micro`: Pearson `0,701`, Spearman `0,600`;
  - `D+E proxy` vs `share_hacinamiento`: Pearson `0,528`, Spearman `0,566`;
  - `ABC1_proxy` vs `share_hogares_sin_auto`: Pearson `-0,698`, Spearman `-0,518`;
  - `D+E proxy` vs `share_cine18_universitaria_o_mas_micro`: Pearson `-0,650`, Spearman `-0,616`;
  - `ABC1_proxy` vs `share_hacinamiento`: Pearson `-0,471`, Spearman `-0,544`.
- Interpretación:
  - el proxy por percentiles tiene validez convergente razonable: zonas con mayor `ABC1_proxy` se asocian con mayor educación universitaria y menor hacinamiento/sin-auto;
  - zonas con mayor `D+E proxy` se asocian con mayor hacinamiento y menor educación universitaria;
  - por lo tanto, el proxy parece defendible como sensibilidad histórica de composición socioeconómica territorial, no como indicador socioeconómico contemporáneo oficial.

## 2026-05-11 - Notebook EOD income proxy stepwise

- Se creó un notebook separado para testear variables EOD 2012 sin contaminar el flujo principal:
  - `03_models/16_eod2012_income_proxy_stepwise.qmd`.
- Base del modelo:
  - MNL;
  - Censo main 4;
  - OSM main;
  - `osm_transport_shelter_yes_density_km2_z`;
  - `osm_railway_subway_entrance_density_km2_z`;
  - `share_mujeres_z`;
  - `share_asistencia_parv_z`.
- Parametrización:
  - `BIP` queda normalizado a cero para variables comunes;
  - tiempos y transbordos mantienen coeficientes por alternativa.
- Preset activo:
  - `joint_mnl_censo_osm_eod_income_proxy_stepwise`.
- Modelos activos:
  - `mnl_joint_current_main_mujeres_parv_plus_eod_abc1_income_proxy`;
  - `mnl_joint_current_main_mujeres_parv_plus_eod_de_income_proxy`;
  - `mnl_joint_current_main_mujeres_parv_plus_eod_abc1_de_income_proxy`;
  - `mnl_joint_current_main_mujeres_parv_plus_eod_dummy_high_abc1_de_income_proxy`.
- Variante dummy agregada:
  - `eod2012_dummy_high_abc1_income_proxy`;
  - `eod2012_dummy_high_de_income_proxy`;
  - ambas se definen como 1 si la zona está en el top 25% de la distribución ZONA777 de la proporción correspondiente;
  - umbrales observados:
    - `ABC1_proxy` P75: `0,1163`;
    - `D+E_proxy` P75: `0,6001`.
- Artefactos materializados en prueba liviana:
  - `03_models/artifacts/interannual_enriched/eod2012_zona777_model_ready_sample2pct.parquet`;
  - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample2pct-eod2012.parquet`;
  - `03_models/artifacts/interannual_enriched/pooled_2024_2025-estimation-sample2pct-censo4-micro-osm-eod2012.parquet`.
- Imputación aplicada:
  - solo `ZONA777 = 831` no tenía variables EOD de hogar/persona;
  - se imputó con mediana EOD/ZONA777 para `eod2012_share_hogares_abc1_income_proxy` y `eod2012_share_hogares_de_income_proxy`;
  - el caso afecta aproximadamente `0,0334%` de filas de la muestra.
- Estado:
  - el notebook compila estáticamente;
  - se ejecutó hasta `estimation-design` sin entrar a estimación;
  - el diseño activo contiene 4 modelos MNL;
  - listo para correr la celda `run-screening`.

## 2026-05-12 - Resultados EOD income proxy: variables continuas y dummies

- Se corrieron modelos MNL usando como base el modelo territorial actual:
  - Censo main 4;
  - OSM main;
  - `osm_transport_shelter_yes_density_km2_z`;
  - `osm_railway_subway_entrance_density_km2_z`;
  - `share_mujeres_z`;
  - `share_asistencia_parv_z`.
- Explicación simple de las variables EOD:
  - primero se clasifican los hogares de la EOD 2012 según su ingreso relativo dentro de la encuesta, usando percentiles ponderados por el factor de expansión muestral;
  - luego, para cada zona, se calcula qué proporción de hogares cae en el tramo alto de ingreso (`ABC1_proxy`) y qué proporción cae en los tramos bajos (`D+E_proxy`);
  - por lo tanto, una variable como `eod2012_share_hogares_abc1_income_proxy_z` no dice que la zona sea oficialmente ABC1, sino que históricamente tenía una mayor proporción relativa de hogares en el tramo superior de ingreso de la EOD 2012;
  - las dummies resumen esta misma idea de forma más discreta: valen 1 para zonas con alta concentración relativa de ese grupo y 0 para el resto;
  - en particular, `eod2012_dummy_high_abc1_income_proxy` identifica zonas en el 25% superior de concentración `ABC1_proxy`, y `eod2012_dummy_high_de_income_proxy` identifica zonas en el 25% superior de concentración `D+E_proxy`.
- Umbrales usados para las dummies:
  - `high_ABC1_proxy = 1` si `share_hogares_abc1_income_proxy >= 0,1163`;
  - `high_D+E_proxy = 1` si `share_hogares_de_income_proxy >= 0,6001`.
- Modelo con proporciones continuas `ABC1_proxy` y `D+E_proxy`:
  - `eod2012_share_hogares_abc1_income_proxy_z`: `QR_OTHER` negativo y marginal (`beta = -0,0154`, `t = -1,87`, `p = 0,062`); `QR_RED` cercano a cero y no significativo (`beta = -0,0053`, `t = -0,34`);
  - `eod2012_share_hogares_de_income_proxy_z`: `QR_OTHER` positivo y significativo (`beta = 0,0369`, `t = 4,53`, `p < 0,001`); `QR_RED` negativo pero no significativo (`beta = -0,0123`, `t = -0,67`).
- Modelos continuos por separado:
  - solo `ABC1_proxy`: `QR_OTHER` negativo y significativo (`beta = -0,0281`, `t = -3,61`), `QR_RED` no significativo;
  - solo `D+E_proxy`: `QR_OTHER` positivo y significativo (`beta = 0,0421`, `t = 5,49`), `QR_RED` no significativo.
- Modelo con dummies de alta concentración:
  - `eod2012_dummy_high_abc1_income_proxy_z`: negativo y significativo para `QR_OTHER` (`beta = -0,0264`, `t = -4,38`) y para `QR_RED` (`beta = -0,0421`, `t = -3,44`);
  - `eod2012_dummy_high_de_income_proxy_z`: no significativo para `QR_OTHER` ni para `QR_RED`.
- Lectura interpretativa provisional:
  - la señal más consistente aparece en `QR_OTHER`: zonas históricamente con mayor proporción de hogares `D+E_proxy` se asocian con mayor utilidad relativa de `QR_OTHER`, mientras que zonas con mayor proporción `ABC1_proxy` tienden a asociarse con menor utilidad relativa de `QR_OTHER`;
  - `QR_RED` no presenta una señal robusta en las variables continuas de ingreso EOD, pero sí aparece una penalización en zonas de alta concentración `ABC1_proxy` cuando se usa la especificación dummy;
  - esto no respalda una lectura simple de "mayor ingreso implica mayor uso QR"; más bien sugiere que el gradiente territorial histórico de ingreso puede estar capturando diferencias de contexto urbano, acceso, composición de usuarios o patrones de adopción que deben interpretarse con cautela.
- Estabilidad de parámetros antiguos:
  - los parámetros base de año, horario, tiempos de espera, transbordos y demanda/oferta mantienen signos e interpretación general;
  - la historia de `T_ESPERA_TRASB` se mantiene: `BIP` y `QR_OTHER` presentan desutilidad significativa, mientras que `QR_RED` sigue cercano a cero y no significativo;
  - las mayores variaciones aparecen en variables de oferta/demanda, especialmente en la especificación dummy, pero no se observa una ruptura estructural de los resultados principales.
- Decisión metodológica pendiente:
  - estas variables EOD quedan como candidatas interpretativamente útiles para discutir con la profesora;
  - antes de fijar una especificación final, hay que cotejar si conviene usar la versión continua, la versión dummy, o una selección más parsimoniosa;
  - por ahora se mantienen como sensibilidad histórica de ingreso territorial basada en EOD 2012, con la advertencia explícita de que no corresponden a una clasificación socioeconómica oficial ni contemporánea.

## 2026-05-12 - Sensibilidad EOD con motorización histórica (`numveh_mean`)

- Se analizó `eod2012_numveh_mean`, definido como el promedio histórico de vehículos por hogar en cada zona EOD 2012, transferido a `ZONA777` por intersección espacial.
- Diagnóstico descriptivo:
  - media zonal: `0,592` vehículos/hogar;
  - mediana zonal: `0,443`;
  - P75: `0,686`;
  - P90: `1,238`;
  - la distribución es asimétrica, con una cola alta de zonas muy motorizadas.
- Correlaciones relevantes:
  - con `eod2012_share_hogares_sin_auto`: `-0,915`;
  - con `eod2012_share_hogares_abc1_income_proxy`: `0,815`;
  - con `eod2012_share_hogares_de_income_proxy`: `-0,723`.
- Se probaron dos sensibilidades adicionales en `03_models/16_eod2012_income_proxy_stepwise.qmd`:
  - ingresos continuos (`ABC1_proxy + D+E_proxy`) + `eod2012_numveh_mean_z`;
  - dummies de alta concentración (`high_ABC1_proxy + high_D+E_proxy`) + `eod2012_numveh_mean_z`.
- Resultado principal:
  - `eod2012_numveh_mean_z` resulta negativo y significativo para `QR_OTHER`;
  - en el modelo continuo: `beta_QR_OTHER = -0,0324`, `t = -3,32`;
  - en el modelo dummy: `beta_QR_OTHER = -0,0388`, `t = -4,51`;
  - para `QR_RED` no aparece una señal robusta.
- Efecto sobre proxies de ingreso:
  - en el modelo continuo, al incluir `numveh_mean`, `ABC1_proxy` pierde señal (`t_QR_OTHER = -0,29`), mientras `D+E_proxy` permanece positivo y significativo para `QR_OTHER` (`beta = 0,0301`, `t = 3,57`);
  - en el modelo dummy, `high_ABC1_proxy` sigue negativo y significativo para ambas alternativas QR, mientras `high_D+E_proxy` sigue sin señal.
- Decisión metodológica provisional:
  - `numveh_mean` se considera una sensibilidad útil y sustantivamente interpretable como motorización histórica territorial;
  - sin embargo, no conviene incorporarla simultáneamente con los proxies de ingreso como especificación principal, porque presenta alta colinealidad conceptual y empírica con ellos;
  - la lectura defendible es que `numveh_mean` confirma que parte de la señal EOD de ingreso alto está asociada a mayor disponibilidad de vehículo, no que el proxy de ingreso deba reemplazarse automáticamente;
  - por ahora queda registrada como diagnóstico/sensibilidad para discutir con la profesora antes de fijar la especificación final.

## 2026-05-13 - Candidato econométrico actual: especificación `parsimonious`

- Se probó una batería de cuatro modelos MNL con macrozonas en `03_models/16_eod2012_income_proxy_stepwise.qmd`, partiendo desde cero para cada estimación:
  - `socio_clean`: elimina `share_hacinamiento_z` y `eod2012_share_hogares_abc1_income_proxy_z`;
  - `osm_local_clean`: elimina `osm_leisure_sports_centre_density_km2_z` y `osm_shop_convenience_density_km2_z`;
  - `no_shelter`: elimina `osm_transport_shelter_yes_density_km2_z`;
  - `parsimonious`: elimina simultáneamente `share_hacinamiento_z`, `eod2012_share_hogares_abc1_income_proxy_z`, `osm_leisure_sports_centre_density_km2_z` y `osm_shop_convenience_density_km2_z`.
- Las cuatro especificaciones convergieron correctamente (`yaml_convergence = true`).
- Comparación de ajuste:
  - modelo macro completo previo: `LL = -232189,9`, `AIC = 464523,8`, `BIC = 465319,6`;
  - `socio_clean`: `LL = -232204,8`, `AIC = 464545,5`, `BIC = 465297,2`;
  - `osm_local_clean`: `LL = -232200,6`, `AIC = 464537,2`, `BIC = 465288,8`;
  - `no_shelter`: `LL = -232204,3`, `AIC = 464548,6`, `BIC = 465322,3`;
  - `parsimonious`: `LL = -232214,2`, `AIC = 464556,5`, `BIC = 465263,9`.
- Lectura:
  - por AIC, el modelo macro completo sigue siendo el mejor;
  - por BIC, `parsimonious` es el mejor candidato, seguido por `osm_local_clean`;
  - sacar `shelter` no parece conveniente, porque empeora BIC frente al completo y además `shelter` mantiene señal estable en los modelos donde se conserva.
- Estabilidad de parámetros:
  - los parámetros de viaje (`T_ESPERA_INI`, `T_ESPERA_TRASB`, `N_TRASB`, `T_VEH`) se mantienen estables;
  - `share_cine18_universitaria_o_mas_micro_z` sigue siendo la señal sociodemográfica dominante, especialmente para `QR_RED`;
  - `share_mujeres_z` y `share_asistencia_parv_z` se mantienen positivos y significativos para `QR_RED`;
  - `eod2012_share_hogares_de_income_proxy_z` se mantiene positivo y significativo para `QR_OTHER`, no para `QR_RED`;
  - `ABC1_proxy` no era significativo y al retirarlo no desestabiliza `D+E_proxy`;
  - `sports_centre` y `convenience` tienen interpretación sustantiva débil frente a su aporte incremental.
- Decisión provisional:
  - `parsimonious` queda como candidato econométrico principal actual;
  - el modelo macro completo queda como sensibilidad de mayor ajuste;
  - `osm_local_clean` queda como sensibilidad alternativa si se quiere retener `hacinamiento` y `ABC1` pero limpiar OSM local.
- Advertencia interpretativa:
  - al retirar `hacinamiento` y `ABC1_proxy`, parte de la heterogeneidad socio-territorial se concentra más en `share_cine18_universitaria_o_mas_micro_z` y en macrozonas;
  - esto se considera aceptable bajo el criterio de parsimonia, pero debe reportarse como decisión metodológica y no como prueba de causalidad.

## 2026-05-14 - Verificación de atributos OD-alternativa de viaje

- Se verificó la duda metodológica levantada en reunión docente: si tiempos y transbordos estaban siendo tratados como promedios zonales o como atributos por alternativa.
- Corrección importante de interpretación:
  - las columnas `TVH_*`, `TEI_*`, `TET_*` y `NTR_*` **no son atributos individuales puros observados para las tres alternativas de cada viaje**;
  - se construyen en `lib/od_buffers_nested_logit.py` como promedios observados por par origen-destino (`zona_inicio_viaje`, `zona_fin_viaje`) y `tipo_pago`;
  - para la alternativa efectivamente elegida se aplica lógica `leave-one-out` cuando hay más de una observación de esa alternativa en el OD, evitando que el propio viaje determine completamente su atributo promedio;
  - para alternativas no elegidas se usa el promedio observado de los viajes de ese OD realizados con ese `tipo_pago`;
  - por lo tanto, son atributos de contexto **OD × alternativa de pago**, no promedios simples por zona de origen.
- En `03_models/16_eod2012_income_proxy_stepwise.qmd`, la función de utilidad usa columnas alternativa-específicas:
  - tiempos en vehículo: `TVH_BIP`, `TVH_QR_RED`, `TVH_QR_OTHER`;
  - espera inicial: `TEI_BIP`, `TEI_QR_RED`, `TEI_QR_OTHER`;
  - espera en transbordo: `TET_BIP`, `TET_QR_RED`, `TET_QR_OTHER`;
  - número de transbordos: `NTR_BIP`, `NTR_QR_RED`, `NTR_QR_OTHER`.
- Diagnóstico empírico sobre `pooled_2024_2025-estimation-sample2pct-censo4-micro-osm-eod2012.parquet`:
  - `TVH_BIP` tiene `235.413` valores únicos en `466.639` observaciones;
  - `TVH_QR_RED` tiene `46.478` valores únicos;
  - `TVH_QR_OTHER` tiene `90.685` valores únicos;
  - `TEI_BIP` tiene `182.297` valores únicos;
  - `TET_BIP` tiene `120.459` valores únicos;
  - `NTR_BIP` tiene `35.373` valores únicos;
  - dentro de grupos `zona_inicio_viaje × franja_v2` con al menos 10 observaciones, la proporción de grupos con variación interna es `1,0` para las columnas revisadas principales.
- Decisión:
  - no se requiere crear una nueva especificación para "sacar promedios zonales", porque los atributos no son promedios zonales sino promedios OD × alternativa con leave-one-out para la alternativa elegida;
  - si la profesora exige usar atributos puramente observados del viaje individual para la alternativa elegida, hay que aclarar que para alternativas no elegidas no existe un contrafactual individual observado; habría que definir otra estrategia de imputación/choice set;
  - lo que sí queda documentado es que las variables territoriales, demanda/oferta, Censo, OSM, EOD y macrozonas siguen siendo controles comunes por zona/origen, como corresponde a su definición.
- Cambio reproducible:
  - se agregó una celda `check-od-alt-trip-attrs` al notebook `03_models/16_eod2012_income_proxy_stepwise.qmd` para validar automáticamente existencia y variación de estas columnas antes de la estimación.

## 2026-05-14 - Sensibilidad pedida por profesora: atributos observados por viaje

- La profesora pidió probar explícitamente cómo cambia el modelo si, en vez de usar los atributos OD × alternativa (`TVH_*`, `TEI_*`, `TET_*`, `NTR_*`), se usan los valores efectivamente observados en cada viaje.
- Decisión metodológica:
  - no se reemplaza el modelo principal OD × alternativa;
  - se agrega una sensibilidad separada, porque los valores observados del viaje son comunes a las tres alternativas para una misma observación y por lo tanto solo son identificables como interacciones con alternativas respecto de una base;
  - bajo esta sensibilidad, `BIP` queda como alternativa base para estos atributos comunes observados;
  - se estiman coeficientes para `QR_OTHER` y `QR_RED` sobre `OBS_TVH`, `OBS_TEI`, `OBS_TET` y `OBS_NTR`.
- Interpretación esperada:
  - estos coeficientes no deben leerse como desutilidad genérica de tiempo/transbordos para cada alternativa;
  - deben leerse como asociación entre las características realizadas del viaje y la probabilidad relativa de elegir `QR_OTHER` o `QR_RED` frente a `BIP`.
- Cambio reproducible:
  - `lib/od_buffers_nested_logit.py` ahora permite exportar métricas realizadas con `include_realized_metrics=True`;
  - `03_models/16_eod2012_income_proxy_stepwise.qmd` incorpora el preset `joint_mnl_censo_osm_eod_parsimonious_observed_trip_attrs`;
  - ese preset activa dos modelos sobre el candidato parsimonioso: `MNL` y `Nested`, ambos con `trip_attr_mode = observed_common`;
  - el notebook construye una muestra `*-observed-trip-attrs.parquet`, verifica que replique exactamente las filas del baseline sample y luego genera la muestra conjunta Censo + OSM + EOD + macrozonas con columnas `OBS_*`.
