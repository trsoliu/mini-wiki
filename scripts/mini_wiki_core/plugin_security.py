"""Security primitives for installing instruction-only Mini-Wiki plugins."""

from __future__ import annotations

import hashlib
import re
import shutil
import stat
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from zipfile import BadZipFile, ZipFile, ZipInfo

import yaml

MAX_PLUGIN_FILES = 2_000
MAX_PLUGIN_TREE_BYTES = 25 * 1024 * 1024


class PluginSecurityError(ValueError):
    """Raised when plugin input violates an installation boundary."""


@dataclass(frozen=True)
class InstructionPlugin:
    """Validated metadata for a text-instruction plugin."""

    name: str
    plugin_type: str
    version: str
    description: str
    manifest_file: str
    sha256: str


def _safe_member(info: ZipInfo) -> PurePosixPath:
    normalized = info.filename.replace("\\", "/")
    member = PurePosixPath(normalized)
    mode = info.external_attr >> 16
    if (
        not normalized
        or member.is_absolute()
        or ".." in member.parts
        or (member.parts and member.parts[0].endswith(":"))
    ):
        raise PluginSecurityError(f"Plugin archive contains unsafe path: {info.filename}")
    if stat.S_ISLNK(mode):
        raise PluginSecurityError(f"Plugin archive contains symbolic link: {info.filename}")
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
        raise PluginSecurityError(f"Plugin archive contains unsupported file type: {info.filename}")
    return member


def safe_extract_zip(
    archive: str | Path,
    destination: str | Path,
    max_uncompressed_bytes: int,
) -> None:
    """Extract a ZIP after a complete traversal, link, count, and size preflight."""
    if max_uncompressed_bytes <= 0:
        raise PluginSecurityError("Plugin size limit must be greater than zero")
    try:
        with ZipFile(archive) as zipped:
            infos = zipped.infolist()
            if len(infos) > MAX_PLUGIN_FILES:
                raise PluginSecurityError("Plugin exceeds file count limit")
            total = sum(info.file_size for info in infos)
            if total > max_uncompressed_bytes:
                raise PluginSecurityError("Plugin exceeds uncompressed size limit")
            members = [(info, _safe_member(info)) for info in infos]

            target_root = Path(destination).resolve()
            target_root.mkdir(parents=True, exist_ok=True)
            for info, member in members:
                target = target_root.joinpath(*member.parts).resolve()
                if target != target_root and target_root not in target.parents:
                    raise PluginSecurityError(f"Plugin archive contains unsafe path: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open(info) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except BadZipFile as exc:
        raise PluginSecurityError(f"Plugin archive is invalid: {exc}") from exc


def download_bounded(url: str, destination: str | Path, max_bytes: int) -> None:
    """Download one HTTPS resource while enforcing declared and streamed size caps."""
    if urlparse(url).scheme.casefold() != "https":
        raise PluginSecurityError("Plugin downloads require HTTPS")
    if max_bytes <= 0:
        raise PluginSecurityError("Plugin download size limit must be greater than zero")
    target = Path(destination)
    request = urllib.request.Request(url, headers={"User-Agent": "Mini-Wiki-Plugin-Manager/3"})
    try:
        with urllib.request.urlopen(request) as response:
            final_url = response.geturl()
            if urlparse(final_url).scheme.casefold() != "https":
                raise PluginSecurityError("Plugin download redirected away from HTTPS")
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError as exc:
                    raise PluginSecurityError("Plugin download has an invalid Content-Length") from exc
                if declared_size > max_bytes:
                    raise PluginSecurityError("Plugin download exceeds size limit")
            target.parent.mkdir(parents=True, exist_ok=True)
            total = 0
            with target.open("wb") as output:
                while True:
                    chunk = response.read(min(64 * 1024, max_bytes + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise PluginSecurityError("Plugin download exceeds size limit")
                    output.write(chunk)
    except PluginSecurityError:
        if target.exists():
            target.unlink()
        raise
    except (OSError, urllib.error.URLError) as exc:
        if target.exists():
            target.unlink()
        raise PluginSecurityError(f"Plugin download failed: {exc}") from exc


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PluginSecurityError(f"Unable to read {path.name}: {exc}") from exc
    if not text.startswith("---\n"):
        raise PluginSecurityError(f"{path.name} must contain YAML frontmatter")
    pieces = text.split("---\n", 2)
    if len(pieces) != 3:
        raise PluginSecurityError(f"{path.name} frontmatter is not closed")
    try:
        value = yaml.safe_load(pieces[1]) or {}
    except yaml.YAMLError as exc:
        raise PluginSecurityError(f"{path.name} frontmatter is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise PluginSecurityError(f"{path.name} frontmatter must be a mapping")
    return value


def hash_instruction_tree(plugin_path: str | Path) -> str:
    """Hash names and bytes of a validated plugin tree deterministically."""
    root = Path(plugin_path).resolve()
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\n")
    return f"sha256:{digest.hexdigest()}"


def validate_instruction_plugin(plugin_path: str | Path) -> InstructionPlugin:
    """Validate an instruction tree without importing or executing anything from it."""
    root = Path(plugin_path).resolve()
    if not root.is_dir():
        raise PluginSecurityError("Plugin source must be a directory")

    files = [path for path in root.rglob("*") if path.is_file() or path.is_symlink()]
    if len(files) > MAX_PLUGIN_FILES:
        raise PluginSecurityError("Plugin exceeds file count limit")
    total = 0
    for path in files:
        if path.is_symlink():
            raise PluginSecurityError(f"Plugin contains symbolic link: {path.relative_to(root).as_posix()}")
        try:
            total += path.stat().st_size
        except OSError as exc:
            raise PluginSecurityError(f"Unable to inspect plugin file: {path.name}") from exc
    if total > MAX_PLUGIN_TREE_BYTES:
        raise PluginSecurityError("Plugin exceeds installed size limit")

    plugin_manifest = root / "PLUGIN.md"
    skill_manifest = root / "SKILL.md"
    if plugin_manifest.is_file():
        manifest_path = plugin_manifest
        manifest_file = "PLUGIN.md"
        default_type = "enhancer"
    elif skill_manifest.is_file():
        manifest_path = skill_manifest
        manifest_file = "SKILL.md"
        default_type = "skill"
    else:
        raise PluginSecurityError("Instruction plugin requires PLUGIN.md or SKILL.md")

    manifest = _frontmatter(manifest_path)
    name = manifest.get("name")
    description = manifest.get("description")
    plugin_type = manifest.get("type", default_type)
    version = manifest.get("version", "1.0.0")
    if not isinstance(name, str) or not name:
        raise PluginSecurityError(f"{manifest_file} requires a string name")
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", name) is None:
        raise PluginSecurityError("Plugin name must contain only lowercase letters, digits, hyphens, or underscores")
    if not isinstance(description, str) or not description.strip():
        raise PluginSecurityError(f"{manifest_file} requires a description")
    if not isinstance(plugin_type, str) or not plugin_type.strip():
        raise PluginSecurityError(f"{manifest_file} type must be a string")
    if not isinstance(version, str) or not version.strip():
        raise PluginSecurityError(f"{manifest_file} version must be a string")
    return InstructionPlugin(
        name=name,
        plugin_type=plugin_type,
        version=version,
        description=description.strip(),
        manifest_file=manifest_file,
        sha256=hash_instruction_tree(root),
    )
