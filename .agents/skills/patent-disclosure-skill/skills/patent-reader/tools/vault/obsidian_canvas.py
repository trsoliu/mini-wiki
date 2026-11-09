"""专利解读 JSON Canvas 与笔记内图谱导航。"""
from __future__ import annotations

import re
from pathlib import Path

try:
    from vault.obsidian_claims import _claim_tree_card_text
    from vault.obsidian_glossary import resolve_glossary_nodes
except ImportError:
    from tools.patent_reader.vault.obsidian_claims import _claim_tree_card_text
    from tools.patent_reader.vault.obsidian_glossary import resolve_glossary_nodes

_CANVAS_COLORS = {
    "center": "#4F46E5",
    "hub": "#0284C7",
    "claims": "#475569",
    "related": "#CA8A04",
    "term": "#EA580C",
    "disclosure": "#0F766E",
    "group_narr": "#6366F1",
    "group_term": "#F97316",
    "group_rel": "#EAB308",
    "narr_problem": "#DC2626",
    "narr_approach": "#D97706",
    "narr_how": "#2563EB",
    "narr_effect": "#059669",
    "narr_diff": "#7C3AED",
    "narr_one": "#4F46E5",
    "clue": "#B45309",
    "group_clue": "#D97706",
}


def _clip_canvas_text(text: str, limit: int = 140) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def _narrative_cards(narrative: dict | None) -> list[tuple[str, str, str, str]]:
    """返回 (id, 标题, 正文, 颜色) 列表。"""
    if not narrative:
        return []
    order = [
        ("problem", "问题", "narr_problem"),
        ("approach", "思路", "narr_approach"),
        ("how", "怎么做", "narr_how"),
        ("effect", "效果", "narr_effect"),
        ("diff", "差别", "narr_diff"),
        ("one_liner", "一句话", "narr_one"),
    ]
    cards: list[tuple[str, str, str, str]] = []
    for key, label, color_key in order:
        text = str(narrative.get(key) or "").strip()
        if not text:
            continue
        if key == "one_liner" and any(
            k in narrative for k in ("problem", "approach", "effect")
        ):
            continue
        cards.append(
            (
                f"narr-{key}",
                label,
                _clip_canvas_text(text, 160),
                _CANVAS_COLORS[color_key],
            )
        )
    return cards[:5]


def build_canvas(
    *,
    vault: Path | None,
    papers_dir: str,
    note_rel_path: str,
    pub: str,
    title: str,
    related: dict,
    glossary_terms: list[str] | list[dict] | None = None,
    glossary_dir: str = "Research/术语",
    create_glossary_stubs: bool = True,
    glossary_root: Path | None = None,
    meta: dict | None = None,
    claim_tree: dict | None = None,
    claim_summaries: dict[int, str] | None = None,
    figure_rels: list[str] | None = None,
    narrative: dict | None = None,
    clue_cards: list[dict] | None = None,
    structure_schema: dict | None = None,
    appearance_schema: dict | None = None,
) -> dict:
    """生成 JSON Canvas：叙事故事地图 + 精简中心 + 术语含义卡 + 分组。

    glossary_root 用于无 vault 时写入本地术语页。
    默认不挂扫描附图（易刷屏）；figure_rels 仅保留非 page_ 精修图最多 1 张。
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    center_id = "center"
    meta = meta or {}
    narrative = narrative or {}
    note_rel = str(note_rel_path).replace("\\", "/")
    note_link = note_rel[:-3] if note_rel.endswith(".md") else note_rel

    domain = str(meta.get("domain") or "").strip()
    ipc = meta.get("ipc") or meta.get("ipc_codes") or ""
    if isinstance(ipc, list):
        ipc = "; ".join(str(x) for x in ipc[:4])
    assignees = meta.get("assignees") or []
    if isinstance(assignees, list):
        asg = "、".join(str(a) for a in assignees[:3])
    else:
        asg = str(assignees)
    scope = str(meta.get("evidence_scope") or "").strip()
    scope_zh = {
        "full_text": "全文",
        "abstract_only": "仅摘要",
        "partial": "部分",
    }.get(scope, scope or "—")

    one = _clip_canvas_text(
        str(narrative.get("one_liner") or narrative.get("problem") or ""), 120
    )
    center_lines = [
        f"# `{pub}`",
        "",
        f"**{title}**" if title else "",
        "",
        one or "（打开下方链接阅读全文解读）",
        "",
        f"[[{note_link}|打开解读笔记]]",
    ]
    nodes.append(
        {
            "id": center_id,
            "type": "text",
            "text": "\n".join(ln for ln in center_lines if ln is not None),
            "x": -40,
            "y": -40,
            "width": 420,
            "height": 240,
            "color": _CANVAS_COLORS["center"],
        }
    )

    # 叙事卡 + 分组（中心上方）
    narr_cards = _narrative_cards(narrative)
    if narr_cards:
        n = len(narr_cards)
        card_w, gap = 250, 16
        total_w = n * card_w + (n - 1) * gap
        start_x = -total_w // 2
        narr_y = -420
        nodes.append(
            {
                "id": "grp-narr",
                "type": "group",
                "x": start_x - 24,
                "y": narr_y - 48,
                "width": total_w + 48,
                "height": 290,
                "label": "叙事",
                "color": _CANVAS_COLORS["group_narr"],
            }
        )
        for i, (nid, label, text, color) in enumerate(narr_cards):
            nodes.append(
                {
                    "id": nid,
                    "type": "text",
                    "text": f"## {label}\n\n{text}",
                    "x": start_x + i * (card_w + gap),
                    "y": narr_y,
                    "width": card_w,
                    "height": 220,
                    "color": color,
                }
            )
            edges.append(
                {
                    "id": f"e-{nid}",
                    "fromNode": nid,
                    "fromSide": "bottom",
                    "toNode": center_id,
                    "toSide": "top",
                    "label": label,
                    "color": color,
                }
            )

    hub_lines = [
        "## 著录",
        "",
        f"**公开号** `{pub}`",
        f"**领域** {domain or '—'}",
        f"**IPC** {ipc or '—'}",
        f"**申请人** {asg or '—'}",
        f"**证据** {scope_zh}",
        "",
        f"[[{papers_dir}/_专利解读索引|索引]]",
    ]
    if domain:
        hub_lines.append(f"[[{papers_dir}/{domain}/_领域索引|{domain}]]")
    hub_lines.append(f"[[{glossary_dir}/_术语索引|术语索引]]")

    nodes.append(
        {
            "id": "hub",
            "type": "text",
            "text": "\n".join(hub_lines),
            "x": -560,
            "y": -80,
            "width": 300,
            "height": 280,
            "color": _CANVAS_COLORS["hub"],
        }
    )
    edges.append(
        {
            "id": "e-hub-center",
            "fromNode": "hub",
            "fromSide": "right",
            "toNode": center_id,
            "toSide": "left",
            "label": "著录",
            "color": _CANVAS_COLORS["hub"],
        }
    )

    claim_text = _claim_tree_card_text(
        claim_tree, pub, summaries=claim_summaries
    )
    if claim_text:
        row_n = max(claim_text.count("\n|"), 3)
        nodes.append(
            {
                "id": "claims",
                "type": "text",
                "text": claim_text,
                "x": -580,
                "y": 220,
                "width": 360,
                "height": min(120 + row_n * 28, 420),
                "color": _CANVAS_COLORS["claims"],
            }
        )
        edges.append(
            {
                "id": "e-claims-center",
                "fromNode": "claims",
                "fromSide": "right",
                "toNode": center_id,
                "toSide": "left",
                "label": "权项",
                "color": _CANVAS_COLORS["claims"],
            }
        )

    try:
        from vault.schema_vault import appearance_canvas_cards, structure_canvas_cards
    except ImportError:
        from tools.patent_reader.vault.schema_vault import (  # type: ignore
            appearance_canvas_cards,
            structure_canvas_cards,
        )
    schema_cards = []
    if structure_schema:
        schema_cards.extend(structure_canvas_cards(structure_schema, x0=-520, y0=520))
    if appearance_schema:
        schema_cards.extend(appearance_canvas_cards(appearance_schema, x0=-520, y0=520))
    for i, card in enumerate(schema_cards):
        nodes.append(card)
        edges.append(
            {
                "id": f"e-schema-{card['id']}",
                "fromNode": card["id"],
                "fromSide": "right",
                "toNode": center_id,
                "toSide": "left",
                "label": "结构" if "structure" in card["id"] else "外观",
            }
        )

    rel_items = list(related.get("related_patents") or [])[:4]
    if rel_items:
        nodes.append(
            {
                "id": "grp-rel",
                "type": "group",
                "x": 480,
                "y": -200,
                "width": 340,
                "height": 40 + len(rel_items) * 150,
                "label": "关联专利",
                "color": _CANVAS_COLORS["group_rel"],
            }
        )
    y = -160
    for i, item in enumerate(rel_items):
        nid = f"rp{i}"
        path = str(item.get("path") or "").replace("\\", "/")
        link = path[:-3] if path.endswith(".md") else path
        other = str(item.get("title") or item.get("pub") or Path(path).stem)
        if "_解读_" in other:
            other = other.split("_解读_")[0]
        elif other.endswith("_解读"):
            other = other[: -len("_解读")]
        label = item.get("label") or "相关专利"
        nodes.append(
            {
                "id": nid,
                "type": "text",
                "text": f"## {other}\n\n*{label}*\n\n[[{link}|打开笔记]]",
                "x": 500,
                "y": y,
                "width": 300,
                "height": 130,
                "color": _CANVAS_COLORS["related"],
            }
        )
        edges.append(
            {
                "id": f"e-center-{nid}",
                "fromNode": center_id,
                "fromSide": "right",
                "toNode": nid,
                "toSide": "left",
                "label": label,
                "color": _CANVAS_COLORS["related"],
            }
        )
        y += 150

    y_dc = 200 if claim_text else 220
    for i, item in enumerate(related.get("disclosures") or []):
        nid = f"dc{i}"
        path = str(item.get("path") or "").replace("\\", "/")
        link = path[:-3] if path.endswith(".md") else path
        nodes.append(
            {
                "id": nid,
                "type": "text",
                "text": f"## 交底书\n\n[[{link}|打开]]",
                "x": -560,
                "y": y_dc + 320 + i * 160,
                "width": 300,
                "height": 120,
                "color": _CANVAS_COLORS["disclosure"],
            }
        )
        edges.append(
            {
                "id": f"e-dc-{nid}",
                "fromNode": nid,
                "fromSide": "right",
                "toNode": center_id,
                "toSide": "left",
                "label": "交底书",
                "color": _CANVAS_COLORS["disclosure"],
            }
        )

    # 公开线索卡（推测层；链到 clues/ 笔记）
    clue_list = list(clue_cards or [])[:6]
    if clue_list:
        clue_y0 = 420
        nodes.append(
            {
                "id": "grp-clues",
                "type": "group",
                "x": 480,
                "y": clue_y0 - 40,
                "width": 340,
                "height": 36 + len(clue_list) * 150,
                "label": "公开线索（推测）",
                "color": _CANVAS_COLORS["group_clue"],
            }
        )
        for i, card in enumerate(clue_list):
            nid = f"clue{i}"
            title = str(card.get("title") or "线索")[:40]
            conf = card.get("confidence") or "中"
            link = str(card.get("link") or "").replace("\\", "/")
            reason = str(card.get("reason") or "")[:64]
            claims = card.get("related_claims") or []
            fids = card.get("related_feature_ids") or []
            bits: list[str] = []
            if claims:
                bits.append("权" + "、".join(str(n) for n in claims[:4]))
            if fids:
                bits.append("·".join(str(x) for x in fids[:4]))
            claim_bit = "可能相关：" + " ".join(bits) if bits else "弱匹配未命中"
            text = (
                f"## {title}\n\n"
                f"*置信 {conf} · 推测*\n\n"
                f"{claim_bit}\n\n"
                f"{reason}\n\n"
                f"[[{link}|打开线索]]"
            )
            nodes.append(
                {
                    "id": nid,
                    "type": "text",
                    "text": text,
                    "x": 500,
                    "y": clue_y0 + i * 150,
                    "width": 300,
                    "height": 140,
                    "color": _CANVAS_COLORS["clue"],
                }
            )
            edges.append(
                {
                    "id": f"e-center-{nid}",
                    "fromNode": center_id,
                    "fromSide": "bottom",
                    "toNode": nid,
                    "toSide": "left",
                    "label": "线索",
                    "color": _CANVAS_COLORS["clue"],
                }
            )
            if claims and claim_text:
                edges.append(
                    {
                        "id": f"e-claims-{nid}",
                        "fromNode": "claims",
                        "fromSide": "right",
                        "toNode": nid,
                        "toSide": "bottom",
                        "label": "权" + "、".join(str(n) for n in claims[:3]),
                        "color": _CANVAS_COLORS["clue"],
                    }
                )

    glossary_nodes: list[dict] = []
    disclosures = related.get("disclosures") or []
    # 从 glossary_terms 预取 definition，resolve 后仍保留
    defn_map: dict[str, str] = {}
    for item in list(glossary_terms or []):
        if isinstance(item, dict):
            t = str(item.get("term") or "").strip()
            d = str(item.get("definition") or "").strip()
            if t and d:
                defn_map[t] = d

    if vault and glossary_terms:
        glossary_nodes = resolve_glossary_nodes(
            vault,
            glossary_dir,
            list(glossary_terms),
            create_stubs=create_glossary_stubs,
            source_pub=pub,
            papers_dir=papers_dir,
            note_rel=note_link,
            disclosures=disclosures,
            definitions=defn_map,
        )
    elif glossary_terms and glossary_root is not None:
        glossary_root.mkdir(parents=True, exist_ok=True)
        fake_vault = glossary_root.parent
        rel_dir = glossary_root.name
        glossary_nodes = resolve_glossary_nodes(
            fake_vault,
            rel_dir,
            list(glossary_terms),
            create_stubs=create_glossary_stubs,
            source_pub=pub,
            papers_dir=papers_dir,
            note_rel="",
            disclosures=disclosures,
            definitions=defn_map,
        )
        for g in glossary_nodes:
            if g.get("path"):
                g["path"] = f"{rel_dir}/{Path(g['path']).name}"
    elif glossary_terms:
        for item in list(glossary_terms)[:8]:
            if isinstance(item, dict):
                glossary_nodes.append(
                    {
                        "term": item.get("term"),
                        "path": "",
                        "has_file": False,
                        "definition": item.get("definition") or "",
                    }
                )
            else:
                glossary_nodes.append(
                    {"term": str(item), "path": "", "has_file": False, "definition": ""}
                )

    for g in glossary_nodes:
        if not g.get("definition") and g.get("term") in defn_map:
            g["definition"] = defn_map[g["term"]]

    show_terms = glossary_nodes[:6]
    if show_terms:
        cols = min(3, len(show_terms))
        rows = (len(show_terms) + cols - 1) // cols
        card_w, card_h, gap_x, gap_y = 240, 150, 16, 16
        grid_w = cols * card_w + (cols - 1) * gap_x
        grid_h = rows * card_h + (rows - 1) * gap_y
        gx = -grid_w // 2
        gy = 320
        nodes.append(
            {
                "id": "grp-term",
                "type": "group",
                "x": gx - 20,
                "y": gy - 40,
                "width": grid_w + 40,
                "height": grid_h + 56,
                "label": "术语（本文含义）",
                "color": _CANVAS_COLORS["group_term"],
            }
        )
        for i, g in enumerate(show_terms):
            nid = f"g{i}"
            term = g.get("term") or ""
            defn = _clip_canvas_text(str(g.get("definition") or "（见术语页）"), 90)
            col, row = i % cols, i // cols
            path = str(g.get("path") or "")
            if path and not path.endswith(".md"):
                link_target = path
            elif path:
                link_target = path[:-3]
            else:
                link_target = ""
            body = f"## {term}\n\n{defn}"
            if link_target:
                body += f"\n\n[[{link_target}|术语页]]"
            nodes.append(
                {
                    "id": nid,
                    "type": "text",
                    "text": body,
                    "x": gx + col * (card_w + gap_x),
                    "y": gy + row * (card_h + gap_y),
                    "width": card_w,
                    "height": card_h,
                    "color": _CANVAS_COLORS["term"],
                }
            )
            edges.append(
                {
                    "id": f"e-g-{nid}",
                    "fromNode": center_id,
                    "fromSide": "bottom",
                    "toNode": nid,
                    "toSide": "top",
                    "label": "术语",
                    "color": _CANVAS_COLORS["term"],
                }
            )

    # 仅非扫描页精修图，最多 1 张（可选）
    figs = [
        f
        for f in (figure_rels or [])
        if f and "page_" not in Path(f).name.lower() and "xref" not in Path(f).name.lower()
    ][:1]
    if figs:
        frel = figs[0].replace("\\", "/")
        nodes.append(
            {
                "id": "fig0",
                "type": "file",
                "file": frel,
                "x": 500,
                "y": y + 20,
                "width": 220,
                "height": 160,
                "color": "6",
            }
        )
        edges.append(
            {
                "id": "e-fig-0",
                "fromNode": center_id,
                "fromSide": "right",
                "toNode": "fig0",
                "toSide": "left",
                "label": "附图",
            }
        )

    return {"nodes": nodes, "edges": edges, "glossary_resolved": glossary_nodes}

def ensure_canvas_nav(content: str, canvas_rel: str, label: str = "专利族图谱") -> str:
    """写入指向 *.canvas 的导航；并清除无扩展名占位链接（点开会生成空 .md）。"""
    rel = canvas_rel.replace("\\", "/")
    if not rel.endswith(".canvas"):
        rel = f"{rel}.canvas"
    link = f"[[{rel}|{label}]]"
    # 去掉模板占位：[[..._图谱|专利族图谱]]（入库后生成）等无 .canvas 链接
    content = re.sub(
        r"^[ \t]*-?\s*\[\[[^\]]*_图谱(?:\|[^\]]*)?\]\][^\n]*\n?",
        "",
        content,
        flags=re.M,
    )
    if link in content:
        return content
    m = re.search(r"^##\s*Obsidian\s*导航\s*\n", content, re.M | re.I)
    if m:
        insert_at = m.end()
        return content[:insert_at] + f"- {link}\n" + content[insert_at:]
    return content
