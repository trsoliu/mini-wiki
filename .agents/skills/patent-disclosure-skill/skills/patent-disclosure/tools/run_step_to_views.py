# -*- coding: utf-8 -*-
"""Run STEP -> views using cad-env; rasterize leftover SVG with the host browser.

Checks cad-env first. Bootstraps only when CadQuery is not importable.
PNG: cairosvg if Cairo exists, else svg_screenshot.py. matplotlib is not used.

  python tools/run_step_to_views.py --enable-step-parse -i model.step -o outputs/case/cad_views
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from cad_venv import HOST_PYTHON_ENV, isolated_env, status, venv_python

STEP_SCRIPT = _SHARED / "step_to_views.py"
SHOT_SCRIPT = _SHARED / "svg_screenshot.py"


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> int:
    proc = subprocess.run(cmd, env=env)
    return int(proc.returncode)


def ensure_cad_env(*, bootstrap: bool) -> dict:
    st = status()
    if st["ok"]:
        print("CAD_VENV: already_ready skip_install=true", file=sys.stderr, flush=True)
        return st
    if not bootstrap:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        print("CAD_VENV: not_ready run bootstrap_cad_venv.py", file=sys.stderr, flush=True)
        raise SystemExit(2)
    print("CAD_VENV: bootstrap_needed", file=sys.stderr, flush=True)
    from bootstrap_cad_venv import bootstrap as do_bootstrap

    return do_bootstrap()


def rasterize_views_dir(views_dir: Path) -> dict:
    if not views_dir.is_dir():
        return {"ok": True, "converted": [], "message": "no_views_dir"}
    env = os.environ.copy()
    env[HOST_PYTHON_ENV] = sys.executable
    proc = subprocess.run(
        [sys.executable, str(SHOT_SCRIPT), "--dir", str(views_dir)],
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
        sys.stderr.flush()
    if proc.returncode != 0 and not proc.stdout.strip():
        return {"ok": False, "error": proc.stderr[-500:] if proc.stderr else "svg_screenshot_failed"}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "raw": proc.stdout[-2000:]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="STEP views via cad-env + optional SVG screenshot")
    p.add_argument("--enable-step-parse", action="store_true")
    p.add_argument("--check-deps", action="store_true")
    p.add_argument("-i", "--input")
    p.add_argument("-o", "--out-dir")
    p.add_argument("--theme", default="")
    p.add_argument("--no-bootstrap", action="store_true", help="Do not install even if cad-env is missing")
    p.add_argument("--no-screenshot", action="store_true", help="Keep SVG only; skip headless PNG")
    args, rest = p.parse_known_args(argv)

    if args.check_deps:
        st = status()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0 if st["ok"] else 2

    try:
        st = ensure_cad_env(bootstrap=not args.no_bootstrap)
    except Exception as e:
        if isinstance(e, SystemExit):
            return int(e.code or 2)
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    py = venv_python()
    env = isolated_env()
    env[HOST_PYTHON_ENV] = sys.executable
    cmd = [str(py), str(STEP_SCRIPT)]
    if args.enable_step_parse:
        cmd.append("--enable-step-parse")
    if args.input:
        cmd.extend(["-i", args.input])
    if args.out_dir:
        cmd.extend(["-o", args.out_dir])
    if args.theme:
        cmd.extend(["--theme", args.theme])
    cmd.extend(rest)
    code = _run(cmd, env=env)
    if code != 0:
        return code

    if args.no_screenshot or not args.out_dir:
        return 0
    views_dir = Path(args.out_dir) / "views"
    shot = rasterize_views_dir(views_dir)
    print(json.dumps({"svg_screenshot": shot}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
