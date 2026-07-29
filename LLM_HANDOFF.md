# LLM handoff — tesis-project

Este documento es el punto de partida para que un LLM o chat nuevo entienda el
proyecto sin depender del historial conversacional.

## Que es este proyecto

Repositorio de tesis sobre adopcion/uso de QR versus BIP en transporte publico.
Contiene notebooks Quarto, scripts de procesamiento, modelos, reportes, figuras,
documentacion metodologica y artefactos locales asociados.

La lectura rapida recomendada es:

1. `readme.md`: vision general del repo, pipeline, dependencias y estructura.
2. `AGENTS.md`: reglas operativas para Codex/LLM dentro del proyecto.
3. `CLAUDE.md`: contexto historico de uso con Claude, memoria y planning.
4. `docs/planning/`: bitacoras y decisiones del proyecto dentro del repo.
5. `docs/reports/`: reportes enviados o en desarrollo.
6. `02_eda/`: notebooks exploratorios.
7. `03_models/`: notebooks y artefactos de modelamiento.

## Estructura esperada del respaldo

En el disco externo deberia existir una carpeta principal:

```text
tesis-project/
```

Esa carpeta debe contener el worktree completo del repo local y, ademas, los
directorios pesados copiados desde el SSD KINGSTON:

```text
tesis-project/
├── 00_setup/
├── 01_processing/
├── 02_eda/
├── 03_models/
├── docs/
├── lib/
├── scripts/
├── data/
├── output/
├── raw/                 # datos crudos copiados desde KINGSTON
├── lake/                # data lake local copiado/mezclado desde KINGSTON
├── local-artifacts/     # artefactos pesados locales copiados desde KINGSTON
├── LLM_HANDOFF.md
└── ...
```

Si se abre desde otro computador, empezar por esta carpeta y revisar si las rutas
hardcodeadas siguen apuntando a `/Volumes/KINGSTON/tesis-project`. En ese caso,
hay dos opciones:

- montar o renombrar el disco/ruta para replicar esa ubicacion;
- cambiar las rutas a la ubicacion nueva del respaldo.

## Planning-with-files

El proyecto usa archivos persistentes de planificacion fuera del repo. En Codex,
la ubicacion activa es:

```text
/Users/vicenteonetto/.codex/plans/tesis-project/
├── task_plan.md
└── notes.md
```

Estos archivos son distintos de:

- `.planning/`: sistema historico dentro del repo, no usar como planning activo.
- `docs/planning/`: documentacion de proyecto y decisiones que si forman parte del repo.

Como leerlos:

- `task_plan.md`: estado operativo de la tarea activa o del ultimo workstream.
- `notes.md`: decisiones, comandos, resultados y gotchas acumulados.

Si otro LLM trabaja desde el computador secundario, debe pedir estos archivos o
leer la copia incluida en el respaldo si fue exportada junto al proyecto.

## Registro de prompts relevantes

El proyecto audita prompts estructurales en:

```text
docs/ai_usage/prompt_history.sqlite3
docs/ai_usage/prompt_history.jsonl
```

Al comenzar una sesion en el repo, correr:

```bash
python scripts/ai_usage_log.py list --limit 5
```

Antes de cerrar trabajos metodologicos, de datos, modelos o reproducibilidad,
registrar la decision relevante con `scripts/ai_usage_log.py record`.

## Entorno minimo para ejecutar

Instalar en el computador secundario:

- Git.
- Python/Miniforge o Mambaforge.
- Quarto.
- VS Code o editor equivalente.
- ChatGPT/Codex Desktop si se va a trabajar con LLM local.
- Paquetes del proyecto desde `requirements.txt`.

Entorno usado frecuentemente en el Mac principal:

```bash
QUARTO_PYTHON=/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python
```

En otro computador esa ruta no existira; hay que crear un entorno equivalente y
ajustar `QUARTO_PYTHON`.

## Comandos utiles

Listar prompts recientes:

```bash
python scripts/ai_usage_log.py list --limit 5
```

Render de un notebook Quarto:

```bash
quarto render 02_eda/eda_qr_vs_bip_profiles.qmd
```

Buscar rutas hardcodeadas a discos externos:

```bash
rg "/Volumes/KINGSTON|/Volumes/TOSHIBA|Tesis_Local|tesis-project" .
```

## Gotchas

- Hay notebooks con rutas absolutas a `/Volumes/KINGSTON/tesis-project`.
- El respaldo en TOSHIBA puede estar en NTFS; en Mac requiere NTFS for Mac para
  escritura.
- No borrar ni sincronizar con `--delete` hasta confirmar que el respaldo quedo
  completo.
- Los datos pesados pueden estar en `raw/`, `lake/` y `local-artifacts/`.
- El analisis EDA reciente debe trabajarse con cuidado: primero lectura propia,
  luego revision critica; evitar graficos sobreexplicados o lenguaje demasiado
  generado por LLM.
