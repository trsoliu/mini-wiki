# -*- coding: utf-8 -*-
"""Create tools/cad-env and install CadQuery (Python 3.10-3.12).

If cad-env already imports cadquery, this script exits 0 and does not reinstall.

pip uses ``python -m pip --isolated`` plus an explicit ``--index-url`` (isolated
mode ignores env/pip.conf). Mirror order: China mirrors, then pypi.org.
requirements-step.txt must stay ASCII (Windows venv pip may decode as GBK).

  python tools/bootstrap_cad_venv.py
  python tools/bootstrap_cad_venv.py --pypi-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from cad_venv import (
    INDEX_ENV,
    VENV_DIR,
    VENV_NAME,
    find_supported_python,
    isolated_env,
    status,
    venv_python,
    version_supported,
    write_meta,
)

REQ_FILE = _SHARED / "requirements-step.txt"

DEFAULT_PIP_INDEXES = (
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://pypi.mirrors.ustc.edu.cn/simple",
    "https://repo.huaweicloud.com/repository/pypi/simple",
    "https://pypi.org/simple",
)


def _index_list(*, pypi_only: bool, extra: list[str]) -> list[str]:
    if pypi_only:
        return ["https://pypi.org/simple"]
    out: list[str] = []
    env_url = os.environ.get(INDEX_ENV, "").strip()
    if env_url:
        out.append(env_url.rstrip("/"))
    for u in extra:
        u = u.strip().rstrip("/")
        if u and u not in out:
            out.append(u)
    for u in DEFAULT_PIP_INDEXES:
        if u not in out:
            out.append(u)
    return out


def _run(cmd: list[str], *, env: dict[str, str] | None = None, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        env=env or isolated_env(),
        timeout=timeout,
        text=True,
        capture_output=True,
    )


def _ensure_pip(py: Path) -> None:
    probe = _run([str(py), "-m", "pip", "--version"], timeout=30)
    if probe.returncode == 0:
        return
    print("CAD_VENV: ensurepip", file=sys.stderr, flush=True)
    ep = _run([str(py), "-m", "ensurepip", "--upgrade"], timeout=120)
    if ep.returncode != 0:
        raise RuntimeError(
            "cad-env has no pip and ensurepip failed: "
            + (ep.stderr or ep.stdout or str(ep.returncode))
        )


def _create_venv(py_exe: str) -> Path:
    VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
    existing = venv_python(VENV_DIR)
    if existing.is_file():
        from cad_venv import python_version

        ver = python_version(existing)
        if version_supported(ver):
            return existing
        print("CAD_VENV: recreate_unsupported_python", file=sys.stderr, flush=True)
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    print(f"CAD_VENV: creating {VENV_DIR} with {py_exe}", file=sys.stderr, flush=True)
    created = _run([py_exe, "-m", "venv", str(VENV_DIR)], timeout=120)
    if created.returncode != 0:
        raise RuntimeError("venv create failed: " + (created.stderr or created.stdout or ""))
    py = venv_python(VENV_DIR)
    if not py.is_file():
        raise RuntimeError(f"venv python missing: {py}")
    return py


def _pip_install(py: Path, indexes: list[str]) -> str:
    if not REQ_FILE.is_file():
        raise RuntimeError(f"missing {REQ_FILE}")
    env = isolated_env()
    print("PIP_INDEX_CANDIDATES: " + " ".join(indexes), file=sys.stderr, flush=True)
    last_err = ""
    for url in indexes:
        cmd = [
            str(py),
            "-m",
            "pip",
            "--isolated",
            "install",
            "--disable-pip-version-check",
            "--index-url",
            url,
            "-r",
            str(REQ_FILE),
        ]
        print(f"PIP_INDEX: {url}", file=sys.stderr, flush=True)
        proc = _run(cmd, env=env, timeout=900)
        if proc.returncode == 0:
            return url
        last_err = (proc.stderr or proc.stdout or f"exit={proc.returncode}")[-2000:]
        print(f"PIP_INDEX_FAIL: {url} exit={proc.returncode}", file=sys.stderr, flush=True)
    raise RuntimeError("pip install failed on all indexes: " + last_err)


def bootstrap(*, pypi_only: bool = False, extra_index: list[str] | None = None) -> dict:
    st = status()
    if st["ok"]:
        print(
            "CAD_VENV: already_ready skip_install=true",
            file=sys.stderr,
            flush=True,
        )
        return st

    py_exe, ver = find_supported_python()
    if not py_exe:
        raise RuntimeError(
            "CadQuery needs Python 3.10-3.12. Current interpreter is "
            f"{sys.version.split()[0]}. Install 3.10, 3.11, or 3.12 and retry."
        )
    print(
        f"CAD_VENV: using_python={py_exe} version={ver[0]}.{ver[1]}.{ver[2]}",
        file=sys.stderr,
        flush=True,
    )
    venv_py = _create_venv(py_exe)
    _ensure_pip(venv_py)
    used = _pip_install(venv_py, _index_list(pypi_only=pypi_only, extra=list(extra_index or [])))
    write_meta(
        {
            "venv_name": VENV_NAME,
            "host_python": sys.executable,
            "venv_python": str(venv_py),
            "base_python": py_exe,
            "pip_index": used,
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        }
    )
    st = status()
    if not st["ok"]:
        raise RuntimeError("bootstrap finished but cadquery still missing: " + json.dumps(st, ensure_ascii=False))
    return st


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Create or reuse tools/cad-env")
    p.add_argument("--pypi-only", action="store_true", help="Use pypi.org only")
    p.add_argument(
        "--index-url",
        action="append",
        default=[],
        help="Extra pip index (still tries pypi.org last). Or set PATENT_SKILL_PIP_INDEX",
    )
    args = p.parse_args(argv)
    try:
        st = bootstrap(pypi_only=args.pypi_only, extra_index=args.index_url)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(st, ensure_ascii=False, indent=2))
    print(
        f"CAD_VENV: ok={'true' if st['ok'] else 'false'} skip_install="
        f"{'true' if st.get('skip_install') else 'false'} reason={st.get('reason') or ''}",
        file=sys.stderr,
        flush=True,
    )
    return 0 if st["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
