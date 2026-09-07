"""公式范式加载与 formula_plan 校验。"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from check_formula_plan import check_plan
from formula_paradigms import load_paradigms, paradigm_by_id


class FormulaParadigmsTests(unittest.TestCase):
    def test_default_library_rich(self):
        cfg = load_paradigms()
        self.assertGreaterEqual(len(cfg["paradigms"]), 15)
        self.assertTrue(paradigm_by_id(cfg, "weighted_sum"))
        self.assertTrue(paradigm_by_id(cfg, "dual_threshold"))
        self.assertTrue(paradigm_by_id(cfg, "stoichiometric_reaction"))
        self.assertTrue(cfg.get("combos"))

    def test_case_override_merges(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "formula_paradigms.yaml"
            p.write_text(
                "version: 1\nparadigms:\n"
                "  - id: my_custom\n    name_zh: 自定义\n"
                "    when_zh: 测试\n    latex: 's = x'\n    notes_zh: ''\n",
                encoding="utf-8",
            )
            cfg = load_paradigms(td)
            self.assertTrue(paradigm_by_id(cfg, "weighted_sum"))
            self.assertTrue(paradigm_by_id(cfg, "my_custom"))

    def test_check_plan_ok_and_forbid_tilde(self):
        plan_ok = {
            "paradigm_ids": ["weighted_sum", "dual_threshold"],
            "plain_zh": "匹配分加权后按双条件触发",
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "weighted_sum",
                    "latex": r"s = \alpha x + \beta y",
                    "role": "score",
                }
            ],
            "numeric_example": {"given": {"x": 1, "y": 1}, "result": {"s": 1}},
        }
        r = check_plan(plan_ok)
        self.assertTrue(r["ok"], r)

        plan_bad = {
            "paradigm_ids": ["weighted_sum"],
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "weighted_sum",
                    "latex": r"s = \tilde{a}",
                    "role": "score",
                }
            ],
            "numeric_example": {"given": {"a": 1}, "result": {"s": 1}},
        }
        r2 = check_plan(plan_bad)
        self.assertFalse(r2["ok"])
        self.assertTrue(any("tilde" in e for e in r2["errors"]))

    def test_source_plan_without_paradigm_ok(self) -> None:
        plan = {
            "plain_zh": "材料主式：状态转移",
            "equations": [
                {
                    "tag": 1,
                    "origin": "source",
                    "source_ref": "设计说明 式(3)",
                    "latex": r"x_{t+1} = A x_t + B u_t",
                    "role": "other",
                }
            ],
            "omitted": [
                {"ref": "论文 式(8)", "reason": "对照实验"},
            ],
        }
        r = check_plan(plan)
        self.assertTrue(r["ok"], r)
        self.assertFalse(any("paradigm_ids 为空" in e for e in r["errors"]))

    def test_source_accent_is_warning_not_error(self) -> None:
        plan = {
            "equations": [
                {
                    "tag": 1,
                    "origin": "source",
                    "source_ref": "原文 式(1)",
                    "latex": r"s = \tilde{a}",
                }
            ],
        }
        r = check_plan(plan)
        self.assertTrue(r["ok"], r)
        self.assertTrue(any("tilde" in w for w in r["warnings"]))

    def test_agent_still_requires_paradigm(self) -> None:
        plan = {
            "plain_zh": "补写打分",
            "equations": [
                {
                    "tag": 1,
                    "origin": "agent",
                    "latex": r"s = x + y",
                    "role": "score",
                }
            ],
            "numeric_example": {"given": {"x": 1, "y": 1}, "result": {"s": 2}},
        }
        r = check_plan(plan)
        self.assertFalse(r["ok"])
        self.assertTrue(any("agent" in e for e in r["errors"]))


if __name__ == "__main__":
    unittest.main()
