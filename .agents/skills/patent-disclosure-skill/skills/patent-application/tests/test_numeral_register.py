# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from check_numeral_register import check_register


SCHEMA = {
    "parts": [
        {"id": "1", "name": "壳体"},
        {"id": "2", "name": "端盖"},
    ]
}
PLAN = {
    "figures": [
        {"fig": 1, "kind": "lineart", "use_in_disclosure": True, "covers": ["1", "2"]},
        {"fig": 2, "kind": "lineart", "use_in_disclosure": True, "covers": ["1"]},
    ]
}
REGISTER_OK = {
    "parts": [
        {"id": "1", "name": "壳体", "figures": [1, 2], "claims": [1], "specification": True},
        {"id": "2", "name": "端盖", "figures": [1], "claims": [1], "specification": True},
    ],
    "figures": [
        {"fig": 1, "title": "总装", "kind": "lineart", "disclosure_only": True},
        {"fig": 2, "title": "剖视", "kind": "lineart", "disclosure_only": True},
    ],
}
CLAIMS = "1. 一种装置，包括壳体（1）和端盖（2）；其特征在于二者围成电机腔。\n"
SPEC = "本实用新型包括壳体（1）与端盖（2）。如图1所示。\n"


class NumeralRegisterTests(unittest.TestCase):
    def test_aligned_pass(self) -> None:
        findings = check_register(
            REGISTER_OK,
            schema=SCHEMA,
            figure_plan=PLAN,
            claims_text=CLAIMS,
            spec_text=SPEC,
        )
        self.assertEqual([item for item in findings if item.level == "ERROR"], [])

    def test_schema_part_missing(self) -> None:
        slim = {
            "parts": [REGISTER_OK["parts"][0]],
            "figures": REGISTER_OK["figures"],
        }
        codes = {item.code for item in check_register(slim, schema=SCHEMA, figure_plan=PLAN)}
        self.assertIn("SCHEMA_MISSING", codes)

    def test_figure_not_registered(self) -> None:
        slim = {
            "parts": [
                {"id": "1", "name": "壳体", "figures": [1], "claims": [1], "specification": True},
                {"id": "2", "name": "端盖", "figures": [1], "claims": [1], "specification": True},
            ],
            "figures": [{"fig": 1, "title": "总装"}],
        }
        codes = {item.code for item in check_register(slim, schema=SCHEMA, figure_plan=PLAN)}
        self.assertIn("FIG_UNREGISTERED", codes)

    def test_claim_mark_missing(self) -> None:
        findings = check_register(
            REGISTER_OK,
            schema=SCHEMA,
            figure_plan=PLAN,
            claims_text="1. 一种装置，包括若干零件；其特征在于围成腔体。\n",
            spec_text=SPEC,
        )
        codes = {item.code for item in findings if item.level == "ERROR"}
        self.assertIn("CLAIM_MARK_MISSING", codes)


if __name__ == "__main__":
    unittest.main()
