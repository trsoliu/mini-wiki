# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

from docket_paths import normalize_case_id
from docket_spec import can_transit
from init_docket import empty_docket, main as init_main
from validate_docket import main as validate_main, validate_docket
from emit_tracker import render_tracker


class CaseIdTests(unittest.TestCase):
    def test_rejects_spaces_only(self) -> None:
        with self.assertRaises(ValueError):
            normalize_case_id("好 案")


class PhaseGraphTests(unittest.TestCase):
    def test_from_zero_path(self) -> None:
        self.assertTrue(can_transit("bootstrap_disclosure", "wait_disclosure"))
        self.assertTrue(can_transit("wait_disclosure", "bootstrap_application"))
        self.assertTrue(can_transit("wait_application", "triage"))
        self.assertFalse(can_transit("bootstrap_disclosure", "bootstrap_application"))

    def test_disclosure_fix_must_go_to_application(self) -> None:
        self.assertTrue(can_transit("wait_disclosure_fix", "dispatch_application"))
        self.assertFalse(can_transit("wait_disclosure_fix", "round_close"))
        self.assertFalse(can_transit("terminal_complete", "triage"))


class ValidateTests(unittest.TestCase):
    def test_empty_from_zero_ok(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_zero",
            patent_type="invention",
            max_rounds=3,
        )
        self.assertEqual(validate_docket(doc), [])
        self.assertEqual(doc["phase"], "bootstrap_disclosure")

    def test_cannot_apply_without_disclosure_from_zero(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_zero",
            patent_type="invention",
            max_rounds=3,
        )
        doc["phase"] = "bootstrap_application"
        errs = validate_docket(doc)
        self.assertTrue(any("交底" in e for e in errs))

    def test_blocking_forbids_dispatch(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_application",
            patent_type="invention",
            max_rounds=3,
            application_dir="outputs/patent-application/x",
        )
        doc["phase"] = "dispatch_disclosure"
        doc["issues"] = [
            {
                "id": "I-01",
                "summary": "用户已要求砍独权，尚未说明新范围",
                "kind": "scope_strategy",
                "disposition": "ask_human",
                "status": "open",
                "blocking": True,
                "round_opened": 1,
            }
        ]
        errs = validate_docket(doc)
        self.assertTrue(any("阻塞" in e for e in errs))

    def test_inventor_unfilled_nonblocking_allows_dispatch(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_application",
            patent_type="invention",
            max_rounds=3,
            application_dir="outputs/patent-application/x",
            disclosure_dir="outputs/x",
        )
        doc["phase"] = "dispatch_application"
        doc["issues"] = [
            {
                "id": "I-01",
                "summary": "发明人未填",
                "kind": "human_fact",
                "disposition": "ask_human",
                "status": "open",
                "blocking": False,
                "round_opened": 1,
            }
        ]
        self.assertEqual(validate_docket(doc), [])

    def test_max_rounds_cap(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_zero",
            patent_type="invention",
            max_rounds=9,
        )
        errs = validate_docket(doc, cfg={"max_rounds": 3})
        self.assertTrue(any("上限" in e for e in errs))

    def test_complete_with_open_todo_fails(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_application",
            patent_type="invention",
            max_rounds=3,
            application_dir="outputs/x",
        )
        doc["phase"] = "terminal_complete"
        doc["issues"] = [
            {
                "id": "I-02",
                "summary": "缺连接关系",
                "kind": "disclosure_gap",
                "disposition": "disclosure_fix",
                "status": "open",
                "blocking": False,
                "round_opened": 1,
            }
        ]
        errs = validate_docket(doc)
        self.assertTrue(any("terminal_complete" in e for e in errs))


class InitAndEmitTests(unittest.TestCase):
    def test_init_and_tracker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            import os

            old = os.environ.get("PATENT_DOCKET_OUTPUT_DIR")
            os.environ["PATENT_DOCKET_OUTPUT_DIR"] = tmp
            try:
                self.assertEqual(
                    init_main(["--case-id", "demo-case", "--mode", "from_zero"]),
                    0,
                )
                yaml_path = Path(tmp) / "demo-case" / "docket.yaml"
                self.assertTrue(yaml_path.is_file())
                self.assertEqual(validate_main(["--yaml", str(yaml_path)]), 0)
                from emit_tracker import main as emit_main

                self.assertEqual(emit_main(["--yaml", str(yaml_path)]), 0)
                tracker = yaml_path.with_name("TRACKER.md")
                text = tracker.read_text(encoding="utf-8")
                self.assertIn("从零开写", text)
                self.assertIn("调度交底初稿", text)
            finally:
                if old is None:
                    os.environ.pop("PATENT_DOCKET_OUTPUT_DIR", None)
                else:
                    os.environ["PATENT_DOCKET_OUTPUT_DIR"] = old

    def test_render_includes_issues(self) -> None:
        doc = empty_docket(
            case_id="demo-case",
            start_mode="from_application",
            patent_type="utility_model",
            max_rounds=3,
            application_dir="outputs/patent-application/demo",
            issues_md="outputs/patent-application/demo/问题清单.md",
        )
        doc["phase"] = "triage"
        doc["issues"] = [
            {
                "id": "I-01",
                "summary": "摘要超 300 字",
                "kind": "machine_format",
                "disposition": "application_fix",
                "status": "open",
                "blocking": False,
                "round_opened": 1,
            }
        ]
        text = render_tracker(doc)
        self.assertIn("I-01", text)
        self.assertIn("实用新型", text)


if __name__ == "__main__":
    unittest.main()
