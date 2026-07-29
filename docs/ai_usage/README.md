# Registro de uso estructural de IA

Este directorio conserva un historial de los prompts relevantes utilizados en el
proyecto y de la forma en que la IA participó en cada tarea.

## Objetivo

Poder reconstruir a posteriori:

- qué instrucciones sustantivas se dieron;
- qué decisión, análisis o implementación se solicitó;
- cómo se utilizó la IA;
- qué herramientas y artefactos estuvieron involucrados;
- cuál fue el resultado de cada intervención.

No es un log completo de conversación. Es un registro curado de decisiones y
trabajo estructural.

## Fuente de verdad

- `prompt_history.sqlite3`: base consultable.
- `prompt_history.jsonl`: exportación legible y versionable, sincronizada después
  de cada inserción.

Ambos archivos son administrados por `scripts/ai_usage_log.py`.

## Cómo se mantiene entre chats

El sistema usa tres capas:

1. **Carga automática de reglas.** Codex lee `AGENTS.md` y Claude Code lee
   `CLAUDE.md` al trabajar dentro de este repositorio.
2. **Gate por turno.** Antes de responder definitivamente, el agente clasifica el
   prompt y registra la entrada si cumple los criterios de relevancia.
3. **Reconciliación.** Al cerrar un workstream, commit o handoff, se comparan las
   decisiones de planning/notas con el historial y se incorporan omisiones.

Al iniciar una sesión, el agente debe consultar las últimas entradas:

```bash
python scripts/ai_usage_log.py list --limit 5
```

La base persiste fuera del contexto conversacional, por lo que un chat nuevo no
necesita recordar el chat anterior para conocer la política o los registros.

## Límite de la automatización

Una base local no puede detectar por sí sola un prompt omitido si el cliente de IA
no cargó `AGENTS.md`/`CLAUDE.md` o ignoró la instrucción. Por eso:

- los clientes que no lean esos archivos deben recibir explícitamente la regla;
- la reconciliación periódica debe usar el historial/exportación del chat cuando
  esté disponible;
- `prompt_history.jsonl` permite revisar y versionar las entradas sin depender de
  SQLite.

La garantía es fuerte para agentes que respetan las instrucciones del repositorio,
pero no es una captura automática universal de todas las plataformas de chat.

## Qué se registra

Registrar el prompt cuando establece, cambia o aprueba de manera explícita:

1. objetivos, alcance, supuestos o metodología;
2. construcción o transformación de datos;
3. auditorías, análisis o criterios de decisión;
4. modelos, variables, validación o evaluación;
5. implementación, debugging o arquitectura;
6. planes reproducibles, documentación o reglas de gobernanza;
7. selección o descarte de una alternativa concreta.

Ejemplos:

- `Construyamos la demanda bus por zona y por paradero, excluyendo la tarjeta.`
- `Use GTFS como fuente canónica para la oferta Metro.`
- `Agrega un test que reproduzca este error antes de corregirlo.`
- `No llevemos esta variable al modelo principal; déjala como sensibilidad.`

## Qué no se registra

- `ok`, `gracias`, `me parece`, `sigue`;
- aprobaciones sin contenido sustantivo nuevo;
- preguntas casuales o cambios menores de redacción;
- reintentos operativos que no cambian el método;
- tablas o logs pegados sin una pregunta o decisión nueva;
- duplicados de una instrucción ya registrada;
- credenciales, secretos o información personal innecesaria.

Un prompt breve sí se registra si contiene una instrucción estructural, por
ejemplo: `ok, pasemos a construir Metro por estación-hora`.

## Tratamiento de entradas grandes

Guardar la parte del mensaje que contiene la instrucción. No copiar tablas,
salidas extensas ni archivos adjuntos completos. Referenciarlos mediante
`--input-ref`, por ejemplo:

```text
block13g-operational-offer-socio-territorial-audit
02_eda/tmp/operational_offer_demand/operational_card_exposure.parquet
```

## Categorías

- `architecture`
- `data-methodology`
- `analysis-audit`
- `modeling`
- `implementation`
- `debugging`
- `planning-decision`
- `workflow-governance`
- `documentation`
- `other-structural`

## Uso

Inicializar:

```bash
python scripts/ai_usage_log.py init
```

Registrar:

```bash
python scripts/ai_usage_log.py record \
  --category data-methodology \
  --prompt "Construyamos demanda bus específica por zona y paradero." \
  --summary "Construir demanda bus específica" \
  --relevance-reason "Define una nueva familia de variables operacionales." \
  --requested-outcome "Artefactos reproducibles de demanda bus." \
  --ai-use-summary "La IA diseñó la definición, implementó el script y validó cobertura." \
  --status completed \
  --artifact scripts/audits/build_operational_offer_demand_exposure.py \
  --tool apply_patch \
  --tag operacional
```

Consultar:

```bash
python scripts/ai_usage_log.py list --limit 20
python scripts/ai_usage_log.py show 1
python scripts/ai_usage_log.py stats
```

Exportar:

```bash
python scripts/ai_usage_log.py export \
  --format markdown \
  --output docs/ai_usage/prompt_history.md
```

## Campos principales

| Campo | Contenido |
|---|---|
| `prompt_text` | Parte exacta del prompt que contiene la instrucción |
| `prompt_summary` | Resumen corto y buscable |
| `category` | Tipo de intervención |
| `relevance_reason` | Razón para conservar el prompt |
| `requested_outcome` | Resultado solicitado por el usuario |
| `ai_use_summary` | Cómo se utilizó la IA |
| `result_status` | `planned`, `completed`, `partial` o `blocked` |
| `input_refs_json` | Datos, tablas o archivos de entrada referenciados |
| `artifacts_json` | Archivos o entregables producidos |
| `tools_json` | Herramientas relevantes utilizadas |
| `tags_json` | Etiquetas para consulta posterior |
