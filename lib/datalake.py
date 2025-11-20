# lib/datalake.py
import os
import pathlib
import glob
import polars as pl
import gcsfs
from functools import lru_cache

# Importar constantes desde config
from config.constants import USE_LOCAL_PATHS

@lru_cache(maxsize=1)
def get_filesystem():
    """
    Initializes and returns the GCS filesystem object.
    Caches the result to avoid re-authentication.
    Returns None if USE_LOCAL_PATHS is True.
    """
    if USE_LOCAL_PATHS:
        return None
    
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        adc = pathlib.Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
        if not adc.exists():
            raise FileNotFoundError("GCS credentials not found. Run: gcloud auth application-default login")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(adc)
        
    return gcsfs.GCSFileSystem()

def read_parquet_portable(path_or_glob: str, **kwargs) -> pl.LazyFrame:
    """
    Scans a Parquet file or dataset from a local or GCS path.
    
    Filters out macOS metadata files (starting with ._) that can cause errors.
    
    Args:
        path_or_glob: Path or glob pattern to the Parquet file(s).
        **kwargs: Additional arguments passed to polars.scan_parquet.
    
    Returns:
        A Polars LazyFrame.
    """
    if USE_LOCAL_PATHS:
        # Expand glob pattern and filter out macOS metadata files
        if '*' in path_or_glob or '?' in path_or_glob:
            matched_files = glob.glob(path_or_glob)
            # Filter out macOS metadata files (._*)
            valid_files = [f for f in matched_files if not os.path.basename(f).startswith('._')]
            if not valid_files:
                raise FileNotFoundError(f"No valid parquet files found matching pattern: {path_or_glob}")
            # If only one file, pass it directly; otherwise pass the list
            if len(valid_files) == 1:
                return pl.scan_parquet(valid_files[0], **kwargs)
            else:
                return pl.scan_parquet(valid_files, **kwargs)
        else:
            # Single file path, check if it's a metadata file
            if os.path.basename(path_or_glob).startswith('._'):
                raise ValueError(f"File appears to be a macOS metadata file: {path_or_glob}")
            return pl.scan_parquet(path_or_glob, **kwargs)
    else:
        # For GCS, Polars can handle glob patterns directly
        # GCS doesn't have macOS metadata files, so we can pass the glob as-is
        return pl.scan_parquet(path_or_glob, **kwargs)

def read_csv_portable(path: str, **kwargs) -> pl.DataFrame:
    """
    Reads a CSV file from a local or GCS path.

    Args:
        path: Path to the CSV file.
        **kwargs: Additional arguments passed to polars.read_csv.

    Returns:
        A Polars DataFrame.
    """
    if USE_LOCAL_PATHS:
        return pl.read_csv(path, **kwargs)
    else:
        fs = get_filesystem()
        with fs.open(path, "rb") as f:
            return pl.read_csv(f, **kwargs)

def scan_csv_portable(path: str, **kwargs) -> pl.LazyFrame:

    """

    Scans a CSV file from a local or GCS path.



    Args:

        path: Path to the CSV file.

        **kwargs: Additional arguments passed to polars.scan_csv.



    Returns:

        A Polars LazyFrame.

    """

    # Polars' scan_csv can handle both local paths and GCS paths (if gcsfs is installed and path starts with gs://)

    return pl.scan_csv(path, **kwargs)



def read_shapefile_portable(path: str, **kwargs):

    """

    (Not Implemented) Reads a shapefile from a local or GCS path.

    """

    raise NotImplementedError("Shapefile reading is not implemented in this refactoring phase.")
