## Post-fix OD-buffers snapshot — 2026-03-25

Snapshot parcial de resultados **post-fix** tras corregir los terminales stale
en `04_transbordos_metro.qmd` y reprocesar los parquets canónicos.

Estado actual del snapshot:

- `biogeme/2025-W17-option1-v2-sample10pct`
- `biogeme/2025-W17-mnl-option1-v2-sample10pct`
- `larch/2025-W17-nested-od-buffers-option1-v2-full`
- `larch/2025-W17-mnl-od-buffers-option1-v2-full`

Lectura preliminar:

- `MNL sample10pct` post-fix mantiene prácticamente la misma historia que el
  baseline pre-fix archivado en `03_models/archives/pre_fix_buffers_2026-03-25/`.
- `Nested sample10pct` post-fix sigue empatando al `MNL`, con `MU_QR = 1` y
  peores criterios de parsimonia, por lo que no cambia la conclusión
  metodológica de que el nido QR no agrega valor.
- `Larch full` post-fix también mantiene la misma narrativa general:
  - `MNL` y `Nested` siguen extremadamente cerca;
  - `Mu:QR = 1.0` en `Nested`;
  - aunque `Nested` mejora levemente el `LL`, el nido permanece pegado al bound,
    por lo que no hay evidencia fuerte de una estructura nested estable y útil.
