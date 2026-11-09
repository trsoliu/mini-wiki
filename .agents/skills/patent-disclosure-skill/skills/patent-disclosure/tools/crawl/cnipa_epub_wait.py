# -*- coding: utf-8 -*-
"""公布站等待参数：优先读同目录 YAML，缺项或文件不可用时回退 DEFAULTS。"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

# 与 cnipa_epub_wait.yaml 默认值保持一致；YAML 缺失时用这里。
DEFAULTS: dict[str, Any] = {
    "goto_timeout_ms": 30_000,
    "goto_wait_until": "commit",
    "gate_poll_sec": 30.0,
    "gate_poll_step_sec": 1.0,
    "submit_timeout_ms": 40_000,
    "advanced_max_class_codes": 1,
    "advanced_max_terms": 1,
    "home_max_terms": 4,
    "stop_on_first_nav_failure": True,
}

_WAIT_UNTIL = frozenset({"commit", "domcontentloaded", "load"})
_INT_KEYS = frozenset(
    {
        "goto_timeout_ms",
        "submit_timeout_ms",
        "advanced_max_class_codes",
        "advanced_max_terms",
        "home_max_terms",
    }
)
_FLOAT_KEYS = frozenset({"gate_poll_sec", "gate_poll_step_sec"})
_BOOL_KEYS = frozenset({"stop_on_first_nav_failure"})

_CACHE: dict[str, Any] | None = None


class EpubNavError(Exception):
    """goto=打不开站；gate=页面到了框不出现；submit=已提交结果页不来。"""

    def __init__(
        self,
        stage: str,
        *,
        hint: str = "",
        message: str = "",
        timeout_s: float | None = None,
        url: str = "",
    ) -> None:
        self.stage = stage
        self.hint = hint
        self.timeout_s = timeout_s
        self.url = url
        self.detail = message
        parts = [f"stage={stage}"]
        if timeout_s is not None:
            parts.append(f"timeout_s={timeout_s:g}")
        if url:
            parts.append(f"url={url}")
        if hint:
            parts.append(f"hint={hint}")
        if message:
            parts.append(message)
        super().__init__(" ".join(parts))


def default_yaml_path() -> Path:
    return Path(__file__).resolve().parent / "cnipa_epub_wait.yaml"


def wait_yaml_path() -> Path:
    raw = (os.environ.get("EPUB_WAIT_YAML") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return default_yaml_path()


def _coerce(key: str, raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    try:
        if key in _INT_KEYS:
            val = int(raw)
            return val if val > 0 else default
        if key in _FLOAT_KEYS:
            val = float(raw)
            return val if val > 0 else default
        if key in _BOOL_KEYS:
            if isinstance(raw, bool):
                return raw
            text = str(raw).strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off"}:
                return False
            return default
        if key == "goto_wait_until":
            text = str(raw).strip().lower()
            return text if text in _WAIT_UNTIL else default
    except (TypeError, ValueError):
        return default
    return default


def _from_mapping(data: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(DEFAULTS)
    if not isinstance(data, dict):
        return out
    for key, default in DEFAULTS.items():
        if key in data:
            out[key] = _coerce(key, data[key], default)
    return out


def load_wait_config(*, force_reload: bool = False) -> dict[str, Any]:
    """合并 YAML 与 DEFAULTS。``force_reload`` 供测试。"""
    global _CACHE
    if _CACHE is not None and not force_reload:
        cfg = dict(_CACHE)
    else:
        cfg = dict(DEFAULTS)
        path = wait_yaml_path()
        if path.is_file():
            try:
                import yaml  # type: ignore

                loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
                cfg = _from_mapping(loaded if isinstance(loaded, dict) else None)
            except Exception:
                cfg = dict(DEFAULTS)
        _CACHE = dict(cfg)
        cfg = dict(cfg)
    env_gate = (os.environ.get("EPUB_WAF_MAX_WAIT_SEC") or "").strip()
    if env_gate:
        try:
            sec = float(env_gate)
            if sec > 0:
                cfg["gate_poll_sec"] = sec
        except ValueError:
            pass
    return cfg


def progress(msg: str) -> None:
    print(f"EPUB_PROGRESS: {msg}", file=sys.stderr, flush=True)
