# User Segmentation and Clustering

## Goal

Retomar la línea de segmentación de usuarios planteada en la propuesta inicial de tesis y conectarla ordenadamente con el frente actual de modelos de elección de medio de pago (`BIP`, `QR_RED`, `QR_OTHER`).

La idea no es reemplazar el modelo logit territorial, sino construir una capa complementaria que permita identificar perfiles de comportamiento y evaluar si la adopción de tecnologías digitales cambia entre segmentos.

## Branch / Worktree

- Branch: `feature/user-segmentation-clustering`
- Worktree: `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-segmentation`
- Base: `feature/od-buffers-enriched-controls` at commit `26ac0b7`

## Scope

- Unidad principal tentativa: usuario/tarjeta anonimizada, no viaje individual.
- Insumos: viajes 2024-2025, variables de uso del sistema, adopción QR, fricciones de viaje, patrones temporales y contexto territorial ya construido.
- Output esperado: segmentos interpretables y reproducibles, con validación descriptiva y uso posterior en modelos MNL o sensibilidades.

## Tasks

- [x] Crear rama y worktree separado para aislar el frente de segmentación.
- [x] Registrar decisiones iniciales y plan de trabajo.
- [ ] Definir unidad de análisis exacta y criterios de inclusión de usuarios.
- [ ] Diseñar tabla usuario-nivel con features de comportamiento.
- [ ] Separar features candidatas por familia: intensidad de uso, temporalidad, multimodalidad, fricciones, adopción QR y contexto territorial.
- [ ] Hacer EDA de features usuario-nivel antes de clusterizar.
- [ ] Probar enfoques de segmentación simples e interpretables (`k-means`, clustering jerárquico, posiblemente GMM o LCA si aporta).
- [ ] Validar estabilidad y sentido sustantivo de los segmentos.
- [ ] Evaluar cómo conectar segmentos con modelos de elección: interacciones, modelos por segmento o comparación descriptiva de adopción.
- [ ] Documentar resultados y decisión metodológica para el informe/tesis.

## Guardrails

- No empezar con algoritmos complejos antes de definir bien la unidad de análisis.
- No usar variables post-tratamiento que hagan circular la interpretación de adopción QR, salvo que se usen explícitamente para describir adopción.
- Priorizar interpretabilidad sobre performance predictiva.
- Mantener separados los objetivos: segmentar comportamiento de usuarios no es lo mismo que estimar causalidad.
- Evitar contaminar el worktree principal de modelos logit.
