# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

from cnipa_parse import (
    EpubSearchHit,
    application_number_for_epub_query,
    normalize_application_number,
    parse_reported_page_size,
    parse_reported_total,
    parse_reported_total_pages,
    parse_search_result_html,
)
from cnipa_search import (
    _build_parser,
    _query_fields,
    completeness_note,
    filter_hits,
    main,
)
from search_config import (
    DEFAULTS,
    load_search_config,
    resolve_max_pages,
    resolve_page_budget,
)

# ---------------------------------------------------------------------------
# 功能测试用检索样例（公开著录字段）
#
# 下列常量只用来覆盖 CLI 映射、真实公布站高级查询和结果过滤，
# 不针对特定公司或个人，也不构成尽职调查或权利归属结论。
# 换成任意同等结构的公开著录值，测试意图不变。
# ---------------------------------------------------------------------------
SAMPLE_APPLICANT = "宇树科技"  # 申请人简称，测 #e71_73 / 别名包含匹配
SAMPLE_APPLICANT_LEGAL = "杭州宇树科技有限公司"  # 常见著录全称，测多 --applicant
SAMPLE_INVENTOR = "王兴兴"  # 发明人/设计人，测 #e72
SAMPLE_TITLE = "四足机器人"  # 足式平台主题词，测 #ti
SAMPLE_TITLE_HUMANOID = "人形机器人"  # 同领域另一名称词
SAMPLE_CLASS_IPC = "B25J"  # 机械手/操纵器，足式与关节常见
SAMPLE_CLASS_WALKING = "B62D57"  # 非轮式行走装置
SAMPLE_APPLICATION_NUMBER = "201921114883.3"  # 用户常见带校验点；填表前会去掉点
SAMPLE_PUBLICATION_NUMBER = "CN210476989U"  # 公开号/公告号格式样例（公开可核）
SAMPLE_TYPE_INVENTION = "invention"
SAMPLE_TYPE_UTILITY = "utility_model"
SAMPLE_TYPE_DESIGN = "design"
SAMPLE_MAX_PAGES = 1  # 单条件默认只翻 1 页
SAMPLE_MAX_PAGES_MULTI = 2  # 多页场景：至少翻到第 2 页

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
except ImportError:  # pragma: no cover
    class PlaywrightTimeoutError(Exception):
        pass

from cnipa_crawler import (
    DEFAULT_USER_AGENT,
    _CLICK_NEXT_PAGE_JS,
    _FETCH_RESULT_PAGE_JS,
    advance_to_next_result_page,
    apply_epub_advanced_catalog_filter,
    collect_result_pages,
    has_next_result_page,
    search_advanced,
)


class SearchConfigTests(unittest.TestCase):
    def test_repo_config_defaults_are_small(self) -> None:
        cfg = load_search_config()
        self.assertEqual(cfg["max_pages"], 3)
        self.assertLessEqual(cfg["max_pages"], cfg["max_pages_hard"])
        self.assertEqual(DEFAULTS["max_pages"], 3)
        self.assertEqual(DEFAULTS["page_size"], 3)
        self.assertEqual(cfg["page_size"], 3)

    def test_complete_uses_hard_cap(self) -> None:
        cfg = {"max_pages": 3, "max_pages_hard": 20}
        self.assertEqual(resolve_max_pages(want_complete=True, cfg=cfg), 20)
        self.assertEqual(resolve_max_pages(requested=None, cfg=cfg), 3)
        self.assertEqual(resolve_max_pages(requested=100, cfg=cfg), 20)

    def test_page_budget_follows_total_pages_when_complete(self) -> None:
        cfg = {"max_pages": 3, "max_pages_hard": 20}
        self.assertEqual(
            resolve_page_budget(want_complete=True, total_pages=61, cfg=cfg),
            61,
        )
        self.assertEqual(
            resolve_page_budget(want_complete=True, total_pages=None, cfg=cfg),
            20,
        )
        self.assertEqual(
            resolve_page_budget(requested=3, want_complete=False, total_pages=61, cfg=cfg),
            3,
        )

    def test_yaml_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            path.write_text("max_pages: 1\nmax_pages_hard: 5\n", encoding="utf-8")
            cfg = load_search_config(path)
            self.assertEqual(cfg["max_pages"], 1)
            self.assertEqual(resolve_max_pages(requested=9, cfg=cfg), 5)


class ListResultParserTests(unittest.TestCase):
    def test_parses_application_applicant_and_title(self) -> None:
        html = """
        <table><tbody><tr>
          <td>2</td>
          <td><a href="/patent/CN120000001A">2026101234567</a></td>
          <td>示例<em>人工智能</em>研究院</td>
          <td>一种示例数据处理方法、装置及电子设备</td>
        </tr></tbody></table>
        """
        hits = parse_search_result_html(html)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].application_number, "202610123456.7")
        self.assertEqual(hits[0].applicant, "示例 人工智能 研究院")
        self.assertEqual(hits[0].title, "一种示例数据处理方法、装置及电子设备")
        self.assertEqual(hits[0].link, "http://epub.cnipa.gov.cn/patent/CN120000001A")

    def test_normalizes_application_number_with_or_without_dot(self) -> None:
        self.assertEqual(
            normalize_application_number("2025123456789"), "202512345678.9"
        )
        self.assertEqual(
            normalize_application_number(SAMPLE_APPLICATION_NUMBER),
            SAMPLE_APPLICATION_NUMBER,
        )

    def test_adapts_application_number_for_epub_query(self) -> None:
        self.assertEqual(
            application_number_for_epub_query("201921114883.3"), "2019211148833"
        )
        self.assertEqual(
            application_number_for_epub_query("2019211148833"), "2019211148833"
        )
        self.assertEqual(
            application_number_for_epub_query("CN201921114883.3"), "2019211148833"
        )


class CardResultParserTests(unittest.TestCase):
    def test_parses_bibliographic_metadata(self) -> None:
        html = """
        <div class="overview-default">
          <div class="item">
            <h1 class="title">一种示例数据处理方法</h1>
            <dl>
              <dt>申请公布号：</dt><dd>CN120000001A</dd>
              <dt>申请号：</dt><dd>2026101234567</dd>
              <dt>申请人：</dt><dd>示例人工智能研究院</dd>
              <dt>申请日：</dt><dd>2026.04.22</dd>
              <dt>申请公布日：</dt><dd>2026.08.18</dd>
              <dt>发明人：</dt><dd>测试发明人;共同发明人甲;共同发明人乙</dd>
              <dt>摘要：</dt><dd>本发明提供一种示例数据处理方法。</dd>
            </dl>
            <div class="qrcode" title="http://epub.cnipa.gov.cn/patent/CN120000001A"></div>
          </div>
        </div>
        """
        hits = parse_search_result_html(html)
        self.assertEqual(len(hits), 1)
        hit = hits[0]
        self.assertEqual(hit.application_number, "202610123456.7")
        self.assertEqual(hit.applicant, "示例人工智能研究院")
        self.assertEqual(hit.inventors, ["测试发明人", "共同发明人甲", "共同发明人乙"])
        self.assertEqual(hit.pub_number, "CN120000001A")

    def test_parses_reported_total(self) -> None:
        self.assertEqual(parse_reported_total("<div>共 68 条</div>"), 68)

    def test_parses_reported_pages_and_page_size(self) -> None:
        html = (
            '<span class="page_total">共 61 页, 到第</span>'
            '<input id="pageSize" value="3" />'
            "<div>每页 3 条</div>"
        )
        self.assertEqual(parse_reported_total_pages(html), 61)
        self.assertEqual(parse_reported_page_size(html), 3)
        self.assertIsNone(parse_reported_total(html))


class PaginationTests(unittest.TestCase):
    def test_official_next_page_selector_is_supported(self) -> None:
        self.assertIn("a.next_page", _CLICK_NEXT_PAGE_JS)
        self.assertIn('text.startsWith("下页")', _CLICK_NEXT_PAGE_JS)

    def test_page_query_fetch_keeps_search_after(self) -> None:
        self.assertIn("AbortController", _FETCH_RESULT_PAGE_JS)
        self.assertIn('"X-Requested-With": "XMLHttpRequest"', _FETCH_RESULT_PAGE_JS)
        self.assertNotIn('searchAfter.value = ""', _FETCH_RESULT_PAGE_JS)
        self.assertNotIn("searchAfter.value = ''", _FETCH_RESULT_PAGE_JS)

    def test_advances_and_waits_for_changed_result(self) -> None:
        page = MagicMock()
        page.evaluate.side_effect = ["old-fingerprint", {"clicked": True}]
        self.assertEqual(advance_to_next_result_page(page), "advanced")
        self.assertEqual(page.wait_for_function.call_count, 2)

    def test_detects_last_page(self) -> None:
        page = MagicMock()
        page.evaluate.side_effect = ["old-fingerprint", {"clicked": False}]
        page.query_selector.return_value = None
        self.assertEqual(advance_to_next_result_page(page), "last_page")

    def test_reports_stalled_page_instead_of_silent_completion(self) -> None:
        page = MagicMock()
        page.evaluate.side_effect = ["old-fingerprint", {"clicked": True}]
        page.wait_for_function.side_effect = PlaywrightTimeoutError("unchanged")
        page.query_selector.return_value = None
        self.assertEqual(advance_to_next_result_page(page), "stalled")

    def test_http_400_stops_incomplete(self) -> None:
        page = MagicMock()
        page.evaluate.side_effect = [
            "old-fingerprint",
            {"clicked": False},
            {"ok": False, "status": 400, "error": "http_400"},
            {"ok": False, "status": 400, "error": "http_400"},
            {"ok": False, "status": 400, "error": "http_400"},
        ]
        page.query_selector.return_value = MagicMock()
        self.assertEqual(
            advance_to_next_result_page(page, next_page_num=2, retries=2, backoff_ms=1),
            "http_400",
        )

    def _pager_cfg(self) -> dict:
        return {
            "max_pages": 3,
            "max_pages_hard": 20,
            "page_size": 3,
            "page_delay_ms": 0,
            "http_error_retries": 0,
            "http_error_backoff_ms": 1,
        }

    def test_collect_stops_at_max_pages_without_claiming_complete(self) -> None:
        page = MagicMock()
        page.title.return_value = "专利查询结果展示"
        page.evaluate.side_effect = Exception("no live pager js")
        html = '<div class="overview-default"><div class="item"><h1 class="title">专利 1</h1></div></div>'
        with patch("cnipa_crawler._safe_page_content", return_value=html), patch(
            "cnipa_crawler.has_next_result_page", return_value=True
        ):
            result = collect_result_pages(page, max_pages=1, cfg=self._pager_cfg())
        self.assertFalse(result.complete)
        self.assertEqual(result.stop_reason, "max_pages")
        self.assertEqual(result.pages_scanned, 1)
        self.assertIsNone(result.total_pages)
        self.assertEqual(result.page_size_actual, 3)

    def test_collect_first_page_reads_total_pages_and_actual_size(self) -> None:
        page = MagicMock()
        page.title.return_value = "专利查询结果展示"
        page.evaluate.side_effect = Exception("use html pager")
        html = """
        <span class="page_total">共 61 页, 到第</span>
        <input id="pageSize" value="3" />
        <div>每页 3 条</div>
        <div class="overview-default">
          <div class="item"><h1 class="title">专利 1</h1></div>
          <div class="item"><h1 class="title">专利 2</h1></div>
          <div class="item"><h1 class="title">专利 3</h1></div>
        </div>
        """
        with patch("cnipa_crawler._safe_page_content", return_value=html), patch(
            "cnipa_crawler.has_next_result_page", return_value=True
        ):
            result = collect_result_pages(page, max_pages=1, cfg=self._pager_cfg())
        self.assertFalse(result.complete)
        self.assertEqual(result.stop_reason, "max_pages")
        self.assertEqual(result.total_pages, 61)
        self.assertEqual(result.page_size_actual, 3)
        self.assertEqual(result.first_page_hit_count, 3)
        self.assertEqual(result.page_budget, 1)
        self.assertEqual(result.pages_remaining, 60)
        self.assertEqual(result.hit_count_estimate, 60 * 3)

    def test_collect_complete_rebudgets_to_total_pages(self) -> None:
        page = MagicMock()
        page.title.return_value = "专利查询结果展示"
        page.evaluate.side_effect = Exception("use html pager")
        html = """
        <span class="page_total">共 61 页, 到第</span>
        <input id="pageSize" value="3" />
        <div class="overview-default"><div class="item"><h1 class="title">专利 1</h1></div></div>
        """
        with patch("cnipa_crawler._safe_page_content", return_value=html), patch(
            "cnipa_crawler.has_next_result_page", return_value=True
        ), patch("cnipa_crawler.advance_to_next_result_page", return_value="stalled"):
            result = collect_result_pages(
                page,
                max_pages=20,
                want_complete=True,
                cfg=self._pager_cfg(),
            )
        self.assertFalse(result.complete)
        self.assertEqual(result.stop_reason, "stalled")
        self.assertEqual(result.total_pages, 61)
        self.assertEqual(result.page_budget, 61)
        self.assertEqual(result.page_size_actual, 3)

    def test_collect_complete_without_total_pages_uses_hard_cap(self) -> None:
        page = MagicMock()
        page.title.return_value = "专利查询结果展示"
        page.evaluate.side_effect = Exception("no live pager js")
        html = '<div class="overview-default"><div class="item"><h1 class="title">专利 1</h1></div></div>'
        cfg = {**self._pager_cfg(), "max_pages_hard": 1}
        with patch("cnipa_crawler._safe_page_content", return_value=html), patch(
            "cnipa_crawler.has_next_result_page", return_value=True
        ):
            result = collect_result_pages(
                page,
                max_pages=20,
                want_complete=True,
                cfg=cfg,
            )
        self.assertFalse(result.complete)
        self.assertEqual(result.stop_reason, "max_pages_hard")
        self.assertIsNone(result.total_pages)
        self.assertEqual(result.page_budget, 1)

    def test_has_next_uses_finder_not_click(self) -> None:
        page = MagicMock()
        page.evaluate.return_value = {"found": True}
        self.assertTrue(has_next_result_page(page))
        page.evaluate.assert_called_once()
        js = page.evaluate.call_args.args[0]
        self.assertIn("found: true", js)
        self.assertNotIn("element.click()", js)


class AdvancedInventorSearchTests(unittest.TestCase):
    def test_user_agent_does_not_leak_a_version_placeholder(self) -> None:
        self.assertNotIn("{version}", DEFAULT_USER_AGENT)

    def test_selects_one_official_catalog(self) -> None:
        page = MagicMock()
        boxes = {cid: MagicMock() for cid in ("isFmgb", "isFmsq", "isXx", "isWg")}
        page.query_selector.side_effect = lambda selector: boxes.get(selector[1:])
        apply_epub_advanced_catalog_filter(page, "fmsq")
        boxes["isFmsq"].check.assert_called_once_with(force=True)
        boxes["isFmgb"].uncheck.assert_called_once_with(force=True)


class HitFilterTests(unittest.TestCase):
    def test_filters_same_name_results_by_applicant(self) -> None:
        hits = [
            EpubSearchHit(
                raw_html="",
                application_number="202610123456.7",
                applicant="示例人工智能研究院",
                inventors=["测试发明人", "共同发明人甲"],
                title="一种示例数据处理方法",
            ),
            EpubSearchHit(
                raw_html="",
                application_number="202610765432.1",
                applicant="另一示例研究院",
                inventors=["测试发明人"],
                title="一种示例检测方法",
            ),
        ]
        rows = filter_hits(
            hits,
            inventor="测试发明人",
            applicants=["示例人工智能研究院"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["application_number"], "202610123456.7")
        self.assertEqual(rows[0]["identity_status"], "verified_inventor_metadata")

    def test_marks_list_mode_match_basis_explicitly(self) -> None:
        hit = EpubSearchHit(
            raw_html="",
            application_number="202010123456.7",
            applicant="示例网络技术有限公司",
            title="一种示例目标检测方法",
        )
        rows = filter_hits(
            [hit],
            inventor="测试发明人",
            applicants=["示例网络技术有限公司"],
        )
        self.assertEqual(rows[0]["identity_status"], "inventor_query_and_applicant")

    def test_merges_publication_and_grant_for_one_application(self) -> None:
        hits = [
            EpubSearchHit(
                raw_html="",
                application_number="202010123456.7",
                pub_number="CN112000001A",
                applicant="示例网络技术有限公司",
                inventors=["测试发明人"],
            ),
            EpubSearchHit(
                raw_html="",
                application_number="202010123456.7",
                pub_number="CN112000001B",
                applicant="示例网络技术有限公司",
                inventors=["测试发明人"],
            ),
        ]
        rows = filter_hits(
            hits,
            inventor="测试发明人",
            applicants=["示例网络技术有限公司"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            [record["pub_number"] for record in rows[0]["publication_records"]],
            ["CN112000001A", "CN112000001B"],
        )

    def test_sample_applicant_alias_and_inventor_filter(self) -> None:
        hits = [
            EpubSearchHit(
                raw_html="",
                application_number=SAMPLE_APPLICATION_NUMBER,
                pub_number=SAMPLE_PUBLICATION_NUMBER,
                applicant=SAMPLE_APPLICANT_LEGAL,
                inventors=[SAMPLE_INVENTOR, "共同发明人甲"],
                title=f"一种关节回转动力单元及应用其的{SAMPLE_TITLE}",
            ),
            EpubSearchHit(
                raw_html="",
                application_number="202010123456.7",
                applicant="另一示例机器人公司",
                inventors=[SAMPLE_INVENTOR],
                title=SAMPLE_TITLE_HUMANOID,
            ),
        ]
        rows = filter_hits(
            hits,
            inventor=SAMPLE_INVENTOR,
            applicants=[SAMPLE_APPLICANT, SAMPLE_APPLICANT_LEGAL],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["application_number"], SAMPLE_APPLICATION_NUMBER)
        self.assertEqual(rows[0]["matched_applicant"], SAMPLE_APPLICANT)
        self.assertEqual(rows[0]["identity_status"], "verified_inventor_metadata")


class CompletenessNoteTests(unittest.TestCase):
    def test_uses_total_pages_when_present(self) -> None:
        self.assertEqual(
            completeness_note(
                complete=True,
                total_pages=61,
                pages_scanned=61,
                page_budget=61,
                pages_remaining=0,
            ),
            "已翻完全部分页（共 61 页）",
        )
        self.assertEqual(
            completeness_note(
                complete=False,
                total_pages=61,
                pages_scanned=20,
                page_budget=20,
                pages_remaining=41,
            ),
            "共 61 页，本次上限 20，还剩 41 页未翻",
        )

    def test_falls_back_to_next_page_without_total(self) -> None:
        self.assertEqual(
            completeness_note(
                complete=True,
                total_pages=None,
                pages_scanned=4,
                page_budget=20,
            ),
            "已翻到末页（没有「下页」）",
        )
        self.assertIn(
            "下页",
            completeness_note(
                complete=False,
                total_pages=None,
                pages_scanned=20,
                page_budget=20,
                has_next=True,
            ),
        )


class QueryFieldsTests(unittest.TestCase):
    def test_cli_maps_all_sample_conditions(self) -> None:
        args = _build_parser().parse_args(
            [
                "--inventor",
                SAMPLE_INVENTOR,
                "--applicant",
                SAMPLE_APPLICANT,
                "--applicant",
                SAMPLE_APPLICANT_LEGAL,
                "--title",
                SAMPLE_TITLE,
                "--class",
                SAMPLE_CLASS_IPC,
                "--application-number",
                SAMPLE_APPLICATION_NUMBER,
                "--publication-number",
                SAMPLE_PUBLICATION_NUMBER,
                "--type",
                SAMPLE_TYPE_INVENTION,
                "--max-pages",
                str(SAMPLE_MAX_PAGES),
            ]
        )
        fields = _query_fields(args)
        self.assertEqual(
            fields,
            {
                "inventor": SAMPLE_INVENTOR,
                "applicant": SAMPLE_APPLICANT,
                "title": SAMPLE_TITLE,
                "class_code": SAMPLE_CLASS_IPC,
                "application_number": application_number_for_epub_query(
                    SAMPLE_APPLICATION_NUMBER
                ),
                "publication_number": SAMPLE_PUBLICATION_NUMBER,
            },
        )
        self.assertEqual(args.applicant, [SAMPLE_APPLICANT, SAMPLE_APPLICANT_LEGAL])
        self.assertEqual(args.type, SAMPLE_TYPE_INVENTION)

    def test_blank_query_is_rejected(self) -> None:
        self.assertEqual(_query_fields(_build_parser().parse_args([])), {})
        self.assertEqual(main([]), 2)


class LiveCnipaSearchTests(unittest.TestCase):
    """真实打公布站高级查询。断言只要求能查到数据；单条件默认 1 页。"""

    def _search(self, fields: dict[str, str], *, max_pages: int = SAMPLE_MAX_PAGES):
        return search_advanced(fields, patent_type="all", max_pages=max_pages)

    def _assert_has_hits(self, result, fields: dict[str, str]) -> None:
        self.assertGreater(
            len(result.hits),
            0,
            f"公布站无结果 fields={fields} pages={result.pages_scanned} "
            f"stop={result.stop_reason} total={result.total_reported}",
        )
        self.assertGreaterEqual(result.pages_scanned, 1)

    def test_live_applicant(self) -> None:
        self._assert_has_hits(
            self._search({"applicant": SAMPLE_APPLICANT}),
            {"applicant": SAMPLE_APPLICANT},
        )

    def test_live_inventor(self) -> None:
        self._assert_has_hits(
            self._search({"inventor": SAMPLE_INVENTOR}),
            {"inventor": SAMPLE_INVENTOR},
        )

    def test_live_title(self) -> None:
        self._assert_has_hits(
            self._search({"title": SAMPLE_TITLE}),
            {"title": SAMPLE_TITLE},
        )

    def test_live_class(self) -> None:
        self._assert_has_hits(
            self._search({"class_code": SAMPLE_CLASS_IPC}),
            {"class_code": SAMPLE_CLASS_IPC},
        )

    def test_live_application_number(self) -> None:
        self._assert_has_hits(
            self._search({"application_number": SAMPLE_APPLICATION_NUMBER}),
            {"application_number": SAMPLE_APPLICATION_NUMBER},
        )

    def test_live_publication_number(self) -> None:
        self._assert_has_hits(
            self._search({"publication_number": SAMPLE_PUBLICATION_NUMBER}),
            {"publication_number": SAMPLE_PUBLICATION_NUMBER},
        )

    def test_live_inventor_and_applicant(self) -> None:
        fields = {"inventor": SAMPLE_INVENTOR, "applicant": SAMPLE_APPLICANT}
        self._assert_has_hits(self._search(fields), fields)

    def test_live_multipage(self) -> None:
        # 发明人样例命中多页；用真实「下页」覆盖翻页，不用宽分类号以免回退 fetch 400
        fields = {"inventor": SAMPLE_INVENTOR}
        result = self._search(fields, max_pages=SAMPLE_MAX_PAGES_MULTI)
        self._assert_has_hits(result, fields)
        self.assertGreaterEqual(
            result.pages_scanned,
            SAMPLE_MAX_PAGES_MULTI,
            f"未翻到多页 stop={result.stop_reason} pages={result.pages_scanned}",
        )


if __name__ == "__main__":
    unittest.main()
