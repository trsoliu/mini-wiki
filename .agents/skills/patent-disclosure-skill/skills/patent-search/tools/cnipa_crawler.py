# -*- coding: utf-8 -*-
"""公布站高级查询爬虫（patent-search 独立实现，不 import 交底 crawl）。

分页策略：
1. 提交查询后解析**当前结果页**，不要用 AJAX POST 再要第 1 页。
2. 第一页采「共 N 页」与真实每页条数，再排程；翻页仍点「下页」，不要做「到第 N 页」。
3. 回退 fetch 时**保留** ``#searchAfter``（清空会导致公布站 HTTP 400）。
4. 400 退避重试，仍失败则 ``complete=false`` 停止，禁止死循环。
"""
from __future__ import annotations

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from browser import launch_chromium
from cnipa_parse import (
    EpubSearchHit,
    application_number_for_epub_query,
    parse_reported_page_size,
    parse_reported_total,
    parse_reported_total_pages,
    parse_search_result_html,
)
from patent_type import TYPE_ALL, epub_checkbox_states, normalize_patent_type
from search_config import load_search_config, resolve_max_pages, resolve_page_budget

EPUB_BASE = "http://epub.cnipa.gov.cn/"
EPUB_ADVANCED = EPUB_BASE.rstrip("/") + "/Advanced"
EPUB_ADVANCED_CHECKBOX = {
    "fmgb": "isFmgb",
    "fmsq": "isFmsq",
    "xxsq": "isXx",
    "wgsq": "isWg",
}
EPUB_TITLE_RESULT = "专利查询结果展示"
EPUB_TITLE_NO_HIT = "无查询结果"

FIELD_SELECTORS = {
    "class_code": ["#e51"],
    "title": ["#ti"],
    "inventor": ["#e72"],
    "applicant": [
        "#e71_73",
        "input[name='catalogInfo.E71_73']",
        "#pa",
        "#e10",
        "input[name='pa']",
        "input[name='e10']",
    ],
    "application_number": ["#an", "#e21", "input[name='an']", "input[name='catalogInfo.An']"],
    "publication_number": ["#pn", "#e11", "input[name='pn']"],
}

_RESULT_PAGE_READY_JS = """(titles) => {
    const t = document.title.trim();
    if (t === titles.noHit) return true;
    if (t !== titles.result) return false;
    const r = document.querySelector("#result");
    if (!r) return false;
    if (r.querySelector("div.item, h1.title")) return true;
    const html = r.innerHTML;
    if (
        html.includes("无查询结果") ||
        html.includes("没有找到") ||
        html.includes("未检索到") ||
        html.includes("0条")
    ) {
        return true;
    }
    return false;
}"""
_RESULT_FINGERPRINT_JS = """() => {
    const result = document.querySelector("#result");
    const text = result ? result.innerText.replace(/\\s+/g, " ").trim() : "";
    return `${location.href}|${text.slice(0, 2000)}`;
}"""
_RESULT_FINGERPRINT_CHANGED_JS = """(previous) => {
    const result = document.querySelector("#result");
    const text = result ? result.innerText.replace(/\\s+/g, " ").trim() : "";
    return `${location.href}|${text.slice(0, 2000)}` !== previous;
}"""
_CURRENT_PAGE_JS = """() => {
    const el = document.querySelector(".current_page");
    const n = Number.parseInt((el && el.textContent) || "", 10);
    return Number.isFinite(n) ? n : null;
}"""
_PAGE_ADVANCED_JS = """(previous) => {
    const el = document.querySelector(".current_page");
    const n = Number.parseInt((el && el.textContent) || "", 10);
    if (Number.isFinite(n) && previous != null && n !== previous) return true;
    const result = document.querySelector("#result");
    const text = result ? result.innerText.replace(/\\s+/g, " ").trim() : "";
    const fp = `${location.href}|${text.slice(0, 2000)}`;
    return typeof previous === "string" && fp !== previous;
}"""
# 回退用：保留 searchAfter，禁止清空（清空会 400）
_FETCH_RESULT_PAGE_JS = """async ({pageNum, pageSize, timeoutMs}) => {
    const form = document.querySelector("#query_form");
    if (!form) return {ok: false, error: "missing_query_form"};
    const pageNumInput = form.querySelector("#pageNum");
    const pageSizeInput = form.querySelector("#pageSize");
    if (!pageNumInput || !pageSizeInput) {
        return {ok: false, error: "missing_page_fields"};
    }
    pageNumInput.value = String(pageNum);
    pageSizeInput.value = String(pageSize);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(form.action, {
            method: "POST",
            body: new URLSearchParams(new FormData(form)),
            credentials: "same-origin",
            signal: controller.signal,
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
            },
        });
        const text = await response.text();
        const currentText = document.querySelector(".current_page")?.textContent || "";
        const totalText = document.querySelector(".page_total")?.textContent || "";
        const totalMatch = totalText.match(/共\\s*(\\d+)\\s*页/);
        const totalScriptMatch = text.match(/\\btotal_page\\s*=\\s*(\\d+)/i) ||
            text.match(/\\btotalPage\\s*[:=]\\s*(\\d+)/i);
        return {
            ok: response.ok,
            status: response.status,
            text,
            currentPage: Number.parseInt(currentText, 10) || pageNum,
            totalPages: totalMatch ? Number.parseInt(totalMatch[1], 10) :
                (totalScriptMatch ? Number.parseInt(totalScriptMatch[1], 10) : null),
        };
    } catch (error) {
        return {ok: false, error: String(error)};
    } finally {
        clearTimeout(timer);
    }
}"""
_FIND_NEXT_PAGE_JS = """() => {
    const candidates = Array.from(document.querySelectorAll(
        'a.next_page, a[rel="next"], button[rel="next"], a, button, ' +
        'input[type="button"], input[type="submit"], span[onclick], li[onclick]'
    ));
    const disabled = (element) => {
        const own = `${element.className || ""} ${element.getAttribute("aria-disabled") || ""}`.toLowerCase();
        const parent = element.parentElement
            ? `${element.parentElement.className || ""} ${element.parentElement.getAttribute("aria-disabled") || ""}`.toLowerCase()
            : "";
        return element.disabled || element.hasAttribute("disabled") ||
            own.includes("disabled") || parent.includes("disabled") ||
            own.includes("btn_dis") || parent.includes("btn_dis") ||
            own.includes("layui-disabled") || parent.includes("layui-disabled");
    };
    for (const element of candidates) {
        if (disabled(element)) continue;
        const text = (element.innerText || element.value || "").replace(/\\s+/g, "").trim();
        const rel = (element.getAttribute("rel") || "").toLowerCase();
        const title = (element.getAttribute("title") || "").replace(/\\s+/g, "").trim();
        const aria = (element.getAttribute("aria-label") || "").replace(/\\s+/g, "").trim();
        const classes = `${element.className || ""} ${element.parentElement?.className || ""}`.toLowerCase();
        const explicit = rel === "next" || title.includes("下一页") || aria.includes("下一页") ||
            text.startsWith("下一页") || text.startsWith("下页");
        const pagerSymbol = [">", "›", "»"].includes(text);
        const classNext = /(^|[\\s_-])next([\\s_-]|$)/.test(classes);
        if (!explicit && !pagerSymbol && !classNext) continue;
        return {found: true, label: text || title || aria || rel || "next"};
    }
    return {found: false, label: ""};
}"""
_CLICK_NEXT_PAGE_JS = """() => {
    const candidates = Array.from(document.querySelectorAll(
        'a.next_page, a[rel="next"], button[rel="next"], a, button, ' +
        'input[type="button"], input[type="submit"], span[onclick], li[onclick]'
    ));
    const disabled = (element) => {
        const own = `${element.className || ""} ${element.getAttribute("aria-disabled") || ""}`.toLowerCase();
        const parent = element.parentElement
            ? `${element.parentElement.className || ""} ${element.parentElement.getAttribute("aria-disabled") || ""}`.toLowerCase()
            : "";
        return element.disabled || element.hasAttribute("disabled") ||
            own.includes("disabled") || parent.includes("disabled") ||
            own.includes("btn_dis") || parent.includes("btn_dis") ||
            own.includes("layui-disabled") || parent.includes("layui-disabled");
    };
    for (const element of candidates) {
        if (disabled(element)) continue;
        const text = (element.innerText || element.value || "").replace(/\\s+/g, "").trim();
        const rel = (element.getAttribute("rel") || "").toLowerCase();
        const title = (element.getAttribute("title") || "").replace(/\\s+/g, "").trim();
        const aria = (element.getAttribute("aria-label") || "").replace(/\\s+/g, "").trim();
        const classes = `${element.className || ""} ${element.parentElement?.className || ""}`.toLowerCase();
        const explicit = rel === "next" || title.includes("下一页") || aria.includes("下一页") ||
            text.startsWith("下一页") || text.startsWith("下页");
        const pagerSymbol = [">", "›", "»"].includes(text);
        const classNext = /(^|[\\s_-])next([\\s_-]|$)/.test(classes);
        if (!explicit && !pagerSymbol && !classNext) continue;
        element.click();
        return {clicked: true, label: text || title || aria || rel || "next"};
    }
    return {clicked: false, label: ""};
}"""
_PAGER_PLAN_JS = """() => {
    const totalText = (document.querySelector(".page_total")?.textContent || "")
        + "\\n" + (document.body?.innerText || "");
    const pages = /共\\s*([\\d,]+)\\s*页/.exec(totalText);
    const per = /每页\\s*(\\d+)\\s*条/.exec(document.body?.innerText || "");
    const sizeEl = document.querySelector("#pageSize");
    const size = Number.parseInt((sizeEl && sizeEl.value) || (per && per[1]) || "", 10);
    return {
        total_pages: pages ? Number.parseInt(pages[1].replace(/,/g, ""), 10) : null,
        page_size: Number.isFinite(size) && size > 0 ? size : null
    };
}"""
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class PagedSearchResult:
    hits: list[EpubSearchHit]
    pages_scanned: int
    complete: bool
    stop_reason: str
    total_reported: int | None = None
    total_pages: int | None = None
    page_size_actual: int | None = None
    first_page_hit_count: int | None = None
    page_budget: int | None = None
    pages_remaining: int | None = None
    hit_count_estimate: int | None = None
    html_bytes: int = 0
    filled_fields: dict[str, str] | None = None


def _max_wait_sec() -> float:
    return float(os.environ.get("EPUB_WAF_MAX_WAIT_SEC", "180"))


def _headed() -> bool:
    return os.environ.get("PLAYWRIGHT_HEADED", "").strip() in ("1", "true", "yes")


def wait_for_epub_home_ready(page: Page, *, max_wait_sec: float | None = None) -> None:
    limit = max_wait_sec if max_wait_sec is not None else _max_wait_sec()
    page.goto(EPUB_BASE, wait_until="load", timeout=120_000)
    elapsed = 0.0
    step = 3.0
    while elapsed < limit:
        page.wait_for_timeout(int(step * 1000))
        elapsed += step
        if page.query_selector("#searchStr"):
            return
    raise TimeoutError(
        f"{limit}s 内未出现检索框 #searchStr；可增大 EPUB_WAF_MAX_WAIT_SEC 或设置 PLAYWRIGHT_HEADED=1"
    )


def wait_for_epub_advanced_ready(page: Page, *, max_wait_sec: float | None = None) -> None:
    limit = max_wait_sec if max_wait_sec is not None else _max_wait_sec()
    page.goto(EPUB_ADVANCED, wait_until="load", timeout=120_000)
    elapsed = 0.0
    step = 3.0
    while elapsed < limit:
        page.wait_for_timeout(int(step * 1000))
        elapsed += step
        if page.query_selector("#e51") or page.query_selector("#advForm"):
            return
    raise TimeoutError(f"{limit}s 内未出现高级查询页；可增大 EPUB_WAF_MAX_WAIT_SEC")


def _safe_page_content(page: Page, *, max_attempts: int = 10) -> str:
    last_err: Exception | None = None
    for i in range(max_attempts):
        try:
            return page.content()
        except Error as e:
            msg = str(e).lower()
            last_err = e
            if "navigating" not in msg and "changing" not in msg:
                raise
            try:
                page.wait_for_load_state("load", timeout=20_000)
            except Exception:
                pass
            page.wait_for_timeout(400 + 200 * i)
    if last_err:
        raise last_err
    raise RuntimeError("_safe_page_content: 未返回内容")


def _wait_result_page_ready(page: Page) -> None:
    page.wait_for_function(
        _RESULT_PAGE_READY_JS,
        arg={"result": EPUB_TITLE_RESULT, "noHit": EPUB_TITLE_NO_HIT},
        timeout=120_000,
    )


def _hit_key(hit: EpubSearchHit) -> str:
    return (
        hit.pub_number
        or hit.application_number
        or hit.link
        or (hit.title or "")[:120]
        or hit.raw_html[:120]
    )


def _merge_hits(target: list[EpubSearchHit], incoming: list[EpubSearchHit]) -> None:
    seen = {_hit_key(hit) for hit in target}
    for hit in incoming:
        key = _hit_key(hit)
        if key in seen:
            continue
        seen.add(key)
        target.append(hit)


def apply_epub_advanced_type_filter(page: Page, patent_type: str = TYPE_ALL) -> None:
    states = epub_checkbox_states(patent_type)
    for home_id, want in states.items():
        cid = EPUB_ADVANCED_CHECKBOX.get(home_id)
        if not cid:
            continue
        box = page.query_selector(f"#{cid}")
        if not box:
            continue
        try:
            if want:
                box.check(force=True)
            else:
                box.uncheck(force=True)
        except Error:
            page.evaluate(
                """({id, checked}) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    el.checked = checked;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('click', { bubbles: true }));
                }""",
                {"id": cid, "checked": want},
            )


def apply_epub_advanced_catalog_filter(page: Page, catalog_id: str) -> None:
    if catalog_id not in EPUB_ADVANCED_CHECKBOX:
        raise ValueError(f"unknown CNIPA publication catalog: {catalog_id}")
    for home_id, advanced_id in EPUB_ADVANCED_CHECKBOX.items():
        box = page.query_selector(f"#{advanced_id}")
        if not box:
            raise RuntimeError(f"CNIPA advanced-search checkbox missing: #{advanced_id}")
        want = home_id == catalog_id
        try:
            if want:
                box.check(force=True)
            else:
                box.uncheck(force=True)
        except Error:
            page.evaluate(
                """({id, checked}) => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    el.checked = checked;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                {"id": advanced_id, "checked": want},
            )


def fill_advanced_field(page: Page, field: str, value: str | None) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    for selector in FIELD_SELECTORS.get(field, []):
        if page.query_selector(selector):
            page.fill(selector, text)
            return True
    return False


def _adapt_advanced_fields(fields: dict[str, str]) -> dict[str, str]:
    adapted: dict[str, str] = {}
    for field, value in fields.items():
        text = (value or "").strip()
        if not text:
            continue
        if field == "application_number":
            text = application_number_for_epub_query(text) or text
        adapted[field] = text
    return adapted


def submit_advanced_query(page: Page, fields: dict[str, str], *, patent_type: str = TYPE_ALL) -> dict[str, str]:
    apply_epub_advanced_type_filter(page, patent_type)
    fields = _adapt_advanced_fields(fields)
    filled: dict[str, str] = {}
    for field, value in fields.items():
        if fill_advanced_field(page, field, value):
            filled[field] = value
    if not filled:
        raise ValueError("advanced search needs at least one filled field")
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with page.expect_navigation(timeout=120_000, wait_until="commit"):
                btn = page.locator("#advForm button[onclick*='adv_Query']")
                if btn.count():
                    btn.first.click()
                else:
                    form = page.query_selector("#advForm")
                    if form is None:
                        raise RuntimeError("高级查询未找到 #advForm")
                    submit_btn = form.query_selector("button")
                    if submit_btn is None:
                        raise RuntimeError("高级查询未找到提交按钮")
                    submit_btn.click()
            _wait_result_page_ready(page)
            return filled
        except (Error, PlaywrightTimeoutError) as exc:
            last_error = exc
            if page.title().strip() in (EPUB_TITLE_RESULT, EPUB_TITLE_NO_HIT):
                try:
                    _wait_result_page_ready(page)
                    return filled
                except (Error, PlaywrightTimeoutError):
                    pass
            page.wait_for_timeout(1_000 * (attempt + 1))
    if last_error:
        raise last_error
    raise RuntimeError("CNIPA advanced search did not start")


def submit_advanced_inventor_search(page: Page, inventor: str, *, catalog_id: str | None = None) -> dict[str, str]:
    if catalog_id:
        apply_epub_advanced_catalog_filter(page, catalog_id)
        if not fill_advanced_field(page, "inventor", inventor):
            raise RuntimeError("CNIPA advanced-search inventor field #e72 missing")
        with page.expect_navigation(timeout=120_000, wait_until="commit"):
            page.locator("#advForm button[onclick*='adv_Query']").click()
        _wait_result_page_ready(page)
        return {"inventor": inventor.strip()}
    return submit_advanced_query(page, {"inventor": inventor}, patent_type=TYPE_ALL)


def has_next_result_page(page: Page) -> bool:
    found = page.evaluate(_FIND_NEXT_PAGE_JS)
    return bool(found and found.get("found"))


def _fetch_next_fragment(
    page: Page,
    *,
    page_num: int,
    page_size: int,
    retries: int,
    backoff_ms: int,
) -> tuple[dict | None, str | None]:
    last_error = None
    for attempt in range(max(1, retries + 1)):
        result = page.evaluate(
            _FETCH_RESULT_PAGE_JS,
            {"pageNum": page_num, "pageSize": page_size, "timeoutMs": 30_000},
        )
        status = result.get("status")
        if status == 400 or str(result.get("error") or "").find("400") >= 0:
            last_error = "http_400"
            page.wait_for_timeout(backoff_ms * (attempt + 1))
            continue
        if result.get("ok") and result.get("text"):
            return result, None
        last_error = str(result.get("error") or f"http_{status}")
        page.wait_for_timeout(backoff_ms * (attempt + 1))
    return None, last_error


def advance_to_next_result_page(
    page: Page,
    *,
    next_page_num: int | None = None,
    page_size: int = 3,
    retries: int = 2,
    backoff_ms: int = 1500,
) -> str:
    """Advance one result page; return advanced / last_page / stalled / http_400."""
    previous_page = page.evaluate(_CURRENT_PAGE_JS)
    previous = previous_page if previous_page is not None else page.evaluate(
        _RESULT_FINGERPRINT_JS
    )
    clicked = page.evaluate(_CLICK_NEXT_PAGE_JS)
    if clicked and clicked.get("clicked"):
        try:
            page.wait_for_function(
                _PAGE_ADVANCED_JS,
                arg=previous,
                timeout=120_000,
            )
            _wait_result_page_ready(page)
            return "advanced"
        except (PlaywrightTimeoutError, Error):
            try:
                page.wait_for_load_state("domcontentloaded", timeout=20_000)
            except Exception:
                pass
            try:
                changed = page.evaluate(_PAGE_ADVANCED_JS, previous)
            except Exception:
                changed = False
            if changed is True:
                try:
                    _wait_result_page_ready(page)
                except (PlaywrightTimeoutError, Error):
                    pass
                return "advanced"
    if next_page_num is None or not page.query_selector("#query_form"):
        if clicked and clicked.get("clicked"):
            return "stalled"
        return "last_page"
    result, error = _fetch_next_fragment(
        page,
        page_num=next_page_num,
        page_size=page_size,
        retries=retries,
        backoff_ms=backoff_ms,
    )
    if error == "http_400":
        return "http_400"
    if result is None:
        return "stalled"
    html = str(result.get("text") or "")
    if not html.strip():
        return "stalled"
    page.evaluate(
        """(html) => {
            const result = document.querySelector("#result");
            if (result) {
                result.innerHTML = html;
                return;
            }
            document.body.insertAdjacentHTML("beforeend", html);
        }""",
        html,
    )
    return "advanced"


def _read_pager_plan(page: Page, html: str) -> tuple[int | None, int | None]:
    total_pages = parse_reported_total_pages(html)
    page_size = parse_reported_page_size(html)
    try:
        info = page.evaluate(_PAGER_PLAN_JS)
    except Exception:
        info = None
    if isinstance(info, dict):
        raw_pages = info.get("total_pages")
        raw_size = info.get("page_size")
        try:
            if raw_pages is not None and int(raw_pages) > 0:
                total_pages = int(raw_pages)
        except (TypeError, ValueError):
            pass
        try:
            if raw_size is not None and int(raw_size) > 0:
                page_size = int(raw_size)
        except (TypeError, ValueError):
            pass
    return total_pages, page_size


def _hit_count_estimate(
    *,
    total_pages: int | None,
    page_size_actual: int | None,
    pages_scanned: int,
    hit_count: int,
    complete: bool,
) -> int | None:
    if complete or (total_pages and pages_scanned >= total_pages):
        return hit_count
    if total_pages and page_size_actual and total_pages > 1:
        return (total_pages - 1) * page_size_actual
    return None


def _finish_pages(
    *,
    hits: list[EpubSearchHit],
    pages_scanned: int,
    complete: bool,
    stop_reason: str,
    total_reported: int | None,
    total_pages: int | None,
    page_size_actual: int | None,
    first_page_hit_count: int | None,
    page_budget: int | None,
    html_bytes: int,
) -> PagedSearchResult:
    remaining = None
    if total_pages is not None:
        remaining = max(0, total_pages - pages_scanned)
    return PagedSearchResult(
        hits=hits,
        pages_scanned=pages_scanned,
        complete=complete,
        stop_reason=stop_reason,
        total_reported=total_reported,
        total_pages=total_pages,
        page_size_actual=page_size_actual,
        first_page_hit_count=first_page_hit_count,
        page_budget=page_budget,
        pages_remaining=remaining,
        hit_count_estimate=_hit_count_estimate(
            total_pages=total_pages,
            page_size_actual=page_size_actual,
            pages_scanned=pages_scanned,
            hit_count=len(hits),
            complete=complete,
        ),
        html_bytes=html_bytes,
    )


def collect_result_pages(
    page: Page,
    *,
    max_pages: int,
    want_complete: bool = False,
    cfg: dict | None = None,
) -> PagedSearchResult:
    settings = cfg or load_search_config()
    fallback_size = int(settings.get("page_size") or 3)
    delay_ms = int(settings["page_delay_ms"])
    retries = int(settings["http_error_retries"])
    backoff_ms = int(settings["http_error_backoff_ms"])

    if page.title().strip() == EPUB_TITLE_NO_HIT:
        return _finish_pages(
            hits=[],
            pages_scanned=1,
            complete=True,
            stop_reason="last_page",
            total_reported=0,
            total_pages=0,
            page_size_actual=fallback_size,
            first_page_hit_count=0,
            page_budget=1,
            html_bytes=0,
        )

    hits: list[EpubSearchHit] = []
    fingerprints: set[str] = set()
    pages_scanned = 0
    total_reported = None
    total_pages: int | None = None
    page_size_actual: int | None = None
    first_page_hit_count: int | None = None
    page_budget = max(1, int(max_pages))
    html_bytes = 0

    while True:
        html = _safe_page_content(page)
        html_bytes += len(html)
        digest = hashlib.sha256(html.encode("utf-8", errors="replace")).hexdigest()
        if digest in fingerprints:
            return _finish_pages(
                hits=hits,
                pages_scanned=pages_scanned,
                complete=False,
                stop_reason="repeated_page",
                total_reported=total_reported,
                total_pages=total_pages,
                page_size_actual=page_size_actual,
                first_page_hit_count=first_page_hit_count,
                page_budget=page_budget,
                html_bytes=html_bytes,
            )
        fingerprints.add(digest)
        pages_scanned += 1
        if total_reported is None:
            total_reported = parse_reported_total(html)
        if pages_scanned == 1:
            total_pages, page_size_actual = _read_pager_plan(page, html)
            if page_size_actual is None:
                page_size_actual = fallback_size
            page_budget = resolve_page_budget(
                requested=None if want_complete else max_pages,
                want_complete=want_complete,
                total_pages=total_pages,
                cfg=settings,
            )
        _merge_hits(hits, parse_search_result_html(html))
        if pages_scanned == 1:
            first_page_hit_count = len(hits)

        if pages_scanned >= page_budget:
            has_next = has_next_result_page(page)
            reached_total = bool(total_pages and pages_scanned >= total_pages)
            if not has_next or reached_total:
                return _finish_pages(
                    hits=hits,
                    pages_scanned=pages_scanned,
                    complete=True,
                    stop_reason="last_page",
                    total_reported=total_reported,
                    total_pages=total_pages,
                    page_size_actual=page_size_actual,
                    first_page_hit_count=first_page_hit_count,
                    page_budget=page_budget,
                    html_bytes=html_bytes,
                )
            stop = "max_pages_hard" if want_complete and total_pages is None else "max_pages"
            return _finish_pages(
                hits=hits,
                pages_scanned=pages_scanned,
                complete=False,
                stop_reason=stop,
                total_reported=total_reported,
                total_pages=total_pages,
                page_size_actual=page_size_actual,
                first_page_hit_count=first_page_hit_count,
                page_budget=page_budget,
                html_bytes=html_bytes,
            )

        status = advance_to_next_result_page(
            page,
            next_page_num=pages_scanned + 1,
            page_size=page_size_actual or fallback_size,
            retries=retries,
            backoff_ms=backoff_ms,
        )
        if status == "last_page":
            return _finish_pages(
                hits=hits,
                pages_scanned=pages_scanned,
                complete=True,
                stop_reason=status,
                total_reported=total_reported,
                total_pages=total_pages,
                page_size_actual=page_size_actual,
                first_page_hit_count=first_page_hit_count,
                page_budget=page_budget,
                html_bytes=html_bytes,
            )
        if status in ("stalled", "http_400"):
            return _finish_pages(
                hits=hits,
                pages_scanned=pages_scanned,
                complete=False,
                stop_reason=status,
                total_reported=total_reported,
                total_pages=total_pages,
                page_size_actual=page_size_actual,
                first_page_hit_count=first_page_hit_count,
                page_budget=page_budget,
                html_bytes=html_bytes,
            )
        page.wait_for_timeout(delay_ms)


def _launch_browser(p: Playwright) -> Browser:
    browser, _label = launch_chromium(p, headless=not _headed())
    return browser


def _new_context(browser: Browser) -> BrowserContext:
    if sys.platform == "darwin":
        platform_token = "Macintosh; Intel Mac OS X 10_15_7"
    elif sys.platform.startswith("linux"):
        platform_token = "X11; Linux x86_64"
    else:
        platform_token = "Windows NT 10.0; Win64; x64"
    user_agent = DEFAULT_USER_AGENT.replace("Windows NT 10.0; Win64; x64", platform_token)
    return browser.new_context(
        user_agent=user_agent,
        locale="zh-CN",
        viewport={"width": 1280, "height": 900},
    )


def search_advanced(
    fields: dict[str, str],
    *,
    patent_type: str = TYPE_ALL,
    max_pages: int | None = None,
    want_complete: bool = False,
    playwright_factory: Callable[[], Playwright] | None = None,
    cfg: dict | None = None,
) -> PagedSearchResult:
    settings = cfg or load_search_config()
    page_limit = resolve_max_pages(
        requested=max_pages,
        want_complete=want_complete,
        cfg=settings,
    )
    patent_type = normalize_patent_type(patent_type, default=TYPE_ALL)
    pw_gen = playwright_factory or sync_playwright
    with pw_gen() as p:
        browser = _launch_browser(p)
        context = _new_context(browser)
        try:
            page = context.new_page()
            wait_for_epub_home_ready(page)
            wait_for_epub_advanced_ready(page)
            filled = submit_advanced_query(page, fields, patent_type=patent_type)
            result = collect_result_pages(
                page,
                max_pages=page_limit,
                want_complete=want_complete,
                cfg=settings,
            )
            result.filled_fields = filled
            return result
        finally:
            context.close()
            browser.close()
