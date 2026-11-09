# -*- coding: utf-8 -*-
"""对外两个入口：检索一页结果、读一篇详情。每次调用只发一个请求。"""
from __future__ import annotations

import json

from .client import DEFAULT_TIMEOUT, fetch_text, looks_blocked
from .detail import PatentDetail, parse_detail_html
from .errors import GooglePatentsBadResponse, GooglePatentsBlocked
from .query import SearchQuery, validate_query, xhr_url
from .results import SearchPage, parse_search_json, patent_url


def search(query: SearchQuery, *, timeout: float = DEFAULT_TIMEOUT) -> SearchPage:
    validate_query(query)
    url = xhr_url(query)
    body = fetch_text(url, timeout=timeout, accept="application/json, text/plain, */*")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        if looks_blocked(body):
            raise GooglePatentsBlocked(
                "Google Patents 返回拦截页（自动流量检测），已停止请求", status=200, url=url
            ) from exc
        raise GooglePatentsBadResponse(
            "检索接口没有返回 JSON（接口可能改版）", url=url
        ) from exc
    return parse_search_json(data, num=query.num, page=query.page)


def fetch_detail(
    pub: str, *, lang: str = "en", timeout: float = DEFAULT_TIMEOUT
) -> PatentDetail:
    url = patent_url(pub, lang)
    html_text = fetch_text(url, timeout=timeout)
    detail = parse_detail_html(html_text, pub=pub, url=url)
    if not (detail.claims or detail.abstract or detail.description):
        raise GooglePatentsBadResponse(
            "详情页没有解析到摘要、权利要求或说明书（页面可能改版）", url=url
        )
    return detail
