"""Build weighted Metro graphs from GTFS snapshots.

Core goals:
1) Derive travel-time weights from `stop_times.txt` (official Metro GTFS).
2) Add configurable transfer penalties (minutes) for line changes within a station.
3) Produce a NetworkX graph ready for Dijkstra that reflects realistic travel time.

This module is intentionally light on notebook dependencies so it can be reused
from notebooks or scripts (e.g., transbordo correction, wait-time recalculation).
"""

from __future__ import annotations

import datetime as dt
from itertools import combinations
from pathlib import Path
from typing import Optional, Tuple

import networkx as nx
import polars as pl

from lib.gtfs_manifest import GtfsVersion


# --------------------------
# Normalización de estaciones
# --------------------------
def normalize_station_name(name: str) -> str:
    """Normalize stop/station names to a canonical uppercase form.

    Mirrors the rules used previously in notebooks so node naming stays consistent.
    """
    import re
    import unicodedata

    if not isinstance(name, str):
        return ""

    base_name = re.sub(r" (L\d[A]?)$", "", name.strip())
    upper_name = base_name.upper()
    no_tildes = "".join(
        c for c in unicodedata.normalize("NFD", upper_name) if unicodedata.category(c) != "Mn"
    )
    text = no_tildes
    # Normalizar abreviaturas de Unión Latino Americana
    text = re.sub(r"\bU\s*\.?\s*L\s*\.?\s*A\b", "U L A", text)
    text = re.sub(r"\bUNION LATINO ?AMERICANA\b", "U L A", text)
    text = text.replace("RONDIZONNI", "RONDIZZONI")
    text = text.replace("PLAZA MAIPU", "PLAZA DE MAIPU")
    text = text.replace("UNION LATINO AMERICANA", "U L A")
    text = text.replace("U.L.A.", "U L A")
    text = text.replace("PDTE. PEDRO AGUIPRRE CERDA", "PDTE PEDRO AGUIRRE CERDA")
    text = re.sub(r"-", " ", text)
    text = re.sub(r"[.'’]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if re.search(r"\bCAL Y CANTO\b", text) and not re.search(r"\bPUENTE\b", text):
        text = re.sub(r"\bCAL Y CANTO\b", "PUENTE CAL Y CANTO", text)
    text = re.sub(r"\bCHILEESPANA\b", "CHILE ESPANA", text)
    return text


# ----------------------
# Viaje en stop_times    
# ----------------------
def compute_travel_times(gtfs_dir: Path) -> pl.DataFrame:
    """Compute average in-vehicle travel time (seconds) between consecutive stops.

    Returns a Polars DataFrame with columns:
        from_stop_id, to_stop_id, from_stop_name, to_stop_name,
        line, avg_travel_secs
    """

    # Load core tables
    routes = pl.read_csv(
        gtfs_dir / "routes.txt",
        schema_overrides={"route_id": pl.Utf8, "route_short_name": pl.Utf8, "route_type": pl.Int8},
    ).filter(pl.col("route_type") == 1)  # only Metro

    trips = pl.read_csv(
        gtfs_dir / "trips.txt", schema_overrides={"route_id": pl.Utf8, "trip_id": pl.Utf8}
    )

    stop_times = pl.read_csv(
        gtfs_dir / "stop_times.txt",
        schema_overrides={"trip_id": pl.Utf8, "stop_id": pl.Utf8, "stop_sequence": pl.Int32},
    ).with_columns(
        pl.col("arrival_time").str.to_time("%H:%M:%S").alias("arr_t"),
        pl.col("departure_time").str.to_time("%H:%M:%S").alias("dep_t"),
    )

    stops = pl.read_csv(gtfs_dir / "stops.txt", schema_overrides={"stop_id": pl.Utf8, "stop_name": pl.Utf8})

    metro_trips = trips.join(routes, on="route_id", how="inner")
    st_metro = stop_times.join(metro_trips, on="trip_id", how="inner")

    # Compute leg times within each trip
    df_travel = (
        st_metro.sort(["trip_id", "stop_sequence"])
        .group_by("trip_id")
        .map_groups(
            lambda group: group.with_columns(
                pl.col("stop_id").shift(-1).alias("to_stop_id"),
                (pl.col("arr_t").shift(-1) - pl.col("dep_t")).dt.total_seconds().alias("travel_secs"),
            )
        )
        .filter(pl.col("to_stop_id").is_not_null() & (pl.col("travel_secs") > 0))
    )

    # Aggregate average per leg and line
    df_edges = (
        df_travel.group_by(["stop_id", "to_stop_id", "route_short_name"])
        .agg(pl.col("travel_secs").mean().alias("avg_travel_secs"))
        .rename({"stop_id": "from_stop_id", "route_short_name": "line"})
    )

    # Attach stop names (for readability / normalization)
    df_edges = df_edges.join(stops.rename({"stop_id": "from_stop_id", "stop_name": "from_stop_name"}), on="from_stop_id", how="left")
    df_edges = df_edges.join(stops.rename({"stop_id": "to_stop_id", "stop_name": "to_stop_name"}), on="to_stop_id", how="left")

    return df_edges


def _clean_stop_name(name: str) -> str:
    """Remove direction suffixes before normalizing."""
    import re
    if not isinstance(name, str):
        return ""
    name = re.sub(r"\s+DIRECCI[OÓ]N\s+.+$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+DIR\s+.+$", "", name, flags=re.IGNORECASE)
    return name.strip()


# ----------------------
# Construcción de grafo
# ----------------------
def build_weighted_graph(
    df_edges: pl.DataFrame,
    transfer_penalty_min: float = 5.86,
) -> nx.Graph:
    """Build weighted graph with tuple nodes (station, line) and typed edges."""

    G = nx.Graph()

    # Aristas de viaje dentro de cada línea
    for row in df_edges.iter_rows(named=True):
        from_norm = normalize_station_name(_clean_stop_name(row["from_stop_name"] or row["from_stop_id"]))
        to_norm = normalize_station_name(_clean_stop_name(row["to_stop_name"] or row["to_stop_id"]))
        line = (row.get("line") or "").strip().upper()
        if not from_norm or not to_norm or not line:
            continue
        u = (from_norm, line)
        v = (to_norm, line)
        weight_min = (row["avg_travel_secs"] or 0) / 60.0
        if weight_min <= 0:
            continue
        G.add_edge(u, v, type="travel", line=line, weight=weight_min)

    # Aristas de transferencia entre copias de una estación (distintas líneas)
    station_to_nodes = {}
    for station, line in G.nodes:
        station_to_nodes.setdefault(station, []).append((station, line))

    for nodes in station_to_nodes.values():
        if len(nodes) < 2:
            continue
        for a, b in combinations(nodes, 2):
            G.add_edge(a, b, type="transfer", weight=transfer_penalty_min)

    return G


def shortest_path_with_line(G: nx.Graph, origen: str, linea_origen: str, destino: str):
    """Dijkstra en el grafo tuple-node respetando la línea inicial.

    origen, destino: nombres de estación (raw); linea_origen: ej. "L1".
    Devuelve (distancia_min, path_nodes) o (None, None) si no hay ruta.
    """
    o_station = normalize_station_name(_clean_stop_name(origen))
    d_station = normalize_station_name(_clean_stop_name(destino))
    line_init = (linea_origen or "").strip().upper()

    start_nodes = [(o_station, line_init)] if (o_station, line_init) in G else []
    if not start_nodes:
        return None, None

    dest_nodes = [n for n in G.nodes if n[0] == d_station]
    if not dest_nodes:
        return None, None

    best = None
    best_path = None
    for s in start_nodes:
        for d in dest_nodes:
            try:
                dist = nx.shortest_path_length(G, s, d, weight='weight')
                if best is None or dist < best:
                    best = dist
                    best_path = nx.shortest_path(G, s, d, weight='weight')
            except nx.NetworkXNoPath:
                continue
    return best, best_path


def build_graph_for_version(
    version: GtfsVersion,
    transfer_penalty_min: float = 5.86,
) -> Tuple[nx.Graph, pl.DataFrame]:
    """Build graph and return also the edge table used.

    Returns (graph, edge_table)
    """

    df_edges = compute_travel_times(version.path)
    G = build_weighted_graph(df_edges, transfer_penalty_min=transfer_penalty_min)
    return G, df_edges
