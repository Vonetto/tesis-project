"""
Centralized configuration values used across notebooks and scripts.

This module is intended to avoid duplicated global definitions scattered
throughout multiple Quarto notebooks. Import the constants you need from
``config`` instead of redefining them.
"""

from typing import Final, List

# ---------------------------------------------------------------------------
# Horarios relevantes para los análisis de demanda y transbordos.
# ---------------------------------------------------------------------------
HORAS_PUNTA_MANANA: Final[List[int]] = [6, 7, 8]
HORAS_PUNTA_TARDE: Final[List[int]] = [18, 19]

# Bloques adicionales utilizados en notebooks de transbordos y tiempos de espera
HORAS_VALLE: Final[List[int]] = [9, 10, 11, 12, 13, 14, 15, 16, 17, 20]
HORAS_BAJO: Final[List[int]] = [21, 22, 23]

# ---------------------------------------------------------------------------
# Rutas GCS para el Data Lake
# ---------------------------------------------------------------------------
GCS_BUCKET_NAME: Final[str] = "tesis-vonetto-datalake"
GCS_RAW_PREFIX: Final[str] = "raw"
GCS_BRONZE_PREFIX: Final[str] = "lake/bronze"
GCS_SILVER_PREFIX: Final[str] = "lake/silver"
GCS_GOLD_PREFIX: Final[str] = "lake/gold"

# Rutas completas GCS
GCS_RAW_PATH: Final[str] = f"gs://{GCS_BUCKET_NAME}/{GCS_RAW_PREFIX}"
GCS_BRONZE_PATH: Final[str] = f"gs://{GCS_BUCKET_NAME}/{GCS_BRONZE_PREFIX}"
GCS_SILVER_PATH: Final[str] = f"gs://{GCS_BUCKET_NAME}/{GCS_SILVER_PREFIX}"
GCS_GOLD_PATH: Final[str] = f"gs://{GCS_BUCKET_NAME}/{GCS_GOLD_PREFIX}"

# ---------------------------------------------------------------------------
# Configuración de Rutas Locales
# ---------------------------------------------------------------------------
# Cambiar a True para usar rutas locales en lugar de GCS
USE_LOCAL_PATHS: Final[bool] = False

# Ruta base del proyecto local (ej. "D:/tesis-project" en Windows, "/Users/user/tesis-project" en Mac/Linux)
# ¡IMPORTANTE: AJUSTAR ESTA RUTA EN EL PC CON WINDOWS!
BASE_LOCAL_PATH: Final[str] = "/Volumes/TOSHIBA EXT/Vicente/tesis-project"

# Rutas locales para el Data Lake
LOCAL_RAW_PATH: Final[str] = f"{BASE_LOCAL_PATH}/raw"
LOCAL_BRONZE_PATH: Final[str] = f"{BASE_LOCAL_PATH}/lake/bronze"
LOCAL_SILVER_PATH: Final[str] = f"{BASE_LOCAL_PATH}/lake/silver"
LOCAL_GOLD_PATH: Final[str] = f"{BASE_LOCAL_PATH}/lake/gold"

# ---------------------------------------------------------------------------
# Futuras constantes compartidas pueden agregarse aquí (p. ej. rutas GCS,
# parámetros de particiones, seeds, etc.).
# ---------------------------------------------------------------------------


