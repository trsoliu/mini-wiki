# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from highlights import clip_quote, ensure_highlights, format_analysis, infer_highlights, paint_html, paint_runs, strength_label, tidy_cjk_wrap


class HighlightTests(unittest.TestCase):
    def test_strength_label(self) -> None:
        self.assertEqual(strength_label("强"), "很强")
        self.assertEqual(strength_label("无"), "未见")

    def test_cross_term_same_id(self) -> None:
        highlights = [{"id": "H1", "claim": "下行资源", "evidence": "CORESET", "bg": "C4B5FD", "fg": "5B21B6"}]
        claim_runs = paint_runs("配置下行资源", highlights, side="claim")
        evid_runs = paint_runs("由 CORESET 承载", highlights, side="evidence")
        self.assertTrue(any(hid == "H1" for _, hid in claim_runs))
        self.assertTrue(any(hid == "H1" for _, hid in evid_runs))
        html = paint_html("配置下行资源", highlights, side="claim")
        self.assertIn("data-hl=\"H1\"", html)

    def test_infer_common_phrase(self) -> None:
        found = infer_highlights("壳体与端盖围出冷却腔", "壳体与端盖形成冷却腔")
        self.assertTrue(any("壳体与端盖" in (h.get("claim") or "") for h in found))

    def test_tidy_cjk_wrap(self) -> None:
        self.assertEqual(tidy_cjk_wrap("以及皮肤固定 座，"), "以及皮肤固定座，")
        self.assertEqual(tidy_cjk_wrap("所述外壳"), "所述外壳")

    def test_format_analysis_breaks_items(self) -> None:
        one_line = (
            "对应：权要「外壳内设有能朝开口运动的推送件」对应对照「外壳内的助针组件」。"
            "差别：对照称为助针组件，不称为壳体组件/助推芯子。"
            "依据：对比文件1 · 说明书 [0009]"
        )
        lined = format_analysis(one_line)
        self.assertEqual(
            lined.split("\n"),
            [
                "对应：权要「外壳内设有能朝开口运动的推送件」对应对照「外壳内的助针组件」。",
                "差别：对照称为助针组件，不称为壳体组件/助推芯子。",
                "依据：对比文件1 · 说明书 [0009]",
            ],
        )
        already = "对应：外壳。\n差别：无壳体组件名称。\n依据：说明书 [0009]。"
        self.assertEqual(format_analysis(already).count("\n"), 2)

    def test_clip_quote_around_needle(self) -> None:
        para = (
            "一种持续血糖监测装置，包括外壳、置于所述外壳内的助针组件，以及皮肤固定座，"
            "所述外壳的一端设有开口，所述监测装置还包括设置于所述助针组件一端的触发罩，"
            "所述触发罩具有用于与皮肤接触的抵顶部。"
        )
        around_open = clip_quote(para, ["开口"], max_len=60)
        around_shell = clip_quote(para, ["外壳"], max_len=60)
        self.assertIn("开口", around_open)
        self.assertIn("外壳", around_shell)
        self.assertLess(len(around_open), len(para))
        self.assertNotEqual(around_open, around_shell)
        self.assertTrue("…" in around_open)

    def test_ensure_fills_when_missing(self) -> None:
        chart = ensure_highlights(
            {
                "features": [{"feature_id": "F1", "text": "冷却腔位于壳体"}],
                "columns": [{"id": "D1"}],
                "cells": [{"feature_id": "F1", "column_id": "D1", "quote": "冷却腔设于壳体内部"}],
            }
        )
        self.assertTrue(chart["highlights"])


if __name__ == "__main__":
    unittest.main()
