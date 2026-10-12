#!/usr/bin/env python
"""保护型 1+N 中间稿校验：分解 / 突围 / 功效矩阵。"""
from __future__ import annotations

from typing import Any

LAYERS = {"principle", "module", "chain", "scenario"}
COMMERCIAL = {"yes", "no", "unknown"}
DISPOSITION = {"dependent", "satellite", "drop"}
DENSITY = {"dense", "sparse", "unchecked"}


def validate_decompose(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes = doc.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return ["decompose.nodes 不能为空"]
    ids: list[str] = []
    for n in nodes:
        if not isinstance(n, dict):
            errors.append("decompose 节点须为 mapping")
            continue
        nid = str(n.get("id") or "").strip()
        if not nid:
            errors.append("decompose 缺 id")
            continue
        ids.append(nid)
        if str(n.get("layer") or "") not in LAYERS:
            errors.append(f"{nid} layer 须 principle|module|chain|scenario")
        if not str(n.get("summary") or "").strip():
            errors.append(f"{nid} 缺 summary")
        if not str(n.get("source") or "").strip():
            errors.append(f"{nid} 缺 source（交底章节或材料路径）")
    if len(ids) != len(set(ids)):
        errors.append("decompose id 重复")
    return errors


def _yn(value) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return str(value or "").strip()


def validate_design_around(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = doc.get("rows")
    if not isinstance(rows, list) or not rows:
        return ["design_around.rows 不能为空"]
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row {i} 须为 mapping")
            continue
        feat = str(row.get("feature") or "").strip() or f"#{i}"
        if _yn(row.get("commercial")) not in COMMERCIAL:
            errors.append(f"{feat} commercial 须 yes|no|unknown")
        disp = str(row.get("disposition") or "")
        if disp not in DISPOSITION:
            errors.append(f"{feat} disposition 须 dependent|satellite|drop")
        if _yn(row.get("commercial")) == "unknown" and disp == "satellite":
            errors.append(f"{feat} 商业未知不得立项为 satellite")
    return errors


def validate_matrix(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    means = doc.get("means") or []
    effects = doc.get("effects") or []
    if not isinstance(means, list) or not means:
        errors.append("matrix.means 不能为空")
    if not isinstance(effects, list) or not effects:
        errors.append("matrix.effects 不能为空")
    mids = {str(x.get("id") or "") for x in means if isinstance(x, dict)}
    eids = {str(x.get("id") or "") for x in effects if isinstance(x, dict)}
    cells = doc.get("cells") or []
    if not isinstance(cells, list) or not cells:
        errors.append("matrix.cells 不能为空（没查过的格子标 unchecked，不要省略）")
        return errors
    for c in cells:
        if not isinstance(c, dict):
            continue
        if str(c.get("mean") or "") not in mids:
            errors.append(f"cell mean 未知: {c.get('mean')}")
        if str(c.get("effect") or "") not in eids:
            errors.append(f"cell effect 未知: {c.get('effect')}")
        dens = str(c.get("density") or "")
        if dens not in DENSITY:
            errors.append("cell density 须 dense|sparse|unchecked")
    return errors
