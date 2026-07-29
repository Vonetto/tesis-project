# Capítulo 4. Resultados

## 4.1 Propósito del capítulo

Este capítulo reunirá los resultados empíricos de la tesis. En la versión actual del manuscrito, la sección queda planteada como una estructura de avance, porque el modelo final aún no está cerrado. El objetivo es dejar preparado el orden de presentación de resultados sin afirmar conclusiones definitivas antes de estabilizar la estrategia de modelamiento.

La lógica del capítulo seguirá una secuencia de menor a mayor complejidad. Primero se presentará la caracterización descriptiva de `BIP` y QR. Luego se reportarán resultados preliminares a nivel tarjeta, incluyendo modelos interpretables, benchmark predictivo y segmentación descriptiva. Finalmente, se incorporará el análisis territorial e interanual como puente hacia una posible etapa de modelamiento zonal.

## 4.2 Caracterización empírica de `BIP` y QR

Esta sección presentará la evidencia descriptiva construida a partir de la base analítica definida en el Capítulo 3. Debe responder preguntas básicas antes de introducir modelos: qué proporción del uso observado corresponde a QR, cómo difiere la intensidad de uso entre tarjetas `BIP` y QR, en qué horarios y modos aparece más QR, y qué tan distintas son las distribuciones entre categorías.

La descripción de datos propiamente tal pertenece al capítulo metodológico: fuentes, unidades, universos, soporte y construcción de variables. En este capítulo se mostrarán los resultados descriptivos derivados de esa base mediante tablas, mapas y gráficos seleccionados.

Los resultados deben presentarse con cautela. Las diferencias descriptivas entre `BIP` y QR no implican separación perfecta entre usuarios ni mecanismos causales. La lectura esperada es que QR representa una fracción minoritaria del uso observado, con diferencias agregadas de intensidad, temporalidad y contexto modal, pero con solapamiento amplio entre distribuciones.

**Pendiente:** seleccionar una tabla de composición general y figuras del EDA QR vs BIP que comuniquen composición, intensidad y diferencias temporales sin sobrecargar el capítulo.

## 4.3 Señal territorial y residencial

Esta sección reportará la relación descriptiva entre QR y territorio. Incluirá mapas o tablas que muestren diferencias por residencia, origen de viaje, macrozona y variables territoriales candidatas. La lectura debe distinguir explícitamente entre atributos de zona y atributos individuales.

El propósito no es afirmar que una característica territorial causa adopción QR, sino mostrar que el fenómeno no se distribuye homogéneamente en la ciudad. En particular, se espera discutir señales asociadas a educación residencial, composición socioeconómica, centralidad urbana, presencia de Metro, contexto operacional y acceso físico a carga `BIP`.

**Pendiente:** decidir qué figuras del EDA se incorporan en cuerpo principal y cuáles pasan a anexo.

## 4.4 Modelos preliminares a nivel tarjeta

Esta sección presentará resultados preliminares de modelos a nivel `id_tarjeta`. La unidad de análisis será la tarjeta como proxy operacional de usuario, no el viaje individual. El foco será evaluar qué variables se asocian con pertenecer a `BIP`, `QR_OTHER` o `QR_RED`.

La especificación interpretable principal será un logit multinomial con `BIP` como categoría de referencia. Los resultados se reportarán de forma parsimoniosa, priorizando signos, magnitudes interpretables y diferencias entre `QR_RED` y `QR_OTHER`. Si se incluyen modelos binarios QR frente a `BIP`, deberán presentarse como lectura agregada y no como sustituto del contraste multiclase.

**Pendiente:** seleccionar la especificación de tarjeta que se presentará como preliminar y verificar que sus resultados estén actualizados.

## 4.5 Benchmark predictivo

Esta sección reportará el benchmark predictivo basado en XGBoost u otro modelo flexible equivalente. Su función será evaluar el techo predictivo de las variables disponibles y contrastar si las señales descriptivas tienen capacidad de separación fuera de modelos lineales.

La interpretación debe ser acotada. Un buen desempeño predictivo no prueba causalidad, y un desempeño moderado no invalida las asociaciones descriptivas. El benchmark ayuda a responder cuánta información contienen las variables observadas para distinguir QR de `BIP`, y si la separación es más clara para `QR_RED` que para `QR_OTHER`.

**Pendiente:** definir métricas finales y tabla/figura resumida para no convertir esta sección en un reporte completo de machine learning.

## 4.6 Segmentación descriptiva mediante NMF

Esta sección presentará, si se mantiene en el manuscrito, la segmentación descriptiva a nivel tarjeta. Los segmentos se construirán sin usar QR/BIP como input y luego se cruzarán post-hoc con el medio de pago observado. Esto permite evaluar si existen perfiles de uso o contexto donde QR, `QR_RED` o `QR_OTHER` aparecen sobrerrepresentados.

El resultado debe leerse como tipología descriptiva. No se debe afirmar que un segmento causa adopción QR ni que NMF identifica grupos sociales observados directamente. La utilidad de esta sección está en resumir patrones complejos de movilidad, territorio y contexto operacional de manera interpretable.

**Pendiente:** decidir si NMF entra en el cuerpo principal o queda como anexo metodológico/descriptivo.

## 4.7 Cambio interanual y análisis zonal 2024-2025

Esta sección incorporará el análisis territorial e interanual. Debe distinguir entre nivel QR inicial, cambio bruto, crecimiento relativo respecto de la tendencia global y contribución volumétrica. Esta distinción es central porque las zonas que más crecen en tasa no necesariamente son las que más explican el aumento agregado.

Los resultados zonales se usarán como extensión territorial del análisis a nivel tarjeta y como motivación para una posible segunda etapa de modelamiento. La sección puede incluir mapas de crecimiento, tipologías top/middle/bottom, mapas bivariados, contribución por macrozona y sensibilidad mínima.

**Pendiente:** definir si este análisis queda como resultado descriptivo final o si se transformará en modelo zonal formal.

## 4.8 Síntesis provisional

La versión final de esta sección debe cerrar el capítulo separando con claridad tres tipos de evidencia: descripción de datos, asociaciones estadísticas preliminares y resultados del modelo final. Mientras el modelo definitivo no esté cerrado, la síntesis debe mantenerse como provisional.

En el avance actual, la lectura esperada es que la adopción QR puede estudiarse de forma coherente a nivel tarjeta y que el análisis zonal aporta una dimensión territorial/interanual complementaria. Los resultados preliminares deben usarse para justificar la estrategia de modelamiento, no para cerrar conclusiones sustantivas definitivas.

## Pendientes para versión final

- Elegir figuras descriptivas principales y anexos.
- Confirmar especificación preliminar a nivel tarjeta.
- Definir si se reporta logit multinomial, XGBoost y NMF en cuerpo principal o parcialmente en anexos.
- Decidir el rol final del análisis zonal: resultado descriptivo, modelo principal o extensión.
- Actualizar texto una vez que los resultados finales estén estabilizados.
