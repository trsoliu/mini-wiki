# -*- coding: utf-8 -*-
"""探测 / 安装外挂 book-to-skill（MIT 转换器，不是书）。"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

GITHUB_REPO = "virgiliojr94/book-to-skill"
GITHUB_README = f"https://raw.githubusercontent.com/{GITHUB_REPO}/master/README.md"
GITHUB_PAGE = f"https://github.com/{GITHUB_REPO}"
FALLBACK_NPX = f"npx --yes skills add {GITHUB_REPO}"
SKILL_DIR_NAMES = ("book-to-skill", "book_to_skill")


def _home() -> Path:
    return Path.home().expanduser()


def candidate_skill_roots() -> list[Path]:
    home = _home()
    extra = os.environ.get("PATENT_OA_SKILLS_DIR", "").strip()
    roots = [
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".copilot" / "skills",
        home / ".cursor" / "skills",
    ]
    if extra:
        roots.insert(0, Path(extra).expanduser())
    return roots


def find_book_to_skill() -> Path | None:
    for root in candidate_skill_roots():
        if not root.is_dir():
            continue
        for name in SKILL_DIR_NAMES:
            skill = root / name / "SKILL.md"
            if skill.is_file():
                return skill.parent
        for child in root.iterdir():
            if not child.is_dir():
                continue
            skill = child / "SKILL.md"
            if not skill.is_file():
                continue
            try:
                head = skill.read_text(encoding="utf-8", errors="replace")[:800].lower()
            except OSError:
                continue
            if "book-to-skill" in head or "booklin" in head:
                return child
    return None


def fetch_github_install_cmd(*, timeout: float = 12.0) -> dict[str, Any]:
    req = urllib.request.Request(
        GITHUB_README,
        headers={"User-Agent": "patent-disclosure-skill-oa-playbook"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "page": GITHUB_PAGE,
            "command": FALLBACK_NPX,
        }
    cmd = FALLBACK_NPX
    m = re.search(r"npx(?:\s+--yes)?\s+skills\s+add\s+\S+", text)
    if m:
        cmd = m.group(0).strip()
        if " --yes " not in f" {cmd} " and cmd.startswith("npx "):
            cmd = "npx --yes " + cmd[4:]
    return {"ok": True, "page": GITHUB_PAGE, "command": cmd, "readme": GITHUB_README}


def _run(cmd: list[str] | str, *, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    if isinstance(cmd, str):
        return subprocess.run(
            cmd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def _npx_cmd() -> str | None:
    return shutil.which("npx") or shutil.which("npx.cmd")


def install_book_to_skill(command: str | None = None) -> dict[str, Any]:
    cmd = (command or FALLBACK_NPX).strip()
    npx = _npx_cmd()
    if npx and "npx" in cmd.split()[0]:
        # replace leading npx with resolved binary on Windows
        rest = cmd.split(None, 1)[1] if " " in cmd else ""
        argv = [npx] + (rest.split() if rest else [])
        try:
            proc = _run(argv)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return {"ok": False, "method": "npx", "error": str(exc), "command": cmd}
        if proc.returncode == 0:
            found = find_book_to_skill()
            return {
                "ok": True,
                "method": "npx",
                "command": cmd,
                "skill_path": str(found) if found else "",
                "stdout_tail": (proc.stdout or "")[-800:],
            }
        npx_err = (proc.stderr or proc.stdout or "")[-800:]
    else:
        npx_err = "npx not found"

    dest = _home() / ".agents" / "skills" / "book-to-skill"
    dest.parent.mkdir(parents=True, exist_ok=True)
    git = shutil.which("git") or shutil.which("git.exe")
    if not git:
        return {
            "ok": False,
            "method": "clone",
            "error": f"npx 失败且未找到 git。npx: {npx_err}",
            "page": GITHUB_PAGE,
            "command": FALLBACK_NPX,
        }
    if dest.exists():
        shutil.rmtree(dest)
    try:
        proc = _run(
            [git, "clone", "--depth", "1", f"https://github.com/{GITHUB_REPO}.git", str(dest)]
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "method": "clone", "error": str(exc), "page": GITHUB_PAGE}
    if proc.returncode != 0:
        return {
            "ok": False,
            "method": "clone",
            "error": (proc.stderr or proc.stdout or "")[-800:],
            "page": GITHUB_PAGE,
        }
    return {"ok": True, "method": "clone", "skill_path": str(dest), "command": "git clone"}


def ensure_book_to_skill(*, install: bool = True) -> dict[str, Any]:
    found = find_book_to_skill()
    if found is not None:
        return {
            "ok": True,
            "installed": True,
            "method": "already",
            "skill_path": str(found),
            "page": GITHUB_PAGE,
        }
    github = fetch_github_install_cmd()
    report: dict[str, Any] = {
        "ok": False,
        "installed": False,
        "method": "missing",
        "github": {k: github[k] for k in github if k != "readme"},
        "page": GITHUB_PAGE,
    }
    if not install:
        report["error"] = "未安装 book-to-skill"
        return report
    print(f"PLAYBOOK: installing via {github.get('command') or FALLBACK_NPX}", file=sys.stderr)
    installed = install_book_to_skill(str(github.get("command") or FALLBACK_NPX))
    report.update(installed)
    if installed.get("ok"):
        report["installed"] = True
        if not report.get("skill_path"):
            again = find_book_to_skill()
            report["skill_path"] = str(again) if again else installed.get("skill_path") or ""
    return report
