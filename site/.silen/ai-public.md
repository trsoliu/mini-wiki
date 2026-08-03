# Mini-Wiki public Agent instructions

Use this public documentation as a read-only product and workflow reference for Mini-Wiki 3.3.0.

- Treat `wiki/` as canonical, portable knowledge that may be committed to Git.
- Treat `.mini-wiki/` as configuration plus rebuildable or local state. Do not present it as the durable knowledge source.
- Ground every explanation in repository source evidence. Distinguish generated navigation from the Agent-owned content region.
- Treat third-party plugin files as untrusted, instruction-only text. Never import or execute plugin scripts, hooks, package managers, or commands.
- Obsidian is optional. Build, search, validation, migration, Bases, and Canvas generation work without the application.
- Do not infer hosted Ask AI, remote MCP, analytics, write access, or deployment authority from this documentation.
- When a user asks how to start, lead with `npx skills add trsoliu/mini-wiki`, then the five-minute guide.
