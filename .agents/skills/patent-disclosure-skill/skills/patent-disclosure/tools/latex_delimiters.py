#!/usr/bin/env python
"""扫 Markdown 里「普通括号包住 LaTeX」的行内公式（Word 不会当成公式）。

``md_to_docx.py`` 只认 ``\\(...\\)`` / ``$...$``。写成 ``(M_{\\mathrm{total}})`` 会原样进正文。
Markdown 预览常把 ``\\(`` 显示成 ``(``，写稿时不要据此删反斜杠。

围栏代码块、行内 `` `...` ``，以及已用 ``\\(...\\)`` / ``$...$`` / ``$$...$$`` / ``\\[...\\]``
包住的公式不扫（公式内 ``\\bigl(`` / ``\\max(`` / ``\\left(`` 等合法嵌套不算违规）。

用法：
  python tools/latex_delimiters.py -i disclosure.md
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from stdio_utf8 import ensure_utf8_stdio

# 括号内出现这些命令，几乎可以断定是 LaTeX 而不是中文夹注。
_LATEX_CMD = (
    r"\\(?:mathrm|operatorname|mathbf|mathit|text|frac|sqrt|left|right"
    r"|leq|geq|leqslant|geqslant|le\b|ge\b|cdot|times"
    r"|alpha|beta|gamma|delta|lambda|mu|sigma|omega|varepsilon|varphi"
    r"|sum|prod|int|max|min|tag|quad|qquad|overline|underline"
    r"|,|;|!)"
)

# ``(M_{\mathrm{total}})`` / ``(m_{\mathrm{silica}}=60\,\mathrm{g})``
_BARE_PAREN_CMD = re.compile(
    rf"(?<!\\)\((?=([^()\n]{{0,200}}{_LATEX_CMD}))([^()\n]{{1,200}})\)"
)

# ``(M_{total})``：下标花括号、但还没写成 ``\(``
_BARE_PAREN_SUB = re.compile(r"(?<!\\)\([A-Za-z][A-Za-z0-9]*_\{[^()\n]{0,120}\)")

_INLINE_CODE = re.compile(r"`[^`]*`")
_FENCE_OPEN = re.compile(r"^(```|~~~)")
# 与 math_render._INLINE_RE 同口径；先遮 $$ 后再用，避免吃掉块级定界符。
_INLINE_DOLLAR = re.compile(r"(?<!\$)\$(?!\$)((?:\\.|[^$\n])+?)\$(?!\$)")


@dataclass(frozen=True)
class BareParenHit:
    line: int
    snippet: str


def _blank_spans(text: str, spans: list[tuple[int, int]]) -> str:
    if not spans:
        return text
    buf = list(text)
    for start, end in spans:
        for i in range(start, min(end, len(buf))):
            if buf[i] != "\n":
                buf[i] = " "
    return "".join(buf)


def _fence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    in_fence = False
    fence_start = 0
    pos = 0
    for line in text.splitlines(keepends=True):
        if _FENCE_OPEN.match(line.lstrip()):
            if not in_fence:
                in_fence = True
                fence_start = pos
            else:
                in_fence = False
                spans.append((fence_start, pos + len(line)))
        pos += len(line)
    if in_fence:
        spans.append((fence_start, pos))
    return spans


def _iter_delim_spans(text: str, opener: str, closer: str) -> list[tuple[int, int]]:
    """配对定界符；公式体内允许裸 ``)`` / ``]``，终结符必须是 closer。"""
    spans: list[tuple[int, int]] = []
    i = 0
    n = len(text)
    ol = len(opener)
    cl = len(closer)
    while i < n:
        if text.startswith(opener, i):
            j = i + ol
            while j < n:
                if text.startswith(closer, j):
                    spans.append((i, j + cl))
                    i = j + cl
                    break
                if text[j] == "\\" and j + 1 < n:
                    j += 2
                else:
                    j += 1
            else:
                i += ol
        else:
            i += 1
    return spans


def _mask_inline_code(text: str) -> str:
    return _INLINE_CODE.sub(lambda m: " " * len(m.group(0)), text)


def _mask_protected(md: str) -> str:
    """先遮围栏与行内代码，再遮已合法定界的公式（顺序不可反）。"""
    text = _blank_spans(md, _fence_spans(md))
    text = _mask_inline_code(text)
    text = _blank_spans(text, _iter_delim_spans(text, "$$", "$$"))
    text = _INLINE_DOLLAR.sub(lambda m: " " * len(m.group(0)), text)
    text = _blank_spans(text, _iter_delim_spans(text, "\\[", "\\]"))
    text = _blank_spans(text, _iter_delim_spans(text, "\\(", "\\)"))
    return text


def find_bare_paren_latex(md: str) -> list[BareParenHit]:
    """返回普通括号包 LaTeX 的命中（1-based 行号）。"""
    hits: list[BareParenHit] = []
    source = md or ""
    masked = _mask_protected(source)
    orig_lines = source.splitlines()
    mask_lines = masked.splitlines()
    for i, (raw, line) in enumerate(zip(orig_lines, mask_lines), 1):
        seen: set[tuple[int, int]] = set()
        for cre in (_BARE_PAREN_CMD, _BARE_PAREN_SUB):
            for m in cre.finditer(line):
                span = m.span()
                if span in seen:
                    continue
                seen.add(span)
                snippet = raw[span[0] : span[1]].strip() or m.group(0).strip()
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                hits.append(BareParenHit(line=i, snippet=snippet))
    return hits


def format_hits_report(hits: list[BareParenHit]) -> str:
    n = len(hits)
    lines = [f"LATEX_DELIM: hits={n}"]
    if n:
        lines.append(
            "行内公式须用 \\(...\\) 或 $...$，不要用普通括号包住 \\mathrm / \\, / _{ }。"
            " Markdown 预览里 \\( 看起来像 (，勿删反斜杠。"
            " 改正后须对**当次时间戳定稿 md**重跑 mermaid_render / md_to_docx，"
            " 禁止用未改正的 draft.md 出交付 Word。"
        )
        for h in hits[:20]:
            lines.append(f"  L{h.line}: {h.snippet}")
        if n > 20:
            lines.append(f"  … 另有 {n - 20} 处")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    p = argparse.ArgumentParser(
        description="检查 Markdown 是否把行内 LaTeX 写成了普通括号"
    )
    p.add_argument("-i", "--input", required=True, type=Path)
    args = p.parse_args(argv)
    path = args.input
    if not path.is_file():
        print(f"错误：找不到 {path}", file=sys.stderr)
        return 1
    try:
        md = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        md = path.read_text(encoding="utf-8", errors="replace")
    hits = find_bare_paren_latex(md)
    print(format_hits_report(hits), file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
