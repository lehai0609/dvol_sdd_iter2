"""Parquet storage writer.

Implements T029: partitioned writes by asset/year-month with
Snappy compression, simple row-group sizing (~100MB), and
atomic file replacement using a staging temp file.

Keep it small and easy to read.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass
class ParquetWriteResult:
    path: Path
    rows: int
    partitions: Mapping[str, str]
    row_group_size: int
    compression: str


def _to_records(items: Iterable[Any]) -> list[Mapping[str, Any]]:
    out: list[Mapping[str, Any]] = []
    for x in items:
        if isinstance(x, Mapping):
            out.append(x)
        elif hasattr(x, "model_dump") and callable(getattr(x, "model_dump")):
            out.append(x.model_dump())  # type: ignore[arg-type]
        else:
            # Fallback to __dict__ for simple objects
            out.append(vars(x))
    return out


def _estimate_rows_per_group(
    df: pd.DataFrame, target_bytes: int = 100 * 1024 * 1024
) -> int:
    if df.empty:
        return 1024
    # Approximate bytes/row using deep memory usage
    bytes_total = df.memory_usage(index=True, deep=True).sum()
    bpr = max(1, int(bytes_total / max(1, len(df))))
    rows = int(target_bytes / bpr) if bpr else 1024
    return max(1024, min(rows, 1_000_000))


def _infer_asset_year_month(df: pd.DataFrame) -> tuple[str, int, int]:
    if "asset" not in df.columns:
        raise ValueError("records must include 'asset' column")
    asset = str(df.loc[df.index[0], "asset"])  # take first value

    if "date_utc" not in df.columns:
        raise ValueError("records must include 'date_utc' column")
    dval = df.loc[df.index[0], "date_utc"]
    if isinstance(dval, datetime):
        dt = dval.date()
    elif isinstance(dval, date):
        dt = dval
    else:
        # Try parsing as ISO date
        dt = datetime.fromisoformat(str(dval)).date()
    return asset, dt.year, dt.month


def write_parquet_partitioned(
    items: Sequence[Any],
    *,
    data_root: str | os.PathLike[str] = "./data",
    table: str,
    compression: str = "snappy",
    row_group_size: int | None = None,
) -> ParquetWriteResult:
    """Write a batch of records to a partitioned Parquet file.

    Partitions: asset=ASSET/year=YYYY/month=MM
    """
    if not items:
        raise ValueError("no records to write")

    records = _to_records(items)
    df = pd.DataFrame.from_records(records)
    if row_group_size is None:
        row_group_size = _estimate_rows_per_group(df)

    asset, year, month = _infer_asset_year_month(df)
    out_dir = (
        Path(data_root)
        / table
        / f"asset={asset}"
        / f"year={year}"
        / f"month={month:02d}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_name = f"data_{ts}_{uuid4().hex[:8]}.parquet"
    tmp_path = out_dir / (file_name + ".tmp")
    final_path = out_dir / file_name

    table_pa = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table_pa,
        tmp_path,
        compression=compression,
        write_statistics=True,
        data_page_size=1 << 16,
        use_dictionary=True,
        row_group_size=row_group_size,
    )

    # Atomic replace within same directory
    os.replace(tmp_path, final_path)

    return ParquetWriteResult(
        path=final_path,
        rows=len(df),
        partitions={"asset": asset, "year": str(year), "month": f"{month:02d}"},
        row_group_size=row_group_size,
        compression=compression,
    )


__all__ = ["ParquetWriteResult", "write_parquet_partitioned"]
