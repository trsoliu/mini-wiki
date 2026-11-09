# -*- coding: utf-8 -*-
"""Google Patents 检索与详情页读取（无需 key）。

本目录在 ``skills/patent-search/tools/`` 与 ``skills/patent-reader/tools/`` 各有一份，
两份文件内容必须逐字一致：改一处须同步拷贝到另一处。

请求纪律：不重试。遇 HTTP 429 / 503 或 Google「Sorry…」拦截页即抛
``GooglePatentsBlocked``，调用方应立即结束本轮，不要换参数或换源继续请求。

    from google_patents import SearchQuery, search, fetch_detail

    page = search(SearchQuery(keywords="(battery) (thermal runaway)", countries=["US", "JP"]))
    detail = fetch_detail("US11450918B2")
"""
from __future__ import annotations

from .api import fetch_detail, search
from .detail import Claim, PatentDetail, parse_detail_html
from .errors import (
    GooglePatentsBadResponse,
    GooglePatentsBlocked,
    GooglePatentsError,
    GooglePatentsNotFound,
    GooglePatentsUnavailable,
)
from .query import (
    DATE_FIELDS,
    SearchQuery,
    build_q,
    inner_query_string,
    normalize_date,
    validate_query,
    web_url,
    xhr_url,
)
from .results import (
    SearchHit,
    SearchPage,
    parse_search_json,
    patent_url,
    split_publication_number,
)

__all__ = [
    "Claim",
    "DATE_FIELDS",
    "GooglePatentsBadResponse",
    "GooglePatentsBlocked",
    "GooglePatentsError",
    "GooglePatentsNotFound",
    "GooglePatentsUnavailable",
    "PatentDetail",
    "SearchHit",
    "SearchPage",
    "SearchQuery",
    "build_q",
    "fetch_detail",
    "inner_query_string",
    "normalize_date",
    "parse_detail_html",
    "parse_search_json",
    "patent_url",
    "search",
    "split_publication_number",
    "validate_query",
    "web_url",
    "xhr_url",
]
