#!/usr/bin/env python
"""加载评分表定义、核验作答、立项后弱校验（是否建议写下外围）。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_FENCE = Path(__file__).resolve().parent
_TOOLS = _FENCE.parent
for p in (_FENCE, _TOOLS):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

DEFAULT_TABLE = _FENCE.parents[1] / "references" / "scorecards" / "gbt42748_fence.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        import yaml

        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"根须为 mapping: {path}")
    return data


def resolve_table_path(case_dir: str | Path | None = None) -> Path:
    if case_dir:
        cd = Path(case_dir).expanduser()
        for rel in ("fence_scorecard.yaml", "fence/fence_scorecard.yaml"):
            p = cd / rel
            if p.is_file():
                return p
    env = (os.environ.get("PATENT_DISCLOSURE_SCORECARD") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
        raise FileNotFoundError(env)
    return DEFAULT_TABLE


def load_table(case_dir: str | Path | None = None) -> dict[str, Any]:
    path = resolve_table_path(case_dir)
    table = _load_yaml(path)
    table["_source"] = str(path)
    validate_table(table)
    return table


def validate_table(table: dict[str, Any]) -> None:
    for key in ("id", "title_zh", "disclaimer_zh", "groups", "items", "thresholds"):
        if key not in table:
            raise ValueError(f"评分表缺 {key}")
    ids = [str(it.get("id") or "") for it in table["items"]]
    if len(ids) != len(set(ids)) or not all(ids):
        raise ValueError("items.id 必须唯一且非空")
    gids = {str(g.get("id") or "") for g in table["groups"]}
    for it in table["items"]:
        if it.get("group") not in gids:
            raise ValueError(f"item {it.get('id')} group 不在 groups 内")
        if it.get("missing") not in ("unscored", "zero"):
            raise ValueError(f"item {it.get('id')} missing 须 unscored|zero")


def item_by_id(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(it["id"]): it for it in table["items"]}


def _cell(raw: dict[str, Any], iid: str) -> dict[str, Any]:
    cell = raw.get(iid) or {}
    if not isinstance(cell, dict):
        return {"score": cell}
    return cell


def item_score(raw: dict[str, Any], iid: str) -> int | None:
    s = _cell(raw, iid).get("score", None)
    if s is None or s == "" or str(s).lower() in ("unscored", "null", "none"):
        return None
    return int(s)


def score_answers(table: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    catalog = item_by_id(table)
    raw = answers.get("items") or {}
    if not isinstance(raw, dict):
        raise ValueError("作答 items 须为 mapping")
    earned: dict[str, int] = {}
    max_possible: dict[str, int] = {}
    unscored: list[str] = []
    notes: dict[str, str] = {}
    for iid, spec in catalog.items():
        grp = str(spec["group"])
        max_possible[grp] = max_possible.get(grp, 0) + 2
        cell = _cell(raw, iid)
        evidence = str(cell.get("evidence") or "").strip()
        notes[iid] = evidence
        score = item_score(raw, iid)
        if score is None:
            if spec.get("missing") == "zero":
                earned.setdefault(grp, 0)
            else:
                unscored.append(iid)
            continue
        if score not in (0, 1, 2):
            raise ValueError(f"{iid} score 须为 0|1|2")
        if score > 0 and not evidence:
            raise ValueError(f"{iid} 正分必须写 evidence（引用交底/查新，不编）")
        earned[grp] = earned.get(grp, 0) + score
    for g in (x["id"] for x in table["groups"]):
        earned.setdefault(g, 0)
        max_possible.setdefault(g, 0)
    decision = decide(table, earned, raw, catalog)
    return {
        "scorecard_id": table.get("id"),
        "earned": earned,
        "max_possible": max_possible,
        "unscored": unscored,
        "open_fence": decision["open_fence"],
        "borderline": decision["borderline"],
        "reasons": decision["reasons"],
        "notes": notes,
    }


def _earned_on(earned: dict[str, int], groups: list[str]) -> int:
    return sum(int(earned.get(g, 0)) for g in groups)


def decide(
    table: dict[str, Any],
    earned: dict[str, int],
    raw: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    th = (table.get("thresholds") or {}).get("open_fence") or {}
    reasons: list[str] = []
    req_groups = list(th.get("require_scored_groups") or [])
    for g in req_groups:
        if all(item_score(raw, iid) is None for iid, spec in catalog.items() if spec.get("group") == g):
            reasons.append(f"分组 {g} 全部未决")
    for iid, need in (th.get("min_item") or {}).items():
        got = item_score(raw, str(iid))
        if got is None or got < int(need):
            reasons.append(f"{iid} 未达到 {need}")
    target = th.get("min_earned_on") or {}
    groups = list(target.get("groups") or ["legal", "technical", "fence"])
    need_val = int(target.get("value") or 16)
    got_val = _earned_on(earned, groups)
    if got_val < need_val:
        reasons.append(f"{'+'.join(groups)} 合计 {got_val} < {need_val}")
    open_fence = not reasons
    bth = (table.get("thresholds") or {}).get("borderline") or {}
    b_groups = list((bth.get("min_earned_on") or {}).get("groups") or groups)
    b_need = int((bth.get("min_earned_on") or {}).get("value") or 12)
    borderline = (not open_fence) and _earned_on(earned, b_groups) >= b_need
    return {"open_fence": open_fence, "borderline": borderline, "reasons": reasons}
