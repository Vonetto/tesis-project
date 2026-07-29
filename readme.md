# Tesis — Datos, modelos y escritura

Este repositorio contiene el pipeline de datos, notebooks de EDA/modelación y documentación viva para la tesis _“Tecnologías digitales y su impacto en la inercia del comportamiento de viaje en transporte público”_ (DCC + MDS, U. de Chile).

El proyecto partió como un flujo **GCS + Parquet**, pero hoy combina:

- fuentes remotas en GCS;
- CSV raw locales de respaldo;
- artefactos pesados locales/symlinkeados en SSD externo;
- notebooks Quarto para EDA, modelos logit, sensibilidades y reportes;
- documentación de planificación y escritura de tesis.

## Arquitectura del proyecto

```
tesis-project/
├─ 00_setup/
│  └─ setup.qmd                # Validación de la capa Bronze
├─ 01_processing/
│  ├─ 01_silver_processing.qmd # Procesamiento Bronze→Silver y PK de viajes
│  └─ tmp/                     # Artefactos locales pesados (ignorado/symlink)
├─ 02_eda/
│  ├─ eda_caracterizacion.qmd  # Perfil demográfico de usuarios QR
│  ├─ eda_trips_overview.qmd   # Análisis de patrones de viaje
│  └─ *.qmd                    # Diagnósticos territoriales y de modelos
├─ 03_models/
│  ├─ *.qmd                    # Notebooks Biogeme/MNL/Nested
│  ├─ larch_logit/             # Comparaciones Larch
│  ├─ artifacts/               # Muestras model-ready pesadas (ignorado/symlink)
│  └─ biogeme-logit/           # Resultados de estimación (ignorado)
├─ docs/
│  ├─ planning/                # Workstreams, bitácoras y decisiones
│  ├─ reports/                 # Reportes LaTeX/Markdown y entregables
│  └─ thesis/                  # Borradores, narrativa y figuras de tesis
├─ lib/
│  └─ *.py                     # Helpers de datos, Censo, OD buffers y modelos
├─ scripts/
│  ├─ audits/                  # Auditorías reproducibles y bypass residencia
│  └─ figures/                 # Figuras para tesis/reportes
├─ tmp/                        # Outputs locales, caches y artefactos auditables
├─ process_data.py             # Pipeline de ingesta RAW→Bronze
├─ _quarto.yml                 # Config del sitio Quarto
├─ GIT_WORKFLOW.md             # Guía de workflow de Git
├─ _site/                      # (generado) HTML renderizados
└─ .quarto/                    # (generado) cachés de Quarto
```

> Las carpetas **`_site/`**, **`_freeze/`** y **`.quarto/`** son artefactos generados por Quarto y **no** deben versionarse.

Los artefactos pesados que se usan localmente se documentan en [`docs/local_artifacts.md`](docs/local_artifacts.md). En este worktree varias rutas pesadas se mantienen como symlinks hacia `/Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/`.

### Data Lake en GCS

- `gs://tesis-vonetto-datalake/raw/`  
  CSV originales (solo lectura).

- `gs://tesis-vonetto-datalake/lake/bronze/`  
  **Bronze** = datos "aterrizados" en Parquet, con cambios mínimos (parseo de fechas y particiones).
  - `bronze/viajes/semana_iso=YYYY-WNN/part-*.parquet` (particionado por semana ISO)
  - `bronze/caracterizacion/snapshot_date=YYYY-MM-DD/part-*.parquet` (snapshot único)

- `gs://tesis-vonetto-datalake/lake/silver/`  
  **Silver** = limpieza y enriquecimiento reutilizable (nombres normalizados, tipos, dedupe, features básicos).

- `gs://tesis-vonetto-datalake/lake/gold/`  
  **Gold** = datasets curados para preguntas/outputs concretos (KPIs, paneles por usuario-semana, métricas de inercia, matrices OD).

Resumen:
- **Bronze**: formato analítico + partición, casi sin “cocina”.
- **Silver**: datos **consistentes** y **reutilizables** para EDA/joins.
- **Gold**: tablas **listas para el paper/modelos**.

## Requisitos

- **Python 3.10+** (se probó con Python 3.13 y Polars ≥ 1.33, PyArrow ≥ 11)
- **Quarto ≥ 1.4** (`quarto --version`)
- **Google Cloud SDK** (`gcloud`) para autenticación

### Paquetes Python

**Core (obligatorios):**
- `polars` - Procesamiento de datos rápido
- `pyarrow` - Backend de Parquet
- `gcsfs` - Acceso a Google Cloud Storage
- `fsspec` - Sistema de archivos abstracto

**Análisis y visualización:**
- `matplotlib` - Gráficos
- `seaborn` - Visualizaciones estadísticas
- `geopandas` - Datos geoespaciales
- `pyogrio` - Lectura eficiente de shapefiles

**Utilidades:**
- `tqdm` - Progress bars

**Instalación completa:**
```bash
pip install polars pyarrow gcsfs fsspec matplotlib seaborn geopandas pyogrio tqdm
```

## Autenticación (GCP)

Una vez por equipo:
```bash
gcloud auth application-default login
````

O define `GOOGLE_APPLICATION_CREDENTIALS` apuntando a un JSON de Service Account.
Los notebooks usan un helper (`enable_adc`) que levanta automáticamente las credenciales.

## Configuración rápida

### 1. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -U polars pyarrow gcsfs fsspec matplotlib seaborn geopandas pyogrio tqdm
```

### 2. Autenticación con GCP

```bash
gcloud auth application-default login
```

### 3. Pipeline de Datos (ejecutar en orden)

> 📄 **Referencia completa del flujo** (etapas 00→06, inputs/artefactos
> intermedios/outputs exactos, fuentes crudas, parametrización por semana y
> gotchas): [`docs/pipeline_procesamiento.md`](docs/pipeline_procesamiento.md).

#### a) Ingesta RAW → Bronze (primera vez o al agregar datos nuevos)

```bash
python process_data.py
```

Esto lee los CSVs de `gs://tesis-vonetto-datalake/raw/` y los escribe como Parquet particionado en `bronze/viajes/`.

**⏱️ Tiempo:** Puede tomar varios minutos dependiendo del volumen de datos.

#### b) Validación de Bronze (opcional pero recomendado)

```bash
quarto render 00_setup/setup.qmd
```

Valida que las particiones se escribieron correctamente y genera un reporte HTML.

#### c) Procesamiento Silver (cuando necesites datos enriquecidos)

```bash
quarto render 01_processing/01_silver_processing.qmd
```

Aplica enriquecimiento geográfico y crea primary keys. **Nota:** El join geográfico está pendiente de completarse.

#### d) Bypass local `proposito` → residencia por usuario (auditoría/modelos)

Para los modelos que requieran variables sociodemográficas asociadas a residencia del usuario, existe un bypass reproducible que recupera `proposito` desde los CSV raw locales y lo enlaza con los viajes procesados.

```bash
python scripts/audits/build_proposito_pk_bridge.py --scope active
```

Este paso no reemplaza el pipeline Bronze/Silver; crea artefactos auditables en `tmp/audits/proposito_residence/pk_bridge/` para:

- enlazar viajes procesados con `proposito`;
- inferir `zona_hogar` por `id_tarjeta`;
- clasificar confianza residencial (`alta`, `media`, `baja`);
- documentar diferencias entre zonas raw y zonas procesadas.

Detalles del script y outputs: [`scripts/audits/README.md`](scripts/audits/README.md).

#### e) Análisis Exploratorio (EDA)

```bash
# Análisis demográfico de usuarios QR
quarto render 02_eda/eda_caracterizacion.qmd

# Análisis de patrones de viaje (parametrizable)
quarto render 02_eda/eda_trips_overview.qmd

# O en modo preview interactivo:
quarto preview 02_eda/eda_caracterizacion.qmd
```

Los HTMLs generados quedan en `_site/` y en las carpetas `*_files/`.

## Parámetros y variables de entorno

* `EDA_YEAR` / `EDA_WEEK` (int): seleccionan particiones.
* `EDA_SAVE_GOLD` (bool-like): si el EDA exporta productos.
* `GOOGLE_APPLICATION_CREDENTIALS`: ruta a credenciales (opcional si usas ADC).
* `QUARTO_PROJECT_DIR`: resuelve rutas a `lib/` cuando ejecutas fuera de la raíz.

## Buenas prácticas

* **Bronze es idempotente**: políticas `write_missing`/`upsert` evitan re-escrituras completas.
* **Silver/Gold** deberán incluir **checks** (conteos, nulos, rangos) y **metadatos** (fecha, versión de código).
* **Privacidad**: todo está pseudonimizado; no subir credenciales ni datos sensibles locales al repo.

## Workflow de Git

Este proyecto usa una estrategia de ramas estructurada:
- `main` - Código estable para hitos importantes
- `develop` - Desarrollo activo y trabajo diario
- `feature/*` - Funcionalidades nuevas
- `docs/*` - Documentación y paper

📖 **Ver guía completa en:** [`GIT_WORKFLOW.md`](GIT_WORKFLOW.md)

## Dónde leer avances y estado del proyecto

La ubicación canónica para entender el estado del trabajo es:

- [`docs/planning/`](docs/planning/)

Ahí la documentación se divide en dos capas:

- [`docs/planning/workstreams/`](docs/planning/workstreams/)
  - bitácora operativa viva por línea de trabajo
  - cada workstream mantiene:
    - `notes.md`
    - `task_plan.md`
  - si quieres entender en qué se está trabajando **hoy**, parte aquí

- [`docs/planning/stages/`](docs/planning/stages/)
  - síntesis histórica por etapas del proyecto
  - no replica el detalle diario; resume hitos, decisiones y outputs
  - si quieres entender **cómo evolucionó** la tesis, parte aquí

Archivos guía:

- [`docs/planning/README.md`](docs/planning/README.md): convención de uso
- [`docs/planning/project_timeline.md`](docs/planning/project_timeline.md): línea de tiempo corta
- [`docs/planning/legacy_map.md`](docs/planning/legacy_map.md): mapeo entre rutas antiguas y nuevas

### Importante

- La carpeta histórica [`docs/plans/tesis-project/`](docs/plans/tesis-project/) queda como **legacy temporal**.
- Los nuevos avances deben registrarse en [`docs/planning/workstreams/`](docs/planning/workstreams/).
- Parte del backfill histórico también se apoya en:
  - [`docs/avances/`](docs/avances/)
  - notebooks en `02_eda/` y `03_models/`

## Contribuciones

Este es un proyecto de tesis. Para dudas o colaboraciones, contactar a Juan Vicente Onetto Romero.

## Licencia

Por definir
