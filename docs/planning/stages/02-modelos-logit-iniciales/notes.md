# Stage 02 — Modelos Logit Iniciales

## Resumen

Esta etapa introdujo la primera familia de modelos de elección discreta del proyecto: logit binario baseline, logit binario extendido, nested logit baseline y nested logit extendido, junto con validación por muestreo estratificado.

## Objetivo de la etapa

Estimar y comparar modelos para la adopción de pago QR versus Bip, identificando:

- señal temporal;
- efecto de atributos del viaje;
- estructura jerárquica entre `BIP`, `QR_RED` y `QR_OTHER`;
- viabilidad de muestreo estratificado para estimación repetida.

## Decisiones metodológicas

- Empezar por una semana representativa para consolidar especificaciones.
- Separar baseline temporal y modelos extendidos con atributos de viaje.
- Validar muestras 20% y 50% antes de escalar.
- Mantener una línea nested, pero documentar con claridad sus supuestos y limitaciones.

## Implementación lograda

- Modelos binarios baseline y extendido en Biogeme.
- Nested Logit baseline y extendido.
- Validación del muestreo estratificado.
- Documentación comparativa extensa del trabajo de la branch `feature/logit-model`.

## Limitaciones o problemas detectados

- Se detectó como limitación importante el problema de transbordos internos Metro-Metro.
- Parte de la narrativa original quedó en una documentación separada de los `planning files`.

## Outputs/notebooks relevantes

- [`03_models/01_binary_logit_qr_adoption.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/01_binary_logit_qr_adoption.qmd)
- [`03_models/02_binary_extended_logit_qr_adoption.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/02_binary_extended_logit_qr_adoption.qmd)
- [`03_models/03_nested_logit.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/03_nested_logit.qmd)
- [`03_models/04_ml_models.qmd`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/03_models/04_ml_models.qmd)
- [`docs/avances/feature-logit-model-development.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/avances/feature-logit-model-development.md)

## Fuentes usadas para el backfill

- [`docs/avances/feature-logit-model-development.md`](/Users/vicenteonetto/Desktop/FCFM/MDS/Tesis_Local/tesis-project/docs/avances/feature-logit-model-development.md)
- notebooks `01`, `02`, `03`, `04` en `03_models/`
