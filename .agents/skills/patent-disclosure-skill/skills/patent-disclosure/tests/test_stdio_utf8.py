# -*- coding: utf-8 -*-
"""stdio UTF-8 与子进程解码。"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

import stdio_utf8
from md_to_docx import MathOutcomeStats


class StdioUtf8Tests(unittest.TestCase):
    def test_ensure_utf8_stdio_sets_env(self) -> None:
        stdio_utf8.ensure_utf8_stdio()
        self.assertEqual(stdio_utf8.os.environ.get("PYTHONUTF8"), "1")
        self.assertEqual(stdio_utf8.os.environ.get("PYTHONIOENCODING"), "utf-8")

    def test_run_roundtrip_cjk(self) -> None:
        r = stdio_utf8.run(
            [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('公式\\n'); sys.stdout.write('ok\\n')",
            ],
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("ok", r.stdout)
        self.assertIn("公式", r.stderr)

    def test_math_report_ascii_markers(self) -> None:
        st = MathOutcomeStats()
        st.omml = 2
        st.text = 1
        st.text_latex.append(r"\min(1,x)")
        buf = io.StringIO()
        with patch("md_to_docx.sys.stderr", buf):
            st.report()
        out = buf.getvalue()
        self.assertIn("MATH: omml=2 png=0 text=1", out)
        self.assertIn("OMML_FAIL: \\min(1,x)", out)
        self.assertIn("omml_text_fallback=1", out)


if __name__ == "__main__":
    unittest.main()
