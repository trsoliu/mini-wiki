"""解析案例 md frontmatter + 正文。"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any


_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def parse_case_markdown(text: str) -> tuple[dict[str, Any], str]:
    m = _FM.match((text or "").strip())
    if not m:
        return {}, text or ""
    raw_fm, body = m.group(1), m.group(2)
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("需要 PyYAML") from exc
    meta = yaml.safe_load(raw_fm) or {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def dump_case_markdown(meta: dict[str, Any], body: str) -> str:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("需要 PyYAML") from exc
    fm = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    body = (body or "").lstrip("\n")
    return f"---\n{fm}\n---\n\n{body.rstrip()}\n"


def chunk_case(meta: dict[str, Any], body: str) -> list[tuple[str, str]]:
    """返回 (chunk_kind, text) 列表供向量化。"""
    chunks: list[tuple[str, str]] = []
    title = str(meta.get("title") or meta.get("case_id") or "case")
    header = (
        f"{title}\n"
        f"type={meta.get('patent_type', '')}\n"
        f"statutes={meta.get('statutes', [])}\n"
        f"defects={meta.get('defect_types', [])}\n"
        f"domain={meta.get('domain', '')}\n"
        f"strategy={meta.get('strategy', [])}\n"
        f"outcome={meta.get('outcome', '')}\n"
    )
    chunks.append(("header", header))
    parts = re.split(r"(?m)^##\s+", body or "")
    if len(parts) == 1:
        text = (body or "").strip()
        if text:
            chunks.append(("body", text[:4000]))
        return chunks
    if parts[0].strip():
        chunks.append(("preamble", parts[0].strip()[:2000]))
    for block in parts[1:]:
        lines = block.splitlines()
        heading = (lines[0] if lines else "section").strip()
        content = "\n".join(lines[1:]).strip()
        kind = "section"
        if "通知" in heading:
            kind = "notice"
        elif "策略" in heading:
            kind = "strategy"
        elif "陈述" in heading:
            kind = "argument"
        elif "修改" in heading:
            kind = "amendment"
        elif "结果" in heading:
            kind = "outcome"
        text = f"## {heading}\n{content}".strip()
        if text:
            chunks.append((kind, text[:4000]))
    return chunks


def read_case_file(path: Path) -> tuple[dict[str, Any], str]:
    return parse_case_markdown(path.read_text(encoding="utf-8"))
