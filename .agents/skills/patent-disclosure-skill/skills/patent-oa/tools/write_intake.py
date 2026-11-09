#!/usr/bin/env python
"""对话收齐后写入会话目录的 intake.json；不完整则拒绝落盘。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCENES = ("invalidity", "fto", "infringement", "sep", "patentability", "oa")
SCENE_KIND = {
    "patentability": "patent",
    "invalidity": "patent",
    "oa": "patent",
    "fto": "product",
    "infringement": "product",
    "sep": "standard",
}


def intake_path(case_dir: Path) -> Path:
    return case_dir / "intake.json"


def make_session_id() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def make_session_dir(case_dir: Path) -> Path:
    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    base = make_session_id()
    dest = case_dir / base
    n = 2
    while dest.exists():
        dest = case_dir / f"{base}-{n}"
        n += 1
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _as_paths(*groups: object) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        if isinstance(group, (list, tuple)):
            items = list(group)
        elif group:
            items = [group]
        else:
            items = []
        for item in items:
            text = str(item or "").strip()
            if text and text not in seen:
                seen.add(text)
                out.append(text)
    return out


def _as_url(raw: object) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    if re.match(r"^https?://", text, re.I):
        return text
    if text.startswith("www."):
        return "https://" + text
    return text


def load_intake(case_dir: Path) -> dict | None:
    path = intake_path(case_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def normalize_intake(raw: dict, *, case_dir: Path) -> dict:
    scene = str(raw.get("scene") or "").strip().lower()
    if scene not in SCENES:
        scene = ""
    left = raw.get("left") if isinstance(raw.get("left"), dict) else {}
    left_paths = _as_paths(left.get("paths"), left.get("path"))
    pub = str(left.get("pub_number") or "").strip()
    source = str(left.get("source") or "").strip().lower()
    if source not in ("pub", "local"):
        source = "local" if left_paths and not pub else "pub"
    if source == "pub":
        left_paths = []
    default_kind = SCENE_KIND.get(scene, "patent")
    right = []
    for item in raw.get("right") or []:
        if not isinstance(item, dict):
            continue
        paths = _as_paths(item.get("paths"), item.get("path"))
        right.append(
            {
                "kind": str(item.get("kind") or default_kind).strip() or default_kind,
                "pub_number": str(item.get("pub_number") or item.get("name") or "").strip(),
                "url": _as_url(item.get("url") or item.get("source_url")),
                "path": paths[0] if paths else "",
                "paths": paths,
                "text": str(item.get("text") or "").strip(),
            }
        )
    case_id = str(raw.get("case_id") or left.get("pub_number") or case_dir.parent.name).strip()
    if not case_id or case_id in {".", case_dir.name}:
        case_id = str(left.get("pub_number") or case_dir.parent.name or case_dir.name).strip() or "chart"
    session_id = str(raw.get("session_id") or case_dir.name).strip() or case_dir.name
    return {
        "submitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "case_id": case_id,
        "session_id": session_id,
        "scene": scene,
        "left": {
            "source": source,
            "pub_number": pub if source == "pub" else "",
            "claims_text": str(left.get("claims_text") or "").strip(),
            "features_path": str(left.get("features_path") or "").strip(),
            "path": left_paths[0] if left_paths else "",
            "paths": left_paths,
        },
        "right": right,
        "allow_search": True if "allow_search" not in raw else bool(raw.get("allow_search")),
        "search_fill": bool(raw.get("search_fill")),
        "include_dependent": True if "include_dependent" not in raw else bool(raw.get("include_dependent")),
        "notes": str(raw.get("notes") or "").strip(),
    }


def missing_fields(data: dict | None) -> list[str]:
    if not data:
        return ["intake"]
    miss: list[str] = []
    scene = str(data.get("scene") or "").strip()
    if scene not in SCENES:
        miss.append("scene")
    left = data.get("left") if isinstance(data.get("left"), dict) else {}
    left_ok = bool(
        left.get("pub_number")
        or left.get("paths")
        or left.get("path")
        or left.get("features_path")
        or left.get("claims_text")
    )
    if not left_ok:
        miss.append("left")
    rights = [item for item in (data.get("right") or []) if isinstance(item, dict)]
    search_fill = bool(data.get("search_fill"))
    if not rights:
        if scene in ("patentability", "invalidity", "oa") and search_fill:
            return miss
        miss.append("right")
        return miss
    for index, item in enumerate(rights, start=1):
        kind = str(item.get("kind") or SCENE_KIND.get(scene, "patent")).strip()
        key = str(item.get("pub_number") or "").strip()
        has_file = bool(item.get("paths") or item.get("path"))
        has_url = bool(item.get("url"))
        has_text = bool(item.get("text"))
        if kind == "product":
            if not key:
                miss.append(f"right[{index}].name")
            if not (has_url or has_file or has_text):
                miss.append(f"right[{index}].evidence")
        elif not (key or has_file or has_text):
            miss.append(f"right[{index}]")
    return miss


def write_intake(raw: dict, *, session_dir: Path) -> tuple[dict, list[str]]:
    session_dir.mkdir(parents=True, exist_ok=True)
    data = normalize_intake(raw, case_dir=session_dir)
    missing = missing_fields(data)
    if missing:
        return data, missing
    dest = intake_path(session_dir)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(dest)
    return data, []


def _load_json(path: str) -> dict:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(text or "{}")
    if not isinstance(data, dict):
        raise ValueError("须为对象")
    return data


def _print_status(session_dir: Path, data: dict | None, missing: list[str]) -> None:
    print(f"INTAKE_OK:{0 if missing else 1}")
    print(f"INTAKE_SESSION:{(data or {}).get('session_id') or session_dir.name}")
    print(f"INTAKE_DIR:{session_dir}")
    print(f"INTAKE_JSON:{intake_path(session_dir)}")
    if missing:
        print("INTAKE_MISSING:" + ",".join(missing))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", help="案件根目录 outputs/patent-chart/{案件}")
    ap.add_argument("--into", help="已有会话目录，写入或检查这一层")
    ap.add_argument("--json", help="intake 对象；- 表示 stdin")
    ap.add_argument("--alloc", action="store_true", help="只建会话目录")
    ap.add_argument("--check", action="store_true", help="只检查是否收齐")
    args = ap.parse_args(argv)
    case_dir = Path(args.dir).resolve() if args.dir else None
    into = Path(args.into).resolve() if args.into else None
    if args.alloc:
        if not case_dir:
            print("ERROR: --alloc 需要 --dir", file=sys.stderr)
            return 2
        session_dir = make_session_dir(case_dir)
        print(f"INTAKE_SESSION:{session_dir.name}")
        print(f"INTAKE_DIR:{session_dir}")
        print(f"INTAKE_JSON:{intake_path(session_dir)}")
        return 0
    session_dir = into or case_dir
    if args.check:
        if not session_dir:
            print("ERROR: --check 需要 --into 或 --dir", file=sys.stderr)
            return 2
        loaded = load_intake(session_dir)
        data = normalize_intake(loaded, case_dir=session_dir) if loaded else None
        missing = missing_fields(data)
        _print_status(session_dir, data, missing)
        return 0 if not missing else 1
    if not args.json:
        print("ERROR: 写入需要 --json", file=sys.stderr)
        return 2
    if not session_dir:
        print("ERROR: 写入需要 --dir 或 --into", file=sys.stderr)
        return 2
    try:
        raw = _load_json(args.json)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    preview_dir = into or case_dir
    preview = normalize_intake(raw, case_dir=preview_dir)
    missing = missing_fields(preview)
    if missing:
        _print_status(preview_dir, preview, missing)
        return 2
    session_dir = into or make_session_dir(case_dir)
    data, missing = write_intake(raw, session_dir=session_dir)
    _print_status(session_dir, data, missing)
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
