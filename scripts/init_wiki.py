#!/usr/bin/env python3
"""
Mini-Wiki 初始化脚本
创建 .mini-wiki 目录结构和默认配置
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


def get_default_config() -> str:
    """返回默认配置文件内容"""
    return '''# Mini-Wiki 配置文件

# 生成选项
generation:
  language: zh                   # zh / en / both
  include_diagrams: true         # 生成 Mermaid 架构图
  include_examples: true         # 包含代码使用示例
  link_to_source: true           # 代码块链接到源码
  max_file_size: 100000          # 跳过大于此大小的文件（字节）

# 排除规则
exclude:
  - node_modules
  - .git
  - dist
  - build
  - coverage
  - __pycache__
  - venv
  - .venv
'''


def get_default_meta() -> dict:
    """返回默认元数据"""
    return {
        "version": "2.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_updated": None,
        "files_documented": 0,
        "modules_count": 0
    }


def init_mini_wiki(project_root: str, force: bool = False) -> dict:
    """
    初始化 .mini-wiki 目录
    
    Args:
        project_root: 项目根目录
        force: 是否强制重新初始化
        
    Returns:
        初始化结果
    """
    root = Path(project_root)
    wiki_dir = root / ".mini-wiki"
    
    result = {
        "success": True,
        "created": [],
        "skipped": [],
        "message": ""
    }
    
    # 检查是否已存在
    if wiki_dir.exists():
        if not force:
            result["success"] = False
            result["message"] = ".mini-wiki 目录已存在。使用 force=True 重新初始化。"
            return result
        else:
            # 备份现有配置
            config_path = wiki_dir / "config.yaml"
            if config_path.exists():
                backup_path = wiki_dir / "config.yaml.bak"
                shutil.copy(config_path, backup_path)
                result["skipped"].append("config.yaml (已备份)")
    
    # 创建目录结构
    directories = [
        ".mini-wiki",
        ".mini-wiki/cache",
        ".mini-wiki/wiki",
        ".mini-wiki/wiki/modules",
        ".mini-wiki/wiki/api",
        ".mini-wiki/wiki/assets",
        ".mini-wiki/i18n",
        ".mini-wiki/i18n/en",
        ".mini-wiki/i18n/zh",
    ]
    
    for dir_path in directories:
        full_path = root / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            result["created"].append(dir_path)
    
    # 创建配置文件
    config_path = wiki_dir / "config.yaml"
    if not config_path.exists() or force:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(get_default_config())
        result["created"].append("config.yaml")
    
    # 创建元数据文件
    meta_path = wiki_dir / "meta.json"
    if not meta_path.exists() or force:
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(get_default_meta(), f, indent=2, ensure_ascii=False)
        result["created"].append("meta.json")
    
    # 创建空的缓存文件
    cache_files = {
        "cache/checksums.json": {},
        "cache/structure.json": {
            "project_type": [],
            "entry_points": [],
            "modules": [],
            "docs_found": []
        }
    }
    
    for cache_file, default_content in cache_files.items():
        cache_path = wiki_dir / cache_file
        if not cache_path.exists():
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, indent=2, ensure_ascii=False)
            result["created"].append(cache_file)
    
    # 创建 .gitignore
    gitignore_path = wiki_dir / ".gitignore"
    if not gitignore_path.exists():
        with open(gitignore_path, 'w', encoding='utf-8') as f:
            f.write("cache/\n*.bak\n")
        result["created"].append(".gitignore")
    
    result["message"] = f"成功初始化 .mini-wiki 目录，创建了 {len(result['created'])} 个文件/目录"
    return result


def print_result(result: dict):
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


if __name__ == '__main__':
    import sys
    
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    force = '--force' in sys.argv
    
    result = init_mini_wiki(project_path, force)
    print_result(result)
