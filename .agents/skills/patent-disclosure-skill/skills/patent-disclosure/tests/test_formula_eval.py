"""公式受限代算、化学守恒、量纲粗检。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from check_formula_plan import check_plan
from formula_chem import check_chemistry, parse_formula_atoms, parse_reaction
from formula_eval import eval_equation
from formula_units import check_additive_units, check_score_weights


class FormulaEvalTests(unittest.TestCase):
    def test_weighted_sum_ok(self) -> None:
        r = eval_equation(
            r"s = \alpha x + \beta y",
            {"alpha": 0.5, "x": 0.8, "beta": 0.5, "y": 0.6},
            {"s": 0.7},
        )
        self.assertEqual(r["status"], "ok", r)

    def test_mismatch(self) -> None:
        r = eval_equation(
            r"s = \alpha x + \beta y",
            {"\\alpha": 0.5, "x": 1, "\\beta": 0.5, "y": 1},
            {"s": 0.1},
        )
        self.assertEqual(r["status"], "mismatch", r)

    def test_min_max_frac(self) -> None:
        r = eval_equation(
            r"s = \min\big(1,\, a / \max(\varepsilon, b)\big)",
            {"a": 2, "b": 1, "varepsilon": 0.01},
            {"s": 1},
        )
        self.assertEqual(r["status"], "ok", r)

    def test_skip_sum(self) -> None:
        r = eval_equation(
            r"\sigma = \frac{1}{W} \sum_{k=1}^{W} s_{(k)}",
            {"W": 3},
            {"sigma": 1},
        )
        self.assertEqual(r["status"], "skip", r)

    def test_skip_unbound(self) -> None:
        r = eval_equation(
            r"s = \alpha x + \beta y",
            {"x": 1, "y": 1},
            {"s": 1},
        )
        self.assertEqual(r["status"], "skip", r)
        self.assertIn("未绑定", r.get("reason") or "")


class FormulaChemTests(unittest.TestCase):
    def test_water_atoms(self) -> None:
        c, err = parse_formula_atoms("H2O")
        self.assertEqual(err, [])
        self.assertEqual(c["H"], 2)
        self.assertEqual(c["O"], 1)

    def test_balanced_reaction(self) -> None:
        left, right, err = parse_reaction(r"\ce{2H2 + O2 -> 2H2O}")
        self.assertEqual(err, [])
        self.assertEqual(left, right)

    def test_unbalanced(self) -> None:
        r = check_chemistry(
            [{"latex": r"\ce{H2 + O2 -> H2O}"}],
            force=True,
        )
        self.assertTrue(r["errors"])

    def test_mass_frac_warn(self) -> None:
        r = check_chemistry([], given={"w1": 0.3, "w2": 0.3}, force=True)
        self.assertTrue(any("质量分数" in w for w in r["warnings"]))


class FormulaUnitsTests(unittest.TestCase):
    def test_mixed_units_warn(self) -> None:
        w = check_additive_units(
            [{"latex": r"y = a + b"}],
            [
                {"symbol": "a", "unit_zh": "kg"},
                {"symbol": "b", "unit_zh": "s"},
            ],
        )
        self.assertTrue(w)

    def test_weight_sum_warn(self) -> None:
        w = check_score_weights(
            ["weighted_sum"],
            {"alpha": 0.8, "beta": 0.8},
        )
        self.assertTrue(w)


class CheckPlanEvalTests(unittest.TestCase):
    def test_eval_catches_bad_numeric(self) -> None:
        plan = {
            "paradigm_ids": ["weighted_sum"],
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "weighted_sum",
                    "latex": r"s = \alpha x + \beta y",
                    "role": "score",
                }
            ],
            "numeric_example": {
                "given": {"alpha": 0.5, "x": 1, "beta": 0.5, "y": 1},
                "result": {"s": 0.1},
            },
        }
        r0 = check_plan(plan)
        self.assertTrue(r0["ok"], r0)
        r1 = check_plan(plan, eval_numeric=True)
        self.assertFalse(r1["ok"], r1)

    def test_eval_ok(self) -> None:
        plan = {
            "paradigm_ids": ["weighted_sum"],
            "plain_zh": "加权和",
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "weighted_sum",
                    "latex": r"s = \alpha x + \beta y",
                    "role": "score",
                }
            ],
            "numeric_example": {
                "given": {"alpha": 0.5, "x": 0.8, "beta": 0.5, "y": 0.6},
                "result": {"s": 0.7},
            },
        }
        r = check_plan(plan, eval_numeric=True)
        self.assertTrue(r["ok"], r)

    def test_chem_unbalanced_errors(self) -> None:
        plan = {
            "paradigm_ids": ["stoichiometric_reaction"],
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "stoichiometric_reaction",
                    "latex": r"\ce{H2 + O2 -> H2O}",
                    "role": "other",
                }
            ],
            "numeric_example": {"given": {"dummy": 1}, "result": {"dummy": 1}},
        }
        r = check_plan(plan)
        self.assertFalse(r["ok"], r)

    def test_chem_balanced_ok(self) -> None:
        plan = {
            "paradigm_ids": ["stoichiometric_reaction"],
            "equations": [
                {
                    "tag": 1,
                    "paradigm_id": "stoichiometric_reaction",
                    "latex": r"\ce{2H2 + O2 -> 2H2O}",
                    "role": "other",
                }
            ],
            "numeric_example": {"given": {"dummy": 1}, "result": {"dummy": 1}},
        }
        r = check_plan(plan)
        self.assertTrue(r["ok"], r)


if __name__ == "__main__":
    unittest.main()
