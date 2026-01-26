---
name: example-enhancer
type: enhancer
version: 1.0.0
description: Example plugin demonstrating the plugin format
author: trsoliu
requires:
  - mini-wiki >= 2.0.0
hooks:
  - after_analyze
  - before_generate
---

# Example Enhancer

This is an example plugin demonstrating the plugin format for mini-wiki.

## What it does

This plugin serves as a template and reference for creating your own plugins.

## How to use

1. Copy this directory as a starting point
2. Rename to your plugin name
3. Update PLUGIN.md with your plugin details
4. Add your scripts and resources

## Hooks

### after_analyze

After project analysis, this hook can add additional analysis data.

Example: Add code complexity metrics to the analysis.

### before_generate

Before content generation, this hook can modify prompts or templates.

Example: Add custom sections to the wiki templates.

## Creating your own plugin

1. Create a new directory in `plugins/`
2. Add `PLUGIN.md` with YAML frontmatter
3. Optionally add `scripts/`, `references/`, `assets/`
4. Enable in `_registry.yaml`
