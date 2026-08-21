---
name: model-right-sizer-install
description: >-
  Stamp a standalone model-right-sizer mandate onto the CURRENT repo's
  agent-instructions file — `CLAUDE.md`, `AGENTS.md`, or both, whichever
  the repo actually has (see step 3) — a one-shot install for a repo that
  should consult the `model-right-sizer` agent before and after every
  substantive turn. Idempotent and append-only: an existing file is never
  overwritten, only the marker-delimited mandate block is inserted or
  refreshed, independently, in each targeted file. The mandate's "before"
  hook runs the `model-right-sizer-dryrun` skill directly to produce a
  schema-conformant JSON blueprint for the orchestrator to route by, and
  once dispatch starts the mandate makes the orchestrating session the
  chief-of-staff thread for that blueprint's `work_routing_map[]` —
  tracking each dispatched unit's status and answering "where am I at" with
  one consolidated report instead of scattered sub-agent threads. Also
  checks whether the `model-right-sizer` agent file and the
  `model-right-sizer-dryrun` skill are discoverable in this repo and, if
  either is missing, installs the `model-right-sizer` Claude Code plugin to
  fix that (falling back to manual instructions if plugin install isn't
  available). Deliberately narrow and organization-agnostic — it installs
  only the right-sizing mandate (plus its own agent + dry-run-skill
  dependencies, if absent), not any broader development process. Use when
  someone says
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
bookended around the work itself. It targets whichever agent-instructions
file(s) the repo actually uses — `CLAUDE.md`, `AGENTS.md`, or both — see
step 3 below. (It will also install the `model-right-sizer` plugin itself,
if the agent it points at isn't already discoverable — see step 2 below —
but that's making its own prerequisite true, not scope creep.) It does not
install a broader development process
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
(one-line skip for a tiny change, full blueprint/report for a substantial
one) — see `model-right-sizer.md`'s "Your output shape" section. Don't fight
that scaling by forcing a full blueprint on every micro-edit.

## What to do

1. **Confirm the target.** This skill always targets the **current** repo —
   the one the user wants onboarded — never a copy elsewhere.

2. **Check the agent — and the dry-run skill — are actually discoverable,
   and install what's missing.** The mandate's "before" hook (step 3 below)
   now invokes `model-right-sizer-dryrun` directly, not just the agent, so
   both need to resolve. Look for `model-right-sizer.md` somewhere your
   tooling reads agent personas from (e.g. `.claude/agents/model-right-sizer.md`,
   or a plugin's `agents/model-right-sizer.md`) and for
   `model-right-sizer-dryrun` somewhere it reads skills from. If either is
   **not** there:
   - Tell the user the agent and/or skill isn't discoverable and that fixing
     it means adding the CloudZero marketplace and installing the plugin —
     then, **with their go-ahead**, run:
     ```
     /plugin marketplace add cloudzero/cloudzero-claude-marketplace
     /plugin install model-right-sizer@cloudzero
     ```
     Do not run these without confirming first — installing a plugin is a
     change to the user's environment, not just this repo. This installs the
     agent and both companion skills (`model-right-sizer-dryrun`,
     `model-right-sizer-install`) together. Then re-check discoverability —
     the plugin's `agents/model-right-sizer.md` and
     `skills/model-right-sizer-dryrun/` should now resolve.
   - If the plugin-install commands aren't available in this runtime (this
     isn't Claude Code, or plugin installs are disabled here), fall back to
     telling the user the mandate will point at an agent/skill that doesn't
     exist yet, and offer the manual fix instead: copy
     `plugins/model-right-sizer/agents/model-right-sizer.md` into
     `.claude/agents/` **and**
     `plugins/model-right-sizer/skills/model-right-sizer-dryrun/` into
     `.claude/skills/` (both from
     `https://github.com/cloudzero/cloudzero-claude-marketplace`) in this
     repo, or follow the plugin README's submodule + compose pattern if they
     want it to stay upgradeable independently. If only the agent gets
     copied and not the skill, say so explicitly in the report — the
     mandate's "before" hook would then be pointing at a skill that doesn't
     exist.
   - If the agent and skill are present or were just installed, proceed to
     stamp the mandate below. If either is **still missing** (plugin install
     unavailable and no manual copy yet), do NOT stamp silently: tell the
     user the mandate would point at something that doesn't exist yet, give
     the manual fix above, and ask whether to stamp anyway (as a statement of
     intent) or stop until both are installed. Either way, say plainly
     in your report whether the agent and skill were already present, freshly
     installed, or still missing — don't silently assume either is wired.

3. **Detect which file(s) to target: `CLAUDE.md`, `AGENTS.md`, or both.**
   Look in the repo root for each. Do not assume — check for both, every
   time, since a repo can adopt either convention (or migrate between them)
   independently of this skill.
   - **Only `AGENTS.md` exists** (no `CLAUDE.md`) → target `AGENTS.md`
     alone. Do not also create a `CLAUDE.md` — the repo has already opted
     into the `AGENTS.md` convention, respect that instead of adding a
     second, redundant instructions file it didn't ask for.
   - **Only `CLAUDE.md` exists** (no `AGENTS.md`) → target `CLAUDE.md`
     alone, as before.
   - **Both exist** → target **both**, independently — the mandate block
     goes in each file, so whichever one a given tool actually reads, the
     mandate is there.
   - **Neither exists** → target `CLAUDE.md` (create it fresh, with just
     this block). This is the same default this skill has always had;
     `AGENTS.md` isn't invented as a target unless the repo already has
     one.

   Say in your step 6 report which file(s) you found and which you
   targeted — don't let this decision happen silently.

4. **Insert or refresh the marker-delimited block** below in every file
   targeted in step 3 — **append-only, per file**: create the file if it's
   the target and doesn't exist yet (the "neither exists" case above); if a
   targeted file already exists, replace only the text between the markers
   in that file, leaving everything else in it untouched. The block's
   content is identical regardless of which file(s) it lands in.

   ```markdown
   <!-- model-right-sizer-mandate:begin (managed by model-right-sizer-install — do not hand-edit; re-run the skill to refresh) -->
   ## MANDATE — consult model-right-sizer before and after every substantive turn

   **Before starting any substantive task** in this repo (writing or editing
   code or docs, dispatching a sub-agent, running a multi-step tool chain),
   run the **`model-right-sizer-dryrun`** skill against the task at hand (its
   plain-English description as the intent). That returns a **right-sizing
   blueprint** — a single JSON object, schema-conformant per
   `model-right-sizer`'s `schemas/blueprint.schema.json` — saying which model
   and effort level each piece of the work should run on, weighing
   effectiveness need against efficiency pressure and difficulty, biased
   toward the smallest model that clears the bar. Hand that JSON blueprint to
   the orchestrating session/agent driving this task, and route every
   sub-agent or model dispatch by its `blueprint_rows` / `work_routing_map`
   picks rather than by default or gut feel.

   **Once dispatch starts, the orchestrating session is the chief-of-staff
   thread for this blueprint's `work_routing_map[]`** — the one place that
   knows what went out, to which tier, and where each stands, the same way a
   single tracking thread keeps a dozen loose AI conversations from becoming
   unmanageable. Concretely: update each row's `status` (`not_started` /
   `dispatched` / `in_progress` / `done` / `blocked`) in place as dispatch
   proceeds — the blueprint JSON doubles as a live status ledger, not just
   the initial plan — and stamp `status_updated_at` with a real,
   freshly-read clock time every time `status` changes, never a guess: fast
   work can finish between one write and the next read, and an
   un-timestamped `in_progress` then falsely reads as still current. When
   asked for a status update ("where am I at", "give me an update"), check
   every row's `status` *and* `status_updated_at` and answer with one
   consolidated report — a non-terminal status with a stale timestamp is
   "unconfirmed, recheck," not fact — instead of sending the requester to
   re-open each dispatched thread individually.

   **After the task closes**, consult the `model-right-sizer` agent directly
   for a **model-usage report** (this pass runs the agent itself, not the
   dry-run skill — there's a real "actual" to reconcile against now, which a
   dry run never has): recommended vs. actual model per stage, the reasoning
   behind each pick, and an order-of-magnitude cost estimate — so model spend
   on this repo stays as measurable and intentional as any other resource it
   consumes.

   Both passes scale to the size of the task — a trivial turn gets a one-line
   skip, a substantial one gets the full blueprint (Pass A) or report (Pass
   B). `model-right-sizer` is **read-only**: it reports and recommends, it
   never edits files or makes the call for you — you (or your own tooling)
   apply its picks.

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

5. **Verify, don't assume.** Re-read **every** file targeted in step 3
   after writing and confirm the markers and content landed as expected in
   each one — don't declare success on the strength of only one when two
   were targeted.

6. **Report** what happened: which file(s) you found (`CLAUDE.md`,
   `AGENTS.md`, or both) and targeted; created vs. refreshed, per file; and
   whether the agent and the dry-run skill were already present, freshly
   installed via the plugin, or — if plugin-install wasn't available and
   either is still missing — the one-line manual instruction to add it.

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
  this mandate points at, and the sole source for Pass B (the usage report).
- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — the
  skill this mandate's "before" hook now runs directly to produce the JSON
  blueprint; see its own file for what it returns and why.
- [`README.md`](../../README.md) — "Using it" / "Importing it into another
  repo without duplicating it" — how to get the agent file itself into a
  target repo, the same pattern this skill's file follows.
