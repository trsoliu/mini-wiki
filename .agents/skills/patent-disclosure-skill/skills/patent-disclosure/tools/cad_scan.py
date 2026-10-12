# -*- coding: utf-8 -*-
"""扫描目录中的 STEP / 原生 CAD（无 CadQuery 依赖）。

供 Step 2 / 迭代补材料时快速分类，记下「交底落盘后是否反问开启」或「交付前提示导出」。

示例：
  python tools/cad_scan.py -r knowledge -r outputs/case
  python tools/cad_scan.py -r . --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from cad_formats import (
    EXPORT_HINT_ZH,
    STEP_CONFIRM_ZH,
    iter_classified,
    recommend_action,
)


def build_report(roots: list[str], *, recursive: bool = True) -> dict:
    classified = iter_classified(roots, recursive=recursive)
    action = recommend_action(
        classified["step"],
        classified["native_cad"],
        classified["iges"],
    )
    return {
        "roots": [str(Path(r).resolve()) if Path(r).exists() else r for r in roots],
        "step_files": classified["step"],
        "native_cad_files": classified["native_cad"],
        "iges_files": classified["iges"],
        "mesh_files": classified["mesh"],
        "action": action,
        "step_parse_default": "off",
        "messages": {
            "ask_enable_step_parse": STEP_CONFIRM_ZH if action == "ask_enable_step_parse" else "",
            "hint_export_step": EXPORT_HINT_ZH if action == "hint_export_step" else "",
        },
        "next_if_enabled": [
            "python tools/cad_venv.py",
            "python tools/run_step_to_views.py --enable-step-parse -i <file.step> -o <outdir>",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="扫描 STEP / 原生 CAD 文件并给出建议动作")
    p.add_argument(
        "-r",
        "--root",
        action="append",
        dest="roots",
        required=True,
        help="扫描根目录或文件，可重复",
    )
    p.add_argument("--no-recursive", action="store_true", help="不递归子目录")
    p.add_argument("--json", action="store_true", help="仅打印 JSON（默认）")
    p.add_argument("--text", action="store_true", help="人类可读摘要")
    args = p.parse_args(argv)

    report = build_report(args.roots, recursive=not args.no_recursive)
    if args.text and not args.json:
        print(f"action: {report['action']}")
        print(f"step ({len(report['step_files'])}):")
        for x in report["step_files"]:
            print(f"  - {x}")
        print(f"native_cad ({len(report['native_cad_files'])}):")
        for x in report["native_cad_files"][:30]:
            print(f"  - {x}")
        if len(report["native_cad_files"]) > 30:
            print(f"  … +{len(report['native_cad_files']) - 30} more")
        msg = report["messages"].get(report["action"]) or ""
        if msg:
            print("---")
            print(msg)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
