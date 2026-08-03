#!/usr/bin/env python3
"""
阅读模式对话开始前：探测 Obsidian 是否安装、默认/已登记库路径。

不强制依赖 Obsidian——无库时仍可写入 outputs/patent_reader/。
有库时自动解析 PATENT_READER_OBSIDIAN_VAULT，发挥索引/Canvas/术语网最大效果。

用法：
  python tools/patent_reader/check_obsidian_env.py
  python tools/patent_reader/check_obsidian_env.py --json
  python tools/patent_reader/check_obsidian_env.py --set "C:\\Users\\you\\Documents\\Obsidian Vault"
  python tools/patent_reader/check_obsidian_env.py --set "D:\\Vault" --setx   # 顺便写用户级环境变量（Windows）
  python tools/patent_reader/check_obsidian_env.py --auto-accept             # 唯一/当前打开库则写入持久化
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from common import (
        probe_obsidian_environment,
        resolve_obsidian_vault,
        write_persisted_vault,
    )
except ImportError:
    from tools.patent_reader.common import (
        probe_obsidian_environment,
        resolve_obsidian_vault,
        write_persisted_vault,
    )


def _print_human(report: dict) -> None:
    print(f"STATUS: {report['status']}")
    print(f"OBSIDIAN_REQUIRED: false  # 可不装；装了效果更好")
    print(f"OBSIDIAN_INSTALLED: {report['obsidian_installed']}")
    resolved = report.get("resolved") or {}
    vault = resolved.get("vault") or ""
    if vault:
        print(f"VAULT: {vault}")
        print(f"VAULT_SOURCE: {resolved.get('source')}")
        print(f"NEEDS_USER_INPUT: false")
    else:
        print("VAULT: (未配置)")
        print("NEEDS_USER_INPUT: true")
        msg = resolved.get("message") or report.get("status")
        print(f"MESSAGE: {msg}")
        cands = resolved.get("candidates") or report.get("vaults") or []
        if cands:
            print("CANDIDATES:")
            for c in cands[:8]:
                print(f"  - {c.get('path')}  (open={c.get('open')}, source={c.get('source')})")
        defaults = resolved.get("suggested_defaults") or []
        if defaults:
            print("SUGGESTED_DEFAULTS:")
            for d in defaults:
                print(f"  - {d}")
        print("ACTION: 请用户提供 Obsidian 库根目录，然后执行：")
        print('  python tools/patent_reader/check_obsidian_env.py --set "库路径"')
        if sys.platform == "win32":
            print("  # 当前 PowerShell 会话：")
            print('  $env:PATENT_READER_OBSIDIAN_VAULT = "库路径"')
        else:
            print('  export PATENT_READER_OBSIDIAN_VAULT="库路径"')
    print(f"PERSISTED_CONFIG: {report.get('persisted_config')}")
    print(f"ENV_VAR: {report.get('env_var')}")


def _set_user_env_windows(name: str, value: str) -> bool:
    try:
        r = subprocess.run(
            ["setx", name, value],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="输出 JSON 报告")
    ap.add_argument(
        "--set",
        default="",
        help="将库路径写入持久化配置，并设置当前进程环境变量",
    )
    ap.add_argument(
        "--setx",
        action="store_true",
        help="Windows 下额外 setx 到用户环境变量（新开终端生效）",
    )
    ap.add_argument(
        "--auto-accept",
        action="store_true",
        help="若已唯一解析到库路径，写入持久化配置",
    )
    ap.add_argument(
        "--require-vault",
        action="store_true",
        help="无库路径时退出码 2（默认仅提示，退出 0；强制入库场景可用）",
    )
    args = ap.parse_args(argv)

    if args.set.strip():
        vault_path = Path(args.set.strip()).expanduser()
        if not vault_path.exists():
            print(f"警告：路径尚不存在，将创建：{vault_path}", file=sys.stderr)
            vault_path.mkdir(parents=True, exist_ok=True)
        cfg = write_persisted_vault(vault_path)
        os.environ["PATENT_READER_OBSIDIAN_VAULT"] = str(vault_path.resolve())
        print(f"OK set vault={vault_path.resolve()}")
        print(f"PERSISTED: {cfg}")
        print(f"ENV_SET: PATENT_READER_OBSIDIAN_VAULT={vault_path.resolve()}")
        if args.setx and sys.platform == "win32":
            ok = _set_user_env_windows(
                "PATENT_READER_OBSIDIAN_VAULT", str(vault_path.resolve())
            )
            print(f"SETX: {'ok' if ok else 'failed'}")
            if ok:
                print("注意：setx 仅对新开终端生效；当前会话已用 ENV_SET。")
        elif args.setx:
            print("SETX: skipped (非 Windows)", file=sys.stderr)
        report = probe_obsidian_environment()
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.auto_accept:
        resolved = resolve_obsidian_vault()
        if resolved.get("vault") and not resolved.get("needs_user_input"):
            cfg = write_persisted_vault(resolved["vault"])
            os.environ["PATENT_READER_OBSIDIAN_VAULT"] = resolved["vault"]
            print(f"OK auto-accept vault={resolved['vault']}")
            print(f"PERSISTED: {cfg}")
        else:
            print("AUTO_ACCEPT: skipped (无唯一可解析库路径)", file=sys.stderr)
            report = probe_obsidian_environment()
            if args.json:
                print(json.dumps(report, ensure_ascii=False, indent=2))
            else:
                _print_human(report)
            return 2 if args.require_vault else 0

    report = probe_obsidian_environment()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)

    if args.require_vault and (
        report["status"] != "ready" or not (report.get("resolved") or {}).get("vault")
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
