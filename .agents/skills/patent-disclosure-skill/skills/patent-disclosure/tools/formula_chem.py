# -*- coding: utf-8 -*-
"""化学式 / 反应式：元素符号合法性与简单原子守恒。

仅在范式 tag 含 chemistry，或 LaTeX 含 \\ce{ / 反应箭头 时启用。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

# 常见元素（含专利材料里会出现的）
_ELEMENTS = {
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U",
}

_ARROW = re.compile(
    r"\\longrightarrow|\\rightarrow|\\to\b|→|->|⇒|\\Rightarrow"
)


def latex_looks_chemical(latex: str) -> bool:
    s = latex.replace("\\\\", "\\")
    if r"\ce{" in s:
        return True
    if _ARROW.search(s) and re.search(r"[A-Z][a-z]?\d", s.replace("{", "").replace("}", "")):
        return True
    return False


def _strip_ce(latex: str) -> str:
    s = latex.replace("\\\\", "\\")
    s = re.sub(r"\\tag\s*\{[^}]*\}", "", s)
    m = re.search(r"\\ce\s*\{(.+)\}\s*$", s, re.S)
    if m:
        s = m.group(1)
    s = re.sub(r"\\mathrm\s*\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", s)
    s = s.replace(r"\_", "_")
    s = s.replace("{", "").replace("}", "")
    s = s.replace("_", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _mul(counter: Counter[str], n: int) -> Counter[str]:
    return Counter({k: v * n for k, v in counter.items()})


def parse_formula_atoms(formula: str) -> tuple[Counter[str], list[str]]:
    """解析 H2O、Al2O3、Ca(OH)2。返回 (原子计数, 错误)。"""
    errors: list[str] = []
    s = formula.replace("·", ".").replace("*", ".")
    s = re.sub(r"\s+", "", s)
    if not s:
        return Counter(), ["空化学式"]

    def parse(i: int, end: int) -> tuple[Counter[str], int]:
        acc: Counter[str] = Counter()
        while i < end:
            if s[i] == "(":
                depth = 1
                j = i + 1
                while j < end and depth:
                    if s[j] == "(":
                        depth += 1
                    elif s[j] == ")":
                        depth -= 1
                    j += 1
                inner, _ = parse(i + 1, j - 1)
                k = j
                m = re.match(r"\d+", s[k:end])
                n = int(m.group()) if m else 1
                if m:
                    k += len(m.group())
                acc += _mul(inner, n)
                i = k
                continue
            if s[i] == ".":
                # 水合物：.5H2O
                i += 1
                m = re.match(r"\d+", s[i:end])
                hyd_n = int(m.group()) if m else 1
                if m:
                    i += len(m.group())
                hyd, ni = parse(i, end)
                acc += _mul(hyd, hyd_n)
                return acc, ni
            m = re.match(r"([A-Z][a-z]?)(\d*)", s[i:end])
            if not m:
                errors.append(f"无法解析片段: {s[i:i + 8]!r}")
                break
            el, digits = m.group(1), m.group(2)
            if el not in _ELEMENTS:
                errors.append(f"未知元素符号: {el}")
            n = int(digits) if digits else 1
            acc[el] += n
            i += len(m.group(0))
        return acc, i

    atoms, _ = parse(0, len(s))
    return atoms, errors


def _split_term(term: str) -> tuple[int, str]:
    t = term.strip()
    m = re.match(r"^(\d+(?:\.\d+)?)(.+)$", t)
    if m:
        coef = float(m.group(1))
        if coef == int(coef):
            return int(coef), m.group(2)
        errors_coef = max(1, int(round(coef)))
        return errors_coef, m.group(2)
    return 1, t


def parse_reaction(latex: str) -> tuple[Counter[str], Counter[str], list[str]] | None:
    raw = _strip_ce(latex)
    if not _ARROW.search(raw) and "=" not in raw:
        return None
    if _ARROW.search(raw):
        left, right = _ARROW.split(raw, maxsplit=1)
    else:
        left, right = raw.split("=", maxsplit=1)
    errors: list[str] = []

    def side(text: str) -> Counter[str]:
        tot: Counter[str] = Counter()
        for part in text.split("+"):
            part = part.strip()
            if not part:
                continue
            coef, form = _split_term(part)
            atoms, err = parse_formula_atoms(form)
            errors.extend(err)
            tot += _mul(atoms, coef)
        return tot

    return side(left), side(right), errors


def check_mass_fractions(given: dict[str, Any] | None) -> list[str]:
    """若 given 中有至少两个 w* 质量分数，检查和是否接近 1。"""
    if not isinstance(given, dict):
        return []
    ws: list[float] = []
    for k, v in given.items():
        kn = str(k).lower().replace("\\", "")
        if re.search(r"(^|_)w(_|$)|frac|massfrac", kn) or kn.startswith("w"):
            try:
                ws.append(float(v))
            except (TypeError, ValueError):
                continue
    if len(ws) < 2:
        return []
    s = sum(ws)
    if abs(s - 1.0) > 0.02:
        return [f"质量分数之和为 {s:.4g}，期望约 1"]
    return []


def check_chemistry(
    equations: list[dict[str, Any]],
    *,
    given: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    errors: 原子不守恒或未知元素
    warnings: 质量分数等
    skipped: 未检出反应式
    """
    errors: list[str] = []
    warnings: list[str] = []
    checked = 0
    for i, eq in enumerate(equations):
        if not isinstance(eq, dict):
            continue
        lx = str(eq.get("latex") or "")
        if not force and not latex_looks_chemical(lx):
            continue
        parsed = parse_reaction(lx)
        if parsed is None:
            if r"\ce{" in lx.replace("\\\\", "\\"):
                warnings.append(f"equations[{i}] 含 \\ce 但未识别为反应式（无箭头）")
            continue
        left, right, perr = parsed
        if perr:
            errors.extend(f"equations[{i}] {e}" for e in perr)
        checked += 1
        if left and right and left != right:
            errors.append(
                f"equations[{i}] 原子不守恒：左 {dict(left)} 右 {dict(right)}"
            )
    warnings.extend(check_mass_fractions(given))
    return {
        "checked_reactions": checked,
        "errors": errors,
        "warnings": warnings,
    }
