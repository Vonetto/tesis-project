# lib/datalake.py
import os, pathlib, sys, re
import polars as pl
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import gcsfs
import pyarrow as pa
import duckdb # Importar duckdb

# Importar constantes desde config
from config.constants import USE_LOCAL_PATHS

def enable_adc():
    if USE_LOCAL_PATHS:
        return # ADC not needed for local paths
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        return
    adc = (pathlib.Path.home()/".config"/"gcloud"/"application_default_credentials.json")
    if not adc.exists():
        raise FileNotFoundError("Run: gcloud auth application-default login")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(adc)

def scan_parquet_portable(base_or_glob: str, token="google_default") -> pl.LazyFrame:
    if USE_LOCAL_PATHS:
        # Local file system with DuckDB
        # DuckDB can handle glob patterns directly
        # It also automatically detects hive partitioning
        try:
            # Use a temporary in-memory DuckDB connection
            con = duckdb.connect(database=':memory:', read_only=False)
            # Scan the parquet files using SQL, then convert to Polars LazyFrame
            # DuckDB's read_parquet handles globs and hive partitioning
            return con.execute(f"SELECT * FROM read_parquet('{base_or_glob}', HIVE_PARTITIONING=TRUE)").pl().lazy()
        except Exception as e:
            raise Exception(f"Error reading local parquet with DuckDB: {e}")
    else:
        # GCS file system with PyArrow
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
