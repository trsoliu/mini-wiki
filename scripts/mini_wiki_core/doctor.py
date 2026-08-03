"""Actionable, read-only diagnostics for Mini-Wiki projects."""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pathspec import GitIgnoreSpec

from mini_wiki_core.config import ConfigError, load_config
from mini_wiki_core.scanner import scan_sources


@dataclass(frozen=True)
class DoctorFinding:
    """One environment or project diagnostic."""

    code: str
    severity: str
    message: str
    remediation: str = ""


@dataclass
class DoctorReport:
    """Machine-readable doctor output."""

    findings: list[DoctorFinding]

    @property
    def ok(self) -> bool:
        return not any(finding.severity == "error" for finding in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "findings": [asdict(finding) for finding in self.findings]}


def find_obsidian() -> str | None:
    """Locate the optional Obsidian executable without invoking it."""
    command = shutil.which("obsidian")
    if command:
        return command
    for candidate in (
        Path("/Applications/Obsidian.app"),
        Path.home() / "Applications" / "Obsidian.app",
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _gitignored(root: Path, target: Path) -> bool:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return False
    try:
        spec = GitIgnoreSpec.from_lines(gitignore.read_text(encoding="utf-8").splitlines())
        relative = target.relative_to(root).as_posix().rstrip("/")
    except (OSError, ValueError):
        return False
    return spec.match_file(f"{relative}/") or spec.match_file(f"{relative}/index.md")


def _fts5_available() -> bool:
    try:
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute("CREATE VIRTUAL TABLE mini_wiki_fts USING fts5(content)")
        finally:
            connection.close()
    except sqlite3.Error:
        return False
    return True


def _manifest_findings(root: Path, current_sources: dict[str, str]) -> list[DoctorFinding]:
    manifest_path = root / ".mini-wiki" / "manifest.json"
    if not manifest_path.is_file():
        return [
            DoctorFinding(
                "MANIFEST_MISSING",
                "warning",
                "The v3 build Manifest is missing.",
                "Run `mini-wiki build`.",
            )
        ]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [
            DoctorFinding(
                "MANIFEST_INVALID",
                "error",
                "The build Manifest is not valid JSON.",
                "Restore it or run `mini-wiki build` after reviewing the file.",
            )
        ]
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 3:
        return []
    raw_sources = manifest.get("sources", {})
    if not isinstance(raw_sources, dict):
        return [
            DoctorFinding(
                "MANIFEST_INVALID",
                "error",
                "Manifest sources must be a mapping.",
                "Run `mini-wiki build` to regenerate it.",
            )
        ]
    recorded: dict[str, str] = {}
    for path, value in raw_sources.items():
        digest = value.get("sha256", "") if isinstance(value, dict) else value
        if isinstance(path, str) and isinstance(digest, str):
            recorded[path] = digest
    if current_sources != recorded:
        return [
            DoctorFinding(
                "MANIFEST_STALE",
                "warning",
                "Source state differs from the last build Manifest.",
                "Run `mini-wiki build` and then `mini-wiki check --strict`.",
            )
        ]
    return []


def doctor_project(project_root: str | Path) -> DoctorReport:
    """Diagnose initialization, portability, freshness, search, and Obsidian integration."""
    root = Path(project_root).resolve()
    findings: list[DoctorFinding] = []
    config_path = root / ".mini-wiki" / "config.yaml"
    if not config_path.is_file():
        findings.append(
            DoctorFinding(
                "NOT_INITIALIZED",
                "error",
                "Mini-Wiki configuration was not found.",
                "Run `mini-wiki init` in the project root.",
            )
        )
    else:
        try:
            config = load_config(root)
        except ConfigError as exc:
            findings.append(
                DoctorFinding(
                    "CONFIG_INVALID",
                    "error",
                    str(exc),
                    "Repair .mini-wiki/config.yaml and rerun doctor.",
                )
            )
        else:
            if config.compatibility_mode:
                findings.append(
                    DoctorFinding(
                        "LEGACY_MODE",
                        "warning",
                        "This project still uses the v2 Vault layout.",
                        "Preview `mini-wiki migrate`; migration is never automatic.",
                    )
                )
            if not config.vault_dir.is_dir():
                findings.append(
                    DoctorFinding(
                        "VAULT_MISSING",
                        "error",
                        "The configured Markdown Vault does not exist.",
                        "Run `mini-wiki init` or repair vault.path.",
                    )
                )
            elif _gitignored(root, config.vault_dir):
                findings.append(
                    DoctorFinding(
                        "VAULT_IGNORED",
                        "warning",
                        "The durable Markdown Vault is excluded by .gitignore.",
                        "Remove the Vault ignore rule so canonical Markdown can be versioned.",
                    )
                )
            current_sources = {source.path.as_posix(): source.sha256 for source in scan_sources(config)}
            findings.extend(_manifest_findings(root, current_sources))

    if _fts5_available():
        findings.append(DoctorFinding("FTS5_AVAILABLE", "info", "SQLite FTS5 is available for local search."))
    else:
        findings.append(
            DoctorFinding(
                "FTS5_UNAVAILABLE",
                "warning",
                "SQLite FTS5 is unavailable; Markdown generation remains functional.",
                "Use a Python/SQLite build with FTS5 to enable local full-text search.",
            )
        )

    obsidian = find_obsidian()
    if obsidian is None:
        findings.append(
            DoctorFinding(
                "OBSIDIAN_NOT_FOUND",
                "info",
                "Obsidian was not found; Mini-Wiki remains fully usable as Markdown.",
                "Install Obsidian only if desktop graph and Canvas workflows are desired.",
            )
        )
    else:
        findings.append(DoctorFinding("OBSIDIAN_FOUND", "info", "Optional Obsidian integration is available."))

    findings.sort(key=lambda finding: (finding.severity, finding.code, finding.message))
    return DoctorReport(findings)
