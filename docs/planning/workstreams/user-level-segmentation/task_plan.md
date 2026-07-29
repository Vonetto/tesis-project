# Segmentacion User-Level / Perfiles Latentes

## Objetivo

Construir un frente separado de segmentacion/perfilamiento a nivel
`id_tarjeta`, usando patrones de movilidad y comportamiento observados para
obtener perfiles latentes sin usar `QR/BIP` como input. Luego cruzar esos
perfiles con `QR vs BIP`, `QR_OTHER` y `QR_RED` para evaluar si existen
segmentos asociados descriptivamente a adopcion QR.

Este frente continua el rediseño user-level, pero NO reemplaza ni bloquea el
benchmark ML. Debe quedar abierto a nuevas matrices y variables conductuales
porque el set supervisado de ML sigue evolucionando.

## Decisiones Cerradas

- Unidad: `id_tarjeta` como proxy operacional de usuario.
- Universo v1: `interannual_ml + clean + home_filter=alta + min_trips=3`.
- Objetivo v1: perfiles no supervisados primero; features para ML quedan como
  fase posterior.
- Metodo principal v1 ejecutado: NMF sobre matriz no negativa
  `macro_franja_modo/share`.
- Sensibilidades metodologicas planificadas: PCA diagnostico, clustering sobre
  scores y sparse k-means sobre matrices conductuales amplias.
- Target QR/BIP queda fuera de la factorizacion.
- `tipo_tarjeta`, `is_qr`, `is_qr_red`, `is_qr_other` y derivados solo se usan
  para caracterizacion post-hoc.
- Matriz principal v1: `macro_franja_modo`.
- Normalizacion principal v1: shares por tarjeta (`row-share`), para perfilar
  estructura de uso y no solo intensidad.
- `n_viajes`, residencia, cohorte y socio-demografia quedan como metadata
  externa para describir segmentos, no como input inicial del NMF.
- `k=4` queda como especificacion principal v1 por seleccion no supervisada
  (`elbow_consensus_k=4`).
- `k=5` queda como sensibilidad porque mejora la separacion descriptiva QR/QR_RED
  sin aumentar demasiado la fragmentacion.
- Para NMF sobre `behavioral_wide v0b`, usar transformacion no negativa robusta:
  `clip(p01,p99) + minmax [0,1] + block_weight`; no usar z-score.
- El frente no debe avanzar con una matriz unica "todo adentro" sin clasificar
  variables. Primero se construye un catalogo por rol analitico.
- Se separan dos familias de matrices futuras:
  - `behavioral_wide`: uso + ritmo + rutina + estructura diaria + posibles
    scores de movilidad.
  - `structural_wide`: `behavioral_wide` + socio-demografia + geografia +
    oferta/acceso como sensibilidad socio-territorial.

## Arquitectura Propuesta

Outputs bajo:

```text
tmp/audits/user_level_redesign/segmentation/
```

Scripts actuales:

```text
scripts/audits/build_user_mobility_segmentation_matrix.py
scripts/audits/run_user_nmf_segmentation.py
scripts/audits/summarize_user_nmf_segments.py
```

Scripts a adaptar o crear para fases siguientes:

```text
scripts/audits/build_user_segmentation_variable_catalog.py
scripts/audits/build_user_behavioral_segmentation_matrix.py
scripts/audits/run_user_segmentation_pca.py
scripts/audits/run_user_sparse_kmeans_segmentation.py
scripts/audits/summarize_user_segmentation_solution.py
```

Nota: existen scripts historicos de PCA/sparse k-means bajo `scripts/audits/`
para matrices `segmentation_behavioral_2x2`. Se pueden reutilizar como
referencia metodologica, pero deben adaptarse al universo user-level actual y
al contrato de variables catalogadas.

Estado 2026-06-04:

- `scripts/audits/build_user_behavioral_segmentation_matrix.py` creado para
  materializar `behavioral_wide v0/v0b`.
- Los scripts historicos `run_segmentation_pca.py` y
  `run_segmentation_sparse_kmeans.py` ya corren sobre el parquet `v0b` usando
  el inventario nuevo, por lo que no hace falta duplicarlos todavia.

Notebook previsto:

```text
02_eda/eda_user_level_segmentation.qmd
02_eda/eda_user_level_segmentation_block_audit.qmd
```

Catalogo vivo:

```text
docs/planning/workstreams/user-level-segmentation/variable_catalog.md
```

Convencion de matriz:

- Filas: `id_tarjeta`.
- Features: columnas `seg_*` no negativas.
- Metadata minima: `tipo_tarjeta`, `is_qr`, `is_qr_red`, `is_qr_other`,
  `n_viajes`, `share_trips_2025`, `home_confidence`.
- Inventario: lista explicita de columnas usadas como input NMF para evitar
  leakage accidental.

CLI candidato v1 del builder:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/build_user_mobility_segmentation_matrix.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --matrix-spec macro_franja_modo --normalization share --force
```

CLI candidato v1 del NMF:

```bash
/Users/vicenteonetto/.local/share/mamba/envs/larch-env/bin/python \
  scripts/audits/run_user_nmf_segmentation.py \
  --scope interannual_ml --variant clean --home-filter alta --min-trips 3 \
  --matrix-spec macro_franja_modo --normalization share \
  --k-range 2-8 --n-runs 10 --seed 20260527
```

Nota operativa: el runner NMF usa `--fit-sample-size 300000` por defecto para
ajustar componentes en una muestra y transformar luego la matriz completa. Usar
`--fit-sample-size 0` solo si se quiere ajustar NMF sobre todas las tarjetas.

## Plan Por Fases

### Fase 1 — Cerrar lectura de NMF existente

Objetivo: exprimir la prueba `macro_franja_modo/share` antes de agregar
variables.

Tareas:

1. Consolidar tabla de segmentos `k=4` y `k=5`.
2. Revisar top features por componente.
3. Proponer nombre tentativo para cada segmento.
4. Cruzar con tamaño, QR lift, QR_RED lift y QR_OTHER lift.
5. Perfilar externamente con `n_viajes`, `share_trips_2025`, residencia/origen
   y bloques conductuales disponibles.
6. Decidir si `k=4` es baseline interpretable y si `k=5` aporta una sensibilidad
   sustantiva o solo fragmenta.

Estado:

- Matriz construida.
- NMF `k=2..8` corrido.
- Post-hoc QR/BIP corrido.
- Mini-validacion provisional cerrada:
  - `k=4` baseline de primera version.
  - `k=5` sensibilidad interpretable.
  - La segmentacion espacio-franja-modo produce perfiles claros.
- Pendiente si se quiere profundizar antes de avanzar: etiquetado humano final
  de segmentos con tablas/figuras para reporte.

### Fase 2 — Catalogo de variables candidatas

Objetivo: clasificar variables antes de construir nuevas matrices.

Roles del catalogo:

- `input_mobility_pattern`: variables o scores de patron espacial/franja/modo.
- `input_behavioral`: uso agregado, rhythm, routine y daily_tour.
- `input_structural_sensitivity`: socio-demografia, geografia, oferta,
  OSM/BIP access.
- `posthoc_only`: variables utiles para describir segmentos, pero no para
  construir el segmento principal.
- `exclude`: target, derivados de QR/BIP, scores arbitrarios, duplicados fuertes
  o variables con problemas de construccion.

Criterios:

- No incluir `is_qr`, `tipo_tarjeta`, `is_qr_red`, `is_qr_other` ni derivados.
- No incluir simultaneamente proxies casi equivalentes de intensidad como
  `n_viajes`, `n_dias_activos` y `n_semanas_activas` sin reduccion.
- Mantener scores compuestos arbitrarios como diagnostico/sensibilidad, no como
  input principal.
- Marcar variables modales de `routine_pack` y `daily_tour_pack` como
  `requiere_rebuild` si dependen de artefactos previos al fix modal.

### Fase 3 — Factibilidad y salud de datos

Objetivo: saber que variables pueden entrar a PCA/sparse k-means sin introducir
ruido metodologico.

Auditorias:

- Missing por variable.
- Varianza casi cero.
- Outliers y necesidad de transformaciones (`log1p`, winsor, clipping).
- Correlaciones fuertes dentro y entre bloques.
- Redundancia por familias.
- Requerimientos de escalamiento y balance por bloque.

Salida esperada:

- Lista `behavioral_wide_main`.
- Lista `behavioral_wide_sensitivity`.
- Lista `structural_wide_sensitivity`.
- Lista `exclude` con razon.

### Fase 4 — Matriz `behavioral_wide`

Objetivo: construir una matriz conductual amplia, separada de lo
socio-territorial.

Bloques candidatos:

- Uso agregado parsimonioso.
- `rhythm_main`.
- `routine_selected_main`.
- `daily_tour_main`.
- Scores o componentes de `macro_franja_modo` en vez de las 88 columnas crudas,
  si se decide evitar dominancia dimensional del bloque espacial/franja/modo.

Caveat:

- Balancear bloques. Si un bloque tiene muchas mas columnas, puede dominar PCA
  o clustering sin ser realmente mas importante.

### Fase 5 — PCA diagnostico

Objetivo: diagnosticar ejes dominantes, redundancia y variables fuertes; no
definir segmentos finales automaticamente.

Preguntas:

- Que explican PC1, PC2, PC3.
- Que variables cargan fuerte por componente.
- Que bloques dominan la varianza.
- Si algun componente se asocia post-hoc con QR, QR_OTHER o QR_RED.

Entregables:

- Varianza explicada.
- Loadings por componente.
- Ranking de variables por contribucion absoluta.
- Lectura sustantiva de ejes.

### Fase 6 — Sparse k-means conductual

Objetivo: usar sparse k-means como selector/validador de variables conductuales
fuertes.

Preguntas:

- Que variables reciben peso.
- Que bloques sobreviven.
- Si los clusters son interpretables y estables.
- Si separan QR/QR_RED post-hoc mas que NMF baseline.

Caveat:

- No interpretar pesos como importancia causal. Son variables utiles para
  separar clusters bajo una especificacion y escalamiento dados.

### Fase 7 — Sensibilidad estructural

Objetivo: probar si agregar socio-demografia, geografia y oferta/acceso cambia
la naturaleza de los segmentos.

Matriz:

- `structural_wide = behavioral_wide + socio + geo + oferta/acceso`.

Lectura:

- Si domina macrozona/educacion/oferta, la solucion debe reportarse como perfil
  usuario-contexto o socio-territorial, no como segmentacion conductual pura.
- Evaluar especialmente QR_RED, porque EDA previo mostro una señal
  socio-geografica mas clara para ese grupo.

### Fase 8 — Comparacion y narrativa final

Comparar:

- NMF `macro_franja_modo/share`.
- PCA + clustering conductual.
- Sparse k-means conductual.
- Sparse k-means/PCA estructural como sensibilidad.

Criterios:

- Interpretabilidad.
- Tamaños de segmentos.
- Estabilidad.
- Asociacion post-hoc QR/BIP.
- Coherencia con hallazgos previos.
- Utilidad narrativa para tesis.

## Hitos Operativos

1. Crear workstream persistente con `task_plan.md` y `notes.md`. Completado.
2. Definir contrato de matriz `macro_franja_modo` y outputs de auditoria.
   Completado.
3. Implementar builder de matriz de movilidad user-level. Completado.
4. Implementar auditorias de matriz antes de NMF. Completado.
5. Implementar runner NMF con seleccion de `k` basada en reconstruccion,
   estabilidad, tamaños e interpretabilidad. Completado.
6. Implementar resumen post-hoc de segmentos contra QR/BIP y metadata externa.
   Completado.
7. Crear QMD de lectura `eda_user_level_segmentation.qmd`. Completado.
8. Etiquetar e interpretar segmentos `k=4` y sensibilidad `k=5` con top
   features y perfiles externos. Mini-validacion provisional completada.
9. Construir catalogo de variables candidatas por rol analitico. Pendiente.
10. Auditar factibilidad de variables para `behavioral_wide`. En progreso:
    notebook `02_eda/eda_user_level_segmentation_block_audit.qmd`, primer
    bloque intensidad cerrado provisionalmente; bloque horario/franja cerrado
    provisionalmente; bloque regularidad/ritmo cerrado provisionalmente;
    bloque modo/transbordo cerrado provisionalmente; bloque espacial/OD/zonas
    cerrado provisionalmente; bloque rutina/repeticion cerrado
    provisionalmente; bloque daily-tour/estructura diaria cerrado
    provisionalmente con caveat cross-block.
11. Construir matriz `behavioral_wide`. En progreso: seccion diagnostica
    `behavioral_wide v0` agregada al notebook de auditoria; calidad conjunta
    aprobada; `behavioral_wide v0b` agregado y renderizado como prueba
    reducida. Resultado inicial: baja pares cross-block altos sin cambiar el
    numero de PCs necesarios para 80% de varianza.
12. Correr PCA diagnostico sobre `behavioral_wide`. En progreso: `v0b_alta_n3`
    materializado y corrido con PCA+KMeans reproducible. Resultado inicial:
    9 PCs para 80% varianza; KMeans sobre PCs sugiere mirar `k=3` por
    silhouette y `k=4` por codo/continuidad interpretativa.
13. Correr sparse k-means sobre `behavioral_wide`. En progreso: primera pasada
    `v0b_alta_n3` para `k=2/3/4` sin permutaciones. Lectura inicial: util como
    selector de variables fuertes, pero no mejora clustering frente a PCA+KMeans
    cuando se fuerza alta sparsidad.
14. Definir transformacion NMF para `behavioral_wide v0b`. Completado:
    `clip(p01,p99) + minmax [0,1] + block_weight`, manteniendo orientacion
    natural de variables y QR/BIP fuera del input.
15. Correr NMF sobre `behavioral_wide v0b` transformado. En progreso:
    primera pasada completada con `k=2..8`, 5 semillas, muestra 300k. Codo
    consenso `k=4`; `k=5` queda como sensibilidad por segmento pequeno de
    anclaje laboral/peak con alta senal QR post-hoc. Paquete visual de revision
    creado en `behavioral_wide_nmf_review.html`. Sensibilidad `k=4/5` corrida
    para `alta_n5`, `alta_n10` y `alta_n3_home3`: confirma perfil QR-heavy
    laboral/peak en `k=5`, pero no mejora la separacion geometrica. Pendiente:
    repetir corrida final con mas semillas/iteraciones si se congela NMF como
    resultado de tesis, y guardar scores/membresias.
16. Evaluar sensibilidad `structural_wide`. Completado:
    se construyo `structural_wide_v1` como `behavioral_wide_v0b` + socio-
    residencial + macrozonas + acceso BIP + oferta + OSM. NMF `k=5` entrega
    segmento QR_RED alto y robusto en universos `alta_n3`, `alta_n5`,
    `alta_n10` y `alta_n3_home3`; las pruebas `v1_no_macro` y
    `v1_socio_only` muestran que la senal no depende solo de la dummy Oriente.
    El diagnostico post-hoc de controles indica que la asociacion bruta
    Oriente->QR_RED se explica principalmente por educacion/socio residencial.
17. Evaluar si scores/segmentos pasan a `prototype_pack` o al ML como fase
    posterior.

## Criterios De Validez

- La matriz debe tener un `id_tarjeta` unico por fila.
- Las columnas `seg_*` deben ser no negativas y sin NaN.
- El inventario de features NMF no puede contener target ni variables derivadas
  de QR/BIP.
- En normalizacion `share`, la suma por fila de `seg_*` debe ser 1 para tarjetas
  con masa valida.
- No seleccionar `k` usando tasa QR/BIP.
- Componentes deben ser interpretables por sus top features.
- Segmentos duros deben tener tamaño razonable o justificarse como nicho.
- La asociacion con QR/BIP es descriptiva, no causal.

## Preguntas Abiertas

- Si `macro_franja_modo` resulta demasiado gruesa, probar primero
  `od_macro` o `macro_franja`.
- Definir si incluir sensibilidad `alta_n5`/`alta_n10` para mejorar estabilidad
  de perfiles en usuarios con mas viajes.
- Definir si se re-ejecuta la matriz con el patch de nombres `seg_*` limpios o
  si se mantienen los outputs actuales para continuidad de resultados.
- Definir si `behavioral_wide` usa las 88 columnas `macro_franja_modo` crudas,
  scores NMF, o ambas como sensibilidad.
- Definir estrategia de ponderacion por bloque antes de PCA/sparse k-means.
- Definir si componentes/segmentos se integran al ML como `prototype_pack`
  luego de demostrar estabilidad e interpretabilidad.
- Definir narrativa final: perfiles latentes como resultado principal de
  segmentacion o como apoyo interpretativo del frente ML/econometrico.
