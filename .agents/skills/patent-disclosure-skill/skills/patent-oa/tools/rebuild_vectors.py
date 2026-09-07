#!/usr/bin/env python
"""扫描 Obsidian oa/cases（及本地回退目录）重建全部案例向量。

用户确认后执行：
  python skills/patent-oa/tools/rebuild_vectors.py --confirm
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from case_md import chunk_case, parse_case_markdown
from config import (
    check_rebuild_needed,
    is_vector_enabled,
    load_config,
    mark_fingerprint_built,
    set_vector_enabled,
)
from embed import EmbedError, Embedder
from store import list_case_note_paths, open_store, upsert_case


def resolve_scan_dirs(cfg: dict, vault: str | None) -> list[Path]:
    dirs: list[Path] = []
    from vault_layout import resolve_oa_root

    if vault:
        dirs.append(resolve_oa_root(cfg, vault))
    # 本地回退 oa_home（即 cases 的父级）
    from config import oa_home

    dirs.append(oa_home())
    seen: set[str] = set()
    out: list[Path] = []
    for d in dirs:
        key = str(d.resolve())
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="")
    p.add_argument("--vault", default="", help="Obsidian 库根")
    p.add_argument(
        "--confirm",
        action="store_true",
        help="确认执行重建（必填，防止误触）",
    )
    p.add_argument("--dry-run", action="store_true", help="只列出将扫描的文件")
    args = p.parse_args(argv)

    cfg = load_config(args.config or None)
    if not is_vector_enabled(cfg):
        # 重建暗示用户要开向量
        set_vector_enabled(True, args.config or None)
        cfg = load_config(args.config or None)

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

    scan_dirs = resolve_scan_dirs(cfg, vault)
    files: list[Path] = []
    seen_files: set[str] = set()
    for d in scan_dirs:
        for f in list_case_note_paths(d):
            key = str(f.resolve())
            if key not in seen_files:
                seen_files.add(key)
                files.append(f)

    status = {
        "vector_enabled": True,
        "scan_dirs": [str(d) for d in scan_dirs],
        "files": [str(f) for f in files],
        "rebuild_check": check_rebuild_needed(cfg),
    }
    if args.dry_run or not args.confirm:
        status["ok"] = False if not args.confirm else True
        status["dry_run"] = bool(args.dry_run)
        if not args.confirm:
            status["note_zh"] = "请加 --confirm 执行重建；可先 --dry-run 查看文件列表。"
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if args.dry_run else 2

    embedder = Embedder(cfg)
    conn, _ = open_store(args.config or None, require_vec=True)
    ok = 0
    failed: list[dict] = []
    try:
        for path in files:
            try:
                meta, body = parse_case_markdown(path.read_text(encoding="utf-8"))
                if not meta.get("case_id"):
                    meta["case_id"] = path.stem
                chunks_spec = chunk_case(meta, body)
                texts = [t for _, t in chunks_spec]
                vectors = embedder.embed_texts(texts, purpose="document")
                chunk_payload = [
                    (kind, text, vectors[i]) for i, (kind, text) in enumerate(chunks_spec)
                ]
                upsert_case(
                    conn,
                    case=meta,
                    note_path=str(path),
                    body_text=body,
                    chunks=chunk_payload,
                )
                ok += 1
            except EmbedError as exc:
                failed.append({"path": str(path), "error": str(exc)})
                print(f"FAIL embed {path}: {exc}", file=sys.stderr)
                # 向量整体失败则中止，避免半截索引
                break
            except Exception as exc:
                failed.append({"path": str(path), "error": str(exc)})
                print(f"FAIL {path}: {exc}", file=sys.stderr)
    finally:
        conn.close()

    if failed and ok == 0:
        print(
            json.dumps(
                {"ok": False, "embedded": ok, "failed": failed, **status},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    fp = mark_fingerprint_built(args.config or None, cfg)
    print(
        json.dumps(
            {
                "ok": True,
                "embedded": ok,
                "failed": failed,
                "embedding_fingerprint": fp,
                "scan_dirs": status["scan_dirs"],
                "note_zh": "重建完成；此后检索将使用新向量模型。",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
