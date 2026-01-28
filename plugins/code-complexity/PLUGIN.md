---
name: code-complexity
type: analyzer
version: 1.0.0
description: |
  分析代码复杂度指标，生成质量报告和可视化图表。
  Analyze code complexity metrics and generate quality reports with visualizations.
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - before_generate
---

# Code Complexity / 代码复杂度分析器

分析项目代码的复杂度指标，帮助识别需要重构的代码区域。

## 功能特性 / Features

### 1. 复杂度指标 / Complexity Metrics

| 指标 | 英文名 | 说明 |
|------|--------|------|
| 圈复杂度 | Cyclomatic Complexity | 代码路径数量 |
| 认知复杂度 | Cognitive Complexity | 代码理解难度 |
| 代码行数 | Lines of Code (LOC) | 物理/逻辑行数 |
| 嵌套深度 | Nesting Depth | 最大嵌套层级 |
| 参数数量 | Parameter Count | 函数参数个数 |
| 依赖数量 | Dependencies | 模块依赖数量 |

### 2. 健康评分 / Health Score

基于多个指标计算代码健康评分：

```
健康评分 = 100 - (complexity_penalty + nesting_penalty + size_penalty)
```

| 评分 | 状态 | 建议 |
|------|------|------|
| 90-100 | 🟢 优秀 | 保持现状 |
| 70-89 | 🟡 良好 | 可以优化 |
| 50-69 | 🟠 一般 | 建议重构 |
| 0-49 | 🔴 较差 | 需要重构 |

### 3. 热点分析 / Hotspot Analysis

识别代码热点区域：
- 🔥 高复杂度函数
- ⚠️ 深层嵌套代码
- 📦 过大模块
- 🔄 高耦合模块

### 4. 趋势追踪 / Trend Tracking

记录复杂度变化趋势，支持历史对比。

## Hooks

### after_analyze

分析项目后：

1. 遍历所有源代码文件
2. 计算每个函数/方法的复杂度
3. 聚合模块级别指标
4. 识别热点区域
5. 保存到 `cache/complexity-report.json`

### before_generate

生成前：

1. 准备复杂度数据
2. 生成可视化图表
3. 创建建议列表
4. 注入到文档模板

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  code-complexity:
    # 启用的指标
    metrics:
      - cyclomatic
      - cognitive
      - loc
      - nesting
      - params
    
    # 阈值配置
    thresholds:
      cyclomatic:
        warning: 10
        error: 20
      cognitive:
        warning: 15
        error: 25
      nesting:
        warning: 4
        error: 6
      params:
        warning: 5
        error: 8
      loc_per_function:
        warning: 50
        error: 100
    
    # 排除路径
    exclude:
      - "**/*.test.ts"
      - "**/__tests__/**"
      - "**/node_modules/**"
    
    # 是否生成趋势图
    track_trends: true
    
    # 是否在 README 中显示徽章
    show_badge: true
```

## 输出示例 / Output Example

### 复杂度报告页面

```markdown
# 代码复杂度报告

## 概览

| 指标 | 值 | 状态 |
|------|------|------|
| 平均圈复杂度 | 5.2 | 🟢 |
| 最高圈复杂度 | 23 | 🔴 |
| 平均嵌套深度 | 2.1 | 🟢 |
| 代码健康评分 | 78/100 | 🟡 |

## 热点函数 Top 5

| 函数 | 文件 | 复杂度 | 建议 |
|------|------|--------|------|
| `parseConfig` | config.ts:42 | 23 | 拆分函数 |
| `validateInput` | validator.ts:15 | 18 | 简化条件 |
| `processData` | handler.ts:89 | 15 | 提取子函数 |

## 模块复杂度分布

​```mermaid
pie title 模块复杂度分布
    "core" : 35
    "plugins" : 25
    "utils" : 15
    "validators" : 25
​```

## 复杂度趋势

​```mermaid
xychart-beta
    title "圈复杂度趋势"
    x-axis [Jan, Feb, Mar, Apr, May]
    y-axis "平均复杂度" 0 --> 15
    line [8, 9, 7, 6, 5.2]
​```
```

### 健康徽章

自动在 README.md 中添加：

```markdown
![Code Health](https://img.shields.io/badge/code%20health-78%25-yellow)
![Complexity](https://img.shields.io/badge/avg%20complexity-5.2-green)
```

## 命令 / Commands

```bash
# 运行完整分析
python scripts/complexity_analyzer.py analyze

# 仅分析指定目录
python scripts/complexity_analyzer.py analyze --path src/

# 导出报告
python scripts/complexity_analyzer.py report --format html

# 检查是否超出阈值（CI 用）
python scripts/complexity_analyzer.py check --fail-on-error
```

## 支持的语言 / Supported Languages

- ✅ TypeScript / JavaScript
- ✅ Python
- ✅ Go
- ✅ Java
- ✅ Rust
- ⚙️ C/C++ (需要额外配置)
