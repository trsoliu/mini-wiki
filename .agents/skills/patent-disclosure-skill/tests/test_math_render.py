# -*- coding: utf-8 -*-
"""math_render 联调脚本（需 matplotlib；仅跑通渲染，不做断言）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

_SOFTMAX_BLOCK = r"P(z_i) = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}"
_INLINE_COMPLEX = r"\sum_{j=1}^{n} w_j \cdot \exp(z_j / T)"
# 交底书常见、matplotlib 需归一化的简写
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


def test_block_and_inline() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return

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
        out_md_path=ROOT / "tests" / "_math_test_out.md",
        assets_rel="_math_test_figures",
    )


def test_fallback_on_bad_latex() -> None:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return

    from math_render import render_markdown_math

    render_markdown_math(
        "$$\\notacommand{x}$$\n",
        out_md_path=ROOT / "tests" / "_math_test_bad.md",
        assets_rel="_math_test_figures",
    )


if __name__ == "__main__":
    test_block_and_inline()
    test_fallback_on_bad_latex()
    print("ok")
