# -*- coding: utf-8 -*-
"""CAD / 三维交换格式后缀分类（无重依赖，供扫描与 Agent 提示）。"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

# 中性 STEP（本技能可选解析目标）
STEP_SUFFIXES: frozenset[str] = frozenset({".step", ".stp"})

# 同属中性几何，但本工具不直接解析；提示可再导出 STEP
IGES_SUFFIXES: frozenset[str] = frozenset({".iges", ".igs"})

# 原生 / 厂商 CAD（需用户导出 STEP 后再开解析）
# 含常见机械/工业设计后缀；.prt/.asm 在多家软件中复用，一律视为 CAD 相关
NATIVE_CAD_SUFFIXES: frozenset[str] = frozenset(
    {
        # SolidWorks
        ".sldprt",
        ".sldasm",
        ".slddrw",
        # Autodesk Inventor
        ".ipt",
        ".iam",
        ".idw",
        # Creo / Pro‑ENGINEER / NX（.prt/.asm 亦见于多厂商）
        ".prt",
        ".asm",
        ".xpr",
        ".xas",
        # Parasolid
        ".x_t",
        ".x_b",
        # CATIA
        ".catpart",
        ".catproduct",
        ".catdrawing",
        # Solid Edge
        ".par",
        ".psm",
        ".pwd",
        # Rhino / Alias 等造型
        ".3dm",
        ".wire",
        # Fusion 360 等
        ".f3d",
        ".f3z",
        # AutoCAD 系（常为工程图/三维混合）
        ".dwg",
        ".dxf",
        # 其他常见交换/内核
        ".sat",  # ACIS
        ".sab",
        ".model",  # CATIA V4 等
        ".exp",
    }
)

# 网格（不算「可导出 STEP 的工程源」，扫描时单独列出，弱提示）
MESH_SUFFIXES: frozenset[str] = frozenset({".stl", ".3mf", ".obj"})


def normalize_suffix(path: str | Path) -> str:
    return Path(path).suffix.lower()


def is_step(path: str | Path) -> bool:
    return normalize_suffix(path) in STEP_SUFFIXES


def is_native_cad(path: str | Path) -> bool:
    return normalize_suffix(path) in NATIVE_CAD_SUFFIXES


def is_iges(path: str | Path) -> bool:
    return normalize_suffix(path) in IGES_SUFFIXES


def is_mesh(path: str | Path) -> bool:
    return normalize_suffix(path) in MESH_SUFFIXES


def classify_path(path: str | Path) -> str | None:
    """返回 step | native_cad | iges | mesh | None。"""
    s = normalize_suffix(path)
    if s in STEP_SUFFIXES:
        return "step"
    if s in NATIVE_CAD_SUFFIXES:
        return "native_cad"
    if s in IGES_SUFFIXES:
        return "iges"
    if s in MESH_SUFFIXES:
        return "mesh"
    return None


def iter_classified(
    roots: Iterable[str | Path],
    *,
    recursive: bool = True,
) -> dict[str, list[str]]:
    """扫描目录，按类收集绝对路径字符串（已排序去重）。"""
    buckets: dict[str, set[str]] = {
        "step": set(),
        "native_cad": set(),
        "iges": set(),
        "mesh": set(),
    }
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        if base.is_file():
            kind = classify_path(base)
            if kind:
                buckets[kind].add(str(base.resolve()))
            continue
        pattern = "**/*" if recursive else "*"
        for p in base.glob(pattern):
            if not p.is_file():
                continue
            kind = classify_path(p)
            if kind:
                buckets[kind].add(str(p.resolve()))
    return {k: sorted(v) for k, v in buckets.items()}


def recommend_action(
    step_files: list[str],
    native_cad_files: list[str],
    iges_files: list[str] | None = None,
) -> str:
    """
    ask_enable_step_parse — 发现 STEP，交底落盘后再反问（成文不中断）
    hint_export_step — 仅有原生/IGES，流程可继续，交付时提示导出
    none — 无相关文件
    """
    if step_files:
        return "ask_enable_step_parse"
    if native_cad_files or (iges_files or []):
        return "hint_export_step"
    return "none"


EXPORT_HINT_ZH = (
    "检测到 CAD 工程/交换文件，但未找到中性三维 **`.step` / `.stp`**。"
    "可在 SolidWorks / Creo / Inventor / NX / Rhino 等中 **另存为 / 导出 STEP** 后放入案件目录；"
    "届时我会再问是否开启解析（请回 **是** / **否**）。本技能默认不解析原生 CAD，也不自动安装重依赖。"
)

STEP_CONFIRM_ZH = (
    "扫描发现 **`.step` / `.stp`**。交底已落盘。是否开启 STEP 多视角解析？"
    "（默认关；选「是」将延迟安装 CadQuery 等依赖并生成多视角图。）请回复 **是** 或 **否**。"
)
