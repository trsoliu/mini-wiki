"""Read-only structural validation for a Mini-Wiki knowledge network."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote

import yaml

from mini_wiki_core.bases import validate_base
from mini_wiki_core.canvas import validate_canvas
from mini_wiki_core.scanner import scan_sources
from mini_wiki_core.vault import (
    CONTENT_END,
    CONTENT_START,
    GENERATED_END,
    GENERATED_START,
    is_managed_document,
)

if TYPE_CHECKING:
    from mini_wiki_core.config import WikiConfig

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass(frozen=True)
class ValidationIssue:
    """One actionable structural finding."""

    code: str
    severity: str
    path: str
    message: str


@dataclass
class ValidationReport:
    """Deterministic collection of structural validation findings."""

    issues: list[ValidationIssue]
    documents: int = 0

    @property
    def ok(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "documents": self.documents,
            "error_count": sum(issue.severity == "error" for issue in self.issues),
            "warning_count": sum(issue.severity == "warning" for issue in self.issues),
            "issues": [asdict(issue) for issue in self.issues],
        }


def _properties(text: str) -> dict[str, Any] | None:
    if not text.startswith("---\n"):
        return None
    pieces = text.split("---\n", 2)
    if len(pieces) != 3:
        return None
    try:
        value = yaml.safe_load(pieces[1]) or {}
    except yaml.YAMLError:
        return None
    return value if isinstance(value, dict) else None


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _managed_regions_valid(text: str) -> bool:
    markers = (GENERATED_START, GENERATED_END, CONTENT_START, CONTENT_END)
    if any(text.count(marker) != 1 for marker in markers):
        return False
    return text.index(GENERATED_START) < text.index(GENERATED_END) < text.index(CONTENT_START) < text.index(CONTENT_END)


def _wikilink_target(target: str, document: Path, vault: Path, documents: set[Path]) -> Path | None:
    value = unquote(target.split("|", 1)[0].split("#", 1)[0]).strip()
    if not value:
        return document
    relative = Path(value)
    if relative.is_absolute():
        return None
    if relative.suffix.casefold() != ".md":
        relative = relative.with_suffix(".md")
    candidates = ((vault / relative).resolve(), (document.parent / relative).resolve())
    for candidate in candidates:
        if candidate in documents:
            return candidate
    value_without_suffix = relative.with_suffix("").as_posix()
    matches = [
        candidate
        for candidate in documents
        if candidate.stem == relative.stem
        or candidate.relative_to(vault).with_suffix("").as_posix() == value_without_suffix
    ]
    return matches[0] if len(matches) == 1 else None


def _markdown_target(raw_target: str, document: Path) -> Path | None:
    value = raw_target.strip()
    value = value[1 : value.index(">")] if value.startswith("<") and ">" in value else value.split(maxsplit=1)[0]
    value = unquote(value.split("#", 1)[0].split("?", 1)[0]).strip()
    if not value or value.startswith("#") or URI_SCHEME_RE.match(value):
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (document.parent / candidate).resolve()


def _add_link_issues(
    text: str,
    document: Path,
    config: WikiConfig,
    documents: set[Path],
    incoming: set[Path],
    issues: list[ValidationIssue],
) -> None:
    path = _relative(document, config.vault_dir)
    for raw_target in WIKILINK_RE.findall(text):
        target = _wikilink_target(raw_target, document, config.vault_dir, documents)
        if target is None:
            issues.append(
                ValidationIssue("LINK_TARGET_MISSING", "error", path, f"Wikilink target does not exist: {raw_target}")
            )
        else:
            incoming.add(target)

    for raw_target in MARKDOWN_LINK_RE.findall(text):
        if raw_target.strip().casefold().startswith("file://"):
            issues.append(ValidationIssue("NON_PORTABLE_LINK", "error", path, "Local file:// links are not portable"))
            continue
        target = _markdown_target(raw_target, document)
        if target is None:
            continue
        if not _inside(target, config.project_root):
            issues.append(
                ValidationIssue("LINK_OUTSIDE_PROJECT", "error", path, f"Link leaves project boundary: {raw_target}")
            )
        elif not target.is_file():
            issues.append(
                ValidationIssue("LINK_TARGET_MISSING", "error", path, f"Link target does not exist: {raw_target}")
            )
        elif _inside(target, config.vault_dir) and target.suffix.casefold() == ".md":
            incoming.add(target)


def _add_source_issues(
    properties: dict[str, Any],
    document: Path,
    config: WikiConfig,
    issues: list[ValidationIssue],
) -> None:
    path = _relative(document, config.vault_dir)
    sources = properties.get("sources", [])
    if not isinstance(sources, list):
        issues.append(ValidationIssue("SOURCES_INVALID", "error", path, "sources must be a list"))
        return
    for source in sources:
        if not isinstance(source, str):
            issues.append(ValidationIssue("SOURCES_INVALID", "error", path, "source paths must be strings"))
            continue
        source_path = Path(source)
        resolved = source_path.resolve() if source_path.is_absolute() else (config.project_root / source_path).resolve()
        if not _inside(resolved, config.project_root):
            issues.append(
                ValidationIssue("SOURCE_OUTSIDE_PROJECT", "error", path, f"Source leaves project boundary: {source}")
            )
        elif not resolved.is_file():
            issues.append(ValidationIssue("SOURCE_MISSING", "warning", path, f"Source does not exist: {source}"))


def _manifest_issues(config: WikiConfig) -> list[ValidationIssue]:
    manifest_path = config.state_dir / "manifest.json"
    if not manifest_path.is_file():
        return [
            ValidationIssue(
                "MANIFEST_MISSING",
                "warning",
                ".mini-wiki/manifest.json",
                "Build Manifest does not exist",
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            ValidationIssue(
                "MANIFEST_INVALID",
                "error",
                ".mini-wiki/manifest.json",
                "Build Manifest is not valid JSON",
            )
        ]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 3:
        return []
    raw_sources = manifest.get("sources", {})
    if not isinstance(raw_sources, dict):
        return [
            ValidationIssue(
                "MANIFEST_INVALID",
                "error",
                ".mini-wiki/manifest.json",
                "Manifest sources must be a mapping",
            )
        ]

    current = {source.path.as_posix(): source.sha256 for source in scan_sources(config)}
    recorded: dict[str, str] = {}
    for path, value in raw_sources.items():
        digest = value.get("sha256", "") if isinstance(value, dict) else value
        if isinstance(path, str) and isinstance(digest, str):
            recorded[path] = digest

    issues: list[ValidationIssue] = []
    for path in sorted(set(current) & set(recorded)):
        if current[path] != recorded[path]:
            issues.append(ValidationIssue("SOURCE_HASH_MISMATCH", "error", path, "Source changed since the last build"))
    for path in sorted(set(current) - set(recorded)):
        issues.append(
            ValidationIssue("SOURCE_NOT_IN_MANIFEST", "warning", path, "Source is not covered by the Manifest")
        )
    for path in sorted(set(recorded) - set(current)):
        issues.append(ValidationIssue("MANIFEST_SOURCE_MISSING", "error", path, "Manifest source no longer exists"))
    return issues


def validate_vault(config: WikiConfig) -> ValidationReport:
    """Validate IDs, links, sources, freshness, orphans, and ownership markers."""
    vault = config.vault_dir.resolve()
    if not vault.is_dir():
        return ValidationReport(
            [ValidationIssue("VAULT_MISSING", "error", "wiki", "Configured Vault directory does not exist")]
        )

    documents = {path.resolve() for path in vault.rglob("*.md") if path.is_file()}
    contents: dict[Path, str] = {}
    managed_documents: set[Path] = set()
    incoming: set[Path] = set()
    ids: dict[str, list[Path]] = {}
    issues: list[ValidationIssue] = []

    for base_path in sorted(path for path in vault.rglob("*.base") if path.is_file()):
        relative_base = base_path.relative_to(vault)
        try:
            base_text = base_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(ValidationIssue("INVALID_BASE", "error", relative_base.as_posix(), str(exc)))
        else:
            issues.extend(validate_base(relative_base, base_text))

    for canvas_path in sorted(path for path in vault.rglob("*.canvas") if path.is_file()):
        relative_canvas = canvas_path.relative_to(vault)
        try:
            canvas_payload = json.loads(canvas_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issues.append(
                ValidationIssue("INVALID_CANVAS", "error", relative_canvas.as_posix(), f"Canvas JSON is invalid: {exc}")
            )
            continue
        for canvas_issue in validate_canvas(relative_canvas, canvas_payload, vault):
            issues.append(
                ValidationIssue(
                    canvas_issue.code,
                    canvas_issue.severity,
                    canvas_issue.path,
                    canvas_issue.message,
                )
            )

    for document in sorted(documents):
        relative = _relative(document, vault)
        try:
            text = document.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(ValidationIssue("DOCUMENT_UNREADABLE", "error", relative, str(exc)))
            continue
        contents[document] = text
        marker_present = any(marker in text for marker in (GENERATED_START, GENERATED_END, CONTENT_START, CONTENT_END))
        if marker_present and not _managed_regions_valid(text):
            issues.append(
                ValidationIssue("MANAGED_REGION_INVALID", "error", relative, "Managed ownership markers are unbalanced")
            )
        if not is_managed_document(text):
            continue
        managed_documents.add(document)
        properties = _properties(text)
        if properties is None:
            issues.append(ValidationIssue("FRONTMATTER_INVALID", "error", relative, "Managed frontmatter is invalid"))
            continue
        node_id = properties.get("id")
        if not isinstance(node_id, str) or not node_id:
            issues.append(ValidationIssue("DOCUMENT_ID_MISSING", "error", relative, "Managed document has no id"))
        else:
            ids.setdefault(node_id, []).append(document)
        _add_source_issues(properties, document, config, issues)

    for node_id, paths in sorted(ids.items()):
        if len(paths) > 1:
            for path in paths:
                issues.append(
                    ValidationIssue(
                        "DUPLICATE_ID",
                        "error",
                        _relative(path, vault),
                        f"Document id is used {len(paths)} times: {node_id}",
                    )
                )

    for document, text in sorted(contents.items()):
        _add_link_issues(text, document, config, documents, incoming, issues)

    for document in sorted(managed_documents - incoming):
        if document.name not in {"index.md", "_index.md"}:
            issues.append(
                ValidationIssue(
                    "ORPHAN_MANAGED_DOCUMENT",
                    "error",
                    _relative(document, vault),
                    "Managed document has no incoming knowledge-network link",
                )
            )

    issues.extend(_manifest_issues(config))
    issues.sort(key=lambda issue: (issue.path, issue.code, issue.message))
    return ValidationReport(issues, len(documents))
