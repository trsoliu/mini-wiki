"""Tests for scripts/init_wiki.py."""

import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pytest

from init_wiki import (
    get_default_config,
    get_default_meta,
    init_mini_wiki,
)


# --- get_default_config ---


def test_get_default_config_returns_string():
    """Default config should be a non-empty string."""
    result = get_default_config()

    assert isinstance(result, str)
    assert len(result) > 0


def test_get_default_config_contains_key_sections():
    """Default config should contain essential configuration sections."""
    result = get_default_config()

    # Check for key configuration sections
    assert "generation:" in result
    assert "exclude:" in result
    assert "language:" in result
    assert "include_diagrams:" in result
    assert "include_examples:" in result


def test_get_default_config_contains_common_excludes():
    """Default config should exclude common directories."""
    result = get_default_config()

    # Check for common exclude patterns
    assert "node_modules" in result
    assert ".git" in result
    assert "__pycache__" in result


def test_get_default_config_is_valid_yaml_format():
    """Default config should be in valid YAML format."""
    result = get_default_config()

    # Basic YAML format checks
    assert "generation:" in result
    assert "exclude:" in result
    # Should have proper indentation
    assert "  language:" in result or "  include_diagrams:" in result


# --- get_default_meta ---


def test_get_default_meta_returns_dict():
    """Default meta should be a dictionary."""
    result = get_default_meta()

    assert isinstance(result, dict)
    assert len(result) > 0


def test_get_default_meta_contains_required_fields():
    """Default meta should contain all required fields."""
    result = get_default_meta()

    # Check for required fields
    assert "version" in result
    assert "created_at" in result
    assert "last_updated" in result
    assert "files_documented" in result
    assert "modules_count" in result


def test_get_default_meta_field_types():
    """Default meta fields should have correct types."""
    result = get_default_meta()

    assert isinstance(result["version"], str)
    assert isinstance(result["created_at"], str)
    assert result["last_updated"] is None
    assert isinstance(result["files_documented"], int)
    assert isinstance(result["modules_count"], int)


def test_get_default_meta_initial_values():
    """Default meta should have correct initial values."""
    result = get_default_meta()

    assert result["version"] == "2.0.0"
    assert result["last_updated"] is None
    assert result["files_documented"] == 0
    assert result["modules_count"] == 0


def test_get_default_meta_created_at_is_iso_format():
    """created_at should be in ISO 8601 format."""
    result = get_default_meta()

    # Should be parseable as ISO datetime
    created_at = result["created_at"]
    assert isinstance(created_at, str)
    # Basic ISO format check
    datetime.fromisoformat(created_at.replace("Z", "+00:00"))


# --- init_mini_wiki success ---


def test_init_mini_wiki_success(tmp_path):
    """Successfully initialize .mini-wiki directory structure."""
    # Arrange
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Act
    result = init_mini_wiki(str(project_root), force=False)

    # Assert
    assert result["success"] is True
    assert len(result["created"]) > 0
    assert result["skipped"] == []
    assert "成功初始化" in result["message"]


def test_init_mini_wiki_creates_directory_structure(tmp_path):
    """Verify all required directories are created."""
    # Arrange
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Act
    init_mini_wiki(str(project_root), force=False)

    # Assert - check directory structure
    wiki_dir = project_root / ".mini-wiki"
    assert wiki_dir.exists()
    assert (wiki_dir / "cache").exists()
    assert (wiki_dir / "wiki").exists()
    assert (wiki_dir / "wiki" / "modules").exists()
    assert (wiki_dir / "wiki" / "api").exists()
    assert (wiki_dir / "wiki" / "assets").exists()
    assert (wiki_dir / "i18n").exists()
    assert (wiki_dir / "i18n" / "en").exists()
    assert (wiki_dir / "i18n" / "zh").exists()


def test_init_mini_wiki_creates_config_file(tmp_path):
    """Verify config.yaml is created with correct content."""
    # Arrange
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Act
    init_mini_wiki(str(project_root), force=False)

    # Assert
    config_path = project_root / ".mini-wiki" / "config.yaml"
    assert config_path.exists()

    content = config_path.read_text(encoding="utf-8")
    assert "generation:" in content
    assert "exclude:" in content
    assert "language:" in content


def test_init_mini_wiki_creates_meta_file(tmp_path):
    """Verify meta.json is created with correct structure."""
    # Arrange
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Act
    init_mini_wiki(str(project_root), force=False)

    # Assert
    meta_path = project_root / ".mini-wiki" / "meta.json"
    assert meta_path.exists()

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert "version" in meta
    assert "created_at" in meta
    assert "last_updated" in meta
    assert "files_documented" in meta
    assert "modules_count" in meta


def test_init_mini_wiki_creates_cache_files(tmp_path):
    """Verify cache files are created."""
    # Arrange
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Act
    init_mini_wiki(str(project_root), force=False)

    # Assert
    cache_dir = project_root / ".mini-wiki" / "cache"
    assert (cache_dir / "checksums.json").exists()
    assert (cache_dir / "structure.json").exists()

    # Verify checksums.json is empty dict
    with open(cache_dir / "checksums.json", "r") as f:
        checksums = json.load(f)
    assert checksums == {}

    # Verify structure.json has correct keys
    with open(cache_dir / "structure.json", "r") as f:
        structure = json.load(f)
    assert "project_type" in structure
    assert "entry_points" in structure
    assert "modules" in structure
    assert "docs_found" in structure
