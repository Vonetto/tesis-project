# Tesis — Data Lake + EDA

Este repositorio contiene el **setup de datos** (GCS + Parquet) y el **EDA** inicial para la tesis _“Tecnologías digitales y su impacto en la inercia del comportamiento de viaje en transporte público”_ (DCC + MDS, U. de Chile).

El proyecto trabaja **100% contra Google Cloud Storage (GCS)**: los CSV viven en `gs://` y se convierten a **Parquet particionado** para análisis rápidos y reproducibles.

## Arquitectura del proyecto

```

tesis-project/
├─ 00\_setup/
│  └─ setup.qmd                # Ingesta a GCS (CSV→Parquet), validaciones
├─ 01\_eda/
│  └─ eda\_trips\_overview\.qmd   # EDA parametrizado por año/semana
├─ lib/
│  └─ datalake.py              # Helpers (enable\_adc, scan\_parquet\_portable, etc.)
├─ \_quarto.yml                 # Config del sitio Quarto
├─ \_site/                      # (generado) HTML renderizados
└─ .quarto/                    # (generado) cachés de Quarto

````

> Las carpetas **`_site/`**, **`_freeze/`** y **`.quarto/`** son artefactos generados por Quarto y **no** deben versionarse.

### Data Lake en GCS

- `gs://tesis-vonetto-datalake/raw/`  
  CSV originales (solo lectura).

- `gs://tesis-vonetto-datalake/lake/bronze/`  
  **Bronze** = datos “aterrizados” en Parquet, con cambios mínimos (parseo de fechas y particiones).
  - `bronze/trips/iso_year=YYYY/iso_week=WW/part-*.parquet`
  - `bronze/caracterizacion/snapshot_date=YYYY-MM-DD/part-*.parquet`

- `gs://tesis-vonetto-datalake/lake/silver/`  
  **Silver** = limpieza y enriquecimiento reutilizable (nombres normalizados, tipos, dedupe, features básicos).

- `gs://tesis-vonetto-datalake/lake/gold/`  
  **Gold** = datasets curados para preguntas/outputs concretos (KPIs, paneles por usuario-semana, métricas de inercia, matrices OD).

Resumen:
- **Bronze**: formato analítico + partición, casi sin “cocina”.
- **Silver**: datos **consistentes** y **reutilizables** para EDA/joins.
- **Gold**: tablas **listas para el paper/modelos**.

## Requisitos

- Python 3.10+ (se probó con Polars ≥ 1.33 y PyArrow ≥ 11).
- Quarto ≥ 1.4 (`quarto --version`).
- Google Cloud SDK (`gcloud`).

Paquetes principales: `polars`, `pyarrow`, `gcsfs`, `fsspec`, `matplotlib`.

## Autenticación (GCP)

Una vez por equipo:
```bash
gcloud auth application-default login
````

O define `GOOGLE_APPLICATION_CREDENTIALS` apuntando a un JSON de Service Account.
Los notebooks usan un helper (`enable_adc`) que levanta automáticamente las credenciales.

## Configuración rápida

1. Crear venv e instalar deps:

```bash
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -U polars pyarrow gcsfs fsspec matplotlib quarto-cli
```

2. Renderizar el **setup** (ingesta CSV→Parquet en bronze):

```bash
quarto render project/00_setup/setup.qmd
```

3. Correr el **EDA** para una semana:

```bash
quarto render project/01_eda/eda_trips_overview.qmd -P year:2025 -P iso_week:17
# Salida HTML queda bajo _site/
```

> También puedes setear env vars y “Run Cell”:
> `EDA_YEAR=2025 EDA_WEEK=17 quarto preview project/01_eda/eda_trips_overview.qmd`

## Parámetros y variables de entorno

* `EDA_YEAR` / `EDA_WEEK` (int): seleccionan particiones.
* `EDA_SAVE_GOLD` (bool-like): si el EDA exporta productos.
* `GOOGLE_APPLICATION_CREDENTIALS`: ruta a credenciales (opcional si usas ADC).
* `QUARTO_PROJECT_DIR`: resuelve rutas a `lib/` cuando ejecutas fuera de la raíz.

## Buenas prácticas

* **Bronze es idempotente**: políticas `write_missing`/`upsert` evitan re-escrituras completas.
* **Silver/Gold** deberán incluir **checks** (conteos, nulos, rangos) y **metadatos** (fecha, versión de código).
* **Privacidad**: todo está pseudonimizado; no subir credenciales ni datos sensibles locales al repo.

## Roadmap breve

* `silver/trips_clean`: normalización, `dur_s`, `wday`, `hour`, etc.
* `gold/user_week_panel`: métricas de inercia (entropía/HHI, stickiness, RCS preliminar).
* Integración con `caracterizacion` (snapshots) a nivel de zona/segmentos.

## Licencia

Por definir



