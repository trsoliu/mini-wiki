# -*- coding: utf-8 -*-
"""检索条件 → Google Patents 查询串。

结果接口：``/xhr/query?url=<内层查询串整体编码>&exp=``。
内层只对 ``q`` 的值编码一次；``after`` / ``before`` 里的冒号、``country`` 等列表里的逗号
不得再单独编码（多编码一层会导致 HTTP 500 或 0 条）。
"""
from __future__ import annotations

import calendar
import re
import urllib.parse
from dataclasses import dataclass, field

from .client import BASE_URL

DATE_FIELDS = ("priority", "filing", "publication")
PATENT_TYPES = ("PATENT", "DESIGN")
STATUSES = ("GRANT", "APPLICATION")
SORTS = ("new", "old")
MAX_NUM = 100

_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_LIST_SAFE = ":,"


@dataclass
class SearchQuery:
    keywords: str = ""
    title: str = ""
    abstract: str = ""
    claims: str = ""
    cpc: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    inventors: list[str] = field(default_factory=list)
    countries: list[str] = field(default_factory=list)
    patent_type: str = ""
    status: str = ""
    language: str = ""
    date_field: str = "priority"
    after: str = ""
    before: str = ""
    sort: str = ""
    num: int = 10
    page: int = 0


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _clean_list(values: list[str]) -> list[str]:
    out: list[str] = []
    for raw in values or []:
        for item in str(raw).split(","):
            item = _clean(item)
            if item and item not in out:
                out.append(item)
    return out


def normalize_date(value: str, *, end: bool = False) -> str:
    """``YYYY`` / ``YYYYMM`` / ``YYYY-MM-DD`` / ``YYYYMMDD`` → ``YYYYMMDD``。

    只给年或年月时，``end=False`` 取首日，``end=True`` 取末日。
    """
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if len(digits) == 4:
        return digits + ("1231" if end else "0101")
    if len(digits) == 6:
        year, month = int(digits[:4]), int(digits[4:])
        if not 1 <= month <= 12:
            raise ValueError(f"日期格式无效：{value!r}（月份应为 01–12）")
        last = calendar.monthrange(year, month)[1]
        return digits + (f"{last:02d}" if end else "01")
    if len(digits) == 8:
        return digits
    raise ValueError(f"日期格式无效：{value!r}（用 YYYY、YYYY-MM 或 YYYY-MM-DD）")


def build_q(query: SearchQuery) -> str:
    parts: list[str] = []
    if _clean(query.keywords):
        parts.append(_clean(query.keywords))
    for prefix, value in (("TI", query.title), ("AB", query.abstract), ("CL", query.claims)):
        value = _clean(value)
        if value:
            parts.append(f"{prefix}=({value})")
    codes = [re.sub(r"\s+", "", c) for c in _clean_list(query.cpc)]
    if len(codes) == 1:
        parts.append(f"CPC={codes[0]}")
    elif codes:
        parts.append("(" + " OR ".join(f"CPC={c}" for c in codes) + ")")
    return " ".join(parts)


def validate_query(query: SearchQuery) -> None:
    if not (build_q(query) or _clean_list(query.assignees) or _clean_list(query.inventors)):
        raise ValueError("至少提供关键词 / 名称 / 摘要 / 权要 / CPC / 申请人 / 发明人之一")
    if not 1 <= int(query.num) <= MAX_NUM:
        raise ValueError(f"num 须在 1–{MAX_NUM} 之间")
    if int(query.page) < 0:
        raise ValueError("page 不能为负")
    for code in _clean_list(query.countries):
        if not _COUNTRY_RE.match(code.upper()):
            raise ValueError(f"国别代码无效：{code!r}（两位字母，如 US、EP、WO、JP、KR）")
    if query.patent_type and query.patent_type.upper() not in PATENT_TYPES:
        raise ValueError(f"type 只能是 {' / '.join(PATENT_TYPES)}")
    if query.status and query.status.upper() not in STATUSES:
        raise ValueError(f"status 只能是 {' / '.join(STATUSES)}")
    if query.sort and query.sort.lower() not in SORTS:
        raise ValueError(f"sort 只能是 {' / '.join(SORTS)}")
    if (query.after or query.before) and query.date_field not in DATE_FIELDS:
        raise ValueError(f"日期字段只能是 {' / '.join(DATE_FIELDS)}")
    normalize_date(query.after)
    normalize_date(query.before, end=True)


def query_params(query: SearchQuery) -> list[tuple[str, str]]:
    params: list[tuple[str, str]] = []
    q = build_q(query)
    if q:
        params.append(("q", q))
    assignees = _clean_list(query.assignees)
    if assignees:
        params.append(("assignee", ",".join(assignees)))
    inventors = _clean_list(query.inventors)
    if inventors:
        params.append(("inventor", ",".join(inventors)))
    countries = [c.upper() for c in _clean_list(query.countries)]
    if countries:
        params.append(("country", ",".join(countries)))
    if query.patent_type:
        params.append(("type", query.patent_type.upper()))
    if query.status:
        params.append(("status", query.status.upper()))
    if query.language:
        params.append(("language", query.language.upper()))
    before = normalize_date(query.before, end=True)
    if before:
        params.append(("before", f"{query.date_field}:{before}"))
    after = normalize_date(query.after)
    if after:
        params.append(("after", f"{query.date_field}:{after}"))
    if query.sort:
        params.append(("sort", query.sort.lower()))
    params.append(("num", str(int(query.num))))
    if int(query.page) > 0:
        params.append(("page", str(int(query.page))))
    return params


def inner_query_string(query: SearchQuery) -> str:
    chunks = []
    for key, value in query_params(query):
        safe = "" if key == "q" else _LIST_SAFE
        chunks.append(f"{key}={urllib.parse.quote(value, safe=safe)}")
    return "&".join(chunks)


def xhr_url(query: SearchQuery) -> str:
    inner = inner_query_string(query)
    return f"{BASE_URL}/xhr/query?url={urllib.parse.quote(inner, safe='')}&exp="


def web_url(query: SearchQuery) -> str:
    """同一组条件的网页检索地址（给人打开核对用）。"""
    return f"{BASE_URL}/?{inner_query_string(query)}"
