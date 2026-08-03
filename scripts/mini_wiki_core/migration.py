"""Explicit, copy-only, recoverable migration from Mini-Wiki v2 to v3."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from mini_wiki_core import __version__
from mini_wiki_core.config import default_config_data
from mini_wiki_core.graph import stable_id
from mini_wiki_core.vault import (
    CONTENT_END,
    CONTENT_START,
    GENERATED_END,
    GENERATED_START,
    is_managed_document,
)


class MigrationError(RuntimeError):
    """Raised when a migration cannot proceed without risking user data."""


@dataclass(frozen=True)
class MigrationPlan:
    """Read-only description of a possible v2-to-v3 migration."""

    project_root: Path
    source: Path
    destination: Path
    applicable: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "applicable": self.applicable,
            "source": self.source.relative_to(self.project_root).as_posix(),
            "destination": self.destination.relative_to(self.project_root).as_posix(),
            "reasons": list(self.reasons),
        }


@dataclass
class MigrationResult:
    """Repository-relative result of an applied or no-op migration."""

    success: bool
    copied: list[str] = field(default_factory=list)
    adopted: list[str] = field(default_factory=list)
    backup: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise MigrationError(f"Unable to read legacy configuration: {exc}") from exc
    if not isinstance(value, dict):
        raise MigrationError("Legacy configuration must be a mapping")
    return value


def plan_migration(project_root: str | Path) -> MigrationPlan:
    """Inspect migration state without creating or changing any files."""
    root = Path(project_root).resolve()
    source = root / ".mini-wiki" / "wiki"
    destination = root / "wiki"
    config = _read_config(root / ".mini-wiki" / "config.yaml")
    try:
        schema_version = int(config.get("schema_version", 0))
    except (TypeError, ValueError):
        schema_version = 0

    if schema_version >= 3 and destination.is_dir():
        return MigrationPlan(root, source, destination, False, ("already-v3",))
    if not source.is_dir():
        return MigrationPlan(root, source, destination, False, ("legacy-vault-missing",))
    return MigrationPlan(root, source, destination, True, ("legacy-v2-vault",))


def _merge_mapping(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge_mapping(current, value)
        else:
            merged[key] = value
    return merged


def _v3_config(legacy: dict[str, Any]) -> str:
    merged = _merge_mapping(default_config_data(), legacy)
    merged["schema_version"] = 3
    vault = merged.get("vault")
    if not isinstance(vault, dict):
        vault = {}
        merged["vault"] = vault
    vault["path"] = "wiki"
    legacy_excludes = legacy.get("exclude")
    if isinstance(legacy_excludes, list) and all(isinstance(item, str) for item in legacy_excludes):
        scan = merged.setdefault("scan", {})
        if isinstance(scan, dict):
            existing = scan.get("exclude", [])
            if isinstance(existing, list):
                scan["exclude"] = list(dict.fromkeys([*existing, *legacy_excludes]))
    return yaml.safe_dump(merged, allow_unicode=True, sort_keys=False)


def _adopt_document(path: Path, vault_root: Path) -> bool:
    body = path.read_text(encoding="utf-8")
    if is_managed_document(body):
        return False
    relative = path.relative_to(vault_root)
    title = relative.stem.replace("_", " ").replace("-", " ").strip().title() or "Legacy Document"
    properties = {
        "id": stable_id("document", f"legacy/{relative.with_suffix('').as_posix()}"),
        "title": title,
        "type": "legacy",
        "status": "migrated",
        "sources": [],
        "mini_wiki_version": __version__,
    }
    frontmatter = yaml.safe_dump(properties, allow_unicode=True, sort_keys=False).rstrip()
    wrapped = (
        f"---\n{frontmatter}\n---\n\n"
        f"{GENERATED_START}\n# {title}\n\n"
        "> Migrated from Mini-Wiki v2. The legacy body below is preserved verbatim.\n"
        f"{GENERATED_END}\n\n{CONTENT_START}\n"
        f"{body}{CONTENT_END}\n"
    )
    path.write_text(wrapped, encoding="utf-8")
    return True


def _validate_plan(plan: MigrationPlan) -> None:
    expected_source = plan.project_root / ".mini-wiki" / "wiki"
    expected_destination = plan.project_root / "wiki"
    source_matches = plan.source.resolve() == expected_source.resolve()
    destination_matches = plan.destination.resolve() == expected_destination.resolve()
    if not source_matches or not destination_matches:
        raise MigrationError("Migration plan paths do not match the project boundary")
    if not plan.source.is_dir():
        raise MigrationError("Legacy Vault does not exist")
    if plan.destination.exists() and any(plan.destination.iterdir()):
        raise MigrationError("Migration destination is not empty")


def apply_migration(plan: MigrationPlan, adopt: bool = False) -> MigrationResult:
    """Copy a legacy Vault, retain it and a backup, then atomically write v3 config."""
    if not plan.applicable:
        return MigrationResult(True, warnings=[f"Migration not applied: {', '.join(plan.reasons)}"])
    _validate_plan(plan)

    state_dir = plan.project_root / ".mini-wiki"
    config_path = state_dir / "config.yaml"
    legacy_config = _read_config(config_path)
    config_bytes = config_path.read_bytes() if config_path.is_file() else b""
    staging_root = state_dir / "staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="migration-", dir=staging_root))
    staged_vault = stage / "wiki"
    staged_config = stage / "config.yaml"
    archive_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup_root = state_dir / "archive" / archive_id / "v2-backup"
    destination_created = False

    try:
        shutil.copytree(plan.source, staged_vault, symlinks=True)
        adopted: list[str] = []
        if adopt:
            for document in sorted(staged_vault.rglob("*.md")):
                if document.is_file() and _adopt_document(document, staged_vault):
                    adopted.append((Path("wiki") / document.relative_to(staged_vault)).as_posix())
        staged_config.write_text(_v3_config(legacy_config), encoding="utf-8")

        backup_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plan.source, backup_root / "wiki", symlinks=True)
        if config_path.is_file():
            shutil.copy2(config_path, backup_root / "config.yaml")

        if plan.destination.exists():
            plan.destination.rmdir()
        os.replace(staged_vault, plan.destination)
        destination_created = True
        os.replace(staged_config, config_path)
    except OSError as exc:
        if destination_created and plan.destination.exists():
            shutil.rmtree(plan.destination)
        if config_bytes:
            config_path.write_bytes(config_bytes)
        raise MigrationError(f"Migration failed: {exc}") from exc
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    copied = [
        path.relative_to(plan.project_root).as_posix() for path in sorted(plan.destination.rglob("*")) if path.is_file()
    ]
    return MigrationResult(
        True,
        copied=copied,
        adopted=adopted,
        backup=backup_root.relative_to(plan.project_root).as_posix(),
    )
