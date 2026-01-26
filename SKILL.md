---
name: wiki-generator
description: |
  Automatically generate structured project Wiki from documentation, code, design files, and images.
  
  Use when:
  - User requests "generate wiki", "create docs", "create documentation"
  - User requests "update wiki", "rebuild wiki"
  - User requests "list plugins", "install plugin", "manage plugins"
  - Project needs automated documentation generation
  
  Features:
  - Smart project structure and tech stack analysis
  - Incremental updates (only changed files)
  - Auto-generate Mermaid architecture diagrams
  - Code blocks link to source files
  - Multi-language support (zh/en)
  - **Plugin system for plugins**
  
  For Chinese instructions, see references/SKILL.zh.md
---

# Wiki Generator

Generate structured project Wiki to `.mini-wiki/` directory.

## Output Structure

```
.mini-wiki/
├── config.yaml              # Configuration
├── meta.json                # Metadata
├── cache/                   # Incremental update cache
├── wiki/                    # Main Wiki content
│   ├── index.md
│   ├── architecture.md
│   ├── getting-started.md
│   ├── modules/
│   ├── api/
│   └── assets/
└── i18n/                    # Multi-language versions
    ├── en/
    └── zh/
```

## Workflow

### 1. Initialization Check

Check if `.mini-wiki/` exists:
- **Not exists**: Run `scripts/init_wiki.py` to create directory structure
- **Exists**: Read `config.yaml` and cache, perform incremental update

### 2. Plugin Discovery

Check `plugins/` directory for installed plugins:
1. Read `plugins/_registry.yaml` for enabled plugins
2. For each enabled plugin, read `PLUGIN.md` manifest
3. Register hooks: `on_init`, `after_analyze`, `before_generate`, `after_generate`

### 3. Project Analysis

Run `scripts/analyze_project.py` or analyze manually:

1. **Identify tech stack**: Check package.json, requirements.txt, etc.
2. **Find entry points**: src/index.ts, main.py, etc.
3. **Identify modules**: Scan src/ directory structure
4. **Find existing docs**: README.md, CHANGELOG.md, etc.
5. **Execute `after_analyze` hooks** from plugins

Save structure to `cache/structure.json`.

### 4. Change Detection

Run `scripts/detect_changes.py` to compare file checksums:
- New files → Generate docs
- Modified files → Update docs
- Deleted files → Mark obsolete

### 5. Content Generation

Execute `before_generate` hooks from plugins, then:

1. **Homepage**: Project overview, navigation, statistics
2. **Architecture doc**: Mermaid diagrams, tech stack, module descriptions
3. **Module docs**: Overview, public interfaces, usage examples
4. **API docs**: Function signatures, parameters, returns, code links

Execute `after_generate` hooks from plugins.

### 6. Source Code Links

Add source links to code blocks:
```markdown
### `functionName` [📄](file:///path/to/file.ts#L42)
```

### 7. Save

- Write wiki files to `.mini-wiki/wiki/`
- Update `cache/checksums.json`
- Update `meta.json` timestamp

## Plugin System

### Plugin Commands

| Command | Usage |
|---------|-------|
| `list plugins` | Show installed plugins |
| `install plugin <path/url>` | Install from path or URL |
| `enable plugin <name>` | Enable plugin |
| `disable plugin <name>` | Disable plugin |
| `uninstall plugin <name>` | Remove plugin |

### Plugin Script

```bash
python scripts/plugin_manager.py list
python scripts/plugin_manager.py install <source>
python scripts/plugin_manager.py enable <name>
python scripts/plugin_manager.py disable <name>
```

### Creating Plugins

See `references/plugin-template.md` for plugin format.

Plugins support hooks:
- `on_init` - Run on initialization
- `after_analyze` - Add analysis data
- `before_generate` - Modify prompts
- `after_generate` - Post-process output
- `on_export` - Convert formats

## Scripts Reference

| Script | Usage |
|--------|-------|
| `scripts/init_wiki.py <path>` | Initialize .mini-wiki directory |
| `scripts/analyze_project.py <path>` | Analyze project structure |
| `scripts/detect_changes.py <path>` | Detect file changes |
| `scripts/generate_diagram.py <wiki-dir>` | Generate Mermaid diagrams |
| `scripts/extract_docs.py <file>` | Extract code comments |
| `scripts/generate_toc.py <wiki-dir>` | Generate table of contents |
| `scripts/plugin_manager.py <cmd>` | Manage plugins |

## References

See `references/` directory for detailed templates and prompts:
- **[prompts.md](references/prompts.md)**: AI prompt templates
- **[templates.md](references/templates.md)**: Wiki page templates
- **[plugin-template.md](references/plugin-template.md)**: Plugin format

## Configuration

`.mini-wiki/config.yaml` format:

```yaml
generation:
  language: en          # zh / en / both
  include_diagrams: true
  include_examples: true
  link_to_source: true

exclude:
  - node_modules
  - dist
  - "*.test.ts"
```

