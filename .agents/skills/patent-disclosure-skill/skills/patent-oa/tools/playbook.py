# -*- coding: utf-8 -*-
"""审查答复经验手册（与案例库分仓）。

预读抽样 → 判断是否与审查答复相关 → 外挂 book-to-skill 蒸馏
→ 转写到 oa/playbooks/{slug}/。默认不进 search_cases / 向量。
"""
from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from typing import Any

from case_md import dump_case_markdown, parse_case_markdown
from pdf_text import read_document

OA_HINT_TERMS = (
    "审查意见",
    "意见陈述",
    "审查答复",
    "创造性",
    "新颖性",
    "权利要求",
    "专利法第",
    "实施细则",
    "审查指南",
    "补正通知",
    "驳回决定",
    "对比文件",
    "充分公开",
    "得不到说明书支持",
    "office action",
    "inventiveness",
    "答复策略",
    "陈述意见",
)

PLAYBOOK_INDEX = "_playbook.md"
COPY_NAMES = (
    "SKILL.md",
    "cheatsheet.md",
    "patterns.md",
    "glossary.md",
    "README.md",
)


def reject_if_url(raw: str) -> None:
    s = (raw or "").strip()
    if re.match(r"https?://", s, re.I) or s.lower().startswith("file://"):
        raise ValueError("只接受本地文件路径，不接受书的 URL")


def safe_slug(raw: str, fallback: str = "playbook") -> str:
    token = "".join(c if c.isalnum() or c in "-_" else "-" for c in (raw or "").strip())
    token = re.sub(r"-{2,}", "-", token).strip("-_")[:80]
    return token or fallback


def keyword_hits(text: str) -> list[str]:
    blob = text or ""
    blob_l = blob.lower()
    hits: list[str] = []
    for term in OA_HINT_TERMS:
        if term.lower() in blob_l or term in blob:
            hits.append(term)
    return hits


def hint_from_hits(hits: list[str], *, char_count_nospace: int) -> str:
    if char_count_nospace < 80:
        return "too_short"
    if len(hits) >= 3:
        return "likely"
    if len(hits) == 0:
        return "unlikely"
    return "unclear"


def peek_source(path: Path, *, max_pages: int = 8, max_chars: int = 12000) -> dict[str, Any]:
    reject_if_url(str(path))
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"找不到文件: {path}")
    result = read_document(path, max_pages=max_pages)
    text = result.get("text") or ""
    if max_chars > 0 and len(text) > max_chars:
        text = text[:max_chars]
        truncated = True
    else:
        truncated = False
    hits = keyword_hits(text)
    hint = hint_from_hits(hits, char_count_nospace=int(result.get("char_count_nospace") or 0))
    return {
        "ok": True,
        "path": str(path),
        "page_count": result.get("page_count"),
        "pages_read": result.get("pages_read"),
        "char_count": len(text),
        "char_count_nospace": result.get("char_count_nospace"),
        "truncated": truncated,
        "warnings": list(result.get("warnings") or []),
        "keyword_hits": hits,
        "hint": hint,
        "text": text,
        "note_zh": (
            "hint 仅供参考。Agent 须阅读 text 判断是否审查答复相关、是否值得蒸馏；"
            "不合适则拒绝，除非用户强烈要求。"
        ),
    }


def playbooks_root(oa_root: Path) -> Path:
    return oa_root / "playbooks"


def list_playbook_records(oa_root: Path) -> list[dict[str, Any]]:
    root = playbooks_root(oa_root)
    if not root.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        index = d / PLAYBOOK_INDEX
        meta: dict[str, Any] = {}
        if index.is_file():
            try:
                meta, _ = parse_case_markdown(index.read_text(encoding="utf-8"))
            except OSError:
                meta = {}
        records.append(
            {
                "slug": str(meta.get("slug") or d.name),
                "title": str(meta.get("title") or d.name),
                "path": str(d),
                "index": str(index) if index.is_file() else "",
                "verified": bool(meta.get("verified")),
                "force": bool(meta.get("force")),
                "source_path": str(meta.get("source_path") or ""),
            }
        )
    return records


def _copy_distilled(src: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    dest.mkdir(parents=True, exist_ok=True)
    for name in COPY_NAMES:
        p = src / name
        if p.is_file():
            shutil.copy2(p, dest / name)
            copied.append(name)
    chapters = src / "chapters"
    if chapters.is_dir():
        target = dest / "chapters"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(
            chapters,
            target,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "node_modules"),
        )
        copied.append("chapters/")
    if not copied:
        md_files = sorted(src.glob("*.md"))
        if not md_files:
            raise ValueError(f"蒸馏目录没有可转写的 Markdown: {src}")
        for p in md_files:
            shutil.copy2(p, dest / p.name)
            copied.append(p.name)
    return copied


def ingest_distilled_skill(
    *,
    skill_dir: Path,
    oa_root: Path,
    source_path: Path,
    slug: str = "",
    title: str = "",
    force: bool = False,
    peek_decision: str = "accept",
) -> dict[str, Any]:
    skill_dir = skill_dir.expanduser().resolve()
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"找不到蒸馏输出目录: {skill_dir}")
    source_path = source_path.expanduser().resolve()
    slug = safe_slug(slug or skill_dir.name or source_path.stem)
    dest = playbooks_root(oa_root) / slug
    dest.mkdir(parents=True, exist_ok=True)
    copied = _copy_distilled(skill_dir, dest)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cheatsheet = dest / "cheatsheet.md"
    patterns = dest / "patterns.md"
    meta = {
        "kind": "playbook",
        "verified": False,
        "force": bool(force),
        "peek_decision": peek_decision,
        "slug": slug,
        "title": title or slug,
        "source_path": str(source_path),
        "skill_dir": str(skill_dir),
        "distilled_at": now,
        "tags": ["oa/playbook"],
    }
    cheat_line = (
        f"- 决策表：[[oa/playbooks/{slug}/cheatsheet|cheatsheet]]"
        if cheatsheet.is_file()
        else "- 决策表：（无 cheatsheet.md）"
    )
    pattern_line = "- 模式/反模式：有 patterns.md" if patterns.is_file() else "- 模式/反模式：（无）"
    force_note = "（用户强烈要求）" if force else ""
    body = (
        f"> 导航：[[oa/_OA索引|_OA索引]] · 经验手册（不进案例检索）\n\n"
        f"# {meta['title']}\n\n"
        f"- 来源（本地）：`{source_path.name}`\n"
        f"- 预读结论：`{peek_decision}`{force_note}\n"
        f"{cheat_line}\n"
        f"{pattern_line}\n\n"
        "## 使用\n\n"
        "写答复时按缺陷阅读 cheatsheet / patterns，**不要**当作 `case_id` 引用。\n"
        "权威顺序：审查指南/法条 → 本库案例 → 本手册打法。\n"
    )
    index = dest / PLAYBOOK_INDEX
    index.write_text(dump_case_markdown(meta, body), encoding="utf-8")
    return {
        "ok": True,
        "slug": slug,
        "dest": str(dest),
        "index": str(index),
        "copied": copied,
        "into_case_index": False,
    }
