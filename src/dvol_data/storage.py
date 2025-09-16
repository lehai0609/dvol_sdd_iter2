from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd


PartitionLayer = Literal["raw", "features", "labels", "models", "artifacts"]


def write_partition(
    df: pd.DataFrame,
    *,
    layer: PartitionLayer,
    table: str,
    asset: str,
    date: str,
    root: str | Path = "data",
) -> Path:
    """Write a DataFrame to a deterministic Parquet partition.

    Layout: ``{root}/{layer}/{table}/asset={asset}/date={date}/part.parquet``

    Returns the path to the Parquet file written.
    """
    root = Path(root)
    outdir = root / layer / table / f"asset={asset}" / f"date={date}"
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "part.parquet"

    # Write without index; upstream tests and readers expect flat rows only
    df.to_parquet(path, index=False)
    return path

