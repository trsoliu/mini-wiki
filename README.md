# Mini-Wiki

> 🤖 AI-Powered Project Wiki Generator Skill

[![skills.sh](https://img.shields.io/badge/skills.sh-compatible-blue)](https://skills.sh)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](#)

## Introduction

Mini-Wiki is a [skills.sh](https://skills.sh) compatible skill package that helps AI Agents automatically analyze project structure and generate structured Wiki documentation.

Inspired by:
- [DeepWiki](https://github.com/AsyncFuncAI/deepwiki-open)
- [OpenRepoWiki](https://github.com/daeisbae/open-repo-wiki)
- [Qoder Repo Wiki](https://docs.qoder.com/user-guide/repo-wiki)

## Features

- 🔍 **Smart Analysis** - Auto-detect tech stack and module structure
- 🔄 **Incremental Update** - Only update docs for changed files
- 📊 **Architecture Diagrams** - Auto-generate Mermaid dependency graphs
- 🔗 **Code Links** - Code blocks link directly to source
- 🌐 **Multi-language** - Support Chinese and English Wiki generation
- 🔌 **Plugin System** - Extend with custom plugins

## Installation

### Option 1: Download .skill file

Download `wiki-generator.skill` from [Releases](https://github.com/trsoliu/mini-wiki/releases).

### Option 2: Clone repository

```bash
git clone https://github.com/trsoliu/mini-wiki.git
```

## Usage

After installation, tell the AI Agent:

```
generate wiki
create project docs
update wiki
```

### Plugin Commands

```
list plugins
install plugin <path/url>
enable plugin <name>
disable plugin <name>
```

## Output Structure

All content is generated to `.mini-wiki/` directory:

```
.mini-wiki/
├── config.yaml              # Configuration
├── cache/                   # Incremental cache
├── wiki/                    # Wiki content
│   ├── index.md
│   ├── architecture.md
│   ├── modules/
│   └── api/
└── i18n/                    # Multi-language
    ├── en/
    └── zh/
```

## Skill Structure

```
mini-wiki/
├── SKILL.md           # Main instructions (English)
├── scripts/           # Python scripts
├── references/        # Prompts, templates, Chinese docs
├── assets/            # Config template
└── plugins/           # Plugin directory
    ├── _registry.yaml
    └── _example/
```

## Related Projects

- [DeepWiki](https://github.com/AsyncFuncAI/deepwiki-open)
- [OpenRepoWiki](https://github.com/daeisbae/open-repo-wiki)
- [Qoder](https://docs.qoder.com/user-guide/repo-wiki)

## License

MIT

## Author

- WeChat: trsoliu
- QR Code:

![WeChat QR](assets/wechat-qr.png)
