# Changelog

All notable changes to this project will be documented in this file.

## [3.0.3] - 2026-01-28

### 🔍 Quality Check System

新增文档质量自动检查系统：

- **新增 `scripts/check_quality.py`**：自动化质量检查脚本
  - 检查行数、章节数、图表数、代码示例数
  - 检查 classDiagram、源码追溯、必需章节
  - 输出质量评估报告（Professional/Standard/Basic）
  - 支持 `--verbose` 详细报告和 `--json` 导出

**使用方法**：
```bash
python scripts/check_quality.py /path/to/.mini-wiki --verbose
```

---

## [3.0.2] - 2026-01-28

### 🚀 Documentation Quality Enhancement

对比 Qoder 等竞品文档质量后，大幅强化文档生成标准：

- **🔴 源码追溯**：每个章节末尾必须包含 `Section sources` 和 `Diagram sources` 引用
- **🔴 classDiagram 强制**：每个核心类/接口必须生成详细类图（含属性+方法）
- **🔴 模块文档结构**：强制 9 个必需章节（概述、核心功能、最佳实践、性能优化、错误处理等）
- **🔴 最小行数要求**：模块文档最少 200+ 行
- **图表要求提升**：从 1-2 个提升到 2-3 个/文档

---

## [3.0.1] - 2026-01-28

### 📝 Documentation Improvements

- **Update Instructions**: Added update section to README with npx, git, and .skill file methods
- **FAQ Section**: Added FAQ addressing common questions:
  - Will updating delete existing docs? (No)
  - How to upgrade low-quality docs? (Commands & quality levels)
  - Will custom content be preserved? (Yes, with `<!-- user-content -->`)
  - How to check doc quality? (`check wiki quality` command)
- **UI Fix**: All `<details>` sections now expanded by default for better readability

---

## [3.0.0] - 2026-01-28

### 🚀 Major Release: Professional-Grade Documentation

本版本全面升级文档生成质量标准，从"基础文档"提升至"企业级专业文档"。

### Added

- **📋 文档质量标准体系**
  - 内容深度要求：完整上下文、详细说明、可运行示例
  - 结构要求：层级标题、表格、Mermaid 图表、交叉链接
  - 每个文档至少 1-2 个图表（架构图、流程图、状态图等）
  - 文档关系网络：自动生成 `doc-map.md`

- **🔍 深度代码分析**
  - 新增代码语义分析步骤（不仅分析结构，还理解功能）
  - 提取函数目的、参数、返回值、副作用
  - 识别设计模式和数据流
  - 生成模块依赖图和调用图

- **🚀 大型项目渐进式扫描**
  - 触发条件：模块 > 10 / 文件 > 50 / 代码行 > 10,000
  - 批次划分 + 优先级排序 + 进度跟踪
  - 断点续传：`继续生成 wiki` 命令
  - 配置：`progressive.batch_size`, `progressive.auto_continue`

- **🔄 文档升级刷新机制**
  - 版本检测：自动识别旧版本生成的文档
  - 质量评估：basic / standard / professional 三级标准
  - 升级策略：`refresh_all` / `upgrade_progressive` / `upgrade_selective`
  - 命令：`检查 wiki 质量`, `升级 wiki`, `刷新全部 wiki`

### Changed

- **SKILL.md** 重构（350 行 → 600+ 行）
  - 新增"文档质量标准"章节
  - 新增"深度代码分析"步骤
  - 新增"大型项目渐进式扫描"章节
  - 新增"文档升级刷新"章节
  - 详细的内容生成规范（首页、架构、模块、API 各 10+ 要求项）

- **references/prompts.md** 全面重写（130 行 → 577 行）
  - 专业级 AI 提示词模板
  - 强制内容深度和图表要求
  - 代码深度分析提示词

- **references/templates.md** 全面重写（279 行 → 1496 行）
  - 专业级 Markdown 模板
  - 内置 Mermaid 图表模板
  - 16 章节模块文档模板

- **SKILL.zh.md** 同步更新

### Plugins Enhanced

- **api-doc-enhancer** v2.0.0 → 专业级（124 行 → 620+ 行）
  - 深度语义分析
  - 3 层示例生成（基础、进阶、错误处理）
  - API 关系图谱
  - 大型项目渐进式扫描支持
  - 文档升级支持

- **repo-analytics** v2.0.0 → 专业级（125 行 → 640+ 行）
  - 5 维分析（贡献者、演进、热点、协作、健康度）
  - 健康度评分系统
  - 协作网络图
  - 风险热点识别
  - 渐进式历史分析

- **patent-generator** v2.0.0 → v3.0.0 专业级（155 行 → 454 行）
  - 基于资深专利代理人经验重写
  - 7 步标准专利交底书流程
  - 符合《专利法实施细则》和《专利审查指南》
  - 发明名称、技术领域、背景技术、发明目的、技术方案、有益效果、实施例
  - 术语抽象化和禁用词汇检查

### Configuration

新增配置项：
```yaml
generation:
  detail_level: detailed      # minimal / standard / detailed
  min_sections: 10            # 每个模块文档最少章节数

diagrams:
  architecture_style: flowchart TB
  dataflow_style: sequenceDiagram
  use_colors: true

linking:
  auto_cross_links: true
  generate_doc_map: true
  generate_dependency_graph: true

progressive:
  enabled: auto
  batch_size: 5
  auto_continue: false

upgrade:
  auto_detect: true
  backup_before_upgrade: true
  preserve_user_content: true
  min_quality: professional
```

---

## [2.1.0] - 2026-01-28

### Added
- **7 个内置插件**:
  - `code-complexity` (分析器)
  - `paper-drafter` (生成器) - **NEW**
  - `repo-analytics` (分析器) - **NEW**
  - `patent-generator` (生成器) - **NEW**
  - `api-doc-enhancer` (生成器)
  - `changelog-generator` (生成器)
  - `diagram-plus` (增强器)
  - `i18n-sync` (增强器)
  - `docusaurus-exporter` (格式/导出器)
  - `gitbook-exporter` (格式/导出器)
- **Skills.sh 兼容性增强**:
  - 支持通过 `owner/repo` 简写安装 GitHub 上的插件
  - 自动将通用 Skills (无 PLUGIN.md) 包装为 mini-wiki 插件
  - 支持直接安装 skills.sh 上的任何 skill 作为增强能力
- **插件管理增强**:
  - 新增 `update` 命令支持插件版本更新
  - Registry 支持记录插件来源元数据 (GitHub/URL)

### Changed
- **SKILL.md**: 增加了 `Plugin Execution Protocol`，强制 AI 在工作流中加载并执行插件指令
- **README**: 增加了对插件运行机制的说明

## [2.0.0] - 2026-01-26

### Added
- 按 [skills.sh](https://skills.sh) 标准重构整个技能
- 增量更新支持（基于文件校验和）
- 多语言 Wiki 生成（`i18n/en/`, `i18n/zh/`）
- 代码块源码链接 `[📄](file://...#L行号)`
- Mermaid 架构图自动生成
- **插件系统** (`plugins/` 目录)
  - `_registry.yaml` 插件注册表
  - `plugin_manager.py` 插件管理脚本
  - 支持 5 种钩子：on_init, after_analyze, before_generate, after_generate, on_export
  - 支持从 URL 或本地路径安装插件
- 7 个 Python 辅助脚本
- 中英文分离的文档

### Changed
- 输出目录改为 `.mini-wiki/`
- SKILL.md 精简至 ~150 行，遵循 Progressive Disclosure 原则
- 移除用户模型配置，Agent 使用自身模型生成内容

### Removed
- 移除 `examples/` 目录（遵循 skills.sh 规范）
- 移除冗余模板文件

## [1.0.0] - 2026-01-26

### Added
- 初始版本
- 基础 Wiki 生成功能
- 项目分析脚本
- 文档提取脚本
