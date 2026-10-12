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

from structure_lineart_compose import (
    build_part_jobs,
    render_view,
    validate_compose,
)

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nE0AAAAASUVORK5CYII="
)


class TestStructureLineartCompose(unittest.TestCase):
    def test_crop_writes_part_svgs_and_relative_hrefs(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            (case / "lineart.png").write_bytes(PNG)
            compose = {
                "version": 1,
                "canvas": {"width": 100, "height": 80},
                "views": [
                    {
                        "view_name": "总装",
                        "layout": "assembly",
                        "source_image": "lineart.png",
                        "output_svg_path": "out.svg",
                        "parts": [
                            {
                                "id": "1",
                                "name": "壳体",
                                "source": "crop",
                                "slot": [0.0, 0.0, 0.6, 0.8],
                                "crop_box": [0.0, 0.0, 0.6, 0.8],
                                "z_index": 1,
                            },
                            {
                                "id": "2",
                                "name": "卡扣",
                                "source": "crop",
                                "slot": [0.5, 0.4, 0.4, 0.4],
                                "crop_box": [0.5, 0.4, 0.4, 0.4],
                                "z_index": 2,
                            },
                        ],
                    }
                ],
            }
            structure = {
                "parts": [{"id": "1", "name": "壳体"}, {"id": "2", "name": "卡扣"}]
            }
            self.assertEqual(validate_compose(compose, case, structure=structure), [])
            out = render_view(compose, compose["views"][0], case)
            text = out.read_text(encoding="utf-8")
            self.assertIn('id="view-source"', text)
            self.assertIn('id="part-1"', text)
            self.assertIn('id="part-2"', text)
            self.assertIn('data-part-id="1"', text)
            self.assertIn('href="parts/', text)
            self.assertNotIn("clipPath", text)
            self.assertNotIn("src-assembly", text)
            self.assertNotIn("data:image", text)
            self.assertIn("inkscape:groupmode", text)
            child = out.parent / "parts" / "总装_1.svg"
            self.assertTrue(child.is_file(), child)
            child_text = child.read_text(encoding="utf-8")
            self.assertIn("viewBox=", child_text)
            self.assertIn("../lineart.png", child_text)
            self.assertNotIn("data:image", child_text)

    def test_image_and_placeholder_and_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            part = case / "p1.png"
            part.write_bytes(PNG)
            compose = {
                "version": 1,
                "views": [
                    {
                        "view_name": "爆炸",
                        "layout": "exploded",
                        "output_svg_path": "exp.svg",
                        "parts": [
                            {
                                "id": "1",
                                "name": "壳体",
                                "source": "image",
                                "image_path": "p1.png",
                                "slot": [0.05, 0.05, 0.4, 0.4],
                            },
                            {
                                "id": "2",
                                "name": "卡扣",
                                "source": "placeholder",
                                "slot": [0.55, 0.05, 0.4, 0.4],
                            },
                            {
                                "id": "3",
                                "name": "螺钉",
                                "source": "image",
                                "image_path": "missing.png",
                            },
                        ],
                    }
                ],
            }
            structure = {
                "parts": [
                    {"id": "1", "name": "壳体"},
                    {"id": "2", "name": "卡扣"},
                    {"id": "3", "name": "螺钉"},
                ]
            }
            errs = validate_compose(compose, case, structure=structure)
            self.assertTrue(any("missing.png" in e for e in errs))
            self.assertEqual(
                validate_compose(
                    compose, case, structure=structure, require_part_images=False
                ),
                [],
            )
            jobs = build_part_jobs(compose, case)
            self.assertEqual([j["part_id"] for j in jobs], ["3"])
            out = render_view(
                compose,
                {
                    **compose["views"][0],
                    "parts": compose["views"][0]["parts"][:2],
                },
                case,
            )
            text = out.read_text(encoding="utf-8")
            self.assertIn('data-source="image"', text)
            self.assertIn('data-source="placeholder"', text)
            self.assertIn('href="parts/', text)
            self.assertNotIn("data:image", text)
            self.assertNotIn('id="view-source"', text)
            child = out.parent / "parts" / "爆炸_1.svg"
            self.assertTrue(child.is_file(), child)
            child_text = child.read_text(encoding="utf-8")
            self.assertIn("../p1.png", child_text)
            ph = out.parent / "parts" / "爆炸_2.svg"
            self.assertTrue(ph.is_file(), ph)
            self.assertIn("stroke-dasharray", ph.read_text(encoding="utf-8"))

    def test_rejects_unknown_and_uncertain_crop(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            (case / "lineart.png").write_bytes(PNG)
            compose = {
                "version": 1,
                "uncertain": ["2"],
                "views": [
                    {
                        "output_svg_path": "o.svg",
                        "source_image": "lineart.png",
                        "parts": [
                            {
                                "id": "99",
                                "name": "幽灵",
                                "source": "placeholder",
                                "slot": [0, 0, 0.5, 0.5],
                            },
                            {
                                "id": "2",
                                "name": "卡扣",
                                "source": "crop",
                                "slot": [0.5, 0.5, 0.4, 0.4],
                            },
                        ],
                    }
                ],
            }
            structure = {"parts": [{"id": "2", "name": "卡扣"}], "uncertain": ["2"]}
            errors = validate_compose(compose, case, structure=structure)
            self.assertTrue(any("99" in e for e in errors))
            self.assertTrue(any("uncertain" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
