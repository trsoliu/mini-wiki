# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

import browser as browser_mod


class LaunchChromiumTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.environ.pop("PATENT_BROWSER_CHANNEL", None)

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("PATENT_BROWSER_CHANNEL", None)
        else:
            os.environ["PATENT_BROWSER_CHANNEL"] = self._old

    def test_falls_back_chrome_then_edge_then_bundled(self) -> None:
        calls: list[str | None] = []

        class Chromium:
            def launch(self, **kwargs):
                ch = kwargs.get("channel")
                calls.append(ch)
                if ch in ("chrome", "msedge"):
                    raise RuntimeError("missing " + str(ch))
                return MagicMock(name="browser")

        pw = MagicMock()
        pw.chromium = Chromium()
        browser, label = browser_mod.launch_chromium(pw, headless=True)
        self.assertEqual(label, "chromium")
        self.assertEqual(calls, ["chrome", "msedge", None])
        self.assertIsNotNone(browser)

    def test_forced_channel_skips_auto(self) -> None:
        os.environ["PATENT_BROWSER_CHANNEL"] = "msedge"
        calls: list[str | None] = []

        class Chromium:
            def launch(self, **kwargs):
                calls.append(kwargs.get("channel"))
                return MagicMock()

        pw = MagicMock()
        pw.chromium = Chromium()
        _b, label = browser_mod.launch_chromium(pw, headless=True)
        self.assertEqual(label, "msedge")
        self.assertEqual(calls, ["msedge"])


class MermaidFenceTests(unittest.TestCase):
    def test_render_one_inject_writes_comment(self) -> None:
        from mermaid_render import render_markdown_mermaid

        md = "# t\n\n```mermaid\nflowchart LR\n  A-->B\n```\n\nend\n"

        def fake_render(src: str, png: Path) -> None:
            png.parent.mkdir(parents=True, exist_ok=True)
            png.write_bytes(b"\x89PNG\r\n")
            self.assertIn("flowchart", src)

        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "out.md"
            new_md, ok, fail = render_markdown_mermaid(
                md,
                out_md_path=out_path,
                assets_rel="mermaid_figures",
                render_one=fake_render,
            )
        self.assertEqual(ok, 1)
        self.assertEqual(fail, 0)
        self.assertIn("<!-- ![图示 1](mermaid_figures/fig_001.png) -->", new_md)
        self.assertIn("```mermaid", new_md)

    def test_failed_block_keeps_fence(self) -> None:
        from mermaid_render import render_markdown_mermaid

        md = "```mermaid\nflowchart LR\n  A-->B\n```\n"

        def boom(_src: str, _png: Path) -> None:
            raise RuntimeError("nope")

        with tempfile.TemporaryDirectory() as td:
            new_md, ok, fail = render_markdown_mermaid(
                md,
                out_md_path=Path(td) / "out.md",
                assets_rel="mermaid_figures",
                render_one=boom,
            )
        self.assertEqual(ok, 0)
        self.assertEqual(fail, 1)
        self.assertIn("```mermaid", new_md)
        self.assertNotIn("<!-- ![图示", new_md)


if __name__ == "__main__":
    unittest.main()
