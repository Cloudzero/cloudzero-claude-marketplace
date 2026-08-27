---
name: model-right-sizer-buzz-install
description: >-
  Extend the model-right-sizer mandate to a Buzz Nest — a persistent
  multi-agent workspace created by Buzz Desktop (github.com/block/buzz),
  identifiable by an `AGENTS.md` whose content opens with a `# Buzz Nest`
  heading. Runs `model-right-sizer-install` first to stamp the standard
  mandate onto that `AGENTS.md`, then closes a Buzz-specific gap plain
  `AGENTS.md`-stamping doesn't cover: every Buzz teammate delegates to its
  real xdp-tools-style agent via an `Agent`/`Task`-tool sub-agent spawn,
  and that spawn does NOT inherit the calling session's `AGENTS.md` or
  project memory — confirmed by direct test, not assumed. So this skill
  also patches the Buzz persona's own system-prompt source file(s) with a
  short pointer paragraph ("read this Nest's AGENTS.md for standing
  mandates before your first action") — a pointer, never a copy of the
  mandate text, so the wording stays single-sourced. Idempotent and
  append-only throughout. Use when someone says "add Buzz support to
  model-right-sizer", "install the right-sizer mandate for my Buzz
  agents", or "make my Buzz teammates consult model-right-sizer".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-buzz-install — extend the mandate into a Buzz Nest

`model-right-sizer-install` already knows how to stamp the standing mandate
onto `AGENTS.md` (see its step 3) — that part isn't special to Buzz, it's
just the generic "this repo uses `AGENTS.md` instead of `CLAUDE.md`" case.
What *is* Buzz-specific, and what this skill exists to close, is a
propagation gap that only shows up once a workspace has **multiple
independently-addressable agent identities that delegate to a real agent
via a sub-agent spawn** — which is exactly how a Buzz Nest's teammates work,
and exactly what a single-session repo never needs to worry about.

## The gap, confirmed by test

A Buzz teammate (e.g. an `xdp-tools:model-right-sizer` persona addressable as
`@xdp-tools:model-right-sizer` in a channel) is itself a small proxy: its
system prompt tells it to *delegate* — invoke the `Agent`/`Task` tool with
the real agent's `subagent_type`, relay the result, and reply via
`buzz messages send`. That sub-agent spawn only receives the **target
agent's own definition** as its system prompt. It does **not** inherit the
calling session's `AGENTS.md`, however good the mandate block sitting inside
it is. This was verified directly: a live spawn of a real `model-right-sizer`
sub-agent, asked to report its own starting context, confirmed zero mention
of `AGENTS.md` or any mandate block — its own words, "if you're checking
whether a mandate mechanism propagates into spawned sub-agents — it did not
reach me." Stamping `AGENTS.md` alone is therefore necessary but not
sufficient in a Buzz Nest; it reaches a fresh top-level session rooted
there, but not the delegate hop every Buzz persona makes on every request.

The fix isn't more `AGENTS.md` editing — it's teaching the **persona's own
system prompt** to read `AGENTS.md` itself, before it delegates. That's a
one-line pointer, not a restatement of the mandate, so the wording still has
exactly one source of truth.

## What to do

1. **Confirm this is actually a Buzz Nest, not just an `AGENTS.md` repo.**
   `AGENTS.md` is a broader convention (several coding-agent tools read it,
   not only Buzz) — don't assume Buzz just because the file exists. Check
   for the Buzz signature: the file's content opens with a `# Buzz Nest`
   heading and a line noting it was "Created once by the Buzz desktop app."
   If `AGENTS.md` exists but doesn't carry that signature, this isn't a Buzz
   Nest — stop here and defer to plain `model-right-sizer-install` instead;
   don't apply Buzz-specific steps to a non-Buzz repo.

2. **Run `model-right-sizer-install` against this Nest first.** It already
   knows how to detect `AGENTS.md`-only repos (no `CLAUDE.md` invented) and
   stamp the standard marker-delimited mandate block into it — reuse that
   logic rather than duplicating the block's text here. If it's already
   present (idempotent re-run), say so and move on to step 3 regardless —
   the mandate being in `AGENTS.md` is necessary but not the part this skill
   actually adds value on.

3. **Find the Buzz persona system-prompt source(s) in this workspace.**
   These are whatever files get pasted into Buzz Desktop's Agents view or
   uploaded as `.agent.json` for the teammates that should carry this
   mandate — commonly `**/generated/personas/*.md` if a `buzz-bridge`-style
   generation pipeline produced them (check for a sibling
   `generate_agent_json.py` or similar to confirm the pattern), but don't
   assume that path — ask the user where their Buzz agents' system prompts
   live if none are found automatically. If genuinely none exist yet (no
   Buzz teammates created in this Nest so far), say so plainly and stop;
   there's nothing to patch until an agent exists.

4. **Insert or refresh a marker-delimited pointer paragraph** in every
   persona source file found in step 3 — append-only, idempotent (check for
   the marker before inserting, skip files that already have it):

   ```markdown
   <!-- model-right-sizer-buzz-mandate:begin (managed by model-right-sizer-buzz-install — do not hand-edit; re-run the skill to refresh) -->
   **Standing mandates.** Before your first substantive action in a channel
   each session, read this Nest's `AGENTS.md` (in your working directory) for
   any standing mandates — e.g. the model-right-sizer consult block — and
   follow them.
   <!-- model-right-sizer-buzz-mandate:end -->
   ```

   This is deliberately a *pointer*, not the mandate text itself — the
   mandate's actual wording stays single-sourced in `AGENTS.md`
   (`model-right-sizer-install` owns that content; this skill never restates
   it). If a persona file's boilerplate already ends with a natural closing
   section (e.g. a "Stay in your lane" paragraph, per the `buzz-bridge`
   convention), insert directly after it; otherwise append at the end of the
   file.

5. **If the personas are already-generated `.agent.json` snapshots** (not
   just source `.md` cards), regenerate them from the patched source per
   whatever pipeline produced them (e.g. re-run its `generate_agent_json.py`)
   — don't hand-edit the JSON directly, or the next regeneration will
   silently drop the change.

6. **Flag, don't perform, the live-push step.** Patching source files
   changes what a *newly created or re-drafted* Buzz agent will say — it
   does **not** update an already-saved, live teammate's actual system
   prompt in Buzz Desktop. That requires `buzz agents draft-update` per
   agent, each one landing as an owner-reviewed draft the human must save.
   That's a bigger, more visible action than editing source files (N owner
   reviews, one per affected agent) — tell the user how many personas were
   patched and that pushing them live is a separate step requiring their
   go-ahead; do not run `draft-update` without it.

7. **Verify, don't assume.** Re-read every file you touched (the `AGENTS.md`
   mandate block from step 2, and every persona pointer from step 4) and
   confirm the markers and content landed as expected.

8. **Report**: whether this was confirmed a Buzz Nest; whether the
   `AGENTS.md` mandate was freshly stamped or already present; which persona
   source files got the pointer paragraph (and which, if any, were skipped
   as already patched); whether a regeneration step ran; and the exact count
   of live agents still needing a `draft-update` to actually pick this up,
   with a clear ask before running that.

## Why this is a separate skill, not a branch inside `model-right-sizer-install`

`model-right-sizer-install` stays organization- and tool-agnostic — it only
ever needs to know "does this repo read `CLAUDE.md`, `AGENTS.md`, or both,"
a question every target repo answers the same simple way. Buzz's delegate
pattern (many independently-addressable identities, each proxying to a real
agent through a sub-agent spawn that doesn't inherit project memory) is a
structurally different problem that only exists for a Buzz Nest, and solving
it means editing a *different class of file* (persona system-prompt
sources, not agent-instructions files) with a *different kind of content*
(a pointer, not the mandate). Folding that into `model-right-sizer-install`
would mean every non-Buzz caller pays for Buzz-shaped branching it never
needs. Keeping this as a sibling skill — the same discipline
`model-right-sizer-install` already uses to stay separate from any bigger
org-specific development flow — means a Buzz Nest gets exactly the one extra
step it needs, and nothing else does.

## Related

- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — run
  first; owns the actual mandate text and the `CLAUDE.md`/`AGENTS.md`
  detection this skill builds on rather than re-implements.
- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — what
  the mandate's "before" hook actually runs; unaffected by this skill.
- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent
  every Buzz persona's delegate hop ultimately spawns.
