
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

# --- Parámetros Configurables ---
GCS_BUCKET = os.getenv("GCS_BUCKET", "tesis-vonetto-datalake")
RAW_PREFIX = os.getenv("RAW_PREFIX", "raw")
BRONZE_PREFIX = os.getenv("BRONZE_PREFIX", "lake/bronze")
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
    'factor_expansion': pl.Float64, 'id_tarjeta': pl.Utf8, 'id_viaje': pl.Int64,
    'mediahora_bajada_1': pl.Utf8, 'mediahora_bajada_2': pl.Utf8,
    'mediahora_bajada_3': pl.Utf8, 'mediahora_bajada_4': pl.Utf8,
    'mediahora_fin_viaje': pl.Utf8, 'mediahora_fin_viaje_hora': pl.Utf8,
    'mediahora_inicio_viaje': pl.Utf8, 'mediahora_inicio_viaje_hora': pl.Utf8,
    'modos': pl.Utf8, 'n_etapas': pl.Int32, 'netapassinbajada': pl.Int64,
    'op_1era_etapa': pl.Utf8, 'op_2da_etapa': pl.Utf8, 'op_3era_etapa': pl.Utf8,
    'op_4ta_etapa': pl.Utf8, 'paradero_bajada_1': pl.Utf8,
    'paradero_bajada_2': pl.Utf8, 'paradero_bajada_3': pl.Utf8,
    'paradero_bajada_4': pl.Utf8, 'paradero_fin_viaje': pl.Utf8,
    'paradero_inicio_viaje': pl.Utf8, 'paradero_subida_1': pl.Utf8,
    'paradero_subida_2': pl.Utf8, 'paradero_subida_3': pl.Utf8,
    'paradero_subida_4': pl.Utf8, 'periodo_bajada_1': pl.Utf8,
    'periodo_bajada_2': pl.Utf8, 'periodo_bajada_3': pl.Utf8,
    'periodo_bajada_4': pl.Utf8, 'periodo_fin_viaje': pl.Utf8,
    'periodo_inicio_viaje': pl.Utf8, 'proposito': pl.Utf8, 'srv_1': pl.Utf8,
    'srv_2': pl.Utf8, 'srv_3': pl.Utf8, 'srv_4': pl.Utf8, 'tc1': pl.Int64,
    'tc2': pl.Int64, 'tc3': pl.Int64, 'te0': pl.Int64, 'te1': pl.Int64,
    'te2': pl.Int64, 'te3': pl.Int64, 'tiempo_bajada_1': pl.Utf8,
    'tiempo_bajada_2': pl.Utf8, 'tiempo_bajada_3': pl.Utf8,
    'tiempo_bajada_4': pl.Utf8, 'tiempo_fin_viaje': pl.Utf8,
    'tiempo_inicio_viaje': pl.Utf8, 'tiempo_subida_1': pl.Utf8,
    'tiempo_subida_2': pl.Utf8, 'tiempo_subida_3': pl.Utf8,
    'tiempo_subida_4': pl.Utf8, 'tipo_corte_etapa_viaje': pl.Utf8,
    'tipo_transporte_1': pl.Utf8, 'tipo_transporte_2': pl.Utf8,
    'tipo_transporte_3': pl.Utf8, 'tipo_transporte_4': pl.Utf8,
    'tipodia': pl.Utf8, 'tv1': pl.Int64, 'tv2': pl.Int64, 'tv3': pl.Int64,
    'tv4': pl.Int64, 'tviaje': pl.Utf8, 'tviaje2': pl.Int64,
    'ultimaetapaconbajada': pl.Int64, 'zona_bajada_1': pl.Utf8,
    'zona_bajada_2': pl.Utf8, 'zona_bajada_3': pl.Utf8,
    'zona_bajada_4': pl.Utf8, 'zona_fin_viaje': pl.Utf8,
    'zona_inicio_viaje': pl.Utf8, 'zona_subida_1': pl.Utf8,
    'zona_subida_2': pl.Utf8, 'zona_subida_3': pl.Utf8,
    'zona_subida_4': pl.Utf8
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
def _detect_sep_from_fullpath(gfs: gcsfs.GCSFileSystem, gcs_path_no_scheme: str, default=";") -> str:
    with gfs.open(gcs_path_no_scheme, "rb") as fh:
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

def _read_csv_polars_gcs(gfs: gcsfs.GCSFileSystem, gcs_path_no_scheme: str, sep: str) -> pl.DataFrame:
    decimal_comma_flag = (sep == ";")
    with gfs.open(gcs_path_no_scheme, "rb") as fh:
        return pl.read_csv(
            fh, separator=sep, dtypes=CSV_DTYPES, try_parse_dates=False,
            null_values=NULL_TOKENS, ignore_errors=False, low_memory=True, 
            decimal_comma=decimal_comma_flag
        )

# --- Lógica de Ingesta ---
def _glob_raw(gfs: gcsfs.GCSFileSystem, patterns: str | list[str]):
    if isinstance(patterns, str):
        patterns = [patterns]
    base = f"{GCS_BUCKET}/{RAW_PREFIX}".strip("/")
    hits = []
    for pat in patterns:
        hits += gfs.glob(f"{base}/{pat}")
    hits = sorted(set(hits))
    print(f"[GCS] {len(hits)} archivos encontrados para patrones: {patterns}")
    if not hits:
        raise FileNotFoundError(f"No se encontraron CSV bajo gs://{base} con patrones {patterns}")
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

def _partition_exists(gfs: gcsfs.GCSFileSystem, base_no_scheme: str, sem: str) -> bool:
    normal = f"{base_no_scheme}/semana_iso={sem}".rstrip("/")
    return gfs.exists(normal)

def _ingest_viajes_files_by_week(gfs: gcsfs.GCSFileSystem, week_map: dict[str, list[str]]):
    out_base = gsjoin(GCS_BUCKET, BRONZE_PREFIX, "viajes").replace("gs://", "")
    fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(gfs))
    wrote, skipped, errored = [], [], []

    print(f"\n⚙️  Iniciando procesamiento de {len(week_map)} semanas para VIAJES...")
    for week, files_in_week in tqdm(week_map.items(), desc="Procesando semanas (viajes)", unit="semana"):
        if _partition_exists(gfs, out_base, week):
            skipped.append(week)
            continue
        
        try:
            print(f"\n  [Semana {week}] Encontrados {len(files_in_week)} archivos. Iniciando lectura...")
            list_of_dfs = []
            for file_path in tqdm(files_in_week, desc=f"    Leyendo archivos sem {week}", leave=False, unit="file"):
                sep = _detect_sep_from_fullpath(gfs, file_path, default=CSV_SEP_DEF)
                df = _read_csv_polars_gcs(gfs, file_path, sep)
                
                time_col = next((c for c in ["tiempo_inicio_viaje", "tiempo_subida_1", "mediahora_inicio_viaje"] if c in df.columns), None)
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
            
            target_dir = f"{out_base}/semana_iso={week_norm}"
            print(f"    - Escribiendo partición en GCS en: {target_dir}")
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

def ingest_new_to_bronze(gfs: gcsfs.GCSFileSystem, viajes_glob: str | None = None, etapas_glob: str | None = None):
    print("="*50)
    print("⏳ Iniciando ingesta RAW -> BRONZE (Estrategia: Semana por Semana con Esquema Estricto)")
    print("="*50)

    viajes_glob = viajes_glob or "raw_csv/source=drive/ingest_date=2025-10-01/*viajes.csv"
    etapas_glob = etapas_glob or "raw_csv/source=drive/ingest_date=2025-10-01/*etapas.csv"

    results = {}
    try:
        files_v = _glob_raw(gfs, viajes_glob)
        week_map_v = _group_files_by_week(files_v)
        results["viajes"] = _ingest_viajes_files_by_week(gfs, week_map_v)
    except FileNotFoundError as e:
        print(f"⚠️ No se procesaron VIAJES: {e}")
        results["viajes"] = None

    try:
        _glob_raw(gfs, etapas_glob)
        print("\nℹ️ El procesamiento de ETAPAS está actualmente desactivado en el script.")
        results["etapas"] = None
    except FileNotFoundError:
        print("\nℹ️ No se encontraron archivos de etapas, se omite su procesamiento.")
        results["etapas"] = None
        
    print("\n🏁 Ingesta finalizada.")
    return results

# --- Punto de Entrada ---

if __name__ == "__main__":
    print("Activando credenciales de Google Cloud...")
    try:
        gcs_fs = get_gcs_filesystem()
        print("✅ Filesystem de GCS inicializado.")
    except FileNotFoundError as e:
        print(f"❌ Error de autenticación: {e}", file=sys.stderr)
        sys.exit(1)

    viajes_pattern = sys.argv[1] if len(sys.argv) > 1 else None
    etapas_pattern = sys.argv[2] if len(sys.argv) > 2 else None

    ingest_new_to_bronze(gfs=gcs_fs, viajes_glob=viajes_pattern, etapas_glob=etapas_pattern)
