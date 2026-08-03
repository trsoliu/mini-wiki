"""Configuration loading and safe project-relative path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_EXCLUDES = (
    ".git",
    ".mini-wiki",
    ".agents",
    ".agent",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
)

VALID_LINK_STYLES = {"wikilink", "markdown"}
VALID_SOURCE_LINK_STYLES = {"relative-markdown"}


class ConfigError(ValueError):
    """Raised when Mini-Wiki configuration is invalid or unsafe."""


@dataclass(frozen=True)
class WikiConfig:
    """Normalized Mini-Wiki v3 configuration."""

    schema_version: int
    project_root: Path
    state_dir: Path
    vault_dir: Path
    compatibility_mode: bool
    link_style: str
    source_links: str
    preserve_manual_content: bool
    language: str
    include_diagrams: bool
    include_examples: bool
    max_file_size: int
    respect_gitignore: bool
    excludes: tuple[str, ...]
    search_enabled: bool
    bases_enabled: bool
    canvas_enabled: bool
    canvas_max_nodes: int
    obsidian_integration: str


def default_config_data() -> dict[str, Any]:
    """Return a fresh v3 configuration mapping."""
    return {
        "schema_version": 3,
        "vault": {
            "path": "wiki",
            "link_style": "wikilink",
            "source_links": "relative-markdown",
            "preserve_manual_content": True,
        },
        "generation": {
            "language": "zh",
            "include_diagrams": True,
            "include_examples": True,
            "max_file_size": 100_000,
        },
        "scan": {
            "respect_gitignore": True,
            "exclude": list(DEFAULT_EXCLUDES),
        },
        "search": {"enabled": True, "index_code_symbols": True},
        "bases": {"enabled": True},
        "canvas": {"enabled": True, "max_nodes": 200},
        "obsidian": {"integration": "auto"},
    }


def default_config_yaml() -> str:
    """Serialize the default configuration with stable key order."""
    return yaml.safe_dump(default_config_data(), allow_unicode=True, sort_keys=False)


def resolve_project_path(root: str | Path, value: str | Path) -> Path:
    """Resolve a path and reject targets outside the project root."""
    project_root = Path(root).resolve()
    candidate = (project_root / value).resolve()
    if candidate != project_root and project_root not in candidate.parents:
        raise ConfigError(f"Path is outside project root: {value}")
    return candidate


def _mapping(value: Any, section: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"Configuration section '{section}' must be a mapping")
    return value


def _string_list(value: Any, section: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"Configuration field '{section}' must be a list of strings")
    return tuple(value)


def load_config(project_root: str | Path) -> WikiConfig:
    """Load v3 configuration or resolve a v2 project in compatibility mode."""
    root = Path(project_root).resolve()
    state_dir = root / ".mini-wiki"
    config_path = state_dir / "config.yaml"
    if not config_path.is_file():
        raise ConfigError(f"Mini-Wiki configuration does not exist: {config_path}")

    try:
        loaded = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Unable to read Mini-Wiki configuration: {exc}") from exc
    if loaded is None:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ConfigError("Mini-Wiki configuration root must be a mapping")

    try:
        schema_version = int(loaded.get("schema_version", 0))
    except (TypeError, ValueError) as exc:
        raise ConfigError("schema_version must be an integer") from exc

    legacy_vault = state_dir / "wiki"
    compatibility_mode = schema_version < 3 and legacy_vault.is_dir()
    vault = _mapping(loaded.get("vault"), "vault")
    generation = _mapping(loaded.get("generation"), "generation")
    scan = _mapping(loaded.get("scan"), "scan")
    search = _mapping(loaded.get("search"), "search")
    bases = _mapping(loaded.get("bases"), "bases")
    canvas = _mapping(loaded.get("canvas"), "canvas")
    obsidian = _mapping(loaded.get("obsidian"), "obsidian")

    vault_value = vault.get("path", ".mini-wiki/wiki" if compatibility_mode else "wiki")
    if not isinstance(vault_value, str) or not vault_value.strip():
        raise ConfigError("vault.path must be a non-empty string")

    link_style = str(vault.get("link_style", "wikilink"))
    if link_style not in VALID_LINK_STYLES:
        raise ConfigError(f"vault.link_style must be one of {sorted(VALID_LINK_STYLES)}")
    source_links = str(vault.get("source_links", "relative-markdown"))
    if source_links not in VALID_SOURCE_LINK_STYLES:
        raise ConfigError(f"vault.source_links must be one of {sorted(VALID_SOURCE_LINK_STYLES)}")

    custom_excludes = _string_list(scan.get("exclude", loaded.get("exclude")), "scan.exclude")
    excludes = tuple(dict.fromkeys((*DEFAULT_EXCLUDES, *custom_excludes)))

    try:
        max_file_size = int(generation.get("max_file_size", 100_000))
        canvas_max_nodes = int(canvas.get("max_nodes", 200))
    except (TypeError, ValueError) as exc:
        raise ConfigError("Numeric Mini-Wiki configuration values must be integers") from exc
    if max_file_size <= 0:
        raise ConfigError("generation.max_file_size must be greater than zero")
    if canvas_max_nodes <= 0:
        raise ConfigError("canvas.max_nodes must be greater than zero")

    return WikiConfig(
        schema_version=max(schema_version, 3 if not compatibility_mode else schema_version),
        project_root=root,
        state_dir=state_dir,
        vault_dir=resolve_project_path(root, vault_value),
        compatibility_mode=compatibility_mode,
        link_style=link_style,
        source_links=source_links,
        preserve_manual_content=bool(vault.get("preserve_manual_content", True)),
        language=str(generation.get("language", "zh")),
        include_diagrams=bool(generation.get("include_diagrams", True)),
        include_examples=bool(generation.get("include_examples", True)),
        max_file_size=max_file_size,
        respect_gitignore=bool(scan.get("respect_gitignore", True)),
        excludes=excludes,
        search_enabled=bool(search.get("enabled", True)),
        bases_enabled=bool(bases.get("enabled", True)),
        canvas_enabled=bool(canvas.get("enabled", True)),
        canvas_max_nodes=canvas_max_nodes,
        obsidian_integration=str(obsidian.get("integration", "auto")),
    )
