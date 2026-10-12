# -*- coding: utf-8 -*-
"""阶段表与枚举（与 references/phases.yaml 对齐）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_PKG = Path(__file__).resolve().parents[1]

START_MODES = (
    "from_zero",
    "from_disclosure",
    "from_application",
    "resume",
)
PATENT_TYPES = ("invention", "utility_model", "design")
ISSUE_KINDS = (
    "machine_format",
    "claim_form",
    "scope_strategy",
    "disclosure_gap",
    "human_fact",
    "noise",
)
DISPOSITIONS = (
    "ignore",
    "application_fix",
    "disclosure_fix",
    "ask_human",
    "defer",
)
STATUSES = ("open", "done", "deferred")
TERMINAL_PHASES = frozenset(
    {"terminal_complete", "terminal_max_rounds", "terminal_blocked"}
)


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML 须为对象: {path}")
    return data


def load_phase_table(path: Path | None = None) -> dict[str, Any]:
    target = path or (_PKG / "references" / "phases.yaml")
    return _load_yaml(target)


def phase_names(table: dict[str, Any] | None = None) -> tuple[str, ...]:
    data = table or load_phase_table()
    names = data.get("phases") or []
    return tuple(str(n) for n in names)


def transitions(table: dict[str, Any] | None = None) -> dict[str, tuple[str, ...]]:
    data = table or load_phase_table()
    raw = data.get("transitions") or {}
    out: dict[str, tuple[str, ...]] = {}
    for key, dests in raw.items():
        out[str(key)] = tuple(str(d) for d in (dests or []))
    return out


def can_transit(current: str, nxt: str, table: dict[str, Any] | None = None) -> bool:
    if current == nxt:
        return True
    allowed = transitions(table).get(current, ())
    return nxt in allowed
