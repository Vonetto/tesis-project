# Tesis — Data Lake + EDA

Este repositorio contiene el **setup de datos** (GCS + Parquet) y el **EDA** inicial para la tesis _“Tecnologías digitales y su impacto en la inercia del comportamiento de viaje en transporte público”_ (DCC + MDS, U. de Chile).

El proyecto trabaja **100% contra Google Cloud Storage (GCS)**: los CSV viven en `gs://` y se convierten a **Parquet particionado** para análisis rápidos y reproducibles.

## Arquitectura del proyecto

```
tesis-project/
├─ 00_setup/
│  └─ setup.qmd                # Validación de la capa Bronze
├─ 01_processing/
│  └─ 01_silver_processing.qmd # Procesamiento Bronze→Silver
├─ 02_eda/
│  ├─ eda_caracterizacion.qmd  # Perfil demográfico de usuarios QR
│  ├─ eda_trips_overview.qmd   # Análisis de patrones de viaje
│  └─ join_validation.qmd      # Validación de joins
├─ lib/
│  └─ datalake.py              # Helpers (enable_adc, scan_parquet_portable)
├─ process_data.py             # Pipeline de ingesta RAW→Bronze
├─ _quarto.yml                 # Config del sitio Quarto
├─ GIT_WORKFLOW.md             # Guía de workflow de Git
├─ _site/                      # (generado) HTML renderizados
└─ .quarto/                    # (generado) cachés de Quarto
```

> Las carpetas **`_site/`**, **`_freeze/`** y **`.quarto/`** son artefactos generados por Quarto y **no** deben versionarse.

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

#### d) Análisis Exploratorio (EDA)

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

## Contribuciones

Este es un proyecto de tesis. Para dudas o colaboraciones, contactar a Juan Vicente Onetto Romero.

## Licencia

Por definir



