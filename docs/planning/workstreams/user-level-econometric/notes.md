# Notas — Frente Econométrico A Nivel Tarjeta

Bitácora del workstream MNL de adopción QR. Para el EDA, panel, matriz
supervisada y diagnóstico de techo predictivo, ver
`docs/planning/workstreams/user-level-redesign/notes.md` (frente previo).

## 2026-06-02 — Estructura del MNL de adopción

Decisión sobre el tipo de modelo, tras aclarar la diferencia conceptual con
los MNL/Nested a nivel viaje:

- A nivel VIAJE el modelo era elección discreta con ATRIBUTOS DE ALTERNATIVA
  (tiempo, costo por modo); ahí el coeficiente genérico es natural y central.
- A nivel TARJETA el modelo es de SOLO características del decisor (no hay
  atributos de alternativa: no existe un "precio de QR" que varíe por tarjeta).
  Esto es una regresión logística multinomial (McFadden). Equivale a
  `statsmodels.MNLogit` / `sklearn multinomial`, pero se estima en Biogeme/Larch.
- Implicancia clave de IDENTIFICACIÓN: con características del decisor, un
  coeficiente genérico (mismo beta sobre la misma covariable en dos alternativas)
  se cancela en las probabilidades relativas. Por eso TODOS los coeficientes son
  específicos de alternativa. La "restricción de genericidad" que sí se puede
  testear es la igualdad de un coeficiente ENTRE las dos alternativas QR.

Estructura:

- Alternativas: BIP (referencia, V=0), QR_OTHER, QR_RED.
- `V_QR_x = ASC_x + beta_x · x_i`; softmax. BIP referencia porque es la
  tecnología preexistente/mayoritaria (83%) y la pregunta es "qué aleja de BIP".
- Coeficientes: empezar TODO específico; simplificar data-driven con LR test
  los de uso indistinguibles entre QR_OTHER/QR_RED.
- Estructura principal MNL plano; nested (QR juntos vs BIP) solo sensibilidad
  IIA (sin atributos de alternativa, lambda≈1 esperado).
- Binario QR vs BIP como síntesis paralela.
- Herramientas: Biogeme principal + Larch validación.

Pregunta de tesis del frente: "¿Qué características de uso del transporte y del
territorio de residencia se ASOCIAN con adoptar QR, y se distingue QR_RED de
QR_OTHER?". Es asociación/perfilamiento, NO causalidad. El techo (~0,68 AUC)
obliga a reportar efectos modestos; QR_RED es el único con perfil nítido.

## 2026-06-02 — Set de variables del main, transformaciones desde distribuciones

Se perfiló cada variable con `scripts/user_level/profile_mnl_features.py`
(solo descriptiva, sin proponer; decisión mirando los datos). Universo main
`interannual_ml_clean + home_alta + n_viajes>=3` (2.460.264 tarjetas).

Transformaciones decididas (con el dato a la vista):

- `n_viajes`: skew 1,99, mediana 10, p99 84, max 544 -> log1p + z.
- `share_trips_2025`: BIMODAL (36,5% en 0, 35,0% en 1, ~28% en medio) ->
  3 dummies de cohorte (ref `solo_2024`): solo_2024 / mixta / solo_2025.
  Continua en sensibilidad. (Tratar lineal sería engañoso: casi nadie en el
  medio; "mixta" es un grupo distinto, no un punto intermedio.)
- 6 shares de uso (`share_lab_pm` 41% en 0, `share_lab_pt` 48%, `share_no_lab`
  52%, `share_trips_with_transfer` 22%, `share_trips_solo_metro` 23%/26% bimodal,
  `share_trips_metro_bus` 56%): todas a z. `has_*` como sensibilidad para las de
  cero dominante. `share_lab_pm` y `pt` separadas (mañana vs tarde).
- `hora_mean`: campana limpia (skew 0,33, centrada en 13h) -> z. Bins por
  franjas de transporte como sensibilidad fija (la DISTRIBUCIÓN no obliga a
  bins, pero la RELACIÓN con QR puede ser no-monótona; y hora_mean promedia
  perfiles opuestos: commuter 8h+18h da 13 igual que perfil mediodía).
- `hora_std`: limpia (skew -0,14), solo 0,24% en 0, sin NaN en n>=3 -> z.
- `t_vehiculo_mean_min` (skew 1,33), `t_espera_ini_mean_min` (skew 1,0,
  cap en 60): winsor p99 (en fold) + z.
- Socio: `educacion`, `de_proxy` ya en z -> z. Franjas etarias
  `res_age_share_25_44` (media 0,34) y `_18_24` (media 0,098) vienen CRUDAS ->
  estandarizar a z. `inmigrantes` (skew 1,7, cola a 4,8 z) y `parv` (max 7,2 z):
  winsor p1-p99 (en fold) + z.
- Discapacidad fuera del main (r=-0,73 con educación, colinealidad daña
  interpretación); educación se queda, es la más interpretable.
- educación y de_proxy ambas en main pese a r=-0,64 (conceptos distintos,
  manejable, interpretar en conjunto).

Preprocesamiento: las transformaciones (winsor, z, log1p, dummies cohorte,
dummies macro) se aplican sobre el universo completo, en `lib/user_level/
mnl_prep.py`. El modelo es DESCRIPTIVO (sin holdout), así que no hay folds ni
leakage que evitar; estandarizar sobre todo el universo es correcto.

NOTA (corrección 2026-06-02, posterior): se descartó el patrón de transformador
fiteable estilo sklearn (fit/transform en-fold) que se había propuesto. Era
sobre-ingeniería importada del frente predictivo (techo XGBoost, donde sí hay
CV). El frente econométrico sigue el patrón del notebook 16
(`03_models/16_eod2012_income_proxy_stepwise.qmd`): listas de SPECS
`(label, [columnas])` + funciones de preparación en lib, columnas ya
transformadas. Ver task_plan.md sección Arquitectura.

## 2026-06-02 — Hallazgo y fix: CENTRO faltaba en las dummies de macrozona

Al elegir la macrozona de referencia se detectó que ~12% de tarjetas tenían
las 6 dummies de macrozona en 0 ("sin macrozona"), contra el ~0,3% de missing
que reportaba el EDA del frente previo (Bloque 5). Cadena de diagnóstico
(scripts en `scripts/user_level/`):

1. `profile_mnl_features.py`: detectó 11,6% home / 13,5% origin sin dummy.
2. `diagnose_macrozone_coverage.py`: zona NO null y socio presente (97%) ->
   no es missing de dato; son zonas reales sin macrozona asignada. De ese 12%,
   solo 0,3% tiene dummies todas-null (missing real).
3. `identify_zones_without_macro.py`: 53 zonas comunes home/origin (gap
   sistemático), rango 262-309, QR +3pp vs resto (excluir sesgaría).
4. `map_nomacro_zones_to_comuna.py`: 48 zonas = comuna SANTIAGO, NMACROZONA=4;
   6 zonas (848-853) ausentes del shapefile.
5. `verify_centro_macrozona.py`: el string MACROZONA de esas 48 es exactamente
   "CENTRO". El shapefile tiene 7 macrozonas (1=NORTE..4=CENTRO..7=EXTERNA).

Causa raíz (CONFIRMADA en código, no inferida): el builder
`scripts/audits/build_user_level_payment_panel.py` listaba en
`MACROZONA_DUMMY_LEVELS` solo 6 niveles, OMITIENDO CENTRO (NMACROZONA=4). Las
dummies se prenden con `macrozone_model.eq(level)` para esos 6, así que las 48
zonas de Santiago centro (string "CENTRO") quedaban con las 6 dummies en 0.
CENTRO es justo la macrozona con QR_OTHER alto (16,9%, Bloque 5), consistente
con el +3pp observado.

Fix aplicado (2026-06-02):
- `build_user_level_payment_panel.py`: CENTRO agregado a `MACROZONA_DUMMY_LEVELS`
  y `macro_centro` a `MACROZONA_COLS`. El string "CENTRO" matchea directo
  (no necesita `.loc` como EXTERNA_ESPECIAL, cuyo string difiere).
- `build_user_model_matrix.py`: `home_macro_centro` y `origin_top1_macro_centro`
  agregados a `HOME_MACRO_FEATURES` / `ORIGIN_MACRO_FEATURES`.
- `profile_mnl_features.py`: `centro` agregado a `MACRO_LEVELS`.

Regeneración (Mac + KINGSTON + larch-env, 2026-06-02):
- Panel `interannual_ml` clean + with_conflicts (--force).
- 5 matrices: alta_n3, alta_n3_home3, alta_n5, alta_n10, alta_media_n3.
  Pasaron de 136 a 138 columnas (las 2 dummies de CENTRO). N por matriz sin
  cambio (alta_n3: 2.460.264).
- Verificado: tras el fix, `centro` aparece como macrozona poblada y el
  "sin_macrozona" cae al ~0,3% real (zonas 848-853 + sin registro).

## 2026-06-02 — Geografía: referencia PONIENTE

7 niveles de macrozona (con CENTRO). REFERENCIA = PONIENTE, por:
- Mayor volumen: 27,7% home, 26,5% origin (intercepto bien estimado, contrastes
  con poder).
- Popular y QR bajo (13,9%, Bloque 5): base "fondo" natural.
- NO es categoría de interés: ORIENTE (QR_RED) y CENTRO (QR_OTHER) son los
  contrastes sustantivos de la tesis; deben leerse contra PONIENTE.
Dummies activas: norte, oriente, centro, sur, suroriente, externa_especial.

Pendiente menor: ~0,3% sin macrozona real (zonas 848-853 ausentes del shapefile
2014 + sin registro). Tratamiento a decidir en mnl_prep (excluir o dummy
residual; son poquísimas tarjetas).

## Estado al cierre de la sesión 2026-06-02

- Set de variables del MNL main: CERRADO, verificado, materializado.
- Matrices regeneradas con CENTRO.
- Siguiente: implementar `lib/user_level/mnl_prep.py` + test.
- Scripts de diagnóstico de macrozona quedan en `scripts/user_level/` como
  registro reproducible del hallazgo CENTRO.

## 2026-06-03 — mnl_prep + runner Biogeme implementados; MNL main estimado

Implementado el frente con el patrón del notebook 16 (funciones + idco, no
clase fiteable):

- `lib/user_level/mnl_prep.py` + `test_mnl_prep.py` (7 tests sintéticos +
  integración con matriz real, todos OK). `prepare_mnl_dataset()` carga la
  matriz, codifica `choice` (1=BIP/2=QR_RED/3=QR_OTHER), aplica las
  transformaciones que el builder dejó crudas: log1p(n_viajes)+z, dummies de
  cohorte (ref solo_2024), shares/hora a z, tiempos winsor p99+z, socio (educ y
  D+E ya z re-estandarizadas al main; franjas etarias crudas->z; inmigrantes y
  parv winsor p1-p99+z), dummies macro ref PONIENTE. Devuelve idco listo.
  - Exclusiones: 9.096 tarjetas sin macrozona (0,37%) + 866 con NaN en features
    (listwise deletion, 0,04%). Universo final main: 2.450.302 tarjetas.
  - Bug corregido: PROJECT_ROOT usaba parents[1] (=lib/) en vez de parents[2]
    (raíz). El test de integración real lo atrapó.
- `scripts/user_level/fit_mnl_biogeme.py`: MNL 3 alternativas, BIP referencia
  (V=0), coeficientes específicos por alternativa, models.loglogit. Flags
  --sample-frac (estratificado por tipo_tarjeta), --binary. Logging Biogeme +
  timestamps.

MNL MAIN estimado (full-específico, modelo principal):
- 64 parámetros, 31 features. Universo estimado: submuestra 30% (735.091
  tarjetas) por restricción de RAM en el full 2,46M (Hessiana exacta + 2,46M
  filas agota memoria). DECISIÓN: el 30% es el reportable.
- Submuestra ESTRATIFICADA por tipo_tarjeta: proporciones idénticas al full
  hasta 4 decimales (BIP 0,8467 / QR_OTHER 0,1317 / QR_RED 0,0216 en ambos).
  ASCs válidos sin corrección (no hay oversampling). Verificado con dato.
- Converge limpio (6 iter, rel.gradient 2e-6). rho² 0,575 (init) idéntico entre
  submuestras 2% y 30% -> coeficientes estables.
- Outputs: `03_models/user_level/mnl/outputs/params_mnl_user_*_s300.csv`.

VALIDACIÓN de signos (sanity check):
- Contra el EDA: educación -> QR_RED +0,76 (t=7,4); QR_OTHER +0,06 (ns).
  Reproduce Bloque 6A (+0,75z vs +0,03z). Cohorte (mixta/solo_2025) fuerte en
  ambos. D+E -> QR_RED -0,11 (sig). Todo coherente.
- Contra el modelo VIAJE (notebook 17, mnl_residence_home_alta_parsimonious):
  la HISTORIA CENTRAL coincide (educación->QR_RED + fuerte; QR_OTHER socio ~0;
  ASCs casi idénticos). NO son comparables numéricamente (unidad viaje vs
  tarjeta, estandarización distinta, base CENTRO vs PONIENTE).
  - Dos discrepancias de signo, AMBAS interpretables y NO contradicciones:
    macro_oriente QR_RED (+0,12 viaje vs -0,97 tarjeta) y D+E. Causa: en el
    modelo tarjeta educación pesa más (+0,76 vs +0,40) y ABSORBE la señal
    socioeconómica compartida con Oriente (r=0,62), dejando el residuo
    geográfico negativo. Coherente con que el driver es educación, no ubicación.
    Documentar esto al reportar para que no se lea como contradicción.

DECISIONES:
- Full-específico es el modelo principal (válido, sin sobreajuste con N=735k,
  ~11.500 obs/parámetro). Se DESCARTA el LR test genérico-entre-QR como paso
  obligatorio: con N grande rechazaría casi cualquier restricción aunque sea
  trivial. Si se quiere la afirmación "uso es genérico entre QR", hacerlo por
  comparación cualitativa de magnitudes, no por test formal.
- Biogeme NO se usa como herramienta predictiva: la predicción/techo ya la da
  el XGBoost (AUC 0,68). División mantenida: logit interpreta, XGBoost predice.

Siguiente: nested (sensibilidad IIA, lambda≈1 esperado), binario QR vs BIP
(--binary), sensibilidades de universo (home>=3, n>=10, alta_media).

## 2026-06-03 — Sensibilidad IIA (nested) CERRADA: MU_QR=1, MNL plano adecuado

Nested logit con nido (QR_RED, QR_OTHER) vs BIP. Implementado en
`fit_mnl_biogeme.py --nested` (models.lognested, MU_QR Beta acotado [1,100]).

Problema técnico: el nested NO converge en submuestras grandes (30%: 1000 iter
sin converger, luego killed por RAM en el cálculo de BHHH/2das derivadas). El
MU_QR con bound hace la superficie de verosimilitud más difícil. Solución:
correr en submuestra 10% (245.030 tarjetas), donde converge (885 iter, ~9 min).

Resultado CONCLUYENTE:
- **MU_QR = 1,0 exacto, en la cota inferior ("Active bound: True")**. t-stat
  0,22, p 0,82 (no distinguible de 1).
- MU_QR=1 => el nested colapsa al MNL plano. El optimizador empujó MU_QR hacia
  <1 (que violaría la teoría del nested logit, requiere MU>=1), señal de que NO
  hay estructura de nido: si acaso, los datos sugieren lo contrario a anidar.
- LR test innecesario: con MU_QR en la cota, nested = plano en el óptimo
  (LL nested 10% = -114.564,4 sería ~idéntico al plano 10%). LR ≈ 0 < 3,84.

CONCLUSIÓN: el MNL plano es la especificación adecuada. IIA razonable. No hay
correlación no observada entre QR_RED y QR_OTHER más allá de las covariables.
Coherente con el EDA (los dos QR son muy distintos: socio-geográfico vs
conductual; no comparten un componente latente "pago digital" fuerte).

Outputs: `params/stats_mnl_user_..._s100_nested.csv`.

Siguiente: binario QR vs BIP, sensibilidades de universo.

## 2026-06-03 — Binario QR vs BIP: confirma que el binario DILUYE la heterogeneidad

Logit binario (BIP vs QR=red+other), submuestra 30% (735.091), 32 parámetros,
converge en 80s. rho² 0,407 (vs 0,575 del multiclase de 3 alternativas).

Hallazgo clave (justifica por qué el multiclase es el modelo principal):
- Educación: binario +0,169 vs multiclase QR_RED +0,76 / QR_OTHER +0,06 (ns).
  El binario PROMEDIA dos perfiles opuestos ponderado por volumen (QR_OTHER es
  ~86% del QR), aguando el +0,76 de QR_RED hasta +0,17. Reportar solo el binario
  diría "educación se asocia débilmente a QR"; el multiclase revela que educación
  NO predice QR en general, predice fuertemente QR_RED y nada de QR_OTHER. Es un
  hallazgo cualitativamente distinto.
- Cohorte robusta en ambos (mixta +0,89, solo_2025 +0,62): driver principal de
  QR en general.
- D+E: binario +0,017 (sig por N grande, pero trivial). Ejemplo del caveat de N:
  significancia sin relevancia práctica.

Rol del binario: SÍNTESIS simple útil, pero esconde la heterogeneidad ->
refuerza que el multinomial es el modelo principal de tesis.
Outputs: `params/stats_mnl_user_..._s300_binary.csv`.

Tres modelos del frente listos: MNL main (principal, full-específico, 30%),
nested (IIA -> plano adecuado), binario (síntesis, muestra la dilución).
Siguiente: sensibilidades de universo (home>=3, n>=10, alta_media); validación
Larch; reporte.

## 2026-06-03 — Sensibilidades de universo: hallazgo ROBUSTO a la definición

Re-estimado el MNL main de 3 alternativas en 3 universos alternativos
(submuestra 20% home3/n10, 10% alta_media por RAM):

| universo | N submuestra | rho² init |
|---|---|---|
| alta_n3 (main) | 735.091 (30%) | 0,575 |
| alta_n3_home3 | 297.858 (20%) | 0,594 |
| alta_n10 | 256.520 (20%) | 0,605 |
| alta_media_n3 | 336.807 (10%) | 0,576 |

Coeficiente de EDUCACIÓN (el hallazgo central) por alternativa:

| universo | QR_RED | QR_OTHER |
|---|---|---|
| alta_n3 | 0,739 | 0,072 |
| home>=3 | 0,758 | 0,087 |
| n>=10 | 0,792 | 0,135 |
| alta_media | 0,706 | 0,103 |

Cohorte solo_2025 (QR_RED / QR_OTHER): 0,67/0,63 ; 0,74/0,69 ; 0,72/0,70 ;
0,69/0,65 respectivamente.

Lectura: el hallazgo central es COMPLETAMENTE robusto a la definición de
universo. Educación->QR_RED se mantiene fuerte (0,71-0,79) y educación->QR_OTHER
~0 (0,07-0,14) en los 4 universos. La heterogeneidad QR_RED (socio) vs QR_OTHER
(difuso) es estructural, no depende del umbral de uso (n>=3/10), soporte
residencial (home>=3) ni confianza residencial (alta vs alta+media). Cohorte
robusta también. En n>=10 (intensivos) educación sube levemente para ambos
(perfiles más nítidos) pero el contraste RED»OTHER se mantiene.

Outputs: `params/stats_mnl_user_..._{home3_s200,n10_s200,alta_media_n3_s100}.csv`.

Nota RAM: las sensibilidades requirieron bajar sample-frac (20-10%) porque el
Biogeme con Hessiana exacta + universos grandes agota memoria. Coeficientes
estables igual (la educación apenas varía entre 10% y 30%).

Pendiente (hitos 8-9): validación Larch (replicar coefs del main), reporte/
interpretación. Frente sustantivo COMPLETO.

## 2026-06-03 — Validación cruzada Larch vs Biogeme: COINCIDEN

`scripts/user_level/fit_mnl_larch.py` replica el MNL main en Larch
(lx.Dataset.construct.from_idco, utility_co, BIP referencia V=0). Reusa mnl_prep.

Problema inicial: primera comparación dio diferencias hasta 0,17 — NO era error
de especificación, sino que Biogeme y Larch usaban submuestras 30% DISTINTAS
(rng.choice con orden de group_by no determinístico). Las mayores diferencias
estaban en macrozonas raras (EXTERNA_ESPECIAL, 0,4% del universo), sensibles a
qué tarjetas entran.

Solución: `mnl_prep.stratified_subsample()` ahora es DETERMINÍSTICA por
id_tarjeta (hash(id+seed) % 1e6 < frac*1e6), no rng.choice. Ambos runners
(Biogeme y Larch) usan la misma función -> tarjetas IDÉNTICAS. Mejora la
reproducibilidad de todo el frente.

Resultado con datos idénticos (10%, 244.823 tarjetas):
- Máxima diferencia absoluta: 0,0057 (solo en EXTERNA_ESPECIAL, pocos datos).
- Coeficientes principales coinciden al ~4to-6to decimal:
  educación QR_RED bio 0,644090 vs larch 0,643969 (dif 0,00012);
  ASC_QR_RED −4,3237 vs −4,3239; Oriente/Centro/Norte <0,001.
- LogLik Larch −114.260,1 (Biogeme converge al mismo óptimo).
- Criterio automático: max diff < 0,01 -> VALIDACIÓN OK.

Conclusión: Larch y Biogeme estiman EXACTAMENTE el mismo modelo. La
especificación está bien implementada, sin errores de código. La diferencia
residual de 0,005 es ruido del optimizador (Newton vs BHHH).

Outputs: `params_larch_*.csv`, `compare_biogeme_larch_*.csv`.

Pendiente: hito 9 (reporte/interpretación). Frente econométrico COMPLETO en
modelos y validación.

## 2026-06-03 — Sensibilidad Oriente/educación: confirma el efecto CONDICIONAL

Pregunta interpretativa: ¿por qué B_QR_RED_HOME_MACRO_ORIENTE es NEGATIVO
(-0,63), si el EDA mostró que Oriente tiene QR_RED alto? Hipótesis: efecto
condicional — educación (r=0,62 con Oriente) absorbe la señal geográfica.

Verificación empírica: flag `--drop-educ` en fit_mnl_biogeme (excluye la
variable de educación, cine18). Modelo con vs sin educación, misma submuestra
10% (244.823 tarjetas, determinística):

| coef (QR_RED, home) | CON educación | SIN educación |
|---|---|---|
| MACRO_ORIENTE | -0,628 (t -5,7) | **+0,451 (t +5,2)** |
| RES_EOD2012 (D+E) | -0,045 (t -2,0) | -0,187 (t -9,3) |

El signo de Oriente SE INVIERTE: sin educación vuelve a ser positivo y
significativo, recuperando la asociación bruta del EDA. CONFIRMA con dato que
la asociación Oriente->QR_RED opera ÍNTEGRAMENTE a través de la educación:
controlando por educación, residir en Oriente NO aumenta QR_RED. El determinante
es el capital educativo de la zona, no la ubicación geográfica. D+E también se
vuelve más negativo sin educación (carga la señal socioeconómica compartida).

Coherente con todo el frente: la geografía no aporta señal propia más allá de
lo socioeconómico (techo XGBoost/GPBoost ya lo mostró; aquí el logit lo
desenreda: "Oriente" era proxy de "educación").

Para la tesis: insumo clave para interpretar el coeficiente de Oriente sin que
parezca contradecir el EDA. Outputs: `params_..._s100_noeduc.csv`.

## 2026-06-07 — Indicadores de inercia (DSI/TSI/LSI de Lizana) en el MNL

Se incorporaron al MNL los indicadores de regularidad/inercia de hábito de
Lizana et al. 2023 (ver [[lizana_weekday_filter]]). Son índices de SIMILITUD
intra-persona ENTRE dos ventanas (base vs eval), valor en [0,1] (1 = patrón
idéntico). Se generan con `scripts/audits/segmentation_window_sensitivity.py`
(rama feature/user-segmentation-clustering) y se calculan SOLO sobre días
hábiles (10 días, filtro de Lizana).

### Qué mide cada índice
- `dsi_day_sequence` (DSI): regularidad de QUÉ DÍAS viaja.
  `1 − Σ|activo_base−activo_eval|/N_días`.
- `tsi_time_distribution` (TSI): regularidad de A QUÉ HORA viaja (franjas).
  `1 − ½·Σ|share_base−share_eval|` (complemento distancia L1).
- `lsi_origin_zone` (LSI-zona): regularidad de DESDE QUÉ ZONA sale (mismo TSI).
- `lsi_origin_stop` (LSI-paradero): ídem pero PARADERO exacto (más granular).

### Las 3 ventanas y qué representan
- `inter_W15_W17` (INTER): abril 2024 vs abril 2025. PERSISTENCIA inter-anual
  del patrón. Parquet `indicators_W15_W17_clean_nonconsecutive.parquet`.
- `intra2024_W15_W17` (INTRA2024): W15 vs W17 DENTRO de abril 2024. Regularidad
  intra-periodo. Generado 2026-06-07.
- `intra2025_W15_W17` (INTRA2025): W15 vs W17 dentro de abril 2025. Ídem 2025.

Cada índice existe SOLO para tarjetas activas en ambas ventanas (≥3 viajes,
≥2 días activos por lado). Incorporarlos NO imputa: hace INNER join y SUBSETEA
el universo a las elegibles. El z se calcula DESPUÉS del subset (sobre el
universo elegible/común final). En modelo conjunto el universo es la
INTERSECCIÓN de las ventanas.

### Decisiones metodológicas cerradas
- SET PARSIMONIOSO (default): se DROPEA `lsi_origin_zone` porque correla
  r≈0,93 con `lsi_origin_stop` (diagnóstico `diagnose_inertia_correlation.py`,
  matriz completa). Meter ambos = multicolinealidad. Se queda LSI-paradero
  (más fino). Quedan 3 índices por ventana: DSI, TSI, LSI-paradero.
- DROP AUTOMÁTICO de cohorte en ventanas intra: en intra-anual la cohorte de
  referencia (solo_2024) queda VACÍA (toda tarjeta elegible viajó ese año) ->
  cohort_mixta+cohort_solo_2025 colineales con la ASC -> NO identificado
  (Larch explota a ±1e7, Biogeme amortigua a ~0). `mnl_prep` lo detecta
  (ref_count==0) y dropea el bloque cohorte. La INTER no se ve afectada.
- Correlación INTER vs INTRA baja (r 0,16–0,38 en los 4 índices) e INTRA2024 vs
  INTRA2025 también baja (r 0,20–0,38). -> aportan SEÑAL DISTINTA: justifica
  tanto los modelos conjuntos como el de 3 ventanas (no son redundantes).
- z sobre el universo común; validación cruzada Biogeme↔Larch en TODAS las
  especificaciones (max diff < 0,01).

### Arquitectura
- `lib/user_level/mnl_prep.py`: `prepare_mnl_dataset(inertia_window=...)`.
  Acepta str (1 ventana) o list[str] (modelo conjunto). Constantes
  `INERTIA_WINDOWS`, `INERTIA_INDICES`, `INERTIA_INDICES_PARSIMONIOUS`.
  Función `_merge_inertia` (inner join multi-ventana con sufijos __inter /
  __intra2025), `_window_tag`. Tests en `test_mnl_prep.py`
  (test_inertia_merge_subsets_and_standardizes, test_inertia_joint_two_windows).
- Runners: `--inertia-window` REPETIBLE en fit_mnl_biogeme y fit_mnl_larch.
  1 vez = ventana individual; 2-3 veces = conjunto sobre universo común.
- `scripts/user_level/diagnose_inertia_correlation.py`: correlación entre
  ventanas sobre el universo común (paso previo a cualquier modelo conjunto).
- `scripts/user_level/summarize_inertia_models.py`: consolida coeficientes de
  los 6 modelos -> `outputs/SUMMARY_inertia_coefs.csv`.

### Universos por especificación
| Especificación | Universo (tarjetas) | Rho² |
|---|---|---|
| inter (individual) | 311.633 | 0,59 |
| intra2024 (individual) | 427.051 | ~0,67 |
| intra2025 (individual) | 439.421 | 0,58 |
| inter+intra2025 (conjunto) | 180.191 | 0,61 |
| inter+intra2024 (conjunto) | 181.915 | 0,62 |
| inter+intra2024+intra2025 (3 ventanas) | 127.829 | 0,64 |

### RESULTADOS — coeficientes de inercia por especificación
Todos en z, específicos por alternativa, vs BIP referencia. Fuente:
`SUMMARY_inertia_coefs.csv`. (s = ventana única en modelos individuales.)

**QR_RED — DSI (días):**
| modelo | INTER | INTRA2024 | INTRA2025 |
|---|---|---|---|
| inter (indiv) | −0,068 | — | — |
| intra2024 (indiv) | — | −0,082 | — |
| intra2025 (indiv) | — | — | −0,046 |
| inter+intra2024 | −0,064 | −0,077 | — |
| inter+intra2025 | −0,022 | — | −0,064 |
| 3 ventanas | −0,021 | −0,090 | −0,061 |

**QR_OTHER — DSI (días):**
| modelo | INTER | INTRA2024 | INTRA2025 |
|---|---|---|---|
| inter (indiv) | −0,103 | — | — |
| intra2024 (indiv) | — | −0,063 | — |
| intra2025 (indiv) | — | — | −0,086 |
| inter+intra2024 | −0,046 | −0,086 | — |
| inter+intra2025 | −0,088 | — | −0,054 |
| 3 ventanas | −0,009 | −0,092 | −0,047 |

**QR_RED — TSI (horas):**
| modelo | INTER | INTRA2024 | INTRA2025 |
|---|---|---|---|
| inter (indiv) | +0,069 | — | — |
| inter+intra2024 | +0,088 | −0,004 | — |
| inter+intra2025 | +0,111 | — | −0,011 |
| 3 ventanas | +0,095 | +0,013 | +0,001 |

**QR_OTHER / QR_RED — LSI-paradero (origen):** negativo y robusto en todas las
especificaciones (INTER −0,06 a −0,12; INTRA −0,03 a −0,12). Mayor regularidad
de paradero -> lealtad BIP. LSI-zona (individuales) ≈ +0,01 a +0,10, no robusto;
por eso fuera del set parsimonioso.

### HALLAZGO CENTRAL — jerarquía temporal de la inercia
Con las 3 ventanas juntas se SEPARAN dos mecanismos que en los modelos de 2
ventanas no se distinguían:
1. **Regularidad de DÍAS (DSI) -> intra-periodo.** En el modelo de 3, el DSI
   INTER se desploma (QR_OTHER: −0,009) y la señal se concentra en las INTRA
   (−0,092 / −0,047). Lo que importa es ser rutinario DENTRO de un mes dado, no
   la persistencia entre años. Asociado a QR_OTHER (adopción difusa/esporádica).
2. **Regularidad de HORAS (TSI) -> inter-anual.** Patrón OPUESTO: solo la
   dimensión INTER predice (QR_RED +0,095), las INTRA son nulas (+0,013 / +0,001).
   Lo que importa es HABER MANTENIDO el horario entre años (estabilidad de largo
   plazo). Asociado a QR_RED.

Lectura unificada de TODO el frente inercia: más regularidad de hábito ->
LEALTAD a BIP (signos negativos dominantes); el adoptante de QR (sobre todo
QR_OTHER) es el usuario de patrón irregular/cambiante. Coherente con QR_OTHER =
"adopción difusa" del techo predictivo. Magnitudes modestas (|β| 0,01–0,18 en z,
vs educación ~0,7): inercia es predictor SECUNDARIO pero significativo y estable.

### Outputs
`params_*_inertia-*.csv` y `params_larch_*_inertia-*.csv` (6 modelos × 2
frameworks), `SUMMARY_inertia_coefs.csv`,
`inertia_correlation_*.csv` / `inertia_corrmatrix_*.csv`.

### Gotchas registrados
- 2024-W15 NO estaba consolidado (solo 61 batches en `tmp/..._2024-W15_batches/`);
  se consolidó a KINGSTON + symlink. Esquema idéntico (135 cols) al de las otras
  semanas, seguro de concatenar.
- `.iter` VENENOSO de Biogeme: al cambiar el modelo (drop cohorte intra), el
  `__<label>.iter` de una corrida previa contamina los valores iniciales y la
  estimación NO converge (Rho² negativo, "termina" en ~67s en vez de ~135s).
  FIX permanente: `fit_mnl_biogeme` borra `__<label>*.iter` ANTES de estimar.

## 2026-06-07 — Inercia a nivel VIAJE (notebook 17): replicación cruzada

Tras validar la inercia a nivel TARJETA (arriba), se replicaron las MISMAS 6
especificaciones a nivel VIAJE en el notebook 17
(`03_models/17_residence_socio_mnl_sensitivity.qmd`), sección 9 autocontenida.
Es VALIDACIÓN CRUZADA: otra unidad (viaje vs tarjeta), otro universo, otro
modelo (con ATRIBUTOS DE ALTERNATIVA TVH/TEI/TET/NTR), mismos índices.

### Diferencias de implementación vs nivel tarjeta
- Unidad = viaje; el índice (por tarjeta) se pega a TODOS los viajes de esa
  tarjeta. Inner join subsetea VIAJES.
- z estandarizado a nivel TARJETA (sobre tarjetas únicas elegibles), NO por
  viaje — si no, las tarjetas con más viajes sobreponderan media/sd. Esa
  sutileza la encapsula `lib/user_level/inertia_trips.attach_inertia_trips`.
- Entran como `extra_cols` del helper `estimate_mnl_with_extras` ya existente
  (betas específicos por alternativa). No se tocó MODEL_SPECS ni el flujo previo.
- Sample base: home_alta de `pooled_2024_2025`, sample2pct (ya viene al 2% del
  builder; NO se aplica sampleo adicional). 279.643 viajes / 254.621 tarjetas.

### COBERTURA (sesgo a documentar)
El inner join recorta fuerte y SESGA hacia usuarios frecuentes
(`scripts/user_level/measure_inertia_coverage_trips.py`). Por eso es
SENSIBILIDAD, no modelo principal del frente viaje.
| Especificación | viajes | % sample | tarjetas |
|---|---|---|---|
| inter | 91.808 | 32,8% | 78.463 |
| intra2024 | 107.869 | 38,6% | 93.552 |
| intra2025 | 114.169 | 40,8% | 98.965 |
| inter+intra2024 | 64.128 | 22,9% | 53.623 |
| inter+intra2025 | 64.870 | 23,2% | 54.085 |
| inter+intra2024+intra2025 | 50.133 | 17,9% | 41.276 |

### RESULTADOS — el patrón de TARJETA se REPLICA a nivel viaje
Coeficientes en z, específicos por alternativa, vs BIP. Fuente:
`SUMMARY_inertia_trips_coefs.csv` (en el RESULTS_DIR del nb 17). Significancia
con |t|>1,96.

**DSI (días) — negativo, MÁS fuerte en QR_OTHER (igual que tarjeta):**
| modelo | QR_OTHER INTER | QR_OTHER INTRA |
|---|---|---|
| inter (indiv) | −0,160 (t −16,2) | — |
| intra2024 (indiv) | — | −0,139 (t −12,5) |
| intra2025 (indiv) | — | −0,124 (t −12,7) |
| inter+intra2024 | −0,138 | intra2024 −0,103 |
| inter+intra2025 | −0,198 | intra2025 −0,075 |
| 3 ventanas | −0,084 | intra2024 −0,087 / intra2025 −0,064 |

**TSI (horas) — positivo, DOMINADO por INTER (igual que tarjeta):**
En los 3 conjuntos `TSI__inter` es fuerte (QR_RED +0,18 a +0,20, t≈6) y las
`TSI__intra` se desploman o invierten (QR_RED +0,06 / −0,04 / −0,05, mayormente
no sig.). Confirma: la regularidad horaria que predice QR_RED es la INTER-anual.

**LSI-paradero — negativo y robusto en INTER**, se diluye en intra2025
(QR_RED/QR_OTHER ~0, no sig.), idéntico a tarjeta.

### HALLAZGO: doble confirmación independiente
La JERARQUÍA TEMPORAL (DSI días→intra, TSI horas→inter; más regularidad →
lealtad BIP) aparece en DOS frentes independientes (tarjeta y viaje). No es
artefacto de la unidad de análisis. A nivel viaje los t-stats de INTER son
incluso más nítidos (ej. DSI QR_OTHER inter t=−16,2). El modelo de 3 ventanas
replica la atenuación del DSI-inter (QR_OTHER baja de −0,16 a −0,08 al entrar
las intra), igual que en tarjeta.

### Arquitectura
- `lib/user_level/inertia_trips.py`: `attach_inertia_trips` (merge + z por
  tarjeta), `inertia_param_tags`. Reusa constantes de `mnl_prep`.
- Notebook 17 sección 9: flag `RUN_INERTIA_TRIPS` (independiente de
  RUN_ESTIMATION). Para correr SOLO inercia: RUN_ESTIMATION=False,
  RUN_INERTIA_TRIPS=True, correr todas las celdas (setup+helpers obligatorios).
- `scripts/user_level/measure_inertia_coverage_trips.py`: cobertura (solo cuenta).
- Outputs: `params_mnl_inertia_trips_home_alta_*.csv` + stats en RESULTS_DIR del
  nb 17, `SUMMARY_inertia_trips_coefs.csv`.

### Gotcha
- intra2024 se interrumpió (Ctrl-C) en la 1ª corrida -> "not converged". Se
  re-corrió limpio (LL=−46826,65, convergió). El radio de región de confianza
  dispara a 1e10 en estos modelos (sample chico + atributos de alternativa),
  pero convergen igual (gradiente relativo < 6e-06). No confundir con el .iter
  venenoso: estos arrancan desde cero (Starting values: {}).
