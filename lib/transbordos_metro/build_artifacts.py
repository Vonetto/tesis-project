"""Generate weighted Metro graphs per GTFS version and persist artifacts.

Outputs (per GTFS snapshot):
  - metro_graph_<folder>.gpickle : weighted NetworkX graph (minutes)
  - metro_edges_<folder>.parquet : edge table with avg travel secs and names

Usage:
  python -m lib.transbordos_metro.build_artifacts \
      --gtfs-root config/GTFS \
      --output-dir 01_processing/metro_graphs \
      --transfer-penalty 5.86
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pickle

import polars as pl

from lib.gtfs_manifest import build_manifest
from lib.transbordos_metro.metro_graph_builder import build_graph_for_version


def generate_all(
    gtfs_root: Path,
    output_dir: Path,
    transfer_penalty_min: float,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(gtfs_root)
    if not manifest:
        raise FileNotFoundError(f"No GTFS folders found under {gtfs_root}")

    summary_rows = []
    for version in manifest:
        print(f"➡️  Building graph for {version.folder} (valid {version.valid_from} → {version.valid_to})")
        G, edges = build_graph_for_version(version, transfer_penalty_min=transfer_penalty_min)

        graph_path = output_dir / f"metro_graph_{version.folder}.gpickle"
        edges_path = output_dir / f"metro_edges_{version.folder}.parquet"

        with open(graph_path, "wb") as f:
            pickle.dump(G, f)
        edges.write_parquet(edges_path)

        summary_rows.append(
            {
                "folder": version.folder,
                "feed_version": version.feed_version,
                "valid_from": version.valid_from,
                "valid_to": version.valid_to,
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "edges_path": str(edges_path),
                "graph_path": str(graph_path),
            }
        )

        print(f"   ✅ Saved graph: {graph_path.name} ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
        print(f"   ✅ Saved edges: {edges_path.name} ({len(edges)} rows)")

    summary = pl.DataFrame(summary_rows)
    summary_path = output_dir / "manifest_graphs.parquet"
    summary.write_parquet(summary_path)
    print(f"📄 Summary written to {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="Build weighted Metro graphs per GTFS version")
    parser.add_argument("--gtfs-root", default="config/GTFS", help="Root folder containing GTFS_* snapshots")
    parser.add_argument(
        "--output-dir",
        default="01_processing/metro_graphs",
        help="Directory to store generated graphs and edge tables",
    )
    parser.add_argument(
        "--transfer-penalty",
        type=float,
        default=5.86,
        help="Transfer penalty in minutes to apply to transfer edges",
    )

    args = parser.parse_args()
    generate_all(Path(args.gtfs_root), Path(args.output_dir), transfer_penalty_min=args.transfer_penalty)


if __name__ == "__main__":
    main()

