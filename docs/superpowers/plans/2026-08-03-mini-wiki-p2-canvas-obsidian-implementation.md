# Mini-Wiki P2 Canvas and Obsidian Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic JSON Canvas views, optional Obsidian status/open integration, and finish the public Mini-Wiki 3.3.0 Skill, CLI, documentation, and release contracts.

**Architecture:** Canvas is another pure projection of the P0 knowledge graph and uses only JSON Canvas 1.0 fields. Obsidian integration is isolated behind an injectable adapter and runs an external action only for the explicit `obsidian open` command. Documentation then moves the old v2 paths and source-link rules to the tested v3 behavior.

**Tech Stack:** Python stdlib JSON/subprocess/urllib, Click, pytest, Ruff, Mypy, JSON Canvas 1.0, Obsidian URI/optional CLI.

## Global Constraints

- Canvas node and edge IDs, ordering, coordinates, dimensions, and serialized JSON are deterministic.
- A Canvas contains at most `canvas.max_nodes` expanded nodes and reports aggregation.
- Only standard JSON Canvas fields are emitted.
- Obsidian absence is informational and never blocks core commands.
- No command starts Obsidian except explicit `mini-wiki obsidian open`.
- Mini-Wiki must not write `.obsidian/`, install plugins, change themes, or require Obsidian CLI.
- Public docs, Skill instructions, examples, and `--version` must all say 3.3.0 and match actual behavior.
- No production behavior is added before its failing test has been observed.

---

## File Map

| File | Responsibility |
|---|---|
| `scripts/mini_wiki_core/canvas.py` | JSON Canvas projection, aggregation, layout, validation |
| `scripts/mini_wiki_core/obsidian.py` | optional CLI/URI status and explicit open adapter |
| `scripts/mini_wiki_core/builder.py` | stage three Canvas artifacts |
| `scripts/mini_wiki_core/validation.py` | validate Canvas schema and file targets |
| `scripts/mini_wiki_core/doctor.py` | include Obsidian status without blocking |
| `scripts/cli.py` | `obsidian status/open` and v3.3.0 version |
| `SKILL.md` | Agent workflow for root Vault, build plan, managed regions, P0-P2 |
| `references/SKILL.zh.md` | Chinese workflow parity |
| `references/prompts.md` | portable source trace and managed-content prompts |
| `references/templates.md` | v3 Properties, links, Base, and Canvas-aware templates |
| `README.md`, `README.zh.md` | current CLI and product contract |
| `CHANGELOG.md` | 3.3.0 release entry |
| `plugins/*/PLUGIN.md` | remove product-owned legacy `file://` or old Vault examples |

### Task 1: deterministic JSON Canvas projection

**Files:**
- Create: `scripts/mini_wiki_core/canvas.py`
- Create: `tests/test_core_canvas.py`

**Interfaces:**
- Consumes P0 `KnowledgeGraph`.
- Produces: `CanvasArtifact`, `render_default_canvases(graph, max_nodes)`, `validate_canvas(path, payload)`.

- [ ] **Step 1: Write failing schema, determinism, and aggregation tests**

```python
@pytest.fixture
def sample_graph() -> KnowledgeGraph:
    nodes = {
        "mw:project:demo": Node("mw:project:demo", "project", "Demo", "wiki/index.md"),
        "mw:document:core": Node("mw:document:core", "document", "Core", "wiki/domains/core/core.md"),
    }
    return KnowledgeGraph(nodes, [Edge("mw:project:demo", "mw:document:core", "contains")])


@pytest.fixture
def large_graph() -> KnowledgeGraph:
    nodes = {
        f"mw:document:module-{index}": Node(
            f"mw:document:module-{index}", "document", f"Module {index}", f"wiki/domains/core/module-{index}.md"
        )
        for index in range(30)
    }
    return KnowledgeGraph(nodes, [])


def test_canvas_is_deterministic_and_uses_standard_fields(sample_graph):
    first = render_default_canvases(sample_graph, max_nodes=200)
    reversed_graph = KnowledgeGraph(dict(reversed(list(sample_graph.nodes.items()))), list(reversed(sample_graph.edges)))
    second = render_default_canvases(reversed_graph, max_nodes=200)
    assert first == second
    payload = json.loads(first.files[Path("wiki/canvas/architecture.canvas")])
    assert set(payload) == {"nodes", "edges"}
    assert all(set(node) <= {"id", "type", "file", "subpath", "text", "url", "label", "background", "backgroundStyle", "x", "y", "width", "height", "color"} for node in payload["nodes"])


def test_canvas_aggregates_when_node_limit_is_exceeded(large_graph):
    artifacts = render_default_canvases(large_graph, max_nodes=10)
    payload = json.loads(artifacts.files[Path("wiki/canvas/domains.canvas")])
    assert len(payload["nodes"]) <= 10
    assert any("aggregated_count" in warning for warning in artifacts.warnings)


def test_file_nodes_target_existing_vault_documents(sample_graph, tmp_path):
    artifact = render_default_canvases(sample_graph, max_nodes=200)
    issues = validate_canvas(Path("architecture.canvas"), json.loads(artifact.files[Path("wiki/canvas/architecture.canvas")]))
    assert issues == []
```

- [ ] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_canvas.py -q`

Expected: import failure because canvas module does not exist.

- [ ] **Step 3: Implement stable IDs, grid layout, and standard JSON**

```python
@dataclass(frozen=True)
class CanvasArtifact:
    files: dict[Path, str]
    warnings: tuple[str, ...] = ()


def canvas_id(prefix: str, stable_id: str) -> str:
    digest = hashlib.sha256(stable_id.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def grid_position(index: int, columns: int = 4) -> tuple[int, int]:
    return (index % columns) * 420, (index // columns) * 260


def dump_canvas(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    payload = {
        "nodes": sorted(nodes, key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: edge["id"]),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
```

Generate `architecture.canvas`, `domains.canvas`, and `traceability.canvas`. Prefer file nodes for document nodes, text nodes only for aggregation summaries, stable graph layers and grid coordinates, and aggregate by domain before truncating.

- [ ] **Step 4: Run focused Canvas tests and verify GREEN**

Run: `.venv/bin/python -m pytest tests/test_core_canvas.py -q`

Expected: deterministic payload, node cap, and schema tests pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add scripts/mini_wiki_core/canvas.py tests/test_core_canvas.py
git commit -m "feat: generate deterministic JSON Canvas views"
```

### Task 2: Canvas build and validation integration

**Files:**
- Modify: `scripts/mini_wiki_core/builder.py`
- Modify: `scripts/mini_wiki_core/validation.py`
- Modify: `tests/test_core_builder.py`
- Modify: `tests/test_core_validation.py`

**Interfaces:**
- Consumes Canvas renderer from Task 1.
- Builder stages three Canvas files when enabled; validator reports malformed nodes, edges, duplicate IDs, and missing file targets.

- [ ] **Step 1: Write failing build and strict-validation tests**

```python
def test_build_emits_three_canvas_files(v3_project):
    result = build_project(v3_project, BuildOptions())
    assert result.success is True
    assert {path.name for path in (v3_project / "wiki/canvas").glob("*.canvas")} == {
        "architecture.canvas",
        "domains.canvas",
        "traceability.canvas",
    }


def test_missing_canvas_file_target_is_strict_error(v3_project):
    canvas = {"nodes": [{"id": "n1", "type": "file", "file": "missing.md", "x": 0, "y": 0, "width": 100, "height": 100}], "edges": []}
    path = v3_project / "wiki/canvas/broken.canvas"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(canvas))
    report = validate_vault(load_config(v3_project))
    assert any(issue.code == "CANVAS_FILE_MISSING" for issue in report.issues)
```

- [ ] **Step 2: Run selected tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_builder.py::test_build_emits_three_canvas_files tests/test_core_validation.py::test_missing_canvas_file_target_is_strict_error -q`

Expected: no Canvas artifacts and no Canvas validation issue.

- [ ] **Step 3: Stage Canvas artifacts and extend strict validation**

```python
if config.canvas_enabled:
    canvas = render_default_canvases(graph, config.canvas_max_nodes)
    artifacts.update(canvas.files)
    result.warnings.extend(canvas.warnings)
```

Parse every `.canvas` as JSON, require list `nodes` and `edges`, unique string IDs, all four standard node types (`text`, `file`, `link`, `group`), numeric geometry, valid edge endpoints, and existing Vault-relative file targets. Canvas warnings do not fail strict check; invalid structure does.

- [ ] **Step 4: Run builder and validation tests**

Run: `.venv/bin/python -m pytest tests/test_core_canvas.py tests/test_core_builder.py tests/test_core_validation.py -q`

Expected: all selected tests pass and repeated builds produce byte-identical Canvas files.

- [ ] **Step 5: Commit Task 2**

```bash
git add scripts/mini_wiki_core/builder.py scripts/mini_wiki_core/validation.py tests/test_core_builder.py tests/test_core_validation.py
git commit -m "feat: integrate Canvas into Wiki builds"
```

### Task 3: optional Obsidian adapter and CLI

**Files:**
- Create: `scripts/mini_wiki_core/obsidian.py`
- Create: `tests/test_core_obsidian.py`
- Modify: `scripts/mini_wiki_core/doctor.py`
- Modify: `scripts/cli.py`
- Modify: `tests/test_core_doctor.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Produces: `ObsidianStatus`, `detect_obsidian(which, platform_name)`, `probe_obsidian_version(status, runner)`, `open_vault(config, status, uri_opener)`.
- CLI: `obsidian status [PATH] --json [--probe]` and `obsidian open [PATH]`.

- [ ] **Step 1: Write failing absence, status, and explicit-open tests**

```python
def test_absent_obsidian_is_available_core_environment(tmp_path):
    status = detect_obsidian(which=lambda _: None, platform_name="linux")
    assert status.cli_available is False
    assert status.uri_available is False
    assert status.core_blocked is False


def test_status_without_probe_never_starts_external_process(v3_project, monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: called.append(args))
    result = runner.invoke(main, ["obsidian", "status", "--json", str(v3_project)])
    assert result.exit_code == 0
    assert called == []


def test_probe_uses_official_version_command_only_when_requested():
    calls = []
    status = ObsidianStatus(True, "/usr/bin/obsidian", True, False, None)
    probed = probe_obsidian_version(status, runner=lambda argv: calls.append(argv) or "1.12.7")
    assert probed.version == "1.12.7"
    assert calls == [["/usr/bin/obsidian", "version"]]


def test_open_uses_uri_only_after_explicit_request(v3_project):
    calls = []
    status = ObsidianStatus(True, "/usr/bin/obsidian", True, False, None)
    result = open_vault(load_config(v3_project), status, uri_opener=lambda uri: calls.append(uri) or 0)
    assert result.success is True
    assert calls == [vault_uri(v3_project / "wiki")]
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_core_obsidian.py tests/test_cli.py -q`

Expected: adapter import fails and no `obsidian` command group exists.

- [ ] **Step 3: Implement side-effect-free detection and explicit opening**

```python
@dataclass(frozen=True)
class ObsidianStatus:
    cli_available: bool
    cli_path: str | None
    uri_available: bool
    core_blocked: bool = False
    version: str | None = None


def detect_obsidian(which: Callable[[str], str | None] = shutil.which, platform_name: str = sys.platform) -> ObsidianStatus:
    cli = which("obsidian")
    uri_available = platform_name in {"darwin", "win32"}
    return ObsidianStatus(cli is not None, cli, uri_available, False, None)


def vault_uri(vault_dir: Path) -> str:
    return "obsidian://open?" + urllib.parse.urlencode({"path": str(vault_dir.resolve())})
```

Do not run version or status subprocesses during normal detection. `status --probe` may explicitly call the official `obsidian version` command and must warn that Obsidian CLI 1.12.7+ requires the app and may launch it. Opening a Vault uses the official `obsidian://open?path=...` URI because the CLI `open` command targets a file, not a Vault; macOS and Windows use safe argument-list platform openers, and unsupported systems return instructions without launching. Doctor imports unprobed status as informational findings.

- [ ] **Step 4: Run adapter, doctor, and CLI tests**

Run: `.venv/bin/python -m pytest tests/test_core_obsidian.py tests/test_core_doctor.py tests/test_cli.py -q`

Expected: status is side-effect free, absence does not fail doctor, and only explicit open invokes the runner.

- [ ] **Step 5: Commit Task 3**

```bash
git add scripts/mini_wiki_core/obsidian.py scripts/mini_wiki_core/doctor.py scripts/cli.py tests/test_core_obsidian.py tests/test_core_doctor.py tests/test_cli.py
git commit -m "feat: add optional Obsidian integration"
```

### Task 4: public v3.3.0 Skill and documentation contract

**Files:**
- Modify: `pyproject.toml`
- Modify: `scripts/cli.py`
- Modify: `SKILL.md`
- Modify: `references/SKILL.zh.md`
- Modify: `references/prompts.md`
- Modify: `references/templates.md`
- Modify: `README.md`
- Modify: `README.zh.md`
- Modify: `CHANGELOG.md`
- Modify: relevant tracked `plugins/*/PLUGIN.md`
- Create: `tests/test_public_contract.py`

**Interfaces:**
- Consumes every implemented P0-P2 command and artifact.
- Produces version 3.3.0 and documentation with no active legacy path or absolute source-link instructions.

- [ ] **Step 1: Write failing public-contract tests**

```python
@pytest.mark.parametrize("path", [
    "SKILL.md",
    "references/SKILL.zh.md",
    "references/prompts.md",
    "references/templates.md",
    "README.md",
    "README.zh.md",
])
def test_public_docs_do_not_teach_legacy_output_or_file_urls(repo_root, path):
    text = (repo_root / path).read_text()
    assert "write wiki files to `.mini-wiki/wiki/`" not in text.casefold()
    assert "写入 wiki 文件到 `.mini-wiki/wiki/`" not in text
    assert "file:///path/to" not in text


def test_versions_are_3_3_0(repo_root):
    assert 'version = "3.3.0"' in (repo_root / "pyproject.toml").read_text()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "3.3.0" in result.output


def test_skill_documents_build_search_bases_and_canvas(repo_root):
    text = (repo_root / "SKILL.md").read_text()
    for required in ["mini-wiki build", "mini-wiki search", "Properties", "Bases", "Canvas"]:
        assert required in text
```

- [ ] **Step 2: Run contract tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_public_contract.py tests/test_cli.py::test_version -q`

Expected: version and multiple old-path/source-link assertions fail.

- [ ] **Step 3: Update every public contract to implemented behavior**

```markdown
## Agent workflow

1. Run `mini-wiki init <project>` once.
2. Run `mini-wiki build <project> --json` to create the graph and `build-plan.json`.
3. Read enabled plugin instructions as text only; never execute plugin scripts.
4. Write professional content only inside `mini-wiki:content` regions.
5. Run `mini-wiki build`, `mini-wiki check --strict`, and relevant searches again.

Durable knowledge is stored in `wiki/`. Rebuildable state is stored in `.mini-wiki/`.
Source references use repository-relative Markdown links and never `file://` URLs.
```

Update both READMEs with all new commands and migration behavior, update Skill output examples to `wiki/domains`, explain Properties/Bases/Canvas, keep the instruction-only plugin rule prominent, update templates to managed regions, update tracked built-in plugin examples that teach the old output contract, add a 3.3.0 changelog entry, and keep historical changelog entries unchanged.

- [ ] **Step 4: Run contract and documentation scans**

Run: `.venv/bin/python -m pytest tests/test_public_contract.py tests/test_cli.py -q`

Run: `grep -RIn --exclude-dir=.git --exclude='docs/wechat-publish-notes.md' --exclude='2026-08-03-obsidian-knowledge-network-upgrade-design.md' --exclude='*.pyc' 'file:///path/to\|写入 wiki 文件到 `.mini-wiki/wiki/`\|write wiki files to `.mini-wiki/wiki/`' SKILL.md references README.md README.zh.md plugins scripts`

Expected: tests pass and grep prints no active legacy instructions.

- [ ] **Step 5: Commit Task 4**

```bash
git add pyproject.toml scripts/cli.py SKILL.md references README.md README.zh.md CHANGELOG.md plugins tests/test_public_contract.py
git commit -m "docs: release Mini-Wiki 3.3.0 knowledge networks"
```

### Task 5: complete P0-P2 release verification

**Files:**
- Create: `tests/test_p2_workflow.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- End-to-end proof for initialization, deterministic build, strict validation, Chinese search, Bases, Canvas, migration compatibility, and optional Obsidian absence.

- [ ] **Step 1: Write the final failing smoke test**

```python
def test_complete_p0_p1_p2_workflow(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    source = tmp_path / "src/安全插件/plugin.py"
    source.parent.mkdir(parents=True)
    source.write_text("def install_plugin():\n    return '安全安装插件'\n")
    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["build", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["check", "--strict", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["search", "安全插件", "--json", str(tmp_path)]).exit_code == 0
    assert len(list((tmp_path / "wiki/views").glob("*.base"))) == 4
    assert len(list((tmp_path / "wiki/canvas").glob("*.canvas"))) == 3
    status = runner.invoke(main, ["obsidian", "status", "--json", str(tmp_path)])
    assert status.exit_code == 0
    assert json.loads(status.output)["core_blocked"] is False
```

- [ ] **Step 2: Run it and verify RED for any remaining release gap**

Run: `.venv/bin/python -m pytest tests/test_p2_workflow.py -q`

Expected: fail at the first remaining integration or output-contract discrepancy.

- [ ] **Step 3: Apply only the final integration corrections and CI smoke entry**

```yaml
- name: Run full Mini-Wiki workflow smoke test
  run: pytest tests/test_p0_workflow.py tests/test_p1_workflow.py tests/test_p2_workflow.py -v
```

Correct only the failing command wiring, serialization, artifact transaction, or documentation contract. Do not add P3 watch, realtime collaboration, embeddings, or automatic plugin execution.

- [ ] **Step 4: Run fresh complete verification**

Run: `.venv/bin/python -m pytest --cov=scripts --cov-report=term-missing -q`

Run: `.venv/bin/python -m ruff check scripts tests`

Run: `.venv/bin/python -m ruff format --check scripts tests`

Run: `.venv/bin/python -m mypy scripts --ignore-missing-imports`

Run: `.venv/bin/mini-wiki --version`

Run: `.venv/bin/mini-wiki --help`

Run: `git diff --check`

Expected: every command exits 0; pytest reports zero failures; CLI reports 3.3.0 and lists `build`, `doctor`, `search`, `migrate`, `plugins`, and `obsidian`.

- [ ] **Step 5: Commit Task 5**

```bash
git add .github/workflows/ci.yml tests/test_p2_workflow.py
git commit -m "test: verify Mini-Wiki 3.3.0 end to end"
```
