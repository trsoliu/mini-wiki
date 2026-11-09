# -*- coding: utf-8 -*-
"""google_patents 子目录：查询串、结果与详情页解析、快速失败（不联网）。

本文件在 patent-search 与 patent-reader 的 tests/ 各有一份，内容一致。
"""
from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
import urllib.parse
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

import google_patents.api as gp_api
import google_patents.client as gp_client
from google_patents import (
    GooglePatentsBlocked,
    GooglePatentsNotFound,
    GooglePatentsUnavailable,
    SearchQuery,
    build_q,
    inner_query_string,
    normalize_date,
    parse_detail_html,
    parse_search_json,
    search,
    split_publication_number,
    validate_query,
    web_url,
    xhr_url,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "google_patents"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class _Resp(io.BytesIO):
    def __init__(self, body: bytes, url: str = "https://patents.google.com/x") -> None:
        super().__init__(body)
        self._url = url

    def geturl(self) -> str:
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        self.close()


class _PatchAttr:
    def __init__(self, obj, name: str, value) -> None:
        self.obj, self.name, self.value = obj, name, value

    def __enter__(self):
        self.old = getattr(self.obj, self.name)
        setattr(self.obj, self.name, self.value)
        return self

    def __exit__(self, *_a):
        setattr(self.obj, self.name, self.old)


class QueryTests(unittest.TestCase):
    def test_inner_keeps_colon_and_comma(self) -> None:
        q = SearchQuery(keywords="(battery) (thermal runaway)", countries=["US", "jp"], after="2020-01-01")
        inner = inner_query_string(q)
        self.assertIn("q=%28battery%29%20%28thermal%20runaway%29", inner)
        self.assertIn("country=US,JP", inner)
        self.assertIn("after=priority:20200101", inner)
        self.assertIn("num=10", inner)
        self.assertNotIn("page=", inner)

    def test_xhr_url_encodes_inner_once_more(self) -> None:
        q = SearchQuery(keywords="battery", countries=["US"])
        url = xhr_url(q)
        self.assertTrue(url.startswith("https://patents.google.com/xhr/query?url="))
        self.assertTrue(url.endswith("&exp="))
        inner = urllib.parse.unquote(url.split("url=", 1)[1].rsplit("&exp=", 1)[0])
        self.assertEqual(inner, inner_query_string(q))

    def test_web_url_uses_same_params(self) -> None:
        q = SearchQuery(keywords="lamp", patent_type="DESIGN", page=1)
        self.assertEqual(web_url(q), "https://patents.google.com/?" + inner_query_string(q))
        self.assertIn("type=DESIGN", web_url(q))
        self.assertIn("page=1", web_url(q))

    def test_build_q_fields(self) -> None:
        q = SearchQuery(
            keywords="battery",
            title="gas sensor",
            abstract="thermal runaway",
            claims="venting",
            cpc=["H01M10/48/low", "G01N33/00"],
        )
        self.assertEqual(
            build_q(q),
            "battery TI=(gas sensor) AB=(thermal runaway) CL=(venting) "
            "(CPC=H01M10/48/low OR CPC=G01N33/00)",
        )

    def test_list_params_and_dates(self) -> None:
        q = SearchQuery(
            assignees=["Rivian", "Tesla"],
            inventors=["Mark Pokora"],
            status="grant",
            date_field="publication",
            after="2020",
            before="2022-06",
            sort="new",
            num=50,
        )
        inner = inner_query_string(q)
        self.assertIn("assignee=Rivian,Tesla", inner)
        self.assertIn("inventor=Mark%20Pokora", inner)
        self.assertIn("status=GRANT", inner)
        self.assertIn("before=publication:20220630", inner)
        self.assertIn("after=publication:20200101", inner)
        self.assertIn("sort=new", inner)
        self.assertIn("num=50", inner)

    def test_normalize_date(self) -> None:
        self.assertEqual(normalize_date("2020"), "20200101")
        self.assertEqual(normalize_date("2020", end=True), "20201231")
        self.assertEqual(normalize_date("2021-03-31"), "20210331")
        self.assertEqual(normalize_date("2024-02", end=True), "20240229")
        self.assertEqual(normalize_date(""), "")
        with self.assertRaises(ValueError):
            normalize_date("20-1")

    def test_validate(self) -> None:
        with self.assertRaises(ValueError):
            validate_query(SearchQuery())
        with self.assertRaises(ValueError):
            validate_query(SearchQuery(keywords="x", countries=["USA"]))
        with self.assertRaises(ValueError):
            validate_query(SearchQuery(keywords="x", num=101))
        with self.assertRaises(ValueError):
            validate_query(SearchQuery(keywords="x", patent_type="UTILITY"))
        validate_query(SearchQuery(assignees=["Rivian"]))


class ResultsTests(unittest.TestCase):
    def test_parse_fixture(self) -> None:
        page = parse_search_json(json.loads(_fixture("search.json")), num=10, page=0)
        self.assertEqual(page.total_results, 16820)
        self.assertEqual(page.total_pages, 95)
        self.assertEqual(len(page.hits), 3)
        first = page.hits[0]
        self.assertEqual(first.publication_number, "US12394859B2")
        self.assertEqual((first.country, first.kind), ("US", "B2"))
        self.assertNotIn("<b>", first.title)
        self.assertEqual(first.url, "https://patents.google.com/patent/US12394859B2/en")
        self.assertIn("JP", first.family_countries)
        with_pdf = [h for h in page.hits if h.pdf_url]
        self.assertTrue(with_pdf)
        self.assertTrue(with_pdf[0].pdf_url.startswith("https://patentimages.storage.googleapis.com/"))
        self.assertTrue(any(h.country == "JP" for h in page.hits))

    def test_split_publication_number(self) -> None:
        self.assertEqual(split_publication_number("US11450918B2"), ("US", "11450918", "B2"))
        self.assertEqual(split_publication_number("usd1032042s1"), ("US", "D1032042", "S1"))
        self.assertEqual(split_publication_number("JP2019026983A"), ("JP", "2019026983", "A"))
        self.assertEqual(split_publication_number("WO2022005144A2"), ("WO", "2022005144", "A2"))


class DetailTests(unittest.TestCase):
    def test_us_detail(self) -> None:
        d = parse_detail_html(_fixture("detail_US11450918B2.html"), pub="US11450918B2")
        self.assertEqual(d.publication_number, "US11450918B2")
        self.assertEqual((d.country, d.kind), ("US", "B2"))
        self.assertEqual(d.title, "Battery module gas sensor for battery cell monitoring")
        self.assertEqual(d.priority_date, "2019-02-20")
        self.assertEqual(d.filing_date, "2020-02-20")
        self.assertEqual(d.inventors, ["Mark Pokora"])
        self.assertEqual(d.assignees, ["Rivian IP Holdings LLC"])
        self.assertIn("H01M10/0525", d.cpc)
        self.assertNotIn("G", d.cpc)
        self.assertTrue(d.pdf_url.endswith("US11450918.pdf"))
        self.assertTrue(d.abstract.startswith("Battery monitoring systems"))
        self.assertEqual(d.translated_from, "")
        self.assertEqual(len(d.claims), 6)
        c1, c2 = d.claims[0], d.claims[1]
        self.assertTrue(c1.is_independent)
        self.assertTrue(c1.text.startswith("A system, comprising:"))
        self.assertEqual(c2.depends_on, [1])
        self.assertFalse(c2.is_independent)
        self.assertEqual(d.claims[5].depends_on, [5])
        self.assertEqual(c1.text_original, "")
        self.assertEqual(len(d.description), 3)
        self.assertTrue(d.description["0001"].startswith("This disclosure claims the benefit"))
        self.assertEqual(d.description_original, {})

    def test_jp_machine_translated_detail(self) -> None:
        d = parse_detail_html(_fixture("detail_JP7371268B2.html"), pub="JP7371268B2")
        self.assertEqual((d.country, d.kind), ("JP", "B2"))
        self.assertEqual(d.translated_from, "Japanese")
        self.assertEqual(len(d.claims), 3)
        c1 = d.claims[0]
        self.assertTrue(c1.text.startswith("A lithium ion secondary battery"))
        self.assertIn("リチウムイオン二次電池", c1.text_original)
        self.assertNotIn("リチウム", c1.text)
        self.assertEqual(d.claims[1].depends_on, [1])
        self.assertEqual(d.claims[2].depends_on, [1, 2])
        self.assertEqual(len(d.description), 3)
        self.assertEqual(set(d.description_original), set(d.description))
        self.assertTrue(d.pdf_url.endswith("JP7371268B2.pdf"))


class FailFastTests(unittest.TestCase):
    def _http_error(self, code: int):
        def opener(req, **_k):
            raise urllib.error.HTTPError(req.full_url, code, "x", {}, None)

        return opener

    def test_503_raises_blocked_once(self) -> None:
        calls: list[str] = []

        def opener(req, **_k):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 503, "x", {}, None)

        with _PatchAttr(gp_client, "_urlopen", opener):
            with self.assertRaises(GooglePatentsBlocked) as cm:
                search(SearchQuery(keywords="battery"))
        self.assertEqual(cm.exception.status, 503)
        self.assertEqual(len(calls), 1)

    def test_429_raises_blocked(self) -> None:
        with _PatchAttr(gp_client, "_urlopen", self._http_error(429)):
            with self.assertRaises(GooglePatentsBlocked):
                gp_client.fetch_text("https://patents.google.com/patent/US1/en")

    def test_404_raises_not_found(self) -> None:
        with _PatchAttr(gp_client, "_urlopen", self._http_error(404)):
            with self.assertRaises(GooglePatentsNotFound):
                gp_client.fetch_text("https://patents.google.com/patent/US1/en")

    def test_sorry_page_raises_blocked(self) -> None:
        body = b"<html><head><title>Sorry...</title></head><body>x</body></html>"
        with _PatchAttr(gp_client, "_urlopen", lambda *_a, **_k: _Resp(body)):
            with self.assertRaises(GooglePatentsBlocked):
                search(SearchQuery(keywords="battery"))

    def test_network_error_is_unavailable(self) -> None:
        def opener(req, **_k):
            raise urllib.error.URLError("down")

        with _PatchAttr(gp_client, "_urlopen", opener):
            with self.assertRaises(GooglePatentsUnavailable):
                gp_client.fetch_text("https://patents.google.com/")

    def test_search_parses_body(self) -> None:
        body = _fixture("search.json")
        with _PatchAttr(gp_api, "fetch_text", lambda *_a, **_k: body):
            page = search(SearchQuery(keywords="battery", countries=["US", "JP"]))
        self.assertEqual(len(page.hits), 3)

    def test_fetch_detail_parses_body(self) -> None:
        body = _fixture("detail_US11450918B2.html")
        with _PatchAttr(gp_api, "fetch_text", lambda *_a, **_k: body):
            d = gp_api.fetch_detail("US11450918B2")
        self.assertEqual(d.url, "https://patents.google.com/patent/US11450918B2/en")
        self.assertEqual(len(d.claims), 6)


if __name__ == "__main__":
    unittest.main()
