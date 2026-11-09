# -*- coding: utf-8 -*-
"""
公布站检索 **路径 B：整页导航提交**（``cnipa_epub_crawler.py`` 的兜底实现）。

本模块是原 ``cnipa_epub_crawler.py`` 的检索逻辑原样迁出，行为不变：
``page.fill`` 写检索框 → 对 ``#indexForm`` / ``#advForm`` 提交 → **整页导航** →
等结果页 ``<title>`` 与 ``#result`` DOM 就绪 → ``page.content()`` 取 HTML。

-------------------------------------------------------------------------------
与路径 A（``cnipa_epub_crawler.py`` 内的 fetch 快路径）的分工
-------------------------------------------------------------------------------
- **路径 A（默认）**：同一会话内用 ``fetch`` POST 表单，只取 HTML 文本。实测每词
  **0.3–0.5 秒**。
- **路径 B（本模块）**：整页导航，浏览器要额外加载结果页的 CSS/JS/图片等资源，
  实测每词 **约 20 秒**；但它走的是站点的常规交互路径，兼容性最好。

本模块因此保留为兜底：路径 A 被站点改版、``fetch`` 被拦截或返回非结果页时，
``cnipa_epub_crawler`` 会自动回退到这里，不影响既有行为。

**高级查询（分类号 + 名称）目前只走本模块**：其表单字段与提交端点未经 fetch 实测，
第二轮收口默认 1×1，一次导航的耗时可接受，不值得为此冒改版风险。

-------------------------------------------------------------------------------
本模块只提供**原子操作**，不含整轮循环
-------------------------------------------------------------------------------
整轮循环（多词、失败处理、回退选择）留在 ``cnipa_epub_crawler.search_epub_keywords``，
以便该模块的名字可被测试 patch。本模块只负责单跳的 gate / 提交 / 取 HTML。

等待参数：同目录 ``cnipa_epub_wait.yaml``（``EPUB_WAIT_YAML`` 可改路径），缺文件回退
``cnipa_epub_wait.DEFAULTS``；``EPUB_WAF_MAX_WAIT_SEC`` 若已设置则覆盖 ``gate_poll_sec``。
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
)

_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from browser import browser_user_agent, launch_chromium
from patent_type import TYPE_ALL, epub_checkbox_states
from cnipa_epub_wait import EpubNavError, load_wait_config, progress


EPUB_BASE = "http://epub.cnipa.gov.cn/"
EPUB_ADVANCED = EPUB_BASE.rstrip("/") + "/Advanced"
# 高级查询页 checkbox（与首页 #fmgb 等不同）
EPUB_ADVANCED_CHECKBOX = {
    "fmgb": "isFmgb",
    "fmsq": "isFmsq",
    "xxsq": "isXx",
    "wgsq": "isWg",
}
# 国知局 /Dxb/IndexQuery 结果页 <title>；改版时须同步单测与 _RESULT_PAGE_READY_JS
EPUB_TITLE_RESULT = "专利查询结果展示"
EPUB_TITLE_NO_HIT = "无查询结果"
# 在浏览器内判断结果页可解析：title + #result DOM（列表或零结果文案）
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


def _cfg() -> dict:
    return load_wait_config()


def _page_url(page: Page) -> str:
    try:
        return str(page.url or "")
    except Exception:
        return ""


def _nav_hint(*, advanced: bool) -> str:
    return "keep_round1" if advanced else "skip_epub"


def _goto(page: Page, url: str, *, advanced: bool) -> None:
    cfg = _cfg()
    timeout_ms = int(cfg["goto_timeout_ms"])
    wait_until = str(cfg["goto_wait_until"])
    progress(f"stage=goto wait_until={wait_until} timeout_ms={timeout_ms} url={url}")
    try:
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
    except (PlaywrightTimeoutError, Error) as exc:
        raise EpubNavError(
            "goto",
            hint=_nav_hint(advanced=advanced),
            message="打开公布站页面超时或失败",
            timeout_s=timeout_ms / 1000.0,
            url=url,
        ) from exc


def _wait_selector(
    page: Page,
    selector: str,
    *,
    advanced: bool,
    max_wait_sec: float | None = None,
) -> None:
    cfg = _cfg()
    limit = float(max_wait_sec) if max_wait_sec is not None else float(cfg["gate_poll_sec"])
    step = float(cfg["gate_poll_step_sec"])
    progress(f"stage=gate selector={selector} timeout_s={limit:g}")
    deadline = time.monotonic() + limit
    while True:
        try:
            if page.query_selector(selector):
                return
        except Error:
            pass
        if time.monotonic() >= deadline:
            raise EpubNavError(
                "gate",
                hint=_nav_hint(advanced=advanced),
                message=f"页面已打开但未出现 {selector}",
                timeout_s=limit,
                url=_page_url(page),
            )
        remaining = deadline - time.monotonic()
        page.wait_for_timeout(int(min(step, max(remaining, 0.05)) * 1000))


def _headed() -> bool:
    return os.environ.get("PLAYWRIGHT_HEADED", "").strip() in ("1", "true", "yes")


def default_result_html_path() -> Path:
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    return Path(__file__).resolve().parent / f"_last_result_{ts}.html"


def wait_for_epub_home_ready(page: Page, *, max_wait_sec: float | None = None) -> None:
    if page.query_selector("#searchStr"):
        return
    _goto(page, EPUB_BASE, advanced=False)
    _wait_selector(page, "#searchStr", advanced=False, max_wait_sec=max_wait_sec)
    _settle_after_load(page)


def open_epub_advanced_search(page: Page) -> None:
    """Open CNIPA's fielded search after the browser session passed the home gate."""
    _goto(page, EPUB_ADVANCED, advanced=True)
    _wait_selector(page, "#advForm #e72", advanced=True)
    _settle_after_load(page)


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


def _wait_result_page_ready(page: Page, *, advanced: bool = False) -> None:
    """等结果页 title 与 #result 列表/零结果 DOM 就绪（不等完整 load）。"""
    timeout_ms = int(_cfg()["submit_timeout_ms"])
    progress(f"stage=submit timeout_ms={timeout_ms}")
    try:
        page.wait_for_function(
            _RESULT_PAGE_READY_JS,
            arg={"result": EPUB_TITLE_RESULT, "noHit": EPUB_TITLE_NO_HIT},
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError as exc:
        raise EpubNavError(
            "submit",
            hint=_nav_hint(advanced=advanced),
            message="提交后未出现结果页（有结果或明确0条）",
            timeout_s=timeout_ms / 1000.0,
            url=_page_url(page),
        ) from exc


def apply_epub_type_filter(page: Page, patent_type: str = TYPE_ALL) -> None:
    """按类型勾选首页 #fmgb/#fmsq/#xxsq/#wgsq（与截图四类一致）。"""
    states = epub_checkbox_states(patent_type)
    for cid, want in states.items():
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


def apply_epub_advanced_type_filter(page: Page, patent_type: str = TYPE_ALL) -> None:
    """高级查询页勾选 #isFmgb / #isFmsq / #isXx / #isWg。"""
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


def wait_for_epub_advanced_ready(page: Page, *, max_wait_sec: float | None = None) -> None:
    """打开 /Advanced，等到分类号框 #e51。框已在则不重新 goto。"""
    if page.query_selector("#e51"):
        return
    _goto(page, EPUB_ADVANCED, advanced=True)
    _wait_selector(page, "#e51", advanced=True, max_wait_sec=max_wait_sec)
    _settle_after_load(page)


#: 公布模式每页条数。检索接口固定回 3 条，只能在结果页用站点自己的「每页N条」下拉框切换：
#: 防护脚本会给页面发出的 PageQuery XHR 加签名，脚本自己发的 fetch/XHR 没有签名会被挂住。
EPUB_PAGE_SIZE = 10
_PAGE_SIZE_RESPONSE_TIMEOUT_MS = 20_000
_PAGE_SIZE_RENDER_TIMEOUT_MS = 10_000
_RESULT_PAGER_JS = """() => {
    const m = document.documentElement.innerHTML.match(/total_item:\\s*(\\d+)/);
    return {
        items: document.querySelectorAll('#result div.item').length,
        total: m ? Number.parseInt(m[1], 10) : null,
        size: (document.querySelector('#pageSize') || {}).value || '',
    };
}"""

#: 点击后等查询请求发出的上限（毫秒）。
_SUBMIT_SENT_TIMEOUT_MS = 20_000
_PAGE_LOADED_TIMEOUT_MS = 15_000
_PAGE_LOADED_JS = "() => document.readyState === 'complete'"
#: 放行后检索框一出现就提交会被回 400：页面加载完成后再静置这么久（毫秒）才提交。
_PAGE_SETTLE_MS = 2_000


def _is_query_request(request) -> bool:
    try:
        return (
            request.resource_type == "document"
            and request.method == "POST"
            and "/Dxb/" in request.url
        )
    except Error:
        return False


def _is_query_document(response) -> bool:
    try:
        return _is_query_request(response.request)
    except Error:
        return False


def _wait_page_loaded(page: Page) -> None:
    try:
        page.wait_for_function(_PAGE_LOADED_JS, timeout=_PAGE_LOADED_TIMEOUT_MS)
    except (PlaywrightTimeoutError, Error):
        pass


def _settle_after_load(page: Page) -> None:
    _wait_page_loaded(page)
    page.wait_for_timeout(_PAGE_SETTLE_MS)


def _submit_and_check(page: Page, click, *, advanced: bool) -> None:
    """先确认查询已发出，再看查询文档状态码：非 200 立即报 submit 失败，不等满结果页超时。"""
    timeout_ms = int(_cfg()["submit_timeout_ms"])
    if advanced:
        _wait_page_loaded(page)
    for attempt in (1, 2):
        sent = False
        try:
            with page.expect_response(_is_query_document, timeout=timeout_ms) as info:
                with page.expect_request(_is_query_request, timeout=_SUBMIT_SENT_TIMEOUT_MS):
                    click()
                sent = True
            break
        except (PlaywrightTimeoutError, Error) as exc:
            if sent or attempt == 2:
                raise EpubNavError(
                    "submit",
                    hint=_nav_hint(advanced=advanced),
                    message="提交后公布站未返回结果页" if sent else "点击提交后未发出查询",
                    timeout_s=timeout_ms / 1000.0,
                    url=_page_url(page),
                ) from exc
            progress("stage=submit_not_sent reclick=1")
            _settle_after_load(page)
    status = int(info.value.status)
    if status != 200:
        kind = "后端出错或超时" if status >= 500 else "防护拒绝提交"
        raise EpubNavError(
            "submit",
            hint=_nav_hint(advanced=advanced),
            message=f"公布站{kind}（HTTP {status}）",
            url=_page_url(page),
        )
    _wait_result_page_ready(page, advanced=advanced)


def apply_result_page_size(page: Page, *, advanced: bool) -> None:
    """在结果页把「每页3条」切成每页 ``EPUB_PAGE_SIZE`` 条，与人工选下拉框同一条请求。"""
    if not page.query_selector("#sizeSelect"):
        return
    info = page.evaluate(_RESULT_PAGER_JS)
    if not isinstance(info, dict) or str(info.get("size")) == str(EPUB_PAGE_SIZE):
        return
    before = int(info.get("items") or 0)
    total = info.get("total")
    if isinstance(total, int) and total <= before:
        return
    want = min(EPUB_PAGE_SIZE, total) if isinstance(total, int) else EPUB_PAGE_SIZE
    _settle_after_load(page)
    try:
        with page.expect_response(
            lambda r: "/Dxb/PageQuery" in r.url, timeout=_PAGE_SIZE_RESPONSE_TIMEOUT_MS
        ) as resp:
            page.select_option("#sizeSelect", str(EPUB_PAGE_SIZE))
        status = int(resp.value.status)
        if status != 200:
            raise EpubNavError(
                "page_size",
                hint=_nav_hint(advanced=advanced),
                message=f"切换每页{EPUB_PAGE_SIZE}条被拒（HTTP {status}）",
                url=_page_url(page),
            )
        page.wait_for_function(
            "(want) => document.querySelectorAll('#result div.item').length >= want",
            arg=want,
            timeout=_PAGE_SIZE_RENDER_TIMEOUT_MS,
        )
    except (PlaywrightTimeoutError, Error) as exc:
        raise EpubNavError(
            "page_size",
            hint=_nav_hint(advanced=advanced),
            message=f"切换每页{EPUB_PAGE_SIZE}条未返回结果",
            url=_page_url(page),
        ) from exc
    progress(f"stage=page_size items={before}->{want}")


def submit_advanced_search(
    page: Page,
    keyword: str,
    *,
    class_code: str,
    patent_type: str = TYPE_ALL,
) -> None:
    """高级查询：分类号 #e51 + 名称 #ti，类型勾选后提交。等结果标题，不死等 AdvancedQuery+load。"""
    apply_epub_advanced_type_filter(page, patent_type)
    page.fill("#e51", class_code)
    if page.query_selector("#ti"):
        page.fill("#ti", keyword or "")
    form = page.query_selector("#advForm")
    if form is None:
        raise RuntimeError("高级查询未找到 #advForm")
    btn = form.query_selector("button")
    if btn is None:
        raise RuntimeError("高级查询未找到提交按钮")
    _submit_and_check(page, lambda: btn.click(no_wait_after=True), advanced=True)


def submit_index_search(
    page: Page,
    keyword: str,
    *,
    patent_type: str = TYPE_ALL,
) -> None:
    apply_epub_type_filter(page, patent_type)
    page.fill("#searchStr", keyword)

    def _click() -> None:
        form = page.query_selector("#indexForm")
        if form:
            form.evaluate("el => el.submit()")
        else:
            page.evaluate(
                """() => {
                const f = document.getElementById('indexForm');
                if (f) f.submit();
            }"""
            )

    _submit_and_check(page, _click, advanced=False)


def _launch_browser(p: Playwright) -> Browser:
    browser, _label = launch_chromium(p, headless=not _headed())
    return browser


def _new_context(browser: Browser) -> BrowserContext:
    """本机浏览器自己的 UA（只去掉 ``HeadlessChrome``）+ zh-CN + 固定视口。

    带 ``HeadlessChrome`` 时首页不放行；写死旧版本号时表单提交回 400。
    详见 ``cnipa_epub_crawler`` 文件头第 3 点。
    """
    return browser.new_context(
        user_agent=browser_user_agent(browser),
        locale="zh-CN",
        viewport={"width": 1280, "height": 900},
    )
