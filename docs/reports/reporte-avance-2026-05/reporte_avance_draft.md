# Reporte de avance - borrador actualizado

**Nombre estudiante:** Juan Vicente Onetto Romero

**Profesor/a guía:** Eduardo Graells-Garrido

**Profesor/a co-guía:** Jacqueline Arriagada Fernández

**Nombre tesis:** Tecnologías digitales y su impacto en el comportamiento de viaje en transporte público.

## I. Principales avances a la fecha

Desde el último reporte se avanzó principalmente en la consolidación de la narrativa, la especificación del modelo y la escritura del manuscrito. La tesis se reformuló con un foco más preciso: estudiar la adopción de tecnologías digitales en transporte público a partir de la elección del medio de pago observado en viajes individuales, distinguiendo entre BIP, QR RED y otros QR.

En la parte metodológica, se consolidó un modelo logit multinomial con BIP como alternativa base para las variables comunes, y con variables de viaje específicas por alternativa cuando corresponde. Además, se incorporaron nuevas fuentes de información territorial que no estaban plenamente desarrolladas en el reporte anterior: variables del Censo 2024 y variables de OpenStreetMap asociadas a la zona de origen del viaje. Estas permiten caracterizar el entorno territorial de cada viaje mediante indicadores sociodemográficos, equipamientos urbanos e infraestructura de transporte.

También se elaboró un reporte metodológico específico del modelo logit territorial, incluyendo definición de variables, función de utilidad, estrategia de estimación, tablas de parámetros, odds ratios e interpretación de resultados. Este documento servirá como base para los capítulos de resultados y metodología de la tesis.

Finalmente, se redactaron borradores avanzados de los capítulos de Introducción, Revisión de literatura y Materiales y métodos. Estos capítulos aún requieren ajustes, pero ya existe una estructura clara para el manuscrito.

## II. Estado de redacción del manuscrito

| Capítulo | Estado | Comentario |
|---|---:|---|
| 1. Introducción | 1 | Borrador avanzado. |
| 2. Revisión de literatura | 1 | Borrador avanzado, con literatura sobre pagos digitales, brecha digital e información en tiempo real. |
| 3. Materiales y métodos | 1 | Borrador avanzado, pendiente de ajustar con la especificación definitiva. |
| 4. Resultados | 0 | Pendiente de cierre del modelo principal. |
| 5. Discusión | 0 | Pendiente. |
| 6. Conclusiones | 0 | Pendiente. |

## III. Principales dificultades

Una dificultad importante ha sido la disponibilidad de fuentes complementarias actualizadas. En particular, se exploró el uso de la Encuesta Origen Destino para incorporar información socioeconómica y de comportamiento de viaje, pero hasta ahora solo se ha encontrado acceso operativo a la versión 2012 para Santiago. Esto limita su integración directa con datos de viajes 2024-2025 y obliga a tratarla, por ahora, como una posible fuente de contexto o sensibilidad histórica.

Otra dificultad ha sido mantener algunas líneas originalmente planteadas en la propuesta, como clusterización o segmentación de usuarios, debido a la naturaleza de los datos disponibles. La información transaccional permite observar viajes y medios de pago, pero no necesariamente construir perfiles individuales robustos entre todos los métodos de pago. Por esto, algunas ideas iniciales debieron reformularse o dejarse como extensiones posibles.

También ha sido desafiante estabilizar la especificación del modelo, porque se han evaluado distintas combinaciones de variables de viaje, Censo, OpenStreetMap e infraestructura. Esto ha requerido comparar incrementalmente modelos, revisar significancia, interpretar signos y evitar que la especificación final se vuelva innecesariamente compleja.

## IV. Próximos pasos y carta Gantt

| Actividad | Mayo | Junio | Julio |
|---|:---:|:---:|:---:|
| Cerrar especificación del modelo principal y sensibilidades | X | X |  |
| Generar tablas finales, odds ratios y figuras |  | X | X |
| Ajustar capítulos 1, 2 y 3 | X | X |  |
| Redactar capítulo de resultados |  | X | X |
| Redactar discusión y conclusiones |  |  | X |
| Migrar manuscrito a LaTeX y consolidar bibliografía |  | X | X |
| Revisión con profesores y ajustes finales | X | X | X |

## V. Síntesis

El trabajo pasó de una etapa exploratoria a una etapa de consolidación. Actualmente existe una narrativa más clara, una especificación econométrica principal definida, una base enriquecida con variables de viaje, Censo y OpenStreetMap, y tres capítulos redactados en versión avanzada.
