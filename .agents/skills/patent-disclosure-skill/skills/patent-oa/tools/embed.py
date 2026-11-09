"""文本向量：多厂商适配（可选；失败可回退标签检索）。

支持 provider：
  - local              ：sentence-transformers
  - openai_compatible  ：智谱 / 通义 / OpenAI
  - minimax            ：MiniMax 专用
"""
from __future__ import annotations

import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal, Sequence

import numpy as np

from config import load_config

Purpose = Literal["document", "query"]


class EmbedError(Exception):
    """向量不可用（超时/鉴权/网络等），调用方应回退标签检索。"""


def _l2_normalize(arr: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return arr / norms


class Embedder:
    PROVIDERS = ("local", "openai_compatible", "minimax")

    def __init__(self, cfg: dict | None = None, config_path: str | None = None):
        self.cfg = cfg or load_config(config_path)
        self.provider = str(self.cfg.get("provider") or "local").strip()
        self.model = str(self.cfg.get("model") or "")
        self.dimensions = int(self.cfg.get("dimensions") or 0)
        self.timeout = float(self.cfg.get("embedding_timeout_sec") or 30)
        self._local = None
        if self.provider not in self.PROVIDERS:
            raise EmbedError(
                f"未知 provider: {self.provider}；可选: {', '.join(self.PROVIDERS)}"
            )

    def _ensure_local(self):
        if self._local is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbedError(
                "本地 embedding 需要 sentence-transformers："
                "pip install -r skills/patent-oa/tools/requirements-oa.txt"
            ) from exc
        try:
            self._local = SentenceTransformer(self.model)
        except Exception as exc:
            raise EmbedError(f"本地模型加载失败: {exc}") from exc

    def embed_texts(
        self,
        texts: Sequence[str],
        *,
        purpose: Purpose = "document",
    ) -> np.ndarray:
        cleaned = [t if (t or "").strip() else " " for t in texts]
        try:
            if self.provider == "local":
                self._ensure_local()
                vecs = self._local.encode(cleaned, normalize_embeddings=True)
                arr = np.asarray(vecs, dtype=np.float32)
            elif self.provider == "openai_compatible":
                arr = self._embed_openai(cleaned)
            elif self.provider == "minimax":
                arr = self._embed_minimax(cleaned, purpose=purpose)
            else:
                raise EmbedError(f"未知 provider: {self.provider}")
        except EmbedError:
            raise
        except Exception as exc:
            raise EmbedError(f"embedding 失败: {exc}") from exc
        if self.dimensions and arr.shape[1] != self.dimensions:
            self.dimensions = int(arr.shape[1])
        return arr

    def embed_one(self, text: str, *, purpose: Purpose = "query") -> np.ndarray:
        return self.embed_texts([text], purpose=purpose)[0]

    def _api_key(self) -> str:
        from config import resolve_api_key

        key = resolve_api_key(self.cfg)
        if not key:
            env_name = str(self.cfg.get("api_key_env") or "OPENAI_API_KEY")
            raise EmbedError(
                f"线上 embedding 需要 API Key：请设置环境变量 {env_name}，"
                "或写入文档目录 embedding.secrets.yaml（config.py set --api-key …）"
            )
        return key

    def _embed_openai(self, texts: list[str]) -> np.ndarray:
        key = self._api_key()
        base = (self.cfg.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        url = f"{base}/embeddings"
        payload_obj: dict = {"model": self.model, "input": texts}
        if self.dimensions and self.dimensions > 0:
            payload_obj["dimensions"] = int(self.dimensions)
        body = json.dumps(payload_obj).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "patent-disclosure-skill-oa",
            },
            method="POST",
        )
        payload = self._http_json(req)
        data = payload.get("data") or []
        data = sorted(data, key=lambda x: int(x.get("index") or 0))
        if not data:
            raise EmbedError(f"embedding 响应无 data: {str(payload)[:400]}")
        vecs = [np.asarray(item["embedding"], dtype=np.float32) for item in data]
        return _l2_normalize(np.stack(vecs, axis=0))

    def _embed_minimax(self, texts: list[str], *, purpose: Purpose) -> np.ndarray:
        key = self._api_key()
        from config import resolve_group_id

        group_id = resolve_group_id(self.cfg)
        base = (
            self.cfg.get("base_url") or "https://api.minimaxi.com/v1/embeddings"
        ).rstrip("/")
        if not base.endswith("/embeddings"):
            if base.endswith("/v1"):
                base = f"{base}/embeddings"
            elif "/embeddings" not in base:
                base = f"{base.rstrip('/')}/v1/embeddings"
        url = base
        if group_id:
            url = f"{url}?{urllib.parse.urlencode({'GroupId': group_id})}"
        embed_type = "query" if purpose == "query" else "db"
        force = str(self.cfg.get("minimax_embed_type") or "").strip()
        if force in ("db", "query"):
            embed_type = force
        payload_obj = {
            "model": self.model or "embo-01",
            "texts": texts,
            "type": embed_type,
        }
        body = json.dumps(payload_obj).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "User-Agent": "patent-disclosure-skill-oa",
            },
            method="POST",
        )
        payload = self._http_json(req)
        base_resp = payload.get("base_resp") or {}
        if isinstance(base_resp, dict) and int(base_resp.get("status_code") or 0) != 0:
            raise EmbedError(f"MiniMax embedding 失败: {base_resp}")
        vectors = payload.get("vectors")
        if not vectors and isinstance(payload.get("data"), list):
            data = sorted(payload["data"], key=lambda x: int(x.get("index") or 0))
            vectors = [item.get("embedding") for item in data]
        if not vectors:
            raise EmbedError(f"MiniMax 响应无 vectors: {str(payload)[:400]}")
        arr = np.stack(
            [np.asarray(v, dtype=np.float32) for v in vectors],
            axis=0,
        )
        return _l2_normalize(arr)

    def _http_json(self, req: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except TimeoutError as exc:
            raise EmbedError(f"embedding 超时（{self.timeout}s）") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise EmbedError(f"embedding 超时（{self.timeout}s）") from exc
            raise EmbedError(f"embedding 网络错误: {exc}") from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise EmbedError(f"embedding API HTTP {exc.code}: {detail}") from exc


def vector_to_bytes(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def bytes_to_vector(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.float32).copy()
