#!/usr/bin/env python
"""保护型 1+N 族树 YAML 校验。"""
from __future__ import annotations

from typing import Any

ROLES = {"core", "satellite"}
TYPES = {"invention", "utility_model", "design"}
N_CLASS = {"scenario", "improve", "chain"}
DENSITY = {"dense", "sparse", "unchecked", ""}
MAX_CORE = 2
MAX_SAT = 3


def validate_family(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    title = str(plan.get("title") or "")
    if "专利布局" not in title:
        errors.append("title 必须含「专利布局」")
    if "保护型" not in title and "1+N" not in title and "1＋N" not in title:
        errors.append("title 须点明保护型 1+N")
    if str(plan.get("strategy") or "protective") != "protective":
        errors.append("strategy 只能是 protective（不做制衡型围别人）")
    nodes = plan.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 不能为空")
        return errors
    ids: list[str] = []
    write_core = 0
    write_sat = 0
    cores = 0
    sats = 0
    for node in nodes:
        if not isinstance(node, dict):
            errors.append("node 须为 mapping")
            continue
        nid = str(node.get("id") or "").strip()
        if not nid:
            errors.append("node 缺 id")
            continue
        ids.append(nid)
        role = str(node.get("role") or "")
        if role == "fence":
            role = "satellite"
            node["role"] = "satellite"
        if role not in ROLES:
            errors.append(f"{nid} role 须 core|satellite")
        ptype = str(node.get("patent_type") or "")
        if ptype not in TYPES:
            errors.append(f"{nid} patent_type 须 invention|utility_model|design")
        if not str(node.get("title") or "").strip():
            errors.append(f"{nid} 缺 title")
        if not str(node.get("necessary_features") or "").strip():
            errors.append(f"{nid} 缺 necessary_features")
        dens = str(node.get("matrix_density") or "")
        if dens not in DENSITY:
            errors.append(f"{nid} matrix_density 非法")
        if role == "core":
            cores += 1
            if not str(node.get("slim_note") or "").strip():
                errors.append(f"{nid} 核心须写 slim_note（从首篇拆走什么）")
        if role == "satellite":
            sats += 1
            ncl = str(node.get("n_class") or "")
            if ncl not in N_CLASS:
                errors.append(f"{nid} n_class 须 scenario|improve|chain")
            if dens == "dense" and node.get("write_this_round"):
                errors.append(f"{nid} 矩阵 dense 不得 write_this_round")
        if node.get("write_this_round"):
            if not node.get("material_ok", True):
                errors.append(f"{nid} material_ok=false 不能 write_this_round")
            if role == "core":
                write_core += 1
            elif role == "satellite":
                write_sat += 1
    if len(ids) != len(set(ids)):
        errors.append("node id 重复")
    if cores < 1:
        errors.append("至少 1 个 core")
    if write_core > MAX_CORE:
        errors.append(f"本趟核心成稿不得超过 {MAX_CORE}")
    if write_sat > MAX_SAT:
        errors.append(f"本趟外围成稿不得超过 {MAX_SAT}")
    return errors
