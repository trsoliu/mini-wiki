"""库内专利解读笔记关联：规则打分、写边、双向回写、全局 Canvas。"""
from __future__ import annotations

import json
import re
from pathlib import Path

try:
    from common import slugify_pub
    from obsidian import (
        build_canvas,
        ensure_canvas_nav,
        parse_frontmatter,
        render_frontmatter,
    )
except ImportError:
    from tools.patent_reader.common import slugify_pub
    from tools.patent_reader.obsidian import (
        build_canvas,
        ensure_canvas_nav,
        parse_frontmatter,
        render_frontmatter,
    )

PUB_RE = re.compile(r"\b([A-Z]{2}\d{6,}[A-Z]?\d?)\b", re.I)
SECTION5_RE = re.compile(
    r"^##\s*五、专利内术语表([\s\S]*?)(?=^##\s*六、|\Z)",
    re.M,
)
RELATED_SECTION_RE = re.compile(
    r"^##\s*相关专利(?:（自动关联）)?\s*\n[\s\S]*?(?=^##\s+|\Z)",
    re.M,
)

RELATION_LABELS = {
    "explicit_cite": "正文互引",
    "same_assignee": "同申请人",
    "ipc_overlap": "IPC 相近",
    "shared_domain": "同领域",
    "shared_terms": "共术语",
    "model_hint": "模型判定",
    "improvement": "疑似改进",
    "family": "同族/系列",
}


def _ipc_prefix(ipc: str, n: int = 4) -> str:
    s = re.sub(r"\s+", "", (ipc or "").upper())
    return s[:n] if s else ""


def extract_glossary_terms_from_note(body: str) -> list[str]:
    m = SECTION5_RE.search(body)
    if not m:
        return []
    block = m.group(1)
    terms: list[str] = []
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0] in ("术语", "---", "----"):
            continue
        if re.match(r"^[-:]+$", cells[0]):
            continue
        term = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", cells[0])
        term = Path(term).name.strip()
        if term and term not in terms and len(term) <= 40:
            terms.append(term)
    return terms[:30]


def load_patent_notes(vault: Path, papers_dir: str) -> list[dict]:
    """扫描库内 *_解读_*.md 笔记。"""
    root = vault / papers_dir
    notes: list[dict] = []
    if not root.is_dir():
        return notes
    try:
        from obsidian import is_spurious_patent_note
    except ImportError:
        from tools.patent_reader.obsidian import is_spurious_patent_note

    for md in sorted(root.rglob("*.md")):
        if md.name.startswith("_") or "_解读_" not in md.name:
            continue
        if is_spurious_patent_note(md):
            continue
        text = md.read_text(encoding="utf-8", errors="replace")
        fm, _, body = parse_frontmatter(text)
        pub = str(fm.get("pub_number") or "").strip()
        if not pub:
            m = PUB_RE.search(md.stem)
            pub = m.group(1).upper() if m else slugify_pub(md.stem)
        assignees = fm.get("assignees") or []
        if isinstance(assignees, str):
            assignees = [assignees] if assignees else []
        rel = str(md.relative_to(vault)).replace("\\", "/")
        title_m = re.search(r"^#\s+(.+)$", body, re.M)
        title = title_m.group(1).strip() if title_m else pub
        notes.append(
            {
                "path": str(md),
                "rel": rel,
                "rel_no_ext": rel[:-3] if rel.endswith(".md") else rel,
                "pub": pub.upper(),
                "domain": str(fm.get("domain") or ""),
                "ipc": str(fm.get("ipc") or ""),
                "assignees": [str(a).strip() for a in assignees if str(a).strip()],
                "terms": extract_glossary_terms_from_note(body),
                "body": body,
                "fm": fm,
                "title": title,
            }
        )
    return notes


def score_pair(a: dict, b: dict) -> dict | None:
    """规则打分；低于阈值返回 None。"""
    if a["pub"] == b["pub"]:
        return None
    reasons: list[str] = []
    relations: list[str] = []
    score = 0.0

    # 正文显式出现对方公开号
    if b["pub"] and re.search(re.escape(b["pub"]), a.get("body") or "", re.I):
        score += 0.5
        relations.append("explicit_cite")
        reasons.append(f"A 正文提及 {b['pub']}")
    if a["pub"] and re.search(re.escape(a["pub"]), b.get("body") or "", re.I):
        score += 0.5
        relations.append("explicit_cite")
        reasons.append(f"B 正文提及 {a['pub']}")

    set_a = {x for x in a.get("assignees") or [] if x}
    set_b = {x for x in b.get("assignees") or [] if x}
    if set_a and set_b and set_a & set_b:
        score += 0.4
        relations.append("same_assignee")
        reasons.append("申请人重叠：" + "、".join(sorted(set_a & set_b)))

    pa, pb = _ipc_prefix(a.get("ipc") or ""), _ipc_prefix(b.get("ipc") or "")
    if pa and pb and (pa == pb or pa.startswith(pb[:3]) or pb.startswith(pa[:3])):
        score += 0.25
        relations.append("ipc_overlap")
        reasons.append(f"IPC 前缀相近：{pa} / {pb}")

    if a.get("domain") and a.get("domain") == b.get("domain") and a["domain"] != "未分类":
        score += 0.15
        relations.append("shared_domain")
        reasons.append(f"同领域：{a['domain']}")

    terms_a = set(a.get("terms") or [])
    terms_b = set(b.get("terms") or [])
    shared = sorted(terms_a & terms_b)
    if shared:
        bump = min(0.3, 0.1 * len(shared))
        score += bump
        relations.append("shared_terms")
        reasons.append("共术语：" + "、".join(shared[:6]))

    # 去重 relation，主关系取权重最高的一种标签
    relations = list(dict.fromkeys(relations))
    if score < 0.35 or not relations:
        return None
    primary = relations[0]
    for preferred in (
        "explicit_cite",
        "same_assignee",
        "ipc_overlap",
        "shared_terms",
        "shared_domain",
    ):
        if preferred in relations:
            primary = preferred
            break
    return {
        "pub_a": a["pub"],
        "pub_b": b["pub"],
        "rel_a": a["rel"],
        "rel_b": b["rel"],
        "score": round(min(1.0, score), 3),
        "relation": primary,
        "relations": relations,
        "reasons": reasons,
        "source": "rules",
    }


def merge_model_scores(
    edges: list[dict],
    model_scores: list[dict],
    notes_by_pub: dict[str, dict],
) -> list[dict]:
    """合并 Agent/模型给出的边（可抬高分数或新增）。"""
    index: dict[tuple[str, str], dict] = {}
    for e in edges:
        key = tuple(sorted([e["pub_a"].upper(), e["pub_b"].upper()]))
        index[key] = e

    for m in model_scores:
        pa = str(m.get("pub_a") or m.get("from") or "").upper().strip()
        pb = str(m.get("pub_b") or m.get("to") or "").upper().strip()
        if not pa or not pb or pa == pb:
            continue
        if pa not in notes_by_pub or pb not in notes_by_pub:
            continue
        key = tuple(sorted([pa, pb]))
        score = float(m.get("score") or 0.7)
        relation = str(m.get("relation") or "model_hint")
        rationale = str(m.get("rationale") or m.get("reason") or "模型提示")
        if key in index:
            cur = index[key]
            cur["score"] = round(min(1.0, max(cur["score"], score)), 3)
            if relation not in cur.get("relations", []):
                cur.setdefault("relations", []).append(relation)
            if score >= cur["score"]:
                cur["relation"] = relation
            cur["reasons"] = list(dict.fromkeys(cur.get("reasons", []) + [rationale]))
            cur["source"] = "rules+model"
        else:
            na, nb = notes_by_pub[pa], notes_by_pub[pb]
            index[key] = {
                "pub_a": pa,
                "pub_b": pb,
                "rel_a": na["rel"],
                "rel_b": nb["rel"],
                "score": round(min(1.0, score), 3),
                "relation": relation,
                "relations": [relation],
                "reasons": [rationale],
                "source": "model",
            }
    return list(index.values())


def discover_links(
    notes: list[dict],
    *,
    min_score: float = 0.45,
    model_scores: list[dict] | None = None,
    focus_pub: str = "",
) -> list[dict]:
    """两两打分并过滤。"""
    edges: list[dict] = []
    for i, a in enumerate(notes):
        for b in notes[i + 1 :]:
            if focus_pub:
                fp = focus_pub.upper()
                if a["pub"] != fp and b["pub"] != fp:
                    continue
            hit = score_pair(a, b)
            if hit:
                edges.append(hit)
    by_pub = {n["pub"]: n for n in notes if n.get("pub")}
    if model_scores:
        edges = merge_model_scores(edges, model_scores, by_pub)
    edges = [e for e in edges if e["score"] >= min_score]
    edges.sort(key=lambda e: -e["score"])
    return edges


def _edges_for_pub(edges: list[dict], pub: str) -> list[dict]:
    pub = pub.upper()
    out: list[dict] = []
    for e in edges:
        if e["pub_a"] == pub:
            out.append({**e, "other_pub": e["pub_b"], "other_rel": e["rel_b"]})
        elif e["pub_b"] == pub:
            out.append({**e, "other_pub": e["pub_a"], "other_rel": e["rel_a"]})
    return out


def _related_section_markdown(note: dict, neighbors: list[dict], vault: Path) -> str:
    lines = [
        "## 相关专利",
        "",
        "> 库内规则关联候选，**不构成法律意见**。",
        "",
        "| 公开号 | 关系 | 置信 | 依据 |",
        "| --- | --- | --- | --- |",
    ]
    for n in neighbors:
        other = n["other_pub"]
        other_rel = n["other_rel"]
        link_target = other_rel[:-3] if other_rel.endswith(".md") else other_rel
        label = RELATION_LABELS.get(n["relation"], n["relation"])
        reason = "；".join(n.get("reasons") or [])[:80]
        lines.append(
            f"| [[{link_target}|{other}]] | {label} | {n['score']:.2f} | {reason} |"
        )
    lines.append("")
    return "\n".join(lines)


def upsert_related_section(content: str, section_md: str) -> str:
    if RELATED_SECTION_RE.search(content):
        return RELATED_SECTION_RE.sub(section_md.rstrip() + "\n\n", content, count=1)
    # 插在免责声明之前，否则附录之后
    m = re.search(r"^##\s*十一、免责声明", content, re.M)
    if m:
        return content[: m.start()] + section_md + "\n" + content[m.start() :]
    m2 = re.search(r"^##\s*十、附录", content, re.M)
    if m2:
        # 放在附录之后、免责之前；若无免责则附录后
        end = content.find("\n## ", m2.end())
        if end == -1:
            return content.rstrip() + "\n\n" + section_md
        return content[:end] + "\n\n" + section_md + content[end:]
    return content.rstrip() + "\n\n" + section_md


def apply_links_to_note(
    note: dict,
    neighbors: list[dict],
    *,
    vault: Path,
) -> dict:
    """回写 frontmatter.related_pubs + 相关专利节。"""
    path = Path(note["path"])
    content = path.read_text(encoding="utf-8")
    fm, _, body = parse_frontmatter(content)
    pubs = [n["other_pub"] for n in neighbors]
    fm["related_pubs"] = list(dict.fromkeys(pubs))
    # 重建全文：fm + 可能已含相关节的 body
    full = render_frontmatter(fm) + body
    section = _related_section_markdown(note, neighbors, vault)
    full = upsert_related_section(full, section)
    path.write_text(full, encoding="utf-8")
    return {"path": note["rel"], "related_pubs": pubs, "count": len(pubs)}


def rebuild_note_canvas(
    vault: Path,
    note: dict,
    neighbors: list[dict],
    *,
    papers_dir: str,
    glossary_dir: str,
) -> str:
    """按关联结果刷新单篇图谱 Canvas（保留叙事/术语含义）。"""
    try:
        from obsidian import harvest_claim_summaries_from_note
        from write_patent_obsidian_note import (
            harvest_glossary_from_note,
            harvest_narrative_from_note,
        )
    except ImportError:
        from tools.patent_reader.obsidian import harvest_claim_summaries_from_note
        from tools.patent_reader.write_patent_obsidian_note import (
            harvest_glossary_from_note,
            harvest_narrative_from_note,
        )

    note_path = Path(note["path"])
    content = note_path.read_text(encoding="utf-8")
    fm, _, _ = parse_frontmatter(content)
    narrative = harvest_narrative_from_note(content)
    glossary = harvest_glossary_from_note(content)
    if not glossary:
        glossary = [{"term": t} for t in (note.get("terms") or [])[:6]]
    claim_summaries = harvest_claim_summaries_from_note(content)
    claim_tree = None
    ct = note_path.parent / "claim_tree.json"
    if ct.is_file():
        try:
            claim_tree = json.loads(ct.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            claim_tree = None

    try:
        from clue_vault import clue_cards_for_canvas, load_clues_sidecar
    except ImportError:
        from tools.patent_reader.clue_vault import (
            clue_cards_for_canvas,
            load_clues_sidecar,
        )

    note_dir_rel = str(note_path.parent.relative_to(vault)).replace("\\", "/")
    clue_cards = clue_cards_for_canvas(
        load_clues_sidecar(note_path.parent), note_dir_rel=note_dir_rel
    )

    related = {
        "related_patents": [
            {
                "path": n["other_rel"],
                "title": n["other_pub"],
                "label": RELATION_LABELS.get(n["relation"], n["relation"]),
            }
            for n in neighbors
        ],
        "disclosures": [],
    }
    canvas = build_canvas(
        vault=vault,
        papers_dir=papers_dir,
        note_rel_path=note["rel"],
        pub=note["pub"],
        title=note.get("title") or note["pub"],
        related=related,
        glossary_terms=glossary,
        glossary_dir=glossary_dir,
        create_glossary_stubs=False,
        meta={
            "domain": fm.get("domain") or note.get("domain") or "",
            "ipc": fm.get("ipc") or "",
            "assignees": fm.get("assignees") or note.get("assignees") or [],
            "evidence_scope": fm.get("evidence_scope") or "",
        },
        claim_tree=claim_tree,
        claim_summaries=claim_summaries,
        narrative=narrative,
        clue_cards=clue_cards,
    )
    canvas.pop("glossary_resolved", None)
    pub_slug = slugify_pub(note["pub"])
    canvas_path = note_path.parent / f"{pub_slug}_图谱.canvas"
    canvas_path.write_text(
        json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    canvas_rel = str(canvas_path.relative_to(vault)).replace("\\", "/")
    updated = ensure_canvas_nav(content, canvas_rel)
    if updated != content:
        note_path.write_text(updated, encoding="utf-8")
    return str(canvas_path)


_GLOBAL_COLORS = {
    "hub": "#0D9488",
    "legend": "#64748B",
    "patent": "#0284C7",
    "bridge": "#CA8A04",
    "group": "#6366F1",
    "edge": "#94A3B8",
}


def _clip(text: str, limit: int) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) <= limit:
        return s
    return s[: limit - 1] + "…"


def _note_display_title(note: dict) -> str:
    title = str(note.get("title") or note.get("pub") or "")
    for prefix in ("专利解读：", "专利解读:", "解读："):
        if title.startswith(prefix):
            title = title[len(prefix) :].strip()
    if "_解读_" in title:
        title = title.split("_解读_")[0]
    return title or note.get("pub") or ""


def _harvest_one_liner(body: str) -> str:
    """从笔记正文抽一句摘要（一节 / 叙事）。"""
    try:
        from write_patent_obsidian_note import harvest_narrative_from_note
    except ImportError:
        from tools.patent_reader.write_patent_obsidian_note import (
            harvest_narrative_from_note,
        )

    narr = harvest_narrative_from_note(body or "")
    for key in ("one_liner", "approach", "problem", "effect"):
        t = str(narr.get(key) or "").strip()
        if t:
            return _clip(t, 72)
    m = re.search(
        r"^##\s*一、[^\n]*\n+([\s\S]*?)(?=^##\s|\Z)",
        body or "",
        re.M,
    )
    if m:
        para = re.sub(r"^>\s*.*$", "", m.group(1), flags=re.M)
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            return _clip(para, 72)
    return ""


def _patent_card_text(note: dict, *, papers_dir: str) -> str:
    pub = note["pub"]
    title = _note_display_title(note)
    domain = note.get("domain") or "—"
    ipc = note.get("ipc") or "—"
    asg = "、".join((note.get("assignees") or [])[:2]) or "—"
    terms = "、".join((note.get("terms") or [])[:5]) or "—"
    one = _harvest_one_liner(note.get("body") or "")
    note_link = note.get("rel_no_ext") or (
        note["rel"][:-3] if note["rel"].endswith(".md") else note["rel"]
    )
    canvas_rel = str(Path(note["rel"]).parent / f"{slugify_pub(pub)}_图谱.canvas").replace(
        "\\", "/"
    )
    lines = [
        f"## `{pub}`",
        "",
        f"**{title}**" if title and title != pub else "",
        "",
        f"- **领域** {domain}",
        f"- **IPC** `{ipc}`",
        f"- **申请人** {asg}",
        f"- **术语** {terms}",
    ]
    if one:
        lines.extend(["", f"> {one}"])
    lines.extend(
        [
            "",
            f"[[{note_link}|打开解读]] · [[{canvas_rel}|单篇图谱]]",
            f"[[{papers_dir}/_专利解读索引|索引]]",
        ]
    )
    return "\n".join(x for x in lines if x is not None)


def _bridge_card_text(edge: dict) -> str:
    label = RELATION_LABELS.get(edge["relation"], edge["relation"])
    rels = [
        RELATION_LABELS.get(r, r)
        for r in (edge.get("relations") or [edge["relation"]])
    ]
    rels = list(dict.fromkeys(rels))
    reasons = edge.get("reasons") or []
    lines = [
        f"## {label} · {edge['score']:.2f}",
        "",
        f"`{edge['pub_a']}` ↔ `{edge['pub_b']}`",
        "",
        "**信号** " + " · ".join(rels),
    ]
    if reasons:
        lines.append("")
        lines.append("**依据**")
        for r in reasons[:4]:
            lines.append(f"- {_clip(r, 56)}")
    src = edge.get("source") or "rules"
    lines.extend(["", f"*来源：{src}*"])
    return "\n".join(lines)


def _layout_patent_positions(notes: list[dict]) -> dict[str, tuple[int, int]]:
    """按领域分列；单领域且篇数≤4 时横向排布，便于看桥卡。"""
    by_domain: dict[str, list[dict]] = {}
    for note in notes:
        by_domain.setdefault(note.get("domain") or "未分类", []).append(note)
    domains = sorted(by_domain.keys())
    col_w, row_h = 520, 360
    pos: dict[str, tuple[int, int]] = {}

    # 单领域少量：左右排开
    if len(domains) == 1 and len(notes) <= 4:
        gap = 720
        start = -((len(notes) - 1) * gap) // 2
        for j, note in enumerate(notes):
            pos[note["pub"]] = (start + j * gap, 40)
        return pos

    start_x = -((len(domains) - 1) * col_w) // 2
    for di, dom in enumerate(domains):
        items = by_domain[dom]
        for j, note in enumerate(items):
            pos[note["pub"]] = (start_x + di * col_w, j * row_h)
    return pos


def build_global_links_canvas(
    vault: Path,
    notes: list[dict],
    edges: list[dict],
    *,
    papers_dir: str,
) -> Path:
    """库级全局关联 Canvas：富文本专利卡 + 关联桥卡 + 统计/图例。"""
    nodes: list[dict] = []
    canvas_edges: list[dict] = []
    pos = _layout_patent_positions(notes)
    id_by_pub: dict[str, str] = {}

    # 统计
    domains = sorted({n.get("domain") or "未分类" for n in notes})
    rel_counts: dict[str, int] = {}
    for e in edges:
        k = RELATION_LABELS.get(e["relation"], e["relation"])
        rel_counts[k] = rel_counts.get(k, 0) + 1
    hub_lines = [
        "# 专利关联总览",
        "",
        f"**{len(notes)}** 篇解读 · **{len(edges)}** 条关联",
        f"**领域** {' · '.join(domains) if domains else '—'}",
        "",
        "边 = 规则/模型信号（同申请人 / IPC / 共术语 / 正文互引等）",
        "**不构成法律意见**",
        "",
        f"[[{papers_dir}/_专利解读索引|打开索引]]",
    ]
    nodes.append(
        {
            "id": "hub",
            "type": "text",
            "text": "\n".join(hub_lines),
            "x": -260,
            "y": -320,
            "width": 520,
            "height": 220,
            "color": _GLOBAL_COLORS["hub"],
        }
    )

    legend_bits = [
        f"- {lab} ×{cnt}" for lab, cnt in sorted(rel_counts.items(), key=lambda x: -x[1])
    ] or ["- （暂无过阈关联）"]
    nodes.append(
        {
            "id": "legend",
            "type": "text",
            "text": "## 关系图例\n\n" + "\n".join(legend_bits) + "\n\n*桥卡写明依据*",
            "x": 320,
            "y": -300,
            "width": 280,
            "height": 200,
            "color": _GLOBAL_COLORS["legend"],
        }
    )
    canvas_edges.append(
        {
            "id": "e-hub-legend",
            "fromNode": "hub",
            "fromSide": "right",
            "toNode": "legend",
            "toSide": "left",
            "label": "图例",
            "color": _GLOBAL_COLORS["edge"],
        }
    )

    # 领域分组框
    by_domain: dict[str, list[dict]] = {}
    for note in notes:
        by_domain.setdefault(note.get("domain") or "未分类", []).append(note)
    for di, (dom, items) in enumerate(sorted(by_domain.items())):
        xs = [pos[n["pub"]][0] for n in items]
        ys = [pos[n["pub"]][1] for n in items]
        card_w, card_h = 400, 300
        pad = 36
        nodes.append(
            {
                "id": f"grp-{di}",
                "type": "group",
                "x": min(xs) - pad,
                "y": min(ys) - pad - 8,
                "width": (max(xs) - min(xs)) + card_w + pad * 2,
                "height": (max(ys) - min(ys)) + card_h + pad * 2 + 16,
                "label": f"领域 · {dom}（{len(items)}）",
                "color": _GLOBAL_COLORS["group"],
            }
        )

    for i, note in enumerate(notes):
        nid = f"p{i}"
        id_by_pub[note["pub"]] = nid
        x, y = pos[note["pub"]]
        nodes.append(
            {
                "id": nid,
                "type": "text",
                "text": _patent_card_text(note, papers_dir=papers_dir),
                "x": x,
                "y": y,
                "width": 400,
                "height": 300,
                "color": _GLOBAL_COLORS["patent"],
            }
        )
        canvas_edges.append(
            {
                "id": f"e-hub-{nid}",
                "fromNode": "hub",
                "fromSide": "bottom",
                "toNode": nid,
                "toSide": "top",
                "label": "收录",
                "color": _GLOBAL_COLORS["hub"],
            }
        )

    # 关联桥卡：落在两端中点
    for i, e in enumerate(edges):
        fa, fb = id_by_pub.get(e["pub_a"]), id_by_pub.get(e["pub_b"])
        if not fa or not fb:
            continue
        xa, ya = pos[e["pub_a"]]
        xb, yb = pos[e["pub_b"]]
        bridge_id = f"br{i}"
        # 横排：桥卡落在中缝略上；纵排：落在右侧
        if abs(ya - yb) < 80 and abs(xa - xb) > 200:
            bx = (xa + xb) // 2 - 160
            by = min(ya, yb) - 280
        elif abs(xa - xb) < 80:
            bx = max(xa, xb) + 440
            by = (ya + yb) // 2
        else:
            bx = (xa + xb) // 2 - 160
            by = (ya + yb) // 2 + 60
        nodes.append(
            {
                "id": bridge_id,
                "type": "text",
                "text": _bridge_card_text(e),
                "x": bx,
                "y": by,
                "width": 320,
                "height": 240,
                "color": _GLOBAL_COLORS["bridge"],
            }
        )
        label = f"{RELATION_LABELS.get(e['relation'], e['relation'])} {e['score']:.2f}"
        canvas_edges.append(
            {
                "id": f"link{i}a",
                "fromNode": fa,
                "fromSide": "right",
                "toNode": bridge_id,
                "toSide": "left",
                "label": label,
                "color": _GLOBAL_COLORS["bridge"],
            }
        )
        canvas_edges.append(
            {
                "id": f"link{i}b",
                "fromNode": bridge_id,
                "fromSide": "right",
                "toNode": fb,
                "toSide": "left",
                "label": "",
                "color": _GLOBAL_COLORS["bridge"],
            }
        )

    out = vault / papers_dir / "_专利关联.canvas"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"nodes": nodes, "edges": canvas_edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # 索引页补链
    index = vault / papers_dir / "_专利解读索引.md"
    if index.is_file():
        body = index.read_text(encoding="utf-8")
        link = f"[[{papers_dir}/_专利关联.canvas|专利关联总览]]"
        # 去掉无 .canvas 的旧链接，避免点出空 md
        body2 = re.sub(
            r"^[ \t]*-?\s*\[\[[^\]]*_专利关联(?!\.canvas)(?:\|[^\]]*)?\]\][^\n]*\n?",
            "",
            body,
            flags=re.M,
        )
        if link not in body2:
            if "## 关联图谱" in body2 and link not in body2:
                body2 = body2.replace(
                    "## 关联图谱",
                    f"## 关联图谱\n\n- {link}",
                    1,
                )
            elif "## 笔记列表" in body2:
                body2 = body2.replace(
                    "## 笔记列表",
                    f"## 关联图谱\n\n- {link}\n\n## 笔记列表",
                    1,
                )
            else:
                body2 = body2.rstrip() + f"\n\n## 关联图谱\n\n- {link}\n"
        if body2 != body:
            index.write_text(body2, encoding="utf-8")
    return out


def run_link_pipeline(
    vault: Path,
    *,
    papers_dir: str = "Research/Patents",
    glossary_dir: str = "Research/术语",
    min_score: float = 0.45,
    model_scores: list[dict] | None = None,
    focus_pub: str = "",
    refresh_canvas: bool = True,
    refresh_global_canvas: bool = True,
    dry_run: bool = False,
) -> dict:
    notes = load_patent_notes(vault, papers_dir)
    edges = discover_links(
        notes,
        min_score=min_score,
        model_scores=model_scores,
        focus_pub=focus_pub,
    )
    updates: list[dict] = []
    canvases: list[str] = []
    if not dry_run:
        for note in notes:
            neighbors = _edges_for_pub(edges, note["pub"])
            if not neighbors:
                continue
            updates.append(apply_links_to_note(note, neighbors, vault=vault))
            if refresh_canvas:
                canvases.append(
                    rebuild_note_canvas(
                        vault,
                        note,
                        neighbors,
                        papers_dir=papers_dir,
                        glossary_dir=glossary_dir,
                    )
                )
        global_path = ""
        if refresh_global_canvas and edges:
            global_path = str(
                build_global_links_canvas(vault, notes, edges, papers_dir=papers_dir)
            )
    else:
        global_path = ""

    return {
        "vault": str(vault),
        "note_count": len(notes),
        "edge_count": len(edges),
        "edges": edges,
        "updated_notes": updates,
        "canvases": canvases,
        "global_canvas": global_path if not dry_run else "",
        "dry_run": dry_run,
        "min_score": min_score,
    }
