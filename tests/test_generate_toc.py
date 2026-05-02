"""Tests for scripts/generate_toc.py."""

from pathlib import Path

from generate_toc import extract_title_from_markdown, generate_toc


# --- extract_title_from_markdown ---


def test_extract_title_from_h1(tmp_path):
    """Should extract the first H1 heading as the title."""
    f = tmp_path / "doc.md"
    f.write_text("# My Title\n\nBody text.\n", encoding="utf-8")

    assert extract_title_from_markdown(str(f)) == "My Title"


def test_extract_title_skips_non_h1(tmp_path):
    """Should skip H2/H3 and find the first H1."""
    f = tmp_path / "doc.md"
    f.write_text("## Not this\n\n# Real Title\n", encoding="utf-8")

    assert extract_title_from_markdown(str(f)) == "Real Title"


def test_extract_title_fallback_to_filename(tmp_path):
    """Without an H1, should derive title from filename."""
    f = tmp_path / "my-module.md"
    f.write_text("No heading here.\n", encoding="utf-8")

    result = extract_title_from_markdown(str(f))
    assert "my" in result.lower() and "module" in result.lower()


def test_extract_title_nonexistent_file():
    """Non-existent file should return the stem of the path."""
    result = extract_title_from_markdown("/no/such/cool-feature.md")
    assert "cool-feature" in result or "cool" in result.lower()


# --- generate_toc ---


def test_generate_toc_empty_dir(tmp_path):
    """Empty wiki dir should return a fallback message."""
    result = generate_toc(str(tmp_path / "nonexistent"))
    assert "目录为空" in result


def test_generate_toc_with_index(tmp_path):
    """Should include index.md in the TOC."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "index.md").write_text("# Home\n\nWelcome.\n", encoding="utf-8")

    result = generate_toc(str(wiki))

    assert "Home" in result
    assert "index.md" in result


# PLACEHOLDER_TOC_PART2
