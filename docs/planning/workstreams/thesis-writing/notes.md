# Notes — Thesis Writing

## 2026-05-07 — Workstream de escritura de tesis creado
- Se creó un workstream separado para registrar memoria, decisiones y próximos pasos de la escritura del manuscrito formal de tesis:
  - `docs/planning/workstreams/thesis-writing/task_plan.md`
  - `docs/planning/workstreams/thesis-writing/notes.md`
- Motivo:
  - separar la memoria de escritura de tesis del workstream técnico `od-buffers-nested-logit`;
  - evitar que decisiones narrativas, estructura de capítulos y pendientes editoriales queden mezclados con detalles de estimación/modelamiento.

## 2026-05-07 — Narrativa vigente de tesis
- Archivo base:
  - `docs/thesis/narrativa_actual_tesis.md`
- Narrativa actual:
  - la tesis se centra en adopción de tecnologías digitales en transporte público observada mediante elección de medio de pago;
  - alternativas principales: `BIP`, `QR_RED`, `QR_OTHER`;
  - `BIP` se interpreta como medio tradicional/base;
  - `QR_OTHER` representa canales QR digitales heterogéneos;
  - `QR_RED` se interpreta cuidadosamente como señal observable de inserción en un canal digital oficial del sistema.
- Límite interpretativo central:
  - el dato identifica medio de pago, no uso efectivo de app, consulta de información en tiempo real ni mecanismo causal individual.
- Líneas que quedan fuera de la promesa principal por ahora:
  - inercia;
  - clustering;
  - segmentación de usuarios;
  - ML/SHAP como eje de tesis.

## 2026-05-07 — Estructura formal de tesis
- La plantilla LaTeX externa define la estructura principal:
  - Introducción;
  - Revisión de la literatura;
  - Materiales y métodos;
  - Resultados;
  - Discusión;
  - Conclusiones;
  - Glosario;
  - Bibliografía;
  - Anexos.
- Archivos externos de referencia:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/contenido.tex`
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/02_revision_literatura.tex`
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_2/MANUAL_NORMALIZACI_N_TESIS.pdf`
- Decisión de trabajo:
  - redactar primero en Markdown dentro del repo;
  - migrar a LaTeX solo cuando cada capítulo esté revisado y aprobado.

## 2026-05-07 — Capítulo 1: Introducción
- Borrador creado:
  - `docs/thesis/capitulos/01_introduccion_borrador.md`
- Contenido actual:
  - contexto de digitalización del transporte público;
  - motivación operacional: planificación, gestión de demanda, focalización de incentivos y políticas;
  - problema de investigación centrado en elección de medio de pago;
  - alternativas `BIP`, `QR_RED`, `QR_OTHER`;
  - pregunta de investigación;
  - objetivo general y objetivos específicos;
  - alcance y límites;
  - organización preliminar de la tesis.
- Ajustes ya incorporados:
  - se reforzó por qué interesa especialmente `QR_RED`;
  - se definió `ZONA777` como zonificación usada por el sistema de transporte público de Santiago para organizar información espacial de viajes;
  - se agregó continuidad con la tesis original: la pregunta amplia por tecnologías digitales se acota empíricamente al medio de pago observado.

## 2026-05-07 — Capítulo 2: Revisión de literatura
- Borrador creado:
  - `docs/thesis/capitulos/02_revision_literatura_borrador.md`
- Estructura actual:
  - propósito del capítulo;
  - digitalización del transporte público y medios de pago;
  - adopción tecnológica, brecha digital y equidad en transporte;
  - información en tiempo real, aplicaciones móviles y experiencia de espera;
  - evidencia empírica sobre pago móvil y adopción de herramientas digitales;
  - modelos para estudiar adopción y elección en transporte;
  - síntesis y brecha que aborda la tesis.
- Papers centrales revisados y usados:
  - Durand et al. (2021), `Access denied? Digital inequality in transport services`;
  - Owusu-Agyemang et al. (2024), `Transit made Easy`;
  - Watkins et al. (2011), `Where Is My Bus?`;
  - Brakewood y Watkins (2019), revisión sobre real-time transit information;
  - Brakewood y Kocur (2013), `Unbanked Transit Riders and Open Payment Fare Collection`;
  - Kaplan et al. (2017), información de transporte, TAM y estudiantes universitarios.
- Evidencia textual verificada:
  - Durand et al. (2021): vulnerabilidad por edad, ingreso, educación, etnicidad, género y región; digital inequality en transporte como fenómeno multidimensional.
  - Owusu-Agyemang et al. (2024): ser unbanked o mayor de 45 reduce odds de uso de EZfare; altos ingresos aumentan adopción.
  - Watkins et al. (2011): usuarios de RTI esperan casi 2 minutos menos y la RTI reduce espera percibida.
  - Brakewood y Watkins (2019): beneficios principales de RTI incluyen reducción de espera, cambios de ruta, satisfacción, seguridad y uso de transporte.
  - Brakewood y Kocur (2013): usuarios sin bankcards tienden a menor ingreso, menor educación, desempleo y minorías.
  - Kaplan et al. (2017): calidad de información y RTI son factores relevantes para uso de transporte en estudiantes universitarios.
- Decisión sobre Boyko y Schaefer (2026):
  - se leyó con mayor detalle;
  - aporta como revisión reciente sobre apps de movilidad, desigualdad social y `digital mobility inequalities`;
  - se decidió dejarlo fuera por ahora para no sobrecargar el capítulo ni desviar el foco desde pago/RTI hacia apps de movilidad en general.
- Ajuste ya incorporado:
  - se definió `pago abierto` / `open payment` para evitar ambigüedad;
  - se aclaró que el caso de Santiago con `QR_RED`/`QR_OTHER` no es idéntico a open payment con tarjetas bancarias.

## 2026-05-07 — Capítulo 3: Materiales y métodos
- Borrador creado:
  - `docs/thesis/capitulos/03_materiales_metodos_borrador.md`
- Contenido actual:
  - diseño general del estudio;
  - fuentes de datos;
  - preprocesamiento, depuración y construcción de atributos de viaje;
  - unidad de análisis, alternativas y muestra;
  - enriquecimiento territorial mediante `ZONA777`;
  - construcción de variables;
  - especificación MNL;
  - parametrización e interpretación;
  - estrategia de estimación y evaluación;
  - consideraciones metodológicas y límites.
- Decisiones metodológicas documentadas:
  - unidad de análisis = viaje individual;
  - modelo principal = MNL;
  - `BIP` como alternativa base para variables comunes;
  - tiempos y transbordos como variables alternativa-específicas;
  - variables territoriales interpretadas a nivel de zona de origen.
- Ajustes ya incorporados:
  - se incluyó preprocesamiento de viajes, filtros y reconstrucción de atributos;
  - se mencionó referencia metodológica a Núñez Sepúlveda (2015) para filtros/indicadores de calidad de servicio;
  - se mencionó recálculo/imputación de esperas de buses/Metro con respaldo en literatura y datos operacionales;
  - se explicó que Biogeme y Larch son bibliotecas especializadas en modelos de elección discreta usadas en investigación aplicada en transporte.

## 2026-05-07 — Pendientes editoriales generales
- Convertir referencias a BibTeX y definir estilo de citación.
- Confirmar fuente formal/documental de `ZONA777`.
- Revisar si los capítulos deben mantener notas de `Pendientes para versión final` o moverlas solo a planning.
- Actualizar Capítulo 3 cuando se cierre:
  - tamaño definitivo de muestra;
  - modelo principal final;
  - variables censales nuevas (`share_mujeres_z`, `share_asistencia_parv_z`) si entran o quedan como sensibilidad.
- No iniciar Capítulo 4 hasta tener resultados finales estabilizados.
