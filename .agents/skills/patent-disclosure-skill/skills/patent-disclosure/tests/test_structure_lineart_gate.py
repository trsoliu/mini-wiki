# -*- coding: utf-8 -*-
"""structure_lineart_gate：默认开、无图可过、件号仍须对齐 Structure。"""
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

from structure_lineart_gate import (
    build_jobs,
    parse_enabled,
    run_check,
    validate_brief,
)


class TestStructureLineartGate(unittest.TestCase):
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
            structure = {
                "parts": [{"id": "1", "name": "基板"}],
                "relations": [],
                "uncertain": [],
            }
            brief = {
                "enabled": True,
                "patent_type": "utility_model",
                "structure_summary": "集成式电驱桥壳体",
                "callout_mode": "overlay",
                "parts_legend": [{"id": "1", "name": "基板"}],
                "views": [
                    {
                        "view_name": "总装",
                        "source_paths": [],
                        "visible_part_ids": ["1"],
                    }
                ],
            }
            self.assertEqual(validate_brief(brief, case, structure=structure), [])
            jobs = build_jobs(brief, case)
            self.assertEqual(len(jobs), 1)
            self.assertFalse(jobs[0]["forbid_text_only"])
            self.assertEqual(jobs[0]["source_paths"], [])

    def test_validate_and_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = case / "p.jpg"
            img.write_bytes(b"\xff\xd8\xff\xd9")
            structure = {
                "parts": [
                    {"id": "1", "name": "基板"},
                    {"id": "2", "name": "卡扣"},
                ],
                "relations": [],
                "uncertain": [],
            }
            brief = {
                "enabled": True,
                "patent_type": "utility_model",
                "structure_summary": "集成式电驱桥壳体",
                "callout_mode": "overlay",
                "parts_legend": [
                    {"id": "1", "name": "基板"},
                    {"id": "2", "name": "卡扣"},
                ],
                "views": [
                    {
                        "view_name": "总装",
                        "source_paths": [str(img)],
                        "source_figs": [1],
                        "visible_part_ids": ["1", "2"],
                        "lineart_goal": "总装轮廓",
                        "gen_prompt": "",
                        "output_path": "lineart_assist/assy_lineart.png",
                    }
                ],
            }
            self.assertEqual(validate_brief(brief, case, structure=structure), [])
            jobs = build_jobs(brief, case)
            self.assertEqual(len(jobs), 1)
            self.assertFalse(jobs[0]["forbid_text_only"])
            self.assertEqual(jobs[0]["callout_mode"], "overlay")
            self.assertEqual([c["id"] for c in jobs[0]["callouts"]], ["1", "2"])
            self.assertEqual(jobs[0]["callout_anchor_manifest"], "structure_callout_anchors.yaml")
            self.assertIn("structure_callout_overlay.py", jobs[0]["callout_overlay_tool"])
            self.assertIn("Do NOT draw part numbers", jobs[0]["gen_prompt"])

            try:
                import yaml  # type: ignore

                (case / "structure_lineart_brief.yaml").write_text(
                    yaml.safe_dump(brief, allow_unicode=True),
                    encoding="utf-8",
                )
                (case / "structure_schema.yaml").write_text(
                    yaml.safe_dump(structure, allow_unicode=True),
                    encoding="utf-8",
                )
            except Exception:
                (case / "structure_lineart_brief.yaml").write_text(
                    json.dumps(brief, ensure_ascii=False),
                    encoding="utf-8",
                )
                (case / "structure_schema.yaml").write_text(
                    json.dumps(structure, ensure_ascii=False),
                    encoding="utf-8",
                )
            (case / "figure_plan.yaml").write_text(
                f"patent_type: utility_model\nfigures:\n  - fig: 1\n    path: {img.name}\n    use_in_disclosure: true\n",
                encoding="utf-8",
            )
            report = run_check(case, enabled=True)
            self.assertTrue(report["ok"], report)

    def test_bad_part_id_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = case / "p.jpg"
            img.write_bytes(b"\xff\xd8\xff\xd9")
            structure = {"parts": [{"id": "1", "name": "基板"}], "relations": [], "uncertain": []}
            brief = {
                "enabled": True,
                "patent_type": "utility_model",
                "structure_summary": "x",
                "callout_mode": "overlay",
                "parts_legend": [{"id": "1", "name": "基板"}],
                "views": [
                    {
                        "view_name": "总装",
                        "source_paths": [str(img)],
                        "visible_part_ids": ["1", "99"],
                    }
                ],
            }
            errs = validate_brief(brief, case, structure=structure)
            self.assertTrue(any("99" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
