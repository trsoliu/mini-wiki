# Mini-Wiki VitePress-Style Theme Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current poster-like Mini-Wiki site with a restrained VitePress-style bilingual documentation theme and remove duplicate page navigation from the header.

**Architecture:** Keep Silen `DefaultTheme`, all 12 routes, AI outputs, and the Pages pipeline intact. Change only the navigation data, both home-page MDX documents, the custom CSS layer, and their repository contract tests; each behavior change follows a red-green test cycle before browser QA.

**Tech Stack:** Silen 0.5.0, MDX, React theme extension, CSS custom properties, pytest contract tests, Playwright CLI, GitHub Actions Pages.

## Global Constraints

- Work directly on the already authorized `main` branch; never stage `docs/wechat-publish-notes.md` or `tmp/`.
- Do not add dependencies, routes, remote fonts, or runtime JavaScript.
- Preserve bilingual search, locale switching, appearance controls, AI outputs, strict links, and `base: '/mini-wiki/'`.
- Header navigation contains only global actions and release metadata; the sidebar owns all five documentation routes.
- Home pages contain a two-column hero, two CTAs, the install command, six feature cards, and four AI artifact links.
- Use semantic Silen tokens, keyboard focus styles, and `prefers-reduced-motion` behavior.
- Verify at 1440px desktop and 375px mobile with no horizontal overflow.

## File Map

- `site/.silen/config.ts`: owns bilingual header navigation and sidebar information architecture.
- `site/index.mdx`: owns the concise Chinese product homepage.
- `site/en/index.mdx`: owns the structurally equivalent English product homepage.
- `site/.silen/custom.css`: owns Mini-Wiki semantic colors, VitePress-like document refinements, homepage layout, responsiveness, and reduced motion.
- `tests/test_site_contract.py`: owns static source contracts for navigation, homepage structure, theme safety, and publishing invariants.

---

### Task 1: Separate Global Header Navigation from the Documentation Tree

**Files:**
- Modify: `tests/test_site_contract.py`
- Modify: `site/.silen/config.ts`

**Interfaces:**
- Consumes: Silen `themeConfig.nav`, `themeConfig.sidebar`, and locale overrides.
- Produces: `zhNav` and `enNav` containing only the release link; `zhSidebar` and `enSidebar` containing all five documentation routes in three task-oriented groups.

- [ ] **Step 1: Write the failing navigation contract test**

Add this test after `test_silen_config_is_strict_pages_safe_and_bilingual`:

```python
def test_header_navigation_is_global_and_sidebar_owns_document_routes() -> None:
    config = read_text("site/.silen/config.ts")
    zh_nav = config.split("const zhNav =", 1)[1].split("const enNav =", 1)[0]
    en_nav = config.split("const enNav =", 1)[1].split("const zhSidebar =", 1)[0]
    zh_sidebar = config.split("const zhSidebar =", 1)[1].split("const enSidebar =", 1)[0]
    en_sidebar = config.split("const enSidebar =", 1)[1].split("export default", 1)[0]

    assert "v3.3.0" in zh_nav
    assert "v3.3.0" in en_nav
    for route in ("/guide/", "/knowledge-network/", "/features/", "/security/", "/reference/"):
        assert f"link: '{route}'" not in zh_nav
        assert zh_sidebar.count(f"link: '{route}'") == 1
    for route in (
        "/en/guide/",
        "/en/knowledge-network/",
        "/en/features/",
        "/en/security/",
        "/en/reference/",
    ):
        assert f"link: '{route}'" not in en_nav
        assert en_sidebar.count(f"link: '{route}'") == 1
    for group in ("开始使用", "核心概念", "运维与参考", "Get started", "Core concepts", "Operations and reference"):
        assert group in config
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
.venv/bin/python -m pytest tests/test_site_contract.py::test_header_navigation_is_global_and_sidebar_owns_document_routes -q
```

Expected: FAIL because `/guide/` and the other document routes are still present in `zhNav` and `enNav`.

- [ ] **Step 3: Implement the minimal navigation split**

Replace the four navigation constants in `site/.silen/config.ts` with:

```ts
const releaseUrl = 'https://github.com/trsoliu/mini-wiki/releases/tag/v3.3.0'

const zhNav = [{ text: 'v3.3.0', link: releaseUrl }]

const enNav = [{ text: 'v3.3.0', link: releaseUrl }]

const zhSidebar = [
  {
    text: '开始使用',
    items: [{ text: '五分钟上手', link: '/guide/' }],
  },
  {
    text: '核心概念',
    items: [
      { text: '知识网络', link: '/knowledge-network/' },
      { text: '核心能力', link: '/features/' },
    ],
  },
  {
    text: '运维与参考',
    items: [
      { text: '安全边界', link: '/security/' },
      { text: '命令与配置', link: '/reference/' },
    ],
  },
]

const enSidebar = [
  {
    text: 'Get started',
    items: [{ text: 'Five-minute guide', link: '/en/guide/' }],
  },
  {
    text: 'Core concepts',
    items: [
      { text: 'Knowledge network', link: '/en/knowledge-network/' },
      { text: 'Core features', link: '/en/features/' },
    ],
  },
  {
    text: 'Operations and reference',
    items: [
      { text: 'Security boundaries', link: '/en/security/' },
      { text: 'CLI and configuration', link: '/en/reference/' },
    ],
  },
]
```

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 5: Commit the navigation change**

```bash
git add site/.silen/config.ts tests/test_site_contract.py
git commit -m "fix: separate global and document navigation"
```

---

### Task 2: Replace Both Poster-Style Homepages with VitePress-Style Product Homes

**Files:**
- Modify: `tests/test_site_contract.py`
- Modify: `site/index.mdx`
- Modify: `site/en/index.mdx`

**Interfaces:**
- Consumes: `layout: home`, internal guide routes, the public GitHub URL, and the four Silen AI artifact routes.
- Produces: matching `.mw-home-hero`, `.mw-hero-visual`, `.mw-feature-grid`, `.mw-feature-card`, and `.mw-ai-links` structures for both locales.

- [ ] **Step 1: Replace the old homepage contract with a failing structural contract**

Replace `test_homepages_lead_with_install_and_expose_the_knowledge_graph` with:

```python
def test_homepages_use_the_vitepress_style_product_structure() -> None:
    for relative_path, guide_link, primary_label, github_label in (
        ("site/index.mdx", "/guide/", "开始使用", "在 GitHub 查看"),
        ("site/en/index.mdx", "/en/guide/", "Get started", "View on GitHub"),
    ):
        frontmatter, body = read_frontmatter(relative_path)
        assert frontmatter["layout"] == "home"
        assert "npx skills add trsoliu/mini-wiki" in body
        assert "3.3.0" in body
        assert guide_link in body
        assert primary_label in body
        assert github_label in body
        assert body.count('className="mw-feature-card"') == 6
        assert 'className="mw-home-hero"' in body
        assert 'className="mw-hero-visual"' in body
        assert 'className="mw-feature-grid"' in body
        assert 'className="mw-ai-links"' in body
        assert "mw-knowledge-graph" not in body
        assert "mw-proof-strip" not in body
        assert "mw-workflow" not in body
        for artifact in (
            "/llms.txt",
            "/llms-full.txt",
            "/ai-index.json",
            "/.well-known/silen/manifest.json",
        ):
            assert artifact in body
```

- [ ] **Step 2: Run the focused test and verify RED**

```bash
.venv/bin/python -m pytest tests/test_site_contract.py::test_homepages_use_the_vitepress_style_product_structure -q
```

Expected: FAIL because the old homepages contain `.mw-knowledge-graph` and do not contain `.mw-feature-grid`.

- [ ] **Step 3: Implement the Chinese homepage**

Keep the current frontmatter and replace its body with this structure and final Chinese copy:

```mdx
<section className="mw-home-hero">
  <div className="mw-hero-copy">
    <p className="mw-kicker">Mini-Wiki 3.3.0</p>
    <h1><span>Mini-Wiki</span>把代码仓库变成可追溯的知识网络</h1>
    <p className="mw-tagline">为维护者与 AI Agent 生成确定性、可搜索、可版本化的项目知识。</p>
    <div className="mw-actions">

[开始使用](/guide/)

[在 GitHub 查看](https://github.com/trsoliu/mini-wiki)

    </div>
    <div className="mw-install" aria-label="安装 Mini-Wiki"><span aria-hidden="true">$</span><code>npx skills add trsoliu/mini-wiki</code></div>
  </div>
  <div className="mw-hero-visual" aria-hidden="true"><div className="mw-logo-halo"><img src="/logo.svg" alt="" /></div></div>
</section>

<section className="mw-feature-grid" aria-label="Mini-Wiki 核心能力">
  <article className="mw-feature-card"><span>01</span><h2>确定性构建</h2><p>稳定 ID、事务写入与可重复构建，让知识变更可以审查和重放。</p></article>
  <article className="mw-feature-card"><span>02</span><h2>源码可追溯</h2><p>项目、领域、模块、文件与符号都能回到明确的仓库证据。</p></article>
  <article className="mw-feature-card"><span>03</span><h2>中英混合搜索</h2><p>本地检索 Markdown、Properties、图谱元数据与有界源码文本。</p></article>
  <article className="mw-feature-card"><span>04</span><h2>Bases 与 Canvas</h2><p>用结构化队列治理知识，用空间视图探索项目关系。</p></article>
  <article className="mw-feature-card"><span>05</span><h2>安全协作边界</h2><p>CLI 管理结构，Agent 只在受保护内容区内补充证据化解释。</p></article>
  <article className="mw-feature-card"><span>06</span><h2>面向 AI Agent</h2><p>同源生成搜索索引、Markdown 路由与模型无关的发现文件。</p></article>
</section>

<section className="mw-ai-strip">
  <div><p className="mw-kicker">AI-ready documentation</p><h2>一次构建，同时服务人和 Agent。</h2><p>所有公开入口来自同一组受控页面。</p></div>
  <div className="mw-ai-links">

[`llms.txt`](/llms.txt)

[`llms-full.txt`](/llms-full.txt)

[`ai-index.json`](/ai-index.json)

[`Agent Contract`](/.well-known/silen/manifest.json)

  </div>
</section>
```

- [ ] **Step 4: Implement the English homepage**

Keep the current English frontmatter and replace its body with:

```mdx
<section className="mw-home-hero">
  <div className="mw-hero-copy">
    <p className="mw-kicker">Mini-Wiki 3.3.0</p>
    <h1><span>Mini-Wiki</span>Turn repositories into traceable knowledge networks</h1>
    <p className="mw-tagline">Build deterministic, searchable, versioned project knowledge for maintainers and AI agents.</p>
    <div className="mw-actions">

[Get started](/en/guide/)

[View on GitHub](https://github.com/trsoliu/mini-wiki)

    </div>
    <div className="mw-install" aria-label="Install Mini-Wiki"><span aria-hidden="true">$</span><code>npx skills add trsoliu/mini-wiki</code></div>
  </div>
  <div className="mw-hero-visual" aria-hidden="true"><div className="mw-logo-halo"><img src="/logo.svg" alt="" /></div></div>
</section>

<section className="mw-feature-grid" aria-label="Mini-Wiki core capabilities">
  <article className="mw-feature-card"><span>01</span><h2>Deterministic builds</h2><p>Stable IDs, transactional writes, and repeatable output make knowledge changes reviewable and reproducible.</p></article>
  <article className="mw-feature-card"><span>02</span><h2>Source traceability</h2><p>Projects, domains, modules, files, and symbols all resolve to explicit repository evidence.</p></article>
  <article className="mw-feature-card"><span>03</span><h2>CJK-aware search</h2><p>Retrieve Markdown, Properties, graph metadata, and bounded source text locally.</p></article>
  <article className="mw-feature-card"><span>04</span><h2>Bases and Canvas</h2><p>Govern knowledge through structured queues and explore project relationships spatially.</p></article>
  <article className="mw-feature-card"><span>05</span><h2>Safe collaboration</h2><p>The CLI owns structure while agents add evidence-based explanation only inside protected regions.</p></article>
  <article className="mw-feature-card"><span>06</span><h2>Agent-ready output</h2><p>Generate search indexes, Markdown routes, and model-independent discovery files from one source.</p></article>
</section>

<section className="mw-ai-strip">
  <div><p className="mw-kicker">AI-ready documentation</p><h2>Build once for humans and agents.</h2><p>Every public surface comes from the same curated pages.</p></div>
  <div className="mw-ai-links">

[`llms.txt`](/llms.txt)

[`llms-full.txt`](/llms-full.txt)

[`ai-index.json`](/ai-index.json)

[`Agent Contract`](/.well-known/silen/manifest.json)

  </div>
</section>
```

- [ ] **Step 5: Run the focused test and verify GREEN**

Run the Step 2 command again.

Expected: `1 passed`.

- [ ] **Step 6: Commit the homepage change**

```bash
git add site/index.mdx site/en/index.mdx tests/test_site_contract.py
git commit -m "feat: simplify Mini-Wiki product home"
```

---

### Task 3: Replace the Experimental CSS with a Restrained Documentation Theme

**Files:**
- Modify: `tests/test_site_contract.py`
- Modify: `site/.silen/custom.css`

**Interfaces:**
- Consumes: Silen semantic color variables and the homepage class contract from Task 2.
- Produces: VitePress-like light/dark tokens, compact documentation typography, three-to-one-column feature layout, and accessible interaction states.

- [ ] **Step 1: Write the failing theme contract**

Add after `test_theme_uses_semantic_tokens_and_local_assets`:

```python
def test_theme_is_restrained_and_vitepress_like() -> None:
    css = read_text("site/.silen/custom.css")

    for fragment in (
        "--mw-brand: #3451b2",
        "--silen-nav-height: 4rem",
        ".mw-home-hero",
        ".mw-hero-visual",
        ".mw-feature-grid",
        "grid-template-columns: repeat(3, minmax(0, 1fr))",
        ".mw-ai-strip",
        "backdrop-filter: blur(12px)",
        "@media (max-width: 48rem)",
    ):
        assert fragment in css
    for old_fragment in (
        "--mini-wiki-grid",
        ".mw-knowledge-graph",
        ".mw-graph-node",
        ".mw-proof-strip",
        ".mw-workflow",
        "font-size: clamp(3.5rem, 8.8vw, 7.8rem)",
    ):
        assert old_fragment not in css
```

Retain `test_home_action_hierarchy_has_only_one_primary_link`, because the VitePress-style action group still has one primary CTA.

- [ ] **Step 2: Run the focused test and verify RED**

```bash
.venv/bin/python -m pytest tests/test_site_contract.py::test_theme_is_restrained_and_vitepress_like -q
```

Expected: FAIL because the old stylesheet contains the grid and knowledge-graph rules and lacks the new token/layout contract.

- [ ] **Step 3: Replace `custom.css` with the new theme**

The complete replacement must implement these exact blocks:

```css
:root {
  --mw-brand: #3451b2;
  --mw-brand-hover: #2f49a0;
  --mw-brand-soft: #eef2ff;
  --silen-background: #ffffff;
  --silen-foreground: #1b1b1f;
  --silen-card: #f6f6f7;
  --silen-card-foreground: #1b1b1f;
  --silen-primary: var(--mw-brand);
  --silen-primary-foreground: #ffffff;
  --silen-secondary: #f6f6f7;
  --silen-secondary-foreground: #3c3c43;
  --silen-muted: #f6f6f7;
  --silen-muted-foreground: #67676c;
  --silen-popover: #ffffff;
  --silen-popover-foreground: #1b1b1f;
  --silen-accent: var(--mw-brand-soft);
  --silen-accent-foreground: var(--mw-brand);
  --silen-destructive: #b8272c;
  --silen-border: #e2e2e3;
  --silen-input: #d7d7d9;
  --silen-ring: var(--mw-brand);
  --silen-radius: 0.5rem;
  --silen-nav-height: 4rem;
  --silen-sidebar-width: 17rem;
  --silen-content-width: 45rem;
  --silen-layout-width: 90rem;
}

.dark {
  --mw-brand: #a8b1ff;
  --mw-brand-hover: #c4c9ff;
  --mw-brand-soft: #25283a;
  --silen-background: #1b1b1f;
  --silen-foreground: #dfdfe0;
  --silen-card: #202127;
  --silen-card-foreground: #dfdfe0;
  --silen-primary: var(--mw-brand);
  --silen-primary-foreground: #1b1b1f;
  --silen-secondary: #252529;
  --silen-secondary-foreground: #c9c9cc;
  --silen-muted: #252529;
  --silen-muted-foreground: #a7a7ab;
  --silen-popover: #202127;
  --silen-popover-foreground: #dfdfe0;
  --silen-accent: var(--mw-brand-soft);
  --silen-accent-foreground: var(--mw-brand);
  --silen-border: #303038;
  --silen-input: #3c3c44;
  --silen-ring: var(--mw-brand);
}

html,
body {
  background: var(--silen-background);
}

body {
  color: var(--silen-foreground);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", "Helvetica Neue", sans-serif;
  -webkit-font-smoothing: antialiased;
}

[data-product-docs='mini-wiki'] {
  min-height: 100svh;
}

[data-product-docs='mini-wiki'] > header,
[data-product-docs='mini-wiki'] header {
  border-bottom: 1px solid color-mix(in srgb, var(--silen-border) 82%, transparent);
  background: color-mix(in srgb, var(--silen-background) 86%, transparent);
  backdrop-filter: blur(12px);
}

.silen-doc,
.silen-page {
  color: var(--silen-foreground);
  font-size: 1rem;
  line-height: 1.75;
  text-wrap: pretty;
}

.silen-doc h1,
.silen-page h1 {
  max-width: 30ch;
  font-size: clamp(2rem, 5vw, 2.35rem);
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 1.25;
}

.silen-doc h2,
.silen-page h2 {
  border-top: 0;
  padding-top: 1.5rem;
  font-size: 1.5rem;
  letter-spacing: -0.025em;
}

.silen-code-block {
  border: 1px solid var(--silen-border);
  border-radius: 0.5rem;
  box-shadow: none;
}

.product-note {
  margin-block: 1.5rem;
  border: 1px solid color-mix(in srgb, var(--mw-brand) 24%, var(--silen-border));
  border-left: 4px solid var(--mw-brand);
  border-radius: 0.5rem;
  background: var(--mw-brand-soft);
  padding: 1rem 1.1rem;
}

:where(a, button, input, select, textarea):focus-visible {
  outline: 2px solid var(--silen-ring);
  outline-offset: 3px;
}

.mw-home {
  width: min(100%, 74rem);
  margin-inline: auto;
  padding: clamp(4.5rem, 9vw, 7.5rem) 1.5rem 4.5rem;
}

.mw-home-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(20rem, 0.88fr);
  align-items: center;
  gap: clamp(2rem, 7vw, 6rem);
  min-height: 31rem;
}

.mw-hero-copy {
  display: grid;
  gap: 1.5rem;
}

.mw-kicker {
  margin: 0;
  color: var(--mw-brand);
  font-size: 0.9rem;
  font-weight: 650;
}

.mw-home-hero h1 {
  max-width: 13ch;
  margin: 0;
  font-size: clamp(2.65rem, 6vw, 4rem);
  font-weight: 720;
  letter-spacing: -0.055em;
  line-height: 1.08;
  text-wrap: balance;
}

.mw-home-hero h1 span {
  display: block;
  margin-bottom: 0.2em;
  color: var(--mw-brand);
}

.mw-tagline {
  max-width: 38rem;
  margin: 0;
  color: var(--silen-muted-foreground);
  font-size: clamp(1.05rem, 2vw, 1.25rem);
  line-height: 1.65;
}

.mw-actions,
.mw-actions > p {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 0;
}

.mw-actions a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--silen-border);
  border-radius: 1.4rem;
  background: var(--silen-secondary);
  padding: 0.65rem 1.2rem;
  color: var(--silen-secondary-foreground);
  font-weight: 650;
  text-decoration: none;
  transition: border-color 160ms ease, background-color 160ms ease, color 160ms ease;
}

.mw-actions > p:first-child a {
  border-color: var(--mw-brand);
  background: var(--mw-brand);
  color: var(--silen-primary-foreground);
}

.mw-actions a:hover {
  border-color: var(--mw-brand-hover);
  color: var(--mw-brand-hover);
}

.mw-actions > p:first-child a:hover {
  background: var(--mw-brand-hover);
  color: var(--silen-primary-foreground);
}

.mw-install {
  display: flex;
  width: fit-content;
  max-width: 100%;
  align-items: center;
  gap: 0.7rem;
  border: 1px solid var(--silen-border);
  border-radius: 0.5rem;
  background: var(--silen-card);
  padding: 0.75rem 0.9rem;
}

.mw-install span {
  color: var(--mw-brand);
  font-weight: 700;
}

.mw-install code {
  overflow-wrap: anywhere;
  color: var(--silen-card-foreground);
}

.mw-hero-visual {
  display: grid;
  min-height: 23rem;
  place-items: center;
}

.mw-logo-halo {
  display: grid;
  width: min(19rem, 72vw);
  aspect-ratio: 1;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(145deg, color-mix(in srgb, var(--mw-brand) 24%, transparent), color-mix(in srgb, var(--mw-brand) 8%, transparent));
  filter: drop-shadow(0 24px 42px color-mix(in srgb, var(--mw-brand) 18%, transparent));
}

.mw-logo-halo img {
  width: 46%;
  height: auto;
}

.mw-feature-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-top: clamp(4rem, 8vw, 7rem);
}

.mw-feature-card {
  min-width: 0;
  border: 1px solid var(--silen-border);
  border-radius: 0.75rem;
  background: var(--silen-card);
  padding: 1.5rem;
}

.mw-feature-card > span {
  display: inline-grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border-radius: 0.5rem;
  background: var(--mw-brand-soft);
  color: var(--mw-brand);
  font-size: 0.75rem;
  font-weight: 700;
}

.mw-feature-card h2 {
  margin: 1.1rem 0 0.55rem;
  font-size: 1.05rem;
  letter-spacing: -0.015em;
}

.mw-feature-card p {
  margin: 0;
  color: var(--silen-muted-foreground);
  font-size: 0.94rem;
  line-height: 1.65;
}

.mw-ai-strip {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 2rem;
  margin-top: 1rem;
  border: 1px solid var(--silen-border);
  border-radius: 0.75rem;
  background: var(--silen-card);
  padding: clamp(1.5rem, 4vw, 2.5rem);
}

.mw-ai-strip h2 {
  margin: 0.45rem 0 0.6rem;
  font-size: clamp(1.45rem, 3vw, 2rem);
  letter-spacing: -0.03em;
}

.mw-ai-strip p {
  margin-bottom: 0;
  color: var(--silen-muted-foreground);
}

.mw-ai-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
}

.mw-ai-links > p {
  margin: 0;
}

.mw-ai-links a {
  display: flex;
  min-height: 3rem;
  align-items: center;
  border: 1px solid var(--silen-border);
  border-radius: 0.5rem;
  background: var(--silen-background);
  padding: 0.75rem;
  color: var(--mw-brand);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.84rem;
  font-weight: 650;
  text-decoration: none;
}

@media (max-width: 64rem) {
  .mw-home-hero {
    grid-template-columns: minmax(0, 1fr);
  }

  .mw-hero-visual {
    min-height: 18rem;
  }

  .mw-feature-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 48rem) {
  .mw-home {
    padding: 3rem 1rem;
  }

  .mw-home-hero {
    min-height: 0;
  }

  .mw-home-hero h1 {
    font-size: clamp(2.45rem, 12vw, 3.2rem);
  }

  .mw-hero-visual {
    min-height: 15rem;
  }

  .mw-feature-grid,
  .mw-ai-strip,
  .mw-ai-links {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}
```

- [ ] **Step 4: Run the theme and CTA tests and verify GREEN**

```bash
.venv/bin/python -m pytest tests/test_site_contract.py::test_theme_is_restrained_and_vitepress_like tests/test_site_contract.py::test_home_action_hierarchy_has_only_one_primary_link -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit the theme change**

```bash
git add site/.silen/custom.css tests/test_site_contract.py
git commit -m "feat: adopt restrained VitePress-style theme"
```

---

### Task 4: Run Repository and Silen Quality Gates

**Files:**
- Verify only; modify the scoped theme files only if a gate exposes a regression.

**Interfaces:**
- Consumes: Tasks 1 through 3.
- Produces: a complete static build with all 12 routes, passing AI retrieval, no private-path leaks, and no source maps.

- [ ] **Step 1: Run the complete local gate**

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm site:check
.venv/bin/python -m pytest -q
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
.venv/bin/mypy scripts --ignore-missing-imports
git diff --check
```

Expected: 12 routes built, AI audit `ok: true`, AI eval `6/6`, artifact contract passes, pytest has zero failures, Ruff and Mypy report no issues, and `git diff --check` exits 0.

- [ ] **Step 2: Inspect the build artifact contract manually**

Verify that `site/.silen/dist/index.html`, `site/.silen/dist/en/index.html`, nested guide/security routes, `llms.txt`, `ai-index.json`, and `.well-known/silen/manifest.json` exist, and that no `.map`, `/Users/`, `docs/wechat-publish-notes.md`, or `tmp/` fragment exists in generated public files.

---

### Task 5: Browser QA and Visual Corrections

**Files:**
- Modify only if QA fails: `site/.silen/custom.css`, `site/.silen/config.ts`, `site/index.mdx`, `site/en/index.mdx`, `tests/test_site_contract.py`.

**Interfaces:**
- Consumes: the production build from Task 4 served under `/mini-wiki/`.
- Produces: desktop and mobile proof that the navigation is not duplicated and the VitePress-style theme works in both locales and appearances.

- [ ] **Step 1: Start the production preview**

```bash
corepack pnpm exec silen preview site --host 127.0.0.1 --port 4173
```

Expected: `http://127.0.0.1:4173/mini-wiki/` responds.

- [ ] **Step 2: Verify the 1440px Chinese homepage**

Check the accessible snapshot and screenshot for: compact header, only `v3.3.0` as text navigation, no five repeated page links, two-column Hero, restrained Logo halo, six cards, AI link strip, no horizontal overflow, and zero console errors/warnings.

- [ ] **Step 3: Verify a documentation page and English locale**

Open `/mini-wiki/guide/`, confirm the sidebar has exactly the three groups and five pages while the header has no duplicate page links. Switch to English and verify `/mini-wiki/en/guide/` preserves the route and shows the English groups.

- [ ] **Step 4: Verify interactive and responsive states**

Test search, dark mode, keyboard focus, `prefers-reduced-motion`, and the mobile navigation at `375x812`. Require `document.documentElement.scrollWidth - window.innerWidth === 0` and ensure Hero actions/cards stack to one column.

- [ ] **Step 5: Verify the real 404 and public artifacts**

Require `/mini-wiki/not-a-route/` to return 404 with the localized not-found page. Require the root, guide, English root, English security, `llms.txt`, `ai-index.json`, manifest, and robots routes to return 200.

- [ ] **Step 6: Commit only evidence-backed corrections**

If QA finds a defect, first add a failing contract test, verify RED, make the smallest correction, verify GREEN, then commit only the scoped files with `test: harden VitePress theme QA`.

---

### Task 6: Sync, Push, Deploy, and Verify GitHub Pages

**Files:**
- No planned source modification.

**Interfaces:**
- Consumes: verified commits on local `main`.
- Produces: synchronized `origin/main`, successful CI and Pages workflows, and the updated live site at `https://trsoliu.github.io/mini-wiki/`.

- [ ] **Step 1: Recheck branch and remote drift**

```bash
git fetch origin
git status --short --branch
git log --oneline HEAD..origin/main
```

Expected: local `main` has no remote-only commits. The only untracked paths remain `docs/wechat-publish-notes.md` and `tmp/`.

- [ ] **Step 2: Push `main`**

```bash
git push origin main
```

- [ ] **Step 3: Wait for CI and Pages**

Use `gh run list` and `gh run watch --exit-status` for the new head SHA. Require the full Python matrix/lint workflow and `Deploy Mini-Wiki site to Pages` to conclude `success`.

- [ ] **Step 4: Verify the live site instead of trusting workflow status**

Open the public Pages URL in a fresh browser session. Verify the new homepage classes and copy, nested Chinese and English routes, the absence of duplicate header links, AI artifact status codes, mobile overflow, and normal-page console output.

- [ ] **Step 5: Confirm repository metadata and final state**

```bash
gh repo view trsoliu/mini-wiki --json homepageUrl
gh api repos/trsoliu/mini-wiki/pages --jq '{status,build_type,html_url}'
git fetch origin
git status --short --branch
```

Expected: `homepageUrl` is `https://trsoliu.github.io/mini-wiki/`, Pages is `built` with `build_type: workflow`, local `HEAD` equals `origin/main`, and the two user-owned untracked paths remain untouched.
