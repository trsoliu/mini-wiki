# -*- coding: utf-8 -*-
"""Google Patents 访问错误。``reason`` 供调用方写机读前缀。"""
from __future__ import annotations


class GooglePatentsError(RuntimeError):
    reason = "error"

    def __init__(self, message: str, *, status: int | None = None, url: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.url = url


class GooglePatentsBlocked(GooglePatentsError):
    """HTTP 429 / 503 或拦截页：本机 IP 被判为自动流量，须立即停止。"""

    reason = "blocked"


class GooglePatentsNotFound(GooglePatentsError):
    """HTTP 404：Google 未收录该公开号（新公开的通常 1–3 周后才收录）。"""

    reason = "not_found"


class GooglePatentsUnavailable(GooglePatentsError):
    """网络不通、超时或其他 HTTP 错误。"""

    reason = "unavailable"


class GooglePatentsBadResponse(GooglePatentsError):
    """返回内容无法解析（接口或页面改版）。"""

    reason = "bad_response"
