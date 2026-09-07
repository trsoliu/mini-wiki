# -*- coding: utf-8 -*-
"""
国知局公布站「检索 + 解析」一步完成：内存中持有结果页 HTML，**默认不落盘**。

内部调用 ``cnipa_epub_crawler.search_epub_keyword``（等同先 ``fetch_epub_result_html`` 再
``parse_search_result_html``）。

**输出约定**（便于 Agent 抓取且不触发误判降级）：

- **stdout**：**仅一行** ``EPUB_HITS_JSON:`` + JSON 数组（UTF-8，含中文标题与 ``abstract``）。
- **stderr**：``EPUB_MERGE:`` / ``EPUB_NOTE:`` / ``EPUB_HINT:`` 等为 **ASCII**。

**专利类型**：``--type invention|utility_model|design|all``（默认 ``all``）。
对应首页勾选：发明公布+发明授权 / 实用新型 / 外观设计（见 ``tools/patent_type.py``）。
第二轮收口：``--class B01J20``（发明/实用 IPC）或 ``--class 26-05``（外观 LOC），走公布站高级查询「分类号+名称」。
仅分类号保底：``--type design --class 26-05``（不跟检索词）。

用法：

  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py 词1
  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type utility_model 卡扣
  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type design 外壳造型
  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type invention --class B01J20 胺功能化
  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type design --class 26-05 台灯
  python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type design --class 26-05

需已安装：``pip install playwright``（或根目录 ``requirements.txt``）。有系统 Chrome / Edge 时不必 ``playwright install chromium``。探测：``python tools/browser.py --probe``。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_CRAWL = Path(__file__).resolve().parent
_TOOLS = _CRAWL.parent
for p in (_CRAWL, _TOOLS):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)

from patent_type import TYPE_ALL, normalize_patent_type
from stdio_utf8 import ensure_utf8_stdio

_MAX_TERMS = 8
_MAX_CLASS_CODES = 3
_MAX_TERMS_WITH_CLASS = 3


def _parse_argv(argv: list[str]) -> tuple[str, list[str], list[str]]:
    patent_type = TYPE_ALL
    rest: list[str] = []
    class_codes: list[str] = []
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
        if a in ("--class", "--ipc", "--loc") and i + 1 < len(argv):
            for part in re.split(r"[,;]+", argv[i + 1]):
                p = part.strip()
                if p and p not in class_codes:
                    class_codes.append(p)
            i += 2
            continue
        if a.startswith("--class=") or a.startswith("--ipc=") or a.startswith("--loc="):
            raw = a.split("=", 1)[1]
            for part in re.split(r"[,;]+", raw):
                p = part.strip()
                if p and p not in class_codes:
                    class_codes.append(p)
            i += 1
            continue
        rest.append(a)
        i += 1
    return patent_type, rest, class_codes


def _terms_from_argv(argv: list[str]) -> list[str]:
    terms: list[str] = []
    for a in argv:
        for part in (a or "").split():
            p = part.strip()
            if p:
                terms.append(p)
    return terms


def _dedupe_hits(hits_lists: list) -> list:
    from cnipa_epub_parse import EpubSearchHit

    seen: set[str] = set()
    out: list[EpubSearchHit] = []
    for hits in hits_lists:
        for h in hits:
            key = h.pub_number or h.link or (h.title or "")[:120]
            if key in seen:
                continue
            seen.add(key)
            out.append(h)
    return out


def _usage() -> None:
    print(
        "usage: python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py [--type invention|utility_model|design|all] [--class CODE] [term ...]",
        file=sys.stderr,
    )
    print(
        "whitespace splits to multiple terms; one browser for all terms; merge by pub_number.",
        file=sys.stderr,
    )
    print(
        "example: python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type utility_model 卡扣",
        file=sys.stderr,
    )
    print(
        "class-only: python skills/patent-disclosure/tools/crawl/cnipa_epub_search.py --type design --class 26-05",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()
    argv = argv if argv is not None else sys.argv[1:]
    patent_type, rest, class_codes = _parse_argv(argv)
    terms = _terms_from_argv(rest)
    if not terms and not class_codes:
        _usage()
        return 2
    if class_codes and len(class_codes) > _MAX_CLASS_CODES:
        print(
            "ERROR: too many --class codes (%d > %d); keep 1-3 prefixes."
            % (len(class_codes), _MAX_CLASS_CODES),
            file=sys.stderr,
        )
        return 2
    max_terms = _MAX_TERMS_WITH_CLASS if class_codes else _MAX_TERMS
    if terms and len(terms) > max_terms:
        print(
            "ERROR: too many terms after split (%d > %d); shorten or run in batches."
            % (len(terms), max_terms),
            file=sys.stderr,
        )
        return 2

    os.environ.setdefault("EPUB_WAF_MAX_WAIT_SEC", "180")

    try:
        import playwright
    except ImportError:
        print(
            "ERROR: pip install playwright  (or: pip install -r requirements.txt)",
            file=sys.stderr,
        )
        print(
            "HINT: python tools/browser.py --probe",
            file=sys.stderr,
        )
        return 1

    from cnipa_epub_crawler import search_epub_keywords
    from cnipa_epub_parse import hits_to_jsonable, suggest_class_codes

    multi = len(terms) > 1 or len(class_codes) > 1

    try:
        rows = search_epub_keywords(
            terms, patent_type=patent_type, class_codes=class_codes or None
        )
    except Exception as e:
        print("CNIPA_EPUB_ERROR:", e, file=sys.stderr)
        return 1

    last_html = rows[-1][0] if rows else ""
    all_batches = [hits for _html, hits in rows]

    if multi:
        hits = _dedupe_hits(all_batches)
        print(
            "EPUB_MERGE: terms=%d type=%s merged_hits=%d"
            % (len(terms), patent_type, len(hits)),
            file=sys.stderr,
            flush=True,
        )
    else:
        hits = all_batches[0] if all_batches else []
        print(
            "EPUB_NOTE: type=%s" % patent_type,
            file=sys.stderr,
            flush=True,
        )

    if class_codes:
        print(
            "EPUB_NOTE: class=%s" % ",".join(class_codes),
            file=sys.stderr,
            flush=True,
        )
    else:
        kind, suggested = suggest_class_codes(hits, patent_type=patent_type)
        if suggested:
            print(
                "EPUB_CLASS_HINT: kind=%s codes=%s"
                % (kind, ",".join(suggested)),
                file=sys.stderr,
                flush=True,
            )

    if not hits and last_html and len(last_html) < 20_000:
        print(
            "EPUB_HINT: 0 hits; try broader terms, --type all, or WebSearch",
            file=sys.stderr,
            flush=True,
        )

    print(
        "EPUB_NOTE: html_bytes=%d disk=0" % len(last_html),
        file=sys.stderr,
        flush=True,
    )
    print(
        "EPUB_HITS_JSON:",
        json.dumps(hits_to_jsonable(hits), ensure_ascii=False),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
