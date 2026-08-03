#!/usr/bin/env python3
"""
生成专利解读 JSON Canvas（公开号中心，连相关笔记与术语）。

用法：
  python tools/patent_reader/build_patent_canvas.py \\
      --vault /path/to/vault \\
      --note-rel Research/Patents/领域/CNxxx/CNxxx_解读_20260721.md \\
      --manifest source_manifest.json \\
      [--bundle synthesis_bundle.json] [--claim-tree claim_tree.json] \\
      [--workdir tmp/patent_reader/RUN] \\
      -o Research/Patents/领域/CNxxx/CNxxx_图谱.canvas
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from common import optional_path, resolve_domain, runtime_config
    from obsidian import build_canvas, harvest_claim_summaries_from_note, scan_vault_related
    from write_patent_obsidian_note import (
        harvest_glossary_from_note,
        harvest_narrative_from_note,
        merge_glossary_candidates,
    )
except ImportError:
    from tools.patent_reader.common import optional_path, resolve_domain, runtime_config
    from tools.patent_reader.obsidian import (
        build_canvas,
        harvest_claim_summaries_from_note,
        scan_vault_related,
    )
    from tools.patent_reader.write_patent_obsidian_note import (
        harvest_glossary_from_note,
        harvest_narrative_from_note,
        merge_glossary_candidates,
    )


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vault", default="", help="Obsidian 库根；默认 PATENT_READER_OBSIDIAN_VAULT")
    ap.add_argument("--note-rel", required=True, help="相对库根的笔记路径")
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--bundle", default=None, type=optional_path)
    ap.add_argument("--claim-tree", default=None, type=optional_path)
    ap.add_argument("--context-anchor", default=None, type=optional_path)
    ap.add_argument("--workdir", default=None, type=optional_path)
    ap.add_argument("-o", "--output", required=True, type=Path)
    ap.add_argument("--title", default="")
    args = ap.parse_args(argv)

    cfg = runtime_config()
    vault_s = args.vault.strip() or cfg["obsidian_vault"]
    if not vault_s:
        print("错误：未指定 --vault 且未设置 PATENT_READER_OBSIDIAN_VAULT", file=sys.stderr)
        return 1
    vault = Path(vault_s).resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    pub = manifest.get("pub_number") or "patent"
    assignees = manifest.get("assignees") or []

    note_path = vault / args.note_rel.replace("\\", "/")
    note_text = note_path.read_text(encoding="utf-8") if note_path.is_file() else ""
    title = args.title.strip()
    if not title and note_text:
        hm = re.search(r"^#\s+(.+)$", note_text, re.M)
        if hm:
            title = hm.group(1).strip()
    if not title:
        title = f"专利解读 {pub}"

    glossary: list = []
    if args.bundle and args.bundle.is_file():
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        glossary = bundle.get("glossary_candidates") or []
    if note_text:
        glossary = merge_glossary_candidates(glossary, harvest_glossary_from_note(note_text))

    anchor: dict = {}
    if args.context_anchor and args.context_anchor.is_file():
        anchor = json.loads(args.context_anchor.read_text(encoding="utf-8"))
    elif args.workdir:
        ca = args.workdir / "context_anchor.json"
        if ca.is_file():
            anchor = json.loads(ca.read_text(encoding="utf-8"))

    domain = ""
    dm = re.search(r"^domain:\s*(.+)$", note_text, re.M) if note_text else None
    if dm:
        domain = dm.group(1).strip().strip("\"'")
    if not domain:
        ipc0 = ""
        codes = anchor.get("ipc_codes") or manifest.get("ipc_codes") or []
        if codes:
            ipc0 = str(codes[0])
        domain = resolve_domain(note_text[:2000] if note_text else title, ipc0)

    related = scan_vault_related(
        vault, cfg["papers_dir"], pub, assignees, domain=domain
    )

    claim_tree = None
    ct = args.claim_tree
    if (not ct or not ct.is_file()) and args.workdir:
        ct = args.workdir / "claim_tree.json"
    if ct and ct.is_file():
        claim_tree = json.loads(ct.read_text(encoding="utf-8"))

    figure_rels: list[str] = []
    images = note_path.parent / "images"
    if images.is_dir():
        note_dir_rel = str(note_path.parent.relative_to(vault)).replace("\\", "/")
        for img in sorted(images.glob("*.png"))[:4]:
            figure_rels.append(f"{note_dir_rel}/images/{img.name}")

    narrative = harvest_narrative_from_note(note_text) if note_text else {}
    claim_summaries = (
        harvest_claim_summaries_from_note(note_text) if note_text else {}
    )

    canvas = build_canvas(
        vault=vault,
        papers_dir=cfg["papers_dir"],
        note_rel_path=args.note_rel.replace("\\", "/"),
        pub=pub,
        title=title,
        related=related,
        glossary_terms=glossary,
        glossary_dir=cfg["glossary_dir"],
        create_glossary_stubs=True,
        meta={
            "domain": domain,
            "ipc": anchor.get("ipc_codes") or manifest.get("ipc_codes") or "",
            "assignees": assignees or anchor.get("assignees") or [],
            "evidence_scope": manifest.get("evidence_scope") or "",
        },
        claim_tree=claim_tree,
        claim_summaries=claim_summaries,
        figure_rels=figure_rels,
        narrative=narrative,
    )
    canvas.pop("glossary_resolved", None)

    out = args.output
    if not out.is_absolute():
        out = vault / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(canvas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK nodes={len(canvas['nodes'])} edges={len(canvas['edges'])}")
    print(f"CANVAS: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
