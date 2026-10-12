#!/usr/bin/env python
"""
将 PDF（.pdf）按页导出为 Markdown，并抽取页面中的嵌入图片，便于 Step 2 扫描与 Agent Read。

依赖 pymupdf（见本目录 requirements-pdf.txt；不要装进根目录 requirements.txt）。

用法:
  python pdf_to_md.py --input document.pdf --output outputs/case/document.md
  python pdf_to_md.py -i a.pdf -o b/out.md --media-dir b/slide_images

默认图片目录：与输出 .md 同级的「{md 文件名}_media/」。
Markdown 中图片跟在对应页正文之后，不堆到文末。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_PDF_REQ = "skills/patent-disclosure/tools/requirements-pdf.txt"
_SHORT_TEXT_CHARS = 80


def _require_fitz():
    try:
        import fitz
    except ImportError:
        print(
            f"缺少依赖 pymupdf。请执行: pip install -r {_PDF_REQ}",
            file=sys.stderr,
        )
        sys.exit(1)
    return fitz


def _rel_media_path(out_file: Path, media_file: Path) -> str:
    try:
        return media_file.relative_to(out_file.parent).as_posix()
    except ValueError:
        return media_file.as_posix()


def _page_text(page) -> str:
    text = page.get_text("text") or ""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _run(input_pdf: Path, output_md: Path, media_dir: Path | None) -> int:
    if not input_pdf.is_file():
        print(f"输入文件不存在: {input_pdf}", file=sys.stderr)
        return 2
    suf = input_pdf.suffix.lower()
    if suf != ".pdf":
        print("警告: 期望 .pdf 文件。", file=sys.stderr)

    fitz = _require_fitz()

    output_md = output_md.resolve()
    output_md.parent.mkdir(parents=True, exist_ok=True)

    if media_dir is None:
        media_dir = output_md.parent / f"{output_md.stem}_media"
    else:
        media_dir = media_dir.resolve()

    try:
        doc = fitz.open(input_pdf)
    except Exception as e:
        print(f"无法打开 PDF: {e}", file=sys.stderr)
        return 3

    lines: list[str] = [
        f"<!-- 由 pdf_to_md.py 自 {input_pdf.name} 转换，勿手改本行元信息 -->\n"
    ]
    img_counter = 0
    n_images = 0
    text_parts: list[str] = []

    try:
        if doc.page_count == 0:
            print("PDF 没有页面。", file=sys.stderr)
            return 4
        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            sn = page_idx + 1
            lines.append(f"\n## 第 {sn} 页\n")
            text = _page_text(page)
            if text:
                lines.append(text)
                lines.append("\n\n")
                text_parts.append(text)
            for image in page.get_images(full=True):
                try:
                    xref = image[0]
                    base_image = doc.extract_image(xref)
                    blob = (base_image or {}).get("image")
                    if not blob:
                        continue
                    ext = (base_image.get("ext") or "png").lower()
                    if ext == "jpeg":
                        ext = "jpg"
                    img_counter += 1
                    fname = f"slide{sn:02d}_img{img_counter:04d}.{ext}"
                    media_dir.mkdir(parents=True, exist_ok=True)
                    out_img = media_dir / fname
                    out_img.write_bytes(blob)
                    rel = _rel_media_path(output_md, out_img)
                    lines.append(f"\n![]({rel})\n")
                    n_images += 1
                except Exception as e:
                    print(f"警告: 第 {sn} 页抽取图片失败: {e}", file=sys.stderr)
    finally:
        doc.close()

    nospace = len(re.sub(r"\s+", "", "".join(text_parts)))
    if nospace == 0 and n_images == 0:
        print(
            "未抽出文本或图片。可能是空文件、扫描件且无嵌入图，或需先 OCR。",
            file=sys.stderr,
        )
        return 4
    if nospace < _SHORT_TEXT_CHARS:
        print(
            "警告: 抽出文字过少，可能是扫描件/图片 PDF。"
            "当前仅支持文本层；请提供可复制文字的 PDF，或先 OCR。",
            file=sys.stderr,
        )

    output_md.write_text("".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"已写入: {output_md}")
    print(f"图片目录: {media_dir}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="PDF → Markdown + 抽取图片")
    p.add_argument("-i", "--input", required=True, type=Path, help="输入 .pdf 路径")
    p.add_argument("-o", "--output", required=True, type=Path, help="输出 .md 路径")
    p.add_argument(
        "--media-dir",
        type=Path,
        default=None,
        help="图片输出目录（默认：与 .md 同级的 {md 主名}_media）",
    )
    args = p.parse_args()
    return _run(args.input, args.output, args.media_dir)


if __name__ == "__main__":
    raise SystemExit(main())
