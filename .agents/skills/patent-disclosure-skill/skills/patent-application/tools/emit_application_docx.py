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


def emit_one(md_path: Path, prefer_omml: bool = True) -> Path:
    out = md_path.with_suffix(".docx")
    text = md_path.read_text(encoding="utf-8")
    doc = convert_md_to_docx(text, base_dir=md_path.parent, prefer_omml=prefer_omml)
    doc.save(str(out))
    return out


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
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
        except Exception as exc:
            print(f"DOCX: ok=0 path={md} reason={exc}")
            fail += 1
    if ok == 0:
        print("DOCX: ok=0 reason=no_markdown")
        return 1
    print(f"APPLICATION_DOCX: ok={1 if fail == 0 else 0} written={ok} failed={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
