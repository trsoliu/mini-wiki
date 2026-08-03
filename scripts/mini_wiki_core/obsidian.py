"""Optional Obsidian detection, explicit probing, and explicit Vault opening."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    from collections.abc import Callable

    from mini_wiki_core.config import WikiConfig


class ObsidianIntegrationError(RuntimeError):
    """Raised when an explicitly requested Obsidian action fails."""


@dataclass(frozen=True)
class ObsidianStatus:
    cli_available: bool
    cli_path: str | None
    uri_available: bool
    core_blocked: bool = False
    version: str | None = None

    def to_dict(self) -> dict[str, bool | str | None]:
        return asdict(self)


@dataclass(frozen=True)
class ObsidianOpenResult:
    success: bool
    message: str
    uri: str | None = None

    def to_dict(self) -> dict[str, bool | str | None]:
        return asdict(self)


def detect_obsidian(
    which: Callable[[str], str | None] = shutil.which,
    platform_name: str = sys.platform,
) -> ObsidianStatus:
    """Detect integration surfaces without starting Obsidian or any subprocess."""
    cli_path = which("obsidian")
    uri_available = platform_name in {"darwin", "win32"}
    return ObsidianStatus(cli_path is not None, cli_path, uri_available, False, None)


def _run_version(argv: list[str]) -> str:
    completed = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=15)
    output = completed.stdout.strip() or completed.stderr.strip()
    if completed.returncode != 0:
        raise ObsidianIntegrationError(output or f"Obsidian CLI exited with {completed.returncode}")
    return output


def probe_obsidian_version(
    status: ObsidianStatus,
    runner: Callable[[list[str]], str] = _run_version,
) -> ObsidianStatus:
    """Run only the official `obsidian version` command after explicit consent."""
    if not status.cli_available or status.cli_path is None:
        return status
    version = runner([status.cli_path, "version"]).strip()
    return replace(status, version=version or None)


def vault_uri(vault_dir: str | Path) -> str:
    """Create the official URI for opening a Vault by absolute path."""
    path = str(Path(vault_dir).resolve())
    return "obsidian://open?" + urlencode({"path": path})


def open_platform_uri(uri: str, platform_name: str = sys.platform) -> int:
    """Open an Obsidian URI using a platform argument list, never a shell string."""
    if platform_name == "darwin":
        return subprocess.run(["open", uri], check=False).returncode
    if platform_name == "win32":
        return subprocess.run(["cmd", "/c", "start", "", uri], check=False).returncode
    raise ObsidianIntegrationError("Open the wiki directory manually as an Obsidian Vault on this platform")


def open_vault(
    config: WikiConfig,
    status: ObsidianStatus,
    uri_opener: Callable[[str], int] = open_platform_uri,
) -> ObsidianOpenResult:
    """Open the configured Vault only for an explicit caller action."""
    if not config.vault_dir.is_dir():
        return ObsidianOpenResult(False, "Configured Vault does not exist. Run `mini-wiki build` first.")
    if not status.uri_available:
        return ObsidianOpenResult(
            False,
            f"Open {config.vault_dir} manually as an Obsidian Vault on this platform.",
        )
    uri = vault_uri(config.vault_dir)
    try:
        return_code = uri_opener(uri)
    except (OSError, ObsidianIntegrationError) as exc:
        return ObsidianOpenResult(False, f"Unable to open Obsidian: {exc}", uri)
    if return_code != 0:
        return ObsidianOpenResult(False, f"Obsidian URI opener exited with {return_code}", uri)
    return ObsidianOpenResult(True, "Obsidian Vault open request sent.", uri)
