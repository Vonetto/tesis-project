# Backup index for LLM - tesis-project

Este archivo explica como quedo guardado el respaldo portable de la tesis en el
disco externo. Si un LLM/chat nuevo abre este proyecto desde otro computador,
debe leer este archivo primero y luego `tesis-project/LLM_HANDOFF.md`.

## Ruta principal del respaldo

El respaldo quedo organizado bajo:

```text
/Volumes/TOSHIBA EXT/Vicente/
```

La carpeta principal de trabajo es:

```text
/Volumes/TOSHIBA EXT/Vicente/tesis-project/
```

En esa carpeta se mezclaron dos fuentes:

1. El worktree local completo del repo `tesis-project`, incluyendo `.git`.
2. Los datos y artefactos pesados copiados desde el SSD KINGSTON, integrados en
   la misma raiz del proyecto.

La verificacion basica al momento de crear el respaldo fue:

```text
tesis-project/                         ~463G
planning-with-files/tesis-project/     ~772K
git reconoce tesis-project como worktree
```

## Que abrir primero

Orden recomendado para un LLM:

1. `BACKUP_INDEX_FOR_LLM.md`: este indice del respaldo.
2. `tesis-project/LLM_HANDOFF.md`: contexto del proyecto y reglas de lectura.
3. `tesis-project/readme.md`: estructura general del repo.
4. `tesis-project/AGENTS.md`: reglas operativas para Codex/LLM.
5. `tesis-project/CLAUDE.md`: memoria historica y contexto de trabajo.
6. `tesis-project/planning-with-files/tesis-project/task_plan.md`: snapshot del
   planning persistente.
7. `tesis-project/planning-with-files/tesis-project/notes.md`: notas del
   planning persistente.

## Mapa de carpetas relevantes

```text
Vicente/
├── BACKUP_INDEX_FOR_LLM.md
├── planning-with-files/
│   └── tesis-project/
│       ├── task_plan.md
│       ├── notes.md
│       └── sub-workstreams/
└── tesis-project/
    ├── .git/
    ├── BACKUP_INDEX_FOR_LLM.md
    ├── LLM_HANDOFF.md
    ├── readme.md
    ├── AGENTS.md
    ├── CLAUDE.md
    ├── 00_setup/
    ├── 01_processing/
    ├── 02_eda/
    ├── 03_models/
    ├── docs/
    ├── lib/
    ├── scripts/
    ├── tests/
    ├── data/
    ├── output/
    ├── raw/
    ├── lake/
    ├── local-artifacts/
    └── planning-with-files/
        └── tesis-project/
```

## Que significa cada carpeta

`tesis-project/`
: Worktree principal. Desde aqui deberian correrse los notebooks, scripts,
modelos y comandos del proyecto.

`tesis-project/raw/`
: Datos crudos copiados desde KINGSTON. Incluye viajes, etapas, zonas, puntos
de carga BIP, caracterizacion, censo y otros insumos originales/pesados.

`tesis-project/lake/`
: Data lake local copiado desde KINGSTON. Incluye capas `bronze/` y `silver/`.
Muchas notebooks pueden depender de estos artefactos ya procesados.

`tesis-project/local-artifacts/`
: Artefactos pesados locales copiados desde KINGSTON. Usar como respaldo de
resultados/intermedios que no necesariamente estan versionados en Git.

`tesis-project/data/`
: Datos versionados o semi-versionados del repo, separados de `raw/` y `lake/`.

`tesis-project/output/`
: Salidas generadas, PDFs, figuras y reportes renderizados.

`tesis-project/02_eda/`
: Notebooks exploratorios. Los mas importantes recientemente son:
`eda_qr_vs_bip_profiles.qmd` y `eda_qr_growth_zonal_2024_2025.qmd`.

`tesis-project/03_models/`
: Notebooks y artefactos de modelamiento. Para el flujo zonal reciente revisar
`18_zonal_qr_growth_modeling.qmd`.

`tesis-project/docs/`
: Documentacion, reportes, planning interno, manuscrito y auditoria de prompts.

`tesis-project/scripts/`
: Scripts auxiliares, incluyendo `scripts/ai_usage_log.py`.

## Planning-with-files

El planning persistente original vive fuera del repo en el computador principal:

```text
/Users/vicenteonetto/.codex/plans/tesis-project/
```

En el respaldo se dejaron dos copias:

```text
/Volumes/TOSHIBA EXT/Vicente/planning-with-files/tesis-project/
/Volumes/TOSHIBA EXT/Vicente/tesis-project/planning-with-files/tesis-project/
```

La primera es para encontrarlo facil desde fuera del repo. La segunda queda
dentro del proyecto para que el respaldo sea autocontenido.

Como leerlo:

- `task_plan.md`: estado operativo y checklist del workstream.
- `notes.md`: decisiones, resultados, comandos y advertencias.
- subcarpetas: workstreams especificos, por ejemplo EDA QR vs BIP, outputs,
  socio-demografia, nested logit, etc.

No confundir con:

- `.planning/`: planning historico dentro del repo.
- `docs/planning/`: documentacion versionada de decisiones del proyecto.
- `planning-with-files/`: snapshot exportado del planning persistente de Codex.

## Prompt audit

El proyecto registra prompts metodologicos y decisiones relevantes en:

```text
tesis-project/docs/ai_usage/prompt_history.sqlite3
tesis-project/docs/ai_usage/prompt_history.jsonl
```

Comando recomendado al iniciar una sesion:

```bash
python3 scripts/ai_usage_log.py list --limit 5
```

Si se toma una decision sustantiva, registrar con:

```bash
python3 scripts/ai_usage_log.py record ...
```

## Rutas que probablemente hay que ajustar en otro computador

El proyecto fue desarrollado en macOS y algunas notebooks/scripts pueden tener
rutas absolutas como:

```text
/Volumes/KINGSTON/tesis-project
/Volumes/TOSHIBA EXT/Vicente/tesis-project
/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project
```

En Windows o en otro Mac, buscar rutas hardcodeadas con:

```bash
rg "/Volumes/KINGSTON|/Volumes/TOSHIBA|Tesis_Local|tesis-project" .
```

Si el respaldo se abre desde Windows, las rutas probablemente cambiaran a algo
como `E:\Vicente\tesis-project`. En ese caso, actualizar las rutas en notebooks,
config o variables de entorno antes de renderizar.

## Entorno minimo para ejecutar desde otro computador

Instalar:

- Git.
- Python con Miniforge/Mambaforge o Conda.
- Quarto.
- VS Code o editor equivalente.
- ChatGPT/Codex Desktop si se trabajara con LLM.
- Dependencias del proyecto desde `requirements.txt`.

Ruta de Python usada en el Mac principal para Quarto:

```bash
QUARTO_PYTHON=/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python
```

Esa ruta no existira en otro computador. Crear un entorno equivalente y ajustar
`QUARTO_PYTHON`.

## Advertencias del respaldo

- No fue una copia bit a bit de metadatos. Fue una copia portable con `rsync`.
- No se uso `--delete`; no se borro nada del origen ni del TOSHIBA.
- Git omitio `.git/fsmonitor--daemon.ipc`, que es un socket temporal y no es
  necesario para reconstruir el proyecto.
- El disco TOSHIBA esta en NTFS; en macOS puede requerir NTFS for Mac para
  escribir.
- Antes de borrar cualquier dato del Mac o KINGSTON, verificar manualmente que
  los notebooks relevantes renderizan desde el respaldo.

## Primer chequeo recomendado en otro computador

Desde la carpeta `tesis-project/`:

```bash
git status --short
python3 scripts/ai_usage_log.py list --limit 5
rg "/Volumes/KINGSTON|/Volumes/TOSHIBA|Tesis_Local" .
```

Luego intentar renderizar un notebook pequeno o directamente el notebook que se
quiera continuar, ajustando rutas y entorno si falla.
