#!/usr/bin/env python
"""
从专利 PDF 抽取附图（caption+bbox 裁切 + xref 回退 + 质量门）。

按专利图注「图 N / FIG. N」锚定邻近矢量/嵌入图 bbox，裁切 PNG 并做质量门决策。

依赖：pip install -r skills/patent-reader/tools/requirements.txt

用法：
  python skills/patent-reader/tools/extract/extract_patent_figures.py -i patent.pdf -o tmp/run/figures
  python skills/patent-reader/tools/extract/extract_patent_figures.py -i patent.pdf -o tmp/run/figures --include-review
  # 产出 figures/manifest.json（含 decision=insert|placeholder）与 PNG
"""
from __future__ import annotations

# Ensure tools/patent_reader is importable when run as a script.
from pathlib import Path as _Path
import sys as _sys

_PR_ROOT = _Path(__file__).resolve().parents[1]
if str(_PR_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PR_ROOT))

import argparse
import json
import sys
from pathlib import Path

try:
    from extract.figure_extract import extract_patent_pdf_figures
except ImportError:
    from tools.patent_reader.extract.figure_extract import extract_patent_pdf_figures


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", required=True, type=Path)
    ap.add_argument("-o", "--output", required=True, type=Path)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--min-xref-bytes", type=int, default=8000)
    ap.add_argument(
        "--xref-only",
        action="store_true",
        help="仅 xref 嵌入图（旧行为）",
    )
    ap.add_argument(
        "--include-review",
        action="store_true",
        help="quality=review 的图也标为 decision=insert（人工确认后少丢可用图）",
    )
    args = ap.parse_args(argv)

    try:
        import fitz
    except ImportError:
        print("需安装 pymupdf：pip install pymupdf", file=sys.stderr)
        return 1

    pdf_path = args.input.resolve()
    if not pdf_path.is_file():
        print(f"错误：找不到 {pdf_path}", file=sys.stderr)
        return 1

    out_dir = args.output.resolve()
    manifest = extract_patent_pdf_figures(
        pdf_path,
        out_dir,
        dpi=args.dpi,
        min_xref_bytes=args.min_xref_bytes,
        prefer_figure_level=not args.xref_only,
        include_review=args.include_review,
    )
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"OK figures={manifest['count']} insert={manifest['insert_count']} "
        f"placeholder={manifest['placeholder_count']}"
    )
    print(f"FIGURES_MANIFEST: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
