# -*- coding: utf-8 -*-
"""外观视图检查：漏视、虚线范围、新事项风险。只出清单，不改像素。

  python skills/patent-disclosure/tools/check_design_views.py --case-dir outputs/{案件}
  python skills/patent-application/tools/check_design_views.py --case-dir <交底> --out <申请产出>/视图检查清单.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ORTHO = ("主视图", "后视图", "左视图", "右视图", "俯视图", "仰视图", "正面", "背面")
OK_EXTRA = ("立体图",)
FAIL = "不合格"
WAIT = "待核"
OK = "通过"


def _load_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text)
        except Exception:
            data = json.loads(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"根须为对象: {path}")
    return data


def _find_schema(case_dir: Path, stem: str) -> Path | None:
    for name in (f"{stem}.yaml", f"{stem}.yml", f"{stem}.json"):
        path = case_dir / name
        if path.is_file():
            return path
    return None


def _names(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    for item in value or []:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _face_key(name: str) -> str:
    text = str(name or "").strip()
    for face in ORTHO + OK_EXTRA:
        if text == face or text.endswith(face):
            return face
    return text


def _omitted_names(schema: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for item in schema.get("omitted_views") or []:
        if isinstance(item, dict):
            text = str(item.get("name") or "").strip()
        else:
            text = str(item).strip()
        if text:
            out.append(_face_key(text))
    return out


def _uncertain_text(schema: dict[str, Any]) -> str:
    bits = _names(schema.get("uncertain"))
    return "；".join(bits)


def _line_scope(schema: dict[str, Any]) -> dict[str, Any]:
    raw = schema.get("line_scope")
    return raw if isinstance(raw, dict) else {}


def _disclosure_covers(plan: dict[str, Any]) -> tuple[set[str], list[dict[str, Any]]]:
    used: list[dict[str, Any]] = []
    covers: set[str] = set()
    for item in plan.get("figures") or []:
        if not isinstance(item, dict) or not item.get("use_in_disclosure"):
            continue
        used.append(item)
        for name in _names(item.get("covers")):
            covers.add(_face_key(name))
    return covers, used


def audit_design_views(schema: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    claimed = [_face_key(x) for x in _names(schema.get("claimed_faces"))]
    omitted = _omitted_names(schema)
    omitted_set = set(omitted)
    claimed_set = set(claimed)
    covers, used = _disclosure_covers(plan)
    uncertain = _uncertain_text(schema)

    for face in claimed:
        if face in omitted_set:
            rows.append(
                {
                    "kind": "漏视",
                    "item": face,
                    "verdict": FAIL,
                    "note": "同时出现在 claimed_faces 与 omitted_views，口径打架",
                }
            )
            continue
        if face not in covers:
            rows.append(
                {
                    "kind": "漏视",
                    "item": face,
                    "verdict": FAIL,
                    "note": "要点落面无入文图覆盖，且不是故意省略。不要默补假面",
                }
            )
        else:
            rows.append(
                {
                    "kind": "漏视",
                    "item": face,
                    "verdict": OK,
                    "note": "入文图已覆盖",
                }
            )

    scope = _line_scope(schema)
    lock_claimed = set(_names(scope.get("claimed")))
    lock_unclaimed = set(_names(scope.get("unclaimed")))
    if not lock_claimed and not lock_unclaimed:
        rows.append(
            {
                "kind": "虚线不一致",
                "item": "line_scope",
                "verdict": WAIT,
                "note": "未锁定实线/虚线范围。出线稿前须写 claimed（实线）与 unclaimed（虚线，可空）",
            }
        )
    else:
        clash = lock_claimed & lock_unclaimed
        if clash:
            rows.append(
                {
                    "kind": "虚线不一致",
                    "item": "锁定表",
                    "verdict": FAIL,
                    "note": "同一部位同时实线与虚线：" + "、".join(sorted(clash)),
                }
            )
        by_view = [item for item in (scope.get("by_view") or []) if isinstance(item, dict)]
        if not by_view:
            rows.append(
                {
                    "kind": "虚线不一致",
                    "item": "各视复核",
                    "verdict": WAIT,
                    "note": "已有锁定表，各视尚未逐视复核。入文前把 by_view 补齐，线型须与锁定表相同",
                }
            )
        else:
            seen: dict[str, tuple[set[str], set[str]]] = {}
            for view in by_view:
                name = _face_key(str(view.get("name") or ""))
                claimed_v = set(_names(view.get("claimed")))
                unclaimed_v = set(_names(view.get("unclaimed")))
                both = claimed_v & unclaimed_v
                if both:
                    rows.append(
                        {
                            "kind": "虚线不一致",
                            "item": name or "未名视图",
                            "verdict": FAIL,
                            "note": "该视同一部位又实又虚：" + "、".join(sorted(both)),
                        }
                    )
                if lock_claimed and claimed_v != lock_claimed:
                    rows.append(
                        {
                            "kind": "虚线不一致",
                            "item": name or "未名视图",
                            "verdict": FAIL,
                            "note": "实线部位与锁定表不同",
                        }
                    )
                if lock_unclaimed and unclaimed_v != lock_unclaimed:
                    rows.append(
                        {
                            "kind": "虚线不一致",
                            "item": name or "未名视图",
                            "verdict": FAIL,
                            "note": "虚线部位与锁定表不同",
                        }
                    )
                if name:
                    seen[name] = (claimed_v, unclaimed_v)
            parts: dict[str, set[str]] = {}
            for name, (claimed_v, unclaimed_v) in seen.items():
                for part in claimed_v:
                    parts.setdefault(part, set()).add("实线")
                for part in unclaimed_v:
                    parts.setdefault(part, set()).add("虚线")
            for part, styles in parts.items():
                if len(styles) > 1:
                    rows.append(
                        {
                            "kind": "虚线不一致",
                            "item": part,
                            "verdict": FAIL,
                            "note": "跨视线型不一致（" + " / ".join(sorted(styles)) + "）",
                        }
                    )
            if not any(row["kind"] == "虚线不一致" and row["verdict"] == FAIL for row in rows):
                rows.append(
                    {
                        "kind": "虚线不一致",
                        "item": "锁定表",
                        "verdict": OK,
                        "note": "各视实线/虚线与锁定表一致",
                    }
                )

    for item in used:
        fig = item.get("fig")
        label = f"图{fig}" if fig not in (None, "") else (str(item.get("path") or "入文图"))
        for raw in _names(item.get("covers")):
            face = _face_key(raw)
            if face in omitted_set:
                rows.append(
                    {
                        "kind": "新事项风险",
                        "item": f"{label} · {face}",
                        "verdict": FAIL,
                        "note": "故意省略的面仍入了文。禁止为省略面补图",
                    }
                )
            elif face in ORTHO and face not in claimed_set:
                rows.append(
                    {
                        "kind": "新事项风险",
                        "item": f"{label} · {face}",
                        "verdict": FAIL,
                        "note": "入文正投影不在 claimed_faces。源材料未见的面不要编",
                    }
                )
    if uncertain:
        for item in used:
            for raw in _names(item.get("covers")):
                face = _face_key(raw)
                if face in uncertain and face in claimed_set:
                    fig = item.get("fig")
                    label = f"图{fig}" if fig not in (None, "") else "入文图"
                    rows.append(
                        {
                            "kind": "新事项风险",
                            "item": f"{label} · {face}",
                            "verdict": WAIT,
                            "note": "该落面写在 uncertain（缺源图），却已有入文图，须核是否编造",
                        }
                    )
                    break
    if not any(row["kind"] == "新事项风险" for row in rows):
        rows.append(
            {
                "kind": "新事项风险",
                "item": "入文集合",
                "verdict": OK,
                "note": "未见省略面入文或编造正投影",
            }
        )
    return rows


def render_checklist(rows: list[dict[str, str]]) -> str:
    fail = sum(1 for row in rows if row["verdict"] == FAIL)
    wait = sum(1 for row in rows if row["verdict"] == WAIT)
    lines = [
        "# 视图检查清单",
        "",
        "> 外观视图底稿。漏视 / 虚线范围 / 新事项只记本清单，**不改原图像素**，不写入简要说明。不构成审查结论。",
        "",
        f"- 不合格 {fail} 条，待核 {wait} 条。",
        "",
        "| 类 | 项 | 结论 | 说明 |",
        "|----|----|------|------|",
    ]
    for row in rows:
        note = (row.get("note") or "").replace("|", "\\|")
        lines.append(f"| {row['kind']} | {row['item']} | {row['verdict']} | {note} |")
    lines.append("")
    return "\n".join(lines)


def check_case(case_dir: Path) -> tuple[list[dict[str, str]], str]:
    app_path = _find_schema(case_dir, "appearance_schema")
    plan_path = _find_schema(case_dir, "figure_plan")
    rows: list[dict[str, str]] = []
    if not app_path or not plan_path:
        missing = []
        if not app_path:
            missing.append("appearance_schema")
        if not plan_path:
            missing.append("figure_plan")
        rows.append(
            {
                "kind": "漏视",
                "item": "材料",
                "verdict": FAIL,
                "note": "缺少 " + "、".join(missing),
            }
        )
        return rows, render_checklist(rows)
    schema = _load_data(app_path)
    plan = _load_data(plan_path)
    rows = audit_design_views(schema, plan)
    return rows, render_checklist(rows)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", required=True, help="交底案件目录")
    ap.add_argument("--out", default="", help="清单路径；默认写到案件目录 视图检查清单.md")
    args = ap.parse_args(argv)
    case_dir = Path(args.case_dir)
    if not case_dir.is_dir():
        print(f"VIEW_CHECK: ok=0 reason=no_case_dir path={case_dir}", file=sys.stderr)
        return 2
    rows, text = check_case(case_dir)
    dest = Path(args.out) if str(args.out).strip() else case_dir / "视图检查清单.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    fail = sum(1 for row in rows if row["verdict"] == FAIL)
    wait = sum(1 for row in rows if row["verdict"] == WAIT)
    print(f"VIEW_CHECK: fail={fail} wait={wait} path={dest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
