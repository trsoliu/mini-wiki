"""Tests for scripts/detect_changes.py."""

import json
from pathlib import Path

from detect_changes import (
    calculate_file_hash,
    should_include_file,
    scan_project_files,
    detect_changes,
    DEFAULT_EXCLUDES,
    CODE_EXTENSIONS,
    DOC_EXTENSIONS,
)


# --- calculate_file_hash ---


def test_calculate_file_hash_returns_hex_string(tmp_path):
    """Hash of a known file should be a 16-char hex string."""
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")

    result = calculate_file_hash(str(f))

    assert isinstance(result, str)
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_calculate_file_hash_deterministic(tmp_path):
    """Same content should always produce the same hash."""
    f = tmp_path / "a.txt"
    f.write_text("deterministic", encoding="utf-8")

    assert calculate_file_hash(str(f)) == calculate_file_hash(str(f))


def test_calculate_file_hash_different_content(tmp_path):
    """Different content should produce different hashes."""
    f1 = tmp_path / "a.txt"
    f1.write_text("content A", encoding="utf-8")
    f2 = tmp_path / "b.txt"
    f2.write_text("content B", encoding="utf-8")

    assert calculate_file_hash(str(f1)) != calculate_file_hash(str(f2))


def test_calculate_file_hash_empty_file(tmp_path):
    """Empty file should still return a valid hash."""
    f = tmp_path / "empty.txt"
    f.write_bytes(b"")

    result = calculate_file_hash(str(f))
    assert len(result) == 16


def test_calculate_file_hash_nonexistent_file():
    """Non-existent file should return empty string."""
    result = calculate_file_hash("/no/such/file.txt")
    assert result == ""


# --- should_include_file ---


def test_should_include_code_files():
    """Code files with known extensions should be included."""
    for ext in [".py", ".ts", ".js", ".go", ".rs", ".vue"]:
        p = Path(f"src/app{ext}")
        assert should_include_file(p, DEFAULT_EXCLUDES) is True


def test_should_include_doc_files():
    """Documentation files should be included."""
    for ext in [".md", ".mdx", ".rst", ".txt"]:
        p = Path(f"docs/readme{ext}")
        assert should_include_file(p, DEFAULT_EXCLUDES) is True


def test_should_exclude_non_code_files():
    """Non-code, non-doc files should be excluded."""
    for name in ["image.png", "data.csv", "archive.zip", "style.css"]:
        p = Path(f"assets/{name}")
        assert should_include_file(p, DEFAULT_EXCLUDES) is False


def test_should_exclude_directories():
    """Files inside excluded directories should be excluded."""
    excluded_dirs = ["node_modules", ".git", "__pycache__", "dist", ".mini-wiki"]
    for d in excluded_dirs:
        p = Path(d) / "some_file.py"
        assert should_include_file(p, DEFAULT_EXCLUDES) is False


def test_should_include_with_custom_excludes():
    """Custom exclude set should be respected."""
    p = Path("mydir/app.py")
    assert should_include_file(p, {"mydir"}) is False
    assert should_include_file(p, {"otherdir"}) is True


def test_should_exclude_glob_pattern():
    """Glob patterns like *.min.js should work via the startswith('*') logic."""
    p = Path("src/bundle.min.js")
    excludes = {"*.min.js"}
    assert should_include_file(p, excludes) is False


# --- scan_project_files ---


def test_scan_project_files_finds_code_and_docs(tmp_project):
    """Scan should find code and doc files, skip excluded dirs."""
    result = scan_project_files(str(tmp_project))

    assert "src/core/app.py" in result
    assert "src/core/main.ts" in result
    assert "src/utils/helpers.js" in result
    assert "docs/readme.md" in result


def test_scan_project_files_excludes_node_modules(tmp_project):
    """Files in node_modules should not appear."""
    result = scan_project_files(str(tmp_project))

    for key in result:
        assert "node_modules" not in key


def test_scan_project_files_excludes_pycache(tmp_project):
    """Files in __pycache__ should not appear."""
    result = scan_project_files(str(tmp_project))

    for key in result:
        assert "__pycache__" not in key


def test_scan_project_files_skips_binary(tmp_project):
    """Binary / non-code files like .png should not appear."""
    result = scan_project_files(str(tmp_project))

    for key in result:
        assert not key.endswith(".png")


def test_scan_project_files_empty_dir(tmp_path):
    """Empty directory should return empty dict."""
    result = scan_project_files(str(tmp_path))
    assert result == {}


def test_scan_project_files_checksums_are_valid(tmp_project):
    """All returned checksums should be 16-char hex strings."""
    result = scan_project_files(str(tmp_project))

    for path, checksum in result.items():
        assert len(checksum) == 16, f"Bad checksum length for {path}"
        assert all(c in "0123456789abcdef" for c in checksum)


# --- detect_changes ---


def test_detect_changes_all_new(tmp_project):
    """With no cache, all files should be reported as added."""
    changes = detect_changes(str(tmp_project))

    assert changes["has_changes"] is True
    assert len(changes["added"]) > 0
    assert changes["modified"] == []
    assert changes["deleted"] == []
    assert "新增" in changes["summary"]


def test_detect_changes_no_changes(tmp_project):
    """After caching current checksums, detect_changes should report no changes."""
    # First pass: populate cache
    first = detect_changes(str(tmp_project))
    cache_dir = tmp_project / ".mini-wiki" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "checksums.json"
    cache_data = {
        k: {"hash": v} for k, v in first["current_checksums"].items()
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # Second pass: should detect no changes
    second = detect_changes(str(tmp_project))

    assert second["has_changes"] is False
    assert second["added"] == []
    assert second["modified"] == []
    assert second["deleted"] == []
    assert "无变更" in second["summary"]


def test_detect_changes_modified_file(tmp_project):
    """Modifying a file should be detected."""
    first = detect_changes(str(tmp_project))
    cache_dir = tmp_project / ".mini-wiki" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "checksums.json"
    cache_data = {
        k: {"hash": v} for k, v in first["current_checksums"].items()
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # Modify a file
    (tmp_project / "src" / "core" / "app.py").write_text("print('changed')\n", encoding="utf-8")

    second = detect_changes(str(tmp_project))

    assert second["has_changes"] is True
    assert "src/core/app.py" in second["modified"]
    assert "修改" in second["summary"]


def test_detect_changes_deleted_file(tmp_project):
    """Deleting a file should be detected."""
    first = detect_changes(str(tmp_project))
    cache_dir = tmp_project / ".mini-wiki" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "checksums.json"
    cache_data = {
        k: {"hash": v} for k, v in first["current_checksums"].items()
    }
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")

    # Delete a file
    (tmp_project / "src" / "utils" / "helpers.js").unlink()

    second = detect_changes(str(tmp_project))

    assert second["has_changes"] is True
    assert "src/utils/helpers.js" in second["deleted"]
    assert "删除" in second["summary"]
