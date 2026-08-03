from __future__ import annotations

import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = ROOT / "site"
ROUTE_DOCUMENTS = (
    "site/index.mdx",
    "site/guide/index.mdx",
    "site/knowledge-network/index.mdx",
    "site/features/index.mdx",
    "site/security/index.mdx",
    "site/reference/index.mdx",
    "site/en/index.mdx",
    "site/en/guide/index.mdx",
    "site/en/knowledge-network/index.mdx",
    "site/en/features/index.mdx",
    "site/en/security/index.mdx",
    "site/en/reference/index.mdx",
)


def read_text(relative_path: str) -> str:
    path = ROOT / relative_path
    assert path.is_file(), f"missing required site file: {relative_path}"
    return path.read_text(encoding="utf-8")


def read_frontmatter(relative_path: str) -> tuple[dict[str, object], str]:
    source = read_text(relative_path)
    assert source.startswith("---\n"), f"missing frontmatter: {relative_path}"
    _, raw_frontmatter, body = source.split("---", maxsplit=2)
    parsed = yaml.safe_load(raw_frontmatter)
    assert isinstance(parsed, dict)
    return parsed, body


def test_node_package_pins_the_silen_toolchain() -> None:
    package = json.loads(read_text("package.json"))

    assert package["private"] is True
    assert package["type"] == "module"
    assert package["packageManager"] == "pnpm@10.34.0"
    assert package["engines"]["node"] == "^20.19.0 || >=22.12.0"
    assert package["devDependencies"]["@aicode-nexus/silen"] == "0.5.0"
    assert package["scripts"] == {
        "site:dev": "silen dev site --host 127.0.0.1 --port 5173",
        "site:build": "silen build site",
        "site:audit": "silen ai audit site",
        "site:eval": "silen ai eval site --json",
        "site:contract": "node scripts/check-silen-site.mjs",
        "site:check": "pnpm site:build && pnpm site:audit && pnpm site:eval && pnpm site:contract",
    }


def test_silen_config_is_strict_pages_safe_and_bilingual() -> None:
    config = read_text("site/.silen/config.ts")

    required_fragments = (
        "defineConfig",
        "title: 'Mini-Wiki'",
        "lang: 'zh-CN'",
        "base: '/mini-wiki/'",
        "siteUrl: 'https://trsoliu.github.io'",
        "onBrokenLinks: 'error'",
        "search: true",
        "locales:",
        "'/en/'",
        "https://github.com/trsoliu/mini-wiki",
        "contract:",
        "instructions: '.silen/ai-public.md'",
    )
    for fragment in required_fragments:
        assert fragment in config


def test_silen_ssr_stays_inside_the_project_dependency_graph() -> None:
    config = read_text("site/.silen/config.ts")

    assert "definePlugin" in config
    assert "mini-wiki:ssr-isolation" in config
    assert "noExternal: true" in config


def test_theme_uses_semantic_tokens_and_local_assets() -> None:
    theme = read_text("site/.silen/theme.tsx")
    css = read_text("site/.silen/custom.css")
    logo = read_text("site/public/logo.svg")

    assert "extends: DefaultTheme" in theme
    assert "data-product-docs" in theme
    assert "--silen-background" in css
    assert "--silen-primary" in css
    assert "prefers-reduced-motion" in css
    assert "focus-visible" in css
    assert 'width="40"' in logo
    assert 'height="40"' in logo


def test_public_agent_contract_and_evals_cover_product_boundaries() -> None:
    instructions = read_text("site/.silen/ai-public.md")
    evaluations = json.loads(read_text("site/.silen/ai-evals.json"))

    assert evaluations["schemaVersion"] == 3
    assert len(evaluations["cases"]) == 6
    case_ids = {case["id"] for case in evaluations["cases"]}
    assert case_ids == {
        "install-mini-wiki",
        "deterministic-ownership",
        "chinese-search",
        "bases-and-canvas",
        "instruction-only-plugins",
        "optional-obsidian",
    }
    for phrase in ("wiki/", ".mini-wiki/", "source evidence", "instruction-only", "Obsidian"):
        assert phrase in instructions


def test_site_sources_do_not_reference_private_or_machine_local_inputs() -> None:
    assert SITE_ROOT.is_dir(), "missing isolated public site root"

    blocked_fragments = (
        "docs/wechat-publish-notes.md",
        "tmp/",
        "/Users/",
        "file://",
    )
    source_files = [
        path
        for path in SITE_ROOT.rglob("*")
        if path.is_file()
        and ".silen/dist" not in path.as_posix()
        and ".silen/.temp" not in path.as_posix()
        and ".silen/cache" not in path.as_posix()
    ]
    assert source_files
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        for blocked in blocked_fragments:
            assert blocked not in text, f"{blocked!r} leaked into {path.relative_to(ROOT)}"


def test_all_public_routes_are_bilingual_and_uniquely_described() -> None:
    titles: list[str] = []
    descriptions: list[str] = []

    for relative_path in ROUTE_DOCUMENTS:
        frontmatter, body = read_frontmatter(relative_path)
        title = frontmatter.get("title")
        description = frontmatter.get("description")
        assert isinstance(title, str) and title.strip()
        assert isinstance(description, str) and description.strip()
        assert "](/" in body, f"missing internal navigation link: {relative_path}"
        titles.append(title)
        descriptions.append(description)

    assert len(titles) == len(set(titles))
    assert len(descriptions) == len(set(descriptions))


def test_homepages_lead_with_install_and_expose_the_knowledge_graph() -> None:
    for relative_path, guide_link in (
        ("site/index.mdx", "/guide/"),
        ("site/en/index.mdx", "/en/guide/"),
    ):
        frontmatter, body = read_frontmatter(relative_path)
        assert frontmatter["layout"] == "home"
        assert "npx skills add trsoliu/mini-wiki" in body
        assert "3.3.0" in body
        assert guide_link in body
        assert "https://github.com/trsoliu/mini-wiki" in body
        assert 'className="mw-knowledge-graph"' in body
        assert 'className="mw-graph-node' in body
        for artifact in (
            "/llms.txt",
            "/llms-full.txt",
            "/ai-index.json",
            "/.well-known/silen/manifest.json",
        ):
            assert artifact in body


def test_security_pages_state_the_non_executable_and_optional_boundaries() -> None:
    for relative_path, safety_rule in (
        ("site/security/index.mdx", "绝不导入或执行"),
        ("site/en/security/index.mdx", "never import or execute"),
    ):
        _, body = read_frontmatter(relative_path)
        for phrase in ("instruction-only", "wiki/", ".mini-wiki/", ".obsidian/", "Obsidian"):
            assert phrase in body
        assert safety_rule in body


def test_reference_pages_only_document_verified_v3_commands() -> None:
    commands = (
        "mini-wiki init",
        "mini-wiki doctor",
        "mini-wiki build --dry-run --json",
        "mini-wiki build --json",
        "mini-wiki check --strict --json",
        "mini-wiki search",
        "mini-wiki migrate --apply --adopt --json",
        "mini-wiki obsidian status --probe --json",
        "mini-wiki plugins install",
    )
    for relative_path in ("site/reference/index.mdx", "site/en/reference/index.mdx"):
        _, body = read_frontmatter(relative_path)
        assert "3.3.0" in body
        for command in commands:
            assert command in body
