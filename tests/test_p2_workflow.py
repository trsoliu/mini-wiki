"""End-to-end P0-P2 acceptance without an Obsidian installation."""

import json
import shutil
from pathlib import Path

from click.testing import CliRunner

from cli import main


def test_complete_p0_p1_p2_workflow(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    source = tmp_path / "src" / "安全插件" / "plugin.py"
    source.parent.mkdir(parents=True)
    source.write_text("def install_plugin():\n    return '安全安装插件'\n")
    runner = CliRunner()

    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["build", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["check", "--strict", str(tmp_path)]).exit_code == 0

    search = runner.invoke(main, ["search", "安全插件", "--json", str(tmp_path)])
    assert search.exit_code == 0
    assert json.loads(search.output)["hits"]

    assert len(list((tmp_path / "wiki" / "views").glob("*.base"))) == 4
    assert len(list((tmp_path / "wiki" / "canvas").glob("*.canvas"))) == 3

    status = runner.invoke(main, ["obsidian", "status", "--json", str(tmp_path)])
    assert status.exit_code == 0
    assert json.loads(status.output)["core_blocked"] is False
