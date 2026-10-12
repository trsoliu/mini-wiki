# -*- coding: utf-8 -*-
"""著录检索结果落盘（与爬取/过滤解耦）。

改输出格式、目录或文件名时，只动本文件即可。检索脚本只传入一份 payload。

默认路径：``outputs/patent-search/SEARCH-YYYYMMDD-HHMMSS.md``
（仓库根或已有 ``outputs/`` 的上一级；可用环境变量 ``PATENT_SEARCH_OUTPUT_DIR`` 覆盖）

也可单独跑：

  python skills/patent-search/tools/emit_search_report.py --json result.json
  python skills/patent-search/tools/emit_search_report.py < result.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPORT_SUBDIR = "patent-search"
REPORT_PREFIX = "SEARCH"
ENV_OUTPUT_DIR = "PATENT_SEARCH_OUTPUT_DIR"

_QUERY_LABELS = {
    "inventor": "发明人",
    "applicant": "申请人",
    "applicants": "申请人别名",
    "title": "名称",
    "abstract": "摘要/简要说明",
    "class_code": "分类号",
    "application_number": "申请号",
    "publication_number": "公开号/公告号",
    "patent_type": "专利类型",
    "type_inferred": "类型来源",
    "type_note": "类型说明",
    "max_pages": "预排翻页上限",
    "want_complete": "穷举（--complete）",
    "derived_from": "派生自",
    "derived_note": "理解要点",
}

_QUERY_MODE_LABELS = {
    "advanced_bibliographic": "著录字段",
    "derived_image": "单图关键字代理",
    "derived_claims": "权要关键字代理",
}

_DERIVED_FROM_LABELS = {
    "image": "单图",
    "claims": "权利要求",
}

_TYPE_LABELS = {
    "invention": "发明",
    "utility_model": "实用新型",
    "design": "外观设计",
    "all": "全部",
}

_IDENTITY_LABELS = {
    "verified_inventor_metadata": "已由官方发明人著录核实",
    "inventor_query_and_applicant": "发明人查询与申请人共同匹配",
    "inventor_query_only_unverified_namesake": "仅姓名查询命中，同名归属待核实",
    "applicant_filter": "申请人过滤",
    "unfiltered": "未过滤",
}


def default_output_dir(start: Path | None = None) -> Path:
    env = (os.environ.get(ENV_OUTPUT_DIR) or "").strip()
    if env:
        return Path(env)
    here = (start or Path(__file__).resolve()).resolve()
    cursor = here if here.is_dir() else here.parent
    for parent in [cursor, *cursor.parents]:
        if (parent / ".git").exists() or (parent / "outputs").is_dir():
            return parent / "outputs" / REPORT_SUBDIR
    return Path.cwd() / "outputs" / REPORT_SUBDIR


def report_filename(when: datetime) -> str:
    return f"{REPORT_PREFIX}-{when.strftime('%Y%m%d-%H%M%S')}.md"


def _text(value: Any, empty: str = "—") -> str:
    if value is None:
        return empty
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (list, tuple)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "；".join(parts) if parts else empty
    text = str(value).strip()
    return text if text else empty


def _md_escape(value: Any) -> str:
    return _text(value).replace("|", "\\|")


def _link(title: Any, url: Any) -> str:
    name = _text(title, empty="（无名称）")
    href = str(url or "").strip()
    if href:
        return f"[{name}]({href})"
    return name


def _format_query_value(key: str, value: Any) -> str:
    if key == "patent_type":
        return _TYPE_LABELS.get(str(value), _text(value))
    if key == "derived_from":
        return _DERIVED_FROM_LABELS.get(str(value), _text(value))
    if key == "type_inferred":
        if value is True:
            return "看图推断（用户未口头指定）"
        if value is False:
            return ""
    return _text(value)


def render_search_report(
    payload: dict[str, Any],
    *,
    queried_at: datetime | None = None,
    report_name: str | None = None,
) -> str:
    """把检索 payload 渲染成 Markdown。二开改版式主要改这里。"""
    when = queried_at
    if when is None and payload.get("queried_at"):
        try:
            when = datetime.strptime(str(payload["queried_at"]), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            when = None
    when = when or datetime.now()
    stamp = when.strftime("%Y-%m-%d %H:%M:%S")
    name = report_name or report_filename(when)
    query = payload.get("query") or {}
    hits = list(payload.get("hits") or [])
    note = _text(payload.get("completeness_note"), empty="")

    lines = [
        f"# 著录检索 {Path(name).stem}",
        "",
        f"- **查询时间**：{stamp}",
        f"- **数据源**：{_text(payload.get('source'), empty='http://epub.cnipa.gov.cn/Advanced')}",
        f"- **范围**：仅已公开/公告记录，不得写成实际提交总数",
        f"- **检索方式**：{_QUERY_MODE_LABELS.get(str(payload.get('query_mode') or ''), _text(payload.get('query_mode'), empty='著录字段'))}",
        f"- **命中**：候选 { _text(payload.get('candidate_count'), empty='0') } 条，过滤后 { _text(payload.get('matched_count'), empty='0') } 件"
        f"（公布/授权记录 { _text(payload.get('matched_publication_count'), empty='0') } 条）",
        f"- **完整性**：{_text(payload.get('complete'))}；{note or _text(payload.get('stop_reason'))}",
        "",
        "## 查询条件",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
    ]
    seen = set()
    for key in (
        "inventor",
        "applicant",
        "applicants",
        "title",
        "abstract",
        "class_code",
        "application_number",
        "publication_number",
        "patent_type",
        "type_inferred",
        "type_note",
        "derived_from",
        "derived_note",
        "max_pages",
        "want_complete",
    ):
        if key not in query:
            continue
        value = query[key]
        if key == "applicant" and query.get("applicants"):
            continue
        if key == "type_inferred" and not value:
            continue
        if value in (None, "", [], ()):
            continue
        seen.add(key)
        lines.append(f"| {_QUERY_LABELS.get(key, key)} | {_md_escape(_format_query_value(key, value))} |")
    for key, value in query.items():
        if key in seen or value in (None, "", [], ()):
            continue
        if key == "type_inferred" and not value:
            continue
        lines.append(f"| {_QUERY_LABELS.get(key, key)} | {_md_escape(_format_query_value(key, value))} |")

    disclaimer = str(payload.get("disclaimer") or "").strip()
    if not disclaimer and str(payload.get("query_mode") or "").startswith("derived"):
        from derived_query import DISCLAIMER as _DERIVED_DISCLAIMER

        disclaimer = _DERIVED_DISCLAIMER
    if disclaimer:
        lines.extend(["", f"> {disclaimer}"])

    lines.extend(
        [
            "",
            "## 分页",
            "",
            "| 项 | 值 |",
            "| --- | --- |",
            f"| 已翻页数 | {_md_escape(payload.get('pages_scanned'))} |",
            f"| 共 N 页 | {_md_escape(payload.get('total_pages'))} |",
            f"| 每页条数（实测） | {_md_escape(payload.get('page_size_actual'))} |",
            f"| 本页命中（第 1 页） | {_md_escape(payload.get('first_page_hit_count'))} |",
            f"| 本次页预算 | {_md_escape(payload.get('page_budget'))} |",
            f"| 还剩页数 | {_md_escape(payload.get('pages_remaining'))} |",
            f"| 条数估计 | {_md_escape(payload.get('hit_count_estimate'))} |",
            f"| 站点「共 N 条」 | {_md_escape(payload.get('total_reported'))} |",
            f"| 停止原因 | {_md_escape(payload.get('stop_reason'))} |",
            "",
            "## 检索结果",
            "",
        ]
    )

    if not hits:
        lines.append("本次无过滤后命中。")
        lines.append("")
        return "\n".join(lines)

    for index, row in enumerate(hits, start=1):
        title = row.get("title")
        link = row.get("link")
        lines.append(f"### {index}. {_link(title, link)}")
        lines.append("")
        lines.append(f"- **详情**：{_link('打开公布页', link) if link else '—'}")
        lines.append(f"- **专利名称**：{_text(title)}")
        lines.append(f"- **公开号/公告号**：{_text(row.get('pub_number'))}")
        lines.append(f"- **申请号**：{_text(row.get('application_number'))}")
        lines.append(f"- **申请人**：{_text(row.get('applicant'))}")
        if row.get("matched_applicant"):
            lines.append(f"- **匹配申请人**：{_text(row.get('matched_applicant'))}")
        lines.append(f"- **发明人**：{_text(row.get('inventors'))}")
        lines.append(f"- **申请日**：{_text(row.get('filing_date'))}")
        lines.append(f"- **公开/公告日**：{_text(row.get('publication_date'))}")
        ipc = row.get("ipc_codes") or []
        loc = row.get("loc_codes") or []
        if ipc:
            lines.append(f"- **IPC**：{_text(ipc)}")
        if loc:
            lines.append(f"- **洛迦诺**：{_text(loc)}")
        identity = row.get("identity_status")
        if identity:
            lines.append(
                f"- **归属标注**：{_IDENTITY_LABELS.get(str(identity), _text(identity))}"
            )
        records = [item for item in (row.get("publication_records") or []) if item]
        extra = [
            rec
            for rec in records
            if rec.get("pub_number") and rec.get("pub_number") != row.get("pub_number")
        ]
        if extra:
            bits = []
            for rec in extra:
                bits.append(_link(rec.get("pub_number"), rec.get("link")))
            lines.append(f"- **其他公布/授权记录**：{'；'.join(bits)}")
        abstract = _text(row.get("abstract"), empty="")
        lines.append(f"- **摘要**：{abstract or '（结果页未提供摘要）'}")
        lines.append("")
    return "\n".join(lines)


def write_search_report(
    payload: dict[str, Any],
    *,
    queried_at: datetime | None = None,
    output_dir: Path | None = None,
) -> Path:
    when = queried_at or datetime.now()
    folder = Path(output_dir) if output_dir else default_output_dir()
    folder.mkdir(parents=True, exist_ok=True)
    name = report_filename(when)
    path = folder / name
    if path.exists():
        path = folder / f"{REPORT_PREFIX}-{when.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.md"
        name = path.name
    path.write_text(
        render_search_report(payload, queried_at=when, report_name=name),
        encoding="utf-8",
    )
    return path


def _load_payload(path: Path | None) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8") if path else sys.stdin.read()
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("JSON 须为对象")
    if "hits" not in data and "EPUB_SEARCH_JSON:" in raw:
        raise ValueError("请传入 EPUB_SEARCH_JSON 后面的对象，不要带前缀")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="把著录检索 JSON 落成 Markdown")
    parser.add_argument("--json", dest="json_path", help="检索结果 JSON 文件；缺省读 stdin")
    parser.add_argument("--output-dir", help="覆盖默认 outputs/patent-search")
    args = parser.parse_args(argv)
    try:
        payload = _load_payload(Path(args.json_path) if args.json_path else None)
        path = write_search_report(
            payload,
            output_dir=Path(args.output_dir) if args.output_dir else None,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"EPUB_SEARCH_MD: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
