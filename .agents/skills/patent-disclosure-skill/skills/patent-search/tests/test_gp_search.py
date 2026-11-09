# -*- coding: utf-8 -*-
"""gp_search.py：参数 → 查询、报告落盘、限流退出码（不联网）。"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

import gp_search
from emit_search_report import render_search_report
from google_patents import GooglePatentsBlocked, parse_search_json

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "google_patents"


def _fixture_page(query):
    data = json.loads((FIXTURES / "search.json").read_text(encoding="utf-8"))
    return parse_search_json(data, num=query.num, page=query.page)


class _Patch:
    def __init__(self, **attrs) -> None:
        self.attrs = attrs

    def __enter__(self):
        self.old = {k: getattr(gp_search, k) for k in self.attrs}
        for k, v in self.attrs.items():
            setattr(gp_search, k, v)
        return self

    def __exit__(self, *_a):
        for k, v in self.old.items():
            setattr(gp_search, k, v)


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = gp_search.main(argv)
    return code, out.getvalue(), err.getvalue()


class GpSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_env = os.environ.get("PATENT_SEARCH_OUTPUT_DIR")
        os.environ["PATENT_SEARCH_OUTPUT_DIR"] = self.tmp.name

    def tearDown(self) -> None:
        if self.old_env is None:
            os.environ.pop("PATENT_SEARCH_OUTPUT_DIR", None)
        else:
            os.environ["PATENT_SEARCH_OUTPUT_DIR"] = self.old_env
        self.tmp.cleanup()

    def test_default_num_is_10_and_page_is_one_based(self) -> None:
        seen = []

        def fake_search(query, **_k):
            seen.append(query)
            return _fixture_page(query)

        with _Patch(search=fake_search):
            code, out, _err = _run(["-q", "(battery) (thermal runaway)", "--country", "US,JP", "--after", "2020"])
        self.assertEqual(code, 0)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].num, 10)
        self.assertEqual(seen[0].page, 0)
        payload = json.loads(out.split("GP_SEARCH_JSON:", 1)[1].strip())
        self.assertEqual(payload["source_id"], "google_patents")
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["returned"], 3)
        self.assertEqual(payload["query"]["countries"], ["US", "JP"])
        self.assertEqual(payload["query"]["after"], "20200101")
        self.assertIn("不得写成完整清单", payload["completeness_note"])
        self.assertIn("country=US,JP", payload["web_url"])
        hit = payload["hits"][0]
        self.assertEqual(hit["pub_number"], "US12394859B2")
        self.assertEqual(hit["link"], "https://patents.google.com/patent/US12394859B2/en")
        md_path = Path(out.split("GP_SEARCH_MD:", 1)[1].split("\n", 1)[0].strip())
        text = md_path.read_text(encoding="utf-8")
        self.assertIn("# 海外检索", text)
        self.assertIn("Google Patents", text)
        self.assertIn("| 局别 | US；JP |", text)
        self.assertIn("命中片段", text)

    def test_page_and_filters_pass_through(self) -> None:
        seen = []

        def fake_search(query, **_k):
            seen.append(query)
            return _fixture_page(query)

        with _Patch(search=fake_search):
            code, _out, _err = _run(
                ["-q", "lamp", "--type", "design", "--status", "grant", "--page", "3", "--num", "20"]
            )
        self.assertEqual(code, 0)
        q = seen[0]
        self.assertEqual((q.patent_type, q.status, q.page, q.num), ("DESIGN", "GRANT", 2, 20))

    def test_blocked_exits_4_without_report(self) -> None:
        def blocked(*_a, **_k):
            raise GooglePatentsBlocked("Google Patents 限流（HTTP 503），已停止请求", status=503)

        with _Patch(search=blocked):
            code, out, err = _run(["-q", "battery"])
        self.assertEqual(code, gp_search.EXIT_BLOCKED)
        self.assertIn("GP_SEARCH_ERROR: reason=blocked status=503", err)
        self.assertNotIn("GP_SEARCH_MD:", out)
        self.assertEqual(list(Path(self.tmp.name).glob("*.md")), [])

    def test_bad_args(self) -> None:
        code, _out, err = _run([])
        self.assertEqual(code, 2)
        self.assertIn("至少提供", err)
        code, _out, err = _run(["-q", "x", "--country", "USA"])
        self.assertEqual(code, 2)
        code, _out, err = _run(["-q", "x", "--page", "0"])
        self.assertEqual(code, 2)

    def test_cnipa_report_unchanged_without_source_id(self) -> None:
        text = render_search_report({"hits": [], "query": {"title": "数据处理"}})
        self.assertIn("# 著录检索", text)
        self.assertNotIn("海外检索", text)


if __name__ == "__main__":
    unittest.main()
