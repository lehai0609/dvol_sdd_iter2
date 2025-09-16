"""Global test configuration to keep warning noise down on Windows/Jupyter.

Applies recommended environment and asyncio policy tweaks before tests import ZMQ/Jupyter.
"""
from __future__ import annotations

import os
import sys

# Silence Jupyter path deprecation by opting into platformdirs now
os.environ.setdefault("JUPYTER_PLATFORM_DIRS", "1")

# On Windows, prefer the selector-based event loop for pyzmq/tornado compatibility
if sys.platform.startswith("win"):
    try:
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        # Best-effort; if unavailable, let tests proceed
        pass

