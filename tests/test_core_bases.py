"""Tests for deterministic native Obsidian Bases artifacts."""

from pathlib import Path

import yaml

from mini_wiki_core.bases import render_default_bases, validate_base


def test_default_bases_are_parseable_official_shape_and_deterministic():
    first = render_default_bases()
    second = render_default_bases()

    assert first == second
    assert set(first) == {
        Path("wiki/views/modules.base"),
        Path("wiki/views/sources.base"),
        Path("wiki/views/quality.base"),
        Path("wiki/views/orphans.base"),
    }
    for path, content in first.items():
        parsed = yaml.safe_load(content)
        assert parsed["filters"]["and"][0] == 'file.ext == "md"'
        assert parsed["views"][0]["type"] == "table"
        assert all(isinstance(item, str) for item in parsed["views"][0]["order"])
        assert validate_base(path, content) == []


def test_base_properties_query_flat_note_properties():
    modules = yaml.safe_load(render_default_bases()[Path("wiki/views/modules.base")])

    assert 'type == "module"' in modules["filters"]["and"]
    assert "note.domain" in modules["views"][0]["order"]
    assert modules["properties"]["note.domain"]["displayName"] == "Domain"


def test_base_validation_rejects_invalid_view_and_order():
    issues = validate_base(
        Path("wiki/views/broken.base"),
        "views:\n  - type: unsupported\n    name: Broken\n    order: invalid\n",
    )

    assert issues
    assert {issue.code for issue in issues} == {"INVALID_BASE"}
    assert all(issue.severity == "error" for issue in issues)
