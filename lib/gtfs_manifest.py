"""Utilities to build a date-aware manifest of available GTFS snapshots.

This module scans `config/GTFS/GTFS_*` folders, reads their `feed_info.txt`,
and produces a manifest with validity ranges. It also exposes a helper to pick
the correct GTFS folder for a given service date.

Why: Metro travel times and headways can change between GTFS versions. When we
reconstruct routes or run Dijkstra, we want to use the snapshot that was valid
on the date of the trip. A manifest gives us that lookup in O(1).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import polars as pl


GTFS_FOLDER_PREFIX = "GTFS_"
FEED_INFO_FILE = "feed_info.txt"


@dataclass(frozen=True)
class GtfsVersion:
    folder: str              # e.g., "GTFS_20250412"
    path: Path               # absolute path to the folder
    valid_from: dt.date
    original_valid_to: dt.date
    feed_version: str
    valid_to: dt.date        # adjusted end date (day before next start)


def _parse_feed_info(path: Path) -> Optional[dict]:
    """Read feed_info.txt into a dict; return None if missing/invalid."""
    if not path.exists():
        return None
    try:
        df = pl.read_csv(path)
        row = df.row(0, named=True)
        return {
            "feed_publisher_name": row.get("feed_publisher_name"),
            "feed_start_date": row.get("feed_start_date"),
            "feed_end_date": row.get("feed_end_date"),
            "feed_version": row.get("feed_version"),
        }
    except Exception:
        return None


def build_manifest(gtfs_root: Path | str = "config/GTFS") -> List[GtfsVersion]:
    """Scan GTFS folders and build a list of `GtfsVersion` with date ranges.

    - valid_from: feed_start_date
    - valid_to: day before the next valid_from; last version keeps its feed_end_date
    """

    root = Path(gtfs_root)
    folders = sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith(GTFS_FOLDER_PREFIX))

    rows = []
    for folder in folders:
        meta = _parse_feed_info(folder / FEED_INFO_FILE)
        if not meta:
            continue
        try:
            start = dt.datetime.strptime(str(meta["feed_start_date"]), "%Y%m%d").date()
            end = dt.datetime.strptime(str(meta["feed_end_date"]), "%Y%m%d").date()
        except Exception:
            continue
        rows.append(
            {
                "folder": folder.name,
                "path": folder.resolve(),
                "valid_from": start,
                "original_valid_to": end,
                "feed_version": meta.get("feed_version", ""),
            }
        )

    if not rows:
        return []

    # Sort by start date and adjust valid_to as day before the next start
    df = pl.DataFrame(rows).sort("valid_from")
    df = df.with_columns(
        pl.col("valid_from").shift(-1).alias("next_start")
    ).with_columns(
        pl.when(pl.col("next_start").is_not_null())
        .then(pl.col("next_start") - pl.duration(days=1))
        .otherwise(pl.col("original_valid_to"))
        .alias("valid_to")
    )

    manifest: List[GtfsVersion] = []
    for row in df.to_dicts():
        manifest.append(
            GtfsVersion(
                folder=row["folder"],
                path=Path(row["path"]),
                valid_from=row["valid_from"],
                original_valid_to=row["original_valid_to"],
                feed_version=row["feed_version"],
                valid_to=row["valid_to"],
            )
        )
    return manifest


def pick_version_for_date(target_date: dt.date, manifest: Iterable[GtfsVersion]) -> Optional[GtfsVersion]:
    """Return the GTFS version whose validity window contains target_date."""
    for gtfs in manifest:
        if gtfs.valid_from <= target_date <= gtfs.valid_to:
            return gtfs
    return None


def manifest_as_df(manifest: Iterable[GtfsVersion]) -> pl.DataFrame:
    """Convenience: manifest to Polars DataFrame."""
    return pl.DataFrame([
        {
            "folder": m.folder,
            "path": str(m.path),
            "valid_from": m.valid_from,
            "valid_to": m.valid_to,
            "feed_version": m.feed_version,
            "original_valid_to": m.original_valid_to,
        }
        for m in manifest
    ])

