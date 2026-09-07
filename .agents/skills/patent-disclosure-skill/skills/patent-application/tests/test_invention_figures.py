# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from render_invention_figures import render_block_diagram, render_flowchart


BLOCK = {
    "fig": 1,
    "kind": "block_diagram",
    "caption": "系统模块关系示意图",
    "columns": [
        {
            "id": "sch",
            "label": "调度器",
            "nodes": [{"id": "n21", "label": "匹配打分"}],
        }
    ],
    "extras": [
        {
            "id": "cfg",
            "label": "配置中心",
            "above": "sch",
            "nodes": [{"id": "n11", "label": "阈值"}],
        }
    ],
    "edges": [{"from": "n11", "to": "n21"}],
}

TWO_COL = {
    "fig": 1,
    "kind": "block_diagram",
    "caption": "系统模块关系示意图",
    "columns": [
        {
            "id": "worker",
            "label": "工作节点",
            "nodes": [
                {"id": "n31", "label": "指标采集"},
                {"id": "n33", "label": "心跳上报"},
                {"id": "n32", "label": "任务执行"},
            ],
        },
        {
            "id": "scheduler",
            "label": "调度器",
            "nodes": [
                {"id": "n21", "label": "资源画像聚合"},
                {"id": "n22", "label": "匹配打分"},
                {"id": "n23", "label": "限频重排队"},
                {"id": "n24", "label": "派发"},
            ],
        },
    ],
    "extras": [
        {
            "id": "cfg",
            "label": "配置中心",
            "above": "scheduler",
            "nodes": [{"id": "n11", "label": "静态优先级与阈值"}],
        }
    ],
    "edges": [
        {"from": "n31", "to": "n21"},
        {"from": "n33", "to": "n23"},
        {"from": "n24", "to": "n32"},
        {"from": "n21", "to": "n22"},
        {"from": "n22", "to": "n23"},
        {"from": "n23", "to": "n24"},
        {"from": "n11", "to": "n22"},
        {"from": "n11", "to": "n23"},
    ],
}

FLOW = {
    "fig": 2,
    "kind": "flowchart",
    "caption": "主流程示意图",
    "nodes": [
        {"id": "step1", "row": 0, "col": 0, "shape": "rect", "label": "步骤一，采集节点指标"},
        {"id": "step3", "row": 1, "col": 0, "shape": "diamond", "label": "步骤三，是否达阈"},
        {"id": "step3a", "row": 2, "col": -1, "shape": "rect", "label": "对队首窗口重排"},
        {"id": "step3b", "row": 2, "col": 1, "shape": "rect", "label": "保持当前队序"},
        {"id": "step4", "row": 3, "col": 0, "shape": "rect", "label": "步骤四，按序派发"},
        {"id": "step5", "row": 4, "col": 0, "shape": "rect", "label": "迁移任务"},
    ],
    "edges": [
        {"from": "step1", "to": "step3"},
        {"from": "step3", "to": "step3a", "label": "是"},
        {"from": "step3", "to": "step3b", "label": "否"},
        {"from": "step3a", "to": "step4"},
        {"from": "step3b", "to": "step4"},
        {"from": "step3b", "to": "step1", "label": "否", "route": "right"},
        {"from": "step5", "to": "step1", "route": "left"},
    ],
}


class InventionFigureTests(unittest.TestCase):
    def test_block_has_names_no_callouts(self) -> None:
        svg = render_block_diagram(BLOCK)
        self.assertNotIn(">图 1<", svg)
        self.assertNotIn("图 1", svg)
        self.assertNotIn('class="callout"', svg)
        self.assertIn("匹配打分", svg)
        self.assertIn("配置中心", svg)

    def test_block_is_black_white(self) -> None:
        svg = render_block_diagram(BLOCK)
        self.assertNotIn("fill=\"#", svg.replace('fill="#fff"', "").replace('fill="#000"', ""))
        self.assertIn('fill="none"', svg)

    def test_flowchart_has_chinese_steps_no_callouts(self) -> None:
        svg = render_flowchart(FLOW)
        self.assertNotIn(">图 2<", svg)
        self.assertNotIn("图 2", svg)
        self.assertIn("步骤一", svg)
        self.assertIn("是", svg)
        self.assertIn("否", svg)
        self.assertNotIn('class="callout"', svg)
        self.assertNotIn("201", svg)
        self.assertNotIn("202", svg)

    def test_svg_viewbox_fits_content_not_a4(self) -> None:
        import re

        for svg in (render_flowchart(FLOW), render_block_diagram(TWO_COL)):
            match = re.search(r'viewBox="([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)"', svg)
            self.assertIsNotNone(match)
            _x, _y, w, h = map(float, match.groups())
            self.assertLess(w, 210.0)
            self.assertLess(h, 220.0)
            self.assertNotIn('height="297', svg)
            self.assertNotIn("图 1", svg)
            self.assertNotIn("图 2", svg)

    def test_png_screenshot_has_tight_ink_margin(self) -> None:
        import tempfile

        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow 不可用")

        from render_invention_figures import svg_to_png

        svg = render_flowchart(FLOW)
        with tempfile.TemporaryDirectory() as td:
            svg_path = Path(td) / "fig.svg"
            png_path = Path(td) / "fig.png"
            svg_path.write_text(svg, encoding="utf-8")
            if not svg_to_png(svg_path, png_path) or not png_path.is_file():
                self.skipTest("Playwright PNG 不可用")
            im = Image.open(png_path)
            w, h = im.size
            mask = im.convert("L").point(lambda p: 255 if p < 250 else 0)
            box = mask.getbbox()
            self.assertIsNotNone(box)
            x0, y0, x1, y1 = box
            self.assertLess(y0 / h, 0.08)
            self.assertLess((h - y1) / h, 0.08)
            self.assertGreater(w / h, 0.45)

    def test_flowchart_polylines_orthogonal(self) -> None:
        import re

        svg = render_flowchart(FLOW)
        for m in re.finditer(r'class="flow" points="([^"]+)"', svg):
            pts = [tuple(map(float, p.split(","))) for p in m.group(1).split()]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                self.assertTrue(
                    abs(x1 - x2) < 0.2 or abs(y1 - y2) < 0.2,
                    msg=f"non-ortho {(x1, y1)}→{(x2, y2)}",
                )

    def test_columns_pack_by_own_node_count(self) -> None:
        from render_invention_figures import layout_block

        nodes, groups, _sides = layout_block(TWO_COL)
        step = nodes["n33"][1] - nodes["n31"][1]
        self.assertAlmostEqual(step, 28.0, places=1)
        self.assertAlmostEqual(nodes["n32"][1] - nodes["n33"][1], step, places=1)
        self.assertLess(groups["worker"][3], groups["scheduler"][3] - 10.0)

    def test_config_edges_do_not_pierce_modules(self) -> None:
        import re

        from render_invention_figures import _segment_hits_box

        svg = render_block_diagram(TWO_COL)
        rects = [
            (float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in re.finditer(
                r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                r'fill="#fff" stroke="#000" stroke-width="[\d.]+"/>',
                svg,
            )
        ]
        self.assertGreaterEqual(len(rects), 8)
        for m in re.finditer(r'class="flow" points="([^"]+)"', svg):
            pts = [tuple(map(float, p.split(","))) for p in m.group(1).split()]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                for box in rects:
                    self.assertFalse(
                        _segment_hits_box(x1, y1, x2, y2, box),
                        msg=f"segment {(x1, y1)}→{(x2, y2)} crosses {box}",
                    )

    def test_loop_routes_miss_side_boxes(self) -> None:
        import re

        from render_invention_figures import _segment_hits_box

        svg = render_flowchart(FLOW)
        rects = [
            (float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)))
            for m in re.finditer(
                r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" '
                r'fill="#fff" stroke="#000" stroke-width="[\d.]+"/>',
                svg,
            )
        ]
        for m in re.finditer(r'class="flow" points="([^"]+)"', svg):
            pts = [tuple(map(float, p.split(","))) for p in m.group(1).split()]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                for box in rects:
                    self.assertFalse(
                        _segment_hits_box(x1, y1, x2, y2, box, pad=0.6),
                        msg=f"loop/flow {(x1, y1)}→{(x2, y2)} crosses {box}",
                    )


if __name__ == "__main__":
    unittest.main()
