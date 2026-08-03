"""Tests for repository scanning boundaries."""

from pathlib import Path

from mini_wiki_core.config import load_config
from mini_wiki_core.scanner import scan_sources


def test_scan_excludes_agent_gitignored_and_vault_content(v3_project: Path):
    agent_file = v3_project / ".agents" / "skills" / "vendor" / "tool.py"
    agent_file.parent.mkdir(parents=True)
    agent_file.write_text("pass\n")
    generated_file = v3_project / "generated" / "secret.py"
    generated_file.parent.mkdir()
    generated_file.write_text("pass\n")
    vault_file = v3_project / "wiki" / "generated.py"
    vault_file.write_text("pass\n")
    (v3_project / ".gitignore").write_text("generated/\n")

    sources = scan_sources(load_config(v3_project))

    assert [source.path.as_posix() for source in sources] == ["src/core/app.py"]


def test_scan_returns_stable_hash_language_and_size(v3_project: Path):
    source_path = v3_project / "src" / "core" / "app.py"
    expected_size = source_path.stat().st_size

    first = scan_sources(load_config(v3_project))
    second = scan_sources(load_config(v3_project))

    assert first == second
    assert first[0].sha256.startswith("sha256:")
    assert len(first[0].sha256) == 71
    assert first[0].language == "python"
    assert first[0].size == expected_size


def test_scan_skips_files_over_configured_limit(v3_project: Path):
    config_path = v3_project / ".mini-wiki" / "config.yaml"
    config_text = config_path.read_text().replace("max_file_size: 100000", "max_file_size: 4")
    config_path.write_text(config_text)

    assert scan_sources(load_config(v3_project)) == []


def test_scan_skips_symlinked_source(v3_project: Path):
    outside = v3_project.parent / "outside.py"
    outside.write_text("secret = True\n")
    link = v3_project / "src" / "linked.py"
    link.symlink_to(outside)

    paths = [source.path.as_posix() for source in scan_sources(load_config(v3_project))]

    assert "src/linked.py" not in paths
