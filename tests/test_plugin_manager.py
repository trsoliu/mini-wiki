"""Tests for scripts/plugin_manager.py."""

import yaml

from plugin_manager import (
    _install_plugin,
    enable_plugin,
    get_plugins_dir,
    get_registry_path,
    install_plugin,
    list_plugins,
    load_registry,
    parse_plugin_manifest,
    save_registry,
    uninstall_plugin,
)

# --- path helpers ---


def test_get_plugins_dir(tmp_path):
    result = get_plugins_dir(str(tmp_path))
    assert result == tmp_path / "plugins"


def test_get_registry_path(tmp_path):
    result = get_registry_path(str(tmp_path))
    assert result == tmp_path / "plugins" / "_registry.yaml"


# --- load_registry / save_registry ---


def test_load_registry_empty(tmp_path):
    result = load_registry(str(tmp_path))
    assert result == {"plugins": []}


def test_load_registry_existing(tmp_path):
    reg_path = tmp_path / "plugins" / "_registry.yaml"
    reg_path.parent.mkdir(parents=True)
    reg_path.write_text(yaml.dump({"plugins": [{"name": "test", "enabled": True}]}))

    result = load_registry(str(tmp_path))
    assert len(result["plugins"]) == 1
    assert result["plugins"][0]["name"] == "test"


def test_save_registry_creates_file(tmp_path):
    registry = {"plugins": [{"name": "foo", "enabled": True}]}
    save_registry(str(tmp_path), registry)

    reg_path = tmp_path / "plugins" / "_registry.yaml"
    assert reg_path.exists()
    loaded = yaml.safe_load(reg_path.read_text())
    assert loaded["plugins"][0]["name"] == "foo"


def test_save_and_load_roundtrip(tmp_path):
    original = {
        "plugins": [
            {"name": "a", "enabled": True, "priority": 10},
            {"name": "b", "enabled": False, "priority": 20},
        ]
    }
    save_registry(str(tmp_path), original)
    loaded = load_registry(str(tmp_path))
    assert len(loaded["plugins"]) == 2
    assert loaded["plugins"][1]["name"] == "b"


# --- parse_plugin_manifest ---


def _create_plugin(tmp_path, name, manifest_content):
    """Helper to create a plugin directory with PLUGIN.md."""
    plugin_dir = tmp_path / "plugins" / name
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "PLUGIN.md").write_text(manifest_content)
    return plugin_dir


def test_parse_plugin_manifest_valid(tmp_path):
    plugin_dir = _create_plugin(
        tmp_path,
        "test-plugin",
        """---
name: test-plugin
type: analyzer
version: 1.0.0
description: A test plugin
---

# Test Plugin
""",
    )
    result = parse_plugin_manifest(plugin_dir)
    assert result is not None
    assert result["name"] == "test-plugin"
    assert result["type"] == "analyzer"
    assert result["version"] == "1.0.0"


def test_parse_plugin_manifest_no_frontmatter(tmp_path):
    plugin_dir = _create_plugin(tmp_path, "no-fm", "# Just a heading\nNo frontmatter here.")
    result = parse_plugin_manifest(plugin_dir)
    assert result is None


def test_parse_plugin_manifest_no_file(tmp_path):
    plugin_dir = tmp_path / "plugins" / "empty"
    plugin_dir.mkdir(parents=True)
    result = parse_plugin_manifest(plugin_dir)
    assert result is None


def test_parse_plugin_manifest_invalid_yaml(tmp_path):
    plugin_dir = _create_plugin(
        tmp_path,
        "bad-yaml",
        """---
name: [invalid yaml
  broken: {
---
""",
    )
    result = parse_plugin_manifest(plugin_dir)
    assert result is None


# --- list_plugins ---


def test_list_plugins_empty(tmp_path):
    result = list_plugins(str(tmp_path))
    assert result == []


def test_list_plugins_with_plugins(tmp_path):
    _create_plugin(
        tmp_path,
        "plugin-a",
        """---
name: plugin-a
type: analyzer
version: 1.0.0
description: Plugin A
---
# Plugin A
""",
    )
    _create_plugin(
        tmp_path,
        "plugin-b",
        """---
name: plugin-b
type: generator
version: 2.0.0
description: Plugin B
---
# Plugin B
""",
    )

    result = list_plugins(str(tmp_path))
    names = [p["name"] for p in result]
    assert "plugin-a" in names
    assert "plugin-b" in names


def test_list_plugins_skips_underscore_dirs(tmp_path):
    _create_plugin(
        tmp_path,
        "_example",
        """---
name: _example
type: analyzer
version: 1.0.0
description: Example
---
""",
    )
    result = list_plugins(str(tmp_path))
    names = [p["name"] for p in result]
    assert "_example" not in names


def test_list_plugins_respects_registry(tmp_path):
    _create_plugin(
        tmp_path,
        "my-plugin",
        """---
name: my-plugin
type: analyzer
version: 1.0.0
description: My Plugin
---
""",
    )
    registry = {"plugins": [{"name": "my-plugin", "enabled": False, "priority": 5}]}
    save_registry(str(tmp_path), registry)

    result = list_plugins(str(tmp_path))
    assert len(result) == 1
    assert result[0]["enabled"] is False
    assert result[0]["priority"] == 5


# --- enable_plugin ---


def test_enable_plugin_success(tmp_path):
    registry = {"plugins": [{"name": "test", "enabled": False}]}
    save_registry(str(tmp_path), registry)

    result = enable_plugin(str(tmp_path), "test", True)
    assert result["success"] is True

    loaded = load_registry(str(tmp_path))
    assert loaded["plugins"][0]["enabled"] is True


def test_disable_plugin_success(tmp_path):
    registry = {"plugins": [{"name": "test", "enabled": True}]}
    save_registry(str(tmp_path), registry)

    result = enable_plugin(str(tmp_path), "test", False)
    assert result["success"] is True
    assert "disabled" in result["message"]


def test_enable_plugin_not_found(tmp_path):
    registry = {"plugins": []}
    save_registry(str(tmp_path), registry)

    result = enable_plugin(str(tmp_path), "nonexistent", True)
    assert result["success"] is False
    assert "not found" in result["message"]


# --- uninstall_plugin ---


def test_uninstall_plugin_success(tmp_path):
    _create_plugin(
        tmp_path,
        "to-remove",
        """---
name: to-remove
type: analyzer
version: 1.0.0
description: Will be removed
---
""",
    )
    registry = {"plugins": [{"name": "to-remove", "enabled": True}]}
    save_registry(str(tmp_path), registry)

    result = uninstall_plugin(str(tmp_path), "to-remove")
    assert result["success"] is True
    assert not (tmp_path / "plugins" / "to-remove").exists()

    loaded = load_registry(str(tmp_path))
    names = [p["name"] for p in loaded["plugins"]]
    assert "to-remove" not in names


def test_uninstall_plugin_not_found(tmp_path):
    result = uninstall_plugin(str(tmp_path), "nonexistent")
    assert result["success"] is False
    assert "not found" in result["message"]


# --- secure instruction-only installation ---


def _instruction_plugin(tmp_path, name="source-plugin", version="1.0.0"):
    plugin = tmp_path / f"{name}-source"
    plugin.mkdir()
    (plugin / "PLUGIN.md").write_text(
        f"---\nname: {name}\ntype: analyzer\nversion: {version}\ndescription: Test instructions\n---\n# Instructions\n"
    )
    return plugin


def test_third_party_install_is_disabled_and_hashed_by_default(tmp_path):
    source = _instruction_plugin(tmp_path)

    result = install_plugin(str(tmp_path), str(source))
    registry = load_registry(str(tmp_path))

    assert result["success"] is True
    assert registry["plugins"][0]["enabled"] is False
    assert registry["plugins"][0]["sha256"].startswith("sha256:")
    assert (tmp_path / "plugins" / "source-plugin" / "PLUGIN.md").exists()


def test_install_never_executes_plugin_scripts(tmp_path):
    source = _instruction_plugin(tmp_path)
    marker = tmp_path / "executed.txt"
    (source / "payload.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n")

    result = install_plugin(str(tmp_path), str(source))

    assert result["success"] is True
    assert not marker.exists()


def test_install_rejects_readme_only_repository(tmp_path):
    source = tmp_path / "generic-source"
    source.mkdir()
    (source / "README.md").write_text("# Generic\n")

    result = install_plugin(str(tmp_path), str(source))

    assert result["success"] is False
    assert "PLUGIN.md or SKILL.md" in result["message"]


def test_install_rejects_insecure_http_without_network_access(tmp_path, monkeypatch):
    called = False

    def unexpected_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    monkeypatch.setattr("urllib.request.urlopen", unexpected_urlopen)

    result = install_plugin(str(tmp_path), "http://example.com/plugin.zip")

    assert result["success"] is False
    assert "HTTPS" in result["message"]
    assert called is False


def test_install_refuses_overwrite_and_preserves_existing_plugin(tmp_path):
    first = _instruction_plugin(tmp_path, version="1.0.0")
    assert install_plugin(str(tmp_path), str(first))["success"] is True
    installed = tmp_path / "plugins" / "source-plugin" / "PLUGIN.md"
    before = installed.read_bytes()

    replacement_root = tmp_path / "replacement"
    replacement_root.mkdir()
    replacement = _instruction_plugin(replacement_root, version="2.0.0")
    result = install_plugin(str(tmp_path), str(replacement))

    assert result["success"] is False
    assert "already installed" in result["message"]
    assert installed.read_bytes() == before


def test_standard_skill_installs_without_mutating_or_wrapping_source(tmp_path):
    source = tmp_path / "skill-source"
    source.mkdir()
    (source / "SKILL.md").write_text(
        "---\nname: source-skill\ndescription: Standard skill instructions\n---\n# Instructions\n"
    )
    before = (source / "SKILL.md").read_bytes()

    result = install_plugin(str(tmp_path), str(source))

    assert result["success"] is True
    assert (source / "SKILL.md").read_bytes() == before
    assert not (source / "PLUGIN.md").exists()
    assert (tmp_path / "plugins" / "source-skill" / "SKILL.md").exists()
    assert not (tmp_path / "plugins" / "source-skill" / "PLUGIN.md").exists()


def test_failed_update_replacement_restores_existing_plugin(tmp_path, monkeypatch):
    first = _instruction_plugin(tmp_path, version="1.0.0")
    assert install_plugin(str(tmp_path), str(first))["success"] is True
    installed = tmp_path / "plugins" / "source-plugin" / "PLUGIN.md"
    before = installed.read_bytes()
    replacement_root = tmp_path / "replacement-update"
    replacement_root.mkdir()
    replacement = _instruction_plugin(replacement_root, version="2.0.0")

    def fail_registry_save(*args):
        raise OSError("registry failure")

    monkeypatch.setattr("plugin_manager.save_registry", fail_registry_save)
    result = _install_plugin(
        str(tmp_path),
        str(replacement),
        replace=True,
        expected_name="source-plugin",
    )

    assert result["success"] is False
    assert "registry failure" in result["message"]
    assert installed.read_bytes() == before
