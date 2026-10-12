"""独权特征清单：加载、校验、渲染第四节/第六节表。不写入 Canvas。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FEATURE_ID_RE = re.compile(r"^F\d+$")
PARA_RE = re.compile(r"^\d{1,4}$")


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _paras(raw: Any) -> list[str]:
    out: list[str] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        s = str(item).strip()
        s = s.replace("说明书", "").strip()
        if PARA_RE.fullmatch(s):
            out.append(s.zfill(4)[-4:])
    return list(dict.fromkeys(out))


def _str_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def normalize_claim_features(raw: Any) -> dict:
    if isinstance(raw, list):
        raw = {"features": raw}
    if not isinstance(raw, dict):
        return {"pub_number": "", "source": "", "features": []}
    features_in = raw.get("features") or raw.get("items") or []
    if not isinstance(features_in, list):
        features_in = []
    features: list[dict] = []
    for i, item in enumerate(features_in, start=1):
        if not isinstance(item, dict):
            continue
        fid = str(item.get("feature_id") or item.get("id") or f"F{i}").strip()
        claim_no = _as_int(item.get("claim_no") or item.get("claim") or item.get("number"))
        text = re.sub(r"\s+", " ", str(item.get("text") or item.get("phrase") or "").strip())
        features.append(
            {
                "feature_id": fid,
                "claim_no": claim_no,
                "text": text,
                "plain": re.sub(r"\s+", " ", str(item.get("plain") or "").strip()),
                "desc_paras": _paras(item.get("desc_paras") or item.get("paragraphs")),
                "part_ids": _str_list(item.get("part_ids")),
                "figures": _str_list(item.get("figures")),
            }
        )
    return {
        "pub_number": str(raw.get("pub_number") or "").strip(),
        "source": str(raw.get("source") or "").strip(),
        "features": features,
    }


def validate_claim_features(raw: Any) -> dict:
    data = normalize_claim_features(raw)
    issues: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    if not data["features"]:
        issues.append("empty_features")
    for feat in data["features"]:
        fid = feat["feature_id"]
        if not FEATURE_ID_RE.fullmatch(fid):
            issues.append(f"bad_feature_id:{fid}")
        if fid in seen:
            issues.append(f"duplicate_feature_id:{fid}")
        seen.add(fid)
        if feat["claim_no"] is None:
            issues.append(f"missing_claim_no:{fid}")
        if not feat["text"]:
            issues.append(f"missing_text:{fid}")
        if not feat["desc_paras"]:
            warnings.append(f"no_desc_paras:{fid}")
    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "count": len(data["features"]),
        "data": data,
    }


def load_claim_features(path: Path | None) -> dict | None:
    if path is None or not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return normalize_claim_features(raw)


def format_desc_cell(paras: list[str]) -> str:
    if not paras:
        return ""
    nums = [int(p) for p in paras]
    if len(nums) == 1:
        return f"说明书 {paras[0]}"
    if len(nums) == 2 and nums[1] == nums[0] + 1:
        return f"说明书 {paras[0]}–{paras[1]}"
    # 连续区间压缩
    runs: list[str] = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        runs.append(
            f"说明书 {start:04d}" if start == prev else f"说明书 {start:04d}–{prev:04d}"
        )
        start = prev = n
    runs.append(
        f"说明书 {start:04d}" if start == prev else f"说明书 {start:04d}–{prev:04d}"
    )
    return " / ".join(runs)


def render_section4_tables(data: dict) -> str:
    groups: dict[int, list[dict]] = {}
    unknown: list[dict] = []
    for feat in data.get("features") or []:
        n = feat.get("claim_no")
        if n is None:
            unknown.append(feat)
            continue
        groups.setdefault(int(n), []).append(feat)
    chunks: list[str] = []
    for claim_no in sorted(groups):
        rows = [
            "| 特征 | 大白话 | 说明书依据 |",
            "|------|--------|------------|",
        ]
        for feat in groups[claim_no]:
            rows.append(
                f"| {feat['feature_id']} | {feat.get('plain') or feat['text']} | "
                f"{format_desc_cell(feat.get('desc_paras') or [])} |"
            )
        chunks.append("\n".join(rows))
    if unknown:
        rows = [
            "| 特征 | 大白话 | 说明书依据 |",
            "|------|--------|------------|",
        ]
        for feat in unknown:
            rows.append(
                f"| {feat['feature_id']} | {feat.get('plain') or feat['text']} | "
                f"{format_desc_cell(feat.get('desc_paras') or [])} |"
            )
        chunks.append("\n".join(rows))
    return "\n\n".join(chunks)


def render_section6_table(data: dict) -> str:
    rows = [
        "| 特征 | 说明书位置 | 附图 |",
        "|------|------------|------|",
    ]
    for feat in data.get("features") or []:
        figs = "、".join(feat.get("figures") or [])
        rows.append(
            f"| {feat['feature_id']} | {format_desc_cell(feat.get('desc_paras') or [])} | {figs} |"
        )
    return "\n".join(rows)


_SEC4 = re.compile(r"(^##\s*四、\s*独立权利要求精读\s*\n)([\s\S]*?)(?=^##\s*五、|\Z)", re.M)
_SEC6 = re.compile(r"(^##\s*六、\s*特征[^\n]*\n)([\s\S]*?)(?=^##\s*七、|\Z)", re.M)
_FEATURE_TABLE = re.compile(
    r"\|[^\n]*特征[^\n]*\|[^\n]*\n\|[-:| ]+\|[\s\S]*?(?=\n(?:\|[^\n]*特征[^\n]*\||> |## |\Z))"
)


def upsert_feature_sections(content: str, data: dict) -> str:
    """用特征清单重写第四节特征表与第六节对照表；保留 callout / 引文。"""
    if not data.get("features"):
        return content
    sec4_tables = render_section4_tables(data)
    sec6_table = render_section6_table(data)

    def repl4(m: re.Match[str]) -> str:
        body = m.group(2)
        if _FEATURE_TABLE.search(body):
            body = _FEATURE_TABLE.sub("", body)
            body = re.sub(r"\n{3,}", "\n\n", body).rstrip() + "\n\n" + sec4_tables + "\n\n"
        else:
            body = body.rstrip() + "\n\n" + sec4_tables + "\n\n"
        return m.group(1) + body

    def repl6(m: re.Match[str]) -> str:
        body = m.group(2)
        if _FEATURE_TABLE.search(body):
            body = _FEATURE_TABLE.sub(sec6_table + "\n\n", body, count=1)
        else:
            body = sec6_table + "\n\n" + body.lstrip()
        return m.group(1) + body

    if _SEC4.search(content):
        content = _SEC4.sub(repl4, content, count=1)
    if _SEC6.search(content):
        content = _SEC6.sub(repl6, content, count=1)
    return content
