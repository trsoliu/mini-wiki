# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from emit_covers_report import (
    covers_paths_beside,
    main,
    render_covers_report,
    write_covers_report,
)


def _payload() -> dict:
    return {
        "search_md": "outputs/patent-search/SEARCH-20260929-120000.md",
        "ranked_at": "2026-09-29 12:00:00",
        "features": [
            {"feature_id": "F3", "claim_no": 1, "text": "桥接筋连通两区"},
        ],
        "rows": [
            {
                "feature_id": "F3",
                "pub_number": "CN218800002U",
                "covers_feature": True,
                "score": 4,
                "snippet": "连通筋连接第一流道与第二流道",
                "abstract": "连通筋连接第一流道与第二流道",
                "link": "http://epub.cnipa.gov.cn/patent/CN218800002U",
            }
        ],
    }


class CoversReportTests(unittest.TestCase):
    def test_render_keeps_feature_and_link(self) -> None:
        text = render_covers_report(_payload())
        self.assertIn("旁路", text)
        self.assertIn("F3", text)
        self.assertIn("CN218800002U", text)
        self.assertIn("能填", text)

    def test_write_beside_does_not_overwrite_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            search_md = Path(tmp) / "SEARCH-20260929-120000.md"
            search_md.write_text("# 著录检索\n\n列表正文不得被改。\n", encoding="utf-8")
            md_path, json_path = write_covers_report(_payload(), beside=search_md)
            self.assertEqual(md_path.name, "SEARCH-20260929-120000.covers.md")
            self.assertTrue(json_path.is_file())
            self.assertEqual(
                search_md.read_text(encoding="utf-8"),
                "# 著录检索\n\n列表正文不得被改。\n",
            )
            self.assertIn("F3", md_path.read_text(encoding="utf-8"))

    def test_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            search_md = Path(tmp) / "SEARCH-20260929-120000.md"
            search_md.write_text("# list\n", encoding="utf-8")
            src = Path(tmp) / "in.json"
            src.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
            self.assertEqual(main(["--json", str(src), "--beside", str(search_md)]), 0)
            md, js = covers_paths_beside(search_md)
            self.assertTrue(md.is_file())
            self.assertTrue(js.is_file())


if __name__ == "__main__":
    unittest.main()
