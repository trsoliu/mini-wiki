"""Rebuild the offline IPC subclass CSV used by the patent map."""
from __future__ import annotations

import argparse
from pathlib import Path

from .config import DEFAULT_CACHE, DEFAULT_CSV, IPC_VERSION
from .download import download_cnipa_pdfs, download_wipo_scheme_xml, probe_ipcpub_zh
from .emit import write_csv
from .parse import parse_cnipa_pdfs, parse_en_xml, parse_ipcpub_json


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE, help="download cache (gitignored)")
    ap.add_argument("--out", type=Path, default=None, help="compiled CSV (default: map data/ipc_subclasses_{version}.csv)")
    ap.add_argument("--skip-zh", action="store_true", help="only parse WIPO EN XML; do not overwrite the map CSV")
    args = ap.parse_args(argv)
    out = args.out or (args.cache / "subclasses_en_only.csv" if args.skip_zh else DEFAULT_CSV)

    xml = download_wipo_scheme_xml(args.cache)
    en = parse_en_xml(xml)
    print("en subclasses", len(en), "from", xml.name)
    if not en:
        raise SystemExit("WIPO EN XML produced no subclass rows")

    zh: dict[str, str] = {}
    source = f"WIPO IPC scheme EN XML {IPC_VERSION}"
    ipcpub_zh = None if args.skip_zh else probe_ipcpub_zh(args.cache)
    if ipcpub_zh:
        zh = parse_ipcpub_json(ipcpub_zh)
        print("ipcpub zh subclasses", len(zh))
        source += " + IPCPUB zh JSON"

    if args.skip_zh:
        write_csv(out, en, {code: "" for code in en}, source + " (zh skipped)")
        print("wrote", out, "(Chinese empty)")
        return 0

    if len(zh) < len(en):
        pdfs = download_cnipa_pdfs(args.cache)
        cnipa = parse_cnipa_pdfs(pdfs)
        zh = {**zh, **cnipa}
        source += " + CNIPA Chinese classification PDFs"

    write_csv(out, en, zh, source)
    print("wrote", out, "rows", len(en))
    for code in ("H01M", "G06F", "H02K"):
        print(code, zh.get(code, ""), "|", (en.get(code) or "")[:60])
    return 0
