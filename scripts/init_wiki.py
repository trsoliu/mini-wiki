#!/usr/bin/env python3
"""
Mini-Wiki 初始化脚本
创建 .mini-wiki 目录结构和默认配置
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mini_wiki_core import __version__
from mini_wiki_core.config import default_config_yaml


def get_default_config() -> str:
    """返回默认配置文件内容"""
    return default_config_yaml()


def get_default_meta() -> dict[str, Any]:
    """返回默认元数据"""
    return {
        "version": __version__,
        "schema_version": 3,
        "generator_version": __version__,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "files_documented": 0,
        "modules_count": 0,
    }


def init_mini_wiki(project_root: str, force: bool = False) -> dict[str, Any]:
    """
    初始化 .mini-wiki 目录

    Args:
        project_root: 项目根目录
        force: 是否强制重新初始化

    Returns:
        初始化结果
    """
    root = Path(project_root)
    state_dir = root / ".mini-wiki"

    result: dict[str, Any] = {"success": True, "created": [], "skipped": [], "message": ""}

    # 检查是否已存在
    if state_dir.exists():
        if not force:
            result["success"] = False
            result["message"] = ".mini-wiki 目录已存在。使用 force=True 重新初始化。"
            return result
        else:
            # 备份现有配置
            config_path = state_dir / "config.yaml"
            if config_path.exists():
                backup_path = state_dir / "config.yaml.bak"
                shutil.copy(config_path, backup_path)
                result["skipped"].append("config.yaml (已备份)")

    # 创建目录结构
    directories = [
        ".mini-wiki",
        ".mini-wiki/cache",
        ".mini-wiki/staging",
        ".mini-wiki/archive",
        "wiki",
        "wiki/domains",
        "wiki/reference",
        "wiki/reference/api",
        "wiki/reference/source",
        "wiki/views",
        "wiki/canvas",
        "wiki/assets",
    ]

    for dir_path in directories:
        full_path = root / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            result["created"].append(dir_path)

    # 创建配置文件
    config_path = state_dir / "config.yaml"
    if not config_path.exists() or force:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(get_default_config())
        result["created"].append("config.yaml")

    # 创建元数据文件
    meta_path = state_dir / "meta.json"
    if not meta_path.exists() or force:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(get_default_meta(), f, indent=2, ensure_ascii=False)
        result["created"].append("meta.json")

    # 创建空的缓存文件
    cache_files: dict[str, dict[str, Any]] = {
        "cache/checksums.json": {},
        "cache/structure.json": {"project_type": [], "entry_points": [], "modules": [], "docs_found": []},
        "cache/analysis.json": {},
        "cache/graph.json": {"nodes": {}, "edges": []},
        "cache/build-plan.json": {"documents": []},
    }

    for cache_file, default_content in cache_files.items():
        cache_path = state_dir / cache_file
        if not cache_path.exists():
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(default_content, f, indent=2, ensure_ascii=False)
            result["created"].append(cache_file)

    # 创建 .gitignore
    manifest_path = state_dir / "manifest.json"
    if not manifest_path.exists() or force:
        manifest = {
            "schema_version": 3,
            "generator_version": __version__,
            "sources": {},
            "documents": {},
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result["created"].append("manifest.json")

    gitignore_path = state_dir / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("cache/\nstaging/\narchive/\n*.bak\n")
        result["created"].append(".gitignore")

    result["message"] = f"成功初始化 .mini-wiki 目录，创建了 {len(result['created'])} 个文件/目录"
    return result


def print_result(result: dict[str, Any]):
    """打印初始化结果"""
    if result["success"]:
        print("✅", result["message"])
        if result["created"]:
            print("\n创建的文件/目录:")
            for item in result["created"]:
                print(f"  + {item}")
        if result["skipped"]:
            print("\n跳过的文件:")
            for item in result["skipped"]:
                print(f"  - {item}")
    else:
        print("❌", result["message"])


if __name__ == "__main__":
    import sys

    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    force = "--force" in sys.argv

    result = init_mini_wiki(project_path, force)
    print_result(result)
