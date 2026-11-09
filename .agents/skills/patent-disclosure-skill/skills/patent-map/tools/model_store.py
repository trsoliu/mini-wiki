#!/usr/bin/env python
"""BGE 中文向量：只装 ONNX，不依赖 PyTorch。固定用户目录，不写运行目录。"""
from __future__ import annotations

import inspect
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

# fastembed 登记名（加载用）；磁盘上拉的是 Qdrant 导出的 ONNX，不是 BAAI 的 PyTorch 仓。
MODEL_ID = "BAAI/bge-small-zh-v1.5"
HF_ONNX_REPO = "Qdrant/bge-small-zh-v1.5"

# 仅这三个端点。魔搭上 BAAI/bge-small-zh-v1.5 是 .bin/.safetensors，fastembed 不能直接加载。
HUB_ENDPOINTS = (
    "https://hf-mirror.com",
    "https://www.modelscope.cn/models",
    "https://huggingface.co",
)

ONNX_NAMES = ("model_optimized.onnx", "model.onnx")
REQUIRED_SIDE = ("config.json", "tokenizer.json")
OPTIONAL_SIDE = ("tokenizer_config.json", "special_tokens_map.json", "vocab.txt", "ort_config.json")
WANTED_FILES = ONNX_NAMES + REQUIRED_SIDE + OPTIONAL_SIDE
PYTORCH_WEIGHTS = (
    "pytorch_model.bin",
    "model.safetensors",
    "pytorch_model.safetensors",
    "model.pt",
    "model.pth",
    "model.bin",
    "model.ckpt",
)
_IGNORE_PATTERNS = ["*.bin", "*.safetensors", "*.pt", "*.pth", "*.ckpt", "pytorch_model*"]
_ALLOW_PATTERNS = [
    "*.onnx",
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "ort_config.json",
]

_UA = {"User-Agent": "patent-map/1.0 (fastembed; ONNX-only; Qdrant/bge-small-zh-v1.5)"}


def global_map_dir() -> Path:
    """数据根，与 oa 同级：{Documents}/patent-disclosure-skill/patent-map/"""
    from map_cache import map_home

    return map_home()


def legacy_model_dir() -> Path:
    return Path.home() / ".patent-disclosure-skill" / "patent-map" / "models" / "bge-small-zh-v1.5"


def default_model_dir() -> Path:
    """模型默认安装位置（各工作区共用，避免反复下载到 cwd）。"""
    env = (os.environ.get("PATENT_MAP_MODEL_DIR") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return global_map_dir() / "models" / "bge-small-zh-v1.5"


def hf_cache_dir() -> Path:
    return global_map_dir() / "models" / "hf-hub"


def fastembed_cache_dir() -> Path:
    return global_map_dir() / "models" / "fastembed-cache"


def lookup_dirs(vault: Path | None = None) -> list[Path]:
    """查找顺序：环境变量/文档目录默认 → 旧用户目录 → sqlite 同级 models/ → fastembed 缓存。"""
    from map_cache import cache_dir_for_vault

    ordered: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            return
        seen.add(key)
        ordered.append(p)

    add(default_model_dir())
    add(legacy_model_dir())
    if vault is not None:
        add(cache_dir_for_vault(vault) / "models" / "bge-small-zh-v1.5")
    add(fastembed_cache_dir())
    return ordered


def _has_onnx(path: Path) -> bool:
    return any(
        (path / name).is_file() and (path / name).stat().st_size > 1_000_000 for name in ONNX_NAMES
    )


def _purge_pytorch_weights(path: Path) -> None:
    if not path.is_dir():
        return
    for name in PYTORCH_WEIGHTS:
        p = path / name
        if p.is_file():
            p.unlink()
            _log(f"已丢弃 PyTorch 权重 {p.name}（fastembed 只用 ONNX）")


def is_model_ready(path: Path) -> bool:
    """必须有 ONNX + 分词器。只有 pytorch_model.bin / safetensors 不算就绪。"""
    if not path.is_dir():
        return False
    if _has_onnx(path):
        has_tok = (path / "tokenizer.json").is_file() or (path / "vocab.txt").is_file()
        return (path / "config.json").is_file() and has_tok
    for child in path.iterdir():
        if child.is_dir() and is_model_ready(child):
            return True
    return False


def resolve_ready_dir(path: Path) -> Path | None:
    if not path.exists():
        return None
    if _has_onnx(path) and is_model_ready(path):
        return path
    if not path.is_dir():
        return None
    for child in sorted(path.rglob("*")):
        if child.is_dir() and _has_onnx(child) and is_model_ready(child):
            return child
    return None


def find_local_model(vault: Path | None = None) -> Path | None:
    for d in lookup_dirs(vault):
        hit = resolve_ready_dir(d)
        if hit is not None:
            return hit
        if d.is_dir():
            for name in ONNX_NAMES:
                for onnx in d.rglob(name):
                    parent = onnx.parent
                    if is_model_ready(parent):
                        return parent
    return None


def _log(msg: str) -> None:
    try:
        sys.stderr.write(f"MAP_MODEL: {msg}\n")
    except UnicodeEncodeError:
        sys.stderr.write(
            f"MAP_MODEL: {msg.encode('utf-8', 'replace').decode('ascii', 'replace')}\n"
        )
    sys.stderr.flush()


def _download_url(url: str, dest: Path, min_size: int, timeout: int = 300) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as fh:
        shutil.copyfileobj(resp, fh)
    size = tmp.stat().st_size
    if size < min_size:
        tmp.unlink(missing_ok=True)
        raise OSError(f"too small ({size} < {min_size}): {url}")
    tmp.replace(dest)


def _copy_model_tree(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    ready = resolve_ready_dir(src) or src
    for name in WANTED_FILES:
        sp = ready / name
        if sp.is_file():
            shutil.copy2(sp, dest / name)
    _purge_pytorch_weights(dest)


def _file_urls(endpoint: str, filename: str) -> list[str]:
    base = endpoint.rstrip("/")
    urls = []
    for rev in ("main", "master"):
        urls.append(f"{base}/{HF_ONNX_REPO}/resolve/{rev}/{filename}")
        urls.append(f"{base}/{HF_ONNX_REPO}/resolve/{rev}/{filename}?download=true")
    return urls


def _try_file_mirrors(dest: Path, endpoint: str) -> bool:
    got_onnx = False
    names = list(ONNX_NAMES[:1]) + list(REQUIRED_SIDE) + list(OPTIONAL_SIDE)
    for name in names:
        min_size = 1_000_000 if name.endswith(".onnx") else 32
        last_err: Exception | None = None
        ok = False
        for url in _file_urls(endpoint, name):
            try:
                _log(f"试下载 {name} ← {url}")
                _download_url(url, dest / name, min_size=min_size)
                ok = True
                if name.endswith(".onnx"):
                    got_onnx = True
                break
            except (OSError, urllib.error.URLError, TimeoutError, ValueError) as e:
                last_err = e
                _log(f"失败 {url}: {e}")
        if name in REQUIRED_SIDE and not ok:
            _log(f"必要文件缺失 {name}: {last_err}")
            return False
        if name == ONNX_NAMES[0] and not ok:
            for alt in ONNX_NAMES[1:]:
                for url in _file_urls(endpoint, alt):
                    try:
                        _log(f"试下载 {alt} ← {url}")
                        _download_url(url, dest / alt, min_size=1_000_000)
                        got_onnx = True
                        ok = True
                        break
                    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as e:
                        last_err = e
                        _log(f"失败 {url}: {e}")
                if ok:
                    break
            if not got_onnx:
                _log(f"ONNX 未拿到: {last_err}")
                return False
    _purge_pytorch_weights(dest)
    return is_model_ready(dest)


def _call_hf_hub_download(endpoint: str, filename: str, dest: Path) -> Path:
    from huggingface_hub import hf_hub_download

    os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")
    kwargs: dict = {
        "repo_id": HF_ONNX_REPO,
        "filename": filename,
        "local_dir": str(dest),
        "cache_dir": str(hf_cache_dir()),
    }
    params = inspect.signature(hf_hub_download).parameters
    if "endpoint" in params:
        kwargs["endpoint"] = endpoint.rstrip("/")
    return Path(hf_hub_download(**kwargs))


def _try_hf_hub_files(dest: Path, endpoint: str) -> bool:
    try:
        from huggingface_hub import hf_hub_download  # noqa: F401
    except ImportError:
        _log("huggingface_hub 未安装，跳过 hub 逐文件")
        return False
    dest.mkdir(parents=True, exist_ok=True)
    _log(f"huggingface_hub 逐文件拉取 ONNX {HF_ONNX_REPO} via {endpoint}")
    got_onnx = False
    names = list(ONNX_NAMES[:1]) + list(REQUIRED_SIDE) + list(OPTIONAL_SIDE)
    for name in names:
        try:
            got = _call_hf_hub_download(endpoint, name, dest)
            target = dest / name
            if got.is_file() and got.resolve() != target.resolve():
                dest.mkdir(parents=True, exist_ok=True)
                shutil.copy2(got, target)
            if name.endswith(".onnx"):
                got_onnx = True
        except Exception as e:
            _log(f"hub 文件失败 {name}: {e}")
            if name == ONNX_NAMES[0]:
                for alt in ONNX_NAMES[1:]:
                    try:
                        got = _call_hf_hub_download(endpoint, alt, dest)
                        target = dest / alt
                        if got.is_file() and got.resolve() != target.resolve():
                            shutil.copy2(got, target)
                        got_onnx = True
                        break
                    except Exception as e2:
                        _log(f"hub 文件失败 {alt}: {e2}")
                if not got_onnx:
                    return False
            if name in REQUIRED_SIDE:
                return False
    _purge_pytorch_weights(dest)
    return is_model_ready(dest)


def _try_hf_snapshot(dest: Path, endpoint: str) -> bool:
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        _log("huggingface_hub 未安装，跳过 snapshot")
        return False
    os.environ["HF_ENDPOINT"] = endpoint.rstrip("/")
    dest.mkdir(parents=True, exist_ok=True)
    _log(f"snapshot ONNX {HF_ONNX_REPO} via {endpoint}")
    kwargs: dict = {
        "repo_id": HF_ONNX_REPO,
        "local_dir": str(dest),
        "cache_dir": str(hf_cache_dir()),
        "allow_patterns": list(_ALLOW_PATTERNS),
        "ignore_patterns": list(_IGNORE_PATTERNS),
    }
    params = inspect.signature(snapshot_download).parameters
    if "endpoint" in params:
        kwargs["endpoint"] = endpoint.rstrip("/")
    try:
        snapshot_download(**kwargs)
    except Exception as e:
        _log(f"snapshot 失败: {e}")
        return False
    _purge_pytorch_weights(dest)
    return resolve_ready_dir(dest) is not None


def _write_readme(dest: Path, note: str) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    readme = dest.parent / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "专利地图向量模型缓存（可删，下次打开会再下）。\n"
            f"加载名：{MODEL_ID}\n"
            f"实际文件：{HF_ONNX_REPO}（ONNX，不用 PyTorch）\n"
            "不要放到 Obsidian 库文件夹内。\n",
            encoding="utf-8",
        )
    (dest / "SOURCE.txt").write_text(note + "\n", encoding="utf-8")


def _pin_hf_env() -> None:
    """把 huggingface / fastembed 缓存钉在用户目录，避免落到 cwd。"""
    os.environ["HF_HUB_CACHE"] = str(hf_cache_dir())
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(hf_cache_dir())
    os.environ["FASTEMBED_CACHE_PATH"] = str(fastembed_cache_dir())
    os.environ.pop("HF_HOME", None)
    hf_cache_dir().mkdir(parents=True, exist_ok=True)
    fastembed_cache_dir().mkdir(parents=True, exist_ok=True)


def ensure_model(vault: Path | None = None) -> tuple[Path | None, str]:
    """
    返回 (模型目录, 来源说明)。已装好则只查盘、不访问网络。
    只拉 Qdrant ONNX；不拉 BAAI PyTorch，不 import torch。
    """
    _pin_hf_env()
    hit = find_local_model(vault)
    if hit is not None:
        _purge_pytorch_weights(hit)
        if is_model_ready(hit):
            return hit, f"local:{hit}"

    dest = default_model_dir()
    dest.mkdir(parents=True, exist_ok=True)
    staging = dest.parent / ".staging-bge-small-zh-v1.5"

    def _commit(src: Path, note: str) -> Path | None:
        _purge_pytorch_weights(src)
        ready = resolve_ready_dir(src)
        if ready is None:
            _log("拒绝提交：目录里没有可用的 ONNX")
            return None
        _copy_model_tree(ready, dest)
        _purge_pytorch_weights(dest)
        if not is_model_ready(dest):
            return None
        _write_readme(dest, note)
        shutil.rmtree(staging, ignore_errors=True)
        return dest

    for endpoint in HUB_ENDPOINTS:
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        if _try_hf_hub_files(staging, endpoint):
            hit2 = _commit(staging, f"huggingface_hub files {HF_ONNX_REPO} @ {endpoint}")
            if hit2:
                return hit2, f"hub-files:{endpoint}"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        if _try_hf_snapshot(staging, endpoint):
            hit2 = _commit(staging, f"huggingface_hub snapshot {HF_ONNX_REPO} @ {endpoint}")
            if hit2:
                return hit2, f"hub-snapshot:{endpoint}"
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        if _try_file_mirrors(staging, endpoint):
            hit2 = _commit(staging, f"resolve ONNX {HF_ONNX_REPO} @ {endpoint}")
            if hit2:
                return hit2, f"files:{endpoint}"

    shutil.rmtree(staging, ignore_errors=True)
    return None, "download-failed"


def write_pointer(vault: Path | None, model_dir: Path | None) -> None:
    """在 sqlite 同级写一份指针，方便人看模型实际装在哪。"""
    if vault is None:
        parent = global_map_dir()
    else:
        from map_cache import cache_dir_for_vault

        parent = cache_dir_for_vault(vault)
    parent.mkdir(parents=True, exist_ok=True)
    text = (
        f"模型默认目录：{default_model_dir()}\n"
        f"本次使用：{model_dir or '（未就绪）'}\n"
        f"格式：ONNX（{HF_ONNX_REPO}），不使用 PyTorch。\n"
        "技能优先读文档目录 patent-disclosure-skill/patent-map/ 这份，避免每个项目下一遍。\n"
    )
    (parent / "MODEL_DIR.txt").write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    path, src = ensure_model()
    print(f"MAP_MODEL:{path or ''}")
    print(f"MAP_MODEL_SOURCE:{src}")
    write_pointer(None, path)
    return 0 if path else 1


if __name__ == "__main__":
    raise SystemExit(main())
