# -*- coding: utf-8 -*-
"""Headless browser: embed SVG in a local page, screenshot PNG.

Starts a short-lived HTTP server on a free port (preferred port is probed first;
busy ports are skipped). Playwright reuses tools/browser.py (system
Chrome/Edge). Server and browser always shut down in ``finally``.

PNG for CAD views does not use matplotlib. If the browser cannot start, keep SVG.

  python tools/svg_screenshot.py --svg a.svg --png a.png
  python tools/svg_screenshot.py --dir outputs/case/cad_views/views
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

PREFERRED_PORT_ENV = "PATENT_SKILL_SVG_PORT"
DEFAULT_PREFERRED_PORT = 18765

_HTML = """<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<style>
html,body{margin:0;padding:0;background:#fff;}
#stage{display:inline-block;background:#fff;}
#stage svg{display:block;max-width:none;}
</style>
</head>
<body><div id="stage">__SVG__</div></body>
</html>
"""


def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


def pick_free_port(host: str = "127.0.0.1", preferred: int | None = None) -> int:
    """Probe ``preferred`` first; if occupied, bind port 0."""
    if preferred is not None and preferred > 0:
        if port_free(host, preferred):
            return preferred
        print(f"SVG_HTTP: preferred_port_busy={preferred}", file=sys.stderr, flush=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def preferred_port_from_env(cli_port: int | None = None) -> int | None:
    if cli_port is not None and cli_port > 0:
        return cli_port
    raw = os.environ.get(PREFERRED_PORT_ENV, "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_PREFERRED_PORT


def wrap_svg_html(svg_text: str) -> str:
    text = svg_text.strip()
    if text.startswith("<?xml"):
        end = text.find("?>")
        if end != -1:
            text = text[end + 2 :].lstrip()
    return _HTML.replace("__SVG__", text)


_HREF_ATTR_RE = re.compile(r'((?:xlink:)?href=")([^"]+)(")', re.IGNORECASE)
_REMOTE_HREF_PREFIXES = ("data:", "http://", "https://", "#", "//", "file:")


def inline_local_hrefs(
    svg_text: str, base_dir: Path, *, _seen: frozenset[Path] | None = None
) -> str:
    """Resolve relative href / xlink:href to data URIs so a pasted SVG still renders.

    Nested ``.svg`` files are inlined recursively. Missing or remote hrefs are left as-is.
    """
    seen = _seen or frozenset()

    def repl(match: re.Match[str]) -> str:
        raw = match.group(2).strip()
        if not raw or raw.lower().startswith(_REMOTE_HREF_PREFIXES):
            return match.group(0)
        target = (base_dir / raw).resolve()
        if not target.is_file() or target in seen:
            return match.group(0)
        suffix = target.suffix.lower()
        nested = seen | {target}
        if suffix == ".svg":
            inner = inline_local_hrefs(
                target.read_text(encoding="utf-8"), target.parent, _seen=nested
            )
            uri = "data:image/svg+xml;base64," + base64.b64encode(inner.encode("utf-8")).decode(
                "ascii"
            )
        elif suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }[suffix]
            uri = f"data:{mime};base64," + base64.b64encode(target.read_bytes()).decode("ascii")
        else:
            return match.group(0)
        return f"{match.group(1)}{uri}{match.group(3)}"

    return _HREF_ATTR_RE.sub(repl, svg_text)


def _load_svg(path: Path) -> str:
    return inline_local_hrefs(path.read_text(encoding="utf-8"), path.parent)


class _SvgHandler(BaseHTTPRequestHandler):
    pages: dict[str, str] = {}

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/view":
            key = (parse_qs(parsed.query).get("id") or [""])[0]
            html = self.pages.get(key)
            if html is None:
                self.send_error(404, "unknown id")
                return
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)


def _start_server(host: str, port: int, pages: dict[str, str]) -> ThreadingHTTPServer:
    class Bound(_SvgHandler):
        pass

    Bound.pages = pages
    httpd = ThreadingHTTPServer((host, port), Bound)
    thread = threading.Thread(target=httpd.serve_forever, name="svg-http", daemon=True)
    thread.start()
    httpd.thread = thread  # type: ignore[attr-defined]
    return httpd


def svg_display_size(svg_text: str) -> tuple[int, int]:
    """读根 SVG 的像素宽高，供截图视口对齐，避免大于 1400×1000 的图画被视口裁掉。"""
    match = re.search(r"<svg\b[^>]*>", svg_text, re.IGNORECASE | re.DOTALL)
    if match:
        tag = match.group(0)
        width_m = re.search(r'\bwidth="([0-9.]+)', tag, re.IGNORECASE)
        height_m = re.search(r'\bheight="([0-9.]+)', tag, re.IGNORECASE)
        if width_m and height_m:
            return (
                max(1, int(round(float(width_m.group(1))))),
                max(1, int(round(float(height_m.group(1))))),
            )
        vb = re.search(
            r'viewBox="\s*[0-9.-]+\s+[0-9.-]+\s+([0-9.]+)\s+([0-9.]+)"',
            tag,
            re.IGNORECASE,
        )
        if vb:
            return (
                max(1, int(round(float(vb.group(1))))),
                max(1, int(round(float(vb.group(2))))),
            )
    return 1400, 1000


def _screenshot_url(page: Any, url: str, png_path: Path, *, width: int, height: int) -> None:
    page.set_viewport_size({"width": max(width + 16, 200), "height": max(height + 16, 200)})
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_selector("#stage svg", timeout=15_000)
    loc = page.locator("#stage")
    box = loc.bounding_box()
    if box is not None:
        need_w = int(round(box["width"])) + 16
        need_h = int(round(box["height"])) + 16
        if need_w > width + 16 or need_h > height + 16:
            page.set_viewport_size({"width": max(need_w, 200), "height": max(need_h, 200)})
    png_path.parent.mkdir(parents=True, exist_ok=True)
    loc.screenshot(path=str(png_path), type="png", timeout=30_000)


def convert_svgs(
    jobs: list[tuple[Path, Path]],
    *,
    host: str = "127.0.0.1",
    preferred_port: int | None = None,
) -> dict[str, Any]:
    """Convert SVG files. Always stops HTTP server + browser."""
    report: dict[str, Any] = {
        "ok": False,
        "port": None,
        "converted": [],
        "failed": [],
        "error": "",
    }
    if not jobs:
        report["ok"] = True
        return report

    pages: dict[str, str] = {}
    queued: list[tuple[str, Path, Path]] = []
    for i, (svg_path, png_path) in enumerate(jobs):
        if not svg_path.is_file():
            report["failed"].append({"svg": str(svg_path), "error": "missing_svg"})
            continue
        key = f"v{i}"
        try:
            pages[key] = wrap_svg_html(_load_svg(svg_path))
        except OSError as e:
            report["failed"].append({"svg": str(svg_path), "error": str(e)})
            continue
        queued.append((key, svg_path, png_path))

    if not queued:
        report["error"] = "no_valid_svg"
        return report

    port = pick_free_port(host, preferred_port)
    report["port"] = port
    print(f"SVG_HTTP: port={port}", file=sys.stderr, flush=True)

    httpd: ThreadingHTTPServer | None = None
    browser = None
    try:
        from playwright.sync_api import sync_playwright

        import browser as browser_mod

        httpd = _start_server(host, port, pages)
        with sync_playwright() as p:
            browser, label = browser_mod.launch_chromium(p, headless=True)
            print(f"SVG_HTTP: browser={label}", file=sys.stderr, flush=True)
            page = browser.new_page(viewport={"width": 1400, "height": 1000})
            try:
                for key, svg_path, png_path in queued:
                    url = f"http://{host}:{port}/view?id={key}"
                    try:
                        disp_w, disp_h = svg_display_size(svg_path.read_text(encoding="utf-8"))
                        _screenshot_url(page, url, png_path, width=disp_w, height=disp_h)
                        report["converted"].append(
                            {"svg": str(svg_path), "png": str(png_path.resolve())}
                        )
                    except Exception as e:
                        report["failed"].append({"svg": str(svg_path), "error": str(e)})
            finally:
                page.close()
                browser.close()
                browser = None
    except Exception as e:
        report["error"] = str(e)
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass
            try:
                httpd.server_close()
            except Exception:
                pass
            print("SVG_HTTP: closed", file=sys.stderr, flush=True)

    report["ok"] = bool(report["converted"]) and not report["error"]
    return report


def jobs_from_dir(root: Path, *, force: bool = False) -> list[tuple[Path, Path]]:
    jobs: list[tuple[Path, Path]] = []
    for svg in sorted(root.glob("*.svg")):
        png = svg.with_suffix(".png")
        if force or not png.is_file():
            jobs.append((svg, png))
    return jobs


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Embed SVG in a local page and screenshot PNG")
    p.add_argument("--svg", type=Path, help="Input SVG")
    p.add_argument("--png", type=Path, help="Output PNG (default: same stem)")
    p.add_argument("--dir", type=Path, help="Convert *.svg in this folder")
    p.add_argument("--force", action="store_true", help="Overwrite existing PNG")
    p.add_argument("--port", type=int, default=0, help="Preferred port; 0 = env or 18765")
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    jobs: list[tuple[Path, Path]] = []
    if args.dir:
        if not args.dir.is_dir():
            print(json.dumps({"ok": False, "error": f"missing dir: {args.dir}"}), file=sys.stderr)
            return 2
        jobs.extend(jobs_from_dir(args.dir, force=args.force))
    if args.svg:
        png = args.png or args.svg.with_suffix(".png")
        jobs.append((args.svg, png))
    if not jobs:
        print(json.dumps({"ok": True, "converted": [], "message": "nothing_to_do"}))
        return 0

    preferred = args.port if args.port > 0 else preferred_port_from_env(None)
    report = convert_svgs(jobs, host=args.host, preferred_port=preferred)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    n = len(report.get("converted") or [])
    print(f"SVG_HTTP: converted={n} ok={'true' if report.get('ok') else 'false'}", file=sys.stderr, flush=True)
    if not report.get("converted") and report.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
