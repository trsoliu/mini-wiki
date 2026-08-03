# -*- coding: utf-8 -*-
"""P0 术语 / P1-P2 附图引擎冒烟。"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "patent_reader"))

from figure_extract import CAPTION_RE, _classify_visual_quality, extract_patent_pdf_figures  # noqa: E402
from obsidian import build_canvas, resolve_glossary_nodes, scan_glossary_index  # noqa: E402


def test_caption_re() -> None:
    assert CAPTION_RE.match("图1 一种隔膜结构示意图")
    assert CAPTION_RE.match("图 2")
    assert CAPTION_RE.match("FIG. 3")
    assert CAPTION_RE.match("【图1】")
    assert not CAPTION_RE.match("如图1所示，基膜包括")


def test_quality_gate() -> None:
    q = _classify_visual_quality(
        page_coverage_ratio=0.3,
        visual_rect_count=5,
        visual_body_ratio=0.25,
        paragraph_text_chars=20,
    )
    assert q["status"] == "usable"
    q2 = _classify_visual_quality(
        page_coverage_ratio=0.95,
        visual_rect_count=1,
        visual_body_ratio=0.01,
        paragraph_text_chars=300,
    )
    assert q2["status"] == "reject"


def test_glossary_and_canvas() -> None:
    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        papers = "Research/Patents"
        gloss = "Research/术语"
        (vault / papers / "化工与材料" / "CN1").mkdir(parents=True)
        note = vault / papers / "化工与材料" / "CN1" / "CN1_解读_20260101.md"
        note.write_text("# 测试\n", encoding="utf-8")
        resolved = resolve_glossary_nodes(
            vault,
            gloss,
            [{"term": "耐热层", "definition": "覆盖在基膜表面的涂层"}],
            create_stubs=True,
            source_pub="CN1",
            papers_dir=papers,
        )
        assert resolved[0]["has_file"]
        assert (vault / gloss / "耐热层.md").is_file()
        idx = scan_glossary_index(vault, gloss)
        assert "耐热层" in idx
        canvas = build_canvas(
            vault=vault,
            papers_dir=papers,
            note_rel_path=str(note.relative_to(vault)).replace("\\", "/"),
            pub="CN1",
            title="测试专利",
            related={"related_patents": [], "disclosures": []},
            glossary_terms=[{"term": "耐热层", "definition": "覆盖在基膜表面的涂层"}],
            glossary_dir=gloss,
            create_glossary_stubs=False,
            narrative={
                "problem": "旧工艺不安全",
                "approach": "改用水性浆料",
                "how": "分散涂布",
                "effect": "更薄",
            },
        )
        types = {n.get("type") for n in canvas["nodes"]}
        assert "group" in types, "应有叙事/术语分组"
        narr = [n for n in canvas["nodes"] if str(n.get("id", "")).startswith("narr-")]
        assert len(narr) >= 3, narr
        term_cards = [
            n
            for n in canvas["nodes"]
            if n.get("type") == "text" and "耐热层" in (n.get("text") or "")
        ]
        assert term_cards and "覆盖在基膜表面" in term_cards[0]["text"]
        center = next(n for n in canvas["nodes"] if n.get("id") == "center")
        assert center.get("type") == "text"
        assert "打开解读笔记" in (center.get("text") or "")


def test_figure_extract_synthetic_pdf() -> None:
    try:
        import fitz
    except ImportError:
        print("SKIP figure pdf (no pymupdf)")
        return
    with tempfile.TemporaryDirectory() as td:
        pdf = Path(td) / "t.pdf"
        out = Path(td) / "figures"
        doc = fitz.open()
        page = doc.new_page()
        page.draw_rect(fitz.Rect(72, 72, 400, 400), color=(0, 0, 0), width=2)
        page.draw_line(fitz.Point(100, 100), fitz.Point(300, 300), color=(0, 0, 0), width=1)
        page.draw_circle(fitz.Point(200, 200), 40, color=(0, 0, 0), width=1)
        # 合成 PDF 用拉丁图号（中文字体在无系统字体时可能插不进）
        page.insert_text(fitz.Point(72, 430), "FIG. 1 structure", fontsize=12)
        doc.save(pdf)
        doc.close()
        man = extract_patent_pdf_figures(pdf, out)
        assert man["count"] >= 1, man
        fig = man["figures"][0]
        assert fig.get("extraction_level") in ("figure", "page")
        assert (out / fig["filename"]).is_file()
        assert "decision" in fig
        assert "quality_signals" in fig


def main() -> int:
    test_caption_re()
    test_quality_gate()
    test_glossary_and_canvas()
    test_figure_extract_synthetic_pdf()
    print("OK p0_p1_p2 smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
