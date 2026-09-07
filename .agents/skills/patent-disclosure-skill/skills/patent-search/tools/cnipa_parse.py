# -*- coding: utf-8 -*-
"""
解析 http://epub.cnipa.gov.cn/ 检索结果页 HTML，提取公布公告列表中的标题、公开号、详情链接、摘要（若有）。

解析 http://epub.cnipa.gov.cn/ 检索结果页 HTML。patent-search 独立副本，不依赖交底 crawl。
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

EPUB_BASE = "http://epub.cnipa.gov.cn/"


# IPC 小组：B01J20/26、C08K3/04（可带 (2006.01)I 版本后缀）
_IPC_GROUP_RE = re.compile(r"\b([A-HY]\d{2}[A-Z]\s*\d{1,4}\s*/\s*\d{2,})\b", re.I)
# 洛迦诺：07-01、26-05（只在「分类号」块内提取，避免把 CSS 的 24px 当成 LOC）
_LOC_RE = re.compile(r"\b(\d{2}-\d{2})\b")


@dataclass
class EpubSearchHit:
    """单条检索命中（字段随页面结构尽力解析，可能为空）。"""

    raw_html: str
    title: str | None = None
    pub_number: str | None = None
    application_number: str | None = None
    applicant: str | None = None
    inventors: list[str] | None = None
    filing_date: str | None = None
    publication_date: str | None = None
    link: str | None = None
    abstract: str | None = None
    ipc_codes: list[str] = field(default_factory=list)
    loc_codes: list[str] = field(default_factory=list)


def _html_fragment_to_plain(html_snippet: str) -> str:
    """从一小段 HTML 抽取可读纯文本（用于摘要等）。"""
    t = re.sub(r"<script[^>]*>.*?</script>", "", html_snippet, flags=re.I | re.DOTALL)
    t = re.sub(r"<style[^>]*>.*?</style>", "", t, flags=re.I | re.DOTALL)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s*全部\s*$", "", t).strip()
    return t


def _normalize_ipc(code: str) -> str:
    return re.sub(r"\s+", "", (code or "")).upper()


def _class_chunk_from_html(html: str) -> str:
    """截取「分类号」块纯文本，在「专利代理」之前停。"""
    m = re.search(r"分类号\s*[：:]", html or "", flags=re.I)
    if not m:
        return ""
    chunk = (html or "")[m.start() : m.start() + 2500]
    chunk = re.split(r"专利代理", chunk, maxsplit=1)[0]
    return _html_fragment_to_plain(chunk)


def extract_class_codes_from_html(html: str) -> tuple[list[str], list[str]]:
    """从结果卡片 HTML 抽出 IPC、LOC（公布站「分类号」字段）。"""
    plain = _class_chunk_from_html(html)
    ipc: list[str] = []
    for m in _IPC_GROUP_RE.finditer(plain):
        code = _normalize_ipc(m.group(1))
        if code not in ipc:
            ipc.append(code)
    loc: list[str] = []
    for m in _LOC_RE.finditer(plain):
        code = m.group(1)
        if code not in loc:
            loc.append(code)
    return ipc[:12], loc[:8]


def ipc_search_prefix(code: str) -> str:
    """第二轮用的分类号：B01J20/26 → B01J20（左前缀匹配）。"""
    compact = _normalize_ipc(code)
    m = re.match(r"^([A-HY]\d{2}[A-Z]\d+)", compact, re.I)
    return (m.group(1) if m else compact).upper()


def suggest_class_codes(
    hits: list[EpubSearchHit],
    *,
    patent_type: str = "all",
    limit: int = 3,
) -> tuple[str, list[str]]:
    """从命中汇总 1～3 个第二轮分类号。发明/实用→IPC 前缀；外观→LOC。"""
    from collections import Counter

    kind = "loc" if (patent_type or "").lower() == "design" else "ipc"
    bag: list[str] = []
    for h in hits:
        if kind == "loc":
            bag.extend(h.loc_codes or [])
        else:
            bag.extend(ipc_search_prefix(c) for c in (h.ipc_codes or []) if c)
    if kind == "ipc" and not bag:
        # 外观误用 invention 时仍可能只有 LOC
        for h in hits:
            bag.extend(h.loc_codes or [])
        if bag:
            kind = "loc"
    if kind == "loc" and not bag:
        for h in hits:
            bag.extend(ipc_search_prefix(c) for c in (h.ipc_codes or []) if c)
        if bag:
            kind = "ipc"
    counted = Counter(bag)
    codes = [c for c, _n in counted.most_common(limit)]
    return kind, codes


def select_hits_for_disclosure(
    hits: list[EpubSearchHit],
    *,
    class_prefixes: list[str] | None = None,
    core_terms: list[str] | None = None,
    limit: int = 8,
) -> list[EpubSearchHit]:
    """1.1 选用：分类号重合优先，再用题名/摘要里的核心手段词。"""
    prefixes = [_normalize_ipc(p) for p in (class_prefixes or []) if p]
    if not prefixes:
        prefixes = [c for c in suggest_class_codes(hits)[1]]
    terms = [t.strip().lower() for t in (core_terms or []) if t and t.strip()]
    scored: list[tuple[int, EpubSearchHit]] = []
    for h in hits:
        codes = " ".join((h.ipc_codes or []) + (h.loc_codes or []))
        codes_n = _normalize_ipc(codes).replace("/", "")
        score = 0
        matched_class = False
        for p in prefixes:
            token = p.replace("/", "")
            if token and token in codes_n:
                score += 4
                matched_class = True
                break
        blob = f"{h.title or ''} {h.abstract or ''}".lower()
        for t in terms:
            if t and t in blob:
                score += 2
        if prefixes and not matched_class:
            score -= 2
        scored.append((score, h))
    scored.sort(key=lambda x: (-x[0],))
    picked = [h for s, h in scored if s > 0][:limit]
    if len(picked) < min(3, limit) and scored:
        # 分类号全空时仍给分数最高的几条，避免 1.1 空白
        extra = [h for _s, h in scored if h not in picked]
        picked.extend(extra[: max(0, min(3, limit) - len(picked))])
    return picked[:limit]


def _hit_key(h: EpubSearchHit) -> str:
    return (h.pub_number or h.link or (h.title or "")[:120] or "").strip()


def backfill_hits_for_disclosure(
    primary: list[EpubSearchHit],
    pool: list[EpubSearchHit],
    *,
    class_prefixes: list[str] | None = None,
    core_terms: list[str] | None = None,
    min_keep: int = 4,
    limit: int = 6,
) -> tuple[list[EpubSearchHit], str]:
    """第二轮不足 ``min_keep`` 时，从第一轮池里按同一分类号回补。

    返回 ``(hits, reason)``：``primary_enough`` / ``backfilled`` / ``still_short``。
    不把分类号明显跑题的条目补进来；禁止为凑数编造命中。
    """
    cap = max(min_keep, limit)
    seen: set[str] = set()
    out: list[EpubSearchHit] = []
    for h in primary:
        k = _hit_key(h)
        if k and k not in seen:
            seen.add(k)
            out.append(h)
        if len(out) >= cap:
            return out[:cap], "primary_enough"
    if len(out) >= min_keep:
        return out[:cap], "primary_enough"

    ranked = select_hits_for_disclosure(
        [h for h in pool if _hit_key(h) not in seen],
        class_prefixes=class_prefixes,
        core_terms=core_terms,
        limit=cap,
    )
    prefixes = [_normalize_ipc(p).replace("/", "") for p in (class_prefixes or []) if p]
    added = 0
    for h in ranked:
        k = _hit_key(h)
        if not k or k in seen:
            continue
        if prefixes:
            codes_n = _normalize_ipc(
                " ".join((h.ipc_codes or []) + (h.loc_codes or []))
            ).replace("/", "")
            if not any(p and p in codes_n for p in prefixes):
                continue
        seen.add(k)
        out.append(h)
        added += 1
        if len(out) >= cap:
            break
    if len(out) < min_keep:
        return out[:cap], "still_short"
    if added:
        return out[:cap], "backfilled"
    return out[:cap], "still_short"


def _extract_abstract_from_item_html(item_html: str) -> str | None:
    """从单条 ``div.item`` 内 ``dt`` 摘要对应的 ``dd`` 中抽取全文（含折叠 span）。"""
    m = re.search(
        r'<dt[^>]*>\s*摘要\s*[：:]\s*</dt>\s*<dd[^>]*>(.*?)</dd>',
        item_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    plain = _html_fragment_to_plain(m.group(1))
    return plain if len(plain) >= 4 else None


def _extract_labeled_value(item_html: str, *labels: str) -> str | None:
    """Extract a ``dt``/``dd`` value from the publication-card layout."""
    alternatives = "|".join(re.escape(label) for label in labels)
    m = re.search(
        rf"<dt[^>]*>\s*(?:{alternatives})\s*[：:]?\s*</dt>\s*<dd[^>]*>(.*?)</dd>",
        item_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    value = _html_fragment_to_plain(m.group(1))
    return value or None


_APPLICATION_NUMBER_RE = re.compile(
    r"(?<!\d)(?:CN\s*)?(\d{12}(?:\.[0-9Xx]|[0-9Xx]))(?!\d)",
    re.IGNORECASE,
)


def normalize_application_number(value: str | None) -> str | None:
    """Normalize a Chinese application number to ``YYYY...N.check`` form."""
    if not value:
        return None
    m = _APPLICATION_NUMBER_RE.search(value.strip())
    if not m:
        return None
    number = m.group(1).upper()
    if "." not in number:
        number = f"{number[:-1]}.{number[-1]}"
    return number


def application_number_for_epub_query(value: str | None) -> str | None:
    """公布站高级查询 ``#an``：去掉校验点，连写成 13 位。

    用户常输入 ``201921114883.3``；站点不认带点形式。无法识别时原样去空白返回。
    """
    text = re.sub(r"\s+", "", value or "")
    if not text:
        return None
    normalized = normalize_application_number(text)
    if normalized:
        return normalized.replace(".", "")
    compact = re.sub(r"^CN", "", text, flags=re.IGNORECASE)
    compact = compact.replace(".", "").replace("．", "")
    return compact or None


def _split_people(value: str | None) -> list[str] | None:
    if not value:
        return None
    names = [
        re.sub(r"^全部\s*", "", part.strip())
        for part in re.split(r"[;；,，、]", value)
        if part.strip()
    ]
    return names or None


def parse_reported_total(html: str) -> int | None:
    """Return the result count displayed by CNIPA when the page exposes it."""
    plain = _html_fragment_to_plain(html)
    patterns = (
        r"(?:共|总计|合计)\s*([\d,]+)\s*(?:条|项|件)",
        r"(?:检索结果|查询结果)\s*[：:]?\s*([\d,]+)\s*(?:条|项|件)",
    )
    for pattern in patterns:
        m = re.search(pattern, plain, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    return None


def parse_reported_total_pages(html: str) -> int | None:
    """结果页「共 N 页」（含 ``.page_total`` 里夹着「到第」的写法）。"""
    plain = _html_fragment_to_plain(html)
    match = re.search(r"共\s*([\d,]+)\s*页", plain)
    if not match:
        return None
    pages = int(match.group(1).replace(",", ""))
    return pages if pages > 0 else None


def parse_reported_page_size(html: str) -> int | None:
    """真实每页条数：隐藏域 ``#pageSize`` 或正文「每页 N 条」。"""
    for pattern in (
        r'id=["\']pageSize["\'][^>]*value=["\'](\d+)["\']',
        r'name=["\']pageSize["\'][^>]*value=["\'](\d+)["\']',
        r'value=["\'](\d+)["\'][^>]*(?:id|name)=["\']pageSize["\']',
    ):
        match = re.search(pattern, html or "", flags=re.IGNORECASE)
        if match:
            size = int(match.group(1))
            if size > 0:
                return size
    plain = _html_fragment_to_plain(html)
    match = re.search(r"每页\s*(\d+)\s*条", plain)
    if not match:
        return None
    size = int(match.group(1))
    return size if size > 0 else None


def _abs_url(href: str) -> str:
    if not href or href.lower().startswith(("javascript:", "#")):
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return EPUB_BASE.rstrip("/") + href
    return EPUB_BASE.rstrip("/") + "/" + href.lstrip("/")


def parse_search_result_html(html: str, base_url: str = EPUB_BASE) -> list[EpubSearchHit]:
    """
    解析「公布公告」检索结果列表页 HTML。
    兼容常见表格行 / 带链接的条目（站点改版时需调整正则或选择器）。
    """
    _ = base_url  # 预留与绝对链接拼接策略扩展
    hits: list[EpubSearchHit] = []
    for m in re.finditer(
        r"<tr[^>]*>(.*?)</tr>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        row = m.group(1)
        low = row.lower()
        if "indexquery" in low or "searchstr" in low:
            continue
        cell_html = re.findall(
            r"<td[^>]*>(.*?)</td>", row, flags=re.IGNORECASE | re.DOTALL
        )
        cells = [_html_fragment_to_plain(cell) for cell in cell_html]
        application_index = next(
            (
                index
                for index, cell in enumerate(cells)
                if normalize_application_number(cell)
            ),
            None,
        )
        application_number = (
            normalize_application_number(cells[application_index])
            if application_index is not None
            else None
        )
        applicant = None
        title = None
        if application_index is not None:
            if application_index + 1 < len(cells):
                applicant = cells[application_index + 1] or None
            if application_index + 2 < len(cells):
                title = cells[application_index + 2] or None
        title_m = re.search(r'title="([^"]+)"', row, re.IGNORECASE)
        if not title and title_m:
            title = title_m.group(1).strip()
        link_scope = (
            cell_html[application_index]
            if application_index is not None and application_index < len(cell_html)
            else row
        )
        link_m = re.search(r'href="([^"]+)"', link_scope, re.IGNORECASE)
        href = link_m.group(1).strip() if link_m else None
        link = _abs_url(href) if href else None
        link = link or None
        pub_m = re.search(
            r"(CN\s*\d{9,}[A-Z]\s*|ZL\s*\d{9,}\.\d+)",
            row,
            re.IGNORECASE,
        )
        pub_number = pub_m.group(1).replace(" ", "") if pub_m else None
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row)).strip()
        if not application_number and not pub_number:
            continue
        ipc, loc = extract_class_codes_from_html(row)
        hits.append(
            EpubSearchHit(
                raw_html=row[:2000],
                title=title or (text[:200] if text else None),
                pub_number=pub_number,
                application_number=application_number,
                applicant=applicant,
                link=link,
                ipc_codes=ipc,
                loc_codes=loc,
            )
        )
    seen: set[str] = set()
    out: list[EpubSearchHit] = []
    for h in hits:
        key = h.pub_number or h.application_number or h.title or h.raw_html[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    if out:
        return out
    overview = _parse_overview_card_layout(html)
    if overview:
        return overview
    return _parse_search_result_fallback_links(html)


def _parse_overview_card_layout(html: str) -> list[EpubSearchHit]:
    """
    新版「公布模式」结果页：无表格行，每条为 ``div.item``，题名在 ``h1.title``，
    详情 URL 多在二维码 ``div.qrcode`` 的 ``title="http://epub.../patent/CN…"`` 上；
    摘要位于 ``dt`` 为「摘要」的 ``dd`` 内（含 ``span.alltxt`` 折叠段）。
    """
    low = html.lower()
    if "overview-default" not in low and 'class="item"' not in low:
        return []
    parts = re.split(r'(<div\s+class="item"\s*>)', html, flags=re.IGNORECASE)
    blocks: list[str] = []
    for j in range(1, len(parts) - 1, 2):
        blocks.append(parts[j] + parts[j + 1])
    if not blocks:
        return []

    base = EPUB_BASE.rstrip("/")
    hits: list[EpubSearchHit] = []
    for item_html in blocks:
        tm = re.search(
            r'<h1[^>]*class="[^"]*\btitle\b[^"]*"[^>]*>\s*([^<]+?)\s*</h1>',
            item_html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        title = re.sub(r"\s+", " ", tm.group(1)).strip() if tm else None
        lm = re.search(
            r'title="(https?://epub\.cnipa\.gov\.cn/patent/[^"]+)"',
            item_html,
            flags=re.IGNORECASE,
        )
        link = lm.group(1).strip() if lm else None
        pm = re.search(
            r"(?:申请公布号|授权公告号)[：:]\s*</dt>\s*<dd>([^<]+?)</dd>",
            item_html,
            flags=re.IGNORECASE,
        )
        pub_number = None
        if pm:
            pub_number = pm.group(1).strip().replace(" ", "")
            if not re.match(r"^(?:CN|ZL)", pub_number, re.IGNORECASE):
                pub_number = None
        if not link and pub_number:
            link = f"{base}/patent/{pub_number}"
        if link:
            m_pub = re.search(
                r"/patent/((?:CN|ZL)[^/?#]+)",
                link,
                flags=re.IGNORECASE,
            )
            if m_pub and not pub_number:
                pub_number = m_pub.group(1).strip()
        application_number = normalize_application_number(
            _extract_labeled_value(item_html, "申请号")
        )
        applicant = _extract_labeled_value(
            item_html, "申请人", "专利权人", "申请（专利权）人"
        )
        inventors = _split_people(
            _extract_labeled_value(item_html, "发明人", "设计人")
        )
        filing_date = _extract_labeled_value(item_html, "申请日")
        publication_date = _extract_labeled_value(
            item_html, "申请公布日", "授权公告日", "公开（公告）日"
        )
        abstract = _extract_abstract_from_item_html(item_html)
        ipc, loc = extract_class_codes_from_html(item_html)
        if not title and not pub_number and not link:
            continue
        raw = "|".join(
            x for x in (title, pub_number, link, (abstract or "")[:400]) if x
        )[:2000]
        hits.append(
            EpubSearchHit(
                raw_html=raw,
                title=title,
                pub_number=pub_number,
                application_number=application_number,
                applicant=applicant,
                inventors=inventors,
                filing_date=filing_date,
                publication_date=publication_date,
                link=link,
                abstract=abstract,
                ipc_codes=ipc,
                loc_codes=loc,
            )
        )
    seen: set[str] = set()
    out: list[EpubSearchHit] = []
    for h in hits:
        key = h.pub_number or h.application_number or h.link or (h.title or "")[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def _parse_search_result_fallback_links(html: str) -> list[EpubSearchHit]:
    """从结果页中抽取指向公布详情的 <a href>。"""
    hits: list[EpubSearchHit] = []
    for m in re.finditer(
        r'<a\s+[^>]*href="([^"]+)"[^>]*>([^<]*)</a>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        href = (m.group(1) or "").strip()
        title = (m.group(2) or "").strip()
        if not href.startswith("/") and "epub.cnipa.gov.cn" not in href:
            continue
        hlow = href.lower()
        if not any(
            x in hlow
            for x in ("/dxb/", "/sw/", "/patent/", "detail", "show")
        ):
            continue
        if "indexForm" in href or "javascript:" in href.lower():
            continue
        low = href.lower()
        if "article" in low and "indexquery" in low:
            continue
        link = _abs_url(href)
        pub_m = re.search(r"(CN\s*\d{9,}[A-Z]?|ZL\s*\d{9,}\.\d+)", href + title, re.I)
        pub_number = pub_m.group(1).replace(" ", "") if pub_m else None
        raw = m.group(0)[:2000]
        if len(title) < 2 and not pub_number:
            continue
        ipc, loc = extract_class_codes_from_html(raw)
        hits.append(
            EpubSearchHit(
                raw_html=raw,
                title=title or None,
                pub_number=pub_number,
                link=link,
                ipc_codes=ipc,
                loc_codes=loc,
            )
        )
    seen: set[str] = set()
    out: list[EpubSearchHit] = []
    for h in hits:
        key = h.link or h.title or ""
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def hits_to_jsonable(hits: list[EpubSearchHit]) -> list[dict]:
    """供 JSON 序列化（不含 raw_html 过大字段时可裁剪）。"""
    rows = []
    for h in hits:
        d = asdict(h)
        d.pop("raw_html", None)
        d["ipc_codes"] = list(h.ipc_codes or [])
        d["loc_codes"] = list(h.loc_codes or [])
        rows.append(d)
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python cnipa_epub_parse.py <结果页.html>", file=sys.stderr)
        sys.exit(2)
    p = Path(sys.argv[1]).expanduser().resolve()
    html = p.read_text(encoding="utf-8")
    hits = parse_search_result_html(html)
    print(json.dumps(hits_to_jsonable(hits), ensure_ascii=False, indent=2))
