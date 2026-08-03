"""Deterministic Mini-Wiki builds with staged, recoverable file updates."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from analyze_project import analyze_project
from mini_wiki_core import __version__
from mini_wiki_core.bases import render_default_bases
from mini_wiki_core.canvas import render_default_canvases
from mini_wiki_core.config import ConfigError, load_config
from mini_wiki_core.graph import build_knowledge_graph
from mini_wiki_core.scanner import scan_sources
from mini_wiki_core.search import SearchDocument, SearchIndex
from mini_wiki_core.vault import document_properties, is_managed_document, render_document

if TYPE_CHECKING:
    from mini_wiki_core.config import WikiConfig
    from mini_wiki_core.models import KnowledgeGraph, Node, SourceFile


class TransactionError(RuntimeError):
    """Raised when a staged build cannot be committed and is rolled back."""


@dataclass(frozen=True)
class BuildOptions:
    """Options controlling one Mini-Wiki build."""

    full: bool = False
    dry_run: bool = False


@dataclass
class BuildResult:
    """Machine-readable summary of a build or transaction preview."""

    success: bool
    created: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    archived: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> list[str]:
        return sorted({*self.created, *self.modified, *self.archived})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _content_hash(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"


class FileTransaction:
    """Stage repository-relative file changes and commit them with rollback."""

    def __init__(self, project_root: str | Path, state_dir: str | Path):
        self.project_root = Path(project_root).resolve()
        self.state_dir = Path(state_dir).resolve()
        if self.state_dir != self.project_root and self.project_root not in self.state_dir.parents:
            raise TransactionError("Mini-Wiki state directory must be inside the project root")
        staging_root = self.state_dir / "staging"
        staging_root.mkdir(parents=True, exist_ok=True)
        self._stage_dir = Path(tempfile.mkdtemp(prefix="build-", dir=staging_root))
        self._writes: dict[Path, Path] = {}
        self._archives: set[Path] = set()
        self._archive_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

    def _relative(self, path: str | Path) -> Path:
        relative = Path(path)
        if relative.is_absolute() or relative == Path() or ".." in relative.parts:
            raise TransactionError(f"Transaction path must be repository-relative: {path}")
        target = (self.project_root / relative).resolve()
        if target != self.project_root and self.project_root not in target.parents:
            raise TransactionError(f"Transaction path leaves project root: {path}")
        return relative

    def _target(self, relative: Path) -> Path:
        return (self.project_root / relative).resolve()

    def _replace(self, source: Path, destination: Path) -> None:
        os.replace(source, destination)

    def stage_text(self, path: str | Path, content: str) -> None:
        """Stage one UTF-8 text file without touching its destination."""
        self.stage_bytes(path, content.encode("utf-8"))

    def stage_bytes(self, path: str | Path, content: bytes) -> None:
        """Stage one binary file without touching its destination."""
        relative = self._relative(path)
        staged = self._stage_dir / "writes" / relative
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(content)
        self._writes[relative] = staged

    def stage_json(self, path: str | Path, value: Any) -> None:
        self.stage_text(path, _json_text(value))

    def stage_archive(self, path: str | Path) -> None:
        """Stage a managed file move into the Mini-Wiki archive."""
        self._archives.add(self._relative(path))

    def preview(self) -> BuildResult:
        created: list[str] = []
        modified: list[str] = []
        for relative, staged in sorted(self._writes.items()):
            target = self._target(relative)
            if not target.exists():
                created.append(relative.as_posix())
            elif not target.is_file() or target.read_bytes() != staged.read_bytes():
                modified.append(relative.as_posix())
        archived = [relative.as_posix() for relative in sorted(self._archives) if self._target(relative).is_file()]
        return BuildResult(True, created, modified, archived)

    def discard(self) -> None:
        """Remove staged files without changing repository targets."""
        shutil.rmtree(self._stage_dir, ignore_errors=True)

    def _backup(self, relative: Path, backup_root: Path) -> Path | None:
        target = self._target(relative)
        if not target.is_file():
            return None
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup)
        return backup

    def _rollback(
        self,
        changed_writes: list[Path],
        archived_paths: list[Path],
        backups: dict[Path, Path | None],
        archive_destinations: dict[Path, Path],
    ) -> None:
        for relative in reversed(archived_paths):
            destination = archive_destinations[relative]
            if destination.exists():
                destination.unlink()
            backup = backups.get(relative)
            if backup is not None and backup.exists():
                target = self._target(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
        for relative in reversed(changed_writes):
            target = self._target(relative)
            backup = backups.get(relative)
            if backup is None:
                if target.exists():
                    target.unlink()
            elif backup.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)

    def commit(self) -> BuildResult:
        """Commit changed staged files, restoring all targets on any failure."""
        result = self.preview()
        changed = [Path(path) for path in sorted({*result.created, *result.modified})]
        archived = [Path(path) for path in result.archived]
        backup_root = self._stage_dir / "rollback"
        backups = {relative: self._backup(relative, backup_root) for relative in {*changed, *archived}}
        archive_destinations = {
            relative: self.state_dir / "archive" / self._archive_id / relative for relative in archived
        }

        try:
            for relative in changed:
                target = self._target(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                self._replace(self._writes[relative], target)
            for relative in archived:
                source = self._target(relative)
                destination = archive_destinations[relative]
                destination.parent.mkdir(parents=True, exist_ok=True)
                self._replace(source, destination)
        except OSError as exc:
            self._rollback(changed, archived, backups, archive_destinations)
            raise TransactionError(str(exc)) from exc
        finally:
            shutil.rmtree(self._stage_dir, ignore_errors=True)
        return result


def _stable_analysis(project_root: Path) -> dict[str, Any]:
    analysis = analyze_project(str(project_root), save_to_cache=False)
    analysis.pop("analyzed_at", None)
    for key in ("project_type", "entry_points", "docs_found"):
        value = analysis.get(key)
        if isinstance(value, list):
            analysis[key] = sorted(value, key=str)
    modules = analysis.get("modules")
    if isinstance(modules, list):
        analysis["modules"] = sorted(modules, key=lambda item: str(item.get("path", "")))
    return analysis


def _document_target(config: WikiConfig, node: Node) -> Path:
    if node.path is None:
        raise ConfigError(f"Document node has no path: {node.id}")
    graph_path = Path(node.path)
    if not graph_path.parts or graph_path.parts[0] != "wiki":
        raise ConfigError(f"Document path is outside the Vault: {node.path}")
    vault_relative = config.vault_dir.relative_to(config.project_root)
    return vault_relative.joinpath(*graph_path.parts[1:])


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _source_records(sources: list[SourceFile]) -> dict[str, dict[str, Any]]:
    return {
        source.path.as_posix(): {
            "sha256": source.sha256,
            "language": source.language,
            "size": source.size,
        }
        for source in sources
    }


def _agent_plan(graph: KnowledgeGraph, document_records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    documents = []
    for path, record in sorted(document_records.items()):
        documents.append(
            {
                "id": record["id"],
                "path": path,
                "sources": record["sources"],
                "status": "generated",
                "required_content_action": "review_or_enrich",
            }
        )
    return {"schema_version": 3, "documents": documents, "warnings": list(graph.warnings)}


def _search_documents(
    config: WikiConfig,
    graph: KnowledgeGraph,
    artifacts: dict[Path, str],
    targets: dict[str, Path],
) -> list[SearchDocument]:
    documents: list[SearchDocument] = []
    for node in sorted(graph.nodes.values(), key=lambda item: item.id):
        if node.kind != "document" or node.id not in targets:
            continue
        properties = document_properties(node, graph)
        target = targets[node.id]
        sources = tuple(str(item) for item in properties["sources"])
        searchable_parts = [artifacts[target]]
        for source in sources:
            source_path = (config.project_root / source).resolve()
            if source_path.is_file() and config.project_root in source_path.parents:
                try:
                    searchable_parts.append(source_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    continue
        documents.append(
            SearchDocument(
                node_id=node.id,
                title=node.title,
                aliases=tuple(str(item) for item in properties["aliases"]),
                tags=tuple(str(item) for item in properties["tags"]),
                body="\n".join(searchable_parts),
                node_type=str(properties["type"]),
                path=target.as_posix(),
                sources=sources,
            )
        )
    return documents


def _build_search_database(config: WikiConfig, documents: list[SearchDocument]) -> bytes:
    staging_root = config.state_dir / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="search-", dir=staging_root) as temporary:
        database = Path(temporary) / "search.sqlite3"
        index = SearchIndex(database)
        index.update(documents)
        return database.read_bytes()


def build_project(project_root: str | Path, options: BuildOptions | None = None) -> BuildResult:
    """Build the complete Markdown Vault and rebuildable state artifacts."""
    selected_options = options or BuildOptions()
    config = load_config(project_root)
    analysis = _stable_analysis(config.project_root)
    sources = scan_sources(config)
    graph = build_knowledge_graph(config, sources)
    old_manifest = _load_manifest(config.state_dir / "manifest.json")
    warnings = list(graph.warnings)

    artifacts: dict[Path, str] = {}
    document_targets: dict[str, Path] = {}
    document_records: dict[str, dict[str, Any]] = {}
    document_nodes = sorted(
        (node for node in graph.nodes.values() if node.kind == "document"),
        key=lambda node: node.path or "",
    )
    for node in document_nodes:
        target = _document_target(config, node)
        absolute_target = config.project_root / target
        existing = absolute_target.read_text(encoding="utf-8") if absolute_target.is_file() else None
        rendered = render_document(node, graph, existing, config.link_style)
        managed = is_managed_document(rendered)
        if existing is not None and not managed:
            warnings.append(f"Preserved unmarked user document: {target.as_posix()}")
        artifacts[target] = rendered
        document_targets[node.id] = target
        source_paths = sorted(str(item) for item in node.metadata.get("sources", ()))
        document_records[target.as_posix()] = {
            "id": node.id,
            "sha256": _content_hash(rendered),
            "sources": source_paths,
            "managed": managed,
        }

    manifest = {
        "schema_version": 3,
        "generator_version": __version__,
        "sources": _source_records(sources),
        "documents": document_records,
    }
    plan = _agent_plan(graph, document_records)
    transaction = FileTransaction(config.project_root, config.state_dir)
    for path, content in sorted(artifacts.items()):
        transaction.stage_text(path, content)
    transaction.stage_json(Path(".mini-wiki/cache/analysis.json"), analysis)
    transaction.stage_json(Path(".mini-wiki/cache/graph.json"), graph.to_dict())
    transaction.stage_json(Path(".mini-wiki/cache/build-plan.json"), plan)
    transaction.stage_json(Path(".mini-wiki/manifest.json"), manifest)
    if config.bases_enabled:
        vault_relative = config.vault_dir.relative_to(config.project_root)
        for base_path, content in sorted(render_default_bases().items()):
            target = vault_relative.joinpath(*base_path.parts[1:])
            transaction.stage_text(target, content)
    if config.canvas_enabled:
        vault_relative = config.vault_dir.relative_to(config.project_root)
        canvas_artifact = render_default_canvases(graph, config.canvas_max_nodes)
        for canvas_path, content in sorted(canvas_artifact.files.items()):
            target = vault_relative.joinpath(*canvas_path.parts[1:])
            transaction.stage_text(target, content)
        warnings.extend(canvas_artifact.warnings)
    if config.search_enabled:
        search_documents = _search_documents(config, graph, artifacts, document_targets)
        search_database = _build_search_database(config, search_documents)
        transaction.stage_bytes(Path(".mini-wiki/cache/search.sqlite3"), search_database)

    old_documents = old_manifest.get("documents", {})
    if isinstance(old_documents, dict):
        for stale_path in sorted(set(old_documents) - set(document_records)):
            try:
                relative = transaction._relative(stale_path)
            except TransactionError:
                warnings.append(f"Ignored unsafe stale document path: {stale_path}")
                continue
            stale_target = config.project_root / relative
            if not stale_target.is_file():
                continue
            stale_text = stale_target.read_text(encoding="utf-8")
            if is_managed_document(stale_text):
                transaction.stage_archive(relative)
            else:
                warnings.append(f"Preserved stale unmarked user document: {relative.as_posix()}")

    if selected_options.dry_run:
        result = transaction.preview()
        transaction.discard()
    else:
        result = transaction.commit()
    result.warnings = sorted(set(warnings))
    return result
