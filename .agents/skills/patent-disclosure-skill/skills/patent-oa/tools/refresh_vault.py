#!/usr/bin/env python
"""刷新 Obsidian oa：目录分层 + 索引 + Bases + 关联 Canvas。

用法：
  python skills/patent-oa/tools/refresh_vault.py
  python skills/patent-oa/tools/refresh_vault.py --vault "D:/Obsidian/MyVault"
  python skills/patent-oa/tools/refresh_vault.py --inventory

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

from config import load_config
from vault_layout import (
    DEFAULT_NUDGE_MIN_HISTORY,
    DEFAULT_NUDGE_MIN_PLAYBOOKS,
    oa_inventory,
    refresh_oa_vault,
)


def _resolve_vault_and_papers(explicit_vault: str, papers_dir: str) -> tuple[str | None, str]:
    vault = explicit_vault.strip() or None
    papers = papers_dir.strip() or "Research/Patents"
    if vault:
        return vault, papers
    try:
        sys.path.insert(0, str(ROOT.parent / "patent-reader" / "tools"))
        from shared.common import resolve_obsidian_vault, runtime_config

        resolved = resolve_obsidian_vault()
        if resolved.get("vault") and not resolved.get("needs_user_input"):
            vault = str(resolved["vault"])
        papers = papers_dir.strip() or runtime_config().get("papers_dir") or papers
    except Exception:
        pass
    return vault, papers


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="")
    p.add_argument("--vault", default="", help="Obsidian 库根；默认探测已保存库")
    p.add_argument("--papers-dir", default="", help="默认 Research/Patents")
    p.add_argument(
        "--inventory",
        action="store_true",
        help="只读统计历史案/手册数量（不写索引）",
    )
    p.add_argument(
        "--min-history",
        type=int,
        default=DEFAULT_NUDGE_MIN_HISTORY,
        help="历史案低于此数则 nudge（默认 3）",
    )
    p.add_argument(
        "--min-playbooks",
        type=int,
        default=DEFAULT_NUDGE_MIN_PLAYBOOKS,
        help="经验手册低于此数则 nudge（默认 3）",
    )
    args = p.parse_args(argv)

    cfg = load_config(args.config or None)
    vault, papers = _resolve_vault_and_papers(args.vault, args.papers_dir)
    if args.inventory:
        result = oa_inventory(
            cfg=cfg,
            vault=vault,
            min_history=args.min_history,
            min_playbooks=args.min_playbooks,
        )
    else:
        result = refresh_oa_vault(cfg=cfg, vault=vault, papers_dir=papers)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
