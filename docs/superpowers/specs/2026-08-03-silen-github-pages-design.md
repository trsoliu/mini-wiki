# Mini-Wiki Silen GitHub Pages Design

**Date:** 2026-08-03

**Status:** Approved for implementation

**Repository:** `trsoliu/mini-wiki`

**Public URL:** `https://trsoliu.github.io/mini-wiki/`

## 1. Goal

Create a production-quality, bilingual Mini-Wiki product and documentation site with
[`@aicode-nexus/silen`](https://github.com/AICode-Nexus/silen). The site must make installation the primary
conversion, explain the v3.3 knowledge-network model, provide durable reference material, expose Silen's
AI-readable artifacts, deploy through GitHub Actions, and become the repository Homepage shown in GitHub About.

## 2. Audience and primary action

The primary audience is developers and AI-engineering leads evaluating a repository documentation workflow.
Chinese is the default language; every public route has an English counterpart.

The homepage action hierarchy is:

1. install Mini-Wiki;
2. open the five-minute guide;
3. inspect the GitHub repository and release.

The site is a curated product surface, not a mirror of every repository document.

## 3. Public-content boundary

Site sources live under `site/`. Existing `docs/` content is not part of the Silen content root because it contains
implementation plans and may contain private or unpublished material. In particular, untracked
`docs/wechat-publish-notes.md` and `tmp/` remain outside the build, commit, and Pages artifact.

The static output lives at `site/.silen/dist` and is ignored locally. GitHub Actions uploads that directory directly
to Pages. The legacy `main:/docs` Pages source is replaced only after the Actions workflow is present on `main`.

## 4. Information architecture

| Chinese route | English route | Purpose |
| --- | --- | --- |
| `/` | `/en/` | Product homepage and installation conversion |
| `/guide/` | `/en/guide/` | Five-minute install/build/search/check workflow |
| `/knowledge-network/` | `/en/knowledge-network/` | Project → domain → module → source → symbol model |
| `/features/` | `/en/features/` | Properties, search, Bases, Canvas, deterministic builds |
| `/security/` | `/en/security/` | Instruction-only plugins, source boundaries, recovery |
| `/reference/` | `/en/reference/` | CLI and configuration reference |

Global navigation exposes Guide, Knowledge Network, Capabilities, Security, Reference, language switch, search,
appearance control, and GitHub.

## 5. Visual direction

The visual concept is **engineering blueprint meets knowledge graph**:

- deep ink surfaces and warm paper content areas;
- electric cyan as the single primary action and graph-edge color;
- amber used only for evidence, warnings, and source-trace cues;
- a restrained grid/noise background rather than generic gradients;
- large editorial typography paired with compact monospace labels;
- squared, technical geometry with small radii and precise borders;
- one memorable homepage network diagram built from semantic HTML/CSS, not a decorative stock image;
- staggered CSS entrance motion with `prefers-reduced-motion` fallback;
- complete light/dark contrast through Silen semantic tokens.

The page avoids generic feature-card marketing. Capabilities are presented as an evidence chain: repository input,
stable graph, managed Markdown, searchable views, validated output.

## 6. Homepage composition

1. **Hero:** Mini-Wiki name, knowledge-network promise, install action, GitHub action, current version, and a visual
   project/domain/module/source/symbol graph.
2. **Proof strip:** deterministic build, standalone search, four Bases, three Canvas views, strict validation.
3. **Workflow:** `init → build → Agent enriches → build → check --strict → search`.
4. **Two readers:** one source serving human maintainers and AI Agents.
5. **Safety boundary:** durable `wiki/`, rebuildable `.mini-wiki/`, instruction-only plugins, optional Obsidian.
6. **Live artifacts:** links to `llms.txt`, `llms-full.txt`, `ai-index.json`, Markdown routes, and Agent Contract.
7. **Final action:** install command and release link.

## 7. Silen architecture

The root JavaScript package is private and pins:

- Node.js `^20.19.0 || >=22.12.0`;
- pnpm `10.34.0`;
- `@aicode-nexus/silen` `0.5.0`.

The Silen configuration sets:

```ts
export default defineConfig({
  title: 'Mini-Wiki',
  description: 'A source-traceable project knowledge network for people and AI.',
  lang: 'zh-CN',
  base: '/mini-wiki/',
  siteUrl: 'https://trsoliu.github.io',
  onBrokenLinks: 'error',
})
```

The site enables local search, semantic theme tokens, Chinese/English locale navigation, public Agent Contract, and
Silen's deterministic AI outputs. It does not enable Ask AI, remote MCP, analytics, external fonts, or runtime
network calls.

## 8. Build and deployment

Root scripts provide:

- `site:dev` — start Silen locally;
- `site:build` — build static output;
- `site:audit` — run Silen AI audit;
- `site:eval` — run deterministic retrieval evaluation;
- `site:check` — build, audit, eval, and assert required public artifacts.

`.github/workflows/pages.yml`:

1. checks out `main`;
2. installs Node 22.12 and pnpm 10.34;
3. performs a frozen install;
4. runs `pnpm site:check`;
5. asserts `site/.silen/dist/.well-known/silen/manifest.json`;
6. uploads hidden files with the Pages artifact;
7. deploys through `actions/deploy-pages`.

The workflow has `contents: read`, `pages: write`, and `id-token: write` only. Pages is switched to Actions after the
workflow reaches `main`; the GitHub repository Homepage is then updated to the verified public URL.

## 9. AI readiness

The site commits a model-free `.silen/ai-evals.json` suite covering:

- installation;
- deterministic build and ownership regions;
- Chinese search;
- Bases and Canvas;
- instruction-only plugin safety;
- optional Obsidian behavior.

Build output must contain `llms.txt`, `llms-full.txt`, `ai-index.json`, route Markdown, sitemap, robots metadata, and
the public Agent Contract. Evaluation failures block Pages deployment.

## 10. Validation

Local gates:

- frozen dependency installation;
- Silen production build with broken links treated as errors;
- AI audit and deterministic eval;
- existing Python test, Ruff, formatting, and Mypy gates;
- package and Markdown formatting checks;
- direct checks for all Chinese and English routes and AI artifacts.

Browser QA covers desktop and mobile widths, light and dark appearances, navigation, language switching, local
search, keyboard focus, reduced motion, direct nested routes, 404 handling, and horizontal overflow.

Post-deployment QA verifies the live root, a nested Chinese route, an English route, `llms.txt`, the Agent Contract,
and the GitHub About Homepage.

## 11. Failure and rollback

- A failed Silen build or AI gate prevents deployment and leaves the current Pages site intact.
- The legacy Pages source is changed only after the new workflow exists remotely.
- If live checks fail, restore the prior Pages source or revert the Pages commit; do not rewrite the v3.3.0 tag.
- The site never consumes untracked or state-directory content.

## 12. Non-goals

- No hosted Ask AI endpoint.
- No remote MCP server.
- No publication of internal plans, cache, archives, test fixtures, or private notes.
- No runtime dependency on Obsidian.
- No modification of Mini-Wiki's v3.3.0 release tag or release asset.
