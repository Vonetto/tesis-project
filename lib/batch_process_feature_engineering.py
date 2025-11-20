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
from tqdm import tqdm

# Habilitar StringCache globalmente para optimizar el uso de memoria
pl.enable_string_cache()

import pathlib
from collections import defaultdict # Added for main function

project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importar funciones de acceso a datos centralizadas
from lib.datalake import read_parquet_portable, get_filesystem

# Importar constantes desde config
from config.constants import GCS_BUCKET_NAME, GCS_SILVER_PREFIX, USE_LOCAL_PATHS, LOCAL_SILVER_PATH, GCS_SILVER_PATH


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# --- PARÁMETRO DE PRUEBA ---
# True:  Lee desde 'viajes_enriquecidos', crea las columnas necesarias que se
#        generarían en el paso de calidad (pero sin filtrar filas) y luego
#        aplica los filtros de anomalías. Sirve para probar si los filtros de
#        anomalías son suficientes por sí solos.
#        Guarda los resultados en paths con sufijo '_test'.
# False: Lee desde 'viajes_limpios' (comportamiento normal).
RUN_ON_ENRIQUECIDOS = False  

if USE_LOCAL_PATHS:
    SILVER_BASE_PATH = LOCAL_SILVER_PATH
else:
    SILVER_BASE_PATH = GCS_SILVER_PATH

if RUN_ON_ENRIQUECIDOS:
    INPUT_PATH = f"{SILVER_BASE_PATH}/viajes_enriquecidos"
else:
    INPUT_PATH = f"{SILVER_BASE_PATH}/viajes_limpios"
    
OUTPUT_FILTRADOS_PATH = f"{SILVER_BASE_PATH}/viajes_filtrados"

NUM_WORKERS = 1  # Se mantiene en 1 para máxima estabilidad con memoria.
FORCE_REPROCESS = True  # False = solo procesa las que faltan (idempotente)
VERBOSE = True  # Mostrar detalles de cada partición procesada


# ============================================================================ 
# FUNCIÓN DE PROCESAMIENTO
# ============================================================================ 

def crear_columnas_de_calidad(df: pl.DataFrame) -> pl.DataFrame:
    """
    Crea las columnas calculadas que se originan en el script de calidad de datos,
    pero sin aplicar ningún filtro de filas. Esto es necesario para que el
    script de feature engineering tenga las columnas que espera cuando se ejecuta
    directamente sobre 'viajes_enriquecidos'.
    """
    df = df.with_columns([
        # Crear columnas calculadas de tiempo
        (pl.col("tv1").fill_null(0) + pl.col("tv2").fill_null(0) + 
         pl.col("tv3").fill_null(0) + pl.col("tv4").fill_null(0)).alias("t_vehiculo_total_seg"),
        
        (pl.col("te0").fill_null(0) + pl.col("tv1").fill_null(0) + pl.col("tc1").fill_null(0) +
         pl.col("te1").fill_null(0) + pl.col("tv2").fill_null(0) + pl.col("tc2").fill_null(0) +
         pl.col("te2").fill_null(0) + pl.col("tv3").fill_null(0) + pl.col("tc3").fill_null(0) +
         pl.col("te3").fill_null(0) + pl.col("tv4").fill_null(0)).alias("t_total_calculado_seg"),
        
        # Calcular suma de distancias euclidianas de vehículo
        (pl.col("dveh_euc1").fill_null(0) + pl.col("dveh_euc2").fill_null(0) + 
         pl.col("dveh_euc3").fill_null(0) + pl.col("dveh_euc4").fill_null(0)).alias("d_vehiculo_eucl_total_m"),
    ])
    
    # Imputar dveh_eucfinal si es null, usando la suma de distancias de vehículo
    df = df.with_columns([
        pl.when(pl.col("dveh_eucfinal").is_null())
          .then(pl.col("d_vehiculo_eucl_total_m"))
          .otherwise(pl.col("dveh_eucfinal"))
          .alias("dveh_eucfinal")
    ])
    
    return df

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
        (pl.col("t_total_calculado_seg") < 35).alias("anom_b3_dur_min"),
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
    
    # --- Idempotency check on the FINAL output ---
    output_partition_filtrados = f"{OUTPUT_FILTRADOS_PATH}/iso_year={year}/iso_week={week}"
    output_file_filtrados = f"{output_partition_filtrados}/data-0.parquet"
    
    if USE_LOCAL_PATHS:
        if pathlib.Path(output_file_filtrados).exists() and not force_reprocess:
            return {'status': 'skipped', 'year': year, 'week': week}
    else:
        fs = get_filesystem()
        if fs.exists(output_file_filtrados.replace("gs://", "").strip("/")) and not force_reprocess:
            return {'status': 'skipped', 'year': year, 'week': week}
    
    df = None
    df_final = None
    
    try:
        if verbose: 
            print(f"\n📖 Leyendo {year}-W{week} ({len(input_files)} archivo{'s' if len(input_files) > 1 else ''})...")
        
        # --- Comprobar si los archivos están vacíos antes de leer ---
        non_empty_files = []
        if USE_LOCAL_PATHS:
            for f in input_files:
                if pathlib.Path(f).stat().st_size > 0:
                    non_empty_files.append(f)
        else:
            fs = get_filesystem()
            for f in input_files:
                if fs.info(f.replace("gs://", "").strip('/'))['size'] > 0:
                    non_empty_files.append(f)
        
        if not non_empty_files:
            return {
                'status': 'skipped_empty',
                'year': year,
                'week': week,
            }

        # --- Leer cada archivo por separado y concatenar con Polars ---
        lista_dfs = [read_parquet_portable(file).collect() for file in non_empty_files]

        if not lista_dfs:
             return {
                'status': 'error',
                'year': year,
                'week': week,
                'error': f"No se pudieron leer archivos Parquet válidos en la partición."
            }
        
        df_viajes = pl.concat(lista_dfs) if len(lista_dfs) > 1 else lista_dfs[0]
        
        # --- Si se corre sobre 'enriquecidos', solo crear columnas necesarias, no filtrar ---
        if RUN_ON_ENRIQUECIDOS:
            if verbose: print(f"   -> Creando columnas de calidad (modo prueba)...")
            df_viajes = crear_columnas_de_calidad(df_viajes)

        if verbose: print(f"   ✓ Leídas {len(df_viajes):,} filas. Aplicando features y filtros de anomalía...")
        
        df_final, stats = generar_features_y_anomalias(df_viajes)
        del df_viajes; df_viajes = None; gc.collect()
        
        if verbose: print(f"   ✓ Procesado. Viajes válidos: {stats['n_validos']:,} / {stats['n_inicial']:,}")

        # --- Filtrar y guardar el output final: viajes_filtrados ---
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
            
        # --- Optimización Final de Tipos de Datos (Solo Numéricos) ---
        if verbose: print(f"   ⚙️  Optimizando tipos de datos numéricos antes de guardar...")
        
        # Dejamos que Parquet maneje la optimización de strings (dictionary encoding).
        # Solo hacemos downcast de los floats que creamos en este paso.
        dtype_optimizations = {
            "t_vehiculo_total_seg": pl.Float32, 
            "t_total_calculado_seg": pl.Float32,
            "distancia_ruta_m": pl.Float32, 
            "distancia_euc_OD_m": pl.Float32,
            "dr_de": pl.Float32, 
            "velocidad_vehiculo_kmhr": pl.Float32, 
            "velocidad_eucl_kmhr": pl.Float32,
        }
        
        cast_expressions = [
            pl.col(col).cast(dtype) 
            for col, dtype in dtype_optimizations.items() 
            if col in df_filtrado.columns
        ]
        
        if cast_expressions:
            df_filtrado = df_filtrado.with_columns(cast_expressions)
  
        if USE_LOCAL_PATHS:
            pathlib.Path(output_partition_filtrados).mkdir(parents=True, exist_ok=True)
        else:
            fs = get_filesystem()
            fs.makedirs(output_partition_filtrados.replace("gs://", "").strip("/"), exist_ok=True)
            
        df_filtrado.write_parquet(output_file_filtrados, compression='zstd')
            
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
    if RUN_ON_ENRIQUECIDOS:
        print(f"   - MODO PRUEBA ACTIVO: Leyendo desde 'viajes_enriquecidos'")
    print(f"   - Workers paralelos: {NUM_WORKERS}")
    print(f"   - Forzar reprocesamiento: {FORCE_REPROCESS}")
    print(f"   - Input:  {INPUT_PATH}")
    print(f"   - Output: {OUTPUT_FILTRADOS_PATH}")
    
    # Initialize GCS filesystem once if needed
    if not USE_LOCAL_PATHS:
        # This will call get_filesystem() and potentially authenticate
        try:
            get_filesystem()
            print("\n✅ Conexión con GCS establecida")
        except Exception as e:
            print(f"\n❌ Error de autenticación: {e}"); return 1
    else:
        print("\n✅ Usando rutas locales.")
    
    print("\n🔍 Buscando particiones disponibles...")
    try:
        particiones = []
        if USE_LOCAL_PATHS:
            # Local file system glob, ignorando archivos ocultos
            for year_dir in pathlib.Path(INPUT_PATH).glob("iso_year=*"):
                year = int(str(year_dir).split('iso_year=')[1])
                for week_dir in year_dir.glob("iso_week=*"):
                    week = int(str(week_dir).split('iso_week=')[1])
                    # Añadir solo archivos parquet que no sean ocultos
                    particiones.extend([
                        {'year': year, 'week': week, 'path': str(p)} 
                        for p in week_dir.glob("*.parquet") if not p.name.startswith('._')
                    ])
        else:
            fs = get_filesystem()
            # GCS glob
            # Ensure INPUT_PATH is treated as a GCS path for globbing
            gcs_input_path = INPUT_PATH.replace("gs://", "").strip('/')
            for year_dir in fs.glob(f"{gcs_input_path}/iso_year=*"):
                year = int(year_dir.split('iso_year=')[1])
                for week_dir in fs.glob(f"{year_dir}/iso_week=*"):
                    week = int(week_dir.split('iso_week=')[1])
                    # Añadir solo archivos parquet que no sean ocultos
                    particiones.extend([
                        {'year': year, 'week': week, 'path': f"gs://{p}"} 
                        for p in fs.glob(f"{week_dir}/*.parquet") if not Path(p).name.startswith('._')
                    ])

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
    
    # Verificar cuántas particiones ya existen
    particiones_pendientes = []
    particiones_existentes = 0
    
    for p in particiones_final:
        output_partition = f"{OUTPUT_FILTRADOS_PATH}/iso_year={p['year']}/iso_week={p['week']}"
        output_file = f"{output_partition}/data-0.parquet"
        
        if USE_LOCAL_PATHS:
            if pathlib.Path(output_file).exists() and not FORCE_REPROCESS:
                particiones_existentes += 1
            else:
                particiones_pendientes.append(p)
        else:
            fs = get_filesystem()
            if fs.exists(output_file.replace("gs://", "").strip("/")) and not FORCE_REPROCESS:
                particiones_existentes += 1
            else:
                particiones_pendientes.append(p)

    print(f"\n📊 Estado de particiones:")
    print(f"   - Total disponibles: {len(particiones_final)}")
    print(f"   - Ya procesadas (skip): {particiones_existentes}")
    print(f"   - Pendientes de procesar: {len(particiones_pendientes)}")
    
    if len(particiones_pendientes) == 0:
        print("\n✅ Todas las particiones ya fueron procesadas!")
        print("   Para reprocesar, cambia FORCE_REPROCESS = True")
    else:
        print(f"\n⏱️  Tiempo estimado: ~{len(particiones_pendientes) * 0.5:.1f} - {len(particiones_pendientes) * 2:.1f} minutos")
        print("💾 Memoria: Se libera explícitamente después de cada partición")
    
    stats_globales = {
        'n_inicial': 0,
        'n_filtrados_tiempo': 0,
        'n_filtrados_paraderos': 0,
        'n_filtrados_dist': 0,
        'n_final': 0,
        'particiones_procesadas': 0,
        'particiones_skipped': particiones_existentes,
        'particiones_fallidas': 0
    }
    
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {executor.submit(procesar_particion, p, FORCE_REPROCESS, VERBOSE): p for p in particiones_pendientes} # Changed from particiones_final to particiones_pendientes
        
        iterable = as_completed(futures)
        if not VERBOSE:
            iterable = tqdm(iterable, total=len(particiones_pendientes), desc="Procesando") # Changed from particiones_final to particiones_pendientes

        for future in iterable:
            try:
                resultado = future.result()
                status = resultado['status']
                stats_globales[status] += 1
                
                if status == 'success':
                    for key, value in resultado['stats'].items():
                        stats_globales[key] += value
                elif status == 'skipped':
                    stats_globales['particiones_skipped'] += 1
                    print(f"⏭️  {resultado['year']}-W{resultado['week']}: ya procesado")
                elif status == 'skipped_empty':
                    stats_globales['particiones_skipped'] += 1
                    print(f"⏭️  {resultado['year']}-W{resultado['week']}: input vacío, omitido")
                elif status == 'error':
                    stats_globales['particiones_fallidas'] += 1
                    print(f"\n❌ Error en {resultado['year']}-W{resultado['week']}:")
                    print(f"   Error: {resultado.get('error', 'Unknown')}")
            except Exception as e:
                stats_globales['error'] += 1
                particion = futures[future]
                print(f"\n💥 Error crítico en worker para {particion['year']}-W{particion['week']}: {e}")

    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80); print("📊 RESUMEN FINAL DE LA PRUEBA"); print("="*80)
    print(f"\n⏱️  Tiempo total: {elapsed_time/60:.2f} minutos")
    print(f"\n📦 Particiones: Total: {len(particiones_final)} | Procesadas: {stats_globales['success']} | Skipped: {stats_globales['skipped'] + stats_globales['skipped_empty']} | Fallidas: {stats_globales['error']}")
    
    if stats_globales['n_inicial'] > 0:
        print(f"\n📈 Resultados Consolidados:")
        print(f"   - Viajes iniciales (enriquecidos): {stats_globales['n_inicial']:,}")
        print(f"   - Viajes marcados como anómalos: {stats_globales['n_anomalos']:,} ({stats_globales['n_anomalos']/stats_globales['n_inicial']*100:.2f}% del total inicial)")
        print(f"   - Viajes VÁLIDOS FINALES: {stats_globales['n_validos']:,}")
        print(f"   - % Retención final (vs. inicial): {stats_globales['n_validos']/stats_globales['n_inicial']*100:.2f}%")

        print(f"\n📊 Desglose de Viajes Anómalos (sobre el total inicial):")
        
        anomaly_keys = [
            "a1_od_viaje", "a1_od_etapa1", "a1_od_etapa2", "a1_od_etapa3", "a1_od_etapa4", 
            "b1_dr_min", "b2_de_max", "b3_dur_min", 
            "c1_vr_baja", "c2_ve_alta", "c3_vr_alta_dr_corto", "c4_vr_alta_dr_largo"
        ]
        
        print(f"{ 'Causa de Anomalia':<30} {'Conteos':>15} {'%':>8}")
        print(f"{'-'*30} {'-'*15} {'-'*8}")

        for key in anomaly_keys:
            count = stats_globales.get(f"count_{key}", 0)
            percentage = (count / stats_globales['n_inicial'] * 100) if stats_globales['n_inicial'] > 0 else 0
            print(f"{key:<30} {count:>15,} {percentage:>7.2f}%")
        
        print(f"{'-'*30} {'-'*15} {'-'*8}")
        
        total_anomalos = stats_globales['n_anomalos']
        total_anomalos_pct = (total_anomalos / stats_globales['n_inicial'] * 100) if stats_globales['n_inicial'] > 0 else 0
        print(f"{ 'TOTAL ANÓMALOS (al menos una causa)':<30} {total_anomalos:>15,} {total_anomalos_pct:>7.2f}%")
    
    print("\n" + "="*80)
    if stats_globales['error'] == 0:
        print("✅ PRUEBA COMPLETADA EXITOSAMENTE")
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