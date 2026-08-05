---
name: model-right-sizer-install
description: >-
  Stamp a standalone model-right-sizer mandate onto the CURRENT repo's
  CLAUDE.md — a one-shot install for a repo that should consult the
  `model-right-sizer` agent before and after every substantive turn — and
  seed the machine-wide learning loop that gives the agent a memory:
  the `model-right-sizer-learned` skill plus its calibration ledger in the
  user-level skills directory, and a matching mandate block in the
  user-level CLAUDE.md. Idempotent and append-only everywhere: an existing
  CLAUDE.md is never overwritten (only the marker-delimited block is
  inserted or refreshed), and an existing learned skill keeps its
  accumulated learnings (only its protected regions are refreshed). Also
  checks whether the `model-right-sizer` agent file itself is discoverable
  in this repo and, if it's missing, installs the `model-right-sizer`
  Claude Code plugin to fix that (falling back to manual instructions if
  plugin install isn't available), and optionally wires SkillOpt-Sleep to
  distill the ledger nightly. Deliberately narrow and
  organization-agnostic — it installs only the right-sizing mandate and its
  learning loop, not any broader development process. Use when someone says
  "install model-right-sizer in this repo", "init this repo for
  model-right-sizer", "add the right-sizer mandate here", or "make this repo
  consult model-right-sizer every turn".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.2.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-install — stamp the right-sizing mandate onto a repo

This skill installs one capability, and only one: a standalone,
**organization-agnostic mandate** that every substantive task in this repo
must consult the `model-right-sizer` agent for model-selection guidance,
bookended around the work itself — **plus the learning loop that keeps those
consults from starting from zero every time.** (It will also install the
`model-right-sizer` plugin itself, if the agent it points at isn't already
discoverable — see step 2 below — but that's making its own prerequisite
true, not scope creep.) It does not install a broader development process
(no worktree discipline, no review pipeline, no ticket reconciliation) —
those belong to whatever flow your own org already runs, if any. This
mandate is scoped narrowly on purpose so any repo, in any org, can adopt it
independent of everything else.

## The two halves: a repo mandate and a machine-wide memory

The install has a **repo-scoped** half and a **machine-scoped** half, and the
split is deliberate:

- **Repo-scoped** — the mandate block in *this* repo's `CLAUDE.md`: consult the
  agent before and after substantive work here.
- **Machine-scoped** — the `model-right-sizer-learned` skill, its
  `ledger.jsonl`, and a mandate block in the user-level `CLAUDE.md`. These live
  **outside every repo, on purpose**. The agent's whole value is pricing the
  cost of error, and that price is only knowable from what past picks actually
  cost — evidence that would be worthless if it were siloed per repo. A
  calibration measured while working on one codebase should sharpen the pick
  made on the next one, so it is stored once, where every session can read it.

What makes that safe is the same discipline the agent applies to its own
handoffs: a ledger row records a **task shape** (`stage_kind`, `loop_class`, the
three signals, recommended-vs-actual, rework cycles), never task content — no
repo names, paths, ticket ids, code, or customer data. Repo-agnostic is not a
nicety here; it is the precondition for storing the thing centrally at all.

**Anything outside this repo gets explicit confirmation before it is written.**
That is the same bar this skill already applies to installing a plugin: changing
the user's environment is a different act from editing the repo they pointed you
at, and it is never silent.

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
   - Tell the user the agent isn't discoverable and that fixing it means
     adding the CloudZero marketplace and installing the plugin — then, **with
     their go-ahead**, run:
     ```
     /plugin marketplace add cloudzero/cloudzero-claude-marketplace
     /plugin install model-right-sizer@cloudzero
     ```
     Do not run these without confirming first — installing a plugin is a
     change to the user's environment, not just this repo. Then re-check
     discoverability — the plugin's `agents/model-right-sizer.md` should now
     resolve.
   - If the plugin-install commands aren't available in this runtime (this
     isn't Claude Code, or plugin installs are disabled here), fall back to
     telling the user the mandate will point at an agent that doesn't exist
     yet, and offer the manual fix instead: copy
     `plugins/model-right-sizer/agents/model-right-sizer.md` from
     `https://github.com/cloudzero/cloudzero-claude-marketplace` into
     `.claude/agents/` in this repo, or follow the plugin README's submodule +
     compose pattern if they want it to stay upgradeable independently.
   - If the agent is present or was just installed, proceed to stamp the
     mandate below. If it is **still missing** (plugin install unavailable
     and no manual copy yet), do NOT stamp silently: tell the user the
     mandate would point at an agent that doesn't exist yet, give the
     manual fix above, and ask whether to stamp anyway (as a statement of
     intent) or stop until the agent is installed. Either way, say plainly
     in your report whether the agent was already present, freshly
     installed, or still missing — don't silently assume it's wired.

3. **Seed the machine-wide learned skill — never clobber what it has already
   learned.** Target `~/.claude/skills/model-right-sizer-learned/` (the
   user-level skill directory, so every session in every repo discovers it;
   substitute the equivalent path if your runtime keeps personal skills
   elsewhere). Confirm with the user before writing outside the repo, then:

   - **`SKILL.md` absent** → author it from this plugin's
     [`templates/learned-skill.seed.md`](../../templates/learned-skill.seed.md),
     verbatim.
   - **`SKILL.md` present** → refresh **only** the YAML frontmatter and the two
     protected regions (`<!-- SLOW_UPDATE_START -->…<!-- SLOW_UPDATE_END -->`
     and `<!-- APPENDIX_START -->…<!-- APPENDIX_END -->`) from the template, and
     leave everything between them exactly as it is. That middle section is
     accumulated calibration — overwriting it on a re-run would silently
     destroy the only artifact in this system that can't be regenerated. The
     frontmatter and the protected regions are the opposite case: they're
     plugin-owned metadata and contract, so they *should* track the template,
     or an install made a year ago keeps a stale `description` and Claude Code
     surfaces the skill by wording the plugin has since improved.
     If a protected marker pair is missing or unbalanced in the existing
     file, do **not** guess where it should go: report it and leave the file
     untouched.
   - **`ledger.jsonl` absent** → create it empty. Present → leave it alone,
     always. It is append-only; this skill never rewrites it.
   - **`eval/routing-tasks.jsonl` absent** → copy this plugin's
     [`eval/routing-tasks.jsonl`](../../eval/routing-tasks.jsonl). Present →
     merge by `id`, adding only rows whose ids aren't there yet, so a user's
     own added tasks survive.

   Idempotency is the property most worth checking here: running this skill
   twice in a row must leave the accumulated learnings byte-identical.

4. **Stamp the machine-wide learning-loop mandate.** With the user's
   confirmation, insert or refresh this marker-delimited block in the
   user-level `CLAUDE.md` (`~/.claude/CLAUDE.md` in Claude Code) — append-only,
   creating the file if it doesn't exist, replacing only the text between the
   markers if it does. This is the half that makes the loop actually close:
   without it, sessions *read* accumulated learnings but never contribute to
   them, and the ledger stays empty forever.

   ```markdown
   <!-- model-right-sizer-learning-loop:begin (managed by model-right-sizer-install — do not hand-edit; re-run the skill to refresh) -->
   ## MANDATE — feed the model-right-sizer learning loop

   Calibration for the `model-right-sizer` agent lives machine-wide, not per
   repo: the `model-right-sizer-learned` skill and its `ledger.jsonl`, in the
   user-level skills directory. It applies in **every** repo.

   **Before** a right-sizing blueprint (Pass A): read the learned skill and the
   ledger rows matching the stage you're scoring, and say out loud what the
   evidence changed — including "nothing" and including "no ledger yet".

   **After** the work closes (Pass B): append one calibration row per stage that
   spent real tokens, via the `model-right-sizer-calibrate` skill. The agent is
   read-only and emits the rows; persisting them is the session's job. A run
   that closes without appending is a run whose evidence was thrown away.

   **Rows record task SHAPES, never task content** — no repo names, file paths,
   ticket ids, code snippets, or customer data. They are read in every repo on
   this machine, so anything repo-specific in them is both a leak and a wrong
   signal. `model-right-sizer-calibrate` enforces this; don't hand-append around
   it.

   Do not edit this block by hand — re-run the `model-right-sizer-install`
   skill (source: https://github.com/cloudzero/cloudzero-claude-marketplace)
   to refresh it.
   <!-- model-right-sizer-learning-loop:end -->
   ```

5. **Insert or refresh the marker-delimited block** below in the repo's
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

   **Both passes read and feed the machine-wide learning loop.** The blueprint
   consults the `model-right-sizer-learned` skill and its calibration ledger
   before finalizing picks; the usage report emits calibration rows that
   `model-right-sizer-calibrate` appends to that ledger. The loop is defined
   once, machine-wide, in the user-level `CLAUDE.md` — this repo just honors
   it. Rows carry task shapes only, never anything specific to this repo.

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

6. **Offer to wire SkillOpt-Sleep — optional, and never run unasked.** The
   learning loop works with **zero dependencies**: the ledger accumulates
   evidence, `model-right-sizer-calibrate summary` aggregates it, and the agent
   reads both. [SkillOpt](https://github.com/microsoft/skillopt)'s `sleep`
   companion is the *optional* automation that distills that evidence into the
   learned skill's prose nightly, behind a held-out validation gate. Treat it
   as an enhancement, never a prerequisite — and say so, so nobody concludes
   the loop is broken without it.

   - **`skillopt-sleep` not on PATH** → print `pip install skillopt` and the
     config below, and **install nothing**. Adding a Python package to the
     user's machine is theirs to decide.
   - **On PATH** → offer, and only on a yes, write
     `~/.skillopt-sleep/config.json` from this plugin's
     [`templates/skillopt-sleep.config.json`](../../templates/skillopt-sleep.config.json).
     The load-bearing key is `target_skill_path`, which must point at the
     learned skill seeded in step 3; `transcript_source: "claude"` lets it
     harvest Claude Code transcripts directly. If a config already exists,
     show the diff and let the user decide — don't overwrite another tool's
     settings.
   - **Scheduling** (`skillopt-sleep schedule`, which installs a cron/Task
     Scheduler entry) is a separate yes/no. Recommend starting with
     `skillopt-sleep dry-run` — it harvests, mines, and replays but stages
     nothing — so the user sees what it would do before anything is scheduled.
   - **Say the privacy part out loud, don't bury it.** Sleep reads local
     session transcripts and writes an `evidence.jsonl` under its staging tree.
     `redact_secrets` defaults on; `"evidence_log": false` disables the log
     entirely. A user should know their transcripts are being read *before*
     they agree to a nightly job, not discover it later.
   - **Nothing is ever auto-adopted.** Sleep *stages* a proposal; applying it
     goes through `model-right-sizer-calibrate review`, with a human looking at
     the diff.
   - Config key names track the installed SkillOpt version. If a key is
     rejected, check `skillopt-sleep`'s own docs rather than guessing — and
     report the mismatch instead of silently writing a config that won't load.

7. **Verify, don't assume.** Re-read every file you wrote and confirm the
   markers and content landed as expected — both `CLAUDE.md` blocks, the
   learned skill's protected regions, and (if it already existed) that the
   accumulated learnings between those regions are unchanged.

8. **Report** what happened, plainly and per artifact — no silent assumptions:
   - the repo mandate block: created vs. refreshed;
   - the agent: already present, freshly installed via the plugin, or still
     missing (with the one-line manual instruction to add it);
   - the learned skill: seeded fresh, protected regions refreshed with
     learnings preserved, or skipped because the user declined;
   - the user-level mandate block: created, refreshed, or declined;
   - SkillOpt-Sleep: configured, scheduled, documented-only, or declined.

   If the user declined any machine-scoped write, say what that costs — the
   ledger won't be fed, so the agent keeps reasoning from first principles —
   rather than reporting a clean success.

## Why this stays isolated from any bigger flow

Some organizations run this same mandate as one bookend inside a much larger
process (design review → right-sizing → build → code review → integration →
…). That full process is out of scope for this repo by design —
`model-right-sizer` ships as a portable, single-agent core (see the plugin
README's scope discipline), and this skill mirrors that discipline: it
installs *only* the right-sizing mandate and the learning loop that mandate
depends on, worded generically enough to slot into any org's existing process
or stand alone with none. The learned skill is held to the same bar — it
accumulates *task-shape* calibration, not organization-specific grounding,
which is also what makes it safe to keep machine-wide. If you want to layer
your own organization's broader flow on top, write your own overlay skill the
same way the README's "Extending this agent for your own organization" section
suggests overlaying the agent file itself — don't fork this skill's text to do
it.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent
  this mandate points at. Pass A step 8 is the hook the learning loop fills.
- [`model-right-sizer-calibrate`](../model-right-sizer-calibrate/SKILL.md) —
  the sibling that feeds the ledger this skill seeds, and reviews/adopts
  SkillOpt's staged proposals.
- [`templates/learned-skill.seed.md`](../../templates/learned-skill.seed.md) —
  the seed for the machine-wide learned skill.
- [`templates/ledger-entry.schema.json`](../../templates/ledger-entry.schema.json)
  — the authoritative row schema; `additionalProperties: false` plus a closed
  `stage_kind` vocabulary is what keeps rows repo-agnostic by construction.
- [`README.md`](../../README.md) — "Using it" / "Importing it into another
  repo without duplicating it" — how to get the agent file itself into a
  target repo, the same pattern this skill's file follows.
