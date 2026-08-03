# Mini-Wiki P1 Search and Bases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add standalone Chinese-aware full-text search and native Obsidian Bases views backed by the P0 knowledge graph and document Properties.

**Architecture:** A rebuildable SQLite cache indexes the same Markdown and graph metadata emitted by P0. Search has an FTS5 implementation and a behaviorally compatible in-memory fallback. Bases are deterministic YAML artifacts generated from the same Property schema, not a second metadata model.

**Tech Stack:** Python sqlite3/FTS5, PyYAML, Click, pytest, Ruff, Mypy.

## Global Constraints

- Search data lives only at `.mini-wiki/cache/search.sqlite3` and never becomes canonical.
- Search must work without Obsidian and without FTS5, with explicit degradation reporting.
- Chinese and mixed Chinese-English queries use deterministic CJK unigram/bigram normalization.
- Bases use only Obsidian-supported YAML fields and query existing flat Properties.
- Search and Bases outputs are deterministic for identical graph, documents, and config.
- No production behavior is added before its failing test has been observed.

---

## File Map

| File | Responsibility |
|---|---|
| `scripts/mini_wiki_core/search.py` | normalization, FTS5 index, fallback ranking, filtered query |
| `scripts/mini_wiki_core/bases.py` | four deterministic `.base` documents and validation |
| `scripts/mini_wiki_core/builder.py` | stage search database and Base artifacts in the P0 transaction |
| `scripts/mini_wiki_core/validation.py` | Base schema validation |
| `scripts/mini_wiki_core/doctor.py` | report FTS5 capability and fallback state |
| `scripts/cli.py` | `search` command and JSON output |

### Task 1: Chinese-aware search normalization and index

**Files:**
- Create: `scripts/mini_wiki_core/search.py`
- Create: `tests/test_core_search.py`

**Interfaces:**
- Consumes P0 managed Markdown and graph nodes.
- Produces `SearchDocument`, `SearchHit`, `IndexUpdate`, `normalize_search_text(text)`, `SearchIndex.update(documents)`, and `SearchIndex.search(query, node_type=None, tag=None, limit=20)`.

- [ ] **Step 1: Write failing normalization, ranking, filter, and fallback tests**

```python
def search_documents() -> list[SearchDocument]:
    return [
        SearchDocument("plugin-system", "插件系统", ("Plugin System",), ("domain/core",), "安装插件", "module", "wiki/plugin.md", ("src/plugin.py",)),
        SearchDocument("storage", "存储", (), ("domain/storage",), "plugin cache", "module", "wiki/storage.md", ("src/storage.py",)),
    ]


def test_normalize_search_text_adds_cjk_unigrams_and_bigrams():
    normalized = normalize_search_text("插件 Plugin")
    assert {"插", "件", "插件", "plugin"} <= set(normalized.split())


def test_search_ranks_exact_title_before_body(tmp_path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    index.update([
        SearchDocument("a", "插件系统", (), ("core",), "无", "module", "wiki/a.md", ()),
        SearchDocument("b", "系统", (), ("core",), "正文介绍插件系统", "module", "wiki/b.md", ()),
    ])
    hits = index.search("插件系统")
    assert [hit.node_id for hit in hits] == ["a", "b"]


def test_search_filters_type_and_tag(tmp_path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    index.update(search_documents())
    hits = index.search("plugin", node_type="module", tag="domain/core", limit=1)
    assert len(hits) == 1
    assert hits[0].node_type == "module"
    assert "domain/core" in hits[0].tags


def test_memory_fallback_has_same_top_hit(tmp_path):
    documents = search_documents()
    index = SearchIndex(tmp_path / "search.sqlite3", force_fallback=True)
    index.update(documents)
    assert index.search("插件")[0].node_id == "plugin-system"


def test_second_index_update_reports_no_changes(tmp_path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    first = index.update(search_documents())
    second = index.update(search_documents())
    assert first.created
    assert second.created == []
    assert second.modified == []
    assert second.deleted == []
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_search.py -q`

Expected: import failure because the search module does not exist.

- [ ] **Step 3: Implement the normalized FTS5 index and fallback**

```python
def normalize_search_text(text: str) -> str:
    lowered = unicodedata.normalize("NFKC", text).casefold()
    words = re.findall(r"[a-z0-9_./-]+", lowered)
    runs = re.findall(r"[\u3400-\u9fff]+", lowered)
    cjk: list[str] = []
    for run in runs:
        cjk.extend(run)
        cjk.extend(run[index : index + 2] for index in range(len(run) - 1))
    return " ".join(dict.fromkeys(words + cjk))


@dataclass(frozen=True)
class SearchDocument:
    node_id: str
    title: str
    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    body: str
    node_type: str
    path: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class SearchHit:
    node_id: str
    title: str
    path: str
    node_type: str
    tags: tuple[str, ...]
    score: float
    snippet: str


@dataclass(frozen=True)
class IndexUpdate:
    created: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()
```

Create a metadata table and FTS5 virtual table keyed by `node_id`, store normalized search text and a content hash, upsert only created or changed documents, delete absent IDs in the same transaction, and sort by explicit exact-title bonus followed by FTS rank and stable ID. The fallback uses the same normalized tokens and bonuses.

- [ ] **Step 4: Run focused search tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_core_search.py -q`

Expected: all FTS5 and forced-fallback tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/mini_wiki_core/search.py tests/test_core_search.py
git commit -m "feat: add Chinese-aware Wiki search"
```

### Task 2: search build integration and CLI

**Files:**
- Modify: `scripts/mini_wiki_core/builder.py`
- Modify: `scripts/mini_wiki_core/doctor.py`
- Modify: `scripts/cli.py`
- Modify: `tests/test_core_builder.py`
- Modify: `tests/test_core_doctor.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Consumes `SearchIndex` from Task 1.
- Produces a staged `.mini-wiki/cache/search.sqlite3` and CLI `search QUERY [PATH] --type --tag --limit --json`.

- [ ] **Step 1: Write failing build and CLI tests**

```python
def test_build_creates_rebuildable_search_index(v3_project):
    build_project(v3_project, BuildOptions())
    database = v3_project / ".mini-wiki/cache/search.sqlite3"
    assert database.exists()
    database.unlink()
    build_project(v3_project, BuildOptions(full=True))
    assert database.exists()


def test_search_cli_outputs_filtered_json(v3_project):
    build_project(v3_project, BuildOptions())
    result = runner.invoke(main, [
        "search", "核心", "--type", "module", "--limit", "5", "--json", str(v3_project)
    ])
    payload = json.loads(result.output)
    assert result.exit_code == 0
    assert len(payload["hits"]) <= 5
    assert all(hit["node_type"] == "module" for hit in payload["hits"])
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_builder.py::test_build_creates_rebuildable_search_index tests/test_cli.py::test_search_cli_outputs_filtered_json -q`

Expected: build omits the database and Click reports no `search` command.

- [ ] **Step 3: Integrate a staged index and CLI output**

```python
@main.command()
@click.argument("query")
@click.option("--type", "node_type")
@click.option("--tag")
@click.option("--limit", default=20, type=click.IntRange(1, 200))
@click.option("--json", "json_output", is_flag=True)
@click.argument("path", required=False)
def search(query: str, node_type: str | None, tag: str | None, limit: int, json_output: bool, path: str | None):
    project = _resolve_project(path)
    hits = SearchIndex(load_config(project).state_dir / "cache/search.sqlite3").search(
        query, node_type=node_type, tag=tag, limit=limit
    )
    payload = {"query": query, "hits": [asdict(hit) for hit in hits]}
    click.echo(json.dumps(payload, ensure_ascii=False) if json_output else format_search_hits(hits))
```

Build the index in the transaction staging directory, then replace it together with Vault artifacts and Manifest. Doctor reports `FTS5_UNAVAILABLE` as a warning and `search_mode: fallback`, not as a failed core environment.

- [ ] **Step 4: Run search integration tests**

Run: `.venv/bin/python -m pytest tests/test_core_builder.py tests/test_core_doctor.py tests/test_cli.py -q`

Expected: database rebuild, filters, JSON serialization, and fallback diagnostics pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/mini_wiki_core/builder.py scripts/mini_wiki_core/doctor.py scripts/cli.py tests/test_core_builder.py tests/test_core_doctor.py tests/test_cli.py
git commit -m "feat: expose standalone Wiki search"
```

### Task 3: deterministic Obsidian Bases

**Files:**
- Create: `scripts/mini_wiki_core/bases.py`
- Create: `tests/test_core_bases.py`
- Modify: `scripts/mini_wiki_core/builder.py`
- Modify: `scripts/mini_wiki_core/validation.py`
- Modify: `tests/test_core_builder.py`
- Modify: `tests/test_core_validation.py`

**Interfaces:**
- Produces: `render_default_bases() -> dict[Path, str]`, `validate_base(path, text) -> list[ValidationIssue]`.
- The builder stages `wiki/views/modules.base`, `sources.base`, `quality.base`, and `orphans.base`.

- [ ] **Step 1: Write failing Base artifact and validation tests**

```python
def test_default_bases_are_parseable_and_deterministic():
    first = render_default_bases()
    second = render_default_bases()
    assert first == second
    assert set(first) == {
        Path("wiki/views/modules.base"),
        Path("wiki/views/sources.base"),
        Path("wiki/views/quality.base"),
        Path("wiki/views/orphans.base"),
    }
    for content in first.values():
        parsed = yaml.safe_load(content)
        assert parsed["views"][0]["type"] == "table"


def test_invalid_base_is_a_strict_validation_error(v3_project):
    path = v3_project / "wiki/views/broken.base"
    path.parent.mkdir(parents=True)
    path.write_text("views: invalid\n")
    report = validate_vault(load_config(v3_project))
    assert any(issue.code == "INVALID_BASE" and issue.severity == "error" for issue in report.issues)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_bases.py tests/test_core_validation.py -q`

Expected: bases module import fails and validation ignores malformed `.base` files.

- [ ] **Step 3: Implement four official-shape Base YAML artifacts**

```python
def _table(name: str, filters: list[str], order: list[str]) -> dict[str, Any]:
    return {
        "filters": {"and": filters},
        "views": [{"type": "table", "name": name, "order": order}],
    }


def render_default_bases() -> dict[Path, str]:
    definitions = {
        "modules.base": _table("Modules", ['file.ext == "md"', 'type == "module"'], ["file.name", "domain", "status", "freshness", "quality"]),
        "sources.base": _table("Sources", ['file.ext == "md"', "source_count > 0"], ["file.name", "sources", "source_count", "freshness"]),
        "quality.base": _table("Quality", ['file.ext == "md"', "quality != null"], ["file.name", "quality", "freshness", "backlink_count"]),
        "orphans.base": _table("Orphans", ['file.ext == "md"', "orphan == true"], ["file.name", "type", "domain", "sources"]),
    }
    return {
        Path("wiki/views") / name: yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
        for name, value in sorted(definitions.items())
    }
```

Validate a mapping root, optional filter mapping, a non-empty list of views, view types from the supported whitelist, and string property names. Stage Bases only when `bases.enabled` is true.

- [ ] **Step 4: Run P1 focused and integrated verification**

Run: `.venv/bin/python -m pytest tests/test_core_search.py tests/test_core_bases.py tests/test_core_builder.py tests/test_core_validation.py tests/test_cli.py -q`

Expected: all P1 tests pass and a full build emits four parseable Base files.

- [ ] **Step 5: Commit Task 3**

```bash
git add scripts/mini_wiki_core/bases.py scripts/mini_wiki_core/builder.py scripts/mini_wiki_core/validation.py tests/test_core_bases.py tests/test_core_builder.py tests/test_core_validation.py
git commit -m "feat: generate Obsidian Bases views"
```

### Task 4: P1 acceptance gate

**Files:**
- Create: `tests/test_p1_workflow.py`

**Interfaces:**
- Consumes P0 build plus P1 search and Bases.

- [ ] **Step 1: Add a complete no-Obsidian acceptance test**

```python
def test_p1_build_search_and_bases_without_obsidian(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    (tmp_path / "src/核心/plugin.py").parent.mkdir(parents=True)
    (tmp_path / "src/核心/plugin.py").write_text("def install_plugin():\n    return '插件安装'\n")
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["build", str(tmp_path)]).exit_code == 0
    result = runner.invoke(main, ["search", "插件安装", "--json", str(tmp_path)])
    assert result.exit_code == 0
    assert json.loads(result.output)["hits"]
    assert len(list((tmp_path / "wiki/views").glob("*.base"))) == 4
```

- [ ] **Step 2: Run it and verify RED for any remaining integration gap**

Run: `.venv/bin/python -m pytest tests/test_p1_workflow.py -q`

Expected: fail only if P1 artifact ordering or Chinese indexing remains incomplete.

- [ ] **Step 3: Correct only the exposed integration behavior**

```python
def search_documents_from_vault(config: WikiConfig) -> list[SearchDocument]:
    return [parse_search_document(path, config.vault_dir) for path in sorted(config.vault_dir.rglob("*.md"))]
```

Ensure index construction reads the staged Markdown content rather than stale committed files, and keep paths repository-relative.

- [ ] **Step 4: Run complete verification through P1**

Run: `.venv/bin/python -m pytest -q`

Run: `.venv/bin/python -m ruff check scripts tests`

Run: `.venv/bin/python -m ruff format --check scripts tests`

Run: `.venv/bin/python -m mypy scripts --ignore-missing-imports`

Run: `git diff --check`

Expected: every command exits 0.

- [ ] **Step 5: Commit Task 4**

```bash
git add tests/test_p1_workflow.py
git commit -m "test: cover search and Bases workflow"
```
