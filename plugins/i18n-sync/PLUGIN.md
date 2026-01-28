---
name: i18n-sync
type: enhancer
version: 1.0.0
description: |
  多语言文档同步工具，自动检测和翻译文档差异。
  Multi-language documentation sync tool with automatic diff detection and translation.
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - after_generate
---

# i18n Sync / 多语言同步工具

自动检测多语言文档的差异，辅助翻译和同步。

## 功能特性 / Features

### 1. 差异检测 / Diff Detection

自动检测主语言和翻译版本之间的差异：

| 状态 | 图标 | 说明 |
|------|------|------|
| 同步 | 🟢 | 内容一致 |
| 过时 | 🟡 | 原文已更新 |
| 缺失 | 🔴 | 翻译不存在 |
| 多余 | ⚪ | 原文已删除 |

### 2. 结构映射 / Structure Mapping

```
.mini-wiki/wiki/              # 主语言 (默认 en)
├── index.md
├── architecture.md
└── modules/
    └── auth.md

.mini-wiki/i18n/zh/          # 翻译版本
├── index.md         🟢 同步
├── architecture.md  🟡 过时 (原文更新于 3 天前)
└── modules/
    └── auth.md      🔴 缺失
```

### 3. 翻译辅助 / Translation Helpers

- 🔍 显示原文和译文的差异对比
- 📋 导出待翻译内容
- 🤖 可集成 AI 翻译 API

### 4. 翻译记忆 / Translation Memory

保存已翻译的片段，提高一致性：

```yaml
# cache/i18n-memory.yaml
"Getting Started": "快速开始"
"Installation": "安装"
"Configuration": "配置"
```

## Hooks

### after_analyze

分析项目后：

1. 扫描主语言文档
2. 扫描各语言翻译目录
3. 对比文件结构和内容哈希
4. 生成同步状态报告
5. 保存到 `cache/i18n-status.json`

### after_generate

生成后：

1. 更新同步状态
2. 生成翻译任务列表
3. 可选：触发自动翻译

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  i18n-sync:
    # 主语言
    source_language: en
    
    # 目标语言列表
    target_languages:
      - zh
      - ja
      - ko
    
    # 忽略的文件
    ignore:
      - "**/*.draft.md"
      - "**/internal/**"
    
    # 是否生成同步报告
    generate_report: true
    
    # 翻译记忆设置
    translation_memory:
      enabled: true
      file: cache/i18n-memory.yaml
    
    # AI 翻译设置（可选）
    ai_translation:
      enabled: false
      provider: openai  # openai | azure | deepl | google
      api_key_env: TRANSLATION_API_KEY
      auto_translate: false  # 仅辅助，不自动替换
    
    # 通知设置
    notifications:
      # 过时超过 N 天发出警告
      outdated_threshold_days: 7
```

## 输出示例 / Output Example

### 同步状态报告

自动生成 `wiki/i18n-status.md`：

```markdown
# 多语言同步状态

最后更新: 2024-01-15 10:30:00

## 概览

| 语言 | 总计 | 🟢 同步 | 🟡 过时 | 🔴 缺失 | 进度 |
|------|------|--------|--------|--------|------|
| 中文 (zh) | 15 | 10 | 3 | 2 | 67% |
| 日语 (ja) | 15 | 8 | 4 | 3 | 53% |

## 中文 (zh) 详情

### 🟡 需要更新 (3)

| 文件 | 原文更新 | 译文更新 | 差异 |
|------|----------|----------|------|
| [architecture.md](file:///wiki/architecture.md) | 3 天前 | 10 天前 | [查看](file:///cache/diffs/zh/architecture.diff) |
| [modules/auth.md](file:///wiki/modules/auth.md) | 1 天前 | 5 天前 | [查看](file:///cache/diffs/zh/auth.diff) |

### 🔴 待翻译 (2)

| 文件 | 原文 | 操作 |
|------|------|------|
| modules/payments.md | [查看](file:///wiki/modules/payments.md) | 新增 |
| api/webhooks.md | [查看](file:///wiki/api/webhooks.md) | 新增 |

## 翻译进度趋势

​```mermaid
xychart-beta
    title "翻译完成度"
    x-axis ["Jan W1", "Jan W2", "Jan W3", "Jan W4"]
    y-axis "完成度 %" 0 --> 100
    bar [45, 52, 60, 67]
​```
```

### 差异对比文件

`cache/diffs/zh/architecture.diff`:

```diff
## 系统架构

- 本项目采用模块化设计。
+ 本项目采用插件化模块设计，支持动态扩展。

### 核心模块

+ #### 插件系统
+ 
+ 新增插件系统，支持以下钩子：
+ - `on_init`
+ - `after_analyze`
+ - `before_generate`
```

## 命令 / Commands

```bash
# 检查同步状态
python scripts/i18n_sync.py status

# 检查指定语言
python scripts/i18n_sync.py status --lang zh

# 导出待翻译内容
python scripts/i18n_sync.py export --lang zh --output ./to-translate/

# 导入翻译结果
python scripts/i18n_sync.py import --lang zh --input ./translated/

# 使用 AI 辅助翻译（需配置 API）
python scripts/i18n_sync.py translate --lang zh --file architecture.md

# 更新翻译记忆
python scripts/i18n_sync.py sync-memory
```

## 工作流建议 / Workflow Suggestions

### 推荐工作流

1. **写作阶段**: 先用主语言完成文档
2. **生成阶段**: 运行 `mini-wiki generate`
3. **检查阶段**: 运行 `i18n-sync status` 查看差异
4. **翻译阶段**: 导出待翻译内容，完成翻译
5. **同步阶段**: 导入翻译，更新翻译记忆

### CI/CD 集成

```yaml
# .github/workflows/docs.yml
- name: Check i18n status
  run: |
    python scripts/i18n_sync.py status --strict
    # 如果有过时翻译超过 7 天，将失败
```

## 支持的语言代码 / Language Codes

使用 ISO 639-1 代码：

| 代码 | 语言 |
|------|------|
| `en` | English |
| `zh` | 中文 |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `fr` | Français |
| `de` | Deutsch |
| `es` | Español |
| `pt` | Português |
| `ru` | Русский |
