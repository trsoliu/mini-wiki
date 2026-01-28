# Changelog

All notable changes to this project will be documented in this file.

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
