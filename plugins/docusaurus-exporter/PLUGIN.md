---
name: docusaurus-exporter
type: formatter
version: 1.0.0
description: |
  将 Wiki 导出为 Docusaurus 兼容格式，支持版本控制和国际化。
  Export Wiki to Docusaurus-compatible format with versioning and i18n support.
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - on_export
---

# Docusaurus Exporter / Docusaurus 导出器

将 mini-wiki 生成的文档导出为 [Docusaurus](https://docusaurus.io/) 兼容格式。

## 功能特性 / Features

### 1. 目录结构转换 / Structure Conversion

```
.mini-wiki/wiki/           →    docs/
├── index.md               →    ├── intro.md
├── architecture.md        →    ├── architecture.md
├── modules/               →    ├── modules/
│   ├── auth.md            →    │   ├── auth.md
│   └── api.md             →    │   └── api.md
└── i18n/zh/               →    i18n/zh/docusaurus-plugin-content-docs/
    └── ...                →        └── current/...
```

### 2. Frontmatter 生成 / Frontmatter Generation

自动添加 Docusaurus 所需的 frontmatter：

```yaml
---
id: module-auth
title: 认证模块
sidebar_label: 认证
sidebar_position: 2
tags:
  - auth
  - security
---
```

### 3. 侧边栏配置 / Sidebar Configuration

自动生成 `sidebars.js`：

```javascript
module.exports = {
  docs: [
    'intro',
    {
      type: 'category',
      label: '模块',
      items: ['modules/auth', 'modules/api'],
    },
  ],
};
```

### 4. 国际化支持 / i18n Support

- 自动映射 `i18n/zh/` → Docusaurus i18n 结构
- 生成 `i18n/zh/code.json` 翻译文件
- 配置语言切换

## Hooks

### on_export

导出时执行：

1. 读取 `.mini-wiki/wiki/` 目录
2. 转换 Markdown 格式
3. 生成 frontmatter
4. 创建 sidebars.js
5. 输出到指定目录

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  docusaurus-exporter:
    # 输出目录
    output_dir: ./docusaurus-docs
    
    # Docusaurus 版本
    docusaurus_version: 3
    
    # 是否包含版本控制
    versioning: false
    
    # 默认语言
    default_locale: en
    
    # 支持的语言
    locales:
      - en
      - zh
    
    # 侧边栏位置
    sidebar_position_from: filename  # filename | frontmatter | auto
```

## 使用方法 / Usage

### 命令行

```bash
# 导出到默认目录
python scripts/plugin_manager.py export docusaurus

# 导出到指定目录
python scripts/plugin_manager.py export docusaurus --output ./my-docs
```

### 用户指令

对 AI 说：
- "export wiki to docusaurus"
- "导出 wiki 为 docusaurus 格式"

## 输出结构 / Output Structure

```
docusaurus-docs/
├── docs/
│   ├── intro.md
│   ├── architecture.md
│   └── modules/
│       ├── _category_.json
│       └── *.md
├── i18n/
│   └── zh/
│       └── docusaurus-plugin-content-docs/
│           └── current/
│               └── *.md
├── sidebars.js
└── docusaurus.config.js.patch   # 建议的配置修改
```

## 注意事项 / Notes

- 确保目标项目已安装 Docusaurus
- 图片路径会自动转换为相对路径
- 代码块语言标识符会保留
- 内部链接会自动转换为 Docusaurus 格式
