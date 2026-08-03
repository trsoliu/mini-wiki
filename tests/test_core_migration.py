"""Tests for explicit, recoverable v2-to-v3 migration."""

from pathlib import Path

import pytest
import yaml

from mini_wiki_core.migration import (
    MigrationError,
    apply_migration,
    plan_migration,
)


@pytest.fixture
def v2_project(tmp_path: Path) -> Path:
    vault = tmp_path / ".mini-wiki" / "wiki"
    vault.mkdir(parents=True)
    (vault / "index.md").write_text("# Legacy\n")
    (vault / "nested").mkdir()
    (vault / "nested" / "notes.md").write_text("Line one\n\nLine  three\n")
    (tmp_path / ".mini-wiki" / "config.yaml").write_text("generation:\n  language: zh\n")
    return tmp_path


def test_migration_preview_has_no_writes(v2_project: Path):
    plan = plan_migration(v2_project)

    assert plan.applicable is True
    assert plan.source == v2_project / ".mini-wiki" / "wiki"
    assert plan.destination == v2_project / "wiki"
    assert not plan.destination.exists()
    assert not (v2_project / ".mini-wiki" / "archive").exists()


def test_migration_copies_and_keeps_legacy_vault(v2_project: Path):
    result = apply_migration(plan_migration(v2_project))

    assert result.success is True
    assert (v2_project / "wiki" / "index.md").read_text() == "# Legacy\n"
    assert (v2_project / ".mini-wiki" / "wiki" / "index.md").exists()
    assert list((v2_project / ".mini-wiki" / "archive").glob("*/v2-backup/wiki/index.md"))
    config = yaml.safe_load((v2_project / ".mini-wiki" / "config.yaml").read_text())
    assert config["schema_version"] == 3
    assert config["vault"]["path"] == "wiki"


def test_migration_refuses_nonempty_destination_without_writes(v2_project: Path):
    destination = v2_project / "wiki"
    destination.mkdir()
    (destination / "private.md").write_text("private")
    before_config = (v2_project / ".mini-wiki" / "config.yaml").read_bytes()

    with pytest.raises(MigrationError, match="not empty"):
        apply_migration(plan_migration(v2_project))

    assert (destination / "private.md").read_text() == "private"
    assert (v2_project / ".mini-wiki" / "config.yaml").read_bytes() == before_config
    assert not (v2_project / ".mini-wiki" / "archive").exists()


def test_migration_adopt_wraps_legacy_body_without_changing_it(v2_project: Path):
    source = v2_project / ".mini-wiki" / "wiki" / "nested" / "notes.md"
    before = source.read_text()

    result = apply_migration(plan_migration(v2_project), adopt=True)
    migrated = (v2_project / "wiki" / "nested" / "notes.md").read_text()

    assert result.success is True
    assert before in migrated
    assert "<!-- mini-wiki:content:start -->" in migrated
    assert "<!-- mini-wiki:content:end -->" in migrated
    assert source.read_text() == before


def test_completed_v3_migration_plans_as_noop(v2_project: Path):
    apply_migration(plan_migration(v2_project))

    plan = plan_migration(v2_project)

    assert plan.applicable is False
    assert "already-v3" in plan.reasons
