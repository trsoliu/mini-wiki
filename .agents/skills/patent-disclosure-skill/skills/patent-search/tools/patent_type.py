# -*- coding: utf-8 -*-
"""著录检索的专利类型常量与国知局 checkbox。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Iterable

# 技能内部规范名
TYPE_INVENTION = "invention"
TYPE_UTILITY_MODEL = "utility_model"
TYPE_DESIGN = "design"
TYPE_ALL = "all"

CANONICAL_TYPES = (TYPE_INVENTION, TYPE_UTILITY_MODEL, TYPE_DESIGN, TYPE_ALL)

TYPE_LABEL_ZH: dict[str, str] = {
    TYPE_INVENTION: "发明",
    TYPE_UTILITY_MODEL: "实用新型",
    TYPE_DESIGN: "外观设计",
    TYPE_ALL: "全部",
}

# 国知局 epub 首页 checkbox id → 中文标签
# 见首页 #indexForm：fmgb 发明公布 / fmsq 发明授权 / xxsq 实用新型 / wgsq 外观设计
EPUB_CHECKBOX_IDS = ("fmgb", "fmsq", "xxsq", "wgsq")

EPUB_TYPE_CHECKBOXES: dict[str, dict[str, bool]] = {
    TYPE_ALL: {"fmgb": True, "fmsq": True, "xxsq": True, "wgsq": True},
    TYPE_INVENTION: {"fmgb": True, "fmsq": True, "xxsq": False, "wgsq": False},
    TYPE_UTILITY_MODEL: {"fmgb": False, "fmsq": False, "xxsq": True, "wgsq": False},
    TYPE_DESIGN: {"fmgb": False, "fmsq": False, "xxsq": False, "wgsq": True},
}

# Google Patents（WebSearch / 浏览器）：官方 type 仅 PATENT | DESIGN
# 中国实用新型无独立 type，用关键词 / 公开号形态辅助
GOOGLE_PATENTS_TYPE_HINT: dict[str, dict[str, str]] = {
    TYPE_INVENTION: {
        "gp_type": "PATENT",
        "query_extra": "country:CN",
        "note": "勾选/参数 type=PATENT；中国发明公开号常见 CN…A / CN…B",
    },
    TYPE_UTILITY_MODEL: {
        "gp_type": "PATENT",
        "query_extra": 'country:CN (实用新型 OR "utility model")',
        "note": "无独立 utility-model type；以 PATENT + 中文「实用新型」/公开号 …U 收窄",
    },
    TYPE_DESIGN: {
        "gp_type": "DESIGN",
        "query_extra": "country:CN",
        "note": "type=DESIGN；中国外观公开号常见 CN…S",
    },
    TYPE_ALL: {
        "gp_type": "",
        "query_extra": "country:CN",
        "note": "不限制 type",
    },
}

# Google 学术：无专利类型过滤器
GOOGLE_SCHOLAR_SUPPORTS_PATENT_TYPE = False

_ALIASES = {
    "发明": TYPE_INVENTION,
    "发明专利": TYPE_INVENTION,
    "invention": TYPE_INVENTION,
    "实用新型": TYPE_UTILITY_MODEL,
    "实用": TYPE_UTILITY_MODEL,
    "utility_model": TYPE_UTILITY_MODEL,
    "utility-model": TYPE_UTILITY_MODEL,
    "um": TYPE_UTILITY_MODEL,
    "外观": TYPE_DESIGN,
    "外观设计": TYPE_DESIGN,
    "design": TYPE_DESIGN,
    "全部": TYPE_ALL,
    "all": TYPE_ALL,
}

# 中国专利文献种类标识（公开/公告号末位字母）→ 三大类
# 依据国知局文献种类代码惯例（A/B/C 发明；U/Y 实用新型；S 外观）
_KIND_LETTER_TO_TYPE: dict[str, str] = {
    "A": TYPE_INVENTION,
    "B": TYPE_INVENTION,
    "C": TYPE_INVENTION,
    "U": TYPE_UTILITY_MODEL,
    "Y": TYPE_UTILITY_MODEL,
    "S": TYPE_DESIGN,
}

_PUB_TAIL_RE = re.compile(r"(?i)^(?:CN|ZL)?\d{7,12}([ABYCUS])\d?$")


def normalize_patent_type(raw: str | None, *, default: str = TYPE_ALL) -> str:
    if raw is None or not str(raw).strip():
        return default
    key = str(raw).strip().lower().replace(" ", "_")
    # 中文别名保持原样查一次
    if raw.strip() in _ALIASES:
        return _ALIASES[raw.strip()]
    if key in _ALIASES:
        return _ALIASES[key]
    if key in CANONICAL_TYPES:
        return key
    raise ValueError(
        f"unknown patent type {raw!r}; use one of {', '.join(CANONICAL_TYPES)}"
    )


def normalize_pub_number(pub: str | None) -> str:
    if not pub:
        return ""
    return re.sub(r"\s+", "", str(pub).strip()).upper()


def infer_patent_type_from_pub(pub: str | None) -> str | None:
    """由中国公开号/公告号文献种类码推断 invention|utility_model|design。

    无法识别（非 CN 形态、缺种类字母等）时返回 None。
    """
    s = normalize_pub_number(pub)
    if not s:
        return None
    m = _PUB_TAIL_RE.match(s)
    if not m:
        return None
    letter = m.group(1).upper()
    return _KIND_LETTER_TO_TYPE.get(letter)


def infer_patent_type_from_biblio(text: str | None) -> str | None:
    """从著录/扉页/摘要等短文本关键词推断（弱于公开号种类码）。"""
    if not text or not str(text).strip():
        return None
    t = str(text)
    if re.search(r"外观设计|外观专利|\bdesign\s+patent\b", t, re.I):
        return TYPE_DESIGN
    if re.search(r"实用新型|\butility\s*model\b", t, re.I):
        return TYPE_UTILITY_MODEL
    if re.search(r"发明专利|发明公布|发明授权|\binvention\s+patent\b", t, re.I):
        return TYPE_INVENTION
    return None


def resolve_reader_patent_type(
    *,
    pub: str | None = None,
    user_declared: str | None = None,
    biblio_text: str | None = None,
) -> dict:
    """解读/交底共用：解析最终类型与依据。

    优先级：用户显式声明（非 all）> 公开号种类码 > 著录关键词。
    """
    out: dict = {
        "patent_type": None,
        "label_zh": None,
        "source": None,
        "pub": normalize_pub_number(pub) or None,
        "confidence": "none",
    }
    if user_declared and str(user_declared).strip():
        try:
            t = normalize_patent_type(user_declared, default="")
        except ValueError:
            t = ""
        if t and t != TYPE_ALL:
            out.update(
                {
                    "patent_type": t,
                    "label_zh": TYPE_LABEL_ZH[t],
                    "source": "user_declared",
                    "confidence": "high",
                }
            )
            return out

    from_pub = infer_patent_type_from_pub(pub)
    if from_pub:
        out.update(
            {
                "patent_type": from_pub,
                "label_zh": TYPE_LABEL_ZH[from_pub],
                "source": "pub_kind_code",
                "confidence": "high",
            }
        )
        return out

    from_biblio = infer_patent_type_from_biblio(biblio_text)
    if from_biblio:
        out.update(
            {
                "patent_type": from_biblio,
                "label_zh": TYPE_LABEL_ZH[from_biblio],
                "source": "biblio_text",
                "confidence": "medium",
            }
        )
        return out

    return out


def epub_checkbox_states(patent_type: str) -> dict[str, bool]:
    t = normalize_patent_type(patent_type, default=TYPE_ALL)
    return dict(EPUB_TYPE_CHECKBOXES[t])


def google_patents_websearch_query(
    keywords: str,
    patent_type: str,
    class_codes: list[str] | None = None,
) -> str:
    """构造供 WebSearch / 浏览器使用的 Google Patents 倾向查询串（非官方 API）。

    ``class_codes``：发明/实用用 ``CPC=B01J20/low``；外观把洛迦诺号当补充词（无稳定 loc 字段）。
    外网不通时可跳过，不作为查新失败条件。
    """
    t = normalize_patent_type(patent_type, default=TYPE_ALL)
    hint = GOOGLE_PATENTS_TYPE_HINT[t]
    parts = [keywords.strip()]
    extra = (hint.get("query_extra") or "").strip()
    if extra:
        parts.append(extra)
    codes = [c.strip() for c in (class_codes or []) if c and str(c).strip()]
    if t == TYPE_DESIGN:
        parts.extend(codes[:3])
    else:
        for c in codes[:3]:
            compact = re.sub(r"\s+", "", c)
            m = re.match(r"^([A-HY]\d{2}[A-Z]\d+)", compact, re.I)
            prefix = m.group(1) if m else compact
            if prefix:
                parts.append(f"CPC={prefix}/low")
    gp_type = (hint.get("gp_type") or "").strip()
    q = " ".join(p for p in parts if p)
    if gp_type:
        q = f"{q} type:{gp_type}"
    return q


def describe_types(types: Iterable[str] | None = None) -> str:
    return ", ".join(types or CANONICAL_TYPES)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="推断或规范化专利类型（公开号种类码 / 用户声明 / 著录关键词）"
    )
    ap.add_argument("--pub", default="", help="公开号，如 CN209861402U")
    ap.add_argument(
        "--declared",
        default="",
        help="用户声明：invention|utility_model|design|发明|实用新型|外观…",
    )
    ap.add_argument(
        "--biblio",
        default="",
        help="可选著录片段（扉页/标题栏含「实用新型」等）",
    )
    ap.add_argument("--json", action="store_true", help="只打印 JSON")
    args = ap.parse_args(argv)

    result = resolve_reader_patent_type(
        pub=args.pub or None,
        user_declared=args.declared or None,
        biblio_text=args.biblio or None,
    )
    line = json.dumps(result, ensure_ascii=False)
    if args.json:
        print(line)
    else:
        print(f"PATENT_TYPE_JSON: {line}")
        if result.get("patent_type"):
            print(
                f"PATENT_TYPE: {result['patent_type']} "
                f"({result.get('label_zh')}) source={result.get('source')}"
            )
        else:
            print("PATENT_TYPE: unknown")
    return 0 if result.get("patent_type") else 2


if __name__ == "__main__":
    raise SystemExit(main())
