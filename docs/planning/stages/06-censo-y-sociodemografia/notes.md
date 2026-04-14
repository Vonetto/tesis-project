# Stage 06 — Censo y Socio-demografía

## Resumen

Etapa abierta dedicada a integrar contexto socio-demográfico al proyecto, primero vía agregados `Censo -> ZONA777` y luego vía microdatos comunales spatialized hacia `MANZENT` y `ZONA777`.

## Objetivo de la etapa

Evaluar e incorporar proxies socio-demográficas defendibles para enriquecer el modelamiento OD-buffers/interanual.

## Decisiones metodológicas

- Usar `MANZENT` como unidad fina observada para interpolación y agregación.
- Separar claramente:
  - agregados oficiales Censo
  - variables derivadas desde microdatos comunales spatialized
- Congelar `softmax_tau003` como ruta principal de spatialization para evitar sobreajuste metodológico.

## Implementación lograda

- join `Censo 2024 -> ZONA777`
- screening de variables censales
- trabajo con microdatos comunales y variables educativas/laborales
- piloto `comuna -> manzana-entidad -> ZONA777`
- EDA inicial de nuevas proxies

## Limitaciones o problemas detectados

- La etapa sigue abierta.
- Queda pendiente decidir shortlist final de variables nuevas para llevar al modelo.

## Outputs/notebooks relevantes

- [`02_eda/eda_censo2024_zona777.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_censo2024_zona777.qmd)
- [`02_eda/eda_censo2024_zona777_model_join.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_censo2024_zona777_model_join.qmd)
- [`02_eda/eda_censo2024_microdata_zona777.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_censo2024_microdata_zona777.qmd)
- [`docs/planning/workstreams/socio-demographics/notes.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/planning/workstreams/socio-demographics/notes.md)

## Fuentes usadas para el backfill

- workstream `socio-demographics`
- notebooks EDA de Censo
