"""Tests for check_quality.py module."""

import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from check_quality import QualityMetrics, analyze_document


def test_analyze_document_basic(sample_markdown):
    """Test basic document analysis."""
    metrics = analyze_document(str(sample_markdown))
    
    assert metrics.file_path == str(sample_markdown)
    assert metrics.line_count > 0
    assert metrics.section_count >= 2  # At least 2 H2 sections
    assert metrics.diagram_count >= 1  # At least 1 mermaid diagram
    assert metrics.code_example_count >= 1  # At least 1 code example


def test_analyze_document_quality_levels(tmp_path):
    """Test quality level classification."""
    # Basic quality document
    basic_doc = tmp_path / "basic.md"
    basic_doc.write_text("""# Title
## Section 1
Some content.
""")
    
    metrics = analyze_document(str(basic_doc))
    assert metrics.section_count < 8
    assert metrics.quality_level in ["basic", "standard"]


def test_analyze_document_nonexistent():
    """Test handling of nonexistent file."""
    metrics = analyze_document("/nonexistent/file.md")
    assert len(metrics.issues) > 0
    assert "无法读取文件" in metrics.issues[0]


def test_analyze_document_mermaid_detection(tmp_path):
    """Test mermaid diagram detection."""
    doc = tmp_path / "with_diagram.md"
    doc.write_text("""# Title

```mermaid
flowchart TB
    A --> B
```

```mermaid
classDiagram
    class Foo
```
""")
    
    metrics = analyze_document(str(doc))
    assert metrics.diagram_count == 2
    assert metrics.class_diagram_count == 1
