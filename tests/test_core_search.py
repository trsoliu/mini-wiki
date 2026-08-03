"""Tests for Chinese-aware standalone Mini-Wiki search."""

from pathlib import Path

from mini_wiki_core.search import (
    SearchDocument,
    SearchIndex,
    normalize_search_text,
)


def search_documents() -> list[SearchDocument]:
    return [
        SearchDocument(
            "plugin-system",
            "插件系统",
            ("Plugin System",),
            ("domain/core",),
            "安装插件",
            "module",
            "wiki/plugin.md",
            ("src/plugin.py",),
        ),
        SearchDocument(
            "storage",
            "存储",
            (),
            ("domain/storage",),
            "plugin cache",
            "module",
            "wiki/storage.md",
            ("src/storage.py",),
        ),
    ]


def test_normalize_search_text_adds_cjk_unigrams_and_bigrams():
    normalized = normalize_search_text("插件 Plugin")

    assert {"插", "件", "插件", "plugin"} <= set(normalized.split())


def test_search_ranks_exact_title_before_body(tmp_path: Path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    index.update(
        [
            SearchDocument("a", "插件系统", (), ("core",), "无", "module", "wiki/a.md", ()),
            SearchDocument("b", "系统", (), ("core",), "正文介绍插件系统", "module", "wiki/b.md", ()),
        ]
    )

    hits = index.search("插件系统")

    assert [hit.node_id for hit in hits] == ["a", "b"]
    assert hits[0].score > hits[1].score


def test_search_filters_type_and_tag(tmp_path: Path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    index.update(search_documents())

    hits = index.search("plugin", node_type="module", tag="domain/core", limit=1)

    assert len(hits) == 1
    assert hits[0].node_type == "module"
    assert "domain/core" in hits[0].tags


def test_memory_fallback_has_same_top_hit(tmp_path: Path):
    documents = search_documents()
    normal = SearchIndex(tmp_path / "normal.sqlite3")
    fallback = SearchIndex(tmp_path / "fallback.sqlite3", force_fallback=True)
    normal.update(documents)
    fallback.update(documents)

    assert fallback.mode == "fallback"
    assert fallback.search("插件")[0].node_id == "plugin-system"
    assert fallback.search("插件")[0].node_id == normal.search("插件")[0].node_id


def test_second_index_update_reports_no_changes(tmp_path: Path):
    index = SearchIndex(tmp_path / "search.sqlite3")

    first = index.update(search_documents())
    second = index.update(search_documents())

    assert first.created == ("plugin-system", "storage")
    assert second.created == ()
    assert second.modified == ()
    assert second.deleted == ()


def test_index_update_reports_modified_and_deleted_documents(tmp_path: Path):
    index = SearchIndex(tmp_path / "search.sqlite3")
    index.update(search_documents())
    changed = SearchDocument(
        "plugin-system",
        "插件系统",
        (),
        ("domain/core",),
        "更新后的安装说明",
        "module",
        "wiki/plugin.md",
        (),
    )

    update = index.update([changed])

    assert update.modified == ("plugin-system",)
    assert update.deleted == ("storage",)
    assert index.search("cache") == []
