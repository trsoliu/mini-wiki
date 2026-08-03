"""Tests for deterministic, transactional Mini-Wiki builds."""

import json
from pathlib import Path

import pytest

from mini_wiki_core.builder import (
    BuildOptions,
    FileTransaction,
    TransactionError,
    build_project,
)
from mini_wiki_core.vault import CONTENT_END, CONTENT_START


def vault_snapshot(project: Path) -> dict[Path, bytes]:
    return {path.relative_to(project): path.read_bytes() for path in (project / "wiki").rglob("*") if path.is_file()}


def test_two_builds_are_byte_identical(v3_project: Path):
    first = build_project(v3_project, BuildOptions())
    snapshot = vault_snapshot(v3_project)
    second = build_project(v3_project, BuildOptions())
    assert first.success is True
    assert second.success is True
    assert second.changed == []
    assert snapshot == vault_snapshot(v3_project)


def test_build_writes_vault_graph_agent_plan_and_manifest(v3_project: Path):
    result = build_project(v3_project, BuildOptions())
    analysis = json.loads((v3_project / ".mini-wiki" / "cache" / "analysis.json").read_text())
    graph = json.loads((v3_project / ".mini-wiki" / "cache" / "graph.json").read_text())
    plan = json.loads((v3_project / ".mini-wiki" / "cache" / "build-plan.json").read_text())
    manifest = json.loads((v3_project / ".mini-wiki" / "manifest.json").read_text())
    assert result.success is True
    assert "analyzed_at" not in analysis
    assert graph["nodes"]
    assert plan["documents"]
    assert manifest["schema_version"] == 3
    assert all(not Path(item["path"]).is_absolute() for item in plan["documents"])
    assert (v3_project / "wiki" / "index.md").exists()
    assert (v3_project / "wiki" / "domains" / "core" / "_index.md").exists()
    assert (v3_project / "wiki" / "domains" / "core" / "core.md").exists()


def test_dry_run_reports_without_writing_files(v3_project: Path):
    result = build_project(v3_project, BuildOptions(dry_run=True))
    assert result.success is True
    assert result.created
    assert list((v3_project / "wiki").rglob("*.md")) == []
    manifest = json.loads((v3_project / ".mini-wiki" / "manifest.json").read_text())
    assert manifest["documents"] == {}


def test_rebuild_preserves_agent_content(v3_project: Path):
    build_project(v3_project, BuildOptions())
    document = v3_project / "wiki" / "domains" / "core" / "core.md"
    existing = document.read_text()
    custom = existing.replace(
        f"{CONTENT_START}\n## Overview\n\nAgent content pending.\n{CONTENT_END}",
        f"{CONTENT_START}\n## Architecture decision\n\nKeep  exact spacing.\n{CONTENT_END}",
    )
    document.write_text(custom)
    build_project(v3_project, BuildOptions(full=True))
    assert "## Architecture decision\n\nKeep  exact spacing." in document.read_text()


def test_removed_source_archives_its_managed_document(v3_project: Path):
    source = v3_project / "src" / "legacy.py"
    source.write_text("def old():\n    return 1\n")
    build_project(v3_project, BuildOptions())
    managed_document = v3_project / "wiki" / "domains" / "general" / "legacy.md"
    assert managed_document.exists()
    source.unlink()
    result = build_project(v3_project, BuildOptions())
    assert "wiki/domains/general/legacy.md" in result.archived
    assert not managed_document.exists()
    assert list((v3_project / ".mini-wiki" / "archive").rglob("legacy.md"))


def test_transaction_restores_files_when_replace_fails(tmp_path: Path, monkeypatch):
    state = tmp_path / ".mini-wiki"
    (state / "staging").mkdir(parents=True)
    first = tmp_path / "wiki" / "a.md"
    second = tmp_path / "wiki" / "b.md"
    first.parent.mkdir()
    first.write_text("before-a")
    second.write_text("before-b")
    transaction = FileTransaction(tmp_path, state)
    transaction.stage_text(Path("wiki/a.md"), "after-a")
    transaction.stage_text(Path("wiki/b.md"), "after-b")
    real_replace = transaction._replace
    calls = 0

    def flaky_replace(source: Path, destination: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replace failure")
        return real_replace(source, destination)

    monkeypatch.setattr(transaction, "_replace", flaky_replace)
    with pytest.raises(TransactionError, match="injected replace failure"):
        transaction.commit()
    assert first.read_text() == "before-a"
    assert second.read_text() == "before-b"
