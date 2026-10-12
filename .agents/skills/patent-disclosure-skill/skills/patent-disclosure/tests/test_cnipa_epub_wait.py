# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools" / "crawl"))
sys.path.insert(0, str(PKG / "tools"))

from cnipa_epub_wait import DEFAULTS, load_wait_config, wait_yaml_path


class WaitConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("EPUB_WAF_MAX_WAIT_SEC", None)
        os.environ.pop("EPUB_WAIT_YAML", None)

    def tearDown(self) -> None:
        os.environ.pop("EPUB_WAF_MAX_WAIT_SEC", None)
        os.environ.pop("EPUB_WAIT_YAML", None)
        load_wait_config(force_reload=True)

    def test_yaml_or_defaults_match_expected_strategy(self) -> None:
        cfg = load_wait_config(force_reload=True)
        self.assertEqual(cfg["goto_timeout_ms"], 30_000)
        self.assertEqual(cfg["goto_wait_until"], "commit")
        self.assertEqual(cfg["gate_poll_sec"], 30.0)
        self.assertEqual(cfg["submit_timeout_ms"], 40_000)
        self.assertEqual(cfg["advanced_max_class_codes"], 1)
        self.assertEqual(cfg["advanced_max_terms"], 1)
        self.assertEqual(cfg["home_max_terms"], 4)
        self.assertNotIn("result_page_size", cfg)
        self.assertTrue(cfg["stop_on_first_nav_failure"])
        self.assertEqual(set(cfg), set(DEFAULTS))

    def test_missing_file_falls_back_to_defaults(self) -> None:
        missing = Path(tempfile.gettempdir()) / "cnipa_epub_wait_missing.yaml"
        if missing.exists():
            missing.unlink()
        os.environ["EPUB_WAIT_YAML"] = str(missing)
        cfg = load_wait_config(force_reload=True)
        self.assertEqual(cfg["goto_timeout_ms"], DEFAULTS["goto_timeout_ms"])
        self.assertEqual(cfg["submit_timeout_ms"], DEFAULTS["submit_timeout_ms"])

    def test_invalid_values_fall_back_per_key(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("goto_timeout_ms: -1\ngoto_wait_until: forever\ngate_poll_sec: 7.5\n")
            path = fh.name
        try:
            os.environ["EPUB_WAIT_YAML"] = path
            cfg = load_wait_config(force_reload=True)
            self.assertEqual(cfg["goto_timeout_ms"], DEFAULTS["goto_timeout_ms"])
            self.assertEqual(cfg["goto_wait_until"], DEFAULTS["goto_wait_until"])
            self.assertEqual(cfg["gate_poll_sec"], 7.5)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_env_overrides_gate_poll(self) -> None:
        os.environ["EPUB_WAF_MAX_WAIT_SEC"] = "12"
        cfg = load_wait_config(force_reload=True)
        self.assertEqual(cfg["gate_poll_sec"], 12.0)

    def test_default_yaml_path_next_to_module(self) -> None:
        self.assertEqual(wait_yaml_path().name, "cnipa_epub_wait.yaml")


if __name__ == "__main__":
    unittest.main()
