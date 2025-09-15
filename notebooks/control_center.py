#!/usr/bin/env python
# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # DVOL Data Ingest – Control Center
# Orchestrate the end-to-end ingest pipeline via 8 main cells.

# %% [tags: [env-setup]]
# 1) Environment Setup
import os
import platform
import sys
import time
from pathlib import Path

# Ensure 'src' is importable
def find_repo_root(start: Path | None = None) -> Path:
    here = start or Path.cwd()
    for p in [here, *here.parents]:
        if (p / 'pyproject.toml').exists() and (p / 'src').exists():
            return p
    return here

repo_root = find_repo_root()
src_path = repo_root / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

print('Python:', platform.python_version())
print('CWD:', os.getcwd())
print('Repo root:', str(repo_root))
print('SRC in path:', str(src_path) in sys.path)
print('UTC time:', time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))

# optional: richer logs in notebooks
try:
    from rich import print as rprint  # type: ignore
except Exception:
    rprint = print

# %% [tags: [config-auth]]
# 2) Configuration / Auth
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv(usecwd=True)
loaded = load_dotenv(env_path, override=False)
print('Loaded .env:', env_path, '->', loaded)

API_BASE = os.getenv('CDD_API_BASE_URL') or os.getenv('CDD_API_BASE') or 'https://api.cryptodatadownload.com/v1'
API_KEY = os.getenv('CDD_API_KEY', '')
DATA_ROOT = os.getenv('DATA_ROOT') or os.getenv('DATA_ROOT_PATH') or str(repo_root / 'data')

config = {
    'api_base': API_BASE,
    'api_key': 'SET' if API_KEY else 'MISSING',
    'data_root': DATA_ROOT,
}
rprint({'config': config})

# %% [tags: [fetch]]
# 3) Data Fetching Operations
# Ensure latest client code is active and env is set
import os, sys
os.environ['CDD_API_BASE_URL'] = API_BASE
os.environ.setdefault('CDD_DEBUG', '0')
from importlib import reload
import dvol_data_ingest.clients.dvol as _c_dvol
import dvol_data_ingest.clients.futures as _c_fut
import dvol_data_ingest.clients.funding as _c_fund
import dvol_data_ingest.clients.options as _c_opt
import dvol_data_ingest.clients.onchain as _c_on
import dvol_data_ingest.notebooks.operations as _ops
reload(_c_dvol); reload(_c_fut); reload(_c_fund); reload(_c_opt); reload(_c_on); reload(_ops)
from dvol_data_ingest.notebooks.operations import interactive_fetch
# Quick auth probe
try:
    from dvol_data_ingest.clients.dvol import DVOLClient, DVOL_PATH
    with DVOLClient() as _probe:
        _r = _probe.get(DVOL_PATH, params={'symbol':'BTC','limit':1})
    rprint({'probe':'dvol','status': _r.status_code, 'url': _r.url})
except Exception as _e:
    rprint({'probe':'dvol','error': str(_e)})

sources = ['dvol', 'options', 'futures', 'funding', 'onchain']  # edit as needed
assets = ['BTC', 'ETH']  # edit as needed

try:
    records = interactive_fetch(sources=sources, assets=assets)
    rprint('[green]Fetch complete[/green]')
except NotImplementedError:
    rprint('[yellow]interactive_fetch not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'fetch_error': str(e)})

# %% [tags: [validate]]
# 4) Schema Validation
from dvol_data_ingest.notebooks.operations import validate_data

try:
    validate_data(strict=True)
    rprint('[green]Validation passed[/green]')
except NotImplementedError:
    rprint('[yellow]validate_data not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'validation_error': str(e)})

# %% [tags: [storage]]
# 5) Parquet Storage
from dvol_data_ingest.storage.parquet import write_parquet_partitioned

# Expect a list of record dicts or Pydantic models with fields: asset, date_utc, ...
# For demo purposes, this will NO-OP if no records variable is defined.
try:
    records = globals().get('records', [])
    if not records:
        rprint('[yellow]No records available to write; skipping.[/yellow]')
    else:
        res = write_parquet_partitioned(records, data_root=DATA_ROOT, table='dvol')
        rprint({'parquet_write': {'path': str(res.path), 'rows': res.rows, 'partitions': res.partitions}})
except Exception as e:
    rprint({'parquet_error': str(e)})

# %% [tags: [monitoring]]
# 6) Monitoring Dashboard
from pathlib import Path

data_dir = Path(DATA_ROOT)
files = list(data_dir.glob('**/*.parquet'))
summary = {
    'file_count': len(files),
    'assets': sorted({p.parts[-3].split('=')[-1] for p in files}) if files else [],
}
rprint({'data_summary': summary})

# Optional: quick peek into one file's schema
if files:
    try:
        import pyarrow.parquet as pq
        meta = pq.ParquetFile(files[0]).schema_arrow
        rprint({'example_file': str(files[0]), 'schema': str(meta)})
    except Exception as e:
        rprint({'monitoring_error': str(e)})

# %% [tags: [backfill]]
# 7) Backfill Operations
from dvol_data_ingest.notebooks.operations import run_backfill

start_utc = '2024-01-01'  # edit
end_utc = '2024-02-01'    # edit
try:
    run_backfill(start=start_utc, end=end_utc)
    rprint('[green]Backfill completed[/green]')
except NotImplementedError:
    rprint('[yellow]run_backfill not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'backfill_error': str(e)})

# %% [tags: [troubleshoot]]
# 8) Troubleshooting Tools
from dvol_data_ingest.notebooks.operations import (
    display_metrics,
    show_status,
    troubleshoot_pipeline,
)

try:
    st = show_status()
    rprint({'status': st})
except NotImplementedError:
    rprint('[yellow]show_status not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'status_error': str(e)})

try:
    display_metrics()
except NotImplementedError:
    rprint('[yellow]display_metrics not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'metrics_error': str(e)})

try:
    troubleshoot_pipeline(verbose=True)
except NotImplementedError:
    rprint('[yellow]troubleshoot_pipeline not implemented yet (T032)[/yellow]')
except Exception as e:
    rprint({'troubleshoot_error': str(e)})
