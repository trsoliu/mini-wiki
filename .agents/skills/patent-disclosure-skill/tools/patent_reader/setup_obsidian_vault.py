#!/usr/bin/env python3
"""
一次性初始化 Obsidian 库：CSS 片段、patents.base、索引页。

用法：
  python tools/patent_reader/setup_obsidian_vault.py
  python tools/patent_reader/setup_obsidian_vault.py --vault D:/Obsidian/MyVault
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from common import resolve_obsidian_vault, runtime_config
    from obsidian import bootstrap_vault
except ImportError:
    from tools.patent_reader.common import resolve_obsidian_vault, runtime_config
    from tools.patent_reader.obsidian import bootstrap_vault


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default="", help="库根路径")
    ap.add_argument("--papers-dir", default="", help="默认 Research/Patents")
    ap.add_argument("--output", default="", help="状态 JSON")
    args = ap.parse_args(argv)

    cfg = runtime_config()
    vault_s = args.vault.strip() or cfg["obsidian_vault"]
    if not vault_s:
        # 再试一次探测（runtime 已含探测；此处给出明确指引）
        resolved = resolve_obsidian_vault()
        if resolved.get("vault"):
            vault_s = resolved["vault"]
        else:
            print(
                "错误：未配置 Obsidian 库。可先运行：\n"
                "  python tools/patent_reader/check_obsidian_env.py\n"
                "然后：\n"
                '  python tools/patent_reader/check_obsidian_env.py --set "你的库路径"\n'
                "或不入库，仅用 write 写入 outputs/patent_reader/。",
                file=sys.stderr,
            )
            return 1

    vault = Path(vault_s).resolve()
    papers = args.papers_dir.strip() or cfg["papers_dir"]
    actions = bootstrap_vault(vault, papers)

    status = {
        "vault": str(vault),
        "papers_dir": papers,
        "actions": actions,
        "vault_source": cfg.get("vault_source", ""),
    }
    print(f"OK bootstrap actions={len(actions)}")
    for a in actions:
        print(f"  {a}")
    if args.output:
        Path(args.output).write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
