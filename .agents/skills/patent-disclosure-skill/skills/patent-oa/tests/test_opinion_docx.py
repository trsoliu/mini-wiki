# -*- coding: utf-8 -*-
"""意见陈述模板与本包 md_to_docx 副本。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from emit_opinion_docx import emit_opinion_docx
from md_to_docx import convert_md_to_docx


class OpinionStatementDocxTests(unittest.TestCase):
    def test_template_converts(self) -> None:
        tpl = (PKG / "assets" / "opinion_statement.md").read_text(encoding="utf-8")
        filled = tpl.replace("（申请号）", "CN202510000000.X").replace(
            "（名称）", "一种示例装置"
        )
        doc = convert_md_to_docx(filled, base_dir=None, prefer_omml=False)
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                texts.extend(c.text for c in row.cells)
        blob = "\n".join(texts)
        self.assertIn("意见陈述书", blob)
        self.assertIn("逐条答复", blob)
        self.assertIn("CN202510000000.X", blob)

    def test_emit_writes_docx(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "意见陈述_test.md"
            md.write_text("# 意见陈述书\n\n申请人陈述如下。\n", encoding="utf-8")
            out = emit_opinion_docx(md)
            self.assertTrue(out.is_file())
            self.assertEqual(out.suffix, ".docx")


if __name__ == "__main__":
    unittest.main()
