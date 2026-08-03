#!/usr/bin/env python3
"""
对已有解读笔记落地公开线索增强：筛选(≤3)→clues/→附录 B→旁注→刷新 Canvas。

摘要主路径：Agent 写入 public_clues.json 的 summary/status。
脚本 HTTP 抓取仅降级：加 --fetch-fallback，且只处理缺 summary 的条目。

用法：
  python tools/patent_reader/materialize_public_clues.py \\
      --note-rel Research/Patents/领域/CNxxx/CNxxx_解读_20260721.md \\
      --public-clues tmp/patent_reader/RUN/public_clues.json

  # 缺摘要时脚本降级
  python tools/patent_reader/materialize_public_clues.py --note-rel ... --fetch-fallback
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from clue_vault import (
        as_clues,
        clue_cards_for_canvas,
        harvest_feature_entries,
        inject_clue_annotations,
        load_clues_sidecar,
        materialize_clues,
        upsert_appendix_b,
    )
    from common import optional_path, runtime_config
    from obsidian import (
        build_canvas,
        ensure_canvas_nav,
        harvest_claim_summaries_from_note,
        parse_frontmatter,
        scan_vault_related,
    )
    from write_patent_obsidian_note import (
        harvest_glossary_from_note,
        harvest_narrative_from_note,
        merge_glossary_candidates,
        sanitize_user_facing_titles,
    )
except ImportError:
    from tools.patent_reader.clue_vault import (
        as_clues,
        clue_cards_for_canvas,
        harvest_feature_entries,
        inject_clue_annotations,
        load_clues_sidecar,
        materialize_clues,
        upsert_appendix_b,
    )
    from tools.patent_reader.common import optional_path, runtime_config
    from tools.patent_reader.obsidian import (
        build_canvas,
        ensure_canvas_nav,
        harvest_claim_summaries_from_note,
        parse_frontmatter,
        scan_vault_related,
    )
    from tools.patent_reader.write_patent_obsidian_note import (
        harvest_glossary_from_note,
        harvest_narrative_from_note,
        merge_glossary_candidates,
        sanitize_user_facing_titles,
    )


def _load_clues(args, note_dir: Path) -> list[dict]:
    if args.public_clues and args.public_clues.is_file():
        return as_clues(json.loads(args.public_clues.read_text(encoding="utf-8")))
    if args.workdir:
        p = args.workdir / "public_clues.json"
        if p.is_file():
            return as_clues(json.loads(p.read_text(encoding="utf-8")))
    side = load_clues_sidecar(note_dir)
    if side:
        # 已 materialize 过：用原 url/title 再跑（允许补抓）
        return side
    return []


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default="", help="默认 PATENT_READER_OBSIDIAN_VAULT")
    ap.add_argument("--note-rel", required=True)
    ap.add_argument("--public-clues", default=None, type=optional_path)
    ap.add_argument("--workdir", default=None, type=optional_path)
    ap.add_argument(
        "--fetch-fallback",
        action="store_true",
        help="缺 summary 时脚本 HTTP 降级（默认关闭）",
    )
    ap.add_argument(
        "--no-fetch",
        action="store_true",
        help="兼容旧参数：等同默认（不脚本抓取）",
    )
    ap.add_argument("--max", type=int, default=3)
    args = ap.parse_args(argv)

    cfg = runtime_config()
    vault_s = args.vault.strip() or cfg["obsidian_vault"]
    if not vault_s:
        print("错误：未指定 vault", file=sys.stderr)
        return 1
    vault = Path(vault_s).resolve()
    note_path = vault / args.note_rel.replace("\\", "/")
    if not note_path.is_file():
        print(f"错误：笔记不存在 {note_path}", file=sys.stderr)
        return 1

    content = note_path.read_text(encoding="utf-8")
    fm, _, body = parse_frontmatter(content)
    pub = str(fm.get("pub_number") or "").strip()
    if not pub:
        m = re.search(r"\b(CN\d+[A-Z]?\d?)\b", note_path.name, re.I)
        pub = m.group(1).upper() if m else note_path.parent.name

    clues = _load_clues(args, note_path.parent)
    if not clues:
        print("WARN 无线索可落地（提供 --public-clues 或 workdir/public_clues.json）", file=sys.stderr)
        return 0

    note_rel = str(note_path.relative_to(vault)).replace("\\", "/")
    rich, appendix = materialize_clues(
        clues,
        note_dir=note_path.parent,
        pub=pub,
        note_rel=note_rel,
        claim_summaries=harvest_claim_summaries_from_note(content),
        feature_entries=harvest_feature_entries(content),
        max_keep=args.max,
        fetch_fallback=bool(args.fetch_fallback) and not args.no_fetch,
    )
    content = upsert_appendix_b(content, appendix)
    content = inject_clue_annotations(content, rich)
    content = sanitize_user_facing_titles(content)

    domain = str(fm.get("domain") or "")
    papers = cfg["papers_dir"]
    glossary_dir = cfg["glossary_dir"]
    related = scan_vault_related(
        vault, papers, pub, fm.get("assignees") or [], domain=domain
    )
    claim_tree = None
    ct = note_path.parent / "claim_tree.json"
    if ct.is_file():
        claim_tree = json.loads(ct.read_text(encoding="utf-8"))

    title_m = re.search(r"^#\s+(.+)$", body, re.M)
    title = title_m.group(1).strip() if title_m else pub
    note_dir_rel = str(note_path.parent.relative_to(vault)).replace("\\", "/")
    glossary = merge_glossary_candidates([], harvest_glossary_from_note(content))
    narrative = harvest_narrative_from_note(content)
    canvas = build_canvas(
        vault=vault,
        papers_dir=papers,
        note_rel_path=note_rel,
        pub=pub,
        title=title,
        related=related,
        glossary_terms=glossary,
        glossary_dir=glossary_dir,
        create_glossary_stubs=False,
        meta={
            "domain": domain,
            "ipc": fm.get("ipc") or "",
            "assignees": fm.get("assignees") or [],
            "evidence_scope": fm.get("evidence_scope") or "",
        },
        claim_tree=claim_tree,
        claim_summaries=harvest_claim_summaries_from_note(content),
        narrative=narrative,
        clue_cards=clue_cards_for_canvas(rich, note_dir_rel=note_dir_rel),
    )
    canvas.pop("glossary_resolved", None)
    pub_slug = pub
    canvas_path = note_path.parent / f"{pub_slug}_图谱.canvas"
    canvas_path.write_text(
        json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    canvas_rel = str(canvas_path.relative_to(vault)).replace("\\", "/")
    content = ensure_canvas_nav(content, canvas_rel)
    note_path.write_text(content, encoding="utf-8")

    print(f"OK clues={len(rich)} note={note_path}")
    print(f"CLUES_DIR: {note_path.parent / 'clues'}")
    print(f"CANVAS: {canvas_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
