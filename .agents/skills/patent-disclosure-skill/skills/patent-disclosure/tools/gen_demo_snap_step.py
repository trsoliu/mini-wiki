# -*- coding: utf-8 -*-
"""生成教学用简易 STEP（矩形基板 + 侧向卡钩）。

默认写出 **FACETED_BREP**（无需 CadQuery）。注意：部分 OCCT/CadQuery 版本对 FACETED_BREP
导入不稳定（可能 Bnd_Box void）；若需 `step_to_views.py` 解析，请在已安装 CadQuery 的
Python 3.9–3.12 环境中按同尺寸 `box` 重建并 `cq.exporters.export` 覆盖为可解析 STEP。

  python tools/gen_demo_snap_step.py
"""
from __future__ import annotations

import argparse
from pathlib import Path


def _faceted_box(
    eid: list[int],
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    zmin: float,
    zmax: float,
    solid_name: str,
) -> tuple[list[str], int]:
    """追加一个轴对齐长方体；eid[0] 为下一个可用 id。返回 (lines, solid_id)。"""

    def next_id() -> int:
        i = eid[0]
        eid[0] += 1
        return i

    lines: list[str] = []
    corners = [
        (xmin, ymin, zmin),
        (xmax, ymin, zmin),
        (xmax, ymax, zmin),
        (xmin, ymax, zmin),
        (xmin, ymin, zmax),
        (xmax, ymin, zmax),
        (xmax, ymax, zmax),
        (xmin, ymax, zmax),
    ]
    pids = []
    for x, y, z in corners:
        i = next_id()
        pids.append(i)
        lines.append(f"#{i}=CARTESIAN_POINT('',({x:.3f},{y:.3f},{z:.3f}));")

    # face corner index quads (outward-ish)
    quads = [
        (0, 3, 2, 1),  # bottom
        (4, 5, 6, 7),  # top
        (0, 1, 5, 4),  # ymin
        (1, 2, 6, 5),  # xmax
        (2, 3, 7, 6),  # ymax
        (3, 0, 4, 7),  # xmin
    ]
    face_ids = []
    for q in quads:
        loop = next_id()
        pts = ",".join(f"#{pids[i]}" for i in q)
        lines.append(f"#{loop}=POLY_LOOP('',({pts}));")
        fb = next_id()
        lines.append(f"#{fb}=FACE_OUTER_BOUND('',#{loop},.T.);")
        face = next_id()
        lines.append(f"#{face}=FACE('',(#{fb}));")
        face_ids.append(face)

    shell = next_id()
    faces = ",".join(f"#{f}" for f in face_ids)
    lines.append(f"#{shell}=CLOSED_SHELL('',({faces}));")
    solid = next_id()
    lines.append(f"#{solid}=MANIFOLD_SOLID_BREP('{solid_name}',#{shell});")
    return lines, solid


def build_step() -> str:
    eid = [10]
    lines: list[str] = []
    # 基板 40×25×2 mm
    L1, s1 = _faceted_box(eid, 0, 40, 0, 25, 0, 2, "BasePlate")
    lines.extend(L1)
    # 卡钩示意块：板缘外伸并下探（教学几何，非真实模具）
    L2, s2 = _faceted_box(eid, 40, 43, 8.5, 16.5, -4, 2, "SnapHook")
    lines.extend(L2)

    a = eid[0] + 5
    header = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('patent-disclosure-skill demo snap plate','teaching only'),'2;1');
FILE_NAME('demo_snap_plate.step','2026-08-10T00:00:00',('patent-disclosure-skill'),(''),
'gen_demo_snap_step.py','','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
"""
    product = f"""
#{a}=APPLICATION_CONTEXT('core data for automotive mechanical design processes');
#{a+1}=APPLICATION_PROTOCOL_DEFINITION('international standard','automotive_design',2001,#{a});
#{a+2}=PRODUCT('demo_snap_plate','demo_snap_plate','teaching STEP for cad_scan / step_to_views',(#{a+3}));
#{a+3}=PRODUCT_CONTEXT('',#{a},'mechanical');
#{a+4}=PRODUCT_DEFINITION_FORMATION('','',#{a+2});
#{a+5}=PRODUCT_DEFINITION('design','',#{a+4},#{a+6});
#{a+6}=PRODUCT_DEFINITION_CONTEXT('part definition',#{a},'design');
#{a+7}=PRODUCT_DEFINITION_SHAPE('','SHAPE FOR demo_snap_plate',#{a+5});
#{a+8}=SHAPE_DEFINITION_REPRESENTATION(#{a+7},#{a+9});
#{a+9}=FACETED_BREP_SHAPE_REPRESENTATION('demo_snap_plate',(#{s1},#{s2}),#{a+10});
#{a+10}=(GEOMETRIC_REPRESENTATION_CONTEXT(3)GLOBAL_UNCERTAINTY_ASSIGNED_CONTEXT((#{a+11}))GLOBAL_UNIT_ASSIGNED_CONTEXT((#{a+12},#{a+13},#{a+14}))REPRESENTATION_CONTEXT('Context #1','3D Context with UNIT and UNCERTAINTY'));
#{a+11}=UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.E-07),#{a+12},'distance_accuracy_value','confusion accuracy');
#{a+12}=(CONVERSION_BASED_UNIT('MILLIMETRE',#{a+15})LENGTH_UNIT()NAMED_UNIT(#{a+16}));
#{a+13}=(NAMED_UNIT(#{a+17})PLANE_ANGLE_UNIT()SI_UNIT($,.RADIAN.));
#{a+14}=(NAMED_UNIT(#{a+17})SI_UNIT($,.STERADIAN.)SOLID_ANGLE_UNIT());
#{a+15}=LENGTH_MEASURE_WITH_UNIT(LENGTH_MEASURE(1.0),#{a+18});
#{a+16}=DIMENSIONAL_EXPONENTS(1.,0.,0.,0.,0.,0.,0.);
#{a+17}=DIMENSIONAL_EXPONENTS(0.,0.,0.,0.,0.,0.,0.);
#{a+18}=(LENGTH_UNIT()NAMED_UNIT(#{a+16})SI_UNIT(.MILLI.,.METRE.));
ENDSEC;
END-ISO-10303-21;
"""
    return header + "\n".join(lines) + "\n" + product


def main(argv: list[str] | None = None) -> int:
    default_out = (
        Path(__file__).resolve().parents[1]
        / "tests"
        / "fixtures"
        / "cad"
        / "demo_snap_plate.step"
    )
    p = argparse.ArgumentParser(description="生成教学用 demo_snap_plate.step")
    p.add_argument("-o", "--out", type=Path, default=default_out)
    args = p.parse_args(argv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_step(), encoding="utf-8", newline="\n")
    print(f"Wrote {args.out} ({args.out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
