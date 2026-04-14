## Pre-fix OD-buffers snapshot — 2026-03-25

Este directorio congela la foto **pre-fix** de OD-buffers que sí quedó
formalmente reportada en `docs/planning/workstreams/od-buffers-nested-logit/notes.md`
antes de reprocesar semanas tras el fix de terminales stale en
`04_transbordos_metro.qmd`.

Se archivaron solo estos cuatro resultados:

- `biogeme/2025-W17-option1-v2-sample60pct`
- `biogeme/2025-W17-mnl-option1-v2-sample60pct`
- `larch/2025-W17-nested-od-buffers-option1-v2-full`
- `larch/2025-W17-mnl-od-buffers-option1-v2-full`

Motivo de selección:

- Son los resultados OD-buffers que quedaron **cerrados en la narrativa del proyecto**
  como contraste principal `nested vs MNL`.
- En `docs/planning/workstreams/od-buffers-nested-logit/notes.md` quedaron reportados explícitamente como:
  - `Biogeme sample60pct`
  - `Larch full`
- Existen artefactos más nuevos en disco, como `sample10pct` nested en Biogeme,
  pero no quedaron documentados como baseline formal y además conviven con caches
  intermedios compartidos por sample.

Uso recomendado:

- tratar este snapshot como referencia **pre-fix** para comparación posterior;
- no usarlo como resultado final vigente una vez que se complete el rerun post-fix.
