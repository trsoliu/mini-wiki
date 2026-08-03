# -*- coding: utf-8 -*-
"""extract_patent_text.py 冒烟测试。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "patent_reader_sample.txt"


def main() -> int:
    out = ROOT / "tmp" / "test_patent_reader"
    if out.exists():
        import shutil

        shutil.rmtree(out)
    cmd = [
        sys.executable,
        str(ROOT / "tools" / "patent_reader" / "extract_patent_text.py"),
        "-i",
        str(SAMPLE),
        "-o",
        str(out),
        "--pub-number",
        "CN999999999B",
    ]
    r = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return r.returncode
    tree = json.loads((out / "claim_tree.json").read_text(encoding="utf-8"))
    assert len(tree.get("roots", [])) >= 1
    manifest = json.loads((out / "source_manifest.json").read_text(encoding="utf-8"))
    assert manifest.get("claim_count", 0) >= 2
    print("OK extract_patent_text smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
