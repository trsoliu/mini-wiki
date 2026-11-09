#!/usr/bin/env python
"""
海外公开号（US / EP / WO / JP / KR …）→ 结构化全文（一次 Google Patents 详情页请求）。

替代海外件的「fetch_patent_pdf + extract_patent_text」：权利要求、从属关系、说明书段号直接取自
详情页结构，不从 PDF 切中文锚点。机翻文献（日、韩、德等）正文为英文译文，原文另存 ``text_original``。

产出（-o 目录下，与 extract_patent_text.py 同名同格式）：
  source/{PUB}.gp_detail.json   详情页解析结果
  source/{PUB}.pdf              官方 PDF（图片 CDN 下载；--no-pdf 跳过；失败不影响文本）
  raw_sections.jsonl / claim_tree.json / source_manifest.json / synthesis_bundle.json
  description_paragraphs.json   段号 → 英文正文（source_url 为 Google Patents 详情页）
  fetch_gp_status.json

不重试：HTTP 429 / 503 或拦截页 → 退出码 4，stderr ``GP_FULLTEXT_ERROR: reason=blocked``，本轮停止。
中国公开号不走本脚本（用 fetch_patent_pdf.py + extract_patent_text.py）。

用法：
  python skills/patent-reader/tools/extract/fetch_gp_fulltext.py --pub US11450918B2 \\
    -o outputs/patent_reader/read-US11450918B2-YYYYMMDDHHmm
"""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys

_PR_ROOT = _Path(__file__).resolve().parents[1]
if str(_PR_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_PR_ROOT))

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from extract.extract_patent_text import build_claim_tree
from extract.fetch_patent_pdf import download_pdf_bytes, normalize_pub
from google_patents import (
    GooglePatentsBlocked,
    GooglePatentsError,
    PatentDetail,
    fetch_detail,
)
from patent_type import infer_jurisdiction, resolve_reader_patent_type
from shared.common import organizations_from_assignees
from vault.desc_paragraphs import write_description_paragraphs_json

EXIT_BLOCKED = 4
DEFAULT_TIMEOUT = 20.0
PDF_TIMEOUT = 30.0


def _evidence_scope(detail: PatentDetail) -> str:
    if detail.claims and detail.description:
        return "full_text"
    if detail.claims or detail.description:
        return "partial"
    return "abstract_only"


def _claim_rows(detail: PatentDetail) -> list[dict]:
    rows = []
    for c in detail.claims:
        rows.append(
            {
                "number": c.number,
                "text": c.text,
                "text_original": c.text_original,
                "is_independent": c.is_independent,
                "parent": c.depends_on[0] if c.depends_on else None,
                "parent_candidates": list(c.depends_on),
            }
        )
    return rows


def _sections(detail: PatentDetail) -> list[dict]:
    sections: list[dict] = []
    if detail.abstract:
        sec = {"section_id": "abstract", "kind": "abstract", "text": detail.abstract}
        if detail.abstract_original:
            sec["text_original"] = detail.abstract_original
        sections.append(sec)
    for c in detail.claims:
        sec = {
            "section_id": f"claim_{c.number}",
            "kind": "claim",
            "number": c.number,
            "text": c.text,
            "is_independent": c.is_independent,
        }
        if c.text_original:
            sec["text_original"] = c.text_original
        sections.append(sec)
    for num in sorted(detail.description):
        sec = {"section_id": f"desc_{num}", "kind": "description", "text": detail.description[num]}
        if detail.description_original.get(num):
            sec["text_original"] = detail.description_original[num]
        sections.append(sec)
    return sections


def write_outputs(detail: PatentDetail, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pub = detail.publication_number
    source_dir = out_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    detail_path = source_dir / f"{pub}.gp_detail.json"
    detail_path.write_text(json.dumps(asdict(detail), ensure_ascii=False, indent=2), encoding="utf-8")

    claims = _claim_rows(detail)
    claim_tree = build_claim_tree(claims)
    sections = _sections(detail)
    organizations = organizations_from_assignees(list(detail.assignees))
    manifest = {
        "pub_number": pub,
        "source_path": detail.url,
        "source": "google_patents_html",
        "jurisdiction": detail.country,
        "language": "en",
        "translated_from": detail.translated_from,
        "evidence_scope": _evidence_scope(detail),
        "claims_parse_failed": False,
        "section_count": len(sections),
        "claim_count": len(claims),
        "independent_claim_count": sum(1 for c in claims if c["is_independent"]),
        "glossary_count": 0,
        "assignees": list(detail.assignees),
        "organizations": organizations,
        "inventors": list(detail.inventors),
        "ipc_codes": list(detail.cpc),
        "priority_date": detail.priority_date,
        "filing_date": detail.filing_date,
        "publication_date": detail.publication_date,
        "grant_date": detail.grant_date,
        "application_number": "",
        "invention_title": detail.title,
        "cited_pubs": [],
        "embodiment_count": 0,
        "description_paragraph_count": len(detail.description),
    }
    bundle = {
        "manifest": manifest,
        "claim_tree": claim_tree,
        "glossary_candidates": [],
        "embodiments": [],
        "background_snippets": [],
        "assignees": manifest["assignees"],
        "organizations": organizations,
        "inventors": manifest["inventors"],
        "ipc_codes": manifest["ipc_codes"],
        "filing_date": detail.filing_date,
        "publication_date": detail.publication_date,
        "application_number": "",
        "invention_title": detail.title,
        "cited_pubs": [],
        "claims": [
            {
                "number": c["number"],
                "text": c["text"],
                "text_original": c["text_original"],
                "is_independent": c["is_independent"],
            }
            for c in claims
        ],
        "sections_preview": [
            {"section_id": s["section_id"], "kind": s.get("kind"), "len": len(s.get("text", ""))}
            for s in sections
        ],
    }

    paths = {
        "detail": detail_path,
        "sections": out_dir / "raw_sections.jsonl",
        "manifest": out_dir / "source_manifest.json",
        "claim_tree": out_dir / "claim_tree.json",
        "bundle": out_dir / "synthesis_bundle.json",
    }
    with paths["sections"].open("w", encoding="utf-8") as f:
        for sec in sections:
            f.write(json.dumps(sec, ensure_ascii=False) + "\n")
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["claim_tree"].write_text(json.dumps(claim_tree, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["bundle"].write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    if detail.description:
        paths["desc_paras"] = write_description_paragraphs_json(
            out_dir / "description_paragraphs.json",
            detail.description,
            pub=pub,
            source_url=detail.url,
        )
    return paths


def download_pdf(detail: PatentDetail, out_dir: Path, *, timeout: float = PDF_TIMEOUT) -> dict:
    dest = out_dir / "source" / f"{detail.publication_number}.pdf"
    if not detail.pdf_url:
        return {"pdf_ok": False, "pdf_error": "详情页没有 PDF 链接"}
    try:
        data = download_pdf_bytes(detail.pdf_url, timeout=timeout, deadline=time.monotonic() + timeout)
    except Exception as exc:  # noqa: BLE001 — PDF 失败不影响文本产出
        return {"pdf_ok": False, "pdf_url": detail.pdf_url, "pdf_error": f"{type(exc).__name__}: {exc}"}
    dest.write_bytes(data)
    return {"pdf_ok": True, "pdf_url": detail.pdf_url, "pdf_path": str(dest.resolve()), "pdf_bytes": len(data)}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="海外公开号 → 结构化全文（Google Patents，一次请求，不重试）")
    ap.add_argument("--pub", required=True, help="海外公开号，如 US11450918B2、EP3389130B1、JP7371268B2")
    ap.add_argument("-o", "--outdir", type=Path, required=True, help="RUN 目录")
    ap.add_argument("--no-pdf", action="store_true", help="不下载官方 PDF")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="详情页请求超时秒数")
    args = ap.parse_args(argv)

    pub = normalize_pub(args.pub)
    jurisdiction = infer_jurisdiction(pub)
    if jurisdiction == "CN" or not jurisdiction:
        print(
            f"ERROR: {pub} 不是海外公开号；中国专利用 fetch_patent_pdf.py + extract_patent_text.py",
            file=sys.stderr,
        )
        return 2

    out_dir = args.outdir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    status_path = out_dir / "fetch_gp_status.json"
    started = time.monotonic()
    status: dict = {"ok": False, "pub": pub, "jurisdiction": jurisdiction}
    try:
        detail = fetch_detail(pub, timeout=args.timeout)
    except GooglePatentsError as exc:
        status.update({"error": str(exc), "reason": exc.reason, "status": exc.status})
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"GP_FULLTEXT_ERROR: reason={exc.reason} status={exc.status} {exc}",
            file=sys.stderr,
        )
        if isinstance(exc, GooglePatentsBlocked):
            print("HINT: 已停止，不要重试；稍后再试，或请用户提供 PDF / 全文", file=sys.stderr)
            return EXIT_BLOCKED
        print("HINT: 请用户提供 PDF / 全文后走 extract_patent_text.py", file=sys.stderr)
        return 1

    paths = write_outputs(detail, out_dir)
    pdf = {"pdf_ok": False, "pdf_error": "skipped (--no-pdf)"} if args.no_pdf else download_pdf(detail, out_dir)
    type_info = resolve_reader_patent_type(pub=pub)
    status.update(
        {
            "ok": True,
            "url": detail.url,
            "translated_from": detail.translated_from,
            "claim_count": len(detail.claims),
            "description_paragraph_count": len(detail.description),
            "patent_type": type_info.get("patent_type"),
            "patent_type_label_zh": type_info.get("label_zh"),
            "patent_type_source": type_info.get("source"),
            "elapsed_sec": round(time.monotonic() - started, 2),
            **pdf,
        }
    )
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    scope = _evidence_scope(detail)
    print(
        f"OK claims={len(detail.claims)} desc_paras={len(detail.description)} scope={scope}"
        + (f" translated_from={detail.translated_from}" if detail.translated_from else "")
    )
    print(f"MANIFEST: {paths['manifest']}")
    print(f"BUNDLE: {paths['bundle']}")
    print(f"CLAIM_TREE: {paths['claim_tree']}")
    print(f"SECTIONS: {paths['sections']}")
    if "desc_paras" in paths:
        print(f"DESC_PARAS: {paths['desc_paras']} ({len(detail.description)})")
    if pdf.get("pdf_ok"):
        print(f"PDF: {pdf['pdf_path']}")
    else:
        print(f"PDF_SKIPPED: {pdf.get('pdf_error')}", file=sys.stderr)
    if type_info.get("patent_type"):
        print(
            f"PATENT_TYPE: {type_info['patent_type']} ({type_info.get('label_zh')}) "
            f"source={type_info.get('source')}"
        )
    print(f"GP_FULLTEXT_STATUS: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
