#!/usr/bin/env python
"""在申请产出目录追加「申请文件修订对话记录.md」。"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG = "申请文件修订对话记录.md"
CASE_TS = re.compile(r"^(.+)_(\d{14})$")

FILE_HEADER = """# 申请文件修订对话记录

> 由 `iteration_dialog_log.py` 按 `prompts/iteration.md` 追加。请勿删除既有条目。

"""


def _append(log_path: Path, entry: str) -> None:
    if log_path.exists():
        prev = log_path.read_text(encoding="utf-8")
        if prev and not prev.endswith("\n"):
            prev += "\n"
        log_path.write_text(prev + "\n" + entry, encoding="utf-8")
    else:
        log_path.write_text(FILE_HEADER + "\n" + entry, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True, help="本轮新产出目录")
    parser.add_argument("--kind", choices=("merge", "correct"), required=True)
    parser.add_argument("--user", default="")
    parser.add_argument("--summary", default="")
    parser.add_argument("--artifacts", default="")
    parser.add_argument("--log-name", default=DEFAULT_LOG)
    args = parser.parse_args()

    case_dir = args.case_dir.expanduser().resolve()
    if not case_dir.is_dir():
        print(f"ERROR: 目录不存在: {case_dir}", file=sys.stderr)
        return 2

    now_local = datetime.now().astimezone()
    now_utc = datetime.now(timezone.utc)
    kind_zh = "合并迭代" if args.kind == "merge" else "纠正迭代"
    user_block = (args.user or "").strip() or "（未传入 --user）"
    summary_block = (args.summary or "").strip() or "—"
    art = (args.artifacts or "").strip()
    art_lines = (
        "\n".join(f"- `{x.strip()}`" for x in art.split(",") if x.strip()) if art else "—"
    )
    entry = f"""## {now_local.strftime("%Y-%m-%d %H:%M:%S")}（本地） · {now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")}（UTC）

**类型**：{kind_zh}

**用户说明摘要**：

{user_block}

**本轮交付目录**：`{case_dir.name}`

**本轮交付文件**：

{art_lines}

**合并/纠正摘要摘录**：

{summary_block}

---

"""
    log_path = case_dir / args.log_name
    _append(log_path, entry)
    print(f"LOG_FILE={log_path}")

    match = CASE_TS.match(case_dir.name)
    if match:
        rolling = case_dir.parent / f"{match.group(1)}_申请文件修订对话记录.md"
        _append(rolling, entry)
        print(f"LOG_FILE={rolling}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
