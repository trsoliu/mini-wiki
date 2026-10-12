"""fetch_patent_pdf：HTML/CDN 解析、并行解析与下载重试（不依赖外网）。"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))

import extract.fetch_patent_pdf as mod
from extract.fetch_patent_pdf import (
    extract_pdf_urls_from_html,
    fetch_patent_pdf,
    load_known_cdn_examples,
    normalize_pub,
    read_page_pdf_urls,
    resolve_pdf_url,
)


SAMPLE_HTML = """
<html>
<meta name="citation_pdf_url" content="https://patentimages.storage.googleapis.com/58/1b/9b/07a9f35635df34/CN119961390A.pdf">
<title>CN119961390A - demo</title>
<a href="https://patentimages.storage.googleapis.com/58/1b/9b/07a9f35635df34/CN119961390A.pdf" itemprop="pdfLink">Download PDF</a>
</html>
"""
FAKE_PDF = b"%PDF-1.4" + b"0" * 6000


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_a):
        self.close()


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "x", {}, None)


class _Patch:
    def __init__(self, **attrs):
        self.attrs = attrs
        self.old: dict = {}

    def __enter__(self):
        for k, v in self.attrs.items():
            self.old[k] = getattr(mod, k)
            setattr(mod, k, v)
        return self

    def __exit__(self, *_a):
        for k, v in self.old.items():
            setattr(mod, k, v)


class FetchPatentPdfTest(unittest.TestCase):
    def test_normalize_pub(self) -> None:
        self.assertEqual(normalize_pub(" cn119961390a "), "CN119961390A")

    def test_extract_cdn_from_html(self) -> None:
        urls = extract_pdf_urls_from_html(SAMPLE_HTML, "CN119961390A")
        self.assertTrue(urls)
        self.assertIn("CN119961390A.pdf", urls[0])
        self.assertTrue(urls[0].startswith("https://patentimages.storage.googleapis.com/"))

    def test_load_known_cdn_examples(self) -> None:
        known = load_known_cdn_examples()
        self.assertIn("CN114552122A", known)
        self.assertTrue(known["CN114552122A"].endswith(".pdf"))

    def test_page_read_stops_after_citation_meta(self) -> None:
        body = SAMPLE_HTML.encode() + b"x" * 200_000
        resp = _FakeResp(body)
        with _Patch(_open=lambda *_a, **_k: resp):
            urls, n = read_page_pdf_urls("https://p/zh", "CN119961390A")
        self.assertIn("CN119961390A.pdf", urls[0])
        self.assertLess(n, 20_000)

    def test_resolve_falls_back_to_known_cdn(self) -> None:
        """页面全部失败时，用 known_cdn_examples 兜底。"""

        def boom(*_a, **_k):
            raise TimeoutError("simulated")

        with _Patch(read_page_pdf_urls=boom):
            url, source, log = resolve_pdf_url(
                "CN114552122A",
                timeout=1,
                known_cdn={
                    "CN114552122A": "https://patentimages.storage.googleapis.com/c2/6c/51/75412585086edf/CN114552122A.pdf"
                },
            )
        self.assertEqual(source, "known_cdn_examples")
        self.assertIn("CN114552122A.pdf", url)
        self.assertTrue(any("fail_page" in x for x in log))

    def test_resolve_reports_not_indexed_on_404(self) -> None:
        def not_found(page, *_a, **_k):
            raise _http_error(page, 404)

        with _Patch(read_page_pdf_urls=not_found):
            with self.assertRaises(FileNotFoundError) as cm:
                resolve_pdf_url("CN122847765A", timeout=1, known_cdn={})
        self.assertIn("未收录", str(cm.exception))

    def test_resolve_reports_design_without_pdf(self) -> None:
        with _Patch(read_page_pdf_urls=lambda *_a, **_k: ([], 1000)):
            with self.assertRaises(FileNotFoundError) as cm:
                resolve_pdf_url("CN309939145S", timeout=1, known_cdn={})
        self.assertIn("fetch_design_views.py", str(cm.exception))

    def test_fetch_uses_direct_url(self) -> None:
        calls: list[str] = []

        def fake_dl(url: str, **_k) -> bytes:
            calls.append(url)
            return FAKE_PDF

        with _Patch(download_pdf_bytes=fake_dl):
            with tempfile.TemporaryDirectory() as td:
                out = Path(td)
                st = fetch_patent_pdf("CN1", out, url="https://example.com/CN1.pdf")
                self.assertTrue(st["ok"])
                self.assertEqual(st["source_id"], "direct_url")
                self.assertTrue((out / "source" / "CN1.pdf").is_file())
        self.assertEqual(calls, ["https://example.com/CN1.pdf"])

    def test_download_retries_transient_error(self) -> None:
        calls: list[str] = []

        def flaky(url: str, **_k) -> bytes:
            calls.append(url)
            if len(calls) == 1:
                raise TimeoutError("simulated stall")
            return FAKE_PDF

        with _Patch(download_pdf_bytes=flaky):
            with tempfile.TemporaryDirectory() as td:
                st = fetch_patent_pdf("CN1", Path(td), url="https://example.com/CN1.pdf")
        self.assertTrue(st["ok"])
        self.assertEqual(len(calls), 2)

    def test_download_404_falls_to_known_cdn(self) -> None:
        page_url = "https://patentimages.storage.googleapis.com/aa/CN114552122A.pdf"
        known_url = load_known_cdn_examples()["CN114552122A"]
        calls: list[str] = []

        def dl(url: str, **_k) -> bytes:
            calls.append(url)
            if url == page_url:
                raise _http_error(url, 404)
            return FAKE_PDF

        with _Patch(
            download_pdf_bytes=dl,
            resolve_pdf_url=lambda *_a, **_k: (page_url, "google_patents_page", []),
        ):
            with tempfile.TemporaryDirectory() as td:
                st = fetch_patent_pdf("CN114552122A", Path(td))
        self.assertTrue(st["ok"])
        self.assertEqual(st["source_id"], "known_cdn_examples")
        self.assertEqual(calls, [page_url, known_url])


if __name__ == "__main__":
    raise SystemExit(unittest.main())
