#!/usr/bin/env python
"""把 Qdrant ONNX（BAAI/bge-small-zh-v1.5）装到用户目录。不下载 PyTorch。"""
from __future__ import annotations

import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from model_store import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
