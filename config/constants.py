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
# Futuras constantes compartidas pueden agregarse aquí (p. ej. rutas GCS,
# parámetros de particiones, seeds, etc.).
# ---------------------------------------------------------------------------


