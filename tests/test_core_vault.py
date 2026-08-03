"""Tests for Obsidian-compatible managed Markdown."""

from pathlib import Path

import yaml

from mini_wiki_core.config import load_config
from mini_wiki_core.graph import build_knowledge_graph
from mini_wiki_core.scanner import scan_sources
from mini_wiki_core.vault import (
    CONTENT_END,
    CONTENT_START,
    GENERATED_END,
    GENERATED_START,
    merge_managed_document,
    relative_source_link,
    render_document,
    render_internal_link,
)


def module_document(v3_project: Path):
    config = load_config(v3_project)
    graph = build_knowledge_graph(config, scan_sources(config))
    return graph.nodes["mw:document:domains/core/core"], graph


def frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_rendered_document_has_flat_properties_and_no_private_path(v3_project: Path):
    node, graph = module_document(v3_project)

    text = render_document(node, graph, None)
    properties = frontmatter(text)

    assert properties["id"] == node.id
    assert properties["type"] == "module"
    assert properties["domain"] == "core"
    assert properties["orphan"] is False
    assert properties["source_count"] == 1
    assert isinstance(properties["sources"], list)
    assert properties["sources"] == ["src/core/app.py"]
    assert properties["source_hash"].startswith("sha256:")
    assert str(v3_project) not in text
    assert "file://" not in text
    assert GENERATED_START in text
    assert CONTENT_START in text


def test_rendered_document_is_deterministic(v3_project: Path):
    node, graph = module_document(v3_project)

    assert render_document(node, graph, None) == render_document(node, graph, None)


def test_rebuild_preserves_agent_content_and_custom_property_byte_for_byte(v3_project: Path):
    node, graph = module_document(v3_project)
    generated = render_document(node, graph, None)
    existing = generated.replace(
        "mini_wiki_version: 3.3.0",
        "mini_wiki_version: 3.2.0\nowner: architecture-team",
    ).replace(
        f"{CONTENT_START}\n## Overview\n\nAgent content pending.\n{CONTENT_END}",
        f"{CONTENT_START}\n## 手工说明\n保留  两个空格\n{CONTENT_END}",
    )

    merged = merge_managed_document(existing, generated)

    assert f"{CONTENT_START}\n## 手工说明\n保留  两个空格\n{CONTENT_END}" in merged
    assert "owner: architecture-team" in merged
    assert "mini_wiki_version: 3.3.0" in merged
    assert "mini_wiki_version: 3.2.0" not in merged


def test_unmarked_user_document_is_not_adopted_or_overwritten(v3_project: Path):
    node, graph = module_document(v3_project)
    existing = "# Private notes\n\nDo not rewrite.\n"

    merged = merge_managed_document(existing, render_document(node, graph, None))

    assert merged == existing


def test_source_link_is_relative_to_nested_document():
    link = relative_source_link(
        Path("wiki/domains/core/plugin-system.md"),
        Path("scripts/plugin_manager.py"),
        (42, 88),
    )

    assert link == "[scripts/plugin_manager.py:42-88](../../../scripts/plugin_manager.py#L42-L88)"


def test_internal_link_supports_wikilink_and_markdown_styles():
    current = Path("wiki/domains/core/core.md")
    target = Path("wiki/architecture.md")

    assert render_internal_link(current, target, "Architecture", "wikilink") == "[[architecture|Architecture]]"
    assert render_internal_link(current, target, "Architecture", "markdown") == "[Architecture](../../architecture.md)"


def test_managed_markers_are_balanced(v3_project: Path):
    node, graph = module_document(v3_project)
    text = render_document(node, graph, None)

    assert text.count(GENERATED_START) == text.count(GENERATED_END) == 1
    assert text.count(CONTENT_START) == text.count(CONTENT_END) == 1
