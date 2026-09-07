# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

from emit_search_report import (
    main,
    render_search_report,
    report_filename,
    write_search_report,
)


def _sample_payload() -> dict:
    return {
        "source": "http://epub.cnipa.gov.cn/Advanced",
        "queried_at": "2026-09-02 11:58:00",
        "query": {
            "inventor": "测试发明人",
            "applicants": ["示例研究院"],
            "title": "数据处理",
            "patent_type": "invention",
            "max_pages": 3,
            "want_complete": False,
        },
        "complete": False,
        "stop_reason": "max_pages",
        "pages_scanned": 1,
        "total_pages": 61,
        "page_size_actual": 3,
        "first_page_hit_count": 3,
        "page_budget": 1,
        "pages_remaining": 60,
        "hit_count_estimate": 180,
        "completeness_note": "共 61 页，本次上限 1，还剩 60 页未翻",
        "candidate_count": 1,
        "matched_count": 1,
        "matched_publication_count": 1,
        "hits": [
            {
                "title": "一种示例数据处理方法",
                "pub_number": "CN120000001A",
                "application_number": "202610123456.7",
                "applicant": "示例研究院",
                "inventors": ["测试发明人"],
                "filing_date": "2026.04.22",
                "publication_date": "2026.08.18",
                "link": "http://epub.cnipa.gov.cn/patent/CN120000001A",
                "abstract": "本发明提供一种示例数据处理方法。",
                "ipc_codes": ["G06F16/00"],
                "identity_status": "verified_inventor_metadata",
            }
        ],
    }


class EmitSearchReportTests(unittest.TestCase):
    def test_filename_uses_timestamp(self) -> None:
        self.assertEqual(
            report_filename(datetime(2026, 9, 2, 11, 58, 7)),
            "SEARCH-20260902-115807.md",
        )

    def test_render_includes_query_and_hit_fields(self) -> None:
        text = render_search_report(
            _sample_payload(),
            queried_at=datetime(2026, 9, 2, 11, 58, 0),
        )
        self.assertIn("查询时间**：2026-09-02 11:58:00", text)
        self.assertIn("| 发明人 | 测试发明人 |", text)
        self.assertIn("| 名称 | 数据处理 |", text)
        self.assertIn("[一种示例数据处理方法](http://epub.cnipa.gov.cn/patent/CN120000001A)", text)
        self.assertIn("本发明提供一种示例数据处理方法。", text)
        self.assertIn("已由官方发明人著录核实", text)
        self.assertIn("共 61 页，本次上限 1，还剩 60 页未翻", text)

    def test_write_to_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_search_report(
                _sample_payload(),
                queried_at=datetime(2026, 9, 2, 11, 58, 0),
                output_dir=Path(tmp),
            )
            self.assertEqual(path.name, "SEARCH-20260902-115800.md")
            self.assertTrue(path.is_file())
            self.assertIn("一种示例数据处理方法", path.read_text(encoding="utf-8"))

    def test_cli_reads_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps(_sample_payload(), ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "out"
            self.assertEqual(main(["--json", str(src), "--output-dir", str(out)]), 0)
            files = list(out.glob("SEARCH-*.md"))
            self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
