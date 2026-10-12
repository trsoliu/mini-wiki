"""Load offline IPC subclass short titles. Browser never fetches WIPO/CNIPA.

Rebuild the CSV with: python skills/patent-map/tools/ipc_scheme/build.py
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_ipc_csv() -> Path:
    """Prefer versioned tables such as ipc_subclasses_2026.01.csv."""
    data = ROOT / "data"
    hits = list(data.glob("ipc_subclasses_*.csv"))
    if not hits:
        return data / "ipc_subclasses.csv"

    def ver_key(path: Path) -> tuple[int, ...]:
        suffix = path.stem[len("ipc_subclasses_") :]
        try:
            return tuple(int(part) for part in suffix.split("."))
        except ValueError:
            return (0,)

    return max(hits, key=ver_key)


DEFAULT_CSV = resolve_ipc_csv()


def _version_from_comment(line: str) -> str:
    text = line.lstrip("#").strip()
    if text.lower().startswith("ipc_version:"):
        return text.split(":", 1)[1].strip()
    return ""


@lru_cache(maxsize=4)
def _load_ipc_subclasses(csv_path: str) -> dict:
    path = Path(csv_path)
    version = ""
    titles: dict[str, str] = {}
    if not path.is_file():
        return {"version": version, "titles": titles, "count": 0}
    with path.open(encoding="utf-8", newline="") as fh:
        data_lines: list[str] = []
        for raw in fh:
            stripped = raw.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                version = version or _version_from_comment(stripped)
                continue
            data_lines.append(raw)
    for row in csv.DictReader(data_lines):
        code = (row.get("code") or "").strip().upper()
        zh = (row.get("zh") or "").strip()
        if code and zh:
            titles[code] = zh
    return {"version": version, "titles": titles, "count": len(titles)}


def load_ipc_subclasses(path: str | Path | None = None) -> dict:
    csv_path = Path(path) if path else resolve_ipc_csv()
    return _load_ipc_subclasses(str(csv_path))
