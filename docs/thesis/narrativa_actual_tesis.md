# Narrativa actual de la tesis

## Título de trabajo

**Tecnologías Digitales y su Impacto en el Comportamiento de Viaje en Transporte Público**

Este título se mantiene como título de trabajo amplio. La narrativa actual de la tesis se focaliza en una dimensión específica de ese marco: la adopción de tecnologías digitales en transporte público observada empíricamente a través de la elección del medio de pago.

## Tesis central

La tesis estudia cómo atributos del viaje, condiciones operacionales del sistema y características territoriales del entorno de origen se asocian con la elección entre medios de pago tradicionales y digitales en el transporte público de Santiago. En particular, el análisis distingue entre viajes pagados con tarjeta `BIP`, viajes pagados mediante `QR_RED` y viajes pagados mediante `QR_OTHER`.

El foco actual no es demostrar causalmente que una persona adopta una tecnología digital por una característica individual específica, sino modelar patrones observados de elección de medio de pago y discutir cómo estos patrones se relacionan con el contexto territorial, la oferta del sistema, la composición sociodemográfica de las zonas de origen y la infraestructura urbana disponible. Bajo esta lectura, `QR_RED` se interpreta cuidadosamente como una señal observable de inserción en un ecosistema digital oficial de transporte, no como prueba directa de uso efectivo de la aplicación, consulta de información en tiempo real o cambio causal de comportamiento.

## Pregunta de investigación principal

¿Cómo se asocian las características del viaje, la oferta operacional, la demanda observada y las características territoriales de la zona de origen con la elección de medios de pago digitales en el transporte público de Santiago, distinguiendo entre `QR_RED`, `QR_OTHER` y `BIP`?

## Objetivo general

Modelar e interpretar la elección de medio de pago en viajes de transporte público de Santiago, con énfasis en la adopción relativa de alternativas digitales frente a `BIP`, incorporando atributos del viaje, condiciones operacionales y variables territoriales sociodemográficas y de entorno construido.

## Objetivos específicos

1. Caracterizar la elección entre `BIP`, `QR_RED` y `QR_OTHER` como un problema de elección discreta a nivel de viaje individual.

2. Estimar modelos logit que permitan comparar la utilidad relativa de los medios de pago digitales respecto de `BIP`, considerando atributos propios del viaje como tiempos, esperas y transbordos.

3. Incorporar variables de demanda y oferta operacional asociadas a la zona y franja temporal de origen del viaje, para evaluar cómo el contexto de funcionamiento del sistema se relaciona con la elección de medio de pago.

4. Integrar variables territoriales de Censo y OpenStreetMap para analizar si la composición sociodemográfica y el entorno construido de la zona de origen se asocian con la adopción relativa de `QR_RED` y `QR_OTHER`.

5. Interpretar los resultados desde una perspectiva de adopción digital y equidad territorial, distinguiendo evidencia estadística observada, hipótesis interpretativas y límites metodológicos del modelo.

## Alcance empírico

La unidad de observación corresponde a un viaje individual observado en la muestra de estimación. Cada viaje se clasifica según su medio de pago observado: `BIP`, `QR_RED` o `QR_OTHER`.

El análisis se sitúa en el sistema de transporte público de Santiago y utiliza `ZONA777` como unidad espacial de referencia para incorporar información contextual del origen del viaje. Esta zonificación permite vincular cada viaje con variables agregadas de demanda, oferta, Censo y OpenStreetMap.

El conjunto de variables actualmente considerado incluye:

- Atributos del viaje: tiempo en vehículo, tiempo de espera inicial, tiempo de espera en transbordos y número de transbordos.
- Variables temporales y operacionales: año, franjas laborales y no laborales, demanda local, densidad de paraderos, líneas de bus y líneas de Metro.
- Variables sociodemográficas: educación superior, hacinamiento, discapacidad, inmigración y variables candidatas adicionales como proporción de mujeres o asistencia a educación parvularia.
- Variables de entorno construido OSM: equipamientos urbanos, infraestructura de transporte, refugios de transporte y accesos físicos a Metro.

## Interpretación de las alternativas

`BIP` representa el medio de pago tradicional y se utiliza como alternativa base para interpretar los coeficientes de variables comunes al viaje o a la zona.

`QR_OTHER` representa adopción digital mediante canales QR distintos del canal oficial de Red Metropolitana de Movilidad. Su interpretación debe mantenerse como una categoría digital heterogénea, potencialmente asociada a diferentes aplicaciones, canales o mecanismos de pago.

`QR_RED` representa el canal QR asociado al ecosistema oficial de Red. En esta tesis se interpreta como una alternativa tecnológicamente mediada y más institucionalizada que `QR_OTHER`. Sin embargo, esta interpretación debe formularse con cautela: el dato observado identifica el medio de pago, no el uso efectivo de funcionalidades específicas de la aplicación ni la consulta de información en tiempo real.

## Hipótesis interpretativas defendibles

1. La adopción de medios de pago digitales en transporte público no es homogénea territorialmente. Puede estar asociada a diferencias en capital educativo, condiciones socioeconómicas, acceso a herramientas digitales y familiaridad con tecnologías móviles.

2. Las zonas con mayor presencia de población con educación superior pueden presentar mayor utilidad relativa de `QR_RED`, consistente con literatura sobre brecha digital, adopción de aplicaciones de movilidad y pago móvil en transporte público.

3. Diferencias entre `QR_RED` y `QR_OTHER` pueden reflejar que no todos los pagos QR capturan el mismo tipo de adopción digital. `QR_RED` puede estar más vinculado a un ecosistema oficial de transporte, mientras que `QR_OTHER` puede representar canales digitales más diversos.

4. La menor penalización o no significancia de ciertos tiempos de espera para `QR_RED`, especialmente en transbordos, puede ser compatible con la literatura sobre información en tiempo real y espera percibida. Esta lectura debe plantearse como hipótesis interpretativa, no como evidencia causal de uso de información en tiempo real.

5. Las variables de entorno construido y microinfraestructura permiten explorar si la adopción relativa de medios digitales se relaciona con condiciones territoriales del acceso al sistema, más allá de atributos individuales no observados.

## Límites narrativos y metodológicos

La tesis no debe afirmar causalidad individual a partir de variables territoriales agregadas. Por ejemplo, una asociación positiva entre educación superior zonal y `QR_RED` no implica que una persona con educación universitaria use necesariamente `QR_RED`; implica que los viajes originados en zonas con mayor presencia de educación superior se asocian con mayor utilidad relativa de esa alternativa.

La tesis tampoco debe afirmar que todos los usuarios de `QR_RED` utilizan activamente la aplicación, consultan información en tiempo real o modifican su comportamiento por esa información. Esos mecanismos son hipótesis interpretativas plausibles, apoyadas por literatura, pero no observadas directamente en los datos actuales.

El modelo actual no promete explicar inercia, hábito, clustering o segmentación de usuarios como resultados centrales. Esas líneas pueden quedar como posibles extensiones internas si más adelante existen tiempo, datos y resultados suficientes, pero no forman parte de la narrativa formal de esta etapa.

## Puente hacia la estructura de la tesis

Esta narrativa puede organizar la tesis formal de la siguiente manera:

1. **Introducción:** presentar la digitalización del transporte público, la emergencia de medios de pago QR y la necesidad de entender su adopción como fenómeno operacional y territorial.

2. **Revisión de literatura:** cubrir adopción digital, brecha digital en transporte, mobile fare payment, aplicaciones de movilidad, información en tiempo real y modelos de elección discreta.

3. **Materiales y métodos:** describir los datos de viajes, la construcción de alternativas, la zonificación `ZONA777`, las variables de viaje, oferta, demanda, Censo y OSM, y la especificación logit.

4. **Resultados:** reportar ajuste, convergencia, parámetros, odds ratios e interpretación de efectos por alternativa.

5. **Discusión:** conectar los resultados con adopción digital, equidad territorial, diferencias entre `QR_RED` y `QR_OTHER`, límites de interpretación y oportunidades para política pública.

6. **Conclusiones:** sintetizar los aportes empíricos y metodológicos, explicitar limitaciones y proponer extensiones futuras.
