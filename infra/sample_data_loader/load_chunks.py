"""
load_chunks.py — Chunk source files and upload to S3 for Snowpipe demo.

Usage:
    python load_chunks.py --source trips --file yellow_tripdata_2024-01.parquet --chunks 4
    python load_chunks.py --source weather --file lcd_lga_2024_01.csv --chunks 4

    # Drop a specific chunk (simulate "week 2 arrives"):
    python load_chunks.py --source trips --file yellow_tripdata_2024-01.parquet --chunks 4 --drop 2

The script splits the source file into N roughly equal chunks and uploads them
to S3. Snowpipe picks them up automatically via S3 event notifications.

Data sources:
    TLC Yellow Taxi: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
    NOAA LCD:        https://www.ncei.noaa.gov/cdo-web/  (select "Local Climatological Data")
                     Station: LaGuardia (USW00014732)

Requirements: pip install boto3 pandas pyarrow
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Optional

import boto3
import pandas as pd

# ─── Config ───────────────────────────────────────────────────────────────────
# Override via environment variables or edit directly.

S3_BUCKET = os.environ.get("POC_S3_BUCKET", "<your-bucket>")
S3_TRIPS_PREFIX = os.environ.get("POC_S3_TRIPS_PREFIX", "trips/")
S3_WEATHER_PREFIX = os.environ.get("POC_S3_WEATHER_PREFIX", "weather/")
AWS_PROFILE = os.environ.get("AWS_PROFILE", None)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _s3_client():
    session = boto3.Session(profile_name=AWS_PROFILE) if AWS_PROFILE else boto3.Session()
    return session.client("s3")


def _upload_parquet(client, df: pd.DataFrame, bucket: str, key: str) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow", compression="snappy")
    buf.seek(0)
    client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    print(f"  uploaded s3://{bucket}/{key}  ({len(df):,} rows)")


def _upload_csv(client, df: pd.DataFrame, bucket: str, key: str) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    client.put_object(Bucket=bucket, Key=key, Body=buf.getvalue().encode("utf-8"))
    print(f"  uploaded s3://{bucket}/{key}  ({len(df):,} rows)")


def _split(df: pd.DataFrame, n_chunks: int) -> list[pd.DataFrame]:
    chunk_size = max(1, len(df) // n_chunks)
    return [df.iloc[i : i + chunk_size] for i in range(0, len(df), chunk_size)][:n_chunks]


# ─── Source-specific loaders ─────────────────────────────────────────────────

def load_trips(file_path: str, n_chunks: int, drop_only: Optional[int]) -> None:
    print(f"Reading TLC Parquet: {file_path}")
    df = pd.read_parquet(file_path)
    print(f"  {len(df):,} total rows → splitting into {n_chunks} chunks")

    chunks = _split(df, n_chunks)
    stem = Path(file_path).stem
    client = _s3_client()

    for i, chunk in enumerate(chunks, start=1):
        if drop_only is not None and i != drop_only:
            print(f"  chunk {i:02d}: skipped (--drop {drop_only})")
            continue
        key = f"{S3_TRIPS_PREFIX}{stem}_chunk_{i:02d}.parquet"
        _upload_parquet(client, chunk, S3_BUCKET, key)


def load_weather(file_path: str, n_chunks: int, drop_only: Optional[int]) -> None:
    print(f"Reading NOAA LCD CSV: {file_path}")
    df = pd.read_csv(file_path, low_memory=False)
    print(f"  {len(df):,} total rows → splitting into {n_chunks} chunks")

    chunks = _split(df, n_chunks)
    stem = Path(file_path).stem
    client = _s3_client()

    for i, chunk in enumerate(chunks, start=1):
        if drop_only is not None and i != drop_only:
            print(f"  chunk {i:02d}: skipped (--drop {drop_only})")
            continue
        key = f"{S3_WEATHER_PREFIX}{stem}_chunk_{i:02d}.csv"
        _upload_csv(client, chunk, S3_BUCKET, key)


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk a source file and upload to S3 for Snowpipe ingestion."
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=["trips", "weather"],
        help="Data source type.",
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to the downloaded source file.",
    )
    parser.add_argument(
        "--chunks",
        type=int,
        default=4,
        help="Number of chunks to split the file into (default: 4).",
    )
    parser.add_argument(
        "--drop",
        type=int,
        default=None,
        metavar="N",
        help="Upload only chunk N (1-indexed). Omit to upload all chunks.",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help=f"S3 bucket name. Defaults to POC_S3_BUCKET env var or '{S3_BUCKET}'.",
    )

    args = parser.parse_args()

    if args.bucket:
        global S3_BUCKET
        S3_BUCKET = args.bucket

    if S3_BUCKET == "<your-bucket>":
        sys.exit("Error: set POC_S3_BUCKET env var or pass --bucket <bucket-name>")

    if not Path(args.file).exists():
        sys.exit(f"Error: file not found: {args.file}")

    print(f"Bucket: s3://{S3_BUCKET}")

    if args.source == "trips":
        load_trips(args.file, args.chunks, args.drop)
    else:
        load_weather(args.file, args.chunks, args.drop)

    print("Done.")


if __name__ == "__main__":
    main()
