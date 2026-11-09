#!/usr/bin/env python
"""Rebuild ipc_subclasses_{version}.csv. From repo root:

    python skills/patent-map/tools/ipc_scheme/build.py
"""
from __future__ import annotations

import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from ipc_scheme.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
