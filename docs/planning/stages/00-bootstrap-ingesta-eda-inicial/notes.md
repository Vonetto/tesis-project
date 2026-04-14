# Stage 00 — Bootstrap, Ingesta y EDA Inicial

## Resumen

Esta etapa cubre el arranque del repo, la configuración base de Quarto/datalake, la ingesta incremental por semanas y los primeros notebooks de EDA para entender viajes, etapas, joins y geometrías de referencia.

## Objetivo de la etapa

Construir una base reproducible para:

- cargar datos de viajes y etapas por partición semanal;
- unificar rutas locales/GCS y acceso al datalake;
- preparar joins con DIC 777 / `ZONA777`;
- abrir los primeros análisis exploratorios del comportamiento de los viajes.

## Decisiones metodológicas

- Organizar el proyecto alrededor de particiones semanales.
- Centralizar acceso a datos y constantes del proyecto.
- Usar notebooks `.qmd` como interfaz principal de exploración.
- Integrar desde temprano la geografía `ZONA777` como referencia para análisis espacial.

## Implementación lograda

- Bootstrap del repo con Quarto y estructura inicial de datalake.
- Ingesta incremental por semana para viajes/etapas.
- Normalización temprana de esquemas, fechas y rutas.
- Primeros notebooks EDA para overview de viajes, joins y caracterización.

## Limitaciones o problemas detectados

- La documentación narrativa de esta etapa no fue sistemática al momento de ocurrir.
- Parte de la reconstrucción depende de `git log` y de los encabezados/objetivos dentro de notebooks.

## Outputs/notebooks relevantes

- [`02_eda/eda_trips_overview.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_trips_overview.qmd)
- [`02_eda/join_validation.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/join_validation.qmd)
- [`02_eda/eda_caracterizacion.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/02_eda/eda_caracterizacion.qmd)

## Fuentes usadas para el backfill

- `git log` entre septiembre y octubre de 2025
- notebooks tempranos en `02_eda/`
