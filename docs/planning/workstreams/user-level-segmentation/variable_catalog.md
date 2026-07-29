# Catalogo De Variables — Segmentacion User-Level

Este catalogo registra decisiones por bloque para construir futuras matrices de
segmentacion. No es un contrato cerrado: cada bloque se agrega despues de una
auditoria especifica y revision conjunta.

Roles:

- `input_mobility_pattern`: patron espacial/franja/modo o scores derivados.
- `input_behavioral`: conducta de uso para matriz `behavioral_wide`.
- `input_structural_sensitivity`: socio-demografia, geografia, oferta o acceso
  para matriz `structural_wide`.
- `posthoc_only`: variable para describir segmentos, no para construirlos.
- `exclude`: no usar como input de segmentacion.

Tiers:

- `main`: candidato principal del bloque.
- `sensitivity`: usar en variantes o pruebas de robustez.
- `diagnostic`: util para EDA, no input principal.
- `drop`: descartar salvo justificacion posterior.

Nota de transformaciones:

- Las tablas por bloque registran la transformacion pensada originalmente para
  PCA/KMeans (`z-score / block scaling`), donde centrar variables es valido.
- Para NMF sobre `behavioral_wide v0b`, usar el contrato no negativo documentado
  en `notes.md`: `clip(p01,p99) + minmax [0,1] + block_weight`.
- No usar z-score ni variables centradas en NMF.

## Bloque Intensidad / Soporte De Uso

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- Missing: 0% para todas las variables candidatas.
- PCA del bloque: PC1 + PC2 explican 94,1% de la varianza.
- Dos representantes (`log1p_n_viajes`,
  `rhythm_active_day_density_span`) reconstruyen el bloque con R2 promedio
  0,913 y R2 minimo 0,815.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `log1p_n_viajes` | intensidad | Exposicion/intensidad total observada. | `input_behavioral` | `main` | `log1p` + z-score / block scaling | Representa PC1 volumen/soporte; correlacion con PC1 = 0,94; variable simple e interpretable. | Puede dominar clustering si se combina con otros proxies de intensidad. |
| `rhythm_active_day_density_span` | intensidad | Densidad/cotidianeidad de dias activos dentro del span observado. | `input_behavioral` | `main` | raw + z-score / block scaling | Representa PC2 densidad/cotidianeidad; correlacion con PC2 = 0,86; aporta dimension distinta a intensidad total. | Tiene techo en 1; revisar escalamiento y posible no linealidad. |
| `log1p_n_dias_activos` | intensidad | Persistencia temporal medida como dias activos. | `posthoc_only` | `sensitivity` | `log1p` | Muy redundante con `log1p_n_viajes` (Spearman 0,968); se reconstruye con R2 0,948 desde representantes. | Puede servir para describir segmentos o sensibilidad. |
| `log1p_n_semanas_activas` | intensidad | Cobertura semanal dentro del scope observado. | `posthoc_only` | `sensitivity` | `log1p` | Carga en eje de soporte observado y se reconstruye con R2 0,882; solo 8 valores unicos. | Discreta y con techo por scope de semanas. |
| `rhythm_trips_per_span_day` | intensidad | Intensidad distribuida por dia del span observado. | `input_behavioral` | `sensitivity` | raw + z-score / block scaling | Casi redundante con `rhythm_active_day_density_span` (Spearman 0,982); se reconstruye con R2 0,831. | Usar si se quiere sensibilidad de intensidad densificada. |
| `rhythm_trips_per_active_week` | intensidad | Frecuencia semanal condicional a semanas activas. | `input_behavioral` | `sensitivity` | raw + z-score / block scaling | Mezcla intensidad total y densidad; se reconstruye con R2 0,815 desde los dos representantes. | No es tan limpio conceptualmente como main; puede duplicar intensidad. |

Decision:

- Para `behavioral_wide_main`, usar:
  - `log1p_n_viajes`.
  - `rhythm_active_day_density_span`.
- Mantener el resto como sensibilidad o perfil externo.
- QR/BIP observado en cuantiles se usa solo como contexto descriptivo, no como
  criterio de seleccion.

## Bloque Horario / Franja

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- Missing: 0% para todas las variables candidatas.
- PCA del bloque: PC1 + PC2 explican 64,3%; PC1 + PC2 + PC3 explican 85,7%.
- Las cuatro shares de franja son composicionales: una queda determinada por
  las otras tres.
- Set v1 (`hora_mean`, `hora_std`, `share_lab_pm`, `share_no_lab`) reconstruye
  mal `share_lab_pt` (R2 = 0,310).
- Set v2 (`hora_mean`, `hora_std`, `share_lab_pm`, `share_lab_pt`,
  `share_no_lab`) reconstruye el bloque completo con R2 minimo = 1,000; esto
  confirma que `share_lab_valle` es redundante si las otras tres shares entran.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `hora_mean` | horario | Hora promedio de inicio de viajes. | `input_behavioral` | `main` | raw + z-score / block scaling | Representa centralidad horaria; correlacion fuerte con PC2 (abs corr = 0,823). | Promedio horario puede ser debil ante patrones bimodales o circularidad. |
| `hora_std` | horario | Variabilidad horaria de viajes. | `input_behavioral` | `main` | raw + z-score / block scaling | Aporta dispersion horaria; asociado a PC1 y no redundante con `hora_mean` (Spearman 0,022). | Puede mezclar dispersion real con bajo soporte de viajes; revisar sensibilidad por `min_trips`. |
| `share_lab_pm` | franja | Proporcion de viajes en punta laboral mañana. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa punta mañana; mejor representante de PC1 (abs corr = 0,801). | Parte de composicion de franjas; interpretar con valle como referencia implicita. |
| `share_lab_pt` | franja | Proporcion de viajes en punta laboral tarde. | `input_behavioral` | `main` | raw share + z-score / block scaling | Necesaria para no perder la dimension punta tarde; en set v1 quedaba mal reconstruida (R2 = 0,310). | Parte de composicion de franjas; no incluir junto a todas las shares sin referencia. |
| `share_no_lab` | franja | Proporcion de viajes en horario no laboral. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa uso no laboral; mejor representante de PC3 (abs corr = 0,829). | Tiene muchos ceros; conviene revisar binning robusto para descriptivos. |
| `share_lab_valle` | franja | Proporcion de viajes en valle laboral. | `posthoc_only` | `sensitivity` | raw share | Redundante por construccion si entran `share_lab_pm`, `share_lab_pt` y `share_no_lab`; queda como categoria base implicita. | Util para describir segmentos y chequear interpretacion de uso laboral regular. |

Decision:

- Para `behavioral_wide_main`, usar:
  - `hora_mean`.
  - `hora_std`.
  - `share_lab_pm`.
  - `share_lab_pt`.
  - `share_no_lab`.
- Excluir `share_lab_valle` del input principal para evitar redundancia
  composicional. Usarla como perfil externo o sensibilidad.
- QR/BIP observado en cuantiles se usa solo como contexto descriptivo, no como
  criterio de seleccion.

## Bloque Regularidad / Ritmo Temporal

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- PCA del bloque: PC1 explica 53,0%; PC1 + PC2 + PC3 explican 81,7%.
- Redundancias fuertes:
  - `rhythm_daily_entropy_norm` y `rhythm_daily_burstiness` son opuestas
    exactas.
  - `rhythm_weekly_entropy_norm` y `rhythm_weekly_burstiness` son opuestas
    exactas.
  - `activity_top1/top2` y `daily_hhi` son casi el mismo eje.
  - `weekly_top1_share` y `weekly_hhi` son casi el mismo eje.
- Set v1 (`mean_gap`, `daily_hhi`, `single_trip_day_share`, `weekly_hhi`)
  alcanza R2 promedio 0,811 y mediano 0,835.
- Set v2 agrega `weekly_entropy_norm` y mejora a R2 promedio 0,886 y mediano
  0,971; queda como main.
- Set v3a agrega `max_gap` y mejora PC3 de 0,279 a 0,515, pero se deja como
  sensibilidad por caveat de extremos/salto interanual.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `rhythm_mean_gap_active_days` | regularidad | Intermitencia promedio entre dias activos. | `input_behavioral` | `main` | `log1p` + z-score / block scaling | Mejor representante de PC2; abs corr con PC2 = 0,958. | Cola larga y missing en tarjetas con un solo dia activo; imputar de forma explicita. |
| `rhythm_daily_hhi` | regularidad | Concentracion diaria de viajes. | `input_behavioral` | `main` | raw + z-score / block scaling | Mejor representante de PC1; abs corr con PC1 = 0,944; reconstruye top shares diarios. | Condicionado por soporte de viajes; revisar sensibilidad por `min_trips`. |
| `rhythm_single_trip_day_share` | regularidad | Proporcion de dias activos con un solo viaje. | `input_behavioral` | `main` | raw share + z-score / block scaling | Captura dimension propia de dias simples; abs corr con PC5 = 0,822. | Puede mezclarse con complejidad diaria y soporte por dia activo. |
| `rhythm_weekly_hhi` | regularidad | Concentracion semanal de viajes. | `input_behavioral` | `main` | raw + z-score / block scaling | Representante parsimonioso de concentracion semanal; reconstruye bien `weekly_top1_share`. | Scope tiene pocas semanas; revisar discretizacion. |
| `rhythm_weekly_entropy_norm` | regularidad | Dispersion semanal normalizada. | `input_behavioral` | `main` | raw + z-score / block scaling | Agregarla mejora R2 promedio del bloque de 0,811 a 0,886 y R2 mediano de 0,835 a 0,971. | No incluir junto a `rhythm_weekly_burstiness`, porque son complementarias. |
| `rhythm_max_gap_active_days` | regularidad | Maxima interrupcion entre dias activos. | `input_behavioral` | `sensitivity` | `log1p` + z-score / block scaling | Captura mejor el PC3 residual que v2 (abs corr = 0,515). | Puede reflejar extremos, ventanas interanuales o salto 2024-2025; no queda como main. |
| `rhythm_median_gap_active_days` | regularidad | Mediana de gaps entre dias activos. | `posthoc_only` | `sensitivity` | `log1p` | Redundante con `rhythm_mean_gap_active_days`; v2 la reconstruye con R2 0,904. | Missing en tarjetas con un solo dia activo. |
| `rhythm_n_gap_days` | regularidad | Numero total de dias sin actividad entre dias activos. | `posthoc_only` | `diagnostic` | raw | Muy correlacionada con concentracion diaria y soporte observado; no es gap puro. | Puede capturar cantidad de dias activos mas que intermitencia. |
| `rhythm_has_gap` | regularidad | Indicador de al menos un gap entre dias activos. | `exclude` | `drop` | raw binary | Casi constante en universos con mayor soporte. | Baja utilidad para segmentacion. |
| `rhythm_activity_top1_day_share` | regularidad | Share concentrado en el dia mas activo. | `posthoc_only` | `sensitivity` | raw share | Redundante con `rhythm_daily_hhi`; v2 la reconstruye con R2 0,980. | Inflada en usuarios de pocos viajes. |
| `rhythm_activity_top2_day_share` | regularidad | Share concentrado en los dos dias mas activos. | `posthoc_only` | `sensitivity` | raw share | Redundante con `rhythm_daily_hhi`; v2 la reconstruye con R2 0,893. | Inflada en usuarios de pocos viajes. |
| `rhythm_daily_entropy_norm` | regularidad | Dispersion diaria normalizada. | `posthoc_only` | `sensitivity` | raw | Redundante con `daily_hhi` y complementaria de `daily_burstiness`; v2 la reconstruye con R2 0,758. | No incluir junto a `daily_burstiness`. |
| `rhythm_daily_burstiness` | regularidad | Burstiness diaria. | `exclude` | `drop` | raw | Complementaria exacta de `daily_entropy_norm`; menos directa que HHI/entropia. | Mantener solo si se cambia la parametrizacion del bloque. |
| `rhythm_weekly_top1_share` | regularidad | Share concentrado en la semana mas activa. | `posthoc_only` | `sensitivity` | raw share | Redundante con `rhythm_weekly_hhi`; v2 la reconstruye con R2 0,971. | Scope corto de semanas. |
| `rhythm_weekly_burstiness` | regularidad | Burstiness semanal. | `exclude` | `drop` | raw | Complementaria exacta de `rhythm_weekly_entropy_norm`. | Mantener solo si se reemplaza entropia semanal. |

Decision:

- Para `behavioral_wide_main`, usar:
  - `rhythm_mean_gap_active_days`.
  - `rhythm_daily_hhi`.
  - `rhythm_single_trip_day_share`.
  - `rhythm_weekly_hhi`.
  - `rhythm_weekly_entropy_norm`.
- Usar `rhythm_max_gap_active_days` como sensibilidad de episodicidad/extremos.
- No usar QR/BIP como criterio de seleccion.

## Bloque Modo / Transbordo / Complejidad Modal

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- Missing: 0% para variables modales/transbordo; casi 0% para
  `share_trips_in_multi_route_od`.
- Las tres shares modales (`solo_bus`, `solo_metro`, `metro_bus`) son una
  composicion cerrada: suman 1 para el 100% de tarjetas en `alta_n3`.
- Correlaciones relevantes:
  - `share_trips_solo_bus` vs `share_trips_solo_metro`: Spearman -0,850.
  - `share_trips_with_transfer` vs `n_trasbordos_mean`: Spearman 0,960.
  - `share_trips_metro_bus` vs `share_trips_with_transfer`: Spearman 0,441.
  - `share_trips_in_multi_route_od` tiene correlacion baja con transbordo
    general (0,097), por lo que no es solo otro proxy de transfer.
- PCA del bloque:
  - PC1 + PC2 explican 79,9%.
  - PC3 agrega una dimension interpretable de complejidad OD/ruta.
  - PC4 captura intermodalidad metro-bus residual.
- Set v1 (`share_trips_solo_bus`, `share_trips_with_transfer`,
  `share_trips_in_multi_route_od`) alcanza R2 promedio 0,817, pero reconstruye
  mal `share_trips_metro_bus` (R2 = 0,332).
- Set v2 agrega `share_trips_metro_bus` y mejora a R2 promedio 0,974,
  R2 mediano 1,000 y R2 minimo 0,846; queda como set principal del bloque.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `share_trips_solo_bus` | modo | Proporcion de viajes solo bus. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa eje bus vs metro; usarla junto a `share_trips_metro_bus` deja `solo_metro` como referencia implicita. | Variable modal puede reflejar oferta/acceso territorial, no solo preferencia conductual. |
| `share_trips_metro_bus` | modo/intermodalidad | Proporcion de viajes que combinan metro y bus. | `input_behavioral` | `main` | raw share + z-score / block scaling | v1 no la reconstruye bien (R2 = 0,332); agregarla en v2 reconstruye la composicion modal y captura PC4 residual. | Puede solaparse con transbordo general; requiere ponderacion por bloque para no duplicar modo. |
| `share_trips_with_transfer` | transbordo | Proporcion de viajes con al menos un transbordo. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representante interpretable de transbordo general; mejor que incluir tambien `n_trasbordos_mean`, que es casi redundante. | Puede medir complejidad de red/oferta ademas de conducta individual. |
| `share_trips_in_multi_route_od` | complejidad_od_ruta | Proporcion de viajes en OD con multiples rutas observadas/disponibles. | `input_behavioral` | `main` | raw share + z-score / block scaling | Aporta eje propio: mejor representante de PC3 (abs corr = 0,610); baja correlacion con transbordo general. | Caveat fuerte: puede capturar estructura de red/oferta y soporte observado; revisar sensibilidad estructural. |
| `share_trips_solo_metro` | modo | Proporcion de viajes solo metro. | `posthoc_only` | `sensitivity` | raw share | Redundante por composicion cerrada si entran `share_trips_solo_bus` y `share_trips_metro_bus`. | Usarla para perfilar segmentos o como alternativa de referencia modal. |
| `n_trasbordos_mean` | transbordo | Promedio de transbordos por viaje. | `posthoc_only` | `sensitivity` | raw | Muy redundante con `share_trips_with_transfer` (Spearman 0,960); v2 la reconstruye con R2 0,846. | Puede ser util si se quiere medir intensidad de transfer mas alla de presencia/ausencia. |

Decision:

- Para `behavioral_wide_main`, usar:
  - `share_trips_solo_bus`.
  - `share_trips_metro_bus`.
  - `share_trips_with_transfer`.
  - `share_trips_in_multi_route_od`.
- Mantener `share_trips_solo_metro` como referencia implicita/post-hoc.
- Mantener `n_trasbordos_mean` como sensibilidad/post-hoc.
- Caveat transversal: si se integran scores NMF o matriz `macro_franja_modo`,
  este bloque puede ser redundante y debe revisarse con ponderacion/sensibilidad.

## Bloque Espacial / OD / Zonas

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- Missing: 0% o practicamente 0% para las variables candidatas.
- PCA del bloque:
  - PC1 explica 63,1% y representa diversidad espacial vs anclaje/concentracion.
  - PC1 + PC2 explican 79,6%.
  - PC1 + PC2 + PC3 explican 87,8%.
- Redundancias fuertes:
  - `activity_zone_top1_share` y `routine_zone_top1_usage_share` son
    duplicadas exactas.
  - `activity_zone_entropy`, `routine_zone_n_unique` y
    `routine_zone_exploration_share` representan el mismo eje general de
    diversidad/exploracion zonal.
  - `routine_od_top1_share` y `routine_od_hhi` son muy redundantes
    (Spearman 0,886).
- Set v1 (`activity_zone_entropy`, `routine_od_hhi`,
  `routine_main_od_roundtrip_balance`, `origin_zone_top1_share`) alcanza
  R2 promedio 0,873 y R2 minimo 0,707.
- Set v2 agrega `routine_main_od_share` y mejora a R2 promedio 0,904,
  R2 mediano 0,931; ademas mejora cobertura de PC4 de 0,167 a 0,402.
  Queda como set principal del bloque.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `activity_zone_entropy` | espacial_zonas | Diversidad de zonas observadas como origen o destino. | `input_behavioral` | `main` | raw + z-score / block scaling | Mejor representante del eje principal diversidad espacial vs anclaje; abs corr con PC1 = 0,948. | Aumenta con soporte/intensidad; requiere ponderacion por bloque. |
| `routine_od_hhi` | espacial_od | Concentracion HHI de pares OD dirigidos. | `input_behavioral` | `main` | raw + z-score / block scaling | Representa concentracion OD dirigida; cubre eje opuesto a diversidad espacial. | Redundante con `routine_od_top1_share`; elegir solo HHI como representante. |
| `routine_main_od_share` | espacial_od | Share de viajes en el OD no dirigido principal. | `input_behavioral` | `main` | raw share + z-score / block scaling | Agregarla en v2 mejora R2 promedio 0,873->0,904 y PC4 0,167->0,402; captura anclaje OD principal. | Puede solaparse con commute-like/daily-tour; revisar sensibilidad posterior. |
| `routine_main_od_roundtrip_balance` | espacial_od | Balance ida/vuelta dentro del OD principal no dirigido. | `input_behavioral` | `main` | raw + z-score / block scaling | Representa eje propio de reciprocidad; abs corr con PC2 = 0,806. | Variable discreta/bimodal; puede pertenecer tambien a bloque daily-tour/commute. |
| `origin_zone_top1_share` | espacial_origen | Concentracion en la zona de origen mas frecuente. | `input_behavioral` | `main` | raw share + z-score / block scaling | Captura anclaje de origen y ejes residuales PC3/PC5 no cubiertos por diversidad general. | Puede reflejar residencia o zona de actividad principal; no confundir con macrozona estructural. |
| `origin_zone_entropy` | espacial_origen | Entropia de zonas de origen. | `posthoc_only` | `sensitivity` | raw | Reconstruida por v2 con R2 0,893; util para describir dispersion de origenes. | Redundante con `activity_zone_entropy` y otros proxies de diversidad. |
| `activity_zone_top1_share` | espacial_zonas | Share en la zona de actividad mas frecuente. | `posthoc_only` | `sensitivity` | raw share | Se reconstruye parcialmente con R2 0,708; menos informativa que entropia para el input principal. | Duplicada conceptualmente con top1 de zona; usar solo para perfiles si hace falta. |
| `routine_zone_top1_usage_share` | espacial_zonas | Share de eventos zonales en la zona mas usada. | `exclude` | `drop` | raw share | Duplicada exacta de `activity_zone_top1_share`. | No usar en matriz final. |
| `routine_zone_exploration_share` | espacial_zonas | Share de eventos zonales fuera de las dos zonas principales. | `posthoc_only` | `sensitivity` | raw share | Redundante con `activity_zone_entropy`; v2 la reconstruye con R2 0,928. | Tiene muchos ceros y deriva de top2. |
| `routine_zone_n_unique` | espacial_zonas | Numero de zonas unicas usadas como origen o destino. | `posthoc_only` | `sensitivity` | `log1p` si se usa | Redundante con diversidad espacial y dependiente de soporte; v2 la reconstruye con R2 0,778. | Cola larga y fuerte dependencia con intensidad/min_trips. |
| `routine_od_top1_share` | espacial_od | Share de viajes en el OD dirigido mas frecuente. | `posthoc_only` | `sensitivity` | raw share | Redundante con `routine_od_hhi`; v2 la reconstruye con R2 0,931. | Mantener para perfil interpretativo si HHI es menos comunicable. |

Decision:

- Para `behavioral_wide_main`, usar:
  - `activity_zone_entropy`.
  - `routine_od_hhi`.
  - `routine_main_od_share`.
  - `routine_main_od_roundtrip_balance`.
  - `origin_zone_top1_share`.
- Excluir `routine_zone_top1_usage_share` por duplicacion exacta.
- Mantener el resto como post-hoc/sensibilidad.
- Caveat transversal: este bloque tiene un eje PC1 muy dominante y puede pesar
  demasiado en clustering; usar escalamiento/ponderacion por bloque.

## Bloque Rutina / Repeticion De Patrones

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- Missing: 0% o practicamente 0% para las variables candidatas.
- Redundancias fuertes:
  - `routine_combo_top1_share` y `routine_od_time_top1_share` son casi la
    misma variable (Spearman 0,995).
  - `routine_combo_hhi` y `routine_od_time_hhi` son casi la misma variable
    (Spearman 0,998).
  - Agregar modo al patron OD-franja no aporta una dimension clara adicional
    dentro de estas metricas agregadas; como el modo ya tiene bloque propio, se
    prefiere el representante OD-franja.
- PCA del bloque:
  - PC1 explica 56,8% y representa concentracion de rutina OD-franja.
  - PC1 + PC2 explican 78,8%.
  - PC1 + PC2 + PC3 explican 89,7%.
- Set v1 (`routine_od_time_hhi`, `routine_lab_peak_share`,
  `routine_od_time_entropy_norm`) alcanza R2 promedio 0,840, R2 mediano 0,943
  y R2 minimo 0,371. Reconstruye bien `routine_combo_hhi` (R2 = 0,995) y
  razonablemente los top1 shares OD-franja/combo (R2 ~0,89).
- Set v2 agrega `routine_commute_like_score` y sube a R2 promedio 0,919, pero
  la mejora viene principalmente de reconstruir el propio score compuesto.
  `routine_od_time_n_unique` sigue bajo (R2 = 0,576), por lo que v2 no resuelve
  el principal residual del bloque.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `routine_od_time_hhi` | rutina_od_tiempo | Concentracion HHI de patrones OD + franja. | `input_behavioral` | `main` | raw + z-score / block scaling | Representante limpio de PC1; abs corr con PC1 = 0,949. Evita reintroducir modo, que ya tiene bloque propio. | Puede solaparse con bloque espacial/OD y horario; revisar redundancia cross-block. |
| `routine_lab_peak_share` | rutina_laboral | Proporcion de viajes en punta laboral dentro del routine pack. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa PC2; abs corr con PC2 = 0,742. Da lectura sustantiva de anclaje laboral. | Caveat fuerte: puede duplicar variables de franja horaria (`share_lab_pm`, `share_lab_pt`). |
| `routine_od_time_entropy_norm` | rutina_od_tiempo | Dispersion normalizada de patrones OD + franja. | `input_behavioral` | `main` | raw + z-score / block scaling | Captura dispersion y parte de PC3; abs corr con PC3 = 0,513. No es solo top1/HHI invertido. | Tiene techo frecuente en 1; revisar escalamiento y sensibilidad con HHI. |
| `routine_commute_like_score` | commute_like | Score compuesto de rutina tipo commute. | `posthoc_only` | `sensitivity` | raw score | v2 mejora R2 promedio, pero principalmente porque el score se reconstruye a si mismo; util para perfilar segmentos. | Indice construido manualmente y prescriptivo; no usar como input main inicial. |
| `routine_od_time_n_unique` | rutina_od_tiempo | Numero de patrones OD + franja unicos. | `posthoc_only` | `sensitivity` | `log1p` si se usa | Aporta residual no bien reconstruido (R2 = 0,576), pero depende mucho de soporte/intensidad. | Puede duplicar intensidad y diversidad espacial; no usar main sin residualizar o ponderar. |
| `routine_od_time_top1_share` | rutina_od_tiempo | Share del patron OD + franja mas frecuente. | `posthoc_only` | `sensitivity` | raw share | Redundante con `routine_od_time_hhi`; v1 lo reconstruye con R2 = 0,890. | Puede ser mas comunicable que HHI para perfiles, pero no hace falta como input main. |
| `routine_combo_top1_share` | rutina_combo_od_tiempo_modo | Share del patron OD + franja + modo mas frecuente. | `exclude` | `drop` | raw share | Casi duplicada de `routine_od_time_top1_share` (Spearman 0,995) y reintroduce modo. | Usar solo si se decide no incluir bloque modal por separado. |
| `routine_combo_hhi` | rutina_combo_od_tiempo_modo | HHI de patrones OD + franja + modo. | `exclude` | `drop` | raw | Casi duplicada de `routine_od_time_hhi` (Spearman 0,998) y se reconstruye con R2 = 0,995 desde v1. | Usar solo si se decide no incluir bloque modal por separado. |

Decision:

- Para `behavioral_wide_main` provisional, usar:
  - `routine_od_time_hhi`.
  - `routine_lab_peak_share`.
  - `routine_od_time_entropy_norm`.
- Mantener `routine_commute_like_score` como sensibilidad/post-hoc.
- Mantener `routine_od_time_n_unique` como sensibilidad diagnostica si se
  quiere explorar residual de diversidad efectiva, idealmente con `log1p` y
  control por intensidad.
- Excluir `routine_combo_*` del input principal mientras el bloque modal entre
  por separado.
- Caveat transversal: antes de construir `behavioral_wide`, revisar redundancia
  cross-block con horario, modo y espacial/OD; este bloque podria pasar a
  sensibilidad si duplica demasiado esos ejes.

## Bloque Daily Tour / Estructura Diaria

Estado: decision provisional cerrada para primera version de `behavioral_wide`.

Evidencia usada:

- Universo principal auditado: `interannual_ml clean alta n3`.
- Universos de estabilidad revisados: `alta_n3`, `alta_n5`, `alta_n10`,
  `alta_n3_home3`.
- El catalogo audita el artefacto completo
  `user_behavior_daily_tour_features_interannual_ml.parquet`, no solo las
  variables `tour_*` actualmente expuestas en `user_model_matrix_*`.
- Missing: 0% para las variables candidatas.
- PCA del bloque:
  - PC1 explica 33,7% y representa complejidad/diversidad diaria vs dia simple
    o pendular.
  - PC1 + PC2 explican 58,1%.
  - PC1 + PC2 + PC3 + PC4 + PC5 explican 85,5%.
- Redundancias fuertes:
  - `tour_three_plus_trip_day_share` y `tour_complex_day_share` son casi la
    misma variable (Spearman 0,987).
  - `tour_reciprocal_od_day_share` y `tour_same_unordered_od_day_share` son
    casi duplicadas (Spearman 0,988).
  - `tour_mode_consistent_day_share` y `tour_mixed_mode_day_share` son
    complementarias exactas (Spearman -1,000).
  - `tour_mixed_mode_day_share` y `tour_distinct_modes_per_day_mean` son casi
    equivalentes (Spearman 0,996).
  - `tour_day_span_hours_mean` y `tour_day_span_hours_median` son redundantes
    (Spearman 0,921).
- Set v1 (`tour_three_plus_trip_day_share`, `tour_reciprocal_od_day_share`,
  `tour_closed_loop_day_share`, `tour_mixed_mode_day_share`,
  `tour_day_span_hours_mean`) alcanza R2 promedio 0,730, R2 mediano 0,847 y R2
  minimo 0,264. Cubre bien estructura diaria, pero reconstruye mal anclaje
  horario de primer/ultimo viaje.
- Set v2 agrega `tour_first_trip_lab_am_peak_share` y
  `tour_last_trip_lab_pm_peak_share`; sube a R2 promedio 0,864, R2 mediano
  0,903 y R2 minimo 0,562. La mejora confirma que el anclaje horario diario es
  una subdimension real y no queda capturado solo por el span.

| variable | family | concept | role | tier | transform | decision_reason | caveat |
|---|---|---|---|---|---|---|---|
| `tour_three_plus_trip_day_share` | daily_tour_complejidad | Share de dias activos con tres o mas viajes. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representante limpio de complejidad diaria; mejor representante de PC1 en v2 (abs corr = 0,807). | Puede solaparse con intensidad por dia activo; revisar contra `rhythm_single_trip_day_share`. |
| `tour_reciprocal_od_day_share` | daily_tour_pendularidad | Share de dias donde primer y ultimo viaje forman OD reciproco. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa pendularidad/ida-vuelta diaria; cubre el lado simple/pendular opuesto a complejidad en PC1. | Puede solaparse con `routine_main_od_roundtrip_balance`. |
| `tour_closed_loop_day_share` | daily_tour_cierre | Share de dias donde el ultimo destino coincide con el primer origen. | `input_behavioral` | `main` | raw share + z-score / block scaling | Captura cierre geometrico del dia; mejor representante de PC3 (abs corr = 0,634) y no es duplicado perfecto de reciprocidad. | Puede solaparse con commute-like y reciprocidad OD. |
| `tour_mixed_mode_day_share` | daily_tour_modo | Share de dias con mas de un modo grueso observado. | `input_behavioral` | `main` | raw share + z-score / block scaling | Representa mezcla modal diaria; cubre PC4 (abs corr = 0,521) y reconstruye `distinct_modes_per_day_mean` con R2 = 0,903. | Caveat fuerte: duplica bloque modal/transbordo; revisar en cross-block. |
| `tour_day_span_hours_mean` | daily_tour_horario | Promedio del span entre primer y ultimo viaje diario. | `input_behavioral` | `main` | raw + z-score / block scaling | Mejor representante de PC2; abs corr con PC2 = 0,923. | Puede duplicar bloque horario y first/last hour. |
| `tour_first_trip_lab_am_peak_share` | daily_tour_anclaje_horario | Share de dias cuyo primer viaje ocurre en punta AM laboral. | `input_behavioral` | `main` | raw share + z-score / block scaling | v2 mejora sustantivamente la reconstruccion de anclaje horario; representa primer viaje laboral y PC3 residual (abs corr = 0,578). | Caveat fuerte: puede duplicar `share_lab_pm`/bloque horario; revisar cross-block. |
| `tour_last_trip_lab_pm_peak_share` | daily_tour_anclaje_horario | Share de dias cuyo ultimo viaje ocurre en punta PM laboral. | `input_behavioral` | `main` | raw share + z-score / block scaling | v2 mejora PC5 (abs corr = 0,550) y reconstruye anclaje de cierre diario. | Caveat fuerte: puede duplicar `share_lab_pt`/bloque horario; revisar cross-block. |
| `tour_workday_commute_like_day_share` | daily_tour_commute_like | Share de dias cerrados con primer viaje AM peak y ultimo PM peak. | `posthoc_only` | `sensitivity` | raw share | Parcialmente reconstruida por v2 (R2 = 0,635); util para perfilar commute-like diario. | Variable compuesta/prescriptiva; no usar como input main inicial. |
| `tour_complex_day_share` | daily_tour_complejidad | Share de dias con tres+ viajes y tres+ zonas. | `posthoc_only` | `sensitivity` | raw share | Redundante con `tour_three_plus_trip_day_share` (Spearman 0,987; R2 = 0,977 en v2). | Mezcla complejidad diaria con diversidad espacial. |
| `tour_same_unordered_od_day_share` | daily_tour_pendularidad | Share de dias con un unico OD no dirigido. | `posthoc_only` | `sensitivity` | raw share | Redundante con `tour_reciprocal_od_day_share` (Spearman 0,988; R2 = 0,978 en v2). | Puede ser mas comunicable, pero no hace falta como input main. |
| `tour_mode_consistent_day_share` | daily_tour_modo | Share de dias con un solo modo grueso observado. | `exclude` | `drop` | raw share | Complementaria exacta de `tour_mixed_mode_day_share`. | Usar solo si se reemplaza `mixed_mode` por su opuesto. |
| `tour_distinct_modes_per_day_mean` | daily_tour_modo | Promedio de modos gruesos distintos por dia activo. | `posthoc_only` | `sensitivity` | raw | Casi equivalente a `tour_mixed_mode_day_share` (Spearman 0,996; R2 = 0,903 en v2). | Duplica bloque modal. |
| `tour_day_span_hours_median` | daily_tour_horario | Mediana del span diario. | `posthoc_only` | `sensitivity` | raw | Redundante con `tour_day_span_hours_mean` (Spearman 0,921; R2 = 0,894 en v2). | Usar si se prefiere robustez a outliers. |
| `tour_peak_anchor_day_share` | daily_tour_anclaje_horario | Share de dias con primer viaje AM peak o ultimo viaje PM peak. | `posthoc_only` | `sensitivity` | raw share | Reconstruida razonablemente por v2 (R2 = 0,855); compuesta de first/last peak. | Menos granular que mantener first y last por separado. |
| `tour_first_trip_hour_mean` | daily_tour_horario | Hora promedio del primer viaje diario. | `posthoc_only` | `sensitivity` | raw | v2 la reconstruye parcialmente (R2 = 0,659); first peak es mas interpretable para main. | Variable horaria continua puede duplicar bloque horario. |
| `tour_last_trip_hour_mean` | daily_tour_horario | Hora promedio del ultimo viaje diario. | `posthoc_only` | `sensitivity` | raw | v2 la reconstruye parcialmente (R2 = 0,640); last peak es mas interpretable para main. | Variable horaria continua puede duplicar bloque horario. |
| `tour_distinct_zones_per_day_mean` | daily_tour_diversidad | Promedio de zonas distintas por dia activo. | `posthoc_only` | `sensitivity` | raw | Residual moderado (R2 = 0,665) pero duplica espacial/zonas. | Puede depender de soporte diario y diversidad espacial general. |
| `tour_distinct_zones_per_day_median` | daily_tour_diversidad | Mediana de zonas distintas por dia activo. | `posthoc_only` | `sensitivity` | raw | Peor reconstruida en v2 (R2 = 0,562), pero altamente relacionada con diversidad zonal. | No usar main sin revisar contra bloque espacial. |
| `tour_distinct_od_per_day_mean` | daily_tour_diversidad | Promedio de OD dirigidos distintos por dia activo. | `posthoc_only` | `sensitivity` | raw | Reconstruida razonablemente por v2 (R2 = 0,800), pero duplica complejidad y OD. | Puede solaparse con bloque espacial/OD. |
| `tour_distinct_unordered_od_per_day_mean` | daily_tour_diversidad | Promedio de OD no dirigidos distintos por dia activo. | `posthoc_only` | `sensitivity` | raw | Reconstruida por v2 con R2 = 0,852; describe diversidad diaria sin direccion. | Puede solaparse con bloque espacial/OD y complejidad diaria. |
| `tour_two_trip_day_share` | daily_tour_complejidad | Share de dias activos con exactamente dos viajes. | `posthoc_only` | `sensitivity` | raw share | Parcialmente reconstruida por v2 (R2 = 0,733) y opuesta a complejidad diaria. | Usar para perfiles de simpleza diaria; no junto a todo el set de complejidad. |

Decision:

- Para `behavioral_wide_main` provisional, usar el set v2:
  - `tour_three_plus_trip_day_share`.
  - `tour_reciprocal_od_day_share`.
  - `tour_closed_loop_day_share`.
  - `tour_mixed_mode_day_share`.
  - `tour_day_span_hours_mean`.
  - `tour_first_trip_lab_am_peak_share`.
  - `tour_last_trip_lab_pm_peak_share`.
- Mantener `tour_workday_commute_like_day_share` como sensibilidad/post-hoc.
- Mantener variables `tour_distinct_*_per_day_*` como sensibilidad descriptiva,
  no como main inicial, por redundancia con espacial/OD/modo.
- Caveat transversal: este bloque es especialmente propenso a duplicar horario,
  modo y espacial/OD. Antes de construir `behavioral_wide`, revisar
  correlaciones cross-block y posiblemente bajar `tour_mixed_mode_day_share` o
  `tour_first/last_trip_lab_*` a sensibilidad si esos ejes ya estan cubiertos.
