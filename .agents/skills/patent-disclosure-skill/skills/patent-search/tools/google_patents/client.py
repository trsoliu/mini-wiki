# -*- coding: utf-8 -*-
"""单次 HTTP GET：不重试，按状态码与拦截页分类错误。

请求策略：不重试，也不放慢后再试。依据 2026-10 / 11 本机实测（Google 未公布阈值）：
- 脚本请求会触发 Google 自动流量拦截，返回 503 与标准「Sorry…」页，无 ``Retry-After``。
- 拦截看一段时间内的请求总量，不看间隔：间隔 4 秒约 12 次被封，拉到 10 秒约 9 次就被封。
- 封禁是整站的，详情页与 PDF 一起失败；解封时间不定（曾 4 分钟以上未恢复）。
所以只适合小量使用：每次调用一个请求，遇拦截立即结束本轮。
"""
from __future__ import annotations

import socket
import ssl
import urllib.error
import urllib.request

from .errors import (
    GooglePatentsBlocked,
    GooglePatentsNotFound,
    GooglePatentsUnavailable,
)

BASE_URL = "https://patents.google.com"
DEFAULT_TIMEOUT = 20.0
BLOCK_STATUS = frozenset({429, 503})
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)

_SSL_CTX = ssl.create_default_context()
_urlopen = urllib.request.urlopen


def looks_blocked(body: str) -> bool:
    head = (body or "")[:4000].lower()
    return (
        "<title>sorry..." in head
        or "unusual traffic" in head
        or "/sorry/index" in head
    )


def fetch_text(url: str, *, timeout: float = DEFAULT_TIMEOUT, accept: str = "") -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": BASE_URL + "/",
    }
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    try:
        with _urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            final_url = resp.geturl() if hasattr(resp, "geturl") else url
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code in BLOCK_STATUS:
            raise GooglePatentsBlocked(
                f"Google Patents 限流（HTTP {exc.code}），已停止请求", status=exc.code, url=url
            ) from exc
        if exc.code == 404:
            raise GooglePatentsNotFound(
                "Google Patents 未收录（HTTP 404）", status=404, url=url
            ) from exc
        raise GooglePatentsUnavailable(
            f"Google Patents 返回 HTTP {exc.code}", status=exc.code, url=url
        ) from exc
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError) as exc:
        raise GooglePatentsUnavailable(
            f"连不上 Google Patents：{type(exc).__name__}: {exc}", url=url
        ) from exc
    if "/sorry/" in (final_url or "") or looks_blocked(body):
        raise GooglePatentsBlocked(
            "Google Patents 返回拦截页（自动流量检测），已停止请求", status=200, url=url
        )
    return body
