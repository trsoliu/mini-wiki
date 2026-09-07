"""审查答复 · Obsidian oa 目录布局（方案 C）。

结构：
  oa/
    _OA索引.md
    _OA看板.base
    _OA关联.canvas
    cases/history/   # 已结案 / 可检索历史案
    pending/         # 待答复通知书
    drafts/          # 入库前人审草稿

入库与 refresh 会：迁移旧平铺文件、写索引/看板/关联 Canvas、
对比文件有解读笔记时链到 Research/Patents。
经验手册在 oa/playbooks/，刷新索引时列出，但不进入案例检索/向量。
"""
from __future__ import annotations

import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from case_md import dump_case_markdown, parse_case_markdown

STATUS_HISTORY = "history"
STATUS_PENDING = "pending"
STATUS_DRAFT = "draft"

STATUS_ALIASES = {
    "history": STATUS_HISTORY,
    "hist": STATUS_HISTORY,
    "done": STATUS_HISTORY,
    "closed": STATUS_HISTORY,
    "pending": STATUS_PENDING,
    "todo": STATUS_PENDING,
    "draft": STATUS_DRAFT,
    "drafts": STATUS_DRAFT,
}

SKIP_NOTE_NAMES = {
    "_OA索引.md",
    "_OA看板.base",
    "_OA关联.canvas",
}

DEFECT_ZH = {
    "novelty": "新颖性",
    "inventiveness": "创造性",
    "clarity": "清楚性",
    "support": "支持",
    "disclosure": "充分公开",
    "formality": "形式缺陷",
    "other": "其他",
}

OUTCOME_ZH = {
    "granted": "授权",
    "rejected": "驳回",
    "pending": "待定/审理中",
    "withdrawn": "撤回",
    "unknown": "未知",
    "amended_then_granted": "修改后授权",
}

STATUS_ZH = {
    STATUS_HISTORY: "历史案",
    STATUS_PENDING: "待答复",
    STATUS_DRAFT: "草稿",
}


def label_defect(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return "—"
    return DEFECT_ZH.get(s.lower(), s)


def label_outcome(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return "—"
    return OUTCOME_ZH.get(s.lower(), s)


def label_defects(items: Any) -> str:
    if not items:
        return "—"
    if not isinstance(items, list):
        items = [items]
    parts = [label_defect(x) for x in items if str(x).strip()]
    return "、".join(parts) if parts else "—"


_NAV_MARK = "[[oa/_OA索引|_OA索引]]"
_SECTION_RELATED = "## 关联案"
_SECTION_COMPARE = "## 对比文件"


def normalize_status(raw: Any, *, default: str = STATUS_HISTORY) -> str:
    s = str(raw or "").strip().lower()
    if not s:
        return default
    return STATUS_ALIASES.get(s, default if s not in STATUS_ALIASES.values() else s)


def oa_rel_from_cfg(cfg: dict | None = None) -> str:
    cfg = cfg or {}
    rel = str(cfg.get("obsidian_oa_dir") or "").strip()
    if rel:
        return rel.replace("\\", "/").strip("/")
    cases = str(cfg.get("obsidian_cases_dir") or "oa/cases").replace("\\", "/")
    if cases.endswith("/cases"):
        return cases[: -len("/cases")] or "oa"
    if cases == "cases":
        return "oa"
    return "oa"


def resolve_oa_root(cfg: dict, vault: str | Path | None) -> Path:
    rel = oa_rel_from_cfg(cfg)
    if vault:
        return Path(vault).expanduser().resolve() / rel
    from config import oa_home

    return oa_home()


def status_subdir(oa_root: Path, status: str) -> Path:
    st = normalize_status(status)
    if st == STATUS_PENDING:
        return oa_root / "pending"
    if st == STATUS_DRAFT:
        return oa_root / "drafts"
    return oa_root / "cases" / "history"


def note_path_for(oa_root: Path, case_id: str, status: str) -> Path:
    return status_subdir(oa_root, status) / f"{case_id}.md"


def ensure_oa_dirs(oa_root: Path) -> list[str]:
    actions: list[str] = []
    for sub in (
        oa_root / "cases" / "history",
        oa_root / "pending",
        oa_root / "drafts",
        oa_root / "playbooks",
    ):
        if not sub.is_dir():
            sub.mkdir(parents=True, exist_ok=True)
            actions.append(f"mkdir:{sub}")
    return actions


def migrate_legacy_layout(oa_root: Path) -> list[str]:
    """把旧平铺 oa/cases/*.md 与 _drafts 迁到 history / drafts。"""
    actions = ensure_oa_dirs(oa_root)
    cases = oa_root / "cases"
    history = cases / "history"
    drafts = oa_root / "drafts"

    legacy_drafts = cases / "_drafts"
    if legacy_drafts.is_dir():
        for p in sorted(legacy_drafts.glob("*.md")):
            dest = drafts / p.name
            if dest.exists():
                actions.append(f"skip_exists:{dest}")
                continue
            shutil.move(str(p), str(dest))
            actions.append(f"move:{p.name}->drafts/")
        try:
            if not any(legacy_drafts.iterdir()):
                legacy_drafts.rmdir()
                actions.append("rmdir:cases/_drafts")
        except OSError:
            pass

    if cases.is_dir():
        for p in sorted(cases.glob("*.md")):
            if p.name.startswith("_") or p.name in SKIP_NOTE_NAMES:
                continue
            dest = history / p.name
            if dest.exists():
                actions.append(f"skip_exists:{dest}")
                continue
            shutil.move(str(p), str(dest))
            actions.append(f"move:{p.name}->cases/history/")
    return actions


def _rel_to(path: Path, root: Path) -> str | None:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


def _wiki_path(path: Path, vault: Path | None, oa_root: Path) -> str:
    rel = None
    if vault:
        rel = _rel_to(path, vault)
    if rel is None:
        under_oa = _rel_to(path, oa_root)
        if under_oa is not None:
            rel = f"{oa_root.name}/{under_oa}"
        else:
            rel = path.as_posix()
    if rel.endswith(".md"):
        rel = rel[:-3]
    return rel


def list_notes_by_status(oa_root: Path) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {
        STATUS_HISTORY: [],
        STATUS_PENDING: [],
        STATUS_DRAFT: [],
    }
    for st in out:
        d = status_subdir(oa_root, st)
        if d.is_dir():
            out[st] = sorted(p for p in d.glob("*.md") if p.is_file() and not p.name.startswith("_"))
    # legacy flat under cases/
    cases = oa_root / "cases"
    if cases.is_dir():
        for p in sorted(cases.glob("*.md")):
            if p.name.startswith("_"):
                continue
            out[STATUS_HISTORY].append(p)
    return out


def list_history_case_paths(cases_or_oa: Path) -> list[Path]:
    """供向量重建：只收历史案。

    可传 oa/cases、oa/cases/history，或 oa 根。
    """
    root = cases_or_oa
    # 若是 oa 根
    if (root / "cases").is_dir() or (root / "pending").is_dir():
        notes = list_notes_by_status(root)
        return notes[STATUS_HISTORY]
    # 若是 oa/cases
    history = root / "history"
    paths: list[Path] = []
    if history.is_dir():
        paths.extend(sorted(p for p in history.glob("*.md") if p.is_file()))
    for p in sorted(root.glob("*.md")):
        if p.name.startswith("_"):
            continue
        paths.append(p)
    # 排除旧 _drafts
    return [p for p in paths if "_drafts" not in p.parts]


def _norm_pub(pub: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", (pub or "").upper())
    return s


def _pub_lookup_key(pub: str) -> str | None:
    """提取可用于匹配的公开号核心；占位符（大量 X）返回 None。"""
    raw = _norm_pub(pub)
    if not raw:
        return None
    if raw.count("X") >= 3:
        return None
    m = re.search(r"(CN\d{7,13}[A-Z]?)", raw)
    if m:
        return m.group(1)
    digits = re.sub(r"[^0-9]", "", raw)
    if len(digits) < 7:
        return None
    return raw


def find_patent_note_rel(vault: Path | None, pub: str, papers_dir: str = "Research/Patents") -> str | None:
    if not vault or not pub:
        return None
    papers = vault / papers_dir
    if not papers.is_dir():
        return None
    target = _pub_lookup_key(pub)
    if not target:
        return None
    candidates: list[Path] = []
    for p in papers.rglob("*.md"):
        if p.name.startswith("_"):
            continue
        # 跳过 clues 等附属页，优先解读主笔记
        if "/clues/" in p.as_posix().replace("\\", "/") or "\\clues\\" in str(p):
            continue
        name_key = _norm_pub(p.stem)
        if target in name_key:
            candidates.append(p)
            continue
        # 父目录名常为公开号
        parent_key = _norm_pub(p.parent.name)
        if target in parent_key:
            candidates.append(p)
            continue
        try:
            head = p.read_text(encoding="utf-8")[:1200]
        except OSError:
            continue
        if target in _norm_pub(head):
            candidates.append(p)
    if not candidates:
        return None
    candidates.sort(
        key=lambda x: (
            0 if "解读" in x.name else 1,
            0 if x.parent.name.upper().startswith("CN") else 1,
            len(x.name),
        )
    )
    rel = candidates[0].relative_to(vault).as_posix()
    return rel[:-3] if rel.endswith(".md") else rel


def _ensure_nav(body: str) -> str:
    if _NAV_MARK in body:
        return body
    nav = (
        f"> 导航：{_NAV_MARK} · "
        "[[oa/_OA关联.canvas|关联 Canvas]] · "
        "[[oa/_OA看板.base|看板]]\n\n"
    )
    return nav + (body or "").lstrip()


def _replace_or_append_section(body: str, heading: str, content: str) -> str:
    pattern = re.compile(
        rf"(?ms)^({re.escape(heading)}\s*\n)(.*?)(?=^##\s|\Z)"
    )
    block = f"{heading}\n\n{content.rstrip()}\n\n"
    if pattern.search(body):
        return pattern.sub(block, body, count=1)
    return (body.rstrip() + "\n\n" + block).lstrip()


def enrich_case_note(
    meta: dict[str, Any],
    body: str,
    *,
    oa_root: Path,
    vault: Path | None = None,
    papers_dir: str = "Research/Patents",
) -> tuple[dict[str, Any], str]:
    """补 status / related_cases / 导航 / 关联案 / 对比文件链。"""
    meta = dict(meta)
    status = normalize_status(meta.get("status"), default=STATUS_HISTORY)
    meta["status"] = status
    related = meta.get("related_cases") or []
    if not isinstance(related, list):
        related = [related]
    meta["related_cases"] = [str(x).strip() for x in related if str(x).strip()]

    body = _ensure_nav(body)

    # 关联案节
    related_lines: list[str] = []
    for cid in meta["related_cases"]:
        # 尝试定位
        found = None
        for st, paths in list_notes_by_status(oa_root).items():
            for p in paths:
                if p.stem == cid:
                    found = p
                    break
            if found:
                break
        if found:
            w = _wiki_path(found, vault, oa_root)
            related_lines.append(f"- [[{w}|{cid}]]")
        else:
            related_lines.append(f"- [[{cid}]]")
    if not related_lines:
        related_lines = ["- （暂无）"]
    body = _replace_or_append_section(body, _SECTION_RELATED, "\n".join(related_lines))

    # 对比文件
    refs = meta.get("compare_refs") or []
    if not isinstance(refs, list):
        refs = [refs]
    compare_lines: list[str] = []
    patent_links: list[str] = []
    for ref in refs:
        ref_s = str(ref).strip()
        if not ref_s:
            continue
        note_rel = find_patent_note_rel(vault, ref_s, papers_dir=papers_dir)
        if note_rel:
            compare_lines.append(f"- `{ref_s}` → [[{note_rel}|解读笔记]]")
            patent_links.append(note_rel)
        else:
            compare_lines.append(f"- `{ref_s}`")
    if patent_links:
        meta["compare_patent_notes"] = patent_links
    else:
        meta.pop("compare_patent_notes", None)
    if compare_lines:
        body = _replace_or_append_section(body, _SECTION_COMPARE, "\n".join(compare_lines))
    elif _SECTION_COMPARE not in body:
        body = _replace_or_append_section(body, _SECTION_COMPARE, "- （暂无）")
    else:
        # 有节但无有效公开号链：保持「仅公开号」或清空误链
        if refs:
            body = _replace_or_append_section(
                body,
                _SECTION_COMPARE,
                "\n".join(f"- `{str(r).strip()}`" for r in refs if str(r).strip()) or "- （暂无）",
            )

    tags = list(meta.get("tags") or [])
    for t in (f"oa/status/{status}", "oa/case"):
        if t not in tags:
            tags.append(t)
    meta["tags"] = tags
    return meta, body


def load_case_records(oa_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for st, paths in list_notes_by_status(oa_root).items():
        for p in paths:
            try:
                meta, body = parse_case_markdown(p.read_text(encoding="utf-8"))
            except OSError:
                continue
            if not meta.get("case_id"):
                meta["case_id"] = p.stem
            meta.setdefault("status", st)
            records.append(
                {
                    "path": p,
                    "status": normalize_status(meta.get("status"), default=st),
                    "meta": meta,
                    "body": body,
                }
            )
    return records


def list_playbook_index_paths(oa_root: Path) -> list[Path]:
    root = oa_root / "playbooks"
    if not root.is_dir():
        return []
    return sorted(p for p in root.glob("*/_playbook.md") if p.is_file())


def _playbook_section(oa_root: Path, vault: Path | None) -> str:
    paths = list_playbook_index_paths(oa_root)
    if not paths:
        return "_（空）_\n"
    lines: list[str] = []
    for p in paths:
        try:
            meta, _ = parse_case_markdown(p.read_text(encoding="utf-8"))
        except OSError:
            meta = {}
        slug = str(meta.get("slug") or p.parent.name)
        title = str(meta.get("title") or slug).replace("|", "/")
        w = _wiki_path(p, vault, oa_root)
        flag = "强制入库" if meta.get("force") else ("已核" if meta.get("verified") else "未核")
        lines.append(f"- [[{w}|{title}]]")
        lines.append(f"  - `{slug}` · {flag} · 不进案例向量")
    return "\n".join(lines) + "\n"


def write_oa_index(oa_root: Path, vault: Path | None = None) -> Path:
    records = load_case_records(oa_root)
    by_status: dict[str, list[dict]] = {
        STATUS_HISTORY: [],
        STATUS_PENDING: [],
        STATUS_DRAFT: [],
    }
    for r in records:
        by_status.setdefault(r["status"], []).append(r)

    def section_list(items: list[dict]) -> str:
        """用列表而非表格：避免 [[path|title]] 中的 | 拆坏表列。"""
        if not items:
            return "_（空）_\n"
        lines: list[str] = []
        for r in sorted(items, key=lambda x: str(x["meta"].get("case_id") or "")):
            m = r["meta"]
            cid = str(m.get("case_id") or r["path"].stem)
            w = _wiki_path(r["path"], vault, oa_root)
            title = str(m.get("title") or cid).replace("|", "/")
            defects = label_defects(m.get("defect_types"))
            statutes = "、".join(str(x) for x in (m.get("statutes") or [])[:2]) or "—"
            outcome = label_outcome(m.get("outcome") or r["status"] or "")
            domain = str(m.get("domain") or "—")
            lines.append(f"- [[{w}|{title}]]")
            lines.append(
                f"  - 缺陷：{defects} · 法条：{statutes} · 结果：{outcome} · 领域：{domain}"
            )
        return "\n".join(lines) + "\n"

    playbook_n = len(list_playbook_index_paths(oa_root))
    body = (
        "---\n"
        "tags:\n"
        "  - oa/index\n"
        "---\n\n"
        "# OA 案例索引\n\n"
        "审查答复私有案例库总览。入库时自动刷新。\n\n"
        "- [[oa/_OA关联.canvas|关联 Canvas]]\n"
        "- [[oa/_OA看板.base|看板（Bases）]]\n\n"
        f"## 统计\n\n"
        f"- 历史案：{len(by_status.get(STATUS_HISTORY) or [])}\n"
        f"- 待答复：{len(by_status.get(STATUS_PENDING) or [])}\n"
        f"- 草稿：{len(by_status.get(STATUS_DRAFT) or [])}\n"
        f"- 经验手册：{playbook_n}\n\n"
        "## 历史案（可检索）\n\n"
        f"{section_list(by_status.get(STATUS_HISTORY) or [])}\n"
        "## 待答复\n\n"
        f"{section_list(by_status.get(STATUS_PENDING) or [])}\n"
        "## 草稿\n\n"
        f"{section_list(by_status.get(STATUS_DRAFT) or [])}\n"
        "## 经验手册（不进案例检索）\n\n"
        f"{_playbook_section(oa_root, vault)}\n"
        "## 目录约定\n\n"
        "- `oa/cases/history/`：已脱敏历史案（进向量/标签检索）\n"
        "- `oa/pending/`：待答复通知书\n"
        "- `oa/drafts/`：入库前人审草稿\n"
        "- `oa/playbooks/`：实务书蒸馏手册；写答复时可 Read，**不**进 `search_cases`\n"
    )
    path = oa_root / "_OA索引.md"
    path.write_text(body, encoding="utf-8")
    return path


def _repo_oa_base_src(root: Path) -> Path | None:
    """技能市场上架禁止提交 *.base；仓库源稿为 oa.base.yaml。"""
    assets = root / "assets" / "obsidian"
    for name in ("oa.base.yaml", "oa.base"):
        path = assets / name
        if path.is_file():
            return path
    return None


def write_oa_base(oa_root: Path) -> Path:
    dest = oa_root / "_OA看板.base"
    # 优先仓库模板
    root = ROOT
    src = _repo_oa_base_src(root)
    if src is not None:
        text = src.read_text(encoding="utf-8").replace("{{OA_DIR}}", "oa")
        dest.write_text(text, encoding="utf-8")
        return dest
    # 内置最小看板
    dest.write_text(
        """filters:
  and:
    - 'file.hasTag("oa/case") or file.hasTag("oa/index") or file.inFolder("oa")'

properties:
  case_id:
    displayName: 案例ID
  status:
    displayName: 状态
  domain:
    displayName: 领域
  outcome:
    displayName: 结果
  patent_type:
    displayName: 专利类型

views:
  - type: table
    name: 全部案例
    order:
      - file.name
      - case_id
      - status
      - domain
      - outcome
    filters:
      and:
        - 'file.inFolder("oa")'
        - 'file.ext == "md"'
        - 'file.name != "_OA索引"'
  - type: table
    name: 历史案
    order:
      - case_id
      - domain
      - outcome
    filters:
      and:
        - 'file.inFolder("oa/cases/history")'
  - type: table
    name: 待答复
    order:
      - file.name
      - status
    filters:
      and:
        - 'file.inFolder("oa/pending")'
""",
        encoding="utf-8",
    )
    return dest


def _share_score(a: dict, b: dict) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.0
    ra = set(str(x) for x in (a.get("related_cases") or []))
    rb = set(str(x) for x in (b.get("related_cases") or []))
    ca, cb = str(a.get("case_id") or ""), str(b.get("case_id") or "")
    if ca and ca in rb or cb and cb in ra:
        score += 3.0
        reasons.append("related")
    sa = set(str(x) for x in (a.get("statutes") or []))
    sb = set(str(x) for x in (b.get("statutes") or []))
    inter_s = sa & sb
    if inter_s:
        score += 2.0
        reasons.append("法条")
    da = set(str(x) for x in (a.get("defect_types") or []))
    db = set(str(x) for x in (b.get("defect_types") or []))
    if da & db:
        score += 1.5
        reasons.append("缺陷")
    if (a.get("domain") or "") and a.get("domain") == b.get("domain"):
        score += 1.0
        reasons.append("领域")
    pa = set(
        k
        for k in (_pub_lookup_key(str(x)) for x in (a.get("compare_refs") or []) if x)
        if k
    )
    pb = set(
        k
        for k in (_pub_lookup_key(str(x)) for x in (b.get("compare_refs") or []) if x)
        if k
    )
    if pa & pb:
        score += 2.0
        reasons.append("对比文件")
    return score, "+".join(reasons) if reasons else ""


def write_oa_canvas(oa_root: Path, vault: Path | None = None) -> Path:
    records = [r for r in load_case_records(oa_root) if r["status"] == STATUS_HISTORY]
    nodes: list[dict] = []
    edges: list[dict] = []
    # hub
    nodes.append(
        {
            "id": "hub",
            "type": "text",
            "text": "# OA 案例关联\n\n同法条 / 同缺陷 / 同领域 / 显式关联 / 同对比文件",
            "x": 0,
            "y": -280,
            "width": 420,
            "height": 140,
            "color": "5",
        }
    )
    cols = max(3, int(len(records) ** 0.5) + 1) if records else 1
    id_by_case: dict[str, str] = {}
    for i, r in enumerate(sorted(records, key=lambda x: str(x["meta"].get("case_id") or ""))):
        m = r["meta"]
        cid = str(m.get("case_id") or r["path"].stem)
        nid = f"c{i}"
        id_by_case[cid] = nid
        w = _wiki_path(r["path"], vault, oa_root)
        defects = label_defects((m.get("defect_types") or [])[:3])
        text = (
            f"## {cid}\n\n"
            f"{m.get('title') or ''}\n\n"
            f"缺陷：{defects}\n"
            f"结果：{label_outcome(m.get('outcome'))}\n\n"
            f"[[{w}|打开]]"
        )
        x = (i % cols) * 380
        y = (i // cols) * 280
        nodes.append(
            {
                "id": nid,
                "type": "text",
                "text": text,
                "x": x,
                "y": y,
                "width": 320,
                "height": 220,
                "color": "4" if (m.get("defect_types") or [None])[0] == "inventiveness" else "3",
            }
        )
        edges.append(
            {
                "id": f"e-hub-{nid}",
                "fromNode": "hub",
                "fromSide": "bottom",
                "toNode": nid,
                "toSide": "top",
                "label": "收录",
            }
        )

    # pair edges
    items = sorted(records, key=lambda x: str(x["meta"].get("case_id") or ""))
    ei = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i]["meta"], items[j]["meta"]
            score, label = _share_score(a, b)
            if score < 1.5:
                continue
            ca = str(a.get("case_id") or "")
            cb = str(b.get("case_id") or "")
            fa, fb = id_by_case.get(ca), id_by_case.get(cb)
            if not fa or not fb:
                continue
            edges.append(
                {
                    "id": f"rel{ei}",
                    "fromNode": fa,
                    "fromSide": "right",
                    "toNode": fb,
                    "toSide": "left",
                    "label": label or f"{score:.1f}",
                    "color": "6",
                }
            )
            ei += 1

    path = oa_root / "_OA关联.canvas"
    path.write_text(
        json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def refresh_case_files(
    oa_root: Path,
    *,
    vault: Path | None = None,
    papers_dir: str = "Research/Patents",
) -> list[str]:
    actions: list[str] = []
    for r in load_case_records(oa_root):
        meta, body = enrich_case_note(
            r["meta"],
            r["body"],
            oa_root=oa_root,
            vault=vault,
            papers_dir=papers_dir,
        )
        # 若 status 与目录不符，迁到正确目录
        want = note_path_for(oa_root, str(meta["case_id"]), meta["status"])
        md = dump_case_markdown(meta, body)
        if r["path"].resolve() != want.resolve():
            want.parent.mkdir(parents=True, exist_ok=True)
            want.write_text(md, encoding="utf-8")
            if r["path"].exists() and r["path"].resolve() != want.resolve():
                r["path"].unlink()
            actions.append(f"relocate:{meta['case_id']}->{want}")
        else:
            r["path"].write_text(md, encoding="utf-8")
            actions.append(f"enrich:{meta['case_id']}")
    return actions


DEFAULT_NUDGE_MIN_HISTORY = 3
DEFAULT_NUDGE_MIN_PLAYBOOKS = 3


def oa_inventory(
    *,
    cfg: dict | None = None,
    vault: str | Path | None = None,
    min_history: int = DEFAULT_NUDGE_MIN_HISTORY,
    min_playbooks: int = DEFAULT_NUDGE_MIN_PLAYBOOKS,
) -> dict[str, Any]:
    """只读统计 oa 库厚度，不写索引、不建目录。"""
    cfg = cfg or {}
    vault_path = Path(vault).expanduser().resolve() if vault else None
    oa_root = resolve_oa_root(cfg, vault_path)
    notes = list_notes_by_status(oa_root) if oa_root.is_dir() else {
        STATUS_HISTORY: [],
        STATUS_PENDING: [],
        STATUS_DRAFT: [],
    }
    history_n = len(notes.get(STATUS_HISTORY) or [])
    playbook_n = len(list_playbook_index_paths(oa_root)) if oa_root.is_dir() else 0
    below_history = history_n < max(0, int(min_history))
    below_playbooks = playbook_n < max(0, int(min_playbooks))
    return {
        "ok": True,
        "oa_root": str(oa_root),
        "vault": str(vault_path) if vault_path else None,
        "counts": {
            STATUS_HISTORY: history_n,
            STATUS_PENDING: len(notes.get(STATUS_PENDING) or []),
            STATUS_DRAFT: len(notes.get(STATUS_DRAFT) or []),
            "playbooks": playbook_n,
        },
        "threshold": {
            "history": int(min_history),
            "playbooks": int(min_playbooks),
        },
        "below": {
            "history": below_history,
            "playbooks": below_playbooks,
        },
        "nudge": below_history or below_playbooks,
    }


def refresh_oa_vault(
    *,
    cfg: dict | None = None,
    vault: str | Path | None = None,
    papers_dir: str = "Research/Patents",
) -> dict[str, Any]:
    cfg = cfg or {}
    vault_path = Path(vault).expanduser().resolve() if vault else None
    oa_root = resolve_oa_root(cfg, vault_path)
    oa_root.mkdir(parents=True, exist_ok=True)
    actions = migrate_legacy_layout(oa_root)
    actions.extend(
        refresh_case_files(oa_root, vault=vault_path, papers_dir=papers_dir)
    )
    index = write_oa_index(oa_root, vault=vault_path)
    base = write_oa_base(oa_root)
    canvas = write_oa_canvas(oa_root, vault=vault_path)
    return {
        "ok": True,
        "oa_root": str(oa_root),
        "vault": str(vault_path) if vault_path else None,
        "index": str(index),
        "base": str(base),
        "canvas": str(canvas),
        "actions": actions,
        "counts": {
            **{st: len(paths) for st, paths in list_notes_by_status(oa_root).items()},
            "playbooks": len(list_playbook_index_paths(oa_root)),
        },
    }
