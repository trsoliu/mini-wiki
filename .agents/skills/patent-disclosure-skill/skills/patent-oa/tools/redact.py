"""案例文本轻量脱敏（规则型；入库前仍须人审）。"""
from __future__ import annotations

import re
from typing import Iterable

# 常见公司后缀 / 占位
_COMPANY = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9]{2,40}?(?:有限公司|股份有限公司|集团有限公司|科技有限公司|有限责任公司))"
)
_APP_NO = re.compile(r"\b(CN)?\d{9,13}\.?\d?\b")
_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_IDCARD = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")


def redact_text(
    text: str,
    *,
    extra_names: Iterable[str] | None = None,
    hash_app_nos: bool = True,
) -> tuple[str, list[str]]:
    """返回 (脱敏文本, 变更摘要列表)。"""
    notes: list[str] = []
    out = text or ""

    def _sub_company(m: re.Match[str]) -> str:
        notes.append(f"company→申请人甲:{m.group(1)[:16]}")
        return "申请人甲"

    out2, n = _COMPANY.subn(_sub_company, out)
    out = out2
    if n:
        notes.append(f"company_replacements={n}")

    for name in extra_names or []:
        name = (name or "").strip()
        if len(name) >= 2 and name in out:
            out = out.replace(name, "【脱敏姓名】")
            notes.append(f"name={name[:8]}")

    if hash_app_nos:
        def _app(m: re.Match[str]) -> str:
            notes.append("app_no_redacted")
            return "CNXXXXXXXXXX.X"

        out, n = _APP_NO.subn(_app, out)
        if n:
            notes.append(f"app_no_count={n}")

    out, n = _PHONE.subn("【电话已脱敏】", out)
    if n:
        notes.append(f"phone={n}")
    out, n = _EMAIL.subn("redacted@example.com", out)
    if n:
        notes.append(f"email={n}")
    out, n = _IDCARD.subn("【证件号已脱敏】", out)
    if n:
        notes.append(f"id={n}")

    return out, notes
