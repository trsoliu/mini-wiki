#!/usr/bin/env python
"""LaTeX → 可编辑 Word Office Math（OMML）。

技术路线：``latex2mathml`` 转 MathML，再映射为 ``m:oMath`` / ``m:oMathPara``，
供 ``python-docx`` 挂到段落。不依赖本机 TeX / Word COM。

复杂宏失败时由调用方回退 PNG/原文。

依赖：``pip install latex2mathml``（另需已有 ``python-docx``）。
"""
from __future__ import annotations

import re
from copy import deepcopy
from xml.etree import ElementTree

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

MATHML_NS = "{http://www.w3.org/1998/Math/MathML}"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")

# latex2mathml 不认识的单位/符号宏 → 宋体与 Cambria Math 都有的字符或已知命令
_LATEX_CMD_TO_REPL: tuple[tuple[str, str], ...] = (
    ("perthousand", "‰"),
    ("textcelsius", "℃"),
    ("textfahrenheit", "℉"),
    ("textdegree", "°"),
    ("angstrom", "Å"),
    ("permil", "‰"),
    ("degree", "°"),
    ("micro", "µ"),
    ("ohm", "Ω"),
    ("AA", "Å"),
)

_CIRC_UNIT_PATTERNS: tuple[str, ...] = (
    r"\\mathrm\s*\{\s*\^\s*\{\s*\\circ\s*\}\s*([A-Z])\s*\}",
    r"\\mathrm\s*\{\s*\^\s*\\circ\s*([A-Z])\s*\}",
    r"\^\s*\{\s*\\circ\s*\}\s*\\mathrm\s*\{\s*([A-Z])\s*\}",
    r"\^\s*\\circ\s*\\mathrm\s*\{\s*([A-Z])\s*\}",
    r"\^\s*\{\s*\\circ\s*\}\s*([A-Z])\b",
    r"\^\s*\\circ\s*([A-Z])\b",
)
_CIRC_UNIT_CHARS = {"C": "℃", "F": "℉"}


def _circ_unit_repl(match: re.Match[str]) -> str:
    letter = match.group(1)
    return _CIRC_UNIT_CHARS.get(letter, "°" + letter)


def normalize_latex_for_omml(latex: str) -> str:
    """去掉 Word 公式不友好的外壳，并把缺字符号换成可显示字符。"""
    body = (latex or "").strip()
    if not body:
        return ""
    body = re.sub(r"\\tag\s*\{([^{}]*)\}", r"\\quad (\1)", body)
    body = re.sub(r"\\notag\b", "", body)
    body = re.sub(r"\\label\s*\{[^{}]*\}", "", body)
    body = body.replace("\n", " ")
    body = re.sub(r"[ \t]{2,}", " ", body).strip()
    body = body.replace(r"\le", r"\leq").replace(r"\ge", r"\geq")
    body = body.replace(r"\land", r"\wedge").replace(r"\lor", r"\vee")
    body = re.sub(r"\\(big+|Big+|left|right|bigl|bigr|Bigl|Bigr)\b", "", body)
    for cmd, repl in _LATEX_CMD_TO_REPL:
        body = re.sub(rf"\\{re.escape(cmd)}(?![A-Za-z])", lambda _match, r=repl: r, body)
    for pattern in _CIRC_UNIT_PATTERNS:
        body = re.sub(pattern, _circ_unit_repl, body)
    body = re.sub(r"\^\s*\{\s*\\circ\s*\}", "°", body)
    body = re.sub(r"\^\s*\\circ(?![A-Za-z])", "°", body)
    # 范围「约」：ASCII ~ 在公式里难看，改用波浪算子
    body = re.sub(r"\\sim(?![A-Za-z])", "∼", body)
    return body


def _map_glyphs(text: str, *, in_script: bool) -> str:
    """上标里的 RING OPERATOR 当度数；其它位置留给 Cambria Math。"""
    if not text:
        return ""
    if in_script:
        return text.replace("\u2218", "\u00b0")
    return text


def _element(name: str):
    return OxmlElement(f"m:{name}")


def _text_run(text: str, *, in_script: bool = False):
    text = _map_glyphs(text, in_script=in_script)
    run = _element("r")
    properties = _element("rPr")
    style = _element("sty")
    style.set(qn("m:val"), "p")
    properties.append(style)
    run.append(properties)
    if text and not _CJK_RE.search(text):
        wrpr = OxmlElement("w:rPr")
        rfonts = OxmlElement("w:rFonts")
        for attr in ("ascii", "hAnsi", "cs", "eastAsia"):
            rfonts.set(qn(f"w:{attr}"), "Cambria Math")
        wrpr.append(rfonts)
        run.append(wrpr)
    value = _element("t")
    value.text = text
    run.append(value)
    return run


def _is_empty_math_node(node) -> bool:
    if node is None:
        return True
    if "".join(node.itertext()).strip():
        return False
    children = list(node)
    if not children:
        return True
    return all(_is_empty_math_node(child) for child in children)


def _append_children(target, source, *, in_script: bool = False) -> None:
    if source.text and source.text.strip():
        target.append(_text_run(source.text.strip(), in_script=in_script))
    for child in source:
        _append_mathml(target, child, in_script=in_script)
        if child.tail and child.tail.strip():
            target.append(_text_run(child.tail.strip(), in_script=in_script))


def _script(target, node, kind: str) -> None:
    children = list(node)
    if kind == "sSup" and children and _is_empty_math_node(children[0]):
        if len(children) > 1:
            _append_mathml(target, children[1], in_script=True)
        return

    result = _element(kind)
    expression = _element("e")
    if children:
        _append_mathml(expression, children[0])
    result.append(expression)
    if kind == "sSub":
        sub = _element("sub")
        if len(children) > 1:
            _append_mathml(sub, children[1])
        result.append(sub)
    elif kind == "sSup":
        sup = _element("sup")
        if len(children) > 1:
            _append_mathml(sup, children[1], in_script=True)
        result.append(sup)
    else:
        sub = _element("sub")
        sup = _element("sup")
        if len(children) > 1:
            _append_mathml(sub, children[1])
        if len(children) > 2:
            _append_mathml(sup, children[2], in_script=True)
        result.extend((sub, sup))
    target.append(result)


def _append_mathml(target, node, *, in_script: bool = False) -> None:
    tag = node.tag.removeprefix(MATHML_NS)
    children = list(node)

    if tag in {"math", "mrow", "mstyle", "semantics", "annotation"}:
        _append_children(target, node, in_script=in_script)
    elif tag in {"mi", "mn", "mo", "mtext"}:
        target.append(_text_run("".join(node.itertext()), in_script=in_script))
    elif tag == "mfrac":
        fraction = _element("f")
        numerator = _element("num")
        denominator = _element("den")
        if children:
            _append_mathml(numerator, children[0])
        if len(children) > 1:
            _append_mathml(denominator, children[1])
        fraction.extend((numerator, denominator))
        target.append(fraction)
    elif tag == "msub":
        _script(target, node, "sSub")
    elif tag == "msup":
        _script(target, node, "sSup")
    elif tag in {"msubsup", "munderover"}:
        _script(target, node, "sSubSup")
    elif tag == "munder":
        _script(target, node, "sSub")
    elif tag == "mover":
        _script(target, node, "sSup")
    elif tag == "msqrt":
        radical = _element("rad")
        properties = _element("radPr")
        hide_degree = _element("degHide")
        hide_degree.set(qn("m:val"), "1")
        properties.append(hide_degree)
        degree = _element("deg")
        expression = _element("e")
        _append_children(expression, node)
        radical.extend((properties, degree, expression))
        target.append(radical)
    elif tag == "mroot":
        radical = _element("rad")
        degree = _element("deg")
        expression = _element("e")
        if children:
            _append_mathml(expression, children[0])
        if len(children) > 1:
            _append_mathml(degree, children[1])
        radical.extend((degree, expression))
        target.append(radical)
    elif tag == "mfenced":
        delimiter = _element("d")
        properties = _element("dPr")
        begin = _element("begChr")
        begin.set(qn("m:val"), node.attrib.get("open", "("))
        end = _element("endChr")
        end.set(qn("m:val"), node.attrib.get("close", ")"))
        properties.extend((begin, end))
        expression = _element("e")
        _append_children(expression, node)
        delimiter.extend((properties, expression))
        target.append(delimiter)
    elif tag == "mtable":
        matrix = _element("m")
        for row_node in children:
            row = _element("mr")
            for cell_node in list(row_node):
                cell = _element("e")
                _append_children(cell, cell_node)
                row.append(cell)
            matrix.append(row)
        target.append(matrix)
    elif tag in {"mtr", "mtd"}:
        _append_children(target, node, in_script=in_script)
    elif tag == "mspace":
        target.append(_text_run(" "))
    else:
        _append_children(target, node, in_script=in_script)


def latex_to_omml(latex: str, *, display: bool = True):
    """返回可挂到 ``paragraph._p`` 的 OMML 元素。

    display=True → ``m:oMathPara``（块级）；False → ``m:oMath``（行内）。
    """
    try:
        from latex2mathml.converter import convert
    except ImportError as error:
        raise RuntimeError(
            "原生公式需要 latex2mathml：pip install latex2mathml"
        ) from error

    body = normalize_latex_for_omml(latex)
    if not body:
        raise ValueError("empty latex")

    mathml = ElementTree.fromstring(convert(body))
    math = _element("oMath")
    _append_mathml(math, mathml)
    if display:
        paragraph = _element("oMathPara")
        paragraph.append(math)
        return paragraph
    return math


def try_latex_to_omml(latex: str, *, display: bool = True):
    """成功返回 OMML 元素，失败返回 None（不抛给调用方）。"""
    try:
        return latex_to_omml(latex, display=display)
    except Exception:
        return None


def clone_omml(element):
    return deepcopy(element)


def omml_available() -> bool:
    try:
        import latex2mathml

        return True
    except ImportError:
        return False
