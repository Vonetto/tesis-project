# lib/inspect_schema.py

import polars as pl
from pathlib import Path
import sys
from collections import defaultdict

# La ruta base donde se guardan los datos finales
BASE_PATH = "/Volumes/KINGSTON/tesis-project/lake/silver/viajes_filtrados"

def update_global_stats(df: pl.DataFrame, global_stats: dict):
    """Actualiza las estadísticas globales (min/max) con los datos de un DataFrame."""
    for col, dtype in df.schema.items():
        if dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64, pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64]:
            # Ignorar columnas con solo nulos
            if df[col].null_count() == len(df):
                continue
            
            col_min = df[col].min()
            col_max = df[col].max()
            
            if col not in global_stats:
                global_stats[col] = {'min': col_min, 'max': col_max}
            else:
                if col_min < global_stats[col]['min']:
                    global_stats[col]['min'] = col_min
                if col_max > global_stats[col]['max']:
                    global_stats[col]['max'] = col_max
    return global_stats

def generate_final_report(df_sample: pl.DataFrame, global_stats: dict):
    """Genera e imprime el informe final de optimización basado en estadísticas globales."""
    print("\n" + "="*83)
    print("✅ ANÁLISIS GLOBAL COMPLETADO")
    print("="*83)
    print("\n--- ESQUEMA REPRESENTATIVO (basado en el último archivo leído) ---")
    
    type_to_bytes = {
        pl.Int8: 1, pl.Int16: 2, pl.Int32: 4, pl.Int64: 8,
        pl.UInt8: 1, pl.UInt16: 2, pl.UInt32: 4, pl.UInt64: 8,
        pl.Float32: 4, pl.Float64: 8, pl.Boolean: 1,
        pl.Date: 4, pl.Datetime: 8, pl.Duration: 8, pl.Categorical: 4
    }
    total_bytes_actual = sum(type_to_bytes.get(dtype, 8) for dtype in df_sample.schema.values())
    
    print(f"{'Columna':<40} {'Tipo de Dato Actual':<20}")
    print(f"{'-'*40} {'-'*20}")
    for col, dtype in df_sample.schema.items():
        print(f"{col:<40} {str(dtype):<20}")
    print("-" * 63)
    print(f"Total estimado por fila (sin compresión de texto): {total_bytes_actual} bytes")
    
    print("\n--- SUGERENCIAS DE OPTIMIZACIÓN (basadas en el rango global de datos) ---")
    sugerencias = []
    
    for col, dtype in df_sample.schema.items():
        nuevo_tipo = str(dtype)
        if dtype in [pl.Int8, pl.Int16, pl.Int32, pl.Int64]:
            stats = global_stats.get(col)
            if stats:
                min_val, max_val = stats['min'], stats['max']
                if -128 <= min_val and max_val <= 127: nuevo_tipo = "Int8"
                elif -32768 <= min_val and max_val <= 32767: nuevo_tipo = "Int16"
                elif -2147483648 <= min_val and max_val <= 2147483647: nuevo_tipo = "Int32"
                else: nuevo_tipo = "Int64"
        elif dtype == pl.Float64:
            nuevo_tipo = "Float32"
        elif dtype == pl.Utf8:
            n_unique = df_sample[col].n_unique()
            if len(df_sample) > 0 and n_unique / len(df_sample) < 0.5 and n_unique > 1:
                nuevo_tipo = "Categorical"
        sugerencias.append((col, str(dtype), nuevo_tipo))

    print(f"\n{'Columna':<40} {'Tipo Actual':<20} {'Tipo Sugerido (Seguro)':<25}")
    print(f"{'-'*40} {'-'*20} {'-'*25}")

    total_bytes_sugerido = 0
    type_map_sugerido = {'Int8': 1, 'Int16': 2, 'Int32': 4, 'Int64': 8, 'Float32': 4, 'Float64': 8, 'Categorical': 4, 'Utf8': 8, 'Date': 4, 'Datetime': 8, 'Boolean': 1, 'UInt64': 8}
    
    for col, tipo_actual, nuevo_tipo in sugerencias:
        print(f"{col:<40} {tipo_actual:<20} {nuevo_tipo:<25}")
        bytes_nuevos = type_to_bytes.get(df_sample.schema[col], 8) # Default to actual bytes
        for k, v in type_map_sugerido.items():
            if k == nuevo_tipo:
                bytes_nuevos = v
                break
        total_bytes_sugerido += bytes_nuevos

    print("-" * 88)
    print(f"\n--- ESTIMACIÓN DE AHORRO ---")
    print(f"Tamaño actual estimado por fila:    {total_bytes_actual} bytes")
    print(f"Tamaño optimizado estimado por fila: {total_bytes_sugerido} bytes")
    ahorro = ((total_bytes_actual - total_bytes_sugerido) / total_bytes_actual) * 100 if total_bytes_actual > 0 else 0
    print(f"Ahorro de espacio estimado:         ~{ahorro:.1f}%")

def main():
    """Función principal para encontrar y analizar todos los archivos."""
    try:
        # Ignorar archivos ocultos de macOS (._) y archivos vacíos
        all_files = [
            p for p in Path(BASE_PATH).rglob("*.parquet") 
            if p.stat().st_size > 0 and not p.name.startswith('._')
        ]
        if not all_files:
            print(f"❌ No se encontraron archivos .parquet válidos en la ruta: {BASE_PATH}")
            sys.exit(1)
            
        print(f"🔍 Encontrados {len(all_files)} archivos Parquet válidos. Analizando rangos globales...")
        
        global_stats = {}
        df_sample = None
        
        for i, file_path in enumerate(all_files):
            print(f"  -> Procesando archivo {i+1}/{len(all_files)}: {file_path.name}")
            try:
                df = pl.read_parquet(file_path)
                update_global_stats(df, global_stats)
                df_sample = df # Guardar el último df como muestra para el esquema
            except Exception as e:
                print(f"⚠️  No se pudo leer o procesar {file_path.name}: {e}")
                continue
        
        if df_sample is None:
            print(f"❌ No se pudo leer ningún archivo Parquet para generar el informe.")
            sys.exit(1)

        generate_final_report(df_sample, global_stats)

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
