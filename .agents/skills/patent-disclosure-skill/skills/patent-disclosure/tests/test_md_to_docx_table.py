"""md_to_docx 表格行解析：单元格内 LaTeX \\| 不应拆列。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from md_to_docx import _parse_table_row


class MdToDocxTableTests(unittest.TestCase):
    def test_latex_norm_pipes_in_cell_stays_one_column(self) -> None:
        row = (
            "| \\(I_W\\)<!-- ![公式·行内](math_figures/inline_075.png) --> "
            "| 队首窗口内任务索引集合 "
            "| \\(\\|I_W\\| \\leq W\\)<!-- ![公式·行内](math_figures/inline_076.png) --> |"
        )
        cells = _parse_table_row(row)
        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[1], "队首窗口内任务索引集合")
        self.assertIn("\\|I_W\\|", cells[2])
        self.assertIn("inline_076.png", cells[2])

    def test_simple_three_column_row(self) -> None:
        row = "| \\(M_{ij}\\) | 匹配分 | 无量纲 |"
        self.assertEqual(
            _parse_table_row(row), ["\\(M_{ij}\\)", "匹配分", "无量纲"]
        )

    def test_escaped_pipe_outside_math(self) -> None:
        row = r"| a \| b | c |"
        cells = _parse_table_row(row)
        self.assertEqual(len(cells), 2)
        self.assertEqual(cells[0], r"a \| b")
        self.assertEqual(cells[1], "c")


if __name__ == "__main__":
    unittest.main()
