# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from emit_application_docx import LatexDelimError, emit_one, main as emit_main


class EmitApplicationDocxDelimTests(unittest.TestCase):
    def test_bare_paren_skips_docx(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "说明书.md"
            md.write_text("# 说明书\n\n" + r"记 (M_{\mathrm{total}}) 克。" + "\n", encoding="utf-8")
            with self.assertRaises(LatexDelimError):
                emit_one(md)
            self.assertFalse(md.with_suffix(".docx").is_file())

    def test_correct_delim_writes_docx(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "说明书.md"
            md.write_text("# 说明书\n\n" + r"记 \(M_{\mathrm{total}}\) 克。" + "\n", encoding="utf-8")
            out = emit_one(md)
            self.assertTrue(out.is_file())

    def test_cli_skips_bad_file_keeps_good(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "说明书.md").write_text(
                "# 说明书\n\n" + r"(M_{\mathrm{total}})" + "\n", encoding="utf-8"
            )
            (Path(tmp) / "说明书摘要.md").write_text("# 摘要\n\n无公式。\n", encoding="utf-8")
            code = emit_main(["--dir", tmp])
            self.assertEqual(code, 1)
            self.assertFalse((Path(tmp) / "说明书.docx").is_file())
            self.assertTrue((Path(tmp) / "说明书摘要.docx").is_file())


if __name__ == "__main__":
    unittest.main()
