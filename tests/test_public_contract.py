"""Tests for the public Mini-Wiki 3.3.0 documentation and CLI contract."""

from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from click.testing import CliRunner

from cli import main
from mini_wiki_core import __version__


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


PUBLIC_DOCS = (
    "SKILL.md",
    "references/SKILL.zh.md",
    "references/prompts.md",
    "references/templates.md",
    "README.md",
    "README.zh.md",
)


@pytest.mark.parametrize("path", PUBLIC_DOCS)
def test_public_docs_do_not_teach_legacy_output_or_file_urls(repo_root: Path, path: str):
    text = (repo_root / path).read_text()

    assert ".mini-wiki/wiki" not in text
    assert "file://" not in text


def test_builtin_plugin_instructions_use_portable_v3_contract(repo_root: Path):
    for path in sorted((repo_root / "plugins").glob("*/PLUGIN.md")):
        text = path.read_text()
        assert ".mini-wiki/wiki" not in text, path
        assert "file://" not in text, path


def test_versions_are_3_3_0(repo_root: Path):
    assert __version__ == "3.3.0"
    assert 'version = "3.3.0"' in (repo_root / "pyproject.toml").read_text()
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "3.3.0" in result.output


def test_skill_documents_complete_agent_workflow(repo_root: Path):
    text = (repo_root / "SKILL.md").read_text()

    for required in (
        "mini-wiki init",
        "mini-wiki build",
        "mini-wiki search",
        "mini-wiki check --strict",
        "Properties",
        "Bases",
        "Canvas",
        "instruction-only",
        "mini-wiki:content",
    ):
        assert required in text


def test_readmes_state_canonical_and_rebuildable_boundaries(repo_root: Path):
    for path in ("README.md", "README.zh.md"):
        text = (repo_root / path).read_text()
        assert "wiki/" in text
        assert ".mini-wiki/" in text
        assert "search" in text.casefold()
        assert "Canvas" in text


def test_changelog_has_3_3_0_release(repo_root: Path):
    text = (repo_root / "CHANGELOG.md").read_text()

    assert "3.3.0" in text
    assert "Obsidian" in text


def test_shipped_config_uses_v3_knowledge_boundaries(repo_root: Path):
    config = yaml.safe_load((repo_root / "assets/config.yaml").read_text())

    assert config["schema_version"] == 3
    assert config["vault"]["path"] == "wiki"
    assert config["search"]["enabled"] is True
    assert config["bases"]["enabled"] is True
    assert config["canvas"]["enabled"] is True


def test_plugin_template_is_instruction_only(repo_root: Path):
    text = (repo_root / "references/plugin-template.md").read_text()

    assert "instruction-only" in text
    assert "├── scripts/" not in text
    assert "must never execute" in text


def test_skill_archive_contains_current_v3_runtime(repo_root: Path):
    with ZipFile(repo_root / "mini-wiki.skill") as archive:
        names = set(archive.namelist())
        assert archive.read("SKILL.md") == (repo_root / "SKILL.md").read_bytes()

    assert {
        "pyproject.toml",
        "scripts/cli.py",
        "scripts/mini_wiki_core/bases.py",
        "scripts/mini_wiki_core/canvas.py",
        "scripts/mini_wiki_core/obsidian.py",
        "scripts/mini_wiki_core/search.py",
        "scripts/mini_wiki_core/validation.py",
    } <= names
    assert not any(name.endswith((".pyc", ".pyo")) or "__pycache__" in name for name in names)
