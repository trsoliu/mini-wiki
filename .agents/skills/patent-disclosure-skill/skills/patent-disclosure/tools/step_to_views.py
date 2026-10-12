# -*- coding: utf-8 -*-
"""STEP (.step/.stp) -> multi-view SVG (+ PNG via Cairo or svg_screenshot.py).

Default OFF: pass ``--enable-step-parse`` (or ``PATENT_SKILL_STEP_PARSE=1``).
Run via cad-env (Python 3.10-3.12). PNG backends: cairosvg, else Playwright
(svg_screenshot.py). matplotlib is not used on this path.

  python tools/cad_venv.py
  python tools/run_step_to_views.py --enable-step-parse -i model.step -o outputs/case/cad_views
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from cad_formats import is_step

# 标准工程视图：名称 → CadQuery SVG projectionDir
DEFAULT_VIEWS: dict[str, tuple[float, float, float]] = {
    "iso": (1.0, 1.0, 1.0),
    "front": (0.0, -1.0, 0.0),
    "top": (0.0, 0.0, 1.0),
    "right": (1.0, 0.0, 0.0),
}

ENABLE_ENV = "PATENT_SKILL_STEP_PARSE"


def _cairosvg_usable() -> tuple[bool, str]:
    """cairosvg 依赖系统 Cairo；Windows 常缺 DLL，此时不算硬失败。"""
    try:
        import cairosvg

        # 触发一次底层 cairo 加载（仅 import 有时不够）
        getattr(cairosvg, "svg2png")
        import cairocffi  # type: ignore

        return True, getattr(cairosvg, "__version__", "unknown")
    except Exception as e:
        return False, str(e)


def deps_status() -> dict[str, Any]:
    missing: list[str] = []
    versions: dict[str, str] = {}
    hints: list[str] = []
    try:
        import cadquery as cq

        versions["cadquery"] = getattr(cq, "__version__", "unknown")
    except Exception as e:
        missing.append(f"cadquery ({e})")

    cairo_ok, cairo_info = _cairosvg_usable()
    if cairo_ok:
        versions["cairosvg"] = cairo_info
    else:
        hints.append(
            "cairosvg/Cairo unavailable; keep SVG and rasterize with svg_screenshot.py "
            f"(headless browser). ({cairo_info})"
        )

    return {
        "ok": not missing,
        "missing": missing,
        "versions": versions,
        "hints": hints,
        "install": "python tools/bootstrap_cad_venv.py",
        "png": "cairosvg" if cairo_ok else "svg_or_browser",
    }


def parse_enabled(cli_flag: bool) -> bool:
    if cli_flag:
        return True
    return os.environ.get(ENABLE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def _safe_stem(path: Path) -> str:
    s = path.stem
    out = "".join(c if c.isalnum() or c in "-_" else "_" for c in s)
    return (out or "model")[:80]


def extract_assembly_tree(step_path: Path) -> dict[str, Any]:
    """尽力从 STEP 取装配标签；失败则回退为单节点 + solids 计数。"""
    tree: dict[str, Any] = {
        "source": str(step_path.resolve()),
        "parts": [],
        "uncertain": [],
        "method": "unknown",
    }
    try:
        from OCP.IFSelect import IFSelect_RetDone
        from OCP.STEPCAFControl import STEPCAFControl_Reader
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.TDataStd import TDataStd_Name
        from OCP.TDF import TDF_Label, TDF_LabelSequence
        from OCP.TDocStd import TDocStd_Document
        from OCP.XCAFApp import XCAFApp_Application
        from OCP.XCAFDoc import XCAFDoc_DocumentTool
    except Exception as e:
        tree["uncertain"].append(f"OCP/XCAF 不可用: {e}")
        return _fallback_solids_tree(step_path, tree)

    try:
        app = XCAFApp_Application.GetApplication_s()
        doc = TDocStd_Document(TCollection_ExtendedString("MDTV-CAF"))
        app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
        reader = STEPCAFControl_Reader()
        reader.SetNameMode(True)
        status = reader.ReadFile(str(step_path))
        if status != IFSelect_RetDone:
            tree["uncertain"].append("STEPCAF ReadFile 未成功")
            return _fallback_solids_tree(step_path, tree)
        if not reader.Transfer(doc):
            tree["uncertain"].append("STEPCAF Transfer 失败")
            return _fallback_solids_tree(step_path, tree)

        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        labels = TDF_LabelSequence()
        shape_tool.GetFreeShapes(labels)
        parts: list[dict[str, Any]] = []

        def _label_name(lab: TDF_Label) -> str:
            attr = TDataStd_Name()
            if lab.FindAttribute(TDataStd_Name.GetID_s(), attr):
                return attr.Get().ToExtString()
            return ""

        for i in range(1, labels.Length() + 1):
            lab = labels.Value(i)
            name = _label_name(lab) or f"Shape_{i}"
            parts.append({"id": str(i), "name": name, "label_path": name})
            children = TDF_LabelSequence()
            if shape_tool.GetComponents(lab, children):
                for j in range(1, children.Length() + 1):
                    clab = children.Value(j)
                    cname = _label_name(clab) or f"{name}_child_{j}"
                    parts.append(
                        {
                            "id": f"{i}.{j}",
                            "name": cname,
                            "parent": str(i),
                            "label_path": f"{name}/{cname}",
                        }
                    )

        tree["parts"] = parts or [{"id": "1", "name": step_path.stem, "label_path": step_path.stem}]
        tree["method"] = "xcaf"
        if not parts:
            tree["uncertain"].append("XCAF 未枚举到子件，仅有自由形状根")
        return tree
    except Exception as e:
        tree["uncertain"].append(f"XCAF 解析异常: {e}")
        return _fallback_solids_tree(step_path, tree)


def _fallback_solids_tree(step_path: Path, tree: dict[str, Any]) -> dict[str, Any]:
    try:
        import cadquery as cq
        from OCP.TopAbs import TopAbs_SOLID
        from OCP.TopExp import TopExp_Explorer

        shape = cq.importers.importStep(str(step_path))
        wrapped = shape.val().wrapped
        exp = TopExp_Explorer(wrapped, TopAbs_SOLID)
        n = 0
        parts = []
        while exp.More():
            n += 1
            parts.append({"id": str(n), "name": f"Solid_{n}", "label_path": f"Solid_{n}"})
            exp.Next()
        if not parts:
            parts = [{"id": "1", "name": step_path.stem, "label_path": step_path.stem}]
            tree["uncertain"].append("未拆出 SOLID，按整模一件处理")
        tree["parts"] = parts
        tree["method"] = "solid_count"
        tree["solid_count"] = n
    except Exception as e:
        tree["parts"] = [{"id": "1", "name": step_path.stem, "label_path": step_path.stem}]
        tree["method"] = "stem_only"
        tree["uncertain"].append(f"无法计数 SOLID: {e}")
    return tree


def _svg_to_png_cairo(svg_path: Path, png_path: Path) -> None:
    import cairosvg

    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))


def _host_python() -> str | None:
    env_py = os.environ.get('PATENT_SKILL_HOST_PYTHON', '').strip()
    if env_py and Path(env_py).is_file():
        return env_py
    try:
        from cad_venv import host_python

        hp = host_python()
        if hp and Path(hp).is_file():
            return hp
    except Exception:
        pass
    return sys.executable


def _rasterize_svgs_browser(svg_paths: list[Path]) -> dict[str, Any]:
    if not svg_paths:
        return {'ok': True, 'converted': []}
    host = _host_python()
    if not host:
        return {'ok': False, 'error': 'no_host_python'}
    views_dir = svg_paths[0].parent
    cmd = [host, str(_SHARED / 'svg_screenshot.py'), '--dir', str(views_dir)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:
        return {'ok': False, 'error': str(e)}
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {'ok': proc.returncode == 0}
    except json.JSONDecodeError:
        return {'ok': proc.returncode == 0, 'raw': (proc.stdout or '')[-1000:]}


def render_views(
    step_path: Path,
    out_dir: Path,
    *,
    views: dict[str, tuple[float, float, float]] | None = None,
    stem: str | None = None,
) -> list[dict[str, Any]]:
    import cadquery as cq

    views = views or DEFAULT_VIEWS
    stem = stem or _safe_stem(step_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    shape = cq.importers.importStep(str(step_path))
    cairo_ok, _ = _cairosvg_usable()
    results: list[dict[str, Any]] = []

    for name, direction in views.items():
        svg_path = out_dir / f'{stem}_{name}.svg'
        png_path = out_dir / f'{stem}_{name}.png'
        cq.exporters.export(
            shape,
            str(svg_path),
            cq.exporters.ExportTypes.SVG,
            opt={
                'projectionDir': direction,
                'showAxes': False,
                'showHidden': False,
                'strokeWidth': 0.2,
            },
        )
        png_backend = 'none'
        png_written = False
        if cairo_ok:
            try:
                _svg_to_png_cairo(svg_path, png_path)
                png_written = png_path.is_file()
                png_backend = 'cairosvg'
            except Exception:
                png_written = False
        role = 'assembly' if name == 'iso' else 'ortho'
        results.append(
            {
                'name': name,
                'role': role,
                'png': str(png_path.resolve()) if png_written else '',
                'svg': str(svg_path.resolve()),
                'projectionDir': list(direction),
                'png_backend': png_backend,
            }
        )

    pending = [Path(r['svg']) for r in results if not r.get('png')]
    if pending:
        shot = _rasterize_svgs_browser(pending)
        converted = {item.get('svg'): item.get('png') for item in (shot.get('converted') or [])}
        for rec in results:
            if rec.get('png'):
                continue
            png = converted.get(rec['svg'])
            if png and Path(str(png)).is_file():
                rec['png'] = str(Path(str(png)).resolve())
                rec['png_backend'] = 'playwright'
    return results


def build_figure_plan_seed(
    *,
    view_records: list[dict[str, Any]],
    out_path: Path,
    theme_summary: str,
    schema_ref: str = "structure_schema.yaml",
    patent_type: str = "utility_model",
) -> dict[str, Any]:
    """CAD views are material only: kind=cad, never disclosure lineart."""
    figures: list[dict[str, Any]] = []
    for rec in view_records:
        figures.append(
            {
                "fig": None,
                "role": "reference",
                "path": rec.get("png") or rec.get("svg") or "",
                "covers": [],
                "kind": "cad",
                "relevance": 0,
                "quality": 0,
                "score": 0,
                "use_in_disclosure": False,
                "reason": (
                    f"STEP view {rec.get('name')}: CAD projection is material only; "
                    "not lineart; never embed in disclosure."
                ),
                "relates_to": [],
                "cad_view": rec.get("name") or "",
            }
        )

    plan = {
        "$schema": "figure_plan",
        "version": 1,
        "patent_type": patent_type,
        "theme_summary": theme_summary or "STEP 自动多视角（待人工确认主题）",
        "schema_ref": schema_ref,
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "figures": figures,
        "notes": [
            "本文件由 step_to_views.py 生成，属草稿。CAD 投影不得入文、不得当线稿。",
            "填表后须识图重评 relevance / quality / score；分数够才可作图生图参考。",
            "局部细节图需另增材料或人工指定 crop；自动视图仅含投影。",
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(out_path, plan)
    return plan


def build_structure_seed(tree: dict[str, Any], out_path: Path) -> dict[str, Any]:
    parts = []
    for p in tree.get("parts") or []:
        parts.append(
            {
                "id": str(p.get("id", "")),
                "name": p.get("name") or "",
                "shape": "unknown",
                "material_hint": "unknown",
            }
        )
    if not parts:
        parts = [{"id": "1", "name": "unknown", "shape": "unknown", "material_hint": "unknown"}]
    seed = {
        "$schema": "structure.schema",
        "version": 1,
        "mode": "disclosure",
        "source_images": [],
        "parts": parts,
        "relations": [],
        "spatial": [],
        "function_of_structure": [],
        "delta_hypothesis": [],
        "uncertain": list(tree.get("uncertain") or [])
        + [
            "装配树来自 STEP 自动解析，件名可能为特征名/空名；须对照视图修订",
            "连接关系未从 STEP 推断，须识图后填写 relations",
        ],
        "not_utility_model_signals": [],
        "cad_assembly_method": tree.get("method"),
    }
    _write_yaml(out_path, seed)
    return seed


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore

        path.write_text(
            yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    except Exception:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if path.suffix.lower() in {".yaml", ".yml"}:
            # 无 PyYAML 时仍用请求的文件名，内容为 JSON（Agent 可读）
            pass


def run_convert(
    step_path: Path,
    out_dir: Path,
    *,
    write_assembly: bool = True,
    write_figure_plan: bool = True,
    write_structure_seed: bool = True,
    theme_summary: str = "",
) -> dict[str, Any]:
    if not step_path.is_file():
        raise FileNotFoundError(step_path)
    if not is_step(step_path):
        raise ValueError(f"不是 .step/.stp: {step_path}")

    status = deps_status()
    if not status["ok"]:
        raise RuntimeError(
            "缺少 STEP 解析依赖: "
            + "; ".join(status["missing"])
            + f"。请先: {status['install']}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_stem(step_path)
    views_dir = out_dir / "views"
    view_records = render_views(step_path, views_dir, stem=stem)

    result: dict[str, Any] = {
        "step": str(step_path.resolve()),
        "out_dir": str(out_dir.resolve()),
        "views": view_records,
        "artifacts": {},
    }

    tree = extract_assembly_tree(step_path)
    if write_assembly:
        asm_path = out_dir / "assembly_tree.yaml"
        _write_yaml(asm_path, tree)
        result["artifacts"]["assembly_tree"] = str(asm_path.resolve())
        result["assembly_tree"] = tree

    if write_structure_seed:
        struct_path = out_dir / "structure_schema.seed.yaml"
        build_structure_seed(tree, struct_path)
        result["artifacts"]["structure_schema_seed"] = str(struct_path.resolve())

    if write_figure_plan:
        fp_path = out_dir / "figure_plan.seed.yaml"
        build_figure_plan_seed(
            view_records=view_records,
            out_path=fp_path,
            theme_summary=theme_summary or f"STEP:{step_path.name}",
        )
        result["artifacts"]["figure_plan_seed"] = str(fp_path.resolve())

    manifest = out_dir / "step_to_views_manifest.json"
    manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["artifacts"]["manifest"] = str(manifest.resolve())
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="STEP → 多视角 PNG + 装配树/figure_plan 种子（默认关闭，需 --enable-step-parse）"
    )
    p.add_argument("--check-deps", action="store_true", help="仅检查依赖，不转换")
    p.add_argument(
        "--enable-step-parse",
        action="store_true",
        help="显式开启（或设环境变量 PATENT_SKILL_STEP_PARSE=1）",
    )
    p.add_argument("-i", "--input", help="输入 .step / .stp")
    p.add_argument("-o", "--out-dir", help="输出目录（建议 outputs/{案件}/cad_views/）")
    p.add_argument("--theme", default="", help="figure_plan theme_summary")
    p.add_argument("--no-assembly", action="store_true")
    p.add_argument("--no-figure-plan", action="store_true")
    p.add_argument("--no-structure-seed", action="store_true")
    args = p.parse_args(argv)

    if args.check_deps:
        st = deps_status()
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return 0 if st["ok"] else 2

    if not parse_enabled(args.enable_step_parse):
        print(
            json.dumps(
                {
                    "error": "step_parse_disabled",
                    "message": (
                        "STEP 解析默认关闭。请经用户确认后使用 --enable-step-parse，"
                        f"或设置 {ENABLE_ENV}=1。"
                    ),
                    "install": "python tools/run_step_to_views.py --enable-step-parse -i <file.step> -o <outdir>",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 3

    if not args.input or not args.out_dir:
        p.error("转换模式需要 -i/--input 与 -o/--out-dir（或改用 --check-deps）")

    try:
        result = run_convert(
            Path(args.input),
            Path(args.out_dir),
            write_assembly=not args.no_assembly,
            write_figure_plan=not args.no_figure_plan,
            write_structure_seed=not args.no_structure_seed,
            theme_summary=args.theme,
        )
    except Exception as e:
        print(json.dumps({"error": type(e).__name__, "message": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"STEP_TO_VIEWS_OK: {result['out_dir']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
