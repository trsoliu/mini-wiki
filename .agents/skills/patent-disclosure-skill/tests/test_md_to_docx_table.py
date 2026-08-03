"""md_to_docx 表格行解析：单元格内 LaTeX \\| 不应拆列。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from md_to_docx import _parse_table_row  # noqa: E402


def test_latex_norm_pipes_in_cell_stays_one_column() -> None:
    row = (
        "| \\(I_W\\)<!-- ![公式·行内](math_figures/inline_075.png) --> "
        "| 队首窗口内任务索引集合 "
        "| \\(\\|I_W\\| \\leq W\\)<!-- ![公式·行内](math_figures/inline_076.png) --> |"
    )
    cells = _parse_table_row(row)
    assert len(cells) == 3
    assert cells[1] == "队首窗口内任务索引集合"
    assert "\\|I_W\\|" in cells[2]
    assert "inline_076.png" in cells[2]


def test_simple_three_column_row() -> None:
    row = "| \\(M_{ij}\\) | 匹配分 | 无量纲 |"
    assert _parse_table_row(row) == ["\\(M_{ij}\\)", "匹配分", "无量纲"]


def test_escaped_pipe_outside_math() -> None:
    row = r"| a \| b | c |"
    cells = _parse_table_row(row)
    assert len(cells) == 2
    assert cells[0] == r"a \| b"
    assert cells[1] == "c"
