#!/usr/bin/env python3
"""
文档提取脚本
从代码文件中提取 JSDoc/TSDoc/DocString 注释
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class DocEntry:
    """文档条目"""
    name: str
    type: str  # 'function', 'class', 'method', 'type', 'interface'
    description: str
    params: List[Dict[str, str]]
    returns: Optional[str]
    examples: List[str]
    line_number: int
    file_path: str


def extract_jsdoc(content: str, file_path: str) -> List[DocEntry]:
    """从 JavaScript/TypeScript 文件中提取 JSDoc 注释"""
    entries = []
    
    # JSDoc 注释模式
    jsdoc_pattern = r'/\*\*\s*([\s\S]*?)\*/\s*(?:export\s+)?(?:async\s+)?(?:function|class|const|let|var|interface|type)\s+(\w+)'
    
    for match in re.finditer(jsdoc_pattern, content):
        doc_text = match.group(1)
        name = match.group(2)
        line_number = content[:match.start()].count('\n') + 1
        
        # 解析描述
        description_lines = []
        params = []
        returns = None
        examples = []
        
        for line in doc_text.split('\n'):
            line = line.strip().lstrip('* ')
            
            if line.startswith('@param'):
                param_match = re.match(r'@param\s+{([^}]+)}\s+(\w+)\s*-?\s*(.*)', line)
                if param_match:
                    params.append({
                        'type': param_match.group(1),
                        'name': param_match.group(2),
                        'description': param_match.group(3)
                    })
            elif line.startswith('@returns') or line.startswith('@return'):
                return_match = re.match(r'@returns?\s+{([^}]+)}\s*(.*)', line)
                if return_match:
                    returns = f"{return_match.group(1)}: {return_match.group(2)}"
            elif line.startswith('@example'):
                # 收集示例代码直到下一个 @ 标签
                continue
            elif not line.startswith('@'):
                description_lines.append(line)
        
        description = ' '.join(description_lines).strip()
        
        # 确定类型
        if 'class' in match.group(0).lower():
            entry_type = 'class'
        elif 'interface' in match.group(0).lower():
            entry_type = 'interface'
        elif 'type' in match.group(0):
            entry_type = 'type'
        else:
            entry_type = 'function'
        
        entries.append(DocEntry(
            name=name,
            type=entry_type,
            description=description,
            params=params,
            returns=returns,
            examples=examples,
            line_number=line_number,
            file_path=file_path
        ))
    
    return entries


def extract_python_docstring(content: str, file_path: str) -> List[DocEntry]:
    """从 Python 文件中提取 DocString"""
    entries = []
    
    # 函数/类定义模式
    def_pattern = r'(?:^|\n)((?:async\s+)?def|class)\s+(\w+)[^:]*:\s*(?:\n\s+)?(?:"""([\s\S]*?)"""|\'\'\'([\s\S]*?)\'\'\')'
    
    for match in re.finditer(def_pattern, content):
        def_type = 'function' if 'def' in match.group(1) else 'class'
        name = match.group(2)
        docstring = match.group(3) or match.group(4) or ''
        line_number = content[:match.start()].count('\n') + 1
        
        # 解析 Google/NumPy 风格 docstring
        description_lines = []
        params = []
        returns = None
        examples = []
        
        current_section = 'description'
        
        for line in docstring.split('\n'):
            stripped = line.strip()
            
            if stripped in ('Args:', 'Arguments:', 'Parameters:'):
                current_section = 'params'
                continue
            elif stripped in ('Returns:', 'Return:'):
                current_section = 'returns'
                continue
            elif stripped in ('Example:', 'Examples:'):
                current_section = 'examples'
                continue
            elif stripped.endswith(':') and not ':' in stripped[:-1]:
                current_section = 'other'
                continue
            
            if current_section == 'description':
                description_lines.append(stripped)
            elif current_section == 'params':
                param_match = re.match(r'(\w+)\s*(?:\(([^)]+)\))?\s*:\s*(.*)', stripped)
                if param_match:
                    params.append({
                        'name': param_match.group(1),
                        'type': param_match.group(2) or 'Any',
                        'description': param_match.group(3)
                    })
            elif current_section == 'returns':
                returns = stripped
            elif current_section == 'examples':
                examples.append(stripped)
        
        description = ' '.join(description_lines).strip()
        
        entries.append(DocEntry(
            name=name,
            type=def_type,
            description=description,
            params=params,
            returns=returns,
            examples=examples,
            line_number=line_number,
            file_path=file_path
        ))
    
    return entries


def extract_docs_from_file(file_path: str) -> List[DocEntry]:
    """从文件中提取文档"""
    path = Path(file_path)
    
    if not path.exists():
        return []
    
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    suffix = path.suffix.lower()
    
    if suffix in {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}:
        return extract_jsdoc(content, file_path)
    elif suffix in {'.py', '.pyi'}:
        return extract_python_docstring(content, file_path)
    
    return []


def docs_to_markdown(entries: List[DocEntry]) -> str:
    """将文档条目转换为 Markdown"""
    lines = []
    
    # 按类型分组
    functions = [e for e in entries if e.type == 'function']
    classes = [e for e in entries if e.type == 'class']
    types = [e for e in entries if e.type in {'type', 'interface'}]
    
    if functions:
        lines.append('## 函数\n')
        for func in functions:
            lines.append(f'### `{func.name}`\n')
            lines.append(f'{func.description}\n')
            
            if func.params:
                lines.append('**参数:**\n')
                for param in func.params:
                    lines.append(f"- `{param['name']}` ({param['type']}): {param['description']}")
                lines.append('')
            
            if func.returns:
                lines.append(f'**返回值:** {func.returns}\n')
    
    if classes:
        lines.append('## 类\n')
        for cls in classes:
            lines.append(f'### `{cls.name}`\n')
            lines.append(f'{cls.description}\n')
    
    if types:
        lines.append('## 类型定义\n')
        for t in types:
            lines.append(f'### `{t.name}`\n')
            lines.append(f'{t.description}\n')
    
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python extract_docs.py <文件路径>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    entries = extract_docs_from_file(file_path)
    
    print(docs_to_markdown(entries))
