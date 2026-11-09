# -*- coding: utf-8 -*-
"""叠标几何校正：序号推到外轮廓留白，引出线末端吸到墨线。

大模型给的归一化坐标经常落在 crop 窗角——窗里仍是剖面线或空腔。
本模块读原图亮度，从画布边洪水填充得到真正的「图外留白」，再移动 label / 吸附 anchor。
"""
from __future__ import annotations

import math
import re
import struct
import sys
import zlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

INK_LUMA = 240
MAX_GRID = 360
_IMAGE_ATTR_RE = re.compile(
    r'<g\b([^>]*data-part-id="([^"]+)"[^>]*)>.*?<image\b([^>]*)/?>',
    re.IGNORECASE | re.DOTALL,
)
_ATTR_RE = re.compile(r'\b(x|y|width|height|href|xlink:href)="([^"]*)"', re.I)
_SOURCE_HREF_RE = re.compile(
    r'id="view-source"[^>]*>.*?<image\b([^>]*)>',
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class Occupancy:
    width: int
    height: int
    ink: bytearray
    exterior: bytearray

    def _i(self, x: int, y: int) -> int:
        return y * self.width + x

    def in_bounds(self, x: float, y: float) -> bool:
        return 0 <= int(x) < self.width and 0 <= int(y) < self.height

    def is_ink(self, x: float, y: float) -> bool:
        xi, yi = int(round(x)), int(round(y))
        if not self.in_bounds(xi, yi):
            return False
        return self.ink[self._i(xi, yi)] == 1

    def is_exterior(self, x: float, y: float) -> bool:
        xi, yi = int(round(x)), int(round(y))
        if not self.in_bounds(xi, yi):
            return True
        return self.exterior[self._i(xi, yi)] == 1


def decode_png_luma(path: Path) -> tuple[int, int, bytes]:
    """8 位非隔行 PNG → 灰度。不依赖 Pillow。"""
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not png")
    pos = 8
    raw = b""
    width = height = bit = color = 0
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        tag = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, bit, color = struct.unpack(">IIBB", chunk[:10])
            interlace = chunk[12]
            if bit != 8 or interlace != 0 or color not in {0, 2, 4, 6}:
                raise ValueError("unsupported png")
        elif tag == b"IDAT":
            raw += chunk
        elif tag == b"IEND":
            break
    if width <= 0 or height <= 0:
        raise ValueError("bad png header")
    buf = zlib.decompress(raw)
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    stride = width * channels
    rows: list[bytearray] = []
    i = 0
    prev = bytearray(stride)
    for _ in range(height):
        filt = buf[i]
        i += 1
        scan = bytearray(buf[i : i + stride])
        i += stride
        if filt == 1:
            for x in range(stride):
                left = scan[x - channels] if x >= channels else 0
                scan[x] = (scan[x] + left) & 255
        elif filt == 2:
            for x in range(stride):
                scan[x] = (scan[x] + prev[x]) & 255
        elif filt == 3:
            for x in range(stride):
                left = scan[x - channels] if x >= channels else 0
                scan[x] = (scan[x] + ((left + prev[x]) // 2)) & 255
        elif filt == 4:

            def paeth(a: int, b: int, c: int) -> int:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    return a
                return b if pb <= pc else c

            for x in range(stride):
                a = scan[x - channels] if x >= channels else 0
                b = prev[x]
                c = prev[x - channels] if x >= channels else 0
                scan[x] = (scan[x] + paeth(a, b, c)) & 255
        elif filt != 0:
            raise ValueError("png filter")
        rows.append(scan)
        prev = scan
    out = bytearray(width * height)
    for y, scan in enumerate(rows):
        for x in range(width):
            if channels == 1:
                out[y * width + x] = scan[x]
            else:
                o = x * channels
                out[y * width + x] = (scan[o] * 299 + scan[o + 1] * 587 + scan[o + 2] * 114) // 1000
    return width, height, bytes(out)


def luma_from_image(path: Path) -> tuple[int, int, bytes]:
    suffix = path.suffix.lower()
    data = path.read_bytes()
    if data.startswith(b"\x89PNG"):
        return decode_png_luma(path)
    try:
        from PIL import Image  # type: ignore

        im = Image.open(path).convert("L")
        return im.size[0], im.size[1], im.tobytes()
    except Exception as exc:
        raise ValueError(f"无法读取亮度图 {path}: {exc}") from exc


def occupancy_from_luma(
    width: int,
    height: int,
    luma: bytes,
    *,
    threshold: int = INK_LUMA,
    max_grid: int = MAX_GRID,
) -> Occupancy:
    if width <= 0 or height <= 0 or len(luma) < width * height:
        raise ValueError("bad luma")
    scale = max(width, height) / float(max_grid) if max(width, height) > max_grid else 1.0
    gw = max(1, int(round(width / scale)))
    gh = max(1, int(round(height / scale)))
    ink = bytearray(gw * gh)
    for gy in range(gh):
        sy = min(height - 1, int(gy * height / gh))
        for gx in range(gw):
            sx = min(width - 1, int(gx * width / gw))
            if luma[sy * width + sx] < threshold:
                ink[gy * gw + gx] = 1
    # 剖面线有缝，先膨胀再洪水填充，否则「外轮廓留白」会漏进零件内部。
    closed = _dilate(ink, gw, gh, radius=3)
    exterior = _flood_exterior(gw, gh, closed)
    return Occupancy(gw, gh, ink, exterior)


def _dilate(ink: bytearray, w: int, h: int, radius: int) -> bytearray:
    if radius <= 0:
        return bytearray(ink)
    out = bytearray(ink)
    r2 = radius * radius
    for i, bit in enumerate(ink):
        if bit != 1:
            continue
        x, y = i % w, i // w
        for dy in range(-radius, radius + 1):
            yy = y + dy
            if yy < 0 or yy >= h:
                continue
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > r2:
                    continue
                xx = x + dx
                if 0 <= xx < w:
                    out[yy * w + xx] = 1
    return out


def _flood_exterior(w: int, h: int, ink: bytearray) -> bytearray:
    ext = bytearray(w * h)
    q: deque[int] = deque()

    def offer(i: int) -> None:
        if ink[i] or ext[i]:
            return
        ext[i] = 1
        q.append(i)

    for x in range(w):
        offer(x)
        offer((h - 1) * w + x)
    for y in range(h):
        offer(y * w)
        offer(y * w + (w - 1))
    while q:
        i = q.popleft()
        x, y = i % w, i // w
        if x > 0:
            offer(i - 1)
        if x + 1 < w:
            offer(i + 1)
        if y > 0:
            offer(i - w)
        if y + 1 < h:
            offer(i + w)
    return ext


def map_to_occ(occ: Occupancy, x: float, y: float, width: int, height: int) -> tuple[float, float]:
    return x * occ.width / max(width, 1), y * occ.height / max(height, 1)


def map_from_occ(occ: Occupancy, x: float, y: float, width: int, height: int) -> tuple[float, float]:
    return x * width / max(occ.width, 1), y * height / max(occ.height, 1)


def parse_part_slots(svg_text: str) -> dict[str, tuple[float, float, float, float]]:
    slots: dict[str, tuple[float, float, float, float]] = {}
    for match in _IMAGE_ATTR_RE.finditer(svg_text):
        pid = match.group(2).strip()
        attrs = {k.lower(): v for k, v in _ATTR_RE.findall(match.group(3))}
        try:
            slots[pid] = (
                float(attrs.get("x") or 0),
                float(attrs.get("y") or 0),
                float(attrs.get("width") or 0),
                float(attrs.get("height") or 0),
            )
        except ValueError:
            continue
    return slots


def source_image_href(svg_text: str) -> str | None:
    match = _SOURCE_HREF_RE.search(svg_text)
    if not match:
        return None
    attrs = {k.lower(): v for k, v in _ATTR_RE.findall(match.group(1))}
    return (attrs.get("href") or attrs.get("xlink:href") or "").strip() or None


def _disk_exterior(occ: Occupancy, x: float, y: float, radius: float) -> bool:
    if radius <= 0:
        return occ.is_exterior(x, y)
    steps = 12
    for k in range(steps):
        ang = 2 * math.pi * k / steps
        if not occ.is_exterior(x + math.cos(ang) * radius, y + math.sin(ang) * radius):
            return False
    return occ.is_exterior(x, y) and not occ.is_ink(x, y)


def _nearest_ink(
    occ: Occupancy,
    hint: tuple[float, float],
    box: tuple[float, float, float, float] | None,
) -> tuple[float, float] | None:
    hx, hy = hint
    if occ.is_ink(hx, hy):
        return hx, hy
    if box:
        x0, y0, bw, bh = box
        x1, y1 = x0 + bw, y0 + bh
    else:
        x0, y0, x1, y1 = 0.0, 0.0, float(occ.width - 1), float(occ.height - 1)
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(occ.width - 1, int(x1))
    y1 = min(occ.height - 1, int(y1))
    best: tuple[float, float] | None = None
    best_d = 1e18
    for y in range(y0, y1 + 1):
        row = y * occ.width
        for x in range(x0, x1 + 1):
            if occ.ink[row + x] != 1:
                continue
            d = (x - hx) ** 2 + (y - hy) ** 2
            if d < best_d:
                best_d = d
                best = (float(x), float(y))
    return best


def place_label(
    occ: Occupancy,
    anchor: tuple[float, float],
    current: tuple[float, float],
    others: Iterable[tuple[float, float]],
    *,
    font_r: float,
    min_sep: float,
) -> tuple[float, float]:
    if _disk_exterior(occ, current[0], current[1], font_r) and math.dist(current, anchor) >= font_r * 1.6:
        if all(math.dist(current, o) >= min_sep for o in others):
            return current
    cx, cy = occ.width / 2.0, occ.height / 2.0
    base = math.atan2(anchor[1] - cy, anchor[0] - cx)
    distances = [
        font_r * 2.4,
        font_r * 3.6,
        font_r * 5.0,
        max(occ.width, occ.height) * 0.08,
        max(occ.width, occ.height) * 0.14,
        max(occ.width, occ.height) * 0.20,
        max(occ.width, occ.height) * 0.28,
    ]
    best: tuple[float, float] | None = None
    best_s = 1e18
    pad = font_r * 2.4
    for dist in distances:
        for k in range(16):
            ang = base + k * math.pi / 8.0
            lx = anchor[0] + math.cos(ang) * dist
            ly = anchor[1] + math.sin(ang) * dist
            if not (-pad <= lx <= occ.width + pad and -pad <= ly <= occ.height + pad):
                continue
            if not _disk_exterior(occ, lx, ly, font_r):
                continue
            if any(math.dist((lx, ly), o) < min_sep for o in others):
                continue
            score = dist + (0 if 0 <= lx < occ.width and 0 <= ly < occ.height else font_r)
            if score < best_s:
                best_s = score
                best = (lx, ly)
    if best is not None:
        return best
    # 画布外侧四边兜底（原图贴边时图内可能没有外轮廓留白）
    for cand in (
        (-font_r * 1.6, anchor[1]),
        (occ.width + font_r * 1.6, anchor[1]),
        (anchor[0], -font_r * 1.6),
        (anchor[0], occ.height + font_r * 1.6),
    ):
        if _disk_exterior(occ, cand[0], cand[1], font_r * 0.6):
            if all(math.dist(cand, o) >= min_sep * 0.7 for o in others):
                return cand
    return current


def layout_callouts(
    callouts: list[dict[str, Any]],
    occ: Occupancy,
    slots: dict[str, tuple[float, float, float, float]],
    canvas: tuple[int, int],
    *,
    font_size: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    """像素画布 canvas=(W,H) 与 occ 网格独立；返回新 callouts（归一化）与改动说明。"""
    width, height = canvas
    notes: list[str] = []
    font_r = max(2.0, font_size * occ.width / max(width, 1) * 0.70)
    min_sep = max(font_r * 2.2, 0.045 * occ.width)
    placed: list[tuple[float, float]] = []
    out: list[dict[str, Any]] = []

    def slot_on_grid(pid: str) -> tuple[float, float, float, float] | None:
        box = slots.get(pid)
        if not box:
            return None
        x, y, w, h = box
        gx, gy = map_to_occ(occ, x, y, width, height)
        gw, gh = map_to_occ(occ, w, h, width, height)
        return gx, gy, gw, gh

    for item in callouts:
        row = dict(item)
        pid = str(row.get("id") or "").strip()
        anchor_n = row.get("anchor")
        label_n = row.get("label")
        if not (isinstance(anchor_n, (list, tuple)) and isinstance(label_n, (list, tuple))):
            out.append(row)
            continue
        ax, ay = map_to_occ(occ, float(anchor_n[0]) * width, float(anchor_n[1]) * height, width, height)
        lx, ly = map_to_occ(occ, float(label_n[0]) * width, float(label_n[1]) * height, width, height)
        box = slot_on_grid(pid)
        snapped = _nearest_ink(occ, (ax, ay), box) or _nearest_ink(occ, (ax, ay), None)
        if snapped and math.hypot(snapped[0] - ax, snapped[1] - ay) > 0.6:
            notes.append(f"snap_anchor id={pid}")
            ax, ay = snapped
        elif snapped:
            ax, ay = snapped
        new_label = place_label(
            occ,
            (ax, ay),
            (lx, ly),
            placed,
            font_r=font_r,
            min_sep=min_sep,
        )
        if math.hypot(new_label[0] - lx, new_label[1] - ly) > 0.8:
            notes.append(f"move_label id={pid}")
        placed.append(new_label)
        apx, apy = map_from_occ(occ, ax, ay, width, height)
        lpx, lpy = map_from_occ(occ, new_label[0], new_label[1], width, height)
        row["anchor"] = [
            round(min(1.0, max(0.0, apx / width)), 4),
            round(min(1.0, max(0.0, apy / height)), 4),
        ]
        # 序号可略出原画布，叠标后的 pad 能看见
        row["label"] = [
            round(min(1.08, max(-0.08, lpx / width)), 4),
            round(min(1.08, max(-0.08, lpy / height)), 4),
        ]
        dx = row["anchor"][0] - row["label"][0]
        dy = row["anchor"][1] - row["label"][1]
        row["route"] = "horizontal" if abs(dx) >= abs(dy) * 0.65 else "vertical"
        out.append(row)
    return out, notes


def occupancy_for_view(view: dict[str, Any], case_dir: Path) -> Occupancy | None:
    candidates: list[Path] = []
    image_raw = str(view.get("image_path") or "").strip()
    if image_raw:
        candidates.append(_resolve(case_dir, image_raw))
    base_raw = str(view.get("base_svg_path") or "").strip()
    if base_raw:
        base = _resolve(case_dir, base_raw)
        if base.is_file():
            href = source_image_href(base.read_text(encoding="utf-8"))
            if href:
                candidates.append((base.parent / href).resolve())
    seen: set[Path] = set()
    for path in candidates:
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            w, h, luma = luma_from_image(path)
            return occupancy_from_luma(w, h, luma)
        except Exception as exc:
            print(f"CALLOUT_LAYOUT: occupancy_skip path={path.name} err={exc}", file=sys.stderr, flush=True)
    return None


def autolayout_view(view: dict[str, Any], case_dir: Path, canvas: tuple[int, int]) -> dict[str, Any]:
    occ = occupancy_for_view(view, case_dir)
    if occ is None:
        print("CALLOUT_LAYOUT: skip_no_occupancy", file=sys.stderr, flush=True)
        return view
    slots: dict[str, tuple[float, float, float, float]] = {}
    base_raw = str(view.get("base_svg_path") or "").strip()
    if base_raw:
        base = _resolve(case_dir, base_raw)
        if base.is_file():
            slots = parse_part_slots(base.read_text(encoding="utf-8"))
    style = view.get("style") if isinstance(view.get("style"), dict) else {}
    font_size = float(style.get("font_size") or max(18, min(canvas) * 0.032))
    laid, notes = layout_callouts(
        list(view.get("callouts") or []),
        occ,
        slots,
        canvas,
        font_size=font_size,
    )
    if notes:
        print("CALLOUT_LAYOUT: " + "; ".join(notes), file=sys.stderr, flush=True)
    else:
        print("CALLOUT_LAYOUT: unchanged", file=sys.stderr, flush=True)
    updated = dict(view)
    updated["callouts"] = laid
    return updated


def _resolve(case_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    return (case_dir / path).resolve()
