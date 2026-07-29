# Capítulo 1. Introducción

## 1.1 Contexto y motivación

La digitalización de los sistemas de transporte público ha modificado progresivamente la forma en que las personas acceden, planifican y pagan sus viajes. En distintas ciudades, las autoridades y operadores han incorporado aplicaciones móviles, información en tiempo real, validadores electrónicos, tarjetas inteligentes y sistemas de pago móvil. Estas tecnologías prometen reducir fricciones operacionales, mejorar la experiencia de usuario y entregar mayor flexibilidad en la interacción con el sistema de transporte.

Desde una perspectiva de gestión, estos cambios también plantean una necesidad operacional concreta. Los sistemas de transporte público requieren comprender cómo las personas interactúan con la oferta disponible, cómo responden a distintos mecanismos de acceso y cómo se distribuye la adopción de nuevas herramientas dentro de la ciudad. Esta información es relevante para planificar servicios, administrar demanda, focalizar incentivos, diseñar estrategias de comunicación y anticipar posibles brechas de acceso.

Sin embargo, la incorporación de tecnologías digitales no implica necesariamente una adopción homogénea por parte de todos los usuarios ni de todos los territorios. La literatura sobre brecha digital en transporte advierte que el acceso efectivo a servicios digitales no depende solo de la disponibilidad material de dispositivos o conectividad, sino también de habilidades, familiaridad tecnológica, acceso financiero, confianza y capacidad de obtener beneficios concretos de dichas herramientas. En consecuencia, la digitalización del transporte puede generar beneficios relevantes, pero también reproducir o amplificar desigualdades existentes si su adopción se concentra en ciertos grupos o zonas.

En el sistema de transporte público de Santiago, la coexistencia entre medios de pago tradicionales y digitales permite estudiar empíricamente este fenómeno. La tarjeta `BIP` constituye el medio de pago tradicional y masivo del sistema, mientras que los pagos mediante código QR representan una forma de acceso digital más reciente. Esta tesis utiliza el medio de pago observado como una señal empírica de adopción digital en transporte público. La interpretación es deliberadamente acotada: el dato permite observar si un viaje o conjunto de viajes fue pagado con `BIP` o QR, pero no permite observar directamente motivaciones individuales, uso efectivo de aplicaciones, consulta de información en tiempo real ni hábitos subjetivos de viaje.

## 1.2 Problema de investigación

El problema central de esta tesis es comprender cómo se distribuye la adopción observada de pagos QR en el transporte público de Santiago y qué características de uso, operación y territorio se asocian con dicha adopción. En particular, interesa estudiar si el uso de QR y su crecimiento reciente se relacionan con atributos de los viajes, condiciones de oferta y demanda, composición sociodemográfica de las zonas y características del entorno urbano.

Este problema es relevante por al menos tres razones. Primero, desde una perspectiva operacional, los medios de pago son parte de la experiencia de acceso al sistema y pueden estar asociados a diferencias en intensidad de uso, horarios, transbordos, fricciones de acceso o exposición a distintos modos. Segundo, desde una perspectiva de política pública, la adopción de medios digitales puede entregar señales sobre inclusión o exclusión tecnológica en el transporte. Tercero, desde una perspectiva territorial, los patrones de adopción pueden no distribuirse uniformemente en la ciudad, sino estar asociados a diferencias de educación, vulnerabilidad, infraestructura urbana, centralidad y oferta de transporte.

La tesis no busca demostrar causalmente que una característica individual específica produce la adopción de un medio de pago digital. Los datos disponibles permiten observar medios de pago, viajes y atributos territoriales agregados, pero no mecanismos subjetivos de decisión. Por esta razón, el análisis se plantea como un estudio de asociación e interpretación de patrones observados. El foco está en describir y modelar regularidades empíricas útiles para comprender la adopción de QR, sin atribuir causalidad individual ni asumir que el medio de pago capture por completo otras formas de interacción digital con el sistema.

## 1.3 Caso de estudio y niveles de análisis

El caso de estudio corresponde al sistema de transporte público de Santiago. La investigación trabaja con registros observados de uso del sistema, clasificados según medio de pago, y con información territorial asociada a zonas `ZONA777`. En este trabajo, `ZONA777` corresponde a una zonificación territorial de análisis de viajes, más desagregada que la comuna, que permite representar orígenes y destinos dentro del área de estudio. Esta zonificación permite vincular observaciones de pago y viaje con variables agregadas de demanda, oferta, Censo y OpenStreetMap.

El análisis distingue dos niveles complementarios. El primero corresponde al nivel de tarjeta, donde `id_tarjeta` se utiliza como proxy operacional de usuario para caracterizar adopción, intensidad de uso y perfiles asociados a `BIP` y QR. El segundo corresponde al nivel zonal, donde se agregan observaciones por zona de residencia u origen de viaje para estudiar diferencias territoriales y cambios interanuales, especialmente entre 2024 y 2025.

En esta tesis, `BIP` se interpreta como el medio de pago tradicional y funciona como referencia para comparar la adopción relativa de pagos digitales. Los pagos QR se interpretan como pagos digitales observados. Cuando los datos y la pregunta lo justifican, esta categoría puede desagregarse entre `QR_RED`, asociado al canal oficial de Red Metropolitana de Movilidad, y `QR_OTHER`, que agrupa otros canales o aplicaciones QR. Esta desagregación permite evaluar si los pagos QR se comportan como una categoría homogénea o si existen diferencias entre canales digitales. Sin embargo, la lectura principal del fenómeno se mantiene en torno a la adopción observada de QR frente a `BIP`.

## 1.4 Pregunta de investigación

La pregunta principal que guía esta tesis es:

**¿Cómo se distribuye la adopción observada de pagos QR en el transporte público de Santiago y cómo se asocia con características de uso, operación y territorio?**

Esta pregunta conecta el fenómeno de adopción digital con tres dimensiones empíricas. La primera corresponde a diferencias de uso del sistema, como intensidad, temporalidad y patrones de viaje. La segunda corresponde al contexto operacional, incluyendo demanda local, oferta de transporte y presencia de modos como bus y Metro. La tercera corresponde a la dimensión territorial, incorporando variables sociodemográficas, entorno construido y macrozonas urbanas.

De forma complementaria, la tesis aborda una pregunta más específica para el cambio reciente de QR:

**¿Qué zonas crecieron más o menos que la tendencia global de adopción QR entre 2024 y 2025, y qué variables candidatas ayudan a describir esas diferencias?**

Esta segunda pregunta permite separar el aumento general de QR en el sistema de las diferencias territoriales relativas. También permite distinguir entre zonas que crecen más en tasa y zonas que explican mayor volumen agregado de nuevos pagos QR.

## 1.5 Objetivos

El objetivo general de esta tesis es caracterizar e interpretar los patrones de adopción de pagos QR en el transporte público de Santiago, evaluando su relación con características de uso, condiciones operacionales y atributos territoriales, y desarrollando una estrategia de modelamiento compatible con la estructura observada de los datos a nivel tarjeta y zona.

Los objetivos específicos son:

1. Caracterizar la composición e intensidad de uso de `BIP` y QR, identificando diferencias agregadas en volumen, frecuencia, temporalidad y contexto modal.

2. Construir y documentar una base analítica que vincule medios de pago observados con atributos de uso, operación y territorio mediante `id_tarjeta` y la zonificación `ZONA777`.

3. Describir la distribución territorial de la adopción QR y su cambio interanual entre 2024 y 2025, diferenciando residencia y origen de viaje.

4. Evaluar variables candidatas asociadas al nivel y crecimiento de QR, incluyendo composición sociodemográfica residencial, centralidad urbana, acceso físico a carga `BIP`, presencia de Metro y contexto operacional de buses.

5. Comparar estrategias de modelamiento interpretables para explicar la adopción o crecimiento de QR, considerando modelos a nivel tarjeta, benchmarks predictivos, segmentación descriptiva y modelos agregados a nivel zonal, según la robustez empírica y la pregunta específica.

6. Interpretar los resultados desde una perspectiva de adopción digital, equidad territorial y gestión del transporte público, distinguiendo evidencia descriptiva, asociaciones estadísticas y límites metodológicos.

## 1.6 Alcance y límites de la investigación

El alcance del trabajo es descriptivo, inferencial e interpretativo, no causal. La tesis analiza asociaciones entre medio de pago, uso del sistema y características territoriales u operacionales. Estas asociaciones no deben leerse como efectos causales ni como atributos individuales no observados. Por ejemplo, una asociación entre mayor proporción de población con educación superior en una zona y mayor adopción de QR no implica que una persona con educación universitaria necesariamente use QR; indica que zonas con mayor presencia de dicha característica presentan diferencias sistemáticas en el patrón observado.

Las variables territoriales se interpretan a nivel agregado. La zonificación `ZONA777` permite organizar espacialmente los viajes y asociar información de Censo, OpenStreetMap y operación, pero no convierte esas variables en características individuales de cada pasajero. Del mismo modo, la presencia de equipamientos urbanos, estaciones o puntos de carga describe el entorno de la zona, no la experiencia completa de cada usuario.

La tesis tampoco interpreta la segmentación, la regularidad de uso o los modelos predictivos como evidencia causal sobre mecanismos individuales. Estas herramientas se utilizan, cuando corresponde, como apoyo descriptivo para perfilar patrones de adopción y ordenar la evidencia empírica. La motivación inicial se vinculaba con una pregunta amplia sobre tecnologías digitales y comportamiento de viaje; en esta versión, esa pregunta se acota empíricamente a una dimensión observable y trazable con los datos disponibles: la adopción de medios de pago digitales, especialmente pagos QR, y su relación con uso, operación y territorio.

Finalmente, el trabajo distingue entre patrones de tasa y patrones de volumen. Una zona puede presentar alto crecimiento relativo de QR, pero aportar poco al aumento agregado si tiene bajo volumen de viajes o tarjetas. A la inversa, una zona de gran volumen puede explicar una parte importante del aumento total aunque su crecimiento relativo sea moderado. Esta distinción es importante para interpretar correctamente los resultados descriptivos y para definir la estrategia de modelamiento.

## 1.7 Organización de la tesis

El resto de la tesis se organiza de la siguiente manera. El Capítulo 2 revisa literatura sobre adopción digital en transporte, brecha digital, pago móvil, aplicaciones de movilidad, información en tiempo real y métodos para estudiar elección o adopción tecnológica. El Capítulo 3 presenta los datos, la construcción de unidades de análisis, la zonificación utilizada, las variables candidatas y la estrategia metodológica. El Capítulo 4 reporta la caracterización empírica de `BIP` y QR, los patrones territoriales e interanuales y los resultados de modelamiento que se definan como principales. El Capítulo 5 discute los resultados desde una perspectiva de adopción digital, equidad territorial, gestión operacional y límites de interpretación. Finalmente, el Capítulo 6 resume las principales conclusiones, limitaciones y posibles extensiones de la investigación.
