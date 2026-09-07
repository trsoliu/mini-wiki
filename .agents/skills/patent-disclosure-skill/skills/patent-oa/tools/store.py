"""sqlite 案例库：元数据始终可用；向量（sqlite-vec）可选。"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path
_HERE = Path(__file__).resolve().parent
ROOT = _HERE.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
from typing import Any, Iterable

import numpy as np

from config import load_config, sqlite_path_from_config
from embed import vector_to_bytes


def _connect(db_path: Path, *, load_vec: bool) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    if not load_vec:
        return conn
    try:
        conn.enable_load_extension(True)
    except AttributeError as exc:
        raise SystemExit("当前 Python sqlite3 不支持 load_extension") from exc
    try:
        import sqlite_vec
    except ImportError as exc:
        raise SystemExit(
            "需要 sqlite-vec：pip install -r skills/patent-oa/tools/requirements-oa.txt"
        ) from exc
    sqlite_vec.load(conn)
    return conn


def init_db(conn: sqlite3.Connection, dimensions: int, *, with_vec: bool = True) -> None:
    conn.executescript(
        """
        create table if not exists meta (
          key text primary key,
          value text not null
        );
        create table if not exists cases (
          case_id text primary key,
          title text,
          patent_type text,
          statutes_json text,
          defect_types_json text,
          domain text,
          notice_kind text,
          outcome text,
          strategy_json text,
          compare_refs_json text,
          tags_json text,
          note_path text,
          body_text text,
          updated_at text
        );
        """
    )
    if with_vec and dimensions > 0:
        row = conn.execute(
            "select value from meta where key = 'dimensions'"
        ).fetchone()
        if row and int(row["value"]) != int(dimensions):
            conn.execute("drop table if exists vec_chunks")
        conn.execute(
            f"""
            create virtual table if not exists vec_chunks using vec0(
              embedding float[{int(dimensions)}]
            )
            """
        )
        conn.execute(
            """
            create table if not exists chunk_meta (
              rowid integer primary key,
              case_id text not null,
              chunk_kind text,
              text text
            )
            """
        )
        conn.execute(
            "insert or replace into meta(key, value) values ('dimensions', ?)",
            (str(int(dimensions)),),
        )
    conn.commit()


def _json_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            return [value]
    return []


def upsert_case_meta(
    conn: sqlite3.Connection,
    *,
    case: dict[str, Any],
    note_path: str,
    body_text: str,
) -> None:
    case_id = str(case.get("case_id") or "").strip()
    if not case_id:
        raise SystemExit("case_id 必填")
    conn.execute(
        """
        insert or replace into cases(
          case_id, title, patent_type, statutes_json, defect_types_json,
          domain, notice_kind, outcome, strategy_json, compare_refs_json,
          tags_json, note_path, body_text, updated_at
        ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            case_id,
            str(case.get("title") or ""),
            str(case.get("patent_type") or ""),
            json.dumps(_json_list(case.get("statutes")), ensure_ascii=False),
            json.dumps(_json_list(case.get("defect_types")), ensure_ascii=False),
            str(case.get("domain") or ""),
            str(case.get("notice_kind") or ""),
            str(case.get("outcome") or ""),
            json.dumps(_json_list(case.get("strategy")), ensure_ascii=False),
            json.dumps(_json_list(case.get("compare_refs")), ensure_ascii=False),
            json.dumps(_json_list(case.get("tags")), ensure_ascii=False),
            note_path,
            body_text,
            str(case.get("updated_at") or case.get("created_at") or ""),
        ),
    )
    conn.commit()


def clear_case_vectors(conn: sqlite3.Connection, case_id: str) -> None:
    try:
        old = conn.execute(
            "select rowid from chunk_meta where case_id = ?", (case_id,)
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for r in old:
        try:
            conn.execute("delete from vec_chunks where rowid = ?", (int(r["rowid"]),))
        except sqlite3.OperationalError:
            pass
    conn.execute("delete from chunk_meta where case_id = ?", (case_id,))
    conn.commit()


def upsert_case(
    conn: sqlite3.Connection,
    *,
    case: dict[str, Any],
    note_path: str,
    body_text: str,
    chunks: list[tuple[str, str, np.ndarray]] | None = None,
) -> None:
    case_id = str(case.get("case_id") or "").strip()
    upsert_case_meta(conn, case=case, note_path=note_path, body_text=body_text)
    if chunks is None:
        return
    clear_case_vectors(conn, case_id)
    for kind, text, vec in chunks:
        cur = conn.execute(
            "insert into chunk_meta(case_id, chunk_kind, text) values (?,?,?)",
            (case_id, kind, text),
        )
        rowid = int(cur.lastrowid)
        conn.execute(
            "insert into vec_chunks(rowid, embedding) values (?, ?)",
            (rowid, vector_to_bytes(vec)),
        )
    conn.commit()


def _normalize_token(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").lower())


def _filter_case_ids(
    cases: list[sqlite3.Row],
    *,
    patent_type: str | None,
    statutes: Iterable[str] | None,
    defect_types: Iterable[str] | None,
    domain: str | None = None,
    tags: Iterable[str] | None = None,
) -> tuple[list[str], dict[str, sqlite3.Row]]:
    want_statutes = {_normalize_token(x) for x in (statutes or []) if x}
    want_defects = {_normalize_token(x) for x in (defect_types or []) if x}
    want_tags = {_normalize_token(x) for x in (tags or []) if x}
    want_domain = _normalize_token(domain or "")
    filtered_ids: list[str] = []
    case_map: dict[str, sqlite3.Row] = {}
    for row in cases:
        case_map[row["case_id"]] = row
        if patent_type and row["patent_type"] and row["patent_type"] != patent_type:
            continue
        st = {_normalize_token(x) for x in json.loads(row["statutes_json"] or "[]")}
        df = {_normalize_token(x) for x in json.loads(row["defect_types_json"] or "[]")}
        tg = {_normalize_token(x) for x in json.loads(row["tags_json"] or "[]")}
        if want_statutes and st and not (want_statutes & st):
            if not any(any(a in b or b in a for b in st) for a in want_statutes):
                continue
        if want_defects and df and not (want_defects & df):
            if not any(any(a in b or b in a for b in df) for a in want_defects):
                continue
        if want_tags and tg and not (want_tags & tg):
            if not any(any(a in b or b in a for b in tg) for a in want_tags):
                continue
        if want_domain and row["domain"]:
            rd = _normalize_token(row["domain"])
            if want_domain not in rd and rd not in want_domain:
                continue
        filtered_ids.append(row["case_id"])
    return filtered_ids, case_map


def _row_to_hit(
    crow: sqlite3.Row,
    *,
    distance: float | None,
    chunk_kind: str = "",
    chunk_text: str = "",
) -> dict:
    return {
        "case_id": crow["case_id"],
        "title": crow["title"],
        "patent_type": crow["patent_type"],
        "statutes": json.loads(crow["statutes_json"] or "[]"),
        "defect_types": json.loads(crow["defect_types_json"] or "[]"),
        "domain": crow["domain"],
        "notice_kind": crow["notice_kind"],
        "outcome": crow["outcome"],
        "strategy": json.loads(crow["strategy_json"] or "[]"),
        "compare_refs": json.loads(crow["compare_refs_json"] or "[]"),
        "tags": json.loads(crow["tags_json"] or "[]"),
        "note_path": crow["note_path"],
        "chunk_kind": chunk_kind,
        "chunk_text": (chunk_text or (crow["body_text"] or ""))[:1200],
        "distance": distance,
    }


def search_by_tags(
    conn: sqlite3.Connection,
    *,
    top_k: int = 5,
    patent_type: str | None = None,
    statutes: Iterable[str] | None = None,
    defect_types: Iterable[str] | None = None,
    domain: str | None = None,
    tags: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """仅标签/字段过滤（无向量）。"""
    cases = conn.execute("select * from cases").fetchall()
    filtered_ids, case_map = _filter_case_ids(
        cases,
        patent_type=patent_type,
        statutes=statutes,
        defect_types=defect_types,
        domain=domain,
        tags=tags,
    )
    if not filtered_ids and cases:
        filtered_ids = [r["case_id"] for r in cases]

    hits: list[dict[str, Any]] = []
    for cid in filtered_ids:
        crow = case_map[cid]
        hits.append(
            _row_to_hit(
                crow,
                distance=None,
                chunk_kind="meta",
                chunk_text=crow["body_text"] or "",
            )
        )
        if len(hits) >= top_k:
            break
    return hits


def search(
    conn: sqlite3.Connection,
    *,
    query_vec: np.ndarray | None,
    top_k: int = 5,
    patent_type: str | None = None,
    statutes: Iterable[str] | None = None,
    defect_types: Iterable[str] | None = None,
    domain: str | None = None,
    tags: Iterable[str] | None = None,
    limit_candidates: int = 50,
) -> list[dict[str, Any]]:
    """先元数据过滤；有向量则 KNN，否则标签检索。"""
    if query_vec is None:
        return search_by_tags(
            conn,
            top_k=top_k,
            patent_type=patent_type,
            statutes=statutes,
            defect_types=defect_types,
            domain=domain,
            tags=tags,
        )

    cases = conn.execute("select * from cases").fetchall()
    filtered_ids, case_map = _filter_case_ids(
        cases,
        patent_type=patent_type,
        statutes=statutes,
        defect_types=defect_types,
        domain=domain,
        tags=tags,
    )
    if not filtered_ids and cases:
        filtered_ids = [r["case_id"] for r in cases]
    if not filtered_ids:
        return []

    placeholders = ",".join("?" for _ in filtered_ids)
    try:
        chunk_rows = conn.execute(
            f"select rowid, case_id, chunk_kind, text from chunk_meta where case_id in ({placeholders})",
            filtered_ids,
        ).fetchall()
    except sqlite3.OperationalError:
        return search_by_tags(
            conn,
            top_k=top_k,
            patent_type=patent_type,
            statutes=statutes,
            defect_types=defect_types,
            domain=domain,
            tags=tags,
        )
    if not chunk_rows:
        return search_by_tags(
            conn,
            top_k=top_k,
            patent_type=patent_type,
            statutes=statutes,
            defect_types=defect_types,
            domain=domain,
            tags=tags,
        )

    q = vector_to_bytes(query_vec)
    try:
        knn = conn.execute(
            """
            select rowid, distance
            from vec_chunks
            where embedding match ?
              and k = ?
            order by distance
            """,
            (q, int(max(limit_candidates, top_k))),
        ).fetchall()
    except sqlite3.OperationalError:
        return search_by_tags(
            conn,
            top_k=top_k,
            patent_type=patent_type,
            statutes=statutes,
            defect_types=defect_types,
            domain=domain,
            tags=tags,
        )

    allowed = {int(r["rowid"]): r for r in chunk_rows}
    hits: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    for item in knn:
        rid = int(item["rowid"])
        meta = allowed.get(rid)
        if not meta:
            continue
        cid = meta["case_id"]
        if cid in seen_cases:
            continue
        seen_cases.add(cid)
        crow = case_map[cid]
        hits.append(
            _row_to_hit(
                crow,
                distance=float(item["distance"]),
                chunk_kind=meta["chunk_kind"],
                chunk_text=meta["text"] or "",
            )
        )
        if len(hits) >= top_k:
            break
    return hits


def open_store(
    config_path: str | None = None,
    *,
    require_vec: bool | None = None,
) -> tuple[sqlite3.Connection, dict]:
    cfg = load_config(config_path)
    path = sqlite_path_from_config(cfg)
    use_vec = bool(cfg.get("vector_enabled")) if require_vec is None else bool(require_vec)
    if use_vec or require_vec:
        conn = _connect(path, load_vec=True)
        dims = int(cfg.get("dimensions") or 512)
        init_db(conn, dims, with_vec=True)
    else:
        try:
            conn = _connect(path, load_vec=True)
            dims = int(cfg.get("dimensions") or 512)
            init_db(conn, dims, with_vec=True)
        except SystemExit:
            conn = _connect(path, load_vec=False)
            init_db(conn, 0, with_vec=False)
    return conn, cfg


def list_case_note_paths(cases_dir: Path) -> list[Path]:
    """扫描可入库历史案（不含 pending/drafts）。

    兼容：oa 根、oa/cases、oa/cases/history。
    """
    from vault_layout import list_history_case_paths

    return list_history_case_paths(cases_dir)
