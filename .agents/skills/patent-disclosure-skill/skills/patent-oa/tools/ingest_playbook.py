#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""审查答复 · 经验手册：预读 / 安装 book-to-skill / 转写入 Obs。

  python skills/patent-oa/tools/ingest_playbook.py peek --path "D:/books/oa.pdf"
  python skills/patent-oa/tools/ingest_playbook.py ensure-skill
  python skills/patent-oa/tools/ingest_playbook.py ingest --from-skill-dir DIR --source-path BOOK --slug slug
  python skills/patent-oa/tools/ingest_playbook.py list
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

from book_to_skill_setup import ensure_book_to_skill
from config import load_config
from playbook import ingest_distilled_skill, list_playbook_records, peek_source, reject_if_url
from vault_layout import refresh_oa_vault, resolve_oa_root


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _ctx(args: argparse.Namespace) -> tuple[dict, str | None, Path]:
    cfg = load_config(args.config or None)
    vault = (args.vault or "").strip() or None
    if not vault:
        try:
            sys.path.insert(0, str(ROOT.parent / "patent-reader" / "tools"))
            from shared.common import resolve_obsidian_vault

            resolved = resolve_obsidian_vault()
            if resolved.get("vault") and not resolved.get("needs_user_input"):
                vault = str(resolved["vault"])
        except Exception:
            vault = None
    return cfg, vault, resolve_oa_root(cfg, vault)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="")
    p.add_argument("--vault", default="")
    sub = p.add_subparsers(dest="cmd", required=True)

    peek = sub.add_parser("peek", help="预读前若干页，供判断是否值得蒸馏")
    peek.add_argument("--path", required=True)
    peek.add_argument("--max-pages", type=int, default=8)
    peek.add_argument("--max-chars", type=int, default=12000)
    peek.add_argument("--no-text", action="store_true", help="JSON 中省略 text")

    ens = sub.add_parser("ensure-skill", help="探测或自动安装 book-to-skill")
    ens.add_argument("--no-install", action="store_true")

    ing = sub.add_parser("ingest", help="把蒸馏输出转写到 oa/playbooks（不进案例向量）")
    ing.add_argument("--from-skill-dir", required=True)
    ing.add_argument("--source-path", required=True)
    ing.add_argument("--slug", default="")
    ing.add_argument("--title", default="")
    ing.add_argument("--force", action="store_true")
    ing.add_argument("--peek-decision", default="accept", choices=("accept", "force", "reject"))

    sub.add_parser("list", help="列出已入库手册")

    args = p.parse_args(argv)
    try:
        if args.cmd == "peek":
            reject_if_url(args.path)
            result = peek_source(
                Path(args.path),
                max_pages=int(args.max_pages),
                max_chars=int(args.max_chars),
            )
            if args.no_text:
                result = {k: v for k, v in result.items() if k != "text"}
            _print(result)
            print("PLAYBOOK: peek", file=sys.stderr)
            return 0
        if args.cmd == "ensure-skill":
            result = ensure_book_to_skill(install=not args.no_install)
            _print(result)
            print(
                f"PLAYBOOK: ensure-skill ok={result.get('ok')} method={result.get('method')}",
                file=sys.stderr,
            )
            return 0 if result.get("ok") else 2
        if args.cmd == "list":
            _cfg, _vault, oa_root = _ctx(args)
            items = list_playbook_records(oa_root)
            _print({"ok": True, "oa_root": str(oa_root), "playbooks": items, "count": len(items)})
            return 0
        if args.cmd == "ingest":
            reject_if_url(args.source_path)
            cfg, vault, oa_root = _ctx(args)
            ing_result = ingest_distilled_skill(
                skill_dir=Path(args.from_skill_dir),
                oa_root=oa_root,
                source_path=Path(args.source_path),
                slug=args.slug,
                title=args.title,
                force=bool(args.force),
                peek_decision=str(args.peek_decision),
            )
            refresh = refresh_oa_vault(cfg=cfg, vault=vault)
            ing_result["refresh"] = {
                "index": refresh.get("index"),
                "oa_root": refresh.get("oa_root"),
                "playbook_count": (refresh.get("counts") or {}).get("playbooks"),
            }
            _print(ing_result)
            print(f"PLAYBOOK: ingested={ing_result.get('slug')}", file=sys.stderr)
            return 0
    except ValueError as exc:
        _print({"ok": False, "error": str(exc)})
        print(f"PLAYBOOK: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        _print({"ok": False, "error": str(exc)})
        print(f"PLAYBOOK: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
