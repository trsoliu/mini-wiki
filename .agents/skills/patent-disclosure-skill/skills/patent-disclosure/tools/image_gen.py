# -*- coding: utf-8 -*-
"""Shared lineart generation planner for design + utility_model.

Disclosure lineart has exactly two origins:
  1. existing material already marked kind=lineart and scoring pass
  2. host LLM generation (img2img first; if unavailable, describe then txt2img)

CAD projections (kind=cad) are ordinary source material only. They never skip
generation, never count as lineart, and never enter the disclosure as-is.
Design disclosures also embed clean product photos (photo_clean) in md+docx.

  python tools/image_gen.py --case-dir outputs/case
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

_SHARED = Path(__file__).resolve().parent
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

IMAGE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
}

LINEART_KIND = "lineart"
CAD_KIND = "cad"
PHOTO_CLEAN_KIND = "photo_clean"
SOURCE_KINDS = ("photo_clean", "cad", "other", "photo_scene")
MIN_LINEART_SCORE = 70.0
MIN_SOURCE_SCORE = 50.0
SKIP_ENV = "PATENT_SKILL_SKIP_LINEART"

GEN_EXISTING = "existing_lineart"
GEN_IMG2IMG = "img2img"
GEN_TXT2IMG = "txt2img"
FALLBACK = "describe_then_txt2img"


def parse_skip(cli_skip: bool = False) -> bool:
    if cli_skip:
        return True
    return os.environ.get(SKIP_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def resolve_path(case_dir: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_file():
        return path.resolve()
    cand = (case_dir / raw).resolve()
    if cand.is_file():
        return cand
    return path


def file_ok(case_dir: Path, raw: str) -> bool:
    p = resolve_path(case_dir, raw)
    return p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES


def composite_score(fig: dict[str, Any]) -> float:
    """0.5 * relevance + 0.5 * quality; else ``score``."""
    try:
        rel = fig.get("relevance")
        qual = fig.get("quality")
        if rel is not None and qual is not None:
            return 0.5 * float(rel) + 0.5 * float(qual)
        return float(fig.get("score") or 0)
    except (TypeError, ValueError):
        return 0.0


def _kind(fig: dict[str, Any]) -> str:
    return str(fig.get("kind") or "").strip().lower()


def _role(fig: dict[str, Any]) -> str:
    return str(fig.get("role") or "").strip().lower()


def is_qualified_existing_lineart(fig: dict[str, Any], case_dir: Path) -> bool:
    """Path 1: material already is real lineart and scoring pass. CAD never qualifies."""
    if _kind(fig) != LINEART_KIND:
        return False
    if _role(fig) == "rejected":
        return False
    if composite_score(fig) < MIN_LINEART_SCORE:
        return False
    try:
        rel = fig.get("relevance")
        qual = fig.get("quality")
        if rel is not None and float(rel) < MIN_LINEART_SCORE:
            return False
        if qual is not None and float(qual) < MIN_LINEART_SCORE:
            return False
    except (TypeError, ValueError):
        return False
    raw = str(fig.get("path") or "").strip()
    return bool(raw) and file_ok(case_dir, raw)


def is_design_photo_for_disclosure(fig: dict[str, Any], case_dir: Path) -> bool:
    """Design disclosures embed clean product photos in md+docx. CAD never qualifies."""
    if _kind(fig) != PHOTO_CLEAN_KIND:
        return False
    if _role(fig) == "rejected":
        return False
    if composite_score(fig) < MIN_SOURCE_SCORE:
        return False
    raw = str(fig.get("path") or "").strip()
    return bool(raw) and file_ok(case_dir, raw)


def pick_design_photos(plan: dict[str, Any], case_dir: Path) -> list[dict[str, Any]]:
    out = []
    for fig in plan.get("figures") or []:
        if isinstance(fig, dict) and is_design_photo_for_disclosure(fig, case_dir):
            item = dict(fig)
            item["resolved_path"] = str(resolve_path(case_dir, str(fig.get("path") or "")))
            item["composite_score"] = composite_score(fig)
            out.append(item)
    return out


def is_source_candidate(fig: dict[str, Any], case_dir: Path) -> bool:
    """Ordinary material that may feed img2img. Includes CAD. Excludes lineart."""
    if _kind(fig) == LINEART_KIND:
        return False
    if _role(fig) == "rejected":
        return False
    if composite_score(fig) < MIN_SOURCE_SCORE:
        return False
    raw = str(fig.get("path") or "").strip()
    return bool(raw) and file_ok(case_dir, raw)


def _source_rank(fig: dict[str, Any]) -> tuple[int, float]:
    kind = _kind(fig)
    bucket = {"photo_clean": 0, "cad": 1, "other": 2, "photo_scene": 3}.get(kind, 2)
    return (bucket, -composite_score(fig))


def pick_sources(plan: dict[str, Any], case_dir: Path, *, limit: int = 4) -> list[dict[str, Any]]:
    cands = [
        fig
        for fig in (plan.get("figures") or [])
        if isinstance(fig, dict) and is_source_candidate(fig, case_dir)
    ]
    cands.sort(key=_source_rank)
    out = []
    for fig in cands[:limit]:
        item = dict(fig)
        item["resolved_path"] = str(resolve_path(case_dir, str(fig.get("path") or "")))
        item["composite_score"] = composite_score(fig)
        out.append(item)
    return out


def qualified_lineart(plan: dict[str, Any], case_dir: Path) -> list[dict[str, Any]]:
    out = []
    for fig in plan.get("figures") or []:
        if isinstance(fig, dict) and is_qualified_existing_lineart(fig, case_dir):
            item = dict(fig)
            item["resolved_path"] = str(resolve_path(case_dir, str(fig.get("path") or "")))
            item["composite_score"] = composite_score(fig)
            out.append(item)
    return out


def decide_mode(plan: dict[str, Any], case_dir: Path) -> dict[str, Any]:
    """Return planner JSON for Agent: existing_lineart | img2img | txt2img."""
    existing = qualified_lineart(plan, case_dir)
    sources = pick_sources(plan, case_dir)
    cad_only_sources = [s for s in sources if _kind(s) == CAD_KIND]
    patent_type = str(plan.get("patent_type") or "").strip().lower()
    design_photos = pick_design_photos(plan, case_dir) if patent_type == "design" else []
    if existing:
        mode = GEN_EXISTING
        fallback = ""
    elif sources:
        mode = GEN_IMG2IMG
        fallback = FALLBACK
    else:
        mode = GEN_TXT2IMG
        fallback = ""
    return {
        "ok": True,
        "mode": mode,
        "fallback": fallback,
        "skip_generation": mode == GEN_EXISTING,
        "patent_type": patent_type,
        "cad_never_lineart": True,
        "cad_never_in_disclosure": True,
        "design_photos_in_disclosure": patent_type == "design",
        "qualified_lineart": existing,
        "source_images": sources,
        "design_photos": design_photos,
        "cad_as_material_only": cad_only_sources,
        "rules": {
            "lineart_origins": [GEN_EXISTING, "llm_img2img_or_txt2img"],
            "img2img_unavailable": FALLBACK,
            "min_lineart_score": MIN_LINEART_SCORE,
            "min_source_score": MIN_SOURCE_SCORE,
            "design_embed_md_and_docx": ["photo_clean", "lineart"],
            "utility_embed": ["lineart"],
        },
    }


def attach_job_mode(job: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Stamp a lineart job with gen_mode. CAD paths in sources stay material."""
    out = dict(job)
    refs = [p for p in (job.get("source_paths") or job.get("reference_images") or []) if p]
    if decision.get("mode") == GEN_EXISTING:
        out["gen_mode"] = GEN_EXISTING
        out["fallback_mode"] = ""
        out["forbid_text_only"] = True
    elif refs:
        out["gen_mode"] = GEN_IMG2IMG
        out["fallback_mode"] = FALLBACK
        out["forbid_text_only"] = False
        out["host_hint"] = (
            "Prefer img2img with reference_images. If the host cannot img2img, "
            "write a detailed description of each reference (describe_path) then txt2img. "
            "Do not put CAD/SVG/PNG into the disclosure as lineart."
        )
    else:
        out["gen_mode"] = GEN_TXT2IMG
        out["fallback_mode"] = ""
        out["forbid_text_only"] = False
        out["host_hint"] = (
            "No usable source image. txt2img from gen_prompt + schema text. "
            "Do not invent CAD as a substitute for lineart."
        )
    return out


def load_plan(case_dir: Path) -> dict[str, Any] | None:
    for name in ("figure_plan.yaml", "figure_plan.yml", "figure_plan.json"):
        p = case_dir / name
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            if p.suffix.lower() in {".yaml", ".yml"}:
                try:
                    import yaml  # type: ignore

                    data = yaml.safe_load(text)
                except Exception:
                    data = json.loads(text)
            else:
                data = json.loads(text)
            return data if isinstance(data, dict) else None
    return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Plan lineart: existing vs img2img vs txt2img")
    p.add_argument("--case-dir", type=Path, required=True)
    args = p.parse_args(argv)
    case_dir = args.case_dir.resolve()
    if not case_dir.is_dir():
        print(json.dumps({"ok": False, "error": f"missing dir: {case_dir}"}), file=sys.stderr)
        return 2
    plan = load_plan(case_dir) or {"figures": []}
    decision = decide_mode(plan, case_dir)
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    print(
        f"IMAGE_GEN: mode={decision['mode']} skip={str(decision['skip_generation']).lower()}",
        file=sys.stderr,
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
