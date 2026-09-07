"""Windows 终端 UTF-8：当前进程 stdio + 子进程 PYTHONUTF8。

PowerShell 5 会把写入 stderr 标成 NativeCommandError，但退出码仍可能是 0。
Agent 应以退出码和机读前缀为准，不要把 stderr 当失败。
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any


def ensure_utf8_stdio() -> None:
    """当前进程 stdout/stderr 按 UTF-8；并为子进程准备 PYTHONUTF8。"""
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream in (sys.stdout, sys.stderr):
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, TypeError):
            pass


def child_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base) if base is not None else os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run(cmd: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """``subprocess.run``：强制 UTF-8 文本，子进程带 PYTHONUTF8。"""
    kwargs.setdefault("encoding", "utf-8")
    kwargs.setdefault("errors", "replace")
    kwargs["env"] = child_env(kwargs.get("env"))
    kwargs.pop("text", None)
    return subprocess.run(cmd, **kwargs)
