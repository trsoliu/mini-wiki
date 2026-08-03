"""Tests for source parsing without source execution."""

from pathlib import Path

from mini_wiki_core.models import SourceFile
from mini_wiki_core.source_analysis import analyze_source


def source_record(path: str, content: str, root: Path) -> SourceFile:
    source_path = root / path
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(content)
    return SourceFile(Path(path), "sha256:test", "python", len(content.encode()))


def test_python_analysis_extracts_symbols_and_import_targets(tmp_path: Path):
    source = source_record(
        "src/core/a.py",
        "from src.core import b\nimport json\n\nclass Client:\n    pass\n\nasync def run():\n    return b.VALUE\n",
        tmp_path,
    )

    result = analyze_source(tmp_path, source)

    assert result.symbols == ("Client", "run")
    assert result.imports == ("json", "src.core.b")
    assert result.warnings == ()


def test_typescript_analysis_extracts_exports_and_relative_imports(tmp_path: Path):
    source = source_record(
        "src/core/client.ts",
        'import { helper } from "./helper";\nexport class Client {}\nexport const run = () => helper();\n',
        tmp_path,
    )

    result = analyze_source(tmp_path, source)

    assert result.symbols == ("Client", "run")
    assert result.imports == ("./helper",)


def test_syntax_error_becomes_warning_instead_of_exception(tmp_path: Path):
    source = source_record("src/broken.py", "def broken(:\n", tmp_path)

    result = analyze_source(tmp_path, source)

    assert result.symbols == ()
    assert result.imports == ()
    assert result.warnings[0].startswith("Unable to parse src/broken.py")
