"""End-to-end acceptance for the Obsidian-independent P0 workflow."""

import json
from pathlib import Path

from click.testing import CliRunner

from cli import main


def test_p0_init_build_check_doctor_and_rebuild(tmp_path: Path):
    source = tmp_path / "src" / "core" / "app.py"
    source.parent.mkdir(parents=True)
    source.write_text("def run():\n    return 'ok'\n")
    runner = CliRunner()

    assert runner.invoke(main, ["init", str(tmp_path)]).exit_code == 0
    first = runner.invoke(main, ["build", str(tmp_path)])
    assert first.exit_code == 0
    assert (tmp_path / "wiki" / "index.md").exists()
    assert (tmp_path / "wiki" / "domains" / "core" / "core.md").exists()
    assert (tmp_path / "wiki" / "views").is_dir()
    assert runner.invoke(main, ["check", "--strict", str(tmp_path)]).exit_code == 0
    assert runner.invoke(main, ["doctor", str(tmp_path)]).exit_code == 0

    second = runner.invoke(main, ["build", "--json", str(tmp_path)])
    result = json.loads(second.output)
    assert second.exit_code == 0
    assert result["created"] == []
    assert result["modified"] == []
    assert result["archived"] == []
