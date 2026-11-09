# -*- coding: utf-8 -*-
"""特征覆盖精排旁路报告。不改动 SEARCH-*.md 列表正文。"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def _text(value: Any, empty: str = "—") -> str:
    if value is None:
        return empty
    if isinstance(value, bool):
        return "是" if value else "否"
    text = str(value).strip()
    return text if text else empty


def _md_escape(value: Any) -> str:
    return _text(value).replace("|", "\\|")


def covers_paths_beside(search_md: Path) -> tuple[Path, Path]:
    stem = search_md.stem
    parent = search_md.parent
    return parent / f"{stem}.covers.md", parent / f"{stem}.covers.json"


def render_covers_report(payload: dict[str, Any]) -> str:
    features = list(payload.get("features") or [])
    rows = list(payload.get("rows") or [])
    search_md = _text(payload.get("search_md"), empty="")
    lines = [
        f"# 特征覆盖精排 {Path(str(payload.get('report_name') or 'covers')).stem}",
        "",
        "> 本文件是著录检索列表的旁路，**不是**检索清单本身。列表见同一次的 `SEARCH-*.md`。",
        "",
        f"- **生成时间**：{_text(payload.get('ranked_at'))}",
        f"- **对应列表**：{search_md or '—'}",
        f"- **特征数**：{len(features)}",
        f"- **打分行数**：{len(rows)}",
        "",
        "## 特征",
        "",
        "| 特征 | 权号 | 原文短语 |",
        "| --- | ---: | --- |",
    ]
    for feat in features:
        lines.append(
            f"| {_md_escape(feat.get('feature_id'))} | {_md_escape(feat.get('claim_no'))} | "
            f"{_md_escape(feat.get('text'))} |"
        )
    lines.extend(["", "## 按特征覆盖", ""])
    if not rows:
        lines.append("无打分行。")
        lines.append("")
        return "\n".join(lines)

    by_feat: dict[str, list[dict]] = {}
    for row in rows:
        fid = str(row.get("feature_id") or "").strip() or "（未标）"
        by_feat.setdefault(fid, []).append(row)

    for fid, items in by_feat.items():
        lines.append(f"### {fid}")
        lines.append("")
        lines.append("| 公开号 | 能填本格 | 分数 | 摘录 | 链接 |")
        lines.append("| --- | --- | ---: | --- | --- |")
        for item in items:
            link = str(item.get("link") or "").strip()
            pub = _text(item.get("pub_number"))
            pub_cell = f"[{pub}]({link})" if link else pub
            covers = item.get("covers_feature")
            if covers is True:
                flag = "能填"
            elif covers is False:
                flag = "不能填"
            else:
                flag = "待核"
            snippet = _md_escape(item.get("snippet") or item.get("abstract") or "")
            lines.append(
                f"| {pub_cell} | {flag} | {_md_escape(item.get('score'))} | {snippet} | "
                f"{link or '—'} |"
            )
        lines.append("")
    return "\n".join(lines)


def write_covers_report(
    payload: dict[str, Any],
    *,
    beside: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    when = datetime.now()
    payload = dict(payload)
    payload.setdefault("ranked_at", when.strftime("%Y-%m-%d %H:%M:%S"))
    if beside:
        md_path, json_path = covers_paths_beside(Path(beside))
    else:
        folder = Path(output_dir) if output_dir else Path.cwd()
        folder.mkdir(parents=True, exist_ok=True)
        stamp = when.strftime("%Y%m%d-%H%M%S")
        md_path = folder / f"SEARCH-{stamp}.covers.md"
        json_path = folder / f"SEARCH-{stamp}.covers.json"
    payload["report_name"] = md_path.name
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_covers_report(payload), encoding="utf-8")
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


def _load(path: Path | None) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8") if path else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON 须为对象")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="落盘 covers_feature 旁路 md/json")
    parser.add_argument("--json", dest="json_path", help="打分结果 JSON；缺省读 stdin")
    parser.add_argument(
        "--beside",
        help="对应的 SEARCH-*.md 路径；写出 SEARCH-*.covers.md / .covers.json",
    )
    parser.add_argument("--output-dir", help="无 --beside 时的目录")
    args = parser.parse_args(argv)
    try:
        payload = _load(Path(args.json_path) if args.json_path else None)
        md_path, json_path = write_covers_report(
            payload,
            beside=Path(args.beside) if args.beside else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"EPUB_SEARCH_COVERS_MD: {md_path}", flush=True)
    print(f"EPUB_SEARCH_COVERS_JSON: {json_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
