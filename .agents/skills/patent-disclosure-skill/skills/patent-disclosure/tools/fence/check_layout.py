#!/usr/bin/env python
"""校验分解 / 突围 / 矩阵 / 族树。

  python tools/fence/check_layout.py --decompose outputs/案/fence/decompose.yaml
  python tools/fence/check_layout.py --around outputs/案/fence/design_around.yaml
  python tools/fence/check_layout.py --matrix outputs/案/fence/matrix.yaml
  python tools/fence/check_layout.py --family outputs/案/fence/family.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_FENCE = Path(__file__).resolve().parent
_TOOLS = _FENCE.parent
for p in (_FENCE, _TOOLS):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from family_lib import validate_family
from layout_lib import validate_decompose, validate_design_around, validate_matrix
from scorecard_lib import _load_yaml
from stdio_utf8 import ensure_utf8_stdio


def _run(label: str, path: str, fn) -> int:
    doc = _load_yaml(Path(path))
    err = fn(doc)
    if err:
        print(f"LAYOUT_ERROR:{label}: " + "; ".join(err))
        return 2
    print(f"LAYOUT_OK:{label}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decompose", default="")
    ap.add_argument("--around", default="")
    ap.add_argument("--matrix", default="")
    ap.add_argument("--family", default="")
    args = ap.parse_args(argv)
    if not any((args.decompose, args.around, args.matrix, args.family)):
        print("LAYOUT_ERROR:需要 --decompose / --around / --matrix / --family")
        return 2
    code = 0
    if args.decompose:
        code = max(code, _run("decompose", args.decompose, validate_decompose))
    if args.around:
        code = max(code, _run("around", args.around, validate_design_around))
    if args.matrix:
        code = max(code, _run("matrix", args.matrix, validate_matrix))
    if args.family:
        code = max(code, _run("family", args.family, validate_family))
    if code == 0:
        print("LAYOUT_OK:1")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
