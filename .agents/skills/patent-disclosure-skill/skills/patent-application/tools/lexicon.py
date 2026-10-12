#!/usr/bin/env python
"""申请文件词库：从 YAML 编译宣传语正则。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_REF = Path(__file__).resolve().parents[1] / "references" / "promo_terms.yaml"
_FALLBACK = ("效果更好", "性能优异", "显著提高", "大大提高", "最佳", "最优")


def load_promo_terms(path: Path | None = None) -> tuple[str, ...]:
    target = path or _REF
    if not target.is_file():
        return _FALLBACK
    try:
        import yaml
    except ImportError:
        return _FALLBACK
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    raw = data.get("terms") if isinstance(data, dict) else None
    terms = tuple(str(item).strip() for item in (raw or []) if str(item).strip())
    return terms or _FALLBACK


@lru_cache(maxsize=4)
def promo_pattern(path: str | None = None) -> re.Pattern[str]:
    terms = load_promo_terms(Path(path) if path else None)
    ordered = sorted(terms, key=len, reverse=True)
    return re.compile("|".join(re.escape(term) for term in ordered))
