#!/usr/bin/env python3
"""
Mermaid 图表生成脚本
根据项目结构生成架构图、依赖图、模块关系图
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import re


def generate_architecture_diagram(structure: Dict[str, Any]) -> str:
    """
    生成项目架构图
    
    Args:
        structure: 项目结构数据 (来自 structure.json)
    
    Returns:
        Mermaid 图表代码
    """
    modules = structure.get('modules', [])
    project_type = structure.get('project_type', [])
    
    lines = ['```mermaid', 'flowchart TB']
    
    # 添加子图
    if 'nodejs' in project_type or 'typescript' in project_type:
        lines.append('    subgraph Frontend["前端层"]')
        frontend_modules = [m for m in modules if any(p in m.get('path', '') 
                          for p in ['components', 'pages', 'views', 'ui'])]
        for m in frontend_modules[:5]:
            safe_name = re.sub(r'[^a-zA-Z0-9]', '', m['name'])
            lines.append(f'        {safe_name}["{m["name"]}"]')
        if not frontend_modules:
            lines.append('        UI["用户界面"]')
        lines.append('    end')
        lines.append('')
    
    lines.append('    subgraph Core["核心层"]')
    core_modules = [m for m in modules if any(p in m.get('path', '') 
                   for p in ['core', 'lib', 'services', 'api', 'src']) 
                   and not any(p in m.get('path', '') 
                   for p in ['components', 'pages', 'views', 'ui', 'utils'])]
    for m in core_modules[:5]:
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', m['name'])
        lines.append(f'        {safe_name}["{m["name"]}"]')
    if not core_modules:
        lines.append('        Logic["业务逻辑"]')
    lines.append('    end')
    lines.append('')
    
    lines.append('    subgraph Utils["工具层"]')
    util_modules = [m for m in modules if any(p in m.get('path', '') 
                   for p in ['utils', 'helpers', 'common', 'shared'])]
    for m in util_modules[:3]:
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', m['name'])
        lines.append(f'        {safe_name}["{m["name"]}"]')
    if not util_modules:
        lines.append('        Utilities["工具函数"]')
    lines.append('    end')
    lines.append('')
    
    # 添加连接
    lines.append('    Frontend --> Core')
    lines.append('    Core --> Utils')
    
    lines.append('```')
    return '\n'.join(lines)


def generate_module_dependency_diagram(module_name: str, dependencies: Dict[str, List[str]]) -> str:
    """
    生成模块依赖关系图
    
    Args:
        module_name: 模块名称
        dependencies: 依赖关系 {"internal": [...], "external": [...]}
    
    Returns:
        Mermaid 图表代码
    """
    lines = ['```mermaid', 'graph LR']
    
    safe_name = re.sub(r'[^a-zA-Z0-9]', '', module_name)
    lines.append(f'    {safe_name}["{module_name}"]')
    
    # 内部依赖
    internal = dependencies.get('internal', [])
    for i, dep in enumerate(internal[:8]):
        dep_name = Path(dep).stem
        safe_dep = re.sub(r'[^a-zA-Z0-9]', '', dep_name) + str(i)
        lines.append(f'    {safe_name} --> {safe_dep}["{dep_name}"]')
    
    # 外部依赖
    external = dependencies.get('external', [])
    if external:
        lines.append(f'    {safe_name} --> ext["外部依赖"]')
        for i, dep in enumerate(external[:5]):
            safe_dep = re.sub(r'[^a-zA-Z0-9]', '', dep) + 'ext' + str(i)
            lines.append(f'    ext --> {safe_dep}["{dep}"]')
    
    lines.append('```')
    return '\n'.join(lines)


def generate_file_tree_diagram(structure: Dict[str, Any], max_depth: int = 3) -> str:
    """
    生成目录结构图
    
    Args:
        structure: 项目结构数据
        max_depth: 最大深度
    
    Returns:
        Mermaid 图表代码 (使用 mindmap)
    """
    modules = structure.get('modules', [])
    
    lines = ['```mermaid', 'mindmap', '  root((项目))']
    
    for module in modules[:10]:
        name = module.get('name', 'unnamed')
        path = module.get('path', '')
        files_count = module.get('files', 0)
        lines.append(f'    {name}')
        lines.append(f'      {files_count} 个文件')
    
    lines.append('```')
    return '\n'.join(lines)


def generate_data_flow_diagram(entry_points: List[str], modules: List[Dict]) -> str:
    """
    生成数据流序列图
    
    Args:
        entry_points: 入口文件列表
        modules: 模块列表
    
    Returns:
        Mermaid 序列图代码
    """
    lines = ['```mermaid', 'sequenceDiagram']
    
    lines.append('    participant U as 用户')
    lines.append('    participant E as 入口')
    
    if modules:
        for i, module in enumerate(modules[:3]):
            name = module.get('name', f'Module{i}')
            safe_name = re.sub(r'[^a-zA-Z0-9]', '', name)
            lines.append(f'    participant {safe_name} as {name}')
    
    lines.append('')
    lines.append('    U->>E: 请求')
    
    if modules:
        prev = 'E'
        for i, module in enumerate(modules[:3]):
            name = module.get('name', f'Module{i}')
            safe_name = re.sub(r'[^a-zA-Z0-9]', '', name)
            lines.append(f'    {prev}->>{safe_name}: 调用')
            prev = safe_name
        lines.append(f'    {prev}-->>U: 响应')
    else:
        lines.append('    E-->>U: 响应')
    
    lines.append('```')
    return '\n'.join(lines)


def generate_class_diagram(classes: List[Dict[str, Any]]) -> str:
    """
    生成类图
    
    Args:
        classes: 类信息列表 [{"name": "ClassName", "methods": [...], "properties": [...]}]
    
    Returns:
        Mermaid 类图代码
    """
    lines = ['```mermaid', 'classDiagram']
    
    for cls in classes[:10]:
        name = cls.get('name', 'Unknown')
        safe_name = re.sub(r'[^a-zA-Z0-9]', '', name)
        lines.append(f'    class {safe_name} {{')
        
        for prop in cls.get('properties', [])[:5]:
            lines.append(f'        +{prop}')
        
        for method in cls.get('methods', [])[:5]:
            lines.append(f'        +{method}()')
        
        lines.append('    }')
    
    lines.append('```')
    return '\n'.join(lines)


def load_structure(wiki_dir: str) -> Optional[Dict[str, Any]]:
    """加载项目结构数据"""
    structure_path = Path(wiki_dir) / "cache" / "structure.json"
    if structure_path.exists():
        with open(structure_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python generate_diagram.py <.mini-wiki目录>")
        sys.exit(1)
    
    wiki_dir = sys.argv[1]
    structure = load_structure(wiki_dir)
    
    if structure:
        print("=== 架构图 ===")
        print(generate_architecture_diagram(structure))
        print()
        print("=== 目录结构图 ===")
        print(generate_file_tree_diagram(structure))
    else:
        print("未找到项目结构数据")
