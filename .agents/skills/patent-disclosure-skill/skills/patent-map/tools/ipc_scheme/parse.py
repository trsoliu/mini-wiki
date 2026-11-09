"""Parse subclass codes/titles from WIPO EN XML, IPCPUB JSON, CNIPA PDFs."""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from .config import CATCHALL_SUFFIX, CATCHALL_TITLE, INDEXING_CODES, INDEXING_TITLE, IPC_VERSION

SUBCLASS_RE = re.compile(r"^[A-HY]\d{2}[A-Z]$")
CLASS_RE = re.compile(r"^[A-HY]\d{2}$")
GROUP_RE = re.compile(r"^[A-HY]\d{2}[A-Z]\d")
PAGE_RE = re.compile(r"^第 \d+ 页")
STOP_PREFIXES = ("附注", "注释", "小类索引", "大类索引", "导引标题")
TAG = re.compile(r"<[^>]+>")


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def text_of(el: ET.Element) -> str:
    return "".join(el.itertext()).strip()


def parse_en_xml(xml_path: Path) -> dict[str, str]:
    """kind=u subclass entries → {code: English title}."""
    tree = ET.parse(xml_path)
    out: dict[str, str] = {}
    for el in tree.iter():
        if local(el.tag) != "ipcEntry":
            continue
        if (el.get("kind") or "") != "u":
            continue
        code = (el.get("symbol") or "").strip().upper()
        if not SUBCLASS_RE.fullmatch(code):
            continue
        parts: list[str] = []
        for child in el:
            if local(child.tag) != "textBody":
                continue
            for title in child:
                if local(title.tag) != "title":
                    continue
                for part in title:
                    if local(part.tag) != "titlePart":
                        continue
                    texts = [text_of(t) for t in part if local(t.tag) == "text" and text_of(t)]
                    if texts:
                        parts.extend(texts)
                    else:
                        blob = text_of(part)
                        if blob:
                            parts.append(blob)
        title = "；".join(p for p in parts if p)
        if title:
            out[code] = title
    return out


def parse_ipcpub_json(path: Path) -> dict[str, str]:
    """IPCPUB CDN tree JSON → {subclass: title} if a Chinese dump ever appears."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}

    def walk(nodes) -> None:
        if isinstance(nodes, dict):
            nodes = [nodes]
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            code = str(node.get("symbol") or node.get("symbolcode") or "").strip().upper()
            kind = str(node.get("kind") or "")
            raw = node.get("title1") or node.get("title") or ""
            title = TAG.sub("", str(raw)).strip()
            if SUBCLASS_RE.fullmatch(code) and title and kind in ("u", "w", ""):
                out.setdefault(code, title)
            walk(node.get("children") or [])

    walk(data)
    return out


def tidy_zh(code: str, zh: str) -> str:
    text = zh.strip()
    if text.startswith(code):
        text = text[len(code) :].lstrip(" ：:.-")
    return text.strip(" .。；，,")


def finalize_zh(code: str, title: str) -> str:
    if code.endswith(CATCHALL_SUFFIX):
        return CATCHALL_TITLE
    if code in INDEXING_CODES:
        return INDEXING_TITLE
    return tidy_zh(code, title)


def clean_cnipa_title(raw: str) -> str:
    text = raw.replace("\n", "")
    text = re.sub(r"\[\d{4}\.\d{2}\]", "", text)
    text = re.sub(r"\[\d{8}\]", "", text)
    text = re.sub(r"〔\d+〕", "", text)
    text = re.sub(r"\[\d+\]", "", text)
    text = re.split(r"附注|注释", text, maxsplit=1)[0]
    text = re.split(r"[（(]", text, maxsplit=1)[0]
    text = re.sub(r"\s+", "", text)
    text = text.replace("碳碳不饱和", "碳-碳不饱和")
    for sep in ("；", "，"):
        if sep in text:
            text = text.split(sep, 1)[0]
            break
    return text.strip(" .。；，,")


def is_stop_line(line: str) -> bool:
    if PAGE_RE.match(line):
        return True
    if SUBCLASS_RE.fullmatch(line) or CLASS_RE.fullmatch(line) or GROUP_RE.match(line):
        return True
    if line.startswith(STOP_PREFIXES):
        return True
    if line.startswith(f"{IPC_VERSION}版IPC分类表-"):
        return True
    return False


def parse_cnipa_pdf_lines(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not SUBCLASS_RE.fullmatch(line):
            i += 1
            continue
        code = line
        parts: list[str] = []
        i += 1
        while i < len(lines):
            nxt = lines[i]
            if is_stop_line(nxt):
                break
            if nxt.startswith(".") or re.fullmatch(r"\d+\.", nxt):
                break
            parts.append(nxt)
            i += 1
        title = clean_cnipa_title("".join(parts))
        if title:
            out[code] = title
    return out


def pdf_lines(path: Path) -> list[str]:
    try:
        import fitz
    except ImportError as e:
        raise RuntimeError("解析国知局 PDF 需要 pymupdf：pip install -r skills/patent-map/tools/ipc_scheme/requirements.txt") from e
    doc = fitz.open(path)
    lines: list[str] = []
    for page in doc:
        for raw in page.get_text().splitlines():
            line = raw.strip()
            if line:
                lines.append(line)
    return lines


def parse_cnipa_pdfs(pdfs: dict[str, Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for section, path in pdfs.items():
        titles = parse_cnipa_pdf_lines(pdf_lines(path))
        print("cnipa", section, "subclasses", len(titles))
        out.update(titles)
    return out
