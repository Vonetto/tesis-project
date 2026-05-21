# Capítulo 3. Materiales y métodos

## 3.1 Diseño general del estudio

Esta tesis desarrolla un estudio empírico observacional sobre la elección de medio de pago en el sistema de transporte público de Santiago. La unidad básica de análisis corresponde al viaje individual observado en los registros del sistema. Para cada viaje se identifica el medio de pago utilizado y se construyen atributos asociados al viaje, al contexto temporal, a la oferta operacional y al entorno territorial de origen.

El objetivo metodológico del capítulo es describir cómo se construye la base analítica utilizada para estimar modelos de elección discreta. En particular, se documentan las fuentes de datos, el preprocesamiento aplicado a los registros de viaje, la construcción de variables, el enriquecimiento territorial mediante la zonificación `ZONA777` y la especificación econométrica utilizada para modelar la elección entre medios de pago.

El análisis se basa en tres alternativas mutuamente excluyentes: `BIP`, `QR_RED` y `QR_OTHER`. La primera corresponde al medio de pago tradicional del sistema, mientras que las dos últimas corresponden a pagos mediante código QR. En el modelo, `BIP` cumple el rol de alternativa base para interpretar la adopción relativa de alternativas digitales. `QR_RED` se analiza con particular atención porque está asociado al canal digital oficial del sistema, aunque esta interpretación se mantiene como una lectura observacional del medio de pago y no como evidencia directa de uso de aplicación, consulta de información en tiempo real u otro mecanismo individual no observado.

La estrategia metodológica combina datos pasivos de viajes con información externa de transporte, territorio y entorno construido. Esta combinación permite estimar asociaciones entre la elección de medio de pago y tres grupos de factores: atributos del viaje, contexto operacional y características territoriales de la zona de origen. El enfoque es inferencial e interpretativo, no causal. Por lo tanto, los resultados deben leerse como patrones de asociación condicionados por las variables incluidas en el modelo.

## 3.2 Fuentes de datos

El análisis utiliza una base principal de viajes observados del sistema de transporte público de Santiago, complementada con fuentes operacionales y territoriales. La base de viajes contiene información sobre validaciones, medio de pago, origen, destino, tiempos y etapas asociadas al desplazamiento. A partir de esta fuente se identifican las alternativas observadas y se construyen atributos de viaje tales como tiempo en vehículo, tiempo de espera inicial, tiempo de espera en transbordos y número de transbordos.

La información operacional se utiliza para mejorar la caracterización de los viajes y del entorno de transporte. Para Metro, se emplean datos GTFS que permiten representar la estructura de líneas, estaciones, horarios y frecuencias del servicio. Esta información se usa tanto para reconstruir rutas internas en la red de Metro como para estimar tiempos esperados de espera y viaje en etapas de Metro. Para buses, se utiliza información operacional proveniente de registros de oferta y perfiles de carga, a partir de los cuales se construyen frecuencias observadas por servicio, paradero y hora.

Además, se incorporan fuentes territoriales externas. Las variables sociodemográficas provienen del Censo 2024 y se agregan a nivel de zona de origen. Algunas variables se obtienen directamente desde agregados espaciales de manzana-entidad, mientras que otras se derivan desde microdatos censales espacializados operacionalmente. Las variables de entorno construido se construyen a partir de OpenStreetMap (OSM), usando densidades de objetos urbanos e infraestructura de transporte dentro de cada zona.

Finalmente, se utilizan geometrías de la zonificación `ZONA777` para vincular los viajes individuales con atributos agregados de origen. Esta zonificación funciona como unidad espacial común entre viajes, variables operacionales, Censo y OSM.

## 3.3 Preprocesamiento, depuración y construcción de atributos de viaje

Antes de la estimación, los registros de viaje fueron sometidos a una etapa de depuración y reconstrucción de atributos. Esta etapa es necesaria porque los datos pasivos del sistema no constituyen directamente una base lista para modelar elección discreta. Los registros originales pueden contener tiempos inválidos, distancias inconsistentes, paraderos faltantes, etapas mal caracterizadas o viajes que no representan experiencias plausibles de desplazamiento. Además, algunos atributos centrales para el modelo, como las esperas y los transbordos, requieren procesamiento adicional antes de ser utilizados como variables explicativas.

La depuración inicial se basó en criterios de consistencia y detección de viajes anómalos inspirados en Núñez Sepúlveda (2015), quien desarrolla una metodología para calcular indicadores de calidad de servicio del transporte público de Santiago a partir de datos pasivos. En esta tesis, dichos criterios se adaptan al objetivo de construir una muestra consistente para modelos de elección discreta. En términos generales, se filtran registros con tiempos no válidos, paraderos inconsistentes, distancias inválidas y patrones de viaje incompatibles con una experiencia razonable de desplazamiento. La motivación de este paso es evitar que errores de medición o viajes mal reconstruidos distorsionen la estimación de parámetros asociados a tiempos, esperas y transbordos.

La lógica de filtrado distingue entre viajes desfavorables pero plausibles y viajes anómalos. Esta distinción es relevante porque los modelos deben preservar experiencias reales de baja calidad de servicio, como viajes largos o con múltiples transbordos, pero no deben interpretar como comportamiento de usuario registros que provienen de errores de estimación, inconsistencias espaciales o artefactos de la base. En este sentido, el preprocesamiento no busca eliminar viajes complejos, sino excluir observaciones que no entregan una representación confiable del fenómeno analizado.

Un segundo componente del preprocesamiento corresponde a la reconstrucción de etapas y transbordos internos de Metro. En los datos originales, ciertos cambios de línea dentro de la red de Metro pueden no quedar representados correctamente como parte de un mismo viaje continuo. Estos casos son problemáticos porque pueden sesgar el número de etapas, el número de transbordos y los tiempos asociados a la experiencia de viaje. Para abordar este punto, se implementó una reconstrucción de rutas internas de Metro mediante un grafo de la red, construido a partir de información GTFS. Esta reconstrucción permite identificar trayectorias factibles entre estaciones, reconocer transbordos internos y mejorar la consistencia de las etapas utilizadas para calcular atributos del viaje.

El tercer componente corresponde al recálculo e imputación de tiempos de espera. Los tiempos de espera originales no se utilizaron de manera acrítica, debido a problemas de trazabilidad y consistencia. En su lugar, se calcularon tiempos esperados usando información operacional. Para Metro, los tiempos de espera se estimaron a partir de headways programados en GTFS, utilizando la mitad del headway equivalente cuando el servicio opera bajo una lógica más regular. Para buses, se estimó la espera esperada a partir de frecuencias observadas por servicio, paradero y hora, siguiendo la formulación discutida por Arriagada et al. (2022) para redes con servicios de buses de headways irregulares. En particular, cuando se asume una llegada tipo Poisson, la espera esperada para una línea con frecuencia observada \(f\) se calcula como:

\[
WT = \frac{60}{f}
\]

medida en minutos cuando \(f\) está expresada en buses por hora. En la implementación, esta relación se expresa en segundos como \(3600/f\). Esta decisión es coherente con tratar la operación de buses como un servicio de frecuencia irregular, distinto del tratamiento aplicado a Metro, donde se utiliza información programada de headways y una aproximación de media espera igual a la mitad del intervalo.

El resultado de esta etapa es una base de viajes con atributos reconstruidos y consistentes para modelación. En particular, se generan variables de tiempo en vehículo, espera inicial, espera en transbordos y número de transbordos. La caminata en transbordos no se incorpora en la especificación principal, debido a la mayor dificultad de estimarla de manera homogénea y confiable para todos los tipos de transbordo. Esta decisión reduce la complejidad del modelo y evita introducir una variable con calidad desigual entre modos.

## 3.4 Unidad de análisis, alternativas y muestra de estimación

La unidad de análisis es el viaje individual. Cada observación corresponde a un desplazamiento observado en el sistema y contiene la alternativa de pago utilizada. El conjunto de elección considerado es:

\[
C_n = \{\texttt{BIP}, \texttt{QR\_RED}, \texttt{QR\_OTHER}\}.
\]

La alternativa `BIP` corresponde al pago mediante tarjeta tradicional. La alternativa `QR_RED` corresponde al pago mediante código QR asociado al canal digital oficial del sistema. La alternativa `QR_OTHER` agrupa pagos QR realizados mediante otros canales o aplicaciones. Estas tres alternativas se tratan como mutuamente excluyentes dentro de cada viaje.

La base de estimación se construye a partir de una muestra conjunta de viajes observados en 2024 y 2025. La incorporación de ambos años permite analizar diferencias temporales en la adopción observada de medios de pago, controlando explícitamente por el año de observación mediante la variable `ANIO_2025`. En vez de estimar modelos separados por año, se utiliza una base pooled que permite incorporar la dimensión temporal dentro de una misma especificación.

Por razones computacionales, la estimación principal se realiza sobre una submuestra estratificada de la base enriquecida. El submuestreo preserva la composición por período de datos y alternativa de pago observada. Es decir, dentro de cada combinación de partición temporal y alternativa elegida se selecciona aleatoriamente una fracción fija de viajes, utilizando una semilla definida para asegurar reproducibilidad. Esta estrategia evita que el muestreo altere de manera importante la representación relativa de `BIP`, `QR_RED` y `QR_OTHER`, especialmente considerando que las alternativas digitales tienen frecuencias distintas a la alternativa tradicional.

En la versión actualmente documentada del modelo, la estimación principal utiliza una submuestra de 2% de la base interanual enriquecida, con aproximadamente 466 mil observaciones. Este número deberá actualizarse en la versión final si la muestra definitiva cambia por la incorporación de nuevas variables o sensibilidades adicionales. Además, se han estimado sensibilidades con muestras mayores en Larch, debido a que este framework permitió correr especificaciones similares con mayor volumen de datos y menor presión de memoria. Estas corridas se utilizan como validación de que los patrones principales no dependan exclusivamente del tamaño de muestra usado en Biogeme.

## 3.5 Enriquecimiento territorial mediante `ZONA777`

Para incorporar información territorial, cada viaje se asocia a una zona de origen `ZONA777`. Esta corresponde a una zonificación utilizada por el sistema de transporte público de Santiago para representar espacialmente los viajes y organizar información de origen y destino. En esta tesis, dicha zonificación permite vincular cada observación individual con variables agregadas de demanda, oferta, Censo y OpenStreetMap.

El enriquecimiento territorial se realiza usando la zona de inicio del viaje. Esta decisión responde a que el objetivo es caracterizar el entorno desde el cual se inicia la interacción con el sistema de transporte y con el medio de pago. Por lo tanto, las variables territoriales incluidas en el modelo describen el contexto de origen, no necesariamente el destino ni la trayectoria completa del viaje.

El uso de `ZONA777` permite combinar fuentes con resoluciones espaciales distintas. Los viajes se observan a nivel individual, mientras que variables de demanda, oferta y territorio se construyen a nivel agregado. La zonificación funciona como una unidad espacial común que permite unir estos niveles de información. Sin embargo, esta operación implica una cautela interpretativa importante: las variables territoriales no deben leerse como características individuales del pasajero. Por ejemplo, una zona con mayor proporción de población con educación universitaria no implica que cada usuario que inicia viaje en esa zona tenga educación universitaria; indica que el entorno territorial de origen presenta esa composición agregada.

## 3.6 Construcción de variables

Las variables utilizadas en el modelo se organizan en cuatro grupos principales: atributos de viaje, variables temporales y operacionales, variables censales y variables de OpenStreetMap.

### 3.6.1 Atributos de viaje

Los atributos de viaje buscan capturar el costo temporal y operacional asociado a cada alternativa de pago. Estas variables se construyen como atributos alternativa-específicos, es decir, pueden tomar valores distintos para `BIP`, `QR_RED` y `QR_OTHER` dentro de una misma observación.

Las variables incluidas son:

- `T_VEH`: tiempo en vehículo de la alternativa, medido en segundos.
- `T_ESPERA_INI`: tiempo de espera inicial de la alternativa, medido en segundos.
- `T_ESPERA_TRASB`: tiempo de espera asociado a transbordos, medido en segundos.
- `N_TRASB`: número de transbordos de la alternativa.

Estas variables se construyen a partir de viajes comparables por origen, destino y tipo de pago. Para la alternativa efectivamente elegida se aplica una corrección tipo leave-one-out, de modo que el viaje observado no contribuya mecánicamente a construir sus propios atributos de contexto. Esta corrección reduce el riesgo de introducir endogeneidad mecánica en los atributos de la alternativa elegida.

### 3.6.2 Variables temporales, demanda y oferta operacional

El segundo grupo de variables describe el contexto temporal y operacional del viaje. A diferencia de los atributos de viaje, estas variables son comunes a las tres alternativas dentro de una observación.

Las variables temporales incluyen `ANIO_2025`, `LAB_PM`, `LAB_PT` y `NO_LAB`. La variable `ANIO_2025` identifica viajes observados durante 2025. Las variables de franja horaria identifican viajes en día laboral durante punta mañana (`LAB_PM`), día laboral durante punta tarde (`LAB_PT`) y día no laboral (`NO_LAB`). La categoría base corresponde a viajes en día laboral fuera de las horas punta definidas (`LAB_VALLE`).

La variable de demanda local se define como `LOG_DEMAND`. Esta variable mide la intensidad de viajes observados en la zona de origen y franja temporal del viaje. Para construirla, se cuenta el número de viajes por año, zona de inicio y franja horaria. Luego se aplica una corrección leave-one-out para evitar que el viaje observado contribuya a su propia medida de demanda, y finalmente se utiliza la transformación \(\log(1+x)\). Esta variable se interpreta como una proxy de intensidad local de demanda, no como demanda total del sistema.

Las variables de oferta operacional resumen la disponibilidad de transporte en la zona de origen. `LOG_BUS_STOP_DENSITY` captura la densidad de paraderos de bus. `LOG_BUS_LINE_COUNT` aproxima la variedad de servicios de bus disponibles por zona y franja. `LOG_METRO_LINE_COUNT` representa el número promedio de líneas de Metro activas asociadas a estaciones de la zona. Todas estas variables se transforman mediante \(\log(1+x)\) para reducir asimetrías y permitir una lectura asociada a cambios proporcionales.

### 3.6.3 Variables censales

Las variables censales provienen del Censo 2024 y se incorporan a nivel de zona de origen. Algunas variables se derivan directamente desde la base agregada de manzana-entidad y se cruzan espacialmente con `ZONA777`. Cuando las unidades censales no coinciden exactamente con las zonas de transporte, se utiliza una agregación areal basada en intersecciones espaciales. Los conteos se agregan antes de calcular proporciones, evitando promediar porcentajes de unidades con distinto tamaño poblacional.

Otras variables se construyen a partir de microdatos comunales del Censo 2024. Dado que estos microdatos no tienen localización fina observada, se utiliza una estrategia operacional de espacialización intra-comunal inspirada en la discusión metodológica de E. Graells-Garrido sobre asignación espacial de viviendas censales sin ubicación fina. Esta estrategia permite generar aproximaciones territoriales consistentes con agregados disponibles, pero no debe interpretarse como ubicación observada de hogares o personas.

El bloque censal principal incluye variables como proporción de población de 18 años o más con educación universitaria o superior, proporción de viviendas con hacinamiento, proporción de personas con discapacidad y proporción de población inmigrante. Estas variables se estandarizan antes de entrar al modelo, por lo que sus coeficientes se interpretan como cambios asociados a un aumento de una desviación estándar en la característica territorial.

### 3.6.4 Variables de OpenStreetMap

Las variables OSM buscan capturar atributos del entorno construido y elementos de infraestructura próximos al origen del viaje. Para construirlas, se extraen objetos OSM dentro del área de estudio y se asignan espacialmente a `ZONA777`. Luego se calculan densidades por kilómetro cuadrado para combinaciones específicas de llave y valor, tales como `amenity=school`, `amenity=university` o `railway=subway_entrance`.

El bloque OSM incluye variables de equipamiento urbano, como densidad de escuelas, universidades, juegos infantiles, centros deportivos y comercio de conveniencia. Además, el modelo incorpora variables de infraestructura de acceso al transporte, como densidad de objetos de transporte con `shelter=yes` y densidad de accesos físicos a Metro (`railway=subway_entrance`). Estas variables se estandarizan antes de la estimación.

La interpretación de las variables OSM requiere cautela porque OpenStreetMap es una fuente colaborativa y su cobertura puede variar espacialmente. Por lo tanto, estas variables se usan como proxies observables del entorno construido y de la infraestructura mapeada, no como inventarios administrativos exhaustivos.

## 3.7 Especificación del modelo de elección discreta

La elección de medio de pago se modela mediante un modelo logit multinomial (MNL) basado en el marco de utilidad aleatoria. Se asume que cada viaje \(n\) tiene asociada una utilidad latente para cada alternativa \(i\) perteneciente al conjunto de elección \(C_n\). La alternativa observada corresponde a aquella que entrega la mayor utilidad.

La utilidad total de la alternativa \(i\) para el viaje \(n\) se define como:

\[
U_{ni} = V_{ni} + \varepsilon_{ni},
\]

donde \(V_{ni}\) corresponde a la utilidad sistemática observable y \(\varepsilon_{ni}\) captura factores no observados por el analista.

La utilidad sistemática combina variables alternativa-específicas y variables comunes al viaje o a la zona de origen:

\[
V_{ni}
=
ASC_i
+
\sum_{k \in K^{AS}} \beta^{AS}_{ki} X_{kni}
+
\sum_{m \in K^{C}} \beta^{C}_{mi} Z_{mn}.
\]

En esta expresión, \(ASC_i\) es la constante específica de alternativa; \(X_{kni}\) representa atributos que pueden variar entre alternativas dentro de un mismo viaje, como tiempos de viaje, esperas y transbordos; y \(Z_{mn}\) representa variables comunes a las alternativas, como año, franja horaria, demanda, oferta, Censo y OSM.

Bajo el supuesto de errores independientes e idénticamente distribuidos Gumbel tipo I, la probabilidad de que el viaje \(n\) utilice la alternativa \(i\) toma la forma:

\[
P_{ni}
=
\frac{\exp(V_{ni})}
{\sum_{j \in C_n} \exp(V_{nj})}.
\]

Los coeficientes se interpretan en términos relativos entre alternativas. Un coeficiente positivo aumenta la utilidad sistemática de una alternativa respecto de las demás, mientras que un coeficiente negativo la reduce, manteniendo constantes el resto de las variables.

## 3.8 Parametrización e interpretación

El modelo combina variables alternativa-específicas y variables comunes. Para las variables alternativa-específicas, como `T_VEH`, `T_ESPERA_INI`, `T_ESPERA_TRASB` y `N_TRASB`, se estiman coeficientes para las tres alternativas. Esto es posible porque el valor de estas variables puede diferir entre `BIP`, `QR_RED` y `QR_OTHER` dentro de una misma observación.

Para las variables comunes al viaje o a la zona, se utiliza `BIP` como alternativa de referencia. En este caso, el valor de la variable es el mismo para las tres alternativas de una observación, por lo que no se identifican tres efectos absolutos independientes. En consecuencia, se fija el coeficiente de `BIP` en cero y se estiman los coeficientes de `QR_RED` y `QR_OTHER` respecto de `BIP`.

Esta parametrización implica que, para variables comunes, un coeficiente positivo de `QR_RED` indica que un aumento en la variable se asocia con mayor utilidad relativa de `QR_RED` frente a `BIP`. De forma análoga, un coeficiente negativo indica menor utilidad relativa de la alternativa digital considerada respecto de `BIP`. Esta lectura es relativa y no debe interpretarse como un efecto absoluto de la variable sobre una alternativa aislada.

Además de reportar coeficientes, la tesis incorpora odds ratios como herramienta de interpretación. Para una variable \(x\) con coeficiente \(\beta\), el odds ratio asociado a un aumento de una unidad en \(x\) se calcula como:

\[
OR = \exp(\beta).
\]

Cuando las variables están estandarizadas, el odds ratio se interpreta como el cambio multiplicativo en los odds asociado a un aumento de una desviación estándar. Para tiempos medidos en segundos, los odds ratios pueden escalarse a un minuto adicional multiplicando el coeficiente por 60 antes de aplicar la exponencial. Esta transformación facilita la lectura sustantiva de los resultados, especialmente para comparar efectos entre variables con distintas unidades.

## 3.9 Estrategia de estimación y evaluación

La estimación se realiza mediante máxima verosimilitud. La función objetivo corresponde a la log-verosimilitud de las elecciones observadas, dada la probabilidad asignada por el modelo a la alternativa efectivamente elegida. La estimación principal se implementa en Biogeme, una biblioteca especializada en la estimación de modelos de elección discreta y ampliamente utilizada en investigación aplicada en transporte. Larch, otra biblioteca orientada a modelos de elección discreta y análisis de demanda de transporte, se utiliza como herramienta complementaria para estimar sensibilidades con muestras mayores y verificar la estabilidad general de los resultados.

Las especificaciones se evalúan combinando criterios estadísticos, computacionales e interpretativos. En primer lugar, se revisa la convergencia numérica del modelo, incluyendo el estado de convergencia, el gradiente final y la presencia de errores de estimación. En segundo lugar, se reportan medidas de ajuste global como log-verosimilitud final, AIC y BIC. La log-verosimilitud permite comparar ajuste entre modelos, mientras que AIC y BIC penalizan la complejidad de la especificación. Dado el tamaño de muestra, BIC aplica una penalización especialmente exigente al número de parámetros, por lo que su interpretación se combina con criterios de interpretabilidad y valor sustantivo.

En tercer lugar, se revisan errores estándar robustos, estadísticos \(t\) y valores \(p\). La selección de variables no se basa únicamente en significancia estadística, sino también en estabilidad, signo, magnitud e interpretación. En particular, para variables territoriales se privilegian especificaciones parsimoniosas y defendibles, evitando sobrecargar el modelo con variables altamente redundantes o de lectura sustantiva débil.

El modelo principal se define como una especificación MNL territorial que incorpora atributos de viaje, controles temporales, demanda local, oferta operacional, variables censales y variables OSM. Sensibilidades adicionales se utilizan para evaluar robustez, pero no reemplazan el criterio central de construir un modelo interpretable y coherente con la pregunta de investigación.

## 3.10 Consideraciones metodológicas y límites

La metodología presenta varias limitaciones que deben considerarse al interpretar los resultados. En primer lugar, el análisis es observacional. Por lo tanto, los coeficientes estimados representan asociaciones condicionadas por las variables incluidas, no efectos causales. No es posible afirmar, por ejemplo, que una característica territorial cause individualmente la adopción de `QR_RED`.

En segundo lugar, las variables territoriales corresponden al entorno de origen del viaje, no a atributos individuales de los pasajeros. Una asociación entre mayor educación universitaria en la zona y mayor utilidad relativa de una alternativa digital debe interpretarse como un patrón territorial, no como evidencia directa sobre el nivel educativo de cada usuario.

En tercer lugar, el medio de pago `QR_RED` se interpreta como una señal observable de inserción en un canal digital institucional, pero no permite observar directamente el uso de aplicaciones, información en tiempo real ni decisiones subjetivas durante el viaje. Esta distinción es central para evitar una sobreinterpretación de los resultados.

En cuarto lugar, la construcción de atributos de viaje depende de supuestos de preprocesamiento. Aunque se implementaron correcciones e imputaciones basadas en información operacional y literatura previa, todo cálculo de tiempos de espera o reconstrucción de etapas en datos pasivos contiene incertidumbre. Esta incertidumbre es menor que utilizar variables originales sin depuración, pero debe ser reconocida como parte de la metodología.

Finalmente, algunas líneas metodológicas originalmente consideradas, como inercia, hábito, clustering o segmentación de usuarios, no forman parte del objetivo principal de esta especificación. La tesis se concentra en la elección observada de medio de pago y en su relación con atributos de viaje, operación y territorio. Otras extensiones pueden ser abordadas en trabajos futuros o en análisis complementarios si los datos y resultados lo permiten.

## Referencias metodológicas a incorporar

- Arriagada, J., Munizaga, M. A., Guevara, C. A., & Prato, C. (2022). *Unveiling route choice strategy heterogeneity from smart card data in a large-scale public transport network*. Transportation Research Part C, 134, 103467.
- Núñez Sepúlveda, C. L. (2015). *Cálculo de indicadores de calidad de servicio para el sistema de transporte público de Santiago a partir de datos pasivos*. Universidad de Chile.
- E. Graells-Garrido (2026). *Cuando los datos no tienen ubicación: un método para asignar viviendas censales*. Datagramas.

## Pendientes para versión final

- Confirmar la cita formal y fuente documental de `ZONA777`.
- Actualizar tamaño final de muestra, período definitivo y porcentaje de submuestreo si cambia la especificación principal.
- Confirmar si el modelo final incorpora nuevas variables censales como `share_mujeres_z` o `share_asistencia_parv_z`.
- Convertir referencias metodológicas a formato BibTeX en la plantilla LaTeX.
- Decidir si se agrega un anexo metodológico con detalle de filtros, reglas de anomalías y validaciones del pipeline de preprocesamiento.
