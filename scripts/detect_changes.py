#!/usr/bin/env python3
"""
变更检测脚本
对比文件校验和，检测项目变更以支持增量更新
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from datetime import datetime, timezone

# 默认排除规则
DEFAULT_EXCLUDES = {
    'node_modules', '.git', 'dist', 'build', '__pycache__',
    '.next', '.nuxt', 'coverage', '.nyc_output', 'vendor',
    'venv', '.venv', 'env', '.mini-wiki'
}

# 支持的代码文件扩展名
CODE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.py', '.pyi',
    '.go', '.rs', '.java', '.kt', '.scala',
    '.rb', '.php', '.cs', '.fs',
    '.vue', '.svelte', '.astro'
}

# 文档扩展名
DOC_EXTENSIONS = {'.md', '.mdx', '.rst', '.txt'}


def calculate_file_hash(file_path: str) -> str:
    """计算文件的 SHA256 哈希值"""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]  # 只取前16位
    except Exception:
        return ""


def should_include_file(file_path: Path, excludes: Set[str]) -> bool:
    """判断文件是否应该被包含"""
    # 检查是否在排除目录中
    for part in file_path.parts:
        if part in excludes:
            return False
        # 检查 glob 模式
        for pattern in excludes:
            if pattern.startswith('*') and file_path.name.endswith(pattern[1:]):
                return False
    
    # 只包含代码和文档文件
    return file_path.suffix in CODE_EXTENSIONS or file_path.suffix in DOC_EXTENSIONS


def scan_project_files(project_root: str, excludes: Set[str] = None) -> Dict[str, str]:
    """
    扫描项目文件并计算校验和
    
    Returns:
        {相对路径: 校验和}
    """
    if excludes is None:
        excludes = DEFAULT_EXCLUDES
    
    root = Path(project_root)
    checksums = {}
    
    for file_path in root.rglob('*'):
        if file_path.is_file() and should_include_file(file_path, excludes):
            rel_path = str(file_path.relative_to(root))
            checksums[rel_path] = calculate_file_hash(str(file_path))
    
    return checksums


def load_cached_checksums(wiki_dir: str) -> Dict[str, Dict[str, str]]:
    """加载缓存的校验和"""
    cache_path = Path(wiki_dir) / "cache" / "checksums.json"
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_checksums(wiki_dir: str, checksums: Dict[str, Dict[str, str]]):
    """保存校验和到缓存"""
    cache_path = Path(wiki_dir) / "cache" / "checksums.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(checksums, f, indent=2, ensure_ascii=False)


def detect_changes(project_root: str, excludes: Set[str] = None) -> Dict[str, Any]:
    """
    检测项目变更
    
    Returns:
        {
            "added": [新增的文件列表],
            "modified": [修改的文件列表],
            "deleted": [删除的文件列表],
            "unchanged": [未变更的文件列表],
            "has_changes": bool,
            "summary": 变更摘要字符串
        }
    """
    root = Path(project_root)
    wiki_dir = root / ".mini-wiki"
    
    # 获取当前文件校验和
    current_checksums = scan_project_files(project_root, excludes)
    
    # 加载缓存的校验和
    cached = load_cached_checksums(str(wiki_dir))
    cached_checksums = {k: v.get('hash', '') for k, v in cached.items()}
    
    current_files = set(current_checksums.keys())
    cached_files = set(cached_checksums.keys())
    
    # 分类变更
    added = list(current_files - cached_files)
    deleted = list(cached_files - current_files)
    
    modified = []
    unchanged = []
    
    for file_path in current_files & cached_files:
        if current_checksums[file_path] != cached_checksums[file_path]:
            modified.append(file_path)
        else:
            unchanged.append(file_path)
    
    has_changes = bool(added or modified or deleted)
    
    summary_parts = []
    if added:
        summary_parts.append(f"+{len(added)} 新增")
    if modified:
        summary_parts.append(f"~{len(modified)} 修改")
    if deleted:
        summary_parts.append(f"-{len(deleted)} 删除")
    if not summary_parts:
        summary_parts.append("无变更")
    
    return {
        "added": sorted(added),
        "modified": sorted(modified),
        "deleted": sorted(deleted),
        "unchanged": sorted(unchanged),
        "has_changes": has_changes,
        "summary": ", ".join(summary_parts),
        "current_checksums": current_checksums
    }


def update_checksums_cache(project_root: str, current_checksums: Dict[str, str], 
                           doc_mapping: Dict[str, str] = None):
    """
    更新校验和缓存
    
    Args:
        project_root: 项目根目录
        current_checksums: 当前文件校验和
        doc_mapping: 文件到文档的映射 {源文件: 生成的文档路径}
    """
    wiki_dir = Path(project_root) / ".mini-wiki"
    
    if doc_mapping is None:
        doc_mapping = {}
    
    cache_data = {}
    for file_path, file_hash in current_checksums.items():
        cache_data[file_path] = {
            "hash": file_hash,
            "doc": doc_mapping.get(file_path, ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    save_checksums(str(wiki_dir), cache_data)


def print_changes(changes: Dict[str, Any]):
    """打印变更信息"""
    print(f"变更检测结果: {changes['summary']}")
    print()
    
    if changes["added"]:
        print("📁 新增文件:")
        for f in changes["added"][:10]:
            print(f"  + {f}")
        if len(changes["added"]) > 10:
            print(f"  ... 还有 {len(changes['added']) - 10} 个文件")
    
    if changes["modified"]:
        print("\n📝 修改的文件:")
        for f in changes["modified"][:10]:
            print(f"  ~ {f}")
        if len(changes["modified"]) > 10:
            print(f"  ... 还有 {len(changes['modified']) - 10} 个文件")
    
    if changes["deleted"]:
        print("\n🗑️ 删除的文件:")
        for f in changes["deleted"][:10]:
            print(f"  - {f}")
        if len(changes["deleted"]) > 10:
            print(f"  ... 还有 {len(changes['deleted']) - 10} 个文件")


if __name__ == '__main__':
    import sys
    
    project_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    changes = detect_changes(project_path)
    print_changes(changes)
