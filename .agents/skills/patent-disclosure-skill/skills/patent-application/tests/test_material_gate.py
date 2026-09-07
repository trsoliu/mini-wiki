# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from material_gate import check_case


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class MaterialGateTests(unittest.TestCase):
    def test_empty_dir_missing_disclosure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = check_case(Path(td))
        self.assertFalse(result["ok"])
        self.assertIn("disclosure", result["missing"])

    def test_invention_disclosure_only(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            _write(
                case / "一种示例方法_20260101120000.md",
                "# 技术交底书\n\n**专利类型**：发明\n\n第三章方案。\n",
            )
            result = check_case(case)
        self.assertTrue(result["ok"])
        self.assertEqual(result["type"], "invention")
        self.assertEqual(result["missing"], [])

    def test_utility_missing_schema_and_plan(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            _write(
                case / "一种示例装置_20260101120000.md",
                "# 技术交底书\n\n**专利类型**：实用新型\n",
            )
            result = check_case(case)
        self.assertFalse(result["ok"])
        self.assertEqual(result["type"], "utility_model")
        self.assertIn("structure_schema", result["missing"])
        self.assertIn("figure_plan", result["missing"])

    def test_utility_complete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            _write(
                case / "一种示例装置_20260101120000.md",
                "# 技术交底书\n\n**专利类型**：实用新型\n",
            )
            _write(
                case / "structure_schema.yaml",
                "$schema: structure.schema\nversion: 1\nparts:\n  - id: '1'\n    name: 壳体\n",
            )
            _write(case / "figs" / "assembly.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>\n")
            _write(
                case / "figure_plan.yaml",
                "patent_type: utility_model\nfigures:\n"
                "  - fig: 1\n    kind: lineart\n    path: figs/assembly.svg\n"
                "    use_in_disclosure: true\n",
            )
            result = check_case(case)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["lineart"], 1)

    def test_design_needs_photo_and_lineart(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            _write(
                case / "一种灯具_20260101120000.md",
                "# 技术交底书\n\n**专利类型**：外观设计\n",
            )
            _write(
                case / "appearance_schema.yaml",
                "product_form: solid\nclaimed_faces: [主视]\n",
            )
            _write(case / "line.svg", "<svg xmlns='http://www.w3.org/2000/svg'/>\n")
            _write(
                case / "figure_plan.yaml",
                "patent_type: design\nfigures:\n"
                "  - fig: 1\n    kind: lineart\n    path: line.svg\n"
                "    use_in_disclosure: true\n",
            )
            result = check_case(case)
        self.assertFalse(result["ok"])
        self.assertIn("photo", result["missing"])
        self.assertNotIn("lineart", result["missing"])

    def test_type_hint_overrides_header(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            _write(
                case / "一种示例方法_20260101120000.md",
                "# 技术交底书\n\n**专利类型**：发明\n",
            )
            result = check_case(case, type_hint="utility_model")
        self.assertEqual(result["type"], "utility_model")
        self.assertIn("structure_schema", result["missing"])


if __name__ == "__main__":
    unittest.main()
