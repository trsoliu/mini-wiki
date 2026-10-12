"""库初始化：索引页、关系图配色、CSS / Bases 引导。"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

try:
    from shared.common import runtime_config
    from vault.obsidian_glossary import purge_spurious_patent_notes, repair_glossary_backlinks
    from vault.obsidian_paths import ASSETS_OBSIDIAN, repo_obsidian_base_src
except ImportError:
    from tools.patent_reader.shared.common import runtime_config
    from tools.patent_reader.vault.obsidian_glossary import (
        purge_spurious_patent_notes,
        repair_glossary_backlinks,
    )
    from tools.patent_reader.vault.obsidian_paths import ASSETS_OBSIDIAN, repo_obsidian_base_src

def upsert_index_entry(
    index_path: Path,
    title: str,
    entry_line: str,
    intro: str,
    extra_body: str = "",
    *,
    dedupe_key: str = "",
) -> None:
    """创建或更新索引页，追加笔记列表条目。

    dedupe_key: 若提供，则删除列表中已含该 key 的旧行后再追加（用于术语按 term 去重）。
    """
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if index_path.is_file():
        body = index_path.read_text(encoding="utf-8")
    else:
        body = (
            f"---\ntags:\n  - patents/index\n---\n\n"
            f"# {title}\n\n{intro}\n\n{extra_body}\n"
        )

    marker = "## 笔记列表"
    # 术语索引用「术语列表」
    if "术语" in title and marker not in body and "## 术语列表" in body:
        marker = "## 术语列表"

    if dedupe_key:
        lines = body.splitlines(keepends=True)
        new_lines: list[str] = []
        for ln in lines:
            if ln.lstrip().startswith("- ") and dedupe_key in ln:
                continue
            new_lines.append(ln)
        body = "".join(new_lines)
    elif entry_line in body:
        index_path.write_text(body, encoding="utf-8")
        return

    if marker not in body:
        body = body.rstrip() + f"\n\n{marker}\n\n"
    body = body.rstrip() + f"\n- {entry_line}\n"
    index_path.write_text(body, encoding="utf-8")


def ensure_domain_index(vault: Path, papers_dir: str, domain: str) -> Path:
    """确保领域索引页存在。"""
    domain_dir = vault / papers_dir / domain
    domain_dir.mkdir(parents=True, exist_ok=True)
    index_path = domain_dir / "_领域索引.md"
    if not index_path.is_file():
        body = (
            "---\n"
            "tags:\n"
            "  - patents/index\n"
            f"cssclasses:\n"
            "  - patent-index\n"
            "---\n\n"
            f"# {domain} · 领域索引\n\n"
            f"领域：**{domain}**。上级：[[{papers_dir}/_专利解读索引|专利解读索引]]。\n\n"
            f"## 本领域仪表盘（Dataview）\n\n"
            f"```dataview\n"
            f'TABLE pub_number AS "公开号", read_date AS "解读日期", '
            f'default(evidence_label, choice(evidence_scope = "full_text", "全文", '
            f'choice(evidence_scope = "abstract_only", "仅摘要", '
            f'choice(evidence_scope = "partial", "部分", evidence_scope)))) AS "证据范围", '
            f'default(speculative_label, choice(confidence_speculative, "是", "否")) AS "含推测"\n'
            f'FROM "{papers_dir}/{domain}"\n'
            f'WHERE contains(file.name, "_解读_")\n'
            f"SORT read_date DESC\n"
            f"```\n\n"
            "## 笔记列表\n\n"
        )
        index_path.write_text(body, encoding="utf-8")
    else:
        # 已有领域索引：升级证据列中文显示
        try:
            body = index_path.read_text(encoding="utf-8")
        except OSError:
            return index_path
        if "evidence_label" not in body and (
            'evidence_scope AS "证据' in body
            or 'AS "证据"' in body
            or 'AS "证据范围"' in body
        ):
            body2 = re.sub(
                r"```dataview\nTABLE[\s\S]*?```",
                (
                    "```dataview\n"
                    'TABLE pub_number AS "公开号", read_date AS "解读日期", '
                    'default(evidence_label, choice(evidence_scope = "full_text", "全文", '
                    'choice(evidence_scope = "abstract_only", "仅摘要", '
                    'choice(evidence_scope = "partial", "部分", evidence_scope)))) AS "证据范围", '
                    'default(speculative_label, choice(confidence_speculative, "是", "否")) AS "含推测"\n'
                    f'FROM "{papers_dir}/{domain}"\n'
                    'WHERE contains(file.name, "_解读_")\n'
                    "SORT read_date DESC\n"
                    "```"
                ),
                body,
                count=1,
            )
            if body2 != body:
                index_path.write_text(body2, encoding="utf-8")
    return index_path


def _repair_index_glossary_dataview(index_path: Path, glossary_dir: str) -> bool:
    """修补索引页「术语网」Dataview：围栏必须为 ```，查询用 FROM … AND #glossary。"""
    try:
        body = index_path.read_text(encoding="utf-8")
    except OSError:
        return False
    fence = "`" * 3
    new_section = (
        "### 术语网（反链入口）\n\n"
        f"> 下列列表依赖 Dataview；若仍为空，请打开 `{glossary_dir}/` 核对术语页，"
        "或点开 `glossary.base`。\n\n"
        f"{fence}dataview\n"
        "LIST\n"
        f'FROM "{glossary_dir}" AND #glossary\n'
        'WHERE file.name != "_术语索引"\n'
        "SORT file.name ASC\n"
        f"{fence}\n\n"
    )
    pat = re.compile(r"###\s*术语网[\s\S]*?(?=##\s*笔记列表|##\s*关联图谱)")
    m = pat.search(body)
    if not m:
        return False
    good = f'{fence}dataview\nLIST\nFROM "{glossary_dir}" AND #glossary\n'
    sec = m.group(0)
    if good in sec and sec.count(fence) >= 2:
        return False
    new_body = pat.sub(new_section, body)
    if new_body == body:
        return False
    index_path.write_text(new_body, encoding="utf-8")
    return True


def _upgrade_index_evidence_dataview(index_path: Path, papers_dir: str) -> bool:
    """将主索引 Dataview 证据/推测列升级为中文（evidence_label / speculative_label）。"""
    try:
        body = index_path.read_text(encoding="utf-8")
    except OSError:
        return False
    if "evidence_label" in body and "speculative_label" in body:
        return False
    if "evidence_scope AS" not in body and 'AS "含推测"' not in body:
        return False
    fence = "`" * 3
    new_table = (
        f"{fence}dataview\n"
        'TABLE pub_number AS "公开号", domain AS "领域", read_date AS "解读日期", '
        'default(evidence_label, choice(evidence_scope = "full_text", "全文", '
        'choice(evidence_scope = "abstract_only", "仅摘要", '
        'choice(evidence_scope = "partial", "部分", evidence_scope)))) AS "证据范围", '
        'ipc AS "IPC", '
        'default(speculative_label, choice(confidence_speculative, "是", "否")) AS "含推测"\n'
        f'FROM "{papers_dir}"\n'
        'WHERE contains(file.name, "_解读_")\n'
        "SORT read_date DESC\n"
        f"{fence}"
    )
    body2, n = re.subn(
        rf"{fence}dataview\nTABLE[\s\S]*?{fence}",
        new_table,
        body,
        count=1,
    )
    if n == 0 or body2 == body:
        return False
    # 确保有关联图谱节
    if "_专利关联.canvas" not in body2:
        link = f"- [[{papers_dir}/_专利关联.canvas|专利关联总览]]（交付后可生成专利关联）\n"
        if "## 关联图谱" in body2:
            body2 = re.sub(
                r"(##\s*关联图谱\s*\n)",
                rf"\1\n{link}",
                body2,
                count=1,
            )
        elif "## 笔记列表" in body2:
            body2 = body2.replace(
                "## 笔记列表",
                f"## 关联图谱\n\n{link}\n## 笔记列表",
                1,
            )
    index_path.write_text(body2, encoding="utf-8")
    return True


def _rgb_pack(hex_color: str) -> int:
    """#RRGGBB → Obsidian graph.json 的 rgb 整数。"""
    h = hex_color.lstrip("#")
    return int(h, 16)


def build_patent_graph_color_groups(
    papers_dir: str = "Research/Patents",
    glossary_dir: str = "Research/术语",
) -> list[dict]:
    """专利解读关系图配色（先匹配先生效）。"""
    papers_q = papers_dir.replace("\\", "/").rstrip("/")
    gloss_q = glossary_dir.replace("\\", "/").rstrip("/")

    def g(query: str, hex_color: str) -> dict:
        return {"query": query, "color": {"a": 1, "rgb": _rgb_pack(hex_color)}}

    return [
        g("file:_图谱", "#14B8A6"),  # Canvas 单篇图谱 · 青绿
        g("file:_专利关联", "#0D9488"),  # 全局关联 · 深青
        g(f'path:"{gloss_q}"', "#F97316"),  # 术语目录 · 橙
        g("tag:#glossary", "#FB923C"),  # 术语标签 · 浅橙
        g("tag:#patents/index", "#64748B"),  # 索引 · 石板灰
        g("tag:#patent/speculative", "#F59E0B"),  # 含推测 · 琥珀
        g("file:_解读_", "#4F46E5"),  # 解读笔记 · 靛
        g("tag:#patents", "#6366F1"),  # 专利标签 · 靛紫
        g("file:.base", "#0F766E"),  # Bases · 深青
        g(f'path:"{papers_q}"', "#818CF8"),  # 专利目录兜底
    ]


def _is_managed_graph_query(query: str) -> bool:
    q = str(query or "")
    return (
        q.startswith("file:_图谱")
        or q.startswith("file:_专利关联")
        or q.startswith("file:_解读_")
        or q.startswith("file:.base")
        or q.startswith("tag:#patent")
        or q.startswith("tag:#glossary")
        or q.startswith("tag:#patents")
        or q.startswith('path:"Research/')
        or q.startswith("path:Research/")
    )


# 关系图保留 Canvas/PDF，过滤附图、旁路 JSON、悬停旁路笔记
# （search 与 Obsidian 搜索语法一致；负向 file: 排除节点）
GRAPH_EXCLUDE_TERMS = (
    "-file:.png",
    "-file:.jpg",
    "-file:.jpeg",
    "-file:.gif",
    "-file:.webp",
    "-file:.svg",
    "-file:.bmp",
    "-file:.tif",
    "-file:.tiff",
    "-file:.json",
    "-file:.jsonl",
    "-file:_权项锚点",
    "-file:_说明书段落",
)

# 不应出现在 search 正向过滤里（解读/图谱用 colorGroups 着色，勿收成「只显示解读」）
GRAPH_SEARCH_STRIP_POSITIVE = (
    "file:_解读_",
    "file:_图谱",
    "file:_专利关联",
    "tag:#patents",
    "tag:#glossary",
    "tag:#patents/index",
    "tag:#patent/speculative",
)

# 兼容旧名
GRAPH_IMAGE_EXCLUDE_TERMS = GRAPH_EXCLUDE_TERMS


def _merge_graph_search_excludes(existing: str) -> str:
    """在保留用户自定义 filter 的前提下，确保排除噪声节点，并去掉误伤的「只显示解读」正向过滤。"""
    parts = [p for p in (existing or "").split() if p]
    stripped = [p for p in parts if p not in GRAPH_SEARCH_STRIP_POSITIVE]
    # 去掉 path:"Research/Patents" 这类过宽正向（配色已有 Groups）
    cleaned: list[str] = []
    for p in stripped:
        if p.startswith('path:"Research/') or p.startswith("path:Research/"):
            continue
        cleaned.append(p)
    for term in GRAPH_EXCLUDE_TERMS:
        if term not in cleaned:
            cleaned.append(term)
    return " ".join(cleaned)


def _merge_graph_search_hide_images(existing: str) -> str:
    """兼容旧调用名。"""
    return _merge_graph_search_excludes(existing)


def ensure_graph_color_groups(
    vault: Path,
    papers_dir: str = "Research/Patents",
    glossary_dir: str = "Research/术语",
) -> str | None:
    """写入/合并 .obsidian/graph.json 颜色分组；返回动作描述或 None。"""
    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    graph_path = obsidian_dir / "graph.json"
    desired = build_patent_graph_color_groups(papers_dir, glossary_dir)
    desired_queries = {g["query"] for g in desired}

    if graph_path.is_file():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {
            "collapse-filter": False,
            "search": "",
            "showTags": False,
            "showAttachments": True,
            "hideUnresolved": False,
            "showOrphans": True,
            "collapse-display": False,
            "showArrow": False,
            "textFadeMultiplier": 0,
            "nodeSizeMultiplier": 1.1,
            "lineSizeMultiplier": 1,
            "collapse-forces": False,
            "centerStrength": 0.5,
            "repelStrength": 10,
            "linkStrength": 1,
            "linkDistance": 250,
            "scale": 1,
            "close": False,
        }

    existing = data.get("colorGroups") or []
    kept = [
        g
        for g in existing
        if isinstance(g, dict)
        and g.get("query")
        and g["query"] not in desired_queries
        and not _is_managed_graph_query(g["query"])
    ]
    data["colorGroups"] = desired + kept
    data["collapse-color-groups"] = False  # 展开 Groups，便于看到配色图例
    data["showAttachments"] = True  # 保留 Canvas/PDF；图片与 JSON 用 search 排除
    data["search"] = _merge_graph_search_excludes(str(data.get("search") or ""))
    data["collapse-filter"] = False  # 展开过滤器，便于看到已排除项
    graph_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"graph_colors:{graph_path}"


def ensure_colored_tags_seed(vault: Path) -> str | None:
    """若已装 Colored Tags，写入更鲜明的调色板与已知专利标签序号（不覆盖用户 tagColors）。"""
    data_path = vault / ".obsidian" / "plugins" / "colored-tags" / "data.json"
    if not data_path.is_file():
        return None
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    changed = False
    palette = data.setdefault("palette", {})
    # bright 比 adaptive-soft 更适合「一眼能分清」
    if palette.get("selected") in (None, "adaptive-soft", ""):
        palette["selected"] = "bright"
        changed = True
    known = data.setdefault("knownTags", {})
    seeds = {
        "patents": 1,
        "glossary": 3,
        "patent": 2,
        "patents/index": 5,
        "glossary/index": 3,
        "patent/evidence": 4,
        "patent/evidence/full": 4,
        "patent/evidence/abstract": 6,
        "patent/speculative": 2,
    }
    for tag, idx in seeds.items():
        if tag not in known:
            known[tag] = idx
            changed = True
    if not changed:
        return None
    data_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return f"colored_tags:{data_path}"


def bootstrap_vault(vault: Path, papers_dir: str = "Research/Patents") -> list[str]:
    """将 assets/obsidian 引导文件写入库（幂等）。"""
    actions: list[str] = []
    papers = vault / papers_dir
    papers.mkdir(parents=True, exist_ok=True)

    obsidian_dir = vault / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    snippets_dir = obsidian_dir / "snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)
    css_src = ASSETS_OBSIDIAN / "patent-reader.css"
    css_dst = snippets_dir / "patent-reader.css"
    if css_src.is_file():
        shutil.copy2(css_src, css_dst)
        actions.append(f"snippet:{css_dst}")

    base_src = repo_obsidian_base_src("patents")
    base_dst = papers / "patents.base"
    if base_src is not None:
        need_copy = not base_dst.is_file() or base_src.stat().st_mtime > base_dst.stat().st_mtime
        if need_copy:
            body = base_src.read_text(encoding="utf-8")
            body = body.replace("{{PAPERS_DIR}}", papers_dir)
            body = body.replace("Research/Patents", papers_dir)
            base_dst.write_text(body, encoding="utf-8")
            actions.append(f"base:{base_dst}")

    gloss_base_src = repo_obsidian_base_src("glossary")
    cfg = runtime_config()
    glossary_rel = cfg.get("glossary_dir") or "Research/术语"
    if gloss_base_src is not None:
        gloss_root = vault / glossary_rel
        gloss_root.mkdir(parents=True, exist_ok=True)
        gloss_base_dst = gloss_root / "glossary.base"
        need_copy = (
            not gloss_base_dst.is_file()
            or gloss_base_src.stat().st_mtime > gloss_base_dst.stat().st_mtime
        )
        if need_copy:
            body = gloss_base_src.read_text(encoding="utf-8")
            body = body.replace("{{GLOSSARY_DIR}}", glossary_rel)
            gloss_base_dst.write_text(body, encoding="utf-8")
            actions.append(f"glossary_base:{gloss_base_dst}")

    index_tpl = ASSETS_OBSIDIAN / "_专利解读索引.template.md"
    index_dst = papers / "_专利解读索引.md"
    if index_tpl.is_file() and not index_dst.is_file():
        body = index_tpl.read_text(encoding="utf-8")
        body = body.replace("{{PAPERS_DIR}}", papers_dir)
        body = body.replace("Research/Patents", papers_dir)
        body = body.replace("{{GLOSSARY_DIR}}", glossary_rel)
        index_dst.write_text(body, encoding="utf-8")
        actions.append(f"index:{index_dst}")
    elif index_dst.is_file():
        # 已有索引：修补术语网 + 升级证据列中文 + 关系图配色说明
        if _repair_index_glossary_dataview(index_dst, glossary_rel):
            actions.append(f"index_glossary_dv:{index_dst}")
        if _upgrade_index_evidence_dataview(index_dst, papers_dir):
            actions.append(f"index_evidence_zh:{index_dst}")
        try:
            ibody = index_dst.read_text(encoding="utf-8")
            if "自动上色" not in ibody and "## 关联图谱" in ibody:
                tip = (
                    "- 打开左侧 **关系图**：节点已按类型自动上色"
                    "（靛=解读，青绿=Canvas，橙=术语，琥珀=含推测）。"
                    "若仍为灰色，请重载库（Ctrl/Cmd+R）。\n"
                )
                ibody2 = ibody.replace("## 关联图谱\n", f"## 关联图谱\n\n{tip}", 1)
                if ibody2 != ibody:
                    index_dst.write_text(ibody2, encoding="utf-8")
                    actions.append(f"index_graph_tip:{index_dst}")
        except OSError:
            pass

    glossary_root = vault / glossary_rel
    glossary_root.mkdir(parents=True, exist_ok=True)
    gloss_index = glossary_root / "_术语索引.md"
    if not gloss_index.is_file():
        gloss_index.write_text(
            "---\n"
            "tags:\n"
            "  - glossary/index\n"
            "---\n\n"
            "# 术语索引\n\n"
            "本目录存放专利解读产生的术语概念页；Canvas 与笔记第五节可 wikilink 至此。\n\n"
            f"上级：[[{papers_dir}/_专利解读索引|专利解读索引]]\n\n"
            "## 术语仪表盘（Bases）\n\n"
            f"![[{glossary_rel}/glossary.base#全部术语]]\n\n"
            "## 术语列表\n\n",
            encoding="utf-8",
        )
        actions.append(f"glossary:{gloss_index}")

    # 空库也创建 appearance.json 并启用 CSS snippet
    appearance = obsidian_dir / "appearance.json"
    try:
        if appearance.is_file():
            data = json.loads(appearance.read_text(encoding="utf-8"))
        else:
            data = {}
            actions.append("created:appearance.json")
        enabled = data.get("enabledCssSnippets") or []
        if "patent-reader" not in enabled:
            enabled.append("patent-reader")
            data["enabledCssSnippets"] = enabled
            appearance.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            actions.append("enabled_snippet:patent-reader")
    except (json.JSONDecodeError, OSError):
        pass

    # 核心插件 Bases：写入 core-plugins.json（社区插件无法由脚本代装）
    core_plugins = obsidian_dir / "core-plugins.json"
    try:
        if core_plugins.is_file():
            cp = json.loads(core_plugins.read_text(encoding="utf-8"))
        else:
            cp = {}
            actions.append("created:core-plugins.json")
        if isinstance(cp, dict) and cp.get("bases") is not True:
            cp["bases"] = True
            core_plugins.write_text(
                json.dumps(cp, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            actions.append("enabled_core:bases")
    except (json.JSONDecodeError, OSError, TypeError):
        pass

    # 全局关系图自动上色（原生 Groups，无需插件）
    g_act = ensure_graph_color_groups(vault, papers_dir, glossary_rel)
    if g_act:
        actions.append(g_act)
    ct_act = ensure_colored_tags_seed(vault)
    if ct_act:
        actions.append(ct_act)

    # 清理空壳「解读 1.md」与术语反链反斜杠重复
    purged = purge_spurious_patent_notes(vault, papers_dir)
    for rel in purged:
        actions.append(f"purged_spurious:{rel}")
    repaired = repair_glossary_backlinks(vault, glossary_rel)
    if repaired:
        actions.append(f"glossary_backlinks_repaired:{repaired}")

    return actions


def try_obsidian_cli_property(file_rel: str, name: str, value: str, vault: Path) -> bool:
    """若 PATH 中有 obsidian CLI，设置属性。"""
    try:
        r = subprocess.run(
            [
                "obsidian",
                "property:set",
                f'file={file_rel}',
                f"name={name}",
                f"value={value}",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(vault),
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

