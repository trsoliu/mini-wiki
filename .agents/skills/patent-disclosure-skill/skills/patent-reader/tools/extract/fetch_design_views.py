#!/usr/bin/env python
"""
中国外观设计视图取证（本包取证入口）。

背景：外观设计（CN…S）在 Google Patents 上常无 PDF CDN / 附图；
直连 ``epub.cnipa.gov.cn/patent/{公开号}`` 也会被 WAF 拦成空页。

可行链路（本脚本固化）：
  1) 复用本包 ``tools/crawl/cnipa_epub_*``：Playwright 过公布站首页 WAF，按公开号检索（``--type design``）
  2) 同浏览器会话打开 ``/patent/{公开号}`` 详情页，从 HTML 解析 ``/imgs/.../NNNNNN.jpg`` 目录
  3) 在同会话内对该目录做序号探测（``1..SEQ_MAX_INDEX_CAP``，默认上限 **50**；
     连续 miss 亦停），下载全尺寸视图——双终止条件，避免死循环 / 滥请求
  4) 同时写出简要说明（来自检索命中 abstract）与 ``figures/manifest.json``

用法：
  python skills/patent-reader/tools/extract/fetch_design_views.py \\
    --pub CN309939145S -o outputs/patent_reader/read-CN309939145S-YYYYMMDDHHmm

  # → {outdir}/figures/images/view_001.jpg …
  # → {outdir}/figures/manifest.json
  # → {outdir}/source/{PUB}_design_brief.json
  # → {outdir}/fetch_design_status.json

依赖：与国知局爬虫相同（Playwright + Chromium），见本包 tools/crawl/requirements-cnipa.txt
"""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys

_PR_ROOT = _Path(__file__).resolve().parents[1]
_CRAWL = _PR_ROOT / "crawl"
for _p in (_PR_ROOT, _CRAWL):
    s = str(_p)
    if s not in _sys.path:
        _sys.path.insert(0, s)

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from patent_type import TYPE_DESIGN, resolve_reader_patent_type

try:
    from cnipa_epub_crawler import (
        _launch_browser,
        _new_context,
        search_epub_keyword_with_page,
    )
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "需要公布站轻量爬虫与 Playwright。请先：\n"
        "  pip install playwright\n"
        "  python tools/browser.py --probe\n"
        "  （无 Chrome/Edge 时才：python -m playwright install chromium）\n"
        f"导入错误: {e}"
    ) from e

from playwright.sync_api import sync_playwright

EPUB_BASE = "http://epub.cnipa.gov.cn"
IMG_PATH_RE = re.compile(
    r"(/imgs/[^\"'\s>]+/)(\d{6})(?:_thumb)?\.(jpg|jpeg|png)",
    re.I,
)
SKIP_URL_SUBSTR = (
    "logo",
    "icon",
    "waiting",
    "loading",
    "controls",
    "bg-pic",
    "jiucuo",
    "gstatic",
)

# 序号探测硬上限（含）：无论 CLI 传多大，都不会超过此值，防止死循环 / 打爆站点
SEQ_MAX_INDEX_CAP = 50
# 连续 miss（404/空体等）达到此数且已有成功下载时提前停止
SEQ_STOP_AFTER_MISSES = 3


def normalize_pub(pub: str) -> str:
    return re.sub(r"\s+", "", (pub or "").strip()).upper()


def _is_design_pub(pub: str) -> bool:
    info = resolve_reader_patent_type(pub=pub)
    return info.get("patent_type") == TYPE_DESIGN or pub.upper().endswith("S")


def _pick_hit(hits: list, pub: str) -> Any | None:
    pub_u = normalize_pub(pub)
    for h in hits:
        pn = normalize_pub(getattr(h, "pub_number", "") or "")
        link = (getattr(h, "link", "") or "").upper()
        if pn == pub_u or pub_u in link:
            return h
    return hits[0] if hits else None


def _folder_from_html(html: str) -> tuple[str, str] | None:
    """Return (folder_path_with_trailing_slash, ext) e.g. ('/imgs/.../130001/', 'jpg')."""
    m = IMG_PATH_RE.search(html or "")
    if not m:
        return None
    return m.group(1), m.group(3).lower()


def _clamp_max_index(max_index: int | None) -> int:
    """Clamp probe upper bound into ``[1, SEQ_MAX_INDEX_CAP]``."""
    if max_index is None:
        return SEQ_MAX_INDEX_CAP
    try:
        n = int(max_index)
    except (TypeError, ValueError):
        return SEQ_MAX_INDEX_CAP
    if n < 1:
        return 1
    return min(n, SEQ_MAX_INDEX_CAP)


def _download_seq(
    page,
    *,
    folder: str,
    ext: str,
    referer: str,
    out_dir: Path,
    max_index: int | None = None,
    stop_after_misses: int = SEQ_STOP_AFTER_MISSES,
    include_thumbs: bool = False,
) -> list[dict[str, Any]]:
    """Probe NNNNNN.jpg in folder; stop on consecutive misses or index cap."""
    cap = _clamp_max_index(max_index)
    stop_after = max(1, int(stop_after_misses or SEQ_STOP_AFTER_MISSES))
    saved: list[dict[str, Any]] = []
    misses = 0
    view_i = 0
    for i in range(1, cap + 1):
        rel = f"{folder}{i:06d}.{ext}"
        url = urljoin(EPUB_BASE + "/", rel.lstrip("/"))
        try:
            resp = page.request.get(url, headers={"Referer": referer}, timeout=60000)
            body = resp.body() if resp.ok else b""
            ct = (resp.headers.get("content-type") or "").lower()
            ok = (
                resp.ok
                and len(body) > 2000
                and ("image" in ct or ext in ("jpg", "jpeg", "png"))
            )
        except Exception:
            ok = False
            body = b""
            ct = ""
            url = urljoin(EPUB_BASE + "/", rel.lstrip("/"))

        if not ok:
            misses += 1
            # 已有成功图时：连续 miss → 提前停；从头全 miss 则继续扫到 cap，避免误杀
            if misses >= stop_after and saved:
                break
            continue

        misses = 0
        view_i += 1
        name = f"view_{view_i:03d}.{ext if ext != 'jpeg' else 'jpg'}"
        path = out_dir / name
        path.write_bytes(body)
        saved.append(
            {
                "fig": view_i,
                "label": f"视图{view_i}",
                "filename": name,
                "relative_path": f"images/{name}",
                "bytes": len(body),
                "url": url,
                "role": "view",
                "kind": "lineart_or_photo",
                "decision": "insert",
                "quality": "usable",
                "source_index": i,
            }
        )

        if include_thumbs:
            turl = urljoin(
                EPUB_BASE + "/",
                f"{folder}{i:06d}_thumb.{ext}".lstrip("/"),
            )
            try:
                tr = page.request.get(turl, headers={"Referer": referer}, timeout=30000)
                tb = tr.body() if tr.ok else b""
                if tr.ok and len(tb) > 800:
                    tname = f"thumb_{view_i:03d}.{ext if ext != 'jpeg' else 'jpg'}"
                    (out_dir / tname).write_bytes(tb)
                    saved.append(
                        {
                            "fig": None,
                            "label": f"缩略图{view_i}",
                            "filename": tname,
                            "relative_path": f"images/{tname}",
                            "bytes": len(tb),
                            "url": turl,
                            "role": "thumb",
                            "decision": "reference",
                            "quality": "thumb",
                            "source_index": i,
                        }
                    )
            except Exception:
                pass

    return saved


def fetch_design_views(
    pub: str,
    outdir: Path,
    *,
    max_index: int | None = None,
    include_thumbs: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    pub_u = normalize_pub(pub)
    if not _is_design_pub(pub_u):
        raise ValueError(
            f"{pub_u} 不像外观设计公开号（种类码应为 S）。"
            "发明/实用新型请用 fetch_patent_pdf.py。"
        )

    outdir = Path(outdir)
    img_dir = outdir / "figures" / "images"
    source_dir = outdir / "source"
    img_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    type_info = resolve_reader_patent_type(pub=pub_u)
    status: dict[str, Any] = {
        "ok": False,
        "pub": pub_u,
        "patent_type": type_info.get("patent_type"),
        "patent_type_label_zh": type_info.get("label_zh"),
        "patent_type_source": type_info.get("source"),
        "method": "cnipa_epub_session_detail_seq",
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }

    with sync_playwright() as p:
        browser = _launch_browser(p)
        ctx = _new_context(browser)
        try:
            page = ctx.new_page()
            result_html, hits = search_epub_keyword_with_page(
                page, pub_u, patent_type=TYPE_DESIGN
            )
            hit = _pick_hit(hits, pub_u)
            if not hit:
                raise FileNotFoundError(
                    f"国知局公布站未命中 {pub_u}（type=design）。请核对公开号或稍后重试。"
                )

            brief = {
                "pub_number": pub_u,
                "title": getattr(hit, "title", None),
                "abstract": getattr(hit, "abstract", None),
                "link": getattr(hit, "link", None) or f"{EPUB_BASE}/patent/{pub_u}",
                "source": "cnipa_epub_crawler",
            }
            brief_path = source_dir / f"{pub_u}_design_brief.json"
            brief_path.write_text(
                json.dumps(brief, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            status["brief_path"] = str(brief_path)
            status["title"] = brief["title"]
            status["cnipa_link"] = brief["link"]

            detail_url = brief["link"]
            page.goto(detail_url, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(4000)
            detail_html = page.content()
            (source_dir / f"{pub_u}_cnipa_detail.html").write_text(
                detail_html, encoding="utf-8"
            )

            folder_ext = _folder_from_html(detail_html)
            if not folder_ext:
                # fallback: live DOM
                for src in page.eval_on_selector_all(
                    "img", "els => els.map(e => e.currentSrc || e.src || '')"
                ):
                    if not src or any(s in src for s in SKIP_URL_SUBSTR):
                        continue
                    m = IMG_PATH_RE.search(src)
                    if m:
                        folder_ext = (m.group(1), m.group(3).lower())
                        break
            if not folder_ext:
                raise FileNotFoundError(
                    f"已打开详情页但未解析到 /imgs/ 视图路径：{detail_url}"
                )

            folder, ext = folder_ext
            status["image_folder"] = folder
            status["image_ext"] = ext

            if force:
                for old in img_dir.glob("view_*.*"):
                    old.unlink(missing_ok=True)
                for old in img_dir.glob("thumb_*.*"):
                    old.unlink(missing_ok=True)

            probe_cap = _clamp_max_index(max_index)
            figures = _download_seq(
                page,
                folder=folder,
                ext=ext,
                referer=page.url,
                out_dir=img_dir,
                max_index=probe_cap,
                stop_after_misses=SEQ_STOP_AFTER_MISSES,
                include_thumbs=include_thumbs,
            )
            if not figures:
                raise FileNotFoundError(
                    f"详情页目录 {folder} 序号探测未下载到视图（可能会话失效，请重试）。"
                )

            status["seq_max_index_cap"] = SEQ_MAX_INDEX_CAP
            status["seq_probe_cap"] = probe_cap
            status["seq_stop_after_misses"] = SEQ_STOP_AFTER_MISSES

            manifest = {
                "source_pdf": None,
                "source": "cnipa_epub_design_views",
                "pub_number": pub_u,
                "count": len([f for f in figures if f.get("role") == "view"]),
                "insert_count": len(
                    [f for f in figures if f.get("decision") == "insert"]
                ),
                "placeholder_count": 0,
                "include_review": False,
                "figures": figures,
                "brief_ref": str(brief_path.relative_to(outdir)).replace("\\", "/"),
            }
            man_path = outdir / "figures" / "manifest.json"
            man_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            status.update(
                {
                    "ok": True,
                    "detail_url": page.url,
                    "figures_dir": str(img_dir),
                    "manifest_path": str(man_path),
                    "view_count": manifest["count"],
                    "bytes_total": sum(f.get("bytes") or 0 for f in figures),
                }
            )
            return status
        finally:
            ctx.close()
            browser.close()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pub", required=True, help="外观设计公开号，如 CN309939145S")
    ap.add_argument(
        "-o",
        "--outdir",
        type=Path,
        required=True,
        help="RUN 目录；视图写入 {outdir}/figures/images/",
    )
    ap.add_argument(
        "--max-index",
        type=int,
        default=SEQ_MAX_INDEX_CAP,
        help=(
            f"目录内最大探测序号（默认 {SEQ_MAX_INDEX_CAP}；"
            f"硬上限 SEQ_MAX_INDEX_CAP={SEQ_MAX_INDEX_CAP}，更大值会被截断）"
        ),
    )
    ap.add_argument(
        "--include-thumbs",
        action="store_true",
        help="同时下载 *_thumb.jpg（默认否）",
    )
    ap.add_argument("--force", action="store_true", help="清空已有 view_/thumb_ 后重下")
    ap.add_argument(
        "--status-json",
        type=Path,
        default=None,
        help="状态 JSON（默认 {outdir}/fetch_design_status.json）",
    )
    args = ap.parse_args(argv)

    out_json = args.status_json or (args.outdir / "fetch_design_status.json")
    args.outdir.mkdir(parents=True, exist_ok=True)

    try:
        status = fetch_design_views(
            args.pub,
            args.outdir,
            max_index=args.max_index,
            include_thumbs=args.include_thumbs,
            force=args.force,
        )
    except Exception as e:
        err = {
            "ok": False,
            "pub": normalize_pub(args.pub),
            "error": f"{type(e).__name__}: {e}",
            "hint": (
                "确认公开号为 CN…S；安装 Playwright Chromium；"
                "网络需能访问 epub.cnipa.gov.cn；可稍后重试。"
            ),
        }
        out_json.write_text(
            json.dumps(err, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"FAIL {err['error']}", file=sys.stderr)
        print(f"HINT: {err['hint']}", file=sys.stderr)
        print(f"FETCH_DESIGN_STATUS: {out_json}")
        return 1

    out_json.write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"OK views={status['view_count']} dir={status['figures_dir']} "
        f"bytes={status['bytes_total']}"
    )
    if status.get("title"):
        print(f"TITLE: {status['title']}")
    if status.get("patent_type"):
        print(
            f"PATENT_TYPE: {status['patent_type']} "
            f"({status.get('patent_type_label_zh')})"
        )
    print(f"MANIFEST: {status['manifest_path']}")
    print(f"FETCH_DESIGN_STATUS: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
