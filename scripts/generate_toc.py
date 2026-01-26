#!/usr/bin/env python3
"""
目录生成脚本
为 wiki 生成导航目录
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import re


def extract_title_from_markdown(file_path: str) -> str:
    """从 Markdown 文件中提取标题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('# '):
                    return line[2:].strip()
        # 如果没有找到标题，使用文件名
        return Path(file_path).stem.replace('-', ' ').replace('_', ' ').title()
    except Exception:
        return Path(file_path).stem


def generate_toc(wiki_dir: str, base_url: str = '') -> str:
    """生成目录结构的 Markdown"""
    wiki_path = Path(wiki_dir)
    
    if not wiki_path.exists():
        return "目录为空"
    
    toc_lines = ['# 目录\n']
    
    # 主要文档
    main_docs = [
        ('index.md', '首页'),
        ('getting-started.md', '快速开始'),
        ('architecture.md', '架构概览'),
        ('configuration.md', '配置说明'),
        ('changelog.md', '更新日志'),
    ]
    
    for filename, default_title in main_docs:
        file_path = wiki_path / filename
        if file_path.exists():
            title = extract_title_from_markdown(str(file_path)) or default_title
            toc_lines.append(f'- [{title}]({base_url}{filename})')
    
    toc_lines.append('')
    
    # 模块文档
    modules_dir = wiki_path / 'modules'
    if modules_dir.exists():
        toc_lines.append('## 模块文档\n')
        for md_file in sorted(modules_dir.glob('*.md')):
            if md_file.name != 'index.md':
                title = extract_title_from_markdown(str(md_file))
                toc_lines.append(f'- [{title}]({base_url}modules/{md_file.name})')
        toc_lines.append('')
    
    # API 文档
    api_dir = wiki_path / 'api'
    if api_dir.exists():
        toc_lines.append('## API 参考\n')
        for md_file in sorted(api_dir.glob('*.md')):
            if md_file.name != 'index.md':
                title = extract_title_from_markdown(str(md_file))
                toc_lines.append(f'- [{title}]({base_url}api/{md_file.name})')
        toc_lines.append('')
    
    # 指南文档
    guides_dir = wiki_path / 'guides'
    if guides_dir.exists():
        toc_lines.append('## 使用指南\n')
        for md_file in sorted(guides_dir.glob('*.md')):
            title = extract_title_from_markdown(str(md_file))
            toc_lines.append(f'- [{title}]({base_url}guides/{md_file.name})')
        toc_lines.append('')
    
    # 设计文档
    design_dir = wiki_path / 'design'
    if design_dir.exists():
        toc_lines.append('## 设计文档\n')
        for md_file in sorted(design_dir.glob('*.md')):
            title = extract_title_from_markdown(str(md_file))
            toc_lines.append(f'- [{title}]({base_url}design/{md_file.name})')
    
    return '\n'.join(toc_lines)


def generate_sidebar(wiki_dir: str) -> str:
    """生成侧边栏导航 (适用于 GitHub Wiki 或 VuePress)"""
    wiki_path = Path(wiki_dir)
    
    sidebar = {
        '/': [
            {'text': '首页', 'link': '/'},
            {'text': '快速开始', 'link': '/getting-started'},
            {'text': '架构概览', 'link': '/architecture'},
        ]
    }
    
    # 添加模块
    modules_dir = wiki_path / 'modules'
    if modules_dir.exists():
        module_items = []
        for md_file in sorted(modules_dir.glob('*.md')):
            if md_file.name != 'index.md':
                title = extract_title_from_markdown(str(md_file))
                module_items.append({
                    'text': title,
                    'link': f'/modules/{md_file.stem}'
                })
        if module_items:
            sidebar['/modules/'] = module_items
    
    # 生成 JSON 格式
    import json
    return json.dumps(sidebar, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python generate_toc.py <wiki目录路径>")
        sys.exit(1)
    
    wiki_dir = sys.argv[1]
    print(generate_toc(wiki_dir))
