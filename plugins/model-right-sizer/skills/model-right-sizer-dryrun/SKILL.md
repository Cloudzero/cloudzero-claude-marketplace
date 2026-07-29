---
name: model-right-sizer-dryrun
description: >-
  Preview the model-routing MAP for an intent without building anything.
  You give it a free-text INTENT — "build a CLI that…", "add a feature
  that…", "refactor X into Y" — and it invokes the `model-right-sizer`
  agent in BLUEPRINT-ONLY mode: decompose the work, score each piece, and
  emit the task→model→effort→budget→schema→confidence routing table (the
  "map"), then STOP. No build, no file edits, no after-the-fact usage
  report — it is the what-would-this-cost / how-would-this-route preview
  lever, safe to run against any idea. Read-only. Use when someone says
  "dry-run the right-sizer on …", "what's the map for …", "how would you
  route …", or "show me the blueprint for … before I build it".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-dryrun — map an intent, don't build it

This skill does exactly one thing: turn a plain-English **intent** into the
`model-right-sizer` agent's **blueprint** — the routing map that says which
model, effort, and reasoning budget each piece of the work should run on —
and then stop. Nothing is built, nothing is edited, no closing usage report
is run. It is the *preview* half of the agent's bookend, unbundled from the
work it normally brackets.

It is the companion to
[`model-right-sizer.md`](../../agents/model-right-sizer.md) (the agent that
produces the map) and a sibling to
[`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) (which
stamps the standing mandate onto a repo). Where `-install` says *"consult
the agent around every real task,"* this skill lets you consult just the
**front** bookend, on demand, against a hypothetical — so you can see the
shape and the intelligence budget of a build before committing to it.

## Why "blueprint-only" is not a new mode

The `model-right-sizer` agent already defines two passes: **Pass A — the
Right-Sizing Blueprint** (before the work starts) and **Pass B — the Closing
Reconciliation** (after it ends). A dry run is simply **Pass A run on its
own**, against a supplied intent instead of an in-flight task. This skill
invents nothing the agent doesn't already do — it just scopes the agent to
its first bookend and skips the build and Pass B that would normally follow.
Keep it that way: if you find yourself asking the agent to estimate *actual*
spend or reconcile recommended-vs-actual, that's Pass B, and it belongs to a
real run, not a dry run.

## What to do

1. **Capture the intent.** Take the user's free-text description of what they
   want built as the intent. If they invoked the skill with an argument
   (`/model-right-sizer-dryrun build a meeting-cost CLI`), that argument *is*
   the intent. If they invoked it bare, ask for one line: "What do you want a
   map for?" — do not guess a build.

2. **Do NOT start building.** This is the load-bearing constraint. You are
   not writing code, not editing files, not scaffolding a repo, not
   dispatching execution sub-agents. If the intent is ambiguous, you may ask
   one clarifying question about *scope* (so the decomposition is honest), but
   you resolve it into a map, never into an implementation.

3. **Invoke `model-right-sizer` for Pass A only.** Dispatch the
   `model-right-sizer` agent with the intent and an explicit instruction that
   this is a **blueprint-only dry run**: produce the Pass A deliverables and
   stop. Pass it, verbatim, the scope of Pass A to return:
   - **Task decomposition** — the stages/sub-agents the intent would spend
     model tokens on, one row each; flag any data-query-shaped stage that a
     deterministic query layer could answer instead of a model.
   - **Three signals per stage** — Effectiveness-need, Efficiency-pressure,
     and Difficulty (0–100 each), every number with a one-clause reason.
   - **Probability-weighted picks** — per stage: primary model + effort +
     confidence %, runner-up + %, and the concrete "what flips it."
   - **The routing table** — `stage → default → model → effort → budget →
     handoff schema → confidence → keep-or-override → rationale`.
   - **The work-routing map** — build unit → tier → effort → budget →
     schema → confidence → rationale → what-flips-it.
   - **Message-schema spec** — the minimal payload each handoff seam carries.
   - **Uncertainty ledger** — assumptions, price-sheet freshness state, and
     what it would measure to sharpen the map.

4. **Emit the map and STOP.** Print the agent's blueprint to the chat as the
   whole deliverable. Do not follow it with a build. Do not write it to a
   file unless the user explicitly asks. Close by naming, in one line, that
   this was a dry run — nothing was built, and the actual usage report (Pass
   B) would only exist if the work were really run.

## What this does NOT do

- It does **not** build, edit, scaffold, or dispatch execution agents.
- It does **not** run Pass B (the recommended-vs-actual usage report) — there
  is no "actual" to reconcile against on a dry run.
- It does **not** stamp or modify the mandate — that's
  [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md).
- It is **read-only**, exactly like the agent it invokes: it maps and
  recommends, it never applies the picks.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent
  whose Pass A this skill surfaces on demand.
- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — the
  sibling that installs the standing before/after mandate; this skill is the
  on-demand, front-bookend-only preview of it.
