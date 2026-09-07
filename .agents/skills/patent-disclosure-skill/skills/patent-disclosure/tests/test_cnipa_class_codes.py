# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PKG = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PKG / "tools" / "crawl"))
sys.path.insert(0, str(PKG / "tools"))

from cnipa_epub_crawler import apply_epub_advanced_type_filter
from cnipa_epub_parse import (
    EpubSearchHit,
    backfill_hits_for_disclosure,
    extract_class_codes_from_html,
    ipc_search_prefix,
    parse_search_result_html,
    select_hits_for_disclosure,
    suggest_class_codes,
)
from cnipa_epub_search import _parse_argv, main as search_main
from patent_type import google_patents_websearch_query

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ClassCodeParseTests(unittest.TestCase):
    def test_ipc_from_result_card(self) -> None:
        html = (_FIXTURES / "epub_item_ipc.html").read_text(encoding="utf-8")
        ipc, loc = extract_class_codes_from_html(html)
        self.assertIn("B01J20/26", ipc)
        self.assertIn("B01D53/02", ipc)
        self.assertFalse(loc)
        hits = parse_search_result_html(html)
        self.assertTrue(hits)
        self.assertIn("B01J20/26", hits[0].ipc_codes)

    def test_loc_from_design_card(self) -> None:
        html = (_FIXTURES / "epub_item_loc.html").read_text(encoding="utf-8")
        ipc, loc = extract_class_codes_from_html(html)
        self.assertEqual(loc, ["26-05"])
        self.assertFalse(ipc)
        hits = parse_search_result_html(html)
        self.assertEqual(hits[0].loc_codes, ["26-05"])

    def test_agent_style_not_treated_as_loc(self) -> None:
        html = '<div style="line-height:24px">无分类号</div>'
        ipc, loc = extract_class_codes_from_html(html)
        self.assertEqual(ipc, [])
        self.assertEqual(loc, [])

    def test_suggest_ipc_prefix(self) -> None:
        hits = [
            EpubSearchHit("x", ipc_codes=["B01J20/26", "B01D53/02"]),
            EpubSearchHit("y", ipc_codes=["B01J20/30"]),
        ]
        kind, codes = suggest_class_codes(hits, patent_type="invention")
        self.assertEqual(kind, "ipc")
        self.assertEqual(codes[0], "B01J20")
        self.assertEqual(ipc_search_prefix("B01J20/26"), "B01J20")

    def test_suggest_loc_for_design(self) -> None:
        hits = [EpubSearchHit("x", loc_codes=["26-05", "26-05"])]
        kind, codes = suggest_class_codes(hits, patent_type="design")
        self.assertEqual(kind, "loc")
        self.assertEqual(codes, ["26-05"])

    def test_select_prefers_matching_class(self) -> None:
        keep = EpubSearchHit(
            "a",
            title="胺功能化吸附剂",
            ipc_codes=["B01J20/26"],
            abstract="二氧化碳",
        )
        noise = EpubSearchHit(
            "b",
            title="无关调度系统",
            ipc_codes=["G06F9/50"],
        )
        picked = select_hits_for_disclosure(
            [noise, keep],
            class_prefixes=["B01J20"],
            core_terms=["胺", "吸附"],
            limit=1,
        )
        self.assertEqual(picked[0].title, keep.title)


def _hit(
    pub: str,
    title: str,
    *,
    ipc: list[str] | None = None,
    loc: list[str] | None = None,
) -> EpubSearchHit:
    return EpubSearchHit(
        "",
        title=title,
        pub_number=pub,
        ipc_codes=list(ipc or []),
        loc_codes=list(loc or []),
    )


class BackfillTests(unittest.TestCase):
    def test_primary_enough(self) -> None:
        primary = [_hit(f"CN{i}", "胺吸附", ipc=["B01J20/26"]) for i in range(4)]
        hits, reason = backfill_hits_for_disclosure(
            primary,
            [_hit("CN99", "调度", ipc=["G06F9/50"])],
            class_prefixes=["B01J20"],
            core_terms=["胺"],
            min_keep=4,
            limit=6,
        )
        self.assertEqual(reason, "primary_enough")
        self.assertEqual(len(hits), 4)
        self.assertEqual([h.pub_number for h in hits], [f"CN{i}" for i in range(4)])

    def test_backfill_same_class_skips_off_class(self) -> None:
        primary = [
            _hit("CN1", "胺功能化", ipc=["B01J20/26"]),
            _hit("CN2", "胺接枝", ipc=["B01J20/30"]),
        ]
        pool = [
            _hit("CN1", "胺功能化", ipc=["B01J20/26"]),
            _hit("CN3", "固体胺吸附剂", ipc=["B01J20/22"]),
            _hit("CN4", "再生吸附", ipc=["B01J20/34"]),
            _hit("CN9", "调度系统", ipc=["G06F9/50"]),
        ]
        hits, reason = backfill_hits_for_disclosure(
            primary,
            pool,
            class_prefixes=["B01J20"],
            core_terms=["胺", "吸附"],
            min_keep=4,
            limit=6,
        )
        self.assertEqual(reason, "backfilled")
        pubs = [h.pub_number for h in hits]
        self.assertEqual(pubs[:2], ["CN1", "CN2"])
        self.assertIn("CN3", pubs)
        self.assertIn("CN4", pubs)
        self.assertNotIn("CN9", pubs)
        self.assertGreaterEqual(len(hits), 4)

    def test_still_short_does_not_invent(self) -> None:
        primary = [_hit("CN1", "台灯", loc=["26-05"])]
        pool = [
            _hit("CN8", "座椅", loc=["06-01"]),
            _hit("CN9", "无关调度", ipc=["G06F9/50"]),
        ]
        hits, reason = backfill_hits_for_disclosure(
            primary,
            pool,
            class_prefixes=["26-05"],
            core_terms=["台灯"],
            min_keep=4,
            limit=6,
        )
        self.assertEqual(reason, "still_short")
        self.assertEqual([h.pub_number for h in hits], ["CN1"])


class SearchArgvTests(unittest.TestCase):
    def test_parse_class_and_type(self) -> None:
        ptype, rest, codes = _parse_argv(
            ["--type", "design", "--class", "26-05,07-01", "台灯"]
        )
        self.assertEqual(ptype, "design")
        self.assertEqual(codes, ["26-05", "07-01"])
        self.assertEqual(rest, ["台灯"])

    def test_class_only_without_terms(self) -> None:
        ptype, rest, codes = _parse_argv(["--type", "design", "--class", "26-05"])
        self.assertEqual(ptype, "design")
        self.assertEqual(codes, ["26-05"])
        self.assertEqual(rest, [])

    def test_main_requires_terms_or_class(self) -> None:
        self.assertEqual(search_main([]), 2)


class GooglePatentsClassTests(unittest.TestCase):
    def test_invention_adds_cpc(self) -> None:
        q = google_patents_websearch_query(
            "胺功能化", "invention", class_codes=["B01J20"]
        )
        self.assertIn("CPC=B01J20/low", q)
        self.assertIn("type:PATENT", q)

    def test_design_adds_loc_as_term(self) -> None:
        q = google_patents_websearch_query("台灯", "design", class_codes=["26-05"])
        self.assertIn("26-05", q)
        self.assertIn("type:DESIGN", q)
        self.assertNotIn("CPC=", q)


class AdvancedTypeFilterTests(unittest.TestCase):
    def test_checks_design_only(self) -> None:
        page = MagicMock()
        boxes = {cid: MagicMock() for cid in ("isFmgb", "isFmsq", "isXx", "isWg")}

        def _qs(sel: str):
            return boxes.get(sel.lstrip("#"))

        page.query_selector.side_effect = _qs
        apply_epub_advanced_type_filter(page, "design")
        boxes["isWg"].check.assert_called()
        boxes["isFmgb"].uncheck.assert_called()


if __name__ == "__main__":
    unittest.main()
