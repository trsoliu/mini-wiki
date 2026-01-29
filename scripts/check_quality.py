#!/usr/bin/env python3
"""
Mini-Wiki 文档质量检查脚本
检查生成的文档是否符合 v3.0.2 质量标准
"""

import os
import re
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class QualityMetrics:
    """单个文档的质量指标"""
    file_path: str
    line_count: int = 0
    section_count: int = 0  # H2 章节数
    subsection_count: int = 0  # H3 章节数
    diagram_count: int = 0  # Mermaid 图表数
    class_diagram_count: int = 0  # classDiagram 数量
    code_example_count: int = 0  # 代码示例数
    table_count: int = 0  # 表格数
    cross_link_count: int = 0  # 交叉链接数
    has_source_tracing: bool = False  # 是否有源码追溯
    has_best_practices: bool = False  # 是否有最佳实践章节
    has_performance: bool = False  # 是否有性能优化章节
    has_troubleshooting: bool = False  # 是否有错误处理/调试章节
    quality_level: str = "basic"  # basic / standard / professional
    issues: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """质量检查报告"""
    wiki_path: str
    check_time: str
    total_docs: int = 0
    professional_count: int = 0
    standard_count: int = 0
    basic_count: int = 0
    docs: List[QualityMetrics] = field(default_factory=list)
    summary_issues: List[str] = field(default_factory=list)


def analyze_document(file_path: str) -> QualityMetrics:
    """分析单个文档的质量"""
    metrics = QualityMetrics(file_path=file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        metrics.issues.append(f"无法读取文件: {e}")
        return metrics
    
    metrics.line_count = len(lines)
    
    # 统计 H2 章节 (##)
    metrics.section_count = len(re.findall(r'^## ', content, re.MULTILINE))
    
    # 统计 H3 章节 (###)
    metrics.subsection_count = len(re.findall(r'^### ', content, re.MULTILINE))
    
    # 统计 Mermaid 图表
    mermaid_blocks = re.findall(r'```mermaid[\s\S]*?```', content)
    metrics.diagram_count = len(mermaid_blocks)
    
    # 统计 classDiagram
    metrics.class_diagram_count = len(re.findall(r'classDiagram', content))
    
    # 统计代码示例 (排除 mermaid)
    all_code_blocks = re.findall(r'```(?!mermaid)[\s\S]*?```', content)
    metrics.code_example_count = len(all_code_blocks)
    
    # 统计表格
    metrics.table_count = len(re.findall(r'^\|.*\|$', content, re.MULTILINE)) // 2  # 估算
    
    # 统计交叉链接 (排除外部链接)
    internal_links = re.findall(r'\[.*?\]\((?!http).*?\.md.*?\)', content)
    metrics.cross_link_count = len(internal_links)
    
    # 检查源码追溯
    metrics.has_source_tracing = bool(
        re.search(r'\*\*Section sources\*\*|\*\*Diagram sources\*\*|file://', content)
    )
    
    # 检查关键章节
    content_lower = content.lower()
    metrics.has_best_practices = bool(
        re.search(r'最佳实践|best practice', content_lower)
    )
    metrics.has_performance = bool(
        re.search(r'性能优化|性能考量|performance', content_lower)
    )
    metrics.has_troubleshooting = bool(
        re.search(r'错误处理|调试|故障排除|troubleshoot|debug', content_lower)
    )
    
    # 评估质量等级
    metrics.quality_level = evaluate_quality_level(metrics)
    
    # 生成问题列表
    metrics.issues = generate_issues(metrics)
    
    return metrics


def evaluate_quality_level(m: QualityMetrics) -> str:
    """评估质量等级"""
    score = 0
    
    # 行数评分 (400+ 为专业级)
    if m.line_count >= 400:
        score += 3
    elif m.line_count >= 250:
        score += 2
    elif m.line_count >= 150:
        score += 1
    
    # 章节数评分
    if m.section_count >= 12:
        score += 3
    elif m.section_count >= 8:
        score += 2
    elif m.section_count >= 5:
        score += 1
    
    # 图表评分
    if m.diagram_count >= 3:
        score += 3
    elif m.diagram_count >= 2:
        score += 2
    elif m.diagram_count >= 1:
        score += 1
    
    # classDiagram 评分
    if m.class_diagram_count >= 1:
        score += 2
    
    # 代码示例评分
    if m.code_example_count >= 5:
        score += 3
    elif m.code_example_count >= 3:
        score += 2
    elif m.code_example_count >= 1:
        score += 1
    
    # 源码追溯评分
    if m.has_source_tracing:
        score += 2
    
    # 关键章节评分
    if m.has_best_practices:
        score += 1
    if m.has_performance:
        score += 1
    if m.has_troubleshooting:
        score += 1
    
    # 最终评级
    if score >= 15:
        return "professional"
    elif score >= 8:
        return "standard"
    else:
        return "basic"


def calculate_expected_metrics(file_path: str) -> Dict[str, int]:
    """基于模块复杂度动态计算期望指标"""
    # 默认期望值（用于无法分析源码的情况）
    expected = {
        "min_lines": 100,
        "min_sections": 6,
        "min_diagrams": 1,
        "min_examples": 2,
    }
    
    # 尝试推断模块复杂度
    file_name = os.path.basename(file_path).replace('.md', '')
    
    # 核心模块检测
    core_keywords = ['core', 'agent', 'editor', 'store', 'main', 'client']
    is_core = any(kw in file_name.lower() for kw in core_keywords)
    
    # 工具/配置模块检测
    util_keywords = ['util', 'helper', 'common', 'shared', 'constant', 'config', 'type']
    is_util = any(kw in file_name.lower() for kw in util_keywords)
    
    # 索引文件检测
    is_index = file_name in ['index', '_index', 'TOC', 'doc-map']
    
    if is_core:
        expected["min_lines"] = 200
        expected["min_sections"] = 8
        expected["min_diagrams"] = 2
        expected["min_examples"] = 3
    elif is_util:
        expected["min_lines"] = 80
        expected["min_sections"] = 5
        expected["min_diagrams"] = 1
        expected["min_examples"] = 2
    elif is_index:
        expected["min_lines"] = 50
        expected["min_sections"] = 3
        expected["min_diagrams"] = 1
        expected["min_examples"] = 0
    
    return expected


def generate_issues(m: QualityMetrics) -> List[str]:
    """生成问题列表（基于动态期望值）"""
    issues = []
    
    # 动态计算期望指标
    expected = calculate_expected_metrics(m.file_path)
    
    # 基于动态期望值检查
    if m.line_count < expected["min_lines"]:
        issues.append(f"行数不足: {m.line_count}/{expected['min_lines']} (基于模块复杂度)")
    
    if m.section_count < expected["min_sections"]:
        issues.append(f"章节数不足: {m.section_count}/{expected['min_sections']}")
    
    if m.diagram_count < expected["min_diagrams"]:
        issues.append(f"图表数不足: {m.diagram_count}/{expected['min_diagrams']}")
    
    if m.class_diagram_count < 1 and expected["min_diagrams"] >= 2:
        issues.append("核心模块缺少 classDiagram 类图")
    
    if m.code_example_count < expected["min_examples"]:
        issues.append(f"代码示例不足: {m.code_example_count}/{expected['min_examples']}")
    
    if not m.has_source_tracing and expected["min_lines"] >= 150:
        issues.append("缺少源码追溯 (Section sources)")
    
    # 核心模块需要更多章节
    if expected["min_sections"] >= 8:
        if not m.has_best_practices:
            issues.append("核心模块缺少「最佳实践」章节")
        if not m.has_performance:
            issues.append("核心模块缺少「性能优化」章节")
        if not m.has_troubleshooting:
            issues.append("核心模块缺少「错误处理」章节")
    
    if m.cross_link_count < 1:
        issues.append("缺少相关文档交叉链接")
    
    return issues


def check_wiki_quality(wiki_path: str) -> QualityReport:
    """检查整个 Wiki 目录的质量"""
    report = QualityReport(
        wiki_path=wiki_path,
        check_time=datetime.now().isoformat()
    )
    
    wiki_dir = Path(wiki_path) / "wiki"
    if not wiki_dir.exists():
        report.summary_issues.append(f"Wiki 目录不存在: {wiki_dir}")
        return report
    
    # 遍历所有 .md 文件
    for md_file in wiki_dir.rglob("*.md"):
        metrics = analyze_document(str(md_file))
        report.docs.append(metrics)
        report.total_docs += 1
        
        if metrics.quality_level == "professional":
            report.professional_count += 1
        elif metrics.quality_level == "standard":
            report.standard_count += 1
        else:
            report.basic_count += 1
    
    return report


def print_report(report: QualityReport, verbose: bool = False):
    """打印质量报告"""
    print("\n" + "=" * 60)
    print("📊 Mini-Wiki 文档质量检查报告")
    print("=" * 60)
    print(f"📁 Wiki 路径: {report.wiki_path}")
    print(f"🕐 检查时间: {report.check_time}")
    print()
    
    # 总体统计
    print("## 📈 总体统计\n")
    print(f"| 指标 | 数值 |")
    print(f"|------|------|")
    print(f"| 文档总数 | {report.total_docs} |")
    print(f"| 🟢 Professional | {report.professional_count} ({report.professional_count/max(1,report.total_docs)*100:.1f}%) |")
    print(f"| 🟡 Standard | {report.standard_count} ({report.standard_count/max(1,report.total_docs)*100:.1f}%) |")
    print(f"| 🔴 Basic | {report.basic_count} ({report.basic_count/max(1,report.total_docs)*100:.1f}%) |")
    print()
    
    # 需要改进的文档
    basic_docs = [d for d in report.docs if d.quality_level == "basic"]
    standard_docs = [d for d in report.docs if d.quality_level == "standard"]
    
    if basic_docs:
        print("## 🔴 需要升级的文档 (Basic)\n")
        print("| 文档 | 行数 | 章节 | 图表 | 问题数 |")
        print("|------|------|------|------|--------|")
        for doc in basic_docs:
            rel_path = os.path.basename(doc.file_path)
            print(f"| {rel_path} | {doc.line_count} | {doc.section_count} | {doc.diagram_count} | {len(doc.issues)} |")
        print()
    
    if standard_docs:
        print("## 🟡 可优化的文档 (Standard)\n")
        print("| 文档 | 行数 | 章节 | 图表 | 问题数 |")
        print("|------|------|------|------|--------|")
        for doc in standard_docs:
            rel_path = os.path.basename(doc.file_path)
            print(f"| {rel_path} | {doc.line_count} | {doc.section_count} | {doc.diagram_count} | {len(doc.issues)} |")
        print()
    
    # 详细问题列表
    if verbose:
        print("## 📋 详细问题列表\n")
        for doc in report.docs:
            if doc.issues:
                rel_path = os.path.relpath(doc.file_path, report.wiki_path)
                print(f"### {rel_path} [{doc.quality_level.upper()}]\n")
                for issue in doc.issues:
                    print(f"- ⚠️ {issue}")
                print()
    
    # 改进建议
    print("## 💡 改进建议\n")
    if report.basic_count > 0:
        print(f"- 运行 `升级 wiki` 命令升级 {report.basic_count} 个 Basic 级文档")
    if not any(d.has_source_tracing for d in report.docs):
        print("- 添加源码追溯 (Section sources / Diagram sources)")
    if not any(d.class_diagram_count > 0 for d in report.docs):
        print("- 为核心类添加 classDiagram 类图")
    
    print()
    print("=" * 60)
    
    # 返回退出码
    if report.basic_count > report.total_docs * 0.5:
        return 2  # 超过50%是 basic，严重
    elif report.basic_count > 0:
        return 1  # 有 basic 文档，警告
    else:
        return 0  # 全部达标


def save_report_json(report: QualityReport, output_path: str):
    """保存报告为 JSON"""
    data = {
        "wiki_path": report.wiki_path,
        "check_time": report.check_time,
        "summary": {
            "total": report.total_docs,
            "professional": report.professional_count,
            "standard": report.standard_count,
            "basic": report.basic_count
        },
        "docs": []
    }
    
    for doc in report.docs:
        data["docs"].append({
            "file": doc.file_path,
            "metrics": {
                "lines": doc.line_count,
                "sections": doc.section_count,
                "diagrams": doc.diagram_count,
                "class_diagrams": doc.class_diagram_count,
                "code_examples": doc.code_example_count,
                "tables": doc.table_count,
                "cross_links": doc.cross_link_count,
                "has_source_tracing": doc.has_source_tracing,
                "has_best_practices": doc.has_best_practices,
                "has_performance": doc.has_performance,
                "has_troubleshooting": doc.has_troubleshooting
            },
            "quality_level": doc.quality_level,
            "issues": doc.issues
        })
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"📄 报告已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Mini-Wiki 文档质量检查工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python check_quality.py /path/to/project/.mini-wiki
  python check_quality.py . --verbose
  python check_quality.py . --json report.json
        """
    )
    parser.add_argument(
        "wiki_path",
        nargs="?",
        default=".mini-wiki",
        help="Wiki 目录路径 (默认: .mini-wiki)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细问题列表"
    )
    parser.add_argument(
        "--json",
        metavar="FILE",
        help="将报告保存为 JSON 文件"
    )
    
    args = parser.parse_args()
    
    # 检查路径
    wiki_path = args.wiki_path
    if not os.path.exists(wiki_path):
        print(f"❌ 路径不存在: {wiki_path}")
        return 1
    
    # 执行检查
    report = check_wiki_quality(wiki_path)
    
    # 打印报告
    exit_code = print_report(report, verbose=args.verbose)
    
    # 保存 JSON
    if args.json:
        save_report_json(report, args.json)
    
    return exit_code


if __name__ == "__main__":
    exit(main())
