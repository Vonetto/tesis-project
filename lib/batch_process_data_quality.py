#!/usr/bin/env python3
"""
Procesamiento en batch de calidad de datos con paralelización
Procesa particiones de viajes_enriquecidos -> viajes_limpios

Características:
- Procesamiento paralelo (3 workers por defecto)
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


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

GCS_BUCKET = "tesis-vonetto-datalake"
SILVER_PATH = f"{GCS_BUCKET}/lake/silver"
INPUT_PATH = f"{SILVER_PATH}/viajes_enriquecidos"
OUTPUT_PATH = f"{SILVER_PATH}/viajes_limpios"

NUM_WORKERS = 1  # CRÍTICO: Con 2+ workers crashea por memoria en particiones grandes
FORCE_REPROCESS = False  # False = solo procesa las que faltan (idempotente)
VERBOSE = True  # Mostrar detalles de cada partición procesada


# ============================================================================
# AUTENTICACIÓN GCS
# ============================================================================

def enable_adc_crossplatform():
    """Configura credenciales de Google Cloud para acceso a GCS"""
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
# FUNCIÓN DE FILTRADO
# ============================================================================

def aplicar_filtros(df: pl.DataFrame) -> Tuple[pl.DataFrame, Dict]:
    """
    Aplica todos los filtros de calidad de datos a un DataFrame.
    
    Returns:
        df_filtrado: DataFrame con los filtros aplicados
        stats: Diccionario con estadísticas de filtrado
    """
    n_inicial = len(df)
    
    # Crear columnas calculadas de tiempo
    df = df.with_columns([
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
    
    # A) Filtrar por tiempos
    df = df.filter(
        (pl.col("t_vehiculo_total_seg") > 0) &
        (pl.col("t_total_calculado_seg") > 0)
    )
    n_despues_tiempo = len(df)
    n_filtrados_tiempo = n_inicial - n_despues_tiempo
    
    # B) Filtrar por paraderos
    df = df.filter(
        pl.col("paradero_inicio_viaje").is_not_null() &
        pl.col("paradero_fin_viaje").is_not_null()
    )
    n_despues_paraderos = len(df)
    n_filtrados_paraderos = n_despues_tiempo - n_despues_paraderos
    
    # C) Imputar y filtrar por distancias
    # Imputar dveh_eucfinal si es null
    df = df.with_columns([
        pl.when(pl.col("dveh_eucfinal").is_null())
          .then(pl.col("d_vehiculo_eucl_total_m"))
          .otherwise(pl.col("dveh_eucfinal"))
          .alias("dveh_eucfinal"),
    ])
    
    # Convertir distancias a Float para comparación
    df = df.with_columns([
        pl.col("distancia_ruta").cast(pl.Float64, strict=False).alias("distancia_ruta_float"),
        pl.col("distancia_eucl").cast(pl.Float64, strict=False).alias("distancia_eucl_float"),
    ])
    
    # Filtrar distancias inválidas (null o <= 0)
    df = df.filter(
        pl.col("distancia_ruta_float").is_not_null() &
        (pl.col("distancia_ruta_float") > 0) &
        pl.col("distancia_eucl_float").is_not_null() &
        (pl.col("distancia_eucl_float") > 0) &
        pl.col("dveh_eucfinal").is_not_null() &
        (pl.col("dveh_eucfinal") > 0)
    )
    
    # Eliminar columnas temporales
    columnas_temporales = [
        "distancia_ruta_float", "distancia_eucl_float"
    ]
    columnas_a_eliminar = [col for col in columnas_temporales if col in df.columns]
    if columnas_a_eliminar:
        df = df.drop(columnas_a_eliminar)
    
    n_final = len(df)
    n_filtrados_dist = n_despues_paraderos - n_final
    
    stats = {
        'n_inicial': n_inicial,
        'n_filtrados_tiempo': n_filtrados_tiempo,
        'n_filtrados_paraderos': n_filtrados_paraderos,
        'n_filtrados_dist': n_filtrados_dist,
        'n_final': n_final,
        'pct_retenido': (n_final / n_inicial * 100) if n_inicial > 0 else 0
    }
    
    return df, stats


# ============================================================================
# PROCESAMIENTO DE PARTICIÓN
# ============================================================================

def procesar_particion(particion: Dict, force_reprocess: bool = False, verbose: bool = False) -> Dict:
    """
    Procesa una partición individual.
    Cada worker ejecuta esto en un proceso separado.
    """
    year = particion['year']
    week = particion['week']
    input_file = particion['path']
    
    # Inicializar GCS en cada worker (necesario para multiprocessing)
    try:
        enable_adc_crossplatform()
        gfs = gcsfs.GCSFileSystem(token="google_default")
        fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(gfs))
    except Exception as e:
        return {
            'status': 'error',
            'year': year,
            'week': week,
            'error': f"Error de autenticación GCS: {e}"
        }
    
    # Verificar si ya existe
    output_partition = f"{OUTPUT_PATH}/iso_year={year}/iso_week={week}"
    output_file = f"{output_partition}/data-0.parquet"
    
    if gfs.exists(output_file) and not force_reprocess:
        return {
            'status': 'skipped',
            'year': year,
            'week': week
        }
    
    df = None
    df_filtrado = None
    tabla = None
    
    try:
        if verbose:
            print(f"\n📖 Leyendo {year}-W{week}...")
        
        # Leer partición
        with fs_arrow.open_input_file(input_file) as f:
            tabla = pq.read_table(f)
        df = pl.from_arrow(tabla)
        
        n_rows = len(df)
        if verbose:
            print(f"   ✓ Leídas {n_rows:,} filas")
        
        # Liberar tabla de Arrow inmediatamente
        del tabla
        tabla = None
        gc.collect()
        
        if verbose:
            print(f"   🔧 Aplicando filtros...")
        
        # Aplicar filtros
        df_filtrado, stats = aplicar_filtros(df)
        
        if verbose:
            print(f"   ✓ Retenidos {stats['n_final']:,} viajes ({stats['pct_retenido']:.1f}%)")
        
        # Liberar DataFrame original
        del df
        df = None
        gc.collect()
        
        if verbose:
            print(f"   💾 Guardando...")
        
        # Guardar partición filtrada
        gfs.makedirs(output_partition, exist_ok=True)
        
        with gfs.open(output_file, 'wb') as f:
            df_filtrado.write_parquet(f, compression='snappy')
        
        if verbose:
            print(f"   ✓ Guardado en {output_file}")
        
        # Liberar DataFrame filtrado
        del df_filtrado
        df_filtrado = None
        gc.collect()
        
        return {
            'status': 'success',
            'year': year,
            'week': week,
            'stats': stats
        }
        
    except Exception as e:
        # Liberar memoria en caso de error
        if tabla is not None:
            del tabla
        if df is not None:
            del df
        if df_filtrado is not None:
            del df_filtrado
        gc.collect()
        
        import traceback
        error_detail = traceback.format_exc()
        
        return {
            'status': 'error',
            'year': year,
            'week': week,
            'error': f"{str(e)}\n{error_detail}"
        }


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Función principal de procesamiento en batch"""
    
    print("="*80)
    print("🔄 PROCESAMIENTO EN BATCH - CALIDAD DE DATOS")
    print("="*80)
    print(f"\n⚙️  Configuración:")
    print(f"   - Workers paralelos: {NUM_WORKERS}")
    print(f"   - Forzar reprocesamiento: {FORCE_REPROCESS}")
    print(f"   - Modo detallado: {VERBOSE}")
    print(f"   - Input:  gs://{INPUT_PATH}")
    print(f"   - Output: gs://{OUTPUT_PATH}")
    
    if NUM_WORKERS == 1:
        print(f"\n💡 Nota: Usando 1 worker (secuencial) para evitar problemas de memoria.")
        print(f"   Si no tienes crashes, puedes aumentar NUM_WORKERS a 2-3 para mayor velocidad.")
    
    # Autenticación GCS
    try:
        enable_adc_crossplatform()
        gfs = gcsfs.GCSFileSystem(token="google_default")
        print("\n✅ Conexión con GCS establecida")
    except Exception as e:
        print(f"\n❌ Error de autenticación: {e}")
        return 1
    
    # Listar todas las particiones disponibles
    print("\n🔍 Buscando particiones disponibles...")
    try:
        years_dirs = [d for d in gfs.ls(INPUT_PATH) if 'iso_year=' in d]
        
        particiones = []
        for year_dir in years_dirs:
            year = int(year_dir.split('iso_year=')[1])
            weeks_dirs = [d for d in gfs.ls(year_dir) if 'iso_week=' in d]
            
            for week_dir in weeks_dirs:
                week = int(week_dir.split('iso_week=')[1])
                data_file = f"{week_dir}/data-0.parquet"
                if gfs.exists(data_file):
                    particiones.append({
                        'year': year,
                        'week': week,
                        'path': data_file
                    })
        
        print(f"✅ Se encontraron {len(particiones)} particiones")
        print(f"   Años: {sorted(set(p['year'] for p in particiones))}")
        
    except Exception as e:
        print(f"❌ Error al listar particiones: {e}")
        return 1
    
    if not particiones:
        print("\n⚠️ No se encontraron particiones para procesar")
        return 0
    
    # Iniciar procesamiento paralelo
    print("\n" + "="*80)
    print("🚀 INICIANDO PROCESAMIENTO EN PARALELO")
    print("="*80)
    
    start_time = time.time()
    
    stats_globales = {
        'n_inicial': 0,
        'n_filtrados_tiempo': 0,
        'n_filtrados_paraderos': 0,
        'n_filtrados_dist': 0,
        'n_final': 0,
        'particiones_procesadas': 0,
        'particiones_skipped': 0,
        'particiones_fallidas': 0
    }
    
    # Usar ProcessPoolExecutor para paralelización
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # Enviar todas las particiones al pool
        futures = {
            executor.submit(procesar_particion, p, FORCE_REPROCESS, VERBOSE): p 
            for p in particiones
        }
        
        # Procesar resultados con barra de progreso
        # Si VERBOSE=True, no usar tqdm para evitar conflictos con prints
        if VERBOSE:
            print(f"\n{'='*80}")
            print("📋 Procesando particiones...")
            print(f"{'='*80}")
            for future in as_completed(futures):
                try:
                    resultado = future.result()
                    
                    if resultado['status'] == 'success':
                        stats_globales['particiones_procesadas'] += 1
                        stats = resultado['stats']
                        stats_globales['n_inicial'] += stats['n_inicial']
                        stats_globales['n_filtrados_tiempo'] += stats['n_filtrados_tiempo']
                        stats_globales['n_filtrados_paraderos'] += stats['n_filtrados_paraderos']
                        stats_globales['n_filtrados_dist'] += stats['n_filtrados_dist']
                        stats_globales['n_final'] += stats['n_final']
                        
                    elif resultado['status'] == 'skipped':
                        stats_globales['particiones_skipped'] += 1
                        print(f"⏭️  {resultado['year']}-W{resultado['week']}: ya procesado")
                        
                    elif resultado['status'] == 'error':
                        stats_globales['particiones_fallidas'] += 1
                        print(f"\n❌ Error en {resultado['year']}-W{resultado['week']}:")
                        print(f"   {resultado.get('error', 'Unknown')}")
                        
                except Exception as e:
                    # Capturar errores críticos como BrokenProcessPool
                    stats_globales['particiones_fallidas'] += 1
                    particion = futures[future]
                    print(f"\n💥 Error crítico en {particion['year']}-W{particion['week']}: {type(e).__name__}")
                    print(f"   {str(e)}")
                    if "BrokenProcessPool" in str(type(e)):
                        print(f"   ⚠️  Esto indica falta de memoria. Reduce NUM_WORKERS.")
        else:
            for future in tqdm(as_completed(futures), total=len(particiones), desc="Procesando"):
                try:
                    resultado = future.result()
                    
                    if resultado['status'] == 'success':
                        stats_globales['particiones_procesadas'] += 1
                        stats = resultado['stats']
                        stats_globales['n_inicial'] += stats['n_inicial']
                        stats_globales['n_filtrados_tiempo'] += stats['n_filtrados_tiempo']
                        stats_globales['n_filtrados_paraderos'] += stats['n_filtrados_paraderos']
                        stats_globales['n_filtrados_dist'] += stats['n_filtrados_dist']
                        stats_globales['n_final'] += stats['n_final']
                        
                    elif resultado['status'] == 'skipped':
                        stats_globales['particiones_skipped'] += 1
                        
                    elif resultado['status'] == 'error':
                        stats_globales['particiones_fallidas'] += 1
                        print(f"\n❌ Error en {resultado['year']}-W{resultado['week']}: {resultado.get('error', 'Unknown')}")
                        
                except Exception as e:
                    # Capturar errores críticos como BrokenProcessPool
                    stats_globales['particiones_fallidas'] += 1
                    particion = futures[future]
                    print(f"\n💥 Error crítico en {particion['year']}-W{particion['week']}: {type(e).__name__}")
                    print(f"   {str(e)}")
                    if "BrokenProcessPool" in str(type(e)):
                        print(f"   ⚠️  Esto indica falta de memoria. Reduce NUM_WORKERS.")
    
    elapsed_time = time.time() - start_time
    
    # Mostrar resumen final
    print("\n" + "="*80)
    print("📊 RESUMEN FINAL DEL PROCESAMIENTO")
    print("="*80)
    print(f"\n⏱️  Tiempo total: {elapsed_time/60:.2f} minutos ({elapsed_time:.1f} segundos)")
    print(f"   Velocidad promedio: {elapsed_time/len(particiones):.1f} seg/partición")
    
    print(f"\n📦 Particiones:")
    print(f"   - Total: {len(particiones)}")
    print(f"   - Procesadas exitosamente: {stats_globales['particiones_procesadas']}")
    print(f"   - Skipped (ya existían): {stats_globales['particiones_skipped']}")
    print(f"   - Fallidas: {stats_globales['particiones_fallidas']}")
    
    if stats_globales['n_inicial'] > 0:
        print(f"\n📈 Viajes totales (de particiones procesadas):")
        print(f"   - Iniciales: {stats_globales['n_inicial']:,}")
        print(f"   - Finales: {stats_globales['n_final']:,}")
        print(f"   - Retenidos: {stats_globales['n_final']/stats_globales['n_inicial']*100:.2f}%")
        
        print(f"\n🗑️ Filtrados:")
        print(f"   - Por tiempos: {stats_globales['n_filtrados_tiempo']:,} ({stats_globales['n_filtrados_tiempo']/stats_globales['n_inicial']*100:.2f}%)")
        print(f"   - Por paraderos: {stats_globales['n_filtrados_paraderos']:,} ({stats_globales['n_filtrados_paraderos']/stats_globales['n_inicial']*100:.2f}%)")
        print(f"   - Por distancias: {stats_globales['n_filtrados_dist']:,} ({stats_globales['n_filtrados_dist']/stats_globales['n_inicial']*100:.2f}%)")
    
    print(f"\n💾 Ubicación de salida:")
    print(f"   gs://{OUTPUT_PATH}/iso_year=YYYY/iso_week=WW/data-0.parquet")
    
    print("\n" + "="*80)
    if stats_globales['particiones_fallidas'] == 0:
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
    else:
        print("⚠️ PROCESAMIENTO COMPLETADO CON ERRORES")
    print("="*80)
    
    return 0 if stats_globales['particiones_fallidas'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

