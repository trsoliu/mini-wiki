"""笔记 YAML frontmatter：解析、渲染、入库增强。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

try:
    from shared.common import organizations_from_assignees
except ImportError:
    from tools.patent_reader.shared.common import organizations_from_assignees

def evidence_scope_label(scope: str) -> str:
    """标签用短英文（patent/evidence/full）。"""
    return {
        "full_text": "full",
        "abstract_only": "abstract",
        "partial": "partial",
    }.get(scope or "", "full")


def evidence_scope_zh(scope: str) -> str:
    """仪表盘/Dataview 显示用中文。"""
    return {
        "full_text": "全文",
        "abstract_only": "仅摘要",
        "partial": "部分",
    }.get(scope or "", scope or "—")


def speculative_zh(flag: bool) -> str:
    return "是" if flag else "否"


def build_tags(domain: str, evidence_scope: str, confidence_speculative: bool) -> list[str]:
    domain_slug = re.sub(r"\s+", "", domain or "未分类")
    tags = [
        f"patents/{domain_slug}",
        f"patent/evidence/{evidence_scope_label(evidence_scope)}",
    ]
    if confidence_speculative:
        tags.append("patent/speculative")
    return tags

def load_tech_effect(raw) -> dict:
    """解析 Agent 技术功效 JSON，供专利地图矩阵使用。"""
    empty = {"tech_means": [], "tech_effects": [], "tech_effect_pairs": []}
    if raw is None:
        return empty
    if isinstance(raw, Path):
        if not raw.is_file():
            return empty
        try:
            raw = json.loads(raw.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return empty
    if not isinstance(raw, dict):
        return empty

    def _labels(val, limit: int = 8) -> list[str]:
        if val is None:
            return []
        if isinstance(val, str):
            val = [val]
        if not isinstance(val, list):
            return []
        out: list[str] = []
        seen: set[str] = set()
        for item in val:
            s = re.sub(r"\s+", " ", str(item or "").strip().strip('"').strip("'"))
            s = s[:40] if ("→" in s or "->" in s) else s[:16]
            if s and s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= limit:
                break
        return out

    return {
        "tech_means": _labels(raw.get("tech_means") or raw.get("means")),
        "tech_effects": _labels(raw.get("tech_effects") or raw.get("effects")),
        "tech_effect_pairs": _labels(raw.get("tech_effect_pairs") or raw.get("pairs"), limit=8),
    }


def _merge_fm_labels(*sources, limit: int = 8) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for src in sources:
        if src is None:
            continue
        if isinstance(src, str):
            items = [src]
        elif isinstance(src, list):
            items = src
        else:
            continue
        for item in items:
            s = re.sub(r"\s+", " ", str(item or "").strip().strip('"').strip("'"))
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s[:40])
            if len(out) >= limit:
                return out
    return out
_LIST_FM_KEYS = (
    "tags",
    "assignees",
    "cssclasses",
    "aliases",
    "related_pubs",
    "inventors",
    "organizations",
    "cited_pubs",
    "ipc_codes",
    "tech_means",
    "tech_effects",
    "tech_effect_pairs",
)


def parse_frontmatter(content: str) -> tuple[dict, str, str]:
    if not content.startswith("---"):
        return {}, "", content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, "", content
    yaml_block = content[3:end].strip()
    body = content[end + 4 :].lstrip("\n")
    data: dict = {}
    key: str | None = None
    for line in yaml_block.splitlines():
        if line.startswith("  - ") and key:
            data.setdefault(key, [])
            if not isinstance(data[key], list):
                data[key] = [data[key]] if data[key] else []
            data[key].append(line[4:].strip())
        elif ":" in line and not line.startswith(" "):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val in ("", "[]"):
                data[key] = [] if key in _LIST_FM_KEYS or val == "[]" else ""
            elif val == "true":
                data[key] = True
            elif val == "false":
                data[key] = False
            else:
                data[key] = val.strip('"')
    return data, yaml_block, body


def render_frontmatter(data: dict) -> str:
    lines = ["---"]
    order = [
        "tags",
        "aliases",
        "cssclasses",
        "pub_number",
        "domain",
        "ipc",
        "ipc_codes",
        "assignees",
        "organizations",
        "inventors",
        "filing_date",
        "publication_date",
        "application_number",
        "invention_title",
        "cited_pubs",
        "related_pubs",
        "tech_means",
        "tech_effects",
        "tech_effect_pairs",
        "read_date",
        "perspective",
        "evidence_scope",
        "confidence_speculative",
    ]
    written: set[str] = set()
    for key in order + sorted(k for k in data if k not in order):
        if key in written or key not in data:
            continue
        written.add(key)
        val = data[key]
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {item}")
        elif isinstance(val, bool):
            lines.append(f"{key}: {'true' if val else 'false'}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _clue_is_speculative(clue: dict) -> bool:
    conf = str(clue.get("confidence") or "").strip().lower()
    if conf in ("高", "high"):
        return False
    if conf in ("中", "低", "medium", "low", "med", "mid", ""):
        return True
    # 未标注置信度但有 URL 的附录线索默认视为推测
    return bool(clue.get("url") or clue.get("link"))


def enrich_note_frontmatter(
    content: str,
    *,
    pub: str,
    domain: str,
    manifest: dict,
    anchor: dict,
    public_clues: list | None = None,
    tech_effect: dict | None = None,
) -> str:
    fm, _, body = parse_frontmatter(content)
    ipc_codes = list(manifest.get("ipc_codes") or anchor.get("ipc_codes") or [])
    ipc = "; ".join(str(x) for x in ipc_codes[:4]) if ipc_codes else ""
    scope = manifest.get("evidence_scope") or fm.get("evidence_scope") or "full_text"
    assignees = manifest.get("assignees") or anchor.get("assignees") or fm.get("assignees") or []
    if isinstance(assignees, str):
        assignees = [assignees] if assignees.strip() else []
    inventors = manifest.get("inventors") or fm.get("inventors") or []
    if isinstance(inventors, str):
        inventors = [inventors] if inventors.strip() else []
    organizations = manifest.get("organizations") or fm.get("organizations") or []
    if isinstance(organizations, str):
        organizations = [organizations] if organizations.strip() else []
    if not organizations:
        organizations = organizations_from_assignees(assignees)
    cited_pubs = manifest.get("cited_pubs") or fm.get("cited_pubs") or []
    if isinstance(cited_pubs, str):
        cited_pubs = [cited_pubs] if cited_pubs.strip() else []
    clues = public_clues or []
    speculative = bool(fm.get("confidence_speculative"))
    if clues:
        speculative = speculative or any(_clue_is_speculative(c) for c in clues)
    # 未传线索文件时，根据正文附录 B / speculative callout 推断
    if not clues and (
        "[!speculative]" in body
        or re.search(r"置信度[：:]\s*(中|低)", body)
        or "公开检索线索" in body and "http" in body
    ):
        speculative = True

    tags = list(dict.fromkeys(build_tags(domain, scope, speculative) + list(fm.get("tags") or [])))
    cssclasses = list(dict.fromkeys(["patent-reader"] + list(fm.get("cssclasses") or [])))
    aliases = list(dict.fromkeys([pub] + list(fm.get("aliases") or [])))

    # ipc 可能已是分号串（Agent 手写）
    if not ipc and isinstance(fm.get("ipc"), str):
        ipc = fm.get("ipc") or ""
    elif isinstance(ipc_codes, list) and len(ipc_codes) > 1 and not str(fm.get("ipc") or "").strip():
        ipc = "; ".join(str(x) for x in ipc_codes[:4])

    fm.update(
        {
            "tags": tags,
            "aliases": aliases,
            "cssclasses": cssclasses,
            "pub_number": pub,
            "domain": domain,
            "ipc": ipc or fm.get("ipc") or "",
            "ipc_codes": ipc_codes[:10] or fm.get("ipc_codes") or [],
            "assignees": assignees[:8] if isinstance(assignees, list) else assignees,
            "organizations": organizations[:8] if isinstance(organizations, list) else organizations,
            "inventors": inventors[:12] if isinstance(inventors, list) else inventors,
            "cited_pubs": cited_pubs[:20] if isinstance(cited_pubs, list) else cited_pubs,
            "evidence_scope": scope,
            "evidence_label": evidence_scope_zh(str(scope)),
            "confidence_speculative": speculative,
            "speculative_label": speculative_zh(bool(speculative)),
        }
    )
    for src_key, fm_key in (
        ("filing_date", "filing_date"),
        ("publication_date", "publication_date"),
        ("application_number", "application_number"),
        ("invention_title", "invention_title"),
    ):
        val = (manifest.get(src_key) or fm.get(fm_key) or "").strip()
        if val:
            fm[fm_key] = val
    if not fm.get("read_date"):
        fm["read_date"] = datetime.now().strftime("%Y-%m-%d")
    te = tech_effect or {}
    means = _merge_fm_labels(fm.get("tech_means"), te.get("tech_means"))
    effects = _merge_fm_labels(fm.get("tech_effects"), te.get("tech_effects"))
    pairs = _merge_fm_labels(fm.get("tech_effect_pairs"), te.get("tech_effect_pairs"))
    if means:
        fm["tech_means"] = means
    if effects:
        fm["tech_effects"] = effects
    if pairs:
        fm["tech_effect_pairs"] = pairs
    return render_frontmatter(fm) + body

