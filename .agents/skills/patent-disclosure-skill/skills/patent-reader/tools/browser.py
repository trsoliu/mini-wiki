#!/usr/bin/env python
"""
共用 Playwright 浏览器启动：系统 Chrome → Edge → 自带 Chromium。

PDF / 外观视图取证过公布站 WAF 时用本模块，避免再下一套浏览器。
有系统 Chrome / Edge 时**不必** ``python -m playwright install chromium``。

环境变量：
  PLAYWRIGHT_HEADED=1           有界面
  PATENT_BROWSER_CHANNEL=chrome|msedge|chromium
                                强制指定，跳过自动探测顺序
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from stdio_utf8 import ensure_utf8_stdio

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
]

# 自动探测顺序：本机 Chrome、本机 Edge，最后才是 Playwright 自带 Chromium
_AUTO_CHANNELS: tuple[str | None, ...] = ("chrome", "msedge", None)


def headed() -> bool:
    return os.environ.get("PLAYWRIGHT_HEADED", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def playwright_installed() -> bool:
    try:
        import playwright
    except ImportError:
        return False
    return True


def channel_label(channel: str | None) -> str:
    return channel if channel else "chromium"


def _forced_channel() -> str | None | object:
    """返回 None=自带 Chromium，str=channel，缺省哨兵表示走自动顺序。"""
    raw = os.environ.get("PATENT_BROWSER_CHANNEL", "").strip().lower()
    if not raw:
        return _AUTO
    if raw in ("chromium", "bundled", "playwright"):
        return None
    if raw in ("chrome", "msedge"):
        return raw
    return _AUTO


_AUTO = object()


def launch_chromium(
    playwright: Any,
    *,
    headless: bool | None = None,
    extra_args: list[str] | None = None,
) -> tuple[Any, str]:
    """
    启动 Chromium 内核浏览器。

    返回 ``(browser, label)``，label 为 ``chrome`` / ``msedge`` / ``chromium``。
    全部失败时抛出 RuntimeError，文案含安装提示（仅此时才建议 install chromium）。
    """
    if headless is None:
        headless = not headed()
    args = list(LAUNCH_ARGS)
    if extra_args:
        args.extend(extra_args)

    forced = _forced_channel()
    if forced is _AUTO:
        candidates: list[str | None] = list(_AUTO_CHANNELS)
    else:
        candidates = [forced]  # type: ignore[list-item]

    errors: list[str] = []
    for ch in candidates:
        kwargs: dict[str, Any] = {"headless": headless, "args": args}
        if ch:
            kwargs["channel"] = ch
        try:
            browser = playwright.chromium.launch(**kwargs)
            label = channel_label(ch)
            print(f"BROWSER: channel={label}", file=sys.stderr, flush=True)
            return browser, label
        except Exception as e:
            errors.append(f"{channel_label(ch)}: {e}")
            continue

    hint = install_chromium_hint()
    detail = " | ".join(errors[:3]) if errors else "unknown"
    raise RuntimeError(f"无法启动浏览器（{detail}）。{hint}") from None


def install_package_hint() -> str:
    return "pip install playwright  （或 pip install -r requirements.txt）"


def install_chromium_hint() -> str:
    return (
        "请安装 Google Chrome 或 Microsoft Edge 后重试；"
        "若均无，再执行：python -m playwright install chromium"
    )


def probe_launch() -> dict[str, Any]:
    """尝试实际启动（无界面）。供 ``--probe`` 与 Agent 判断是否需要下 Chromium。"""
    out: dict[str, Any] = {
        "playwright": playwright_installed(),
        "channel": None,
        "ok": False,
        "error": None,
        "hint": None,
    }
    if not out["playwright"]:
        out["error"] = "playwright_not_installed"
        out["hint"] = install_package_hint()
        return out
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser, label = launch_chromium(p, headless=True)
            try:
                out["ok"] = True
                out["channel"] = label
            finally:
                browser.close()
    except Exception as e:
        out["error"] = str(e)
        out["hint"] = install_chromium_hint()
    return out


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Playwright 浏览器探测（Chrome → Edge → Chromium）")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="探测能否启动；stdout 一行 JSON",
    )
    args = parser.parse_args(argv)
    if not args.probe:
        parser.print_help()
        return 2
    report = probe_launch()
    ok = bool(report.get("ok"))
    err = report.get("error") or ""
    ch = report.get("channel") or ""
    print(
        f"PROBE: ok={'true' if ok else 'false'} channel={ch} error={err}",
        file=sys.stderr,
        flush=True,
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
