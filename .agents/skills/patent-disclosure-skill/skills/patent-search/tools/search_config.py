# -*- coding: utf-8 -*-
"""Load patent-search pagination defaults from config.yaml (dialog / CLI may override)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "max_pages": 3,
    "max_pages_hard": 20,
    "page_delay_ms": 800,
    "http_error_retries": 2,
    "http_error_backoff_ms": 1500,
    "page_size": 3,
}

_INT_KEYS = frozenset(DEFAULTS)


def config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config.yaml"


def load_search_config(path: Path | None = None) -> dict[str, Any]:
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
    for key in _INT_KEYS:
        if key not in data:
            continue
        try:
            cfg[key] = int(data[key])
        except (TypeError, ValueError):
            continue
    return cfg


def resolve_max_pages(
    *,
    requested: int | None = None,
    want_complete: bool = False,
    cfg: dict[str, Any] | None = None,
) -> int:
    settings = cfg or load_search_config()
    hard = max(1, int(settings["max_pages_hard"]))
    if want_complete:
        return hard
    if requested is None:
        return max(1, min(int(settings["max_pages"]), hard))
    return max(1, min(int(requested), hard))


def resolve_page_budget(
    *,
    requested: int | None = None,
    want_complete: bool = False,
    total_pages: int | None = None,
    cfg: dict[str, Any] | None = None,
) -> int:
    """第一页采到「共 N 页」后的实际翻页预算。

    ``--complete``：有总页数则按总页数翻完（硬上限随总页数）；探测不到才用 ``max_pages_hard``。
    普通检索：仍用 ``max_pages`` / ``--max-pages``，且不超过总页数。
    """
    settings = {**DEFAULTS, **(cfg or {})}
    hard = max(1, int(settings["max_pages_hard"]))
    pages = int(total_pages) if total_pages and int(total_pages) > 0 else None
    if want_complete:
        return pages if pages is not None else hard
    if requested is None:
        budget = max(1, min(int(settings["max_pages"]), hard))
    else:
        budget = max(1, min(int(requested), hard))
    if pages is not None:
        return min(budget, pages)
    return budget
