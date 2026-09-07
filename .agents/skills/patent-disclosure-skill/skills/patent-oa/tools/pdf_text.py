"""审查答复：PDF / 文本抽取（审查通知书、历史答复等）。

优先数字 PDF 文本层（pymupdf）；扫描件若几乎无字会明确告警，不要求用户手贴。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


def _require_fitz():
    try:
        import fitz  # type: ignore

        return fitz
    except ImportError as exc:
        raise SystemExit(
            "PDF 解析需要 pymupdf：pip install -r skills/patent-oa/tools/requirements-oa.txt"
        ) from exc


def extract_pdf_text(path: Path, *, max_pages: int = 0) -> dict[str, Any]:
    """抽取 PDF 全文。返回 text / page_count / char_count / warnings。"""
    fitz = _require_fitz()
    path = path.expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"找不到文件: {path}")
    doc = fitz.open(path)
    try:
        n = doc.page_count
        limit = n if max_pages <= 0 else min(n, max_pages)
        parts: list[str] = []
        for i in range(limit):
            page = doc.load_page(i)
            parts.append(page.get_text("text") or "")
        text = "\n".join(parts)
        # 归一化多余空白，保留段落
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        warnings: list[str] = []
        chars = len(re.sub(r"\s+", "", text))
        if chars < 80 and n > 0:
            warnings.append(
                "extracted_text_too_short: 可能是扫描件/图片 PDF。"
                "当前仅支持文本层抽取；请提供可复制文字的 PDF，或先用 OCR 工具转成带字 PDF。"
            )
        if max_pages > 0 and n > max_pages:
            warnings.append(f"truncated_to_pages={max_pages}_of_{n}")
        return {
            "ok": True,
            "path": str(path),
            "page_count": n,
            "pages_read": limit,
            "char_count": len(text),
            "char_count_nospace": chars,
            "warnings": warnings,
            "text": text,
        }
    finally:
        doc.close()


def read_document(path: Path, *, max_pages: int = 0) -> dict[str, Any]:
    """读 PDF / md / txt。"""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"找不到文件: {path}")
    suf = path.suffix.lower()
    if suf == ".pdf":
        return extract_pdf_text(path, max_pages=max_pages)
    if suf in {".md", ".txt", ".markdown"}:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        return {
            "ok": True,
            "path": str(path),
            "page_count": 1,
            "pages_read": 1,
            "char_count": len(text),
            "char_count_nospace": len(re.sub(r"\s+", "", text)),
            "warnings": [],
            "text": text,
        }
    raise SystemExit(f"不支持的格式: {suf}（支持 .pdf / .md / .txt）")


def write_extract(
    result: dict[str, Any],
    out_text: Path,
    *,
    out_json: Path | None = None,
) -> dict[str, Any]:
    out_text = out_text.expanduser().resolve()
    out_text.parent.mkdir(parents=True, exist_ok=True)
    out_text.write_text(result.get("text") or "", encoding="utf-8")
    meta = {k: v for k, v in result.items() if k != "text"}
    meta["text_path"] = str(out_text)
    if out_json:
        out_json = out_json.expanduser().resolve()
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        meta["json_path"] = str(out_json)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="抽取审查通知书/答复 PDF（或 md/txt）为纯文本，供审查答复使用"
    )
    p.add_argument("-i", "--input", required=True, help="PDF / md / txt 路径")
    p.add_argument(
        "-o",
        "--output",
        default="",
        help="输出 .txt；默认与输入同目录 {stem}.extracted.txt",
    )
    p.add_argument("--json", default="", help="可选元数据 JSON 路径")
    p.add_argument("--max-pages", type=int, default=0, help="最多读前 N 页；0=全部")
    p.add_argument(
        "--stdout-text",
        action="store_true",
        help="同时把全文打到 stdout（大文件慎用）",
    )
    args = p.parse_args(argv)

    src = Path(args.input)
    result = read_document(src, max_pages=int(args.max_pages or 0))
    out = Path(args.output) if args.output else src.with_suffix("").with_name(
        src.stem + ".extracted.txt"
    )
    # with_suffix on pdf → stem.extracted better:
    if not args.output:
        out = src.parent / f"{src.stem}.extracted.txt"
    jpath = Path(args.json) if args.json else out.with_suffix(".json")
    meta = write_extract(result, out, out_json=jpath)
    meta["warnings"] = result.get("warnings") or []
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    if result.get("warnings"):
        for w in result["warnings"]:
            print(f"WARN: {w}", file=sys.stderr)
    if args.stdout_text:
        print(result.get("text") or "")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
