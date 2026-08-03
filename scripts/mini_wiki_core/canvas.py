"""Deterministic JSON Canvas 1.0 projections of the Mini-Wiki graph."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mini_wiki_core.models import KnowledgeGraph, Node

if TYPE_CHECKING:
    from mini_wiki_core.models import Edge

NODE_TYPES = frozenset({"text", "file", "link", "group"})
NODE_FIELDS = frozenset(
    {
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
)
EDGE_FIELDS = frozenset(
    {
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
)
SIDES = frozenset({"top", "right", "bottom", "left"})
ENDS = frozenset({"none", "arrow"})


@dataclass(frozen=True)
class CanvasArtifact:
    files: dict[Path, str]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanvasIssue:
    code: str
    severity: str
    path: str
    message: str


def canvas_id(prefix: str, stable_value: str) -> str:
    digest = hashlib.sha256(stable_value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def grid_position(index: int, columns: int = 4) -> tuple[int, int]:
    if columns < 1:
        raise ValueError("Canvas grid columns must be greater than zero")
    return (index % columns) * 420, (index // columns) * 260


def dump_canvas(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    payload = {
        "nodes": sorted(nodes, key=lambda node: str(node["id"])),
        "edges": sorted(edges, key=lambda edge: str(edge["id"])),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _vault_file(path: str) -> str:
    candidate = Path(path)
    if candidate.parts and candidate.parts[0] == "wiki":
        candidate = Path(*candidate.parts[1:])
    return candidate.as_posix()


def _domain(node: Node) -> str:
    metadata_domain = node.metadata.get("domain")
    if isinstance(metadata_domain, str) and metadata_domain:
        return metadata_domain
    if node.path:
        parts = Path(node.path).parts
        if "domains" in parts:
            index = parts.index("domains")
            if index + 1 < len(parts):
                return parts[index + 1]
    return node.kind


def _aggregate(nodes: list[Node], max_nodes: int, canvas_name: str) -> tuple[list[Node], list[str]]:
    ordered = sorted(nodes, key=lambda node: node.id)
    if len(ordered) <= max_nodes:
        return ordered, []

    grouped: dict[str, list[Node]] = defaultdict(list)
    for node in ordered:
        grouped[_domain(node)].append(node)
    domain_items = sorted(grouped.items())
    warnings = [
        f"{canvas_name}: aggregated_count={len(ordered)} original nodes into domain summaries (max_nodes={max_nodes})"
    ]
    if len(domain_items) > max_nodes:
        kept = domain_items[: max(0, max_nodes - 1)]
        overflow = domain_items[len(kept) :]
        domain_items = kept
        if overflow:
            combined = [node for _, group in overflow for node in group]
            domain_items.append(("other", combined))

    aggregated = []
    for domain, members in domain_items:
        count = len(members)
        aggregated.append(
            Node(
                id=f"mw:canvas-summary:{canvas_name}:{domain}",
                kind="aggregation",
                title=domain.replace("-", " ").replace("_", " ").title(),
                metadata={"aggregated_count": count, "domain": domain},
            )
        )
    return aggregated[:max_nodes], warnings


def _node_payload(node: Node, index: int) -> dict[str, Any]:
    x, y = grid_position(index)
    common: dict[str, Any] = {
        "id": canvas_id("node", node.id),
        "x": x,
        "y": y,
        "width": 340,
        "height": 180,
    }
    if node.kind == "document" and node.path:
        return {**common, "type": "file", "file": _vault_file(node.path), "color": "5"}
    if node.kind == "aggregation":
        count = int(node.metadata.get("aggregated_count", 0))
        return {
            **common,
            "type": "text",
            "text": f"## {node.title}\n\n{count} nodes aggregated",
            "color": "3",
        }
    return {
        **common,
        "type": "text",
        "text": f"## {node.title}\n\n`{node.kind}`",
        "color": "4" if node.kind in {"project", "domain"} else "6",
    }


def _edge_payload(edge: Edge, included: dict[str, str]) -> dict[str, Any] | None:
    if edge.source_id not in included or edge.target_id not in included:
        return None
    return {
        "id": canvas_id("edge", f"{edge.source_id}|{edge.type}|{edge.target_id}"),
        "fromNode": included[edge.source_id],
        "toNode": included[edge.target_id],
        "toEnd": "arrow",
        "label": edge.type,
    }


def _render_canvas(
    graph: KnowledgeGraph,
    nodes: list[Node],
    max_nodes: int,
    canvas_name: str,
) -> tuple[str, list[str]]:
    selected, warnings = _aggregate(nodes, max_nodes, canvas_name)
    payload_nodes = [_node_payload(node, index) for index, node in enumerate(selected)]
    included = {node.id: str(payload["id"]) for node, payload in zip(selected, payload_nodes, strict=True)}
    payload_edges = []
    if not any(node.kind == "aggregation" for node in selected):
        for edge in sorted(set(graph.edges)):
            payload = _edge_payload(edge, included)
            if payload is not None:
                payload_edges.append(payload)
    return dump_canvas(payload_nodes, payload_edges), warnings


def render_default_canvases(graph: KnowledgeGraph, max_nodes: int) -> CanvasArtifact:
    """Render architecture, domain, and traceability canvases from one graph."""
    if max_nodes < 1:
        raise ValueError("canvas.max_nodes must be greater than zero")
    definitions = {
        "architecture": [
            node for node in graph.nodes.values() if node.kind in {"project", "domain", "module", "document"}
        ],
        "domains": [
            node
            for node in graph.nodes.values()
            if node.kind == "domain"
            or (node.kind == "document" and node.metadata.get("document_type") in {"domain", "module"})
        ],
        "traceability": [node for node in graph.nodes.values() if node.kind in {"document", "source_file", "symbol"}],
    }
    files: dict[Path, str] = {}
    warnings: list[str] = []
    for name, nodes in sorted(definitions.items()):
        content, canvas_warnings = _render_canvas(graph, nodes, max_nodes, name)
        files[Path("wiki/canvas") / f"{name}.canvas"] = content
        warnings.extend(canvas_warnings)
    return CanvasArtifact(files, tuple(sorted(set(warnings))))


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_canvas(path: Path, payload: Any, vault_dir: Path | None = None) -> list[CanvasIssue]:
    """Validate JSON Canvas 1.0 structure and optional Vault file targets."""
    location = path.as_posix()
    issues: list[CanvasIssue] = []
    if not isinstance(payload, dict):
        return [CanvasIssue("INVALID_CANVAS", "error", location, "Canvas root must be an object")]
    unknown_top = sorted(set(payload) - {"nodes", "edges"})
    if unknown_top:
        issues.append(
            CanvasIssue("INVALID_CANVAS", "error", location, f"Unsupported top-level fields: {', '.join(unknown_top)}")
        )
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return [CanvasIssue("INVALID_CANVAS", "error", location, "nodes and edges must be arrays")]

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            issues.append(CanvasIssue("INVALID_CANVAS", "error", location, f"nodes[{index}] must be an object"))
            continue
        unknown = sorted(set(node) - NODE_FIELDS)
        if unknown:
            issues.append(
                CanvasIssue(
                    "INVALID_CANVAS",
                    "error",
                    location,
                    f"nodes[{index}] has unsupported fields: {', '.join(unknown)}",
                )
            )
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            issues.append(CanvasIssue("INVALID_CANVAS", "error", location, f"nodes[{index}].id is required"))
        elif node_id in node_ids:
            issues.append(CanvasIssue("CANVAS_DUPLICATE_ID", "error", location, f"Duplicate node id: {node_id}"))
        else:
            node_ids.add(node_id)
        node_type = node.get("type")
        if node_type not in NODE_TYPES:
            issues.append(
                CanvasIssue("INVALID_CANVAS", "error", location, f"nodes[{index}].type is unsupported: {node_type}")
            )
        for field in ("x", "y", "width", "height"):
            if not _is_integer(node.get(field)):
                issues.append(
                    CanvasIssue(
                        "CANVAS_GEOMETRY_INVALID",
                        "error",
                        location,
                        f"nodes[{index}].{field} must be an integer",
                    )
                )
        required_field = {"text": "text", "file": "file", "link": "url"}.get(str(node_type))
        if required_field and (not isinstance(node.get(required_field), str) or not node[required_field]):
            issues.append(
                CanvasIssue(
                    "INVALID_CANVAS",
                    "error",
                    location,
                    f"nodes[{index}].{required_field} is required for {node_type} nodes",
                )
            )
        if node_type == "file" and isinstance(node.get("file"), str):
            file_path = Path(node["file"])
            if file_path.is_absolute() or ".." in file_path.parts:
                issues.append(
                    CanvasIssue(
                        "INVALID_CANVAS",
                        "error",
                        location,
                        f"nodes[{index}].file must be Vault-relative",
                    )
                )
            elif vault_dir is not None and not (vault_dir / file_path).is_file():
                issues.append(
                    CanvasIssue(
                        "CANVAS_FILE_MISSING",
                        "error",
                        location,
                        f"Canvas file target does not exist: {node['file']}",
                    )
                )
        if node_type == "group" and node.get("backgroundStyle") not in {None, "cover", "ratio", "repeat"}:
            issues.append(
                CanvasIssue("INVALID_CANVAS", "error", location, f"nodes[{index}].backgroundStyle is invalid")
            )

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(CanvasIssue("INVALID_CANVAS", "error", location, f"edges[{index}] must be an object"))
            continue
        unknown = sorted(set(edge) - EDGE_FIELDS)
        if unknown:
            issues.append(
                CanvasIssue(
                    "INVALID_CANVAS",
                    "error",
                    location,
                    f"edges[{index}] has unsupported fields: {', '.join(unknown)}",
                )
            )
        edge_id = edge.get("id")
        if not isinstance(edge_id, str) or not edge_id:
            issues.append(CanvasIssue("CANVAS_EDGE_INVALID", "error", location, f"edges[{index}].id is required"))
        elif edge_id in edge_ids:
            issues.append(CanvasIssue("CANVAS_DUPLICATE_ID", "error", location, f"Duplicate edge id: {edge_id}"))
        else:
            edge_ids.add(edge_id)
        if edge.get("fromNode") not in node_ids or edge.get("toNode") not in node_ids:
            issues.append(
                CanvasIssue("CANVAS_EDGE_INVALID", "error", location, f"edges[{index}] references a missing node")
            )
        if edge.get("fromSide") not in {None, *SIDES} or edge.get("toSide") not in {None, *SIDES}:
            issues.append(CanvasIssue("CANVAS_EDGE_INVALID", "error", location, f"edges[{index}] side is invalid"))
        if edge.get("fromEnd") not in {None, *ENDS} or edge.get("toEnd") not in {None, *ENDS}:
            issues.append(CanvasIssue("CANVAS_EDGE_INVALID", "error", location, f"edges[{index}] end is invalid"))

    issues.sort(key=lambda issue: (issue.code, issue.message))
    return issues
