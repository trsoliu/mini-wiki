# -*- coding: utf-8 -*-
"""案卷目录：工作区 outputs/docket/{case_id}/。"""
from __future__ import annotations

import os
import re
from pathlib import Path

from docket_config import load_docket_config

ENV_OUTPUT_DIR = "PATENT_DOCKET_OUTPUT_DIR"
_SLUG = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,80}$")


def default_output_root(start: Path | None = None) -> Path:
    env = (os.environ.get(ENV_OUTPUT_DIR) or "").strip()
    if env:
        return Path(env)
    here = (start or Path(__file__).resolve()).resolve()
    cursor = here if here.is_dir() else here.parent
    for parent in [cursor, *cursor.parents]:
        if (parent / ".git").exists() or (parent / "outputs").is_dir():
            sub = load_docket_config()["output_subdir"]
            return parent / "outputs" / sub
    sub = load_docket_config()["output_subdir"]
    return Path.cwd() / "outputs" / sub


def normalize_case_id(value: str) -> str:
    text = (value or "").strip().replace(" ", "-")
    if not _SLUG.match(text):
        raise ValueError("case_id 仅允许字母数字、点、下划线、连字符")
    return text


def docket_dir_for(case_id: str, *, root: Path | None = None) -> Path:
    slug = normalize_case_id(case_id)
    return (root or default_output_root()) / slug


def docket_yaml_path(case_id: str, *, root: Path | None = None) -> Path:
    return docket_dir_for(case_id, root=root) / "docket.yaml"
