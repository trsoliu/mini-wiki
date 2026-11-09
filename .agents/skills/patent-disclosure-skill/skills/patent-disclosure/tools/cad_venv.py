# -*- coding: utf-8 -*-
"""Locate and probe the CadQuery venv named ``cad-env``.

CadQuery wheels support Python 3.10-3.12. Do not force 3.10 when 3.11/3.12
is already available. Host 3.13+ must pick another interpreter for the venv.

  python tools/cad_venv.py
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parent
VENV_NAME = "cad-env"
VENV_DIR = _SHARED / VENV_NAME
META_NAME = "cad_venv_meta.json"
MIN_MINOR = (3, 10)
MAX_MINOR = (3, 12)

INDEX_ENV = "PATENT_SKILL_PIP_INDEX"
HOST_PYTHON_ENV = "PATENT_SKILL_HOST_PYTHON"


def isolated_env() -> dict[str, str]:
    """Drop PIP_* / PYTHONPATH so 3.13 site-packages cannot leak into cad-env."""
    env = os.environ.copy()
    drop = [k for k in env if k.startswith("PIP_") or k in {"PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE"}]
    for k in drop:
        env.pop(k, None)
    env["PYTHONNOUSERSITE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def venv_python(venv_dir: Path | None = None) -> Path:
    root = venv_dir or VENV_DIR
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def meta_path(venv_dir: Path | None = None) -> Path:
    return (venv_dir or VENV_DIR) / META_NAME


def read_meta(venv_dir: Path | None = None) -> dict[str, Any]:
    path = meta_path(venv_dir)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def write_meta(data: dict[str, Any], venv_dir: Path | None = None) -> None:
    path = meta_path(venv_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def python_version(exe: str | Path) -> tuple[int, int, int] | None:
    try:
        out = subprocess.check_output(
            [str(exe), "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
            env=isolated_env(),
            stderr=subprocess.DEVNULL,
            timeout=20,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = out.strip().split(".")
    if len(parts) < 2:
        return None
    try:
        major, minor = int(parts[0]), int(parts[1])
        micro = int(parts[2]) if len(parts) > 2 else 0
    except ValueError:
        return None
    return major, minor, micro


def version_supported(ver: tuple[int, int, int] | None) -> bool:
    if ver is None:
        return False
    return MIN_MINOR <= ver[:2] <= MAX_MINOR


def _py_launcher(minor: int) -> list[str]:
    if os.name == "nt":
        return ["py", f"-3.{minor}"]
    return [f"python3.{minor}"]


def find_supported_python() -> tuple[str | None, tuple[int, int, int] | None]:
    """Prefer the current interpreter when it is 3.10-3.12; else newest supported."""
    current = tuple(sys.version_info[:3])
    if version_supported(current):
        return sys.executable, current

    for minor in (12, 11, 10):
        cmd = _py_launcher(minor)
        try:
            out = subprocess.check_output(
                cmd + ["-c", "import sys; print(sys.executable); print('%d.%d.%d' % sys.version_info[:3])"],
                env=isolated_env(),
                stderr=subprocess.DEVNULL,
                timeout=20,
                text=True,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        ver = tuple(int(x) for x in lines[1].split(".")[:3])
        if version_supported(ver):  # type: ignore[arg-type]
            return lines[0], ver  # type: ignore[return-value]
    return None, None


def host_python() -> str | None:
    env_py = os.environ.get(HOST_PYTHON_ENV, "").strip()
    if env_py and Path(env_py).is_file():
        return env_py
    meta = read_meta()
    saved = str(meta.get("host_python") or "").strip()
    if saved and Path(saved).is_file():
        return saved
    return sys.executable


def _cadquery_ok(py: Path) -> tuple[bool, str]:
    try:
        out = subprocess.check_output(
            [str(py), "-c", "import cadquery as cq; print(getattr(cq, '__version__', 'unknown'))"],
            env=isolated_env(),
            stderr=subprocess.STDOUT,
            timeout=45,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    return True, out.strip().splitlines()[-1] if out.strip() else "unknown"


def status(venv_dir: Path | None = None) -> dict[str, Any]:
    root = venv_dir or VENV_DIR
    py = venv_python(root)
    report: dict[str, Any] = {
        "ok": False,
        "venv_name": VENV_NAME,
        "venv_dir": str(root),
        "python": str(py) if py.is_file() else "",
        "version": "",
        "cadquery": "",
        "reason": "",
        "skip_install": False,
        "supported": f"{MIN_MINOR[0]}.{MIN_MINOR[1]}-{MAX_MINOR[0]}.{MAX_MINOR[1]}",
        "bootstrap": "python tools/bootstrap_cad_venv.py",
    }
    if not py.is_file():
        report["reason"] = "missing_venv"
        return report
    ver = python_version(py)
    if ver:
        report["version"] = "%d.%d.%d" % ver
    if not version_supported(ver):
        report["reason"] = "unsupported_python"
        return report
    ok, info = _cadquery_ok(py)
    if not ok:
        report["reason"] = "cadquery_missing"
        report["cadquery"] = info
        return report
    report["ok"] = True
    report["skip_install"] = True
    report["cadquery"] = info
    report["reason"] = "ready"
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Probe tools/cad-env (CadQuery 3.10-3.12)")
    p.parse_args(argv)
    st = status()
    print(json.dumps(st, ensure_ascii=False, indent=2))
    print(
        f"CAD_VENV: ok={'true' if st['ok'] else 'false'} skip_install="
        f"{'true' if st['skip_install'] else 'false'} reason={st.get('reason') or ''}",
        file=sys.stderr,
        flush=True,
    )
    return 0 if st["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
