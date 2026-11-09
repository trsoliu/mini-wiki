"""专利解读 Obsidian 库增强入口。

实现已按职责拆到同目录：
- obsidian_paths.py：模板 / CSS 路径
- obsidian_frontmatter.py：YAML 解析与入库字段
- obsidian_claims.py：权利要求树与 mermaid
- obsidian_glossary.py：术语网、相关笔记扫描
- obsidian_canvas.py：JSON Canvas
- obsidian_bootstrap.py：库初始化与索引

本模块再导出原公开符号，旧的 `from vault.obsidian import …` 仍然可用。
"""
from __future__ import annotations

try:
    from vault.obsidian_bootstrap import (
        bootstrap_vault,
        build_patent_graph_color_groups,
        ensure_colored_tags_seed,
        ensure_domain_index,
        ensure_graph_color_groups,
        try_obsidian_cli_property,
        upsert_index_entry,
    )
    from vault.obsidian_canvas import build_canvas, ensure_canvas_nav
    from vault.obsidian_claims import (
        claim_delta_text,
        claim_deltas_from_tree,
        claim_tree_to_mermaid,
        harvest_claim_summaries_from_note,
        load_claim_deltas,
        merge_claim_summaries,
        render_claim_tree_markdown,
        upsert_claim_tree_section,
    )
    from vault.obsidian_frontmatter import (
        build_tags,
        enrich_note_frontmatter,
        evidence_scope_label,
        evidence_scope_zh,
        load_tech_effect,
        parse_frontmatter,
        render_frontmatter,
        speculative_zh,
    )
    from vault.obsidian_glossary import (
        append_glossary_backlinks,
        ensure_glossary_stub,
        is_spurious_patent_note,
        normalize_wiki_path,
        purge_spurious_patent_notes,
        repair_glossary_backlinks,
        resolve_glossary_nodes,
        scan_glossary_index,
        scan_vault_related,
    )
    from vault.obsidian_paths import ASSETS_OBSIDIAN, repo_obsidian_base_src
except ImportError:
    from tools.patent_reader.vault.obsidian_bootstrap import (
        bootstrap_vault,
        build_patent_graph_color_groups,
        ensure_colored_tags_seed,
        ensure_domain_index,
        ensure_graph_color_groups,
        try_obsidian_cli_property,
        upsert_index_entry,
    )
    from tools.patent_reader.vault.obsidian_canvas import build_canvas, ensure_canvas_nav
    from tools.patent_reader.vault.obsidian_claims import (
        claim_delta_text,
        claim_deltas_from_tree,
        claim_tree_to_mermaid,
        harvest_claim_summaries_from_note,
        load_claim_deltas,
        merge_claim_summaries,
        render_claim_tree_markdown,
        upsert_claim_tree_section,
    )
    from tools.patent_reader.vault.obsidian_frontmatter import (
        build_tags,
        enrich_note_frontmatter,
        evidence_scope_label,
        evidence_scope_zh,
        load_tech_effect,
        parse_frontmatter,
        render_frontmatter,
        speculative_zh,
    )
    from tools.patent_reader.vault.obsidian_glossary import (
        append_glossary_backlinks,
        ensure_glossary_stub,
        is_spurious_patent_note,
        normalize_wiki_path,
        purge_spurious_patent_notes,
        repair_glossary_backlinks,
        resolve_glossary_nodes,
        scan_glossary_index,
        scan_vault_related,
    )
    from tools.patent_reader.vault.obsidian_paths import ASSETS_OBSIDIAN, repo_obsidian_base_src

__all__ = [
    "ASSETS_OBSIDIAN",
    "append_glossary_backlinks",
    "bootstrap_vault",
    "build_canvas",
    "build_patent_graph_color_groups",
    "build_tags",
    "claim_delta_text",
    "claim_deltas_from_tree",
    "claim_tree_to_mermaid",
    "enrich_note_frontmatter",
    "ensure_canvas_nav",
    "ensure_colored_tags_seed",
    "ensure_domain_index",
    "ensure_glossary_stub",
    "ensure_graph_color_groups",
    "evidence_scope_label",
    "evidence_scope_zh",
    "harvest_claim_summaries_from_note",
    "is_spurious_patent_note",
    "load_claim_deltas",
    "load_tech_effect",
    "merge_claim_summaries",
    "normalize_wiki_path",
    "parse_frontmatter",
    "purge_spurious_patent_notes",
    "render_claim_tree_markdown",
    "render_frontmatter",
    "repair_glossary_backlinks",
    "repo_obsidian_base_src",
    "resolve_glossary_nodes",
    "scan_glossary_index",
    "scan_vault_related",
    "speculative_zh",
    "try_obsidian_cli_property",
    "upsert_claim_tree_section",
    "upsert_index_entry",
]
