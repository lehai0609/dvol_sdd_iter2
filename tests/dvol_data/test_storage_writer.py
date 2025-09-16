from pathlib import Path

import pandas as pd

from dvol_data.storage import write_partition


def test_write_partition_creates_expected_path(tmp_path: Path):
    # Use tmp root to avoid polluting repo data dir
    df = pd.DataFrame({"x": [1]})
    path = write_partition(
        df,
        layer="raw",
        table="raw_dvol",
        asset="BTC",
        date="2024-06-01",
        root=tmp_path,
    )

    # Expected path layout
    expected = tmp_path / "raw" / "raw_dvol" / "asset=BTC" / "date=2024-06-01" / "part.parquet"
    assert path == expected
    assert path.exists()

