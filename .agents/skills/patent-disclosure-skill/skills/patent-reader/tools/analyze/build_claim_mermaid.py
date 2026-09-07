#!/usr/bin/env python
"""
由 claim_tree.json 生成 mermaid 权利要求树（独立权=子图）。

用法：
  python skills/patent-reader/tools/analyze/build_claim_mermaid.py --claim-tree claim_tree.json --pub-number CNxxx -o claim_mermaid.mmd
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
    from vault.obsidian import claim_tree_to_mermaid
except ImportError:
    from tools.patent_reader.vault.obsidian import claim_tree_to_mermaid


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claim-tree", required=True, type=Path)
    ap.add_argument("--pub-number", default="")
    ap.add_argument("-o", "--output", required=True, type=Path)
    args = ap.parse_args(argv)

    tree = json.loads(args.claim_tree.read_text(encoding="utf-8"))
    mmd = claim_tree_to_mermaid(tree, args.pub_number)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(mmd + "\n", encoding="utf-8")
    print(f"OK mermaid lines={len(mmd.splitlines())}")
    print(f"MERMAID: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
