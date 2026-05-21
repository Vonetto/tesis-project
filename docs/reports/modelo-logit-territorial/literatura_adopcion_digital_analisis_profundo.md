# Analisis profundo de literatura seleccionada

Este documento selecciona los tres trabajos mas utiles para cada rama de la revision bibliografica:

1. Educacion, nivel socioeconomico y brecha digital.
2. Mobile ticketing y pago digital en transporte publico.
3. Apps de informacion en tiempo real y valor de la espera.

El criterio de seleccion no fue solo cercania tematica, sino utilidad directa para interpretar resultados del modelo: `share_cine18_universitaria_o_mas_micro_z`, diferencias entre `QR_RED` y `QR_OTHER`, y el resultado de `T_ESPERA_TRASB` para `QR_RED`.

## Seleccion final

| Rama | Referencias seleccionadas | Por que estas tres |
| --- | --- | --- |
| Educacion/NSE/brecha digital | Durand et al. (2021); Boyko y Schaefer (2026); Brakewood y Kocur (2013) | Entregan el marco conceptual de desigualdad digital en transporte, una revision reciente centrada en apps, y evidencia directa de que ingreso/educacion/bancarizacion importan en sistemas de pago. |
| Mobile ticketing/pago digital | Owusu-Agyemang et al. (2024); Brakewood et al. (2020); Wani et al. (2025) | Son los mas cercanos al caso de pago movil en transporte: adopcion real de mobile fare payment, beneficios operacionales/usuario, y adopcion de pago digital en ciudad en desarrollo. |
| Apps/informacion/espera | Watkins et al. (2011); Brakewood y Watkins (2019); Kaplan et al. (2017) | Permiten interpretar la espera no solo como tiempo objetivo, sino como experiencia mediada por informacion, familiaridad y tecnologia. |

## 1. Educacion, NSE y brecha digital

### 1.1 Durand et al. (2021) - "Access denied? Digital inequality in transport services"

Referencia:
Durand, A., Zijlstra, T., van Oort, N., Hoogendoorn-Lanser, S. y Hoogendoorn, S. (2021). "Access denied? Digital inequality in transport services". *Transport Reviews*. DOI: `10.1080/01441647.2021.1923584`.

Fuente revisada:
https://www.tandfonline.com/doi/abs/10.1080/01441647.2021.1923584

#### Que estudia

Es una revision conceptual y sistematica sobre como la digitalizacion de servicios de transporte puede generar desigualdad. Su foco no es solo el acceso fisico a tecnologias, sino tambien las habilidades, motivaciones, autonomia de uso y beneficios efectivos que las personas pueden extraer de herramientas digitales.

El aporte principal es que traslada la literatura general de brecha digital al dominio de transporte. Esto es importante porque en transporte la digitalizacion no es un lujo aislado: puede convertirse en requisito para acceder a informacion, tarifas, descuentos, planificacion o incluso pago.

#### Como sirve para tu tesis

Sirve como base teorica para argumentar que la variable de educacion superior no debe interpretarse solamente como "mas educacion implica preferencia por QR", sino como una proxy territorial de capacidades digitales, familiaridad tecnologica, acceso a servicios financieros y capacidad de aprovechar herramientas digitales.

En tu modelo, `share_cine18_universitaria_o_mas_micro_z` tiene un efecto fuerte y positivo sobre `QR_RED`. Durand et al. ayuda a interpretar ese resultado como parte de una desigualdad digital aplicada al transporte: zonas con mayor capital educativo pueden tener mayor capacidad de usar una app oficial de transporte, manejar medios de pago digitales, resolver fricciones tecnologicas y beneficiarse de informacion en tiempo real.

#### Que no permite afirmar

No permite afirmar causalmente que una persona con educacion universitaria usa mas QR. Tu variable es territorial y no individual. La lectura correcta es: los viajes que se originan en zonas con mayor proporcion de poblacion universitaria se asocian a mayor utilidad relativa de `QR_RED` frente a `BIP`.

Tampoco permite separar educacion de ingreso, bancarizacion o acceso a smartphone. En tu especificacion actual, educacion superior puede estar capturando un paquete de capital socioeconomico y digital.

#### Valor para el reporte

Alto. Deberia citarse en el marco interpretativo general, antes de discutir resultados. Es el paper que permite decir que la brecha digital en transporte es multidimensional y que la digitalizacion puede reproducir desigualdades existentes.

Texto util para adaptar:
> La asociacion positiva entre educacion superior territorial y uso relativo de `QR_RED` es consistente con la literatura de desigualdad digital en transporte, donde el acceso efectivo a servicios digitales depende no solo de la disponibilidad material de tecnologia, sino tambien de habilidades, motivacion, autonomia y capacidad de obtener beneficios de las herramientas digitales.

### 1.2 Boyko y Schaefer (2026) - "Smartphone apps for mobility access from a social inequality perspective"

Referencia:
Boyko, D. y Schaefer, K. J. (2026). "Smartphone apps for mobility access from a social inequality perspective: a systematic literature review". *European Transport Research Review*, 18, 21. DOI: `10.1186/s12544-026-00772-x`.

Fuente revisada:
https://link.springer.com/article/10.1186/s12544-026-00772-x

#### Que estudia

Es una revision sistematica reciente sobre apps de movilidad y desigualdad social. Revisa literatura que combina tres dimensiones: smartphone/apps, transporte/movilidad, e inclusion/exclusion/desigualdad. El paper identifica grupos vulnerables, barreras de acceso y medidas de mitigacion.

Su aporte principal es el concepto de "digital mobility inequalities": desigualdades que emergen cuando las barreras digitales y las barreras de movilidad se superponen. Por ejemplo, una persona puede vivir en una zona con mala oferta de transporte y, ademas, no poder acceder a soluciones digitales que podrian mejorar su movilidad.

#### Como sirve para tu tesis

Sirve especialmente para justificar por que `QR_RED` debe leerse como una alternativa tecnologicamente mediada. `QR_RED` no es solo un codigo QR: esta vinculado a una app oficial, a smartphone, posiblemente a cuenta, conectividad y familiaridad con herramientas digitales. Por tanto, su adopcion puede estar socialmente estratificada.

Tambien ayuda a justificar por que es razonable incorporar variables territoriales: la adopcion de apps no depende solo del individuo, sino tambien de condiciones territoriales, oferta de transporte, centralidad, disponibilidad de servicios y composicion social.

#### Que no permite afirmar

Es una revision general, no un estudio de pago QR ni de Santiago. No entrega coeficientes directamente comparables con tu modelo. Su utilidad es conceptual y de marco teorico, no de contraste cuantitativo.

Ademas, al estar publicado en 2026, es muy reciente. Eso es positivo para actualidad, pero si la tesis busca referencias clasicas, conviene combinarlo con Durand et al. (2021).

#### Valor para el reporte

Alto como soporte conceptual complementario. Conviene citarlo cuando expliques que la digitalizacion del acceso al transporte puede crear o amplificar barreras para ciertos grupos.

Texto util para adaptar:
> La literatura reciente sobre apps de movilidad advierte que asumir disponibilidad universal de smartphone, conectividad y habilidades digitales puede sobreestimar la preparacion de los usuarios para adoptar servicios basados en apps. En este sentido, la adopcion de `QR_RED` puede reflejar tanto preferencias de pago como diferencias territoriales en capital digital.

### 1.3 Brakewood y Kocur (2013) - "Unbanked Transit Riders and Open Payment Fare Collection"

Referencia:
Brakewood, C. y Kocur, G. (2013). "Unbanked Transit Riders and Open Payment Fare Collection". *Transportation Research Record*, 2351, 133-141. DOI: `10.3141/2351-15`.

Fuente revisada:
https://trid.trb.org/View/1240897

#### Que estudia

Analiza el problema de usuarios no bancarizados en sistemas de pago abiertos en transporte. El paper estima modelos de eleccion discreta para estudiar probabilidad de tener tarjetas de credito/debito o usar servicios financieros alternativos en Chicago.

El hallazgo relevante es que una fraccion significativa de usuarios no tiene tarjeta de credito/debito, y que esos usuarios pertenecen a grupos de menor ingreso, menor educacion y minorias etnicas. El paper discute alternativas para no excluirlos: mantener efectivo, tarjetas emitidas por agencia o tarjetas prepago cargables con efectivo.

#### Como sirve para tu tesis

Es de los mas directos para conectar educacion, ingreso y medios de pago en transporte. Aunque estudia open payment con tarjetas bancarias, no QR, el mecanismo es muy parecido: cuando un sistema de pago requiere infraestructura financiera/digital, la adopcion deja de ser homogenea.

Sirve para justificar dos puntos:

1. La eleccion de medio de pago esta mediada por acceso financiero y capital socioeconomico.
2. Normalizar `BIP` como referencia tiene sentido sustantivo: `BIP` es el medio tradicional, mas masivo, mientras que QR puede requerir capacidades adicionales.

#### Que no permite afirmar

No estudia apps ni QR, sino tarjetas bancarias/contactless. Por tanto, no debe usarse como evidencia directa de adopcion de `QR_RED`, sino como antecedente sobre inclusion financiera en tecnologias de pago de transporte.

#### Valor para el reporte

Muy alto para la rama educacion/NSE. Es el paper que vincula directamente menor educacion y menor ingreso con menor acceso a medios de pago abiertos en transporte.

Texto util para adaptar:
> La literatura sobre sistemas open payment muestra que la adopcion de nuevos medios de pago puede estar limitada por condiciones socioeconomicas y financieras. En particular, los usuarios no bancarizados tienden a pertenecer a grupos con menor ingreso y menor educacion, lo que refuerza la necesidad de interpretar la adopcion de QR desde una perspectiva de equidad.

## 2. Mobile ticketing y pago digital en transporte

### 2.1 Owusu-Agyemang et al. (2024) - "Transit made Easy"

Referencia:
Owusu-Agyemang, S., Simons, R. A., Henning, M. y Marshall, M. (2024). "Transit made Easy: Examining the adoption and impact of mobile fare payment technology among bus riders". *Transportation Research Interdisciplinary Perspectives*, 25, 101086. DOI: `10.1016/j.trip.2024.101086`.

Fuente revisada:
https://www.sciencedirect.com/science/article/pii/S2590198224000721

#### Que estudia

Evalua la adopcion e impacto de EZfare, una tecnologia de pago movil en transporte publico, usando encuestas a usuarios entre 2020 y 2022. El paper examina si la adopcion difiere segun atributos socioeconomicos/demograficos y si usuarios establecidos de EZfare viajan con mayor frecuencia.

Los resultados principales son muy utiles para tu tesis: ser no bancarizado o tener mas de 45 anos reduce los odds de usar EZfare, mientras que usuarios de ingresos altos son mucho mas propensos a adoptarlo. Tambien se observa mayor frecuencia de viajes entre usuarios establecidos.

#### Como sirve para tu tesis

Es probablemente el paper mas importante para defender la interpretacion de `QR_RED` como adopcion de pago movil. Tiene tres ventajas:

1. Estudia pago movil en buses, no solo tecnologia general.
2. Usa adopcion observada de una app real, no solo intencion declarada.
3. Encuentra heterogeneidad socioeconomica/demografica en la adopcion.

Para tu resultado de educacion universitaria, el paper no se centra directamente en educacion, pero si muestra que variables socioeconomicas y de acceso financiero explican adopcion. Esto permite conectar tu proxy territorial de educacion/NSE con evidencia internacional de mobile fare payment.

#### Que no permite afirmar

No estudia Santiago ni pago QR. Tampoco permite decir que el efecto de educacion en tu modelo sea causal. Ademas, EZfare opera en otro contexto institucional y tarifario.

#### Valor para el reporte

Muy alto. Deberia estar entre las referencias centrales de la seccion de resultados. Sirve para decir que tu hallazgo no es aislado: otros sistemas de pago movil en transporte muestran adopcion diferenciada por perfil socioeconomico.

Texto util para adaptar:
> La asociacion entre zonas de mayor educacion superior y mayor utilidad relativa de `QR_RED` es consistente con evidencia reciente sobre mobile fare payment, donde la adopcion de aplicaciones de pago en transporte se distribuye de forma desigual segun atributos socioeconomicos, bancarizacion y edad.

### 2.2 Brakewood et al. (2020) - "An evaluation of the benefits of mobile fare payment technology"

Referencia:
Brakewood, C., Ziedan, A., Hendricks, S. J., Barbeau, S. J. y Joslin, A. (2020). "An evaluation of the benefits of mobile fare payment technology from the user and operator perspectives". *Transport Policy*, 93, 54-66. DOI: `10.1016/j.tranpol.2020.04.015`.

Fuente revisada:
https://trid.trb.org/View/1705255

#### Que estudia

Evalua una app de pago movil desplegada en un sistema de buses en Tallahassee, Florida, desde la perspectiva de usuarios y operadores. Se levantan encuestas antes/despues a usuarios y encuestas a operadores de bus.

Los resultados indican que los usuarios de la app reportan gastar menos tiempo comprando pases y menos tiempo abordando. Los operadores tambien observan menor tiempo de validacion/cobro y menor tiempo de abordaje para usuarios de app. Sin embargo, la evidencia sobre aumento de viajes en transporte es limitada.

#### Como sirve para tu tesis

Este paper no es tanto sobre adopcion diferencial, sino sobre los mecanismos por los cuales una app de pago puede cambiar la experiencia de viaje:

1. Reduce friccion de compra.
2. Puede reducir tiempo de abordaje.
3. Puede mejorar experiencia de usuario y operacion.
4. Pero no necesariamente aumenta viajes de forma clara.

Para tu modelo, sirve para interpretar que `QR_RED` puede estar capturando conveniencia y menor friccion operativa, no solo un metodo de pago. Tambien ayuda a explicar por que el QR oficial podria tener una utilidad relativa distinta a `QR_OTHER`.

#### Que no permite afirmar

No sirve para explicar directamente el coeficiente de educacion universitaria, porque su foco no es la desigualdad socioeconomica de adopcion. Tampoco permite explicar la espera en transbordo.

#### Valor para el reporte

Alto, pero secundario respecto de Owusu-Agyemang et al. (2024). Conviene usarlo para discutir beneficios de la tecnologia y no para justificar brecha digital.

Texto util para adaptar:
> La literatura sobre mobile fare payment muestra que estas tecnologias pueden generar beneficios de experiencia y operacion, tales como menor tiempo de compra de pases y menor tiempo de abordaje. Por lo tanto, la eleccion de `QR_RED` puede reflejar una combinacion de adopcion tecnologica, conveniencia y menor friccion en el proceso de pago.

### 2.3 Wani et al. (2025) - "Digital payment adoption in public transportation"

Referencia:
Wani, S. A., Pani, A., Mohan, R. y Bhowmik, B. (2025). "Digital payment adoption in public transportation: Mediating role of mode choice segments in developing cities". *Transportation Research Part A*, 191, 104319. DOI: `10.1016/j.tra.2024.104319`.

Fuente revisada:
https://www.sciencedirect.com/science/article/abs/pii/S0965856424003677

#### Que estudia

Estudia adopcion de pago digital en transporte publico en Kota, India, una ciudad en desarrollo. Usa una metodologia en dos pasos: primero segmenta usuarios mediante Latent Class Cluster Analysis y luego evalua factores de adopcion usando modelos de clasificacion como Decision Tree, Random Forest y XGBoost.

El paper identifica que la adopcion de pago digital depende de uso previo de apps de viaje, tipo de telefono, disponibilidad de internet y edad. Tambien revisa literatura donde las variables sociodemograficas usuales incluyen educacion, ingreso, genero y empleo.

#### Como sirve para tu tesis

Es muy util por tres razones:

1. Es un contexto de ciudad en desarrollo, mas cercano a Santiago que estudios de EE.UU./Europa.
2. Conecta pago digital con segmentacion de usuarios.
3. Refuerza la idea de que la adopcion no es uniforme, sino que depende de caracteristicas tecnologicas y sociodemograficas.

Para tu modelo, sirve para defender la separacion entre `QR_RED` y `QR_OTHER`. Si distintos segmentos adoptan de manera distinta tecnologias digitales, entonces tiene sentido no tratar todo QR como una sola alternativa.

#### Que no permite afirmar

No usa un MNL de eleccion de medio de pago como el tuyo; usa segmentacion y modelos de machine learning. Por tanto, el valor es sustantivo/comparativo, no metodologico directo.

#### Valor para el reporte

Muy alto. Es la mejor referencia para conectar tu caso con "developing cities" y para justificar segmentacion/heterogeneidad.

Texto util para adaptar:
> Estudios recientes en ciudades en desarrollo muestran que la adopcion de pago digital en transporte depende de variables tecnologicas y sociodemograficas, y que los factores relevantes pueden variar por segmento de usuario. Esto respalda la decision de modelar separadamente `QR_RED` y `QR_OTHER`, en lugar de agrupar todo pago QR en una unica alternativa.

## 3. Apps, informacion en tiempo real y valor de la espera

### 3.1 Watkins et al. (2011) - "Where Is My Bus?"

Referencia:
Watkins, K. E., Ferris, B., Borning, A., Rutherford, G. S. y Layton, D. (2011). "Where Is My Bus? Impact of mobile real-time information on the perceived and actual wait time of transit riders". *Transportation Research Part A*, 45(8), 839-848. DOI: `10.1016/j.tra.2011.06.010`.

Fuente revisada:
https://ideas.repec.org/a/eee/transa/v45y2011i8p839-848.html

#### Que estudia

Estudia el efecto de informacion movil en tiempo real, mediante OneBusAway, sobre la espera percibida y real de usuarios de bus en Seattle. Los investigadores observan pasajeros llegando a paraderos, miden su espera y preguntan cuanto creen haber esperado.

El hallazgo clave es que usuarios sin informacion en tiempo real tienden a percibir la espera como mayor que la espera medida, mientras que usuarios con informacion en tiempo real no presentan esa sobrepercepcion. Ademas, usuarios de informacion en tiempo real reportan esperas tipicas menores y esperan casi dos minutos menos que usuarios con informacion tradicional.

#### Como sirve para tu tesis

Es la referencia mas directa para interpretar `T_ESPERA_TRASB`. Si usuarios de `QR_RED` estan mas conectados a la app oficial y a informacion en tiempo real, es plausible que la espera en transbordo tenga menor desutilidad percibida o sea gestionada de forma distinta.

Esto calza con el comentario de tu profesora: si el usuario tiene informacion, una espera mayor puede ser menos penalizante porque permite planificar, anticipar o usar ese tiempo de otra forma.

#### Que no permite afirmar

Tu modelo no observa directamente si el usuario consulto informacion en tiempo real. Por lo tanto, no puedes decir que el coeficiente no significativo de `T_ESPERA_TRASB` en `QR_RED` se debe causalmente a informacion en tiempo real. Debe plantearse como hipotesis compatible con la literatura.

#### Valor para el reporte

Muy alto. Es la referencia central para la interpretacion de espera.

Texto util para adaptar:
> La ausencia de una desutilidad significativa de la espera en transbordo para `QR_RED` es compatible con evidencia previa segun la cual la informacion movil en tiempo real reduce la espera percibida y permite ajustar el momento de llegada al paradero. Dado que `QR_RED` esta asociado a una app oficial, este resultado puede interpretarse como una hipotesis de menor penalizacion percibida de la espera para usuarios con mayor acceso a informacion.

### 3.2 Brakewood y Watkins (2019) - "A literature review of the passenger benefits of real-time transit information"

Referencia:
Brakewood, C. y Watkins, K. (2019). "A literature review of the passenger benefits of real-time transit information". *Transport Reviews*, 39(3), 327-356. DOI: `10.1080/01441647.2018.1472147`.

Fuente revisada:
https://ideas.repec.org/a/taf/transr/v39y2019i3p327-356.html

#### Que estudia

Es una revision de literatura sobre beneficios de informacion en tiempo real para pasajeros de transporte publico. Resume evidencia sobre comportamiento y percepciones.

Los beneficios principales se relacionan con reduccion de tiempos de espera, reduccion de tiempo total por cambios de ruta, aumento de uso de transporte, mayor satisfaccion y mejor percepcion de seguridad.

#### Como sirve para tu tesis

Sirve para que la interpretacion de `T_ESPERA_TRASB` no dependa de un solo estudio. Watkins et al. (2011) es evidencia puntual; Brakewood y Watkins (2019) muestra que existe un cuerpo de literatura mas amplio que encuentra beneficios de informacion en tiempo real.

Tambien ayuda a explicar por que la app oficial puede importar aunque el modelo sea de medio de pago: la app puede combinar pago, informacion, planificacion y percepcion de control.

#### Que no permite afirmar

No habla especificamente de QR ni de pago. Es informacion de transporte, no mobile ticketing. Por eso conviene citarlo junto con mobile fare payment, no en reemplazo.

#### Valor para el reporte

Muy alto como respaldo general. Conviene usarlo junto con Watkins et al. (2011).

Texto util para adaptar:
> La literatura sobre informacion en tiempo real sugiere que sus beneficios para pasajeros se concentran en la experiencia de espera, la satisfaccion, la percepcion de seguridad y la posibilidad de ajustar decisiones de viaje. Esto entrega un marco plausible para interpretar diferencias en la penalizacion de espera entre alternativas de pago asociadas o no a una app oficial.

### 3.3 Kaplan et al. (2017) - "The role of information systems in non-routine transit use of university students"

Referencia:
Kaplan, S., Monteiro, M. M., Anderson, M. K., Nielsen, O. A. y Dos Santos, E. M. (2017). "The role of information systems in non-routine transit use of university students: Evidence from Brazil and Denmark". *Transportation Research Part A*, 95, 34-48. DOI: `10.1016/j.tra.2016.10.029`.

Fuente revisada:
https://orbit.dtu.dk/en/publications/the-role-of-information-systems-in-non-routine-transit-use-of-uni

#### Que estudia

Estudia la relacion entre sistemas de informacion, intenciones de uso de transporte y uso no rutinario en estudiantes universitarios, con evidencia de Copenhagen y de Recife/Natal en Brasil. El marco teorico se basa en Technology Acceptance Model y usa modelos de ecuaciones estructurales.

Los resultados muestran que calidad y fuente de informacion explican uso de transporte; que informacion de calidad esta vinculada a nivel de servicio y familiaridad; y que informacion en tiempo real se relaciona con calidad de informacion y familiaridad.

#### Como sirve para tu tesis

Este paper es especialmente bueno porque combina tres elementos que aparecen en tu tesis:

1. Informacion de transporte.
2. Aceptacion tecnologica.
3. Contexto latinoamericano, aunque sea Brasil y poblacion universitaria.

Tambien conecta con tu variable de educacion superior: en zonas con mayor presencia universitaria, puede haber mayor familiaridad con sistemas de informacion y mayor adopcion de herramientas digitales de movilidad.

#### Que no permite afirmar

El estudio trabaja con estudiantes universitarios y uso de informacion, no con pago QR. Por tanto, su transferencia al caso de Red debe ser cuidadosa. Sirve para conectar informacion y aceptacion tecnologica, no para probar adopcion de pago digital.

#### Valor para el reporte

Alto. Lo usaria despues de Watkins et al. y Brakewood/Watkins, como puente entre informacion de transporte, TAM y contexto latinoamericano/universitario.

Texto util para adaptar:
> La evidencia sobre sistemas de informacion en transporte muestra que la calidad de informacion, la familiaridad y la disponibilidad de informacion en tiempo real se asocian con el uso de transporte y con la percepcion de utilidad/facilidad de uso. Esto refuerza la interpretacion de que `QR_RED` puede estar capturando una experiencia digital mas amplia que el acto de pago.

## Papers buenos pero secundarios

| Paper | Por que no queda en los tres principales |
| --- | --- |
| Velazquez, Kaplan y Monzon (2018), app de informacion de transporte | Es util para TAM y apps, pero Kaplan et al. (2017) es mas cercano por incluir Brasil y por conectar informacion con uso de transporte. Puede quedar como cita secundaria. |
| Pike et al. (2024), open-loop payment challenges | Muy util para discusion aplicada, pero menos academico/central que Brakewood y Kocur (2013) u Owusu-Agyemang et al. (2024). |
| Brakewood y Kocur (2011), contactless bank cards | Buen antecedente metodologico, pero Brakewood y Kocur (2013) es mas util para equidad porque explicita no bancarizacion, menor ingreso y menor educacion. |
| Brakewood, Macfarlane y Watkins (2015), RTI y ridership NYC | Buen complemento sobre efectos agregados, pero para `T_ESPERA_TRASB` importan mas espera percibida/real y beneficios de RTI. |

## Sintesis para usar en la tesis

La lectura conjunta permite formular tres afirmaciones defendibles:

1. La adopcion de pago digital en transporte no es homogenea. Depende de edad, ingreso, bancarizacion, acceso a telefono/internet, uso previo de apps y capacidades digitales. Por eso es razonable que la variable territorial de educacion superior tenga un efecto fuerte sobre `QR_RED`.

2. `QR_RED` debe interpretarse como una alternativa tecnologicamente mediada. No solo representa un medio de pago, sino tambien una posible puerta de entrada a informacion, planificacion y menor friccion de uso del sistema.

3. La espera en transbordo para usuarios de `QR_RED` puede tener una penalizacion distinta porque la informacion en tiempo real reduce la incertidumbre y la espera percibida. En el reporte esto debe plantearse como hipotesis interpretativa compatible con la literatura, no como causalidad probada.

## Recomendacion de uso en el reporte

Para no sobrecargar el reporte, usaria solo seis referencias en el texto principal:

1. Durand et al. (2021) para brecha digital en transporte.
2. Brakewood y Kocur (2013) para no bancarizacion, educacion/ingreso y medios de pago.
3. Owusu-Agyemang et al. (2024) para adopcion de mobile fare payment.
4. Wani et al. (2025) para pago digital en transporte en ciudad en desarrollo y segmentacion.
5. Watkins et al. (2011) para espera percibida/real.
6. Brakewood y Watkins (2019) para revision general de beneficios de RTI.

Kaplan et al. (2017) lo dejaria como cita adicional si quieres reforzar el componente de informacion/TAM y el puente con America Latina.
