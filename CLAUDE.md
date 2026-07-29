# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Taste Skill is a library of **Agent Skills** (portable `SKILL.md` instruction files) that steer AI coding agents (Claude Code, Codex, Cursor, GitHub Copilot) away from generic "AI slop" frontends and toward deliberate, art-directed design output. There is no application code, build step, or test suite here — the deliverable is markdown instruction files plus a small set of one-off Node scripts for processing README/asset images.

Distributed via the [`npx skills add`](https://github.com/vercel-labs/agent-skills) CLI, which scans `skills/`, and also packaged as an installable Claude Code plugin via `.claude-plugin/`.

## Repository structure

- `skills/<folder>/SKILL.md` — one skill per folder. This is the entire product.
- `skills/llms.txt` — one-line summary of every skill, used as a discovery index.
- `skill.sh` — local registry mapping a skill's shorthand name to its `SKILL.md` path (`source ./skill.sh <name>`).
- `.claude-plugin/plugin.json` / `marketplace.json` — makes this repo installable as a Claude Code plugin.
- `.github/copilot-instructions.md` — auto-read by GitHub Copilot; a condensed version of the anti-slop rules below.
- `research/` — background research that justifies specific rules in the skills (e.g. `research/laziness/` documents why LLMs truncate output, which is what `output-skill` exists to counter). Each topic is a subfolder with its own README.
- `scripts/*.mjs` — ad hoc Node/`sharp` scripts the maintainer runs locally to process README banner/button/sponsor images (several have hardcoded Windows `C:/Users/...` source paths). Not part of any build pipeline; not meant to run in CI or by contributors.
- `assets/`, `examples/` — images referenced by `README.md`.
- `CHANGELOG.md` — user-facing changelog for the skills themselves (not this repo's tooling).

There is no `package.json`, no linter, no test runner, and no CI workflow. "Development" in this repo means editing `SKILL.md` files and keeping the three places that list them in sync.

## Working with skills (the core task)

### Every `SKILL.md` has YAML frontmatter with exactly two fields

```yaml
---
name: <install-name>
description: <when an agent should use this skill, written for the agent to match against>
---
```

The **install name** (`name:` field) is what users pass to `--skill`, and is often *different from the folder name* (e.g. folder `skills/taste-skill/` → install name `design-taste-frontend`; folder `skills/gpt-tasteskill/` → install name `gpt-taste`). Never assume folder name == install name.

### Adding, renaming, or removing a skill requires updating four places

Missing any of these silently breaks discovery or installation:
1. The `skills/<folder>/SKILL.md` file itself.
2. `skill.sh` — add/update the `SKILLS[...]=` entry.
3. `skills/llms.txt` — add/update the one-line summary (`install-name: description`).
4. `README.md` — the skill table (`## Skills` or `### Image generation skills`), including the "Which one should I use?" section if relevant.

If the change is user-visible (new skill, behavior change, renamed install name), also add an entry to `CHANGELOG.md` under `[Unreleased]` or a new version heading, following the existing style (grouped by `### Repo`, `### What's new`, etc., SemVer-ish: experimental pre-releases iterate freely, stable releases lock the API).

### Two skill families

- **Implementation skills** (`taste-skill`, `taste-skill-v1`, `gpt-tasteskill`, `image-to-code-skill`, `redesign-skill`, `soft-skill`, `output-skill`, `minimalist-skill`, `brutalist-skill`, `stitch-skill`) output code/instructions for building UI.
- **Image-generation skills** (`imagegen-frontend-web`, `imagegen-frontend-mobile`, `brandkit`) output reference images only, no code — for pairing with an image generator before handing frames to a coding agent.

### `taste-skill` (install name `design-taste-frontend`) is the default/flagship skill and the most heavily maintained file

It is currently **v2 (experimental)**; `taste-skill-v1` is kept only for exact-behavior backward compatibility and should not receive new rules. When editing `taste-skill/SKILL.md`, preserve its internal conventions:

- **Numbered sections** (`## 0. BRIEF INFERENCE`, `## 1. THE THREE DIALS`, …) — new rules belong under the most specific existing section, not bolted onto the end.
- **Three named dials** — `DESIGN_VARIANCE`, `MOTION_INTENSITY`, `VISUAL_DENSITY` (1–10 scales). These exact variable names are referenced throughout the doc; never invent aliases (e.g. `LAYOUT_VARIANCE`).
- **"Mandatory" hard rules vs. contextual guidance** — rules marked `(mandatory)` are meant to be treated as pre-flight-check failures, not suggestions. Most other rules are explicitly *contextual* ("None of this fires automatically... first read the brief, then pull only what fits") and should state their override condition, not just their default.
- **Canonical code skeletons** (Sticky-Stack, Horizontal-Pan, Scroll-Reveal-Stagger in §5) are reference implementations agents copy verbatim — keep them runnable TSX, not pseudocode, and keep the `"use client"` / `useReducedMotion` / GSAP `ScrollTrigger` cleanup patterns intact if you touch them.
- **The em-dash ban (§9.G)** is treated as the single most-violated rule historically — do not reintroduce em-dashes into example copy anywhere in this file, including in this file's own prose examples.

### Sibling skills intentionally diverge from `taste-skill`

`gpt-tasteskill` (stricter/GPT-oriented), `brutalist-skill`, `minimalist-skill`, `soft-skill` (aesthetic-specific rule sets) and `redesign-skill` (audit-existing-project workflow) are shorter, self-contained variants — do not try to unify them with `taste-skill`'s structure or dial system unless a change explicitly asks for that.

## Commands

No build, lint, or test commands exist. The only executable code is the maintainer-only image scripts:

```bash
node scripts/build-emil-sponsor-row.mjs
node scripts/convert-readme-assets-webp.mjs
node scripts/process-readme-buttons.mjs
node scripts/process-sponsor-badge.mjs
```

These require the `sharp` package (not declared anywhere — install ad hoc with `npm install sharp` if running them) and several reference hardcoded local `C:/Users/...` source paths that only exist on the maintainer's machine. Don't expect them to run in a fresh environment.

To browse a skill locally:

```bash
source ./skill.sh <install-name>   # prints the SKILL.md path, e.g. ./skill.sh gpt-taste
```
