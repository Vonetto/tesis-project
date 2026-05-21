# Gemini CLI Onboarding — Cross-Worktree Model Coordination

## Fecha: 2026-05-18

He procesado la documentación del workstream actual (`task_plan.md`, `notes.md`, `model_matrix.md`, `feature_registry.md`) y la `narrativa_actual_tesis.md`. 

### Entendimiento Central de la Tesis
- **Objetivo Explicativo:** La tesis se centra en entender la adopción digital (`QR_RED` y `QR_OTHER` vs `BIP`) basándose en atributos territoriales (Censo, OSM, EOD) y operacionales (tiempos, transbordos). No busca causalidad individual estricta ni es un ejercicio puramente predictivo.
- **Modelo Principal:** El modelo MNL `parsimonious` (que incluye macrozonas y variables socio/OSM limpias) es la línea base econométrica y analítica.
- **Rol del ML (tesis-project-ml):** XGBoost y SHAP actuaron como **diagnóstico de adecuación funcional**. Validaron que:
  - El MNL no pierde mucha señal frente a modelos no lineales (brecha de ~2pp en ROC-AUC).
  - La dirección de los efectos coincide cualitativamente en los beeswarms de SHAP con los betas del MNL.
  - **Restricción Narrativa:** No se harán comparaciones cuantitativas directas de signos entre SHAP y MNL en la tesis debido a colinealidad territorial.
- **Segmentación (tesis-project-segmentation):** Es descriptiva y basada en comportamiento observado, evitando circularidad con los modelos de elección.

### Estado Actual del Workstream
El frente ML ya está cerrado para esta iteración. Los siguientes pasos prioritarios identificados son:
1. **Desbloquear segmentación:** Rematerializar muestras MNL preservando `id_tarjeta` (via `06_materialize_segment_model_samples.qmd` en el worktree respectivo).
2. **Interpretación Formal:** Cerrar la comparación de los modelos Larch (agregado vs nested vs observado) del notebook 16.
3. **Redacción de Resultados:** Iniciar la escritura del Capítulo 4 usando el MNL parsimonious como eje, con sensibilidades Larch y SHAP visual como apoyo.

Estoy alineado con las convenciones de `planning-with-files` y el marco de trabajo. Quedo a disposición para ejecutar cualquiera de estos pasos.