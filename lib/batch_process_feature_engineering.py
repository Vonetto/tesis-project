#!/usr/bin/env python3
"""
Procesamiento en batch de Feature Engineering y Detección de Anomalías
Procesa particiones de viajes_limpios -> viajes_con_indicadores y viajes_filtrados

Características:
- Procesamiento paralelo (configurable)
- Idempotente (skip particiones ya procesadas)
- Gestión de memoria optimizada
- Progress bar con tqdm
"""

import os
import sys
import gc
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, Tuple

import polars as pl
import pyarrow.parquet as pq
import gcsfs
import pyarrow.fs as pafs
from tqdm import tqdm

# Importar constantes desde config
from config.constants import GCS_BUCKET_NAME, GCS_SILVER_PREFIX, USE_LOCAL_PATHS, LOCAL_SILVER_PATH, GCS_SILVER_PATH


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

if USE_LOCAL_PATHS:
    SILVER_BASE_PATH = LOCAL_SILVER_PATH
else:
    SILVER_BASE_PATH = GCS_SILVER_PATH

INPUT_PATH = f"{SILVER_BASE_PATH}/viajes_limpios"
OUTPUT_INDICADORES_PATH = f"{SILVER_BASE_PATH}/viajes_con_indicadores"
OUTPUT_FILTRADOS_PATH = f"{SILVER_BASE_PATH}/viajes_filtrados"

NUM_WORKERS = 1  # Se mantiene en 1 para máxima estabilidad con memoria.
FORCE_REPROCESS = True  # False = solo procesa las que faltan (idempotente)
VERBOSE = True  # Mostrar detalles de cada partición procesada


# ============================================================================
# AUTENTICACIÓN GCS
# ============================================================================

def enable_adc_crossplatform():
    """Configura credenciales de Google Cloud para acceso a GCS"""
    if USE_LOCAL_PATHS:
        return # ADC not needed for local paths
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    if sys.platform.startswith("win"):
        adc_path = os.path.join(os.environ["APPDATA"], "gcloud", "application_default_credentials.json")
    else:
        adc_path = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if not os.path.exists(adc_path):
        raise FileNotFoundError(f"No se encontró ADC en {adc_path}. Ejecuta: gcloud auth application-default login")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = adc_path


# ============================================================================
# FUNCIÓN DE PROCESAMIENTO
# ============================================================================

def generar_features_y_anomalias(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict]:
    """
    Aplica feature engineering y filtros de anomalías a un DataFrame.
    
    Returns:
        df_final: DataFrame con todos los indicadores y flags de anomalía.
        stats: Diccionario con estadísticas de anomalías.
    """
    n_inicial = len(df)
    
    # 1. Feature Engineering: Calcular indicadores
    df_with_features = df.with_columns([
        pl.col("t_total_calculado_seg").cast(pl.Float64), # Ya no es alias
        pl.col("t_vehiculo_total_seg").cast(pl.Float64), # Ya no es alias
        pl.col("distancia_ruta").cast(pl.Float64).alias("distancia_ruta_m"),
        pl.col("distancia_eucl").cast(pl.Float64).alias("distancia_euc_OD_m"),
    ]).with_columns([
        (pl.col("distancia_ruta_m") / pl.col("distancia_euc_OD_m")).alias("dr_de"),
        (pl.col("distancia_ruta_m") / 1000 / (pl.col("t_vehiculo_total_seg") / 3600)).alias("velocidad_vehiculo_kmhr"),
        (pl.col("distancia_euc_OD_m") / 1000 / (pl.col("t_vehiculo_total_seg") / 3600)).alias("velocidad_eucl_kmhr"),
    ])

    # 2. Detección de Anomalías
    df_final = df_with_features.with_columns([
        (pl.col("paradero_inicio_viaje").cast(pl.Utf8) == pl.col("paradero_fin_viaje").cast(pl.Utf8)).alias("anom_a1_od_viaje"),
        (pl.col("paradero_subida_1") == pl.col("paradero_bajada_1")).alias("anom_a1_od_etapa1"),
        (pl.col("paradero_subida_2") == pl.col("paradero_bajada_2")).alias("anom_a1_od_etapa2"),
        (pl.col("paradero_subida_3") == pl.col("paradero_bajada_3")).alias("anom_a1_od_etapa3"),
        (pl.col("paradero_subida_4") == pl.col("paradero_bajada_4")).alias("anom_a1_od_etapa4"),
        (pl.col("distancia_ruta_m") < 350).alias("anom_b1_dr_min"),
        (pl.col("distancia_euc_OD_m") > 50000).alias("anom_b2_de_max"),
        (pl.col("tiempo_total_seg") < 35).alias("anom_b3_dur_min"),
        (pl.col("velocidad_vehiculo_kmhr") < 4).alias("anom_c1_vr_baja"),
        (pl.col("velocidad_eucl_kmhr") > 70).alias("anom_c2_ve_alta"),
        ((pl.col("velocidad_vehiculo_kmhr") > 60) & (pl.col("distancia_ruta_m") < 5000)).alias("anom_c3_vr_alta_dr_corto"),
        ((pl.col("velocidad_vehiculo_kmhr") > 70) & (pl.col("distancia_ruta_m") >= 5000)).alias("anom_c4_vr_alta_dr_largo"),
    ]).with_columns([
        (
            pl.col("anom_a1_od_viaje") | pl.col("anom_a1_od_etapa1") | pl.col("anom_a1_od_etapa2") |
            pl.col("anom_a1_od_etapa3") | pl.col("anom_a1_od_etapa4") |
            pl.col("anom_b1_dr_min") | pl.col("anom_b2_de_max") | pl.col("anom_b3_dur_min") |
            pl.col("anom_c1_vr_baja") | pl.col("anom_c2_ve_alta") | pl.col("anom_c3_vr_alta_dr_corto") |
            pl.col("anom_c4_vr_alta_dr_largo")
        ).fill_null(False).alias("is_anomalo")
    ])

    # 3. Calcular estadísticas
    stats_part = df_final.select([
        pl.len().alias("n_viajes"),
        pl.col("is_anomalo").sum().alias("n_anomalos"),
        *[pl.col(f"anom_{k}").sum().alias(f"count_{k}") for k in ["a1_od_viaje", "a1_od_etapa1", "a1_od_etapa2", "a1_od_etapa3", "a1_od_etapa4", "b1_dr_min", "b2_de_max", "b3_dur_min", "c1_vr_baja", "c2_ve_alta", "c3_vr_alta_dr_corto", "c4_vr_alta_dr_largo"]]
    ])
    
    stats = {key: stats_part[key][0] for key in stats_part.columns}
    stats['n_inicial'] = n_inicial
    stats['n_validos'] = n_inicial - stats['n_anomalos']
    
    return df_final, stats


# ============================================================================
# PROCESAMIENTO DE PARTICIÓN
# ============================================================================

def procesar_particion(particion: Dict, force_reprocess: bool = False, verbose: bool = False) -> Dict:
    """
    Procesa una partición individual: lee, procesa y escribe en dos outputs.
    """
    year = particion['year']
    week = particion['week']
    input_files = particion['path']  # Puede ser una lista de archivos
    
    # Asegurar que input_files sea una lista
    if isinstance(input_files, str):
        input_files = [input_files]
    
    fs = None # Initialize fs
    fs_arrow = None # Initialize fs_arrow

    if not USE_LOCAL_PATHS:
        try:
            enable_adc_crossplatform()
            fs = gcsfs.GCSFileSystem(token="google_default")
            fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(fs))
        except Exception as e:
            return {'status': 'error', 'year': year, 'week': week, 'error': f"Error de autenticación GCS: {e}"}
    
    # Verificar si ya existe en el primer output (viajes_con_indicadores)
    output_partition_indicadores = f"{OUTPUT_INDICADORES_PATH}/iso_year={year}/iso_week={week}"
    output_file_indicadores = f"{output_partition_indicadores}/data-0.parquet"
    
    if USE_LOCAL_PATHS:
        if pathlib.Path(output_file_indicadores).exists() and not force_reprocess:
            return {'status': 'skipped', 'year': year, 'week': week}
    else:
        if fs.exists(output_file_indicadores.replace("gs://", "").strip("/")) and not force_reprocess:
            return {'status': 'skipped', 'year': year, 'week': week}
    
    df = None
    df_final = None
    tabla = None
    
    try:
        if verbose: 
            print(f"\n📖 Leyendo {year}-W{week} ({len(input_files)} archivo{'s' if len(input_files) > 1 else ''})...")
        
        # Leer todos los archivos de la partición y combinarlos
        tablas = []
        for input_file in input_files:
            if USE_LOCAL_PATHS:
                with open(input_file, 'rb') as f:
                    tabla = pq.read_table(f)
                    tablas.append(tabla)
            else:
                with fs_arrow.open_input_file(input_file) as f:
                    tabla = pq.read_table(f)
                    tablas.append(tabla)
        
        # Combinar todas las tablas en una sola
        if len(tablas) == 1:
            df = pl.from_arrow(tablas[0])
        else:
            # Combinar múltiples tablas
            df = pl.concat([pl.from_arrow(t) for t in tablas])
        
        del tablas; gc.collect()
        
        if verbose: print(f"   ✓ Leídas {len(df):,} filas. Aplicando features y filtros...")
        
        df_final, stats = generar_features_y_anomalias(df)
        del df; df = None; gc.collect()
        
        if verbose: print(f"   ✓ Procesado. Viajes válidos: {stats['n_validos']:,} / {stats['n_inicial']:,}")

        # --- Escritura 1: viajes_con_indicadores ---
        if verbose: print(f"   💾 Guardando viajes_con_indicadores...")
        if USE_LOCAL_PATHS:
            pathlib.Path(output_partition_indicadores).mkdir(parents=True, exist_ok=True)
            df_final.write_parquet(output_file_indicadores, compression='zstd')
        else:
            fs.makedirs(output_partition_indicadores.replace("gs://", "").strip("/"), exist_ok=True)
            with fs.open(output_file_indicadores.replace("gs://", "").strip("/"), 'wb') as f:
                df_final.write_parquet(f, compression='zstd')
        
        # --- Escritura 2: viajes_filtrados ---
        if verbose: print(f"   💾 Guardando viajes_filtrados...")
        df_filtrado = df_final.filter(pl.col("is_anomalo") != True)
        
        # Columnas de anomalías a eliminar de viajes_filtrados
        anomaly_cols_to_drop = [
            "anom_a1_od_viaje", "anom_a1_od_etapa1", "anom_a1_od_etapa2", "anom_a1_od_etapa3", "anom_a1_od_etapa4",
            "anom_b1_dr_min", "anom_b2_de_max", "anom_b3_dur_min",
            "anom_c1_vr_baja", "anom_c2_ve_alta", "anom_c3_vr_alta_dr_corto", "anom_c4_vr_alta_dr_largo",
            "is_anomalo"
        ]
        
        # Eliminar solo las columnas que existen en df_filtrado
        cols_to_drop_existing = [col for col in anomaly_cols_to_drop if col in df_filtrado.columns]
        if cols_to_drop_existing:
            df_filtrado = df_filtrado.drop(cols_to_drop_existing)
        
        output_partition_filtrados = f"{OUTPUT_FILTRADOS_PATH}/iso_year={year}/iso_week={week}"
        output_file_filtrados = f"{output_partition_filtrados}/data-0.parquet"
        
        if USE_LOCAL_PATHS:
            pathlib.Path(output_partition_filtrados).mkdir(parents=True, exist_ok=True)
            df_filtrado.write_parquet(output_file_filtrados, compression='zstd')
        else:
            fs.makedirs(output_partition_filtrados.replace("gs://", "").strip("/"), exist_ok=True)
            with fs.open(output_file_filtrados.replace("gs://", "").strip("/"), 'wb') as f:
                df_filtrado.write_parquet(f, compression='zstd')
            
        if verbose: print(f"   ✓ Partición {year}-W{week} guardada exitosamente.")
        
        del df_final, df_filtrado; gc.collect()
        
        return {'status': 'success', 'year': year, 'week': week, 'stats': stats}
        
    except Exception as e:
        del df, df_final; gc.collect()
        import traceback
        error_detail = traceback.format_exc()
        return {'status': 'error', 'year': year, 'week': week, 'error': f"{str(e)}\n{error_detail}"}


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print("🔄 BATCH PROCESSING - FEATURE ENGINEERING & ANOMALY DETECTION")
    print("="*80)
    print(f"\n⚙️  Configuración:")
    print(f"   - Workers paralelos: {NUM_WORKERS}")
    print(f"   - Forzar reprocesamiento: {FORCE_REPROCESS}")
    print(f"   - Input:  {INPUT_PATH}")
    print(f"   - Output (indicadores): {OUTPUT_INDICADORES_PATH}")
    print(f"   - Output (filtrados):  {OUTPUT_FILTRADOS_PATH}")
    
    fs = None # Initialize fs
    if not USE_LOCAL_PATHS:
        try:
            enable_adc_crossplatform()
            fs = gcsfs.GCSFileSystem(token="google_default")
            print("\n✅ Conexión con GCS establecida")
        except Exception as e:
            print(f"\n❌ Error de autenticación: {e}"); return 1
    else:
        print("\n✅ Usando rutas locales.")
    
    print("\n🔍 Buscando particiones disponibles...")
    try:
        particiones = []
        if USE_LOCAL_PATHS:
            # Local file system glob
            for year_dir in pathlib.Path(INPUT_PATH).glob("iso_year=*"):
                year = int(str(year_dir).split('iso_year=')[1])
                for week_dir in year_dir.glob("iso_week=*"):
                    week = int(str(week_dir).split('iso_week=')[1])
                    particiones.extend([{'year': year, 'week': week, 'path': str(p)} for p in week_dir.glob("*.parquet")])
        else:
            # GCS glob
            for year_dir in fs.glob(f"{INPUT_PATH.replace('gs://', '').strip('/')}/iso_year=*"):
                year = int(year_dir.split('iso_year=')[1])
                for week_dir in fs.glob(f"{year_dir}/iso_week=*"):
                    week = int(week_dir.split('iso_week=')[1])
                    particiones.extend([{'year': year, 'week': week, 'path': f"gs://{p}"} for p in fs.glob(f"{week_dir}/*.parquet")])

        # Agrupar por partición, ya que pueden haber múltiples archivos
        from collections import defaultdict
        grouped_partitions = defaultdict(list)
        for p in particiones:
            grouped_partitions[(p['year'], p['week'])].append(p['path'])
        
        particiones_final = [{'year': k[0], 'week': k[1], 'path': v} for k,v in grouped_partitions.items()]

        print(f"✅ Se encontraron {len(particiones_final)} particiones")
    except Exception as e:
        print(f"❌ Error al listar particiones: {e}"); return 1
    
    if not particiones_final:
        print("\n⚠️ No se encontraron particiones para procesar"); return 0
    
    print("\n" + "="*80); print("🚀 INICIANDO PROCESAMIENTO"); print("="*80)
    start_time = time.time()
    
    stats_globales = defaultdict(int)
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(procesar_particion, p, FORCE_REPROCESS, VERBOSE): p for p in particiones_final}
        
        iterable = as_completed(futures)
        if not VERBOSE:
            iterable = tqdm(iterable, total=len(particiones_final), desc="Procesando")

        for future in iterable:
            try:
                resultado = future.result()
                status = resultado['status']
                stats_globales[status] += 1
                
                if status == 'success':
                    for key, value in resultado['stats'].items():
                        stats_globales[key] += value
                elif status == 'skipped' and VERBOSE:
                    print(f"⏭️  {resultado['year']}-W{resultado['week']}: ya procesado")
                elif status == 'error':
                    print(f"\n❌ Error en {resultado['year']}-W{resultado['week']}:\n{resultado.get('error', 'Unknown')}")
            except Exception as e:
                stats_globales['error'] += 1
                particion = futures[future]
                print(f"\n💥 Error crítico en worker para {particion['year']}-W{particion['week']}: {e}")

    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80); print("📊 RESUMEN FINAL"); print("="*80)
    print(f"\n⏱️  Tiempo total: {elapsed_time/60:.2f} minutos")
    print(f"\n📦 Particiones: Total: {len(particiones_final)} | Procesadas: {stats_globales['success']} | Skipped: {stats_globales['skipped']} | Fallidas: {stats_globales['error']}")
    
    if stats_globales['n_inicial'] > 0:
        print(f"\n📈 Viajes: Iniciales: {stats_globales['n_inicial']:,} | Válidos: {stats_globales['n_validos']:,} ({stats_globales['n_validos']/stats_globales['n_inicial']*100:.2f}%)")
        print(f"   Anómalos: {stats_globales['n_anomalos']:,} ({stats_globales['n_anomalos']/stats_globales['n_inicial']*100:.2f}%)")
    
    print("\n" + "="*80)
    if stats_globales['error'] == 0:
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
    else:
        print("⚠️ PROCESAMIENTO COMPLETADO CON ERRORES")
    print("="*80)
    
    return 0 if stats_globales['error'] == 0 else 1

if __name__ == "__main__":
    # Añadir soporte para argumentos de línea de comando
    import argparse
    parser = argparse.ArgumentParser(description="Procesamiento en batch de feature engineering y anomalías.")
    parser.add_argument("--workers", type=int, default=NUM_WORKERS, help=f"Número de workers paralelos (default: {NUM_WORKERS})")
    parser.add_argument("--force", action="store_true", help="Forzar el reprocesamiento de todas las particiones.")
    args = parser.parse_args()
    
    NUM_WORKERS = args.workers
    FORCE_REPROCESS = args.force
    
    sys.exit(main())
