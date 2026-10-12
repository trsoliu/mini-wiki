# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from check_source_parts import check_source_parts


class SourcePartsTests(unittest.TestCase):
    def test_hallucinated_cover_and_mark(self) -> None:
        structure = {
            "parts": [{"id": "1", "name": "壳体"}],
            "uncertain": ["齿数"],
            "source_images": ["a.png"],
        }
        plan = {"figures": [{"fig": 1, "covers": ["1", "9"], "path": "a.png"}]}
        text = "三、壳体（1）。五、保护齿数与垫片（8）。"
        findings = check_source_parts(Path("."), structure=structure, plan=plan, disclosure_text=text)
        codes = {item.code for item in findings}
        self.assertIn("HALLUCINATED_COVER", codes)
        self.assertIn("HALLUCINATED_MARK", codes)
        self.assertIn("UNCERTAIN_IN_PROTECT", codes)

    def test_uncertain_as_part(self) -> None:
        structure = {
            "parts": [{"id": "2", "name": "卡扣"}],
            "uncertain": ["2"],
            "source_images": [],
        }
        findings = check_source_parts(Path("."), structure=structure, plan={"figures": []}, disclosure_text="")
        codes = {item.code for item in findings}
        self.assertIn("UNCERTAIN_AS_PART", codes)
        self.assertIn("PART_WITHOUT_SOURCE", codes)

    def test_aligned_parts_pass(self) -> None:
        structure = {
            "parts": [{"id": "1", "name": "壳体"}],
            "uncertain": [],
            "source_images": ["a.png"],
        }
        plan = {"figures": [{"fig": 1, "covers": ["1"], "path": "a.png"}]}
        findings = check_source_parts(
            Path("."),
            structure=structure,
            plan=plan,
            disclosure_text="三、包括壳体（1）。五、一种装置，包括壳体（1）。",
        )
        self.assertEqual([item for item in findings if item.level == "ERROR"], [])


if __name__ == "__main__":
    unittest.main()
