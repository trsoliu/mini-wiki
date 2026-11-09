# -*- coding: utf-8 -*-
"""由 docket.yaml 生成 TRACKER.md。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stdio_utf8 import ensure_utf8_stdio
from validate_docket import load_docket, validate_docket

_TYPE = {
    "invention": "发明",
    "utility_model": "实用新型",
    "design": "外观设计",
}
_MODE = {
    "from_zero": "从零开写",
    "from_disclosure": "已有交底",
    "from_application": "已有申请/清单",
    "resume": "续跑",
}
_PHASE = {
    "bootstrap_disclosure": "调度交底初稿",
    "wait_disclosure": "等待交底初稿",
    "bootstrap_application": "调度首套申请",
    "wait_application": "等待申请文件",
    "triage": "分诊问题清单",
    "ask_human": "问人",
    "dispatch_disclosure": "退回交底",
    "wait_disclosure_fix": "等待交底纠正",
    "dispatch_application": "再出申请",
    "round_close": "轮次收口",
    "terminal_complete": "结束（清单可关）",
    "terminal_max_rounds": "结束（已满 3 轮）",
    "terminal_blocked": "结束（阻塞未解）",
    "intake": "接入",
}


def _cell(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return text.replace("|", "\\|") if text else "—"


def render_tracker(data: dict[str, Any]) -> str:
    paths = data.get("paths") or {}
    issues = data.get("issues") or []
    rounds = data.get("rounds") or []
    lines = [
        f"# 案卷 {data.get('case_id') or '—'}",
        "",
        f"- **专利类型**：{_TYPE.get(str(data.get('patent_type')), _cell(data.get('patent_type')))}",
        f"- **开写方式**：{_MODE.get(str(data.get('start_mode')), _cell(data.get('start_mode')))}",
        f"- **阶段**：{_PHASE.get(str(data.get('phase')), _cell(data.get('phase')))}（`{data.get('phase')}`）",
        f"- **轮次**：{data.get('round')} / {data.get('max_rounds')}",
        f"- **更新**：{_cell(data.get('updated_at'))}",
        "",
        "## 路径",
        "",
        "| 项 | 路径 |",
        "| --- | --- |",
        f"| 案卷目录 | {_cell(paths.get('docket_dir'))} |",
        f"| 材料 | {_cell(paths.get('materials_dir'))} |",
        f"| 交底目录 | {_cell(paths.get('disclosure_dir'))} |",
        f"| 交底正文 | {_cell(paths.get('disclosure_md'))} |",
        f"| 申请目录 | {_cell(paths.get('application_dir'))} |",
        f"| 问题清单 | {_cell(paths.get('issues_md'))} |",
        "",
        "## 议题",
        "",
    ]
    if not issues:
        lines.append("（尚无分诊条目）")
        lines.append("")
    else:
        lines.extend(
            [
                "| id | 摘要 | kind | 处置 | 状态 | 阻塞 | 轮次 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in issues:
            if not isinstance(item, dict):
                continue
            blocking = "是" if item.get("blocking") else "否"
            lines.append(
                "| {id} | {summary} | {kind} | {disp} | {st} | {blk} | {rnd} |".format(
                    id=_cell(item.get("id")),
                    summary=_cell(item.get("summary")),
                    kind=_cell(item.get("kind")),
                    disp=_cell(item.get("disposition")),
                    st=_cell(item.get("status")),
                    blk=blocking,
                    rnd=_cell(item.get("round_opened")),
                )
            )
        lines.append("")
    lines.extend(["## 已交付轮次", ""])
    if not rounds:
        lines.append("（还没有记入的申请交付）")
        lines.append("")
    else:
        lines.extend(["| n | 申请目录 | 交底目录 | 说明 |", "| --- | --- | --- | --- |"])
        for row in rounds:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"| {_cell(row.get('n'))} | {_cell(row.get('application_dir'))} | "
                f"{_cell(row.get('disclosure_dir'))} | {_cell(row.get('notes'))} |"
            )
        lines.append("")
    notes = str(data.get("notes") or "").strip()
    if notes:
        lines.extend(["## 备注", "", notes, ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="从 docket.yaml 生成 TRACKER.md")
    parser.add_argument("--yaml", required=True)
    args = parser.parse_args(argv)
    path = Path(args.yaml)
    if not path.is_file():
        print(f"DOCKET_ERROR: 找不到 {path}", file=sys.stderr)
        return 2
    try:
        data = load_docket(path)
        errors = validate_docket(data)
        if errors:
            print("DOCKET_ERROR: " + "; ".join(errors), file=sys.stderr)
            return 2
        text = render_tracker(data)
        out = path.with_name("TRACKER.md")
        out.write_text(text, encoding="utf-8")
    except Exception as exc:
        print(f"DOCKET_ERROR: {exc}", file=sys.stderr)
        return 2
    print("DOCKET_OK:", str(out), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
