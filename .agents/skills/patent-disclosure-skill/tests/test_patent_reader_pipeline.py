# -*- coding: utf-8 -*-
"""专利解读工具链冒烟测试（含 Obsidian L0–L2）。"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "tests" / "fixtures" / "patent_reader_sample.txt"


def run(cmd: list[str], env: dict | None = None) -> subprocess.CompletedProcess[str]:
    import os

    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=merged,
    )


def build_sample_note() -> str:
    t = (ROOT / "assets" / "patent_note_template.md").read_text(encoding="utf-8")
    t = (
        t.replace("{{发明名称或公开号}}", "示例隔膜")
        .replace("{{CN…}}", "CN999999999B")
        .replace("{{domain}}", "化工与材料")
        .replace("{{ipc}}", "H01M")
        .replace("{{assignees}}", "示例科技")
        .replace("{{入门|研发|规避}}", "入门")
        .replace("{{全文|仅摘要|部分}}", "全文")
        .replace("{{RUN}}", "test-run")
        .replace("{{公开号目录}}", "CN999999999B")
        .replace("YYYY-MM-DD", "2026-07-21")
        .replace(
            "| | | desc_… / 实施例… |",
            "| 电芯隔膜 | 电池内部 | desc_001 / 实施例1 |",
        )
        .replace(
            "（来自 `context_anchor.ipc_application`。）",
            "电化学储能（离线词表）。",
        )
        .replace(
            "> - **线索**：标题 — 置信度：中 — [来源](URL) — 理由：…\n>\n> 无可靠 URL 时写：",
            "> 未发现可核验的公开对应，可能为防御性/储备专利。\n>\n> 无可靠 URL 时写：",
        )
        .replace(
            "> 【{{公开号}}·权利要求{{N}}】{{原文逐字片段}}",
            "> 【CN999999999B·权利要求1】1.一种锂离子电池隔膜",
        )
    )
    return t


def main() -> int:
    out = ROOT / "tmp" / "test_patent_reader"
    if out.exists():
        import shutil

        shutil.rmtree(out)

    r = run(
        [
            sys.executable,
            str(ROOT / "tools" / "patent_reader" / "extract_patent_text.py"),
            "-i",
            str(SAMPLE),
            "-o",
            str(out),
            "--pub-number",
            "CN999999999B",
        ]
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return r.returncode

    r2 = run(
        [sys.executable, str(ROOT / "tools" / "patent_reader" / "build_context_anchor.py"), "-w", str(out)]
    )
    if r2.returncode != 0:
        print(r2.stderr or r2.stdout)
        return r2.returncode

    mmd = out / "claim_mermaid.mmd"
    r2b = run(
        [
            sys.executable,
            str(ROOT / "tools" / "patent_reader" / "build_claim_mermaid.py"),
            "--claim-tree",
            str(out / "claim_tree.json"),
            "--pub-number",
            "CN999999999B",
            "-o",
            str(mmd),
        ]
    )
    if r2b.returncode != 0:
        print(r2b.stderr or r2b.stdout)
        return r2b.returncode
    assert "subgraph" in mmd.read_text(encoding="utf-8")

    note = ROOT / "tmp" / "test_patent_note.md"
    note.write_text(build_sample_note(), encoding="utf-8")

    plan = {
        "sections": ["all"],
        "grounding": {"section9": "desc_001"},
        "context_anchor_ref": str(out / "context_anchor.json"),
        "public_clues_ref": str(out / "public_clues.json"),
    }
    (out / "note_plan.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    (out / "public_clues.json").write_text("[]", encoding="utf-8")

    lint_json = out / "lint.json"
    r3 = run(
        [
            sys.executable,
            str(ROOT / "tools" / "patent_reader" / "lint_patent_note.py"),
            "--note",
            str(note),
            "--manifest",
            str(out / "source_manifest.json"),
            "--claim-tree",
            str(out / "claim_tree.json"),
            "--plan",
            str(out / "note_plan.json"),
            "--context-anchor",
            str(out / "context_anchor.json"),
            "--output",
            str(lint_json),
        ]
    )
    if r3.returncode != 0:
        print(r3.stderr or r3.stdout)
        return r3.returncode

    with tempfile.TemporaryDirectory() as td:
        vault = Path(td)
        env = {"PATENT_READER_OBSIDIAN_VAULT": str(vault)}

        r_setup = run(
            [sys.executable, str(ROOT / "tools" / "patent_reader" / "setup_obsidian_vault.py")],
            env=env,
        )
        if r_setup.returncode != 0:
            print(r_setup.stderr or r_setup.stdout)
            return r_setup.returncode

        assert (vault / "Research" / "Patents" / "patents.base").is_file()
        assert (vault / ".obsidian" / "snippets" / "patent-reader.css").is_file()
        assert (vault / ".obsidian" / "appearance.json").is_file()
        appearance = json.loads(
            (vault / ".obsidian" / "appearance.json").read_text(encoding="utf-8")
        )
        assert "patent-reader" in appearance.get("enabledCssSnippets", [])
        assert (vault / "Research" / "术语" / "glossary.base").is_file()

        r4 = run(
            [
                sys.executable,
                str(ROOT / "tools" / "patent_reader" / "write_patent_obsidian_note.py"),
                "--content-file",
                str(note),
                "--manifest",
                str(out / "source_manifest.json"),
                "--context-anchor",
                str(out / "context_anchor.json"),
                "--bundle",
                str(out / "synthesis_bundle.json"),
                "--public-clues",
                str(out / "public_clues.json"),
                "--workdir",
                str(out),
                "--lint-json",
                str(lint_json),
                "--output",
                str(out / "write_status.json"),
            ],
            env=env,
        )
        if r4.returncode != 0:
            print(r4.stderr or r4.stdout)
            return r4.returncode

        status = json.loads((out / "write_status.json").read_text(encoding="utf-8"))
        assert status.get("canvas"), "应生成 canvas"
        canvas = Path(status["canvas"])
        assert canvas.is_file()
        canvas_data = json.loads(canvas.read_text(encoding="utf-8"))
        assert len(canvas_data.get("nodes", [])) >= 2

        written = Path(status["written"])
        body = written.read_text(encoding="utf-8")
        assert "patent-reader" in body
        assert "patents/化工与材料" in body
        assert "术语索引" in body
        assert body.count("## Obsidian 导航") == 1

        # 校验 public_clues 脚本
        r_clues = run(
            [
                sys.executable,
                str(ROOT / "tools" / "patent_reader" / "validate_public_clues.py"),
                "-i",
                str(out / "public_clues.json"),
            ]
        )
        if r_clues.returncode != 0:
            print(r_clues.stderr or r_clues.stdout)
            return r_clues.returncode

    # 无 vault：仍应产出 canvas + 本地术语
    r5 = run(
        [
            sys.executable,
            str(ROOT / "tools" / "patent_reader" / "write_patent_obsidian_note.py"),
            "--content-file",
            str(note),
            "--manifest",
            str(out / "source_manifest.json"),
            "--context-anchor",
            str(out / "context_anchor.json"),
            "--bundle",
            str(out / "synthesis_bundle.json"),
            "--public-clues",
            str(out / "public_clues.json"),
            "--lint-json",
            str(lint_json),
            "--output",
            str(out / "write_status_novault.json"),
        ],
        env={"PATENT_READER_OBSIDIAN_VAULT": "", "PATENT_DISCLOSURE_OBSIDIAN_VAULT": ""},
    )
    if r5.returncode != 0:
        print(r5.stderr or r5.stdout)
        return r5.returncode
    st2 = json.loads((out / "write_status_novault.json").read_text(encoding="utf-8"))
    assert st2.get("canvas"), "无 vault 也应生成 canvas"
    assert Path(st2["canvas"]).is_file()

    print("OK patent reader pipeline smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
