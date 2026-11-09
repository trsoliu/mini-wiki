# -*- coding: utf-8 -*-
"""解析 Google Patents 详情页（``/patent/{公开号}/en``）。

机翻页（日、韩、德等）每段同时含原文（``span.google-src-text``）与英文译文：
``text`` 取译文，``text_original`` 取原文；英文原生文献 ``text_original`` 为空。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .html_text import tidy_block
from .results import split_publication_number

_BLOCK_TAGS = frozenset(
    {"div", "p", "br", "li", "ul", "ol", "claim-text", "heading", "tr", "table"}
)
_LEADING_NUM_RE = re.compile(r"^\s*\d+\s*[.．、]\s*")
_CLAIM_REF_RE = re.compile(r"(\d+)\s*$")
_TEXT_REF_RE = re.compile(
    r"\bclaims?\s+((?:\d+\s*(?:,|or|and|to|through|-|–|—)?\s*)+)",
    re.I,
)


@dataclass
class Claim:
    number: int
    text: str
    text_original: str = ""
    depends_on: list[int] = field(default_factory=list)

    @property
    def is_independent(self) -> bool:
        return not self.depends_on


@dataclass
class PatentDetail:
    publication_number: str
    country: str
    kind: str
    title: str
    abstract: str
    abstract_original: str
    claims: list[Claim]
    description: dict[str, str]
    description_original: dict[str, str]
    inventors: list[str]
    assignees: list[str]
    priority_date: str
    filing_date: str
    publication_date: str
    grant_date: str
    cpc: list[str]
    pdf_url: str
    url: str
    translated_from: str = ""


class _Buffer:
    def __init__(self) -> None:
        self.text: list[str] = []
        self.original: list[str] = []

    def add(self, value: str, *, original: bool) -> None:
        (self.original if original else self.text).append(value)

    def newline(self) -> None:
        self.text.append("\n")
        self.original.append("\n")

    def result(self) -> tuple[str, str]:
        return tidy_block("".join(self.text)), tidy_block("".join(self.original))


class _Capture:
    """跟踪一个元素直到其闭合（按同名标签计深度）。"""

    def __init__(self, tag: str, key: str) -> None:
        self.tag = tag
        self.depth = 1
        self.key = key
        self.buf = _Buffer()
        self.refs: list[int] = []


class _DetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.section = ""
        self.sections_seen = False
        self.skip_depth = 0
        self.src_depth = 0
        self.capture: _Capture | None = None
        self.claims: list[tuple[int, str, str, list[int]]] = []
        self.paragraphs: list[tuple[str, str, str]] = []
        self.abstract = _Buffer()
        self.inline: dict[str, str] = {}
        self.inline_key = ""
        self.inline_text: list[str] = []
        self.last_code = ""
        self.cpc: list[str] = []

    def _meta(self, key: str, value: str) -> None:
        self.meta.setdefault(key, []).append(value)

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k: (v or "") for k, v in attrs_list}
        classes = attrs.get("class", "").split()
        itemprop = attrs.get("itemprop", "")

        if tag == "meta":
            self._handle_meta(attrs)
            return
        if tag == "section" and itemprop in ("abstract", "claims", "description"):
            self.section = itemprop
            self.sections_seen = True
            return
        if tag == "time" and itemprop in ("priorityDate", "filingDate", "publicationDate"):
            self.inline.setdefault(itemprop, attrs.get("datetime", ""))
            return
        if itemprop in ("publicationNumber", "Code", "translatedLanguage") and not self.inline_key:
            self.inline_key = itemprop
            self.inline_text = []
            return

        if self.src_depth:
            if tag == "span":
                self.src_depth += 1
            return
        if tag == "span" and "google-src-text" in classes:
            self.src_depth = 1
            return
        if self.section and tag in ("h2", "aside"):
            self.skip_depth += 1
            return

        if self.section == "claims" and self._is_claim_start(tag, attrs, classes):
            self._close_capture()
            self.capture = _Capture(tag, attrs.get("num", ""))
            return
        if self.section == "description" and self._is_paragraph_start(tag, attrs, classes):
            self._close_capture()
            self.capture = _Capture(tag, attrs.get("num", ""))
            return

        cap = self.capture
        if cap is not None:
            if tag == cap.tag:
                cap.depth += 1
            if tag == "claim-ref":
                m = _CLAIM_REF_RE.search(attrs.get("idref", ""))
                if m:
                    cap.refs.append(int(m.group(1)))
            if tag in _BLOCK_TAGS:
                cap.buf.newline()
        elif self.section == "abstract" and tag in _BLOCK_TAGS:
            self.abstract.newline()

    def handle_startendtag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        if tag == "meta":
            self._handle_meta({k: (v or "") for k, v in attrs_list})
            return
        if tag == "br":
            if self.capture is not None:
                self.capture.buf.newline()
            elif self.section == "abstract":
                self.abstract.newline()

    def handle_endtag(self, tag: str) -> None:
        if self.inline_key and tag in ("dd", "span"):
            value = re.sub(r"\s+", " ", "".join(self.inline_text)).strip()
            if self.inline_key == "Code":
                self.last_code = value
            else:
                self.inline.setdefault(self.inline_key, value)
            self.inline_key = ""
            return
        if self.src_depth:
            if tag == "span":
                self.src_depth -= 1
            return
        if self.skip_depth and tag in ("h2", "aside"):
            self.skip_depth -= 1
            return
        if tag == "section" and self.section:
            self._close_capture()
            self.section = ""
            return
        cap = self.capture
        if cap is not None:
            if tag in _BLOCK_TAGS:
                cap.buf.newline()
            if tag == cap.tag:
                cap.depth -= 1
                if cap.depth == 0:
                    self._close_capture()

    def handle_data(self, data: str) -> None:
        if self.inline_key:
            self.inline_text.append(data)
            return
        if self.skip_depth:
            return
        original = self.src_depth > 0
        if self.capture is not None:
            self.capture.buf.add(data, original=original)
        elif self.section == "abstract":
            self.abstract.add(data, original=original)

    def _handle_meta(self, attrs: dict[str, str]) -> None:
        name = attrs.get("name", "")
        content = attrs.get("content", "")
        if name == "DC.contributor":
            self._meta(f"contributor:{attrs.get('scheme', '')}", content)
        elif name == "DC.date":
            self._meta(f"date:{attrs.get('scheme', '')}", content)
        elif name:
            self._meta(name, content)
        itemprop = attrs.get("itemprop", "")
        if itemprop == "kindCode":
            self.inline.setdefault("kindCode", content)
        elif (
            itemprop == "Leaf"
            and content == "true"
            and self.last_code
            and not self.sections_seen
            and self.last_code not in self.cpc
        ):
            self.cpc.append(self.last_code)

    @staticmethod
    def _is_claim_start(tag: str, attrs: dict[str, str], classes: list[str]) -> bool:
        if not attrs.get("num", "").strip().isdigit():
            return False
        return tag == "claim" or "claim" in classes

    @staticmethod
    def _is_paragraph_start(tag: str, attrs: dict[str, str], classes: list[str]) -> bool:
        if not attrs.get("num", "").strip().isdigit():
            return False
        return tag == "p" or "description-paragraph" in classes

    def _close_capture(self) -> None:
        cap = self.capture
        self.capture = None
        if cap is None or not cap.key:
            return
        text, original = cap.buf.result()
        if self.section == "claims":
            self.claims.append((int(cap.key), text, original, cap.refs))
        elif self.section == "description":
            self.paragraphs.append((cap.key.zfill(4)[-4:], text, original))


def _refs_from_text(text: str, number: int) -> list[int]:
    found: list[int] = []
    for m in _TEXT_REF_RE.finditer(text or ""):
        chunk = m.group(1)
        for a, b in re.findall(r"(\d+)\s*(?:to|through|-|–|—)\s*(\d+)", chunk):
            found.extend(range(int(a), int(b) + 1))
        found.extend(int(n) for n in re.findall(r"\d+", chunk))
    return sorted({n for n in found if 0 < n < number})


def _first(meta: dict[str, list[str]], key: str) -> str:
    values = meta.get(key) or []
    return re.sub(r"\s+", " ", values[0]).strip() if values else ""


def _all(meta: dict[str, list[str]], key: str) -> list[str]:
    out: list[str] = []
    for value in meta.get(key) or []:
        value = re.sub(r"\s+", " ", value).strip()
        if value and value not in out:
            out.append(value)
    return out


def parse_detail_html(html_text: str, *, pub: str = "", url: str = "") -> PatentDetail:
    parser = _DetailParser()
    parser.feed(html_text or "")
    parser.close()

    claims: list[Claim] = []
    seen: set[int] = set()
    for number, text, original, refs in parser.claims:
        if number in seen or not text:
            continue
        seen.add(number)
        text = _LEADING_NUM_RE.sub("", text, count=1)
        depends = sorted({n for n in refs if 0 < n < number}) or _refs_from_text(text, number)
        claims.append(Claim(number=number, text=text, text_original=original, depends_on=depends))
    claims.sort(key=lambda c: c.number)

    description: dict[str, str] = {}
    description_original: dict[str, str] = {}
    for num, text, original in parser.paragraphs:
        if text and num not in description:
            description[num] = text
            if original:
                description_original[num] = original

    abstract, abstract_original = parser.abstract.result()
    if not abstract:
        abstract = _first(parser.meta, "DC.description")

    number = (parser.inline.get("publicationNumber") or pub or "").strip().upper()
    country, _digits, kind = split_publication_number(number)
    kind = parser.inline.get("kindCode") or kind
    return PatentDetail(
        publication_number=number,
        country=country,
        kind=kind,
        title=_first(parser.meta, "DC.title"),
        abstract=abstract,
        abstract_original=abstract_original,
        claims=claims,
        description=description,
        description_original=description_original,
        inventors=_all(parser.meta, "contributor:inventor"),
        assignees=_all(parser.meta, "contributor:assignee"),
        priority_date=parser.inline.get("priorityDate", ""),
        filing_date=parser.inline.get("filingDate", "") or _first(parser.meta, "date:dateSubmitted"),
        publication_date=parser.inline.get("publicationDate", ""),
        grant_date=_first(parser.meta, "date:issue"),
        cpc=list(parser.cpc),
        pdf_url=_first(parser.meta, "citation_pdf_url"),
        url=url,
        translated_from=parser.inline.get("translatedLanguage", ""),
    )
