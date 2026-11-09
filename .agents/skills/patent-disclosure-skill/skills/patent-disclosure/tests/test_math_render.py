# -*- coding: utf-8 -*-
"""math_render 联调（需 matplotlib；无库则跳过）。"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

SHARED_PKG = Path(__file__).resolve().parents[1]
SHARED = SHARED_PKG / "tools"
ROOT = SHARED_PKG.parent.parent if SHARED_PKG.parent.name == "skills" else SHARED_PKG.parent
sys.path.insert(0, str(SHARED))

_SOFTMAX_BLOCK = r"P(z_i) = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}"
_INLINE_COMPLEX = r"\sum_{j=1}^{n} w_j \cdot \exp(z_j / T)"
_INLINE_GE_LE = r"a_{cpu,j} \le 0"
_INLINE_PAREN = r"T_r"
_BLOCK_LOGIC = (
    r"t - t_{last} \ge T_r \quad \land \quad |\sigma_{now} - \sigma_{last}| \ge \Delta s"
)
_SCORE_BLOCK = (
    r"Score(\mathbf{d},\mathbf{p}) = w_{cpu}\cdot d_{cpu}\cdot p_{cpu} + w_{mem}\cdot "
    r"\min\left(1,\frac{p_{mem}}{\max(1,d_{mem})}\right) + w_{io}\cdot(1-p_{io\_busy})\cdot d_{io} "
    r"- \lambda\cdot n_{inflight}\n\tag{1}"
)


class MathRenderTests(unittest.TestCase):
    def test_inline_paren_with_nested_parens(self) -> None:
        """``\\(...\\)`` 内含 ``\\max(...)`` 时须整段匹配，不能露出转义符。"""
        try:
            import matplotlib
        except ImportError:
            self.skipTest("matplotlib not installed")
        from math_render import iter_inline_paren_spans, render_markdown_math

        sample = (
            r"分项：\(Y_{ij}=\min(1,\,A/\max(\varepsilon,b))\)；"
            r"\(Z_{ij}=(1-g)\cdot b\)。"
        )
        spans = iter_inline_paren_spans(sample)
        self.assertEqual(len(spans), 2)
        self.assertIn(r"\max(\varepsilon,b)", spans[0][2])

        out_dir = ROOT / "tmp"
        out_dir.mkdir(parents=True, exist_ok=True)
        new_md, ok, failed = render_markdown_math(
            sample + "\n",
            out_md_path=out_dir / "_math_nested_paren.md",
            assets_rel="_math_nested_paren_figs",
        )
        self.assertGreaterEqual(ok, 2)
        self.assertEqual(failed, 0)
        self.assertIn("公式·行内", new_md)
        self.assertEqual(new_md.count("<!-- ![公式·行内]"), 2)

    def test_block_and_inline(self) -> None:
        try:
            import matplotlib
        except ImportError:
            self.skipTest("matplotlib not installed")
        from math_render import render_markdown_math

        md = (
            f"温度参数 $T$ 下，加权 logits 为 ${_INLINE_COMPLEX}$，"
            f"约束 ${_INLINE_GE_LE}$ 与 \\({_INLINE_PAREN}\\)。\n\n"
            f"$$\n{_SOFTMAX_BLOCK}\n$$\n\n"
            f"$$\n{_BLOCK_LOGIC}\n$$\n\n"
            f"$$\n{_SCORE_BLOCK}\n$$\n"
        )
        render_markdown_math(
            md,
            out_md_path=ROOT / "tmp" / "_math_test_out.md",
            assets_rel="_math_test_figures",
        )

    def test_fallback_on_bad_latex(self) -> None:
        try:
            import matplotlib
        except ImportError:
            self.skipTest("matplotlib not installed")
        from math_render import render_markdown_math

        render_markdown_math(
            "$$\\notacommand{x}$$\n",
            out_md_path=ROOT / "tmp" / "_math_test_bad.md",
            assets_rel="_math_test_figures",
        )


if __name__ == "__main__":
    unittest.main()
