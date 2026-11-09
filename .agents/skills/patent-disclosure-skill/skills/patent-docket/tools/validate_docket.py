# -*- coding: utf-8 -*-
"""校验 docket.yaml。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from docket_config import load_docket_config
from docket_spec import (
    DISPOSITIONS,
    ISSUE_KINDS,
    PATENT_TYPES,
    START_MODES,
    STATUSES,
    TERMINAL_PHASES,
    load_phase_table,
    phase_names,
)
from stdio_utf8 import ensure_utf8_stdio


def load_docket(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("docket.yaml 须为对象")
    return data


def validate_docket(data: dict[str, Any], *, cfg: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    settings = cfg or load_docket_config()
    cap = int(settings["max_rounds"])
    table = load_phase_table()
    phases = set(phase_names(table))

    if data.get("schema") != "patent-docket":
        errors.append("schema 须为 patent-docket")
    if data.get("version") not in (1, "1"):
        errors.append("version 须为 1")
    case_id = str(data.get("case_id") or "").strip()
    if not case_id:
        errors.append("缺少 case_id")
    ptype = str(data.get("patent_type") or "")
    if ptype not in PATENT_TYPES:
        errors.append("patent_type 无效")
    mode = str(data.get("start_mode") or "")
    if mode not in START_MODES:
        errors.append("start_mode 无效")
    phase = str(data.get("phase") or "")
    if phase not in phases:
        errors.append(f"phase 无效: {phase}")
    try:
        round_n = int(data.get("round") or 0)
    except (TypeError, ValueError):
        round_n = 0
        errors.append("round 须为整数")
    try:
        max_rounds = int(data.get("max_rounds") or 0)
    except (TypeError, ValueError):
        max_rounds = 0
        errors.append("max_rounds 须为整数")
    if max_rounds and max_rounds > cap:
        errors.append(f"max_rounds 不能超过配置上限 {cap}")
    if round_n < 1 or (max_rounds and round_n > max_rounds):
        errors.append("round 须在 1..max_rounds")
    paths = data.get("paths")
    if not isinstance(paths, dict):
        errors.append("缺少 paths")
        paths = {}
    issues = data.get("issues")
    if not isinstance(issues, list):
        errors.append("issues 须为列表")
        issues = []
    rounds = data.get("rounds")
    if not isinstance(rounds, list):
        errors.append("rounds 须为列表")
        rounds = []
    if len(rounds) > cap:
        errors.append("rounds 条数超过 max_rounds")
    if max_rounds and len(rounds) > max_rounds:
        errors.append("rounds 条数超过本案 max_rounds")

    seen_ids: set[str] = set()
    blocking_open = False
    for i, item in enumerate(issues):
        if not isinstance(item, dict):
            errors.append(f"issues[{i}] 须为对象")
            continue
        iid = str(item.get("id") or "").strip()
        if not iid:
            errors.append(f"issues[{i}] 缺少 id")
        elif iid in seen_ids:
            errors.append(f"重复 issue id: {iid}")
        else:
            seen_ids.add(iid)
        if str(item.get("kind") or "") not in ISSUE_KINDS:
            errors.append(f"{iid or i} kind 无效")
        if str(item.get("disposition") or "") not in DISPOSITIONS:
            errors.append(f"{iid or i} disposition 无效")
        if str(item.get("status") or "") not in STATUSES:
            errors.append(f"{iid or i} status 无效")
        if item.get("status") == "open" and item.get("disposition") == "ask_human" and item.get("blocking") is True:
            blocking_open = True

    if blocking_open and phase not in ("ask_human", "terminal_blocked", "intake", "triage"):
        # triage 刚写入尚未跳转时允许短暂停留；派工阶段不允许
        if phase.startswith("dispatch") or phase.startswith("bootstrap") or phase.startswith("wait_"):
            errors.append("存在阻塞问人条目时不得停留在派工/等待阶段")

    if phase == "bootstrap_application" and not str(paths.get("disclosure_dir") or "").strip():
        errors.append("bootstrap_application 需要 paths.disclosure_dir")
    if phase == "triage" and mode == "from_application":
        if not str(paths.get("issues_md") or "").strip() and not str(paths.get("application_dir") or "").strip():
            errors.append("from_application 的 triage 需要申请目录或问题清单路径")
    if phase in TERMINAL_PHASES and phase == "terminal_complete":
        still = [
            it
            for it in issues
            if isinstance(it, dict) and it.get("status") == "open" and it.get("disposition") not in ("ignore", "defer")
        ]
        if still:
            errors.append("terminal_complete 时不得仍有 open 的待办（ignore/defer 除外）")
    if mode == "from_zero" and phase == "bootstrap_application":
        if not str(paths.get("disclosure_md") or paths.get("disclosure_dir") or "").strip():
            errors.append("从零进入申请手之前必须已有交底路径")
    return errors


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="校验专利案卷 docket.yaml")
    parser.add_argument("--yaml", required=True, help="docket.yaml 路径")
    args = parser.parse_args(argv)
    path = Path(args.yaml)
    if not path.is_file():
        print(f"DOCKET_ERROR: 找不到 {path}", file=sys.stderr)
        return 2
    try:
        data = load_docket(path)
        errors = validate_docket(data)
    except Exception as exc:
        print(f"DOCKET_ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("DOCKET_ERROR: " + "; ".join(errors), file=sys.stderr)
        return 2
    print("DOCKET_OK:", str(path), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
