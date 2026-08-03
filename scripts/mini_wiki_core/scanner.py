"""Repository scanner with shared, Git-compatible exclusion rules."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from pathspec import GitIgnoreSpec

from mini_wiki_core.config import DEFAULT_EXCLUDES, WikiConfig
from mini_wiki_core.models import SourceFile

CODE_EXTENSIONS = frozenset(
    {
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".py",
        ".pyi",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".scala",
        ".rb",
        ".php",
        ".cs",
        ".fs",
        ".vue",
        ".svelte",
        ".astro",
    }
)

LANGUAGES = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".pyi": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".scala": "scala",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".fs": "fsharp",
    ".vue": "vue",
    ".svelte": "svelte",
    ".astro": "astro",
}


def _read_gitignore(root: Path) -> list[str]:
    path = root / ".gitignore"
    if not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(64 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _relative_root(path: Path, project_root: Path) -> Path | None:
    try:
        return path.resolve().relative_to(project_root)
    except ValueError:
        return None


def _matches_root(relative: Path, excluded_roots: tuple[Path, ...]) -> bool:
    return any(relative == root or root in relative.parents for root in excluded_roots)


def scan_sources(config: WikiConfig) -> list[SourceFile]:
    """Scan source files without following links or leaving the project root."""
    root = config.project_root.resolve()
    configured_patterns = list(config.excludes or DEFAULT_EXCLUDES)
    patterns = configured_patterns + (_read_gitignore(root) if config.respect_gitignore else [])
    exclusions = GitIgnoreSpec.from_lines(patterns)
    literal_directories = {
        pattern.rstrip("/") for pattern in configured_patterns if "/" not in pattern and "*" not in pattern
    }

    excluded_roots: list[Path] = []
    for candidate in (config.state_dir, config.vault_dir):
        relative = _relative_root(candidate, root)
        if relative is not None and relative.parts:
            excluded_roots.append(relative)
    excluded_root_tuple = tuple(excluded_roots)

    sources: list[SourceFile] = []
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for directory_name in sorted(directory_names):
            candidate = current_path / directory_name
            relative = candidate.relative_to(root)
            relative_text = relative.as_posix() + "/"
            if candidate.is_symlink():
                continue
            if directory_name in literal_directories:
                continue
            if _matches_root(relative, excluded_root_tuple):
                continue
            if exclusions.match_file(relative_text):
                continue
            kept_directories.append(directory_name)
        directory_names[:] = kept_directories

        for file_name in sorted(file_names):
            candidate = current_path / file_name
            if candidate.suffix.lower() not in CODE_EXTENSIONS or candidate.is_symlink():
                continue
            relative = candidate.relative_to(root)
            if _matches_root(relative, excluded_root_tuple) or exclusions.match_file(relative.as_posix()):
                continue
            resolved = candidate.resolve()
            if resolved != root and root not in resolved.parents:
                continue
            try:
                size = candidate.stat().st_size
                if size > config.max_file_size:
                    continue
                digest = _sha256(candidate)
            except OSError:
                continue
            sources.append(
                SourceFile(
                    path=relative,
                    sha256=digest,
                    language=LANGUAGES.get(candidate.suffix.lower(), candidate.suffix.lower().lstrip(".")),
                    size=size,
                )
            )

    return sorted(sources, key=lambda source: source.path.as_posix())
