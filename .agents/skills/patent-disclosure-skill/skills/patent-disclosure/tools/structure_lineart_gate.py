# -*- coding: utf-8 -*-
"""实用新型结构线稿门禁：成文前默认开。无参考图则文生图。CAD 不得当线稿入文。

  python tools/structure_lineart_gate.py --case-dir outputs/case --check
  python tools/structure_lineart_gate.py --case-dir outputs/case --prepare-jobs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

ENABLE_ENV = "PATENT_SKILL_STRUCTURE_LINEART"
SKIP_ENV = "PATENT_SKILL_SKIP_LINEART"

CONFIRM_ZH = ""


def parse_enabled(cli_flag: bool = False, *, skip: bool = False) -> bool:
    if skip:
        return False
    if os.environ.get(SKIP_ENV, "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    if os.environ.get("PATENT_SKILL_SKIP_STRUCTURE_LINEART", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return False
    return True


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
        p = case_dir / name
        if p.is_file():
            return p
    return None


def _resolve_path(case_dir: Path, p: str) -> Path:
    path = Path(p)
    if path.is_file():
        return path.resolve()
    cand = (case_dir / p).resolve()
    if cand.is_file():
        return cand
    return path


def parts_index(structure: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in structure.get("parts") or []:
        if not isinstance(part, dict):
            continue
        pid = str(part.get("id") or "").strip()
        if not pid:
            continue
        out[pid] = str(part.get("name") or "").strip()
    return out


def validate_brief(
    brief: dict[str, Any],
    case_dir: Path,
    *,
    structure: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not brief.get("enabled"):
        errors.append("structure_lineart_brief.enabled 不为 true")
    if (brief.get("patent_type") or "") != "utility_model":
        errors.append("patent_type 须为 utility_model")

    views = brief.get("views") or []
    if not views:
        errors.append("views 为空")

    legend = brief.get("parts_legend") or []
    has_summary = bool(str(brief.get("structure_summary") or "").strip())
    if not legend and not has_summary:
        errors.append("structure_summary 与 parts_legend 不能都空")

    struct_parts = parts_index(structure or {})
    if structure is not None and not struct_parts:
        errors.append("structure_schema.parts 为空，无法对齐件号")

    legend_ids: set[str] = set()
    for i, item in enumerate(legend):
        if not isinstance(item, dict):
            errors.append(f"parts_legend[{i}] 非法")
            continue
        pid = str(item.get("id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not pid:
            errors.append(f"parts_legend[{i}] 缺少 id")
            continue
        legend_ids.add(pid)
        if struct_parts:
            if pid not in struct_parts:
                errors.append(f"parts_legend id={pid} 不在 structure_schema.parts 中")
            elif name and struct_parts.get(pid) and name != struct_parts[pid]:
                errors.append(
                    f"parts_legend id={pid} 名称「{name}」与 structure「{struct_parts[pid]}」不一致"
                )

    mode = str(brief.get("callout_mode") or "overlay").strip().lower()
    if mode not in {"overlay", "in_prompt", "contour_only"}:
        errors.append("callout_mode 须为 overlay | in_prompt | contour_only")

    for i, v in enumerate(views):
        if not isinstance(v, dict):
            errors.append(f"views[{i}] 非法")
            continue
        paths = v.get("source_paths") or []
        if not paths:
            continue
        ok_any = False
        for raw in paths:
            rp = _resolve_path(case_dir, str(raw))
            if rp.is_file():
                ok_any = True
            else:
                errors.append(f"views[{i}] 源图不存在: {raw}")
        if not ok_any:
            errors.append(f"views[{i}] 无任何可读源图")

        visible = [str(x).strip() for x in (v.get("visible_part_ids") or []) if str(x).strip()]
        if mode != "contour_only" and not visible and legend_ids:
            errors.append(f"views[{i}] 在 callout_mode={mode} 下应提供 visible_part_ids")
        for pid in visible:
            if legend_ids and pid not in legend_ids:
                errors.append(f"views[{i}] visible_part_ids 含未知件号: {pid}")
            if struct_parts and pid not in struct_parts:
                errors.append(f"views[{i}] visible_part_ids 不在 structure.parts: {pid}")

    return errors


def collect_source_images_from_plan(plan: dict[str, Any], case_dir: Path) -> list[str]:
    out: list[str] = []
    for fig in plan.get("figures") or []:
        if not isinstance(fig, dict):
            continue
        p = fig.get("path") or ""
        if not p:
            continue
        rp = _resolve_path(case_dir, str(p))
        if rp.is_file():
            out.append(str(rp))
    return out


def _callouts_for_view(brief: dict[str, Any], view: dict[str, Any]) -> list[dict[str, str]]:
    legend = {
        str(x.get("id")).strip(): str(x.get("name") or "").strip()
        for x in (brief.get("parts_legend") or [])
        if isinstance(x, dict) and str(x.get("id") or "").strip()
    }
    visible = [str(x).strip() for x in (view.get("visible_part_ids") or []) if str(x).strip()]
    if not visible:
        visible = list(legend.keys())
    return [{"id": pid, "name": legend.get(pid, "")} for pid in visible]


def build_jobs(brief: dict[str, Any], case_dir: Path) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    assist = case_dir / "lineart_assist"
    assist.mkdir(parents=True, exist_ok=True)
    mode = str(brief.get("callout_mode") or "overlay").strip().lower()
    for i, v in enumerate(brief.get("views") or []):
        if not isinstance(v, dict):
            continue
        resolved = []
        for raw in v.get("source_paths") or []:
            rp = _resolve_path(case_dir, str(raw))
            if rp.is_file():
                resolved.append(str(rp))
        name = str(v.get("view_name") or f"view_{i+1}")
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:60] or f"view_{i+1}"
        out_path = v.get("output_path") or f"lineart_assist/{safe}_structure_lineart.png"
        callout_out = v.get("callout_output_path") or ""
        if not callout_out:
            stem = Path(str(out_path)).stem
            parent = str(Path(str(out_path)).parent).replace("\\", "/")
            callout_out = f"{parent}/{stem}_callouts.png"

        callouts = _callouts_for_view(brief, v)
        legend_txt = "；".join(f"{c['id']}-{c['name']}" for c in callouts if c.get("id"))

        prompt = (v.get("gen_prompt") or "").strip()
        if not prompt:
            prompt = (
                f"Black-and-white patent-style STRUCTURE line art of the assembly in the reference image(s). "
                f"View: {name}. Summary: {brief.get('structure_summary') or ''}. "
                f"Goal: {v.get('lineart_goal') or 'clean structural contours'}. "
                "No color, no photoreal shading, no logos, no invented internals not visible in the reference; "
                "white background; match proportions in the reference images."
            )
            if mode == "in_prompt" and legend_txt:
                prompt += (
                    f" Add leader lines and part numbers exactly as: {legend_txt}. "
                    "Do not invent other part numbers."
                )
            elif mode == "overlay":
                prompt += " Do NOT draw part numbers or leader lines in this contour pass; numbers will be overlaid later."
            elif mode == "contour_only":
                prompt += " Contour only; no part numbers."

        jobs.append(
            {
                "view_name": name,
                "source_paths": resolved,
                "reference_images": resolved,
                "relates_hint": v.get("relates_hint") or [],
                "visible_part_ids": [c["id"] for c in callouts],
                "callouts": callouts,
                "callout_mode": mode,
                "callout_legend": legend_txt,
                "gen_prompt": prompt,
                "output_path": out_path,
                "callout_output_path": callout_out,
                "callout_anchor_manifest": "structure_callout_anchors.yaml",
                "callout_overlay_tool": "tools/structure_callout_overlay.py",
                "absolute_output_path": str((case_dir / out_path).resolve()),
                "absolute_callout_output_path": str((case_dir / callout_out).resolve()),
                "forbid_text_only": False,
                "host_hint": (
                    "Use reference images for img2img contour; if img2img unavailable, "
                    "describe references then txt2img. After contour generation, write "
                    "structure_lineart_compose.yaml (one SVG group per part) and run "
                    "structure_lineart_compose.py; then inspect the composed figure "
                    "with a vision model and persist normalized part anchors plus nearby label "
                    "positions in structure_callout_anchors.yaml (set base_svg_path); then render SVG with "
                    "structure_callout_overlay.py. After overlay, re-read the labeled figure "
                    "and verify each leader lands on the named part (not a neighbor); fix YAML "
                    "and re-overlay (max 2 rounds); do not regenerate contours to fix numbers. "
                    "CAD projections are material only, never disclosure lineart."
                ),
            }
        )
    return jobs


def run_check(case_dir: Path, *, enabled: bool) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ok": False,
        "enabled_flag": enabled,
        "confirm_prompt_zh": CONFIRM_ZH,
        "errors": [],
        "hints": [],
    }
    if not enabled:
        result["errors"].append(
            f"structure_lineart 已跳过（--skip 或 {SKIP_ENV}=1 / PATENT_SKILL_SKIP_STRUCTURE_LINEART=1）"
        )
        return result

    brief_path = _find_schema(case_dir, "structure_lineart_brief")
    plan_path = _find_schema(case_dir, "figure_plan")
    struct_path = _find_schema(case_dir, "structure_schema")

    if not plan_path and not struct_path:
        result["errors"].append("案件目录缺少 figure_plan / structure_schema")
        return result

    if not struct_path:
        result["errors"].append("缺少 structure_schema；请先按 fill_structure_schema.md 填写")
        return result

    if not brief_path:
        result["errors"].append("缺少 structure_lineart_brief.yaml；请先按 structure_lineart_assist.md 填写")
        return result

    structure = _load_data(struct_path)
    brief = _load_data(brief_path)
    errors = validate_brief(brief, case_dir, structure=structure)
    result["errors"] = errors
    result["brief_path"] = str(brief_path)
    result["structure_path"] = str(struct_path)
    result["ok"] = not errors
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="实用新型结构线稿门禁（默认开；无参考图则文生图）")
    p.add_argument("--case-dir", type=Path, help="案件 outputs 目录")
    p.add_argument("--enable-structure-lineart", action="store_true", help="兼容旧旗标；默认已开启")
    p.add_argument("--skip-structure-lineart", action="store_true")
    p.add_argument("--check", action="store_true", help="仅校验")
    p.add_argument("--prepare-jobs", action="store_true", help="校验通过后写出 jobs JSON")
    args = p.parse_args(argv)

    if not args.case_dir:
        p.error("需要 --case-dir")

    enabled = parse_enabled(args.enable_structure_lineart, skip=args.skip_structure_lineart)
    case_dir = args.case_dir.resolve()
    if not case_dir.is_dir():
        print(json.dumps({"ok": False, "errors": [f"不是目录: {case_dir}"]}, ensure_ascii=False), file=sys.stderr)
        return 1

    report = run_check(case_dir, enabled=enabled)
    if args.prepare_jobs:
        if not report.get("ok"):
            print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        brief = _load_data(Path(report["brief_path"]))
        jobs = build_jobs(brief, case_dir)
        try:
            from image_gen import attach_job_mode, decide_mode, load_plan

            decision = decide_mode(load_plan(case_dir) or {}, case_dir)
            jobs = [attach_job_mode(j, decision) for j in jobs]
        except Exception:
            decision = {}
        if not jobs:
            report["ok"] = False
            report["errors"] = list(report.get("errors") or []) + ["未生成任何 job"]
            print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        out = case_dir / "lineart_assist" / "structure_lineart_jobs.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ok": True,
            "forbid_text_only": False,
            "decision": decision,
            "callout_mode": brief.get("callout_mode") or "overlay",
            "jobs": jobs,
            "note": (
                "See prompts/image_gen.md: img2img, else describe then txt2img. "
                "CAD is not lineart. Compose per-part SVG groups, persist vision-located "
                "anchors with base_svg_path, overlay SVG callouts into the composed file, "
                "then re-read the labeled figure and fix YAML if a leader hits the wrong part "
                "(max 2 rounds); do not invent ids."
            ),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report["jobs_path"] = str(out)
        report["job_count"] = len(jobs)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"STRUCTURE_LINEART_JOBS: {out}", file=sys.stderr)
        return 0

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
