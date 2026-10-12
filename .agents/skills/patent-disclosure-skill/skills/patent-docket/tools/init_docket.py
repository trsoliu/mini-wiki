# -*- coding: utf-8 -*-
"""新建案卷目录与 docket.yaml。"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from docket_config import load_docket_config
from docket_paths import docket_dir_for, normalize_case_id
from docket_spec import PATENT_TYPES, START_MODES
from stdio_utf8 import ensure_utf8_stdio

_PHASE0 = {
    "from_zero": "bootstrap_disclosure",
    "from_disclosure": "bootstrap_application",
    "from_application": "triage",
    "resume": "intake",
}


def empty_docket(
    *,
    case_id: str,
    start_mode: str,
    patent_type: str,
    max_rounds: int,
    disclosure_dir: str = "",
    disclosure_md: str = "",
    application_dir: str = "",
    issues_md: str = "",
    materials_dir: str = "",
    docket_dir: str = "",
) -> dict[str, Any]:
    phase = _PHASE0[start_mode]
    return {
        "schema": "patent-docket",
        "version": 1,
        "case_id": case_id,
        "patent_type": patent_type,
        "start_mode": start_mode,
        "phase": phase,
        "round": 1,
        "max_rounds": max_rounds,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "paths": {
            "docket_dir": docket_dir,
            "materials_dir": materials_dir,
            "disclosure_dir": disclosure_dir,
            "disclosure_md": disclosure_md,
            "application_dir": application_dir,
            "issues_md": issues_md,
        },
        "issues": [],
        "rounds": [],
        "human_queue": [],
        "notes": "",
    }


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="初始化专利案卷")
    parser.add_argument("--case-id", required=True)
    parser.add_argument(
        "--mode",
        required=True,
        choices=START_MODES,
        help="from_zero|from_disclosure|from_application|resume",
    )
    parser.add_argument("--type", dest="patent_type", default="invention")
    parser.add_argument("--disclosure-dir", default="")
    parser.add_argument("--disclosure-md", default="")
    parser.add_argument("--application-dir", default="")
    parser.add_argument("--issues-md", default="")
    parser.add_argument("--materials-dir", default="")
    parser.add_argument("--force", action="store_true", help="已有 yaml 时覆盖")
    args = parser.parse_args(argv)
    try:
        slug = normalize_case_id(args.case_id)
        ptype = str(args.patent_type).strip()
        if ptype not in PATENT_TYPES:
            raise ValueError("patent_type 无效")
        if args.mode == "from_disclosure" and not (args.disclosure_dir or args.disclosure_md):
            raise ValueError("from_disclosure 需要 --disclosure-dir 或 --disclosure-md")
        if args.mode == "from_application" and not (args.application_dir or args.issues_md):
            raise ValueError("from_application 需要 --application-dir 或 --issues-md")
        if args.mode == "resume":
            raise ValueError("resume 不要 init；直接校验已有 docket.yaml")
    except ValueError as exc:
        print(f"DOCKET_ERROR: {exc}", file=sys.stderr)
        return 2

    cfg = load_docket_config()
    folder = docket_dir_for(slug)
    folder.mkdir(parents=True, exist_ok=True)
    yaml_path = folder / "docket.yaml"
    if yaml_path.exists() and not args.force:
        print(f"DOCKET_ERROR: 已存在 {yaml_path}，续跑请不要 init；覆盖须 --force", file=sys.stderr)
        return 2

    doc = empty_docket(
        case_id=slug,
        start_mode=args.mode,
        patent_type=ptype,
        max_rounds=int(cfg["max_rounds"]),
        disclosure_dir=args.disclosure_dir.strip(),
        disclosure_md=args.disclosure_md.strip(),
        application_dir=args.application_dir.strip(),
        issues_md=args.issues_md.strip(),
        materials_dir=args.materials_dir.strip(),
        docket_dir=str(folder).replace("\\", "/"),
    )
    try:
        import yaml
    except ImportError:
        print("DOCKET_ERROR: 需要 PyYAML", file=sys.stderr)
        return 1
    yaml_path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print("DOCKET_DIR:", str(folder), flush=True)
    print("DOCKET_YAML:", str(yaml_path), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
