# -*- coding: utf-8 -*-
"""按 StructureSchema.parts 把结构线稿拼成可分层编辑的 SVG。

每个部件一个子文件 ``parts/{视}_{id}.svg``，总图 ``<g id="part-{id}">`` 用相对路径引用。
粒度止于 StructureSchema 件号：一层一件，不把同一 id 拆成多块。
crop：子 SVG 用 viewBox 裁总装 PNG；image：子 SVG 包装该件小图；placeholder：虚线槽位。
总图不嵌整图 base64、不用 clipPath。总装/crop 视可在零件层下用相对 href 铺 id="view-source"。

  python tools/structure_lineart_compose.py --case-dir outputs/case
  python tools/structure_lineart_compose.py --case-dir outputs/case --check
  python tools/structure_lineart_compose.py --case-dir outputs/case --prepare-jobs
"""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any


def load_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text)
        except Exception as exc:
            raise ValueError(f"无法读取 YAML {path}: {exc}") from exc
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"拼装文件根须为对象: {path}")
    return data


def resolve_path(case_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (case_dir / path).resolve()


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue
            if i + 2 > len(data):
                break
            seg_len = int.from_bytes(data[i : i + 2], "big")
            if marker in {
                0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
            }:
                height = int.from_bytes(data[i + 3 : i + 5], "big")
                width = int.from_bytes(data[i + 5 : i + 7], "big")
                return width, height
            i += max(seg_len, 2)
    raise ValueError(f"仅支持 PNG/JPEG 尺寸读取: {path}")


def _find_schema(case_dir: Path, stem: str) -> Path | None:
    for name in (f"{stem}.yaml", f"{stem}.yml", f"{stem}.json"):
        p = case_dir / name
        if p.is_file():
            return p
    return None


def _parts_index(structure: dict[str, Any]) -> dict[str, str]:
    return {
        str(p.get("id") or "").strip(): str(p.get("name") or "").strip()
        for p in (structure.get("parts") or [])
        if isinstance(p, dict) and str(p.get("id") or "").strip()
    }


def _uncertain_ids(structure: dict[str, Any], compose: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for src in (structure, compose):
        for item in src.get("uncertain") or []:
            if isinstance(item, dict):
                pid = str(item.get("id") or "").strip()
            else:
                pid = str(item or "").strip()
            if pid:
                ids.add(pid)
    return ids


def _box(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, w, h = (float(v) for v in value)
    except (TypeError, ValueError):
        return None
    return x, y, w, h


def _box_ok(box: tuple[float, float, float, float], *, label: str, errors: list[str]) -> None:
    x, y, w, h = box
    if w <= 0 or h <= 0:
        errors.append(f"{label} 宽高须 > 0")
    for n, name in ((x, "x"), (y, "y"), (w, "w"), (h, "h")):
        if not 0.0 <= n <= 1.0:
            errors.append(f"{label} 的 {name} 超出 0..1")
    if x + w > 1.05 or y + h > 1.05:
        errors.append(f"{label} 超出画布（允许 0.05 余量）")


def _safe_token(raw: str, fallback: str) -> str:
    token = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw)[:60]
    return token or fallback


def _grid_slots(n: int) -> list[tuple[float, float, float, float]]:
    if n <= 0:
        return []
    cols = max(1, math.ceil(math.sqrt(n)))
    rows = math.ceil(n / cols)
    gap = 0.04
    cell_w = (1.0 - gap * (cols + 1)) / cols
    cell_h = (1.0 - gap * (rows + 1)) / rows
    slots: list[tuple[float, float, float, float]] = []
    for i in range(n):
        r, c = divmod(i, cols)
        slots.append((gap + c * (cell_w + gap), gap + r * (cell_h + gap), cell_w, cell_h))
    return slots


def validate_compose(
    compose: dict[str, Any],
    case_dir: Path,
    *,
    structure: dict[str, Any] | None = None,
    require_part_images: bool = True,
) -> list[str]:
    errors: list[str] = []
    if int(compose.get("version") or 0) != 1:
        errors.append("structure_lineart_compose.version 须为 1")
    views = compose.get("views") or []
    if not isinstance(views, list) or not views:
        errors.append("views 为空")
        return errors

    parts = _parts_index(structure or {})
    uncertain = _uncertain_ids(structure or {}, compose)
    canvas = compose.get("canvas") if isinstance(compose.get("canvas"), dict) else {}
    for key in ("width", "height"):
        if key in canvas:
            try:
                if float(canvas[key]) <= 0:
                    errors.append(f"canvas.{key} 须 > 0")
            except (TypeError, ValueError):
                errors.append(f"canvas.{key} 非数字")

    for vi, view in enumerate(views):
        if not isinstance(view, dict):
            errors.append(f"views[{vi}] 非法")
            continue
        layout = str(view.get("layout") or "assembly").strip().lower()
        if layout not in {"assembly", "exploded"}:
            errors.append(f"views[{vi}].layout 须为 assembly | exploded")
        output_raw = str(view.get("output_svg_path") or "").strip()
        if not output_raw:
            errors.append(f"views[{vi}] 缺少 output_svg_path")
        source_raw = str(view.get("source_image") or "").strip()
        source_path = resolve_path(case_dir, source_raw) if source_raw else None
        if source_raw and source_path is not None and not source_path.is_file():
            errors.append(f"views[{vi}] source_image 不存在: {source_raw}")

        items = view.get("parts") or []
        if not isinstance(items, list) or not items:
            errors.append(f"views[{vi}].parts 为空")
            continue
        seen: set[str] = set()
        for pi, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"views[{vi}].parts[{pi}] 非法")
                continue
            pid = str(item.get("id") or "").strip()
            name = str(item.get("name") or "").strip()
            loc = f"views[{vi}] 件号 {pid or '?'}"
            if not pid:
                errors.append(f"views[{vi}].parts[{pi}] 缺少 id")
                continue
            if pid in seen:
                errors.append(f"views[{vi}] 件号 {pid} 重复")
            seen.add(pid)
            if parts:
                if pid not in parts:
                    errors.append(f"{loc} 不在 structure_schema.parts")
                elif name and parts[pid] and name != parts[pid]:
                    errors.append(f"{loc} 名称与 StructureSchema 不一致")
            source = str(item.get("source") or "").strip().lower()
            if source not in {"crop", "image", "placeholder"}:
                errors.append(f"{loc} source 须为 crop | image | placeholder")
            if pid in uncertain and source in {"crop", "image"}:
                errors.append(f"{loc} 属于 uncertain，只能 placeholder")
            slot = _box(item.get("slot")) if item.get("slot") is not None else None
            if slot is not None:
                _box_ok(slot, label=f"{loc} slot", errors=errors)
            crop_box = _box(item.get("crop_box")) if item.get("crop_box") is not None else None
            if crop_box is not None:
                _box_ok(crop_box, label=f"{loc} crop_box", errors=errors)
            if source == "crop":
                if not source_raw or source_path is None or not source_path.is_file():
                    errors.append(f"{loc} source=crop 需要存在的 views[].source_image")
            if source == "image" and require_part_images:
                img_raw = str(item.get("image_path") or "").strip()
                if not img_raw:
                    errors.append(f"{loc} source=image 缺少 image_path")
                elif not resolve_path(case_dir, img_raw).is_file():
                    errors.append(f"{loc} 零件图不存在: {img_raw}")
    return errors


def _rel_href(from_file: Path, to_file: Path) -> str:
    return Path(os.path.relpath(to_file.resolve(), start=from_file.resolve().parent)).as_posix()


def _write_part_svg(
    path: Path,
    inner: str,
    *,
    width: float,
    height: float,
    view_box: str,
    title: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    w = max(width, 1.0)
    h = max(height, 1.0)
    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w:.2f}" height="{h:.2f}" viewBox="{view_box}">'
        ),
        f"<title>{html.escape(title)}</title>",
        inner,
        "</svg>",
    ]
    path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def _fit_in_slot(
    img_w: int, img_h: int, slot_w: float, slot_h: float
) -> tuple[float, float, float, float]:
    if img_w <= 0 or img_h <= 0:
        return 0.0, 0.0, slot_w, slot_h
    scale = min(slot_w / img_w, slot_h / img_h)
    dw, dh = img_w * scale, img_h * scale
    return (slot_w - dw) / 2.0, (slot_h - dh) / 2.0, dw, dh


def _resolved_parts(view: dict[str, Any]) -> list[dict[str, Any]]:
    items = [p for p in (view.get("parts") or []) if isinstance(p, dict)]
    layout = str(view.get("layout") or "assembly").strip().lower()
    missing = [i for i, p in enumerate(items) if _box(p.get("slot")) is None]
    grid = _grid_slots(len(items)) if layout == "exploded" and missing else []
    out: list[dict[str, Any]] = []
    for i, item in enumerate(items):
        row = dict(item)
        source = str(row.get("source") or "").strip().lower()
        if not source:
            source = "crop" if layout == "assembly" else "image"
            row["source"] = source
        slot = _box(row.get("slot"))
        crop_box = _box(row.get("crop_box"))
        if slot is None:
            if layout == "exploded" and grid:
                slot = grid[i]
            elif crop_box is not None:
                slot = crop_box
            else:
                slot = (0.0, 0.0, 1.0, 1.0)
            row["slot"] = list(slot)
        if source == "crop" and crop_box is None:
            row["crop_box"] = list(slot)
        try:
            row["_z"] = int(row.get("z_index") or i)
        except (TypeError, ValueError):
            row["_z"] = i
        row["_order"] = i
        out.append(row)
    out.sort(key=lambda x: (x["_z"], x["_order"]))
    return out


def _canvas_size(compose: dict[str, Any], view: dict[str, Any], case_dir: Path) -> tuple[int, int]:
    canvas = compose.get("canvas") if isinstance(compose.get("canvas"), dict) else {}
    try:
        width = int(float(canvas["width"])) if canvas.get("width") is not None else 0
        height = int(float(canvas["height"])) if canvas.get("height") is not None else 0
    except (TypeError, ValueError):
        width, height = 0, 0
    source_raw = str(view.get("source_image") or "").strip()
    if (width <= 0 or height <= 0) and source_raw:
        src = resolve_path(case_dir, source_raw)
        if src.is_file():
            return image_size(src)
    if width <= 0:
        width = 1600
    if height <= 0:
        height = 1200
    return width, height


def _image_href(
    href: str,
    *,
    x: float | None = None,
    y: float | None = None,
    width: float,
    height: float,
    preserve: str = "none",
) -> str:
    pos = ""
    if x is not None and y is not None:
        pos = f'x="{x:.2f}" y="{y:.2f}" '
    escaped = html.escape(href)
    ratio = html.escape(preserve)
    return (
        f'<image {pos}width="{width:.2f}" height="{height:.2f}" '
        f'preserveAspectRatio="{ratio}" href="{escaped}" xlink:href="{escaped}"/>'
    )


def _should_embed_source(view: dict[str, Any], source_path: Path | None) -> bool:
    """总装/剖视，或任何 crop 开窗视：铺整张轮廓，避免零件窗拼不全把整机裁掉。"""
    if source_path is None or not source_path.is_file():
        return False
    layout = str(view.get("layout") or "assembly").strip().lower()
    if layout != "exploded":
        return True
    return any(
        str(item.get("source") or "").strip().lower() == "crop"
        for item in (view.get("parts") or [])
        if isinstance(item, dict)
    )


def render_view(compose: dict[str, Any], view: dict[str, Any], case_dir: Path) -> Path:
    width, height = _canvas_size(compose, view, case_dir)
    bg = str((compose.get("canvas") or {}).get("background") or "#ffffff")
    output_path = resolve_path(case_dir, str(view["output_svg_path"]))
    source_raw = str(view.get("source_image") or "").strip()
    source_path = resolve_path(case_dir, source_raw) if source_raw else None
    src_w = src_h = 0
    if source_path is not None and source_path.is_file():
        src_w, src_h = image_size(source_path)

    safe_view = _safe_token(str(view.get("view_name") or "view"), "view")
    parts_dir = output_path.parent / "parts"
    parts = _resolved_parts(view)
    body: list[str] = []
    if _should_embed_source(view, source_path) and source_path is not None:
        href = _rel_href(output_path, source_path)
        body.append(
            f'<g id="view-source" data-source="source_image" '
            f'inkscape:groupmode="layer" inkscape:label="source">'
            f'<title>source</title>'
            f"{_image_href(href, width=float(width), height=float(height), preserve='xMidYMid meet')}"
            "</g>"
        )
    for item in parts:
        pid = str(item["id"])
        token = _safe_token(pid, "part")
        gid = f"part-{token}"
        title_plain = f"{pid} {item.get('name') or ''}".strip()
        title = html.escape(title_plain)
        label = html.escape(str(item.get("name") or pid))
        sx, sy, sw, sh = _box(item["slot"]) or (0.0, 0.0, 1.0, 1.0)
        x, y, w, h = sx * width, sy * height, sw * width, sh * height
        source = str(item.get("source") or "placeholder")
        child_path = parts_dir / f"{safe_view}_{token}.svg"
        ox = oy = 0.0
        dw, dh = w, h
        wrote_child = False
        if source == "crop" and source_path is not None and source_path.is_file() and src_w and src_h:
            cx, cy, cw, ch = _box(item.get("crop_box")) or (sx, sy, sw, sh)
            rx, ry, rw, rh = cx * src_w, cy * src_h, cw * src_w, ch * src_h
            rw, rh = max(rw, 0.01), max(rh, 0.01)
            _write_part_svg(
                child_path,
                _image_href(_rel_href(child_path, source_path), width=float(src_w), height=float(src_h)),
                width=rw,
                height=rh,
                view_box=f"{rx:.2f} {ry:.2f} {rw:.2f} {rh:.2f}",
                title=title_plain,
            )
            wrote_child = True
        elif source == "image":
            img_raw = str(item.get("image_path") or "").strip()
            img_path = resolve_path(case_dir, img_raw) if img_raw else None
            if img_path is not None and img_path.is_file():
                iw, ih = image_size(img_path)
                _write_part_svg(
                    child_path,
                    _image_href(_rel_href(child_path, img_path), width=float(iw), height=float(ih)),
                    width=float(iw),
                    height=float(ih),
                    view_box=f"0 0 {iw} {ih}",
                    title=title_plain,
                )
                ox, oy, dw, dh = _fit_in_slot(iw, ih, w, h)
                wrote_child = True
        if not wrote_child:
            inner_w, inner_h = max(w, 1.0), max(h, 1.0)
            _write_part_svg(
                child_path,
                (
                    f'<rect x="1" y="1" width="{max(inner_w - 2, 1):.2f}" '
                    f'height="{max(inner_h - 2, 1):.2f}" fill="#f7f7f7" '
                    f'stroke="#111" stroke-width="1.5" stroke-dasharray="8 5"/>'
                ),
                width=inner_w,
                height=inner_h,
                view_box=f"0 0 {inner_w:.2f} {inner_h:.2f}",
                title=title_plain,
            )
        href = _rel_href(output_path, child_path)
        body.append(
            f'<g id="{html.escape(gid)}" data-part-id="{html.escape(pid)}" '
            f'data-source="{html.escape(source)}" '
            f'inkscape:groupmode="layer" inkscape:label="{label}">'
            f"<title>{title}</title>"
            f"{_image_href(href, x=x + ox, y=y + oy, width=dw, height=dh)}"
            "</g>"
        )

    svg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
            f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        ),
        f'<rect id="canvas-bg" width="{width}" height="{height}" fill="{html.escape(bg)}"/>',
        *body,
        "</svg>",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(svg) + "\n", encoding="utf-8")
    return output_path


def build_part_jobs(compose: dict[str, Any], case_dir: Path) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for view in compose.get("views") or []:
        if not isinstance(view, dict):
            continue
        view_name = str(view.get("view_name") or "view")
        safe_view = _safe_token(view_name, "view")
        layout = str(view.get("layout") or "assembly").strip().lower()
        source_raw = str(view.get("source_image") or "").strip()
        refs = []
        if source_raw:
            src = resolve_path(case_dir, source_raw)
            if src.is_file():
                refs.append(str(src))
        for item in _resolved_parts(view):
            source = str(item.get("source") or "").strip().lower()
            if source != "image":
                continue
            img_raw = str(item.get("image_path") or "").strip()
            pid = str(item["id"])
            if not img_raw:
                img_raw = f"lineart_assist/parts/{safe_view}_{_safe_token(pid, 'p')}.png"
            dest = resolve_path(case_dir, img_raw)
            if dest.is_file():
                continue
            name = str(item.get("name") or "")
            jobs.append(
                {
                    "view_name": view_name,
                    "layout": layout,
                    "part_id": pid,
                    "name": name,
                    "image_path": img_raw,
                    "absolute_output_path": str(dest),
                    "reference_images": refs,
                    "gen_prompt": (
                        f"Black-and-white patent-style STRUCTURE line art of ONE isolated part only: "
                        f"{pid} {name}. White background, no other parts, no part numbers, "
                        f"no leader lines, no logos, no photoreal shading. Match the named part; "
                        f"do not invent unseen internals."
                    ),
                    "host_hint": (
                        "Generate a single-part contour PNG at image_path. Then re-run "
                        "structure_lineart_compose.py without --prepare-jobs."
                    ),
                }
            )
    return jobs


def run_check(case_dir: Path, *, require_part_images: bool = True) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "errors": []}
    compose_path = _find_schema(case_dir, "structure_lineart_compose")
    struct_path = _find_schema(case_dir, "structure_schema")
    if not compose_path:
        result["errors"].append("缺少 structure_lineart_compose.yaml；请先按 structure_lineart_compose.md 填写")
        return result
    if not struct_path:
        result["errors"].append("缺少 structure_schema；请先按 fill_structure_schema.md 填写")
        return result
    compose = load_data(compose_path)
    structure = load_data(struct_path)
    errors = validate_compose(
        compose, case_dir, structure=structure, require_part_images=require_part_images
    )
    result["errors"] = errors
    result["compose_path"] = str(compose_path)
    result["structure_path"] = str(struct_path)
    result["ok"] = not errors
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按部件槽位拼装可分层编辑的结构线稿 SVG")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--layout-file", type=Path, help="默认案件目录 structure_lineart_compose.yaml")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--prepare-jobs", action="store_true", help="只写出缺文件的单件生图 jobs")
    args = parser.parse_args(argv)

    case_dir = args.case_dir.resolve()
    if not case_dir.is_dir():
        print(json.dumps({"ok": False, "errors": [f"不是目录: {case_dir}"]}, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.layout_file:
        compose_path = args.layout_file.resolve()
        struct_path = _find_schema(case_dir, "structure_schema")
        structure = load_data(struct_path) if struct_path else None
        try:
            compose = load_data(compose_path)
        except Exception as exc:
            print(json.dumps({"ok": False, "errors": [str(exc)]}, ensure_ascii=False), file=sys.stderr)
            return 2
        errors = validate_compose(
            compose,
            case_dir,
            structure=structure,
            require_part_images=not args.prepare_jobs,
        )
        report = {
            "ok": not errors,
            "errors": errors,
            "compose_path": str(compose_path),
        }
    else:
        report = run_check(case_dir, require_part_images=not args.prepare_jobs)
        if report.get("ok"):
            compose = load_data(Path(report["compose_path"]))
        else:
            compose = {}

    if args.check or not report.get("ok"):
        print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr if not report.get("ok") else sys.stdout)
        if not report.get("ok"):
            print("STRUCTURE_LINEART_COMPOSE: check_failed", file=sys.stderr)
            return 2
        if args.check and not args.prepare_jobs:
            return 0

    if args.prepare_jobs:
        jobs = build_part_jobs(compose, case_dir)
        out = case_dir / "lineart_assist" / "structure_lineart_compose_jobs.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ok": True, "jobs": jobs, "count": len(jobs)}
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report["jobs_path"] = str(out)
        report["job_count"] = len(jobs)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"STRUCTURE_LINEART_COMPOSE: {out}", file=sys.stderr)
        return 0

    outputs: list[str] = []
    part_svgs: list[str] = []
    for view in compose.get("views") or []:
        if not isinstance(view, dict):
            continue
        out = render_view(compose, view, case_dir)
        outputs.append(str(out))
        safe_view = _safe_token(str(view.get("view_name") or "view"), "view")
        parts_dir = out.parent / "parts"
        if parts_dir.is_dir():
            part_svgs.extend(str(p) for p in sorted(parts_dir.glob(f"{safe_view}_*.svg")))
    report["outputs"] = outputs
    report["part_svgs"] = part_svgs
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"STRUCTURE_LINEART_COMPOSE: composed={len(outputs)} parts={len(part_svgs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
