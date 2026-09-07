#!/usr/bin/env python
"""把已填好的意见陈述 Markdown 转为 Word。

只用本包 ``md_to_docx.py`` 副本，禁止调用交底包。默认 ``--no-omml``（陈述书一般无公式）。

用法：
  python skills/patent-oa/tools/emit_opinion_docx.py -i outputs/oa/案/意见陈述_20260903120000.md
  python skills/patent-oa/tools/emit_opinion_docx.py -i 意见陈述.md -o 意见陈述.docx
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from md_to_docx import convert_md_to_docx  # noqa: E402
from stdio_utf8 import ensure_utf8_stdio  # noqa: E402


def emit_opinion_docx(md_path: Path, docx_path: Path | None = None) -> Path:
    md_path = md_path.resolve()
    if not md_path.is_file():
        raise FileNotFoundError(md_path)
    out = (docx_path or md_path.with_suffix(".docx")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    text = md_path.read_text(encoding="utf-8")
    doc = convert_md_to_docx(text, base_dir=md_path.parent, prefer_omml=False)
    doc.save(str(out))
    return out


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-i", "--input", required=True, help="已按模板填好的意见陈述 .md")
    p.add_argument("-o", "--output", default="", help="输出 .docx（默认与 md 同名）")
    args = p.parse_args(argv)
    in_path = Path(args.input)
    out_path = Path(args.output) if str(args.output).strip() else None
    try:
        dest = emit_opinion_docx(in_path, out_path)
    except FileNotFoundError as exc:
        print(f"错误：找不到 {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"DOCX: ok=0 reason={exc}", file=sys.stderr)
        return 1
    print(f"DOCX: ok=1 path={dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
