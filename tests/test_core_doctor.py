"""Tests for actionable Mini-Wiki project diagnostics."""

from pathlib import Path

from mini_wiki_core.doctor import doctor_project


def test_doctor_reports_missing_initialization_with_remediation(tmp_path: Path):
    report = doctor_project(tmp_path)
    finding = next(item for item in report.findings if item.code == "NOT_INITIALIZED")

    assert finding.severity == "error"
    assert "mini-wiki init" in finding.remediation
    assert report.ok is False


def test_doctor_warns_when_durable_vault_is_gitignored(v3_project: Path):
    (v3_project / ".gitignore").write_text("wiki/\n")

    report = doctor_project(v3_project)

    assert "VAULT_IGNORED" in {item.code for item in report.findings}


def test_doctor_treats_missing_obsidian_as_informational(v3_project: Path, monkeypatch):
    monkeypatch.setattr("mini_wiki_core.doctor.find_obsidian", lambda: None)

    report = doctor_project(v3_project)
    finding = next(item for item in report.findings if item.code == "OBSIDIAN_NOT_FOUND")

    assert finding.severity == "info"


def test_doctor_reports_legacy_mode_without_migrating(tmp_path: Path):
    (tmp_path / ".mini-wiki" / "wiki").mkdir(parents=True)
    (tmp_path / ".mini-wiki" / "config.yaml").write_text("generation:\n  language: zh\n")

    report = doctor_project(tmp_path)

    assert "LEGACY_MODE" in {item.code for item in report.findings}
    assert not (tmp_path / "wiki").exists()
