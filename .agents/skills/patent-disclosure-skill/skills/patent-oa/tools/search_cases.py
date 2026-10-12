#!/usr/bin/env python
"""标签过滤 + 可选向量检索（向量不可用时自动回退标签）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config import check_rebuild_needed, is_vector_enabled, load_config
from embed import EmbedError, Embedder
from pdf_text import read_document, write_extract
from store import open_store, search

_DEFAULT_QUERY_CHARS = 6000


def diff_fields(hit: dict, query: dict) -> dict:
    return {
        "domain_query": query.get("domain") or "",
        "domain_case": hit.get("domain") or "",
        "domain_match": (query.get("domain") or "") == (hit.get("domain") or "")
        if (query.get("domain") and hit.get("domain"))
        else None,
        "statutes_query": query.get("statutes") or [],
        "statutes_case": hit.get("statutes") or [],
        "defect_types_query": query.get("defect_types") or [],
        "defect_types_case": hit.get("defect_types") or [],
        "patent_type_query": query.get("patent_type") or "",
        "patent_type_case": hit.get("patent_type") or "",
        "compare_refs_case": hit.get("compare_refs") or [],
        "outcome_case": hit.get("outcome") or "",
    }


def resolve_query(
    *,
    query: str,
    query_file: str,
    pdf: str,
    save_extract_dir: str,
    query_chars: int,
) -> tuple[str, dict]:
    meta: dict = {"source": "text", "warnings": [], "extract_path": ""}
    q = (query or "").strip()
    if query_file:
        q = Path(query_file).read_text(encoding="utf-8").strip()
        meta["source"] = "file"
        meta["path"] = str(Path(query_file).resolve())
    if pdf:
        src = Path(pdf)
        result = read_document(src)
        meta["source"] = "pdf" if src.suffix.lower() == ".pdf" else src.suffix.lower()
        meta["path"] = str(src.resolve())
        meta["warnings"] = list(result.get("warnings") or [])
        meta["page_count"] = result.get("page_count")
        out_dir = Path(save_extract_dir) if save_extract_dir else src.parent
        out_txt = out_dir / f"{src.stem}.extracted.txt"
        out_json = out_dir / f"{src.stem}.extracted.json"
        write_meta = write_extract(result, out_txt, out_json=out_json)
        meta["extract_path"] = write_meta["text_path"]
        meta["extract_json"] = write_meta.get("json_path", "")
        q = (result.get("text") or "").strip()
    if not q and not (query or query_file or pdf):
        # 允许纯标签检索：无 query 文本
        return "", meta
    if pdf or query_file or query:
        if not q:
            raise SystemExit("PDF/文件未抽出可用文本")
    full_len = len(q)
    if q and query_chars > 0 and len(q) > query_chars:
        q = q[:query_chars]
        meta["truncated"] = True
        meta["full_char_count"] = full_len
        meta["query_char_count"] = len(q)
    else:
        meta["truncated"] = False
        meta["query_char_count"] = len(q)
    return q, meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", default="", help="审查通知书 PDF（自动抽取文本，推荐）")
    p.add_argument("--query", default="", help="检索文本（通知书摘要/缺陷描述）")
    p.add_argument("--query-file", default="", help="从已抽取的 .txt/.md 读查询")
    p.add_argument("--save-extract-dir", default="")
    p.add_argument("--query-chars", type=int, default=_DEFAULT_QUERY_CHARS)
    p.add_argument("--config", default="")
    p.add_argument("--patent-type", default="")
    p.add_argument("--statute", action="append", default=[])
    p.add_argument("--defect", action="append", default=[])
    p.add_argument("--tag", action="append", default=[], help="Obsidian 标签过滤")
    p.add_argument("--domain", default="")
    p.add_argument("--top-k", type=int, default=0)
    p.add_argument(
        "--tags-only",
        action="store_true",
        help="强制仅标签检索（忽略向量）",
    )
    args = p.parse_args(argv)

    has_text_src = bool(args.pdf or args.query or args.query_file)
    has_filters = bool(args.statute or args.defect or args.tag or args.patent_type or args.domain)
    if not has_text_src and not has_filters:
        raise SystemExit("需要 --pdf/--query/--query-file，或至少一项标签/法条过滤")

    q, qmeta = resolve_query(
        query=args.query,
        query_file=args.query_file,
        pdf=args.pdf,
        save_extract_dir=args.save_extract_dir,
        query_chars=int(args.query_chars or 0),
    )

    cfg = load_config(args.config or None)
    top_k = int(args.top_k or cfg.get("default_top_k") or 5)
    rebuild = check_rebuild_needed(cfg)
    mode = "tags_only"
    embed_error = ""
    vec = None

    use_vector = (
        is_vector_enabled(cfg)
        and not args.tags_only
        and bool(q)
        and not rebuild.get("needed")
    )
    # 若需重建但仍启用向量，尝试用现有索引；失败再回退。首次未建索引则直接标签。
    if is_vector_enabled(cfg) and not args.tags_only and bool(q):
        if rebuild.get("needed") and rebuild.get("reason") == "first_enable":
            mode = "tags_only"
            embed_error = "vector_index_missing_needs_rebuild"
        else:
            try:
                embedder = Embedder(cfg)
                vec = embedder.embed_one(q, purpose="query")
                mode = "vector"
            except EmbedError as exc:
                mode = "tags_fallback"
                embed_error = str(exc)
                vec = None
            except Exception as exc:
                mode = "tags_fallback"
                embed_error = str(exc)
                vec = None
    elif args.tags_only or not is_vector_enabled(cfg):
        mode = "tags_only"

    conn, _ = open_store(args.config or None, require_vec=(mode == "vector"))
    try:
        hits = search(
            conn,
            query_vec=vec,
            top_k=top_k,
            patent_type=args.patent_type or None,
            statutes=args.statute or None,
            defect_types=args.defect or None,
            domain=args.domain or None,
            tags=args.tag or None,
        )
    finally:
        conn.close()

    query_meta = {
        "patent_type": args.patent_type,
        "statutes": args.statute,
        "defect_types": args.defect,
        "tags": args.tag,
        "domain": args.domain,
    }
    for h in hits:
        h["diff"] = diff_fields(h, query_meta)

    out = {
        "query_preview": (q or "")[:500],
        "query_meta": qmeta,
        "retrieval_mode": mode,
        "vector_enabled": is_vector_enabled(cfg),
        "rebuild": rebuild,
        "top_k": top_k,
        "hits": hits,
    }
    if embed_error:
        out["embed_error"] = embed_error
        print(f"WARN: 向量不可用，已回退标签检索: {embed_error}", file=sys.stderr)
    if rebuild.get("needed") and rebuild.get("ask_zh"):
        out["rebuild_hint_zh"] = rebuild["ask_zh"]
        print(f"HINT: {rebuild['ask_zh']}", file=sys.stderr)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if qmeta.get("warnings"):
        for w in qmeta["warnings"]:
            print(f"WARN: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
