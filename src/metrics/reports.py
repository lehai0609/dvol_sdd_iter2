"""Simple reporting utilities (T051 tests).

Functions produce deterministic filenames given stem and run_id.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict

import pandas as pd
import matplotlib

# Use non-interactive backend for headless environments
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def write_csv_report(
    df: pd.DataFrame, *, out_dir: Path, stem: str, run_id: str
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stem}_{run_id}.csv"
    df.to_csv(path, index=False)
    return path


def write_png_lineplot(
    series: pd.Series, *, out_dir: Path, stem: str, run_id: str
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stem}_{run_id}.png"
    plt.figure(figsize=(6, 3))
    pd.Series(series).plot(kind="line")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()
    return path


def write_html_summary(
    metrics: Dict[str, float], *, out_dir: Path, stem: str, run_id: str
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{stem}_{run_id}.html"
    # Minimal HTML
    rows = "\n".join(f"<li>{k}: {v}</li>" for k, v in metrics.items())
    html = f"""
    <html><head><meta charset='utf-8'><title>{stem} {run_id}</title></head>
    <body>
      <h1>Summary</h1>
      <ul>{rows}</ul>
    </body></html>
    """
    path.write_text(html, encoding="utf-8")
    return path
