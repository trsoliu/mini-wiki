# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_design_views import FAIL, WAIT, audit_design_views, main


def _ok_schema(**extra):
    data = {
        "product_form": "solid",
        "claimed_faces": ["主视图", "左视图"],
        "omitted_views": [{"name": "后视图", "reason": "与主视图对称"}],
        "line_scope": {
            "claimed": ["灯罩", "折臂"],
            "unclaimed": ["电源线"],
            "by_view": [
                {"name": "主视图", "claimed": ["灯罩", "折臂"], "unclaimed": ["电源线"]},
                {"name": "左视图", "claimed": ["灯罩", "折臂"], "unclaimed": ["电源线"]},
            ],
        },
        "uncertain": [],
    }
    data.update(extra)
    return data


def _plan(*covers_list):
    figures = []
    for i, covers in enumerate(covers_list, start=1):
        figures.append(
            {
                "fig": i,
                "path": f"assets/v{i}.png",
                "covers": covers,
                "kind": "lineart",
                "use_in_disclosure": True,
            }
        )
    return {"patent_type": "design", "figures": figures}


class CheckDesignViewsTests(unittest.TestCase):
    def test_missing_face_and_omitted_conflict(self) -> None:
        rows = audit_design_views(_ok_schema(), _plan(["主视图"]))
        leak = [r for r in rows if r["kind"] == "漏视"]
        self.assertTrue(any(r["item"] == "左视图" and r["verdict"] == FAIL for r in leak))
        self.assertTrue(any(r["item"] == "主视图" and r["verdict"] == "通过" for r in leak))

    def test_dashed_mismatch_across_views(self) -> None:
        schema = _ok_schema()
        schema["line_scope"]["by_view"][1]["unclaimed"] = []
        schema["line_scope"]["by_view"][1]["claimed"] = ["灯罩", "折臂", "电源线"]
        rows = audit_design_views(schema, _plan(["主视图"], ["左视图"]))
        dashed = [r for r in rows if r["kind"] == "虚线不一致" and r["verdict"] == FAIL]
        self.assertTrue(dashed)

    def test_new_matter_omitted_face_in_figures(self) -> None:
        rows = audit_design_views(_ok_schema(), _plan(["主视图"], ["后视图"]))
        matter = [r for r in rows if r["kind"] == "新事项风险" and r["verdict"] == FAIL]
        self.assertTrue(any("后视图" in r["item"] for r in matter))

    def test_unlocked_scope_is_wait(self) -> None:
        schema = _ok_schema()
        schema["line_scope"] = {}
        rows = audit_design_views(schema, _plan(["主视图"], ["左视图"]))
        self.assertTrue(any(r["kind"] == "虚线不一致" and r["verdict"] == WAIT for r in rows))

    def test_writes_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "appearance_schema.json").write_text(
                json.dumps(_ok_schema(), ensure_ascii=False), encoding="utf-8"
            )
            (root / "figure_plan.json").write_text(
                json.dumps(_plan(["主视图"], ["左视图"]), ensure_ascii=False), encoding="utf-8"
            )
            self.assertEqual(main(["--case-dir", str(root)]), 0)
            text = (root / "视图检查清单.md").read_text(encoding="utf-8")
            self.assertIn("漏视", text)
            self.assertIn("不改原图像素", text)
            self.assertNotIn("应当授权", text)


if __name__ == "__main__":
    unittest.main()
