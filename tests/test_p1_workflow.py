"""End-to-end P1 search and Bases acceptance without Obsidian."""

import json
import shutil
from pathlib import Path

from click.testing import CliRunner

from cli import main


def test_p1_build_search_and_bases_without_obsidian(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    source = tmp_path / "src" / "核心" / "plugin.py"
    source.parent.mkdir(parents=True)
    source.write_text("def install_plugin():\n    return '插件安装'\n")
    runner = CliRunner()

    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["build", str(tmp_path)]).exit_code == 0
    result = runner.invoke(main, ["search", "插件安装", "--json", str(tmp_path)])

    assert result.exit_code == 0
    assert json.loads(result.output)["hits"]
    assert len(list((tmp_path / "wiki" / "views").glob("*.base"))) == 4
    assert runner.invoke(main, ["check", "--strict", str(tmp_path)]).exit_code == 0
