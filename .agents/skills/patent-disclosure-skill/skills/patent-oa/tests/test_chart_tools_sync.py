# -*- coding: utf-8 -*-
"""对照导出脚本是对照包副本，必须保持一致。"""
from __future__ import annotations

import unittest
from pathlib import Path

OA_TOOLS = Path(__file__).resolve().parents[1] / "tools"
CHART_TOOLS = Path(__file__).resolve().parents[2] / "patent-chart" / "tools"
COPIED = ("emit_chart.py", "highlights.py", "xlsx_minimal.py", "write_intake.py")


class ChartToolsSyncTests(unittest.TestCase):
    def test_copied_files_match_chart_package(self) -> None:
        for name in COPIED:
            src = CHART_TOOLS / name
            dst = OA_TOOLS / name
            self.assertTrue(src.is_file(), f"缺少对照包 {name}")
            self.assertTrue(dst.is_file(), f"缺少本包副本 {name}")
            self.assertEqual(
                src.read_bytes(),
                dst.read_bytes(),
                f"{name} 与 skills/patent-chart/tools/ 不一致，请拷贝覆盖",
            )


if __name__ == "__main__":
    unittest.main()
