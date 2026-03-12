# Task Plan — OD Buffers Model Enrichment

## Goal
Consolidar el modelo principal OD-buffers alt-specific y enriquecer su capacidad explicativa con nuevos controles antes de cerrar la discusion fina de nested/colinealidad:
- base principal: **MNL alt-specific** con observacion = viaje individual;
- nuevos bloques: demanda, oferta de servicio, socio-demografia y comparacion interanual 2024/2025.

## Constraints / Guardrails
- Usar dataset corregido (parquet v2) y columnas finales (sin caminata).
- Restringir a pares **OD con las 3 alternativas observadas**.
- Mantener la estructura **alt-specific** y `leave_one_out` en la alternativa elegida.
- No perder la evidencia ya obtenida de `nested vs MNL`; esa rama queda documentada pero en pausa.
- Incorporar nuevos controles primero sobre el benchmark MNL y reevaluar nested solo despues.

## Plan
- [x] Definir dataset/particiones a usar (OD, choice, columnas finales).
- [x] Migrar a dummies temporales V2 (base = `LAB_VALLE`).
- [x] Limpiar notebook para dejar **solo Option1** en el flujo operativo.
- [x] Redisenar tabla de contexto a **OD x tipo_pago**.
- [x] Redisenar dataset de viajes con atributos alternativo-especificos.
- [x] Definir utilidades completas para `V_BIP`, `V_QR_RED` y `V_QR_OTHER`.
- [x] Restringir a OD con las 3 alternativas observadas.
- [x] Aplicar `leave_one_out` solo en la alternativa elegida.
- [x] Usar coeficientes distintos por alternativa para tiempos/esperas/transbordos.
- [x] Re-estimar corrida limpia del modelo principal y dejar output final.
- [x] Revisar minuciosamente la implementación/estimación del modelo principal y documentar riesgos metodológicos/código.
- [ ] Analizar e interpretar resultados del modelo principal.
- [x] Implementar la misma especificación como **MNL benchmark principal** en **Larch**.
- [x] Implementar la misma especificación como **MNL benchmark principal** en **Biogeme**.
- [x] Comparar `nested vs MNL` en ambos frameworks para documentar que el nido no agrega valor frente a `MU_QR = 1`.
- [x] Diagnosticar estabilidad de parámetros y colinealidad en la especificación alt-specific actual.
- [x] Diseñar una ruta de refinamiento parsimoniosa que mantenga la lógica alt-specific pero reduzca problemas de identificación.
- [x] Definir el primer experimento de simplificación del MNL principal (variantes `full`, `no_ntr`, `no_tet`).
- [x] Extender experimento de refinamiento con variantes para colinealidad cross-alternative (`generic`, `mixed_tei_specific`, `diff_vs_bip`).
- [x] Crear notebook separado para refinamiento y comparación cruzada (`06_mnl_refinement_diagnostics.qmd`).
- [x] Ejecutar variantes de refinamiento en Biogeme y Larch y comparar resultados.
- [x] Investigar la implementación correcta en Larch 6 y dejar un notebook separado de réplica.
- [ ] Inventariar y priorizar nuevas variables de control candidatas (demanda, oferta, accesibilidad, socio-demo).
- [ ] Construir primer bloque de variables de demanda por zona/OD y franja horaria.
- [ ] Construir primer bloque de variables de oferta de servicio por zona (paraderos, lineas, cercania a metro).
- [ ] Retomar e integrar socio-demo en el modelo principal, comenzando por origen.
- [x] Evaluar factibilidad de apilar `W17-2024` con `W17-2025` y definir una `dummy` de anio.
- [x] Identificar y corregir dos bugs del pipeline Metro antes del pooling interanual:
  - normalizacion de nombres de estaciones de combinacion en `04_transbordos_metro.qmd` / `metro_graph_builder.py`
  - filtrado de `service_id` por fecha real en `06_recalculo_tiempos_espera.qmd`
- [x] Corregir errores silenciosos adicionales del pipeline 04/05/06:
  - preservar fecha en la espera bus del paso `06`
  - impedir transbordos en `tv*_calculado` Metro de una etapa individual
  - limpiar timestamps/zonas stale en etapas reconstruidas y arreglar `metro_any`
- [x] Auditar `n_eventos` vs `n_buses_unicos` en `05_transbordos_bus.qmd`.
- [x] Hacer una segunda pasada tecnica sobre `04/05/06` para buscar bugs silenciosos adicionales y cerrar correcciones estructurales:
  - separar `direction_id` en el calculo de headways Metro del paso `06`
  - fijar rutas de salida ambiguas en `04_transbordos_metro.qmd`
- [x] Hacer una tercera pasada tecnica sobre GTFS/versionado y supuestos temporales:
  - eliminar desalineacion potencial entre `GTFS_VERSION` manual y `manifest` en `06`
  - impedir que `gtfs_manifest` extienda snapshots mas alla de `feed_end_date`
  - agregar guard explicito para semanas ISO que crucen multiples versiones GTFS
- [ ] Definir si `05_transbordos_bus.qmd` debe:
  - mantener `n_eventos`,
  - deduplicar eventos exactos / casi exactos,
  - o migrar a una frecuencia depurada.
- [x] Corregir el tratamiento de variantes Metro `R/V` en el paso `06`:
  - mantener `te` sobre variantes activas reales,
  - calcular `tv` solo sobre variantes activas reales y no sobre la linea agregada sintetica,
  - marcar `metro_variant_conflict_i` cuando una etapa solo existe en la agregacion base.
- [x] Reprocesar `W17-2024` con grafo Metro regenerado y tiempos de espera recalculados.
- [x] Reprocesar `W17-2025` al menos en el paso `06_recalculo_tiempos_espera.qmd` para corregir el filtro de calendario.
- [x] Extraer el paso pesado equivalente a `06_recalculo_tiempos_espera.qmd` a un runner externo optimizado:
  - crear script CLI fuera del notebook;
  - conservar la logica metodologica vigente;
  - agregar caches/indices para que `W17-2024` y `W17-2025` sean corribles en tiempos razonables.
- [ ] Re-estimar el benchmark MNL enriquecido y revisar si mejora interpretabilidad/estabilidad.
- [ ] Solo despues del enriquecimiento, decidir si vale la pena reintentar nested y/o retomar la comparacion `full` vs `generic` vs `mixed_tei_specific`.

## Paused / Parked
- Seleccion final entre `full`, `generic` y `mixed_tei_specific` queda pausada hasta probar especificaciones con controles adicionales.
- Interpretacion final cerrada de los parametros actuales queda pausada; los resultados actuales se conservan como baseline metodologico.
- Reintento del nested sobre variantes parsimoniosas queda diferido hasta despues del enriquecimiento del modelo.

## Status
- Current: `W17-2024` y `W17-2025` ya quedaron reprocesadas y validadas con el pipeline corregido. La rama de limpieza del pipeline queda cerrada a nivel de outputs finales de modelacion; el foco activo vuelve al enriquecimiento de la especificacion y la reestimacion de modelos con comparacion interanual.
