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

## 2026-07-06 — Reorientación del Capítulo 1
- Archivo actualizado:
  - `docs/thesis/capitulos/01_introduccion_borrador.md`
- Cambio narrativo principal:
  - la introducción deja de quedar comprometida con un modelo final MNL a nivel viaje y con `QR_RED`/`QR_OTHER` como eje obligatorio;
  - el foco pasa a adopción observada de pagos QR frente a `BIP`, patrones de uso, territorio, operación e interanualidad 2024-2025.
- Decisiones de redacción:
  - `QR_RED` y `QR_OTHER` quedan como desagregación posible cuando la pregunta y los datos lo justifiquen;
  - la pregunta principal se formula de manera amplia: distribución de la adopción QR y asociación con uso, operación y territorio;
  - se agrega una pregunta complementaria sobre crecimiento zonal 2024-2025;
  - los objetivos incluyen descripción QR vs `BIP`, construcción de base analítica, distribución territorial, cambio interanual, variables candidatas y comparación de estrategias de modelamiento.
- Límite metodológico reforzado:
  - el trabajo no promete modelar inercia o hábito como eje central;
  - la segmentación y los modelos predictivos solo pueden entrar como herramientas descriptivas/complementarias;
  - el medio de pago se interpreta como señal observable, no como mecanismo individual causal.

## 2026-07-06 — Avance del manuscrito con metodología principal a nivel tarjeta
- Archivos actualizados:
  - `docs/thesis/capitulos/01_introduccion_borrador.md`;
  - `docs/thesis/capitulos/03_materiales_metodos_borrador.md`;
  - `docs/thesis/capitulos/04_resultados_borrador.md`.
- Decisión metodológica para el avance:
  - usar `id_tarjeta` como unidad principal del manuscrito para estudiar adopción/perfil QR;
  - tratar `id_tarjeta` como proxy operacional de usuario, no como persona observada;
  - mantener el análisis zonal 2024-2025 como extensión territorial/interanual y posible segunda etapa de modelamiento.
- Cambio en Capítulo 1:
  - se ajustaron objetivos para permitir modelos a nivel tarjeta, benchmarks predictivos, segmentación descriptiva y análisis zonal;
  - se removió la idea de que segmentación/ML quedan completamente fuera del alcance;
  - se aclaró que esas herramientas no prueban causalidad ni mecanismos individuales.
- Cambio en Capítulo 3:
  - se reemplazó el borrador anterior, que estaba amarrado a viaje individual y MNL de viaje;
  - la nueva estructura cubre diseño general, fuentes, preprocesamiento, unidad tarjeta, unidad zonal, variables por familias, logit/multinomial, XGBoost, NMF y límites metodológicos;
  - se dejó explícito que XGBoost es benchmark/techo predictivo y NMF es tipología descriptiva post-hoc.
- Capítulo 4:
  - se creó un esqueleto de Resultados sin conclusiones definitivas;
  - incluye secciones para caracterización QR vs BIP, señal territorial, modelos preliminares a nivel tarjeta, benchmark predictivo, NMF y análisis zonal;
  - los resultados finales quedan pendientes hasta estabilizar especificación y figuras.
- Guardrail:
  - no migrar estos cambios a LaTeX hasta que el usuario revise y apruebe los Markdown;
  - evitar reintroducir el viaje individual como unidad principal del manuscrito salvo que se decida explícitamente.

## 2026-07-06 — Descripción de datos incorporada explícitamente
- Archivo actualizado:
  - `docs/thesis/capitulos/03_materiales_metodos_borrador.md`;
  - `docs/thesis/capitulos/04_resultados_borrador.md`.
- Decisión editorial:
  - la descripción de datos pertenece al Capítulo 3, junto con fuentes, unidades analíticas, universos, soporte y construcción de variables;
  - el Capítulo 4 queda para evidencia empírica descriptiva: tablas, mapas y gráficos derivados de esa base.
- Cambio aplicado:
  - se agregó la subsección `3.3 Descripción de los datos analíticos`;
  - se ajustó `4.2` para llamarse `Caracterización empírica de BIP y QR`, evitando duplicar la descripción metodológica de datos.
- Pendiente:
  - completar en la versión final una tabla corta con tamaño de universos, composición `BIP`/QR, desagregación `QR_RED`/`QR_OTHER`, soporte por año y cobertura territorial.

## 2026-07-06 — Capítulo 1 migrado a LaTeX
- Archivo externo actualizado:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/01_introduccion.tex`.
- Cambio aplicado:
  - se migró la introducción revisada desde Markdown al capítulo LaTeX formal de la plantilla;
  - el capítulo mantiene el foco amplio en adopción observada de pagos QR frente a `BIP`, patrones de uso, operación, territorio e interanualidad;
  - se define `ZONA777` brevemente en la introducción y se mantiene `id_tarjeta` como proxy operacional de usuario;
  - los objetivos quedan compatibles con metodología principal a nivel tarjeta y análisis zonal como extensión territorial/interanual.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutó correctamente en la plantilla externa;
  - el PDF se generó sin errores de compilación asociados al capítulo;
  - quedaron advertencias normales de primera pasada sobre referencias/lastpage y bibliografía vacía.
- Pendiente:
  - revisión editorial del usuario sobre extensión, tono y balance entre tarjeta/zona antes de migrar nuevos capítulos.

## 2026-07-06 — Capítulo 2 migrado a LaTeX
- Archivo externo actualizado:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/02_revision_literatura.tex`.
- Cambio aplicado:
  - se migró la revisión de literatura al capítulo LaTeX formal;
  - se corrigió el foco del borrador para no quedar amarrado a viaje individual ni a `QR_RED`/`QR_OTHER` como eje obligatorio;
  - el capítulo queda centrado en adopción QR frente a `BIP`, brecha digital, pago móvil, información en tiempo real, métodos interpretables/predictivos/descriptivos y lectura territorial.
- Decisiones de redacción:
  - se mantiene `QR_RED`/`QR_OTHER` como desagregación posible, no como promesa obligatoria;
  - XGBoost queda presentado como benchmark/techo predictivo, no como explicación causal;
  - NMF queda presentado como segmentación descriptiva post-hoc;
  - las variables territoriales se interpretan como agregados zonales, no como atributos individuales.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutó correctamente en la plantilla externa;
  - el PDF se generó sin errores asociados al capítulo;
  - quedan advertencias normales de primera pasada sobre referencias/lastpage y bibliografía vacía.
- Pendiente:
  - convertir referencias autor-año a entradas BibTeX y reemplazar por citas formales;
  - decidir si se agrega una referencia reciente adicional sobre apps de movilidad y desigualdad social.

## 2026-07-06 — Capítulo 3 migrado parcialmente a LaTeX
- Archivo externo actualizado:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/03_materiales_metodos.tex`.
- Alcance aplicado:
  - se migró la estructura base de Materiales y métodos;
  - se incluyeron las partes estables: diseño general, fuentes, unidad tarjeta, unidad zonal, construcción de variables, estrategia preliminar de modelamiento y límites metodológicos;
  - se dejó la descripción cuantitativa de datos en versión general, sin tablas ni figuras todavía.
- Decisiones de redacción:
  - el capítulo mantiene `id_tarjeta` como unidad principal para adopción/perfiles;
  - la unidad zonal queda explícitamente como complemento territorial/interanual;
  - XGBoost queda como benchmark predictivo y NMF como segmentación descriptiva post-hoc;
  - se incluyeron comentarios internos `TODO` en LaTeX para recordar tabla de universos, soporte anual, cobertura territorial y selección de figuras.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutó correctamente en la plantilla externa;
  - el PDF se generó sin errores asociados al capítulo;
  - quedan advertencias normales de primera pasada sobre referencias/lastpage y bibliografía vacía.
- Pendiente:
  - revisar con el usuario la sección de descripción de datos;
  - decidir qué figuras del EDA se incorporan en cuerpo, resultados o anexos;
  - confirmar fuente formal/documental de `ZONA777`;
  - decidir qué detalles técnicos pasan a anexos.

## 2026-07-06 — Capítulo 3 completado con descripción cuantitativa base
- Archivo externo actualizado:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/03_materiales_metodos.tex`.
- Cambio aplicado:
  - se completó la sección `Descripción de los datos analíticos`;
  - se agregó una tabla con el universo base de tarjetas-año y viajes observados en 2024 y 2025;
  - se agregó una tabla con el panel zonal interanual usando soporte mínimo de 250 observaciones por año;
  - se explicitó que residencia y origen de viaje son universos distintos: tarjetas asociadas a zona versus viajes iniciados en zona;
  - se reforzó la distinción entre cambio bruto, crecimiento relativo y contribución volumétrica.
- Decisión editorial:
  - la descripción cuantitativa base queda en Materiales y métodos;
  - las figuras interpretativas del EDA se seleccionarán después para Resultados o Anexos, evitando sobrecargar el capítulo metodológico.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa;
  - el PDF se generó en `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/main.pdf`;
  - el log quedó sin errores ni referencias rotas; solo permanece la advertencia esperada de bibliografía vacía.

## 2026-07-06 — Declaración y anexo de uso de IA incorporados
- Documento institucional revisado:
  - `/Users/vicenteonetto/Downloads/Instructivo_No_17_2026_Lineamientos_Uso_de_IA_en_Tesis_junio_2026_.pdf`.
- Requisito identificado:
  - la tesis debe incluir una `Declaración de uso de inteligencia artificial` en páginas preliminares;
  - cuando la IA se usa en componentes sustantivos, debe describirse prompts representativos, metodología de integración, verificación y criterios críticos;
  - el detalle puede ir en la declaración, metodología o anexo complementario, según acuerdo con la guía.
- Archivos externos actualizados:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/main.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/anexo.tex`.
- Decisión editorial:
  - se incorporó una declaración breve en preliminares;
  - se incorporó un anexo con herramientas/modelos, metodología de integración y verificación, prompts representativos normalizados y aprendizajes para repetir el proceso;
  - no se listan todos los prompts crudos, porque el instructivo permite una descripción representativa y muchos intercambios fueron iteraciones informales o menores.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa;
  - el PDF final compila sin errores; solo permanece la advertencia esperada de bibliografía vacía.

## 2026-07-06 — Ajuste editorial del anexo de uso de IA
- Archivos externos actualizados:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/main.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/anexo.tex`.
- Cambio aplicado:
  - se eliminó o suavizó lenguaje que atribuía a la IA interpretación, análisis de resultados, planificación metodológica o revisión de decisiones sustantivas;
  - los usos quedaron descritos como apoyo técnico, editorial, documental, de formato, depuración y compilación;
  - los prompts representativos fueron reemplazados por ejemplos más acotados: corrección de solapes, depuración de notebooks, borradores o estructuras de sección, conversión de tablas a LaTeX y revisión formal del instructivo.
- Decisión editorial:
  - cumplir el instructivo institucional sin sobreatribuir responsabilidades a la IA;
  - mantener transparencia, pero enfatizando que hallazgos, análisis, decisiones metodológicas y validación empírica son responsabilidad del autor.
- Verificación:
  - `pdflatex -interaction=nonstopmode main.tex` ejecutado dos veces correctamente en la plantilla externa;
  - el PDF final compila sin errores; solo permanece la advertencia esperada de bibliografía vacía.

## 2026-07-06 — Cierre temporal del avance de manuscrito
- Estado al pausar esta línea de trabajo:
  - Capítulo 1 (`Introducción`) migrado a LaTeX y actualizado para no prometer un modelo final cerrado;
  - Capítulo 2 (`Revisión de literatura`) migrado a LaTeX con foco en adopción QR, brecha digital, pago móvil, RTI, TAM, modelos interpretables/predictivos y lectura territorial;
  - Capítulo 3 (`Materiales y métodos`) migrado a LaTeX con unidad tarjeta, unidad zonal complementaria, construcción de variables, modelos preliminares y descripción cuantitativa base de los datos;
  - Capítulo 4 (`Resultados`) queda solo como estructura inicial, sin resultados definitivos;
  - declaración preliminar y anexo de uso de IA incorporados, con lenguaje ajustado para presentarlo como apoyo técnico/editorial y no como análisis o decisión metodológica.
- Archivos externos principales:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/01_introduccion.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/02_revision_literatura.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/03_materiales_metodos.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/04_resultados.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/anexo.tex`;
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/main.tex`.
- Pendientes cuando se retome:
  - revisar editorialmente Capítulos 1--3;
  - convertir referencias a BibTeX;
  - decidir qué figuras descriptivas del EDA entran en Resultados o Anexos;
  - completar Resultados solo cuando esté decidido el set de resultados preliminares/finales.
