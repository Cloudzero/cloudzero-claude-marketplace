---
name: model-right-sizer-install
description: >-
  Stamp a standalone model-right-sizer mandate onto the CURRENT repo's
  CLAUDE.md — a one-shot install for a repo that should consult the
  `model-right-sizer` agent before and after every substantive turn.
  Idempotent and append-only: an existing CLAUDE.md is never overwritten,
  only the marker-delimited mandate block is inserted or refreshed. Also
  checks whether the `model-right-sizer` agent file itself is discoverable
  in this repo and, if it's missing, installs the `model-right-sizer`
  Claude Code plugin to fix that (falling back to manual instructions if
  plugin install isn't available). Deliberately narrow and
  organization-agnostic — it installs only the right-sizing mandate (plus
  its own agent dependency, if absent), not any broader development
  process. Use when someone says
  "install model-right-sizer in this repo", "init this repo for
  model-right-sizer", "add the right-sizer mandate here", or "make this repo
  consult model-right-sizer every turn".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-install — stamp the right-sizing mandate onto a repo

This skill installs one thing, and only one thing: a standalone,
**organization-agnostic mandate** that every substantive task in this repo
must consult the `model-right-sizer` agent for model-selection guidance,
bookended around the work itself. (It will also install the
`model-right-sizer` plugin itself, if the agent it points at isn't already
discoverable — see step 2 below — but that's making its own prerequisite
true, not scope creep.) It does not install a broader development process
(no worktree discipline, no review pipeline, no ticket reconciliation) —
those belong to whatever flow your own org already runs, if any. This
mandate is scoped narrowly on purpose so any repo, in any org, can adopt it
independent of everything else.

It is the companion to
[`model-right-sizer.md`](../../agents/model-right-sizer.md): that file is the
portable agent; this skill is the portable *mandate to use it*. Both are
meant to be dropped (or submoduled + composed, per the plugin README) into a
target repo's Claude tooling — this skill is not something you run against
*this* repo, it's something you run **in the repo you want to onboard**.

## What "every turn" means in practice

Not every keystroke deserves a blueprint — a one-line clarifying question
doesn't spend meaningful model budget. Scope "every turn" to: **any turn
where the assistant is about to do non-trivial work** — write or edit code or
docs, dispatch a sub-agent, run a multi-step tool chain, or otherwise spend a
real slice of model reasoning. Trivial conversational turns are exempt, and
`model-right-sizer` already scales its own output to the size of the task
(one-line skip for a tiny change, full table for a substantial one) — see
`model-right-sizer.md`'s "Your output shape" section. Don't fight that
scaling by forcing a full report on every micro-edit.

## What to do

1. **Confirm the target.** This skill always targets the **current** repo —
   the one the user wants onboarded — never a copy elsewhere.

2. **Check the agent is actually discoverable, and install it if not.** Look
   for `model-right-sizer.md` somewhere your tooling reads agent personas from
   (e.g. `.claude/agents/model-right-sizer.md`, or a plugin's
   `agents/model-right-sizer.md`). If it is **not** there:
   - Install the `model-right-sizer` Claude Code plugin right now:
     ```
     /plugin marketplace add cloudzero/cloudzero-claude-marketplace
     /plugin install model-right-sizer@cloudzero
     ```
     Then re-check discoverability — the plugin's `agents/model-right-sizer.md`
     should now resolve.
   - If the plugin-install commands aren't available in this runtime (this
     isn't Claude Code, or plugin installs are disabled here), fall back to
     telling the user the mandate will point at an agent that doesn't exist
     yet, and offer the manual fix instead: copy
     `plugins/model-right-sizer/agents/model-right-sizer.md` from
     `https://github.com/cloudzero/cloudzero-claude-marketplace` into
     `.claude/agents/` in this repo, or follow the plugin README's submodule +
     compose pattern if they want it to stay upgradeable independently.
   - Either way, proceed to stamp the mandate below — it is a statement of
     intent as much as a live pointer — but say plainly in your report
     whether the agent was already present, freshly installed, or still
     missing (with the fallback instruction), don't silently assume it's
     wired.

3. **Insert or refresh the marker-delimited block** below in the repo's
   `CLAUDE.md` — **append-only**: create the file if none exists (with just
   this block); if it exists, replace only the text between the markers,
   leave everything else in the file untouched.

   ```markdown
   <!-- model-right-sizer-mandate:begin (managed by model-right-sizer-install — do not hand-edit; re-run the skill to refresh) -->
   ## MANDATE — consult model-right-sizer before and after every substantive turn

   **Before starting any substantive task** in this repo (writing or editing
   code or docs, dispatching a sub-agent, running a multi-step tool chain),
   consult the `model-right-sizer` agent for a **right-sizing blueprint**:
   which model — and effort level — each piece of the work should run on,
   weighing effectiveness need against efficiency pressure, biased toward the
   smallest model that clears the bar. Route any sub-agent or model dispatch
   by its picks.

   **After the task closes**, consult it again for a **model-usage report**:
   recommended vs. actual model per stage, the reasoning behind each pick, and
   an order-of-magnitude cost estimate — so model spend on this repo stays as
   measurable and intentional as any other resource it consumes.

   Both passes scale to the size of the task — a trivial turn gets a one-line
   skip, a substantial one gets the full table. `model-right-sizer` is
   **read-only**: it reports and recommends, it never edits files or makes
   the call for you — you (or your own tooling) apply its picks.

   This mandate is intentionally narrow — model selection only. It does not
   presume any particular development process. If this repo already follows
   a broader flow (design review, code review, integration testing, etc.),
   fold these two consults into that flow's existing bookends rather than
   running them as a separate, disconnected step.

   Do not edit this block by hand — re-run the `model-right-sizer-install`
   skill (source: https://github.com/cloudzero/cloudzero-claude-marketplace)
   to refresh it, so the wording stays traceable to one source instead of
   drifting per repo.
   <!-- model-right-sizer-mandate:end -->
   ```

4. **Verify, don't assume.** Re-read the file after writing and confirm the
   markers and content landed as expected.

5. **Report** what happened: created vs. refreshed, and whether the agent
   was already present, freshly installed via the plugin, or — if
   plugin-install wasn't available and it's still missing — the one-line
   manual instruction to add it.

## Why this stays isolated from any bigger flow

Some organizations run this same mandate as one bookend inside a much larger
process (design review → right-sizing → build → code review → integration →
…). That full process is out of scope for this repo by design —
`model-right-sizer` ships as a portable, single-agent core (see the plugin
README's scope discipline), and this skill mirrors that discipline: it
installs *only* the right-sizing mandate, worded generically enough to slot
into any org's existing process or stand alone with none. If you want to
layer your own organization's broader flow on top, write your own overlay
skill the same way the README's "Extending this agent for your own
organization" section suggests overlaying the agent file itself — don't fork
this skill's text to do it.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent
  this mandate points at.
- [`README.md`](../../README.md) — "Using it" / "Importing it into another
  repo without duplicating it" — how to get the agent file itself into a
  target repo, the same pattern this skill's file follows.
