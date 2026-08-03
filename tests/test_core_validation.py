"""Tests for structural Mini-Wiki Vault validation."""

from pathlib import Path

from mini_wiki_core.builder import BuildOptions, build_project
from mini_wiki_core.config import load_config
from mini_wiki_core.validation import validate_vault


def write_managed_doc(
    path: Path,
    node_id: str,
    body: str,
    sources: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    source_lines = "\n".join(f"  - {source}" for source in (sources or []))
    path.write_text(
        f"---\nid: {node_id}\ntitle: Test\ntype: module\nsources:\n{source_lines}\n---\n"
        f"<!-- mini-wiki:generated:start -->\n{body}\n<!-- mini-wiki:generated:end -->\n"
        "<!-- mini-wiki:content:start -->\ncontent\n<!-- mini-wiki:content:end -->\n"
    )


def test_validation_reports_duplicate_id_missing_link_and_orphan(v3_project: Path):
    write_managed_doc(v3_project / "wiki" / "a.md", "mw:document:a", "[[missing]]")
    write_managed_doc(v3_project / "wiki" / "b.md", "mw:document:a", "no links")

    report = validate_vault(load_config(v3_project))

    assert {issue.code for issue in report.issues} >= {
        "DUPLICATE_ID",
        "LINK_TARGET_MISSING",
        "ORPHAN_MANAGED_DOCUMENT",
    }
    assert report.ok is False


def test_generated_vault_passes_strict_structural_validation(v3_project: Path):
    build_project(v3_project, BuildOptions())

    report = validate_vault(load_config(v3_project))

    assert report.ok is True
    assert [issue for issue in report.issues if issue.severity == "error"] == []


def test_validation_reports_changed_source_as_stale(v3_project: Path):
    build_project(v3_project, BuildOptions())
    (v3_project / "src" / "core" / "app.py").write_text("def run():\n    return 'changed'\n")

    report = validate_vault(load_config(v3_project))

    assert "SOURCE_HASH_MISMATCH" in {issue.code for issue in report.issues}
    assert report.ok is False


def test_validation_rejects_source_reference_outside_project(v3_project: Path):
    write_managed_doc(
        v3_project / "wiki" / "unsafe.md",
        "mw:document:unsafe",
        "no links",
        ["../private.py"],
    )

    report = validate_vault(load_config(v3_project))

    assert "SOURCE_OUTSIDE_PROJECT" in {issue.code for issue in report.issues}


def test_validation_reports_unbalanced_managed_regions(v3_project: Path):
    path = v3_project / "wiki" / "broken.md"
    path.write_text(
        "---\nid: mw:document:broken\ntitle: Broken\ntype: module\n---\n"
        "<!-- mini-wiki:generated:start -->\nmissing end\n"
        "<!-- mini-wiki:content:start -->\ncontent\n<!-- mini-wiki:content:end -->\n"
    )

    report = validate_vault(load_config(v3_project))

    assert "MANAGED_REGION_INVALID" in {issue.code for issue in report.issues}


def test_invalid_base_is_a_strict_validation_error(v3_project: Path):
    path = v3_project / "wiki" / "views" / "broken.base"
    path.write_text("views: invalid\n")

    report = validate_vault(load_config(v3_project))

    assert any(issue.code == "INVALID_BASE" and issue.severity == "error" for issue in report.issues)
