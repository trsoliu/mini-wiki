"""Core data models for deterministic Mini-Wiki builds."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class SourceFile:
    """A repository-relative source file and its stable content identity."""

    path: Path
    sha256: str
    language: str
    size: int


@dataclass(frozen=True)
class Node:
    """A typed knowledge-graph node."""

    id: str
    kind: str
    title: str
    path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, order=True)
class Edge:
    """A directed, typed knowledge-graph relationship."""

    source_id: str
    target_id: str
    type: str


@dataclass
class KnowledgeGraph:
    """A stable collection of nodes, edges, and non-fatal analysis warnings."""

    nodes: dict[str, Node]
    edges: list[Edge]
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible mapping with stable ordering."""
        return {
            "nodes": {node_id: asdict(self.nodes[node_id]) for node_id in sorted(self.nodes)},
            "edges": [asdict(edge) for edge in sorted(set(self.edges))],
            "warnings": list(self.warnings),
        }
