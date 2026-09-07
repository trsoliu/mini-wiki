# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
if str(PKG / "tools") not in sys.path:
    sys.path.insert(0, str(PKG / "tools"))

from math_to_omml import try_latex_to_omml


class MathToOmmlTests(unittest.TestCase):
    def test_inline_subscript(self) -> None:
        node = try_latex_to_omml(r"s_{ij}", display=False)
        self.assertIsNotNone(node)
        xml = str(node)
        self.assertIn("oMath", xml)

    def test_weighted_sum(self) -> None:
        node = try_latex_to_omml(r"s_{ij}=\alpha x+\beta y+\gamma z-\lambda n_{j}", display=True)
        self.assertIsNotNone(node)


if __name__ == "__main__":
    unittest.main()
