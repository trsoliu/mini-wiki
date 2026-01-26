# Plugin Template / 扩展模板

This document describes the PLUGIN.md format for creating mini-wiki plugins.

## PLUGIN.md Format

```yaml
---
name: plugin-name
type: generator          # analyzer | generator | formatter | integrator | enhancer
version: 1.0.0
description: Short description of what this plugin does
author: Your Name
requires:
  - mini-wiki >= 2.0.0
hooks:
  - on_init              # Run on initialization
  - after_analyze        # Run after project analysis
  - before_generate      # Run before content generation
  - after_generate       # Run after content generation
  - on_export            # Run on export
---

# Plugin Name

Description of the plugin.

## What it does

Explain the functionality.

## How to use

Instructions for using this plugin.

## Hooks

### on_init
What happens during initialization.

### after_analyze
What this hook adds to the analysis.

## Configuration

Any configuration options.
```

## Plugin Types / 扩展类型

| Type | Description |
|------|-------------|
| `analyzer` | Enhance project analysis (e.g., code complexity) |
| `generator` | Add new doc types (e.g., API docs) |
| `formatter` | Output format adapters (e.g., Docusaurus) |
| `integrator` | External integrations (e.g., GitHub) |
| `enhancer` | Improve existing features |

## Available Hooks / 可用钩子

| Hook | Timing | Use Case |
|------|--------|----------|
| `on_init` | 初始化时 | Setup plugin resources |
| `after_analyze` | 分析后 | Add analysis data |
| `before_generate` | 生成前 | Modify prompts/templates |
| `after_generate` | 生成后 | Post-process output |
| `on_export` | 导出时 | Convert to other formats |

## Directory Structure / 目录结构

```
your-plugin/
├── PLUGIN.md         # Plugin manifest (required)
├── scripts/             # Plugin scripts (optional)
│   └── your_script.py
├── references/          # Reference docs (optional)
└── assets/              # Assets (optional)
```
