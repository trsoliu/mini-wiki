# -*- coding: utf-8 -*-
"""外观检查脚本与视图口径须与交底包保持同文。"""
from __future__ import annotations

import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
DISCLOSURE = Path(__file__).resolve().parents[2] / "patent-disclosure"

PAIRS = (
    ("tools/check_design_views.py", "tools/check_design_views.py"),
    ("references/design_view_cnipa.md", "references/design_view_cnipa.md"),
)


class DesignViewSyncTests(unittest.TestCase):
    def test_copied_files_match_disclosure(self) -> None:
        for rel_app, rel_src in PAIRS:
            src = DISCLOSURE / rel_src
            dst = APP / rel_app
            self.assertTrue(src.is_file(), f"缺少交底 {rel_src}")
            self.assertTrue(dst.is_file(), f"缺少本包副本 {rel_app}")
            self.assertEqual(
                src.read_bytes(),
                dst.read_bytes(),
                f"{rel_app} 与交底包不一致，请拷贝覆盖",
            )


if __name__ == "__main__":
    unittest.main()
