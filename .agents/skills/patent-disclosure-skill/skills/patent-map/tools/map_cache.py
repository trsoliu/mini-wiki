#!/usr/bin/env python
"""专利地图 SQLite 加速副本：vault 为源，按路径+mtime+size 失效。"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

SCHEMA_VERSION = 2


def documents_dir() -> Path:
    """操作系统「文档」目录，与 oa 包同一套解析。"""
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


def skill_data_root() -> Path:
    """与 oa 同级：{Documents}/patent-disclosure-skill/"""
    return (documents_dir() / "patent-disclosure-skill").resolve()


def map_home() -> Path:
    env = (os.environ.get("PATENT_MAP_HOME") or "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (skill_data_root() / "patent-map").resolve()


def cache_dir_for_vault(vault: Path | None = None) -> Path:
    """数据根：{Documents}/patent-disclosure-skill/patent-map/ ，与 oa 同级。"""
    return map_home()


def cache_db_path(vault: Path | None = None) -> Path:
    return cache_dir_for_vault(vault) / "index.sqlite"


def fallback_cache_dir() -> Path:
    return map_home()


def _connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    readme = db.parent / "README.txt"
    if not readme.is_file():
        readme.write_text(
            "专利地图加速副本（可删，下次打开会重建）。\n"
            "与审查答复 oa 同级，在操作系统文档目录：\n"
            "  {Documents}/patent-disclosure-skill/patent-map/\n"
            "不要放进 Obsidian 库文件夹内。PATENT_MAP_HOME 可覆盖本目录。\n"
            "向量模型默认也在本夹 models/ ；若曾装在 ~/.patent-disclosure-skill/patent-map/models/ 仍可读。\n",
            encoding="utf-8",
        )
    conn = sqlite3.connect(str(db), timeout=8)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            rel_path TEXT PRIMARY KEY,
            mtime REAL NOT NULL,
            size INTEGER NOT NULL,
            pub TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
            pub TEXT PRIMARY KEY,
            embed_text TEXT NOT NULL,
            model_id TEXT NOT NULL,
            dim INTEGER NOT NULL,
            vector TEXT NOT NULL,
            x REAL,
            y REAL
        )
        """
    )
    row = conn.execute("SELECT value FROM meta WHERE key='schema'").fetchone()
    if row is None or int(row[0]) != SCHEMA_VERSION:
        conn.execute("DELETE FROM notes")
        conn.execute("DELETE FROM embeddings")
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('schema', ?)",
            (str(SCHEMA_VERSION),),
        )
        conn.commit()
    return conn


def file_stamp(path: Path) -> tuple[float, int]:
    st = path.stat()
    return (st.st_mtime, st.st_size)


def load_cached(conn: sqlite3.Connection, rel: str, mtime: float, size: int) -> dict | None:
    row = conn.execute(
        "SELECT payload FROM notes WHERE rel_path=? AND mtime=? AND size=?",
        (rel, mtime, size),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def upsert(conn: sqlite3.Connection, rel: str, mtime: float, size: int, rec: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO notes(rel_path, mtime, size, pub, payload)
        VALUES (?, ?, ?, ?, ?)
        """,
        (rel, mtime, size, rec.get("pub") or "", json.dumps(rec, ensure_ascii=False)),
    )


def drop_missing(conn: sqlite3.Connection, keep: set[str]) -> None:
    rows = conn.execute("SELECT rel_path FROM notes").fetchall()
    for (rel,) in rows:
        if rel not in keep:
            conn.execute("DELETE FROM notes WHERE rel_path=?", (rel,))


def load_embedding(
    conn: sqlite3.Connection, pub: str, embed_text: str, model_id: str
) -> list[float] | None:
    row = conn.execute(
        "SELECT vector FROM embeddings WHERE pub=? AND embed_text=? AND model_id=?",
        (pub, embed_text, model_id),
    ).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list) or not data:
        return None
    try:
        return [float(x) for x in data]
    except (TypeError, ValueError):
        return None


def upsert_embedding(
    conn: sqlite3.Connection,
    pub: str,
    embed_text: str,
    model_id: str,
    vector: list[float],
    x: float | None,
    y: float | None,
) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO embeddings(pub, embed_text, model_id, dim, vector, x, y)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pub,
            embed_text,
            model_id,
            len(vector),
            json.dumps(vector),
            x,
            y,
        ),
    )
