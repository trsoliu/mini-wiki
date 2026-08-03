# Mini-Wiki P0 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reliable v3 Mini-Wiki loop: repository scanning, a stable knowledge graph, a versionable `wiki/` Vault, deterministic managed documents, validation, migration, and safe instruction-only plugin installation.

**Architecture:** Keep the installed CLI and legacy top-level modules, and add a focused `mini_wiki_core` package under `scripts/`. Existing commands delegate path, scan, graph, and Vault behavior to that package so there is one source of truth. All writes stage first and use a rollback journal before updating the Vault and Manifest.

**Tech Stack:** Python 3.10-3.12, Click, PyYAML, PathSpec, pytest, Ruff, Mypy.

## Global Constraints

- The default durable Vault is exactly `wiki/`; `.mini-wiki/` contains only config, cache, staging, archive, and manifests.
- Markdown is canonical; every cache and index is rebuildable.
- Obsidian is optional and must not be required by `init`, `build`, `check`, or `doctor`.
- Generated artifacts must not contain absolute user paths or `file://` URLs.
- A normal build may replace only managed frontmatter fields and `mini-wiki:generated` regions; `mini-wiki:content` is preserved byte-for-byte.
- Existing `.mini-wiki/wiki/` projects remain readable and are migrated only by an explicit, recoverable command.
- Plugins are instruction-only; Mini-Wiki and the host Agent must never execute plugin-provided scripts.
- No production behavior is added before its failing test has been observed.
- Preserve the untracked `docs/wechat-publish-notes.md` and `tmp/` paths.

---

## File Map

| File | Responsibility |
|---|---|
| `scripts/mini_wiki_core/config.py` | v3 config, defaults, safe project-relative paths, legacy resolution |
| `scripts/mini_wiki_core/models.py` | immutable source, node, edge, graph, manifest, result models |
| `scripts/mini_wiki_core/scanner.py` | shared excludes, Git ignore rules, source hashing |
| `scripts/mini_wiki_core/source_analysis.py` | language-aware symbol and import extraction without executing source |
| `scripts/mini_wiki_core/graph.py` | stable IDs and deterministic project/domain/module/source/document graph |
| `scripts/mini_wiki_core/vault.py` | frontmatter, managed regions, portable links, staged writes |
| `scripts/mini_wiki_core/builder.py` | build orchestration, dry run, manifest, transaction rollback |
| `scripts/mini_wiki_core/validation.py` | duplicate IDs, links, source references, freshness, orphan checks |
| `scripts/mini_wiki_core/doctor.py` | actionable environment and project diagnostics |
| `scripts/mini_wiki_core/migration.py` | previewable and recoverable v2-to-v3 migration |
| `scripts/mini_wiki_core/plugin_security.py` | bounded download, safe ZIP extraction, manifest validation |
| `scripts/init_wiki.py` | legacy public initializer delegating to v3 config/layout |
| `scripts/analyze_project.py` | consume shared exclusions and exclude `.agents/` |
| `scripts/detect_changes.py` | consume shared scan policy and v3 manifest |
| `scripts/check_quality.py` | accept either a state directory or resolved Vault path |
| `scripts/plugin_manager.py` | use secure staging and default-disable third-party installs |
| `scripts/cli.py` | expose `build`, strict `check`, `doctor`, and `migrate` |
| `pyproject.toml` | package `mini_wiki_core`, add PathSpec, keep CLI entry point |

### Task 1: v3 configuration and initialization

**Files:**
- Create: `scripts/mini_wiki_core/__init__.py`
- Create: `scripts/mini_wiki_core/config.py`
- Modify: `scripts/init_wiki.py`
- Modify: `pyproject.toml`
- Modify: `tests/conftest.py`
- Test: `tests/test_core_config.py`
- Test: `tests/test_init_wiki.py`

**Interfaces:**
- Produces: `WikiConfig`, `default_config_data()`, `load_config(project_root)`, `resolve_project_path(root, value)`.
- Produces: `init_mini_wiki(project_root, force=False)` creating `.mini-wiki/` and root `wiki/`.

- [ ] **Step 1: Write the failing config and initializer tests**

```python
from pathlib import Path

import pytest
import yaml

from init_wiki import init_mini_wiki
from mini_wiki_core.config import ConfigError, load_config, resolve_project_path


def test_init_creates_v3_state_and_root_vault(tmp_path: Path):
    result = init_mini_wiki(str(tmp_path))
    config = yaml.safe_load((tmp_path / ".mini-wiki/config.yaml").read_text())
    assert result["success"] is True
    assert config["schema_version"] == 3
    assert config["vault"]["path"] == "wiki"
    assert (tmp_path / "wiki/domains").is_dir()
    assert not (tmp_path / ".mini-wiki/wiki").exists()


def test_load_config_uses_legacy_vault_without_silent_migration(tmp_path: Path):
    (tmp_path / ".mini-wiki/wiki").mkdir(parents=True)
    (tmp_path / ".mini-wiki/config.yaml").write_text("generation:\n  language: zh\n")
    config = load_config(tmp_path)
    assert config.compatibility_mode is True
    assert config.vault_dir == tmp_path / ".mini-wiki/wiki"


def test_resolve_project_path_rejects_escape(tmp_path: Path):
    with pytest.raises(ConfigError, match="outside project root"):
        resolve_project_path(tmp_path, "../private")


@pytest.fixture
def v3_project(tmp_path: Path) -> Path:
    result = init_mini_wiki(str(tmp_path))
    assert result["success"] is True
    source = tmp_path / "src/core/app.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run():\n    return 'ok'\n")
    return tmp_path
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_config.py tests/test_init_wiki.py -q`

Expected: collection fails because `mini_wiki_core.config` does not exist, then after the empty package exists the assertions fail because initialization still creates `.mini-wiki/wiki`.

- [ ] **Step 3: Implement the minimal v3 config API and initializer delegation**

```python
@dataclass(frozen=True)
class WikiConfig:
    project_root: Path
    state_dir: Path
    vault_dir: Path
    compatibility_mode: bool
    link_style: str
    source_links: str
    preserve_manual_content: bool
    language: str
    include_diagrams: bool
    include_examples: bool
    max_file_size: int
    respect_gitignore: bool
    excludes: tuple[str, ...]
    search_enabled: bool
    bases_enabled: bool
    canvas_enabled: bool
    canvas_max_nodes: int
    obsidian_integration: str


def resolve_project_path(root: Path, value: str) -> Path:
    root = root.resolve()
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise ConfigError(f"Path is outside project root: {value}")
    return candidate


def load_config(project_root: str | Path) -> WikiConfig:
    root = Path(project_root).resolve()
    state = root / ".mini-wiki"
    raw = yaml.safe_load((state / "config.yaml").read_text()) or {}
    legacy = int(raw.get("schema_version", 0)) < 3 and (state / "wiki").exists()
    vault = raw.get("vault", {})
    generation = raw.get("generation", {})
    scan = raw.get("scan", {})
    custom_excludes = tuple(scan.get("exclude", raw.get("exclude", ())))
    vault_value = vault.get("path", ".mini-wiki/wiki" if legacy else "wiki")
    return WikiConfig(
        project_root=root,
        state_dir=state,
        vault_dir=resolve_project_path(root, vault_value),
        compatibility_mode=legacy,
        link_style=vault.get("link_style", "wikilink"),
        source_links=vault.get("source_links", "relative-markdown"),
        preserve_manual_content=bool(vault.get("preserve_manual_content", True)),
        language=str(generation.get("language", "zh")),
        include_diagrams=bool(generation.get("include_diagrams", True)),
        include_examples=bool(generation.get("include_examples", True)),
        max_file_size=int(generation.get("max_file_size", 100_000)),
        respect_gitignore=bool(scan.get("respect_gitignore", True)),
        excludes=tuple(dict.fromkeys((*DEFAULT_EXCLUDES, *custom_excludes))),
        search_enabled=bool(raw.get("search", {}).get("enabled", True)),
        bases_enabled=bool(raw.get("bases", {}).get("enabled", True)),
        canvas_enabled=bool(raw.get("canvas", {}).get("enabled", True)),
        canvas_max_nodes=int(raw.get("canvas", {}).get("max_nodes", 200)),
        obsidian_integration=str(raw.get("obsidian", {}).get("integration", "auto")),
    )
```

Add `pathspec>=0.12` to project dependencies, add `mini_wiki_core*` to setuptools package discovery, and change the initializer directory list to `.mini-wiki/cache`, `.mini-wiki/staging`, `.mini-wiki/archive`, `wiki/domains`, `wiki/reference/api`, `wiki/reference/source`, `wiki/views`, `wiki/canvas`, and `wiki/assets`.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_core_config.py tests/test_init_wiki.py -q`

Expected: all focused tests pass, including updated legacy initializer assertions.

- [ ] **Step 5: Commit Task 1**

```bash
git add pyproject.toml scripts/init_wiki.py scripts/mini_wiki_core tests/test_core_config.py tests/test_init_wiki.py
git commit -m "feat: add v3 Vault configuration"
```

### Task 2: shared scanner and stable knowledge graph

**Files:**
- Create: `scripts/mini_wiki_core/models.py`
- Create: `scripts/mini_wiki_core/scanner.py`
- Create: `scripts/mini_wiki_core/source_analysis.py`
- Create: `scripts/mini_wiki_core/graph.py`
- Modify: `scripts/analyze_project.py`
- Modify: `scripts/detect_changes.py`
- Test: `tests/test_core_scanner.py`
- Test: `tests/test_core_source_analysis.py`
- Test: `tests/test_core_graph.py`
- Test: `tests/test_analyze_project.py`
- Test: `tests/test_detect_changes.py`

**Interfaces:**
- Consumes: `WikiConfig` from Task 1.
- Produces: `SourceFile`, `SourceAnalysis`, `Node`, `Edge`, `KnowledgeGraph`, `scan_sources(config)`, `analyze_source(root, source)`, `build_knowledge_graph(config, sources)`.

- [ ] **Step 1: Write failing boundary and graph tests**

```python
def test_scan_excludes_agent_and_gitignored_content(v3_project):
    (v3_project / ".agents/skills/vendor").mkdir(parents=True, exist_ok=True)
    (v3_project / ".agents/skills/vendor/tool.py").write_text("pass")
    (v3_project / ".gitignore").write_text("generated/\n")
    (v3_project / "generated/secret.py").parent.mkdir()
    (v3_project / "generated/secret.py").write_text("pass")
    (v3_project / "wiki/generated.py").parent.mkdir(exist_ok=True)
    (v3_project / "wiki/generated.py").write_text("pass")
    (v3_project / "src/app.py").parent.mkdir()
    (v3_project / "src/app.py").write_text("def run():\n    return 1\n")
    paths = [item.path.as_posix() for item in scan_sources(load_config(v3_project))]
    assert paths == ["src/app.py"]


def test_graph_ids_and_order_are_stable(v3_project):
    config = load_config(v3_project)
    sources = [
        SourceFile(Path("src/z.py"), "sha256:z", "python", 1),
        SourceFile(Path("src/a.py"), "sha256:a", "python", 1),
    ]
    first = build_knowledge_graph(config, sources).to_dict()
    second = build_knowledge_graph(config, list(reversed(sources))).to_dict()
    assert first == second
    assert "mw:source:src/a.py" in first["nodes"]
    assert any(edge["type"] == "documents" for edge in first["edges"])


def test_python_symbols_and_internal_dependencies_become_graph_edges(v3_project):
    (v3_project / "src/core/a.py").write_text("from src.core import b\n\ndef install_plugin():\n    return b.VALUE\n")
    (v3_project / "src/core/b.py").write_text("VALUE = 1\n")
    config = load_config(v3_project)
    graph = build_knowledge_graph(config, scan_sources(config))
    assert "mw:symbol:src/core/a.py#install_plugin" in graph.nodes
    assert Edge("mw:symbol:src/core/a.py#install_plugin", "mw:source:src/core/a.py", "defined_in") in graph.edges
    assert Edge("mw:source:src/core/a.py", "mw:source:src/core/b.py", "depends_on") in graph.edges
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_scanner.py tests/test_core_graph.py -q`

Expected: imports fail because scanner, source-analysis, models, and graph modules do not exist.

- [ ] **Step 3: Implement immutable models, shared scanning, and deterministic graph creation**

```python
@dataclass(frozen=True)
class SourceFile:
    path: Path
    sha256: str
    language: str
    size: int


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    title: str
    path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, order=True)
class Edge:
    source_id: str
    target_id: str
    type: str


@dataclass
class KnowledgeGraph:
    nodes: dict[str, Node]
    edges: list[Edge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {key: asdict(self.nodes[key]) for key in sorted(self.nodes)},
            "edges": [asdict(edge) for edge in sorted(self.edges)],
        }


@dataclass(frozen=True)
class SourceAnalysis:
    symbols: tuple[str, ...]
    imports: tuple[str, ...]


def analyze_source(root: Path, source: SourceFile) -> SourceAnalysis:
    text = (root / source.path).read_text(encoding="utf-8", errors="replace")
    if source.path.suffix == ".py":
        tree = ast.parse(text)
        symbols = tuple(sorted(node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))))
        imports = tuple(sorted({alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}))
        return SourceAnalysis(symbols, imports)
    symbol_pattern = re.compile(r"(?:export\s+)?(?:async\s+)?(?:function|class|interface|type|func)\s+([A-Za-z_$][\w$]*)")
    imports = set(re.findall(r"from\s+[\"']([^\"']+)[\"']", text))
    imports.update(re.findall(r"require\(\s*[\"']([^\"']+)[\"']\s*\)", text))
    if source.path.suffix == ".go":
        imports.update(re.findall(r"^[ \t]*[\"']([^\"']+)[\"']", text, re.MULTILINE))
    return SourceAnalysis(tuple(sorted(set(symbol_pattern.findall(text)))), tuple(sorted(imports)))
```

Use `PathSpec.from_lines("gitwildmatch", ...)` for `.gitignore`, always exclude the resolved state and Vault directories, reject symlinks or resolved paths outside the project, reject files over `max_file_size`, reject any path whose parts contain shared excluded directory names, hash bytes with SHA-256, and sort by POSIX repository-relative path. Build project, domain, module, source, symbol, and document nodes with `mw:<kind>:<normalized-key>` IDs. Parse source text only; never import or execute it. A syntax error keeps the source node and becomes a graph warning rather than aborting the build. Resolve only repository-local imports into `depends_on` edges and retain unresolved/external imports as metadata. Make `analyze_project` and `detect_changes` import the shared default exclusions so `.agents/` cannot re-enter through legacy commands.

- [ ] **Step 4: Run graph, legacy analyzer, and change tests**

Run: `.venv/bin/python -m pytest tests/test_core_scanner.py tests/test_core_source_analysis.py tests/test_core_graph.py tests/test_analyze_project.py tests/test_detect_changes.py -q`

Expected: all selected tests pass and `.agents/` regression tests report no scanned files.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/mini_wiki_core scripts/analyze_project.py scripts/detect_changes.py tests/test_core_scanner.py tests/test_core_source_analysis.py tests/test_core_graph.py tests/test_analyze_project.py tests/test_detect_changes.py
git commit -m "feat: build a stable repository knowledge graph"
```

### Task 3: Obsidian-compatible managed Markdown

**Files:**
- Create: `scripts/mini_wiki_core/vault.py`
- Test: `tests/test_core_vault.py`

**Interfaces:**
- Consumes: `WikiConfig`, `KnowledgeGraph`, `Node`, `SourceFile`.
- Produces: `render_document(node, graph, existing_text)`, `merge_managed_document(existing, generated)`, `relative_source_link(document_path, source_path, lines)`.

- [ ] **Step 1: Write failing managed-content and path tests**

```python
def test_rendered_document_has_flat_properties_and_no_private_path(v3_project):
    module_node = Node("mw:module:core", "module", "Core", "wiki/domains/core/core.md")
    graph = KnowledgeGraph({module_node.id: module_node}, [])
    text = render_document(module_node, graph, None)
    frontmatter = yaml.safe_load(text.split("---", 2)[1])
    assert frontmatter["id"] == module_node.id
    assert frontmatter["orphan"] is False
    assert isinstance(frontmatter["sources"], list)
    assert str(v3_project) not in text
    assert "file://" not in text


def test_rebuild_preserves_agent_content_byte_for_byte():
    existing = """---\nid: old\n---\n<!-- mini-wiki:generated:start -->\nold\n<!-- mini-wiki:generated:end -->\n<!-- mini-wiki:content:start -->\n## 手工说明\n保留  两个空格\n<!-- mini-wiki:content:end -->\n"""
    generated = """---\nid: new\n---\n<!-- mini-wiki:generated:start -->\nnew\n<!-- mini-wiki:generated:end -->\n<!-- mini-wiki:content:start -->\ngenerated placeholder\n<!-- mini-wiki:content:end -->\n"""
    merged = merge_managed_document(existing, generated)
    assert "## 手工说明\n保留  两个空格\n" in merged
    assert "\nnew\n" in merged


def test_source_link_is_relative_to_nested_document():
    link = relative_source_link(
        Path("wiki/domains/core/plugin-system.md"),
        Path("scripts/plugin_manager.py"),
        (42, 88),
    )
    assert link == "[scripts/plugin_manager.py:42-88](../../../scripts/plugin_manager.py#L42-L88)"
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_vault.py -q`

Expected: import failure because `mini_wiki_core.vault` does not exist.

- [ ] **Step 3: Implement deterministic frontmatter, managed regions, and relative links**

```python
GENERATED_START = "<!-- mini-wiki:generated:start -->"
GENERATED_END = "<!-- mini-wiki:generated:end -->"
CONTENT_START = "<!-- mini-wiki:content:start -->"
CONTENT_END = "<!-- mini-wiki:content:end -->"


def relative_source_link(document_path: Path, source_path: Path, lines: tuple[int, int] | None) -> str:
    relative = Path(os.path.relpath(source_path, document_path.parent)).as_posix()
    label = source_path.as_posix()
    suffix = ""
    if lines:
        start, end = lines
        label = f"{label}:{start}-{end}"
        suffix = f"#L{start}-L{end}"
    return f"[{label}]({relative}{suffix})"


def merge_managed_document(existing: str | None, generated: str) -> str:
    if not existing or CONTENT_START not in existing or CONTENT_END not in existing:
        return generated if not existing else existing
    content = existing.split(CONTENT_START, 1)[1].split(CONTENT_END, 1)[0]
    before, after = generated.split(CONTENT_START, 1)
    _, tail = after.split(CONTENT_END, 1)
    return before + CONTENT_START + content + CONTENT_END + tail
```

Serialize properties in a fixed field order, sort lists, exclude timestamps, and render internal links from graph IDs. Existing unmarked Markdown returns unchanged and is reported as unmanaged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_core_vault.py -q`

Expected: all Vault tests pass, including exact manual-content preservation.

- [ ] **Step 5: Commit Task 3**

```bash
git add scripts/mini_wiki_core/vault.py tests/test_core_vault.py
git commit -m "feat: render managed Obsidian Markdown"
```

### Task 4: deterministic build transaction and Manifest

**Files:**
- Create: `scripts/mini_wiki_core/builder.py`
- Modify: `scripts/cli.py`
- Modify: `scripts/detect_changes.py`
- Test: `tests/test_core_builder.py`
- Test: `tests/test_cli.py`
- Modify: `tests/test_detect_changes.py`

**Interfaces:**
- Consumes: configuration, scanner, graph, and Vault renderer from Tasks 1-3.
- Produces: `BuildOptions`, `BuildResult`, `FileTransaction`, `build_project(project_root, options)` and CLI `build`.

- [ ] **Step 1: Write failing idempotence, dry-run, and rollback tests**

```python
def test_two_builds_are_byte_identical(v3_project):
    first = build_project(v3_project, BuildOptions())
    snapshot = {p.relative_to(v3_project): p.read_bytes() for p in (v3_project / "wiki").rglob("*") if p.is_file()}
    second = build_project(v3_project, BuildOptions())
    assert first.success is True
    assert second.changed == []
    assert snapshot == {p.relative_to(v3_project): p.read_bytes() for p in (v3_project / "wiki").rglob("*") if p.is_file()}


def test_build_writes_graph_and_agent_plan_caches(v3_project):
    build_project(v3_project, BuildOptions())
    analysis = json.loads((v3_project / ".mini-wiki/cache/analysis.json").read_text())
    graph = json.loads((v3_project / ".mini-wiki/cache/graph.json").read_text())
    plan = json.loads((v3_project / ".mini-wiki/cache/build-plan.json").read_text())
    assert "analyzed_at" not in analysis
    assert graph["nodes"]
    assert plan["documents"]
    assert all(not Path(item["path"]).is_absolute() for item in plan["documents"])


def test_removed_source_archives_its_managed_document(v3_project):
    source = v3_project / "src/legacy.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("def old():\n    return 1\n")
    build_project(v3_project, BuildOptions())
    source.unlink()
    result = build_project(v3_project, BuildOptions())
    assert result.archived
    assert list((v3_project / ".mini-wiki/archive").rglob("legacy.md"))


def test_changes_uses_manifest_after_build(v3_project):
    build_project(v3_project, BuildOptions())
    assert detect_changes(str(v3_project))["has_changes"] is False
    (v3_project / "src/core/app.py").write_text("def run():\n    return 'changed'\n")
    changes = detect_changes(str(v3_project))
    assert changes["modified"] == ["src/core/app.py"]


def test_dry_run_does_not_write_vault(v3_project):
    result = build_project(v3_project, BuildOptions(dry_run=True))
    assert result.success is True
    assert result.created
    assert list((v3_project / "wiki").rglob("*.md")) == []


def test_transaction_restores_files_when_replace_fails(tmp_path, monkeypatch):
    target = tmp_path / "wiki/index.md"
    target.parent.mkdir(parents=True)
    target.write_text("before")
    tx = FileTransaction(tmp_path, tmp_path / ".mini-wiki")
    tx.stage_text(Path("wiki/index.md"), "after")
    real_replace = tx._replace
    calls = 0

    def flaky_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        return real_replace(source, destination)

    monkeypatch.setattr(tx, "_replace", flaky_replace)
    with pytest.raises(TransactionError):
        tx.commit()
    assert target.read_text() == "before"
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_builder.py tests/test_cli.py::test_build -q`

Expected: imports or CLI lookup fail because builder and `build` command do not exist.

- [ ] **Step 3: Implement staged artifacts, rollback journal, and deterministic Manifest**

```python
@dataclass(frozen=True)
class BuildOptions:
    full: bool = False
    dry_run: bool = False


@dataclass
class BuildResult:
    success: bool
    created: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> list[str]:
        return sorted(self.created + self.modified + self.archived)


def build_project(project_root: str | Path, options: BuildOptions) -> BuildResult:
    config = load_config(project_root)
    analysis = analyze_project(str(config.project_root), save_to_cache=False)
    analysis.pop("analyzed_at", None)
    sources = scan_sources(config)
    graph = build_knowledge_graph(config, sources)
    artifacts = render_vault_artifacts(config, graph)
    manifest = build_manifest(config, graph, artifacts)
    transaction = FileTransaction(config.project_root, config.state_dir)
    for path, content in sorted(artifacts.items()):
        transaction.stage_text(path, content)
    transaction.stage_json(Path(".mini-wiki/cache/analysis.json"), analysis)
    transaction.stage_json(Path(".mini-wiki/cache/graph.json"), graph.to_dict())
    transaction.stage_json(Path(".mini-wiki/cache/build-plan.json"), build_agent_plan(graph, manifest))
    transaction.stage_json(Path(".mini-wiki/manifest.json"), manifest.to_dict())
    return transaction.preview() if options.dry_run else transaction.commit()
```

Use `tempfile.mkdtemp(dir=state/staging)`, content hashes rather than mtimes, sorted UTF-8 JSON, backup-before-replace, and reverse-order rollback. Compare the prior Manifest with the new graph: move only stale Mini-Wiki-managed documents to the run archive, and never archive an unmarked user document. The Agent plan lists each document ID, repository-relative path, sources, status, and required content action. Make v3 `detect_changes` compare current scan hashes with Manifest source records while retaining the old checksum-cache reader in compatibility mode. Add Click flags `--full`, `--dry-run`, and `--json`; JSON must contain `success`, `created`, `modified`, `archived`, `warnings`, and `errors`.

- [ ] **Step 4: Run builder and CLI tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_core_builder.py tests/test_detect_changes.py tests/test_cli.py -q`

Expected: build tests pass and existing CLI commands retain their prior behavior.

- [ ] **Step 5: Commit Task 4**

```bash
git add scripts/mini_wiki_core/builder.py scripts/detect_changes.py scripts/cli.py tests/test_core_builder.py tests/test_detect_changes.py tests/test_cli.py
git commit -m "feat: add deterministic Mini-Wiki builds"
```

### Task 5: strict validation and doctor

**Files:**
- Create: `scripts/mini_wiki_core/validation.py`
- Create: `scripts/mini_wiki_core/doctor.py`
- Modify: `scripts/check_quality.py`
- Modify: `scripts/cli.py`
- Test: `tests/test_core_validation.py`
- Test: `tests/test_core_doctor.py`
- Test: `tests/test_check_quality.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `ValidationIssue`, `ValidationReport`, `validate_vault(config, graph=None)`, `DoctorFinding`, `doctor_project(project_root)`.
- CLI: `check --strict --json` and `doctor --json`.

- [ ] **Step 1: Write failing structural validation and CLI exit-code tests**

```python
def write_managed_doc(path: Path, node_id: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {node_id}\ntitle: Test\ntype: module\n---\n"
        f"<!-- mini-wiki:generated:start -->\n{body}\n<!-- mini-wiki:generated:end -->\n"
        "<!-- mini-wiki:content:start -->\ncontent\n<!-- mini-wiki:content:end -->\n"
    )


def test_validation_reports_duplicate_id_missing_link_and_orphan(v3_project):
    write_managed_doc(v3_project / "wiki/a.md", "mw:document:a", "[[missing]]")
    write_managed_doc(v3_project / "wiki/b.md", "mw:document:a", "no links")
    report = validate_vault(load_config(v3_project))
    assert {issue.code for issue in report.issues} >= {
        "DUPLICATE_ID",
        "LINK_TARGET_MISSING",
        "ORPHAN_MANAGED_DOCUMENT",
    }


def test_check_strict_returns_nonzero_for_broken_network(v3_project):
    write_managed_doc(v3_project / "wiki/broken.md", "mw:document:broken", "[[missing]]")
    result = runner.invoke(main, ["check", "--strict", str(v3_project)])
    assert result.exit_code == 1
    assert "LINK_TARGET_MISSING" in result.output


def test_quality_checker_accepts_resolved_vault_path(v3_project):
    (v3_project / "wiki/index.md").write_text("# Index\n")
    report = check_wiki_quality(str(v3_project / "wiki"))
    assert report.total_docs == 1
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_validation.py tests/test_core_doctor.py tests/test_check_quality.py tests/test_cli.py -q`

Expected: new module imports fail and the quality-path regression reports zero documents.

- [ ] **Step 3: Implement validation, doctor, and corrected quality path resolution**

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    path: str
    message: str


@dataclass
class ValidationReport:
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return not any(item.severity == "error" for item in self.issues)


def resolve_quality_directory(path: str | Path) -> Path:
    candidate = Path(path)
    nested = candidate / "wiki"
    return nested if nested.is_dir() else candidate
```

Parse frontmatter with `yaml.safe_load`, resolve Wikilinks and Markdown links inside the Vault, exempt `index.md` and `_index.md` from orphan errors, treat uncovered source as a warning, verify source paths remain inside the project, compare Manifest source hashes, and validate managed-region pairing. Doctor must report missing initialization, ignored `wiki/`, legacy mode, stale/missing Manifest, absent FTS5 as warning, and Obsidian absence as informational only.

- [ ] **Step 4: Run validation, quality, doctor, and CLI tests**

Run: `.venv/bin/python -m pytest tests/test_core_validation.py tests/test_core_doctor.py tests/test_check_quality.py tests/test_cli.py -q`

Expected: all selected tests pass; strict structural errors return exit code 1 and normal quality reports still render.

- [ ] **Step 5: Commit Task 5**

```bash
git add scripts/mini_wiki_core/validation.py scripts/mini_wiki_core/doctor.py scripts/check_quality.py scripts/cli.py tests/test_core_validation.py tests/test_core_doctor.py tests/test_check_quality.py tests/test_cli.py
git commit -m "feat: validate Mini-Wiki knowledge networks"
```

### Task 6: explicit recoverable migration

**Files:**
- Create: `scripts/mini_wiki_core/migration.py`
- Modify: `scripts/cli.py`
- Test: `tests/test_core_migration.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `MigrationPlan`, `plan_migration(project_root)`, `apply_migration(plan)`.
- CLI: `migrate` previews by default; `migrate --apply [--adopt] --json` performs a copy-and-backup migration. `--adopt` adds managed regions without changing legacy body bytes.

- [ ] **Step 1: Write failing preview, apply, and collision tests**

```python
@pytest.fixture
def v2_project(tmp_path: Path) -> Path:
    vault = tmp_path / ".mini-wiki/wiki"
    vault.mkdir(parents=True)
    (vault / "index.md").write_text("# Legacy\n")
    (tmp_path / ".mini-wiki/config.yaml").write_text("generation:\n  language: zh\n")
    return tmp_path


def test_migration_preview_has_no_writes(v2_project):
    plan = plan_migration(v2_project)
    assert plan.applicable is True
    assert plan.source == v2_project / ".mini-wiki/wiki"
    assert plan.destination == v2_project / "wiki"
    assert not plan.destination.exists()


def test_migration_copies_and_keeps_legacy_vault(v2_project):
    plan = plan_migration(v2_project)
    result = apply_migration(plan)
    assert result.success is True
    assert (v2_project / "wiki/index.md").read_text() == "# Legacy\n"
    assert (v2_project / ".mini-wiki/wiki/index.md").exists()
    assert list((v2_project / ".mini-wiki/archive").glob("*/v2-backup/wiki/index.md"))


def test_migration_refuses_nonempty_destination(v2_project):
    (v2_project / "wiki").mkdir()
    (v2_project / "wiki/private.md").write_text("private")
    with pytest.raises(MigrationError, match="not empty"):
        apply_migration(plan_migration(v2_project))


def test_migration_adopt_wraps_legacy_body_without_changing_it(v2_project):
    before = (v2_project / ".mini-wiki/wiki/index.md").read_text()
    result = apply_migration(plan_migration(v2_project), adopt=True)
    migrated = (v2_project / "wiki/index.md").read_text()
    assert result.success is True
    assert before in migrated
    assert "<!-- mini-wiki:content:start -->" in migrated
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_migration.py -q`

Expected: import failure because migration module does not exist.

- [ ] **Step 3: Implement copy-only migration with backup and v3 config rewrite**

```python
@dataclass(frozen=True)
class MigrationPlan:
    project_root: Path
    source: Path
    destination: Path
    applicable: bool
    reasons: tuple[str, ...]


def plan_migration(project_root: str | Path) -> MigrationPlan:
    root = Path(project_root).resolve()
    source = root / ".mini-wiki/wiki"
    destination = root / "wiki"
    return MigrationPlan(root, source, destination, source.is_dir(), ("legacy-v2-vault",) if source.is_dir() else ())
```

Use `shutil.copytree` only after target validation, create a timestamped archive with the old config and Vault, never delete the source, write v3 config atomically, preserve unmarked Markdown by default, and return repository-relative paths. With `adopt=True`, place the complete legacy body inside the content region and generate a managed frontmatter/relationship region around it; never parse and reserialize the legacy body. Re-running against a completed v3 project returns a no-op plan.

- [ ] **Step 4: Run migration and CLI tests**

Run: `.venv/bin/python -m pytest tests/test_core_migration.py tests/test_cli.py -q`

Expected: preview is read-only, apply preserves both copies and backup, collisions fail without modifying either tree.

- [ ] **Step 5: Commit Task 6**

```bash
git add scripts/mini_wiki_core/migration.py scripts/cli.py tests/test_core_migration.py tests/test_cli.py
git commit -m "feat: add recoverable v3 migration"
```

### Task 7: secure instruction-only plugin installation

**Files:**
- Create: `scripts/mini_wiki_core/plugin_security.py`
- Modify: `scripts/plugin_manager.py`
- Test: `tests/test_plugin_security.py`
- Modify: `tests/test_plugin_manager.py`

**Interfaces:**
- Produces: `safe_extract_zip(archive, destination, max_uncompressed_bytes)`, `validate_instruction_plugin(path)`, `download_bounded(url, destination, max_bytes)`.
- Existing `install_plugin()` and `update_plugin()` consume the secure functions and preserve their dictionary result shape.

- [ ] **Step 1: Write failing malicious archive and default-disable tests**

```python
@pytest.fixture
def instruction_plugin(tmp_path: Path) -> Path:
    plugin = tmp_path / "source-plugin"
    plugin.mkdir()
    (plugin / "PLUGIN.md").write_text(
        "---\nname: source-plugin\ntype: analyzer\nversion: 1.0.0\n"
        "description: Test instructions\n---\n# Instructions\n"
    )
    return plugin


def test_safe_extract_rejects_parent_traversal(tmp_path):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("../../escaped.txt", "owned")
    with pytest.raises(PluginSecurityError, match="unsafe path"):
        safe_extract_zip(archive, tmp_path / "out", 1024)
    assert not (tmp_path / "escaped.txt").exists()


def test_safe_extract_rejects_uncompressed_limit(tmp_path):
    archive = tmp_path / "large.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("PLUGIN.md", "x" * 2048)
    with pytest.raises(PluginSecurityError, match="size limit"):
        safe_extract_zip(archive, tmp_path / "out", 1024)


def test_third_party_install_is_disabled_by_default(tmp_path, instruction_plugin):
    result = install_plugin(str(tmp_path), str(instruction_plugin))
    registry = load_registry(str(tmp_path))
    assert result["success"] is True
    assert registry["plugins"][0]["enabled"] is False
    assert "sha256" in registry["plugins"][0]
```

- [ ] **Step 2: Run security tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_plugin_security.py tests/test_plugin_manager.py -q`

Expected: security module import fails and current installer enables a third-party plugin.

- [ ] **Step 3: Implement bounded extraction and atomic plugin replacement**

```python
def safe_extract_zip(archive: Path, destination: Path, max_uncompressed_bytes: int) -> None:
    with ZipFile(archive) as zipped:
        total = sum(info.file_size for info in zipped.infolist())
        if total > max_uncompressed_bytes:
            raise PluginSecurityError("Plugin exceeds uncompressed size limit")
        for info in zipped.infolist():
            member = PurePosixPath(info.filename)
            mode = info.external_attr >> 16
            if member.is_absolute() or ".." in member.parts or stat.S_ISLNK(mode):
                raise PluginSecurityError(f"Plugin contains unsafe path: {info.filename}")
            target = destination.joinpath(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not info.is_dir():
                with zipped.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
```

Use `TemporaryDirectory` outside `plugins/`, enforce HTTPS for network installs, cap streamed bytes, validate `PLUGIN.md` frontmatter or standard `SKILL.md`, reject arbitrary README wrapping, reject overwrite unless an explicit update path is used, hash the validated tree, set new third-party registry entries to `enabled: false`, and restore the old directory if update replacement fails.

- [ ] **Step 4: Run all plugin tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_plugin_security.py tests/test_plugin_manager.py tests/test_cli.py -q`

Expected: traversal, symlink, and size attacks fail without escaped files; local valid instructions install disabled; built-in registry state remains unchanged.

- [ ] **Step 5: Commit Task 7**

```bash
git add scripts/mini_wiki_core/plugin_security.py scripts/plugin_manager.py tests/test_plugin_security.py tests/test_plugin_manager.py tests/test_cli.py
git commit -m "fix: harden instruction plugin installation"
```

### Task 8: P0 integrated acceptance

**Files:**
- Create: `tests/test_p0_workflow.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes every P0 public command and data contract.
- Produces an end-to-end regression proving the core loop without Obsidian.

- [ ] **Step 1: Write the failing end-to-end workflow test**

```python
def test_p0_init_build_check_doctor_and_rebuild(tmp_path):
    (tmp_path / "src/core/app.py").parent.mkdir(parents=True)
    (tmp_path / "src/core/app.py").write_text("def run():\n    return 'ok'\n")
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    first = runner.invoke(main, ["build", str(tmp_path)])
    assert first.exit_code == 0
    assert (tmp_path / "wiki/index.md").exists()
    assert (tmp_path / "wiki/views").is_dir()
    assert runner.invoke(main, ["check", "--strict", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["doctor", str(tmp_path)]).exit_code == 0
    second = runner.invoke(main, ["build", "--json", str(tmp_path)])
    assert second.exit_code == 0
    assert json.loads(second.output)["modified"] == []
```

- [ ] **Step 2: Run it and verify RED for the remaining integration gap**

Run: `.venv/bin/python -m pytest tests/test_p0_workflow.py -q`

Expected: fail on the first unintegrated assertion, not on fixture setup.

- [ ] **Step 3: Make only the integration corrections required by the failing assertion**

```yaml
- name: Run P0 workflow smoke test
  run: pytest tests/test_p0_workflow.py -v
```

Add the smoke step to CI and fix command wiring or artifact ordering exposed by the test. Do not add P1 or P2 behavior in this task.

- [ ] **Step 4: Run complete P0 verification**

Run: `.venv/bin/python -m pytest -q`

Run: `.venv/bin/python -m ruff check scripts tests`

Run: `.venv/bin/python -m ruff format --check scripts tests`

Run: `.venv/bin/python -m mypy scripts --ignore-missing-imports`

Run: `git diff --check`

Expected: every command exits 0 with no failures or formatting errors.

- [ ] **Step 5: Commit Task 8**

```bash
git add .github/workflows/ci.yml tests/test_p0_workflow.py
git commit -m "test: cover the P0 Mini-Wiki workflow"
```
