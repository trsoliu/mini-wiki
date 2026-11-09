# -*- coding: utf-8 -*-
"""按范式 tag 的轻量检查：量纲粗匹配、加权系数（均为 warning）。"""
from __future__ import annotations

import re
from typing import Any

_FAMILIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dimensionless", ("无量纲", "[0,1]", "(0,1]", "比例", "%", "percent", "1")),
    ("mass", ("kg", "g", "mg", "质量", "mass")),
    ("length", ("mm", "cm", "km", "m", "长度")),
    ("time", ("ms", "s", "min", "h", "秒", "小时")),
    ("amount", ("mol", "摩尔")),
    ("volume", ("ml", "l", "m3", "m^3", "升")),
    ("concentration", ("mol/l", "mol/m", "mol·", "mol/", "molar")),
    ("energy", ("j", "ev", "kj", "w·h")),
)


def _family(unit_zh: str) -> str | None:
    u = unit_zh.strip().lower().replace(" ", "")
    if not u:
        return None
    for name, keys in _FAMILIES:
        for k in keys:
            if k.lower() in u:
                return name
    return None


def _norm_sym(raw: str) -> str:
    s = str(raw).strip()
    s = s.replace("\\\\", "\\")
    s = re.sub(r"\\mathrm\s*\{([^}]*)\}", r"\1", s)
    s = s.replace("{", "").replace("}", "").replace("\\", "")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s)
    return s.strip("_").lower()


def check_additive_units(
    equations: list[dict[str, Any]],
    symbols: list[dict[str, Any]] | None,
) -> list[str]:
    """简单和式中，相加符号若单位族不同则警告。"""
    if not isinstance(symbols, list):
        return []
    fam: dict[str, str] = {}
    for item in symbols:
        if not isinstance(item, dict):
            continue
        fam_name = _family(str(item.get("unit_zh") or ""))
        if not fam_name:
            continue
        fam[_norm_sym(item.get("symbol") or "")] = fam_name
    if len(fam) < 2:
        return []
    warnings: list[str] = []
    for i, eq in enumerate(equations or []):
        if not isinstance(eq, dict):
            continue
        lx = str(eq.get("latex") or "").replace("\\\\", "\\")
        if "+" not in lx and "-" not in lx:
            continue
        if re.search(r"\\sum|\\prod|\\ce\{", lx):
            continue
        lx_n = "_" + _norm_sym(lx) + "_"
        present = [
            k
            for k in fam
            if k and re.search(rf"(^|_){re.escape(k)}(_|$)", lx_n)
        ]
        families = {fam[k] for k in present}
        # 无量纲可与任何项相加（视为已归一）——仅当出现两个以上有量纲且不同族
        dimful = {f for f in families if f != "dimensionless"}
        if len(dimful) >= 2:
            warnings.append(
                f"equations[{i}] 相加项量纲族不一致: {sorted(dimful)}（请先归一或改符号表）"
            )
    return warnings


def check_score_weights(
    paradigm_ids: list[str],
    given: dict[str, Any] | None,
) -> list[str]:
    """weighted_sum 类：若 given 同时给出 αβγ，和宜接近 1（警告）。"""
    if not any(p in {"weighted_sum", "weighted_sum_unit"} for p in paradigm_ids):
        return []
    if not isinstance(given, dict):
        return []
    keys = {}
    for k, v in given.items():
        kn = str(k).lower().replace("\\", "")
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if "alpha" in kn or kn in ("α", "a_w"):
            keys["alpha"] = fv
        elif "beta" in kn or kn == "β":
            keys["beta"] = fv
        elif "gamma" in kn or kn == "γ":
            keys["gamma"] = fv
    if len(keys) < 2:
        return []
    s = sum(keys.values())
    if abs(s - 1.0) > 0.05:
        return [f"加权系数 {keys} 之和为 {s:.4g}，建议在参数表说明未归一或改为和为 1"]
    return []
