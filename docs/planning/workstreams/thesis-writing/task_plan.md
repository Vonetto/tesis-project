# Task Plan — Thesis Writing

## Goal
Construir progresivamente el manuscrito formal de tesis a partir del trabajo ya maduro del proyecto, manteniendo una narrativa defendible centrada en adopción digital en transporte público observada mediante pagos QR frente a `BIP`, con metodología principal a nivel `id_tarjeta` y análisis zonal como extensión territorial/interanual 2024-2025.

## Constraints / Guardrails
- Antes de redactar o insertar un capítulo, primero desglosar objetivo, contenido, estructura, insumos, pendientes y riesgos narrativos.
- Trabajar primero en borradores Markdown revisables bajo `docs/thesis/capitulos/`; no migrar a LaTeX hasta que el contenido esté aprobado.
- Mantener `QR_RED` como proxy observable de inserción en un canal digital oficial, sin afirmar uso observado de app, información en tiempo real ni causalidad individual.
- Tratar `QR_RED`/`QR_OTHER` como una desagregación posible cuando el análisis lo requiera; en modelos a nivel tarjeta, mantener la desagregación como contraste preliminar relevante frente a `BIP`.
- Interpretar variables censales como características territoriales de la zona de origen, no atributos individuales de pasajeros.
- Presentar XGBoost como benchmark/techo predictivo, no como explicación causal.
- Presentar NMF como segmentación descriptiva/post-hoc, no como modelo causal ni como unidad social observada directamente.
- Usar los EDA QR vs BIP e interanual zonal como insumos formales para descripción de datos, resultados descriptivos y definición del modelamiento.
- Cumplir el Instructivo N° 17/2026 de la Universidad de Chile sobre uso transparente de IA:
  - declaración formal en páginas preliminares;
  - detalle metodológico en anexo con herramientas, usos, verificación y prompts representativos;
  - redactar esta sección como transparencia de apoyo técnico/editorial, evitando atribuir análisis, hallazgos o decisiones metodológicas a la IA.

## Current Status
- [x] Reconstruir narrativa vigente de tesis:
  - archivo: `docs/thesis/narrativa_actual_tesis.md`.
- [x] Adaptar la plantilla formal externa de tesis como referencia estructural:
  - plantilla: `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/`;
  - manual: `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_2/MANUAL_NORMALIZACI_N_TESIS.pdf`.
- [x] Redactar borrador del Capítulo 1 — Introducción:
  - archivo: `docs/thesis/capitulos/01_introduccion_borrador.md`.
- [x] Redactar borrador del Capítulo 2 — Revisión de la literatura:
  - archivo: `docs/thesis/capitulos/02_revision_literatura_borrador.md`.
- [x] Redactar borrador inicial del Capítulo 3 — Materiales y métodos:
  - archivo: `docs/thesis/capitulos/03_materiales_metodos_borrador.md`.
- [x] Actualizar Capítulo 1 para reflejar el cambio de foco:
  - QR agregado frente a `BIP`;
  - análisis territorial e interanual;
  - modelamiento aún abierto entre nivel de uso y nivel zonal.
- [x] Reorientar Capítulo 3 hacia metodología reutilizable:
  - unidad principal `id_tarjeta`;
  - unidad zonal complementaria;
  - variables por familias;
  - modelos preliminares: logit/multinomial, XGBoost y NMF.
- [x] Crear esqueleto del Capítulo 4 — Resultados:
  - archivo: `docs/thesis/capitulos/04_resultados_borrador.md`.
- [x] Incorporar declaración y anexo de uso de IA:
  - declaración preliminar en `main.tex`;
  - anexo en `secciones/anexo.tex`;
  - verificación: `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa.
- [x] Cerrar estado de avance antes de pausar esta línea de trabajo:
  - Capítulo 1 migrado a LaTeX;
  - Capítulo 2 migrado a LaTeX;
  - Capítulo 3 migrado a LaTeX con descripción cuantitativa base;
  - Capítulo 4 dejado como estructura inicial;
  - declaración/anexo de uso de IA incorporado y ajustado a un tono prudente.
- [ ] Revisar con el usuario el Capítulo 1 actualizado y cerrar cambios de foco.
- [ ] Revisar con el usuario el Capítulo 2 y cerrar selección de literatura.
- [ ] Revisar con el usuario el Capítulo 3 y cerrar detalles metodológicos.
- [ ] Revisar con el usuario el Capítulo 4 como esqueleto y definir qué entra en cuerpo/anexos.
- [ ] Convertir referencias principales a BibTeX.
- [ ] Migrar capítulos aprobados desde Markdown a la plantilla LaTeX.
  - [x] Capítulo 1 — Introducción:
    - destino: `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/01_introduccion.tex`.
    - verificación: `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa.
  - [x] Capítulo 2 — Revisión de literatura:
    - destino: `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/02_revision_literatura.tex`.
    - verificación: `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa.
    - pendiente: convertir referencias autor-año a BibTeX/citas formales.
  - [x] Capítulo 3 — Materiales y métodos, estructura base:
    - destino: `/Users/vicenteonetto/Desktop/FCFM/MDS/Seminario_Tesis_1/informe-tesis/Template-Tesis-postgrado/secciones/03_materiales_metodos.tex`.
    - verificación: `pdflatex -interaction=nonstopmode main.tex` ejecutado correctamente en la plantilla externa.
    - avance: descripción cuantitativa base incorporada con tablas de universo tarjetas-año/viajes y panel zonal interanual con soporte mínimo.
    - pendiente: seleccionar figuras para cuerpo/anexos, convertir referencias a BibTeX y confirmar fuente formal de `ZONA777`.
  - [ ] Capítulo 4 — Resultados.

## Chapter Prioritization
- [x] Listo para borrador: Introducción.
- [x] Listo para borrador: Revisión de literatura, usando papers de adopción digital, brecha digital, mobile fare payment, RTI y TAM.
- [x] Listo para borrador: Materiales y métodos, usando EDA QR vs BIP, notas de user-level, Censo, OSM, `ZONA777`, MNL/logit tarjeta, XGBoost, NMF y análisis zonal.
- [x] Esqueleto inicial: Resultados, sin cerrar resultados definitivos.
- [ ] Esperar: Discusión, hasta estabilizar resultados y decisión sobre variables nuevas.
- [ ] Esperar: Conclusiones, hasta cerrar resultados/discusión.

## Immediate Next Steps
- [ ] Pausado por ahora: seguir editando el manuscrito/reporte formal.
- [ ] Revisar versión LaTeX del Capítulo 1 con el usuario:
  - verificar que objetivos y alcance no prometan un modelo final cerrado;
  - confirmar que `id_tarjeta` y zona quedan bien balanceados;
  - ajustar estilo antes de migrar nuevos capítulos.
- [ ] Revisar Capítulo 3 con el usuario:
  - confirmar si la metodología principal del avance queda formalmente a nivel tarjeta;
  - decidir qué detalles de preprocesamiento de viajes quedan en cuerpo y cuáles en anexo;
  - confirmar fuente formal de `ZONA777`;
  - revisar la descripción de datos y decidir qué figuras seleccionadas entran en cuerpo o anexos.
- [ ] Revisar Capítulo 4 con el usuario:
  - decidir qué figuras descriptivas entran;
  - decidir si MNL/logit tarjeta, XGBoost y NMF entran como resultados preliminares en cuerpo o anexos.
- [ ] Hacer revisión crítica del Capítulo 2:
  - decidir si mantener fuera Boyko y Schaefer (2026) por ahora;
  - verificar que cada afirmación sustantiva tenga fuente trazable;
  - evitar redundancia entre Durand et al. (2021), Boyko y Schaefer (2026) y literatura de apps.
