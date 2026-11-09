"""Obsidian 模板与 CSS 资源路径。"""
from __future__ import annotations

from pathlib import Path

try:
    from shared.common import ROOT
except ImportError:
    from tools.patent_reader.shared.common import ROOT

ASSETS_OBSIDIAN = ROOT / "assets" / "obsidian"


def repo_obsidian_base_src(stem: str) -> Path | None:
    """技能市场上架禁止提交 *.base；仓库源稿为 *.base.yaml，拷库时再写成 .base。"""
    for name in (f"{stem}.base.yaml", f"{stem}.base"):
        path = ASSETS_OBSIDIAN / name
        if path.is_file():
            return path
    return None
