"""Language-aware source parsing that never imports or executes source code."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mini_wiki_core.models import SourceFile


@dataclass(frozen=True)
class SourceAnalysis:
    """Symbols and imports extracted from one source file."""

    symbols: tuple[str, ...]
    imports: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def _python_analysis(path: Path, text: str) -> SourceAnalysis:
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return SourceAnalysis((), (), (f"Unable to parse {path.as_posix()}: {exc.msg}",))

    symbols = {
        node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level + (node.module or "")
            for alias in node.names:
                imports.add(prefix if alias.name == "*" else f"{prefix}.{alias.name}".strip("."))
    return SourceAnalysis(tuple(sorted(symbols)), tuple(sorted(imports)))


def _script_analysis(path: Path, text: str) -> SourceAnalysis:
    declaration_pattern = re.compile(
        r"(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function|class|interface|type)\s+([A-Za-z_$][\w$]*)"
    )
    variable_pattern = re.compile(r"(?:export\s+)(?:const|let|var)\s+([A-Za-z_$][\w$]*)")
    symbols = set(declaration_pattern.findall(text)) | set(variable_pattern.findall(text))
    imports = set(re.findall(r"from\s+[\"']([^\"']+)[\"']", text))
    imports.update(re.findall(r"require\(\s*[\"']([^\"']+)[\"']\s*\)", text))
    return SourceAnalysis(tuple(sorted(symbols)), tuple(sorted(imports)))


def _go_analysis(path: Path, text: str) -> SourceAnalysis:
    symbols = set(re.findall(r"^func\s+(?:\([^)]*\)\s*)?([A-Za-z_]\w*)", text, re.MULTILINE))
    symbols.update(re.findall(r"^type\s+([A-Za-z_]\w*)", text, re.MULTILINE))
    imports = set(re.findall(r"^[ \t]*(?:[A-Za-z_]\w*\s+)?\"([^\"]+)\"", text, re.MULTILINE))
    return SourceAnalysis(tuple(sorted(symbols)), tuple(sorted(imports)))


def analyze_source(project_root: str | Path, source: SourceFile) -> SourceAnalysis:
    """Read and parse a source file, returning warnings instead of executing it."""
    path = Path(project_root) / source.path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return SourceAnalysis((), (), (f"Unable to read {source.path.as_posix()}: {exc}",))

    suffix = source.path.suffix.lower()
    if suffix in {".py", ".pyi"}:
        return _python_analysis(source.path, text)
    if suffix == ".go":
        return _go_analysis(source.path, text)
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte", ".astro"}:
        return _script_analysis(source.path, text)
    return SourceAnalysis((), ())
