#!/usr/bin/env python
"""加载 / 合并发明交底公式起草菜单（仅 origin: agent 选题）。

用法：
  python tools/formula_paradigms.py list
  python tools/formula_paradigms.py list --case-dir outputs/foo
  python tools/formula_paradigms.py show weighted_sum
  python tools/formula_paradigms.py combos
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stdio_utf8 import ensure_utf8_stdio

DEFAULT_PATH = Path(__file__).resolve().parents[1] / "references" / "formulas" / "paradigms.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("需要 PyYAML：pip install pyyaml") from exc
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"配置根须为 mapping: {path}")
    return data


def _merge_paradigm_lists(base: list[dict], overlay: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    order: list[str] = []
    for item in base + overlay:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            continue
        if pid not in by_id:
            order.append(pid)
        by_id[pid] = {**by_id.get(pid, {}), **item}
    return [by_id[i] for i in order]


def _merge_combos(base: list[dict], overlay: list[dict]) -> list[dict]:
    return _merge_paradigm_lists(base, overlay)


def resolve_paradigm_paths(case_dir: str | Path | None = None) -> list[Path]:
    paths: list[Path] = [DEFAULT_PATH]
    env = (os.environ.get("PATENT_FORMULA_PARADIGMS") or "").strip()
    if env:
        paths.append(Path(env).expanduser())
    if case_dir:
        cd = Path(case_dir).expanduser()
        for name in ("formula_paradigms.yaml", "formula_paradigms.json"):
            p = cd / name
            if p.is_file():
                paths.append(p)
                break
    return paths


def load_paradigms(case_dir: str | Path | None = None) -> dict[str, Any]:
    """合并后的完整配置：rules + paradigms + combos + _sources。"""
    rules: dict[str, Any] = {}
    paradigms: list[dict] = []
    combos: list[dict] = []
    sources: list[str] = []
    version = 1
    for path in resolve_paradigm_paths(case_dir):
        if not path.is_file():
            continue
        data = _load_yaml(path)
        sources.append(str(path.resolve()))
        version = int(data.get("version") or version)
        if isinstance(data.get("rules"), dict):
            rules = {**rules, **data["rules"]}
        paradigms = _merge_paradigm_lists(
            paradigms, list(data.get("paradigms") or [])
        )
        combos = _merge_combos(combos, list(data.get("combos") or []))
    if not paradigms:
        raise SystemExit(f"未加载到任何范式；请检查 {DEFAULT_PATH}")
    return {
        "version": version,
        "rules": rules,
        "paradigms": paradigms,
        "combos": combos,
        "_sources": sources,
    }


def paradigm_by_id(cfg: dict[str, Any], pid: str) -> dict[str, Any] | None:
    for p in cfg.get("paradigms") or []:
        if str(p.get("id")) == pid:
            return p
    return None


def combo_by_id(cfg: dict[str, Any], cid: str) -> dict[str, Any] | None:
    for c in cfg.get("combos") or []:
        if str(c.get("id")) == cid:
            return c
    return None


def latex_for(p: dict[str, Any]) -> str:
    return str(p.get("render_latex") or p.get("latex") or "").strip()


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["list", "show", "combos", "paths"])
    ap.add_argument("id", nargs="?", default="", help="show 时的 paradigm id")
    ap.add_argument("--case-dir", default="", help="案件目录（可读覆盖配置）")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    case = args.case_dir.strip() or None
    if args.cmd == "paths":
        out = [str(p) for p in resolve_paradigm_paths(case)]
        print(json.dumps(out, ensure_ascii=False, indent=2) if args.json else "\n".join(out))
        return 0

    cfg = load_paradigms(case)
    if args.cmd == "list":
        rows = [
            {
                "id": p.get("id"),
                "name_zh": p.get("name_zh"),
                "when_zh": p.get("when_zh"),
                "tags": p.get("tags") or [],
            }
            for p in cfg["paradigms"]
        ]
        if args.json:
            print(json.dumps({"sources": cfg["_sources"], "paradigms": rows}, ensure_ascii=False, indent=2))
        else:
            print(f"sources: {len(cfg['_sources'])}  paradigms: {len(rows)}")
            for r in rows:
                print(f"- {r['id']}: {r['name_zh']} — {r['when_zh']}")
        return 0

    if args.cmd == "combos":
        if args.json:
            print(json.dumps(cfg.get("combos") or [], ensure_ascii=False, indent=2))
        else:
            for c in cfg.get("combos") or []:
                print(
                    f"- {c.get('id')}: {c.get('name_zh')} "
                    f"← {', '.join(c.get('paradigm_ids') or [])}"
                )
        return 0

    # show
    pid = args.id.strip()
    if not pid:
        raise SystemExit("show 需要 paradigm id")
    p = paradigm_by_id(cfg, pid)
    if not p:
        raise SystemExit(f"未知范式 id: {pid}")
    payload = {**p, "latex_effective": latex_for(p), "rules": cfg.get("rules")}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
