# Pipeline de procesamiento de datos — referencia completa

Documento de referencia del flujo de procesamiento de viajes, desde los CSV crudos
hasta el artefacto `viajes_con_te_calculado_<semana>.parquet` que consumen los
modelos y la línea de segmentación. El objetivo es evitar re-auditar el pipeline
cada vez que haya que reprocesar una semana nueva.

Última auditoría: 2026-05-24. Si se modifica una etapa, actualizar este doc.

## Resumen del flujo

```
RAW (CSV)  ─ perfiles_de_carga ──────────────────────────────────┐
                                                                  │
[process_data.py]  RAW → Bronze                                   │
   └─> bronze/viajes/ (parquet, particionado iso_year/iso_week)   │
                                                                  │
[01_silver_processing]  Bronze → Silver (PK de viaje)             │
   └─> silver/viajes_enriquecidos                                 │
                                                                  │
[02_data_quality]                                                 │
   └─> silver/viajes_limpios                                      │
                                                                  │
[03_feature_engineering]                                          │
   ├─> silver/viajes_con_indicadores                              │
   └─> silver/viajes_filtrados                                    │
                                                                  │
[04_transbordos_metro]                                            │
   └─> 01_processing/tmp/etapas_reconstruidas_<semana>.parquet ──┤  (input A de 06)
                                                                  │
[05_transbordos_bus]  (lee RAW perfiles_de_carga directamente) ──┘
   └─> tmp/frecuencias_buses_<semana>.parquet                       (input B de 06)

[06_recalculo_tiempos_espera]  A + B + GTFS + grafo metro
   └─> tmp/viajes_con_te_calculado_<semana>.parquet   ← ARTEFACTO FINAL (viajes)

[07 (post-pipeline) build_proposito_pk_bridge.py]  consume el output de 06
   └─> tmp/audits/proposito_residence/pk_bridge/user_home_candidates_<scope>.parquet
       (+ bridges y diagnósticos)                    ← ARTEFACTO de residencia/usuario
```

Orden de ejecución: **lineal 01 → 02 → 03 → 04 → 05 → 06**, y luego **07** como
paso post-pipeline. No hay dependencia circular entre 05 y 06 (ver nota en la
etapa 05).

## Fuentes crudas (RAW)

Con `USE_LOCAL_PATHS = True` (en `config/constants.py`), el pipeline lee de discos
locales; con `False`, de GCS (`gs://tesis-vonetto-datalake/`).

| Fuente | Ubicación local | Contenido |
|---|---|---|
| Perfiles de carga | `/Volumes/TOSHIBA EXT/Vicente/tesis-project/raw/raw_csv/perfiles_carga/<fecha>.perfiles_de_carga.csv` | Transacciones/etapas por día. Insumo base de todo el pipeline. |
| Caracterización QR | `/Volumes/KINGSTON/tesis-project/raw/caracterizacion/caracterización qr_<YYYYMM>.csv` | Mapea contrato → tipo de pago (BIP / QR_RED / QR_OTHER). **Por mes.** |
| GTFS | `config/GTFS/GTFS_<YYYYMMDD>/` | Rutas, viajes, calendario, frecuencias. Una versión por rango de fechas. |
| Grafo metro | `01_processing/metro_graphs/metro_graph_GTFS_<YYYYMMDD>.gpickle` | Grafo para tiempos de espera de metro (etapa 06). |
| Zonas 777 | `/Volumes/KINGSTON/tesis-project/raw/zonas777/` | Cartografía zonal. |

Cobertura RAW verificada (2026-05-24): perfiles_de_carga tiene **todo abril 2024**
(W14–W17) y **todo noviembre 2024**, además de las semanas 2025 ya usadas. GTFS
disponibles: `GTFS_20240210` (cubre 2024), `GTFS_20250412`, `GTFS_20250517`,
`GTFS_20251108`.

## Etapas

### process_data.py — RAW → Bronze

- **Input:** CSVs `*.perfiles_de_carga.csv` (RAW).
- **Output:** `bronze/viajes/` particionado por `iso_year=<>/iso_week=<>`.
- **Notas:** agrupa archivos por semana ISO; deriva `is_qr` de `contrato`
  (contratos `171`/`102`); idempotente (`write_missing`/`upsert`).

### 01_silver_processing.qmd — Bronze → Silver

- **Input:** `bronze/viajes/**/*.parquet`.
- **Output:** `silver/viajes_enriquecidos` (`SILVER_VIAJES_PATH`).
- **Hace:** asigna PK de viaje (`add_pk_viaje`). El join geográfico está marcado
  como pendiente; por ahora pasa el LF tal cual tras el PK.

### 02_data_quality.qmd — limpieza

- **Input:** `silver/viajes_enriquecidos` (`INPUT_PATH`).
- **Output:** `silver/viajes_limpios` (`OUTPUT_PATH`).
- **Parametrización:** `YEAR_ANALISIS` / `WEEK_ANALISIS` (manual, una semana).

### 03_feature_engineering.qmd — indicadores y filtros

- **Input:** `silver/viajes_limpios`.
- **Outputs:** `silver/viajes_con_indicadores` y `silver/viajes_filtrados`.
- **Parametrización:** itera por partición (`iso_year`/`iso_week`); fijar a la
  semana objetivo para no reprocesar todo.

### 04_transbordos_metro.qmd — reconstrucción de etapas

- **Input:** `silver/viajes_filtrados/iso_year=<>/iso_week=<>/`.
- **Output:** `01_processing/tmp/etapas_reconstruidas_<semana>.parquet`
  (**input A** de la etapa 06).
- **Parametrización:** `YEAR_ANALISIS` / `WEEK_ANALISIS` → `PARTITION_LABEL`.

### 05_transbordos_bus.qmd — frecuencias de bus

- **Input:** CSVs RAW `*.perfiles_de_carga.csv` (lee directo, **independiente de
  01–04**).
- **Output:** `tmp/frecuencias_buses_<semana>.parquet` (**input B** de la etapa 06).
- **⚠️ Gotcha:** el glob de CSV **no filtra por semana** — leería todos los
  archivos de la carpeta (abril + noviembre). Filtrar a las fechas de la semana
  objetivo antes de calcular frecuencias.
- **⚠️ Nota:** el markdown dice "frecuencias generadas en 06" — es un comentario
  **obsoleto**. El código del 05 las **produce**; el 06 las consume.

### 06_recalculo_tiempos_espera (qmd + scripts/recalculo_tiempos_espera_optimized.py)

- **Inputs:**
  - A: `tmp/etapas_reconstruidas_<semana>.parquet` (`--input-path`).
  - B: `tmp/frecuencias_buses_<semana>.parquet` (`--freq-path`).
  - GTFS de la semana (`config/GTFS`, autoselección por fecha vía `gtfs_manifest`).
  - Grafo de metro (`metro_graph_GTFS_<folder>.gpickle`).
- **Output:** `tmp/viajes_con_te_calculado_<semana>.parquet` (**ARTEFACTO FINAL**).
- **Hace:** calcula tiempos de espera esperados (metro vía GTFS/grafo; bus vía
  frecuencias observadas) sin sobrescribir los originales (`te0_calculado`, etc.).
- **CLI:** `python scripts/recalculo_tiempos_espera_optimized.py --partition 2024-W15`
  (acepta `--input-path`, `--freq-path`, `--output-path`, `--resume`,
  `--finalize-only`).
- **Restricción:** la semana ISO debe caer dentro de **una sola** versión GTFS;
  si la cruza, falla a propósito.

### 07 (post-pipeline) — bypass de residencia (scripts/audits/build_proposito_pk_bridge.py)

Paso **posterior** al pipeline: no forma parte del flujo 01–06 y no debe fusionarse
con él. Existe porque el pipeline normal descarta `proposito`, y los modelos de
residencia lo necesitan para inferir `zona_hogar` por usuario.

- **Inputs:**
  - `tmp/viajes_con_te_calculado_<semana>.parquet` (output de la etapa 06).
  - CSVs RAW de perfiles de carga (para recuperar `proposito`, que el pipeline bota).
- **Outputs** (en `tmp/audits/proposito_residence/pk_bridge/`, sufijados por scope):
  - `user_home_candidates_<scope>.parquet` — **el que consumen los modelos de
    residencia (03h/17) y la segmentación**: `zona_hogar` + `home_confidence`
    (`alta`/`media`/`baja`) por `id_tarjeta`.
  - `processed_trip_proposito_bridge_<scope>.parquet`, `raw_viajes_proposito_pk_<scope>.parquet`
    y diagnósticos de join.
- **CLI:** `python scripts/audits/build_proposito_pk_bridge.py --scope active`
  (scopes: `active`, `ml_2025`, `active_ml`). Detalle en
  [`scripts/audits/README.md`](../scripts/audits/README.md).
- **⚠️ Gotcha (importante para semanas nuevas):** el diccionario de inputs del
  script está **hardcodeado** a las semanas existentes (2024-W17, 2025-W14/W15/W17).
  Al procesar una semana nueva (p.ej. 2024-W14/W15), hay que **agregar su entrada
  a ese diccionario** o el bypass no la verá.
- **Por qué se mantiene separado:** el pipeline 01–06 produce *viajes* (unidad de
  los modelos de elección); el bypass produce un *bridge de residencia por usuario*
  con su propio scope y ciclo de vida. Cambiar la lógica de residencia no debe
  forzar reprocesar viajes, y viceversa.

## Gotchas al reprocesar una semana nueva

1. **Caracterización por año/mes.** El default de `resolve_caracterizacion_path`
   apunta a `202504` (2025). Para procesar viajes de **2024** hay que usar
   `caracterización qr_202404.csv` explícitamente, o `is_qr`/`tipo_pago` queda mal.
2. **Filtrar CSV en la etapa 05** (ver gotcha arriba).
3. **Fijar la semana** en las etapas 01/03 si iteran sobre todas las particiones.
4. **Validar cada semana nueva** contra una existente (mismo schema, conteos
   plausibles, `share_qr` en rango razonable) antes de encadenar hacia adelante.
5. **No sobrescribir** artefactos canónicos: escribir la semana nueva como
   partición/archivo separado.
6. **Etapa 07 (bypass):** agregar la semana nueva al diccionario hardcodeado de
   `build_proposito_pk_bridge.py` si se necesita el bridge de residencia para ella.

## Artefactos finales y quién los consume

- `tmp/viajes_con_te_calculado_<semana>.parquet`: insumo de los notebooks de
  modelación (`03_models/...`), del bypass de residencia
  (`scripts/audits/build_proposito_pk_bridge.py`) y de la línea de segmentación
  (`tesis-project-segmentation/03_models/user_segmentation/`).
- Semanas procesadas a la fecha (2026-05-24): 2024-W17; 2025-W14, W15, W17.

## Relacionado

- Bypass residencia: `scripts/audits/README.md`.
- Plan activo para procesar 2024 W14/W15:
  `tmp/plans/segmentacion-ventana-2024/` (task_plan.md + notes.md).
