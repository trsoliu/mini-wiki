"""Write skills/patent-map/data/ipc_subclasses_{version}.csv."""
from __future__ import annotations

import csv
from pathlib import Path

from .config import IPC_VERSION
from .parse import finalize_zh


def write_csv(
    path: Path,
    en: dict[str, str],
    zh: dict[str, str],
    source: str,
) -> None:
    missing = [c for c in en if c not in zh]
    if missing:
        raise SystemExit(f"missing {len(missing)} Chinese titles, e.g. {missing[:12]}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(f"# ipc_version: {IPC_VERSION}\n")
        fh.write(f"# source: {source}\n")
        writer = csv.writer(fh)
        writer.writerow(["code", "zh", "en"])
        for code, en_title in en.items():
            writer.writerow([code, finalize_zh(code, zh[code]), en_title])
