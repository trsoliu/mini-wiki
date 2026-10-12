# -*- coding: utf-8 -*-
"""受限代算：只允许 + - * / min max 与简单分式，禁止任意代码。

认不出的式子返回 skip（警告、改手算），不算失败。
"""
from __future__ import annotations

import ast
import math
import re
from typing import Any

_GREEK = (
    (r"\varepsilon", "varepsilon"),
    (r"\epsilon", "epsilon"),
    (r"\lambda", "lambda"),
    (r"\alpha", "alpha"),
    (r"\beta", "beta"),
    (r"\gamma", "gamma"),
    (r"\delta", "delta"),
    (r"\sigma", "sigma"),
    (r"\omega", "omega"),
    (r"\rho", "rho"),
    (r"\tau", "tau"),
    (r"\eta", "eta"),
    (r"\mu", "mu"),
    (r"\pi", "pi"),
    (r"\phi", "phi"),
    (r"\theta", "theta"),
    (r"\kappa", "kappa"),
)

_SKIP_PATTERNS = (
    r"\\sum",
    r"\\prod",
    r"\\arg",
    r"\\begin\{cases\}",
    r"\\lVert",
    r"\\rVert",
    r"\\\|",
    r"\\cdotp",  # keep
    r"\\ce\{",
    r"\\rightarrow",
    r"\\to\b",
    r"\\geqslant",
    r"\\leqslant",
    r"\\leq",
    r"\\geq",
    r"\\neq",
    r"\\in\b",
    r"\\forall",
    r"\\exists",
    r"Q_\{",
    r"\^\{?\\mathrm\{norm",
    r"e\^",
    r"\\exp",
    r"\\ln",
    r"\\log",
    r"\\sin",
    r"\\cos",
    r"\\leftarrow",
    r";",
)

_ALLOWED_AST = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
    ast.Pow,  # only if introduced by mistake we reject below
    ast.Tuple,
    ast.List,
)


def _norm_key(raw: str) -> str:
    s = str(raw).strip().strip("$")
    s = s.replace("\\\\", "\\")
    for latex, name in _GREEK:
        s = s.replace(latex, name)
    s = re.sub(r"\\mathrm\s*\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", s)
    s = s.replace("{", "").replace("}", "").replace("\\", "")
    s = re.sub(r"[^A-Za-z0-9]+", "_", s)
    return s.strip("_").lower()


def _to_float(v: Any) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip())
        except ValueError:
            return None
    return None


def given_map(given: dict[str, Any] | None) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(given, dict):
        return out
    for k, v in given.items():
        n = _to_float(v)
        if n is None:
            continue
        out[_norm_key(k)] = n
    return out


def _split_assignment(latex: str) -> tuple[str, str] | None:
    s = latex.strip()
    if not s:
        return None
    s = re.sub(r"\\tag\s*\{[^}]*\}", "", s)
    parts = re.split(r"(?<![<>!])=(?!=)", s, maxsplit=1)
    if len(parts) != 2:
        return None
    lhs, rhs = parts[0].strip(), parts[1].strip()
    if not lhs or not rhs:
        return None
    if re.search(r"[<>]=?", lhs) or re.search(r"[<>]=?", rhs):
        return None
    return lhs, rhs


def _should_skip(latex: str) -> str | None:
    blob = latex.replace("\\\\", "\\")
    for pat in _SKIP_PATTERNS:
        if re.search(pat, blob):
            return f"含无法受限代算的结构（{pat}）"
    if "\\|" in blob or blob.count("|") >= 2:
        return "含范数/绝对值竖线，跳过代算"
    return None


def _replace_frac(s: str) -> str:
    """反复展开 \\frac{a}{b} → ((a)/(b))。"""
    frac = re.compile(r"\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}")
    prev = None
    while prev != s:
        prev = s
        s = frac.sub(r"(( \1 )/( \2 ))", s)
    return s


def _latex_ops_to_python(s: str) -> str:
    s = _replace_frac(s)
    s = s.replace("\\cdot", "*").replace("\\times", "*").replace("\\div", "/")
    s = re.sub(r"\\(?:left|right|big|Big|bigg|Bigg)\s*", "", s)
    s = re.sub(r"\\(?:,|;|!|quad|qquad)\s*", " ", s)
    s = s.replace("~", " ")
    s = re.sub(r"\\min\s*", " min ", s)
    s = re.sub(r"\\max\s*", " max ", s)
    s = re.sub(r"\\mathrm\s*\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\text\s*\{([^}]*)\}", r"\1", s)
    for latex, name in _GREEK:
        s = s.replace(latex, f" {name} ")
    s = s.replace("{", "(").replace("}", ")")
    s = s.replace("\\", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = _insert_implicit_mul(s)
    return s


def _insert_implicit_mul(s: str) -> str:
    s = re.sub(r"\b(min|max)\s*\(", r"\1(", s)
    s = re.sub(r"([A-Za-z0-9._\)])\s+([A-Za-z_])", r"\1 * \2", s)
    s = re.sub(r"([0-9.\)])\s*\(", r"\1 * (", s)
    s = re.sub(r"\b(min|max)\s*\*\s*\(", r"\1(", s)
    return s


def _subst_names(expr: str, values: dict[str, float]) -> tuple[str, list[str]]:
    """按规范化名最长优先替换为数字。"""
    unresolved: list[str] = []
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    # 下标形式 b_i_cpu 可能已被 ops 处理成 b_i_cpu
    names = sorted(set(tokens), key=len, reverse=True)
    out = expr
    for name in names:
        if name in ("min", "max"):
            continue
        key = name.lower()
        if key in values:
            out = re.sub(rf"\b{re.escape(name)}\b", repr(values[key]), out)
        else:
            unresolved.append(name)
    return out, unresolved


def _ast_allowed(node: ast.AST) -> bool:
    if not isinstance(node, _ALLOWED_AST):
        return False
    if isinstance(node, ast.Pow):
        return False
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in ("min", "max"):
            return False
        if node.keywords:
            return False
    if isinstance(node, ast.Name) and node.id not in ("min", "max"):
        return False
    for child in ast.iter_child_nodes(node):
        if not _ast_allowed(child):
            return False
    return True


def eval_rhs(rhs_latex: str, values: dict[str, float]) -> tuple[float | None, str | None]:
    """成功返回 (value, None)；失败返回 (None, reason)。reason 以 skip: 开头表示应警告。"""
    py = _latex_ops_to_python(rhs_latex)
    py, unresolved = _subst_names(py, values)
    if unresolved:
        return None, "skip: 未绑定符号 " + ", ".join(unresolved[:8])
    if re.search(r"[A-Za-z_]", re.sub(r"\b(min|max)\b", "", py)):
        return None, "skip: 代换后仍含标识符"
    if not re.fullmatch(r"[\d\s+\-*/().,eEminax]+", py.replace("min", "").replace("max", " ")):
        # 粗过滤后再 AST
        pass
    try:
        tree = ast.parse(py, mode="eval")
    except SyntaxError as exc:
        return None, f"skip: 无法解析为算术式 ({exc})"
    if not _ast_allowed(tree):
        return None, "skip: 含不允许的运算（仅 + - * / min max）"
    try:
        val = eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, {"min": min, "max": max})
    except Exception as exc:
        return None, f"skip: 求值失败 ({exc})"
    if not isinstance(val, (int, float)) or not math.isfinite(float(val)):
        return None, "skip: 结果非有限数"
    return float(val), None


def close_enough(got: float, expected: float, rel: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    scale = max(abs(expected), abs(got), 1e-12)
    return abs(got - expected) <= max(abs_tol, rel * scale)


def eval_equation(
    latex: str,
    given: dict[str, Any] | None,
    result: dict[str, Any] | None,
    *,
    rel: float = 1e-6,
) -> dict[str, Any]:
    """
    status: ok | mismatch | skip
    """
    skip = _should_skip(latex)
    if skip:
        return {"status": "skip", "reason": skip}
    parts = _split_assignment(latex)
    if not parts:
        return {"status": "skip", "reason": "不是单一赋值式 lhs = rhs"}
    lhs, rhs = parts
    values = given_map(given)
    if not values:
        return {"status": "skip", "reason": "numeric_example.given 无可用数字"}
    got, err = eval_rhs(rhs, values)
    if err:
        status = "skip" if err.startswith("skip:") else "mismatch"
        return {"status": status, "reason": err, "lhs": lhs}
    expected_map = given_map(result) if isinstance(result, dict) else {}
    lhs_key = _norm_key(lhs)
    if lhs_key not in expected_map:
        if len(expected_map) == 1:
            expected = next(iter(expected_map.values()))
        else:
            return {
                "status": "skip",
                "reason": f"result 中无与左端 {_norm_key(lhs)} 对应的键",
                "lhs": lhs,
                "got": got,
            }
    else:
        expected = expected_map[lhs_key]
    if close_enough(got, expected, rel=rel):
        return {"status": "ok", "lhs": lhs, "got": got, "expected": expected}
    return {
        "status": "mismatch",
        "reason": f"代算 {got} 与 result {expected} 不符（rel={rel}）",
        "lhs": lhs,
        "got": got,
        "expected": expected,
    }
