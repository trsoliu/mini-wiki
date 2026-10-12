"""权利要求树：本项新增、mermaid、笔记第三节与 Canvas 权项卡。"""
from __future__ import annotations

import json
import re
from pathlib import Path

def _descendants_of(nodes: list[dict], root: int) -> set[int]:
    """返回 root 及其所有从属权利要求编号。"""
    by_parent: dict[int | None, list[int]] = {}
    for n in nodes:
        by_parent.setdefault(n.get("parent"), []).append(n["number"])
    desc: set[int] = {root}
    stack = [root]
    while stack:
        cur = stack.pop()
        for child in by_parent.get(cur, []):
            if child not in desc:
                desc.add(child)
                stack.append(child)
    return desc


def claim_delta_text(
    text_preview: str,
    *,
    is_independent: bool = False,
    limit: int = 72,
) -> str:
    """从权项原文预览抽出「本项新增」短句（启发式降级；优先用 Agent claim_deltas）。"""
    t = re.sub(r"\s+", " ", (text_preview or "").strip())
    t = re.sub(
        r"^如权利要求[\d、或与以及至到\s]+所述的[^，。；]{0,80}[，,；;]?\s*",
        "",
        t,
    )
    t = re.sub(r"^其特征在于[：:]\s*", "", t)
    if is_independent:
        t = re.sub(r"^一种", "", t)
    # 截到首个长分句，避免整段配方灌进表
    for sep in ("；", ";", "。"):
        if sep in t and t.index(sep) >= 12:
            t = t.split(sep, 1)[0]
            break
    t = t.strip(" ，,;；")
    if len(t) > limit:
        t = t[: limit - 1] + "…"
    return t or "（见原文）"


def load_claim_deltas(raw) -> dict[int, str]:
    """解析 Agent「本项新增」JSON。

    支持：
    - {"deltas":[{"claim":1,"delta":"…"}, …]}
    - {"1":"…","2":"…"} / {"deltas":{"1":"…"}}
    - [{"claim":1,"delta":"…"}] / [{"number":1,"summary":"…"}]
    """
    out: dict[int, str] = {}
    if raw is None:
        return out
    if isinstance(raw, Path):
        if not raw.is_file():
            return out
        try:
            raw = json.loads(raw.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return out
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("deltas"), list):
            items = raw["deltas"]
        elif isinstance(raw.get("deltas"), dict):
            items = [
                {"claim": k, "delta": v} for k, v in raw["deltas"].items()
            ]
        elif isinstance(raw.get("claim_deltas"), (list, dict)):
            return load_claim_deltas(raw.get("claim_deltas"))
        else:
            # 纯映射：键为权号
            items = [{"claim": k, "delta": v} for k, v in raw.items() if str(k).isdigit() or isinstance(k, int)]
    else:
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        num = item.get("claim", item.get("number", item.get("id")))
        text = item.get("delta", item.get("summary", item.get("text", item.get("本项新增"))))
        try:
            n = int(num)
        except (TypeError, ValueError):
            continue
        s = re.sub(r"\s+", " ", str(text or "").strip())
        if n > 0 and s:
            out[n] = s
    return out

def claim_deltas_from_tree(claim_tree: dict | None) -> dict[int, str]:
    """若 claim_tree.nodes[].delta / agent_delta 已由 Agent 写入，则回收。"""
    out: dict[int, str] = {}
    if not claim_tree:
        return out
    for n in claim_tree.get("nodes") or []:
        num = n.get("number")
        text = n.get("delta") or n.get("agent_delta") or n.get("summary")
        if num is None or not text:
            continue
        try:
            out[int(num)] = re.sub(r"\s+", " ", str(text).strip())
        except (TypeError, ValueError):
            continue
    return out


def merge_claim_summaries(*parts: dict[int, str] | None) -> dict[int, str]:
    """后写覆盖先写。推荐顺序：heuristic←note←tree←agent。"""
    out: dict[int, str] = {}
    for part in parts:
        for k, v in (part or {}).items():
            try:
                n = int(k)
            except (TypeError, ValueError):
                continue
            s = re.sub(r"\s+", " ", str(v or "").strip())
            if n > 0 and s:
                out[n] = s
    return out


def _mermaid_escape(s: str) -> str:
    return (
        (s or "")
        .replace("\\", "/")
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", " ")
    )


def claim_tree_to_mermaid(
    claim_tree: dict,
    pub: str = "",
    *,
    summaries: dict[int, str] | None = None,
) -> str:
    """由 claim_tree.json 生成 mermaid（短标签；独立权=子图）。"""
    nodes = claim_tree.get("nodes") or []
    if not nodes:
        return "flowchart TB\n  empty[无权利要求树数据]"
    summaries = summaries or {}
    roots = claim_tree.get("roots") or [
        n["number"] for n in nodes if n.get("is_independent")
    ]
    by_num = {n["number"]: n for n in nodes if n.get("number") is not None}
    lines = [
        "flowchart TB",
        "  classDef ind fill:#4F46E5,stroke:#312E81,color:#fff",
        "  classDef dep fill:#F8FAFC,stroke:#64748B,color:#0F172A",
    ]
    if pub:
        lines.append(f'  meta["{_mermaid_escape(pub)}"]:::ind')
    for root in roots:
        family = sorted(_descendants_of(nodes, root))
        sg_id = f"sg{root}"
        root_n = by_num.get(root) or {}
        root_raw = summaries.get(root) or claim_delta_text(
            str(root_n.get("text_preview") or ""),
            is_independent=True,
            limit=28,
        )
        if len(root_raw) > 28:
            root_raw = root_raw[:27] + "…"
        root_gist = _mermaid_escape(root_raw)
        lines.append(f'  subgraph {sg_id}["独立权 {root} · {root_gist}"]')
        for num in family:
            n = by_num.get(num) or {}
            raw = summaries.get(num) or claim_delta_text(
                str(n.get("text_preview") or ""),
                is_independent=bool(n.get("is_independent")),
                limit=22,
            )
            if len(raw) > 22:
                raw = raw[:21] + "…"
            gist = _mermaid_escape(raw)
            if n.get("is_independent"):
                lines.append(f'    c{num}["权{num} 独立\\n{gist}"]:::ind')
            else:
                parent = n.get("parent")
                lines.append(f'    c{num}["权{num} ←{parent}\\n{gist}"]:::dep')
        for num in family:
            n = by_num.get(num) or {}
            parent = n.get("parent")
            if parent in family:
                lines.append(f"    c{parent} --> c{num}")
        lines.append("  end")
        if pub:
            lines.append(f"  meta --> c{root}")
    # 多独立权时弱连（产品↔方法）
    if len(roots) >= 2:
        lines.append(f"  c{roots[0]} -.相关.- c{roots[1]}")
    return "\n".join(lines)


def _claim_tree_branch_prefix(
    num: int,
    by_num: dict[int, dict],
    children: dict[int | None, list[int]],
) -> str:
    """为权项生成树形前缀：◆ / ├─ / └─ / │ 等（单一视图表达从属）。"""
    n = by_num.get(num) or {}
    if n.get("is_independent") or n.get("parent") is None:
        return "◆"
    parent = n.get("parent")
    # 根 → parent 路径（用于画左侧竖线）
    path_to_parent: list[int] = []
    cur = parent
    guard = 0
    while cur is not None and guard < 32:
        path_to_parent.append(int(cur))
        cur = (by_num.get(cur) or {}).get("parent")
        guard += 1
    path_to_parent.reverse()
    prefix = ""
    for anc in path_to_parent[:-1]:
        ap = (by_num.get(anc) or {}).get("parent")
        # 独立权之间不互画竖线（多根树并排）
        if ap is None:
            prefix += "　"
            continue
        sibs = children.get(ap, [])
        prefix += "　" if sibs and sibs[-1] == anc else "│ "
    sibs = children.get(parent, [])
    prefix += "└─" if sibs and sibs[-1] == num else "├─"
    return prefix


def render_claim_tree_markdown(
    claim_tree: dict,
    *,
    pub: str = "",
    summaries: dict[int, str] | None = None,
    include_mermaid: bool = False,
) -> str:
    """第三节「权利要求树」：单一树形一览表（结构+新增合在一起）。

    mermaid 默认不嵌入正文（避免与表重复）；需要时可 include_mermaid=True
    或单独使用 claim_mermaid.mmd。
    """
    rows = _claim_tree_rows(claim_tree, summaries=summaries, delta_limit=56)
    if not rows:
        return (
            "## 三、权利要求树\n\n"
            "> 暂无结构化权项树；请对照说明书权利要求书阅读。\n"
        )
    ind_count = sum(1 for b, _, _ in rows if b == "◆")
    dep_count = len(rows) - ind_count
    lines = [
        "## 三、权利要求树",
        "",
        f"> 共 **{len(rows)}** 项 · 独立 **{ind_count}** / 从属 **{dep_count}**。"
        "下表一列看清从属与新增；独立权展开见**第四节**。",
        "",
        "| 结构 | 权 | 本项新增 |",
        "| --- | ---: | --- |",
    ]
    for branch, num, delta in rows:
        lines.append(f"| `{branch}` | {num} | {delta.replace('|', '\\|')} |")

    if include_mermaid:
        mmd = claim_tree_to_mermaid(claim_tree, pub, summaries=summaries)
        lines.extend(
            [
                "",
                "> [!note]- 图形示意（可选）",
                "> 与上表同一棵树，仅供偏好流程图的读者。",
                ">",
                "> ```mermaid",
            ]
        )
        for ml in mmd.splitlines():
            lines.append(f"> {ml}")
        lines.append("> ```")

    return "\n".join(lines).rstrip() + "\n"


def harvest_claim_summaries_from_note(content: str) -> dict[int, str]:
    """从旧版缩进树/表中回收人工写过的短摘要。"""
    m = re.search(
        r"^##\s*三、\s*权利要求树\s*\n([\s\S]*?)(?=^##\s*四、|\Z)",
        content,
        re.M,
    )
    if not m:
        return {}
    sec = m.group(1)
    out: dict[int, str] = {}
    for mm in re.finditer(
        r"\*\*权\s*(\d+)[^*]*\*\*[：:]\s*(.+?)(?=\n|$)",
        sec,
    ):
        out[int(mm.group(1))] = mm.group(2).strip()
    # 旧四列表：权|类型|从属|本项新增
    for mm in re.finditer(
        r"^\|\s*(\d+)\s*\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+)\|",
        sec,
        re.M,
    ):
        num = int(mm.group(1))
        cell = mm.group(2).strip()
        if cell and cell not in ("本项新增", "---"):
            out.setdefault(num, cell)
    # 新三列表：结构|权|本项新增
    for mm in re.finditer(
        r"^\|\s*`?[^|]*`?\s*\|\s*(\d+)\s*\|\s*([^|]+)\|",
        sec,
        re.M,
    ):
        num = int(mm.group(1))
        cell = mm.group(2).strip()
        if cell and cell not in ("本项新增", "---", "权"):
            out.setdefault(num, cell)
    return out


def upsert_claim_tree_section(content: str, section_md: str) -> str:
    """用新版第三节替换笔记中的「三、权利要求树」。"""
    section_md = section_md.rstrip() + "\n\n"
    pat = re.compile(
        r"^##\s*三、\s*权利要求树\s*\n[\s\S]*?(?=^##\s*四、|\Z)",
        re.M,
    )
    if pat.search(content):
        return pat.sub(section_md, content, count=1)
    # 插在第二节后
    m = re.search(r"^##\s*二、.*$", content, re.M)
    if m:
        rest = content[m.end() :]
        m2 = re.search(r"^##\s+", rest, re.M)
        if m2:
            ins = m.end() + m2.start()
            return content[:ins] + section_md + content[ins:]
    return content.rstrip() + "\n\n" + section_md
def _claim_tree_rows(
    claim_tree: dict,
    *,
    summaries: dict[int, str] | None = None,
    delta_limit: int = 40,
) -> list[tuple[str, int, str]]:
    """统一权项树行：(结构前缀, 权号, 本项新增)。与笔记第三节同构。"""
    nodes = claim_tree.get("nodes") or []
    if not nodes:
        return []
    summaries = dict(summaries or {})
    by_num = {n["number"]: n for n in nodes if n.get("number") is not None}
    for n in nodes:
        num = n.get("number")
        if num is None:
            continue
        if num in summaries and str(summaries[num]).strip():
            summaries[num] = re.sub(r"\s+", " ", str(summaries[num]).strip())
            if len(summaries[num]) > delta_limit:
                summaries[num] = summaries[num][: delta_limit - 1] + "…"
            continue
        summaries[num] = claim_delta_text(
            str(n.get("text_preview") or ""),
            is_independent=bool(n.get("is_independent")),
            limit=delta_limit,
        )

    children: dict[int | None, list[int]] = {}
    for n in nodes:
        parent = None if n.get("is_independent") else n.get("parent")
        children.setdefault(parent, []).append(n["number"])
    for k in children:
        children[k] = sorted(children[k])

    def _walk(num: int, acc: list[int]) -> None:
        if num in acc:
            return
        acc.append(num)
        for ch in children.get(num, []):
            _walk(ch, acc)

    order: list[int] = []
    roots = list(
        dict.fromkeys(
            [n["number"] for n in nodes if n.get("is_independent")]
            or (claim_tree.get("roots") or [])
        )
    )
    for r in roots:
        _walk(int(r), order)
    for num in sorted(by_num.keys()):
        if num not in order:
            order.append(num)

    rows: list[tuple[str, int, str]] = []
    for num in order:
        n = by_num[num]
        if n.get("is_independent") or n.get("parent") is None:
            branch = "◆"
        else:
            branch = _claim_tree_branch_prefix(num, by_num, children)
        rows.append((branch, num, summaries.get(num) or "—"))
    return rows


def _claim_tree_card_text(
    claim_tree: dict | None,
    pub: str,
    *,
    summaries: dict[int, str] | None = None,
) -> str:
    """Canvas 权项卡：与笔记第三节同一套树形表（更短一句）。"""
    if not claim_tree:
        return ""
    rows = _claim_tree_rows(claim_tree, summaries=summaries, delta_limit=32)
    if not rows:
        return ""
    ind = sum(1 for b, _, _ in rows if b == "◆")
    lines = [
        f"## 权项树 · `{pub}`",
        "",
        f"独立 {ind} / 共 {len(rows)} · 与笔记第三节同构",
        "",
        "| 结构 | 权 | 本项新增 |",
        "| --- | ---: | --- |",
    ]
    for branch, num, delta in rows[:14]:
        lines.append(f"| `{branch}` | {num} | {delta.replace('|', '\\|')} |")
    if len(rows) > 14:
        lines.append(f"| … |  | 另 {len(rows) - 14} 项 |")
    return "\n".join(lines)

