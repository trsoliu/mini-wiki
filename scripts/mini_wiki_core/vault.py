"""Obsidian-compatible Markdown rendering with protected content regions."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import yaml

from mini_wiki_core import __version__

if TYPE_CHECKING:
    from mini_wiki_core.models import KnowledgeGraph, Node

GENERATED_START = "<!-- mini-wiki:generated:start -->"
GENERATED_END = "<!-- mini-wiki:generated:end -->"
CONTENT_START = "<!-- mini-wiki:content:start -->"
CONTENT_END = "<!-- mini-wiki:content:end -->"

MANAGED_PROPERTIES = frozenset(
    {
        "id",
        "title",
        "type",
        "status",
        "domain",
        "aliases",
        "tags",
        "sources",
        "source_hash",
        "source_count",
        "freshness",
        "orphan",
        "backlink_count",
        "quality",
        "mini_wiki_version",
    }
)


def _frontmatter(text: str) -> tuple[dict[str, Any], str] | None:
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return None
    try:
        properties = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(properties, dict):
        return None
    return properties, parts[2]


def _dump_frontmatter(properties: dict[str, Any]) -> str:
    body = yaml.safe_dump(properties, allow_unicode=True, sort_keys=False).rstrip()
    return f"---\n{body}\n---\n"


def _region(text: str, start_marker: str, end_marker: str) -> str | None:
    start = text.find(start_marker)
    if start < 0:
        return None
    content_start = start + len(start_marker)
    end = text.find(end_marker, content_start)
    if end < 0:
        return None
    return text[content_start:end]


def is_managed_document(text: str) -> bool:
    """Return whether all Mini-Wiki ownership markers are present and ordered."""
    generated = _region(text, GENERATED_START, GENERATED_END)
    content = _region(text, CONTENT_START, CONTENT_END)
    return _frontmatter(text) is not None and generated is not None and content is not None


def _source_paths(node: Node) -> tuple[str, ...]:
    value = node.metadata.get("sources", ())
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(sorted(str(item) for item in value))


def _source_hash(graph: KnowledgeGraph, sources: tuple[str, ...]) -> str:
    if not sources:
        return ""
    digest = hashlib.sha256()
    for path in sources:
        source = graph.nodes.get(f"mw:source:{path}")
        source_digest = "" if source is None else str(source.metadata.get("sha256", ""))
        digest.update(f"{path}\0{source_digest}\n".encode())
    return f"sha256:{digest.hexdigest()}"


def _backlink_count(node: Node, graph: KnowledgeGraph) -> int:
    incoming_documents = {
        edge.source_id
        for edge in graph.edges
        if edge.target_id == node.id
        and edge.source_id in graph.nodes
        and graph.nodes[edge.source_id].kind == "document"
    }
    if node.id != "mw:document:index":
        incoming_documents.add("mw:document:index")
    return len(incoming_documents)


def document_properties(node: Node, graph: KnowledgeGraph) -> dict[str, Any]:
    """Build the flat Property mapping used by Markdown and Bases."""
    document_type = str(node.metadata.get("document_type", node.kind))
    domain = str(node.metadata.get("domain", ""))
    aliases = tuple(sorted(str(alias) for alias in node.metadata.get("aliases", ())))
    sources = _source_paths(node)
    tags = [f"mini-wiki/{document_type}"]
    if domain:
        tags.append(f"domain/{domain}")
    return {
        "id": node.id,
        "title": node.title,
        "type": document_type,
        "status": str(node.metadata.get("status", "generated")),
        "domain": domain,
        "aliases": list(aliases),
        "tags": sorted(tags),
        "sources": list(sources),
        "source_hash": _source_hash(graph, sources),
        "source_count": len(sources),
        "freshness": "current",
        "orphan": False,
        "backlink_count": _backlink_count(node, graph),
        "quality": str(node.metadata.get("quality", "basic")),
        "mini_wiki_version": __version__,
    }


def relative_source_link(
    document_path: Path,
    source_path: Path,
    lines: tuple[int, int] | None = None,
) -> str:
    """Render a portable source link relative to a repository Markdown file."""
    if document_path.is_absolute() or source_path.is_absolute():
        raise ValueError("Source links require repository-relative paths")
    relative = Path(os.path.relpath(source_path, document_path.parent)).as_posix()
    label = source_path.as_posix()
    suffix = ""
    if lines is not None:
        start, end = lines
        if start < 1 or end < start:
            raise ValueError("Source line range is invalid")
        label = f"{label}:{start}-{end}"
        suffix = f"#L{start}-L{end}"
    return f"[{label}]({quote(relative, safe='/._-')}{suffix})"


def _vault_path(path: Path) -> Path:
    if path.parts and path.parts[0] == "wiki":
        return Path(*path.parts[1:])
    return path


def render_internal_link(current: Path, target: Path, label: str, link_style: str) -> str:
    """Render an internal Vault link in Wikilink or portable Markdown form."""
    if link_style == "wikilink":
        vault_target = _vault_path(target).with_suffix("").as_posix()
        return f"[[{vault_target}|{label}]]"
    if link_style == "markdown":
        relative = Path(os.path.relpath(target, current.parent)).as_posix()
        return f"[{label}]({quote(relative, safe='/._-')})"
    raise ValueError(f"Unsupported link style: {link_style}")


def _related_documents(node: Node, graph: KnowledgeGraph) -> list[Node]:
    related_ids: set[str] = set()
    if node.id == "mw:document:index":
        related_ids.update(node_id for node_id, candidate in graph.nodes.items() if candidate.kind == "document")
    else:
        related_ids.add("mw:document:index")
        for edge in graph.edges:
            if edge.type not in {"related_to", "references"}:
                continue
            if edge.source_id == node.id:
                related_ids.add(edge.target_id)
            elif edge.target_id == node.id:
                related_ids.add(edge.source_id)
    related_ids.discard(node.id)
    return sorted(
        (
            graph.nodes[node_id]
            for node_id in related_ids
            if node_id in graph.nodes and graph.nodes[node_id].kind == "document" and graph.nodes[node_id].path
        ),
        key=lambda candidate: candidate.id,
    )


def _generated_region(node: Node, graph: KnowledgeGraph, link_style: str) -> str:
    if node.path is None:
        raise ValueError(f"Document node has no path: {node.id}")
    current = Path(node.path)
    source_lines = [f"- {relative_source_link(current, Path(path))}" for path in _source_paths(node)]
    if not source_lines:
        source_lines = ["- No direct source files; this document summarizes project-level knowledge."]
    related_lines = [
        f"- {render_internal_link(current, Path(candidate.path or ''), candidate.title, link_style)}"
        for candidate in _related_documents(node, graph)
    ]
    if not related_lines:
        related_lines = ["- No related documents yet."]
    return "\n".join(
        [
            f"# {node.title}",
            "",
            "> This navigation and traceability region is managed by Mini-Wiki.",
            "",
            "## Source trace",
            "",
            *source_lines,
            "",
            "## Related documents",
            "",
            *related_lines,
        ]
    )


def _new_document(node: Node, graph: KnowledgeGraph, link_style: str) -> str:
    properties = document_properties(node, graph)
    generated = _generated_region(node, graph, link_style)
    return (
        _dump_frontmatter(properties)
        + "\n"
        + GENERATED_START
        + "\n"
        + generated
        + "\n"
        + GENERATED_END
        + "\n\n"
        + CONTENT_START
        + "\n## Overview\n\nAgent content pending.\n"
        + CONTENT_END
        + "\n"
    )


def merge_managed_document(existing: str | None, generated: str) -> str:
    """Merge generated ownership regions while preserving user content and properties."""
    if existing is None:
        return generated
    if not is_managed_document(existing) or not is_managed_document(generated):
        return existing

    existing_frontmatter = _frontmatter(existing)
    generated_frontmatter = _frontmatter(generated)
    if existing_frontmatter is None or generated_frontmatter is None:
        return existing
    existing_properties, _ = existing_frontmatter
    generated_properties, generated_body = generated_frontmatter
    merged_properties = dict(generated_properties)
    for key in sorted(existing_properties):
        if key not in MANAGED_PROPERTIES:
            merged_properties[key] = existing_properties[key]

    preserved_content = _region(existing, CONTENT_START, CONTENT_END)
    generated_content = _region(generated_body, CONTENT_START, CONTENT_END)
    if preserved_content is None or generated_content is None:
        return existing
    content_start = generated_body.index(CONTENT_START) + len(CONTENT_START)
    content_end = generated_body.index(CONTENT_END, content_start)
    merged_body = generated_body[:content_start] + preserved_content + generated_body[content_end:]
    return _dump_frontmatter(merged_properties) + merged_body


def render_document(
    node: Node,
    graph: KnowledgeGraph,
    existing_text: str | None,
    link_style: str = "wikilink",
) -> str:
    """Render one document and merge it with an existing managed file if present."""
    if node.kind != "document":
        raise ValueError(f"Expected document node, got {node.kind}: {node.id}")
    generated = _new_document(node, graph, link_style)
    return merge_managed_document(existing_text, generated)
