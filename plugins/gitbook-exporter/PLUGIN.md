---
name: gitbook-exporter
type: formatter
version: 1.0.0
description: |
  将 Wiki 导出为 GitBook 兼容格式，支持 SUMMARY.md 和多语言。
  Export Wiki to GitBook-compatible format with SUMMARY.md and i18n support.
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - on_export
---

# GitBook Exporter / GitBook 导出器

将 mini-wiki 生成的文档导出为 [GitBook](https://www.gitbook.com/) 兼容格式。

## 功能特性 / Features

### 1. 目录结构转换 / Structure Conversion

```
.mini-wiki/wiki/           →    gitbook-docs/
├── index.md               →    ├── README.md
├── architecture.md        →    ├── architecture.md
├── modules/               →    ├── modules/
│   ├── auth.md            →    │   ├── README.md
│   └── api.md             →    │   └── api.md
└── i18n/zh/               →    zh/
    └── ...                →        └── ...
```

### 2. SUMMARY.md 生成 / SUMMARY.md Generation

自动生成 GitBook 导航文件：

```markdown
# Summary

* [介绍](README.md)
* [架构](architecture.md)
* [模块](modules/README.md)
    * [认证](modules/auth.md)
    * [API](modules/api.md)
* [API 参考](api/README.md)
    * [核心](api/core.md)
    * [工具](api/utils.md)
```

### 3. book.json 配置 / book.json Configuration

自动生成 GitBook 配置：

```json
{
  "title": "项目名称",
  "description": "项目描述",
  "author": "作者",
  "language": "zh-hans",
  "gitbook": "3.2.3",
  "plugins": [
    "search",
    "sharing",
    "fontsettings",
    "theme-default"
  ],
  "pluginsConfig": {
    "sharing": {
      "facebook": false,
      "twitter": true
    }
  }
}
```

### 4. 多语言支持 / i18n Support

支持 GitBook 多语言结构：

```
gitbook-docs/
├── LANGS.md
├── en/
│   ├── README.md
│   └── SUMMARY.md
└── zh/
    ├── README.md
    └── SUMMARY.md
```

**LANGS.md 示例：**
```markdown
# Languages

* [English](en/)
* [中文](zh/)
```

## Hooks

### on_export

导出时执行：

1. 读取 `.mini-wiki/wiki/` 目录
2. 转换文件名（index.md → README.md）
3. 生成 SUMMARY.md
4. 创建 book.json
5. 处理多语言目录
6. 输出到指定目录

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  gitbook-exporter:
    # 输出目录
    output_dir: ./gitbook-docs
    
    # GitBook 版本
    gitbook_version: "3.2.3"
    
    # 默认语言
    default_language: zh-hans
    
    # 多语言模式
    multilingual: true
    
    # 支持的语言
    languages:
      - code: en
        label: English
      - code: zh
        label: 中文
    
    # GitBook 插件
    plugins:
      - search
      - sharing
      - highlight
      - copy-code-button
    
    # 是否包含 PDF 导出配置
    pdf_options:
      enabled: true
      fontSize: 12
      paperSize: a4
```

## 使用方法 / Usage

### 命令行

```bash
# 导出到默认目录
python scripts/plugin_manager.py export gitbook

# 导出到指定目录
python scripts/plugin_manager.py export gitbook --output ./my-gitbook

# 仅生成 SUMMARY.md
python scripts/plugin_manager.py export gitbook --summary-only
```

### 用户指令

对 AI 说：
- "export wiki to gitbook"
- "导出 wiki 为 gitbook 格式"
- "generate gitbook docs"

## 输出结构 / Output Structure

```
gitbook-docs/
├── README.md              # 首页
├── SUMMARY.md             # 导航目录
├── book.json              # GitBook 配置
├── architecture.md
├── modules/
│   ├── README.md
│   └── *.md
├── api/
│   └── *.md
└── assets/
    └── images/
```

## 与 Docusaurus Exporter 对比 / Comparison

| 特性 | GitBook | Docusaurus |
|------|---------|------------|
| 导航配置 | SUMMARY.md | sidebars.js |
| 配置文件 | book.json | docusaurus.config.js |
| 首页文件 | README.md | intro.md |
| 多语言 | LANGS.md | i18n/ 目录 |
| 托管 | GitBook.com | 自托管 |
| 适合场景 | 快速文档 | 完整文档站 |

## 注意事项 / Notes

- GitBook 3.x 和 GitBook.com (v2) 格式略有不同
- 相对链接会自动转换
- Mermaid 图表需要 GitBook 插件支持
- 建议安装 `gitbook-plugin-mermaid-gb3` 插件
