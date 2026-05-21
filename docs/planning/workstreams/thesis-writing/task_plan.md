# Task Plan — Thesis Writing

## Goal
Construir progresivamente el manuscrito formal de tesis a partir del trabajo ya maduro del proyecto, manteniendo una narrativa defendible centrada en adopción digital en transporte público observada mediante elección de medio de pago (`BIP`, `QR_RED`, `QR_OTHER`).

## Constraints / Guardrails
- Antes de redactar o insertar un capítulo, primero desglosar objetivo, contenido, estructura, insumos, pendientes y riesgos narrativos.
- Trabajar primero en borradores Markdown revisables bajo `docs/thesis/capitulos/`; no migrar a LaTeX hasta que el contenido esté aprobado.
- Mantener `QR_RED` como proxy observable de inserción en un canal digital oficial, sin afirmar uso observado de app, información en tiempo real ni causalidad individual.
- Interpretar variables censales como características territoriales de la zona de origen, no atributos individuales de pasajeros.
- No prometer inercia, clustering, segmentación ni ML/SHAP como eje central mientras no se decida explícitamente integrarlos.
- Usar el reporte logit territorial como insumo formal, pero no como sustituto del manuscrito de tesis.

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
- [x] Redactar borrador del Capítulo 3 — Materiales y métodos:
  - archivo: `docs/thesis/capitulos/03_materiales_metodos_borrador.md`.
- [ ] Revisar con el usuario el Capítulo 1 y cerrar cambios de foco.
- [ ] Revisar con el usuario el Capítulo 2 y cerrar selección de literatura.
- [ ] Revisar con el usuario el Capítulo 3 y cerrar detalles metodológicos.
- [ ] Convertir referencias principales a BibTeX.
- [ ] Migrar capítulos aprobados desde Markdown a la plantilla LaTeX.

## Chapter Prioritization
- [x] Listo para borrador: Introducción.
- [x] Listo para borrador: Revisión de literatura, usando papers de adopción digital, brecha digital, mobile fare payment, RTI y TAM.
- [x] Listo para borrador: Materiales y métodos, usando reporte logit territorial, notas de preprocesamiento, Censo, OSM, `ZONA777` y MNL.
- [ ] Esperar: Resultados, hasta cerrar modelo principal y sensibilidades sociodemográficas.
- [ ] Esperar: Discusión, hasta estabilizar resultados y decisión sobre variables nuevas.
- [ ] Esperar: Conclusiones, hasta cerrar resultados/discusión.

## Immediate Next Steps
- [ ] Hacer revisión crítica del Capítulo 2:
  - decidir si mantener fuera Boyko y Schaefer (2026) por ahora;
  - verificar que cada afirmación sustantiva tenga fuente trazable;
  - evitar redundancia entre Durand et al. (2021), Boyko y Schaefer (2026) y literatura de apps.
- [ ] Hacer revisión crítica del Capítulo 3:
  - confirmar referencias de preprocesamiento;
  - confirmar fuente formal de `ZONA777`;
  - actualizar muestra final si cambia por variables nuevas.
- [ ] Definir cuándo iniciar Capítulo 4 — Resultados:
  - requiere modelo final o, al menos, decisión clara de modelo principal y sensibilidades.
