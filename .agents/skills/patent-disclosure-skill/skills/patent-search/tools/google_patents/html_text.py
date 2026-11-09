# -*- coding: utf-8 -*-
"""HTML 片段 → 纯文本。"""
from __future__ import annotations

import html
import re

_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(value: str) -> str:
    text = _TAG_RE.sub("", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def tidy_block(value: str) -> str:
    """保留换行的多行文本：每行压空白，去掉空行。"""
    lines = [re.sub(r"[ \t\r\f\v\u00a0]+", " ", line).strip() for line in (value or "").split("\n")]
    return "\n".join(line for line in lines if line)
