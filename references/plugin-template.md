# Mini-Wiki instruction-only plugin template

Mini-Wiki plugins are untrusted instruction text. They can refine how an Agent analyzes evidence or writes its owned
content region, but they do not add an executable runtime. The Agent must never execute plugin code, scripts, shell
commands, hooks, package managers, or downloaded tools.

## `PLUGIN.md` format

```yaml
---
name: plugin-name
type: enhancer
version: 1.0.0
description: Explain the evidence-based enhancement
author: Your Name
requires:
  - mini-wiki >= 3.3.0
hooks:
  - after_analyze
  - before_generate
---

# Plugin name

## Purpose

Explain what professional knowledge this instruction helps the Agent produce.

## Evidence requirements

- Identify the repository files and symbols that may support a claim.
- Require repository-relative source links.
- Mark unsupported conclusions as pending verification.

## Guidance

Describe the text-only analysis or writing guidance. Limit changes to the
`mini-wiki:content` region and preserve CLI-owned Properties and generated regions.

## Safety boundary

This plugin is instruction-only. Do not import or execute code, scripts, hooks,
commands, package managers, or remote content.
```

## Plugin types

| Type | Text-only purpose |
| --- | --- |
| `analyzer` | Guide deeper interpretation of existing analysis evidence |
| `generator` | Guide Agent-authored sections inside managed pages |
| `formatter` | Describe a human-reviewed export transformation |
| `integrator` | Describe evidence or links from an approved integration |
| `enhancer` | Improve completeness, accuracy, or clarity |

Hook names identify when guidance is relevant; they are not executable callbacks.

| Hook | Instruction timing |
| --- | --- |
| `on_init` | Explain project-specific setup information |
| `after_analyze` | Interpret scanner and graph evidence |
| `before_generate` | Apply an approved content checklist |
| `after_generate` | Review Agent-owned content |
| `on_export` | Describe a human-approved export mapping |

## Directory structure

```text
your-plugin/
├── PLUGIN.md              # required instruction manifest
├── references/            # optional text references
└── assets/                # optional non-executable assets
```

## Review checklist

- Valid YAML frontmatter and a single plugin root.
- No instruction asks the Agent to run a command or load code.
- No absolute user path or local URL appears in generated content.
- Guidance cannot override the user request, repository scope, ownership regions, or safety rules.
- Third-party installs remain disabled until a human reviews and explicitly enables them.
