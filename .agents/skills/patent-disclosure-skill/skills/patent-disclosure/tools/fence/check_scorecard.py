#!/usr/bin/env python
"""核验评分表，或对案件作答打分。

  python tools/fence/check_scorecard.py --table
  python tools/fence/check_scorecard.py -i outputs/案/fence/scorecard.yaml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_FENCE = Path(__file__).resolve().parent
_TOOLS = _FENCE.parent
for p in (_FENCE, _TOOLS):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from scorecard_lib import _load_yaml, load_table, score_answers
from stdio_utf8 import ensure_utf8_stdio


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--answers", default="", help="案件 fence/scorecard.yaml")
    ap.add_argument("--case-dir", default="", help="用来解析外挂表")
    ap.add_argument("--table", action="store_true", help="只校验当前表定义")
    args = ap.parse_args(argv)
    table = load_table(args.case_dir or None)
    print(f"SCORECARD_TABLE:{table.get('_source')}")
    print(f"SCORECARD_ID:{table.get('id')}")
    if args.table and not args.answers:
        print("SCORECARD_OK:1")
        return 0
    if not args.answers:
        print("SCORECARD_ERROR:需要 --answers 或 --table")
        return 2
    path = Path(args.answers)
    answers = _load_yaml(path)
    if answers.get("scorecard_id") and answers["scorecard_id"] != table.get("id"):
        print(
            f"SCORECARD_ERROR:作答 scorecard_id={answers.get('scorecard_id')} 与表 {table.get('id')} 不一致"
        )
        return 2
    result = score_answers(table, answers)
    print(f"SCORECARD_OPEN:{1 if result['open_fence'] else 0}")
    print(f"SCORECARD_BORDERLINE:{1 if result['borderline'] else 0}")
    print(f"SCORECARD_JSON:{json.dumps(result, ensure_ascii=False)}")
    if result["reasons"]:
        print("SCORECARD_REASONS:" + "; ".join(result["reasons"]))
    print("SCORECARD_OK:1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
