# Avance frente econometrico: modelo MNL con zona de residencia

## 1. Cambio metodologico

Se actualizo la forma de medir las variables territoriales del modelo:

- Las variables que representan caracteristicas del usuario/hogar se miden en la **zona de residencia inferida del usuario**.
- Las variables que representan el contexto del viaje se mantienen en la **zona de origen del viaje**.
- La residencia se infiere desde viajes declarados como `HOGAR`, usando la zona de destino mas frecuente por tarjeta.
- Para la estimacion principal se usan solo tarjetas donde esa residencia es poco ambigua: casos con una unica zona observada como hogar, o con una zona claramente dominante entre los viajes declarados como `HOGAR`.

Esta separacion evita atribuir al usuario caracteristicas de una zona donde solamente inicio un viaje.

## 2. Validacion de la residencia inferida

Se valido la residencia con un criterio independiente: para cada tarjeta se reviso si la zona de origen mas frecuente en la manana coincide con la zona de destino mas frecuente en la tarde. Cuando ambas zonas coinciden, esa zona se interpreta como una senal alternativa de residencia.

| Criterio | Tarjetas comparadas | Coinciden con residencia inferida | Tasa de acuerdo |
|---|---:|---:|---:|
| Origen frecuente manana = destino frecuente tarde | 1,130,241 | 1,086,898 | 96.2% |

Lectura: cuando el criterio alternativo entrega una senal clara, coincide en `96.2%` de los casos con la residencia inferida desde los viajes `HOGAR`. Esto respalda usar esa residencia como base para medir variables socioeconomicas.

## 3. Comparacion de ajuste

Se compara el modelo candidato por residencia contra el baseline previo, que media las mismas variables socioeconomicas por zona de origen del viaje. La comparacion usa la misma muestra.

| Modelo | Medicion de variables socioeconomicas | N viajes | LL final | AIC | Estado |
|---|---|---:|---:|---:|---|
| Baseline previo | Zona de origen del viaje | 279,643 | -137,382.9 | 274,897.8 | Converge |
| Candidato main | Zona de residencia inferida | 279,643 | -136,351.6 | 272,835.2 | Converge |

Lectura: medir las variables socioeconomicas por residencia mejora el ajuste del MNL en la misma muestra.

## 4. Coeficientes seleccionados del modelo candidato

La alternativa base normalizada es BIP. La tabla muestra variables seleccionadas por relevancia sustantiva; la tabla completa de parametros queda en el anexo.

| Variable | QR_OTHER beta | QR_OTHER t | QR_RED beta | QR_RED t | Lectura breve |
|---|---:|---:|---:|---:|---|
| Educacion universitaria o mas en zona de residencia | 0.158 | 13.34 | 0.397 | 16.88 | Es la senal socioeconomica mas fuerte; aumenta especialmente QR_RED. |
| Discapacidad en zona de residencia | 0.073 | 5.47 | -0.243 | -7.98 | Efecto opuesto entre QR_OTHER y QR_RED; resultado relevante pero no trivial de interpretar. |
| Inmigrantes en zona de residencia | 0.060 | 7.75 | 0.006 | 0.35 | Senal positiva para QR_OTHER; no robusta para QR_RED. |
| Edad promedio en zona de residencia | -0.100 | -10.27 | 0.040 | 1.87 | Menor QR_OTHER en zonas de mayor edad; QR_RED queda debil. |
| Proxy ingreso E-D en zona de residencia | 0.007 | 0.70 | 0.041 | 1.90 | Su estimacion no es estadisticamente fuerte; probablemente parte de su efecto queda absorbido por educacion, macrozona y otros controles territoriales. |
| Macrozona Oriente | -0.004 | -0.18 | 0.122 | 2.75 | Oriente muestra una asociacion positiva con QR_RED y sin senal robusta para QR_OTHER. |
| Tiempo de espera inicial | -0.00127 | -15.56 | -0.00104 | -10.53 | Mayor espera inicial reduce utilidad relativa de QR. |
| Tiempo de espera en transbordo | -0.00065 | -5.61 | -0.00029 | -2.45 | Mayor espera en transbordo reduce utilidad relativa de QR. |

## 5. Lectura principal

- La residencia inferida es consistente con una validacion independiente basada en patrones manana/tarde.
- Medir variables socioeconomicas por residencia mejora el ajuste respecto del baseline por origen.
- La educacion residencial es el resultado mas estable: zonas con mayor educacion universitaria se asocian con mayor uso de QR, especialmente QR_RED.
- La macrozona Oriente muestra una senal positiva para QR_RED una vez que las caracteristicas socioeconomicas se miden por residencia y no por el punto de inicio del viaje.
- La variable de discapacidad aparece como una senal importante y no trivial; conviene discutirla con cautela y contrastarla con el frente ML.

## Fuentes de resultados

- Modelo candidato por residencia: resultados Biogeme del notebook 17, especificacion candidata por residencia.
- Baseline comparable por origen: resultados Biogeme del notebook 17, misma muestra y variables medidas por origen.
- Validacion AM/PM: auditoria `commute_vs_proposito_summary_ml_2025.csv`.

## Anexo: parametros completos del modelo candidato en formato wide

Los coeficientes de variables comunes al viaje o a la zona se interpretan respecto de BIP. Para variables alternativas-especificas, como tiempos y transbordos, tambien se estima directamente un coeficiente para BIP.

| Variable                                  | BIP Est.   | BIP t    |   QR_OTHER Est. |   QR_OTHER t |   QR_RED Est. |   QR_RED t |
|:------------------------------------------|:-----------|:---------|----------------:|-------------:|--------------:|-----------:|
| Constante especifica alternativa          |            |          |       -2.048    |     -18.7294 |      -4.2339  |   -18.8435 |
| Tiempo en vehiculo                        | -5.81e-05  | -1.4005  |        2.76e-05 |       0.672  |       1.9e-05 |     0.4561 |
| Espera inicial                            | -0.0012    | -14.8115 |       -0.0013   |     -15.5553 |      -0.001   |   -10.5288 |
| Espera transbordo                         | -0.0006    | -5.0754  |       -0.0006   |      -5.6091 |      -0.0003  |    -2.4549 |
| N transbordos                             | 0.0014     | 0.0253   |       -0.0614   |      -1.1468 |      -0.1037  |    -1.8624 |
| Laboral PM                                |            |          |        0.0814   |       4.3442 |       0.4521  |    11.4155 |
| Laboral punta tarde                       |            |          |        0.2008   |       8.9388 |       0.4106  |     9.2001 |
| No laboral                                |            |          |        0.1786   |       7.7629 |       0.1726  |     3.4562 |
| Anio 2025                                 |            |          |        0.3432   |      29.5267 |       0.2802  |    11.6735 |
| Demanda zona-franja                       |            |          |       -0.0341   |      -3.3534 |       0.0217  |     1.0647 |
| Densidad paraderos bus                    |            |          |        0.0181   |       1.0612 |      -0.1306  |    -3.4147 |
| Lineas bus                                |            |          |        0.0289   |       1.574  |       0.0597  |     1.5668 |
| Lineas metro                              |            |          |        0.1109   |       4.0922 |      -0.0808  |    -1.5423 |
| Residencia: educacion universitaria o mas |            |          |        0.1583   |      13.3413 |       0.3973  |    16.8769 |
| Residencia: discapacidad                  |            |          |        0.0727   |       5.4689 |      -0.2431  |    -7.975  |
| Residencia: inmigrantes                   |            |          |        0.0598   |       7.7512 |       0.0063  |     0.3462 |
| Residencia: mujeres                       |            |          |        0.0014   |       0.269  |       0.0165  |     1.1363 |
| Residencia: asistencia parvularia         |            |          |       -0.038    |      -4.143  |       0.0541  |     2.865  |
| Residencia: edad promedio                 |            |          |       -0.0996   |     -10.2716 |       0.0402  |     1.8749 |
| Residencia: proxy ingreso E-D             |            |          |        0.0068   |       0.7011 |       0.0408  |     1.9038 |
| OSM: juegos/plazas infantiles             |            |          |        0.014    |       2.2994 |       0.0423  |     3.4265 |
| OSM: colegios                             |            |          |        0.0109   |       1.6523 |      -0.0172  |    -1.1761 |
| OSM: universidades                        |            |          |       -0.0216   |      -8.064  |      -0.012   |    -2.1181 |
| OSM: refugios/paraderos                   |            |          |       -0.0308   |      -3.3724 |       0.0316  |     1.5739 |
| OSM: accesos metro                        |            |          |       -0.0159   |      -3.7541 |       0.0054  |     0.6346 |
| Macrozona norte                           |            |          |       -0.0308   |      -0.9753 |      -0.0317  |    -0.4097 |
| Macrozona poniente                        |            |          |       -0.0591   |      -2.6301 |      -0.2849  |    -5.3291 |
| Macrozona oriente                         |            |          |       -0.0039   |      -0.1783 |       0.1223  |     2.754  |
| Macrozona sur                             |            |          |       -0.0474   |      -1.6773 |      -0.0783  |    -1.1975 |
| Macrozona suroriente                      |            |          |       -0.0752   |      -2.9964 |      -0.05    |    -0.9171 |
| Macrozona externa/especial                |            |          |        0.0275   |       0.2255 |       0.2998  |     1.3577 |
