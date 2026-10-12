# -*- coding: utf-8 -*-
"""design_lineart_gate：默认开、无图可过、空 source_paths 允许文生图。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from design_lineart_gate import (
    build_jobs,
    parse_enabled,
    run_check,
    validate_brief,
)


class TestDesignLineartGate(unittest.TestCase):
    def test_default_on(self):
        self.assertTrue(parse_enabled(False))
        self.assertTrue(parse_enabled(True))
        self.assertFalse(parse_enabled(False, skip=True))

    def test_skip_env(self):
        with mock.patch.dict(os.environ, {"PATENT_SKILL_SKIP_LINEART": "1"}):
            self.assertFalse(parse_enabled(False))

    def test_check_disabled(self):
        with tempfile.TemporaryDirectory() as td:
            report = run_check(Path(td), enabled=False)
            self.assertFalse(report["ok"])
            self.assertTrue(any("跳过" in e for e in report["errors"]))

    def test_empty_source_paths_ok(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            brief = {
                "enabled": True,
                "patent_type": "design",
                "overall_shape": "折臂台灯",
                "design_points": ["弯月灯头"],
                "views": [
                    {
                        "view_name": "立体图",
                        "source_paths": [],
                        "lineart_goal": "整体轮廓",
                    }
                ],
            }
            self.assertEqual(validate_brief(brief, case), [])
            jobs = build_jobs(brief, case)
            self.assertEqual(len(jobs), 1)
            self.assertFalse(jobs[0]["forbid_text_only"])
            self.assertEqual(jobs[0]["source_paths"], [])

            (case / "design_lineart_brief.yaml").write_text(
                json.dumps(brief, ensure_ascii=False),
                encoding="utf-8",
            )
            (case / "figure_plan.yaml").write_text(
                "patent_type: design\nfigures: []\n",
                encoding="utf-8",
            )
            report = run_check(case, enabled=True)
            self.assertTrue(report["ok"], report)

    def test_validate_and_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = case / "p.jpg"
            img.write_bytes(b"\xff\xd8\xff\xd9")
            brief = {
                "enabled": True,
                "patent_type": "design",
                "overall_shape": "折臂台灯",
                "design_points": ["弯月灯头"],
                "views": [
                    {
                        "view_name": "立体图",
                        "source_paths": [str(img)],
                        "source_figs": [1],
                        "relates_hint": [{"fig": 1, "relation": "same_state"}],
                        "lineart_goal": "整体轮廓",
                        "gen_prompt": "",
                        "output_path": "lineart_assist/stereo_lineart.png",
                    }
                ],
            }
            self.assertEqual(validate_brief(brief, case), [])
            jobs = build_jobs(brief, case)
            self.assertEqual(len(jobs), 1)
            self.assertFalse(jobs[0]["forbid_text_only"])
            self.assertEqual(jobs[0]["reference_images"], [str(img.resolve())])
            self.assertEqual(jobs[0]["source_paths"], jobs[0]["reference_images"])
            self.assertIn("line art", jobs[0]["gen_prompt"].lower())

            try:
                import yaml  # type: ignore

                (case / "design_lineart_brief.yaml").write_text(
                    yaml.safe_dump(brief, allow_unicode=True),
                    encoding="utf-8",
                )
            except Exception:
                (case / "design_lineart_brief.yaml").write_text(
                    json.dumps(brief, ensure_ascii=False),
                    encoding="utf-8",
                )
            (case / "figure_plan.yaml").write_text(
                f"patent_type: design\nfigures:\n  - fig: 1\n    path: {img.name}\n    use_in_disclosure: true\n",
                encoding="utf-8",
            )
            report = run_check(case, enabled=True)
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()
