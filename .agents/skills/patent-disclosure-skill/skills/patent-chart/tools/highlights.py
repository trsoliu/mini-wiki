# -*- coding: utf-8 -*-
"""跨列同色标注：权要短语与对照摘录共用同一色号（术语可以不同）。"""
from __future__ import annotations

import re
from typing import Any

# 图例/对应片段：高亮色号用于加粗彩色字（Excel）；bg 给 HTML 底纹
PALETTE: list[dict[str, str]] = [
    {"id": "H1", "bg": "BFDBFE", "fg": "2563EB", "name": "蓝"},
    {"id": "H2", "bg": "A5F3FC", "fg": "0891B2", "name": "青"},
    {"id": "H3", "bg": "FED7AA", "fg": "EA580C", "name": "橙"},
    {"id": "H4", "bg": "BBF7D0", "fg": "16A34A", "name": "绿"},
    {"id": "H5", "bg": "FECDD3", "fg": "E11D48", "name": "玫红"},
    {"id": "H6", "bg": "FEF08A", "fg": "CA8A04", "name": "黄"},
    {"id": "H7", "bg": "DDD6FE", "fg": "7C3AED", "name": "紫"},
    {"id": "H8", "bg": "FECACA", "fg": "DC2626", "name": "红"},
]
# 须与 xlsx_minimal._styles_xml 中新增的 8 个 cellXf 起点一致
HIGHLIGHT_XF_BASE = 23

_CJK = r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]"
_CJK_PUNCT = r"[，。、；：！？,.．]"

STRENGTH_ZH = {"强": "很强", "中": "中等", "弱": "偏弱", "无": "未见"}
SKIP_CHARS = set("的和或及与在将把被所述一种该其并或，。、；：,. ;:()（）[]【】")


def palette_by_id() -> dict[str, dict[str, str]]:
    return {item["id"]: item for item in PALETTE}


def palette_index(hid: str) -> int:
    key = (hid or "H1").split("_")[0]
    for i, item in enumerate(PALETTE):
        if item["id"] == key:
            return i
    return 0


def highlight_style(hid: str) -> int:
    return HIGHLIGHT_XF_BASE + palette_index(hid)


def strength_label(token: str) -> str:
    return STRENGTH_ZH.get(token or "无", "未见")


def tidy_cjk_wrap(text: str) -> str:
    """PDF/OCR 换行常在汉字之间留下空格，如「皮肤固定 座」→「皮肤固定座」。"""
    if not text:
        return text
    out = text.replace("\u00a0", " ")
    prev = None
    while prev != out:
        prev = out
        out = re.sub(rf"({_CJK})[ \t\r\n]+({_CJK})", r"\1\2", out)
        out = re.sub(rf"({_CJK})[ \t\r\n]+({_CJK_PUNCT})", r"\1\2", out)
        out = re.sub(rf"({_CJK_PUNCT})[ \t\r\n]+({_CJK})", r"\1\2", out)
    return out


_ANALYSIS_SPLIT = re.compile(r"(?=(?:对应|差别|依据|覆盖|未记载|备注)[：:])")


def format_analysis(text: str) -> str:
    """对应说明按「对应 / 差别 / 依据」分行；一段写成一行也能拆开。"""
    raw = (text or "").strip()
    if not raw:
        return raw
    parts = [p.strip() for p in _ANALYSIS_SPLIT.split(raw) if p and p.strip()]
    if len(parts) >= 2:
        return "\n".join(tidy_cjk_wrap(p) for p in parts)
    lines = [tidy_cjk_wrap(ln.strip()) for ln in re.split(r"[\r\n]+", raw) if ln.strip()]
    return "\n".join(lines) if lines else tidy_cjk_wrap(raw)


def _clean_needle(text: str) -> str:
    return tidy_cjk_wrap((text or "").strip())


def _ok_span(text: str) -> bool:
    s = _clean_needle(text)
    if len(s) < 2:
        return False
    if all(ch in SKIP_CHARS or ch.isspace() for ch in s):
        return False
    return True


def _first_span(haystack: str, needle: str) -> tuple[int, int] | None:
    if not haystack or not needle:
        return None
    idx = haystack.find(needle)
    if idx < 0:
        return None
    return idx, idx + len(needle)


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return not (a[1] <= b[0] or b[1] <= a[0])


def normalize_highlights(raw: list[Any] | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for i, item in enumerate(raw or []):
        if not isinstance(item, dict):
            continue
        hid = str(item.get("id") or "").strip() or PALETTE[i % len(PALETTE)]["id"]
        if hid in seen:
            hid = f"{hid}_{i}"
        seen.add(hid)
        color = palette_by_id().get(hid.split("_")[0], PALETTE[i % len(PALETTE)])
        out.append(
            {
                "id": hid,
                "label": str(item.get("label") or item.get("claim") or hid).strip(),
                "claim": _clean_needle(str(item.get("claim") or item.get("label") or "")),
                "evidence": _clean_needle(
                    str(item.get("evidence") or item.get("quote") or item.get("claim") or "")
                ),
                "bg": str(item.get("bg") or color["bg"]).replace("#", ""),
                "fg": str(item.get("fg") or color["fg"]).replace("#", ""),
            }
        )
    return out


def infer_highlights(claim: str, quote: str, start_index: int = 0) -> list[dict[str, str]]:
    """仅在未手写 highlights 时：抽出两边共有的最长短语。术语不同的对应靠 Agent 写 id。"""
    claim = claim or ""
    quote = quote or ""
    if not claim or not quote:
        return []
    used_c: list[tuple[int, int]] = []
    used_q: list[tuple[int, int]] = []
    found: list[dict[str, str]] = []
    max_n = min(16, len(claim), len(quote))
    for n in range(max_n, 1, -1):
        if len(found) >= 6:
            break
        for i in range(0, len(claim) - n + 1):
            sub = claim[i : i + n]
            if not _ok_span(sub):
                continue
            c_span = (i, i + n)
            if any(_overlaps(c_span, u) for u in used_c):
                continue
            q_span = _first_span(quote, sub)
            if q_span is None:
                continue
            if any(_overlaps(q_span, u) for u in used_q):
                continue
            color = PALETTE[(start_index + len(found)) % len(PALETTE)]
            found.append(
                {
                    "id": color["id"] if color["id"] not in {h["id"] for h in found} else f"{color['id']}_{len(found)}",
                    "label": sub,
                    "claim": sub,
                    "evidence": sub,
                    "bg": color["bg"],
                    "fg": color["fg"],
                }
            )
            used_c.append(c_span)
            used_q.append(q_span)
            if len(found) >= 6:
                break
    return found


def ensure_highlights(chart: dict[str, Any]) -> dict[str, Any]:
    given = normalize_highlights(chart.get("highlights"))
    if given:
        chart["highlights"] = given
        return chart
    merged: list[dict[str, str]] = []
    cmap = {}
    for cell in chart.get("cells") or []:
        cmap[(cell.get("feature_id"), cell.get("column_id"))] = cell
    for feat in chart.get("features") or []:
        for col in chart.get("columns") or []:
            cell = cmap.get((feat.get("feature_id"), col.get("id"))) or {}
            quote = str(cell.get("quote") or "")
            extra = infer_highlights(str(feat.get("text") or ""), quote, start_index=len(merged))
            for item in extra:
                if any(item["claim"] == old["claim"] and item["evidence"] == old["evidence"] for old in merged):
                    continue
                merged.append(item)
    chart["highlights"] = merged
    return chart


def _apply_spans(text: str, needles: list[tuple[str, str]]) -> list[tuple[str, str | None]]:
    """needles: (highlight_id, substring). 返回 (片段, hid|None)。"""
    text = text or ""
    if not text or not needles:
        return [(text, None)] if text else []
    occupied: list[tuple[int, int, str]] = []
    for hid, needle in needles:
        if not needle:
            continue
        start = 0
        while True:
            idx = text.find(needle, start)
            if idx < 0:
                break
            span = (idx, idx + len(needle), hid)
            if not any(_overlaps((span[0], span[1]), (a, b)) for a, b, _ in occupied):
                occupied.append(span)
                break
            start = idx + 1
    occupied.sort(key=lambda x: x[0])
    runs: list[tuple[str, str | None]] = []
    cursor = 0
    for a, b, hid in occupied:
        if a > cursor:
            runs.append((text[cursor:a], None))
        runs.append((text[a:b], hid))
        cursor = b
    if cursor < len(text):
        runs.append((text[cursor:], None))
    return runs or [(text, None)]


def claim_needles(highlights: list[dict[str, str]]) -> list[tuple[str, str]]:
    return [(h["id"], h["claim"]) for h in highlights if h.get("claim")]


def evidence_needles(highlights: list[dict[str, str]]) -> list[tuple[str, str]]:
    return [(h["id"], h["evidence"]) for h in highlights if h.get("evidence")]


def paint_runs(text: str, highlights: list[dict[str, str]], *, side: str) -> list[tuple[str, str | None]]:
    needles = claim_needles(highlights) if side == "claim" else evidence_needles(highlights)
    return _apply_spans(text, needles)


def _esc_html(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def runs_to_html(runs: list[tuple[str, str | None]], highlights: list[dict[str, str]]) -> str:
    colors = {h["id"]: h for h in highlights}
    parts: list[str] = []
    for chunk, hid in runs:
        if not chunk:
            continue
        body = _esc_html(chunk)
        if not hid or hid not in colors:
            parts.append(body)
            continue
        h = colors[hid]
        parts.append(
            f'<mark class="hl" data-hl="{_esc_html(hid)}" '
            f'style="background:#{h["bg"]};color:#1A1A1A;padding:0 .12em;border-radius:2px;">'
            f"{body}</mark>"
        )
    return "".join(parts)


def paint_html(text: str, highlights: list[dict[str, str]], *, side: str) -> str:
    return runs_to_html(paint_runs(text, highlights, side=side), highlights)


def runs_to_xlsx(runs: list[tuple[str, str | None]], highlights: list[dict[str, str]]) -> list[tuple[str, str | None]]:
    """对应片段：高亮色加粗。Excel 无法做局部底纹。"""
    colors = {h["id"]: h for h in highlights}
    out: list[tuple[str, str | None]] = []
    for chunk, hid in runs:
        if not chunk:
            continue
        rgb = None
        if hid:
            h = colors.get(hid)
            if h is None:
                key = hid.split("_")[0]
                h = next((item for item in highlights if item["id"].split("_")[0] == key), None)
            if h and h.get("fg"):
                rgb = "FF" + str(h["fg"]).replace("#", "")
        out.append((chunk, rgb))
    return out


_CLIP_BREAKS = set("，。；、；,.;!?！？：:")
_CLIP_RADIUS = 28
_CLIP_MAX = 120


def clip_needles(cell: dict[str, Any] | None, highlights: list[dict[str, str]] | None) -> list[str]:
    """对照表截取窗口用的短语：对应用语优先，再 covered。"""
    out: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        text = tidy_cjk_wrap(str(text or "").strip())
        if len(text) >= 2 and text not in seen:
            seen.add(text)
            out.append(text)

    for item in highlights or []:
        add(item.get("evidence") or "")
    for text in (cell.get("covered") or [] if cell else []):
        add(text)
    for item in highlights or []:
        add(item.get("claim") or "")
    return out


def _snap_clip(quote: str, start: int, end: int) -> tuple[int, int]:
    for i in range(start, max(-1, start - 10), -1):
        if i < len(quote) and quote[i] in _CLIP_BREAKS:
            start = i + 1
            break
    for i in range(end, min(len(quote), end + 10)):
        if quote[i] in _CLIP_BREAKS:
            end = i + 1
            break
    return start, end


def clip_quote(
    quote: str,
    needles: list[str] | None = None,
    *,
    radius: int = _CLIP_RADIUS,
    max_len: int = _CLIP_MAX,
) -> str:
    """按对应短语截一小段，避免整段独权复述铺进对照表。"""
    quote = quote or ""
    if not quote:
        return ""
    if len(quote) <= max_len:
        return quote
    primary: tuple[int, int] | None = None
    for needle in needles or []:
        needle = tidy_cjk_wrap((needle or "").strip())
        if len(needle) < 2:
            continue
        idx = quote.find(needle)
        if idx >= 0:
            primary = (idx, idx + len(needle))
            break
    if primary is None:
        chunk = quote[: max_len]
        if len(quote) > max_len:
            chunk = chunk.rstrip("，。、；,.; ") + "…"
        return chunk
    a, b = primary
    lo = max(0, a - radius)
    hi = min(len(quote), b + radius)
    near = radius * 2
    for needle in needles or []:
        needle = tidy_cjk_wrap((needle or "").strip())
        if len(needle) < 2:
            continue
        idx = quote.find(needle)
        if idx < 0:
            continue
        if idx >= a - near and idx + len(needle) <= b + near:
            lo = min(lo, idx)
            hi = max(hi, idx + len(needle))
    lo, hi = _snap_clip(quote, lo, hi)
    chunk = quote[lo:hi].strip()
    if lo > 0:
        chunk = "…" + chunk
    if hi < len(quote):
        chunk = chunk + "…"
    if len(chunk) > max_len:
        keep = max_len - 1
        inner = chunk[1:] if chunk.startswith("…") else chunk
        inner = inner[:keep].rstrip("，。、；,.; ") + "…"
        chunk = ("…" if chunk.startswith("…") else "") + inner
        if not chunk.startswith("…") and lo > 0:
            chunk = "…" + chunk
    return chunk
