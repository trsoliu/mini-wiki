# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools" / "fence"))
sys.path.insert(0, str(PKG / "tools"))

from check_layout import main as layout_main
from check_scorecard import main as check_main
from family_lib import validate_family
from layout_lib import validate_decompose, validate_design_around, validate_matrix
from scorecard_lib import load_table, score_answers


def _answers(overrides: dict | None = None) -> dict:
    items = {
        "L1": {"score": 2, "evidence": "第五章必要特征与 3.4 步骤对应"},
        "L2": {"score": 2, "evidence": "第三与第五章逐条可指"},
        "L3": {"score": 2, "evidence": "1.1 最接近文献区别在卡扣顺序"},
        "L4": {"score": 2, "evidence": "独权一层，优选在实施例"},
        "T1": {"score": 2, "evidence": "替换外壳仍须用到锁合机构"},
        "T2": {"score": 2, "evidence": "主路径可实施"},
        "T3": {"score": 2, "evidence": "与对比文件结构关系不同"},
        "E1": {"score": None, "evidence": "材料未写寿命"},
        "E2": {"score": None, "evidence": "材料未写竞品"},
        "E3": {"score": None, "evidence": "无许可事实"},
        "F1": {"score": 2, "evidence": "锁合机构与外观轮廓可分件"},
        "F2": {"score": 2, "evidence": "P1 n_class=improve"},
        "F3": {"score": 2, "evidence": "结构图已有铰链局部"},
    }
    if overrides:
        items.update(overrides)
    return {"scorecard_id": "gbt42748_fence", "disclosure_md": "x.md", "items": items}


def _plan(**extra) -> dict:
    plan = {
        "title": "专利布局 · 保护型1+N",
        "strategy": "protective",
        "case_id": "demo",
        "nodes": [
            {
                "id": "C1",
                "role": "core",
                "patent_type": "invention",
                "title": "锁合方法",
                "necessary_features": "步骤一锁定",
                "slim_note": "拆走外观轮廓与铰链局部",
                "write_this_round": True,
                "material_ok": True,
            },
            {
                "id": "P1",
                "role": "satellite",
                "n_class": "improve",
                "patent_type": "utility_model",
                "title": "铰链结构",
                "necessary_features": "双轴铰链",
                "matrix_density": "sparse",
                "write_this_round": True,
                "material_ok": True,
            },
            {
                "id": "P2",
                "role": "satellite",
                "n_class": "scenario",
                "patent_type": "design",
                "title": "折臂造型",
                "necessary_features": "臂与灯头弧面",
                "matrix_density": "dense",
                "write_this_round": False,
                "material_ok": True,
            },
        ],
        "matrix": {
            "means": [{"id": "m1", "label": "双轴铰链"}],
            "effects": [{"id": "e1", "label": "预紧"}],
            "cells": [{"mean": "m1", "effect": "e1", "density": "sparse", "node_id": "P1"}],
        },
    }
    plan.update(extra)
    return plan


class ScorecardTests(unittest.TestCase):
    def test_table_loads(self) -> None:
        table = load_table()
        self.assertEqual(table["id"], "gbt42748_fence")
        self.assertGreaterEqual(len(table["items"]), 10)

    def test_open_when_satellite_and_material(self) -> None:
        table = load_table()
        r = score_answers(table, _answers())
        self.assertTrue(r["open_fence"], r["reasons"])

    def test_no_open_without_satellite(self) -> None:
        table = load_table()
        r = score_answers(table, _answers({"F1": {"score": 0, "evidence": "拆不开"}}))
        self.assertFalse(r["open_fence"])
        self.assertTrue(any("F1" in x for x in r["reasons"]))

    def test_search_unscored_does_not_block(self) -> None:
        table = load_table()
        r = score_answers(table, _answers({"L3": {"score": None, "evidence": "未查新"}}))
        self.assertTrue(r["open_fence"], r["reasons"])

    def test_positive_needs_evidence(self) -> None:
        table = load_table()
        with self.assertRaises(ValueError):
            score_answers(table, _answers({"F1": {"score": 2, "evidence": ""}}))

    def test_cli_table(self) -> None:
        self.assertEqual(check_main(["--table"]), 0)


class LayoutTests(unittest.TestCase):
    def test_decompose_needs_source(self) -> None:
        err = validate_decompose({"nodes": [{"id": "D1", "layer": "principle", "summary": "x"}]})
        self.assertTrue(any("source" in e for e in err))

    def test_around_unknown_not_satellite(self) -> None:
        err = validate_design_around(
            {
                "rows": [
                    {
                        "feature": "铰链",
                        "commercial": "unknown",
                        "disposition": "satellite",
                    }
                ]
            }
        )
        self.assertTrue(any("商业未知" in e for e in err))

    def test_matrix_unchecked_ok(self) -> None:
        err = validate_matrix(
            {
                "means": [{"id": "m1", "label": "a"}],
                "effects": [{"id": "e1", "label": "b"}],
                "cells": [{"mean": "m1", "effect": "e1", "density": "unchecked"}],
            }
        )
        self.assertEqual(err, [])

    def test_layout_cli(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "decompose.yaml"
            p.write_text(
                "nodes:\n  - id: D1\n    layer: principle\n    summary: x\n    source: 第五章\n",
                encoding="utf-8",
            )
            self.assertEqual(layout_main(["--decompose", str(p)]), 0)


class FamilyPlanTests(unittest.TestCase):
    def test_title_required(self) -> None:
        err = validate_family({"title": "族树", "nodes": []})
        self.assertTrue(any("专利布局" in e for e in err))

    def test_title_needs_protective(self) -> None:
        err = validate_family({"title": "专利布局", "nodes": []})
        self.assertTrue(any("保护型 1+N" in e for e in err))

    def test_dense_cannot_write(self) -> None:
        plan = _plan()
        plan["nodes"][2]["write_this_round"] = True
        err = validate_family(plan)
        self.assertTrue(any("dense" in e for e in err))

    def test_valid_plan(self) -> None:
        self.assertEqual(validate_family(_plan()), [])
