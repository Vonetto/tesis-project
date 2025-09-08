# lib/datalake.py
import os, pathlib, sys, re
import polars as pl
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import gcsfs
import pyarrow as pa

def enable_adc():
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    adc = (pathlib.Path.home()/".config"/"gcloud"/"application_default_credentials.json")
    if not adc.exists():
        raise FileNotFoundError("Run: gcloud auth application-default login")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(adc)

def scan_parquet_portable(base_or_glob: str, token="google_default") -> pl.LazyFrame:
    gfs = gcsfs.GCSFileSystem(token=token)
    fs_arrow = pafs.PyFileSystem(pafs.FSSpecHandler(gfs))
    part_schema = pa.schema([pa.field("iso_year", pa.int32()),
                             pa.field("iso_week", pa.int32())])

    is_glob = any(ch in base_or_glob for ch in "*?[")
    if is_glob:
        pattern = re.sub(r"^gs://","",base_or_glob).rstrip("/")
        paths = gfs.glob(pattern)
        if not paths: raise FileNotFoundError(f"No objects: {base_or_glob}")
        is_hive = any("iso_year=" in p for p in paths)
        part = (ds.HivePartitioning.discover(schema=part_schema)
                if is_hive else ds.DirectoryPartitioning.discover(field_names=["iso_year","iso_week"]))
        dset = ds.dataset(paths, filesystem=fs_arrow, format="parquet", partitioning=part)
        return pl.scan_pyarrow_dataset(dset)

    base_no = re.sub(r"^gs://","",base_or_glob).rstrip("/")
    # detect layout
    is_hive = any("/iso_year=" in p for p in gfs.ls(base_no))
    part = (ds.HivePartitioning.discover(schema=part_schema)
            if is_hive else ds.DirectoryPartitioning.discover(field_names=["iso_year","iso_week"]))
    dset = ds.dataset(base_no, filesystem=fs_arrow, format="parquet", partitioning=part)
    return pl.scan_pyarrow_dataset(dset)
