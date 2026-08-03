"""Tests for side-effect-free optional Obsidian integration."""

from pathlib import Path

from mini_wiki_core.config import load_config
from mini_wiki_core.obsidian import (
    ObsidianStatus,
    detect_obsidian,
    open_vault,
    probe_obsidian_version,
    vault_uri,
)


def test_absent_obsidian_is_an_available_core_environment():
    status = detect_obsidian(which=lambda _: None, platform_name="linux")

    assert status.cli_available is False
    assert status.uri_available is False
    assert status.core_blocked is False


def test_detection_never_invokes_the_cli():
    calls: list[str] = []

    status = detect_obsidian(
        which=lambda command: calls.append(command) or "/usr/bin/obsidian",
        platform_name="linux",
    )

    assert status.cli_available is True
    assert calls == ["obsidian"]
    assert status.version is None


def test_probe_uses_official_version_command_only_when_requested():
    calls: list[list[str]] = []
    status = ObsidianStatus(True, "/usr/bin/obsidian", True, False, None)

    probed = probe_obsidian_version(status, runner=lambda argv: calls.append(argv) or "1.12.7")

    assert probed.version == "1.12.7"
    assert calls == [["/usr/bin/obsidian", "version"]]


def test_open_uses_uri_only_after_explicit_request(v3_project: Path):
    calls: list[str] = []
    status = ObsidianStatus(True, "/usr/bin/obsidian", True, False, None)

    result = open_vault(
        load_config(v3_project),
        status,
        uri_opener=lambda uri: calls.append(uri) or 0,
    )

    assert result.success is True
    assert calls == [vault_uri(v3_project / "wiki")]


def test_open_on_unsupported_platform_returns_instructions_without_launch(v3_project: Path):
    calls: list[str] = []
    status = ObsidianStatus(False, None, False, False, None)

    result = open_vault(
        load_config(v3_project),
        status,
        uri_opener=lambda uri: calls.append(uri) or 0,
    )

    assert result.success is False
    assert "manually" in result.message
    assert calls == []


def test_vault_uri_uses_encoded_absolute_path_without_file_url(tmp_path: Path):
    vault = tmp_path / "Wiki Vault"

    uri = vault_uri(vault)

    assert uri.startswith("obsidian://open?path=")
    assert "%2F" in uri
    assert "Wiki+Vault" in uri
    assert "file://" not in uri
