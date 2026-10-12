# -*- coding: utf-8 -*-
"""pdf_to_md：缺文件、按页插图、空 PDF 退出码。无 pymupdf 则跳过转换用例。"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
sys.path.insert(0, str(SHARED))

from pdf_to_md import _run

# 1x1 RGBA PNG
_MINI_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _have_fitz() -> bool:
    try:
        import fitz  # noqa: F401

        return True
    except ImportError:
        return False


class PdfToMdTests(unittest.TestCase):
    def test_missing_file_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = _run(Path(tmp) / "nope.pdf", Path(tmp) / "out.md", None)
        self.assertEqual(code, 2)

    def test_text_and_image_stay_on_page(self) -> None:
        if not _have_fitz():
            self.skipTest("pymupdf not installed")
        import fitz

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "demo.pdf"
            out = Path(tmp) / "demo.md"
            doc = fitz.open()
            p1 = doc.new_page()
            p1.insert_textbox(
                fitz.Rect(72, 72, 520, 200),
                "page-one-device cooling jacket with dual-cavity annular flow ring "
                "and spraying seal used in the winding end region.",
            )
            p1.insert_image(fitz.Rect(72, 100, 120, 148), stream=_MINI_PNG)
            p2 = doc.new_page()
            p2.insert_text((72, 72), "page-two-method")
            doc.save(src)
            doc.close()

            code = _run(src, out, None)
            self.assertEqual(code, 0)
            md = out.read_text(encoding="utf-8")
            i1 = md.find("## 第 1 页")
            i2 = md.find("## 第 2 页")
            img = md.find("![")
            self.assertNotEqual(i1, -1)
            self.assertNotEqual(i2, -1)
            self.assertNotEqual(img, -1)
            self.assertLess(i1, img)
            self.assertLess(img, i2)
            self.assertIn("page-one-device", md)
            self.assertIn("page-two-method", md)
            self.assertTrue((Path(tmp) / "demo_media").is_dir())
            self.assertTrue(any((Path(tmp) / "demo_media").iterdir()))

    def test_empty_pdf_returns_4(self) -> None:
        if not _have_fitz():
            self.skipTest("pymupdf not installed")
        import fitz

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "blank.pdf"
            out = Path(tmp) / "blank.md"
            doc = fitz.open()
            doc.new_page()
            doc.save(src)
            doc.close()
            buf = io.StringIO()
            old = sys.stderr
            sys.stderr = buf
            try:
                code = _run(src, out, None)
            finally:
                sys.stderr = old
            self.assertEqual(code, 4)
            self.assertFalse(out.exists())
            self.assertIn("未抽出", buf.getvalue())

    def test_short_text_warns_but_succeeds(self) -> None:
        if not _have_fitz():
            self.skipTest("pymupdf not installed")
        import fitz

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "tiny.pdf"
            out = Path(tmp) / "tiny.md"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "ab")
            doc.save(src)
            doc.close()
            buf = io.StringIO()
            old = sys.stderr
            sys.stderr = buf
            try:
                code = _run(src, out, None)
            finally:
                sys.stderr = old
            self.assertEqual(code, 0)
            self.assertTrue(out.is_file())
            self.assertIn("扫描件", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
