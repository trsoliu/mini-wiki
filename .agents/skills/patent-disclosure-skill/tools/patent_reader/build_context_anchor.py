#!/usr/bin/env python3
"""
为专利通俗解读生成「技术落地线索」包（零付费 API）：
  - 专利内：实施例、背景、术语
  - 离线：IPC 行业坐标（references/ipc_application_hints.yaml）
  - WebSearch 查询模板（供 Agent 执行）
  - Obsidian 导航建议

用法：
  python tools/patent_reader/build_context_anchor.py -w tmp/patent_reader/RUN
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from common import (
        resolve_domain,
        resolve_ipc_hints,
        runtime_config,
        slugify_pub,
    )
except ImportError:
    from tools.patent_reader.common import (
        resolve_domain,
        resolve_ipc_hints,
        runtime_config,
        slugify_pub,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def title_from_bundle(bundle: dict, manifest: dict) -> str:
    for sec in bundle.get("sections_preview") or []:
        if sec.get("kind") == "abstract":
            return manifest.get("pub_number", "")
    return manifest.get("pub_number", "patent")


def read_abstract(bundle_path: Path) -> str:
    workdir = bundle_path.parent
    jsonl = workdir / "raw_sections.jsonl"
    if not jsonl.is_file():
        return ""
    for line in jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("kind") == "abstract":
            return row.get("text", "")[:500]
    return ""


def build_web_search_queries(
    pub: str,
    assignees: list[str],
    title_hint: str,
    ipc_hint: dict,
    claim_keywords: list[str],
) -> list[dict]:
    queries: list[dict] = []
    assignee = assignees[0] if assignees else ""
    kw = " ".join(claim_keywords[:3]) if claim_keywords else title_hint[:40]

    if assignee and kw:
        queries.append(
            {
                "purpose": "官网或新闻中的产品/方案线索",
                "query": f'"{assignee}" {kw} (产品 OR 解决方案 OR 发布会)',
                "priority": 1,
            }
        )
        # 尝试猜官网（仅作搜索提示，不爬）
        short = re.sub(r"(股份|有限|公司|集团|科技|技术).*$", "", assignee)[:12]
        if short:
            queries.append(
                {
                    "purpose": "限定企业站点",
                    "query": f"{short} {kw} site:com OR site:cn",
                    "priority": 2,
                }
            )

    for hint in (ipc_hint.get("search_hints") or [])[:2]:
        queries.append(
            {
                "purpose": f"行业语境：{ipc_hint.get('industry', '')}",
                "query": f"{kw} {hint}",
                "priority": 3,
            }
        )

    queries.append(
        {
            "purpose": "同申请人其他专利（国知局公开信息）",
            "query": f"{assignee or pub} 专利 {kw}",
            "priority": 4,
            "tool": "cnipa_epub_search.py",
            "note": "可用 cnipa_epub_search.py 分词检索，合并 EPUB_HITS_JSON",
        }
    )
    return queries[:6]


def claim_keyword_tokens(bundle: dict) -> list[str]:
    stop = {
        "一种", "一種", "其特征", "特徵", "在于", "在於", "所述", "包括", "其中",
        "权利要求", "方法", "系统", "装置", "步骤", "用于", "以及", "或者",
        "根据", "通过", "进行", "具有", "配置", "对应", "以上", "以下",
    }
    tokens: list[str] = []
    for c in bundle.get("claims") or []:
        if not c.get("is_independent"):
            continue
        text = c.get("text", "")
        # 优先 4–8 字块，过滤半截功能词
        for m in re.finditer(r"[\u4e00-\u9fff]{4,8}", text):
            w = m.group(0)
            if any(s in w for s in ("其特征", "根据权利要求")):
                continue
            if w in stop or w[:2] in stop:
                continue
            if w not in tokens:
                tokens.append(w)
        if len(tokens) >= 6:
            break
        for m in re.finditer(r"[\u4e00-\u9fff]{2,3}", text):
            w = m.group(0)
            if w in stop or w in tokens:
                continue
            tokens.append(w)
        break
    return tokens[:6]


def obsidian_navigation(domain: str, pub: str, cfg: dict) -> dict:
    papers = cfg["papers_dir"]
    slug = slugify_pub(pub)
    return {
        "vault_root": cfg["obsidian_vault"] or "",
        "note_dir": f"{papers}/{domain}/{slug}",
        "moc_global": f"{papers}/_专利解读索引",
        "moc_domain": f"{papers}/{domain}/_领域索引",
        "wikilinks": [
            f"[[{papers}/_专利解读索引|专利解读索引]]",
            f"[[{papers}/{domain}/_领域索引|{domain}领域索引]]",
        ],
        "frontmatter_suggest": {
            "domain": domain,
            "pub_number": pub,
        },
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-w", "--workdir", required=True, type=Path, help="extract 产出目录")
    ap.add_argument("-o", "--output", default="", help="默认 workdir/context_anchor.json")
    args = ap.parse_args(argv)

    workdir = args.workdir.resolve()
    manifest_path = workdir / "source_manifest.json"
    bundle_path = workdir / "synthesis_bundle.json"
    if not manifest_path.is_file() or not bundle_path.is_file():
        print("错误：请先运行 extract_patent_text.py", file=sys.stderr)
        return 1

    manifest = load_json(manifest_path)
    bundle = load_json(bundle_path)
    pub = manifest.get("pub_number", "")
    assignees = manifest.get("assignees") or bundle.get("assignees") or []
    ipc_codes = manifest.get("ipc_codes") or bundle.get("ipc_codes") or []
    abstract = read_abstract(bundle_path)
    text_for_match = abstract + "\n" + " ".join(bundle.get("background_snippets") or [])

    ipc_hint = resolve_ipc_hints(text_for_match, ipc_codes)
    domain = resolve_domain(text_for_match, ipc_codes[0] if ipc_codes else "")
    claim_kw = claim_keyword_tokens(bundle)
    cfg = runtime_config()

    anchor = {
        "pub_number": pub,
        "domain": domain,
        "assignees": assignees,
        "ipc_codes": ipc_codes,
        "patent_internal": {
            "embodiments": bundle.get("embodiments") or [],
            "background_snippets": bundle.get("background_snippets") or [],
            "glossary_candidates": bundle.get("glossary_candidates") or [],
        },
        "ipc_application": {
            "matched_by": ipc_hint.get("matched_by"),
            "ipc_prefix": ipc_hint.get("ipc_prefix"),
            "industry": ipc_hint.get("industry"),
            "typical_modules": ipc_hint.get("typical_modules") or [],
            "user_scenarios": ipc_hint.get("user_scenarios") or [],
        },
        "web_search_queries": build_web_search_queries(
            pub, assignees, abstract[:80], ipc_hint, claim_kw
        ),
        "obsidian": obsidian_navigation(domain, pub, cfg),
        "writing_guide": {
            "section_9": "九、技术应用场景：必须锚定 desc_id/实施例/背景句，标置信度「高」",
            "appendix_a": "附录 A IPC 行业坐标：来自 ipc_application，标「离线词表」",
            "appendix_b": "附录 B：检索后 Agent 打开 URL 写 summary（主路径）；入库只落地 clues/；脚本抓取仅降级",
            "forbidden": "不得将推测线索写入主结论章节（一至八）",
        },
    }

    out_path = Path(args.output) if args.output else workdir / "context_anchor.json"
    out_path.write_text(json.dumps(anchor, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK domain={domain} ipc={ipc_hint.get('ipc_prefix')} queries={len(anchor['web_search_queries'])}")
    print(f"CONTEXT_ANCHOR: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
