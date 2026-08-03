"""Tests for the Mini-Wiki v3 configuration contract."""

from pathlib import Path

import pytest
import yaml

from init_wiki import init_mini_wiki
from mini_wiki_core.config import ConfigError, default_config_data, load_config, resolve_project_path


def test_default_config_contains_v3_vault_and_feature_sections():
    config = default_config_data()

    assert config["schema_version"] == 3
    assert config["vault"] == {
        "path": "wiki",
        "link_style": "wikilink",
        "source_links": "relative-markdown",
        "preserve_manual_content": True,
    }
    assert config["search"]["enabled"] is True
    assert config["bases"]["enabled"] is True
    assert config["canvas"] == {"enabled": True, "max_nodes": 200}


def test_init_creates_v3_state_and_root_vault(tmp_path: Path):
    result = init_mini_wiki(str(tmp_path))
    config = yaml.safe_load((tmp_path / ".mini-wiki" / "config.yaml").read_text())

    assert result["success"] is True
    assert config["schema_version"] == 3
    assert config["vault"]["path"] == "wiki"
    assert (tmp_path / "wiki" / "domains").is_dir()
    assert not (tmp_path / ".mini-wiki" / "wiki").exists()


def test_load_config_uses_legacy_vault_without_silent_migration(tmp_path: Path):
    (tmp_path / ".mini-wiki" / "wiki").mkdir(parents=True)
    (tmp_path / ".mini-wiki" / "config.yaml").write_text("generation:\n  language: zh\n")

    config = load_config(tmp_path)

    assert config.compatibility_mode is True
    assert config.vault_dir == tmp_path / ".mini-wiki" / "wiki"


def test_load_config_merges_legacy_and_required_excludes(tmp_path: Path):
    (tmp_path / ".mini-wiki").mkdir()
    (tmp_path / ".mini-wiki" / "config.yaml").write_text("exclude:\n  - private-build\n")

    config = load_config(tmp_path)

    assert {".git", ".mini-wiki", ".agents", "private-build"} <= set(config.excludes)


def test_resolve_project_path_rejects_escape(tmp_path: Path):
    with pytest.raises(ConfigError, match="outside project root"):
        resolve_project_path(tmp_path, "../private")


def test_load_config_rejects_invalid_link_style(tmp_path: Path):
    (tmp_path / ".mini-wiki").mkdir()
    (tmp_path / ".mini-wiki" / "config.yaml").write_text(
        "schema_version: 3\nvault:\n  path: wiki\n  link_style: html\n"
    )

    with pytest.raises(ConfigError, match="link_style"):
        load_config(tmp_path)
