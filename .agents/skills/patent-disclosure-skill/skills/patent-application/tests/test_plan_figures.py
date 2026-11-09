# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from plan_figures import build_plan, suggest_figures, validate_plan


class PlanFiguresTests(unittest.TestCase):
    def test_method_claim_gets_flowchart(self) -> None:
        claims = "1. 一种调度方法，包括以下步骤：步骤一，采集；步骤二，打分。\n"
        kinds = [item["kind"] for item in suggest_figures(claims, patent_type="invention")]
        self.assertIn("flowchart", kinds)

    def test_internal_cavity_gets_section(self) -> None:
        claims = "1. 一种装置，包括壳体，所述壳体内设有冷却腔体。\n"
        kinds = [item["kind"] for item in suggest_figures(claims, patent_type="invention")]
        self.assertIn("section", kinds)
        self.assertIn("block_diagram", kinds)

    def test_disclosure_lineart_kept_and_claim_kind_appended(self) -> None:
        plan = {
            "figures": [
                {
                    "fig": 1,
                    "kind": "lineart",
                    "use_in_disclosure": True,
                    "covers": ["1"],
                    "reason": "总装",
                    "relates_to": [],
                }
            ]
        }
        claims = "1. 一种装置，所述壳体可拆卸连接端盖。\n"
        figs = suggest_figures(claims, patent_type="utility_model", disclosure_plan=plan)
        kinds = [item["kind"] for item in figs]
        self.assertIn("lineart", kinds)
        self.assertIn("exploded", kinds)
        exploded = next(item for item in figs if item["kind"] == "exploded")
        self.assertEqual(exploded["source"], "pending")

    def test_validate_requires_reason(self) -> None:
        findings = validate_plan({"figures": [{"fig": 1, "kind": "flowchart", "reason": "", "covers": []}]})
        self.assertIn("NO_REASON", {item.code for item in findings})

    def test_build_plan_schema(self) -> None:
        plan = build_plan("1. 一种方法，包括以下步骤：步骤一，采集。\n")
        self.assertEqual(plan["$schema"], "application_figure_plan")
        self.assertTrue(plan["figures"])


if __name__ == "__main__":
    unittest.main()
