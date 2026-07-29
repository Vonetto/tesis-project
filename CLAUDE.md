# tesis-project — Guía para Claude

Este archivo se carga automáticamente al iniciar una sesión de Claude Code en este proyecto. Su propósito es dejar configuradas dos herramientas de continuidad para tareas largas y multi-sesión: **`claude-mem`** (memoria persistente) y **`/plan-with-files`** (planning con archivos).

## Reglas del proyecto (override de defaults)

- Prioridad: **cero bugs y comprensión completa de lo que se hace**. Si algo no se entiende del todo (un cálculo, una transformación, un supuesto del modelo), preguntar o investigar antes de escribir código.
- No avanzar con suposiciones tácitas: anotar supuestos en `notes.md` (ver más abajo) o en memoria.
- Idioma de trabajo: español para conversación; los comentarios de código y nombres de variables siguen lo que ya esté en el archivo correspondiente.

---

## 1. Memoria persistente — `claude-mem`

El plugin **`claude-mem@thedotmack`** está habilitado globalmente (`~/.claude/settings.json → enabledPlugins`) y expone un MCP server que persiste memoria entre sesiones. Está disponible automáticamente en este proyecto.

### Qué guardar en memoria

- **Decisiones de modelado** y la razón detrás (por qué se descartó una alternativa, qué supuesto se asumió).
- **Estructura de los datos** que no es obvia leyendo el código (qué significa cada columna, qué unidades, qué casos atípicos importan).
- **Convenciones del repo** que se hayan aclarado en conversación (rutas, naming, dónde van los outputs).
- **Preferencias de trabajo** que María Antonia indique explícitamente.
- **Gotchas e incidentes**: cosas que rompieron antes y por qué, para no repetir.

### Qué NO guardar en memoria

- Estado operacional del día (qué paso vamos, qué falta) — eso va en `task_plan.md` (ver sección 2).
- Datos brutos, resultados numéricos largos, logs.
- Información derivable trivialmente del código o de `git log`.
- Información personal sensible (financiera, médica, credenciales).

### Cuándo recuperar memoria

- Al inicio de una sesión nueva si el tema parece continuar trabajo previo.
- Cuando el usuario referencia algo de "la otra vez" o "lo que decidimos".
- Antes de hacer una recomendación sobre código que ya tocamos antes — verificar contra la memoria, pero también contra el estado actual del archivo (la memoria puede estar desactualizada).

---

## 2. Planning persistente — `/plan-with-files`

El slash command **`/plan-with-files`** vive en `~/.claude/commands/plan-with-files.md` y está disponible globalmente. Mantiene en disco dos archivos markdown que sobreviven entre sesiones: `task_plan.md` (qué falta) y `notes.md` (decisiones, comandos, outcomes).

### Cuándo invocarlo

- Tareas que abarcan **varias sesiones** (refactor de un módulo, alineación de notebooks con un modelo nuevo, escritura de un capítulo de la tesis).
- Tareas con **5+ pasos** donde es fácil perder el hilo.
- Reproducibilidad: cuando interesa dejar registro de qué comandos se corrieron y por qué.

No usar para preguntas puntuales ni para tareas de un solo paso.

### Ubicación de los archivos

- Por defecto: `~/.claude/plans/tesis-project/` (fuera del repo, no contamina git).
- Fallback si hay restricciones de sandbox: `tesis-project/tmp/plans/`.

### Flujo típico

1. `/plan-with-files <descripción corta de la tarea>` — inicializa `task_plan.md` y `notes.md` desde los templates en `~/.claude/commands/assets/`.
2. Durante el trabajo: actualizar `task_plan.md` al completar pasos o cambiar scope; agregar decisiones a `notes.md` con fecha absoluta (YYYY-MM-DD).
3. Al cerrar: en `notes.md`, dejar estado final (done/partial), archivos cambiados, comandos para reproducir, y follow-ups conocidos.

---

## 3. Cómo se complementan las dos herramientas

| Aspecto | `claude-mem` | `/plan-with-files` |
|---|---|---|
| **Qué guarda** | Conocimiento, decisiones, contexto narrativo | Estado de tarea, pasos pendientes, comandos |
| **Granularidad** | Hechos discretos, perdurables | Lista viva de una tarea concreta |
| **Vida útil** | Indefinida (atraviesa proyectos) | Mientras dure la tarea, luego se archiva |
| **Lectura** | Recuperación contextual (cuando el tema lo amerita) | Inicio de cada sesión donde la tarea sigue abierta |

**Regla de oro**: si la información describe **qué aprendimos**, va a `claude-mem`. Si describe **qué vamos a hacer**, va a `task_plan.md`. Si describe **qué hicimos hoy y cómo se reproduce**, va a `notes.md`.

Ejemplo concreto:
- "El modelo MNL converge mal cuando se usa la variable X sin estandarizar" → **claude-mem** (es un aprendizaje perdurable).
- "Falta correr la calibración v3 con el dataset filtrado" → **task_plan.md**.
- "Hoy 2026-05-15: corrí `python scripts/calibrate_v3.py`, resultados en `03_models/v3/`" → **notes.md**.

---

## 4. Registro de prompts relevantes

El proyecto mantiene un historial auditable del uso estructural de IA en:

- `docs/ai_usage/prompt_history.sqlite3`
- `docs/ai_usage/prompt_history.jsonl`

Al iniciar una sesión nueva en este repositorio, ejecutar:

```bash
python scripts/ai_usage_log.py list --limit 5
```

Esto recupera el contexto reciente del registro, pero no permite asumir que toda
conversación no registrada era irrelevante.

Antes de cerrar cada turno, aplicar la política de `docs/ai_usage/README.md` y
registrar solo prompts que cambien objetivos, alcance, metodología, datos,
modelamiento, implementación, decisiones o reglas de trabajo.

No registrar confirmaciones vacías (`ok`, `me parece`), conversación casual,
pedidos de continuar sin una decisión nueva ni tablas pegadas sin una instrucción
metodológica. Si un prompt corto contiene una decisión sustantiva, sí se registra.

El registro se realiza con:

```bash
python scripts/ai_usage_log.py record --help
```

La entrada debe guardar la parte decisional del prompt y resumir qué hizo la IA,
qué herramientas utilizó y qué artefactos produjo. No guardar secretos ni copiar
datos brutos extensos.

Al cerrar un workstream, antes de un commit o durante un handoff, contrastar las
decisiones estructurales de `task_plan.md` y `notes.md` con las últimas entradas del
historial. Si falta alguna, reconstruirla y marcarla como backfill en `notes`.

---

## 5. Estructura del repositorio (referencia rápida)

```
tesis-project/
├── 00_setup/          # configuración inicial, dependencias
├── 01_processing/     # pipeline de procesamiento de datos
├── 02_eda/            # análisis exploratorio
├── 03_models/         # modelos (carpeta más activa, ~148 subdirectorios)
├── config/            # configuraciones
├── data/              # datasets (no commitear pesados — usar lake/)
├── docs/              # documentación
├── lake/              # datos versionados/pesados
├── lib/               # código reutilizable
├── papers/            # bibliografía
├── scripts/           # scripts auxiliares
├── tmp/               # temporales (incluye codex-skills/ histórico)
├── .planning/         # sistema de planning anterior — NO usar, mantener como histórico
├── biogeme.toml       # config Biogeme
├── _quarto.yml        # config Quarto (documentos)
├── requirements.txt   # deps Python
└── process_data.py    # entry point de procesamiento
```

**Nota sobre `.planning/`**: contiene archivos de un sistema de planning previo (`PROJECT.md`, `ROADMAP.md`, `STATE.md`, etc.). No es lo mismo que `/plan-with-files` y no debe modificarse — queda como registro histórico. El planning activo vive en `~/.claude/plans/tesis-project/`.
