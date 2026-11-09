"""Download WIPO EN scheme, probe IPCPUB Chinese JSON, fetch CNIPA PDFs."""
from __future__ import annotations

import gzip
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from .config import (
    CNIPA_PDF_FALLBACK,
    CNIPA_TABLE_PAGE,
    IPC_VERSION_DATE,
    IPCPUB_CDN,
    IPCPUB_HOME,
    USER_AGENT,
    WIPO_SCHEME_ZIP,
)

SCHEME_XML_NAME = f"EN_ipc_scheme_{IPC_VERSION_DATE}.xml"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, identity"}


def _unwrap(data: bytes, content_encoding: str = "") -> bytes:
    if not data:
        return data
    if data[:2] == b"\x1f\x8b" or (content_encoding or "").lower() == "gzip":
        if data[:2] == b"\x1f\x8b":
            return gzip.decompress(data)
    return data


def _request(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _unwrap(resp.read(), resp.getheader("Content-Encoding") or "")


def _get(url: str, timeout: int = 60) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, _unwrap(resp.read(), resp.getheader("Content-Encoding") or "")
    except urllib.error.HTTPError as e:
        body = e.read() if e.fp else b""
        return e.code, _unwrap(body, e.headers.get("Content-Encoding") or "") if body else b""


def download_wipo_scheme_xml(cache: Path) -> Path:
    """Return EN scheme XML path; download+unzip into cache if needed."""
    cache.mkdir(parents=True, exist_ok=True)
    xml_path = cache / SCHEME_XML_NAME
    if xml_path.is_file() and xml_path.stat().st_size > 100_000:
        return xml_path
    zip_path = cache / Path(WIPO_SCHEME_ZIP).name
    if not zip_path.is_file() or zip_path.stat().st_size < 100_000:
        print("download", WIPO_SCHEME_ZIP)
        zip_path.write_bytes(_request(WIPO_SCHEME_ZIP))
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.replace("\\", "/").endswith(SCHEME_XML_NAME)]
        if not names:
            names = [n for n in zf.namelist() if n.lower().endswith(".xml") and "EN_" in n]
        if not names:
            raise FileNotFoundError(f"no EN scheme XML in {zip_path}: {zf.namelist()[:12]}")
        target = names[0]
        xml_path.write_bytes(zf.read(target))
    return xml_path


def ipcpub_timestamp(html: str, version_date: str) -> str:
    m = re.search(rf'"{re.escape(version_date)}"\s*:\s*"(\d{{14}})"', html)
    return m.group(1) if m else ""


def ipcpub_scheme_json_url(version_date: str, timestamp: str, lang: str, name: str = "index") -> str:
    return f"{IPCPUB_CDN}/{version_date}/{timestamp}/IPC/scheme/{lang}/json/{name}.json"


def probe_ipcpub_zh(cache: Path) -> Path | None:
    """If WIPO publishes Chinese scheme JSON, save index.json. Official IPCPUB is EN/FR only."""
    cache.mkdir(parents=True, exist_ok=True)
    status, home = _get(IPCPUB_HOME)
    if status != 200:
        print("ipcpub home", status)
        return None
    html = home.decode("utf-8", "replace")
    ts = ipcpub_timestamp(html, IPC_VERSION_DATE)
    if not ts:
        print("ipcpub: no timestamp for", IPC_VERSION_DATE)
        return None
    url = ipcpub_scheme_json_url(IPC_VERSION_DATE, ts, "zh")
    print("ipcpub zh", url)
    st, body = _get(url)
    if st != 200 or not body.strip().startswith(b"[") and not body.strip().startswith(b"{"):
        print(f"ipcpub zh scheme unavailable ({st}); WIPO authentic languages are EN/FR")
        return None
    out = cache / "ipcpub_zh_index.json"
    out.write_bytes(body)
    print("wrote", out, "bytes", len(body))
    return out


def _cnipa_pdf_links(html: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for href, showname in re.findall(
        r'href="([^"]*downfile\.jsp[^"]+)"[^>]*>\s*([^<]*分类表-[A-H]部\.pdf)',
        html,
        flags=re.I,
    ):
        section = showname.strip()[-4]
        if section in "ABCDEFGH":
            found[section] = urllib.parse.urljoin(CNIPA_TABLE_PAGE, html_unescape_href(href))
    if found:
        return found
    for href in re.findall(r'href="([^"]*downfile\.jsp[^"]+)"', html):
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        showname = urllib.parse.unquote((qs.get("showname") or [""])[0])
        m = re.search(r"分类表-([A-H])部", showname)
        if m:
            found[m.group(1)] = urllib.parse.urljoin(CNIPA_TABLE_PAGE, html_unescape_href(href))
    return found


def html_unescape_href(href: str) -> str:
    return (
        href.replace("&amp;", "&")
        .replace("&#38;", "&")
        .replace("&quot;", '"')
    )


def download_cnipa_pdfs(cache: Path) -> dict[str, Path]:
    """Download A–H Chinese classification PDFs listed on the CNIPA notice page."""
    pdf_dir = cache / "cnipa_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    print("cnipa page", CNIPA_TABLE_PAGE)
    html = _request(CNIPA_TABLE_PAGE, timeout=60).decode("utf-8", "replace")
    (cache / "cnipa_table_page.html").write_text(html, encoding="utf-8")
    links = _cnipa_pdf_links(html)
    if len(links) < 8:
        print("cnipa scrape incomplete", sorted(links), "→ fallback hashes")
        links = {**CNIPA_PDF_FALLBACK, **links}
    out: dict[str, Path] = {}
    for section in "ABCDEFGH":
        path = pdf_dir / f"IPC_{IPC_VERSION_DATE}_{section}.pdf"
        if path.is_file() and path.stat().st_size > 50_000:
            out[section] = path
            continue
        url = links[section]
        print("download", section, url)
        path.write_bytes(_request(url, timeout=180))
        out[section] = path
    return out
