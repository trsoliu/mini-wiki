#!/usr/bin/env python
"""校验 claim_features.json（独权特征行，对照表左列）。

用法：
  python skills/patent-reader/tools/analyze/validate_claim_features.py -i claim_features.json
  python skills/patent-reader/tools/analyze/validate_claim_features.py -i claim_features.json --write
"""
from __future__ import annotations

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
    from analyze.claim_features import normalize_claim_features, validate_claim_features
except ImportError:
    from tools.patent_reader.analyze.claim_features import (
        normalize_claim_features,
        validate_claim_features,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", required=True, type=Path)
    ap.add_argument(
        "-o",
        "--output",
        default=None,
        type=Path,
        help="校验报告 JSON（默认旁路 .lint.json）",
    )
    ap.add_argument(
        "--write",
        action="store_true",
        help="把 normalize 后的清单写回 -i",
    )
    args = ap.parse_args(argv)

    if not args.input.is_file():
        print(f"FAIL missing {args.input}", file=sys.stderr)
        return 2
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"FAIL invalid json: {e}", file=sys.stderr)
        return 2

    result = validate_claim_features(raw)
    data = result.get("data") or normalize_claim_features(raw)
    report = {
        "passed": result["passed"],
        "issues": result["issues"],
        "warnings": result["warnings"],
        "count": result["count"],
    }
    out_path = args.output or Path(str(args.input) + ".lint.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.write:
        args.input.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"WROTE normalized features → {args.input}")

    print(
        f"{'OK' if report['passed'] else 'FAIL'} claim_features "
        f"count={report['count']} issues={len(report['issues'])} "
        f"warnings={len(report['warnings'])}"
    )
    for x in report["issues"]:
        print(f"  issue: {x}")
    for x in report["warnings"][:12]:
        print(f"  warn: {x}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
