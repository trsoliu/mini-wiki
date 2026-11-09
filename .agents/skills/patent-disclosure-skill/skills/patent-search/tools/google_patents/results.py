# -*- coding: utf-8 -*-
"""解析 ``/xhr/query`` 返回的 JSON。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .client import BASE_URL
from .errors import GooglePatentsBadResponse
from .html_text import strip_tags

PDF_HOST = "https://patentimages.storage.googleapis.com/"

_PUB_RE = re.compile(r"^([A-Z]{2})(.+?)([A-Z]\d?)?$")


@dataclass
class SearchHit:
    publication_number: str
    country: str
    kind: str
    title: str
    snippet: str
    assignee: str
    inventor: str
    priority_date: str
    filing_date: str
    publication_date: str
    grant_date: str
    language: str
    pdf_url: str
    url: str
    family_countries: list[str] = field(default_factory=list)


@dataclass
class SearchPage:
    total_results: int | None
    total_pages: int | None
    page: int
    num: int
    hits: list[SearchHit]


def split_publication_number(pub: str) -> tuple[str, str, str]:
    """``US11450918B2`` → ``("US", "11450918", "B2")``；无法识别时国别为空。"""
    p = re.sub(r"\s+", "", pub or "").upper()
    m = _PUB_RE.match(p)
    if not m:
        return "", p, ""
    return m.group(1), m.group(2), m.group(3) or ""


def patent_url(pub: str, lang: str = "en") -> str:
    p = re.sub(r"\s+", "", pub or "").upper()
    return f"{BASE_URL}/patent/{p}/{lang}" if lang else f"{BASE_URL}/patent/{p}"


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _family_countries(meta: Any) -> list[str]:
    try:
        rows = meta["aggregated"]["country_status"]
    except (KeyError, TypeError):
        return []
    out: list[str] = []
    for row in rows or []:
        code = str((row or {}).get("country_code") or "").strip().upper()
        if code and code not in out:
            out.append(code)
    return out


def parse_search_json(data: Any, *, num: int, page: int) -> SearchPage:
    if not isinstance(data, dict) or not isinstance(data.get("results"), dict):
        raise GooglePatentsBadResponse("检索结果 JSON 缺少 results 字段（接口可能改版）")
    results = data["results"]
    hits: list[SearchHit] = []
    for cluster in results.get("cluster") or []:
        for item in (cluster or {}).get("result") or []:
            pat = (item or {}).get("patent") or {}
            number = str(pat.get("publication_number") or "").strip().upper()
            if not number:
                continue
            country, _digits, kind = split_publication_number(number)
            pdf = str(pat.get("pdf") or "").strip()
            hits.append(
                SearchHit(
                    publication_number=number,
                    country=country,
                    kind=kind,
                    title=strip_tags(str(pat.get("title") or "")),
                    snippet=strip_tags(str(pat.get("snippet") or "")),
                    assignee=strip_tags(str(pat.get("assignee") or "")),
                    inventor=strip_tags(str(pat.get("inventor") or "")),
                    priority_date=str(pat.get("priority_date") or ""),
                    filing_date=str(pat.get("filing_date") or ""),
                    publication_date=str(pat.get("publication_date") or ""),
                    grant_date=str(pat.get("grant_date") or ""),
                    language=str(pat.get("language") or ""),
                    pdf_url=(PDF_HOST + pdf.lstrip("/")) if pdf else "",
                    url=patent_url(number),
                    family_countries=_family_countries(pat.get("family_metadata")),
                )
            )
    return SearchPage(
        total_results=_int_or_none(results.get("total_num_results")),
        total_pages=_int_or_none(results.get("total_num_pages")),
        page=int(page),
        num=int(num),
        hits=hits,
    )
