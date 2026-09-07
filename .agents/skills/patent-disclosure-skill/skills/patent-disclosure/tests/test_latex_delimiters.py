# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from latex_delimiters import find_bare_paren_latex, main as delim_main
from mermaid_render import main as mermaid_main


class BareParenLatexTests(unittest.TestCase):
    def test_correct_inline_paren_math_is_clean(self) -> None:
        md = r"符号 \(M_{\mathrm{total}}\) 与 \(m_{\mathrm{silica}}=60\,\mathrm{g}\)。"
        self.assertEqual(find_bare_paren_latex(md), [])

    def test_dollar_and_block_math_are_clean(self) -> None:
        md = (
            r"行内 $M_{\mathrm{total}}$。"
            "\n\n"
            r"\[ M_{\mathrm{total}} = m_{\mathrm{silica}} + m_{\mathrm{amine}} \]"
            "\n"
        )
        self.assertEqual(find_bare_paren_latex(md), [])

    def test_bare_paren_mathrm_is_hit(self) -> None:
        md = r"记总投料量为 (M_{\mathrm{total}}) 克。"
        hits = find_bare_paren_latex(md)
        self.assertEqual(len(hits), 1)
        self.assertIn(r"\mathrm{total}", hits[0].snippet)

    def test_table_cell_and_thinspace_example(self) -> None:
        md = (
            "| 符号 | 含义 |\n"
            "|------|------|\n"
            r"| (M_{\mathrm{total}}) | 总质量 |"
            "\n"
            r"例如 (m_{\mathrm{silica}}=60\,\mathrm{g})。"
            "\n"
        )
        hits = find_bare_paren_latex(md)
        self.assertGreaterEqual(len(hits), 2)
        blobs = " ".join(h.snippet for h in hits)
        self.assertIn(r"\mathrm{total}", blobs)
        self.assertIn(r"\mathrm{silica}", blobs)

    def test_fenced_and_inline_code_ignored(self) -> None:
        md = (
            "```markdown\n"
            r"(M_{\mathrm{total}})"
            "\n```\n"
            r"反例是 `(M_{\mathrm{total}})`，正文用 \(M_{\mathrm{total}}\)。"
            "\n"
        )
        self.assertEqual(find_bare_paren_latex(md), [])

    def test_cli_exit_code(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "a.md"
            p.write_text(r"坏的 (M_{\mathrm{total}})", encoding="utf-8")
            self.assertEqual(delim_main(["-i", str(p)]), 1)
            p.write_text(r"好的 \(M_{\mathrm{total}}\)", encoding="utf-8")
            self.assertEqual(delim_main(["-i", str(p)]), 0)


class MermaidRenderSkipsDocxTests(unittest.TestCase):
    def test_bare_paren_skips_docx(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "draft.md"
            out = Path(tmp) / "out.md"
            src.write_text("# T\n\n" + r"(M_{\mathrm{total}})" + "\n", encoding="utf-8")
            with patch(
                "mermaid_render.render_markdown_mermaid",
                side_effect=lambda md, **k: (md, 0, 0),
            ), patch("mermaid_render.try_write_docx", return_value=True) as w:
                code = mermaid_main(["-i", str(src), "-o", str(out)])
            self.assertEqual(code, 0)
            w.assert_not_called()
            self.assertTrue(out.is_file())

    def test_correct_delim_still_calls_docx(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "draft.md"
            out = Path(tmp) / "out.md"
            src.write_text("# T\n\n" + r"\(M_{\mathrm{total}}\)" + "\n", encoding="utf-8")
            with patch(
                "mermaid_render.render_markdown_mermaid",
                side_effect=lambda md, **k: (md, 0, 0),
            ), patch("mermaid_render.try_write_docx", return_value=True) as w:
                code = mermaid_main(["-i", str(src), "-o", str(out)])
            self.assertEqual(code, 0)
            w.assert_called_once()


if __name__ == "__main__":
    unittest.main()
