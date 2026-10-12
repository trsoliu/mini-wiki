# -*- coding: utf-8 -*-
"""image_gen planner: existing lineart vs img2img vs txt2img; CAD never qualifies."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

from image_gen import (
    GEN_EXISTING,
    GEN_IMG2IMG,
    GEN_TXT2IMG,
    FALLBACK,
    attach_job_mode,
    decide_mode,
    is_design_photo_for_disclosure,
    is_qualified_existing_lineart,
    is_source_candidate,
)


def _png(case: Path, name: str) -> Path:
    p = case / name
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8)
    return p


class TestImageGen(unittest.TestCase):
    def test_existing_lineart(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = _png(case, "ok.png")
            plan = {
                "figures": [
                    {
                        "kind": "lineart",
                        "path": img.name,
                        "relevance": 80,
                        "quality": 80,
                        "score": 80,
                        "role": "assembly",
                    }
                ]
            }
            d = decide_mode(plan, case)
            self.assertEqual(d["mode"], GEN_EXISTING)
            self.assertTrue(d["skip_generation"])
            self.assertEqual(d["fallback"], "")

    def test_cad_never_qualifies_as_lineart(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = _png(case, "cad.png")
            fig = {
                "kind": "cad",
                "path": img.name,
                "relevance": 90,
                "quality": 90,
                "score": 90,
                "role": "reference",
                "use_in_disclosure": False,
            }
            self.assertFalse(is_qualified_existing_lineart(fig, case))
            self.assertTrue(is_source_candidate(fig, case))
            d = decide_mode({"figures": [fig]}, case)
            self.assertEqual(d["mode"], GEN_IMG2IMG)
            self.assertEqual(d["fallback"], FALLBACK)
            self.assertFalse(d["skip_generation"])
            self.assertTrue(d["cad_never_lineart"])
            self.assertTrue(d["cad_as_material_only"])

    def test_low_score_lineart_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            img = _png(case, "scribble.png")
            fig = {
                "kind": "lineart",
                "path": img.name,
                "relevance": 40,
                "quality": 40,
                "score": 40,
            }
            self.assertFalse(is_qualified_existing_lineart(fig, case))

    def test_txt2img_when_no_sources(self):
        d = decide_mode({"figures": []}, Path("."))
        self.assertEqual(d["mode"], GEN_TXT2IMG)
        self.assertFalse(d["skip_generation"])

    def test_attach_job_mode(self):
        decision = {"mode": GEN_IMG2IMG, "fallback": FALLBACK}
        job = attach_job_mode({"source_paths": ["/tmp/a.png"]}, decision)
        self.assertEqual(job["gen_mode"], GEN_IMG2IMG)
        self.assertEqual(job["fallback_mode"], FALLBACK)
        self.assertFalse(job["forbid_text_only"])

        empty = attach_job_mode({"source_paths": []}, {"mode": GEN_TXT2IMG})
        self.assertEqual(empty["gen_mode"], GEN_TXT2IMG)

    def test_design_photos_listed_for_disclosure(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            photo = _png(case, "product.png")
            cad = _png(case, "cad.png")
            plan = {
                "patent_type": "design",
                "figures": [
                    {
                        "kind": "photo_clean",
                        "path": photo.name,
                        "relevance": 80,
                        "quality": 80,
                        "score": 80,
                        "role": "perspective",
                    },
                    {
                        "kind": "cad",
                        "path": cad.name,
                        "relevance": 90,
                        "quality": 90,
                        "score": 90,
                        "role": "reference",
                    },
                ],
            }
            self.assertTrue(is_design_photo_for_disclosure(plan["figures"][0], case))
            self.assertFalse(is_design_photo_for_disclosure(plan["figures"][1], case))
            d = decide_mode(plan, case)
            self.assertTrue(d["design_photos_in_disclosure"])
            self.assertEqual(len(d["design_photos"]), 1)
            self.assertEqual(d["rules"]["design_embed_md_and_docx"], ["photo_clean", "lineart"])
            self.assertTrue(d["cad_never_in_disclosure"])


if __name__ == "__main__":
    unittest.main()
