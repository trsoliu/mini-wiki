<div align="center">

<img src="assets/banner.png" alt="Mini-Wiki Banner" width="100%">

[![Version](https://img.shields.io/badge/version-3.3.0-06B6D4?style=for-the-badge)](https://github.com/trsoliu/mini-wiki/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![skills.sh compatible](https://img.shields.io/badge/skills.sh-compatible-blue?style=for-the-badge)](https://skills.sh)

**A source-traceable project knowledge network for AI Agents, Markdown, and Obsidian**

[中文](README.zh.md) · [Skill instructions](SKILL.md) · [Changelog](CHANGELOG.md)

</div>

## What Mini-Wiki is

Mini-Wiki 3.3 turns a repository into a deterministic, versionable Markdown knowledge network. It learns from
Obsidian's strongest knowledge-management ideas—Properties, links/backlinks, Bases, Canvas, and optional app
integration—while keeping every core workflow independent of Obsidian.

The split is deliberate:

- the CLI owns scanning, stable IDs, graph construction, managed Markdown, navigation, validation, search, Bases,
  Canvas, the Manifest, transactions, and migration;
- the AI Agent owns evidence-based explanations inside protected content regions;
- Git owns the durable history;
- Obsidian is an optional reading and exploration surface.

## What changed in 3.3.0

- Canonical Wiki moved to the repository-level `wiki/` directory.
- Stable repository graph connects project, domain, module, source, symbol, and document nodes.
- Managed Markdown preserves Agent content and unknown user Properties across rebuilds.
- Transactional build, Manifest, dry-run, strict validation, and recoverable archive make updates deterministic.
- Local CJK-aware search works with or without SQLite FTS5.
- Four native Obsidian Bases provide module, source, quality, and orphan work queues.
- Three deterministic JSON Canvas 1.0 views expose architecture, domains, and source traceability.
- Optional Obsidian status/open commands are isolated from the core workflow.
- Third-party plugins are installed as disabled, instruction-only text with archive and path safety checks.

## Knowledge and state boundaries

```text
wiki/                         # canonical, portable knowledge; commit this
├── index.md
├── getting-started.md
├── architecture.md
├── knowledge-map.md
├── domains/
├── reference/
├── views/
│   ├── modules.base
│   ├── sources.base
│   ├── quality.base
│   └── orphans.base
└── canvas/
    ├── architecture.canvas
    ├── domains.canvas
    └── traceability.canvas

.mini-wiki/                   # configuration and rebuildable/local state
├── config.yaml
├── manifest.json
├── meta.json
├── cache/
│   ├── analysis.json
│   ├── graph.json
│   ├── build-plan.json
│   └── search.sqlite3
├── staging/
└── archive/                  # recoverable retired managed pages
```

Mini-Wiki never needs to create or modify `.obsidian/`. Durable documents use repository-relative links and remain
usable in a browser, editor, Git host, or any Markdown tool.

## Install

As an Agent Skill:

```bash
npx skills add trsoliu/mini-wiki
```

For the local CLI:

```bash
git clone https://github.com/trsoliu/mini-wiki.git
cd mini-wiki
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/mini-wiki --version
```

Development dependencies are available with `pip install -e '.[dev]'`.

## Build a Wiki

```bash
mini-wiki init /path/to/project
mini-wiki doctor --json /path/to/project
mini-wiki build --dry-run --json /path/to/project
mini-wiki build --json /path/to/project
mini-wiki check --strict --json /path/to/project
mini-wiki search "architecture decision" --json /path/to/project
```

After the first build, the Agent reads the build plan and graph, enriches only the `mini-wiki:content` regions with
repository evidence, then rebuilds and validates. A second unchanged build should produce no unexplained changes.

## Managed Markdown contract

```markdown
---
id: mw:document:domains/core/core
title: Core
type: module
domain: core
sources:
  - src/core/app.py
freshness: current
quality: basic
mini_wiki_version: 3.3.0
---

<!-- mini-wiki:generated:start -->
CLI-owned navigation, evidence, and relationships.
<!-- mini-wiki:generated:end -->

<!-- mini-wiki:content:start -->
Agent-owned professional explanation, preserved byte-for-byte on rebuild.
<!-- mini-wiki:content:end -->
```

Unknown Properties are user-owned and preserved. Documents without ownership markers are not adopted or overwritten.
Removed managed documents move to `.mini-wiki/archive/` rather than being silently deleted.

## Search without Obsidian

```bash
mini-wiki search "插件安装" --json /path/to/project
mini-wiki search "storage" --type module --tag domain/storage --limit 10 /path/to/project
```

The local index combines Markdown, Properties, aliases, tags, graph metadata, and bounded source text. Deterministic
CJK unigram/bigram normalization supports Chinese and mixed-language queries. SQLite FTS5 is an accelerator, not a
requirement; the fallback keeps the same filters and ranking rules.

## Properties, Bases, and Canvas

Properties are the single metadata model for pages and derived views.

| Artifact | Purpose |
| --- | --- |
| `views/modules.base` | Module status, freshness, quality, and backlinks |
| `views/sources.base` | Source coverage and drift |
| `views/quality.base` | Review and enrichment queue |
| `views/orphans.base` | Notes not connected to the knowledge network |
| `canvas/architecture.canvas` | Architectural layers and dependencies |
| `canvas/domains.canvas` | Domain and module map |
| `canvas/traceability.canvas` | Document-to-source and symbol traceability |

Bases are native declarative views over Properties. Canvas files are deterministic JSON Canvas 1.0 projections of
the graph; edit the source facts and rebuild instead of keeping unique knowledge inside a generated view.

## Validation and recovery

```bash
mini-wiki check --strict --json /path/to/project
mini-wiki migrate --json /path/to/project
mini-wiki migrate --apply --json /path/to/project
mini-wiki migrate --apply --adopt --json /path/to/project
```

Strict mode checks IDs, links, source boundaries and drift, ownership markers, orphans, Base schema, and Canvas node
and edge integrity. Migration is preview-first, refuses a non-empty destination, backs up legacy material, validates
the copied result, and switches configuration only after success. `--adopt` preserves each legacy body inside the
Agent-owned region.

## Optional Obsidian integration

```bash
mini-wiki obsidian status --json /path/to/project
mini-wiki obsidian status --probe --json /path/to/project
mini-wiki obsidian open /path/to/project
```

Normal status is side-effect free. `--probe` explicitly invokes the Obsidian CLI and may start the application.
`open` is the only Mini-Wiki command that asks Obsidian to open the configured Wiki, through an encoded Obsidian URI.
Build, search, check, migration, Bases, and Canvas generation never require the app.

## Instruction-only plugins

```bash
mini-wiki plugins list /path/to/project
mini-wiki plugins install owner/repository /path/to/project
mini-wiki plugins enable plugin-name /path/to/project
mini-wiki plugins disable plugin-name /path/to/project
mini-wiki plugins update plugin-name /path/to/project
mini-wiki plugins uninstall plugin-name /path/to/project
```

Plugin instructions are untrusted text. The Agent may read enabled `PLUGIN.md` or `SKILL.md` files and apply relevant
guidance, but must never import or execute plugin scripts, hooks, package managers, or commands. Network sources must
use HTTPS; installation rejects traversal paths, symbolic links, invalid roots, excessive archives, and silent
overwrite. Third-party plugins are disabled by default and recorded with a tree hash.

## Configuration

`mini-wiki init` creates schema v3 configuration with independent switches for search, Bases, Canvas, and optional
Obsidian integration. Scanning respects Git ignore rules, configured exclusions, symlink boundaries, file-size
limits, the state directory, and the Wiki directory.

See [SKILL.md](SKILL.md) for the complete Agent protocol, [Chinese workflow](references/SKILL.zh.md) for the Chinese
guide, [prompts](references/prompts.md) for evidence-first generation, and [templates](references/templates.md) for
managed-note examples.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
.venv/bin/mypy scripts
```

## License

[MIT](LICENSE)
