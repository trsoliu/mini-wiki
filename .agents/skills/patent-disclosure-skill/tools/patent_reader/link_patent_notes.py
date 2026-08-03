#!/usr/bin/env python3
"""
扫描 Obsidian 库内专利解读笔记，按规则（+可选模型分）建立关联并回写。

用法：
  # 先预览（不改库）
  python tools/patent_reader/link_patent_notes.py --dry-run

  # 写入 related_pubs、相关专利节、刷新单篇图谱 + 全局 _专利关联.canvas
  python tools/patent_reader/link_patent_notes.py

  # 仅围绕刚入库的公开号
  python tools/patent_reader/link_patent_notes.py --focus-pub CN999999999B

  # 合并 Agent 模型判定（可选 JSON）
  python tools/patent_reader/link_patent_notes.py --model-scores model_links.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from common import optional_path, runtime_config
    from patent_link import run_link_pipeline
except ImportError:
    from tools.patent_reader.common import optional_path, runtime_config
    from tools.patent_reader.patent_link import run_link_pipeline


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default="", help="库根；默认环境变量 / 自动探测")
    ap.add_argument("--papers-dir", default="", help="默认 Research/Patents")
    ap.add_argument("--glossary-dir", default="", help="默认 Research/术语")
    ap.add_argument("--min-score", type=float, default=0.45, help="边阈值 0–1")
    ap.add_argument("--focus-pub", default="", help="只计算与该公开号相关的边")
    ap.add_argument(
        "--model-scores",
        default=None,
        type=optional_path,
        help='JSON 列表：[{"pub_a","pub_b","relation","score","rationale"}]',
    )
    ap.add_argument("--dry-run", action="store_true", help="只输出边，不写库")
    ap.add_argument("--no-canvas", action="store_true", help="不刷新单篇 Canvas")
    ap.add_argument("--no-global-canvas", action="store_true", help="不写全局关联 Canvas")
    ap.add_argument("-o", "--output", default=None, type=optional_path, help="结果 JSON")
    args = ap.parse_args(argv)

    cfg = runtime_config()
    vault_s = args.vault.strip() or cfg["obsidian_vault"]
    if not vault_s:
        print(
            "错误：未配置 Obsidian 库。请先 check_obsidian_env.py 或 --vault。",
            file=sys.stderr,
        )
        return 1
    vault = Path(vault_s).resolve()
    if not vault.is_dir():
        print(f"错误：库不存在 {vault}", file=sys.stderr)
        return 1

    model_scores: list = []
    if args.model_scores and args.model_scores.is_file():
        raw = json.loads(args.model_scores.read_text(encoding="utf-8"))
        model_scores = raw if isinstance(raw, list) else raw.get("links") or raw.get("edges") or []

    result = run_link_pipeline(
        vault,
        papers_dir=args.papers_dir.strip() or cfg["papers_dir"],
        glossary_dir=args.glossary_dir.strip() or cfg["glossary_dir"],
        min_score=args.min_score,
        model_scores=model_scores,
        focus_pub=args.focus_pub.strip(),
        refresh_canvas=not args.no_canvas,
        refresh_global_canvas=not args.no_global_canvas,
        dry_run=args.dry_run,
    )

    print(
        f"OK notes={result['note_count']} edges={result['edge_count']} "
        f"updated={len(result['updated_notes'])} dry_run={result['dry_run']}"
    )
    for e in result["edges"][:20]:
        print(
            f"  LINK {e['pub_a']} <-> {e['pub_b']} "
            f"{e['relation']} score={e['score']} ({e.get('source')})"
        )
    if result.get("global_canvas"):
        print(f"GLOBAL_CANVAS: {result['global_canvas']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"LINKS_JSON: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
