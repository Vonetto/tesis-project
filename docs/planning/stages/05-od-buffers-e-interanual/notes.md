# Stage 05 — OD-buffers e Interanual

## Resumen

Etapa abierta centrada en el cambio desde modelos iniciales a una formulación OD-buffers alt-specific, primero sobre nested/MNL y luego en una extensión interanual con nuevos bloques de contexto.

## Objetivo de la etapa

Consolidar una baseline principal de modelamiento para:

- observación = viaje individual;
- contexto `OD × tipo_pago`;
- comparación `nested vs MNL`;
- incorporación progresiva de controles de demanda, oferta y contexto interanual.

## Decisiones metodológicas

- Priorizar `MNL` como benchmark principal cuando `nested` no agregara valor real.
- Separar un notebook específico para refinamiento y diagnóstico.
- Mantener la línea interanual y de oferta/contexto como continuación natural del pipeline OD-buffers.

## Implementación lograda

- Construcción de notebooks `05`, `06`, `07`, `08`, `09`.
- Desarrollo del workstream específico de OD-buffers y refinamiento.

## Limitaciones o problemas detectados

- Etapa todavía abierta.
- La selección final de especificaciones y controles sigue evolucionando.

## Outputs/notebooks relevantes

- [`03_models/05_nested_logit_od_buffers.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/05_nested_logit_od_buffers.qmd)
- [`03_models/06_mnl_refinement_diagnostics.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/06_mnl_refinement_diagnostics.qmd)
- [`03_models/07_nested_logit_enriched_interannual.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/07_nested_logit_enriched_interannual.qmd)
- [`03_models/08_nested_logit_enriched_interannual_censo.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/08_nested_logit_enriched_interannual_censo.qmd)
- [`03_models/09_interannual_framework_audit.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/09_interannual_framework_audit.qmd)

## Fuentes usadas para el backfill

- workstream `od-buffers-nested-logit`
- notebooks `05-09`
