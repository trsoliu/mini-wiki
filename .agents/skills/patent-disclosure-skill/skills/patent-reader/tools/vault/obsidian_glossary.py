"""术语 stub、反链、空壳笔记清理，以及库内相关笔记扫描。"""
from __future__ import annotations

import re
from pathlib import Path

try:
    from shared.common import slugify_pub, slugify_term
except ImportError:
    from tools.patent_reader.shared.common import slugify_pub, slugify_term

def scan_vault_related(
    vault: Path,
    papers_dir: str,
    pub: str,
    assignees: list[str],
    *,
    domain: str = "",
) -> dict:
    """扫描库内相关笔记：同领域解读、同申请人、交底书。"""
    papers = vault / papers_dir
    related_patents: list[dict] = []
    disclosures: list[dict] = []
    if not papers.is_dir():
        return {"related_patents": [], "disclosures": [], "glossary_notes": []}

    assignee_set = {a.strip() for a in assignees if a and len(a.strip()) >= 2}
    pub_slug = slugify_pub(pub)
    seen: set[str] = set()

    for md in papers.rglob("*.md"):
        if md.name.startswith("_") or is_spurious_patent_note(md):
            continue
        rel = str(md.relative_to(vault)).replace("\\", "/")
        text = md.read_text(encoding="utf-8", errors="replace")[:4000]
        base = md.stem
        if pub_slug in base or (pub and pub in base):
            continue

        if "_解读_" in md.name and rel not in seen:
            same_domain = bool(domain) and f"/{domain}/" in f"/{rel}/"
            same_assignee = bool(assignee_set) and any(a in text for a in assignee_set)
            if same_domain or same_assignee:
                label = "同申请人" if same_assignee else "同领域"
                if same_domain and same_assignee:
                    label = "同申请人·同领域"
                related_patents.append(
                    {"path": rel, "title": base, "label": label}
                )
                seen.add(rel)

        if pub in text and ("交底书" in text or "disclosure" in base.lower()):
            disclosures.append({"path": rel, "title": base})

    return {
        "related_patents": related_patents[:8],
        "disclosures": disclosures[:5],
        "glossary_notes": [],
    }


def _parse_aliases_from_fm(yaml_block: str) -> tuple[str, list[str]]:
    """仅从 aliases / title 取值，避免把 tags 误收为 alias。"""
    title = ""
    aliases: list[str] = []
    in_aliases = False
    for line in yaml_block.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("title:"):
            title = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            in_aliases = False
            continue
        if stripped.startswith("tags:") or stripped.startswith("cssclasses:"):
            in_aliases = False
            continue
        if stripped.startswith("aliases:"):
            in_aliases = True
            rest = stripped.split(":", 1)[1].strip()
            if rest and rest not in ("", "[]"):
                aliases.append(rest.strip('"').strip("'"))
            continue
        if in_aliases:
            if stripped.startswith("  - ") or (stripped.startswith("- ") and not stripped.startswith("- ipc")):
                aliases.append(stripped.lstrip("- ").strip().strip('"').strip("'"))
                continue
            if stripped and not stripped.startswith(" "):
                in_aliases = False
    return title, [a for a in aliases if a]


def scan_glossary_index(vault: Path, glossary_dir: str) -> dict[str, str]:
    """扫描术语目录：term/alias -> 相对库根路径（无 .md）。"""
    root = vault / glossary_dir
    index: dict[str, str] = {}
    if not root.is_dir():
        return index
    for md in root.rglob("*.md"):
        if md.name.startswith("_"):
            continue
        rel = str(md.relative_to(vault).with_suffix("")).replace("\\", "/")
        stem = md.stem
        index[stem] = rel
        index[stem.lower()] = rel
        try:
            text = md.read_text(encoding="utf-8", errors="replace")[:1200]
        except OSError:
            continue
        fm_m = re.match(r"^---\n([\s\S]*?)\n---", text)
        if not fm_m:
            continue
        title, aliases = _parse_aliases_from_fm(fm_m.group(1))
        if title:
            index[title] = rel
            index[title.lower()] = rel
        for alias in aliases:
            index[alias] = rel
            index[alias.lower()] = rel
    return index


def _glossary_file_matches_term(path: Path, term: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")[:1200]
    fm_m = re.match(r"^---\n([\s\S]*?)\n---", text)
    if not fm_m:
        return path.stem == term or path.stem == slugify_term(term)
    title, aliases = _parse_aliases_from_fm(fm_m.group(1))
    keys = {title, path.stem, *(aliases or [])}
    keys |= {k.lower() for k in keys if k}
    return term in keys or term.lower() in keys


def normalize_wiki_path(path: str) -> str:
    """库内 wikilink 路径：统一 /，去掉 .md（Obsidian 惯例）。"""
    s = (path or "").replace("\\", "/").strip()
    if s.endswith(".md"):
        s = s[:-3]
    # 去掉误产生的「文件名 1」后缀对应路径中的空格副本（仅清理链到空壳的情况由调用方处理）
    return s


def _wikilink_target(line: str) -> str:
    m = re.search(r"\[\[([^\]|#]+)", line)
    return normalize_wiki_path(m.group(1)) if m else ""


def is_spurious_patent_note(path: Path) -> bool:
    """空壳/重复解读笔记：如「CN…_解读_20260721 1.md」（点坏链自动生成）。"""
    name = path.name
    if re.search(r"\s+\d+\.md$", name) and "_解读_" in name:
        return True
    if "_解读_" in name and path.is_file() and path.stat().st_size == 0:
        return True
    return False


def append_glossary_backlinks(
    path: Path,
    *,
    source_pub: str,
    note_rel: str = "",
    disclosures: list[dict] | None = None,
) -> None:
    """在术语页追加/合并反链：来源专利解读、交底书。路径一律正斜杠并去重。"""
    if not path.is_file():
        return
    body = path.read_text(encoding="utf-8")
    marker = "## 反链"
    note_rel = normalize_wiki_path(note_rel)
    # 防御：调用方若传入 Path 的 Windows 字符串
    if note_rel.startswith("./"):
        note_rel = note_rel[2:]

    # 先规范化已有反链节（去掉反斜杠重复项）
    body, section_changed = _normalize_glossary_backlink_section(body)

    lines: list[str] = []
    if source_pub:
        if note_rel:
            lines.append(f"- 解读：[[{note_rel}|{source_pub}]]")
        elif f"`{source_pub}`" not in body and f"|{source_pub}]]" not in body:
            lines.append(f"- 专利：`{source_pub}`")
    for d in disclosures or []:
        p = normalize_wiki_path(str(d.get("path") or ""))
        title = d.get("title") or p
        if p:
            lines.append(f"- 交底书：[[{p}|{title}]]")

    existing_targets: set[str] = set()
    if marker in body:
        sec = body.split(marker, 1)[1]
        for ln in sec.splitlines():
            tgt = _wikilink_target(ln)
            if tgt:
                existing_targets.add(tgt)
            # 无链接的「专利：`CNxxx`」行
            if source_pub and f"`{source_pub}`" in ln:
                existing_targets.add(f"pub:{source_pub}")

    new_lines: list[str] = []
    for ln in lines:
        tgt = _wikilink_target(ln)
        if tgt and tgt in existing_targets:
            continue
        if source_pub and ln.strip() == f"- 专利：`{source_pub}`" and (
            f"pub:{source_pub}" in existing_targets or f"|{source_pub}]]" in body
        ):
            continue
        if ln in body:
            continue
        new_lines.append(ln)
        if tgt:
            existing_targets.add(tgt)

    need_seen_in = False
    if source_pub and body.startswith("---"):
        fm_end = body.find("\n---", 3)
        fm_head = body[: fm_end + 4] if fm_end != -1 else body[:800]
        if "seen_in:" not in fm_head:
            need_seen_in = True
        elif source_pub not in fm_head:
            need_seen_in = True

    if not new_lines and not need_seen_in and not section_changed:
        return

    if new_lines:
        if marker not in body:
            body = body.rstrip() + f"\n\n{marker}\n\n" + "\n".join(new_lines) + "\n"
        else:
            for ln in new_lines:
                body = body.rstrip() + f"\n{ln}\n"

    if need_seen_in and source_pub:
        if "seen_in:" in body[:800]:
            body = re.sub(
                r"(seen_in:\s*\n(?:\s+- .+\n)*)",
                rf"\1  - {source_pub}\n",
                body,
                count=1,
            )
        else:
            end = body.find("\n---", 3)
            if end != -1:
                body = body[:end] + f"\nseen_in:\n  - {source_pub}\n" + body[end:]
    path.write_text(body, encoding="utf-8")


def _normalize_glossary_backlink_section(body: str) -> tuple[str, bool]:
    """反链节：路径改正斜杠，按目标去重。"""
    marker = "## 反链"
    if marker not in body:
        return body, False
    pre, rest = body.split(marker, 1)
    # 反链节到下一 ## 或文末
    m = re.match(r"(\s*\n)([\s\S]*?)(?=\n##\s|\Z)", rest)
    if not m:
        return body, False
    head_ws, sec = m.group(1), m.group(2)
    tail = rest[m.end() :]
    kept: list[str] = []
    seen: set[str] = set()
    for ln in sec.splitlines():
        raw = ln.rstrip()
        if not raw.strip():
            continue
        if "[[" in raw:

            def _fix_link(mo: re.Match[str]) -> str:
                target = mo.group(1).replace("\\", "/")
                rest_g = mo.group(2) or ""
                return f"[[{target}{rest_g}]]"

            raw = re.sub(r"\[\[([^\]|#]+)((?:\|[^\]]*)?)\]\]", _fix_link, raw)
        key = _wikilink_target(raw) or raw.strip()
        if key in seen:
            continue
        seen.add(key)
        kept.append(raw)
    new_sec = ("\n".join(kept) + "\n") if kept else ""
    new_body = pre + marker + head_ws + new_sec + tail
    return new_body, new_body != body


def repair_glossary_backlinks(vault: Path, glossary_dir: str) -> int:
    """批量修复术语页反链（反斜杠重复）。返回修改文件数。"""
    root = vault / glossary_dir
    if not root.is_dir():
        return 0
    n = 0
    for path in root.glob("*.md"):
        if path.name.startswith("_"):
            continue
        try:
            old = path.read_text(encoding="utf-8")
        except OSError:
            continue
        new, changed = _normalize_glossary_backlink_section(old)
        if changed and new != old:
            path.write_text(new, encoding="utf-8")
            n += 1
    return n


def purge_spurious_patent_notes(vault: Path, papers_dir: str) -> list[str]:
    """删除点坏链产生的空壳「…解读… 1.md」。"""
    root = vault / papers_dir
    removed: list[str] = []
    if not root.is_dir():
        return removed
    for md in root.rglob("*.md"):
        if not is_spurious_patent_note(md):
            continue
        # 仅删空文件或明确的「 数字」后缀副本
        try:
            if md.stat().st_size == 0 or re.search(r"\s+\d+\.md$", md.name):
                rel = str(md.relative_to(vault)).replace("\\", "/")
                md.unlink()
                removed.append(rel)
        except OSError:
            continue
    return removed


def ensure_glossary_stub(
    vault: Path,
    glossary_dir: str,
    term: str,
    *,
    definition: str = "",
    source_pub: str = "",
    papers_dir: str = "Research/Patents",
    note_rel: str = "",
    disclosures: list[dict] | None = None,
) -> tuple[str, bool]:
    """确保术语页存在；撞名时换唯一 slug；返回 (相对路径无.md, 是否新建)。"""
    root = vault / glossary_dir
    root.mkdir(parents=True, exist_ok=True)
    slug = slugify_term(term)
    path = root / f"{slug}.md"
    if path.is_file() and not _glossary_file_matches_term(path, term):
        # slug 撞名但术语不同 → 换唯一文件名
        i = 2
        while True:
            cand = root / f"{slug}_{i}.md"
            if not cand.is_file() or _glossary_file_matches_term(cand, term):
                path = cand
                break
            i += 1
    rel = str(path.relative_to(vault).with_suffix("")).replace("\\", "/")
    created = False
    if path.is_file():
        # 合并 alias；若正文仍是占位且有第五节含义则回填
        text = path.read_text(encoding="utf-8")
        if term not in text[:600]:
            text = re.sub(
                r"(aliases:\s*\n(?:\s+- .+\n)*)",
                rf"\1  - {term}\n",
                text,
                count=1,
            )
            path.write_text(text, encoding="utf-8")
        if definition.strip():
            _fill_glossary_definition(path, term, definition.strip())
    else:
        defn = definition.strip() or "（待补充：来自专利说明书定义或一般理解）"
        body = (
            "---\n"
            "tags:\n"
            "  - glossary\n"
            "aliases:\n"
            f"  - {term}\n"
            f"title: {term}\n"
            f"source_pub: {source_pub}\n"
            "seen_in:\n"
            f"  - {source_pub}\n"
            "---\n\n"
            f"# {term}\n\n"
            f"{defn}\n\n"
            f"来源专利：`{source_pub}` · [[{papers_dir}/_专利解读索引|专利解读索引]]\n\n"
            "## 反链\n\n"
        )
        path.write_text(body, encoding="utf-8")
        created = True
    append_glossary_backlinks(
        path,
        source_pub=source_pub,
        note_rel=note_rel,
        disclosures=disclosures,
    )
    return rel, created


def _fill_glossary_definition(path: Path, term: str, definition: str) -> bool:
    """用第五节「本文含义」回填空壳/占位术语页正文。"""
    if not definition or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    m = re.search(
        rf"(^#\s*{re.escape(term)}\s*\n\n)(.+?)(\n\n来源专利[：:]|\n\n##\s*反链|\Z)",
        text,
        re.M | re.S,
    )
    if not m:
        return False
    old = m.group(2).strip()
    if old == definition:
        return False
    if not (
        old.startswith("（待补充")
        or old.startswith("(待补充")
        or len(old) < 8
    ):
        # 已有实质定义则不覆盖，仅当很短时允许补强
        if len(old) >= 8 and "待补充" not in old:
            return False
    new_text = text[: m.start(2)] + definition + text[m.end(2) :]
    path.write_text(new_text, encoding="utf-8")
    return True


def resolve_glossary_nodes(
    vault: Path,
    glossary_dir: str,
    terms: list[str] | list[dict],
    *,
    create_stubs: bool = True,
    source_pub: str = "",
    papers_dir: str = "Research/Patents",
    definitions: dict[str, str] | None = None,
    note_rel: str = "",
    disclosures: list[dict] | None = None,
) -> list[dict]:
    """将术语列表解析为 Canvas 可用节点信息。"""
    definitions = definitions or {}
    index = scan_glossary_index(vault, glossary_dir)
    nodes: list[dict] = []
    # 全部术语建 stub/反链；Canvas 仅展示前 8 个节点
    for i, item in enumerate(terms):
        if isinstance(item, dict):
            term = str(item.get("term") or "").strip()
            defn = str(item.get("definition") or definitions.get(term, "")).strip()
        else:
            term = str(item).strip()
            defn = definitions.get(term, "")
        if not term:
            continue
        rel = index.get(term) or index.get(term.lower())
        created = False
        if not rel and create_stubs:
            rel, created = ensure_glossary_stub(
                vault,
                glossary_dir,
                term,
                definition=defn,
                source_pub=source_pub,
                papers_dir=papers_dir,
                note_rel=note_rel,
                disclosures=disclosures,
            )
            index[term] = rel
        elif rel:
            # 已有页：补反链；有定义则尝试回填空壳
            stub_path = vault / f"{rel}.md"
            if defn:
                _fill_glossary_definition(stub_path, term, defn)
            append_glossary_backlinks(
                stub_path,
                source_pub=source_pub,
                note_rel=note_rel,
                disclosures=disclosures,
            )
        if i < 8:
            nodes.append(
                {
                    "term": term,
                    "path": rel or "",
                    "created": created,
                    "has_file": bool(rel),
                    "definition": defn,
                }
            )
    return nodes

