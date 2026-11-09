# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(SHARED))

from structure_callout_layout import (
    occupancy_from_luma,
    layout_callouts,
    parse_part_slots,
)


def frame_luma(w: int = 80, h: int = 60, t: int = 6) -> bytes:
    """白底、黑框（中空），模拟剖视空腔。"""
    pix = bytearray([255] * (w * h))
    for y in range(h):
        for x in range(w):
            if x < t or y < t or x >= w - t or y >= h - t:
                pix[y * w + x] = 20
    return bytes(pix)


def test_label_leaves_cavity_and_anchor_snaps_to_ink() -> None:
    w, h = 80, 60
    occ = occupancy_from_luma(w, h, frame_luma(w, h), max_grid=80)
    callouts = [
        {
            "id": "2",
            "name": "前端盖",
            "anchor": [0.50, 0.50],
            "label": [0.50, 0.52],
            "confidence": 0.9,
        }
    ]
    slots = {"2": (0.0, 0.0, 80.0, 60.0)}
    laid, notes = layout_callouts(callouts, occ, slots, (w, h), font_size=8)
    assert any("snap_anchor" in n for n in notes)
    assert any("move_label" in n for n in notes)
    ax, ay = laid[0]["anchor"]
    lx, ly = laid[0]["label"]
    assert occ.is_ink(ax * occ.width, ay * occ.height)
    assert occ.is_exterior(lx * occ.width, ly * occ.height)
    assert not occ.is_ink(lx * occ.width, ly * occ.height)


def test_label_on_hatch_moves_outside() -> None:
    w, h = 80, 60
    pix = bytearray([255] * (w * h))
    for y in range(10, 50):
        for x in range(20, 70):
            pix[y * w + x] = 30
    occ = occupancy_from_luma(w, h, bytes(pix), max_grid=80)
    callouts = [
        {
            "id": "7",
            "name": "喷淋孔",
            "anchor": [0.55, 0.50],
            "label": [0.50, 0.45],
            "confidence": 0.9,
        }
    ]
    laid, notes = layout_callouts(
        callouts, occ, {"7": (20.0, 10.0, 50.0, 40.0)}, (w, h), font_size=8
    )
    assert any("move_label" in n for n in notes)
    lx, ly = laid[0]["label"]
    assert occ.is_exterior(lx * occ.width, ly * occ.height)


def test_hatch_gap_is_not_exterior() -> None:
    w, h = 80, 60
    pix = bytearray([255] * (w * h))
    for y in range(8, 52):
        for x in range(18, 70, 3):
            pix[y * w + x] = 20
    occ = occupancy_from_luma(w, h, bytes(pix), max_grid=80)
    # 剖面线缝隙里的白点不得当成图外留白
    assert not occ.is_exterior(40, 30)
    callouts = [
        {
            "id": "7",
            "name": "喷淋孔",
            "anchor": [0.50, 0.50],
            "label": [0.48, 0.48],
            "confidence": 0.9,
        }
    ]
    laid, notes = layout_callouts(callouts, occ, {"7": (18.0, 8.0, 52.0, 44.0)}, (w, h), font_size=8)
    assert any("move_label" in n for n in notes)
    lx, ly = laid[0]["label"]
    assert occ.is_exterior(lx * occ.width, ly * occ.height)


def test_parse_part_slots() -> None:
    svg = (
        '<svg><g id="part-2" data-part-id="2"><title>2</title>'
        '<image x="10" y="20" width="30" height="40" href="parts/a.svg"/>'
        "</g></svg>"
    )
    slots = parse_part_slots(svg)
    assert slots["2"] == (10.0, 20.0, 30.0, 40.0)
