# Censo 2024 — Microdatos comunales vs agregado manzana-entidad

## Resumen

Los archivos de microdatos del Censo 2024 ya descargados en:

- [`personas_censo2024.zip`](/Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip)
- [`hogares_censo2024.zip`](/Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip)
- [`viviendas_censo2024.zip`](/Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip)

traen microdatos con identificadores de `region`, `provincia` y `comuna`, pero **no** `MANZENT`, `ID_ENTIDAD` ni otra clave espacial fina.

En cambio, la base agregada que usamos para `ZONA777` proviene de la **base manzana-entidad** y la **cartografía** censal, por lo que sí puede espacializarse con un join geométrico y luego agregarse/interpolarse a `ZONA777`.

## Tabla 1. Estructura de los archivos

| Archivo | Unidad de análisis | Geografía explícita en microdato | N° columnas | Sirve para espacializar directo a `ZONA777` | Comentario |
|---|---|---:|---:|---|---|
| `personas_censo2024.csv` | Persona | `region`, `provincia`, `comuna` | 63 | No | Requiere un método adicional de asignación intra-comunal para bajar de comuna a una geografía fina. |
| `hogares_censo2024.csv` | Hogar | `region`, `provincia`, `comuna` | 18 | No | Útil para variables de tenencia/equipamiento, pero no tiene ubicación menor que comuna. |
| `viviendas_censo2024.csv` | Vivienda | `region`, `provincia`, `comuna` | 25 | No | Útil para materialidad y servicios, pero tampoco tiene manzana. |
| `Base_manzana_entidad_CPV24.csv` | Manzana-entidad agregada | `MANZENT`, `COD_MANZANA`, `COD_ENTIDAD`, `COD_ZONA`, `COD_DISTRITO`, `CUT`, `COMUNA` | 200+ | Sí | Es la base que hoy usamos para derivar indicadores por `ZONA777`. |

## Tabla 2. Variables útiles por archivo y relación con el agregado manzana-entidad

| Archivo | Variables relevantes observadas | ¿Ya están representadas en nuestro agregado `manzana -> ZONA777`? | Comentario |
|---|---|---|---|
| `personas_censo2024.csv` | `sexo`, `edad`, `edad_quinquenal`, `p25_lug_nacimiento`, `p26_llegada_periodo`, `p27_nacionalidad`, `p28_* pueblo`, `p29_afrodescendencia`, `p32a`-`p32f` dificultades, `discapacidad`, `p37_alfabet`, `escolaridad`, `sit_fuerza_trabajo`, `p40_cise_rec`, `cod_ciuo`, `cod_caenes`, `p44_lug_trab`, `p45_medio_transporte` | Parcialmente | Ya tenemos agregadas varias: edad, inmigración, pueblos originarios, afrodescendencia, discapacidad, alfabetismo, escolaridad, ocupación y uso de transporte público al trabajo. Quedan fuera atributos más finos como `p26_llegada_periodo`, `p27_nacionalidad` detallada, `p44_lug_trab`, `cod_ciuo`, `cod_caenes`. |
| `hogares_censo2024.csv` | `p12_tenencia_viv`, `p13_comb_cocina`, `p14_comb_calefaccion`, `p15a_serv_tel_movil`, `p15b_serv_compu`, `p15c_serv_tablet`, `p15d_serv_internet_fija`, `p15e_serv_internet_movil`, `p15f_serv_internet_satelital`, `tipologia_hogar` | Parcialmente | Ya tenemos `serv_tel_movil`, `serv_compu` e `internet` en forma agregada. Quedan fuera variables nuevas potenciales como tenencia, cocina, calefacción, `tablet`, internet fija/móvil/satelital y tipología de hogar. |
| `viviendas_censo2024.csv` | `cant_hog`, `cant_per`, `p2_tipo_vivienda`, `p3a/p3b_estado_ocupacion`, `p4a_mat_paredes`, `p4b_mat_techo`, `p4c_mat_piso`, `p5_num_dormitorios`, `p6_fuente_agua`, `p7_distrib_agua`, `p8_serv_hig`, `p9_fuente_elect`, `p10_basura`, `indice_hacinamiento` | Parcialmente | Ya tenemos `n_vp_ocupada` y `n_viv_hacinadas`. Quedan fuera variables potencialmente muy útiles para un índice socioeconómico o de calidad habitacional: materialidad, agua, saneamiento, electricidad, dormitorios y tipo de vivienda. |

## Tabla 3. Qué tipo de variables conviene buscar en cada fuente

| Necesidad | Mejor fuente dentro del Censo 2024 | Razón |
|---|---|---|
| Variable ya espacializable hoy | Base manzana-entidad + cartografía | Ya trae geografía fina y permite agregación/interpolación a `ZONA777`. |
| Variable nueva de vivienda/servicios no usada aún | Base manzana-entidad si existe agregada | Permite mantener el pipeline actual sin asignación heurística. |
| Variable disponible solo en microdatos de personas/hogares/viviendas | Microdatos comunales | Exige un método adicional para bajar de comuna a una resolución menor. |
| Ingresos monetarios | Ninguno de los microdatos Censo revisados | El Censo 2024 no trae ingresos directos en estos archivos. |

## Lectura metodológica

1. El Censo 2024 público mezcla dos niveles:
   - microdatos comunales;
   - agregados espaciales por manzana-entidad.
2. Nuestro pipeline actual usa el segundo grupo, por eso puede llegar a `ZONA777` sin inventar la ubicación de hogares/personas.
3. Si quisiéramos usar una variable que aparece solo en `personas`/`hogares`/`viviendas`, ya no bastaría el pipeline actual:
   - habría que usar una estrategia de asignación intra-comunal como la discutida en el post de Eduardo Graells-Garrido,
   - o cambiar de fuente/metodología.
4. En estos microdatos no aparecen variables de ingreso. Para “plata” habría que ir a otra fuente o construir un proxy/factor.

## Headers inspeccionados

Headers completos inspeccionados directamente desde los zips:

- `personas_censo2024.csv`: 63 columnas
- `hogares_censo2024.csv`: 18 columnas
- `viviendas_censo2024.csv`: 25 columnas

Comando usado:

```bash
unzip -p /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip personas_censo2024.csv | head -n 2
unzip -p /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip hogares_censo2024.csv | head -n 2
unzip -p /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip viviendas_censo2024.csv | head -n 2
```
