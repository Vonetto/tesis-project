
import os
import sys
import pathlib
import csv
import re
from datetime import datetime
import polars as pl
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import gcsfs
from tqdm import tqdm

# Importar constantes desde config
from config.constants import GCS_BUCKET_NAME, GCS_RAW_PREFIX, GCS_BRONZE_PREFIX, USE_LOCAL_PATHS, LOCAL_RAW_PATH, LOCAL_BRONZE_PATH

# --- Parámetros Configurables ---
if USE_LOCAL_PATHS:
    RAW_BASE_PATH = LOCAL_RAW_PATH
    BRONZE_BASE_PATH = LOCAL_BRONZE_PATH
else:
    RAW_BASE_PATH = GCS_RAW_PATH
    BRONZE_BASE_PATH = GCS_BRONZE_PATH
CSV_SEP_DEF = os.getenv("CSV_SEP_DEFAULT", ";")

# --- Definición de Esquema Estricto ---
# Basado en el esquema de referencia proporcionado por el usuario.
CSV_DTYPES = {
    '': pl.Utf8, 'comuna_fin_viaje': pl.Utf8, 'comuna_inicio_viaje': pl.Utf8,
    'contrato': pl.Utf8, 'distancia_eucl': pl.Utf8, 'distancia_ruta': pl.Utf8,
    'dt1': pl.Utf8, 'dt2': pl.Utf8, 'dt3': pl.Utf8, 'dtfinal': pl.Int64,
    'dveh_euc1': pl.Int64, 'dveh_euc2': pl.Int64, 'dveh_euc3': pl.Int64,
    'dveh_euc4': pl.Int64, 'dveh_eucfinal': pl.Int64, 'dveh_ruta1': pl.Int64,
    'dveh_ruta2': pl.Int64, 'dveh_ruta3': pl.Int64, 'dveh_ruta4': pl.Int64,
    'dveh_rutafinal': pl.Int64, 'egreso': pl.Int64, 'entrada': pl.Int64,
    'id_tarjeta': pl.Utf8, 'id_viaje': pl.Int64,
    'modos': pl.Utf8, 'n_etapas': pl.Int32,
    'op_1era_etapa': pl.Utf8, 'op_2da_etapa': pl.Utf8, 'op_3era_etapa': pl.Utf8,
    'op_4ta_etapa': pl.Utf8, 'paradero_bajada_1': pl.Utf8,
    'paradero_bajada_2': pl.Utf8, 'paradero_bajada_3': pl.Utf8,
    'paradero_bajada_4': pl.Utf8, 'paradero_fin_viaje': pl.Utf8,
    'paradero_inicio_viaje': pl.Utf8, 'paradero_subida_1': pl.Utf8,
    'paradero_subida_2': pl.Utf8, 'paradero_subida_3': pl.Utf8,
    'paradero_subida_4': pl.Utf8, 'srv_1': pl.Utf8,
    'srv_2': pl.Utf8, 'srv_3': pl.Utf8, 'srv_4': pl.Utf8, 'tc1': pl.Int64,
    'tc2': pl.Int64, 'tc3': pl.Int64, 'te0': pl.Int64, 'te1': pl.Int64,
    'te2': pl.Int64, 'te3': pl.Int64, 'tiempo_bajada_1': pl.Utf8,
    'tiempo_bajada_2': pl.Utf8, 'tiempo_bajada_3': pl.Utf8,
    'tiempo_bajada_4': pl.Utf8, 'tiempo_fin_viaje': pl.Utf8,
    'tiempo_inicio_viaje': pl.Utf8, 'tiempo_subida_1': pl.Utf8,
    'tiempo_subida_2': pl.Utf8, 'tiempo_subida_3': pl.Utf8,
    'tiempo_subida_4': pl.Utf8,
    'tipo_transporte_1': pl.Utf8, 'tipo_transporte_2': pl.Utf8,
    'tipo_transporte_3': pl.Utf8, 'tipo_transporte_4': pl.Utf8,
    'tipodia': pl.Utf8, 'tv1': pl.Int64, 'tv2': pl.Int64, 'tv3': pl.Int64,
    'tv4': pl.Int64, 'tviaje2': pl.Int64,
    'zona_bajada_1': pl.Utf8,
    'zona_bajada_2': pl.Utf8, 'zona_bajada_3': pl.Utf8,
    'zona_bajada_4': pl.Utf8, 'zona_fin_viaje': pl.Utf8,
    'zona_inicio_viaje': pl.Utf8, 'zona_subida_1': pl.Utf8,
    'zona_subida_2': pl.Utf8, 'zona_subida_3': pl.Utf8,
    'zona_subida_4': pl.Utf8
}

# --- Definición de Esquema para ETAPAS ---
ETAPAS_DTYPES = {
    'operador': pl.Utf8,
    'id_etapa': pl.Int64,
    'correlativo_viajes': pl.Int64,
    'correlativo_etapas': pl.Int64,
    'tipo_dia': pl.Utf8,
    'tipo_transporte': pl.Utf8,
    'fExpansionServicioPeriodoTS': pl.Float64,
    'tiene_bajada': pl.Int64,
    'tiempo2': pl.Utf8,
    'tiempo_subida': pl.Utf8,
    'tiempo_bajada': pl.Utf8,
    'tiempo_etapa': pl.Int64,
    'media_hora_subida': pl.Utf8,
    'media_hora_bajada': pl.Utf8,
    'x_subida': pl.Float64,
    'y_subida': pl.Float64,
    'x_bajada': pl.Float64,
    'y_bajada': pl.Float64,
    'dist_ruta_paraderos': pl.Float64,
    'dist_eucl_paraderos': pl.Float64,
    'servicio_subida': pl.Utf8,
    'servicio_bajada': pl.Utf8,
    'parada_subida': pl.Utf8,
    'parada_bajada': pl.Utf8,
    'comuna_subida': pl.Utf8,
    'comuna_bajada': pl.Utf8,
    'zona_subida': pl.Utf8,
    'zona_bajada': pl.Utf8,
    'sitio_subida': pl.Utf8,
    'fExpansionZonaPeriodoTS': pl.Float64,
    'tEsperaMediaIntervalo': pl.Float64,
    'periodoSubida': pl.Utf8,
    'periodoBajada': pl.Utf8,
    'tiempoIniExpedicion': pl.Utf8,
    'contrato': pl.Utf8
}

NULL_TOKENS = ["", "-", "NA", "N/A", "null", "NULL"]

# --- Autenticación y Setup de FS ---
def enable_adc_crossplatform():
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    if sys.platform.startswith("win"):
        adc = pathlib.Path(os.environ["APPDATA"]) / "gcloud" / "application_default_credentials.json"
    else:
        adc = pathlib.Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
    if not adc.exists():
        raise FileNotFoundError("No encuentro ADC. Ejecuta: gcloud auth application-default login")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(adc)
    return str(adc)

def get_gcs_filesystem():
    enable_adc_crossplatform()
    return gcsfs.GCSFileSystem(token="google_default")

def gsjoin(*parts: str) -> str:
    return "gs://" + "/".join(s.strip("/").replace("gs://", "") for s in parts)

# --- Funciones de Lectura y Parseo de CSV ---
def _detect_sep_from_fullpath(fs, path: str, default=";") -> str:
    if USE_LOCAL_PATHS:
        with open(path, "rb") as fh:
            head = fh.readline().decode("utf-8", errors="ignore")
    else:
        path_no_scheme = path.replace("gs://", "").strip("/")
        with fs.open(path_no_scheme, "rb") as fh:
            head = fh.readline().decode("utf-8", errors="ignore")
    candidates = [",", ";", "|", "\t"]
    counts = {c: head.count(c) for c in candidates}
    sep = max(counts, key=counts.get)
    return sep if counts.get(sep, 0) > 0 else default

def _fix_ddmmyy_to_iso(expr: pl.Expr) -> pl.Expr:
    s = expr.cast(pl.Utf8).str.strip_chars()
    s = s.str.replace_all(r"^(\d{2})[-/](\d{2})[-/](\d{2})", r"20$3-$2-$1")
    s = s.str.replace_all(r"^(\d{2})[-/](\d{2})[-/](\d{4})", r"$3-$2-$1")
    s = s.str.replace_all(r"\s+", " ")
    s = s.str.replace_all(r"(\d{4}-\d{2}-\d{2}) (\d):(\d{2})", r"$1 0$2:$3")
    formats = [
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",
        "%Y-%m-%d"
    ]
    tries = [s.str.strptime(pl.Datetime, format=f, strict=False, exact=False) for f in formats]
    return pl.coalesce(tries)

def _read_csv_polars(fs, path: str, sep: str, dtypes: dict = None) -> pl.DataFrame:
    if dtypes is None:
        dtypes = CSV_DTYPES
    decimal_comma_flag = (sep == ";")
    if USE_LOCAL_PATHS:
        with open(path, "rb") as fh:
            return pl.read_csv(
                fh, separator=sep, dtypes=dtypes, try_parse_dates=False,
                null_values=NULL_TOKENS, ignore_errors=False, low_memory=True, 
                decimal_comma=decimal_comma_flag
            )
    else:
        path_no_scheme = path.replace("gs://", "").strip("/")
        with fs.open(path_no_scheme, "rb") as fh:
            return pl.read_csv(
                fh, separator=sep, dtypes=dtypes, try_parse_dates=False,
                null_values=NULL_TOKENS, ignore_errors=False, low_memory=True, 
                decimal_comma=decimal_comma_flag
            )

# --- Lógica de Ingesta ---
def _glob_raw(fs, base_path: str, patterns: str | list[str]):
    if isinstance(patterns, str):
        patterns = [patterns]
    
    hits = []
    if USE_LOCAL_PATHS:
        # Local file system
        base_path_obj = pathlib.Path(base_path)
        for pat in patterns:
            # Use glob from pathlib for local files
            hits.extend(str(p) for p in base_path_obj.glob(pat))
        print(f"[Local] {len(hits)} archivos encontrados para patrones: {patterns}")
    else:
        # GCS file system
        base_path_no_scheme = base_path.replace("gs://", "").strip("/")
        for pat in patterns:
            hits.extend(fs.glob(f"{base_path_no_scheme}/{pat}"))
        print(f"[GCS] {len(hits)} archivos encontrados para patrones: {patterns}")
    
    hits = sorted(set(hits))
    if not hits:
        raise FileNotFoundError(f"No se encontraron archivos bajo {base_path} con patrones {patterns}")
    return hits

def _week_from_path(gcs_path_no_scheme: str) -> str | None:
    filename = os.path.basename(gcs_path_no_scheme)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if not m:
        m = re.search(r"(\d{4})(\d{2})(\d{2})", filename)
        if not m:
            return None
        date_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" 
    else:
        date_str = m.group(1)
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        iso_year, iso_week, _ = d.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"
    except Exception:
        return None

def _group_files_by_week(file_paths: list[str]) -> dict[str, list[str]]:
    week_map = {}
    print(f"🔍 Agrupando {len(file_paths)} archivos por semana ISO...")
    for path in tqdm(file_paths, desc="Agrupando archivos", unit="file"):
        week = _week_from_path(path)
        if week:
            week_map.setdefault(week, []).append(path)
        else:
            print(f"⚠️ No se pudo determinar la semana para el archivo: {path}")
    print(f"🗓️  Se encontraron {len(week_map)} semanas distintas para procesar.")
    return week_map

def _sanitize_before_write(dfw: pl.DataFrame, sem_key) -> tuple[pl.DataFrame, str]:
    sem = str(sem_key[0]) if isinstance(sem_key, (list, tuple)) else str(sem_key)
    if "semana_iso" in dfw.columns:
        dfw = dfw.drop("semana_iso")
    dfw = dfw.with_columns(pl.lit(sem).cast(pl.Utf8).alias("semana_iso"))
    return dfw, sem

def _partition_exists(fs, base_path: str, sem: str, dataset: str = "viajes") -> bool:
    if dataset == "etapas":
        normal = f"{base_path}/etapas/semana_iso={sem}".rstrip("/")
    else:
        normal = f"{base_path}/semana_iso={sem}".rstrip("/")
    if USE_LOCAL_PATHS:
        return pathlib.Path(normal).exists()
    else:
        return fs.exists(normal.replace("gs://", "").strip("/"))

def _ingest_viajes_files_by_week(raw_fs, bronze_fs, raw_base_path: str, bronze_base_path: str, week_map: dict[str, list[str]]):
    wrote, skipped, errored = [], [], []

    print(f"\n⚙️  Iniciando procesamiento de {len(week_map)} semanas para VIAJES...")
    for week, files_in_week in tqdm(week_map.items(), desc="Procesando semanas (viajes)", unit="semana"):
        if _partition_exists(bronze_fs, bronze_base_path, week):
            skipped.append(week)
            continue
        
        try:
            print(f"\n  [Semana {week}] Encontrados {len(files_in_week)} archivos. Iniciando lectura...")
            list_of_dfs = []
            for file_path in tqdm(files_in_week, desc=f"    Leyendo archivos sem {week}", leave=False, unit="file"):
                sep = _detect_sep_from_fullpath(raw_fs, file_path, default=CSV_SEP_DEF)
                df = _read_csv_polars(raw_fs, file_path, sep)
                
                time_col = next((c for c in ["tiempo_inicio_viaje", "tiempo_subida_1"] if c in df.columns), None)
                if not time_col:
                    print(f"      ⚠️  No se encontró columna temporal en {os.path.basename(file_path)}. Se omite archivo.")
                    continue
                
                df = df.with_columns(_fix_ddmmyy_to_iso(pl.col(time_col)).alias(time_col))
                df = df.with_columns([
                    pl.col(time_col).dt.date().alias("fecha"),
                    pl.col(time_col).dt.iso_year().alias("iso_year"),
                    pl.col(time_col).dt.week().alias("iso_week"),
                ])
                list_of_dfs.append(df)

            if not list_of_dfs:
                print(f"  ⚠️ No se pudo leer ningún archivo para la semana {week}, omitiendo.")
                errored.append(week)
                continue

            print(f"    - Concatenando {len(list_of_dfs)} dataframes para la semana {week}...")
            df_week = pl.concat(list_of_dfs, how="vertical_relaxed").rechunk()
            df_week, week_norm = _sanitize_before_write(df_week, week)

            if "contrato" in df_week.columns:
                df_week = df_week.with_columns(
                    pl.col("contrato").cast(pl.Utf8, strict=False).str.strip_chars().is_in(["171", "102"]).alias("is_qr")
                )
            
            target_dir = f"{bronze_base_path}/semana_iso={week_norm}"
            print(f"    - Escribiendo partición en {'Local' if USE_LOCAL_PATHS else 'GCS'} en: {target_dir}")
            
            if USE_LOCAL_PATHS:
                # For local, use Polars' native write_parquet
                pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
                df_week.write_parquet(f"{target_dir}/part-0.parquet", compression="zstd")
            else:
                # For GCS, use pyarrow.dataset
                fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(bronze_fs))
                ds.write_dataset(
                    data=df_week.to_arrow(), base_dir=target_dir, filesystem=fs_arrow, format="parquet",
                    existing_data_behavior="overwrite_or_ignore",
                    file_options=ds.ParquetFileFormat().make_write_options(compression="zstd"),
                    basename_template="part-{i}.parquet",
                )
            print(f"    - ✅ Semana {week} escrita exitosamente.")
            wrote.append(week)

        except Exception as e:
            print(f"  ❌ Error procesando semana {week}: {e}")
            import traceback
            traceback.print_exc()
            errored.append(week)

    print(f"\n✅ Resumen VIAJES → Nuevas: {len(wrote)}, Omitidas: {len(skipped)}, Errores: {len(errored)}")
    return {"dataset": "viajes", "written": sorted(wrote), "skipped": sorted(skipped), "errored": sorted(errored)}

def _ingest_etapas_files_by_week(raw_fs, bronze_fs, raw_base_path: str, bronze_base_path: str, week_map: dict[str, list[str]]):
    wrote, skipped, errored = [], [], []

    print(f"\n⚙️  Iniciando procesamiento de {len(week_map)} semanas para ETAPAS...")
    for week, files_in_week in tqdm(week_map.items(), desc="Procesando semanas (etapas)", unit="semana"):
        if _partition_exists(bronze_fs, bronze_base_path, week, dataset="etapas"):
            skipped.append(week)
            continue
        
        try:
            print(f"\n  [Semana {week}] Encontrados {len(files_in_week)} archivos. Iniciando lectura...")
            list_of_dfs = []
            for file_path in tqdm(files_in_week, desc=f"    Leyendo archivos sem {week}", leave=False, unit="file"):
                # Los archivos de etapas usan pipe (|) como separador
                sep = "|"
                df = _read_csv_polars(raw_fs, file_path, sep, dtypes=ETAPAS_DTYPES)
                
                # Buscar columna temporal (puede ser tiempo_subida, tiempo2, o tiempoIniExpedicion)
                time_col = next((c for c in ["tiempo_subida", "tiempo2", "tiempoIniExpedicion"] if c in df.columns), None)
                if not time_col:
                    print(f"      ⚠️  No se encontró columna temporal en {os.path.basename(file_path)}. Se omite archivo.")
                    continue
                
                df = df.with_columns(_fix_ddmmyy_to_iso(pl.col(time_col)).alias(time_col))
                df = df.with_columns([
                    pl.col(time_col).dt.date().alias("fecha"),
                    pl.col(time_col).dt.iso_year().alias("iso_year"),
                    pl.col(time_col).dt.week().alias("iso_week"),
                ])
                list_of_dfs.append(df)

            if not list_of_dfs:
                print(f"  ⚠️ No se pudo leer ningún archivo para la semana {week}, omitiendo.")
                errored.append(week)
                continue

            print(f"    - Concatenando {len(list_of_dfs)} dataframes para la semana {week}...")
            df_week = pl.concat(list_of_dfs, how="vertical_relaxed").rechunk()
            df_week, week_norm = _sanitize_before_write(df_week, week)
            
            target_dir = f"{bronze_base_path}/etapas/semana_iso={week_norm}"
            print(f"    - Escribiendo partición en {'Local' if USE_LOCAL_PATHS else 'GCS'} en: {target_dir}")
            
            if USE_LOCAL_PATHS:
                # For local, use Polars' native write_parquet
                pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)
                df_week.write_parquet(f"{target_dir}/part-0.parquet", compression="zstd")
            else:
                # For GCS, use pyarrow.dataset
                fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(bronze_fs))
                ds.write_dataset(
                    data=df_week.to_arrow(), base_dir=target_dir, filesystem=fs_arrow, format="parquet",
                    existing_data_behavior="overwrite_or_ignore",
                    file_options=ds.ParquetFileFormat().make_write_options(compression="zstd"),
                    basename_template="part-{i}.parquet",
                )
            print(f"    - ✅ Semana {week} escrita exitosamente.")
            wrote.append(week)

        except Exception as e:
            print(f"  ❌ Error procesando semana {week}: {e}")
            import traceback
            traceback.print_exc()
            errored.append(week)

    print(f"\n✅ Resumen ETAPAS → Nuevas: {len(wrote)}, Omitidas: {len(skipped)}, Errores: {len(errored)}")
    return {"dataset": "etapas", "written": sorted(wrote), "skipped": sorted(skipped), "errored": sorted(errored)}

def ingest_new_to_bronze(raw_fs, bronze_fs, raw_base_path: str, bronze_base_path: str, viajes_glob: str | None = None, etapas_glob: str | None = None):
    print("="*50)
    print("⏳ Iniciando ingesta RAW -> BRONZE (Estrategia: Semana por Semana con Esquema Estricto)")
    print("="*50)

    viajes_glob = viajes_glob or "raw_csv/source=drive/ingest_date=2025-10-01/*viajes.csv"
    etapas_glob = etapas_glob or "raw_csv/source=drive/ingest_date=2025-10-01/*etapas.csv"

    results = {}
    try:
        files_v = _glob_raw(raw_fs, raw_base_path, viajes_glob)
        week_map_v = _group_files_by_week(files_v)
        results["viajes"] = _ingest_viajes_files_by_week(raw_fs, bronze_fs, raw_base_path, bronze_base_path, week_map_v)
    except FileNotFoundError as e:
        print(f"⚠️ No se procesaron VIAJES: {e}")
        results["viajes"] = None

    try:
        files_e = _glob_raw(raw_fs, raw_base_path, etapas_glob)
        week_map_e = _group_files_by_week(files_e)
        results["etapas"] = _ingest_etapas_files_by_week(raw_fs, bronze_fs, raw_base_path, bronze_base_path, week_map_e)
    except FileNotFoundError as e:
        print(f"⚠️ No se procesaron ETAPAS: {e}")
        results["etapas"] = None
        
    print("\n🏁 Ingesta finalizada.")
    return results

# --- Punto de Entrada ---

if __name__ == "__main__":
    if USE_LOCAL_PATHS:
        print("✅ Usando rutas locales.")
        raw_fs = None # Not needed for local open()
        bronze_fs = None # Not needed for local write_parquet
        raw_base_path = RAW_BASE_PATH
        bronze_base_path = BRONZE_BASE_PATH
        # Ensure local directories exist
        pathlib.Path(raw_base_path).mkdir(parents=True, exist_ok=True)
        pathlib.Path(bronze_base_path).mkdir(parents=True, exist_ok=True)
    else:
        print("Activando credenciales de Google Cloud...")
        try:
            raw_fs = get_gcs_filesystem()
            bronze_fs = raw_fs # Same FS for read and write
            print("✅ Filesystem de GCS inicializado.")
        except FileNotFoundError as e:
            print(f"❌ Error de autenticación: {e}", file=sys.stderr)
            sys.exit(1)
        raw_base_path = RAW_BASE_PATH
        bronze_base_path = BRONZE_BASE_PATH

    viajes_pattern = sys.argv[1] if len(sys.argv) > 1 else None
    etapas_pattern = sys.argv[2] if len(sys.argv) > 2 else None

    ingest_new_to_bronze(raw_fs=raw_fs, bronze_fs=bronze_fs, raw_base_path=raw_base_path, bronze_base_path=bronze_base_path, viajes_glob=viajes_pattern, etapas_glob=etapas_pattern)
