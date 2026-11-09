# -*- coding: utf-8 -*-
"""著录字段抽取单测。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from shared.common import (
    extract_cited_pub_numbers,
    extract_filing_date,
    extract_inventors,
    extract_publication_date,
    organizations_from_assignees,
)


def test_biblio_extract() -> None:
    text = """
发明名称：一种隔膜
申请人：示例科技有限公司
发明人：张三、李四
申请日：2024年3月1日
公开日：2025年1月15日
背景记载了 CN107785522B 与 US9123456B2。
"""
    assert extract_filing_date(text) == "2024-03-01"
    assert extract_publication_date(text) == "2025-01-15"
    assert extract_inventors(text) == ["张三", "李四"]
    assert "CN107785522B" in extract_cited_pub_numbers(text, "CN999999999B")
    assert organizations_from_assignees(["示例科技有限公司", "张三"]) == ["示例科技有限公司"]


if __name__ == "__main__":
    test_biblio_extract()
    print("OK biblio extract")
