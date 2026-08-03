"""Deterministic knowledge-graph construction."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from mini_wiki_core.models import Edge, KnowledgeGraph, Node, SourceFile
from mini_wiki_core.source_analysis import SourceAnalysis, analyze_source

if TYPE_CHECKING:
    from mini_wiki_core.config import WikiConfig


def stable_key(value: str) -> str:
    """Normalize a user or path value for use in a stable graph ID."""
    normalized = unicodedata.normalize("NFKC", value).replace("\\", "/").strip(" /")
    normalized = re.sub(r"\s+", "-", normalized)
    return re.sub(r"[^\w./#-]", "-", normalized, flags=re.UNICODE)


def stable_id(kind: str, value: str) -> str:
    return f"mw:{kind}:{stable_key(value)}"


def _module_name(path: Path) -> str:
    parts = path.parts
    if not parts:
        return "root"
    if parts[0] in {"src", "lib", "packages", "apps"}:
        if len(parts) >= 3:
            return parts[1]
        if len(parts) == 2:
            return path.stem
    return parts[0] if len(parts) > 1 else "root"


def _domain_name(module: str) -> str:
    lowered = module.casefold()
    domains = {
        "api": ("api", "server", "backend"),
        "core": ("core", "engine", "runtime"),
        "storage": ("store", "storage", "database", "db", "persist"),
        "interface": ("ui", "component", "frontend", "view", "editor"),
        "platform": ("electron", "desktop", "web", "mobile", "app"),
        "tooling": ("script", "cli", "tool", "plugin"),
    }
    for domain, keywords in domains.items():
        if any(keyword in lowered for keyword in keywords):
            return domain
    return "general"


def _title(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip().title() or "Root"


def _import_candidates(import_name: str, source_path: Path, source_paths: set[str]) -> list[str]:
    candidates: list[PurePosixPath] = []
    if import_name.startswith("."):
        base = PurePosixPath(source_path.parent.as_posix())
        cleaned = import_name
        while cleaned.startswith("../"):
            base = base.parent
            cleaned = cleaned[3:]
        cleaned = cleaned.removeprefix("./")
        candidates.append(base / cleaned)
    elif import_name.startswith(("src.", "lib.", "scripts.", "packages.")):
        candidates.append(PurePosixPath(import_name.replace(".", "/")))
    else:
        return []

    resolved: list[str] = []
    suffixes = ("", ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".go", "/__init__.py", "/index.ts")
    for candidate in candidates:
        base_text = candidate.as_posix()
        for suffix in suffixes:
            path = base_text + suffix
            if path in source_paths:
                resolved.append(path)
    return sorted(set(resolved))


def _hub_documents(project_id: str, sources: tuple[str, ...]) -> tuple[list[Node], list[Edge]]:
    definitions = (
        ("index", "Project Home", "wiki/index.md", "project"),
        ("getting-started", "Getting Started", "wiki/getting-started.md", "guide"),
        ("architecture", "Architecture", "wiki/architecture.md", "architecture"),
        ("knowledge-map", "Knowledge Map", "wiki/knowledge-map.md", "map"),
    )
    nodes: list[Node] = []
    edges: list[Edge] = []
    for key, title, path, document_type in definitions:
        node = Node(
            id=stable_id("document", key),
            kind="document",
            title=title,
            path=path,
            metadata={"document_type": document_type, "sources": sources},
        )
        nodes.append(node)
        edges.append(Edge(node.id, project_id, "documents"))
    return nodes, edges


def build_knowledge_graph(config: WikiConfig, sources: list[SourceFile]) -> KnowledgeGraph:
    """Build a stable, repository-relative graph from scanned source files."""
    ordered_sources = sorted(sources, key=lambda item: item.path.as_posix())
    analyses: dict[str, SourceAnalysis] = {}
    warnings: list[str] = []
    for source in ordered_sources:
        analysis = analyze_source(config.project_root, source)
        analyses[source.path.as_posix()] = analysis
        warnings.extend(analysis.warnings)

    nodes: dict[str, Node] = {}
    edge_set: set[Edge] = set()
    project_name = config.project_root.name or "project"
    project_id = stable_id("project", project_name)
    nodes[project_id] = Node(project_id, "project", project_name, "wiki/index.md")

    source_paths = {source.path.as_posix() for source in ordered_sources}
    all_source_paths = tuple(sorted(source_paths))
    hub_nodes, hub_edges = _hub_documents(project_id, all_source_paths)
    nodes.update({node.id: node for node in hub_nodes})
    edge_set.update(hub_edges)

    by_module: dict[str, list[SourceFile]] = defaultdict(list)
    for source in ordered_sources:
        by_module[_module_name(source.path)].append(source)

    by_domain: dict[str, list[SourceFile]] = defaultdict(list)
    for module, module_sources in by_module.items():
        by_domain[_domain_name(module)].extend(module_sources)

    source_to_document: dict[str, str] = {}
    for module in sorted(by_module):
        module_sources = sorted(by_module[module], key=lambda item: item.path.as_posix())
        domain = _domain_name(module)
        domain_id = stable_id("domain", domain)
        module_id = stable_id("module", module)
        document_key = f"domains/{domain}/{module}"
        document_id = stable_id("document", document_key)
        document_path = f"wiki/{document_key}.md"

        nodes.setdefault(domain_id, Node(domain_id, "domain", _title(domain), f"wiki/domains/{domain}/_index.md"))
        nodes[module_id] = Node(
            module_id,
            "module",
            _title(module),
            metadata={"domain": domain, "sources": tuple(item.path.as_posix() for item in module_sources)},
        )
        nodes[document_id] = Node(
            document_id,
            "document",
            _title(module),
            document_path,
            {
                "document_type": "module",
                "domain": domain,
                "module": module,
                "sources": tuple(item.path.as_posix() for item in module_sources),
            },
        )
        edge_set.update(
            {
                Edge(project_id, domain_id, "contains"),
                Edge(domain_id, module_id, "contains"),
                Edge(document_id, module_id, "documents"),
            }
        )

        for source in module_sources:
            path_text = source.path.as_posix()
            source_id = stable_id("source", path_text)
            analysis = analyses[path_text]
            nodes[source_id] = Node(
                source_id,
                "source_file",
                source.path.name,
                path_text,
                {
                    "sha256": source.sha256,
                    "language": source.language,
                    "size": source.size,
                    "imports": analysis.imports,
                    "symbols": analysis.symbols,
                },
            )
            source_to_document[path_text] = document_id
            edge_set.add(Edge(module_id, source_id, "contains"))
            edge_set.add(Edge(document_id, source_id, "generated_from"))
            for symbol in analysis.symbols:
                symbol_id = stable_id("symbol", f"{path_text}#{symbol}")
                nodes[symbol_id] = Node(symbol_id, "symbol", symbol, metadata={"source": path_text})
                edge_set.add(Edge(symbol_id, source_id, "defined_in"))

    for domain in sorted(by_domain):
        domain_id = stable_id("domain", domain)
        document_key = f"domains/{domain}/_index"
        document_id = stable_id("document", document_key)
        domain_sources = tuple(sorted(source.path.as_posix() for source in by_domain[domain]))
        nodes[document_id] = Node(
            document_id,
            "document",
            f"{_title(domain)} Domain",
            f"wiki/{document_key}.md",
            {
                "document_type": "domain",
                "domain": domain,
                "sources": domain_sources,
            },
        )
        edge_set.add(Edge(document_id, domain_id, "documents"))

    for source in ordered_sources:
        path_text = source.path.as_posix()
        source_id = stable_id("source", path_text)
        for import_name in analyses[path_text].imports:
            for target_path in _import_candidates(import_name, source.path, source_paths):
                if target_path == path_text:
                    continue
                target_id = stable_id("source", target_path)
                edge_set.add(Edge(source_id, target_id, "depends_on"))
                source_document = source_to_document.get(path_text)
                target_document = source_to_document.get(target_path)
                if source_document and target_document and source_document != target_document:
                    edge_set.add(Edge(source_document, target_document, "related_to"))

    index_document_id = stable_id("document", "index")
    for node in nodes.values():
        if node.kind == "document" and node.id != index_document_id:
            edge_set.add(Edge(index_document_id, node.id, "references"))

    return KnowledgeGraph(nodes, sorted(edge_set), tuple(sorted(set(warnings))))
