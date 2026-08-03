"""Chinese-aware standalone search with SQLite FTS5 and a compatible fallback."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

CJK_RUN_RE = re.compile(r"[\u3400-\u9fff]+")
WORD_RE = re.compile(r"[a-z0-9_./-]+")


def _canonical_text(text: str) -> str:
    return unicodedata.normalize("NFKC", text).casefold().strip()


def normalize_search_text(text: str) -> str:
    """Normalize words and add deterministic CJK unigram/bigram tokens."""
    lowered = _canonical_text(text)
    words = WORD_RE.findall(lowered)
    cjk: list[str] = []
    for run in CJK_RUN_RE.findall(lowered):
        cjk.extend(run)
        cjk.extend(run[index : index + 2] for index in range(len(run) - 1))
    return " ".join(dict.fromkeys([*words, *cjk]))


@dataclass(frozen=True)
class SearchDocument:
    node_id: str
    title: str
    aliases: tuple[str, ...]
    tags: tuple[str, ...]
    body: str
    node_type: str
    path: str
    sources: tuple[str, ...]


@dataclass(frozen=True)
class SearchHit:
    node_id: str
    title: str
    path: str
    node_type: str
    tags: tuple[str, ...]
    score: float
    snippet: str


@dataclass(frozen=True)
class IndexUpdate:
    created: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()


def _document_hash(document: SearchDocument) -> str:
    payload = {
        "node_id": document.node_id,
        "title": document.title,
        "aliases": list(document.aliases),
        "tags": list(document.tags),
        "body": document.body,
        "node_type": document.node_type,
        "path": document.path,
        "sources": list(document.sources),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class SearchIndex:
    """Persistent rebuildable metadata index with optional FTS5 acceleration."""

    def __init__(self, database: str | Path, force_fallback: bool = False):
        self.database = Path(database)
        self.force_fallback = force_fallback
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._fts_enabled = False
        self._initialize()

    @property
    def mode(self) -> str:
        return "fts5" if self._fts_enabled else "fallback"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS search_documents (
                    node_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    aliases TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    body TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    sources TEXT NOT NULL,
                    normalized_title TEXT NOT NULL,
                    normalized_aliases TEXT NOT NULL,
                    normalized_tags TEXT NOT NULL,
                    normalized_body TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                )
                """
            )
            if self.force_fallback:
                return
            try:
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(
                        node_id UNINDEXED,
                        title,
                        aliases,
                        tags,
                        body,
                        tokenize = 'unicode61'
                    )
                    """
                )
            except sqlite3.OperationalError:
                self._fts_enabled = False
            else:
                self._fts_enabled = True

    def update(self, documents: list[SearchDocument]) -> IndexUpdate:
        """Incrementally synchronize documents by stable content hash."""
        ordered = sorted(documents, key=lambda document: document.node_id)
        if len({document.node_id for document in ordered}) != len(ordered):
            raise ValueError("Search documents must have unique node IDs")
        incoming = {document.node_id: _document_hash(document) for document in ordered}

        with self._connect() as connection:
            existing = {
                str(row["node_id"]): str(row["content_hash"])
                for row in connection.execute("SELECT node_id, content_hash FROM search_documents")
            }
            created = tuple(sorted(set(incoming) - set(existing)))
            modified = tuple(
                sorted(node_id for node_id in set(incoming) & set(existing) if incoming[node_id] != existing[node_id])
            )
            deleted = tuple(sorted(set(existing) - set(incoming)))

            for node_id in deleted:
                connection.execute("DELETE FROM search_documents WHERE node_id = ?", (node_id,))
                if self._fts_enabled:
                    connection.execute("DELETE FROM search_fts WHERE node_id = ?", (node_id,))

            changed = set(created) | set(modified)
            for document in ordered:
                if document.node_id not in changed:
                    continue
                aliases = json.dumps(list(document.aliases), ensure_ascii=False, separators=(",", ":"))
                tags = json.dumps(list(document.tags), ensure_ascii=False, separators=(",", ":"))
                sources = json.dumps(list(document.sources), ensure_ascii=False, separators=(",", ":"))
                normalized_title = normalize_search_text(document.title)
                normalized_aliases = normalize_search_text(" ".join(document.aliases))
                normalized_tags = normalize_search_text(" ".join(document.tags))
                normalized_body = normalize_search_text(document.body)
                connection.execute(
                    """
                    INSERT INTO search_documents (
                        node_id, title, aliases, tags, body, node_type, path, sources,
                        normalized_title, normalized_aliases, normalized_tags, normalized_body, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        title = excluded.title,
                        aliases = excluded.aliases,
                        tags = excluded.tags,
                        body = excluded.body,
                        node_type = excluded.node_type,
                        path = excluded.path,
                        sources = excluded.sources,
                        normalized_title = excluded.normalized_title,
                        normalized_aliases = excluded.normalized_aliases,
                        normalized_tags = excluded.normalized_tags,
                        normalized_body = excluded.normalized_body,
                        content_hash = excluded.content_hash
                    """,
                    (
                        document.node_id,
                        document.title,
                        aliases,
                        tags,
                        document.body,
                        document.node_type,
                        document.path,
                        sources,
                        normalized_title,
                        normalized_aliases,
                        normalized_tags,
                        normalized_body,
                        incoming[document.node_id],
                    ),
                )
                if self._fts_enabled:
                    connection.execute("DELETE FROM search_fts WHERE node_id = ?", (document.node_id,))
                    connection.execute(
                        "INSERT INTO search_fts (node_id, title, aliases, tags, body) VALUES (?, ?, ?, ?, ?)",
                        (
                            document.node_id,
                            normalized_title,
                            normalized_aliases,
                            normalized_tags,
                            normalized_body,
                        ),
                    )
        return IndexUpdate(created, modified, deleted)

    def _candidate_ids(self, connection: sqlite3.Connection, tokens: tuple[str, ...]) -> set[str] | None:
        if not self._fts_enabled:
            return None
        query = " OR ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)
        try:
            return {
                str(row["node_id"])
                for row in connection.execute("SELECT node_id FROM search_fts WHERE search_fts MATCH ?", (query,))
            }
        except sqlite3.OperationalError:
            return None

    @staticmethod
    def _score(row: sqlite3.Row, query: str, tokens: tuple[str, ...]) -> float:
        title_tokens = set(str(row["normalized_title"]).split())
        alias_tokens = set(str(row["normalized_aliases"]).split())
        tag_tokens = set(str(row["normalized_tags"]).split())
        body_tokens = set(str(row["normalized_body"]).split())
        score = 0.0
        canonical_query = _canonical_text(query)
        canonical_title = _canonical_text(str(row["title"]))
        if canonical_query == canonical_title:
            score += 1_000.0
        elif canonical_query and canonical_query in canonical_title:
            score += 500.0
        for token in tokens:
            if token in title_tokens:
                score += 20.0
            if token in alias_tokens:
                score += 12.0
            if token in tag_tokens:
                score += 8.0
            if token in body_tokens:
                score += 2.0
        return score

    def search(
        self,
        query: str,
        node_type: str | None = None,
        tag: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        """Search with stable ranking and optional exact metadata filters."""
        if limit < 1:
            raise ValueError("Search limit must be greater than zero")
        tokens = tuple(normalize_search_text(query).split())
        if not tokens:
            return []

        with self._connect() as connection:
            candidates = self._candidate_ids(connection, tokens)
            rows = list(connection.execute("SELECT * FROM search_documents ORDER BY node_id"))

        ranked: list[SearchHit] = []
        for row in rows:
            node_id = str(row["node_id"])
            if candidates is not None and node_id not in candidates:
                continue
            if node_type is not None and str(row["node_type"]) != node_type:
                continue
            tags = tuple(str(item) for item in json.loads(str(row["tags"])))
            if tag is not None and tag not in tags:
                continue
            score = self._score(row, query, tokens)
            if score <= 0:
                continue
            body = " ".join(str(row["body"]).split())
            snippet = body[:157] + "..." if len(body) > 160 else body
            ranked.append(
                SearchHit(
                    node_id=node_id,
                    title=str(row["title"]),
                    path=str(row["path"]),
                    node_type=str(row["node_type"]),
                    tags=tags,
                    score=score,
                    snippet=snippet,
                )
            )
        ranked.sort(key=lambda hit: (-hit.score, hit.node_id))
        return ranked[:limit]
