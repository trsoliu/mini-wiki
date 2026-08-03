"""Tests for scripts/cli.py."""

from __future__ import annotations

import json

from click.testing import CliRunner

from cli import main

runner = CliRunner()


def test_version():
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "3.2.0" in result.output


def test_help():
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Mini-Wiki" in result.output
    assert "init" in result.output
    assert "analyze" in result.output
    assert "check" in result.output
    assert "changes" in result.output
    assert "build" in result.output
    assert "doctor" in result.output
    assert "plugins" in result.output


def test_init_creates_wiki_dir(tmp_path):
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / ".mini-wiki").exists()
    assert (tmp_path / ".mini-wiki" / "config.yaml").exists()
    assert (tmp_path / ".mini-wiki" / "meta.json").exists()


def test_init_already_exists(tmp_path):
    runner.invoke(main, ["init", str(tmp_path)])
    result = runner.invoke(main, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "已存在" in result.output


def test_init_force(tmp_path):
    runner.invoke(main, ["init", str(tmp_path)])
    result = runner.invoke(main, ["init", "--force", str(tmp_path)])
    assert result.exit_code == 0


def test_analyze(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')")
    result = runner.invoke(main, ["analyze", "--no-cache", str(tmp_path)])
    assert result.exit_code == 0
    assert "项目" in result.output or "技术栈" in result.output


def test_changes(tmp_path):
    (tmp_path / "app.py").write_text("pass")
    result = runner.invoke(main, ["changes", str(tmp_path)])
    assert result.exit_code == 0


def test_build(tmp_path):
    runner.invoke(main, ["init", str(tmp_path)])
    source = tmp_path / "src" / "core" / "app.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run():\n    return 'ok'\n")

    result = runner.invoke(main, ["build", "--json", str(tmp_path)])

    assert result.exit_code == 0
    assert json.loads(result.output)["success"] is True
    assert (tmp_path / "wiki" / "index.md").exists()


def test_build_requires_initialization(tmp_path):
    result = runner.invoke(main, ["build", str(tmp_path)])

    assert result.exit_code == 1
    assert "configuration does not exist" in result.output


def test_check_no_wiki(tmp_path):
    result = runner.invoke(main, ["check", str(tmp_path)])
    assert result.exit_code == 1
    assert "No wiki found" in result.output


def test_check_strict_returns_nonzero_for_broken_network(v3_project):
    broken = v3_project / "wiki" / "broken.md"
    broken.write_text(
        "---\nid: mw:document:broken\ntitle: Broken\ntype: module\n---\n"
        "<!-- mini-wiki:generated:start -->\n[[missing]]\n<!-- mini-wiki:generated:end -->\n"
        "<!-- mini-wiki:content:start -->\ncontent\n<!-- mini-wiki:content:end -->\n"
    )

    result = runner.invoke(main, ["check", "--strict", str(v3_project)])

    assert result.exit_code == 1
    assert "LINK_TARGET_MISSING" in result.output


def test_check_strict_json_reports_healthy_generated_vault(v3_project):
    runner.invoke(main, ["build", str(v3_project)])

    result = runner.invoke(main, ["check", "--strict", "--json", str(v3_project)])

    assert result.exit_code == 0
    assert json.loads(result.output)["ok"] is True


def test_doctor_json_is_machine_readable(v3_project):
    result = runner.invoke(main, ["doctor", "--json", str(v3_project)])

    assert result.exit_code == 0
    assert "findings" in json.loads(result.output)


def test_plugins_list(tmp_path):
    result = runner.invoke(main, ["plugins", "list", str(tmp_path)])
    assert result.exit_code == 0


def test_plugins_help():
    result = runner.invoke(main, ["plugins", "--help"])
    assert result.exit_code == 0
    assert "install" in result.output
    assert "uninstall" in result.output
    assert "enable" in result.output
    assert "disable" in result.output


def test_plugins_enable_not_found(tmp_path):
    (tmp_path / "plugins").mkdir()
    result = runner.invoke(main, ["plugins", "enable", "nonexistent", str(tmp_path)])
    assert "not found" in result.output


def test_plugins_uninstall_not_found(tmp_path):
    result = runner.invoke(main, ["plugins", "uninstall", "nonexistent", str(tmp_path)])
    assert result.exit_code == 1
    assert "not found" in result.output
