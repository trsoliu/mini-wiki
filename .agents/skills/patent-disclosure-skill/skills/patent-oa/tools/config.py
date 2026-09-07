"""审查答复：嵌入与 sqlite 路径配置。

默认落盘在操作系统「文档」目录：
  {Documents}/patent-disclosure-skill/oa/embedding.config.yaml
  {Documents}/patent-disclosure-skill/oa/data/oa_vectors.sqlite

可用环境变量 PATENT_OA_HOME 覆盖整个 oa 根目录。
本包 docs/embedding.config.yaml 仅作模板种子。

多厂商 preset：zhipu / dashscope / openai / minimax / local
向量模型可选：可 skip；中途 enable 后若模型变更须重建索引。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
REPO_TEMPLATE = ROOT / "docs" / "embedding.config.yaml"

PRESETS: dict[str, dict[str, Any]] = {
    "zhipu": {
        "provider": "openai_compatible",
        "model": "embedding-3",
        "dimensions": 1024,
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key_env": "ZHIPUAI_API_KEY",
        "group_id_env": "",
        "note_zh": "智谱 embedding-3（OpenAI 兼容）；维度可选 256/512/1024/2048。",
    },
    "dashscope": {
        "provider": "openai_compatible",
        "model": "text-embedding-v3",
        "dimensions": 1024,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "api_key_env": "DASHSCOPE_API_KEY",
        "group_id_env": "",
        "note_zh": "通义 DashScope text-embedding-v3（OpenAI 兼容）。",
    },
    "openai": {
        "provider": "openai_compatible",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "group_id_env": "",
        "note_zh": "海外 OpenAI text-embedding-3-small。",
    },
    "minimax": {
        "provider": "minimax",
        "model": "embo-01",
        "dimensions": 1536,
        "base_url": "https://api.minimaxi.com/v1/embeddings",
        "api_key_env": "MINIMAX_API_KEY",
        "group_id_env": "MINIMAX_GROUP_ID",
        "note_zh": "MiniMax embo-01（专用接口，非 OpenAI 兼容；需 API Key + GroupId）。",
    },
    "local": {
        "provider": "local",
        "model": "BAAI/bge-small-zh-v1.5",
        "dimensions": 512,
        "base_url": "",
        "api_key_env": "",
        "group_id_env": "",
        "note_zh": "本地 sentence-transformers；案例不出库；首次会下载模型。",
    },
}

RECOMMENDED_PRESET = "zhipu"
RECOMMENDED = {
    **{k: PRESETS[RECOMMENDED_PRESET][k] for k in (
        "provider", "model", "dimensions", "base_url", "api_key_env", "group_id_env"
    )},
    "preset": RECOMMENDED_PRESET,
    "rationale_zh": (
        "向量模型可选。推荐启用时用智谱 embedding-3；"
        "也可 skip，仅靠 Obsidian 标签/字段检索；中途可再 enable 并重建索引。"
    ),
}


def documents_dir() -> Path:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            CSIDL_PERSONAL = 5
            SHGFP_TYPE_CURRENT = 0
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            hr = ctypes.windll.shell32.SHGetFolderPathW(
                None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf
            )
            if hr == 0 and buf.value:
                p = Path(buf.value)
                if p.is_dir() or p.parent.is_dir():
                    return p
        except Exception:
            pass
        known = os.environ.get("USERPROFILE") or os.environ.get("HOME")
        if known:
            return Path(known) / "Documents"
    xdg = (os.environ.get("XDG_DOCUMENTS_DIR") or "").strip()
    if xdg:
        return Path(xdg).expanduser()
    return Path.home() / "Documents"


def oa_home() -> Path:
    env = (os.environ.get("PATENT_OA_HOME") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (documents_dir() / "patent-disclosure-skill" / "oa").resolve()


def default_config_path() -> Path:
    return oa_home() / "embedding.config.yaml"


def default_sqlite_path() -> Path:
    return oa_home() / "data" / "oa_vectors.sqlite"


def default_cases_dir() -> Path:
    return oa_home() / "cases"


def default_secrets_path() -> Path:
    """API Key 等敏感项：仅写在用户文档目录，勿提交仓库。"""
    return oa_home() / "embedding.secrets.yaml"


def load_secrets(path: str | Path | None = None) -> dict[str, Any]:
    sp = Path(path).expanduser().resolve() if path else default_secrets_path()
    if not sp.is_file():
        return {}
    data = _load_yaml(sp)
    return data if isinstance(data, dict) else {}


def write_secrets(
    *,
    api_key: str = "",
    group_id: str = "",
    path: str | Path | None = None,
    merge: bool = True,
) -> Path:
    sp = Path(path).expanduser().resolve() if path else default_secrets_path()
    existing: dict[str, Any] = load_secrets(sp) if merge and sp.is_file() else {}
    if api_key.strip():
        existing["api_key"] = api_key.strip()
    if group_id.strip():
        existing["group_id"] = group_id.strip()
    existing["note_zh"] = "本文件含密钥，仅保存在本机文档目录；勿提交 git、勿发到公开聊天记录外泄。"
    _dump_yaml(sp, existing)
    return sp


def resolve_api_key(cfg: dict[str, Any]) -> str:
    """优先环境变量，其次文档目录 secrets 文件。"""
    env_name = str(cfg.get("api_key_env") or "").strip()
    if env_name:
        key = os.environ.get(env_name, "").strip()
        if key:
            return key
    secrets = load_secrets()
    return str(secrets.get("api_key") or "").strip()


def resolve_group_id(cfg: dict[str, Any]) -> str:
    if str(cfg.get("group_id") or "").strip():
        return str(cfg.get("group_id")).strip()
    env_name = str(cfg.get("group_id_env") or "MINIMAX_GROUP_ID").strip()
    if env_name:
        gid = os.environ.get(env_name, "").strip()
        if gid:
            return gid
    secrets = load_secrets()
    return str(secrets.get("group_id") or "").strip()


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("需要 PyYAML：pip install -r skills/patent-oa/tools/requirements-oa.txt") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"配置须为 mapping: {path}")
    return data


def _dump_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("需要 PyYAML：pip install -r skills/patent-oa/tools/requirements-oa.txt") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def ensure_seed_config(path: Path | None = None) -> Path:
    cfg_path = path or default_config_path()
    if cfg_path.is_file():
        return cfg_path
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if REPO_TEMPLATE.is_file():
        shutil.copy2(REPO_TEMPLATE, cfg_path)
    else:
        _dump_yaml(cfg_path, _default_template_dict())
    return cfg_path


def _default_template_dict() -> dict[str, Any]:
    return {
        "version": 1,
        "user_confirmed": False,
        "vector_enabled": False,
        "embedding_timeout_sec": 30,
        "embedding_fingerprint": "",
        "preset": RECOMMENDED_PRESET,
        "provider": RECOMMENDED["provider"],
        "model": RECOMMENDED["model"],
        "dimensions": RECOMMENDED["dimensions"],
        "base_url": RECOMMENDED["base_url"],
        "api_key_env": RECOMMENDED["api_key_env"],
        "group_id_env": RECOMMENDED.get("group_id_env") or "",
        "sqlite_path": str(default_sqlite_path()),
        "obsidian_cases_dir": "oa/cases",
        "obsidian_oa_dir": "oa",
        "default_top_k": 5,
    }


def resolve_config_path(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return default_config_path()


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg_path = resolve_config_path(path)
    if not cfg_path.is_file():
        if path:
            raise SystemExit(f"缺少配置文件: {cfg_path}")
        ensure_seed_config(cfg_path)
    data = _load_yaml(cfg_path)
    data["_config_path"] = str(cfg_path)
    data["_oa_home"] = str(oa_home())
    data["_documents_dir"] = str(documents_dir())
    data.setdefault("provider", RECOMMENDED["provider"])
    data.setdefault("model", RECOMMENDED["model"])
    data.setdefault("dimensions", RECOMMENDED["dimensions"])
    data.setdefault("sqlite_path", str(default_sqlite_path()))
    data.setdefault("obsidian_cases_dir", "oa/cases")
    data.setdefault("obsidian_oa_dir", "oa")
    data.setdefault("default_top_k", 5)
    data.setdefault("base_url", RECOMMENDED.get("base_url") or "")
    data.setdefault("api_key_env", RECOMMENDED.get("api_key_env") or "ZHIPUAI_API_KEY")
    data.setdefault("group_id_env", "")
    data.setdefault("group_id", "")
    data.setdefault("minimax_embed_type", "")
    data.setdefault("preset", "")
    data.setdefault("user_confirmed", False)
    data.setdefault("vector_enabled", False)
    data.setdefault("embedding_timeout_sec", 30)
    data.setdefault("embedding_fingerprint", "")
    return data


def needs_user_confirm(cfg: dict[str, Any] | None = None, path: str | Path | None = None) -> bool:
    data = cfg if cfg is not None else load_config(path)
    return not bool(data.get("user_confirmed"))


def is_vector_enabled(cfg: dict[str, Any] | None = None, path: str | Path | None = None) -> bool:
    data = cfg if cfg is not None else load_config(path)
    return bool(data.get("vector_enabled"))


def embedding_fingerprint(cfg: dict[str, Any]) -> str:
    return "|".join(
        [
            str(cfg.get("provider") or ""),
            str(cfg.get("model") or ""),
            str(int(cfg.get("dimensions") or 0)),
            str(cfg.get("base_url") or ""),
        ]
    )


def check_rebuild_needed(cfg: dict[str, Any] | None = None, path: str | Path | None = None) -> dict[str, Any]:
    """首次启用或模型变更时提示重建。"""
    data = cfg if cfg is not None else load_config(path)
    if not data.get("vector_enabled"):
        return {
            "needed": False,
            "reason": "vector_disabled",
            "ask_zh": "",
        }
    current = embedding_fingerprint(data)
    stored = str(data.get("embedding_fingerprint") or "")
    if not stored:
        return {
            "needed": True,
            "reason": "first_enable",
            "current_fingerprint": current,
            "stored_fingerprint": "",
            "ask_zh": (
                "向量检索已开启，但尚未建立索引。是否扫描 Obsidian `oa/cases`（及本地回退目录）"
                "重建向量？回复「确认重建」后执行："
                "python skills/patent-oa/tools/rebuild_vectors.py --confirm"
            ),
        }
    if stored != current:
        return {
            "needed": True,
            "reason": "model_changed",
            "current_fingerprint": current,
            "stored_fingerprint": stored,
            "ask_zh": (
                "检测到向量模型/维度/接口已变更，旧索引不兼容。"
                "是否重建全部案例向量？回复「确认重建」后执行："
                "python skills/patent-oa/tools/rebuild_vectors.py --confirm"
            ),
        }
    return {
        "needed": False,
        "reason": "ok",
        "current_fingerprint": current,
        "stored_fingerprint": stored,
        "ask_zh": "",
    }


def sqlite_path_from_config(cfg: dict[str, Any]) -> Path:
    raw = str(cfg.get("sqlite_path") or default_sqlite_path())
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = oa_home() / p
    return p.resolve()


def _infer_api_key_env(provider: str, model: str, base_url: str, existing: dict) -> str:
    blob = f"{base_url} {model}".lower()
    if provider == "local":
        return ""
    if provider == "minimax" or "minimax" in blob or model.startswith("embo"):
        return "MINIMAX_API_KEY"
    if "bigmodel" in blob or model in ("embedding-3", "embedding-2"):
        return "ZHIPUAI_API_KEY"
    if "dashscope" in blob or model.startswith("text-embedding-v"):
        return "DASHSCOPE_API_KEY"
    if "openai.com" in blob or model.startswith("text-embedding-3"):
        return "OPENAI_API_KEY"
    if provider == "openai_compatible":
        return str(existing.get("api_key_env") or "ZHIPUAI_API_KEY")
    return str(existing.get("api_key_env") or "")


def _patch_config(path: Path | None, updates: dict[str, Any]) -> Path:
    cfg_path = resolve_config_path(path)
    existing: dict[str, Any] = {}
    if cfg_path.is_file():
        existing = _load_yaml(cfg_path)
    elif REPO_TEMPLATE.is_file() and not path:
        existing = _load_yaml(REPO_TEMPLATE)
    else:
        existing = _default_template_dict()
    existing.update(updates)
    _dump_yaml(cfg_path, existing)
    return cfg_path


def write_config(
    *,
    provider: str,
    model: str,
    dimensions: int,
    path: str | Path | None = None,
    base_url: str = "",
    api_key_env: str = "",
    sqlite_path: str = "",
    group_id_env: str = "",
    group_id: str = "",
    preset: str = "",
    vector_enabled: bool | None = None,
    clear_fingerprint_on_change: bool = True,
) -> Path:
    cfg_path = resolve_config_path(path)
    existing: dict[str, Any] = {}
    if cfg_path.is_file():
        existing = _load_yaml(cfg_path)
    elif REPO_TEMPLATE.is_file() and not path:
        existing = _load_yaml(REPO_TEMPLATE)

    if not base_url:
        if provider == "openai_compatible":
            base_url = existing.get("base_url") or RECOMMENDED["base_url"]
        elif provider == "minimax":
            base_url = existing.get("base_url") or PRESETS["minimax"]["base_url"]

    if not api_key_env:
        api_key_env = _infer_api_key_env(provider, model, base_url or "", existing)

    if provider == "minimax" and not group_id_env:
        group_id_env = existing.get("group_id_env") or "MINIMAX_GROUP_ID"

    sqlite_default = str(default_sqlite_path())
    ve = (
        bool(vector_enabled)
        if vector_enabled is not None
        else True  # 显式 set 模型时默认开启向量
    )
    new_fp_parts = {
        "provider": provider,
        "model": model,
        "dimensions": int(dimensions),
        "base_url": base_url if provider != "local" else "",
    }
    old_fp = embedding_fingerprint(
        {
            "provider": existing.get("provider"),
            "model": existing.get("model"),
            "dimensions": existing.get("dimensions"),
            "base_url": existing.get("base_url"),
        }
    )
    new_fp = embedding_fingerprint(new_fp_parts)
    fingerprint = str(existing.get("embedding_fingerprint") or "")
    if clear_fingerprint_on_change and old_fp and old_fp != new_fp:
        fingerprint = ""  # 强制提示重建

    existing.update(
        {
            "version": int(existing.get("version") or 1),
            "user_confirmed": True,
            "vector_enabled": ve,
            "embedding_timeout_sec": int(existing.get("embedding_timeout_sec") or 30),
            "embedding_fingerprint": fingerprint,
            "preset": preset or existing.get("preset") or "",
            "provider": provider,
            "model": model,
            "dimensions": int(dimensions),
            "base_url": base_url if provider != "local" else "",
            "api_key_env": api_key_env if provider != "local" else "",
            "group_id_env": group_id_env if provider == "minimax" else "",
            "group_id": group_id if provider == "minimax" else (existing.get("group_id") or ""),
            "minimax_embed_type": existing.get("minimax_embed_type") or "",
            "sqlite_path": sqlite_path or existing.get("sqlite_path") or sqlite_default,
            "obsidian_cases_dir": existing.get("obsidian_cases_dir") or "oa/cases",
            "default_top_k": int(existing.get("default_top_k") or 5),
        }
    )
    _dump_yaml(cfg_path, existing)
    return cfg_path


def skip_vector(path: str | Path | None = None) -> Path:
    """跳过向量模型：仅标签检索工作流。"""
    return _patch_config(
        Path(path) if path else None,
        {
            "version": 1,
            "user_confirmed": True,
            "vector_enabled": False,
            "embedding_timeout_sec": 30,
            "embedding_fingerprint": "",
            "sqlite_path": str(default_sqlite_path()),
            "obsidian_cases_dir": "oa/cases",
            "default_top_k": 5,
        },
    )


def set_vector_enabled(enabled: bool, path: str | Path | None = None) -> Path:
    cfg_path = resolve_config_path(path)
    existing = _load_yaml(cfg_path) if cfg_path.is_file() else _default_template_dict()
    existing["vector_enabled"] = bool(enabled)
    existing["user_confirmed"] = True
    if enabled and not existing.get("embedding_fingerprint"):
        # 保持 fingerprint 空 → check_rebuild_needed 会提示
        pass
    if not enabled:
        existing["embedding_fingerprint"] = ""
    _dump_yaml(cfg_path, existing)
    return cfg_path


def mark_fingerprint_built(path: str | Path | None = None, cfg: dict[str, Any] | None = None) -> str:
    data = cfg if cfg is not None else load_config(path)
    fp = embedding_fingerprint(data)
    cfg_path = resolve_config_path(path or data.get("_config_path"))
    existing = _load_yaml(cfg_path) if cfg_path.is_file() else {}
    existing["embedding_fingerprint"] = fp
    existing["vector_enabled"] = True
    existing["user_confirmed"] = True
    _dump_yaml(cfg_path, existing)
    return fp


def apply_preset(preset: str, path: str | Path | None = None, *, vector_enabled: bool = True) -> Path:
    key = (preset or "").strip().lower()
    if key not in PRESETS:
        raise SystemExit(f"未知 preset: {preset}；可选: {', '.join(PRESETS)}")
    p = PRESETS[key]
    return write_config(
        provider=str(p["provider"]),
        model=str(p["model"]),
        dimensions=int(p["dimensions"]),
        path=path,
        base_url=str(p.get("base_url") or ""),
        api_key_env=str(p.get("api_key_env") or ""),
        group_id_env=str(p.get("group_id_env") or ""),
        preset=key,
        vector_enabled=vector_enabled,
    )


def recommend_payload() -> dict[str, Any]:
    cfg_path = str(default_config_path())
    alts = []
    for name, p in PRESETS.items():
        if name == RECOMMENDED_PRESET:
            continue
        alts.append({"preset": name, **p})
    return {
        "recommended": RECOMMENDED,
        "presets": {k: v for k, v in PRESETS.items()},
        "alternatives": alts,
        "providers": ["local", "openai_compatible", "minimax"],
        "vector_optional": True,
        "paths": {
            "documents_dir": str(documents_dir()),
            "oa_home": str(oa_home()),
            "config": cfg_path,
            "sqlite": str(default_sqlite_path()),
            "cases_fallback": str(default_cases_dir()),
        },
        "ask_user_zh": (
            "审查答复 · 向量配置（对话交互，向量可选）：\n"
            "请回复：\n"
            "0) 跳过向量（仅标签检索）\n"
            "1) 采用推荐预设智谱 embedding-3（随后请提供 API Key）\n"
            "2) 其他预设：dashscope / minimax / local / openai\n"
            "3) 自定义：请提供 base_url、model、dimensions，以及 API Key\n"
            "Agent 将写入文档目录配置；Key 写入 embedding.secrets.yaml（不进仓库），"
            "然后自动跑 selftest 自检。\n"
            f"配置路径：{cfg_path}"
        ),
        "dialogue_zh": (
            "对话步骤见 skills/patent-oa/prompts/configure_embedding.md："
            "问答收集 → 写配置/secrets → selftest → 如需重建再确认。"
        ),
        "secrets_path": str(default_secrets_path()),
        "default_config_path": cfg_path,
    }


def run_selftest(path: str | Path | None = None) -> dict[str, Any]:
    """对当前配置做一次极短 embedding 自检。"""
    import time

    from embed import EmbedError, Embedder

    cfg = load_config(path)
    out: dict[str, Any] = {
        "vector_enabled": bool(cfg.get("vector_enabled")),
        "provider": cfg.get("provider"),
        "model": cfg.get("model"),
        "base_url": cfg.get("base_url"),
        "config_path": cfg.get("_config_path"),
        "secrets_path": str(default_secrets_path()),
        "has_api_key": bool(resolve_api_key(cfg)) if cfg.get("provider") != "local" else None,
    }
    if not cfg.get("vector_enabled"):
        out.update({"ok": True, "skipped": True, "reason": "vector_disabled", "note_zh": "未启用向量，跳过自检。"})
        return out
    if cfg.get("provider") != "local" and not resolve_api_key(cfg):
        out.update(
            {
                "ok": False,
                "skipped": False,
                "error": "missing_api_key",
                "note_zh": "缺少 API Key：请在对话中提供，或写入 embedding.secrets.yaml / 环境变量。",
            }
        )
        return out
    t0 = time.perf_counter()
    try:
        emb = Embedder(cfg, config_path=str(path) if path else None)
        vec = emb.embed_one("专利审查意见通知书 创造性 自检", purpose="query")
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        out.update(
            {
                "ok": True,
                "skipped": False,
                "dim": int(vec.shape[0]),
                "elapsed_ms": elapsed_ms,
                "timeout_sec": cfg.get("embedding_timeout_sec"),
                "note_zh": "自检通过：已成功调用向量模型。",
            }
        )
        return out
    except EmbedError as exc:
        out.update(
            {
                "ok": False,
                "skipped": False,
                "error": str(exc),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                "note_zh": "自检失败：请检查 base_url / model / API Key / 网络；仍可用标签检索。",
            }
        )
        return out
    except Exception as exc:
        out.update(
            {
                "ok": False,
                "skipped": False,
                "error": str(exc),
                "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                "note_zh": "自检异常。",
            }
        )
        return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name, help_zh in (
        ("recommend", "打印推荐选型与全部 preset（JSON）"),
        ("show", "显示当前配置（不含密钥明文）"),
        ("status", "向量开关 + 是否需重建"),
        ("selftest", "对当前向量配置做一次短文本自检"),
    ):
        p = sub.add_parser(name, help=help_zh)
        p.add_argument("--config", default="")

    p_seed = sub.add_parser("seed", help="将仓库模板复制到文档目录（若不存在）")
    p_seed.add_argument("--config", default="")
    p_seed.add_argument("--force", action="store_true")

    p_skip = sub.add_parser("skip-vector", help="跳过向量模型（仅标签检索）")
    p_skip.add_argument("--config", default="")

    p_en = sub.add_parser("enable-vector", help="开启向量（可附 --preset）")
    p_en.add_argument("--config", default="")
    p_en.add_argument("--preset", default="", choices=tuple(PRESETS.keys()))

    p_dis = sub.add_parser("disable-vector", help="关闭向量检索")
    p_dis.add_argument("--config", default="")

    p_set = sub.add_parser("set", help="写入模型配置（默认开启向量）")
    p_set.add_argument("--config", default="")
    p_set.add_argument("--preset", default="", choices=tuple(PRESETS.keys()))
    p_set.add_argument("--provider", default="", choices=("local", "openai_compatible", "minimax"))
    p_set.add_argument("--model", default="")
    p_set.add_argument("--dimensions", type=int, default=0)
    p_set.add_argument("--base-url", default="")
    p_set.add_argument("--api-key-env", default="")
    p_set.add_argument("--group-id-env", default="")
    p_set.add_argument("--group-id", default="")
    p_set.add_argument("--sqlite-path", default="")
    p_set.add_argument("--no-vector", action="store_true", help="写模型但不开启向量")
    p_set.add_argument(
        "--api-key",
        default="",
        help="写入文档目录 embedding.secrets.yaml（勿提交 git）",
    )
    p_set.add_argument(
        "--secret-group-id",
        default="",
        help="MiniMax GroupId 写入 secrets（可与 --group-id 二选一）",
    )
    p_set.add_argument(
        "--run-selftest",
        action="store_true",
        help="写入后立即跑 selftest",
    )

    args = parser.parse_args(argv)
    cfg_arg = getattr(args, "config", "") or None

    if args.cmd == "recommend":
        print(json.dumps(recommend_payload(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "seed":
        target = resolve_config_path(cfg_arg)
        if target.is_file() and not args.force:
            print(json.dumps({"ok": True, "config_path": str(target), "seeded": False}, ensure_ascii=False))
            return 0
        if args.force and target.is_file():
            target.unlink()
        path = ensure_seed_config(target)
        print(json.dumps({"ok": True, "config_path": str(path), "seeded": True}, ensure_ascii=False))
        return 0
    if args.cmd == "show":
        cfg = load_config(cfg_arg)
        safe = {k: v for k, v in cfg.items() if not str(k).startswith("_") or k in ("_config_path", "_oa_home")}
        safe["_has_api_key"] = bool(resolve_api_key(cfg)) if cfg.get("provider") != "local" else None
        safe["_secrets_path"] = str(default_secrets_path())
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "selftest":
        result = run_selftest(cfg_arg)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1
    if args.cmd == "status":
        cfg = load_config(cfg_arg)
        rebuild = check_rebuild_needed(cfg)
        print(
            json.dumps(
                {
                    "vector_enabled": bool(cfg.get("vector_enabled")),
                    "user_confirmed": bool(cfg.get("user_confirmed")),
                    "provider": cfg.get("provider"),
                    "model": cfg.get("model"),
                    "dimensions": cfg.get("dimensions"),
                    "embedding_timeout_sec": cfg.get("embedding_timeout_sec"),
                    "embedding_fingerprint": cfg.get("embedding_fingerprint"),
                    "has_api_key": bool(resolve_api_key(cfg))
                    if cfg.get("provider") != "local"
                    else None,
                    "secrets_path": str(default_secrets_path()),
                    "rebuild": rebuild,
                    "config_path": cfg.get("_config_path"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.cmd == "skip-vector":
        path = skip_vector(cfg_arg)
        print(
            json.dumps(
                {
                    "ok": True,
                    "config_path": str(path),
                    "vector_enabled": False,
                    "note_zh": "已跳过向量；入库与检索仅用标签/字段。中途可用 enable-vector 开启。",
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.cmd == "disable-vector":
        path = set_vector_enabled(False, cfg_arg)
        print(json.dumps({"ok": True, "config_path": str(path), "vector_enabled": False}, ensure_ascii=False))
        return 0
    if args.cmd == "enable-vector":
        if args.preset:
            path = apply_preset(args.preset, cfg_arg, vector_enabled=True)
        else:
            path = set_vector_enabled(True, cfg_arg)
        cfg = load_config(path)
        rebuild = check_rebuild_needed(cfg)
        print(
            json.dumps(
                {
                    "ok": True,
                    "config_path": str(path),
                    "vector_enabled": True,
                    "rebuild": rebuild,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.cmd == "set":
        ve = not bool(args.no_vector)
        if args.preset:
            path = apply_preset(args.preset, cfg_arg, vector_enabled=ve)
            if args.group_id or args.sqlite_path or args.group_id_env or args.base_url:
                cfg = load_config(path)
                write_config(
                    provider=str(cfg["provider"]),
                    model=str(cfg["model"]),
                    dimensions=int(cfg["dimensions"]),
                    path=path,
                    base_url=args.base_url or str(cfg.get("base_url") or ""),
                    api_key_env=str(cfg.get("api_key_env") or ""),
                    sqlite_path=args.sqlite_path or str(cfg.get("sqlite_path") or ""),
                    group_id_env=args.group_id_env or str(cfg.get("group_id_env") or ""),
                    group_id=args.group_id or str(cfg.get("group_id") or ""),
                    preset=args.preset,
                    vector_enabled=ve,
                )
        else:
            if not (args.provider and args.model and args.dimensions):
                raise SystemExit("set 需要 --preset，或 --provider --model --dimensions")
            path = write_config(
                provider=args.provider,
                model=args.model,
                dimensions=args.dimensions,
                path=cfg_arg,
                base_url=args.base_url,
                api_key_env=args.api_key_env,
                sqlite_path=args.sqlite_path,
                group_id_env=args.group_id_env,
                group_id=args.group_id,
                vector_enabled=ve,
            )
        secrets_path = ""
        if args.api_key or args.secret_group_id:
            sp = write_secrets(
                api_key=args.api_key,
                group_id=args.secret_group_id or args.group_id,
            )
            secrets_path = str(sp)
        cfg = load_config(path)
        payload: dict[str, Any] = {
            "ok": True,
            "config_path": str(path),
            "vector_enabled": bool(cfg.get("vector_enabled")),
            "rebuild": check_rebuild_needed(cfg),
            "has_api_key": bool(resolve_api_key(cfg))
            if cfg.get("provider") != "local"
            else None,
        }
        if secrets_path:
            payload["secrets_path"] = secrets_path
        # 默认在开启向量时跑自检；可用环境 OA_SKIP_SELFTEST=1 跳过
        do_test = bool(args.run_selftest) or (
            ve and os.environ.get("OA_SKIP_SELFTEST", "").strip() not in ("1", "true", "yes")
        )
        if do_test and ve:
            payload["selftest"] = run_selftest(path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if do_test and ve and not payload.get("selftest", {}).get("ok"):
            return 1
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
