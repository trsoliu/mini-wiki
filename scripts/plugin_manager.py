#!/usr/bin/env python3
"""
Plugin Manager / 扩展管理器

Manage mini-wiki plugins: list, install, enable, disable.
"""

import os
import re
import shutil
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import yaml

from mini_wiki_core.plugin_security import (
    MAX_PLUGIN_TREE_BYTES,
    PluginSecurityError,
    download_bounded,
    safe_extract_zip,
    validate_instruction_plugin,
)

MAX_PLUGIN_DOWNLOAD_BYTES = 10 * 1024 * 1024


def get_plugins_dir(project_root: str) -> Path:
    """Get the plugins directory path."""
    return Path(project_root) / "plugins"


def get_registry_path(project_root: str) -> Path:
    """Get the registry file path."""
    return get_plugins_dir(project_root) / "_registry.yaml"


def load_registry(project_root: str) -> dict[str, Any]:
    """Load the plugin registry."""
    registry_path = get_registry_path(project_root)
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {"plugins": []}
    return {"plugins": []}


def save_registry(project_root: str, registry: dict[str, Any]):
    """Save the plugin registry."""
    registry_path = get_registry_path(project_root)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".registry-", suffix=".yaml", dir=registry_path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            yaml.safe_dump(registry, output, default_flow_style=False, allow_unicode=True, sort_keys=False)
        os.replace(temporary_path, registry_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def parse_plugin_manifest(plugin_path: Path) -> dict[str, Any] | None:
    """Parse PLUGIN.md or a standard SKILL.md frontmatter without execution."""
    manifest_path = plugin_path / "PLUGIN.md"
    skill_manifest = False
    if not manifest_path.is_file():
        manifest_path = plugin_path / "SKILL.md"
        skill_manifest = True
    if not manifest_path.is_file():
        return None

    with open(manifest_path, encoding="utf-8") as f:
        content = f.read()

    # Extract YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        try:
            data = yaml.safe_load(match.group(1))
            if not isinstance(data, dict):
                return None
            normalized = cast("dict[str, Any]", data)
            if skill_manifest:
                normalized.setdefault("type", "skill")
                normalized.setdefault("version", "1.0.0")
            return normalized
        except yaml.YAMLError:
            return None
    return None


def list_plugins(project_root: str) -> list[dict[str, Any]]:
    """List all installed plugins."""
    plugins_dir = get_plugins_dir(project_root)
    registry = load_registry(project_root)

    plugins: list[dict[str, Any]] = []

    if not plugins_dir.exists():
        return plugins

    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            manifest = parse_plugin_manifest(item)
            if manifest:
                # Check if enabled in registry
                reg_entry = next((e for e in registry.get("plugins", []) if e.get("name") == manifest["name"]), None)
                plugins.append(
                    {
                        **manifest,
                        "path": str(item),
                        "enabled": reg_entry.get("enabled", False) if reg_entry else False,
                        "priority": reg_entry.get("priority", 100) if reg_entry else 100,
                    }
                )

    return sorted(plugins, key=lambda x: x.get("priority", 100))


def _source_details(source: str) -> tuple[str, str, str]:
    if re.fullmatch(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", source):
        return "github", source, f"https://github.com/{source}/archive/refs/heads/main.zip"
    if source.startswith(("http://", "https://")):
        return "url", source, source
    return "local", Path(source).name, source


def _find_instruction_root(extracted: Path) -> Path:
    if (extracted / "PLUGIN.md").is_file() or (extracted / "SKILL.md").is_file():
        return extracted
    candidates = [
        path
        for path in sorted(extracted.iterdir())
        if path.is_dir() and ((path / "PLUGIN.md").is_file() or (path / "SKILL.md").is_file())
    ]
    if len(candidates) != 1:
        raise PluginSecurityError("Plugin archive must contain exactly one PLUGIN.md or SKILL.md root")
    return candidates[0]


def _install_plugin(
    project_root: str,
    source: str,
    *,
    replace: bool,
    expected_name: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"success": False, "message": "", "name": None}
    root = Path(project_root).resolve()
    if not root.is_dir():
        result["message"] = "Installation failed: project root does not exist"
        return result
    plugins_dir = get_plugins_dir(str(root))
    plugins_dir.mkdir(parents=True, exist_ok=True)
    local_stage: Path | None = None
    backup: Path | None = None

    try:
        source_type, source_origin, resolved_source = _source_details(source)
        with tempfile.TemporaryDirectory(prefix="mini-wiki-plugin-") as temporary:
            workspace = Path(temporary)
            if source_type in {"github", "url"}:
                archive = workspace / "plugin.zip"
                download_bounded(resolved_source, archive, MAX_PLUGIN_DOWNLOAD_BYTES)
                extracted = workspace / "extracted"
                safe_extract_zip(archive, extracted, MAX_PLUGIN_TREE_BYTES)
                instruction_root = _find_instruction_root(extracted)
            else:
                source_path = Path(resolved_source).expanduser().resolve()
                if source_path.suffix.casefold() in {".zip", ".skill"}:
                    extracted = workspace / "extracted"
                    safe_extract_zip(source_path, extracted, MAX_PLUGIN_TREE_BYTES)
                    instruction_root = _find_instruction_root(extracted)
                else:
                    instruction_root = source_path

            metadata = validate_instruction_plugin(instruction_root)
            if expected_name is not None and metadata.name != expected_name:
                raise PluginSecurityError(
                    f"Updated plugin name mismatch: expected {expected_name}, received {metadata.name}"
                )
            target_dir = plugins_dir / metadata.name
            if target_dir.exists() and not replace:
                raise PluginSecurityError(f'Plugin "{metadata.name}" is already installed')
            if replace and not target_dir.is_dir():
                raise PluginSecurityError(f'Plugin "{metadata.name}" is not installed')

            prepared = workspace / "prepared"
            shutil.copytree(instruction_root, prepared)
            metadata = validate_instruction_plugin(prepared)
            local_stage = Path(tempfile.mkdtemp(prefix=".mini-wiki-plugin-", dir=root))
            shutil.copytree(prepared, local_stage, dirs_exist_ok=True)

            registry = load_registry(str(root))
            raw_plugins = registry.get("plugins", [])
            if not isinstance(raw_plugins, list):
                raise PluginSecurityError("Plugin registry entries must be a list")
            existing = next(
                (entry for entry in raw_plugins if isinstance(entry, dict) and entry.get("name") == metadata.name),
                None,
            )
            priority = existing.get("priority", 100) if existing else len(raw_plugins) * 10 + 10
            source_record: dict[str, Any] = {"type": source_type, "origin": source_origin}
            if source_type == "github":
                source_record["branch"] = "main"
            entry = {
                "name": metadata.name,
                "enabled": False,
                "priority": priority,
                "type": metadata.plugin_type,
                "version": metadata.version,
                "source": source_record,
                "sha256": metadata.sha256,
                "instruction_only": True,
                "manifest": metadata.manifest_file,
                "installed_at": datetime.now().isoformat(),
            }
            updated_plugins = [
                item for item in raw_plugins if not isinstance(item, dict) or item.get("name") != metadata.name
            ]
            updated_plugins.append(entry)
            updated_registry = {**registry, "plugins": updated_plugins}

            if target_dir.exists():
                backup = root / f".mini-wiki-plugin-backup-{uuid.uuid4().hex}"
                os.replace(target_dir, backup)
            try:
                os.replace(local_stage, target_dir)
                local_stage = None
                save_registry(str(root), updated_registry)
            except Exception:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                if backup is not None and backup.exists():
                    os.replace(backup, target_dir)
                    backup = None
                raise
            if backup is not None and backup.exists():
                shutil.rmtree(backup)
                backup = None

            result.update(
                {
                    "success": True,
                    "name": metadata.name,
                    "message": f'Plugin "{metadata.name}" installed disabled; review instructions before enabling',
                }
            )
    except Exception as exc:
        result["message"] = f"Installation failed: {exc}"
    finally:
        if local_stage is not None and local_stage.exists():
            shutil.rmtree(local_stage)
        if backup is not None and backup.exists():
            target_name = expected_name or result.get("name")
            recovery_target = plugins_dir / str(target_name) if target_name else None
            if recovery_target is not None and not recovery_target.exists():
                os.replace(backup, recovery_target)
            else:
                shutil.rmtree(backup)
    return result


def install_plugin(project_root: str, source: str) -> dict[str, Any]:
    """Install validated text instructions without importing or executing plugin files."""
    return _install_plugin(project_root, source, replace=False)


def enable_plugin(project_root: str, name: str, enabled: bool = True) -> dict[str, Any]:
    """Enable or disable an plugin."""
    registry = load_registry(project_root)
    plugins = registry.get("plugins", [])

    for ext in plugins:
        if ext.get("name") == name:
            ext["enabled"] = enabled
            save_registry(project_root, registry)
            status = "enabled" if enabled else "disabled"
            return {"success": True, "message": f'Plugin "{name}" {status}'}

    return {"success": False, "message": f'Plugin "{name}" not found'}


def uninstall_plugin(project_root: str, name: str) -> dict[str, Any]:
    """Uninstall an plugin."""
    if re.fullmatch(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?", name) is None:
        return {"success": False, "message": f'Plugin "{name}" not found'}
    plugins_dir = get_plugins_dir(project_root)
    ext_path = plugins_dir / name

    if not ext_path.exists():
        return {"success": False, "message": f'Plugin "{name}" not found'}

    # Remove directory
    shutil.rmtree(ext_path)

    # Update registry
    registry = load_registry(project_root)
    plugins = registry.get("plugins", [])
    plugins = [e for e in plugins if e.get("name") != name]
    registry["plugins"] = plugins
    save_registry(project_root, registry)

    return {"success": True, "message": f'Plugin "{name}" uninstalled'}


def update_plugin(project_root: str, name: str) -> dict[str, Any]:
    """Update a plugin to the latest version."""
    registry = load_registry(project_root)
    plugins = registry.get("plugins", [])

    # Find plugin
    plugin_entry = next((p for p in plugins if p.get("name") == name), None)
    if not plugin_entry:
        return {"success": False, "message": f'Plugin "{name}" not found'}

    # Check source
    source_meta = plugin_entry.get("source", {})
    # Handle legacy registry entries
    if isinstance(source_meta, str):
        # Try to guess
        if re.match(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$", source_meta):
            source_type = "github"
            source_origin = source_meta
        elif source_meta.startswith("http"):
            source_type = "url"
            source_origin = source_meta
        else:
            source_type = "local"
            source_origin = source_meta
    else:
        source_type = source_meta.get("type", "local")
        source_origin = source_meta.get("origin")

    if source_type == "local":
        return {"success": False, "message": f'Plugin "{name}" is installed locally. Please update files manually.'}

    if not isinstance(source_origin, str) or not source_origin:
        return {"success": False, "message": f'Plugin "{name}" has no valid update source'}
    return _install_plugin(project_root, source_origin, replace=True, expected_name=name)


def print_plugins(plugins: list[dict[str, Any]]):
    """Print plugin list."""
    if not plugins:
        print("No plugins installed.")
        return

    print(f"{'Name':<25} {'Type':<12} {'Version':<10} {'Status':<10}")
    print("-" * 60)
    for ext in plugins:
        status = "✅ enabled" if ext.get("enabled", True) else "❌ disabled"
        print(f"{ext.get('name', 'unknown'):<25} {ext.get('type', '-'):<12} {ext.get('version', '-'):<10} {status:<10}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python plugin_manager.py list [project_path]")
        print("  python plugin_manager.py install <source> [project_path]")
        print("  python plugin_manager.py update <name> [project_path]")
        print("  python plugin_manager.py enable <name> [project_path]")
        print("  python plugin_manager.py disable <name> [project_path]")
        print("  python plugin_manager.py uninstall <name> [project_path]")
        sys.exit(1)

    command = sys.argv[1]

    # Default project path is current working directory
    project_path = os.getcwd()

    # Parse rest of arguments more carefully
    args = sys.argv[2:]
    source = None
    target_name = None

    if command == "install":
        if len(args) > 0:
            source = args[0]
            # If there's a second argument and it's not a flag, it might be project path
            if len(args) > 1 and not args[1].startswith("-"):
                project_path = args[1]

    elif command == "update" or command in ["enable", "disable", "uninstall"]:
        if len(args) > 0:
            target_name = args[0]
            if len(args) > 1 and not args[1].startswith("-"):
                project_path = args[1]

    elif command == "list" and len(args) > 0 and not args[0].startswith("-"):
        project_path = args[0]

    print(f"Project root: {project_path}")

    if command == "list":
        plugins = list_plugins(project_path)
        print_plugins(plugins)

    elif command == "install":
        if not source:
            print("Error: source path or URL required")
            sys.exit(1)
        result = install_plugin(project_path, source)

        print(result["message"])
        sys.exit(0 if result["success"] else 1)

    elif command == "update":
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = update_plugin(project_path, target_name)
        print(result["message"])
        sys.exit(0 if result["success"] else 1)

    elif command == "enable":
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = enable_plugin(project_path, target_name, True)
        print(result["message"])

    elif command == "disable":
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = enable_plugin(project_path, target_name, False)
        print(result["message"])

    elif command == "uninstall":
        if not target_name:
            print("Error: plugin name required")
            sys.exit(1)
        result = uninstall_plugin(project_path, target_name)
        print(result["message"])

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
