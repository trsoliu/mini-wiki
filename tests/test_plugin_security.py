"""Security tests for instruction-only Mini-Wiki plugins."""

import stat
from pathlib import Path
from zipfile import ZipFile, ZipInfo

import pytest

from mini_wiki_core.plugin_security import (
    PluginSecurityError,
    download_bounded,
    safe_extract_zip,
    validate_instruction_plugin,
)


def test_safe_extract_rejects_parent_traversal(tmp_path: Path):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("../../escaped.txt", "owned")

    with pytest.raises(PluginSecurityError, match="unsafe path"):
        safe_extract_zip(archive, tmp_path / "out", 1024)

    assert not (tmp_path / "escaped.txt").exists()


def test_safe_extract_rejects_uncompressed_limit_without_partial_files(tmp_path: Path):
    archive = tmp_path / "large.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("PLUGIN.md", "x" * 2048)

    with pytest.raises(PluginSecurityError, match="size limit"):
        safe_extract_zip(archive, tmp_path / "out", 1024)

    assert not (tmp_path / "out" / "PLUGIN.md").exists()


def test_safe_extract_rejects_zip_symlink(tmp_path: Path):
    archive = tmp_path / "link.zip"
    info = ZipInfo("payload-link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive, "w") as zipped:
        zipped.writestr(info, "../../private")

    with pytest.raises(PluginSecurityError, match="symbolic link"):
        safe_extract_zip(archive, tmp_path / "out", 1024)


def test_safe_extract_writes_a_valid_instruction_archive(tmp_path: Path):
    archive = tmp_path / "valid.zip"
    with ZipFile(archive, "w") as zipped:
        zipped.writestr("plugin-main/PLUGIN.md", "# Instructions\n")

    safe_extract_zip(archive, tmp_path / "out", 1024)

    assert (tmp_path / "out" / "plugin-main" / "PLUGIN.md").read_text() == "# Instructions\n"


def test_validate_requires_plugin_or_skill_frontmatter(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Generic repository\n")

    with pytest.raises(PluginSecurityError, match=r"PLUGIN\.md or SKILL\.md"):
        validate_instruction_plugin(tmp_path)


def test_validate_rejects_local_symlink(tmp_path: Path):
    (tmp_path / "PLUGIN.md").write_text(
        "---\nname: safe-plugin\ntype: analyzer\nversion: 1.0.0\ndescription: Safe instructions\n---\n# Instructions\n"
    )
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("private")
    (tmp_path / "linked.txt").symlink_to(outside)

    with pytest.raises(PluginSecurityError, match="symbolic link"):
        validate_instruction_plugin(tmp_path)


def test_download_bounded_rejects_http_before_network(tmp_path: Path, monkeypatch):
    called = False

    def unexpected_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be called")

    monkeypatch.setattr("mini_wiki_core.plugin_security.urllib.request.urlopen", unexpected_urlopen)

    with pytest.raises(PluginSecurityError, match="HTTPS"):
        download_bounded("http://example.com/plugin.zip", tmp_path / "plugin.zip", 1024)

    assert called is False


def test_download_bounded_removes_partial_file_on_limit(tmp_path: Path, monkeypatch):
    class FakeResponse:
        def __init__(self):
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def geturl(self):
            return "https://example.com/plugin.zip"

        def read(self, size):
            return b"x" * size

    monkeypatch.setattr(
        "mini_wiki_core.plugin_security.urllib.request.urlopen",
        lambda request: FakeResponse(),
    )
    destination = tmp_path / "plugin.zip"

    with pytest.raises(PluginSecurityError, match="size limit"):
        download_bounded("https://example.com/plugin.zip", destination, 1024)

    assert not destination.exists()
