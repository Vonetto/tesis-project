# Stage 01 — Limpieza y Anomalías

## Resumen

Esta etapa consolidó la lógica de limpieza básica, consistencia de tiempos y distancias, e identificación de viajes anómalos antes de cualquier modelamiento.

## Objetivo de la etapa

Obtener un dataset de viajes confiable, con:

- filtros básicos de calidad;
- selección explícita de métricas válidas de tiempo y distancia;
- flags de anomalía basados en reglas comportamentales y operativas.

## Decisiones metodológicas

- Validar componentes de tiempo antes de confiar en variables agregadas.
- Tratar `distancia_ruta` como proxy principal de distancia en ruta tras detectar inconsistencias en otras columnas.
- Separar claramente:
  - limpieza básica
  - detección de anomalías

## Implementación lograda

- Filtros por tiempos, paraderos y distancias inválidas.
- Construcción de métricas derivadas como velocidades y relaciones DR/DE.
- Identificación de anomalías de velocidad, duración y viajes circulares.
- Producción de datasets limpios y datasets con flags.

## Limitaciones o problemas detectados

- Persistía incertidumbre en torno a la calidad absoluta de algunas medidas de distancia.
- No todos los filtros conceptualmente posibles quedaron implementados en esa primera ronda.

## Outputs/notebooks relevantes

- [`docs/avances/filtrado_y_limpieza_simple.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/avances/filtrado_y_limpieza_simple.md)

## Fuentes usadas para el backfill

- [`docs/avances/filtrado_y_limpieza_simple.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/avances/filtrado_y_limpieza_simple.md)
