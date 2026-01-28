---
name: api-doc-enhancer
type: generator
version: 1.0.0
description: |
  增强 API 文档生成能力，自动提取代码注释和类型信息。
  Enhance API documentation generation with automatic comment and type extraction.
author: mini-wiki
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - before_generate
  - after_generate
---

# API Doc Enhancer / API 文档增强器

自动从代码中提取注释、类型定义和函数签名，生成更完整的 API 文档。

## 功能特性 / Features

### 1. 注释提取 / Comment Extraction

自动识别和提取多种注释格式：

| 语言 | 支持的格式 |
|------|-----------|
| JavaScript/TypeScript | JSDoc (`/** ... */`) |
| Python | docstring (`"""..."""`) |
| Go | GoDoc comments |
| Rust | `///` 和 `//!` 文档注释 |
| Java | Javadoc |

### 2. 类型推断 / Type Inference

- 提取 TypeScript 类型定义
- 解析 Python type hints
- 识别函数参数和返回值类型

### 3. 示例代码生成 / Example Generation

根据函数签名自动生成使用示例。

## Hooks

### after_analyze

分析阶段后，扫描源代码文件：

1. 识别导出的函数、类、接口
2. 提取 JSDoc/docstring 注释
3. 解析类型定义
4. 保存到 `cache/api-analysis.json`

### before_generate

生成前准备 API 文档模板：

1. 按模块分组 API
2. 生成函数签名格式
3. 准备参数表格数据

### after_generate

生成后增强 API 文档：

1. 添加源码链接 `[📄](file:///path#L42)`
2. 生成类型关系图
3. 添加 "See Also" 交叉引用

## 配置 / Configuration

在 `.mini-wiki/config.yaml` 中添加：

```yaml
plugins:
  api-doc-enhancer:
    # 启用的语言
    languages:
      - typescript
      - python
    
    # 是否生成示例代码
    generate_examples: true
    
    # 是否包含私有 API
    include_private: false
    
    # 类型图表样式
    diagram_style: mermaid
```

## 输出示例 / Output Example

```markdown
## `createWiki(options)`

创建新的 Wiki 实例。

**参数 / Parameters**

| 名称 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `options` | `WikiOptions` | ✅ | Wiki 配置选项 |
| `options.title` | `string` | ✅ | Wiki 标题 |
| `options.language` | `'zh' \| 'en'` | ❌ | 语言，默认 'en' |

**返回值 / Returns**

`Promise<Wiki>` - Wiki 实例

**示例 / Example**

​```typescript
const wiki = await createWiki({
  title: 'My Project',
  language: 'zh'
});
​```

[📄 源码](file:///src/wiki.ts#L42)
```
