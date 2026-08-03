"""Tests for deterministic JSON Canvas 1.0 projections."""

import json
from pathlib import Path

import pytest

from mini_wiki_core.canvas import render_default_canvases, validate_canvas
from mini_wiki_core.models import Edge, KnowledgeGraph, Node


@pytest.fixture
def sample_graph() -> KnowledgeGraph:
    nodes = {
        "mw:project:demo": Node("mw:project:demo", "project", "Demo", "wiki/index.md"),
        "mw:document:core": Node(
            "mw:document:core",
            "document",
            "Core",
            "wiki/domains/core/core.md",
            {"document_type": "module", "domain": "core"},
        ),
    }
    return KnowledgeGraph(nodes, [Edge("mw:project:demo", "mw:document:core", "contains")])


@pytest.fixture
def large_graph() -> KnowledgeGraph:
    nodes = {
        f"mw:document:module-{index}": Node(
            f"mw:document:module-{index}",
            "document",
            f"Module {index}",
            f"wiki/domains/core/module-{index}.md",
            {"document_type": "module", "domain": "core"},
        )
        for index in range(30)
    }
    return KnowledgeGraph(nodes, [])


def test_canvas_is_deterministic_and_uses_only_standard_fields(sample_graph: KnowledgeGraph):
    first = render_default_canvases(sample_graph, max_nodes=200)
    reversed_graph = KnowledgeGraph(
        dict(reversed(list(sample_graph.nodes.items()))),
        list(reversed(sample_graph.edges)),
    )
    second = render_default_canvases(reversed_graph, max_nodes=200)

    assert first == second
    payload = json.loads(first.files[Path("wiki/canvas/architecture.canvas")])
    assert set(payload) == {"nodes", "edges"}
    assert all(
        set(node)
        <= {
            "id",
            "type",
            "file",
            "subpath",
            "text",
            "url",
            "label",
            "background",
            "backgroundStyle",
            "x",
            "y",
            "width",
            "height",
            "color",
        }
        for node in payload["nodes"]
    )
    assert all(
        set(edge)
        <= {
            "id",
            "fromNode",
            "fromSide",
            "fromEnd",
            "toNode",
            "toSide",
            "toEnd",
            "color",
            "label",
        }
        for edge in payload["edges"]
    )


def test_canvas_aggregates_when_node_limit_is_exceeded(large_graph: KnowledgeGraph):
    artifacts = render_default_canvases(large_graph, max_nodes=10)
    payload = json.loads(artifacts.files[Path("wiki/canvas/domains.canvas")])

    assert len(payload["nodes"]) <= 10
    assert any("aggregated_count" in warning for warning in artifacts.warnings)
    assert any(node["type"] == "text" and "aggregated" in node["text"] for node in payload["nodes"])


def test_file_nodes_use_vault_relative_document_targets(sample_graph: KnowledgeGraph):
    artifact = render_default_canvases(sample_graph, max_nodes=200)
    payload = json.loads(artifact.files[Path("wiki/canvas/architecture.canvas")])

    assert validate_canvas(Path("architecture.canvas"), payload) == []
    file_nodes = [node for node in payload["nodes"] if node["type"] == "file"]
    assert file_nodes[0]["file"] == "domains/core/core.md"
    assert all(not Path(node["file"]).is_absolute() for node in file_nodes)


def test_canvas_validation_rejects_duplicate_ids_and_bad_geometry():
    payload = {
        "nodes": [
            {"id": "n1", "type": "text", "text": "A", "x": 0, "y": 0, "width": 100, "height": 100},
            {"id": "n1", "type": "text", "text": "B", "x": "0", "y": 0, "width": 100, "height": 100},
        ],
        "edges": [{"id": "e1", "fromNode": "n1", "toNode": "missing"}],
    }

    issues = validate_canvas(Path("broken.canvas"), payload)

    assert {issue.code for issue in issues} >= {"CANVAS_DUPLICATE_ID", "CANVAS_GEOMETRY_INVALID", "CANVAS_EDGE_INVALID"}
