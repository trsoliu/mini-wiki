#!/usr/bin/env python
"""件号 / 图号登记：图 ↔ 权要 ↔ 说明书双向核对。

用法：
  python tools/check_numeral_register.py --register 件号登记表.yaml \\
    --schema structure_schema.yaml --figure-plan figure_plan.yaml \\
    --claims 权利要求书.md --spec 说明书.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from stdio_utf8 import ensure_utf8_stdio

MARK = re.compile(r"[（(](\d+)[）)]")


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
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("需要 PyYAML：pip install -r requirements.txt") from exc
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} 根须为 mapping")
    return data


def _as_int_list(raw: Any) -> list[int]:
    out: list[int] = []
    for item in raw or []:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


def _part_id(raw: Any) -> str:
    return str(raw).strip()


def _split_claims(text: str) -> dict[int, str]:
    start = re.compile(r"(?m)^\s*(\d+)\s*[.、．]\s*")
    matches = list(start.finditer(text))
    claims: dict[int, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        claims[int(match.group(1))] = text[match.end() : end]
    return claims


def _mentions_part(text: str, part_id: str, name: str) -> bool:
    if MARK.search(text) and part_id in MARK.findall(text):
        return True
    if name and name in text:
        return True
    return False


def check_register(
    register: dict[str, Any],
    *,
    schema: Optional[dict[str, Any]] = None,
    figure_plan: Optional[dict[str, Any]] = None,
    claims_text: Optional[str] = None,
    spec_text: Optional[str] = None,
) -> list[Finding]:
    findings: list[Finding] = []
    parts = [item for item in (register.get("parts") or []) if isinstance(item, dict)]
    figures = [item for item in (register.get("figures") or []) if isinstance(item, dict)]
    ids = [_part_id(item.get("id")) for item in parts]
    if ids and len(ids) != len(set(ids)):
        findings.append(Finding("ERROR", "DUP_ID", "件号登记表 parts.id 有重复。"))

    for item in parts:
        if not _part_id(item.get("id")):
            findings.append(Finding("ERROR", "EMPTY_ID", "存在空的 parts.id。"))
        if not str(item.get("name") or "").strip():
            findings.append(
                Finding("ERROR", "EMPTY_NAME", f"件号 {item.get('id')} 缺少 name。")
            )

    if schema is not None:
        schema_parts = {
            _part_id(item.get("id")): str(item.get("name") or "").strip()
            for item in (schema.get("parts") or [])
            if isinstance(item, dict) and _part_id(item.get("id"))
        }
        register_ids = {i for i in ids if i}
        for pid, pname in schema_parts.items():
            if pid not in register_ids:
                findings.append(
                    Finding("ERROR", "SCHEMA_MISSING", f"structure_schema 件号 {pid}（{pname}）未入登记表。")
                )
        for item in parts:
            pid = _part_id(item.get("id"))
            if pid and pid not in schema_parts:
                findings.append(
                    Finding("ERROR", "REGISTER_EXTRA", f"登记表件号 {pid} 不在 structure_schema。")
                )
            name = str(item.get("name") or "").strip()
            if pid in schema_parts and name and schema_parts[pid] and name != schema_parts[pid]:
                findings.append(
                    Finding(
                        "WARNING",
                        "NAME_MISMATCH",
                        f"件号 {pid} 登记名「{name}」与 schema「{schema_parts[pid]}」不一致。",
                    )
                )

    plan_figs: set[int] = set()
    cover_map: dict[int, set[str]] = {}
    if figure_plan is not None:
        for item in figure_plan.get("figures") or []:
            if not isinstance(item, dict) or item.get("use_in_disclosure") is not True:
                continue
            try:
                fig = int(item.get("fig"))
            except (TypeError, ValueError):
                continue
            plan_figs.add(fig)
            covers = {str(x).strip() for x in (item.get("covers") or []) if str(x).strip()}
            cover_map[fig] = covers

        registered_figs: set[int] = set()
        for item in figures:
            try:
                registered_figs.add(int(item.get("fig")))
            except (TypeError, ValueError):
                continue
        for item in parts:
            registered_figs.update(_as_int_list(item.get("figures")))

        for fig in sorted(plan_figs):
            if fig not in registered_figs:
                findings.append(
                    Finding("ERROR", "FIG_UNREGISTERED", f"入文图 {fig} 未写入登记表 figures 或 parts.figures。")
                )
        for fig in sorted(registered_figs):
            if plan_figs and fig not in plan_figs:
                findings.append(
                    Finding("ERROR", "FIG_UNKNOWN", f"登记表图 {fig} 不是 figure_plan 的入文 fig。")
                )
        for item in parts:
            pid = _part_id(item.get("id"))
            for fig in _as_int_list(item.get("figures")):
                covers = cover_map.get(fig)
                if covers is not None and covers and pid not in covers:
                    findings.append(
                        Finding(
                            "WARNING",
                            "COVERS_MISMATCH",
                            f"件号 {pid} 登记出现于图 {fig}，但 figure_plan.covers 未列该件。",
                        )
                    )

    if claims_text is not None and parts:
        claim_map = _split_claims(claims_text)
        for item in parts:
            pid = _part_id(item.get("id"))
            name = str(item.get("name") or "").strip()
            listed = set(_as_int_list(item.get("claims")))
            appeared: set[int] = set()
            for num, body in claim_map.items():
                if _mentions_part(body, pid, name):
                    appeared.add(num)
            for num in sorted(listed - appeared):
                findings.append(
                    Finding(
                        "ERROR",
                        "CLAIM_MARK_MISSING",
                        f"件号 {pid} 登记出现于权项 {num}，但该权项未见「（{pid}）」或名称「{name}」。",
                    )
                )
            for num in sorted(appeared - listed):
                findings.append(
                    Finding(
                        "WARNING",
                        "CLAIM_UNLISTED",
                        f"权项 {num} 出现了件号 {pid}，登记表 claims 未列入。",
                    )
                )

    if spec_text is not None and parts:
        for item in parts:
            pid = _part_id(item.get("id"))
            name = str(item.get("name") or "").strip()
            hit = _mentions_part(spec_text, pid, name)
            flagged = item.get("specification")
            if flagged is True and not hit:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPEC_MARK_MISSING",
                        f"件号 {pid} 标明已入说明书，但未见「（{pid}）」或名称「{name}」。",
                    )
                )
            if flagged is False and hit:
                findings.append(
                    Finding(
                        "WARNING",
                        "SPEC_UNFLAGGED",
                        f"说明书出现了件号 {pid}，登记表 specification 未标 true。",
                    )
                )
            if flagged is None and not hit:
                findings.append(
                    Finding(
                        "WARNING",
                        "SPEC_UNCHECKED",
                        f"件号 {pid} 未填 specification，且说明书未见该件。",
                    )
                )

    if not parts and not figures:
        findings.append(Finding("ERROR", "EMPTY_REGISTER", "登记表 parts 与 figures 都为空。"))

    return findings


def main() -> int:
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", required=True, type=Path)
    parser.add_argument("--schema", type=Path, default=None)
    parser.add_argument("--figure-plan", type=Path, default=None)
    parser.add_argument("--claims", type=Path, default=None)
    parser.add_argument("--spec", type=Path, default=None)
    args = parser.parse_args()

    try:
        register = _load_mapping(args.register.expanduser().resolve())
        schema = _load_mapping(args.schema) if args.schema else None
        plan = _load_mapping(args.figure_plan) if args.figure_plan else None
        claims = args.claims.read_text(encoding="utf-8") if args.claims else None
        spec = args.spec.read_text(encoding="utf-8") if args.spec else None
    except FileNotFoundError as exc:
        print("APPLICATION_NUMERALS: ok=0 errors=1 warnings=0")
        print(f"文件不存在：{exc.filename}", file=sys.stderr)
        return 1
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("APPLICATION_NUMERALS: ok=0 errors=1 warnings=0")
        print(f"无法读取：{exc}", file=sys.stderr)
        return 1

    findings = check_register(
        register, schema=schema, figure_plan=plan, claims_text=claims, spec_text=spec
    )
    errors = sum(item.level == "ERROR" for item in findings)
    warnings = sum(item.level == "WARNING" for item in findings)
    ok = errors == 0
    print(f"APPLICATION_NUMERALS: ok={1 if ok else 0} errors={errors} warnings={warnings}")
    if not findings:
        print("PASS: 图↔权要↔说明书未见结构性缺口。机器通过不等于可提交。")
    else:
        for item in findings:
            print(f"{item.level}\t{item.code}\t{item.message}")
        print(f"汇总: {errors} 个错误, {warnings} 个警告。机器通过不等于可提交。")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
