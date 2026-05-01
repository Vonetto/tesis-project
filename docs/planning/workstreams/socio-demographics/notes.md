# Notes — Socio-demographic Integration (Censo/CASEN ↔ Zonas777)

## 2026-04-09 (fork: análisis de microdatos comunales)
- Objetivo de este fork:
  - centrarse en los microdatos comunales del Censo 2024 para entender con precisión variables educativas/laborales y evaluar proxies de ingreso/estatus antes de cualquier spatialization fina.
- Verificación local de archivos:
  - existen:
    - `/Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip`
    - `/Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip`
    - `/Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip`
  - no existe una base `CASEN` descargada/integrada en el proyecto actualmente.
- Headers confirmados:
  - `personas_censo2024.csv` incluye:
    - `escolaridad`
    - `cine11`
    - `p37_alfabet`
    - `sit_fuerza_trabajo`
    - `p40_cise_rec`
    - `cod_ciuo`
    - `cod_caenes`
    - `p44_lug_trab`
    - `p45_medio_transporte`
  - `hogares_censo2024.csv` incluye:
    - tenencia/equipamiento/TIC (`p15a_serv_tel_movil`, `p15b_serv_compu`, `p15d_serv_internet_fija`, `p15e_serv_internet_movil`, etc.)
  - `viviendas_censo2024.csv` incluye:
    - materialidad, dormitorios, agua, saneamiento, electricidad e `indice_hacinamiento`.
- Distinción metodológica clave:
  - `prom_escolaridad18` que usamos hoy en `ZONA777` viene de la **base manzana-entidad** ya agregada;
  - `escolaridad` en `personas_censo2024.csv` es una variable **individual** de microdato comunal y probablemente es lo que el profesor tiene en mente al hablar de “nivel educacional”.
- Hallazgos exploratorios rápidos sobre `escolaridad` (muestra local de 300k filas):
  - los códigos más frecuentes son `12`, `17`, `15`, `8`, `16`, `14`, etc.;
  - su cruce con `cine11` sugiere que `escolaridad` es una escala ordinal fina de logro educativo/avance, no solo una categoría binaria;
  - `cine11` parece capturar niveles agregados más cercanos a “nivel educacional”, mientras `escolaridad` entrega mayor granularidad;
  - esto abre dos rutas candidatas:
    - seguir usando `prom_escolaridad18` como proxy continua simple;
    - o derivar desde microdatos comunales shares por tramo (`baja`, `media`, `técnica`, `superior`, etc.) si se implementa una spatialization defensible.

## 2026-04-09 (diccionario microdatos comunales confirmado)
- Usuario aportó:
  - `/Users/vicenteonetto/Downloads/diccionario_variables_censo2024 (1).xlsx`
  - `/Users/vicenteonetto/Downloads/diccionario_variables_glosas_censo2024 (1).xlsx`
- Hallazgo clave:
  - `diccionario_variables_censo2024 (1).xlsx` sí es el codebook de microdatos comunales (`tabla_personas`, `tabla_hogares`, `tabla_viviendas`) y contiene valores + etiquetas por variable.
  - `diccionario_variables_glosas_censo2024 (1).xlsx` corresponde al diccionario de la base agregada manzana-entidad, consistente con lo ya usado antes.
- Confirmaciones de variables de `tabla_personas`:
  - `escolaridad`: **Años de escolaridad**, valores `0:24`, `-99 = no respuesta`.
  - `cine11`: **Logro educativo CINE** (niveles 1:12, `-99` no respuesta); esta variable es conceptualmente más cercana a “nivel educacional” que `escolaridad`.
  - `sit_fuerza_trabajo`: `1=ocupado`, `2=desocupado`, `3=fuera de la fuerza de trabajo`, `-99`, `NA`.
  - `p40_cise_rec`: `1=independiente`, `2=dependiente`, `3=familiar/personal no remunerado`, `-99`, `NA`.
  - `p37_alfabet`: `1=sí`, `2=no`, `-99`, `NA`.
  - `cod_ciuo`: grandes grupos ocupacionales CIUO-08.CL a 1 dígito.
  - `cod_caenes`: rama de actividad económica CAENES a 1 dígito.
  - `p44_lug_trab`: localización del trabajo (misma vivienda / misma comuna / otra comuna / otro país / varias).
  - `p45_medio_transporte`: medio principal al trabajo.
- Implicancia metodológica:
  - si el profesor hablaba de “nivel educacional”, la variable más natural del microdato es probablemente `cine11`;
  - `escolaridad` sirve más bien como medida continua de años de estudio;
  - `prom_escolaridad18` del agregado manzana-entidad no es equivalente exacto a `cine11`, aunque se relaciona estrechamente.

## 2026-04-09 (propuesta de desagregación espacial de microdatos comunales)
- Se acordó como propuesta metodológica base para este fork:
  - **no** asignar microdatos comunales directo a `ZONA777`;
  - primero espacializar **comuna -> manzana-entidad**;
  - después agregar **manzana-entidad -> ZONA777** con el pipeline ya existente.
- Unidad de asignación propuesta:
  - trabajar a nivel de **vivienda/hogar** como unidad base de la población sintética;
  - las personas quedan asociadas a la vivienda/hogar asignada.
- Datos a combinar:
  - microdatos comunales `personas/hogares/viviendas`;
  - base agregada `manzana-entidad`;
  - cartografía de manzanas;
  - agregación posterior a `ZONA777`.
- Lógica del método:
  - construir perfiles de vivienda/hogar/personas dentro de cada comuna;
  - asignar inicialmente hogares a manzanas candidatas;
  - refinar la asignación con un algoritmo de calibración/optimización para reproducir los agregados finos observados;
  - una vez calibrado, derivar variables nuevas por manzana y luego agregarlas a `ZONA777`.
- Variables de calibración priorizadas:
  - `n_hog`, `n_per`;
  - tamaño/composición de hogar;
  - estructura etaria gruesa;
  - alfabetismo, discapacidad;
  - acceso TIC del hogar;
  - hacinamiento;
  - `prom_escolaridad18` como ancla educativa fuerte.
- Variables objetivo iniciales (a recuperar espacialmente):
  - educación: `cine11`, `escolaridad`;
  - estatus laboral: `sit_fuerza_trabajo`, `p40_cise_rec`.
- Variables objetivo de segunda ronda:
  - `cod_ciuo`, `cod_caenes`.
- Decisión de modelación asociada:
  - no abrir de entrada muchas categorías educativas en el modelo;
  - derivar después 1-2 proxies compactas e interpretables desde `cine11`/`escolaridad`, una vez validada la spatialization.
- Validaciones mínimas exigidas antes de usar resultados en el modelo:
  - preservar totales comunales;
  - reproducir bien las restricciones usadas a nivel manzana;
  - comparar `prom_escolaridad18` reconstruido desde microdatos vs agregado observado;
  - revisar estabilidad frente a distintas semillas/inicializaciones;
  - verificar que los agregados finales en `ZONA777` no generen patrones absurdos.
- Estrategia de implementación propuesta:
  - partir con un **piloto en pocas comunas** antes de escalar a toda el área de estudio.

## 2026-04-09 (etapas de implementación acordadas para la spatialization)
- La implementación se tratará como un problema de **población sintética espacializada**, no como un join espacial directo.
- Interpretación metodológica acordada:
  - los resultados no representan ubicación real individual;
  - representan una asignación plausible y calibrada de hogares/personas dentro de cada comuna.
- Etapa 0 — congelar especificación:
  - cerrar unidad de asignación;
  - cerrar shortlist de variables `hard`, `calibration`, `target`, `later`;
  - definir criterio explícito de éxito/falla del piloto.
- Etapa 1 — ensamblaje de datos base:
  - enlazar `personas`, `hogares` y `viviendas`;
  - construir tabla sintética base a nivel `vivienda/hogar`;
  - verificar consistencia interna de llaves y conteos.
- Etapa 2 — preparación de restricciones finas:
  - construir tabla objetivo a nivel `manzana-entidad`;
  - preparar las variables de calibración que existen en el agregado fino;
  - revisar comparabilidad exacta entre definición microdato vs definición agregado.
- Etapa 3 — piloto de asignación simple:
  - correr primero un método auditable/simple;
  - evitar comenzar con optimización compleja;
  - seleccionar pocas comunas heterogéneas para prueba.
- Etapa 4 — validación obligatoria:
  - validar preservación de totales comunales;
  - validar fit de restricciones a nivel manzana;
  - usar validación cruzada dejando fuera al menos una variable fina conocida;
  - evaluar estabilidad con múltiples semillas/inicializaciones.
- Etapa 5 — refinamiento:
  - solo si el método simple no cumple criterios, probar refinamiento con swaps / simulated annealing / heurísticas;
  - cualquier aumento de complejidad debe justificarse con mejora real en validación.
- Gate metodológico antes de usar outputs en modelos:
  - una variable spatializada solo puede entrar al modelo si muestra:
    - recuperación razonable en validación cruzada;
    - estabilidad razonable entre corridas;
    - patrón agregado a `ZONA777` interpretable y no aberrante.

## 2026-04-09 (implementación iniciada — etapa 1)
- Se implementó el módulo:
  - [`lib/censo2024_microdata_base.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_microdata_base.py)
- Responsabilidad del módulo:
  - leer `personas`, `hogares`, `viviendas` desde los zips oficiales;
  - limpiar códigos faltantes/suprimidos comunes (`NA`, `-99`, `-66`);
  - agregar features de personas a nivel `id_vivienda + id_hogar`;
  - mergear atributos de hogar y vivienda en una base única reutilizable.
- Features agregadas implementadas a nivel hogar:
  - conteos de personas y tramos etarios (`0-17`, `18-24`, `25-44`, `45-59`, `60+`);
  - `n_discapacidad_5mas`, `n_analfabet_15mas`;
  - `n_ocupado_15mas`, `n_desocupado_15mas`, `n_fuera_fuerza_trabajo_15mas`;
  - `n_independiente`, `n_dependiente`, `n_no_remunerado`;
  - `prom_escolaridad18_micro`.
- Se agregó test sintético:
  - [`lib/test_censo2024_microdata_base.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_microdata_base.py)
- Validación realizada:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_microdata_base`
  - resultado: `3 tests OK`
- Smoke test con esquema real:
  - se construyeron zips sampleados de `50,000` filas desde los archivos oficiales;
  - el módulo produjo correctamente:
    - `/tmp/censo2024_household_microdata_base_sample.parquet`
  - shape observado del sample:
    - `50,000 x 55`
- Estado:
  - el contrato de la **tabla base enlazada** ya quedó fijado;
  - falta materializar la corrida completa y evaluar tiempo/memoria antes de pasar a la etapa 2.

## 2026-04-09 (implementación iniciada — etapa 2)
- Se implementó el módulo:
  - [`lib/censo2024_manzent_targets.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_manzent_targets.py)
- Responsabilidad del módulo:
  - leer la base `manzana-entidad` desde el zip oficial;
  - extraer solo las variables de calibración/holdout definidas para la spatialization;
  - derivar `n_18_mas` de forma estricta para comparar/validar `prom_escolaridad18`.
- Cobertura del contrato actual:
  - restricciones/calibración:
    - `n_per`, `n_hog`
    - `n_edad_18_24`, `n_edad_25_44`, `n_edad_45_59`, `n_edad_60_mas`
    - `n_discapacidad`, `n_analfabet`
    - `n_serv_compu`, `n_internet`, `n_viv_hacinadas`
    - `prom_escolaridad18`
  - variables útiles para validación/holdout:
    - `n_ocupado`, `n_desocupado`, `n_fuera_fuerza_trabajo`
    - `n_cise_rec_independientes`, `n_cise_rec_dependientes`, `n_cise_rec_trabajador_no_remunerado`
    - `n_cine_nunca_curso_primera_infancia`, `n_cine_primaria`, `n_cine_secundaria`, `n_cine_terciaria_maestria_doctorado`, `n_cine_especial_diferencial`
- Se agregó test sintético:
  - [`lib/test_censo2024_manzent_targets.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_manzent_targets.py)
- Validación realizada:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_manzent_targets`
  - resultado: `1 test OK`
- Corrida real validada:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_manzent_targets --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-parquet /tmp/censo2024_manzent_targets.parquet`
  - output observado:
    - `/tmp/censo2024_manzent_targets.parquet`
    - shape: `197,032 x 36`
- Estado:
  - el contrato de la **tabla objetivo fina** ya quedó fijado;
  - lo siguiente es elegir comunas piloto y construir la primera versión auditable del motor de asignación.

## 2026-04-09 (comunas piloto acordadas para TDD del motor de asignación)
- Se fijaron como comunas piloto iniciales:
  - **Vitacura**
  - **La Pintana**
  - **Santiago**
- Justificación funcional del set:
  - `Vitacura`: caso alto ingreso / alta escolaridad / baja vulnerabilidad relativa;
  - `La Pintana`: caso de vulnerabilidad alta y baja escolaridad relativa;
  - `Santiago`: caso heterogéneo y más exigente internamente.
- Uso metodológico previsto:
  - pilotear el motor de asignación en tres extremos/escenarios distintos;
  - usar la base `manzana-entidad` como verdad parcial para validar reconstrucción fina;
  - exigir que el método supere una baseline simple antes de escalar a más comunas.

## 2026-04-09 (baseline tonta implementada para el piloto)
- Se implementó el módulo:
  - [`lib/censo2024_spatialize_baseline.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_baseline.py)
- Lógica implementada:
  - leer microdatos solo para `Vitacura`, `La Pintana`, `Santiago`;
  - escalar cuotas de `n_hog` por manzana para que sumen exactamente el total de hogares microdato de cada comuna;
  - asignar hogares aleatoriamente a `MANZENT` dentro de la misma comuna respetando esas cuotas exactas;
  - agregar de vuelta a `MANZENT` y evaluar contra la verdad observada.
- Tests agregados:
  - [`lib/test_censo2024_spatialize_baseline.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_baseline.py)
- Validación local:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_microdata_base lib.test_censo2024_manzent_targets lib.test_censo2024_spatialize_baseline`
  - resultado: `7 tests OK`
- Corrida piloto real:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_spatialize_baseline --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-dir /tmp/censo2024_spatialize_baseline_pilot --seed 42 --comunas 13132 13112 13101`
- Métricas globales observadas:
  - `prom_escolaridad18`: `MAE=1.039`, `RMSE=1.355`, `corr=0.843`
  - `share_cine_terciaria`: `MAE=0.102`, `RMSE=0.142`, `corr=0.776`
- Lectura metodológica importante:
  - esas correlaciones globales están infladas por diferencias **entre comunas**.
- Métricas **dentro de cada comuna**:
  - `Vitacura`:
    - `prom_escolaridad18`: `MAE=0.674`, `RMSE=0.876`, `corr=-0.035`
    - `share_cine_terciaria`: `MAE=0.092`, `RMSE=0.121`, `corr=-0.096`
  - `La Pintana`:
    - `prom_escolaridad18`: `MAE=0.786`, `RMSE=1.026`, `corr=-0.000`
    - `share_cine_terciaria`: `MAE=0.042`, `RMSE=0.058`, `corr=-0.057`
  - `Santiago`:
    - `prom_escolaridad18`: `MAE=1.466`, `RMSE=1.770`, `corr=-0.023`
    - `share_cine_terciaria`: `MAE=0.167`, `RMSE=0.200`, `corr=-0.028`
- Conclusión operacional:
  - la baseline tonta preserva cuotas comunales/manzana de hogares, pero **no** reconstruye el patrón espacial intra-comunal de educación;
  - esto la deja como benchmark útil, pero insuficiente como método de spatialization.

## 2026-04-09 (criterio operativo de éxito del piloto)
- Se formalizó el criterio mínimo de éxito del piloto simple:
  - preservar exactamente los totales comunales de hogares vía cuotas escaladas por `n_hog`;
  - superar a la baseline tonta **dentro de cada comuna** en correlación espacial para los holdouts:
    - `prom_escolaridad18`
    - `share_cine_terciaria`
  - verificar estabilidad básica entre semillas para evitar mejoras espurias por desempates aleatorios.
- Aclaración metodológica:
  - la métrica pooled entre comunas **no** es criterio suficiente;
  - la evaluación principal se hace por comuna piloto (`Vitacura`, `La Pintana`, `Santiago`).

## 2026-04-09 (primer método inspirado en el artículo: matching por perfiles)
- Se implementó el módulo:
  - [`lib/censo2024_spatialize_profile.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_profile.py)
- Lógica implementada:
  - mantener cuotas exactas por `MANZENT` escaladas desde `n_hog`;
  - construir un **score de perfil de hogar** dentro de cada comuna usando:
    - `p15b_serv_compu`
    - acceso a internet por cualquier vía (`p15d/p15e/p15f`)
    - `indice_hacinamiento > 2.5`
    - tamaño de hogar (`n_personas_hogar`)
  - construir un **score de perfil de manzana** usando agregados finos equivalentes:
    - `share_serv_compu`
    - `share_internet`
    - `share_hacin`
    - `persons_per_hog`
  - ordenar hogares y slots de manzana por score dentro de cada comuna y asignar monótonamente con desempate aleatorio reproducible.
- Tests agregados:
  - [`lib/test_censo2024_spatialize_profile.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_profile.py)
- Validación local:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_spatialize_profile lib.test_censo2024_spatialize_baseline lib.test_censo2024_microdata_base lib.test_censo2024_manzent_targets`
  - resultado: `11 tests OK`
- Corrida piloto real:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_spatialize_profile --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-dir /tmp/censo2024_spatialize_profile_pilot --seed 42 --comunas 13132 13112 13101`
- Métricas globales observadas:
  - `prom_escolaridad18`: `MAE=0.948`, `RMSE=1.283`, `corr=0.878`
  - `share_cine_terciaria`: `MAE=0.098`, `RMSE=0.141`, `corr=0.867`
- Métricas por comuna:
  - `Santiago`:
    - `prom_escolaridad18`: `MAE=0.923`, `RMSE=1.306`, `corr=0.656`
    - `share_cine_terciaria`: `MAE=0.110`, `RMSE=0.150`, `corr=0.708`
  - `La Pintana`:
    - `prom_escolaridad18`: `MAE=1.046`, `RMSE=1.351`, `corr=0.443`
    - `share_cine_terciaria`: `MAE=0.049`, `RMSE=0.069`, `corr=0.326`
  - `Vitacura`:
    - `prom_escolaridad18`: `MAE=0.787`, `RMSE=1.061`, `corr=0.092`
    - `share_cine_terciaria`: `MAE=0.178`, `RMSE=0.219`, `corr=0.050`
- Comparación contra la baseline tonta:
  - mejora claramente la correlación intra-comunal en las tres comunas para ambos holdouts;
  - la mejora es fuerte en `Santiago` y `La Pintana`;
  - en `Vitacura` mejora la correlación pero sigue siendo débil;
  - en `La Pintana` y `Vitacura` el `MAE` de `prom_escolaridad18` no mejora respecto a la baseline tonta, pese a la mejora en correlación.
- Chequeo rápido de estabilidad por semilla (`1`, `42`, `99`):
  - `Santiago`: `prom_corr` entre `0.643` y `0.656`; `cine_corr` entre `0.690` y `0.708`
  - `La Pintana`: `prom_corr` entre `0.430` y `0.443`; `cine_corr` entre `0.326` y `0.345`
  - `Vitacura`: `prom_corr` entre `0.092` y `0.166`; `cine_corr` entre `0.013` y `0.050`
- Estado:
  - el método simple por perfiles **supera el benchmark aleatorio en correlación intra-comunal** y es estable en semillas;
  - todavía no domina en todas las métricas de error absoluto;
  - `Vitacura` sigue siendo el caso donde la señal intra-comunal queda más débil.

## 2026-04-09 (versión intermedia: perfiles discretos con cuotas exactas por perfil)
- Se implementó un segundo método, más cercano al artículo, en:
  - [`lib/censo2024_spatialize_profile_discrete.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_profile_discrete.py)
- Diferencia metodológica respecto al método anterior:
  - el método de `score continuo` ordena hogares y manzanas con un ranking unidimensional;
  - esta versión define **perfiles discretos** de hogar usando solo dimensiones observables también a nivel `MANZENT`:
    - `compu sí/no`
    - `internet sí/no`
    - `hacinado sí/no`
  - luego asigna **cuotas exactas por perfil** dentro de cada comuna;
  - el tamaño del hogar se usa solo como criterio de ordenamiento dentro de cada perfil para acercarse a `persons_per_hog`, no como dimensión dura del perfil.
- Decisión explícita:
  - **no** se incorporó aún `tipo de vivienda` al perfil porque en la tabla fina actual no hay una restricción equivalente por manzana que permita calibrarlo sin meter un supuesto extra.
- Tests agregados:
  - [`lib/test_censo2024_spatialize_profile_discrete.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_profile_discrete.py)
- Validación local:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_spatialize_profile_discrete lib.test_censo2024_spatialize_profile lib.test_censo2024_spatialize_baseline lib.test_censo2024_microdata_base lib.test_censo2024_manzent_targets`
  - resultado: `14 tests OK`
- Corrida piloto real:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_spatialize_profile_discrete --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-dir /tmp/censo2024_spatialize_profile_discrete_pilot --seed 42 --comunas 13132 13112 13101`
- Resultados globales:
  - `prom_escolaridad18`: `MAE=0.763`, `RMSE=1.009`, `corr=0.909`
  - `share_cine_terciaria`: `MAE=0.080`, `RMSE=0.111`, `corr=0.868`
- Resultados por comuna:
  - `Santiago`:
    - `prom_escolaridad18`: `MAE=0.885`, `RMSE=1.174`, `corr=0.649`
    - `share_cine_terciaria`: `MAE=0.112`, `RMSE=0.145`, `corr=0.663`
  - `La Pintana`:
    - `prom_escolaridad18`: `MAE=0.702`, `RMSE=0.895`, `corr=0.350`
    - `share_cine_terciaria`: `MAE=0.046`, `RMSE=0.062`, `corr=0.215`
  - `Vitacura`:
    - `prom_escolaridad18`: `MAE=0.634`, `RMSE=0.846`, `corr=0.147`
    - `share_cine_terciaria`: `MAE=0.087`, `RMSE=0.110`, `corr=0.589`
- Ajuste interno de calibración:
  - las cuotas por `n_hog`, `compu`, `internet` y `hacinamiento` quedaron exactas por construcción en las tres comunas (`MAE=0` para esas restricciones frente a los targets discretos escalados).
- Estabilidad por semilla (`1`, `42`, `99`):
  - `Santiago`: `prom_corr` entre `0.649` y `0.663`; `cine_corr` entre `0.663` y `0.678`
  - `La Pintana`: `prom_corr` entre `0.327` y `0.376`; `cine_corr` entre `0.215` y `0.279`
  - `Vitacura`: `prom_corr` entre `0.083` y `0.147`; `cine_corr` entre `0.589` y `0.600`
- Comparación cualitativa contra los métodos previos:
  - supera con claridad a la baseline aleatoria en las tres comunas;
  - frente al método de `score continuo`, mejora mucho `Vitacura` y reduce `MAE` de manera consistente;
  - a cambio, en `Santiago` y `La Pintana` sacrifica algo de correlación respecto al `score continuo`, aunque sigue muy por encima de la baseline.
- Lectura operacional:
  - el método discreto parece más **balanceado** entre reconstrucción espacial y control de errores absolutos;
  - el método de `score continuo` sigue siendo mejor si el objetivo es maximizar correlación en `Santiago`/`La Pintana`;
  - todavía no hay un ganador absoluto, pero ya existe una segunda versión simple que mejora el caso difícil (`Vitacura`) sin romper estabilidad.

## 2026-04-09 (tercera versión: distancia ponderada + softmax con capacidad)
- Se implementó una tercera asignación inicial más alineada con el artículo en:
  - [`lib/censo2024_spatialize_softmax.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_softmax.py)
- Piezas nuevas incorporadas respecto a las versiones previas:
  - **escalado explícito** de objetivos finos por atributo para que coincidan con los totales reales observados en microdatos de cada comuna;
  - **distancia ponderada** entre perfil de grupo-hogar y objetivo de manzana;
  - asignación inicial por **softmax con capacidad** `exp(-dist / tau) * capacidad`.
- Decisión de diseño:
  - se trabajó con grupos `compu/internet/hacinamiento × bucket de tamaño de hogar`;
  - el tamaño de hogar entra como atributo continuo/bucket en la distancia, no como restricción exacta por manzana.
- Tests agregados:
  - [`lib/test_censo2024_spatialize_softmax.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_softmax.py)
- Validación local:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_spatialize_softmax`
  - resultado: `3 tests OK`
- Barrido corto de `tau` sobre el piloto:
  - probados: `0.03`, `0.05`, `0.10`, `0.15`, `0.25`
  - mejor valor observado: **`tau = 0.03`**
- Corrida piloto definitiva:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_spatialize_softmax --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-dir /tmp/censo2024_spatialize_softmax_pilot_tau003 --seed 42 --tau 0.03 --comunas 13132 13112 13101`
- Resultados con `tau=0.03`:
  - globales:
    - `prom_escolaridad18`: `MAE=0.766`, `RMSE=1.005`, `corr=0.909`
    - `share_cine_terciaria`: `MAE=0.068`, `RMSE=0.096`, `corr=0.885`
  - `Santiago`:
    - `prom_escolaridad18`: `MAE=0.858`, `corr=0.647`
    - `share_cine_terciaria`: `MAE=0.099`, `corr=0.633`
  - `La Pintana`:
    - `prom_escolaridad18`: `MAE=0.731`, `corr=0.473`
    - `share_cine_terciaria`: `MAE=0.039`, `corr=0.307`
  - `Vitacura`:
    - `prom_escolaridad18`: `MAE=0.644`, `corr=0.112`
    - `share_cine_terciaria`: `MAE=0.066`, `corr=0.531`
- Comparación operativa entre métodos:
  - `baseline`: descartada como benchmark solamente; no reconstruye estructura intra-comunal;
  - `profile_score`: mejor correlación para `Santiago` y buena en `La Pintana`, pero muy débil en `Vitacura` y peor en errores absolutos;
  - `profile_discrete`: más balanceado, mejora mucho `Vitacura`, pero pierde correlación en `Santiago`/`La Pintana`;
  - `softmax_tau003`: incorpora dos piezas centrales del artículo y queda como compromiso fuerte:
    - mejora `La Pintana` frente a `profile_discrete`;
    - mantiene `Vitacura` mucho mejor que `profile_score`;
    - y baja `MAE` de `share_cine_terciaria` en las tres comunas.
- Limitación observada:
  - aunque el método `softmax` mejora los holdouts, no reproduce exactamente los objetivos escalados por atributo a nivel manzana; eso todavía requeriría un refinamiento posterior por swaps / annealing.

## 2026-04-09 (cuarta versión: refinamiento por swaps sobre la solución softmax)
- Se implementó el refinamiento local por swaps en:
  - [`lib/censo2024_spatialize_anneal.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_anneal.py)
- Qué agrega respecto a `softmax_tau003`:
  - define una **energía** por comuna como suma de residuales absolutos normalizados por atributo:
    - `n_per`
    - `compu`
    - `internet`
    - `hacinamiento`
  - selecciona una manzana con probabilidad proporcional a su error;
  - selecciona otra con probabilidad inversa a su error;
  - evalúa swaps entre muestras pequeñas de hogares en ambas manzanas;
  - acepta mejoras y también algunas peores usando criterio tipo Metropolis con temperatura.
- Tests agregados:
  - [`lib/test_censo2024_spatialize_anneal.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_anneal.py)
- Validación local completa:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_spatialize_anneal lib.test_censo2024_spatialize_softmax lib.test_censo2024_spatialize_profile_discrete lib.test_censo2024_spatialize_profile lib.test_censo2024_spatialize_baseline lib.test_censo2024_microdata_base lib.test_censo2024_manzent_targets`
  - resultado: `18 tests OK`
- Corrida piloto real:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_spatialize_anneal --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --out-dir /tmp/censo2024_spatialize_anneal_pilot --seed 42 --tau 0.03 --n-iter 5000 --init-temp 0.001 --alpha 0.9995 --sample-size 6 --comunas 13132 13112 13101`
- Resultados globales:
  - `prom_escolaridad18`: `MAE=0.754`, `RMSE=0.988`, `corr=0.910`
  - `share_cine_terciaria`: `MAE=0.067`, `RMSE=0.094`, `corr=0.888`
- Resultados por comuna:
  - `Santiago`:
    - `prom_escolaridad18`: `MAE=0.860`, `corr=0.635`
    - `share_cine_terciaria`: `MAE=0.098`, `corr=0.634`
  - `La Pintana`:
    - `prom_escolaridad18`: `MAE=0.693`, `corr=0.419`
    - `share_cine_terciaria`: `MAE=0.038`, `corr=0.267`
  - `Vitacura`:
    - `prom_escolaridad18`: `MAE=0.658`, `corr=0.089`
    - `share_cine_terciaria`: `MAE=0.066`, `corr=0.504`
- Estadísticas internas del refinamiento:
  - `Santiago`: energía `1.278 -> 1.134`
  - `La Pintana`: energía `1.944 -> 1.580`
  - `Vitacura`: energía `1.398 -> 1.346`
- Comparación operativa contra `softmax_tau003`:
  - mejora ligeramente los resultados globales;
  - mejora `MAE` en `La Pintana`;
  - en `Santiago` mantiene o empeora levemente la correlación;
  - en `Vitacura` empeora un poco respecto a la solución inicial `softmax_tau003`.
- Lectura:
  - el refinamiento por swaps **sí baja la energía interna** y mejora algo el ajuste agregado;
  - pero todavía no produce una mejora uniforme en los holdouts por comuna;
  - esto sugiere que el esquema de energía actual y/o la propuesta de swaps todavía necesitan ajuste antes de considerarlo un refinamiento claramente superior.

## 2026-04-09 (variantes conservadoras de energía para evitar sobreajuste)
- Se extendió [`lib/censo2024_spatialize_anneal.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_spatialize_anneal.py) para soportar tres modos explícitos:
  - `count`: residuales absolutos normalizados por totales comunales
  - `share`: composición por manzana (`persons_per_hog`, `share_compu`, `share_internet`, `share_hacin`)
  - `hybrid`: `n_per` en conteos + resto en shares
- Se actualizó [`lib/test_censo2024_spatialize_anneal.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_spatialize_anneal.py):
  - el caso de juguete ahora verifica mejora para `count`, `share` y `hybrid`;
  - además verifica que las tres energías efectivamente den valores distintos sobre el mismo estado.
- Validación local completa:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_spatialize_anneal lib.test_censo2024_spatialize_softmax lib.test_censo2024_spatialize_profile_discrete lib.test_censo2024_spatialize_profile lib.test_censo2024_spatialize_baseline lib.test_censo2024_microdata_base lib.test_censo2024_manzent_targets`
  - resultado: `19 tests OK`
- Corridas cortas comparables (`2500` iteraciones, misma inicialización `softmax_tau003`, misma semilla `42`):
  - `count`:
    - global:
      - `prom_escolaridad18`: `MAE=0.757`, `corr=0.910`
      - `share_cine_terciaria`: `MAE=0.0676`, `corr=0.886`
    - por comuna:
      - `Santiago`: `prom_mae=0.864`, `prom_corr=0.637`, `cine_mae=0.0994`, `cine_corr=0.628`
      - `La Pintana`: `prom_mae=0.698`, `prom_corr=0.450`, `cine_mae=0.0374`, `cine_corr=0.296`
      - `Vitacura`: `prom_mae=0.657`, `prom_corr=0.049`, `cine_mae=0.0659`, `cine_corr=0.490`
  - `share`:
    - global:
      - `prom_escolaridad18`: `MAE=0.755`, `corr=0.910`
      - `share_cine_terciaria`: `MAE=0.0670`, `corr=0.888`
    - por comuna:
      - `Santiago`: `prom_mae=0.847`, `prom_corr=0.642`, `cine_mae=0.0967`, `cine_corr=0.639`
      - `La Pintana`: `prom_mae=0.715`, `prom_corr=0.448`, `cine_mae=0.0383`, `cine_corr=0.261`
      - `Vitacura`: `prom_mae=0.646`, `prom_corr=0.109`, `cine_mae=0.0664`, `cine_corr=0.528`
  - `hybrid`:
    - global:
      - `prom_escolaridad18`: `MAE=0.760`, `corr=0.910`
      - `share_cine_terciaria`: `MAE=0.0672`, `corr=0.889`
    - por comuna:
      - `Santiago`: `prom_mae=0.842`, `prom_corr=0.659`, `cine_mae=0.0971`, `cine_corr=0.648`
      - `La Pintana`: `prom_mae=0.717`, `prom_corr=0.466`, `cine_mae=0.0386`, `cine_corr=0.298`
      - `Vitacura`: `prom_mae=0.677`, `prom_corr=0.123`, `cine_mae=0.0659`, `cine_corr=0.505`
- Lectura:
  - `share` queda mejor parado como variante conservadora más balanceada:
    - mejora el ajuste global en ambos holdouts frente a `count`;
    - mejora `Santiago` y `Vitacura` en términos generales;
    - empeora algo `La Pintana`, sobre todo en correlación de `share_cine_terciaria`.
  - `hybrid` empuja más la correlación en `Santiago`, pero degrada más el `MAE` global de `prom_escolaridad18`.
  - ninguna variante domina en todas las comunas; todavía conviene mantener la comparación contra `softmax_tau003` como baseline de refinamiento.
- Experimento adicional: aplicar el mismo refinamiento `annealing(share)` sobre la solución inicial `profile_discrete`:
  - salida:
    - `/tmp/censo2024_profile_discrete_anneal_share`
  - comparación global:
    - inicial `profile_discrete`:
      - `prom_escolaridad18`: `MAE=0.763`, `corr=0.909`
      - `share_cine_terciaria`: `MAE=0.0801`, `corr=0.868`
    - refinada `profile_discrete + annealing(share)`:
      - `prom_escolaridad18`: `MAE=0.765`, `corr=0.905`
      - `share_cine_terciaria`: `MAE=0.0781`, `corr=0.868`
  - lectura:
    - el refinamiento sobre `profile_discrete` mejora levemente solo el `MAE` de `share_cine_terciaria`;
    - empeora `prom_escolaridad18` y no mejora de forma convincente las correlaciones;
    - por ahora, el annealing parece tener más sentido sobre `softmax_tau003` que sobre `profile_discrete`.

## 2026-04-09 (operacionalización de `softmax_tau003` hacia `ZONA777`)
- Se implementó el pipeline productivo en:
  - [`lib/censo2024_microdata_zona777.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_microdata_zona777.py)
- Qué hace:
  - toma microdatos comunales `personas/hogares/viviendas`;
  - corre la asignación `softmax_tau003` hacia `MANZENT`;
  - deriva proxies compactas a nivel `MANZENT`;
  - agrega esas proxies a `ZONA777` reutilizando el mismo camino espacial del pipeline censal existente (`intersects_area` / area-weighted).
- Se extendió la base microdato en [`lib/censo2024_microdata_base.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/censo2024_microdata_base.py) para incluir conteos **CINE 18+**:
  - `n_cine18_nunca_curso_primera_infancia`
  - `n_cine18_primaria`
  - `n_cine18_secundaria`
  - `n_cine18_terciaria_maestria_doctorado`
  - `n_cine18_especial_diferencial`
- Tests agregados:
  - [`lib/test_censo2024_microdata_zona777.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_microdata_zona777.py)
  - actualización de [`lib/test_censo2024_microdata_base.py`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/lib/test_censo2024_microdata_base.py)
- Validación local:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_microdata_base lib.test_censo2024_microdata_zona777 lib.test_censo2024_spatialize_softmax lib.test_censo2024_spatialize_anneal`
  - resultado: `10 tests OK`
- Smoke real del pipeline nuevo sobre el piloto:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m lib.censo2024_microdata_zona777 --personas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip --hogares-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip --viviendas-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip --base-zip /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip --carto-parquet /Volumes/KINGSTON/tesis-project/raw/censo2024/cartografia_parquet/Cartografia_censo2024_Pais_Manzanas.parquet --zonas777-shp /Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp --out-dir /tmp/censo2024_microdata_zona777_pilot --tau 0.03 --seed 42 --comunas 13132 13112 13101`
  - salida:
    - `/tmp/censo2024_microdata_zona777_pilot/censo2024_microdata_manzent_features.parquet`
    - `/tmp/censo2024_microdata_zona777_pilot/censo2024_microdata_zona777_features.parquet`
    - `/tmp/censo2024_microdata_zona777_pilot/censo2024_microdata_zona777_summary.json`
  - resumen:
    - `n_households = 293,809`
    - `n_assigned_households = 293,809`
    - `n_manzent_features = 3,202`
    - `n_zona777_features = 111`
- Variables nuevas disponibles en la salida `ZONA777`:
  - conteos:
    - `n_ocupado_15mas`
    - `n_desocupado_15mas`
    - `n_fuera_fuerza_trabajo_15mas`
    - `n_dependiente`
    - `n_independiente`
    - `n_cine18_primaria`
    - `n_cine18_secundaria`
    - `n_cine18_terciaria_maestria_doctorado`
  - promedios / shares:
    - `prom_escolaridad18_micro`
    - `share_ocupado_15mas_micro`
    - `share_fuera_fuerza_trabajo_15mas_micro`
    - `share_dependiente_micro`
    - `share_independiente_micro`
    - `share_cine18_primaria_micro`
    - `share_cine18_secundaria_micro`
    - `share_cine18_terciaria_micro`

## 2026-04-12 (EDA reproducible para variables `ZONA777` derivadas de microdatos)
- Se creó el notebook:
  - [`02_eda/eda_censo2024_microdata_zona777.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_censo2024_microdata_zona777.qmd)
- Qué cubre:
  - inventario del output nuevo;
  - sanidad básica (`min/max`, nulls, fuera de rango);
  - zonas problemáticas;
  - comparación con `prom_escolaridad18`, `share_discapacidad` y `share_analfabet` del Censo agregado tradicional;
  - mapas de educación y laboral/estatus;
  - matriz de correlación del bloque nuevo;
  - shortlist preliminar de variables a llevar al modelo.
- Se persistió el piloto dentro del repo para que el notebook no dependa de `/tmp`:
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_manzent_features.parquet`
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_zona777_features.parquet`
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_zona777_summary.json`
- Resumen del piloto persistido:
  - `111` zonas `ZONA777`
  - `30` columnas en el parquet final `ZONA777`
  - ejemplos de variables nuevas:
    - `prom_escolaridad18_micro`
    - `share_cine18_terciaria_micro`
    - `share_dependiente_micro`

## 2026-02-17 (feedback profesora aplicado)
- Decisión metodológica para integración socio-demo en modelos de buffers:
  - Probar **dos variantes**: (a) solo origen, (b) OD (origen + destino).
  - Priorizar análisis/reporting de **solo origen** como baseline principal.
- Esta decisión se alinea con el modelo principal de buffers: OD + Option1 + V2.

## 2026-01-23
- Zonas777 shapefile path (user provided):
  - /Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp
- Preference: most disaggregated spatial level (manzana/entidad) if possible; likely evaluate origin-only and OD joins.

### Sources identified
- INE communiqué (2025-12-16): base manzana–entidad + cartografía censal; 189 variables; official portals censo2024.cl / ine.gob.cl.
- Cartografía Censo 2024 (geoparquet) direct download (from open data link):
  - https://storage.googleapis.com/bktdescargascenso2024/Cartografia/GEOPARQUET/Cartografia_censo2024_Pais.zip
  - Size (HEAD): ~794,658,978 bytes (~757 MB)

### ArcGIS Feature Service (microdatos/manzana‑entidad)
- ArcGIS item: “Microdatos Censo 2024” (public)
- FeatureServer URL:
  - https://services.arcgis.com/r7t1P5pnkoOLRdhr/arcgis/rest/services/Microdatos_Censo_2024_v2/FeatureServer
- Layers:
  - 0: Manzanas
  - 1: Manzanas‑entidades
- Layer 1 fields: 212 fields. Example socio‑demo fields (counts/means):
  - n_edad_0_5, n_edad_6_13, n_edad_14_17, n_edad_18_24, n_edad_25_44, n_edad_45_59, n_edad_60_mas, prom_edad
  - n_inmigrantes, n_pueblos_orig, n_afrodescendencia, n_lengua_indigena, n_discapacidad
  - prom_escolaridad18, n_ocupado, n_desocupado, n_fuera_fuerza_trabajo
  - n_hog, prom_per_hog, n_hog_unipersonales, n_hog_60, n_hog_menores
  - n_serv_internet_fija, n_serv_internet_movil, n_internet, n_serv_compu, n_serv_tel_movil
  - n_vp_ocupada, n_viv_hacinadas, n_viv_irrecuperables, n_hog_allegados
  - n_fuente_agua_publica, n_serv_hig_alc_dentro, n_fuente_elect_publica, n_basura_servicios

### Caveat
- ArcGIS item description suggests geometry may be based on Censo 2017 boundaries; needs verification before final use.

## 2026-01-25
- Downloaded cartography geoparquet ZIP:
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/Cartografia_censo2024_Pais.zip
- ZIP contents (geoparquet layers):
  - Cartografia_censo2024_Pais_Zonal.parquet
  - Cartografia_censo2024_Pais_Aldeas.parquet
  - Cartografia_censo2024_Pais_Comunal.parquet
  - Cartografia_censo2024_Pais_Distrital.parquet
  - Cartografia_censo2024_Pais_Entidades.parquet
  - Cartografia_censo2024_Pais_Limite_Urbano.parquet
  - Cartografia_censo2024_Pais_Localidades.parquet
  - Cartografia_censo2024_Pais_Manzanas.parquet
  - Cartografia_censo2024_Pais_Provincial.parquet
  - Cartografia_censo2024_Pais_Regional.parquet
  - Diccionario_variables_geograficas_CPV24.xlsx
- Note: ZIP includes cartography layers and geographic dictionary; base manzana‑entidad table still pending (not inside ZIP).

## 2026-01-26
- Descargas locales (INE Censo 2024):
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/diccionario_variables_glosas_censo2024.xlsx
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip
- Base manzana‑entidad (CSV dentro del zip) incluye campos geográficos finos:
  - Ejemplo de header: CONTENEDOR_COMUNAL;COD_REGION;REGION;PROVINCIA;CUT;COMUNA;AREA_C;MANZENT;DISTRITO;COD_DISTRITO;COD_LOCALIDAD;COD_ZONA;LOCALIDAD;COD_ENTIDAD;COD_MANZANA;ENTIDAD;…
- Microdatos (hogares/personas/viviendas) muestran solo nivel región/provincia/comuna (no manzana/entidad en el header):
  - personas: id_vivienda;id_hogar;id_persona;region;provincia;comuna;…
  - hogares: id_vivienda;id_hogar;region;provincia;comuna;…
  - viviendas: id_vivienda;region;provincia;comuna;…
- Diccionario de variables: hojas disponibles en XLSX: Dicionario, temáticas, Glosas_variables_geográficas, DPA, estructura geográfica.
- Cartografía ZIP contiene parquet de Manzanas y Entidades (a extraer para spatial join):
  - Cartografia_censo2024_Pais_Manzanas.parquet
  - Cartografia_censo2024_Pais_Entidades.parquet

## 2026-01-26 (variable shortlist proposal)
- Proposed variable groups for Zonas777 aggregation (from base manzana‑entidad; exact names to verify in diccionario):
  - Población: n_per, n_hombres, n_mujeres; edades n_edad_0_5, n_edad_6_13, n_edad_14_17, n_edad_18_24, n_edad_25_44, n_edad_45_59, n_edad_60_mas; prom_edad.
  - Migración/etnia: n_inmigrantes, n_pueblos_orig, n_afrodescendencia, n_lengua_indigena.
  - Discapacidad: n_dificultad_* (ver/oir/mover/recordar/etc.).
  - Educación: prom_escolaridad18 (si aplica).
  - Trabajo: n_ocupado, n_desocupado, n_fuera_fuerza_trabajo.
  - Hogares: n_hog, prom_per_hog, n_hog_unipersonales, n_hog_60, n_hog_menores.
  - Vivienda: n_vp_ocupada, n_viv_hacinadas, n_viv_irrecuperables, n_hog_allegados.
  - Servicios: n_serv_internet_fija, n_serv_internet_movil, n_internet, n_serv_compu, n_serv_tel_movil.
  - Infraestructura: n_fuente_agua_publica, n_serv_hig_alc_dentro, n_fuente_elect_publica, n_basura_servicios.
- Aggregation defaults (to confirm):
  - Counts: sum over manzana/entidad within Zonas777.
  - Means: weighted by n_per (or n_hog) when possible; otherwise simple mean.
  - Shares: derived after summing counts (e.g., share_internet = n_internet / n_hog; share_hacinamiento = n_viv_hacinadas / n_vp_ocupada; share_inmigrantes = n_inmigrantes / n_per).

## 2026-01-26 (diccionario export)
- Exported full variable dictionary to CSV for inspection:
  - tmp/censo2024/diccionario_variables_glosas_censo2024.csv (columns: Temática, Variable, Tipo de variable, Descripción, Universo; 212 rows)

## 2026-01-26 (variables confirmed)
- User‑selected variable list checked against dictionary: all present (no missing).
- Variables + universo (per diccionario) captured for reference (see tmp/censo2024/diccionario_variables_glosas_censo2024.csv).

## 2026-01-26 (doc)
- Created variable dictionary doc: `docs/diccionario_censo2024_vars.md` (selected variables with descriptions/universe).

## 2026-01-26 (spatial join decisions)
- Zonas777 shapefile has no CRS; bounds match Santiago lat/lon. We will **assign EPSG:4674 (SIRGAS 2000)** to align with Censo 2024 cartography CRS.
- Join strategy:
  1) Base manzana‑entidad (CSV) ↔ Entidades cartography (parquet) via **ID_ENTIDAD** (primary key).
  2) Spatial join Entidades → Zonas777 using **centroid within** as default.
  3) Diagnostics to compute:
     - % entidades whose centroid falls outside Zonas777
     - % entidades intersecting multiple Zonas777
  4) If diagnostics show high mismatch, switch to **area‑weighted overlay** instead of centroid assignment.

## 2026-01-26 (implementation)
- Added script: `lib/censo2024_zona777.py` (join base manzana‑entidad + Entidades cartography → Zonas777, centroid join, diagnostics, aggregation).
- Added notebook: `02_eda/eda_censo2024_zona777.qmd` (runs script and inspects outputs).
- Outputs directory: `02_eda/tmp/censo2024_zona777/`.

## 2026-01-26 (run diagnostics)
- Initial centroid join run (national entidades vs Zonas777) returned:
  - pct_centroid_outside_zonas777 = 0.9951
  - pct_entities_intersect_multiple_zonas777 = 0.0021
- Interpretation: expected high outside because Censo entidades are national while Zonas777 cover Santiago only. Need to filter entities to Zonas777 extent (bbox/intersection or RM) before diagnostics/aggregation.

## 2026-01-26 (filter strategy)
- Implemented filter_mode in `lib/censo2024_zona777.py`: none | bbox | region | both.
- Notebook now runs **bbox** and **region** modes and writes separate outputs:
  - `censo2024_zona777_agg_bbox.parquet` + diagnostics
  - `censo2024_zona777_agg_region.parquet` + diagnostics

## 2026-01-26 (filter: intersects)
- Added `filter_mode=intersects` to keep only Entidades that intersect Zonas777 polygons (more precise than bbox/region filters).
- Notebook updated to run bbox, region, and intersects modes; writes separate outputs.

## 2026-01-26 (filter diagnostics results)
- bbox filter: pct_centroid_outside=0.7186, pct_multi_zone=0.1194
- region filter: pct_centroid_outside=0.9329, pct_multi_zone=0.0287
- intersects filter: pct_centroid_outside=0.2835, pct_multi_zone=0.3041
- Interpretation: intersects is the only viable prefilter; multi-zone rate is high → centroid assignment likely biased; area-weighted overlay recommended.

## 2026-01-26 (area-weighted overlay)
- Added area-weighted overlay option (`area_weighted=True`) using Entidades × Zonas777 intersection (UTM 19S for area).
- Notebook now runs `intersects_area` and writes:
  - `censo2024_zona777_agg_intersects_area.parquet`
  - `censo2024_zona777_diag_intersects_area.json`

## 2026-01-26 (ID_ENTIDAD normalization)
- Added normalization for ID_ENTIDAD (strip non-digits) in both base CSV and cartography to fix join mismatches.
- Added COD_REGION to KEY_COLS to allow filtering base by region if needed.

## 2026-01-26 (join mismatch debug + cartography switch)
- Found join mismatch using **Entidades** cartography:
  - `Cartografia_censo2024_Pais_Entidades.parquet` has ~28k rows (too small for manzana coverage).
  - Join overlap with base MANZENT very low (~6% in sample; ~4% in RM). ID_ENTIDAD overlap ~0%.
- Checked **Manzanas** cartography:
  - `Cartografia_censo2024_Pais_Manzanas.parquet` has ~216k rows.
  - Join overlap with base MANZENT is high (≈85% overall; ≈96% in RM sample).
- Decision: **switch to Manzanas cartography and join key MANZENT** (not Entidades/ID_ENTIDAD).
- Updates implemented:
  - `JoinConfig` now uses `carto_parquet` (manzanas) and default join key `MANZENT`.
  - Added join coverage diagnostics:
    - `pct_base_keys_in_carto`
    - `pct_carto_keys_in_base`
    - `pct_rows_with_n_per` (after merge)
  - Enforced numeric casting in `_aggregate_by_zona` to avoid string arithmetic errors.
- Notebook updated to use `Cartografia_censo2024_Pais_Manzanas.parquet`.

## 2026-01-26 (run results with Manzanas cartography)
- Re‑ran `02_eda/eda_censo2024_zona777.qmd` with Manzanas cartography.
- Diagnostics (coverage now OK):
  - **bbox**: pct_centroid_outside=0.0385, pct_multi_zone=0.1636, pct_base_keys_in_carto=1.0, pct_carto_keys_in_base=0.7585, pct_rows_with_n_per=0.7585
  - **region**: pct_centroid_outside=0.1589, pct_multi_zone=0.1431, pct_base_keys_in_carto=0.9596, pct_carto_keys_in_base=0.7555, pct_rows_with_n_per=0.7555
  - **intersects**: pct_centroid_outside=0.00128, pct_multi_zone=0.1699, pct_base_keys_in_carto=1.0, pct_carto_keys_in_base=0.7610, pct_rows_with_n_per=0.7610
  - **intersects_area**: same coverage as intersects (area‑weighted overlay).
- Aggregated outputs now contain non‑zero counts and shares (example ZONA777 rows show plausible totals).
- Row counts from outputs (after re-run, all shares summarized):
  - bbox/region/intersects: 801 zonas
  - intersects_area: 803 zonas

## 2026-01-26 (decision)
- Selected **intersects_area** as the default socio‑demographic output for Zonas777.

## 2026-01-26 (alias + sanity)
- Created alias (final output):
  - `02_eda/tmp/censo2024_zona777/censo2024_zona777_agg_final.parquet`
- Sanity checks on shares (intersects_area):
  - Summary: `02_eda/tmp/censo2024_zona777/censo2024_zona777_sanity_intersects_area.csv`
  - Examples >1: `02_eda/tmp/censo2024_zona777/censo2024_zona777_sanity_examples_gt1.json`
  - Shares >1 appear in:
    - `share_serv_tel_movil` (n_gt_1=647, max≈7.04)
    - `share_internet` (n_gt_1=370, max≈7.01)
    - `share_serv_compu` (n_gt_1=26, max≈6.19)
    - `share_ocupado` (n_gt_1=4, max≈3.06)
  - Interpretation for now: likely multiple services/devices per hogar (numerator not a strict subset of denominator) plus area‑weighted rounding; keep as‑is and document.
  - In intersects_area summary: share_internet and share_serv_tel_movil show max > 1 (up to ~7), consistent with multi‑service counts; share_ocupado max ~3.06 (likely definition/denominator effects).

## 2026-01-26 (notebook path fix)
- Updated `02_eda/eda_censo2024_zona777.qmd` to compute `OUT_DIR` from `PROJECT_ROOT` to avoid writing under `02_eda/02_eda/...` when executed from the `02_eda/` folder.

## 2026-01-26 (buffers join scaffold)
- Added script: `lib/censo2024_join_buffers.py` to join Censo Zonas777 aggregates onto buffers.
  - Buffer A (inicio) → adds `censo_*` columns (join by zona_inicio_viaje).
  - Buffer OD → adds `censo_o_*` and `censo_d_*` columns (join by zona_inicio_viaje/zona_fin_viaje).
  - Outputs to `02_eda/tmp/buffers_zona777_censo2024/`.
- Added section to `02_eda/eda_buffers_zona777_tipo_pago.qmd` to run the join and print diagnostics.

## 2026-01-26 (buffers join results)
- Join outputs (2025‑W17):
  - Inicio: 2,389 filas; `pct_missing_censo_inicio` ≈ 0.00628
    - `02_eda/tmp/buffers_zona777_censo2024/buffers_zona777_inicio_tipo_pago_2025-W17_censo.parquet`
  - OD: 473,035 filas; `pct_missing_censo_origen` ≈ 0.00338; `pct_missing_censo_destino` ≈ 0.00224
 - `02_eda/tmp/buffers_zona777_censo2024/buffers_zona777_od_tipo_pago_2025-W17_censo.parquet`

## 2026-02-27 (model integration — origin first)
- Se integró Censo final (`censo2024_zona777_agg_final.parquet`) al pipeline de modelamiento en:
  - `03_models/05_nested_logit_od_buffers.qmd`
- Flujo agregado:
  - Join por `zona_inicio_viaje` (origen) sobre `Option1 V2`.
  - Variables socio seleccionadas: `prom_edad`, `prom_escolaridad18`, `share_inmigrantes`, `share_ocupado`, `share_internet`, `share_hacinamiento`.
  - Estimación nueva: `Option1 V2 + socio origen` (betas `B_SOC_O_*`).
  - Celda de comparación objetiva baseline vs socio-origen.

## 2026-01-26 (mini‑EDA buffers + missing zonas)
- Added mini‑EDA section to `02_eda/eda_buffers_zona777_tipo_pago.qmd`:
  - Summaries (mean/median) for 5 Censo vars by `tipo_pago` for Buffer A and Buffer OD (origen/destino).
  - Lists of missing zonas where `censo_n_per` is null (inicio, od origen, od destino).
 - Observed: Buffer A summaries are identical across tipo_pago because Censo is joined at zona-level and the summary is unweighted; each zona appears once per tipo_pago. Differences appear in Buffer OD (origen/destino) due to different OD composition.
 - Suggestion recorded: use **n_viajes-weighted** summaries if we want socio‑demo differences by tipo_pago.

## 2026-01-26 (prom_edad scale check)
- `prom_edad` in base is stored as **string with decimal comma** (e.g., `\"38,3\"`), so naive `pd.to_numeric` yields NaN for many rows.
- This explains the low `prom_edad` (~3.9) seen in summaries.
- Fix implemented: in `_read_base_csv`, for variable columns, replace comma → dot before `pd.to_numeric`.
- Action: re-run `02_eda/eda_censo2024_zona777.qmd` and the buffer mini‑EDA to refresh prom_edad stats.

## 2026-01-26 (join key switch)
- ID_ENTIDAD in base appears in scientific notation (e.g., 1,10101E+11). Switched join key to **MANZENT** (present in base + cartography) for reliable matching.
- Added join_key support in script; normalizes join key by stripping non-digits.

## 2026-01-26 (key normalization v2)
- Updated key normalization to handle scientific notation (e.g., 1.340201e+13) and decimal commas by converting to numeric then formatting as integer string.

## 2026-01-26 (numeric casting)
- Base variable columns now cast to numeric via `pd.to_numeric(errors='coerce')` to avoid string division errors during aggregation.

- 2026-02-27: En `02_eda/eda_censo2024_zona777.qmd` se agregaron celdas para (i) inventariar variables disponibles del parquet final y (ii) listar explicitamente las 6 variables socio actualmente usadas en `Option1 V2 + socio origen`.

## 2026-04-12 (split CINE-11 terciario)
- Se refinó la recodificación educativa adulta derivada desde `cine11` usando el diccionario oficial de microdatos Censo 2024:
  - `share_cine18_terciaria_corta_micro` = `cine11 == 8`
  - `share_cine18_universitaria_micro` = `cine11 == 9`
  - `share_cine18_postgrado_micro` = `cine11 in [10, 11]`
- Se mantuvo `share_cine18_terciaria_micro` como agregado de referencia (`8+9+10+11`) para comparar contra la versión compacta anterior.
- Se regeneró el piloto `softmax_tau003` en:
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/`
- El notebook `02_eda/eda_censo2024_microdata_zona777.qmd` fue actualizado para:
  - dejar de tratar `prom_escolaridad18_micro` como share;
  - comparar la nueva desagregación `terciaria corta / universitaria / postgrado`;
  - actualizar mapas, matriz de correlación y shortlist preliminar.

## 2026-04-14 (EDA preliminar de variables `ZONA777` derivadas desde microdatos spatialized)
- Se consolidó el piloto operativo:
  - `microdatos comunales -> softmax_tau003 -> MANZENT -> ZONA777`
- Artefactos principales del piloto:
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_zona777_features.parquet`
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_manzent_features.parquet`
  - `02_eda/tmp/censo2024_microdata_zona777/pilot_softmax_tau003/censo2024_microdata_zona777_summary.json`
- Notebook de auditoría/EDA:
  - [`02_eda/eda_censo2024_microdata_zona777.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_censo2024_microdata_zona777.qmd)

### Sanidad básica del output `ZONA777`
- El piloto quedó con:
  - `111` zonas `ZONA777`
  - `36` columnas en el agregado final
  - `3202` filas `MANZENT`
- Hallazgo de calidad:
  - todas las shares auditadas quedaron en rango `[0,1]`, sin `nulls`;
  - `prom_escolaridad18_micro` quedó con rango plausible:
    - `min ~= 7.76`
    - `max ~= 16.17`

### Hallazgos preliminares del bloque educación
- `share_cine18_universitaria_micro` quedó casi pegada a la dimensión educativa principal ya conocida:
  - `corr(prom_escolaridad18_micro, share_cine18_universitaria_micro) ~= 0.981`
  - `corr(prom_escolaridad18, share_cine18_universitaria_micro) ~= 0.909`
- Lectura:
  - esta variable funciona como la mejor proxy interpretable de **capital humano alto general**;
  - puede reemplazar interpretativamente a `prom_escolaridad18`, pero no conviene meterlas juntas de entrada.
- `share_cine18_postgrado_micro` mostró una señal más específica:
  - `corr(prom_escolaridad18_micro, share_cine18_postgrado_micro) ~= 0.806`
  - `corr(prom_escolaridad18, share_cine18_postgrado_micro) ~= 0.790`
  - baja asociación con el bloque laboral:
    - `corr(share_ocupado_15mas_micro, share_cine18_postgrado_micro) ~= 0.114`
    - `corr(share_fuera_fuerza_trabajo_15mas_micro, share_cine18_postgrado_micro) ~= 0.011`
    - `corr(share_dependiente_micro, share_cine18_postgrado_micro) ~= -0.067`
    - `corr(share_independiente_micro, share_cine18_postgrado_micro) ~= 0.038`
- Lectura:
  - `postgrado` parece capturar una dimensión más selectiva de **élite educativa / estatus alto**, no solo escolaridad promedio.
- `share_cine18_terciaria_corta_micro` quedó más separada del gradiente educativo tradicional:
  - `corr(prom_escolaridad18_micro, share_cine18_terciaria_corta_micro) ~= 0.417`
  - `corr(prom_escolaridad18, share_cine18_terciaria_corta_micro) ~= 0.301`
  - y muy alineada al bloque laboral:
    - `corr(share_ocupado_15mas_micro, share_cine18_terciaria_corta_micro) ~= 0.862`
    - `corr(share_dependiente_micro, share_cine18_terciaria_corta_micro) ~= 0.835`
    - `corr(share_fuera_fuerza_trabajo_15mas_micro, share_cine18_terciaria_corta_micro) ~= -0.888`
    - `corr(share_independiente_micro, share_cine18_terciaria_corta_micro) ~= -0.828`
- Lectura:
  - `terciaria_corta` no parece solo “más educación”, sino una dimensión más cercana a **formación técnica / inserción laboral formal**.

### Hallazgos preliminares del bloque laboral
- `share_ocupado_15mas_micro` y `share_fuera_fuerza_trabajo_15mas_micro` son casi espejo:
  - `corr ~= -0.980`
- `share_dependiente_micro` y `share_independiente_micro` son casi espejo:
  - `corr ~= -0.997`
- Juicio preliminar:
  - para primeras pruebas de modelo no conviene cargar todo el bloque laboral;
  - si se quiere una sola candidata laboral, `share_independiente_micro` parece más informativa que `share_dependiente_micro` o `share_ocupado_15mas_micro`.

### Lectura sustantiva provisional
- El split educativo de `CINE-11` permitió separar tres cosas que antes estaban mezcladas:
  - `share_cine18_universitaria_micro`:
    - proxy de **capital humano alto general**
  - `share_cine18_postgrado_micro`:
    - proxy de **élite educativa / estatus alto**
  - `share_cine18_terciaria_corta_micro`:
    - proxy de una dimensión distinta, más cercana a **formación técnica / inserción laboral**
- Esto es más informativo que seguir usando solo `prom_escolaridad18`, porque permite diferenciar entre educación alta general, educación muy alta y educación técnica.

### Fiabilidad y límites de estas variables
- Estas variables **no** son observaciones directas a nivel `ZONA777`;
  - son proxies derivadas desde una población sintética spatialized:
    - `comuna -> MANZENT -> ZONA777`
- La confianza metodológica actual se apoya en:
  - mejor desempeño frente a la baseline aleatoria;
  - validación contra targets finos observados;
  - rangos plausibles y patrones espaciales coherentes;
  - correlaciones que cuentan historias sustantivamente razonables.
- Límite explícito:
  - deben presentarse como **proxies spatialized validadas**, no como mediciones observadas directamente en `ZONA777`.

### Implicancia para modelación
- No conviene meter juntas desde el inicio variables que representan la misma dimensión:
  - `prom_escolaridad18`
  - `prom_escolaridad18_micro`
  - `share_cine18_universitaria_micro`
  - `share_cine18_terciaria_micro`
- Prioridad preliminar para próximas corridas del modelo:
  1. `share_cine18_universitaria_micro`
  2. `share_cine18_terciaria_corta_micro`
  3. `share_cine18_postgrado_micro`
  4. `share_independiente_micro` como laboral secundaria
- Estrategia acordada:
  - probarlas **de a poco**, no todas juntas;
  - primero como reemplazo o competidoras de `prom_escolaridad18`;
  - luego, si la interpretación se mantiene estable, evaluar combinaciones controladas.

### Integración en notebook de modelos `08`
- Se decidió implementar la primera ronda en Biogeme, no en Larch, dentro de:
  - `03_models/08_nested_logit_enriched_interannual_censo.qmd`
- El notebook `08` quedó extendido con una ruta paralela `Censo + microdatos spatialized`:
  - construcción del parquet full `ZONA777` si no existe:
    - `02_eda/tmp/censo2024_microdata_zona777/full_softmax_tau003/censo2024_microdata_zona777_features.parquet`
  - construcción de un `model-ready` específico para microdatos;
  - estandarización de variables microdato sobre las zonas efectivamente usadas en la muestra;
  - construcción de una muestra de estimación combinada:
    - `pooled_2024_2025-estimation-sample5pct-censo4-micro.parquet`
- Variables microdato incluidas en esta primera ronda:
  - `share_cine18_universitaria_micro`
  - `share_cine18_terciaria_corta_micro`
  - `share_cine18_postgrado_micro`
  - `share_independiente_micro`
- Especificaciones añadidas al notebook:
  - `mnl_interannual_micro_share_cine18_universitaria`
  - `mnl_interannual_micro_share_cine18_terciaria_corta`
  - `mnl_interannual_micro_share_cine18_postgrado`
  - `mnl_interannual_censo_escolaridad_micro_terciaria_corta`
  - `mnl_interannual_censo_escolaridad_micro_postgrado`
- Criterio mantenido:
  - no empezar combinando `prom_escolaridad18` con `share_cine18_universitaria_micro`, por su alta redundancia;
  - sí probar primero cada proxy nueva por separado y luego combinaciones controladas con `prom_escolaridad18`.
- Validación de edición:
  - los bloques Python del `qmd` fueron chequeados sintácticamente y compilan sin errores antes de ejecutar la corrida completa.

## 2026-04-15 — Primera ronda de modelación: resultados y observaciones

### Modelos estimados y fit comparado

| Modelo | Params | LL | AIC | LRT vs baseline | Gradiente |
|---|---|---|---|---|---|
| `mnl_interannual_censo_baseline` | 30 | -467,338.7 | 934,737 | — | 9.4 |
| `mnl_interannual_micro_share_cine18_universitaria` | 32 | -464,686.6 | 929,437 | 5,304 | 8.8 |
| `mnl_interannual_micro_share_cine18_postgrado` | 32 | -465,082.2 | 930,228 | 4,513 | 7.8 |
| `mnl_interannual_censo_prom_escolaridad18` | 32 | -464,865.3 | 929,795 | 4,947 | 13.5 |
| `mnl_interannual_micro_share_cine18_terciaria_corta` | 32 | -466,720.3 | 933,505 | 1,237 | 6.9 |
| `mnl_interannual_censo_escolaridad_micro_terciaria_corta` | 34 | -464,718.2 | 929,504 | 5,241 | ⚠️ 241 |
| `mnl_interannual_censo_escolaridad_micro_postgrado` | 34 | -464,705.6 | 929,479 | 5,266 | ⚠️ 564 |
| `mnl_interannual_micro_universitaria_terciaria_corta` | 34 | -464,668.8 | 929,406 | 5,340 | ⚠️ 1,926 |

Baseline = modelo enriquecido de notebook 07 con controles de transporte, oferta, demanda y `DUMMY_ANIO_2025`. N=933,276.

### Observaciones sobre las variables micro de educación

**`share_cine18_universitaria_micro`:**
- Coeficiente QR_RED: +0.474, t=67.98; QR_OTHER: +0.087, t=26.43
- Significativa en ambas alternativas. Efecto asimétrico: QR_RED captura ~5.5x más que QR_OTHER
- Mejor fit individual entre todas las variables probadas (AIC 929,437 vs baseline 934,737)
- Supera a `prom_escolaridad18` en AIC por 358 puntos con igual número de parámetros

**`share_cine18_postgrado_micro`:**
- Coeficiente QR_RED: +0.342, t=66.73; QR_OTHER: +0.064, t=24.03
- Misma dirección que universitaria. Fit menor (ΔAIC=791 respecto a universitaria)
- Patrón de movimiento de coeficientes de transporte similar al de universitaria

**`share_cine18_terciaria_corta_micro`:**
- Coeficiente QR_RED: -0.226, t=-33.84; QR_OTHER: -0.042, t=-13.15
- Signo opuesto a universitaria y postgrado
- Fit individual mucho más débil (LRT=1,237 vs 5,304 de universitaria)

**`prom_escolaridad18` (agregado oficial):**
- Coeficiente QR_RED: +0.552, t=62.86; QR_OTHER: +0.082, t=21.59
- Misma dirección que universitaria. Coeficiente mayor en valor absoluto, pero fit peor
- Gradiente 13.5 — aceptable pero levemente más alto que los modelos micro

### Observaciones sobre modelos combinados

**`prom_escolaridad18` + terciaria corta / postgrado:**
- Ambos muestran problemas serios de convergencia numérica (gradient norm 241 y 564 respectivamente)
- Las variables microdato y el agregado oficial comparten la misma población subyacente → superficie de likelihood plana
- Los coeficientes reportados en estos modelos deben interpretarse con mucha cautela y no usarse como evidencia principal

**`share_cine18_universitaria_micro` + `share_cine18_terciaria_corta_micro`:**
- Gradient norm = 1,926 — el más alto de todos
- A pesar de que ambas tienen signos opuestos (esperado como indicador de baja colinealidad), el combo muestra convergencia numérica muy débil
- En el combo, terciaria corta pierde ~87% de su efecto: QR_RED pasa de -0.226 (sola) a -0.030 (en combo)
- El ΔAIC sobre universitaria sola es solo 31 puntos con 2 parámetros extra y no-convergencia

### Observaciones sobre movimiento de otros coeficientes al incorporar educación

Nota: los patrones a continuación son más pronunciados en los modelos con variables de fuerte corrección (universitaria, postgrado, escolaridad18). Terciaria corta sola, por ser el corrector más débil, produce movimientos menores o no produce el patrón.

- `LOG_DEMAND` QR_RED: +0.128 en baseline → flipa a negativo en modelos con universitaria (-0.073), postgrado (-0.088), escolaridad18 (-0.047) y todos los combos. Con terciaria corta sola se atenúa a +0.046 pero **no flipa** (permanece positivo)
  - Interpretación: en baseline, LOG_DEMAND absorbía parte del efecto de composición socioeducativa zonal; la corrección depende de la fuerza de la variable educativa
- `METRO_LINE_COUNT` QR_RED: -0.053 baseline → varía ampliamente (+0.008 a +0.221) según especificación educativa; con terciaria corta sola sube a +0.167
  - El parámetro es inestable entre especificaciones y no se observa dirección consistente
- `NO_LAB` QR_RED: 0.302 baseline → con universitaria/postgrado/combos cae a 0.025-0.090 e incluso pierde significancia; con terciaria corta sola permanece en 0.191 (significativo)
  - Sugiere que el efecto de franja no-laboral para QR_RED estaba parcialmente capturando heterogeneidad socioeducativa zonal, más visible cuando la variable educativa tiene fuerza suficiente
- `LAB_PT` QR_RED: se atenúa al agregar educación; con universitaria/postgrado/escolaridad18/combos cae a 0.191-0.283; con terciaria corta sola permanece en 0.380 (atenuación menor)
- `ASC_QR_RED`: se vuelve menos negativo al agregar educación; con universitaria/postgrado/escolaridad18/combos oscila entre -3.5 y -3.9; con terciaria corta sola permanece en -4.233 (cerca del baseline de -4.490)

### Observación sobre asimetría QR_RED vs QR_OTHER

En todos los modelos con variables de educación, el efecto sobre QR_RED es aproximadamente 5–7x mayor que sobre QR_OTHER (rango observado: 5.3x para postgrado, 5.4x para universitaria y terciaria corta, 6.7x para escolaridad18). Esta asimetría es consistente independientemente de la variable educativa usada.

---

## 2026-04-16 — Segunda ronda: variables censo agregadas (share_hacinamiento, share_internet)

### Modelos estimados y fit comparado

| Modelo | Params | LL | AIC | LRT vs baseline | Gradiente |
|---|---|---|---|---|---|
| `mnl_interannual_censo_baseline` | 30 | -467,338.7 | 934,737 | — | 9.4 |
| `mnl_interannual_micro_share_cine18_universitaria` | 32 | -464,686.6 | 929,437 | 5,304 | 8.8 |
| `mnl_interannual_censo_prom_escolaridad18` | 32 | -464,865.3 | 929,795 | 4,947 | 13.5 |
| `mnl_interannual_micro_share_cine18_postgrado` | 32 | -465,082.2 | 930,228 | 4,513 | 7.8 |
| `mnl_interannual_censo_share_internet` | 32 | -465,843.5 | 931,751 | 2,990 | 7.8 |
| `mnl_interannual_censo_share_hacinamiento` | 32 | -466,449.9 | 932,964 | 1,778 | 4.5 |
| `mnl_interannual_micro_share_cine18_terciaria_corta` | 32 | -466,720.3 | 933,505 | 1,237 | 6.9 |

Todos los LRT con 2 df son altamente significativos (χ² crítico al 0.001 = 13.8). Gradientes todos aceptables (< 20).

### Observaciones: `share_hacinamiento`

- Coeficiente QR_RED: **-0.324**, t=-36.5, p≈0; QR_OTHER: **-0.009**, t=-2.76, p=0.006
- Signo negativo en ambas alternativas: más hacinamiento → menor adopción QR. Coherente con su interpretación como proxy inverso de ingreso.
- **Asimetría extrema**: efecto QR_RED es ~36x el efecto QR_OTHER (0.324 / 0.009). Hacinamiento predice fuertemente la adopción de pago RED, pero su efecto en QR_OTHER es prácticamente nulo.
- Quinto mejor fit individual entre variables convergentes (AIC=932,964 vs baseline 934,737; ΔAIC=-1,773).
- Mejor que terciaria corta (AIC=933,505) pero notablemente peor que postgrado (AIC=930,228).

**Movimiento de otros coeficientes:**
- `ASC_QR_RED`: -4.535 — más negativo que baseline (-4.490) y que todos los modelos con variables de educación (−3.5 a −4.233). Comportamiento opuesto al patrón educativo: las variables positivas (educación) volvían el ASC menos negativo; hacinamiento (predictor negativo) lo vuelve más negativo.
- `LOG_DEMAND` QR_RED: +0.051, t=5.14 — atenuado respecto al baseline (+0.128) pero no flipa. Comportamiento similar al de terciaria corta sola (+0.046); hacinamiento es un corrector débil del confounding demanda-composición.
- `METRO_LINE_COUNT` QR_RED: +0.026, t=0.95, p=0.34 — no significativo. Patrón de inestabilidad consistente con lo observado en los modelos educativos.
- `NO_LAB` QR_RED: +0.216 — entre el baseline (0.302) y el rango universitaria/postgrado (0.025–0.090); más cercano al patrón de corrector débil (cf. terciaria corta: 0.191).
- `LAB_PT` QR_RED: +0.406 — similar a terciaria corta sola (0.380), lejos del rango de los correctores fuertes (0.191–0.283). Confirma comportamiento de corrector débil.

### Observaciones: `share_internet`

- Coeficiente QR_RED: **+0.633**, t=+43.5, p≈0; QR_OTHER: **+0.088**, t=+17.2, p≈0
- Signo positivo en ambas alternativas: más acceso a internet → mayor adopción QR.
- **Asimetría**: ~7.2x (0.633 / 0.088). Magnitud consistente con el rango educativo (5.3x–6.7x).
- Cuarto mejor fit individual entre variables convergentes (AIC=931,751; ΔAIC=-2,986), tras universitaria, escolaridad18 y postgrado. Queda 1,523 puntos de AIC por encima de postgrado (AIC=930,228).
- Coeficiente QR_RED (+0.633) es el más alto de todos los modelos individuales, superando a universitaria (+0.474) y escolaridad18 (+0.552).

**Movimiento de otros coeficientes:**
- `ASC_QR_RED`: -4.334 — menos negativo que baseline (-4.490) y que hacinamiento (-4.535); más negativo que terciaria corta (-4.233) y los modelos educativos fuertes (−3.5 a −3.9). Posición intermedia coherente con fit de rango similar.
- `LOG_DEMAND` QR_RED: +0.021, t=2.11, p=0.035 — al borde de la significancia, casi neutro. Más atenuado que hacinamiento (+0.051) y terciaria corta (+0.046); más cercano al flip observado en postgrado y superiores. Internet es corrector más fuerte del confounding de demanda que hacinamiento, aunque no llega a flipa a negativo como universitaria/postgrado/escolaridad18.
- `METRO_LINE_COUNT` QR_RED: **-0.069**, t=-2.53, p=0.011 — significativo negativo. Notable: en todos los modelos anteriores este parámetro fue inestable y mayoritariamente positivo o no significativo. Con share_internet se vuelve significativamente negativo. Posible correlación espacial entre cobertura de internet y densidad de líneas de metro (zonas con más metro pueden tener más o menos internet de formas no lineales).
- `METRO_LINE_COUNT` QR_OTHER: +0.069, t=5.04 — significativo positivo, casi simétrico en magnitud al QR_RED pero con signo opuesto. Patrón inusual que no aparece en los otros modelos.
- `NO_LAB` QR_RED: +0.174 — más atenuado que hacinamiento (0.216) y terciaria corta (0.191), pero aún lejos del rango universitaria/postgrado (0.025–0.090). Corrector intermedio.
- `LAB_PT` QR_RED: +0.383 — similar a terciaria corta (0.380) y hacinamiento (0.406). Atenuación moderada respecto al baseline.

### Observaciones comparadas sobre proxies de ingreso

**`share_hacinamiento`:**
- Proxy inverso de ingreso (más hacinamiento → menor renta esperada). Señal real pero débil en términos de fit.
- La asimetría extrema QR_RED/QR_OTHER (~36x) es llamativa: hacinamiento captura adopción RED pero no QR_OTHER. Una posible lectura es que los pagos QR_OTHER (canales más informales) no son sensibles a la composición socioeconómica de la zona tanto como el pago formal RED.
- No resuelve el confounding de LOG_DEMAND de forma sustancial (queda +0.051).

**`share_internet`:**
- Proxy compuesto: captura simultáneamente acceso a infraestructura digital y nivel socioeconómico. No es un proxy limpio de ingreso.
- Cuarto mejor modelo individual convergente. Queda 1,523 puntos de AIC por encima de postgrado (AIC=930,228).
- La anomalía de `METRO_LINE_COUNT` QR_RED (−0.069, significativo) sugiere que internet tiene correlaciones espaciales con la distribución de infraestructura de transporte que ninguna de las variables educativas captaba.
- El efecto QR_RED (+0.633) es el mayor de todos los modelos individuales, lo que puede reflejar que digital literacy + infraestructura de conectividad son más directamente relevantes para el pago QR (que es un acto digital) que el nivel educativo per se.

**Posición relativa respecto a variables educativas:**
- Ninguna de las dos variables de esta ronda supera a universitaria o escolaridad18 en fit.
- Internet queda entre postgrado (AIC=930,228) y hacinamiento (AIC=932,964); hacinamiento queda entre internet y terciaria corta (AIC=933,505).
- Para el objetivo de identificar un proxy de ingreso/socioeconómico: hacinamiento es más interpretable causalmente como proxy de ingreso, pero estadísticamente más débil; internet tiene mejor fit pero mezcla canales de efecto.

---

## 2026-04-16 — Cierre de etapa: comparación final `universitaria_micro` vs `prom_escolaridad18`

### Comparación final de variables candidatas principales

| Variable | Interpretación | LL | AIC | Gradiente | QR_RED | QR_OTHER |
|---|---|---|---|---|---|---|
| `prom_escolaridad18` | promedio agregado de escolaridad adulta | -464,865.3 | 929,794.6 | 13.5 | +0.552 | +0.081 |
| `share_cine18_universitaria_micro` | proporción de adultos con educación universitaria | -464,686.6 | 929,437.2 | 8.8 | +0.474 | +0.087 |

### Decisión metodológica
- Se cierra la etapa tomando `share_cine18_universitaria_micro` como **proxy principal candidata** de capital humano alto general.
- `prom_escolaridad18` se mantiene como **benchmark agregado tradicional** para comparar especificaciones.
- `share_cine18_postgrado_micro` queda como **especificación de sensibilidad**:
  - útil para testear una lectura más selectiva de élite educativa / estatus alto;
  - no reemplaza a `universitaria_micro` como variable principal.
- `share_cine18_terciaria_corta_micro` queda fuera del rol de proxy principal de ingreso/capital humano alto:
  - su interpretación es distinta, más cercana a formación técnica / estructura laboral.

### Justificación de la decisión
- La prioridad no es solo el fit, sino la combinación de:
  - interpretabilidad;
  - coherencia con la idea de “nivel educacional” sugerida como proxy;
  - estabilidad/convergencia razonable;
  - y, recién después, desempeño empírico.
- Bajo ese criterio, `share_cine18_universitaria_micro` domina a `prom_escolaridad18`:
  - es más interpretable;
  - está más cerca de la noción de “nivel educacional” por tramos;
  - muestra mejor `LL`, mejor `AIC` y mejor gradiente;
  - y mantiene signos limpios y significativos en ambas alternativas QR.

### Implicancia para la línea principal
- La siguiente integración al frente principal del modelo debería hacerse con:
  - `share_cine18_universitaria_micro` como candidata principal;
  - `prom_escolaridad18` como benchmark;
  - `share_cine18_postgrado_micro` solo como sensibilidad.

---

## 2026-04-16 — Reapertura metodológica: construir `universitaria o más`

### Motivo
- Se reabrió la definición de la proxy educativa principal por una objeción conceptual válida:
  - si el objetivo es usar **nivel académico como proxy de ingreso**, dejar `postgrado` fuera de la categoría principal puede ser metodológicamente incoherente;
  - `share_cine18_universitaria_micro` mide solo `cine11 == 9`, no “al menos universitaria”.

### Nueva definición operativa
- Se define una nueva variable adulta:
  - `n_cine18_universitaria_o_mas = cine11 in [9, 10, 11]` para personas de 18+.
- A partir de eso se deriva:
  - `share_cine18_universitaria_o_mas_micro = n_cine18_universitaria_o_mas / n_cine18_total_obs`.
- Interpretación:
  - proporción de adultos de la zona con **educación universitaria o postgrado**;
  - esto corresponde mejor a “al menos universitaria” como proxy de capital humano alto / ingreso potencial.

### Implementación realizada
- `lib/censo2024_microdata_base.py`
  - se agregó `n_cine18_universitaria_o_mas` a la agregación hogar-personas.
- `lib/censo2024_microdata_zona777.py`
  - se agregó el conteo a `MANZENT_COUNT_COLS`;
  - se derivó `share_cine18_universitaria_o_mas_micro` tanto en `MANZENT` como en `ZONA777`.
- `lib/test_censo2024_microdata_base.py`
  - se extendieron asserts para el nuevo conteo adulto.
- `lib/test_censo2024_microdata_zona777.py`
  - se extendieron asserts para la nueva share en `MANZENT` y `ZONA777`.
- `02_eda/eda_censo2024_microdata_zona777.qmd`
  - se incorporó la nueva variable al bloque de educación, correlaciones y mapas.
- `03_models/08_nested_logit_enriched_interannual_censo.qmd`
  - se incorporó al `model-ready` micro;
  - se agregó parámetro/tag `SHARE_CINE18_UNIVERSITARIA_O_MAS_MICRO_Z`;
  - se añadió una especificación MNL:
    - `mnl_interannual_micro_share_cine18_universitaria_o_mas`;
  - y su bloque de carga de resultados correspondiente.

### Validación hecha
- Tests unitarios:
  - `~/.local/share/mamba/envs/larch-env/bin/python -m unittest lib.test_censo2024_microdata_base lib.test_censo2024_microdata_zona777`
  - resultado: `5 tests OK`
- Sintaxis notebooks:
  - `02_eda/eda_censo2024_microdata_zona777.qmd` → `10` bloques Python OK
  - `03_models/08_nested_logit_enriched_interannual_censo.qmd` → `60` bloques Python OK

### Estado
- La decisión previa que favorecía `share_cine18_universitaria_micro` queda **provisional**.
- Antes de integrar una proxy educativa final al frente principal, ahora corresponde correr y evaluar:
  - `share_cine18_universitaria_o_mas_micro`
  - contra `share_cine18_universitaria_micro`
  - y contra `prom_escolaridad18`.

---

## 2026-04-16 — Cierre final: `universitaria_o_mas` reemplaza a `universitaria` exacta

### Resultado de la comparación final

| Variable | Interpretación | LL | AIC | Gradiente | QR_RED | QR_OTHER |
|---|---|---|---|---|---|---|
| `prom_escolaridad18` | promedio agregado de escolaridad adulta | -464,865.3 | 929,794.6 | 13.5 | +0.552 | +0.081 |
| `share_cine18_universitaria_micro` | proporción de adultos con educación universitaria exacta | -464,686.6 | 929,437.2 | 8.8 | +0.474 | +0.087 |
| `share_cine18_universitaria_o_mas_micro` | proporción de adultos con al menos educación universitaria | -464,717.0 | 929,498.0 | 9.9 | +0.436 | +0.081 |

### Lectura
- `share_cine18_universitaria_o_mas_micro` queda muy cerca de `share_cine18_universitaria_micro` en desempeño empírico:
  - pierde muy poco en `LL`/`AIC`;
  - mantiene signos positivos y muy significativos en `QR_RED` y `QR_OTHER`;
  - sigue superando claramente a `prom_escolaridad18`.
- La ganancia principal no es de fit, sino de **coherencia metodológica**:
  - evita dejar `postgrado` fuera del grupo de educación alta;
  - representa mejor la idea de “al menos universitaria” como proxy de ingreso/capital humano alto.

### Decisión metodológica final
- Se reemplaza la decisión provisional anterior.
- La proxy educativa principal pasa a ser:
  - `share_cine18_universitaria_o_mas_micro`
- Se mantiene:
  - `prom_escolaridad18` como benchmark explícito;
  - `share_cine18_postgrado_micro` como sensibilidad;
  - `share_cine18_universitaria_micro` como referencia desagregada útil, pero no como proxy principal final.
- Se cierra la rama educativa en este punto:
  - no seguir abriendo nuevas proxies educativas por ahora.

### Implicancia para la línea principal
- La próxima integración al frente principal del modelo debe hacerse con:
  - `share_cine18_universitaria_o_mas_micro` como variable educativa candidata;
  - `prom_escolaridad18` como benchmark explícito;
  - `share_cine18_postgrado_micro` solo como sensibilidad.
