# Capítulo 3. Materiales y métodos

## 3.1 Diseño general del estudio

Esta tesis desarrolla un estudio empírico observacional sobre la adopción de pagos QR en el transporte público de Santiago. El análisis utiliza registros pasivos de uso del sistema y los combina con información operacional y territorial para caracterizar diferencias entre `BIP` y pagos QR, estudiar perfiles de adopción a nivel tarjeta y describir el crecimiento territorial del uso QR entre 2024 y 2025.

La estrategia metodológica se organiza en dos niveles complementarios. El primer nivel corresponde a la tarjeta, donde `id_tarjeta` se utiliza como proxy operacional de usuario. Este nivel permite comparar tarjetas asociadas a `BIP`, `QR_RED` y `QR_OTHER`, construir indicadores de intensidad y temporalidad de uso, e implementar modelos preliminares de adopción. El segundo nivel corresponde a la zona `ZONA777`, donde los registros se agregan por residencia u origen de viaje para estudiar patrones territoriales y cambios interanuales en la participación QR.

El enfoque es descriptivo, predictivo e interpretativo, no causal. Los modelos y segmentaciones se usan para ordenar evidencia empírica, evaluar asociaciones y preparar hipótesis de modelamiento. No se interpreta el medio de pago como evidencia directa de motivaciones individuales, uso efectivo de aplicaciones, consulta de información en tiempo real ni preferencias subjetivas no observadas.

## 3.2 Fuentes de datos y caso de estudio

El caso de estudio corresponde al sistema de transporte público de Santiago. La base principal contiene registros observados de uso del sistema durante 2024 y 2025, con información de medio de pago, viajes asociados, fechas, franjas temporales y localización territorial. A partir de esta base se distinguen tres categorías de medio de pago: `BIP`, `QR_RED` y `QR_OTHER`.

`BIP` corresponde al medio de pago tradicional del sistema. `QR_RED` identifica pagos QR asociados al canal oficial de Red Metropolitana de Movilidad. `QR_OTHER` agrupa pagos QR realizados mediante otros canales o aplicaciones. En algunos análisis, `QR_RED` y `QR_OTHER` se agregan como QR frente a `BIP`; en otros, se mantienen separados para evaluar si los canales digitales presentan perfiles distintos.

La base de viajes se complementa con fuentes externas. Las variables sociodemográficas provienen de información censal agregada a nivel territorial. Las variables de entorno construido se construyen a partir de OpenStreetMap (OSM), usando objetos urbanos asignados a zonas. Las variables de carga `BIP` describen distancia, densidad y cantidad de puntos de carga física. Las variables operacionales resumen oferta y demanda de transporte, incluyendo señales asociadas a bus, Metro, paraderos, estaciones y relaciones demanda-oferta.

La unidad espacial común es `ZONA777`. En esta tesis, `ZONA777` corresponde a una zonificación de análisis de viajes más desagregada que la comuna, utilizada para representar orígenes y destinos dentro del área de estudio. Esta zonificación permite unir registros de uso con variables de Censo, OSM, carga `BIP` y contexto operacional.

## 3.3 Descripción de los datos analíticos

La base analítica se construye a partir de registros observados de uso del sistema. Cada registro permite identificar el medio de pago y vincularlo con información temporal y espacial. A partir de estos registros se generan dos vistas principales de los datos: una vista a nivel tarjeta y una vista agregada a nivel zona.

La vista a nivel tarjeta resume el historial observado de cada `id_tarjeta`. Para cada tarjeta se registra su tipo de pago observado (`BIP`, `QR_RED` o `QR_OTHER`) y se agregan medidas de uso, tales como número de viajes, días activos, semanas activas y distribución temporal de actividad. Esta vista permite estudiar adopción y perfil de uso sin tratar cada viaje como una decisión independiente. También permite distinguir tarjetas con uso muy ocasional de tarjetas con actividad más frecuente, lo que es relevante para definir universos de análisis y sensibilidades.

La vista zonal resume la adopción QR en unidades `ZONA777`. Para cada zona se calculan cantidades observadas, participación QR y soporte mínimo por año. Esta vista se construye separadamente para residencia u origen habitual y para origen de viaje. La primera aproxima el entorno territorial asociado a la tarjeta; la segunda describe dónde se inician los viajes observados. Ambas geografías responden preguntas distintas y no deben mezclarse sin explicitar la unidad de lectura.

La descripción de datos en la tesis debe reportar, al menos, el tamaño de los universos usados, la proporción de observaciones `BIP` y QR, la desagregación entre `QR_RED` y `QR_OTHER`, el soporte disponible por año y la cobertura espacial de las zonas. También debe mostrar cómo cambia la lectura al pasar de conteo de zonas a volumen de tarjetas o viajes. Esta distinción es importante porque un patrón puede ser territorialmente extendido pero representar poco volumen, o concentrar gran parte del aumento agregado en pocas zonas de alta actividad.

El EDA QR vs `BIP` cumple el rol de descripción inicial de los datos. Sus figuras y tablas permiten mostrar que QR es minoritario en el sistema, que presenta diferencias agregadas de intensidad y temporalidad, y que tiene una señal territorial observable. Estas lecturas se usarán como motivación y caracterización de la base, no como evidencia causal ni como resultado definitivo del modelo final.

## 3.4 Preprocesamiento y construcción de datos analíticos

Los registros originales no se utilizan directamente como base final de modelamiento. Primero se construyen artefactos intermedios que agregan, depuran y resumen la información en unidades analíticas consistentes. Este paso es necesario porque una misma tarjeta puede tener múltiples viajes, las zonas pueden tener soporte desigual y las variables territoriales u operacionales provienen de fuentes con distinta granularidad.

A nivel tarjeta, los registros se agregan por `id_tarjeta`. Para cada tarjeta se identifica el tipo de medio de pago observado y se construyen medidas de intensidad de uso, tales como número de viajes, días activos y semanas activas. También se derivan indicadores temporales, modales y de contexto territorial asociados al uso observado. Cuando se requiere residencia u origen habitual, estos se interpretan como asignaciones operacionales basadas en los patrones observados, no como domicilio individual verificado.

A nivel zona, se construyen paneles por año y geografía. Las dos geografías principales son residencia y origen de viaje. En residencia, el universo corresponde a tarjetas asociadas a una zona de hogar u origen habitual. En origen de viaje, el universo corresponde a viajes iniciados en la zona. Para cada zona y año se calcula el soporte observado, el número de observaciones QR, el total de observaciones y la participación QR.

Para evitar que zonas con muy bajo soporte dominen la lectura, los análisis interanuales utilizan umbrales mínimos de observación por año. El umbral base utilizado en los EDA recientes es de 250 observaciones por año, con sensibilidades a otros umbrales. Las zonas sin soporte comparable se mantienen identificadas en mapas y tablas, pero no se usan para inferir crecimiento relativo.

## 3.5 Unidad de análisis a nivel tarjeta

La unidad principal para estudiar adopción y perfiles de pago es `id_tarjeta`. Esta unidad permite comparar tarjetas observadas como `BIP`, `QR_RED` o `QR_OTHER`, y es más coherente que el viaje individual cuando la pregunta se refiere a adopción de medio de pago o perfil de uso.

El uso de `id_tarjeta` tiene una interpretación acotada. Una tarjeta no necesariamente equivale a una persona, porque una persona puede usar más de una tarjeta o una tarjeta puede tener usos compartidos. Por esta razón, la tesis habla de tarjetas o proxies operacionales de usuario, no de individuos observados. Esta distinción es central para evitar una lectura individualista de resultados que son construidos a partir de identificadores operacionales.

En este nivel, el outcome natural no es la elección de medio de pago en cada viaje, sino el tipo de tarjeta o canal de pago observado. Por ello, los modelos preliminares se formulan como modelos de adopción o clasificación de tipo de tarjeta. La comparación puede ser binaria, QR frente a `BIP`, o multinomial, distinguiendo `BIP`, `QR_RED` y `QR_OTHER`.

## 3.6 Unidad de análisis a nivel zona

El segundo nivel de análisis es zonal. Su propósito no es reemplazar el análisis a nivel tarjeta, sino describir cómo la adopción QR se distribuye territorialmente y cómo cambia entre 2024 y 2025. Este nivel permite responder preguntas que no se contestan bien con tarjetas individuales, como qué macrozonas explican mayor volumen agregado de nuevos pagos QR o qué zonas crecen más que la tendencia global.

Para cada zona se calculan medidas de participación QR por año:

\[
share\_QR_{z,t} = \frac{QR_{z,t}}{N_{z,t}},
\]

donde \(QR_{z,t}\) es el número de observaciones QR en la zona \(z\) y año \(t\), y \(N_{z,t}\) es el total de observaciones comparables. El cambio bruto se define como:

\[
\Delta_z = share\_QR_{z,2025} - share\_QR_{z,2024}.
\]

El crecimiento relativo descuenta la tendencia global de la geografía correspondiente:

\[
\Delta^{rel}_z = \Delta_z - \Delta^{global}.
\]

Esta medida permite distinguir zonas que crecen más o menos que el promedio global, incluso cuando casi todas las zonas aumentan su participación QR. Además, se calcula un aporte volumétrico por cambio de share:

\[
aporte_z = N_{z,2025} \cdot (share\_QR_{z,2025} - share\_QR_{z,2024}).
\]

Esta descomposición separa la pregunta de tasa de crecimiento de la pregunta de contribución agregada. Una zona puede crecer mucho en términos relativos y aportar poco volumen si tiene pocas observaciones; también puede aportar mucho volumen con un crecimiento relativo moderado si concentra muchas tarjetas o viajes.

## 3.7 Construcción de variables

Las variables se organizan en familias, de modo que la metodología sea estable aunque cambie el modelo final. La primera familia corresponde a intensidad y temporalidad de uso. Incluye número de viajes, días activos, semanas activas, concentración temporal, presencia en semanas específicas y patrones de uso en días laborales o no laborales. Estas variables describen cómo se usa el sistema, no por qué se elige un medio de pago.

La segunda familia corresponde a variables residenciales y sociodemográficas. Incluye proxies de educación, composición socioeconómica, edad y otras características agregadas de la zona de residencia u origen habitual. Estas variables se interpretan como atributos territoriales, no como características individuales de cada tarjeta.

La tercera familia corresponde a contexto operacional. Incluye presencia de Metro, número de estaciones, oferta de bus, abordajes observados, demanda zonal y medidas de presión demanda-oferta. Estas variables buscan describir el entorno de transporte en el que se usa el sistema.

La cuarta familia corresponde a entorno urbano OSM. Incluye densidades o índices derivados de objetos urbanos, tales como comercio y servicios, educación superior, salud, equipamiento cívico, áreas verdes y otros componentes del entorno construido. Estas variables se usan como proxies de centralidad y equipamiento urbano. Dado que OSM es una fuente colaborativa, su lectura debe ser cuidadosa y no equivalente a un catastro administrativo completo.

La quinta familia corresponde al acceso físico a carga `BIP`. Incluye distancia al punto de carga más cercano, densidad de puntos de carga y número de puntos de carga asociados a la zona. En la estrategia actual, estas variables cumplen un rol importante como controles negativos o controles de contraste: permiten evaluar si la adopción QR parece responder a falta de acceso físico a carga `BIP` o si se alinea más con otros perfiles territoriales y operacionales.

Finalmente, se incorporan macrozonas y variables geográficas base. Estas variables ayudan a distinguir señales propias de una variable candidata de estructuras territoriales más amplias. Por ejemplo, una variable sociodemográfica puede capturar parte de la estructura Oriente/Poniente o Centro/Periferia si no se controla por macrozona.

## 3.8 Modelos preliminares a nivel tarjeta

El primer frente metodológico corresponde a modelos interpretables a nivel tarjeta. La especificación base se plantea como un modelo logit multinomial para el tipo de tarjeta observado:

\[
C_i \in \{\texttt{BIP}, \texttt{QR\_OTHER}, \texttt{QR\_RED}\}.
\]

`BIP` se utiliza como categoría de referencia. Los coeficientes de `QR_OTHER` y `QR_RED` se interpretan en relación con `BIP`, condicionados por las variables incluidas. Esta estructura permite evaluar si los canales QR tienen perfiles similares o si `QR_RED` y `QR_OTHER` responden a patrones diferentes.

El modelo a nivel tarjeta no debe confundirse con un modelo de elección de ruta o modo a nivel viaje. En este caso, las covariables describen la tarjeta, su contexto de uso y su entorno territorial. Por lo tanto, el modelo se interpreta como una regresión de adopción o pertenencia a tipo de tarjeta, no como una elección instantánea de pago en cada viaje.

La tesis puede reportar también especificaciones binarias QR frente a `BIP`, pero estas se interpretan como versiones agregadas. Si `QR_RED` y `QR_OTHER` tienen perfiles distintos, la agregación puede diluir señales relevantes. Por esta razón, el modelo multinomial cumple un rol central como especificación interpretable preliminar.

## 3.9 Benchmark predictivo

El segundo frente metodológico corresponde a modelos predictivos, especialmente XGBoost. Su propósito no es reemplazar el modelo interpretable ni entregar evidencia causal, sino estimar un techo predictivo aproximado con las variables disponibles. Si un modelo flexible con muchas interacciones y no linealidades logra separar solo moderadamente `BIP` y QR, eso informa el límite descriptivo de las variables observadas.

El benchmark predictivo se evalúa con métricas de clasificación, como AUC y PR-AUC en problemas binarios, y métricas one-vs-rest en problemas multiclase. Estas métricas se interpretan como capacidad de ordenamiento y separabilidad, no como prueba de mecanismo. También se utilizan para comparar familias de variables y evaluar si la señal está concentrada en uso, territorio, operación u otras dimensiones.

En el manuscrito, XGBoost debe presentarse como complemento metodológico. Su aporte principal es responder cuánto se puede predecir con las variables disponibles y si los patrones encontrados por modelos interpretables son compatibles con un techo predictivo razonable.

## 3.10 Segmentación descriptiva mediante NMF

El tercer frente metodológico corresponde a segmentación descriptiva a nivel tarjeta. La estrategia principal utiliza factorización no negativa de matrices (NMF) sobre representaciones de movilidad y contexto construidas sin usar el medio de pago como input. Esta decisión evita que los segmentos se definan mecánicamente por ser QR o `BIP`.

La segmentación busca identificar perfiles latentes de uso o contexto. Una vez construidos los segmentos, se cruza post-hoc su composición con `BIP`, QR, `QR_RED` y `QR_OTHER`. Por lo tanto, la pregunta no es si NMF predice causalmente adopción QR, sino si existen perfiles de uso o contexto donde los pagos QR aparecen sobrerrepresentados.

Esta herramienta es especialmente útil para ordenar patrones complejos que no se reducen bien a una sola variable. Sin embargo, sus resultados deben leerse como tipologías descriptivas. No reemplazan el modelo interpretable ni prueban mecanismos individuales.

## 3.11 Análisis zonal e interanual

El análisis zonal complementa el frente a nivel tarjeta. Su objetivo es describir dónde se ubica la adopción QR, cómo cambió entre 2024 y 2025 y qué zonas o macrozonas explican mayor parte del aumento agregado.

Este análisis utiliza mapas, tablas por macrozona, distribuciones de crecimiento, gradientes por variables candidatas y descomposición de volumen. La lectura distingue cuatro conceptos: nivel QR inicial, cambio bruto, crecimiento relativo frente a la tendencia global y contribución volumétrica al aumento total.

El análisis zonal no se presenta como modelo final en esta etapa. Funciona como descripción territorial, validación de robustez y preparación de una posible segunda etapa de modelamiento. Si el modelo final incorpora una regresión zonal, esta sección entregará el puente metodológico necesario.

## 3.12 Límites metodológicos

La metodología presenta límites importantes. Primero, el análisis es observacional. Las asociaciones entre QR, uso, operación y territorio no deben leerse como efectos causales. Segundo, `id_tarjeta` es una unidad operacional, no una persona observada. Tercero, las variables territoriales describen zonas, no atributos individuales de quienes usan el sistema.

Cuarto, el medio de pago observado no permite inferir directamente motivaciones, acceso a smartphone, bancarización, uso de aplicaciones, confianza tecnológica ni consulta de información en tiempo real. Estas dimensiones pueden ser relevantes para interpretar resultados, pero no se observan directamente en la base.

Quinto, los análisis zonales dependen de soporte mínimo, asignación territorial y definición de geografía. Por eso se reportan sensibilidades a soporte, tratamiento de macrozonas externas y diferencias entre tasa y volumen. Finalmente, los modelos preliminares pueden estar limitados por el techo predictivo de las variables disponibles; una baja capacidad predictiva no invalida el análisis descriptivo, pero sí acota el tipo de afirmaciones que se pueden sostener.

## Pendientes para versión final

- Confirmar la fuente formal/documental de `ZONA777`.
- Actualizar tamaños finales de muestra y universos de estimación.
- Decidir qué resultados preliminares a nivel tarjeta pasan al capítulo de Resultados.
- Definir si el modelo zonal queda como resultado principal, extensión o trabajo futuro.
- Convertir referencias metodológicas a BibTeX en la plantilla LaTeX.
- Decidir qué detalles técnicos pasan a anexos para no sobrecargar el cuerpo del manuscrito.
