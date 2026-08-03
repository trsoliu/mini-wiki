# Mini-Wiki Silen GitHub Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, publish, and live-verify a Chinese-first bilingual Mini-Wiki product/documentation site with Silen, then expose it through the repository's GitHub About Homepage field.

**Architecture:** Keep all public site inputs in an isolated `site/` content root and generate `site/.silen/dist` deterministically. A root pnpm package pins Silen and provides build, AI-audit, retrieval-evaluation, and artifact-contract gates. GitHub Actions deploys only the generated Silen directory to Pages; existing repository documentation, local Mini-Wiki state, and untracked private notes remain outside the artifact.

**Tech Stack:** Silen 0.5.0, MDX, React theme extension, semantic CSS, pnpm 10.34.0, Node.js 22.12+, Python pytest contract tests, GitHub Actions Pages, Playwright browser QA, GitHub CLI.

## Global Constraints

- [ ] Work directly on the already-approved `main` branch and preserve unrelated user files.
- [ ] Never stage, publish, or read site content from `docs/wechat-publish-notes.md`, `tmp/`, `.mini-wiki/`, or generated local caches.
- [ ] Keep Chinese as the default locale and provide an English counterpart for every public route.
- [ ] Keep installation as the primary conversion; GitHub and release links are secondary actions.
- [ ] Use only local assets and CSS. Do not add analytics, hosted Ask AI, remote MCP, external fonts, or runtime network dependencies.
- [ ] Treat broken links, failed AI audit/evaluation, missing public artifacts, source-map leakage, and private-path leakage as release blockers.
- [ ] Do not change the existing `v3.3.0` tag or release assets.

---

## Task 1: Lock the public-site contract and Silen foundation

**Files:**

- Create: `tests/test_site_contract.py`
- Create: `package.json`
- Create: `pnpm-lock.yaml`
- Modify: `.gitignore`
- Create: `site/.silen/config.ts`
- Create: `site/.silen/theme.tsx`
- Create: `site/.silen/custom.css`
- Create: `site/.silen/ai-public.md`
- Create: `site/.silen/ai-evals.json`
- Create: `site/public/logo.svg`

### Step 1: Write the failing repository-level contract tests

- [ ] Add tests that require `packageManager` to equal `pnpm@10.34.0`, Node engines to accept the official Silen runtime range, and `@aicode-nexus/silen` to equal `0.5.0` exactly.
- [ ] Require root scripts for `site:dev`, `site:build`, `site:audit`, `site:eval`, `site:contract`, and `site:check`.
- [ ] Require Silen config to contain `base: '/mini-wiki/'`, `siteUrl: 'https://trsoliu.github.io'`, `onBrokenLinks: 'error'`, local search, bilingual locale definitions, GitHub social navigation, and the public Agent Contract.
- [ ] Require the public-content root and AI evaluation suite while rejecting references to `.mini-wiki/`, `docs/wechat-publish-notes.md`, `tmp/`, `/Users/`, and `file://`.

Run:

```bash
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: FAIL because the Silen package and site files do not exist yet.

### Step 2: Create the pinned JavaScript package

- [ ] Add a private ESM `package.json` with Node `^20.19.0 || >=22.12.0`, pnpm `10.34.0`, and exact Silen `0.5.0`.
- [ ] Define `site:dev` as a local-only server on `127.0.0.1:5173`.
- [ ] Define independent build, audit, eval, artifact-contract, and composed `site:check` scripts.
- [ ] Install with the pinned pnpm version and commit the generated lockfile.
- [ ] Ignore `site/.silen/dist`, Silen caches, and local Playwright artifacts without widening existing ignore boundaries.

Run:

```bash
corepack pnpm install
corepack pnpm exec silen --version
```

Expected: install succeeds and the CLI reports Silen 0.5.0.

### Step 3: Add the Silen configuration and theme extension

- [ ] Configure canonical title, description, Chinese default language, Pages base path, site URL, strict broken-link behavior, local search, route-mirroring locales, repository link, and footer metadata.
- [ ] Enable deterministic AI outputs and a public read-only Agent Contract with instructions from `site/.silen/ai-public.md`.
- [ ] Extend the default theme with a product root marker and reusable semantic callout component.
- [ ] Implement the approved “engineering blueprint meets knowledge graph” token system in light and dark appearances.
- [ ] Add responsive layout, visible keyboard focus, reduced-motion fallback, high-contrast code surfaces, and an inline SVG logo with intrinsic dimensions.

### Step 4: Add deterministic AI evaluation fixtures

- [ ] Add schema-version 3 retrieval cases for install, deterministic ownership, Chinese search, Bases/Canvas, instruction-only plugin safety, and optional Obsidian integration.
- [ ] Add public Agent instructions that accurately explain canonical `wiki/`, rebuildable `.mini-wiki/`, evidence requirements, and non-executable plugin text.

### Step 5: Run the focused contract test

Run:

```bash
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: PASS for package, config, boundary, and foundation assertions.

### Step 6: Commit the foundation

```bash
git add .gitignore package.json pnpm-lock.yaml tests/test_site_contract.py site/.silen site/public/logo.svg
git commit -m "feat: establish Silen site foundation"
```

---

## Task 2: Build the Chinese-first bilingual product and documentation surface

**Files:**

- Create: `site/index.mdx`
- Create: `site/guide/index.mdx`
- Create: `site/knowledge-network/index.mdx`
- Create: `site/features/index.mdx`
- Create: `site/security/index.mdx`
- Create: `site/reference/index.mdx`
- Create: `site/en/index.mdx`
- Create: `site/en/guide/index.mdx`
- Create: `site/en/knowledge-network/index.mdx`
- Create: `site/en/features/index.mdx`
- Create: `site/en/security/index.mdx`
- Create: `site/en/reference/index.mdx`
- Modify: `tests/test_site_contract.py`

### Step 1: Extend tests for the complete route and content contract

- [ ] Require all six Chinese routes and all six mirrored English routes.
- [ ] Require each document to have a unique title, description, and navigable internal links.
- [ ] Require the Chinese and English homepages to contain the exact install command, guide action, repository action, current version, semantic knowledge graph, and links to AI-readable artifacts.
- [ ] Require security pages to state the instruction-only plugin and optional-Obsidian boundaries.
- [ ] Require reference pages to include the v3.3.0 command surface without invented flags.

Run:

```bash
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: FAIL because the route documents do not exist.

### Step 2: Create the Chinese homepage

- [ ] Build the hero with Mini-Wiki positioning, version marker, copyable install command, primary guide action, secondary GitHub action, and semantic project/domain/module/source/symbol graph.
- [ ] Add the deterministic-build proof strip and the `init → build → Agent enriches → build → check --strict → search` evidence chain.
- [ ] Explain the two-reader model for maintainers and AI Agents.
- [ ] Add the knowledge/state safety boundary and public AI artifact links.
- [ ] End with the install action and v3.3.0 release link.

### Step 3: Create the five Chinese documentation routes

- [ ] `guide/`: installation, five-minute workflow, Agent enrichment loop, validation, and next steps.
- [ ] `knowledge-network/`: stable IDs and project → domain → module → source → symbol relationships with source traceability.
- [ ] `features/`: Properties, local CJK-aware search, four Bases, three deterministic Canvas views, and managed Markdown.
- [ ] `security/`: canonical/state boundaries, instruction-only plugin model, transaction/recovery behavior, scanning boundaries, and optional Obsidian behavior.
- [ ] `reference/`: verified CLI commands, directory layout, managed markers, configuration switches, and exit/validation expectations.

### Step 4: Create the complete English route mirror

- [ ] Translate meaning and product hierarchy rather than mechanically transliterating headings.
- [ ] Preserve identical command lines, version facts, safety constraints, and route relationships.
- [ ] Ensure locale switching can remain on the equivalent route.

### Step 5: Build and repair all link/content failures

Run:

```bash
corepack pnpm site:build
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: Silen production build succeeds with no broken links and all route-contract tests pass.

### Step 6: Commit the public content

```bash
git add site/index.mdx site/guide site/knowledge-network site/features site/security site/reference site/en tests/test_site_contract.py
git commit -m "feat: add bilingual Mini-Wiki product docs"
```

---

## Task 3: Add artifact gates, Pages deployment, and repository entry points

**Files:**

- Create: `scripts/check-silen-site.mjs`
- Create: `.github/workflows/pages.yml`
- Modify: `package.json`
- Modify: `tests/test_site_contract.py`
- Modify: `README.md`
- Modify: `README.zh.md`

### Step 1: Write failing deployment and artifact assertions

- [ ] Require a Pages workflow triggered by `main` and `workflow_dispatch` with concurrency cancellation.
- [ ] Require only `contents: read`, `pages: write`, and `id-token: write` permissions.
- [ ] Require checkout v6, setup-node v6 at 22.12.0, pnpm 10.34.0, frozen install, `pnpm site:check`, Pages configuration, hidden-file artifact upload, and deployment.
- [ ] Require both READMEs to expose the live site next to the existing documentation entry links.

Run:

```bash
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: FAIL because the workflow, artifact script, and README entry links are absent.

### Step 2: Add the generated-artifact contract gate

- [ ] Check every Chinese and English HTML route.
- [ ] Check `llms.txt`, `llms-full.txt`, `ai-index.json`, `sitemap.xml`, `robots.txt`, route Markdown, and `.well-known/silen/manifest.json`.
- [ ] Recursively reject source maps, `sourceMappingURL`, user-local absolute paths, private note paths, `tmp/`, and `.mini-wiki/` references from deployable text artifacts.
- [ ] Fail with precise missing/leaking paths and return success only after a complete production build.

Run:

```bash
corepack pnpm site:build
corepack pnpm site:contract
```

Expected: PASS with a concise artifact-count summary.

### Step 3: Add the Pages workflow

- [ ] Pin the official Pages action majors and upload `site/.silen/dist` with hidden files included.
- [ ] Ensure build and deploy are separate jobs and the deploy environment publishes the Pages URL.
- [ ] Keep the workflow independent of Python CI while making `site:check` the sole deployment gate.

### Step 4: Add visible repository documentation links

- [ ] Add the Pages URL to the centered header navigation in `README.md` and `README.zh.md`.
- [ ] Keep existing Skill, changelog, version, and release links intact.

### Step 5: Run the complete site gate

Run:

```bash
corepack pnpm site:check
.venv/bin/python -m pytest tests/test_site_contract.py -q
```

Expected: build, audit, eval, artifact gate, and contract tests all pass.

### Step 6: Commit deployment support

```bash
git add .github/workflows/pages.yml scripts/check-silen-site.mjs package.json tests/test_site_contract.py README.md README.zh.md
git commit -m "ci: deploy Mini-Wiki site to GitHub Pages"
```

---

## Task 4: Verify locally, publish from main, update About, and prove the live site

**Files:**

- Verify: all tracked changes in this plan
- Preserve: `docs/wechat-publish-notes.md`
- Preserve: `tmp/`

### Step 1: Run all repository gates

Run:

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm site:check
.venv/bin/python -m pytest -q
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
.venv/bin/mypy scripts --ignore-missing-imports
git diff --check
```

Expected: all JavaScript/site and Python gates pass with no whitespace errors.

### Step 2: Run local browser QA

- [ ] Start the production preview on an explicit free localhost port and verify the actual process/URL.
- [ ] Check desktop and mobile layouts for `/mini-wiki/`, a nested Chinese route, `/mini-wiki/en/`, and an English nested route.
- [ ] Verify light/dark appearance, local search, navigation, route-preserving language switch, keyboard focus, reduced-motion behavior, direct nested-route loading, 404 handling, and no horizontal overflow.
- [ ] Verify `llms.txt`, the Agent Contract, and the manifest directly over HTTP.

Expected: all visual and interaction checks pass without console or request errors.

### Step 3: Review the exact release diff and sync main

Run:

```bash
git status --short
git diff --stat origin/main...HEAD
git fetch origin
git rebase origin/main
git push origin main
```

Expected: only the approved design, plan, site, tests, README, package, and Pages workflow are pushed; user-owned untracked files remain untracked.

### Step 4: Switch Pages to GitHub Actions and wait for deployment

- [ ] Confirm `.github/workflows/pages.yml` exists on remote `main` before changing the Pages build type.
- [ ] Change the Pages source from legacy `main:/docs` to GitHub Actions.
- [ ] Wait for both Python CI and Pages runs for the pushed commit to complete successfully.
- [ ] If deployment fails, diagnose and repair the workflow or site; leave the previous live site recoverable until the Actions path is verified.

### Step 5: Update the GitHub About Homepage field

Run:

```bash
gh repo edit trsoliu/mini-wiki --homepage https://trsoliu.github.io/mini-wiki/
```

Expected: repository metadata reports `homepageUrl` as the verified Pages URL.

### Step 6: Prove the live release surface

- [ ] Require HTTP 200 for the root homepage, one nested Chinese route, the English homepage, one nested English route, `llms.txt`, `ai-index.json`, and `.well-known/silen/manifest.json`.
- [ ] Confirm the live HTML identifies Mini-Wiki 3.3.0 and contains the primary install action.
- [ ] Confirm GitHub Pages reports workflow build type, the deployment commit matches local `HEAD`, and About links to the same canonical URL.
- [ ] Record exact CI run URLs and the live Pages URL in the handoff.

Expected: the Silen site is reachable, all public artifacts are present, GitHub About exposes the entry, and the local tree contains only the preserved user-owned untracked files.
