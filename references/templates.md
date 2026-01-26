# Wiki 页面模板

本文件包含生成 Wiki 各页面的 Markdown 模板。

## 目录

1. [首页模板](#首页模板)
2. [架构文档模板](#架构文档模板)
3. [模块文档模板](#模块文档模板)
4. [API 参考模板](#api-参考模板)
5. [快速开始模板](#快速开始模板)

---

## 首页模板

```markdown
# {{ PROJECT_NAME }}

[![技术栈](https://img.shields.io/badge/Tech-{{ TECH_STACK }}-blue)](#)
[![版本](https://img.shields.io/badge/Version-{{ VERSION }}-green)](#)

> {{ PROJECT_DESCRIPTION }}

## 📚 文档导航

| 文档 | 描述 |
|------|------|
| [🚀 快速开始](getting-started.md) | 安装和配置指南 |
| [🏗 架构概览](architecture.md) | 系统设计和模块结构 |
| [📦 模块文档](modules/_index.md) | 各模块详细说明 |
| [📖 API 参考](api/_index.md) | 接口文档 |

## ✨ 主要特性

{{ FEATURES_LIST }}

## 🏗 项目结构

\`\`\`
{{ PROJECT_STRUCTURE }}
\`\`\`

## 📊 项目统计

| 指标 | 数值 |
|------|------|
| 代码文件 | {{ TOTAL_FILES }} |
| 模块数 | {{ TOTAL_MODULES }} |

## 📦 核心模块

{{ MODULES_TABLE }}

---

*由 Mini-Wiki 自动生成 | {{ GENERATED_AT }}*
```

---

## 架构文档模板

```markdown
# 系统架构

> {{ PROJECT_NAME }} 的技术架构概览

## 架构图

\`\`\`mermaid
flowchart TB
    subgraph Frontend["前端层"]
        {{ FRONTEND_NODES }}
    end
    
    subgraph Core["核心层"]
        {{ CORE_NODES }}
    end
    
    subgraph Utils["工具层"]
        {{ UTIL_NODES }}
    end
    
    Frontend --> Core
    Core --> Utils
\`\`\`

## 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
{{ TECH_STACK_TABLE }}

## 模块划分

{{ MODULES_DESCRIPTION }}

## 数据流

\`\`\`mermaid
sequenceDiagram
    {{ DATA_FLOW }}
\`\`\`

---

[← 返回首页](index.md)
```

---

## 模块文档模板

```markdown
# {{ MODULE_NAME }}

> {{ MODULE_DESCRIPTION }}

## 概述

{{ MODULE_OVERVIEW }}

## 文件结构

\`\`\`
{{ MODULE_PATH }}/
{{ MODULE_STRUCTURE }}
\`\`\`

## 公开接口

### 函数

| 函数名 | 描述 | 源码 |
|--------|------|------|
{{ FUNCTIONS_TABLE }}

### 类

| 类名 | 描述 | 源码 |
|------|------|------|
{{ CLASSES_TABLE }}

## 使用示例

\`\`\`{{ LANG }}
{{ EXAMPLE_CODE }}
\`\`\`

## 相关模块

{{ RELATED_MODULES }}

---

[← 返回模块列表](_index.md)
```

---

## API 参考模板

```markdown
# API 参考: {{ MODULE_NAME }}

> {{ MODULE_DESCRIPTION }}

## 函数

### `{{ FUNCTION_NAME }}` [📄](file://{{ SOURCE_PATH }}#L{{ LINE }})

{{ FUNCTION_DESCRIPTION }}

**签名:**
\`\`\`{{ LANG }}
{{ FUNCTION_SIGNATURE }}
\`\`\`

**参数:**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
{{ PARAMS_TABLE }}

**返回值:** `{{ RETURN_TYPE }}` - {{ RETURN_DESC }}

**示例:**
\`\`\`{{ LANG }}
{{ EXAMPLE }}
\`\`\`

---

## 类型定义

### `{{ TYPE_NAME }}`

\`\`\`{{ LANG }}
{{ TYPE_DEFINITION }}
\`\`\`

| 属性 | 类型 | 说明 |
|------|------|------|
{{ TYPE_PROPERTIES }}

---

[← 返回 API 列表](_index.md)
```

---

## 快速开始模板

```markdown
# 快速开始

> 本指南帮助你快速上手 {{ PROJECT_NAME }}

## 环境要求

{{ REQUIREMENTS_LIST }}

## 安装

\`\`\`bash
{{ INSTALL_COMMAND }}
\`\`\`

## 配置

\`\`\`bash
cp .env.example .env
\`\`\`

## 启动

\`\`\`bash
{{ START_COMMAND }}
\`\`\`

## 第一个示例

\`\`\`{{ LANG }}
{{ FIRST_EXAMPLE }}
\`\`\`

---

[← 返回首页](index.md)
```

---

## config.yaml 模板

```yaml
# Mini-Wiki 配置文件

generation:
  language: zh          # zh / en / both
  include_diagrams: true
  include_examples: true
  link_to_source: true
  max_file_size: 100000

exclude:
  - node_modules
  - .git
  - dist
  - build
  - coverage
  - __pycache__
  - venv
  - "*.test.ts"
  - "*.spec.js"
```
