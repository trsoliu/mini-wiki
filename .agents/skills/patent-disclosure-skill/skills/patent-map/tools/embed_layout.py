#!/usr/bin/env python
"""解读短文 → fastembed 向量 → PCA 二维坐标。向量不进前端 JSON。"""
from __future__ import annotations

import math
import os
import sys
import threading
from pathlib import Path

from model_store import MODEL_ID, default_model_dir, ensure_model, write_pointer

_LOCK = threading.Lock()
_ENCODER = None
_ENCODER_PATH: str | None = None


def compose_embed_text(rec: dict) -> str:
    """一句话 + 发明名称 + 术语 + 手段/功效；不要整本说明书。"""
    bits: list[str] = []
    title = (rec.get("invention_title") or rec.get("title") or "").strip()
    if title:
        bits.append(title[:120])
    one = (rec.get("one_liner") or "").strip()
    if one and one not in bits:
        bits.append(one[:160])
    terms = [str(t).strip() for t in (rec.get("terms") or []) if str(t).strip()]
    if terms:
        bits.append("术语：" + "、".join(terms[:12]))
    for me in rec.get("means_effects") or []:
        a = str(me.get("mean") or "").strip()[:40]
        b = str(me.get("effect") or "").strip()[:40]
        if a and b:
            bits.append(f"{a} → {b}")
        elif a or b:
            bits.append(a or b)
    domain = (rec.get("domain") or "").strip()
    if domain:
        bits.append("领域：" + domain)
    ipc = (rec.get("ipc") or "").strip()
    if ipc:
        bits.append("IPC：" + ipc)
    text = "。".join(bits).strip()
    return text[:1200] or (rec.get("pub") or "")


def project_2d(vectors: list[list[float]]) -> list[tuple[float, float]]:
    n = len(vectors)
    if n == 0:
        return []
    if n == 1:
        return [(0.5, 0.5)]
    try:
        import numpy as np
    except ImportError:
        return [
            (
                0.5 + 0.32 * math.cos(2 * math.pi * i / n),
                0.5 + 0.32 * math.sin(2 * math.pi * i / n),
            )
            for i in range(n)
        ]
    x = np.asarray(vectors, dtype="float64")
    x = x - x.mean(axis=0)
    # 样本少时 SVD 仍稳定
    u, s, _vt = np.linalg.svd(x, full_matrices=False)
    k = min(2, u.shape[1], s.shape[0])
    xy = u[:, :k] * s[:k]
    if k == 1:
        xy = np.column_stack([xy[:, 0], np.zeros(n)])
    lo = xy.min(axis=0)
    span = np.maximum(xy.max(axis=0) - lo, 1e-6)
    xy = (xy - lo) / span
    # 略留边，避免点贴框
    xy = 0.08 + xy * 0.84
    return [(float(a), float(b)) for a, b in xy]


def nearest_k(
    vectors: list[list[float]], pubs: list[str], k: int = 3
) -> list[list[dict]]:
    n = len(vectors)
    out: list[list[dict]] = [[] for _ in range(n)]
    if n < 2:
        return out
    try:
        import numpy as np
    except ImportError:
        return out
    x = np.asarray(vectors, dtype="float64")
    nrm = np.linalg.norm(x, axis=1, keepdims=True)
    nrm = np.maximum(nrm, 1e-9)
    x = x / nrm
    sim = x @ x.T
    kk = min(k, n - 1)
    for i in range(n):
        order = np.argsort(-sim[i])
        hits = []
        for j in order:
            j = int(j)
            if j == i:
                continue
            hits.append({"pub": pubs[j], "score": round(float(sim[i, j]), 4)})
            if len(hits) >= kk:
                break
        out[i] = hits
    return out


def _get_encoder(model_dir: Path):
    global _ENCODER, _ENCODER_PATH
    key = str(model_dir)
    if _ENCODER is not None and _ENCODER_PATH == key:
        return _ENCODER
    from fastembed import TextEmbedding

    _ENCODER = TextEmbedding(
        model_name=MODEL_ID,
        cache_dir=str(model_dir.parent / "fastembed-cache"),
        specific_model_path=str(model_dir),
        local_files_only=True,
    )
    _ENCODER_PATH = key
    return _ENCODER


def _embed_texts(model_dir: Path, texts: list[str]) -> list[list[float]]:
    enc = _get_encoder(model_dir)
    vectors: list[list[float]] = []
    for vec in enc.embed(texts, batch_size=min(32, max(len(texts), 1))):
        vectors.append([float(x) for x in list(vec)])
    return vectors


def _skip_embed() -> bool:
    v = (os.environ.get("PATENT_MAP_SKIP_EMBED") or "").strip().lower()
    return v in {"1", "true", "yes", "on"}


def attach_layout(patents: list[dict], vault: Path | None) -> tuple[list[dict], dict]:
    """给每条专利补 x/y/nearest；失败则前端退回 IPC 地形。"""
    info = {
        "available": False,
        "mode": "ipc",
        "model": MODEL_ID,
        "model_dir": str(default_model_dir()),
        "source": "",
        "error": "",
        "embedded": 0,
    }
    if not patents:
        info["error"] = "empty"
        return patents, info
    if _skip_embed():
        info["error"] = "skipped"
        return patents, info

    from map_cache import (
        cache_db_path,
        fallback_cache_dir,
        load_embedding,
        upsert_embedding,
        _connect,
    )

    db = cache_db_path(vault) if vault else fallback_cache_dir() / "index.sqlite"
    with _LOCK:
        model_dir, src = ensure_model(vault)
        write_pointer(vault, model_dir)
        info["source"] = src
        info["model_dir"] = str(model_dir or default_model_dir())
        if model_dir is None:
            info["error"] = "模型未就绪（已尝试国内镜像）。pip install -r skills/patent-map/tools/requirements.txt 后重开地图。"
            return patents, info
        try:
            import fastembed  # noqa: F401
        except ImportError:
            info["error"] = "未安装 fastembed。pip install -r skills/patent-map/tools/requirements.txt"
            return patents, info

        conn = _connect(db)
        texts = [compose_embed_text(p) for p in patents]
        pubs = [str(p.get("pub") or "") for p in patents]
        vectors: list[list[float] | None] = [None] * len(patents)
        need_idx: list[int] = []
        try:
            for i, (pub, text) in enumerate(zip(pubs, texts)):
                cached = load_embedding(conn, pub, text, MODEL_ID)
                if cached is not None:
                    vectors[i] = cached
                else:
                    need_idx.append(i)
            if need_idx:
                new_vecs = _embed_texts(model_dir, [texts[i] for i in need_idx])
                if len(new_vecs) != len(need_idx):
                    raise RuntimeError("向量条数与文本不一致")
                for i, vec in zip(need_idx, new_vecs):
                    vectors[i] = vec
                    upsert_embedding(conn, pubs[i], texts[i], MODEL_ID, vec, None, None)
            if any(v is None for v in vectors):
                raise RuntimeError("仍有专利没有向量")
            packed = [v for v in vectors if v is not None]
            xy = project_2d(packed)
            near = nearest_k(packed, pubs, k=3)
            for i, rec in enumerate(patents):
                rec["x"] = round(xy[i][0], 5)
                rec["y"] = round(xy[i][1], 5)
                rec["nearest"] = near[i]
                rec["embed_text"] = texts[i]
                upsert_embedding(
                    conn,
                    pubs[i],
                    texts[i],
                    MODEL_ID,
                    packed[i],
                    rec["x"],
                    rec["y"],
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            info["error"] = f"向量计算失败：{e}"
            sys.stderr.write(f"MAP_EMBED: {e}\n")
            return patents, info
        finally:
            conn.close()

    info["available"] = True
    info["mode"] = "semantic"
    info["embedded"] = len(patents)
    info["error"] = ""
    return patents, info
