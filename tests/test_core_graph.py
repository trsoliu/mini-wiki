"""Tests for stable Mini-Wiki knowledge graphs."""

import json
from pathlib import Path

from mini_wiki_core.config import load_config
from mini_wiki_core.graph import build_knowledge_graph
from mini_wiki_core.models import Edge
from mini_wiki_core.scanner import scan_sources


def test_graph_is_stable_when_source_input_order_changes(v3_project: Path):
    config = load_config(v3_project)
    sources = scan_sources(config)

    first = build_knowledge_graph(config, sources).to_dict()
    second = build_knowledge_graph(config, list(reversed(sources))).to_dict()

    assert first == second
    assert "mw:source:src/core/app.py" in first["nodes"]
    assert any(edge["type"] == "documents" for edge in first["edges"])
    assert str(v3_project) not in json.dumps(first)


def test_python_symbols_and_internal_dependencies_become_graph_edges(v3_project: Path):
    (v3_project / "src" / "core" / "a.py").write_text(
        "from src.core import b\n\ndef install_plugin():\n    return b.VALUE\n"
    )
    (v3_project / "src" / "core" / "b.py").write_text("VALUE = 1\n")
    config = load_config(v3_project)

    graph = build_knowledge_graph(config, scan_sources(config))

    assert "mw:symbol:src/core/a.py#install_plugin" in graph.nodes
    assert (
        Edge(
            "mw:symbol:src/core/a.py#install_plugin",
            "mw:source:src/core/a.py",
            "defined_in",
        )
        in graph.edges
    )
    assert (
        Edge(
            "mw:source:src/core/a.py",
            "mw:source:src/core/b.py",
            "depends_on",
        )
        in graph.edges
    )


def test_graph_maps_multiple_sources_to_one_module_document(v3_project: Path):
    (v3_project / "src" / "core" / "extra.py").write_text("def extra():\n    return True\n")
    config = load_config(v3_project)

    graph = build_knowledge_graph(config, scan_sources(config))
    document = graph.nodes["mw:document:domains/core/core"]

    assert document.path == "wiki/domains/core/core.md"
    assert document.metadata["sources"] == ("src/core/app.py", "src/core/extra.py")
    generated_from = [edge for edge in graph.edges if edge.source_id == document.id and edge.type == "generated_from"]
    assert len(generated_from) == 2
