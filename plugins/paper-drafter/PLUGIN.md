---
name: paper-drafter
type: generator
version: 1.0.0
description: |
  Expert-level academic paper generator producing IMRaD structured drafts in LaTeX/Markdown.
  专家级学术论文生成器，生成基于 IMRaD 结构的 LaTeX/Markdown 草稿。
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - after_generate
---

# Academic Paper Drafter / 学术论文起草助手

> **Top-Tier Academic Standard**: Transforms project artifacts into potential conference/journal paper drafts (CS/Engineering focus).

## 核心方法论 (Core Methodology)

1.  **IMRaD Structure**: 严格遵循 Introduction, Methods, Results, and Discussion 标准结构。
2.  **Novelty Synthesis**: 结合代码创新点与现有技术背景，合成"学术贡献点" (Academic Contributions)。
3.  **Formal Tone**: 强制使用客观、第三人称、被动语态为主的学术英语/中文。

## 功能特性 / Features

### 1. 自动化 IMRaD 构建

- **Introduction**: 
  - *Problem Statement*: 这里的"痛点"转化为"Research Gap"。
  - *Contribution*: 总结项目的核心技术方案。
- **Methodology**:
  - *System Architecture*: 将 Mermaid 架构图转化为形式化的系统描述。
  - *Algorithm Formalization*: 将核心算法转化为伪代码 (Algorithm environment) 或数学公式。
- **Experiments (Proposed)**:
  - 基于单元测试和性能测试数据，自动设计实验章节。
  - 如果没有数据，自动生成"实验设计方案" (Experimental Setup)。

### 2. LaTeX 深度集成

直接生成可编译的 `.tex` 文件结构：
- 使用 `IEEEtran` 或 `ACM` 模板格式。
- 自动生成 `BibTeX` 引用占位符。
- 自动将 Mermaid 转换为 `figure` 环境占位描述。

### 3. 学术语言优化

- **Vocabulary**: 使用 "leverage", "propose", "demonstrate", "outperform" 等学术高频词。
- **Style**: 避免口语化，确保逻辑连贯性 (Coherence & Cohesion)。

## Hooks

### after_analyze (Contribution Extraction)

1.  **Metric Analysis**: 提取代码中的性能指标（时间复杂度、覆盖率）作为"Results"的素材。
2.  **Architecture Modeling**: 识别系统拓扑结构，为"Methodology"提供素材。

### after_generate (Paper Drafting)

1.  **Drafting**:
    - 读取 `wiki/architecture.md` (System Design)
    - 读取 `wiki/modules/` (Detailed Implementation)
    - 读取 `patent/` (如果有，提取 Novelty)
2.  **Formatting**:
    - 输出 `paper/draft.tex` (LaTeX Source)
    - 输出 `paper/draft.md` (Markdown Preview)
    - 输出 `paper/references.bib` (Suggested References)

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  paper-drafter:
    # 目标会议/期刊风格
    template: IEEE  # IEEE | ACM | Nature_Style | Generic
    
    # 语言
    language: en  # en (推荐) | zh
    
    # 侧重点
    focus: system  # system (架构) | algorithm (算法) | application (应用)
    
    # 是否包含伪代码
    include_pseudocode: true
```

## 输出示例 / Output Example

### LaTeX Draft (`paper/draft.tex`)

```latex
\documentclass[conference]{IEEEtran}
\title{Mini-Wiki: An Automated Agentic Documentation Framework}

\begin{abstract}
Documentation maintenance remains a critical bottleneck in software evolution...
\end{abstract}

\section{Introduction}
Systematic documentation is essential... However, existing tools lack...
In this paper, we propose Mini-Wiki, an agent-driven framework...

\section{Methodology}
\subsection{Plugin Architecture}
The system employs a hook-based lifecycle management...
\begin{algorithm}
\caption{Plugin Instruction Protocol}
...
\end{algorithm}
```

## 手动命令（仅供人工参考）

出于安全模型（指令型插件，不执行代码），此处不包含命令示例。如需 CLI 用法，请参考项目 README。
