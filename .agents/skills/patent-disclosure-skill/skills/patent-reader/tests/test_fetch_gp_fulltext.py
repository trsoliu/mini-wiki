# -*- coding: utf-8 -*-
"""海外公开号：局别识别、fetch_gp_fulltext 产出、fetch_patent_pdf 限流与页数（不联网）。"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

import extract.fetch_gp_fulltext as gp_full
import extract.fetch_patent_pdf as pdf_mod
from google_patents import GooglePatentsBlocked, parse_detail_html
from patent_type import infer_jurisdiction, resolve_reader_patent_type

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "google_patents"
FAKE_PDF = b"%PDF-1.4" + b"0" * 6000


def _detail(name: str, pub: str):
    html = (FIXTURES / name).read_text(encoding="utf-8")
    return parse_detail_html(html, pub=pub, url=f"https://patents.google.com/patent/{pub}/en")


class _Patch:
    def __init__(self, mod, **attrs) -> None:
        self.mod, self.attrs = mod, attrs

    def __enter__(self):
        self.old = {k: getattr(self.mod, k) for k in self.attrs}
        for k, v in self.attrs.items():
            setattr(self.mod, k, v)
        return self

    def __exit__(self, *_a):
        for k, v in self.old.items():
            setattr(self.mod, k, v)


def _run(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = gp_full.main(argv)
    return code, out.getvalue(), err.getvalue()


class JurisdictionTests(unittest.TestCase):
    def test_infer_jurisdiction(self) -> None:
        self.assertEqual(infer_jurisdiction("CN119961390A"), "CN")
        self.assertEqual(infer_jurisdiction("US11450918B2"), "US")
        self.assertEqual(infer_jurisdiction("USD1032042S1"), "US")
        self.assertEqual(infer_jurisdiction("ep3389130b1"), "EP")
        self.assertEqual(infer_jurisdiction("WO2022005144A2"), "WO")
        self.assertIsNone(infer_jurisdiction("abc"))

    def test_overseas_type_from_kind(self) -> None:
        us = resolve_reader_patent_type(pub="US11450918B2")
        self.assertEqual((us["patent_type"], us["source"], us["jurisdiction"]), ("invention", "pub_kind_code_overseas", "US"))
        self.assertEqual(resolve_reader_patent_type(pub="USD1032042S1")["patent_type"], "design")
        self.assertEqual(resolve_reader_patent_type(pub="JP3212345U")["patent_type"], "utility_model")
        cn = resolve_reader_patent_type(pub="CN209861402U")
        self.assertEqual((cn["patent_type"], cn["source"], cn["jurisdiction"]), ("utility_model", "pub_kind_code", "CN"))


class FetchGpFulltextTests(unittest.TestCase):
    def test_us_outputs(self) -> None:
        detail = _detail("detail_US11450918B2.html", "US11450918B2")
        with tempfile.TemporaryDirectory() as td:
            with _Patch(
                gp_full,
                fetch_detail=lambda *_a, **_k: detail,
                download_pdf_bytes=lambda *_a, **_k: FAKE_PDF,
            ):
                code, out, _err = _run(["--pub", "US11450918B2", "-o", td])
            self.assertEqual(code, 0)
            self.assertIn("OK claims=6 desc_paras=3 scope=full_text", out)
            run = Path(td)
            tree = json.loads((run / "claim_tree.json").read_text(encoding="utf-8"))
            nodes = {n["number"]: n for n in tree["nodes"]}
            self.assertTrue(nodes[1]["is_independent"])
            self.assertEqual(nodes[2]["parent"], 1)
            self.assertEqual(nodes[6]["parent"], 5)
            paras = json.loads((run / "description_paragraphs.json").read_text(encoding="utf-8"))
            self.assertEqual(paras["source_url"], "https://patents.google.com/patent/US11450918B2/en")
            self.assertEqual(paras["count"], 3)
            manifest = json.loads((run / "source_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["jurisdiction"], "US")
            self.assertEqual(manifest["priority_date"], "2019-02-20")
            self.assertIn("H01M10/0525", manifest["ipc_codes"])
            sections = [
                json.loads(line)
                for line in (run / "raw_sections.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(sections[0]["section_id"], "abstract")
            self.assertIn("desc_0001", {s["section_id"] for s in sections})
            self.assertTrue((run / "source" / "US11450918B2.pdf").is_file())
            self.assertTrue((run / "source" / "US11450918B2.gp_detail.json").is_file())
            status = json.loads((run / "fetch_gp_status.json").read_text(encoding="utf-8"))
            self.assertTrue(status["ok"] and status["pdf_ok"])
            self.assertEqual(status["patent_type"], "invention")

    def test_jp_keeps_original_text(self) -> None:
        detail = _detail("detail_JP7371268B2.html", "JP7371268B2")
        with tempfile.TemporaryDirectory() as td:
            with _Patch(gp_full, fetch_detail=lambda *_a, **_k: detail):
                code, out, _err = _run(["--pub", "JP7371268B2", "-o", td, "--no-pdf"])
            self.assertEqual(code, 0)
            self.assertIn("translated_from=Japanese", out)
            bundle = json.loads((Path(td) / "synthesis_bundle.json").read_text(encoding="utf-8"))
            self.assertIn("リチウムイオン二次電池", bundle["claims"][0]["text_original"])
            self.assertEqual(bundle["manifest"]["translated_from"], "Japanese")
            self.assertFalse((Path(td) / "source" / "JP7371268B2.pdf").exists())

    def test_blocked_exits_4(self) -> None:
        def blocked(*_a, **_k):
            raise GooglePatentsBlocked("Google Patents 限流（HTTP 503），已停止请求", status=503)

        with tempfile.TemporaryDirectory() as td:
            with _Patch(gp_full, fetch_detail=blocked):
                code, _out, err = _run(["--pub", "US11450918B2", "-o", td])
            self.assertEqual(code, gp_full.EXIT_BLOCKED)
            self.assertIn("GP_FULLTEXT_ERROR: reason=blocked status=503", err)
            status = json.loads((Path(td) / "fetch_gp_status.json").read_text(encoding="utf-8"))
            self.assertFalse(status["ok"])
            self.assertFalse((Path(td) / "claim_tree.json").exists())

    def test_rejects_cn_pub(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            code, _out, err = _run(["--pub", "CN119961390A", "-o", td])
        self.assertEqual(code, 2)
        self.assertIn("fetch_patent_pdf.py", err)


class FetchPatentPdfOverseasTests(unittest.TestCase):
    def test_overseas_requests_one_page(self) -> None:
        self.assertEqual(
            pdf_mod.google_patent_page_urls("US11450918B2"),
            ["https://patents.google.com/patent/US11450918B2/en"],
        )
        self.assertEqual(len(pdf_mod.google_patent_page_urls("CN119961390A")), 3)

    def test_503_reports_rate_limit(self) -> None:
        def limited(page, *_a, **_k):
            raise urllib.error.HTTPError(page, 503, "x", {}, None)

        with _Patch(pdf_mod, read_page_pdf_urls=limited):
            with self.assertRaises(FileNotFoundError) as cm:
                pdf_mod.resolve_pdf_url("US11450918B2", timeout=1, known_cdn={})
        self.assertIn("限流（HTTP 503）", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
