import os
import sys
import shutil
from pathlib import Path
import polars as pl
from tqdm import tqdm
from collections import defaultdict
import re
from datetime import datetime

# --- VERIFICACIÓN DE VERSIÓN ---
print(f"--- Usando Polars versión: {pl.__version__} ---")
# -----------------------------

# --- Setup de Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config.constants import (
    USE_LOCAL_PATHS,
    LOCAL_RAW_PERFILES_PATH,
    LOCAL_BRONZE_PATH,
    GCS_BRONZE_PERFILES_PATH,
)
from lib.datalake import get_filesystem

# --- Configuración del Script ---
if USE_LOCAL_PATHS:
    RAW_PATH = LOCAL_RAW_PERFILES_PATH
    BRONZE_PATH = LOCAL_BRONZE_PATH
else:
    from config.constants import GCS_RAW_PATH
    RAW_PATH = f"{GCS_RAW_PATH}/raw_csv/perfiles_carga"
    BRONZE_PATH = GCS_BRONZE_PERFILES_PATH

BRONZE_OUTPUT_PATH = f"{BRONZE_PATH}/perfiles_de_carga_consolidados"
# Directorio temporal para una escritura segura y atómica
TEMP_OUTPUT_PATH = f"{BRONZE_PATH}/perfiles_de_carga_consolidados_tmp"

# --- Lógica Principal ---

def get_week_from_filename(filename: str) -> tuple[int, int] | None:
    """Extrae el año y la semana ISO de un nombre de archivo."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    if not match:
        return None
    try:
        date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
        iso_year, iso_week, _ = date.isocalendar()
        return iso_year, iso_week
    except ValueError:
        return None

def process_perfiles_de_carga():
    """
    Lee archivos CSV diarios de perfiles_de_carga, los agrupa por semana,
    y guarda cada semana como un único archivo Parquet particionado usando una
    estrategia de escritura atómica para evitar corrupción.
    """
    print("="*80)
    print("🔄 Iniciando Pre-procesamiento de Perfiles de Carga (Modo Atómico)")
    print("="*80)
    
    # Limpiar directorio temporal antes de empezar, si existe
    if os.path.exists(TEMP_OUTPUT_PATH):
        print(f"🧹 Limpiando directorio temporal anterior: {TEMP_OUTPUT_PATH}")
        shutil.rmtree(TEMP_OUTPUT_PATH)

    try:
        # 1. Encontrar y agrupar archivos por partición de destino
        print(f"🔍 Buscando y agrupando archivos en: {RAW_PATH}")
        if USE_LOCAL_PATHS:
            file_paths = [str(p) for p in Path(RAW_PATH).glob("*.perfiles_de_carga.csv")]
        else:
            # Esta sección necesitaría una implementación de `shutil.rmtree` y `os.rename` para GCS
            # Por ahora, nos centramos en la lógica local que es la que se está usando.
            raise NotImplementedError("La escritura atómica para GCS requiere un manejo más complejo y no está implementada.")

        if not file_paths:
            print("❌ No se encontraron archivos 'perfiles_de_carga.csv'. Abortando.")
            return

        grouped_files = defaultdict(list)
        for f in file_paths:
            week_tuple = get_week_from_filename(os.path.basename(f))
            if week_tuple:
                grouped_files[week_tuple].append(f)
            else:
                print(f"⚠️ No se pudo determinar la semana para el archivo: {os.path.basename(f)}")

        print(f"✅ Encontrados {len(file_paths)} archivos CSV, agrupados en {len(grouped_files)} particiones (semanas).")

        schema = {'ServicioSentido': pl.Utf8, 'ServicioUsuario': pl.Utf8, 'Patente': pl.Utf8, 'Paradero': pl.Utf8, 'NombreParada': pl.Utf8, 'Tiempo': pl.Utf8, 'TiempoGPSMasCercano': pl.Utf8, "TiempoGPSInterpolado": pl.Utf8}
        cols_to_select = list(schema.keys())

        # 2. Procesar cada grupo y escribir en el directorio temporal
        print(f"⚙️  Procesando y escribiendo en directorio temporal: {TEMP_OUTPUT_PATH}")
        
        for (year, week), files_in_week in tqdm(grouped_files.items(), desc="Procesando particiones", unit="semana"):
            lf_week = pl.concat([
                pl.scan_csv(file, separator='|', has_header=True, schema_overrides=schema, low_memory=True, ignore_errors=True).select(cols_to_select)
                for file in files_in_week
            ], how="diagonal")

            df_processed = (
                lf_week
                .with_columns(pl.col("Tiempo").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False).alias("timestamp"))
                .with_columns([
                    # Para las columnas GPS: 
                    # - Si tienen formato completo (contienen "-"), parsear directamente
                    # - Si solo tienen hora (ej: "00:02:39"), combinar con la fecha del timestamp principal
                    # - Si timestamp es null o la columna GPS está vacía, el resultado será null
                    pl.when(pl.col("TiempoGPSMasCercano").str.contains("-", literal=True))
                        .then(pl.col("TiempoGPSMasCercano").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False))
                        .when(pl.col("timestamp").is_not_null())
                        .then(
                            pl.concat_str([
                                pl.col("timestamp").dt.date().cast(pl.Utf8),
                                pl.lit(" "),
                                pl.col("TiempoGPSMasCercano")
                            ]).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
                        )
                        .otherwise(None)
                        .alias("timestamp_gps_mas_cercano"),
                    pl.when(pl.col("TiempoGPSInterpolado").str.contains("-", literal=True))
                        .then(pl.col("TiempoGPSInterpolado").str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False))
                        .when(pl.col("timestamp").is_not_null())
                        .then(
                            pl.concat_str([
                                pl.col("timestamp").dt.date().cast(pl.Utf8),
                                pl.lit(" "),
                                pl.col("TiempoGPSInterpolado")
                            ]).str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False)
                        )
                        .otherwise(None)
                        .alias("timestamp_gps_interpolado"),
                    pl.col("timestamp").dt.iso_year().alias("iso_year"),
                    pl.col("timestamp").dt.week().alias("iso_week"),
                    pl.col("ServicioSentido").cast(pl.Categorical),
                    pl.col("Patente").cast(pl.Categorical),
                    pl.col("Paradero").cast(pl.Categorical),
                    pl.col("NombreParada").cast(pl.Categorical),

                ])
                .collect()
            )

            if df_processed.is_empty():
                continue

            partition_dir = os.path.join(TEMP_OUTPUT_PATH, f"iso_year={year}", f"iso_week={week}")
            output_file_path = os.path.join(partition_dir, "data-0.parquet")
            Path(partition_dir).mkdir(parents=True, exist_ok=True)
            df_processed.write_parquet(output_file_path, compression="zstd")

        # 3. "Commit" atómico: Si todo fue exitoso, reemplazar el directorio final
        print("\n✅ Escritura en directorio temporal completada.")
        print("   Realizando 'commit' atómico...")
        
        if os.path.exists(BRONZE_OUTPUT_PATH):
            shutil.rmtree(BRONZE_OUTPUT_PATH)
        
        os.rename(TEMP_OUTPUT_PATH, BRONZE_OUTPUT_PATH)
        
        print("   ✅ 'Commit' realizado con éxito.")

    except Exception as e:
        print(f"\n❌ Ocurrió un error durante el procesamiento: {e}")
        print("   🧹 Limpiando directorio temporal para evitar datos corruptos...")
        if os.path.exists(TEMP_OUTPUT_PATH):
            shutil.rmtree(TEMP_OUTPUT_PATH)
        print("   Directorio temporal eliminado.")
        # Re-raise the exception so the script exits with an error code
        raise
        
    print("\n" + "="*80)
    print("✅ ¡Éxito! Pre-procesamiento de perfiles_de_carga completado de forma segura.")
    print(f"   Los datos consolidados y particionados están en: {BRONZE_OUTPUT_PATH}")
    print("="*80)

if __name__ == "__main__":
    process_perfiles_de_carga()
