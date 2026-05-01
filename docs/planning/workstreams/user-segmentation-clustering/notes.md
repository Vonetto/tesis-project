# User Segmentation and Clustering Notes

## 2026-05-01 - Apertura del workstream

Se decide abrir un frente separado de segmentación/clustering para recuperar el foco de la propuesta inicial de tesis.

### Motivación

La propuesta original no se limitaba a estimar modelos logit de elección de medio de pago. También planteaba caracterizar comportamientos de usuarios, identificar perfiles o segmentos y estudiar cómo esos perfiles se relacionan con la adopción de tecnologías digitales en transporte público.

El trabajo reciente avanzó fuertemente en la especificación MNL territorial e infraestructura de acceso, pero dejó pendiente esta capa de segmentación. Este workstream busca reconectar ambos frentes sin desordenar la rama principal.

### Decisión de organización

- Se creó el worktree:
  - `/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project-segmentation`
- Se creó la rama:
  - `feature/user-segmentation-clustering`
- La rama parte desde:
  - `feature/od-buffers-enriched-controls`
  - commit `26ac0b7`
- La rama fue publicada en `origin`.

### Decisión metodológica inicial

La segmentación debe pensarse principalmente a nivel de usuario/tarjeta anonimizada, no a nivel de viaje individual.

Razón:

- el modelo logit actual explica elección en viajes;
- la segmentación busca describir perfiles de comportamiento persistente;
- por lo tanto, necesita features agregadas por usuario en una ventana temporal.

### Rol respecto al modelo MNL

La segmentación se tratará como una capa complementaria:

- primero se construyen perfiles de comportamiento;
- luego se evalúa si esos perfiles ayudan a interpretar diferencias en adopción de `QR_RED` y `QR_OTHER`;
- finalmente se decide si los segmentos entran al modelo como interacciones, como modelos separados por segmento o como análisis descriptivo paralelo.

No se asume de entrada que el modelo MNL final deba reemplazarse por un modelo segmentado.

### Preguntas iniciales

- ¿Cuál es la unidad de usuario disponible y estable entre 2024 y 2025?
- ¿Qué ventana temporal usar para construir perfiles?
- ¿Se segmenta usando solo comportamiento de viaje o también contexto territorial?
- ¿La adopción QR debe ser una variable usada para formar segmentos o una variable usada para describir segmentos?
- ¿Conviene separar primero usuarios frecuentes de usuarios esporádicos?
- ¿Qué hacemos con usuarios observados en solo un año?

### Primer enfoque recomendado

Partir con una tabla usuario-nivel simple:

- número de viajes observados;
- share de viajes por medio de pago;
- indicador de adopción QR;
- diversidad de horarios/franjas;
- frecuencia de uso en días laborales/no laborales;
- tiempos promedio y dispersión de viaje;
- transbordos promedio;
- uso de metro/bus o combinaciones modales;
- diversidad espacial de zonas de origen/destino;
- contexto territorial promedio o dominante de origen.

Luego hacer EDA antes de aplicar clustering.

### Riesgos

- Confundir segmentos de comportamiento con segmentos socioeconómicos.
- Crear clusters dominados solo por intensidad de uso.
- Incluir adopción QR en el clustering y luego interpretar mecánicamente que los clusters explican adopción QR.
- Forzar demasiados clusters sin estabilidad ni interpretación clara.
