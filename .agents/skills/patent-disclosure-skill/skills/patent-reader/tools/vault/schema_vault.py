# -*- coding: utf-8 -*-
"""StructureSchema / AppearanceSchema：笔记 upsert + Canvas 卡片。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _as_dict(raw: Any) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, Path)):
        p = Path(raw)
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_structure_schema(raw: Any) -> dict:
    data = _as_dict(raw)
    if "structure_schema" in data and isinstance(data["structure_schema"], dict):
        return data["structure_schema"]
    return data if data.get("parts") is not None or data.get("$schema") else {}


def load_appearance_schema(raw: Any) -> dict:
    data = _as_dict(raw)
    if "appearance_schema" in data and isinstance(data["appearance_schema"], dict):
        return data["appearance_schema"]
    return data if data.get("overall_shape") is not None or data.get("views") is not None else {}


def resolve_schema_files(
    workdir: Path | None,
    *,
    structure_path: Path | None = None,
    appearance_path: Path | None = None,
) -> tuple[dict, dict]:
    structure: dict = {}
    appearance: dict = {}
    if structure_path and structure_path.is_file():
        structure = load_structure_schema(structure_path)
    elif workdir:
        for name in ("structure_schema.json", "structure_facts.json"):
            p = workdir / name
            if p.is_file():
                structure = load_structure_schema(p)
                break
        plan = workdir / "note_plan.json"
        if not structure and plan.is_file():
            structure = load_structure_schema(plan)
    if appearance_path and appearance_path.is_file():
        appearance = load_appearance_schema(appearance_path)
    elif workdir:
        for name in ("appearance_schema.json", "appearance_facts.json"):
            p = workdir / name
            if p.is_file():
                appearance = load_appearance_schema(p)
                break
        plan = workdir / "note_plan.json"
        if not appearance and plan.is_file():
            appearance = load_appearance_schema(plan)
    return structure, appearance


def _parts_by_id(parts: list) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for p in parts or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        if pid:
            out[pid] = p
    return out


def _part_cell(parts_by_id: dict[str, dict], pid: Any) -> str:
    """件号 + 名称，便于阅读（无名称时仅件号）。"""
    key = str(pid).strip() if pid is not None else ""
    if not key or key == "—":
        return "—"
    name = (parts_by_id.get(key) or {}).get("name") or ""
    name = str(name).strip()
    return f"{key} {name}".strip() if name else key


def render_structure_section_md(schema: dict) -> str:
    parts = schema.get("parts") or []
    rels = schema.get("relations") or []
    spatial = schema.get("spatial") or []
    funcs = schema.get("function_of_structure") or []
    uncertain = schema.get("uncertain") or []
    by_id = _parts_by_id(parts)
    lines = [
        "## 结构说明",
        "",
        "### 部件",
        "",
        "| 件号 | 名称 | 形状 | 材料提示 |",
        "| --- | --- | --- | --- |",
    ]
    if not parts:
        lines.append("| — | — | — | — |")
    for p in parts:
        lines.append(
            f"| {p.get('id') or '—'} | {p.get('name') or '—'} "
            f"| {p.get('shape') or '—'} | {p.get('material_hint') or '—'} |"
        )
    lines += [
        "",
        "### 连接关系",
        "",
        "| 自 | 至 | 类型 | 位置 |",
        "| --- | --- | --- | --- |",
    ]
    if not rels:
        lines.append("| — | — | — | — |")
    for r in rels:
        lines.append(
            f"| {_part_cell(by_id, r.get('from'))} | {_part_cell(by_id, r.get('to'))} "
            f"| {r.get('type') or '—'} | {r.get('where') or '—'} |"
        )
    if spatial:
        lines += ["", "### 空间关系", ""]
        lines.extend(f"- {s}" for s in spatial)
    if funcs:
        lines += ["", "### 结构作用", ""]
        lines.extend(f"- {s}" for s in funcs)
    if uncertain:
        lines += ["", "### 不确定项", ""]
        lines.extend(f"- {s}" for s in uncertain)
    lines.append("")
    return "\n".join(lines)


def render_appearance_section_md(schema: dict) -> str:
    views = schema.get("views") or []
    points = schema.get("design_points") or []
    ornament = schema.get("ornament") or []
    color = schema.get("color") or []
    uncertain = schema.get("uncertain") or []
    lines = [
        "## 外观要点",
        "",
        f"- **产品**：{schema.get('product_name') or '—'}",
        f"- **整体造型**：{schema.get('overall_shape') or '—'}",
        "",
        "### 视图",
        "",
        "| 视图 | 说明 |",
        "| --- | --- |",
    ]
    if not views:
        lines.append("| — | — |")
    for v in views:
        if isinstance(v, dict):
            lines.append(f"| {v.get('name') or '—'} | {v.get('notes') or '—'} |")
        else:
            lines.append(f"| {v} | — |")
    if points:
        lines += ["", "### 设计要点", ""]
        lines.extend(f"- {s}" for s in points)
    if ornament or color:
        lines += ["", "### 图案 / 色彩", ""]
        lines.extend(f"- 图案：{s}" for s in ornament)
        lines.extend(f"- 色彩：{s}" for s in color)
    if uncertain:
        lines += ["", "### 不确定项", ""]
        lines.extend(f"- {s}" for s in uncertain)
    lines.append("")
    return "\n".join(lines)


def _upsert_named_section(content: str, heading: str, section_md: str, *, after_heading: str) -> str:
    section_md = section_md.rstrip() + "\n\n"
    pat = re.compile(
        rf"^##\s*{re.escape(heading)}\s*\n[\s\S]*?(?=^##\s+|\Z)",
        re.M,
    )
    if pat.search(content):
        return pat.sub(section_md, content, count=1)
    m = re.search(rf"^##\s*{re.escape(after_heading)}\s*.*$", content, re.M)
    if m:
        rest = content[m.end() :]
        m2 = re.search(r"^##\s+", rest, re.M)
        if m2:
            ins = m.end() + m2.start()
            return content[:ins] + section_md + content[ins:]
        return content.rstrip() + "\n\n" + section_md
    return content.rstrip() + "\n\n" + section_md


def upsert_structure_section(content: str, section_md: str) -> str:
    # 兼容旧标题「结构说明（StructureSchema）」
    for heading in ("结构说明（StructureSchema）", "结构说明"):
        pat = re.compile(
            rf"^##\s*{re.escape(heading)}\s*\n[\s\S]*?(?=^##\s+|\Z)",
            re.M,
        )
        if pat.search(content):
            return pat.sub(section_md.rstrip() + "\n\n", content, count=1)
    return _upsert_named_section(
        content, "结构说明", section_md, after_heading="五、专利内术语表"
    )


def upsert_appearance_section(content: str, section_md: str) -> str:
    for heading in ("外观要点（AppearanceSchema）", "外观要点"):
        pat = re.compile(
            rf"^##\s*{re.escape(heading)}\s*\n[\s\S]*?(?=^##\s+|\Z)",
            re.M,
        )
        if pat.search(content):
            return pat.sub(section_md.rstrip() + "\n\n", content, count=1)
    return _upsert_named_section(
        content, "外观要点", section_md, after_heading="五、专利内术语表"
    )


def structure_canvas_cards(schema: dict, *, x0: int = -520, y0: int = 320) -> list[dict]:
    if not schema:
        return []
    cards: list[dict] = []
    parts = schema.get("parts") or []
    rels = schema.get("relations") or []
    by_id = _parts_by_id(parts)
    body = ["# 结构 · 部件", ""]
    for p in parts[:12]:
        body.append(f"- **{p.get('id')}** {p.get('name') or ''}（{p.get('shape') or ''}）")
    if rels:
        body += ["", "# 连接", ""]
        for r in rels[:10]:
            body.append(
                f"- {_part_cell(by_id, r.get('from'))} → {_part_cell(by_id, r.get('to'))} "
                f"· {r.get('type') or ''} @ {r.get('where') or ''}"
            )
    cards.append(
        {
            "id": "structure-schema",
            "type": "text",
            "text": "\n".join(body)[:1800],
            "x": x0,
            "y": y0,
            "width": 360,
            "height": min(420, 120 + 28 * (len(parts) + len(rels))),
            "color": "4",
        }
    )
    return cards


def appearance_canvas_cards(schema: dict, *, x0: int = -520, y0: int = 320) -> list[dict]:
    if not schema:
        return []
    points = schema.get("design_points") or []
    views = schema.get("views") or []
    body = [
        "# 外观要点",
        "",
        f"**{schema.get('product_name') or ''}**",
        "",
        schema.get("overall_shape") or "",
        "",
        "## 设计要点",
    ]
    body.extend(f"- {p}" for p in points[:8])
    if views:
        body += ["", "## 视图"]
        for v in views[:6]:
            name = v.get("name") if isinstance(v, dict) else str(v)
            body.append(f"- {name}")
    return [
        {
            "id": "appearance-schema",
            "type": "text",
            "text": "\n".join(body)[:1800],
            "x": x0,
            "y": y0,
            "width": 360,
            "height": 320,
            "color": "3",
        }
    ]
