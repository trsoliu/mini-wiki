"""Shared pytest fixtures for Mini-Wiki tests."""

import json
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory structure."""
    # Create basic project structure
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "docs").mkdir()

    # Create some sample files
    (tmp_path / "src" / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "src" / "utils.py").write_text("def helper():\n    return True\n")
    (tmp_path / "README.md").write_text("# Test Project\n")

    return tmp_path


@pytest.fixture
def sample_markdown(tmp_path: Path) -> Path:
    """Create a sample markdown file for testing."""
    content = """# Module Documentation

## Overview
This is a test module.

## API Reference

### Function: test_func

```python
def test_func(x: int) -> int:
    return x * 2
```

## Examples

```python
result = test_func(5)
assert result == 10
```

## Architecture

```mermaid
flowchart TB
    A[Input] --> B[Process]
    B --> C[Output]
```
"""
    md_file = tmp_path / "test.md"
    md_file.write_text(content)
    return md_file


@pytest.fixture
def sample_structure() -> Dict:
    """Sample project structure data."""
    return {
        "project_type": ["python", "nodejs"],
        "modules": [
            {"name": "core", "path": "src/core", "files": 5},
            {"name": "utils", "path": "src/utils", "files": 3},
            {"name": "api", "path": "src/api", "files": 8},
        ],
        "tech_stack": ["python", "fastapi", "pytest"],
    }
