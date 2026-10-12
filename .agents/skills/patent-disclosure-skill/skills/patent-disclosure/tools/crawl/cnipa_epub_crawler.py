# -*- coding: utf-8 -*-
"""
中国专利公布公告站：http://epub.cnipa.gov.cn/ —— **首页「公布公告查询」**（#indexForm /
#searchStr）及 **高级查询**（/Advanced，分类号与名称字段）。

本文件是检索入口（对外 API 不变）。实际提交有两条路径，由 ``EPUB_FAST_FETCH`` 选择：

| 路径 | 做法 | 每词条数 | 角色 |
|------|------|----------|------|
| **B  整页导航**（``cnipa_epub_nav.py``） | 填框 → 提交 → 结果页用站点下拉框切每页 10 条 → 等 DOM | **10** | 默认 |
| **A  fetch**（本文件） | 同会话内 ``fetch`` POST 表单，只取 HTML 文本 | 3 | 默认关闭，仅排查用 |

检索接口 ``/Dxb/IndexQuery`` 固定每页 3 条，不认 ``pageModel.pageSize``。每页 10 条只能在
结果页上用站点自己的「每页N条」下拉框切换（页面 XHR 到 ``/Dxb/PageQuery``，防护脚本会给它
加签名；脚本自己发的 fetch/XHR 没有签名，实测 8～20 秒无响应）。路径 A 不打开结果页，做不到。
后续的词直接在结果页顶部检索框提交，不回首页。
解析始终由 ``cnipa_epub_parse.py`` 完成，两条路径共用。

===============================================================================
站点防护特征（实测，改站时请重新验证）
分析 by Claude Opus 5 Extra High
===============================================================================

**1. 瑞数类动态 cookie 防护。**
首访返回一段挑战 JS 并**自跳转一次**（同 URL 再导航），由 JS 计算后种下动态 cookie，
之后才放行真正的首页 DOM。cookie 名**随机且成对**，形如 ``NOh8RTWx6K2dS`` /
``NOh8RTWx6K2dT``（同一随机前缀 + ``S`` / ``T`` 后缀），另有 ``enable_<前缀>``、``WEB``
与 ``.AspNetCore.Antiforgery.*``。前缀每次可能不同，**不可硬编码 cookie 名**。

后果：``goto`` 之后 DOM 会被销毁重建，期间 ``query_selector`` 可能抛
"Execution context was destroyed"。gate 轮询必须**吞掉**该异常继续等
（见 ``cnipa_epub_nav._wait_selector``），否则会误判成站点不可用。

**2. 纯 HTTP 直连不可行（已实测否定）。**
把浏览器 cookie 原样搬进 ``requests``、并配齐 UA / Referer / Origin /
Content-Type 后 POST ``/Dxb/IndexQuery``，拿回的是 **202 + 约 3.1KB 挑战页**，不是结果页。
该 cookie 需要页面内 JS 持续参与，脱离浏览器运行时即失效。
**结论：不要再尝试"加请求头直连"或复用 cookie 的离线抓取方案。**

**3. 指纹敏感：UA 用本机浏览器自己的，只去掉 ``HeadlessChrome``。**
未覆盖 UA 时无头浏览器自带 ``HeadlessChrome/<ver>``，实测**直接不放行**：
首页 DOM 仅 39 字节、``<title>`` 为空、``#searchStr`` 等到超时也不出现。
UA 里的版本号还须与真实内核一致（``tools/browser.browser_user_agent``）。写死旧版本
（内核 154 却报 ``Chrome/120``）时 GET 照常放行，**POST 提交却回 400**：正文 6 字节，
页面变成 ``<html><head></head><body></body></html>``（39 字节）。2026-10 实测同一轻查询
旧 UA 2/2 被拒，真实版本号 3/3 通过。
启动参数 ``--disable-blink-features=AutomationControlled``（见 ``tools/browser.py``）同理。

挑战页与拒绝页的特征（用于归类，不能跳过——挑战 JS 必须由浏览器跑完才放行）：

| 状态 | 特征 | 处理 |
|------|------|------|
| 挑战页 | GET 回 202，约 2.7KB，含 ``$_ts``，随后自跳转到 200 | gate 轮询等它跑完，正常 6–15 秒 |
| 提交被拒 | 查询 POST 回 400 等非 200 / 非 5xx，页面空白 | 立即报 submit 失败；冷却后换新会话重试一次 |
| 后端超时 | 查询 POST 回 504（宽条件如只填 ``B25J``，可等满 300 秒） | 不重试，缩窄条件 |

检索框一出现就提交（零点几秒内）同样会被回 400：gate 之后先等页面 ``load`` 完成再静置
2 秒（``cnipa_epub_nav._settle_after_load``）才提交或 fetch。

结果页 HTML 原文里的 ``<title>`` 与部分字段是 ``&#x…;`` 实体（DOM 里是中文），
按原文判断标题前须先反转义（见 ``_looks_like_result_html``）。

**4. 限流是会话级的，且不可逆。**
连续无间隔提交，**第 3 次**起即被拒（返回 400 或直接挂住）。一旦触发，该浏览器上下文
即报废：在同一 context 里重新走首页 gate 实测 **41.5 秒仍过不去**，之后请求一直回 202 挑战页。
但**换一个全新的 browser context 可立即恢复**（实测重新 gate 3.8 秒即正常）。
说明封禁绑定会话而非 IP，因此：

- 词与词之间必须**节流**（见下「自适应节流」）；
- HTTP 400/202、挑战页等**会话已脏**时，不要原地重试，应**丢弃脏 context 重建**
  （``_FastSession.rebuild``），且重建前要**先冷却**——刚被限流时新 context 同样过不了 gate。
- 页内 ``fetch`` 的 ``status=-1``（AbortController 超时、导航把执行上下文拆掉）只表示
  **这一跳提交失败**，会话未必报废。此时保留当前页、回退整页导航；不要当成限流去
  ``rebuild``。``rebuild`` 自己的 gate 失败也须 ``return None``，让检索循环走导航兜底，
  禁止把 ``EpubNavError`` 抛出检索循环、整轮 ``skip_epub``。

===============================================================================
自适应节流（``_PaceController``）
===============================================================================

思路取自 TCP **Vegas / BBR**：以**响应延迟**而非"被拒"作为主信号，在报废前退让。
不采用 Reno 式 AIMD，因为代价极不对称——多等 1 秒只亏 1 秒，被拒一次却要赔上整个会话。

方向与 TCP 相反（间隔是发送窗口的倒数）：**连续健康才加性减速间隔，一见尖峰立刻乘性拉大**。

实测基线：正常 fetch 0.19–0.62 秒；第一轮被拒前出现过 1.25 秒的孤立尖峰，
4 个词后会话即报废——尖峰因此被当作早期预警。

单轮查新只有 2–8 个样本，不足以收敛，故把学到的间隔**跨进程持久化**
（临时目录 ``cnipa_epub_pace.json``），按新鲜度衰减后作为下一轮起点。

**5. 不覆盖的场景**：图形/滑块验证码、短信验证、强制登录。若站点启用，本模块无破解逻辑；
可试 ``PLAYWRIGHT_HEADED=1`` 人工辅助，或按 ``prompts/prior_art_search.md`` 降级 WebSearch。

以上手段仅用于降低自动化与常规浏览器之间的形态差异，便于合法的公开文献查新，
**不**表示规避法律法规或站点服务条款。

===============================================================================
检索关键词建议
===============================================================================
首页检索框对多个词按 **同时包含（AND）** 理解，词多且专时极易 0 条；建议**一次一个短词**，
需要宽召回时用 ``cnipa_epub_search.py``（按空白拆词、逐词检索再按 ``pub_number`` 合并）。

===============================================================================
环境变量
===============================================================================
  EPUB_FAST_FETCH=1 / true     打开路径 A（每词只有 3 条，仅排查站点改版时用）
  EPUB_PACE_FILE               自适应节奏持久化路径；设 ``off`` 关闭持久化
  PLAYWRIGHT_HEADED=1          有界面浏览器
  EPUB_WAIT_YAML               覆盖等待参数 YAML 路径
  EPUB_WAF_MAX_WAIT_SEC        覆盖 gate 轮询上限（秒）
  EPUB_RESULT_HTML             CLI 落盘结果页 HTML 的路径
"""
from __future__ import annotations

import html as html_lib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from playwright.sync_api import (
    Browser,
    Error,
    Page,
    Playwright,
    sync_playwright,
)

_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE.parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from cnipa_epub_parse import (
    EpubSearchHit,
    hits_to_jsonable,
    parse_search_result_html,
)
from stdio_utf8 import ensure_utf8_stdio
from patent_type import (
    TYPE_ALL,
    epub_checkbox_states,
    normalize_patent_type,
)
from cnipa_epub_wait import EpubNavError, load_wait_config, progress

# 路径 B（整页导航）的原子操作全部来自 cnipa_epub_nav。
# 这里以**模块级名字**重新导出：既保持 `from cnipa_epub_crawler import ...` 的既有用法，
# 也让 `patch("cnipa_epub_crawler.submit_index_search")` 等测试替身继续生效
# （下方回退路径一律按模块级名字调用，不写成 nav.xxx）。
from cnipa_epub_nav import (  # noqa: F401  (re-export)
    EPUB_ADVANCED,
    EPUB_ADVANCED_CHECKBOX,
    EPUB_BASE,
    EPUB_PAGE_SIZE,
    EPUB_TITLE_NO_HIT,
    EPUB_TITLE_RESULT,
    _RESULT_PAGE_READY_JS,
    _goto,
    _headed,
    _launch_browser,
    _new_context,
    _nav_hint,
    _page_url,
    _safe_page_content,
    _wait_result_page_ready,
    _wait_selector,
    apply_epub_advanced_type_filter,
    apply_epub_type_filter,
    apply_result_page_size,
    default_result_html_path,
    open_epub_advanced_search,
    submit_advanced_search,
    submit_index_search,
    wait_for_epub_advanced_ready,
    wait_for_epub_home_ready,
)

# ---------------------------------------------------------------------------
# 路径 A：同会话 fetch 提交
# ---------------------------------------------------------------------------

#: 总开关。True=优先 fetch 快路径（每词 3 条）；False=全程整页导航（每词 10 条）。
#: 环境变量 EPUB_FAST_FETCH=1/0 可临时覆盖。
EPUB_FAST_FETCH = False

# --- 自适应节流 -------------------------------------------------------------
# 借鉴 TCP **Vegas / BBR** 一支：用**延迟变化**当早期拥塞信号，在被拒之前退让。
# 不用 Reno 的 AIMD，因为这里代价极不对称：多等 1 秒只亏 1 秒，而触发一次限流会
# 让整个会话报废（冷却 + 重新 gate，实测最差 41.5 秒仍过不去），"冲到丢包再退"不划算。
#
# 方向与 TCP 相反：间隔是发送窗口的倒数，所以这里是**加性减、乘性增**——
# 保守地变快（连续健康才小步下探），激进地变慢（一见尖峰立刻乘性拉大）。

#: 总倍率系数。所有间隔乘以它；网络差或想更稳就调大（如 1.5），激进可设 0.8。
FAST_THROTTLE_SCALE = 1.0

#: 无历史时的起步间隔（秒）。实测 3 秒 8/8 稳，2 秒在第 6 词附近被拒。
FAST_THROTTLE_START_SEC = 3.0

#: 自适应上下限（秒）。下限不进入已知危险区（2 秒以下实测会被拒）。
FAST_THROTTLE_MIN_SEC = 2.0
FAST_THROTTLE_MAX_SEC = 8.0

#: 连续几次健康才允许下探，以及每次下探的**比例**。
#: 用乘性回落而非固定步长：上涨是乘性的，若下探用固定步长，从高位回到起步值需要
#: 几十次健康查询，而一轮只有 2–8 个词，实际上永远回不来。几何回落保证可恢复，
#: 同时仍显著慢于上涨（×1.5 vs ×0.92），维持"保守变快、激进变慢"。
FAST_HEALTHY_STREAK = 2
FAST_THROTTLE_DOWN_RATIO = 0.92

#: 见到延迟尖峰时的乘性放大倍数；被明确拒绝时则直接翻倍。
FAST_THROTTLE_UP_RATIO = 1.5

#: EWMA 平滑系数（新样本权重）。
FAST_EWMA_ALPHA = 0.3

#: 尖峰判定。实测正常 0.19–0.62 秒；第一轮被拒前出现过 1.25 秒的孤立尖峰。
#: 绝对阈值直接判定；比例阈值需同时超过 floor，避免基线极小时把正常波动误判为尖峰。
FAST_RTT_SPIKE_ABS_SEC = 1.5
FAST_RTT_SPIKE_RATIO = 2.0
FAST_RTT_SPIKE_FLOOR_SEC = 0.8

#: 学到的节奏跨进程持久化：一轮查新只有 2–8 个样本，不够单轮收敛，靠跨会话累积。
#: 路径可用 EPUB_PACE_FILE 覆盖；设为 "off" 关闭持久化。
FAST_PACE_FILENAME = "cnipa_epub_pace.json"
#: 新鲜期内直接沿用；过了新鲜期向起步值回归一半；超过陈旧期整条丢弃
#: （站点松紧与时段有关，旧值不可全信）。
FAST_PACE_FRESH_SEC = 1_800.0
FAST_PACE_STALE_SEC = 21_600.0

#: 重建会话前的冷却（秒）。刚被限流时**即使换新 context 也过不了 gate**（实测），
#: 需要先静默一段再重建。
FAST_REBUILD_COOLDOWN_SEC = 8.0

#: 重建后过 gate 的时间预算（秒）。比常规 gate 宽松，因为此时站点正处于收紧状态。
FAST_REBUILD_GATE_SEC = 40.0

#: 单次 fetch 的浏览器内超时（毫秒）。正常 0.3–0.5 秒返回；超时由 JS 返回 status=-1，
#: 按「本跳失败」回退导航，不按会话限流重建。
FAST_FETCH_TIMEOUT_MS = 8_000

#: 一轮检索里最多重建几次脏会话；超过则本轮放弃快路径，改走整页导航。
FAST_MAX_REBUILD = 2

#: 结果页长度下限（字节）。实测正常结果页约 35–37KB，挑战页约 3.1KB。
_FAST_MIN_HTML_BYTES = 2_000

# 在已过 gate 的会话内提交表单，只取 HTML 文本，不做整页导航、不加载结果页资源。
# AbortController 负责超时，避免被限流时干等到 Playwright 层超时。
#
# 提交方式优先 **FormData(表单) 整表**（借鉴 patent-search 的翻页实现）：
# 由浏览器按表单真实结构序列化，自动带上隐藏字段、CSRF 令牌，以及 checkbox 的**真实 value**
# （公布站高级页用的是 value="true"，并非惯例的 "on"）。手工拼参数只作为表单缺失时的兜底。
_FAST_FETCH_JS = """async ({term, states, timeoutMs}) => {
  const ac = new AbortController();
  const timer = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const form = document.getElementById('indexForm');
    let url = '/Dxb/IndexQuery';
    let body;
    let mode;
    if (form) {
      const box = form.querySelector('#searchStr');
      if (box) box.value = term;
      for (const [id, want] of Object.entries(states)) {
        const el = form.querySelector('#' + id);
        if (el) el.checked = !!want;
      }
      if (form.action) url = form.action;
      body = new URLSearchParams(new FormData(form));
      mode = 'form';
    } else {
      body = new URLSearchParams();
      body.set('searchStr', term);
      for (const [k, v] of Object.entries(states)) { if (v) body.set(k, 'on'); }
      mode = 'manual';
    }
    const r = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
      body: body.toString(),
      credentials: 'include',
      signal: ac.signal,
    });
    const text = await r.text();
    return {ok: true, status: r.status, html: text, mode: mode};
  } catch (e) {
    return {ok: false, status: -1, html: '', err: String(e).slice(0, 120)};
  } finally {
    clearTimeout(timer);
  }
}"""


def _cfg() -> dict:
    return load_wait_config()


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def fast_fetch_enabled() -> bool:
    """模块常量 + 环境变量；环境变量只用于**关闭**。"""
    raw = os.environ.get("EPUB_FAST_FETCH", "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    return bool(EPUB_FAST_FETCH)


def _looks_like_result_html(html: Any) -> bool:
    """区分「真结果页」与「挑战页 / 错误页」。

    挑战页约 3.1KB 且不含结果页 title；0 条命中的页面 title 为「无查询结果」，属正常结果。
    原文 title 是 ``&#x…;`` 实体，先反转义再比对。
    """
    if not isinstance(html, str) or len(html) < _FAST_MIN_HTML_BYTES:
        return False
    head = html_lib.unescape(html[:8000])
    return (
        EPUB_TITLE_RESULT in head
        or EPUB_TITLE_NO_HIT in head
        or 'class="item"' in html
    )


def _pace_path() -> Path | None:
    """持久化文件路径；返回 None 表示关闭持久化。

    默认放系统临时目录：这是工具的运行期状态，不是用户产出，不应污染仓库或 ``outputs/``。
    """
    raw = os.environ.get("EPUB_PACE_FILE", "").strip()
    if raw.lower() in {"off", "0", "none", "false"}:
        return None
    if raw:
        return Path(raw).expanduser()
    return Path(tempfile.gettempdir()) / FAST_PACE_FILENAME


class _PaceController:
    """按观测到的响应延迟调节词间间隔（Vegas 式：以延迟而非被拒作为主信号）。

    单轮查新样本很少（2–8 个词），单靠本轮难以收敛，因此把学到的间隔跨进程持久化，
    按新鲜度衰减后作为下一轮起点。
    """

    def __init__(self) -> None:
        self.interval = float(FAST_THROTTLE_START_SEC)
        self.srtt: float | None = None
        self.rtt_min: float | None = None
        self.healthy_streak = 0
        self.samples = 0
        self._load()

    # -- 持久化 ------------------------------------------------------------
    def _load(self) -> None:
        path = _pace_path()
        if path is None or not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            saved = float(data["interval"])
            age = max(0.0, time.time() - float(data.get("saved_at", 0)))
        except (OSError, ValueError, KeyError, TypeError):
            return
        if age > FAST_PACE_STALE_SEC:
            return  # 太旧，站点松紧可能已变，按起步值重新学
        if age > FAST_PACE_FRESH_SEC:
            # 半衰：既不全信旧值，也不浪费它
            saved = (saved + FAST_THROTTLE_START_SEC) / 2.0
        self.interval = _clamp(
            saved, FAST_THROTTLE_MIN_SEC, FAST_THROTTLE_MAX_SEC
        )
        progress(f"stage=pace_load interval={self.interval:.2f} age_s={age:.0f}")

    def save(self) -> None:
        """一轮结束后落盘。没有成功样本就别写，免得把失败经验固化下来。"""
        path = _pace_path()
        if path is None or self.samples <= 0:
            return
        payload = {
            "interval": round(self.interval, 3),
            "saved_at": time.time(),
            "srtt": round(self.srtt, 3) if self.srtt is not None else None,
            "samples": self.samples,
        }
        try:
            # 原子写：多个查新进程可能同时结束。
            tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            tmp.replace(path)
        except OSError:
            pass

    # -- 观测与调节 --------------------------------------------------------
    def wait_sec(self, last_submit_at: float) -> float:
        if last_submit_at <= 0:
            return 0.0
        target = self.interval * max(0.1, float(FAST_THROTTLE_SCALE))
        return max(0.0, target - (time.monotonic() - last_submit_at))

    def _is_spike(self, rtt: float) -> bool:
        if rtt >= FAST_RTT_SPIKE_ABS_SEC:
            return True
        if self.srtt is None or rtt < FAST_RTT_SPIKE_FLOOR_SEC:
            return False
        return rtt > self.srtt * FAST_RTT_SPIKE_RATIO

    def observe(self, rtt: float, reason: str) -> None:
        """记录一次提交结果并调整间隔。``reason`` 同 ``_submit_once``。"""
        if reason == "unsupported":
            return  # 与站点节奏无关，不污染统计
        before = self.interval
        if reason == "throttled":
            self.interval = _clamp(
                self.interval * 2.0, FAST_THROTTLE_MIN_SEC, FAST_THROTTLE_MAX_SEC
            )
            self.healthy_streak = 0
            progress(
                f"stage=pace reason=throttled interval={before:.2f}->{self.interval:.2f}"
            )
            return

        self.samples += 1
        self.srtt = rtt if self.srtt is None else (
            FAST_EWMA_ALPHA * rtt + (1 - FAST_EWMA_ALPHA) * self.srtt
        )
        self.rtt_min = rtt if self.rtt_min is None else min(self.rtt_min, rtt)

        if self._is_spike(rtt):
            self.interval = _clamp(
                self.interval * FAST_THROTTLE_UP_RATIO,
                FAST_THROTTLE_MIN_SEC,
                FAST_THROTTLE_MAX_SEC,
            )
            self.healthy_streak = 0
            progress(
                f"stage=pace reason=rtt_spike rtt={rtt:.2f} srtt={self.srtt:.2f} "
                f"interval={before:.2f}->{self.interval:.2f}"
            )
            return

        self.healthy_streak += 1
        if self.healthy_streak >= FAST_HEALTHY_STREAK:
            self.healthy_streak = 0
            self.interval = _clamp(
                self.interval * FAST_THROTTLE_DOWN_RATIO,
                FAST_THROTTLE_MIN_SEC,
                FAST_THROTTLE_MAX_SEC,
            )
            if self.interval != before:
                progress(
                    f"stage=pace reason=healthy rtt={rtt:.2f} srtt={self.srtt:.2f} "
                    f"interval={before:.2f}->{self.interval:.2f}"
                )


class _FastSession:
    """持有 browser context / page，负责 gate、节流与脏会话重建。

    站点限流绑定会话：一旦被拒，同 context 内无法恢复，必须整体重建（见文件头第 4 点）。
    """

    def __init__(self, browser: Browser, pace: "_PaceController | None" = None) -> None:
        self.browser = browser
        self.context: Any = None
        self.page: Any = None
        self.rebuilds = 0
        self.pace = pace if pace is not None else _PaceController()
        self._last_submit_at = 0.0

    # -- 生命周期 ----------------------------------------------------------
    def ensure_page(self) -> Any:
        """保证有可用 context / page。

        **不**在这里过 gate：gate 失败必须发生在检索循环内，才能沿用既有的
        ``stop_on_first_nav_failure`` 处理，行为与改造前一致。
        """
        if self.page is None:
            self.context = _new_context(self.browser)
            self.page = self.context.new_page()
        return self.page

    def close(self) -> None:
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass
        self.context = None
        self.page = None

    def rebuild(self) -> Any:
        """丢弃脏会话换新的。返回新 page；超过上限或新会话过不了 gate 时返回 None。

        gate 失败**不**再抛 ``EpubNavError``：调用方会把 ``None`` 当成快路径不可用，
        回退整页导航。失败的半成品 context 随即关掉，避免把没检索框的页交给导航路径。
        """
        if self.rebuilds >= FAST_MAX_REBUILD:
            return None
        self.rebuilds += 1
        progress(
            f"stage=session_rebuild n={self.rebuilds} cooldown_s={FAST_REBUILD_COOLDOWN_SEC:g}"
        )
        self.close()
        self._last_submit_at = 0.0
        # 刚被限流时立刻重建仍会被挡在 gate 外，先静默冷却。
        time.sleep(FAST_REBUILD_COOLDOWN_SEC)
        self.ensure_page()
        try:
            wait_for_epub_home_ready(self.page, max_wait_sec=FAST_REBUILD_GATE_SEC)
        except EpubNavError as exc:
            progress(
                f"stage=rebuild_gate_failed hint={exc.hint or '-'} fallback=nav"
            )
            print(
                "EPUB_NOTE: rebuild_gate_failed fallback=nav",
                file=sys.stderr,
                flush=True,
            )
            self.close()
            return None
        return self.page

    # -- 提交 --------------------------------------------------------------
    def _throttle(self) -> None:
        wait = self.pace.wait_sec(self._last_submit_at)
        if wait > 0:
            time.sleep(wait)

    def _submit_once(self, keyword: str, patent_type: str) -> tuple[str | None, str]:
        """提交一次。

        返回 ``(html, reason)``：

        - ``("...", "ok")``          成功
        - ``(None, "throttled")``    HTTP 拒绝/挑战页 —— 会话已脏，值得冷却后重建
        - ``(None, "submit_failed")`` 页内 fetch 中断（status=-1 / Abort）—— 保留会话，回退导航
        - ``(None, "unsupported")``  环境或站点结构不支持 fetch —— 重试无意义，直接回退
        """
        self._throttle()
        started = time.monotonic()
        try:
            res = self.page.evaluate(
                _FAST_FETCH_JS,
                {
                    "term": keyword,
                    "states": epub_checkbox_states(patent_type),
                    "timeoutMs": FAST_FETCH_TIMEOUT_MS,
                },
            )
        except Error:
            self._last_submit_at = time.monotonic()
            return None, "unsupported"
        self._last_submit_at = time.monotonic()
        rtt = time.monotonic() - started
        # 测试替身或站点改版可能返回非 dict —— 重试也不会变好，直接回退。
        if not isinstance(res, dict):
            return None, "unsupported"
        html = res.get("html")
        status = res.get("status")
        err = str(res.get("err") or "").strip()
        html_len = len(html) if isinstance(html, str) else 0
        if res.get("ok") and status == 200 and _looks_like_result_html(html):
            progress(
                f"stage=fetch term={keyword} ms={rtt * 1000:.0f} bytes={html_len} "
                f"mode={res.get('mode') or '-'}"
            )
            self.pace.observe(rtt, "ok")
            return html, "ok"
        # status=-1：AbortController / 执行上下文被拆掉。不是 400/202 那种会话封禁。
        if status == -1 or not res.get("ok"):
            reason = "submit_failed"
        else:
            reason = "throttled"
        extra = f" err={err[:120]}" if err else ""
        progress(
            f"stage=fetch_reject term={keyword} status={status} "
            f"bytes={html_len} reason={reason}{extra}"
        )
        # 中断不拉大节流间隔，避免偶发 abort 把后续词全部拖慢。
        self.pace.observe(rtt, "throttled" if reason == "throttled" else "unsupported")
        return None, reason

    def query(self, keyword: str, patent_type: str) -> str | None:
        """提交一个词；仅会话级限流才重建；本跳中断或重建失败则返回 None 走导航。

        gate 由调用方在循环内先行保证（见 ``ensure_page`` 注释）。
        """
        if self.page is None:
            return None
        html, reason = self._submit_once(keyword, patent_type)
        if reason == "ok":
            return html
        if reason != "throttled":
            # 本跳失败或结构不支持：保留当前页，让调用方走整页导航。
            return None
        if self.rebuild() is None:
            return None
        html, reason = self._submit_once(keyword, patent_type)
        return html if reason == "ok" else None


# ---------------------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------------------


def fetch_epub_result_html(
    keyword: str,
    *,
    patent_type: str = TYPE_ALL,
    playwright_factory: Callable[[], Playwright] | None = None,
) -> str:
    """只拉取检索结果页 HTML（一词一页，不翻页）。"""
    rows = search_epub_keywords(
        [keyword], patent_type=patent_type, playwright_factory=playwright_factory
    )
    return rows[0][0]


def search_epub_keywords(
    terms: list[str],
    *,
    patent_type: str = TYPE_ALL,
    class_codes: list[str] | None = None,
    playwright_factory: Callable[[], Playwright] | None = None,
) -> list[tuple[str, list[EpubSearchHit]]]:
    """一场检索共用一个浏览器；一词一页，返回与检索次数等长的 ``(html, hits)``。

    ``class_codes`` 非空时走公布站 **高级查询**（分类号 + 名称）；``terms`` 可为空
    （只按分类号，保底放宽）。高级查询只走整页导航路径。
    导航失败默认停止后续跳（``stop_on_first_nav_failure``）；已完成的跳仍返回。
    """
    codes = [c.strip() for c in (class_codes or []) if c and str(c).strip()]
    if not terms and not codes:
        return []
    kw_list = list(terms) if terms else [""]
    cfg = _cfg()
    stop = bool(cfg["stop_on_first_nav_failure"])
    pw_gen = playwright_factory or sync_playwright
    with pw_gen() as p:
        browser = _launch_browser(p)
        session = _FastSession(browser)
        # 快路径仅用于首页检索；高级查询字段未经 fetch 实测，继续走导航。
        fast_on = fast_fetch_enabled() and not codes

        def _run_hop(code: str, keyword: str) -> str:
            nonlocal fast_on
            page = session.ensure_page()
            html: str | None = None
            if fast_on:
                # gate 与导航路径共用；检索框已在时是空操作。
                wait_for_epub_home_ready(page)
                html = session.query(keyword, patent_type)
                if html is None:
                    # 站点改版 / 被拦 / 环境不支持：本轮不再试，整轮回退导航。
                    fast_on = False
                    print(
                        "EPUB_NOTE: fast_fetch_unavailable fallback=nav",
                        file=sys.stderr,
                        flush=True,
                    )
            if html is None:
                # 快路径可能已重建过会话，重新取 page。
                page = session.ensure_page()
                if not code:
                    wait_for_epub_home_ready(page)
                    submit_index_search(page, keyword, patent_type=patent_type)
                else:
                    wait_for_epub_advanced_ready(page)
                    submit_advanced_search(
                        page,
                        keyword,
                        class_code=code,
                        patent_type=patent_type,
                    )
                apply_result_page_size(page, advanced=bool(code))
                html = _safe_page_content(page)
            return html

        try:
            out: list[tuple[str, list[EpubSearchHit]]] = []
            hops: list[tuple[str, str]]
            if not codes:
                hops = [("", keyword) for keyword in kw_list if keyword]
            else:
                hops = [(code, keyword) for code in codes for keyword in kw_list]
            total = len(hops)
            # gate 长尾或单次提交被拒时，一轮内允许冷却后换新会话重试一次。
            fresh_retry_left = 1
            for i, (code, keyword) in enumerate(hops, start=1):
                label = (
                    f"stage=home term={keyword} i={i}/{total}"
                    if not code
                    else f"stage=advanced class={code} term={keyword or '-'} i={i}/{total}"
                )
                progress(label)
                failure: EpubNavError | None = None
                for _attempt in (1, 2):
                    try:
                        html = _run_hop(code, keyword)
                        out.append((html, parse_search_result_html(html)))
                        failure = None
                        break
                    except EpubNavError as exc:
                        failure = exc
                        if fresh_retry_left <= 0:
                            break
                        fresh_retry_left -= 1
                        progress(
                            f"stage=fresh_session_retry after={exc.stage} hint={exc.hint or '-'}"
                        )
                        if session.rebuild() is None:
                            break
                if failure is None:
                    continue
                remaining = total - i
                progress(
                    f"stage={failure.stage} remaining_skipped={remaining} hint={failure.hint}"
                )
                if not stop:
                    print(
                        f"EPUB_NOTE: hop_failed_continue stage={failure.stage} hint={failure.hint}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue
                print(
                    f"EPUB_NOTE: stopped_after_failure stage={failure.stage} hint={failure.hint}",
                    file=sys.stderr,
                    flush=True,
                )
                if out:
                    return out
                raise failure
            return out
        finally:
            if fast_fetch_enabled() and not codes:
                session.pace.save()
            session.close()
            browser.close()


def search_epub_keyword(
    keyword: str,
    *,
    patent_type: str = TYPE_ALL,
    class_codes: list[str] | None = None,
    playwright_factory: Callable[[], Playwright] | None = None,
) -> tuple[str, list[EpubSearchHit]]:
    rows = search_epub_keywords(
        [keyword],
        patent_type=patent_type,
        class_codes=class_codes,
        playwright_factory=playwright_factory,
    )
    return rows[0]


def search_epub_keyword_with_page(
    page: Page,
    keyword: str,
    *,
    patent_type: str = TYPE_ALL,
) -> tuple[str, list[EpubSearchHit]]:
    """在**调用方已持有的 page** 上检索（如 patent-reader 取外观图时复用同一会话）。

    这里保持整页导航语义：调用方通常还要在同一 page 上继续打开详情页。
    """
    wait_for_epub_home_ready(page)
    submit_index_search(page, keyword, patent_type=patent_type)
    html = _safe_page_content(page)
    return html, parse_search_result_html(html)


def _dump_home_debug() -> None:
    """调试：仅拉取首页并保存 WAF 通过后 HTML。"""
    out = Path(__file__).resolve().parent / "_last_home.html"
    with sync_playwright() as p:
        browser = _launch_browser(p)
        context = _new_context(browser)
        page = context.new_page()
        try:
            wait_for_epub_home_ready(page)
            out.write_text(page.content(), encoding="utf-8")
            print("已保存:", out)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    ensure_utf8_stdio()
    argv = [a for a in sys.argv[1:] if a.strip()]
    if argv and argv[0] in ("--dump-home", "-d"):
        _dump_home_debug()
        sys.exit(0)
    patent_type = TYPE_ALL
    filtered: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--type", "-t") and i + 1 < len(argv):
            patent_type = normalize_patent_type(argv[i + 1], default=TYPE_ALL)
            i += 2
            continue
        if a.startswith("--type="):
            patent_type = normalize_patent_type(a.split("=", 1)[1], default=TYPE_ALL)
            i += 1
            continue
        filtered.append(a)
        i += 1
    kw = (filtered[0] if filtered else "批处理").strip()
    try:
        out_html, hits = search_epub_keyword(kw, patent_type=patent_type)
    except EpubNavError as e:
        print("CNIPA_EPUB_ERROR:", e, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("CNIPA_EPUB_ERROR:", e, file=sys.stderr)
        sys.exit(1)
    out_path = Path(
        os.environ.get("EPUB_RESULT_HTML", "").strip() or default_result_html_path()
    )
    out_path = out_path.expanduser().resolve()
    out_path.write_text(out_html, encoding="utf-8")
    print(
        "结果页长度",
        len(out_html),
        "解析条目数",
        len(hits),
        file=sys.stderr,
        flush=True,
    )
    print("结果页 HTML 已保存:", out_path, file=sys.stderr, flush=True)
    print(
        "EPUB_HITS_JSON:",
        json.dumps(hits_to_jsonable(hits), ensure_ascii=False),
        flush=True,
    )
