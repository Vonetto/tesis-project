# Capítulo 1. Introducción

## 1.1 Contexto y motivación

La digitalización de los sistemas de transporte público ha modificado progresivamente la forma en que las personas acceden, planifican y pagan sus viajes. En distintas ciudades, las autoridades y operadores han incorporado aplicaciones móviles, información en tiempo real, validadores electrónicos, tarjetas inteligentes y sistemas de pago móvil. Estas tecnologías prometen reducir fricciones operacionales, mejorar la experiencia de usuario y entregar mayor flexibilidad en la interacción con el sistema de transporte.

Desde una perspectiva de gestión, estos cambios también plantean una necesidad operacional concreta. Los sistemas de transporte público requieren comprender cómo las personas interactúan con la oferta disponible, cómo responden a distintos mecanismos de acceso y cómo se distribuye la adopción de nuevas herramientas dentro de la ciudad. Esta información es relevante para planificar servicios, administrar demanda, focalizar incentivos, diseñar estrategias de comunicación y anticipar posibles brechas de acceso. En este sentido, estudiar la adopción de medios de pago digitales no solo permite caracterizar una innovación tecnológica, sino también generar evidencia útil para la toma de decisiones en transporte público.

Sin embargo, la incorporación de tecnologías digitales no implica necesariamente una adopción homogénea por parte de todos los usuarios. La literatura sobre brecha digital en transporte advierte que el acceso efectivo a servicios digitales no depende solo de la disponibilidad material de dispositivos o conectividad, sino también de habilidades, familiaridad tecnológica, acceso financiero, confianza y capacidad de obtener beneficios concretos de dichas herramientas. En consecuencia, la digitalización del transporte puede generar beneficios relevantes, pero también reproducir o amplificar desigualdades existentes si su adopción se concentra en ciertos grupos o territorios.

En el sistema de transporte público de Santiago, la coexistencia entre medios de pago tradicionales y digitales permite estudiar empíricamente este fenómeno. La tarjeta `BIP` constituye el medio de pago tradicional y masivo del sistema, mientras que los pagos mediante código QR representan una forma de acceso digital más reciente. Dentro de estos pagos QR, es relevante distinguir entre `QR_RED`, asociado al canal oficial de Red Metropolitana de Movilidad, y `QR_OTHER`, que agrupa otros canales o aplicaciones QR. Esta distinción permite analizar si la adopción digital observada mediante el medio de pago se comporta como una categoría homogénea o si existen diferencias entre canales digitales.

## 1.2 Problema de investigación

El problema central de esta tesis es comprender cómo se relacionan las características del viaje, el contexto operacional y el entorno territorial de origen con la elección del medio de pago en el transporte público de Santiago. En particular, interesa estudiar si la elección de alternativas digitales, especialmente `QR_RED`, se asocia con atributos del viaje, condiciones de oferta y demanda, composición sociodemográfica de la zona de origen y características del entorno construido. El énfasis en `QR_RED` se debe a que esta alternativa está asociada al canal digital oficial del sistema, por lo que puede interpretarse como una señal observable de inserción en un ecosistema institucional de transporte digital. Esta interpretación es cuidadosa: el dato permite observar el medio de pago utilizado, pero no confirma directamente el uso de aplicaciones, consulta de información en tiempo real ni otros mecanismos específicos.

Este problema es relevante por al menos tres razones. Primero, desde una perspectiva operacional, los medios de pago son parte de la experiencia de acceso al sistema y pueden estar asociados a diferencias en tiempos, transbordos, fricciones de uso o patrones horarios. Comprender estas asociaciones puede aportar al diseño de medidas de gestión de demanda, focalización de incentivos y planificación de servicios. Segundo, desde una perspectiva de política pública, la adopción de medios digitales puede entregar señales sobre inclusión o exclusión tecnológica en el transporte. Tercero, desde una perspectiva territorial, los patrones de adopción pueden no distribuirse uniformemente en la ciudad, sino estar asociados a diferencias de educación, vulnerabilidad, infraestructura urbana y oferta de transporte.

La tesis no busca demostrar causalmente que una característica individual específica produce la adopción de un medio de pago digital. Los datos disponibles permiten observar viajes, medios de pago y atributos territoriales agregados, pero no permiten observar directamente motivaciones individuales, uso efectivo de aplicaciones, consulta de información en tiempo real o decisiones subjetivas durante la espera. Por esta razón, el análisis se plantea como un estudio de asociación e interpretación de patrones observados, apoyado en modelos de elección discreta y en literatura sobre adopción digital en transporte.

## 1.3 Caso de estudio y alternativas de pago

El caso de estudio corresponde al sistema de transporte público de Santiago. La unidad de análisis es el viaje individual observado en la muestra de estimación. Para cada viaje se identifica el medio de pago utilizado y se construyen atributos asociados al viaje, al contexto temporal y a la zona de origen.

El conjunto de alternativas considerado está compuesto por tres categorías mutuamente excluyentes:

- `BIP`: viaje pagado con tarjeta `BIP`.
- `QR_RED`: viaje pagado mediante código QR asociado al canal oficial de Red Metropolitana de Movilidad.
- `QR_OTHER`: viaje pagado mediante otros canales o aplicaciones QR distintos de `QR_RED`.

En esta tesis, `BIP` se interpreta como el medio de pago tradicional y funciona como alternativa de referencia para comparar la adopción relativa de medios digitales. `QR_OTHER` representa una categoría digital heterogénea, asociada a canales QR no oficiales o externos al canal principal de Red. `QR_RED`, por su parte, se interpreta cuidadosamente como una señal observable de inserción en un ecosistema digital oficial de transporte. Esta interpretación no implica afirmar que todos los usuarios de `QR_RED` utilicen activamente la aplicación, consulten información en tiempo real o modifiquen causalmente su comportamiento por dicha información. El dato observado identifica el medio de pago, no el mecanismo subjetivo que explica su uso.

## 1.4 Pregunta de investigación

La pregunta principal que guía esta tesis es:

**¿Cómo se asocian las características del viaje, la oferta operacional, la demanda observada y las características territoriales de la zona de origen con la elección de medios de pago digitales en el transporte público de Santiago, distinguiendo entre `QR_RED`, `QR_OTHER` y `BIP`?**

Esta pregunta permite conectar el fenómeno de adopción digital con tres dimensiones empíricas. La primera corresponde a los atributos propios del viaje, como tiempos, esperas y transbordos. La segunda corresponde al contexto operacional del sistema, incluyendo demanda local y oferta de transporte. La tercera corresponde a la dimensión territorial, incorporando variables sociodemográficas y de entorno construido asociadas a la zona de inicio del viaje.

## 1.5 Objetivos

El objetivo general de esta tesis es modelar e interpretar la elección de medio de pago en viajes de transporte público de Santiago, con énfasis en la adopción relativa de alternativas digitales frente a `BIP`, incorporando atributos del viaje, condiciones operacionales y variables territoriales sociodemográficas y de entorno construido.

Los objetivos específicos son:

1. Caracterizar la elección entre `BIP`, `QR_RED` y `QR_OTHER` como un problema de elección discreta a nivel de viaje individual.

2. Estimar modelos logit que permitan comparar la utilidad relativa de los medios de pago digitales respecto de `BIP`, considerando atributos propios del viaje como tiempos, esperas y transbordos.

3. Incorporar variables de demanda y oferta operacional asociadas a la zona y franja temporal de origen del viaje, para evaluar cómo el contexto de funcionamiento del sistema se relaciona con la elección de medio de pago.

4. Integrar variables territoriales de Censo y OpenStreetMap para analizar si la composición sociodemográfica y el entorno construido de la zona de origen se asocian con la adopción relativa de `QR_RED` y `QR_OTHER`.

5. Interpretar los resultados desde una perspectiva de adopción digital y equidad territorial, distinguiendo evidencia estadística observada, hipótesis interpretativas y límites metodológicos del modelo.

## 1.6 Alcance y límites de la investigación

El análisis se realiza a nivel de viaje individual. Cada observación corresponde a un viaje observado, clasificado según su medio de pago. Para incorporar información territorial, cada viaje se asocia a una zona de origen `ZONA777`. Esta corresponde a una zonificación utilizada por el sistema de transporte público de Santiago para representar espacialmente los viajes y organizar información de origen y destino. En esta tesis, dicha zonificación permite vincular cada observación individual con variables agregadas de demanda, oferta, Censo y OpenStreetMap.

El modelo considera atributos del viaje, variables temporales y operacionales, características sociodemográficas de la zona de origen y atributos del entorno construido. Entre las variables de viaje se incluyen tiempos en vehículo, esperas y transbordos. Entre las variables operacionales se incluyen medidas de demanda local y oferta de transporte. Las variables sociodemográficas provienen del Censo 2024 y las variables de entorno construido se construyen a partir de OpenStreetMap.

El alcance del trabajo es inferencial e interpretativo, no causal. Las variables territoriales no deben leerse como atributos individuales de cada pasajero. Por ejemplo, una asociación entre mayor proporción de población con educación superior en la zona de origen y mayor utilidad relativa de `QR_RED` no implica que una persona con educación universitaria necesariamente use `QR_RED`; indica que los viajes originados en zonas con mayor presencia de dicha característica presentan diferencias sistemáticas en la elección observada.

(*Esta delimitación también refleja la evolución del trabajo de tesis. La motivación inicial se vinculaba con una pregunta más amplia sobre tecnologías digitales y comportamiento de viaje en transporte público. En esta versión, esa pregunta se acota empíricamente a una dimensión observable, trazable y modelable con los datos disponibles: la elección del medio de pago. Por lo tanto, `BIP`, `QR_RED` y `QR_OTHER` se utilizan como alternativas que permiten estudiar adopción digital observada, sin asumir que el medio de pago capture por completo otras formas de interacción digital con el sistema.*)

*(Asimismo, la tesis no tiene como objetivo central modelar inercia, hábito, clustering o segmentación de usuarios. Esas líneas podrían constituir extensiones futuras si existen datos y resultados suficientes, pero no forman parte de la promesa principal del trabajo. El foco de esta investigación es la adopción de medios de pago digitales observada mediante elección discreta y su relación con atributos de viaje, operación y territorio.*)

## 1.7 Organización de la tesis

El resto de la tesis se organiza de la siguiente manera. El Capítulo 2 revisa literatura sobre adopción digital en transporte, brecha digital, pago móvil, aplicaciones de movilidad, información en tiempo real y modelos de elección discreta. El Capítulo 3 presenta los datos, la construcción de variables, la zonificación utilizada y la metodología de estimación. El Capítulo 4 reporta los resultados de los modelos estimados, incluyendo métricas de ajuste, parámetros y medidas de interpretación como odds ratios. El Capítulo 5 discute los resultados desde una perspectiva de adopción digital, equidad territorial y política pública. Finalmente, el Capítulo 6 resume las principales conclusiones, limitaciones y posibles extensiones de la investigación.
