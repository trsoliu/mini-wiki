#!/usr/bin/env python
"""把源图做成黑白申请附图 PNG（按内容截取，不画图号、不铺 A4 留白）。

仅用于实用新型升格与发明点名图。外观禁用（原样复制交底图，不合格只记问题清单）。

用法：
  python tools/compose_application_figure.py --source 线稿.png --fig 1 --out-dir figures
  python tools/compose_application_figure.py --source 场景.png --fig 3 --out-dir figures --abstract
"""
from __future__ import annotations

import argparse
import html
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote
from urllib.request import pathname2url

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stdio_utf8 import ensure_utf8_stdio


def _file_url(path: Path) -> str:
    return "file:" + pathname2url(str(path.resolve()))


def compose_sheet(source: Path, fig_no: int, out_dir: Path, *, abstract: bool = False) -> dict[str, Any]:
    source = source.expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not source.is_file():
        raise FileNotFoundError(source)
    png_path = out_dir / f"图{fig_no}.png"
    svg_path = out_dir / f"图{fig_no}.svg"
    src_url = html.escape(_file_url(source), quote=True)
    html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  html,body{{margin:0;background:#fff;}}
  .art{{display:inline-block;background:#fff;}}
  .art img{{max-width:170mm;max-height:220mm;object-fit:contain;
            filter:grayscale(1) contrast(1.05);display:block;}}
</style></head>
<body>
<div class="art"><img src="{src_url}" alt=""/></div>
</body></html>
"""
    png_ok = _screenshot_html(html_doc, png_path)
    svg_path.write_text(_wrapper_svg(png_path.name if png_ok else source.name), encoding="utf-8")
    written = [str(svg_path)]
    if png_ok:
        written.append(str(png_path))
        if abstract:
            abs_path = out_dir / "摘要附图.png"
            shutil.copyfile(png_path, abs_path)
            written.append(str(abs_path))
    elif source.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        shutil.copyfile(source, png_path)
        written.append(str(png_path))
        png_ok = True
        if abstract:
            abs_path = out_dir / "摘要附图.png"
            shutil.copyfile(png_path, abs_path)
            written.append(str(abs_path))
    return {"svg": str(svg_path), "png_ok": bool(png_ok), "written": written}


def _wrapper_svg(image_href: str) -> str:
    href = html.escape(quote(image_href), quote=True)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="170mm" height="120mm" viewBox="0 0 170 120">'
        f'<image x="0" y="0" width="170" height="120" preserveAspectRatio="xMidYMid meet" '
        f'xlink:href="{href}"/></svg>\n'
    )


def _screenshot_html(html_doc: str, png_path: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as pw:
        for channel in ("chrome", "msedge", None):
            kwargs: dict[str, Any] = {"headless": True}
            if channel:
                kwargs["channel"] = channel
            try:
                browser = pw.chromium.launch(**kwargs)
            except Exception:
                continue
            try:
                page = browser.new_page(viewport={"width": 1400, "height": 1800}, device_scale_factor=2)
                page.set_content(html_doc, wait_until="load")
                loc = page.locator(".art")
                loc.first.wait_for(timeout=8000)
                loc.first.screenshot(path=str(png_path), type="png")
                return True
            except Exception:
                continue
            finally:
                browser.close()
    return False


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--fig", required=True, type=int)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--abstract", action="store_true")
    args = parser.parse_args()
    try:
        result = compose_sheet(args.source, args.fig, args.out_dir, abstract=args.abstract)
    except FileNotFoundError as exc:
        print(f"APPLICATION_FIG: ok=0 svg=0 png=0 png_fail=1")
        print(f"源图不存在：{exc}", file=sys.stderr)
        return 1
    png_ok = 1 if result["png_ok"] else 0
    print(f"APPLICATION_FIG: ok=1 svg=1 png={png_ok} png_fail={0 if png_ok else 1}")
    for path in result["written"]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
