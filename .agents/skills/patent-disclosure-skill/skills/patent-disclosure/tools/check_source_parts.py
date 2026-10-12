# -*- coding: utf-8 -*-
"""源材料门禁：parts / 件号必须来自 schema 与 figure_plan；幻觉件进 uncertain。

用法：
  python tools/check_source_parts.py --case-dir outputs/{案件}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stdio_utf8 import ensure_utf8_stdio

NEAR_MARK = re.compile(r"([\u4e00-\u9fffA-Za-z0-9]{1,16})[（(](\d+)[）)]")
DISCLOSURE_TS = re.compile(r".+_\d{14}\.md$", re.I)


@dataclass
class Finding:
    level: str
    code: str
    message: str


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        import yaml

        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 根须为 mapping")
    return data


def _find_schema(case_dir: Path, stem: str) -> Path | None:
    for name in (f"{stem}.yaml", f"{stem}.yml", f"{stem}.json"):
        cand = case_dir / name
        if cand.is_file():
            return cand
    return None


def _uncertain_ids(raw: Any) -> set[str]:
    out: set[str] = set()
    for item in raw or []:
        if isinstance(item, dict):
            pid = str(item.get("id") or "").strip()
            if pid:
                out.add(pid)
            continue
        text = str(item).strip()
        if text.isdigit():
            out.add(text)
    return out


def _uncertain_texts(raw: Any) -> list[str]:
    out: list[str] = []
    for item in raw or []:
        if isinstance(item, dict):
            note = str(item.get("note") or item.get("text") or item.get("name") or "").strip()
            if note:
                out.append(note)
        else:
            text = str(item).strip()
            if text and not text.isdigit():
                out.append(text)
    return out


def _parts_index(schema: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in schema.get("parts") or []:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        if pid:
            out[pid] = str(item.get("name") or "").strip()
    return out


def _find_disclosure_md(case_dir: Path) -> Path | None:
    dated = sorted(
        (p for p in case_dir.glob("*.md") if DISCLOSURE_TS.match(p.name)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for path in dated:
        try:
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:80])
        except OSError:
            continue
        if "# 技术交底书" in head or "**专利类型**" in head:
            return path
    return None


def check_source_parts(
    case_dir: Path,
    *,
    structure: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    disclosure_text: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    parts = _parts_index(structure or {})
    if not parts:
        findings.append(Finding("ERROR", "NO_PARTS", "structure_schema.parts 为空；未见件不要编进 parts。"))
        return findings
    uncertain_ids = _uncertain_ids((structure or {}).get("uncertain"))
    uncertain_notes = _uncertain_texts((structure or {}).get("uncertain"))
    covered: set[str] = set()
    for fig in (plan or {}).get("figures") or []:
        if not isinstance(fig, dict):
            continue
        for raw in fig.get("covers") or []:
            pid = str(raw).strip()
            if not pid:
                continue
            covered.add(pid)
            if pid not in parts:
                findings.append(
                    Finding("ERROR", "HALLUCINATED_COVER", f"figure_plan 图{fig.get('fig')} covers 含未入 parts 的件号 {pid}。")
                )
            if pid in uncertain_ids:
                findings.append(
                    Finding("ERROR", "UNCERTAIN_IN_COVERS", f"件号 {pid} 在 uncertain 中，不得列入 figure_plan.covers。")
                )
    source_images = [str(x).strip() for x in (structure or {}).get("source_images") or [] if str(x).strip()]
    has_source = bool(source_images) or any(
        str(fig.get("path") or "").strip()
        for fig in (plan or {}).get("figures") or []
        if isinstance(fig, dict)
    )
    for pid, name in parts.items():
        if pid in uncertain_ids:
            findings.append(
                Finding("ERROR", "UNCERTAIN_AS_PART", f"件号 {pid}（{name}）已在 uncertain，不得写入 parts。")
            )
        if pid not in covered:
            findings.append(
                Finding(
                    "WARNING" if has_source else "ERROR",
                    "PART_WITHOUT_SOURCE",
                    f"件号 {pid}（{name}）未出现在任何 figure_plan.covers；未见结构应进 uncertain，不要写入权要/说明书。",
                )
            )
    if disclosure_text:
        for match in NEAR_MARK.finditer(disclosure_text):
            name, pid = match.group(1), match.group(2)
            if pid not in parts:
                findings.append(
                    Finding("ERROR", "HALLUCINATED_MARK", f"交底出现未披露件号（{pid}）「{name}」，应进 uncertain，不得当既定部件。")
                )
        protect = disclosure_text
        if "五、" in disclosure_text:
            protect = disclosure_text.split("五、", 1)[-1]
        for note in uncertain_notes:
            if len(note) >= 2 and note in protect:
                findings.append(
                    Finding("ERROR", "UNCERTAIN_IN_PROTECT", f"uncertain「{note}」出现在欲保护/后文，不得写成既定特征。")
                )
    return findings


def audit_case(case_dir: Path) -> tuple[list[Finding], Path | None]:
    struct_path = _find_schema(case_dir, "structure_schema")
    plan_path = _find_schema(case_dir, "figure_plan")
    if struct_path is None:
        return [Finding("ERROR", "NO_SCHEMA", "缺少 structure_schema；填表前不要编部件。")], None
    structure = _load_mapping(struct_path)
    plan = _load_mapping(plan_path) if plan_path else {}
    md = _find_disclosure_md(case_dir)
    text = md.read_text(encoding="utf-8") if md else None
    return check_source_parts(case_dir, structure=structure, plan=plan, disclosure_text=text), md


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true", help="写出 源材料门禁.md")
    args = parser.parse_args()
    case_dir = args.case_dir.expanduser().resolve()
    if not case_dir.is_dir():
        print("SOURCE_PARTS: ok=0 errors=1 warnings=0")
        print(f"不是目录：{case_dir}", file=sys.stderr)
        return 1
    try:
        findings, _md = audit_case(case_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("SOURCE_PARTS: ok=0 errors=1 warnings=0")
        print(f"无法读取：{exc}", file=sys.stderr)
        return 1
    errors = sum(item.level == "ERROR" for item in findings)
    warnings = sum(item.level == "WARNING" for item in findings)
    ok = errors == 0
    print(f"SOURCE_PARTS: ok={1 if ok else 0} errors={errors} warnings={warnings}")
    if args.json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    elif findings:
        for item in findings:
            print(f"{item.level}\t{item.code}\t{item.message}")
        print("汇总: 幻觉件进 uncertain，不要写入权要/说明书。")
    else:
        print("PASS: 件号均可追溯到 schema / figure_plan。")
    if args.write:
        lines = ["# 源材料门禁", "", "只允许源图/原文已披露的部件进入 parts 与第五章。", ""]
        if not findings:
            lines.append("未见未披露件号。")
        else:
            for item in findings:
                lines.append(f"- **{item.level}** `{item.code}` {item.message}")
        path = case_dir / "源材料门禁.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"SOURCE_PARTS_REPORT: {path}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
