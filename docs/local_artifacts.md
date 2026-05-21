# Artefactos locales pesados

Este proyecto usa artefactos pesados reproducibles que no deben versionarse ni vivir necesariamente en el disco interno.

## Ubicacion externa

Los artefactos movidos al Kingston SSD quedan bajo:

```text
/Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/
```

La estructura replica rutas relativas del repo. Por ejemplo:

```text
/Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/03_models/artifacts
/Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/01_processing/tmp
/Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/tmp/audits/proposito_residence/pk_bridge
```

En el worktree se dejan symlinks con las rutas originales para que notebooks y scripts sigan funcionando sin cambios.

## Symlinks actuales

```text
01_processing/tmp -> /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/01_processing/tmp
03_models/artifacts -> /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/03_models/artifacts
03_models/archives/pre_fix_interannual_2026-03-26 -> /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/03_models/archives/pre_fix_interannual_2026-03-26
tmp/audits/proposito_residence/pk_bridge -> /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/tmp/audits/proposito_residence/pk_bridge
```

Tambien se movieron como symlinks individuales varios artefactos pesados bajo `tmp/`, incluyendo:

```text
tmp/viajes_con_te_calculado_*.parquet
tmp/viajes_con_te_calculado_*_batches*
tmp/viajes_completo_2025-W17.parquet
tmp/viajes_con_te_metro_2025-W17.parquet
tmp/viajes_con_te_calculado_y_caminata_2025-W17.parquet
tmp/viajes_bus_te_desag_2025-W17.parquet
tmp/lake_silver_viajes_filtrados_iso_year=*_data-0.parquet
tmp/raw_raw_csv_source=drive_ingest_date=2025-10-17_2024-11-23.perfiles_de_carga.csv
tmp/part-0.parquet
tmp/data-0.parquet
```

Si el Kingston no esta montado en `/Volumes/KINGSTON`, las rutas anteriores fallaran.

## Restaurar symlinks

Desde la raiz del repo:

```bash
ln -s /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/01_processing/tmp 01_processing/tmp
ln -s /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/03_models/artifacts 03_models/artifacts
mkdir -p 03_models/archives
ln -s /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/03_models/archives/pre_fix_interannual_2026-03-26 03_models/archives/pre_fix_interannual_2026-03-26
mkdir -p tmp/audits/proposito_residence
ln -s /Volumes/KINGSTON/tesis-project/local-artifacts/tesis-project/tmp/audits/proposito_residence/pk_bridge tmp/audits/proposito_residence/pk_bridge
```

## Verificacion rapida

```bash
test -f tmp/audits/proposito_residence/pk_bridge/user_home_candidates_ml_2025.parquet
test -f 03_models/artifacts/interannual_enriched/trips_context_pooled_2024_2025.parquet
test -f 01_processing/tmp/etapas_reconstruidas_2025-W17.parquet
test -f tmp/viajes_con_te_calculado_2025-W17.parquet
test -f 03_models/archives/pre_fix_interannual_2026-03-26/interannual_enriched/trips_context_pooled_2024_2025.parquet
```

El Kingston esta formateado como `exfat`, por lo que macOS puede crear archivos `._*` en el destino. Esos archivos son metadatos AppleDouble y no forman parte de los artefactos analiticos.
