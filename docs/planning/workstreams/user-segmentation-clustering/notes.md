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

La segmentación no debe partir asumiendo que `id_tarjeta` identifica usuarios.

Razones:

- `pk_viaje` es una llave primaria de viaje, generada a partir de `id_tarjeta`, `id_viaje` y el timestamp normalizado de inicio;
- `id_tarjeta` identifica una credencial/medio de pago, no necesariamente una persona;
- un mismo usuario podría viajar con tarjeta BIP física y luego con QR, apareciendo como identificadores distintos;
- `is_qr` se deriva operativamente desde `id_contrato`/`contrato`, con contratos `171` y `102` marcados como QR;
- ya existe una advertencia metodológica en `02_eda/eda_trips_overview.qmd`: cada `id_tarjeta` puede ser BIP o QR, por lo que el share QR por `id_tarjeta` no debe interpretarse como adopción gradual de una misma persona.

Por lo tanto, el primer paso del workstream es auditar identificadores y decidir si la segmentación será:

- por credencial/medio de pago;
- por viaje agrupado a nivel de tarjeta;
- por usuario real, solo si existe una llave que permita vincular BIP y QR para la misma persona;
- o por perfiles de uso agregados sin afirmar identidad individual.

### Rol respecto al modelo MNL

La segmentación se tratará como una capa complementaria:

- primero se construyen perfiles de comportamiento;
- luego se evalúa si esos perfiles ayudan a interpretar diferencias en adopción de `QR_RED` y `QR_OTHER`;
- finalmente se decide si los segmentos entran al modelo como interacciones, como modelos separados por segmento o como análisis descriptivo paralelo.

No se asume de entrada que el modelo MNL final deba reemplazarse por un modelo segmentado.

### Preguntas iniciales

- ¿Existe una llave de usuario real que vincule BIP y QR para una misma persona?
- ¿Qué representa exactamente `id_contrato` y si permite distinguir canales QR sin identificar personas?
- ¿Cuál es la unidad disponible y estable entre 2024 y 2025?
- ¿Qué ventana temporal usar para construir perfiles?
- ¿Se segmenta usando solo comportamiento de viaje o también contexto territorial?
- ¿La adopción QR debe ser una variable usada para formar segmentos o una variable usada para describir segmentos?
- ¿Conviene separar primero credenciales frecuentes de credenciales esporádicas?
- ¿Qué hacemos con identificadores observados en solo un año?

### Primer enfoque recomendado

Partir con una auditoría de identificadores y luego, si corresponde, una tabla agregada por la unidad elegida:

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
