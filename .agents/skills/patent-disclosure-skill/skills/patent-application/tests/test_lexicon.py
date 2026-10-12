# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from lexicon import load_promo_terms, promo_pattern


class LexiconTests(unittest.TestCase):
    def test_default_yaml_has_base_terms(self) -> None:
        terms = load_promo_terms()
        self.assertIn("显著提高", terms)
        self.assertIn("最优", terms)
        self.assertIn("应用前景广阔", terms)
        self.assertTrue(promo_pattern().search("从而显著提高检测精度"))
        self.assertTrue(promo_pattern().search("本方案填补空白且安全可靠"))
        self.assertIsNone(promo_pattern().search("优选地，所述阈值"))
        self.assertIsNone(promo_pattern().search("先进先出队列"))

    def test_custom_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "promo_terms.yaml"
            path.write_text("version: 1\nterms:\n  - 超级棒\n", encoding="utf-8")
            promo_pattern.cache_clear()
            try:
                pattern = promo_pattern(str(path))
                self.assertTrue(pattern.search("本方案超级棒"))
                self.assertIsNone(pattern.search("显著提高"))
            finally:
                promo_pattern.cache_clear()


if __name__ == "__main__":
    unittest.main()
