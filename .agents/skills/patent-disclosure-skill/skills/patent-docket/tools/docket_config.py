# -*- coding: utf-8 -*-
"""案卷 config.yaml。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "max_rounds": 3,
    "output_subdir": "docket",
}

_PKG = Path(__file__).resolve().parents[1]


def config_path() -> Path:
    return _PKG / "config.yaml"


def load_docket_config(path: Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULTS)
    target = path or config_path()
    if not target.is_file():
        return cfg
    try:
        import yaml
    except ImportError:
        return cfg
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return cfg
    if "max_rounds" in data:
        cfg["max_rounds"] = int(data["max_rounds"])
    if "output_subdir" in data and str(data["output_subdir"]).strip():
        cfg["output_subdir"] = str(data["output_subdir"]).strip()
    if cfg["max_rounds"] < 1:
        cfg["max_rounds"] = 1
    return cfg
