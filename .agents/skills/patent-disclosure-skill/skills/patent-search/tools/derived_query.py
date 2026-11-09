# -*- coding: utf-8 -*-
"""单图 / 权要 → 公布站名称、摘要关键字（布尔代理，不是以图搜图或语义检索）。"""
from __future__ import annotations

import re

from patent_type import TYPE_ALL, TYPE_DESIGN, TYPE_INVENTION, TYPE_UTILITY_MODEL

DERIVED_IMAGE = "image"
DERIVED_CLAIMS = "claims"
DERIVED_FROM_VALUES = (DERIVED_IMAGE, DERIVED_CLAIMS)

QUERY_MODE_BIBLIOGRAPHIC = "advanced_bibliographic"
QUERY_MODE_IMAGE = "derived_image"
QUERY_MODE_CLAIMS = "derived_claims"

DISCLAIMER = (
    "本检索由图片或权利要求生成公布站「名称 / 摘要」关键字后查询，"
    "不是以图搜图，也不是权利要求语义检索；漏检可能较高，不得作为查新或 FTO 结论。"
)

IMAGE_TYPE_REQUIRED = (
    "单图检索必须指定 --type（design / utility_model / invention），不能用 all"
)

INFERRED_TYPE_NOTES = {
    TYPE_DESIGN: "未指定类型，按产品外观检索；若要查结构请说实用新型",
    TYPE_UTILITY_MODEL: "未指定类型，按结构图检索实用新型；若要查外观请说明",
    TYPE_INVENTION: "未指定类型，按流程图/框图检索发明；若实际要查外观或实用新型请说明",
}

_BOOLEAN = {"and", "or", "not"}
_TOKEN = re.compile(r"\s+")


def normalize_derived_from(value: str | None) -> str:
    text = (value or "").strip().casefold()
    aliases = {
        "image": DERIVED_IMAGE,
        "img": DERIVED_IMAGE,
        "photo": DERIVED_IMAGE,
        "图": DERIVED_IMAGE,
        "单图": DERIVED_IMAGE,
        "图片": DERIVED_IMAGE,
        "claims": DERIVED_CLAIMS,
        "claim": DERIVED_CLAIMS,
        "权要": DERIVED_CLAIMS,
        "权利要求": DERIVED_CLAIMS,
    }
    if not text:
        return ""
    if text not in aliases:
        raise ValueError("derived-from 只接受 image 或 claims")
    return aliases[text]


def query_mode_for(derived_from: str | None) -> str:
    kind = normalize_derived_from(derived_from) if derived_from else ""
    if kind == DERIVED_IMAGE:
        return QUERY_MODE_IMAGE
    if kind == DERIVED_CLAIMS:
        return QUERY_MODE_CLAIMS
    return QUERY_MODE_BIBLIOGRAPHIC


def require_image_patent_type(derived_from: str, patent_type: str) -> None:
    """单图检索禁止静默 all；权要不受此限。"""
    if derived_from == DERIVED_IMAGE and patent_type == TYPE_ALL:
        raise ValueError(IMAGE_TYPE_REQUIRED)


def inferred_type_note(patent_type: str) -> str:
    return INFERRED_TYPE_NOTES.get(patent_type, "")


def join_and(terms: list[str] | tuple[str, ...] | None) -> str:
    """把特征词收成公布站摘要框可用的 ``A and B`` 式。"""
    parts: list[str] = []
    seen: set[str] = set()
    for raw in terms or []:
        token = _TOKEN.sub(" ", str(raw or "").strip())
        key = token.casefold()
        if not token or key in _BOOLEAN or key in seen:
            continue
        seen.add(key)
        parts.append(token)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return " and ".join(parts)
