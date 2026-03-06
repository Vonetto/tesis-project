# Notes — Socio-demographic Integration (Censo/CASEN ↔ Zonas777)

## 2026-02-17 (feedback profesora aplicado)
- Decisión metodológica para integración socio-demo en modelos de buffers:
  - Probar **dos variantes**: (a) solo origen, (b) OD (origen + destino).
  - Priorizar análisis/reporting de **solo origen** como baseline principal.
- Esta decisión se alinea con el modelo principal de buffers: OD + Option1 + V2.

## 2026-01-23
- Zonas777 shapefile path (user provided):
  - /Volumes/KINGSTON/tesis-project/raw/zonas777/Zonas777-04-04-2014/Shape/Zonas777_V07_04_2014.shp
- Preference: most disaggregated spatial level (manzana/entidad) if possible; likely evaluate origin-only and OD joins.

### Sources identified
- INE communiqué (2025-12-16): base manzana–entidad + cartografía censal; 189 variables; official portals censo2024.cl / ine.gob.cl.
- Cartografía Censo 2024 (geoparquet) direct download (from open data link):
  - https://storage.googleapis.com/bktdescargascenso2024/Cartografia/GEOPARQUET/Cartografia_censo2024_Pais.zip
  - Size (HEAD): ~794,658,978 bytes (~757 MB)

### ArcGIS Feature Service (microdatos/manzana‑entidad)
- ArcGIS item: “Microdatos Censo 2024” (public)
- FeatureServer URL:
  - https://services.arcgis.com/r7t1P5pnkoOLRdhr/arcgis/rest/services/Microdatos_Censo_2024_v2/FeatureServer
- Layers:
  - 0: Manzanas
  - 1: Manzanas‑entidades
- Layer 1 fields: 212 fields. Example socio‑demo fields (counts/means):
  - n_edad_0_5, n_edad_6_13, n_edad_14_17, n_edad_18_24, n_edad_25_44, n_edad_45_59, n_edad_60_mas, prom_edad
  - n_inmigrantes, n_pueblos_orig, n_afrodescendencia, n_lengua_indigena, n_discapacidad
  - prom_escolaridad18, n_ocupado, n_desocupado, n_fuera_fuerza_trabajo
  - n_hog, prom_per_hog, n_hog_unipersonales, n_hog_60, n_hog_menores
  - n_serv_internet_fija, n_serv_internet_movil, n_internet, n_serv_compu, n_serv_tel_movil
  - n_vp_ocupada, n_viv_hacinadas, n_viv_irrecuperables, n_hog_allegados
  - n_fuente_agua_publica, n_serv_hig_alc_dentro, n_fuente_elect_publica, n_basura_servicios

### Caveat
- ArcGIS item description suggests geometry may be based on Censo 2017 boundaries; needs verification before final use.

## 2026-01-25
- Downloaded cartography geoparquet ZIP:
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/Cartografia_censo2024_Pais.zip
- ZIP contents (geoparquet layers):
  - Cartografia_censo2024_Pais_Zonal.parquet
  - Cartografia_censo2024_Pais_Aldeas.parquet
  - Cartografia_censo2024_Pais_Comunal.parquet
  - Cartografia_censo2024_Pais_Distrital.parquet
  - Cartografia_censo2024_Pais_Entidades.parquet
  - Cartografia_censo2024_Pais_Limite_Urbano.parquet
  - Cartografia_censo2024_Pais_Localidades.parquet
  - Cartografia_censo2024_Pais_Manzanas.parquet
  - Cartografia_censo2024_Pais_Provincial.parquet
  - Cartografia_censo2024_Pais_Regional.parquet
  - Diccionario_variables_geograficas_CPV24.xlsx
- Note: ZIP includes cartography layers and geographic dictionary; base manzana‑entidad table still pending (not inside ZIP).

## 2026-01-26
- Descargas locales (INE Censo 2024):
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/Base_manzana_entidad_CPV24.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/diccionario_variables_glosas_censo2024.xlsx
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/hogares_censo2024.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/personas_censo2024.zip
  - /Volumes/KINGSTON/tesis-project/raw/censo2024/viviendas_censo2024.zip
- Base manzana‑entidad (CSV dentro del zip) incluye campos geográficos finos:
  - Ejemplo de header: CONTENEDOR_COMUNAL;COD_REGION;REGION;PROVINCIA;CUT;COMUNA;AREA_C;MANZENT;DISTRITO;COD_DISTRITO;COD_LOCALIDAD;COD_ZONA;LOCALIDAD;COD_ENTIDAD;COD_MANZANA;ENTIDAD;…
- Microdatos (hogares/personas/viviendas) muestran solo nivel región/provincia/comuna (no manzana/entidad en el header):
  - personas: id_vivienda;id_hogar;id_persona;region;provincia;comuna;…
  - hogares: id_vivienda;id_hogar;region;provincia;comuna;…
  - viviendas: id_vivienda;region;provincia;comuna;…
- Diccionario de variables: hojas disponibles en XLSX: Dicionario, temáticas, Glosas_variables_geográficas, DPA, estructura geográfica.
- Cartografía ZIP contiene parquet de Manzanas y Entidades (a extraer para spatial join):
  - Cartografia_censo2024_Pais_Manzanas.parquet
  - Cartografia_censo2024_Pais_Entidades.parquet

## 2026-01-26 (variable shortlist proposal)
- Proposed variable groups for Zonas777 aggregation (from base manzana‑entidad; exact names to verify in diccionario):
  - Población: n_per, n_hombres, n_mujeres; edades n_edad_0_5, n_edad_6_13, n_edad_14_17, n_edad_18_24, n_edad_25_44, n_edad_45_59, n_edad_60_mas; prom_edad.
  - Migración/etnia: n_inmigrantes, n_pueblos_orig, n_afrodescendencia, n_lengua_indigena.
  - Discapacidad: n_dificultad_* (ver/oir/mover/recordar/etc.).
  - Educación: prom_escolaridad18 (si aplica).
  - Trabajo: n_ocupado, n_desocupado, n_fuera_fuerza_trabajo.
  - Hogares: n_hog, prom_per_hog, n_hog_unipersonales, n_hog_60, n_hog_menores.
  - Vivienda: n_vp_ocupada, n_viv_hacinadas, n_viv_irrecuperables, n_hog_allegados.
  - Servicios: n_serv_internet_fija, n_serv_internet_movil, n_internet, n_serv_compu, n_serv_tel_movil.
  - Infraestructura: n_fuente_agua_publica, n_serv_hig_alc_dentro, n_fuente_elect_publica, n_basura_servicios.
- Aggregation defaults (to confirm):
  - Counts: sum over manzana/entidad within Zonas777.
  - Means: weighted by n_per (or n_hog) when possible; otherwise simple mean.
  - Shares: derived after summing counts (e.g., share_internet = n_internet / n_hog; share_hacinamiento = n_viv_hacinadas / n_vp_ocupada; share_inmigrantes = n_inmigrantes / n_per).

## 2026-01-26 (diccionario export)
- Exported full variable dictionary to CSV for inspection:
  - tmp/censo2024/diccionario_variables_glosas_censo2024.csv (columns: Temática, Variable, Tipo de variable, Descripción, Universo; 212 rows)

## 2026-01-26 (variables confirmed)
- User‑selected variable list checked against dictionary: all present (no missing).
- Variables + universo (per diccionario) captured for reference (see tmp/censo2024/diccionario_variables_glosas_censo2024.csv).

## 2026-01-26 (doc)
- Created variable dictionary doc: `docs/diccionario_censo2024_vars.md` (selected variables with descriptions/universe).

## 2026-01-26 (spatial join decisions)
- Zonas777 shapefile has no CRS; bounds match Santiago lat/lon. We will **assign EPSG:4674 (SIRGAS 2000)** to align with Censo 2024 cartography CRS.
- Join strategy:
  1) Base manzana‑entidad (CSV) ↔ Entidades cartography (parquet) via **ID_ENTIDAD** (primary key).
  2) Spatial join Entidades → Zonas777 using **centroid within** as default.
  3) Diagnostics to compute:
     - % entidades whose centroid falls outside Zonas777
     - % entidades intersecting multiple Zonas777
  4) If diagnostics show high mismatch, switch to **area‑weighted overlay** instead of centroid assignment.

## 2026-01-26 (implementation)
- Added script: `lib/censo2024_zona777.py` (join base manzana‑entidad + Entidades cartography → Zonas777, centroid join, diagnostics, aggregation).
- Added notebook: `02_eda/eda_censo2024_zona777.qmd` (runs script and inspects outputs).
- Outputs directory: `02_eda/tmp/censo2024_zona777/`.

## 2026-01-26 (run diagnostics)
- Initial centroid join run (national entidades vs Zonas777) returned:
  - pct_centroid_outside_zonas777 = 0.9951
  - pct_entities_intersect_multiple_zonas777 = 0.0021
- Interpretation: expected high outside because Censo entidades are national while Zonas777 cover Santiago only. Need to filter entities to Zonas777 extent (bbox/intersection or RM) before diagnostics/aggregation.

## 2026-01-26 (filter strategy)
- Implemented filter_mode in `lib/censo2024_zona777.py`: none | bbox | region | both.
- Notebook now runs **bbox** and **region** modes and writes separate outputs:
  - `censo2024_zona777_agg_bbox.parquet` + diagnostics
  - `censo2024_zona777_agg_region.parquet` + diagnostics

## 2026-01-26 (filter: intersects)
- Added `filter_mode=intersects` to keep only Entidades that intersect Zonas777 polygons (more precise than bbox/region filters).
- Notebook updated to run bbox, region, and intersects modes; writes separate outputs.

## 2026-01-26 (filter diagnostics results)
- bbox filter: pct_centroid_outside=0.7186, pct_multi_zone=0.1194
- region filter: pct_centroid_outside=0.9329, pct_multi_zone=0.0287
- intersects filter: pct_centroid_outside=0.2835, pct_multi_zone=0.3041
- Interpretation: intersects is the only viable prefilter; multi-zone rate is high → centroid assignment likely biased; area-weighted overlay recommended.

## 2026-01-26 (area-weighted overlay)
- Added area-weighted overlay option (`area_weighted=True`) using Entidades × Zonas777 intersection (UTM 19S for area).
- Notebook now runs `intersects_area` and writes:
  - `censo2024_zona777_agg_intersects_area.parquet`
  - `censo2024_zona777_diag_intersects_area.json`

## 2026-01-26 (ID_ENTIDAD normalization)
- Added normalization for ID_ENTIDAD (strip non-digits) in both base CSV and cartography to fix join mismatches.
- Added COD_REGION to KEY_COLS to allow filtering base by region if needed.

## 2026-01-26 (join mismatch debug + cartography switch)
- Found join mismatch using **Entidades** cartography:
  - `Cartografia_censo2024_Pais_Entidades.parquet` has ~28k rows (too small for manzana coverage).
  - Join overlap with base MANZENT very low (~6% in sample; ~4% in RM). ID_ENTIDAD overlap ~0%.
- Checked **Manzanas** cartography:
  - `Cartografia_censo2024_Pais_Manzanas.parquet` has ~216k rows.
  - Join overlap with base MANZENT is high (≈85% overall; ≈96% in RM sample).
- Decision: **switch to Manzanas cartography and join key MANZENT** (not Entidades/ID_ENTIDAD).
- Updates implemented:
  - `JoinConfig` now uses `carto_parquet` (manzanas) and default join key `MANZENT`.
  - Added join coverage diagnostics:
    - `pct_base_keys_in_carto`
    - `pct_carto_keys_in_base`
    - `pct_rows_with_n_per` (after merge)
  - Enforced numeric casting in `_aggregate_by_zona` to avoid string arithmetic errors.
- Notebook updated to use `Cartografia_censo2024_Pais_Manzanas.parquet`.

## 2026-01-26 (run results with Manzanas cartography)
- Re‑ran `02_eda/eda_censo2024_zona777.qmd` with Manzanas cartography.
- Diagnostics (coverage now OK):
  - **bbox**: pct_centroid_outside=0.0385, pct_multi_zone=0.1636, pct_base_keys_in_carto=1.0, pct_carto_keys_in_base=0.7585, pct_rows_with_n_per=0.7585
  - **region**: pct_centroid_outside=0.1589, pct_multi_zone=0.1431, pct_base_keys_in_carto=0.9596, pct_carto_keys_in_base=0.7555, pct_rows_with_n_per=0.7555
  - **intersects**: pct_centroid_outside=0.00128, pct_multi_zone=0.1699, pct_base_keys_in_carto=1.0, pct_carto_keys_in_base=0.7610, pct_rows_with_n_per=0.7610
  - **intersects_area**: same coverage as intersects (area‑weighted overlay).
- Aggregated outputs now contain non‑zero counts and shares (example ZONA777 rows show plausible totals).
- Row counts from outputs (after re-run, all shares summarized):
  - bbox/region/intersects: 801 zonas
  - intersects_area: 803 zonas

## 2026-01-26 (decision)
- Selected **intersects_area** as the default socio‑demographic output for Zonas777.

## 2026-01-26 (alias + sanity)
- Created alias (final output):
  - `02_eda/tmp/censo2024_zona777/censo2024_zona777_agg_final.parquet`
- Sanity checks on shares (intersects_area):
  - Summary: `02_eda/tmp/censo2024_zona777/censo2024_zona777_sanity_intersects_area.csv`
  - Examples >1: `02_eda/tmp/censo2024_zona777/censo2024_zona777_sanity_examples_gt1.json`
  - Shares >1 appear in:
    - `share_serv_tel_movil` (n_gt_1=647, max≈7.04)
    - `share_internet` (n_gt_1=370, max≈7.01)
    - `share_serv_compu` (n_gt_1=26, max≈6.19)
    - `share_ocupado` (n_gt_1=4, max≈3.06)
  - Interpretation for now: likely multiple services/devices per hogar (numerator not a strict subset of denominator) plus area‑weighted rounding; keep as‑is and document.
  - In intersects_area summary: share_internet and share_serv_tel_movil show max > 1 (up to ~7), consistent with multi‑service counts; share_ocupado max ~3.06 (likely definition/denominator effects).

## 2026-01-26 (notebook path fix)
- Updated `02_eda/eda_censo2024_zona777.qmd` to compute `OUT_DIR` from `PROJECT_ROOT` to avoid writing under `02_eda/02_eda/...` when executed from the `02_eda/` folder.

## 2026-01-26 (buffers join scaffold)
- Added script: `lib/censo2024_join_buffers.py` to join Censo Zonas777 aggregates onto buffers.
  - Buffer A (inicio) → adds `censo_*` columns (join by zona_inicio_viaje).
  - Buffer OD → adds `censo_o_*` and `censo_d_*` columns (join by zona_inicio_viaje/zona_fin_viaje).
  - Outputs to `02_eda/tmp/buffers_zona777_censo2024/`.
- Added section to `02_eda/eda_buffers_zona777_tipo_pago.qmd` to run the join and print diagnostics.

## 2026-01-26 (buffers join results)
- Join outputs (2025‑W17):
  - Inicio: 2,389 filas; `pct_missing_censo_inicio` ≈ 0.00628
    - `02_eda/tmp/buffers_zona777_censo2024/buffers_zona777_inicio_tipo_pago_2025-W17_censo.parquet`
  - OD: 473,035 filas; `pct_missing_censo_origen` ≈ 0.00338; `pct_missing_censo_destino` ≈ 0.00224
 - `02_eda/tmp/buffers_zona777_censo2024/buffers_zona777_od_tipo_pago_2025-W17_censo.parquet`

## 2026-02-27 (model integration — origin first)
- Se integró Censo final (`censo2024_zona777_agg_final.parquet`) al pipeline de modelamiento en:
  - `03_models/05_nested_logit_od_buffers.qmd`
- Flujo agregado:
  - Join por `zona_inicio_viaje` (origen) sobre `Option1 V2`.
  - Variables socio seleccionadas: `prom_edad`, `prom_escolaridad18`, `share_inmigrantes`, `share_ocupado`, `share_internet`, `share_hacinamiento`.
  - Estimación nueva: `Option1 V2 + socio origen` (betas `B_SOC_O_*`).
  - Celda de comparación objetiva baseline vs socio-origen.

## 2026-01-26 (mini‑EDA buffers + missing zonas)
- Added mini‑EDA section to `02_eda/eda_buffers_zona777_tipo_pago.qmd`:
  - Summaries (mean/median) for 5 Censo vars by `tipo_pago` for Buffer A and Buffer OD (origen/destino).
  - Lists of missing zonas where `censo_n_per` is null (inicio, od origen, od destino).
 - Observed: Buffer A summaries are identical across tipo_pago because Censo is joined at zona-level and the summary is unweighted; each zona appears once per tipo_pago. Differences appear in Buffer OD (origen/destino) due to different OD composition.
 - Suggestion recorded: use **n_viajes-weighted** summaries if we want socio‑demo differences by tipo_pago.

## 2026-01-26 (prom_edad scale check)
- `prom_edad` in base is stored as **string with decimal comma** (e.g., `\"38,3\"`), so naive `pd.to_numeric` yields NaN for many rows.
- This explains the low `prom_edad` (~3.9) seen in summaries.
- Fix implemented: in `_read_base_csv`, for variable columns, replace comma → dot before `pd.to_numeric`.
- Action: re-run `02_eda/eda_censo2024_zona777.qmd` and the buffer mini‑EDA to refresh prom_edad stats.

## 2026-01-26 (join key switch)
- ID_ENTIDAD in base appears in scientific notation (e.g., 1,10101E+11). Switched join key to **MANZENT** (present in base + cartography) for reliable matching.
- Added join_key support in script; normalizes join key by stripping non-digits.

## 2026-01-26 (key normalization v2)
- Updated key normalization to handle scientific notation (e.g., 1.340201e+13) and decimal commas by converting to numeric then formatting as integer string.

## 2026-01-26 (numeric casting)
- Base variable columns now cast to numeric via `pd.to_numeric(errors='coerce')` to avoid string division errors during aggregation.

- 2026-02-27: En `02_eda/eda_censo2024_zona777.qmd` se agregaron celdas para (i) inventariar variables disponibles del parquet final y (ii) listar explicitamente las 6 variables socio actualmente usadas en `Option1 V2 + socio origen`.
