#!/usr/bin/env python
"""校验案件 formula_plan：来源标记、agent 范式 id、禁装饰音、数值例等。

用法：
  python tools/check_formula_plan.py -i outputs/某案/formula_plan.yaml
  python tools/check_formula_plan.py -i plan.yaml --eval
  python tools/check_formula_plan.py -i plan.yaml --case-dir outputs/某案
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from formula_chem import check_chemistry, latex_looks_chemical
from formula_eval import eval_equation
from formula_paradigms import (
    combo_by_id,
    load_paradigms,
    paradigm_by_id,
)
from formula_units import check_additive_units, check_score_weights
from stdio_utf8 import ensure_utf8_stdio


def _load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise SystemExit("需要 PyYAML") from exc
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise SystemExit("formula_plan 根须为 mapping")
    return data


def equation_origin(eq: dict[str, Any]) -> str:
    """source | agent | invalid。无 origin 且已填 paradigm_id 时按 agent（旧计划）。"""
    raw = str(eq.get("origin") or "").strip().lower()
    if raw in ("source", "agent"):
        return raw
    if raw:
        return "invalid"
    if str(eq.get("paradigm_id") or "").strip():
        return "agent"
    return "source"


def _selected_tags(cfg: dict[str, Any], pids: list[str]) -> set[str]:
    tags: set[str] = set()
    for pid in pids:
        p = paradigm_by_id(cfg, pid)
        if not p:
            continue
        for t in p.get("tags") or []:
            tags.add(str(t).strip().lower())
    return tags


def check_plan(
    plan: dict[str, Any],
    case_dir: str | Path | None = None,
    *,
    eval_numeric: bool = False,
) -> dict[str, Any]:
    cfg = load_paradigms(case_dir)
    rules = cfg.get("rules") or {}
    errors: list[str] = []
    warnings: list[str] = []

    pids = [str(x).strip() for x in (plan.get("paradigm_ids") or []) if str(x).strip()]
    combo_id = str(plan.get("combo_id") or "").strip()
    if combo_id:
        combo = combo_by_id(cfg, combo_id)
        if not combo:
            errors.append(f"未知 combo_id: {combo_id}")
        else:
            for pid in combo.get("paradigm_ids") or []:
                if str(pid) not in pids:
                    warnings.append(f"combo {combo_id} 含 {pid}，但 paradigm_ids 未列出（建议补全）")

    eqs = plan.get("equations") or []
    if not isinstance(eqs, list):
        errors.append("equations 须为列表")
        eqs = []

    origins: list[str] = []
    for eq in eqs:
        if not isinstance(eq, dict):
            origins.append("invalid")
        else:
            origins.append(equation_origin(eq))

    has_agent = any(o == "agent" for o in origins)
    has_source = any(o == "source" for o in origins)

    if has_agent and not pids:
        derived: list[str] = []
        for eq, o in zip(eqs, origins):
            if not isinstance(eq, dict) or o != "agent":
                continue
            epid = str(eq.get("paradigm_id") or "").strip()
            if epid:
                derived.append(epid)
        if derived:
            warnings.append("含 agent 式但根级 paradigm_ids 为空（已按各式 paradigm_id 校验）")
            pids = list(dict.fromkeys(derived))
        else:
            errors.append("含 origin: agent 的公式但 paradigm_ids / paradigm_id 为空")

    for pid in pids:
        if not paradigm_by_id(cfg, pid):
            errors.append(f"未知 paradigm_id: {pid}")

    omitted = plan.get("omitted")
    if omitted is None:
        omitted = []
    if omitted and not isinstance(omitted, list):
        errors.append("omitted 须为列表")
        omitted = []
    elif isinstance(omitted, list):
        for i, item in enumerate(omitted):
            if not isinstance(item, dict):
                errors.append(f"omitted[{i}] 须为 mapping")
                continue
            ref = str(item.get("ref") or item.get("source_ref") or "").strip()
            reason = str(item.get("reason") or item.get("reason_zh") or "").strip()
            if not ref:
                warnings.append(f"omitted[{i}] 缺 ref")
            if not reason:
                warnings.append(f"omitted[{i}] 缺 reason")

    forbid = list(rules.get("forbid_accent_commands") or [])
    if rules.get("forbid_accents", True) and not forbid:
        forbid = [r"\tilde", r"\hat", r"\bar", r"\breve", r"\vec"]

    latex_blobs: list[str] = []
    for i, eq in enumerate(eqs):
        if not isinstance(eq, dict):
            errors.append(f"equations[{i}] 须为 mapping")
            continue
        origin = origins[i]
        if origin == "invalid":
            errors.append(
                f"equations[{i}].origin 须为 source 或 agent，收到 {eq.get('origin')!r}"
            )
        epid = str(eq.get("paradigm_id") or "").strip()
        if origin == "agent":
            if not epid:
                errors.append(f"equations[{i}] origin=agent 但未填 paradigm_id")
            elif not paradigm_by_id(cfg, epid):
                errors.append(f"equations[{i}].paradigm_id 未知: {epid}")
            elif epid not in pids:
                warnings.append(f"equations[{i}] 使用 {epid} 但未列入 paradigm_ids")
        elif origin == "source":
            if not str(eq.get("source_ref") or "").strip():
                warnings.append(f"equations[{i}] origin=source 建议填写 source_ref")
            if epid and not paradigm_by_id(cfg, epid):
                warnings.append(
                    f"equations[{i}] source 式的 paradigm_id={epid} 不在库中（可选标签，已忽略）"
                )
        lx = str(eq.get("latex") or "")
        if origin in ("source", "agent") and not lx.strip():
            errors.append(f"equations[{i}] 缺 latex")
        latex_blobs.append(lx)
        normalized = lx.replace("\\\\", "\\")
        for cmd in forbid:
            token = cmd if str(cmd).startswith("\\") else f"\\{cmd}"
            if token not in normalized:
                continue
            msg = f"equations[{i}] 含禁用装饰音 {token}"
            if origin == "agent":
                errors.append(msg)
            else:
                warnings.append(msg + "（source 式保真；成文若改记号须填 original_latex）")

    plain = str(plan.get("plain_zh") or "").strip()
    if eqs and not plain:
        warnings.append("建议填写 plain_zh（主关系人话）")

    if rules.get("require_numeric_example", True) and (eqs or pids):
        ne = plan.get("numeric_example") or {}
        missing_ne = not isinstance(ne, dict) or not (ne.get("given") or ne.get("result"))
        if missing_ne:
            if has_agent:
                errors.append("缺少 numeric_example.given / result（可算数值例）")
            elif has_source:
                warnings.append(
                    "origin=source 建议补 numeric_example；复杂式可手算或从缺，勿为代算改写公式"
                )

    syms = plan.get("symbols") or []
    max_sym = int(rules.get("max_free_symbols") or 0)
    if max_sym and isinstance(syms, list) and len(syms) > max_sym:
        warnings.append(f"symbols 共 {len(syms)} 个，超过建议上限 {max_sym}")

    # 裸 max(1, …) 启发式
    blob = "\n".join(latex_blobs)
    if re.search(r"max\s*\(\s*1\s*,", blob, re.I):
        warnings.append("检测到 max(1, …)：请确认 1 与分母同量纲，否则改用 ε")

    tags = _selected_tags(cfg, pids)
    ne = plan.get("numeric_example") or {}
    given = ne.get("given") if isinstance(ne, dict) else None
    result = ne.get("result") if isinstance(ne, dict) else None

    eval_details: list[dict[str, Any]] = []
    if eval_numeric and eqs:
        any_ok = False
        for i, eq in enumerate(eqs):
            if not isinstance(eq, dict):
                continue
            lx = str(eq.get("latex") or "")
            if not lx.strip():
                continue
            detail = eval_equation(lx, given, result)
            detail["index"] = i
            eval_details.append(detail)
            st = detail.get("status")
            if st == "ok":
                any_ok = True
            elif st == "mismatch":
                errors.append(
                    f"equations[{i}] 数值例代算失败：{detail.get('reason')}"
                )
            else:
                warnings.append(
                    f"equations[{i}] 未自动代算：{detail.get('reason')}（请手算）"
                )
        if eval_details and not any_ok and not any(
            d.get("status") == "mismatch" for d in eval_details
        ):
            warnings.append(
                "所有公式均未能自动代算（求和/范数/分位等复杂式属预期）；请按 §8.2 手算 numeric_example"
            )

    chem_force = "chemistry" in tags or "stoich" in tags
    chem_latex = any(
        isinstance(eq, dict) and latex_looks_chemical(str(eq.get("latex") or ""))
        for eq in eqs
    )
    chem_details: dict[str, Any] | None = None
    if chem_force or chem_latex:
        chem_details = check_chemistry(eqs, given=given, force=chem_force)
        errors.extend(chem_details.get("errors") or [])
        warnings.extend(chem_details.get("warnings") or [])

    if "score" in tags or "normalize" in tags:
        warnings.extend(check_score_weights(pids, given))

    if "physics" in tags or "si" in tags or isinstance(syms, list):
        warnings.extend(check_additive_units(eqs, syms if isinstance(syms, list) else None))

    out: dict[str, Any] = {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "paradigm_count": len(cfg.get("paradigms") or []),
        "sources": cfg.get("_sources"),
        "tags": sorted(tags),
    }
    if eval_numeric:
        out["eval"] = eval_details
    if chem_details is not None:
        out["chemistry"] = {
            "checked_reactions": chem_details.get("checked_reactions"),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-i", "--input", required=True, help="formula_plan.yaml|json")
    ap.add_argument("--case-dir", default="", help="案件目录（加载覆盖范式）")
    ap.add_argument(
        "--eval",
        dest="eval_numeric",
        action="store_true",
        help="对可解析的简单式代入 numeric_example 核对 result（复杂式跳过并警告）",
    )
    args = ap.parse_args(argv)

    path = Path(args.input)
    if not path.is_file():
        raise SystemExit(f"找不到: {path}")
    case = args.case_dir.strip() or str(path.parent)
    plan = _load(path)
    result = check_plan(plan, case_dir=case, eval_numeric=args.eval_numeric)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
