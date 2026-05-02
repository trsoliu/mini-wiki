"""Tests for scripts/analyze_project.py."""

import json
from pathlib import Path

from analyze_project import (
    categorize_module,
    detect_monorepo_tools,
    detect_package_manager,
    detect_project_types,
    discover_modules,
    find_documentation,
    find_entry_points,
    analyze_project,
    IGNORE_DIRS,
    CODE_EXTENSIONS,
)


# --- categorize_module ---


def test_categorize_ui_modules():
    for name in ["components", "ui-kit", "views", "pages"]:
        assert categorize_module(name) == "ui"


def test_categorize_api_modules():
    for name in ["api", "services", "handler"]:
        assert categorize_module(name) == "api"


def test_categorize_utility_modules():
    for name in ["utils", "helpers", "common", "shared"]:
        assert categorize_module(name) == "utility"


def test_categorize_core_modules():
    for name in ["core", "lib", "engine"]:
        assert categorize_module(name) == "core"


def test_categorize_config_modules():
    assert categorize_module("config") == "config"
    assert categorize_module("settings") == "config"


def test_categorize_test_modules():
    assert categorize_module("tests") == "test"
    assert categorize_module("spec") == "test"


def test_categorize_unknown_module():
    assert categorize_module("random-name") == "module"


# --- detect_package_manager ---


def test_detect_npm(tmp_path):
    (tmp_path / "package-lock.json").write_text("{}")
    assert "npm" in detect_package_manager(tmp_path)


def test_detect_yarn(tmp_path):
    (tmp_path / "yarn.lock").write_text("")
    assert "yarn" in detect_package_manager(tmp_path)


def test_detect_pnpm(tmp_path):
    (tmp_path / "pnpm-lock.yaml").write_text("")
    assert "pnpm" in detect_package_manager(tmp_path)


def test_detect_bun(tmp_path):
    (tmp_path / "bun.lockb").write_bytes(b"")
    assert "bun" in detect_package_manager(tmp_path)


def test_detect_no_package_manager(tmp_path):
    assert detect_package_manager(tmp_path) == []


# --- detect_monorepo_tools ---


def test_detect_turborepo(tmp_path):
    (tmp_path / "turbo.json").write_text("{}")
    result = detect_monorepo_tools(tmp_path)
    assert "turborepo" in result
    assert "monorepo" in result


def test_detect_lerna(tmp_path):
    (tmp_path / "lerna.json").write_text("{}")
    result = detect_monorepo_tools(tmp_path)
    assert "lerna" in result
    assert "monorepo" in result


def test_detect_pnpm_workspaces(tmp_path):
    (tmp_path / "pnpm-workspace.yaml").write_text("packages:\n  - packages/*")
    result = detect_monorepo_tools(tmp_path)
    assert "pnpm-workspaces" in result


def test_detect_npm_workspaces(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"workspaces": ["packages/*"]}))
    result = detect_monorepo_tools(tmp_path)
    assert "npm-workspaces" in result


def test_detect_no_monorepo(tmp_path):
    assert detect_monorepo_tools(tmp_path) == []


# --- detect_project_types ---


def test_detect_python_project(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    types = detect_project_types(tmp_path)
    assert "python" in types


def test_detect_nodejs_project(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"name": "test"}))
    types = detect_project_types(tmp_path)
    assert "nodejs" in types


def test_detect_go_project(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.21\n")
    types = detect_project_types(tmp_path)
    assert "go" in types


def test_detect_rust_project(tmp_path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\n')
    types = detect_project_types(tmp_path)
    assert "rust" in types


def test_detect_react_in_package_json(tmp_path):
    pkg = {"name": "test", "dependencies": {"react": "^18.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    types = detect_project_types(tmp_path)
    assert "react" in types


def test_detect_empty_project(tmp_path):
    assert detect_project_types(tmp_path) == []


# --- find_entry_points ---


def test_find_entry_points_python(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    entries = find_entry_points(tmp_path, ["python"])
    assert "main.py" in entries


def test_find_entry_points_node(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.ts").write_text("export default {}")
    entries = find_entry_points(tmp_path, ["nodejs", "typescript"])
    assert "src/index.ts" in entries


def test_find_entry_points_empty(tmp_path):
    assert find_entry_points(tmp_path, []) == []


# --- discover_modules ---


def test_discover_modules_src_dir(tmp_path):
    src = tmp_path / "src"
    (src / "core").mkdir(parents=True)
    (src / "core" / "app.py").write_text("pass")
    (src / "utils").mkdir()
    (src / "utils" / "helpers.py").write_text("pass")

    modules = discover_modules(tmp_path)
    names = [m["name"] for m in modules]
    assert "core" in names
    assert "utils" in names


def test_discover_modules_fallback_to_root(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run.py").write_text("pass")

    modules = discover_modules(tmp_path)
    names = [m["name"] for m in modules]
    assert "scripts" in names


def test_discover_modules_empty(tmp_path):
    assert discover_modules(tmp_path) == []


def test_discover_modules_ignores_excluded_dirs(tmp_path):
    src = tmp_path / "src"
    (src / "node_modules").mkdir(parents=True)
    (src / "node_modules" / "pkg.js").write_text("pass")

    modules = discover_modules(tmp_path)
    names = [m["name"] for m in modules]
    assert "node_modules" not in names


# --- find_documentation ---


def test_find_documentation_readme(tmp_path):
    (tmp_path / "README.md").write_text("# Hello")
    docs = find_documentation(tmp_path)
    assert "README.md" in docs


def test_find_documentation_multiple(tmp_path):
    (tmp_path / "README.md").write_text("# Hello")
    (tmp_path / "CHANGELOG.md").write_text("# Changes")
    (tmp_path / "LICENSE").write_text("MIT")
    docs = find_documentation(tmp_path)
    assert len(docs) >= 3


def test_find_documentation_docs_dir(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# Guide")
    docs = find_documentation(tmp_path)
    assert any("guide.md" in d for d in docs)


def test_find_documentation_empty(tmp_path):
    assert find_documentation(tmp_path) == []


# --- analyze_project ---


def test_analyze_project_basic(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "README.md").write_text("# Test")

    result = analyze_project(str(tmp_path), save_to_cache=False)

    assert result["project_name"] == tmp_path.name
    assert "stats" in result
    assert result["stats"]["total_docs"] >= 1
    assert "analyzed_at" in result


def test_analyze_project_saves_cache(tmp_path):
    wiki_dir = tmp_path / ".mini-wiki" / "cache"
    wiki_dir.mkdir(parents=True)

    (tmp_path / "app.py").write_text("pass")

    analyze_project(str(tmp_path), save_to_cache=True)

    cache_file = tmp_path / ".mini-wiki" / "cache" / "structure.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text())
    assert "project_name" in data


def test_analyze_project_empty(tmp_path):
    result = analyze_project(str(tmp_path), save_to_cache=False)
    assert result["stats"]["total_files"] == 0
    assert result["modules"] == []
