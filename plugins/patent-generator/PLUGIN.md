---
name: patent-generator
type: generator
version: 2.0.0
description: |
  Expert-level patent drafting system using TRIZ methodology and standard claim hierarchies.
  基于 TRIZ 方法论和标准权利要求层级架构的专家级专利生成系统。
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - after_generate
---

# Expert Patent Generator / 专家级专利生成器

> **Enterprise Edition Level**: Transforms code into defensible intellectual property using legal best practices and systematic innovation theories.

## 核心设计哲学 / Core Philosophy

1.  **Systematic Innovation (TRIZ)**: 使用 TRIZ（发明问题解决理论）识别代码中的技术矛盾与创新原理。
2.  **Defensible Hierarchies**: 构建严密的"独立权利要求 -> 从属权利要求"保护层级。
3.  **Embodiment Expansion**: 自动推演替代实施例（Alternative Embodiments）以扩大保护范围。

## 功能特性 / Features

### 1. 深度创新挖掘 (Inventive Step Mining)

不仅仅是描述代码，而是使用 **TRIZ 40个发明原理** 分析技术改进：

- **Segmentation (分割原理)**: 分析模块化解耦设计
- **Local Quality (局部质量)**: 识别针对特定场景的优化算法
- **Feedback (反馈原理)**: 提取闭环控制与自适应逻辑
- **Intermediary (中介物)**: 分析中间件与代理模式

### 2. 权利要求书构建 (Claims Construction)

自动生成结构化的权利要求书 (Claims)：

*   **Independent Claims (独权)**: 最小化限制特征，通过上位概念（Genus）替代下位概念（Species）来最大化保护范围。
    *   *Example*: Use "data storage device" instead of "Redis cache".
*   **Dependent Claims (从权)**: 构建多层防御体系。
    *   Tier 1: 核心功能具体实现
    *   Tier 2: 性能优化特征
    *   Tier 3: 安全与异常处理机制
*   **Method/Apparatus/System Claims**: 同时生成"方法"、"装置"、"系统"和"介质"四套权利要求。

### 3. 具体实施方式扩展 (Embodiment Expansion)

基于代码逻辑自动推演替代方案（规避设计）：

- **算法替换**: "QuickSort can be replaced by MergeSort or HeapSort..."
- **架构变种**: "Although implemented as microservices, can be monolithic..."
- **数据结构**: "Identifying trees can be replaced by hash maps for O(1) access..."

### 4. 交互式附图 (Patent Drawings)

生成符合专利局标准（USPTO/CNIPA）的附图说明：

- **Fig. 1**: System Environment (系统环境图)
- **Fig. 2**: Core Logic Flowchart (核心逻辑流程图)
- **Fig. 3**: Data Structure Diagram (数据结构示意图)
- **Fig. 4**: Hardware Apparatus Block Diagram (硬件装置框图)

## Hooks

### after_analyze (Innovation Mining)

1.  **Code Pattern Analysis**: 识别设计模式（单例、工厂、观察者）作为技术方案。
2.  **Complexity extraction**: 将高圈复杂度（Cyclomatic Complexity）的代码段标记为潜在的"非显而易见性"（Non-obviousness）来源。
3.  **Diff Analysis**: 对比 Git 历史，提取"解决的技术问题"（Technical Problem Solved）。

### after_generate (Drafting)

1.  **Claim Tree Generation**: 构建权利要求树。
2.  **Specification Drafting**:
    *   **Field**: 自动分类 IPC/CPC 号。
    *   **Background**: 基于痛点生成现有技术缺陷描述。
    *   **Summary**: 对应权项生成发明内容。
    *   **Detailed Description**: 结合代码引用生成实施例。
3.  **Review**: 进行形式审查（Antecedent Basis 检查、不清楚的主题检查）。

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加专业配置：

```yaml
plugins:
  patent-generator:
    # 目标局点
    jurisdiction: CN  # CN (China) | US (USPTO) | EP (EPO) | PCT
    
    # 策略模式
    strategy: defensive  # defensive (广覆盖) | offensive (针对竞品)
    
    # TRIZ 增强
    enable_triz_analysis: true
    
    # 实施例扩展强度
    embodiment_expansion_level: high  # low | medium | high
    
    # 术语抽象化字典 (用于上位化)
    term_abstraction:
      "Redis": "high-speed caching memory"
      "MySQL": "relational database storage"
      "React Component": "user interface rendering unit"
      
    # 发明人信息
    inventors:
      - name: "Alice Smith"
        citizenship: "US"
```

## 输出示例 / Output Example

### 权利要求书 (`patent/claims.md`)

```markdown
1. A documentation generation system, comprising:
   an analysis interface configured to receive a project identifier;
   a parsing engine coupled to the analysis interface...
   and a generation module configured to...

2. The system of claim 1, wherein the parsing engine utilizes a recursive descent algorithm...

3. A computer-implemented method for automated documentation...
```

### 创新点 TRIZ 分析报告 (`patent/triz_analysis.md`)

```markdown
## Detected Innovation: Plugin Hooks Mechanism

**TRIZ Principle #35: Parameter Changes**
Changing the degree of flexibility...

**Technical Contradiction:**
System Stability vs. Flexibility.
The invention resolves this by isolating dynamic plugins from the core kernel...
```

## 命令 / Commands

```bash
# 生成全套申请文件
python scripts/plugin_manager.py run patent-generator generate --full

# 仅生成权利要求树
python scripts/plugin_manager.py run patent-generator claims

# 运行侵权规避分析 (FTO Draft)
python scripts/plugin_manager.py run patent-generator fto-check
```
