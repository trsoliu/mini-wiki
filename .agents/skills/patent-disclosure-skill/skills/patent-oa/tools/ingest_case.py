#!/usr/bin/env python
"""案例脱敏入库：写 Obsidian/docs 笔记并更新 sqlite-vec。

支持直接喂 PDF：自动抽取文本 → 生成案例草稿 md →（可选）入库。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from case_md import chunk_case, dump_case_markdown, parse_case_markdown
from config import (
    is_vector_enabled,
    load_config,
    sqlite_path_from_config,
)
from embed import EmbedError, Embedder
from pdf_text import read_document, write_extract
from redact import redact_text
from store import open_store, upsert_case
from vault_layout import (
    STATUS_DRAFT,
    STATUS_HISTORY,
    enrich_case_note,
    ensure_oa_dirs,
    note_path_for,
    refresh_oa_vault,
    resolve_oa_root,
    status_subdir,
)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def build_draft_from_pdfs(
    *,
    notice_pdf: Path,
    reply_pdf: Path | None,
    case_id: str,
    title: str,
    out_md: Path,
) -> dict:
    """从通知书/答复 PDF 生成带 frontmatter 的案例草稿（仍须人审补全标签后入库）。"""
    notice = read_document(notice_pdf)
    write_extract(
        notice,
        notice_pdf.parent / f"{notice_pdf.stem}.extracted.txt",
        out_json=notice_pdf.parent / f"{notice_pdf.stem}.extracted.json",
    )
    sections = [
        f"# {title or case_id}",
        "",
        "## 通知书要点",
        "",
        (notice.get("text") or "").strip() or "（未能抽取文本，请检查是否为扫描件）",
        "",
    ]
    warnings = list(notice.get("warnings") or [])
    sources = [str(notice_pdf.resolve())]
    if reply_pdf:
        reply = read_document(reply_pdf)
        write_extract(
            reply,
            reply_pdf.parent / f"{reply_pdf.stem}.extracted.txt",
            out_json=reply_pdf.parent / f"{reply_pdf.stem}.extracted.json",
        )
        warnings.extend(reply.get("warnings") or [])
        sources.append(str(reply_pdf.resolve()))
        sections.extend(
            [
                "## 陈述要点",
                "",
                (reply.get("text") or "").strip() or "（答复 PDF 未能抽取文本）",
                "",
                "## 策略",
                "",
                "（待根据答复 PDF 归纳）",
                "",
                "## 结果",
                "",
                "unknown",
                "",
            ]
        )
    else:
        sections.extend(
            [
                "## 策略",
                "",
                "（待补）",
                "",
                "## 陈述要点",
                "",
                "（待补）",
                "",
                "## 结果",
                "",
                "unknown",
                "",
            ]
        )

    meta = {
        "case_id": case_id,
        "title": title or case_id,
        "patent_type": "invention",
        "statutes": [],
        "defect_types": [],
        "domain": "",
        "notice_kind": "office_action",
        "outcome": "unknown",
        "strategy": [],
        "compare_refs": [],
        "related_cases": [],
        "status": STATUS_DRAFT,
        "redacted": False,
        "tags": [],
        "source_paths": sources,
        "created_at": _now(),
        "updated_at": _now(),
    }
    body = "\n".join(sections)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(dump_case_markdown(meta, body), encoding="utf-8")
    return {
        "draft_md": str(out_md.resolve()),
        "case_id": case_id,
        "warnings": warnings,
        "notice_chars": notice.get("char_count"),
        "sources": sources,
    }


def ingest_one(
    *,
    source: Path,
    config_path: str | None,
    vault: str | None,
    extra_names: list[str],
    skip_redact: bool,
    dry_run: bool,
) -> dict:
    cfg = load_config(config_path)
    raw = source.read_text(encoding="utf-8")
    meta, body = parse_case_markdown(raw)
    if not meta.get("case_id"):
        meta["case_id"] = source.stem
    if not skip_redact:
        body2, notes = redact_text(body, extra_names=extra_names)
        body = body2
        if meta.get("title"):
            t2, n2 = redact_text(str(meta["title"]), extra_names=extra_names)
            meta["title"] = t2
            notes.extend(n2)
        meta["redacted"] = True
        meta["redact_notes"] = notes[:40]
    else:
        meta.setdefault("redacted", False)

    meta["updated_at"] = _now()
    meta.setdefault("created_at", meta["updated_at"])
    meta.setdefault("patent_type", "invention")
    meta.setdefault("statutes", [])
    meta.setdefault("defect_types", [])
    meta.setdefault("tags", [])
    meta.setdefault("related_cases", [])
    meta.setdefault("status", STATUS_HISTORY)
    tags = list(meta.get("tags") or [])
    for d in meta.get("defect_types") or []:
        tag = f"oa/{d}"
        if tag not in tags:
            tags.append(tag)
    for s in meta.get("statutes") or []:
        tag = f"法条/{s}"
        if tag not in tags:
            tags.append(tag)
    meta["tags"] = tags

    oa_root = resolve_oa_root(cfg, vault)
    ensure_oa_dirs(oa_root)
    papers_dir = "Research/Patents"
    try:
        sys.path.insert(0, str(ROOT.parent / "patent-reader" / "tools"))
        from shared.common import runtime_config

        papers_dir = runtime_config().get("papers_dir") or papers_dir
    except Exception:
        pass
    vault_path = Path(vault).expanduser().resolve() if vault else None
    meta, body = enrich_case_note(
        meta,
        body,
        oa_root=oa_root,
        vault=vault_path,
        papers_dir=papers_dir,
    )
    note_path = note_path_for(oa_root, str(meta["case_id"]), meta["status"])
    note_path.parent.mkdir(parents=True, exist_ok=True)
    md = dump_case_markdown(meta, body)

    chunks_spec = chunk_case(meta, body)
    chunk_payload = None
    embed_error = ""
    vector_mode = "skipped"
    do_vector = is_vector_enabled(cfg) and meta.get("status") == STATUS_HISTORY
    if do_vector:
        try:
            embedder = Embedder(cfg)
            texts = [t for _, t in chunks_spec]
            vectors = embedder.embed_texts(texts, purpose="document")
            chunk_payload = [
                (kind, text, vectors[i]) for i, (kind, text) in enumerate(chunks_spec)
            ]
            vector_mode = "embedded"
        except EmbedError as exc:
            embed_error = str(exc)
            vector_mode = "meta_only_embed_failed"
        except Exception as exc:
            embed_error = str(exc)
            vector_mode = "meta_only_embed_failed"
    elif meta.get("status") != STATUS_HISTORY:
        vector_mode = "skipped_non_history"
    else:
        vector_mode = "meta_only_vector_disabled"

    result = {
        "case_id": meta["case_id"],
        "note_path": str(note_path),
        "chunks": len(chunk_payload or chunks_spec),
        "vector_mode": vector_mode,
        "redacted": bool(meta.get("redacted")),
        "dry_run": dry_run,
    }
    if embed_error:
        result["embed_error"] = embed_error
    if dry_run:
        result["preview_meta"] = {
            k: meta[k]
            for k in ("case_id", "title", "statutes", "defect_types", "tags")
            if k in meta
        }
        return result

    note_path.write_text(md, encoding="utf-8")
    # 历史案才进 sqlite；pending/draft 只写笔记
    if meta.get("status") == STATUS_HISTORY:
        conn, _ = open_store(
            config_path,
            require_vec=(chunk_payload is not None),
        )
        try:
            upsert_case(
                conn,
                case=meta,
                note_path=str(note_path),
                body_text=body,
                chunks=chunk_payload,
            )
        finally:
            conn.close()
        result["sqlite"] = str(sqlite_path_from_config(cfg))
    else:
        result["sqlite"] = None
        result["note_zh"] = "非 history 状态：已写 Obs 笔记，未写入向量库。"

    try:
        refresh = refresh_oa_vault(cfg=cfg, vault=vault, papers_dir=papers_dir)
        result["oa_refresh"] = {
            "index": refresh.get("index"),
            "canvas": refresh.get("canvas"),
            "counts": refresh.get("counts"),
        }
    except Exception as exc:
        result["oa_refresh_error"] = str(exc)
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-i",
        "--input",
        default="",
        help="案例 md；若省略且给了 --pdf，则先从 PDF 生成草稿",
    )
    p.add_argument("--pdf", default="", help="通知书 PDF（自动抽取，推荐）")
    p.add_argument("--reply-pdf", default="", help="可选：意见陈述/答复 PDF")
    p.add_argument("--case-id", default="", help="从 PDF 起草时的 case_id")
    p.add_argument("--title", default="", help="从 PDF 起草时的标题")
    p.add_argument(
        "--draft-only",
        action="store_true",
        help="仅从 PDF 生成案例 md 草稿，不入库（供人审补标签）",
    )
    p.add_argument("--config", default="")
    p.add_argument("--vault", default="", help="Obsidian 库根；默认回退 {Documents}/…/oa/cases")
    p.add_argument("--extra-name", action="append", default=[], help="额外脱敏姓名/实体")
    p.add_argument("--skip-redact", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    vault = args.vault.strip() or None
    if not vault:
        try:
            sys.path.insert(0, str(ROOT.parent / "patent-reader" / "tools"))
            from shared.common import resolve_obsidian_vault

            resolved = resolve_obsidian_vault()
            if resolved.get("vault") and not resolved.get("needs_user_input"):
                vault = str(resolved["vault"])
        except Exception:
            vault = None

    src: Path | None = Path(args.input) if args.input else None
    draft_info = None

    if args.pdf:
        pdf = Path(args.pdf)
        if not pdf.is_file():
            raise SystemExit(f"找不到 PDF: {pdf}")
        case_id = (args.case_id or pdf.stem).strip()
        cfg = load_config(args.config or None)
        oa_root = resolve_oa_root(cfg, vault)
        ensure_oa_dirs(oa_root)
        draft_dir = status_subdir(oa_root, STATUS_DRAFT)
        draft_md = draft_dir / f"{case_id}.md"
        draft_info = build_draft_from_pdfs(
            notice_pdf=pdf,
            reply_pdf=Path(args.reply_pdf) if args.reply_pdf else None,
            case_id=case_id,
            title=args.title or case_id,
            out_md=draft_md,
        )
        src = Path(draft_info["draft_md"])
        if args.draft_only:
            print(json.dumps({"ok": True, **draft_info, "draft_only": True}, ensure_ascii=False, indent=2))
            return 0

    if src is None:
        raise SystemExit("需要 -i 案例.md，或 --pdf 通知书.pdf")
    if not src.is_file():
        raise SystemExit(f"找不到输入: {src}")
    if src.suffix.lower() == ".pdf":
        raise SystemExit("请使用 --pdf 传入 PDF（不要把 PDF 当作 -i）")

    out = ingest_one(
        source=src,
        config_path=args.config or None,
        vault=vault,
        extra_names=list(args.extra_name or []),
        skip_redact=bool(args.skip_redact),
        dry_run=bool(args.dry_run),
    )
    if draft_info:
        out["from_pdf_draft"] = draft_info
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
