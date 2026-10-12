# -*- coding: utf-8 -*-
"""cad-env probe, pip indexes, SVG HTTP port, requirements ASCII."""
from __future__ import annotations

import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

import bootstrap_cad_venv as boot
import cad_venv
import svg_screenshot as shot
from step_to_views import build_figure_plan_seed


class CadVenvTests(unittest.TestCase):
    def test_venv_name_and_range(self) -> None:
        self.assertEqual(cad_venv.VENV_NAME, "cad-env")
        self.assertTrue(str(cad_venv.VENV_DIR).endswith("cad-env") or cad_venv.VENV_DIR.name == "cad-env")
        self.assertTrue(cad_venv.version_supported((3, 10, 0)))
        self.assertTrue(cad_venv.version_supported((3, 11, 9)))
        self.assertTrue(cad_venv.version_supported((3, 12, 1)))
        self.assertFalse(cad_venv.version_supported((3, 9, 18)))
        self.assertFalse(cad_venv.version_supported((3, 13, 0)))

    def test_isolated_env_drops_pythonpath(self) -> None:
        with patch.dict("os.environ", {"PYTHONPATH": "C:\\leak", "PIP_INDEX_URL": "http://x"}, clear=False):
            env = cad_venv.isolated_env()
        self.assertNotIn("PYTHONPATH", env)
        self.assertNotIn("PIP_INDEX_URL", env)
        self.assertEqual(env.get("PYTHONNOUSERSITE"), "1")

    def test_status_missing_venv(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            st = cad_venv.status(Path(td) / "cad-env")
        self.assertFalse(st["ok"])
        self.assertEqual(st["reason"], "missing_venv")
        self.assertFalse(st["skip_install"])


class BootstrapIndexTests(unittest.TestCase):
    def test_china_mirrors_then_pypi(self) -> None:
        urls = boot._index_list(pypi_only=False, extra=[])
        self.assertEqual(urls[-1], "https://pypi.org/simple")
        self.assertTrue(any("tsinghua" in u or "tuna" in u for u in urls))
        self.assertTrue(any("aliyun" in u for u in urls))

    def test_pypi_only(self) -> None:
        self.assertEqual(boot._index_list(pypi_only=True, extra=[]), ["https://pypi.org/simple"])


class CadNoMatplotlibTests(unittest.TestCase):
    def test_cad_scripts_do_not_import_matplotlib(self) -> None:
        names = (
            "step_to_views.py",
            "svg_screenshot.py",
            "run_step_to_views.py",
            "cad_venv.py",
            "bootstrap_cad_venv.py",
            "requirements-step.txt",
        )
        for name in names:
            text = (SHARED / name).read_text(encoding="utf-8")
            self.assertNotIn("import matplotlib", text, name)
            self.assertNotIn("matplotlib_tessellate", text, name)


class RequirementsAsciiTests(unittest.TestCase):
    def test_step_and_root_are_ascii(self) -> None:
        for path in (SHARED / "requirements-step.txt", ROOT / "requirements.txt"):
            raw = path.read_bytes()
            raw.decode("ascii")


class SvgScreenshotTests(unittest.TestCase):
    def test_wrap_strips_xml_decl(self) -> None:
        html = shot.wrap_svg_html('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>')
        self.assertIn("<svg", html)
        self.assertNotIn("<?xml", html)
        self.assertIn('id="stage"', html)

    def test_wrap_allows_braces_in_svg(self) -> None:
        html = shot.wrap_svg_html('<svg><style>.x{fill:red}</style></svg>')
        self.assertIn("{fill:red}", html)

    def test_pick_free_port_skips_busy(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        busy = int(srv.getsockname()[1])
        try:
            got = shot.pick_free_port("127.0.0.1", preferred=busy)
            self.assertNotEqual(got, busy)
            self.assertGreater(got, 0)
        finally:
            srv.close()

    def test_jobs_from_dir_skips_existing_png(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.svg").write_text("<svg/>", encoding="utf-8")
            (root / "a.png").write_bytes(b"x")
            (root / "b.svg").write_text("<svg/>", encoding="utf-8")
            jobs = shot.jobs_from_dir(root)
            stems = [s.stem for s, _ in jobs]
            self.assertEqual(stems, ["b"])


class FigurePlanSeedPathTests(unittest.TestCase):
    def test_falls_back_to_svg(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "figure_plan.seed.yaml"
            plan = build_figure_plan_seed(
                view_records=[
                    {
                        "name": "iso",
                        "role": "assembly",
                        "png": "",
                        "svg": str(Path(td) / "iso.svg"),
                    }
                ],
                out_path=out,
                theme_summary="t",
            )
            self.assertTrue(plan["figures"][0]["path"].endswith("iso.svg"))


if __name__ == "__main__":
    unittest.main()
