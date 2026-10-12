# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from structure_callout_overlay import (
    canvas_padding,
    image_size,
    pad_svg_canvas,
    render_view,
    validate_manifest,
)


# 1×1 白色 PNG。
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nE0AAAAASUVORK5CYII="
)


class TestStructureCalloutOverlay(unittest.TestCase):
    def test_validate_and_render_svg(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            (case / "lineart.png").write_bytes(PNG)
            manifest = {
                "version": 1,
                "coordinate_system": "normalized",
                "views": [
                    {
                        "image_path": "lineart.png",
                        "output_svg_path": "lineart_callouts.svg",
                        "callouts": [
                            {
                                "id": "1",
                                "name": "壳体",
                                "anchor": [0.65, 0.65],
                                "label": [0.85, 0.40],
                                "confidence": 0.95,
                            }
                        ],
                    }
                ],
            }
            structure = {"parts": [{"id": "1", "name": "壳体"}]}
            self.assertEqual(validate_manifest(manifest, case, structure=structure), [])
            self.assertEqual(image_size(case / "lineart.png"), (1, 1))
            output = render_view(manifest["views"][0], case)
            text = output.read_text(encoding="utf-8")
            self.assertIn('data-part-id="1"', text)
            self.assertIn("<path", text)
            self.assertIn(">1</text>", text)
            self.assertIn("data:image/png;base64,", text)
            self.assertIn("structure-callouts", text)
            self.assertIn('viewBox="-', text)
            self.assertGreaterEqual(canvas_padding(100, 80, {}), 64)
            self.assertIn('viewBox="-', pad_svg_canvas('<svg width="10" height="10" viewBox="0 0 10 10"></svg>', 4))

    def test_injects_into_composed_svg_without_flattening_parts(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            (case / "composed.svg").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80" '
                'viewBox="0 0 100 80">\n'
                '<g id="part-1" data-part-id="1"><rect width="40" height="40"/></g>\n'
                "</svg>\n",
                encoding="utf-8",
            )
            manifest = {
                "version": 1,
                "coordinate_system": "normalized",
                "views": [
                    {
                        "base_svg_path": "composed.svg",
                        "output_svg_path": "labeled.svg",
                        "callouts": [
                            {
                                "id": "1",
                                "name": "壳体",
                                "anchor": [0.40, 0.40],
                                "label": [0.80, 0.20],
                                "confidence": 0.95,
                            }
                        ],
                    }
                ],
            }
            structure = {"parts": [{"id": "1", "name": "壳体"}]}
            self.assertEqual(validate_manifest(manifest, case, structure=structure), [])
            output = render_view(manifest["views"][0], case)
            text = output.read_text(encoding="utf-8")
            self.assertIn('id="part-1"', text)
            self.assertIn('id="structure-callouts"', text)
            self.assertIn(">1</text>", text)
            self.assertNotIn("data:image/png;base64,", text)
            self.assertIn('viewBox="-', text)

    def test_rejects_unknown_id_and_bad_coordinates(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            (case / "lineart.png").write_bytes(PNG)
            manifest = {
                "version": 1,
                "coordinate_system": "normalized",
                "views": [
                    {
                        "image_path": "lineart.png",
                        "output_svg_path": "out.svg",
                        "callouts": [
                            {
                                "id": "99",
                                "name": "未知",
                                "anchor": [1.2, 0.5],
                                "label": [0.5, 0.5],
                                "confidence": 0.4,
                            }
                        ],
                    }
                ],
            }
            errors = validate_manifest(
                manifest,
                case,
                structure={"parts": [{"id": "1", "name": "壳体"}]},
            )
            self.assertTrue(any("99" in error for error in errors))
            self.assertTrue(any("超出" in error for error in errors))
            self.assertTrue(any("置信度" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
