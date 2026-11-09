#!/usr/bin/env python
"""把申请文件目录中的 Markdown 转为 Word。只用本包 md_to_docx 副本。

默认转换：权利要求书.md、说明书.md、说明书摘要.md、说明书附图.md（若存在）。

用法：
  python tools/emit_application_docx.py --dir outputs/patent-application/{案}
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from md_to_docx import convert_md_to_docx
from stdio_utf8 import ensure_utf8_stdio

DEFAULT_STEMS = ("权利要求书", "说明书", "说明书摘要", "说明书附图")

_DELIM_HITS_TOTAL = 0


class LatexDelimError(Exception):
    """行内公式写成普通括号；跳过该文件 Word，与交底 mermaid_render 硬拦截同口径。"""

    def __init__(self, path: Path, n: int) -> None:
        super().__init__(f"latex_delim hits={n} file={path.name}")
        self.path = path
        self.n = n


def _warn_bare_paren_latex(md_path: Path, text: str) -> int:
    """行内公式写成普通括号时提示 ``LATEX_DELIM:``。

    ``(M_{\\mathrm{total}})`` 这类写法 Word 会当纯文本，说明书里尤其要避免。
    返回命中数；``emit_one`` 在命中时**跳过**该文件 Word（``DOCX: ok=0 reason=latex_delim``）。
    """
    global _DELIM_HITS_TOTAL
    try:
        from latex_delimiters import find_bare_paren_latex, format_hits_report
    except ImportError:
        return 0
    hits = find_bare_paren_latex(text)
    if hits:
        _DELIM_HITS_TOTAL += len(hits)
        print(f"LATEX_DELIM_FILE: {md_path.name}", file=sys.stderr)
        print(format_hits_report(hits), file=sys.stderr)
    return len(hits)


def emit_one(md_path: Path, prefer_omml: bool = True) -> Path:
    out = md_path.with_suffix(".docx")
    text = md_path.read_text(encoding="utf-8")
    n = _warn_bare_paren_latex(md_path, text)
    if n:
        raise LatexDelimError(md_path, n)
    doc = convert_md_to_docx(text, base_dir=md_path.parent, prefer_omml=prefer_omml)
    doc.save(str(out))
    return out


def main(argv: list[str] | None = None) -> int:
    global _DELIM_HITS_TOTAL
    _DELIM_HITS_TOTAL = 0
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args(argv)
    root = args.dir.expanduser().resolve()
    if not root.is_dir():
        print(f"DOCX: ok=0 reason=missing_dir path={root}")
        return 1
    ok = 0
    fail = 0
    for stem in DEFAULT_STEMS:
        md = root / f"{stem}.md"
        if not md.is_file():
            continue
        try:
            dest = emit_one(md, prefer_omml=True)
            print(f"DOCX: ok=1 path={dest}")
            ok += 1
        except LatexDelimError as exc:
            print(f"DOCX: ok=0 path={md} reason=latex_delim hits={exc.n}")
            fail += 1
        except Exception as exc:
            print(f"DOCX: ok=0 path={md} reason={exc}")
            fail += 1
    if ok == 0 and fail == 0:
        print("DOCX: ok=0 reason=no_markdown")
        return 1
    if _DELIM_HITS_TOTAL:
        print(f"LATEX_DELIM: hits={_DELIM_HITS_TOTAL}", file=sys.stderr)
    print(f"APPLICATION_DOCX: ok={1 if fail == 0 else 0} written={ok} failed={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
