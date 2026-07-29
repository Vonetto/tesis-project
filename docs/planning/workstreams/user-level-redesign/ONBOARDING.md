# ONBOARDING — Rediseño A Nivel Tarjeta / Usuario

Punto de entrada para una sesión nueva de Claude en este frente. Lee este
archivo primero. Apunta a `notes.md` y `task_plan.md` para detalle.

---

## TL;DR

- **Pregunta de tesis**: qué predice la adopción QR vs BIP en transporte
  público de Santiago.
- **Pivote metodológico** (2026-05-27): la unidad de análisis pasó de viaje a
  `id_tarjeta`. El modelo principal ya no es elección de medio de pago por
  viaje sino adopción de tipo de tarjeta.
- **Universo principal candidato**: panel `interannual_ml_clean` con
  `home_confidence == "alta"` y `n_viajes >= 3`. ~2,46M tarjetas, QR share
  15,3%.
- **Estado**: EDA bloques 1 al 7 completos. BIP friction lookup construido.
  Próximo paso: cerrar definición de variables del main y empezar
  modelamiento.
- **Decisión central pendiente**: confirmar universo (home_alta vs
  home_alta+n_home_dest≥3), umbral n_viajes (3/5/10), y target (binario vs
  multiclase). Hay evidencia para defender multiclase.

---

## Archivos clave (orden de lectura)

| # | Archivo | Para qué |
|---|---|---|
| 1 | `docs/planning/workstreams/user-level-redesign/task_plan.md` | Hitos, decisiones tomadas, preguntas abiertas formales |
| 2 | `docs/planning/workstreams/user-level-redesign/notes.md` | Bitácora cronológica con TODOS los hallazgos por bloque |
| 3 | `02_eda/eda_user_level_panel.qmd` | Notebook EDA (bloques 1, 2, 2b, 3, 4, 5, 6A, 6B, 6C, 7A-7F) |
| 4 | `scripts/audits/build_user_level_payment_panel.py` | Constructor del panel principal |
| 5 | `scripts/audits/build_bip_load_access_zona777.py` | Lookup de fricción BIP por zona777 |
| 6 | `scripts/audits/build_proposito_pk_bridge.py` | Bridge proposito→residencia (interannual_ml) |
| 7 | `scripts/audits/audit_user_level_scope_coverage.py` | Auditoría de cobertura por scope |

**`notes.md` es la fuente canónica.** Si hay contradicción, gana `notes.md`.

---

## Mapa de artefactos persistentes

**No regenerar a menos que se cambie el constructor o la lógica upstream.**

| Artefacto | Path | Tamaño/N |
|---|---|---|
| Panel principal limpio | `tmp/audits/user_level_redesign/user_level_payment_panel_interannual_ml_clean.parquet` | 6.355.016 tarjetas, 92.845.168 viajes, 149 cols |
| Panel con conflictos (sensibilidad) | `tmp/audits/user_level_redesign/user_level_payment_panel_interannual_ml_with_conflicts.parquet` | 6.360.054 tarjetas |
| Bridge residencia | `tmp/audits/proposito_residence/pk_bridge/user_home_candidates_interannual_ml.parquet` | 5.773.880 tarjetas con home inferida |
| Lookup fricción BIP | `tmp/audits/bip_load_access/bip_load_access_by_zona777.parquet` | 803 zonas, 1.903 puntos físicos deduplicados |
| Diagnósticos panel | `tmp/audits/user_level_redesign/user_level_panel_*.csv` | summary, target dist, threshold sensitivity, missing |
| Diagnósticos bridge | `tmp/audits/proposito_residence/pk_bridge/*.csv` | join diagnostics, home_confidence dist |

Detalle de columnas y métodos en `notes.md` secciones:
- Panel: `2026-05-28 — Panel id_tarjeta interannual_ml construido`.
- Bridge: `2026-05-28 — Bridge proposito/residencia interannual_ml completado`.
- BIP load lookup: `2026-05-28 — EDA breve fuente externa: puntos de carga bip!`.

---

## Decisiones cerradas

| Decisión | Valor | Sección de `notes.md` |
|---|---|---|
| Unidad de análisis | `id_tarjeta` como proxy de usuario | `2026-05-27 — Giro Metodologico Post Reunion` |
| Scope panel | `interannual_ml`: 2024-W14..W17 + 2025-W14..W17 (8 semanas) | `2026-05-27 — Auditoria De Cobertura interannual_ml` |
| Target candidato principal | Binario `QR vs BIP` + multiclase `BIP/QR_RED/QR_OTHER` como extensión obligatoria | `2026-05-28 — EDA panel Bloque 6A: socioeconomia residencial` |
| Filtro residencia main | `home_confidence == "alta"` | `2026-05-28 — EDA panel: decisiones preliminares Bloques 1-3` |
| Umbral n_viajes main | `n_viajes >= 3` (candidato principal, no cerrado) | `2026-05-28 — EDA panel: decisiones preliminares Bloques 1-3` |
| Convención modal | Bus = `tipo_transporte` 1 o 3; Metro/ferroviario = 2 o 4 | `2026-05-28 — Convencion modal para panel de usuario` |
| Cohorte temporal | `share_trips_2025` (o dummies de cohorte) entra como control obligatorio | `2026-05-28 — EDA panel: decisiones preliminares Bloques 1-3` |
| Conflictos target | Excluir las 5.038 tarjetas QR_RED↔QR_OTHER del main. Conservar en `with_conflicts.parquet` | `2026-05-28 — Panel id_tarjeta interannual_ml construido` |
| Geografía main | `home_macrozone + origin_top1_macrozone` | `2026-05-28 — EDA panel Bloque 5: geografia y contexto` |
| OSM | Fuera del main inicial; sensibilidad acotada con `origin_top1_university_high_dummy` y `origin_top1_school` | `2026-05-28 — EDA panel Bloque 6B: infraestructura/oferta OSM` |
| Variables `share_mujeres` | Winsor p01-p99 obligatorio antes de usar | `2026-05-28 — EDA panel Bloque 6A: socioeconomia residencial` |
| Renombrar D+E proxy | Documentar como concentración de hogares D+E, NO como ingreso alto | `2026-05-28 — EDA panel Bloque 6A: socioeconomia residencial` |
| Exposición temporal | Solo UNA de {n_viajes, n_dias_activos, n_semanas_activas} en main (r > 0,84 entre las tres) | `2026-05-28 — EDA panel Bloque 6C: colinealidad conjunta` |
| BIP load lookup | Red completa abierta (puntos bip + retail + metro + centros), no solo `Puntos bip!` | `2026-05-28 — EDA breve fuente externa: puntos de carga bip!` |
| Activity vs origin top-1 | NO usar las dos en econométrico (Spearman 0,74-0,77 por variable) | `2026-05-28 — EDA panel Bloque 6B: infraestructura/oferta OSM` |

### Listas de variables candidatas

Detalle exhaustivo en `notes.md`:

- **Variables de uso (Bloque 4)**: ver `2026-05-28 — EDA panel Bloque 4: variables agregadas de uso` → "Lista candidata reducida para modelo interpretable" (10 vars).
- **Geografía (Bloque 5)**: ver `Decision para modelo econometrico` con sensibilidades.
- **Socioeconómicas (Bloque 6A)**: ver `Set socioeconomico candidato para econometrico` (baseline parsimonioso).
- **Decisión integrada (Bloque 6C)**: ver `Decision econometrica` para reglas finales (exposición, modal, geografía, socio, estabilidad espacial, OSM).

---

## Preguntas abiertas

| Pregunta | Posibles caminos | Quien decide |
|---|---|---|
| Universo final: `home_alta` (3,54M) vs `home_alta + n_home_dest_trips_card >= 3` (1,49M) | Trade-off cobertura vs validez de medición. Notes recomienda la segunda como sensibilidad fuerte | Usuario |
| Umbral n_viajes definitivo | 3 (candidato), 5 o 10 como sensibilidades | Usuario |
| Target principal: binario o multiclase | Bloques 6A y 7 muestran que multiclase está justificado por perfil distinto de QR_RED. El binario sigue siendo síntesis útil | Usuario, antes de fittear |
| Discapacidad en main o solo sensibilidad | Correlaciona r=-0,73 con educación. Decidir según foco interpretativo | Usuario |
| Ponderación por `n_viajes` | Profesor dijo que pierde importancia si filtramos ocasionales. Pendiente confirmar | Usuario |
| Split ML temporal | Profesor no dio regla cerrada; aleatorio por tarjeta como base, sensibilidad temporal | Usuario |
| Estabilidad espacial: `origin_zone_top1_share` vs `origin_zone_entropy` | NO usar juntas (r=-0,70). Elegir una | Usuario |

---

## Plan inmediato

Después del EDA bloques 1-7 viene un **conjunto de nuevos bloques de
variables externas** que va a auditarse con la misma plantilla
(cobertura → correlación → ranking univariado → bins → probe árbol):

1. **BIP friction block** (lookup ya construido en
   `bip_load_access_by_zona777.parquet`): incorporar al panel y auditar
   `distance_to_nearest_bip_point` y `bip_load_density_km2` por residencia.
2. **Digital-territorial block**: conectividad SUBTEL + franjas etarias
   Censo. Pendiente decidir granularidad (comuna vs zona).
3. **Info-need block**: headway GTFS, route choice set size, complejidad de
   transbordo. El más costoso, dejar para el final.

Criterio de aceptación por bloque: Δ AUC ≥ 0,01 en `qr_other_vs_bip` (frente
difícil) o en `qr_red_vs_*` (frente sustantivo).

---

## Glosario rápido

- **`id_tarjeta`**: identificador anónimo de tarjeta BIP/QR. Proxy de
  usuario, sabiendo que una persona puede tener más de una.
- **BIP**: tarjeta física tradicional.
- **QR_RED**: pago QR vía app oficial Red Movilidad. ~2,1% de tarjetas.
  Perfil socioeconómico distinto (ORIENTE, alta educación).
- **QR_OTHER**: pago QR vía otras apps/wallets. ~14,6% de tarjetas. Perfil
  conductual-temporal (cohort 2025, ocasional, alta dispersión horaria).
- **`is_qr`**: flag binario QR = QR_RED + QR_OTHER.
- **`home_confidence`**: nivel de concentración modal de la zona_hogar
  inferida desde viajes con `PROPOSITO=HOGAR`. `alta` = top_share ≥ 0,875.
  NO implica muchos viajes de soporte: 46% de tarjetas en `alta` tienen
  sólo 1 viaje destino=hogar observado.
- **`share_trips_2025`**: fracción de viajes del usuario que ocurren en
  2025. Captura cohort temporal. Casi ortogonal a intensidad (r ≈ 0).
- **`res_de_proxy`**: variable estandarizada de concentración de hogares
  D+E proxy en zona de residencia. **z alto = más D+E = zona popular.**
  NO leer como "ingreso alto".
- **scope `interannual_ml`**: 8 semanas (2024-W14..17 + 2025-W14..17).
- **`home_alta`**: filtro `home_confidence == "alta"`.
- **panel limpio**: `interannual_ml_clean.parquet`, excluye conflictos
  QR_RED↔QR_OTHER.

---

## Notas operativas

- **Idioma de trabajo**: español para conversación y documentación.
- **Reglas del proyecto** (CLAUDE.md raíz): cero bugs, comprensión completa
  antes de avanzar. Documentar supuestos en notes.md.
- **Memoria persistente** (`claude-mem`): para aprendizajes durables
  cross-proyecto. `task_plan.md` y `notes.md` para estado operacional de
  este frente.
- **No tocar `.planning/`**: histórico de sistema previo de planning.
- **KINGSTON / TOSHIBA**: discos externos del usuario. El sandbox de Claude
  NO los monta. Cualquier path que dependa de ellos solo se resuelve desde
  la Mac del usuario.
