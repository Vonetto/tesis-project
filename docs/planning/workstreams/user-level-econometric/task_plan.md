# Frente Econométrico A Nivel Tarjeta (MNL De Adopción QR)

## Objetivo

Estimar el modelo principal de tesis: un MNL de adopción de tipo de tarjeta
a nivel `id_tarjeta`, que responde "¿qué características de uso del transporte
y del territorio de residencia se asocian con adoptar pago QR, y se distingue
el perfil de QR_RED del de QR_OTHER?". Es interpretación (signos, magnitudes,
significancia), complementaria al diagnóstico de techo predictivo (XGBoost),
que ya mostró que la separación es moderada (~0,68 AUC) y de origen conductual.

Continúa el frente `user-level-redesign` (ver su notes.md para EDA, panel,
matriz supervisada y techo predictivo). Este workstream cubre SOLO la
estimación econométrica.

## Estado

- Set de variables del MNL main: CERRADO y verificado (2026-06-02).
- Matrices regeneradas con fix de CENTRO (ver notes.md). 138 cols.
- Estructura del modelo: definida (MNL plano, BIP referencia, coeficientes
  específicos por alternativa, nested como sensibilidad IIA).
- Pendiente: implementar `lib/user_level/mnl_prep.py`, runners Biogeme/Larch,
  estimar, interpretar.

## Decisiones cerradas

### Modelo
- Unidad: `id_tarjeta` (proxy de usuario). Es un MNL de SOLO características
  del decisor (no hay atributos de alternativa) = regresión logística
  multinomial. Por identificación, todos los coeficientes son específicos de
  alternativa (un coeficiente genérico sobre una característica del decisor se
  cancela en las probabilidades relativas).
- Alternativas: BIP (referencia, V=0), QR_OTHER, QR_RED.
  - `V_QR_x = ASC_x + beta_x · x_i`, softmax estándar.
- Binario `QR vs BIP` como síntesis paralela.
- Coeficientes: empezar todo ESPECÍFICO por alternativa; simplificar
  data-driven (LR test) los de uso que sean indistinguibles entre QR_OTHER y
  QR_RED ("restricción de genericidad" = igualdad ENTRE las dos alternativas
  QR, no genericidad clásica sobre atributos).
- Estructura: MNL plano principal; nested (QR_OTHER+QR_RED vs BIP) solo como
  sensibilidad de IIA (esperado lambda≈1, sin atributos de alternativa el nido
  aporta poco).
- Herramientas: Biogeme (principal) + Larch (validación cruzada de coefs).

### Universo
- Main: `interannual_ml_clean + home_alta + n_viajes>=3` (2.460.264 tarjetas).
- Sensibilidades de universo: `home>=3`, `n>=5`, `n>=10`, `alta_media`
  (matrices ya materializadas).

### Set x_i del MNL main (transformaciones decididas mirando distribuciones)
- Exposición/cohorte:
  - `n_viajes` -> log1p + z (skew 1,99, cola larga).
  - cohorte temporal -> 3 dummies (ref `solo_2024`): solo_2024 / mixta /
    solo_2025. `share_trips_2025` es BIMODAL (36% en 0, 35% en 1), por eso
    dummies y no continua. Continua en sensibilidad.
- Uso/conductual (estandarizar a z):
  - 6 shares: `share_lab_pm`, `share_lab_pt`, `share_no_lab`,
    `share_trips_with_transfer`, `share_trips_solo_metro`,
    `share_trips_metro_bus`. Todas a z; `has_*` como sensibilidad para las de
    cero dominante (no_lab 52%, metro_bus 56%, lab_pt 48% en 0).
  - `hora_mean` -> z (campana limpia, skew 0,33). Bins por franjas de
    transporte como sensibilidad fija (chequeo de no-linealidad).
  - `hora_std` -> z (sin NaN en n>=3).
  - `t_vehiculo_mean_min`, `t_espera_ini_mean_min` -> winsor p99 (en fold) + z.
- Socio residencial:
  - `res_educacion` (`res_share_cine18_universitaria_o_mas_micro_z`) -> z (ya).
  - `res_de_proxy` (`res_eod2012_share_hogares_de_income_proxy_z`) -> z (ya).
  - `res_age_share_25_44`, `res_age_share_18_24` -> ESTANDARIZAR a z (vienen
    crudas en proporción).
  - `res_parv` (`res_share_asistencia_parv_z`) -> winsor p1-p99 (en fold) + z
    (cola: max 7,2 z).
  - `res_inmigrantes` (`res_share_inmigrantes_z`) -> winsor p1-p99 (en fold)
    + z (skew 1,7, cola a 4,8 z).
- Geografía (dummies one-hot, específica por alternativa):
  - `home_macro_*` + `origin_top1_macro_*`, 7 niveles (CENTRO incluido tras
    fix). REFERENCIA: PONIENTE (mayor volumen ~27%, QR bajo 13,9%, no es
    categoría de interés). Dummies activas: norte, oriente, centro, sur,
    suroriente, externa_especial.

### Fuera del main -> sensibilidades
- Ruta (`service_route_*`, 31% missing): fuera del main; sensibilidad con
  imputación+flag.
- `res_discapacidad` (r=-0,73 con educación): fuera por colinealidad.
- `res_mujeres_winsor`, edad continua, cohorte continua, bins hora,
  `has_*` shares, OSM, BIP friction, offer, rhythm, context residual.

### Preprocesamiento
- PATRÓN: se sigue el del notebook 16 (`03_models/16_eod2012_income_proxy_
  stepwise.qmd`), NO un transformador fiteable estilo sklearn. El 16 usa
  listas de SPECS `(label, [columnas])` + funciones de preparación en `lib/`,
  y ASUME columnas ya transformadas (en z). Se descarta el MNLPreprocessor
  fit/transform: es sobre-ingeniería del frente predictivo (techo XGBoost).
  El modelo econométrico es DESCRIPTIVO (sin holdout); estandarizar/winsorizar
  sobre el universo completo es correcto, no es leakage (no se mide
  generalización out-of-sample).
- Las transformaciones que el builder NO hizo (deja crudo por contrato) las
  aplica `mnl_prep` (lib): log1p de n_viajes, winsor inmigrantes/parv,
  estandarizar las 2 franjas etarias que vienen crudas, dummies de cohorte,
  dummies de macrozona con ref PONIENTE. Análogo a lo que
  `lib/od_buffers_nested_logit.py` hace para el nivel viaje.
- El ~0,3% residual sin macrozona real (zonas 848-853 + sin registro):
  tratamiento menor, decidir en mnl_prep (excluir o dummy residual).

## Arquitectura (convención: todo lo nuevo bajo `user_level/`)

Sigue el patrón del notebook 16: funciones de preparación en lib + specs
declarativas + runner que orquesta. NO clases fiteables.

```
lib/user_level/
  __init__.py
  mnl_prep.py          # FUNCIONES: carga matriz, drops r=1, aplica
                       # transformaciones faltantes (log1p, winsor, estandarizar
                       # franjas, dummies cohorte, dummies macro ref PONIENTE),
                       # devuelve DataFrame idco + listas de columnas. Sin clase.
  test_mnl_prep.py
scripts/user_level/
  fit_mnl_biogeme.py   # MNL plano 3 alt + binario. PRINCIPAL. SPECS (label,cols)
  fit_mnl_larch.py     # réplica/validación (lx.Dataset.construct.from_idco).
  (ya existen: profile_mnl_features.py, diagnose/identify/map/verify de macro)
03_models/user_level/
  mnl/  (specs y outputs; formato a confirmar: inline como el 16, o YAML)
02_eda/user_level/
  mnl_report.qmd       # reporte/interpretación (al final, solo lee outputs)
```

Formato de datos para el modelo: idco (una fila por id_tarjeta, x_i + choice
1=BIP/2=QR_RED/3=QR_OTHER). Larch: `lx.Dataset.construct.from_idco(pdf,
alts={1:"BIP",2:"QR_RED",3:"QR_OTHER"})`; Biogeme: `db.Database` sobre el mismo
pandas idco. Coeficientes específicos por alternativa, BIP referencia. Es el
MISMO modelo que el notebook 16, cambiando unidad viaje -> tarjeta.

Base macrozona: PONIENTE (no CENTRO como el nivel viaje). Divergencia
documentada: a nivel viaje CENTRO es destino frecuente (alto volumen de viajes
al centro); a nivel tarjeta la macrozona es RESIDENCIA, donde PONIENTE domina
(27%) y CENTRO es minoritario con QR alto.

No tocar lo de nivel viaje (03_models/biogeme-logit, larch_logit,
lib/od_buffers_nested_logit.py).

## Hitos

1. `lib/user_level/mnl_prep.py` + test: FUNCIONES de preparación. ✅ (2026-06-03)
2. `fit_mnl_biogeme.py`: runner MNL 3 alt, específico por alternativa. ✅ (2026-06-03)
3. MNL main estimado (full-específico, submuestra 30% por RAM, signos
   validados vs EDA y vs notebook 17). ✅ (2026-06-03)
4. ~~LR test genérico-entre-QR~~ DESCARTADO como obligatorio (N grande rechaza
   restricciones triviales; full-específico es el modelo principal).
5. Nested (sensibilidad IIA). ✅ (2026-06-03) MU_QR=1 en cota -> MNL plano
   adecuado, IIA razonable. Nota: nested solo converge en submuestra ~10%.
6. Binario QR vs BIP. ✅ (2026-06-03) Confirma que el binario diluye la
   heterogeneidad (educación +0,17 vs QR_RED +0,76 / QR_OTHER ~0) -> multiclase
   es el modelo principal.
7. Sensibilidades de universo (home>=3, n>=10, alta_media). ✅ (2026-06-03)
   Hallazgo robusto: educación->QR_RED 0,71-0,79 y ->QR_OTHER ~0 en los 4
   universos. Pendiente opcional: ruta, discapacidad como sensibilidades de spec.
8. `fit_mnl_larch.py`: validar coeficientes contra Biogeme. ✅ (2026-06-03)
   Max diff 0,0057 con datos idénticos -> Larch y Biogeme coinciden. Requirió
   submuestra determinística por hash de id_tarjeta (mnl_prep.stratified_subsample).
9. Reporte/interpretación. ⏳ siguiente.

10. Indicadores de INERCIA (DSI/TSI/LSI de Lizana) en el MNL. ✅ (2026-06-07)
    Ver notes.md sección "2026-06-07 — Indicadores de inercia". 6 modelos
    estimados y validados (Biogeme↔Larch, max diff < 0,01):
    - 3 individuales (inter, intra2024, intra2025).
    - 2 conjuntos de 2 ventanas (inter+intra2024, inter+intra2025).
    - 1 conjunto de 3 ventanas (inter+intra2024+intra2025).
    Set parsimonioso (sin LSI-zona, r≈0,93 con LSI-paradero). Universo por
    inner join (sin imputar): 128K–439K según especificación.
    HALLAZGO: jerarquía temporal — DSI(días)→intra, TSI(horas)→inter; más
    regularidad → lealtad BIP. Predictor secundario pero robusto.
    Outputs: `SUMMARY_inertia_coefs.csv`, `params_*_inertia-*.csv`.

11. Inercia a nivel VIAJE (notebook 17). ✅ (2026-06-07) Las MISMAS 6
    especificaciones replicadas en el frente viaje (sección 9 del nb 17, módulo
    `lib/user_level/inertia_trips.py`). Validación cruzada: otra unidad/universo/
    modelo, MISMO patrón. Cobertura tras inner join: 18%–41% del sample (sesgo a
    usuarios frecuentes -> es SENSIBILIDAD, no main). HALLAZGO replicado: jerarquía
    temporal DSI(días)→intra, TSI(horas)→inter; t-stats de INTER aún más nítidos
    (DSI QR_OTHER inter t=−16). Outputs: `SUMMARY_inertia_trips_coefs.csv`,
    `params_mnl_inertia_trips_home_alta_*.csv`. Ver notes.md sección viaje.

## Preguntas abiertas

- Forma exacta de las funciones de utilidad en Biogeme/Larch (replicar el
  patrón del notebook 16: `m.utility_co[alt]`, `P("BETA_x_qr_red")*X("col")`).
- Confirmar al implementar mnl_prep que `home_macro_centro` /
  `origin_top1_macro_centro` existen en la matriz regenerada.
- Ponderación por `n_viajes`: profesor dijo que pierde sentido al filtrar
  ocasionales. Confirmar que el MNL va sin pesos.
- Tratamiento del ~0,3% sin macrozona residual.
- Formato de specs: inline en el runner como el 16, o YAML externo. A definir
  al escribir fit_mnl_biogeme.
- El modelo principal es DESCRIPTIVO (sin holdout): estandarización/winsor
  sobre el universo completo, NO en folds. (El fit/transform en-fold era del
  frente predictivo/techo, no aplica aquí.)
