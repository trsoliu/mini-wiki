# -*- coding: utf-8 -*-
"""独权特征清单校验与笔记表渲染。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from analyze.claim_features import (
    format_desc_cell,
    normalize_claim_features,
    render_section4_tables,
    upsert_feature_sections,
    validate_claim_features,
)
from analyze.validate_claim_features import main as validate_main


def _sample() -> dict:
    return {
        "pub_number": "CN219812345U",
        "source": "agent",
        "features": [
            {
                "feature_id": "F1",
                "claim_no": 1,
                "text": "壳体与端盖围出冷却腔",
                "plain": "壳体和端盖围成冷却腔",
                "desc_paras": ["0021"],
                "figures": ["图1"],
            },
            {
                "feature_id": "F2",
                "claim_no": 1,
                "text": "冷却板分区流道",
                "plain": "冷却板分成两区流道",
                "desc_paras": ["0022", "0023"],
            },
        ],
    }


class ClaimFeaturesTests(unittest.TestCase):
    def test_validate_ok(self) -> None:
        result = validate_claim_features(_sample())
        self.assertTrue(result["passed"])
        self.assertEqual(result["count"], 2)

    def test_duplicate_id_fails(self) -> None:
        raw = _sample()
        raw["features"][1]["feature_id"] = "F1"
        result = validate_claim_features(raw)
        self.assertFalse(result["passed"])
        self.assertTrue(any("duplicate" in x for x in result["issues"]))

    def test_format_desc_range(self) -> None:
        self.assertEqual(format_desc_cell(["0022", "0023"]), "说明书 0022–0023")

    def test_section4_contains_ids(self) -> None:
        md = render_section4_tables(normalize_claim_features(_sample()))
        self.assertIn("| F1 |", md)
        self.assertIn("| F2 |", md)
        self.assertIn("说明书 0021", md)

    def test_upsert_keeps_callout(self) -> None:
        note = (
            "## 四、独立权利要求精读\n\n"
            "> [!patent-claim] 权利要求 1\n\n"
            "> 【CN219812345U·权利要求1】一种总成。\n\n"
            "| 特征 | 大白话 | 说明书依据 |\n"
            "|------|--------|------------|\n"
            "| 旧名 | 旧 | |\n\n"
            "## 五、专利内术语表\n\n"
            "## 六、特征—说明书—附图对照\n\n"
            "| 特征 | 说明书位置 | 附图 |\n"
            "|------|------------|------|\n"
            "| 旧 | | |\n\n"
            "## 七、和现有技术的差别\n"
        )
        out = upsert_feature_sections(note, normalize_claim_features(_sample()))
        self.assertIn("[!patent-claim]", out)
        self.assertIn("| F1 |", out)
        self.assertNotIn("| 旧名 |", out)
        self.assertIn("## 六、", out)
        self.assertIn("图1", out)

    def test_cli_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "claim_features.json"
            path.write_text(json.dumps(_sample(), ensure_ascii=False), encoding="utf-8")
            self.assertEqual(validate_main(["-i", str(path), "--write"]), 0)
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["features"][0]["desc_paras"], ["0021"])


if __name__ == "__main__":
    unittest.main()
