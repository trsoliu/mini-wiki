# -*- coding: utf-8 -*-
"""专利库内关联 link_patent_notes 冒烟。"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "patent_reader"))

from patent_link import discover_links, load_patent_notes, run_link_pipeline  # noqa: E402


def _note(pub: str, domain: str, ipc: str, assignees: list[str], terms: list[str], extra: str = "") -> str:
    term_rows = "\n".join(f"| {t} | 定义 | 说明书 |" for t in terms)
    asg = "\n".join(f"  - {a}" for a in assignees)
    return f"""---
tags:
  - patents/{domain}
cssclasses:
  - patent-reader
pub_number: {pub}
domain: {domain}
ipc: {ipc}
assignees:
{asg}
evidence_scope: full_text
confidence_speculative: false
---

# 专利解读：{pub}

## 五、专利内术语表

| 术语 | 专利内含义 | 依据 |
| --- | --- | --- |
{term_rows}

## 十一、免责声明

不构成法律意见。

{extra}
"""


def test_link_same_assignee_and_terms() -> None:
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        papers = "Research/Patents"
        d1 = vault / papers / "化工与材料" / "CN111"
        d2 = vault / papers / "化工与材料" / "CN222"
        d1.mkdir(parents=True)
        d2.mkdir(parents=True)
        (d1 / "CN111_解读_20260101.md").write_text(
            _note(
                "CN111111111A",
                "化工与材料",
                "H01M50/00",
                ["示例科技有限公司"],
                ["耐热层", "基膜"],
            ),
            encoding="utf-8",
        )
        (d2 / "CN222_解读_20260102.md").write_text(
            _note(
                "CN222222222A",
                "化工与材料",
                "H01M10/0525",
                ["示例科技有限公司"],
                ["耐热层", "隔膜"],
                extra="背景中提及 CN111111111A 作为对比。",
            ),
            encoding="utf-8",
        )
        # 无关第三件：不同申请人、不同领域
        d3 = vault / papers / "软件" / "CN333"
        d3.mkdir(parents=True)
        (d3 / "CN333_解读_20260103.md").write_text(
            _note(
                "CN333333333A",
                "软件",
                "G06F9/00",
                ["另一家公司"],
                ["调度器"],
            ),
            encoding="utf-8",
        )

        notes = load_patent_notes(vault, papers)
        assert len(notes) == 3
        edges = discover_links(notes, min_score=0.45)
        pubs_pairs = {tuple(sorted([e["pub_a"], e["pub_b"]])) for e in edges}
        assert ("CN111111111A", "CN222222222A") in pubs_pairs
        assert all("CN333333333A" not in p for p in pubs_pairs)

        result = run_link_pipeline(
            vault,
            papers_dir=papers,
            min_score=0.45,
            focus_pub="CN222222222A",
            refresh_canvas=True,
            refresh_global_canvas=True,
        )
        assert result["edge_count"] >= 1
        assert result["global_canvas"]
        gpath = Path(result["global_canvas"])
        assert gpath.is_file()
        canvas = json.loads(gpath.read_text(encoding="utf-8"))
        texts = "\n".join(
            n.get("text") or "" for n in canvas["nodes"] if n.get("type") == "text"
        )
        assert "专利关联总览" in texts
        assert "CN111111111A" in texts or "CN222222222A" in texts
        assert any(str(n.get("id", "")).startswith("br") for n in canvas["nodes"]), (
            "应有关联桥卡"
        )
        assert any(n.get("id") == "legend" for n in canvas["nodes"])
        n2 = (d2 / "CN222_解读_20260102.md").read_text(encoding="utf-8")
        assert "## 相关专利" in n2
        assert "相关专利（自动关联）" not in n2
        assert "related_pubs:" in n2
        assert "CN111111111A" in n2
        # 双向
        n1 = (d1 / "CN111_解读_20260101.md").read_text(encoding="utf-8")
        assert "CN222222222A" in n1


def test_model_scores_merge() -> None:
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        papers = "Research/Patents"
        for pub, asg, ipc, terms in (
            ("CNAAA000001A", "甲", "G06F1/00", ["模块甲"]),
            ("CNBBB000001A", "乙", "A61K9/00", ["完全不同词"]),
        ):
            p = vault / papers / "未分类" / pub
            p.mkdir(parents=True)
            (p / f"{pub}_解读_20260101.md").write_text(
                _note(pub, "未分类", ipc, [asg], terms),
                encoding="utf-8",
            )
        notes = load_patent_notes(vault, papers)
        edges = discover_links(
            notes,
            min_score=0.4,
            model_scores=[
                {
                    "pub_a": "CNAAA000001A",
                    "pub_b": "CNBBB000001A",
                    "relation": "improvement",
                    "score": 0.8,
                    "rationale": "测试模型边",
                }
            ],
        )
        assert len(edges) == 1
        assert edges[0]["relation"] == "improvement"
        assert edges[0]["source"] in ("model", "rules+model")
        assert edges[0]["score"] >= 0.8


def main() -> int:
    test_link_same_assignee_and_terms()
    test_model_scores_merge()
    print("OK link_patent_notes smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
