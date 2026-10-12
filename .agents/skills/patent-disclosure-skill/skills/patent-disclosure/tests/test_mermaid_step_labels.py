# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from mermaid_render import ensure_step_ids_in_visible_labels, render_markdown_mermaid


class EnsureStepIdLabelsTests(unittest.TestCase):
    def test_prefixes_missing_step_id(self) -> None:
        src = "flowchart TD\n  S1[识别教师指令对应的教学活动] --> S2[确定活动状态和目标]\n"
        out, n = ensure_step_ids_in_visible_labels(src)
        self.assertEqual(n, 2)
        self.assertIn('S1["S1 识别教师指令对应的教学活动"]', out)
        self.assertIn('S2["S2 确定活动状态和目标"]', out)

    def test_keeps_labels_that_already_show_id(self) -> None:
        src = 'flowchart TD\n  S1["S1 采集节点指标"] --> S2["S2 滑动平滑生成画像"]\n'
        out, n = ensure_step_ids_in_visible_labels(src)
        self.assertEqual(n, 0)
        self.assertEqual(out, src)

    def test_diamond_and_skips_plain_module_ids(self) -> None:
        src = "flowchart TD\n  S5{是否达阈} --> A[\"模块A\"]\n"
        out, n = ensure_step_ids_in_visible_labels(src)
        self.assertEqual(n, 1)
        self.assertIn('S5{"S5 是否达阈"}', out)
        self.assertIn('A["模块A"]', out)


class RenderRewritesSourceTests(unittest.TestCase):
    def test_rewritten_source_is_written_back(self) -> None:
        md = (
            "```mermaid\n"
            "flowchart TD\n"
            "  S1[识别指令] --> S2[确定状态]\n"
            "```\n"
        )
        rendered: list[str] = []

        def fake_render(src: str, png: Path) -> None:
            rendered.append(src)
            png.parent.mkdir(parents=True, exist_ok=True)
            png.write_bytes(b"png")

        with tempfile.TemporaryDirectory() as td:
            out_md = Path(td) / "out.md"
            text, ok, failed = render_markdown_mermaid(
                md,
                out_md_path=out_md,
                assets_rel="mermaid_figures",
                render_one=fake_render,
            )
        self.assertEqual(ok, 1)
        self.assertEqual(failed, 0)
        self.assertIn('S1["S1 识别指令"]', rendered[0])
        self.assertIn('S1["S1 识别指令"]', text)
        self.assertIn("mermaid_figures/fig_001.png", text)


if __name__ == "__main__":
    unittest.main()
