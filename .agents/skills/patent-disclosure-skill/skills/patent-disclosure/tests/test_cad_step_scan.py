# -*- coding: utf-8 -*-
"""cad_formats / cad_scan / figure_plan seed（无 CadQuery）。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from cad_formats import (
    classify_path,
    is_native_cad,
    is_step,
    iter_classified,
    recommend_action,
)
from cad_scan import build_report
from step_to_views import build_figure_plan_seed, parse_enabled


class TestCadFormats(unittest.TestCase):
    def test_step_suffixes(self):
        self.assertTrue(is_step("a.STEP"))
        self.assertTrue(is_step("b.stp"))
        self.assertEqual(classify_path("x.sldasm"), "native_cad")
        self.assertTrue(is_native_cad("part.ipt"))
        self.assertEqual(classify_path("a.iges"), "iges")
        self.assertIsNone(classify_path("readme.md"))

    def test_recommend(self):
        self.assertEqual(recommend_action(["a.step"], ["b.sldprt"]), "ask_enable_step_parse")
        self.assertEqual(recommend_action([], ["b.sldprt"]), "hint_export_step")
        self.assertEqual(recommend_action([], [], ["c.igs"]), "hint_export_step")
        self.assertEqual(recommend_action([], []), "none")


class TestCadScan(unittest.TestCase):
    def test_scan_temp(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "m.stp").write_text("ISO-10303-21;", encoding="utf-8")
            (root / "sub").mkdir()
            (root / "sub" / "a.sldprt").write_bytes(b"x")
            (root / "note.md").write_text("hi", encoding="utf-8")
            report = build_report([str(root)])
            self.assertEqual(report["action"], "ask_enable_step_parse")
            self.assertEqual(len(report["step_files"]), 1)
            self.assertEqual(len(report["native_cad_files"]), 1)
            self.assertIn("ask_enable_step_parse", report["messages"])
            self.assertTrue(report["messages"]["ask_enable_step_parse"])

    def test_hint_only_native(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "asm.sldasm").write_bytes(b"x")
            report = build_report([str(root)])
            self.assertEqual(report["action"], "hint_export_step")
            self.assertTrue(report["messages"]["hint_export_step"])


class TestFigurePlanSeed(unittest.TestCase):
    def test_relates_to_alternate(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "figure_plan.seed.yaml"
            views = [
                {"name": "iso", "role": "assembly", "png": str(Path(td) / "iso.png")},
                {"name": "front", "role": "ortho", "png": str(Path(td) / "front.png")},
                {"name": "top", "role": "ortho", "png": str(Path(td) / "top.png")},
            ]
            plan = build_figure_plan_seed(
                view_records=views,
                out_path=out,
                theme_summary="test",
            )
            self.assertEqual(plan["figures"][0]["role"], "reference")
            self.assertEqual(plan["figures"][0]["kind"], "cad")
            self.assertFalse(plan["figures"][0]["use_in_disclosure"])
            self.assertIsNone(plan["figures"][0]["fig"])
            self.assertEqual(plan["figures"][0]["relates_to"], [])
            self.assertTrue(all(not f["use_in_disclosure"] for f in plan["figures"]))
            self.assertTrue(out.is_file())

    def test_parse_enabled_default_off(self):
        self.assertFalse(parse_enabled(False))
        self.assertTrue(parse_enabled(True))


class TestIterClassified(unittest.TestCase):
    def test_file_root(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "x.dwg"
            f.write_bytes(b"0")
            got = iter_classified([f])
            self.assertEqual(got["native_cad"], [str(f.resolve())])


class TestDemoStepInExample(unittest.TestCase):
    def test_example_step_triggers_ask(self):
        demo = (
            SHARED_PKG
            / "tests"
            / "fixtures"
            / "cad"
            / "demo_snap_plate.step"
        )
        self.assertTrue(demo.is_file(), "missing demo STEP; run gen_demo_snap_step.py")
        self.assertIn("ISO-10303-21", demo.read_text(encoding="utf-8")[:80])
        report = build_report([str(demo.parent)])
        self.assertEqual(report["action"], "ask_enable_step_parse")
        self.assertTrue(any(p.endswith("demo_snap_plate.step") for p in report["step_files"]))


if __name__ == "__main__":
    unittest.main()
