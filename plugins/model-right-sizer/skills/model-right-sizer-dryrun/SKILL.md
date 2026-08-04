---
name: model-right-sizer-dryrun
description: >-
  Preview the model-routing MAP for an intent without building anything.
  You give it a free-text INTENT — "build a CLI that…", "add a feature
  that…", "refactor X into Y" — and it invokes the `model-right-sizer`
  agent in BLUEPRINT-ONLY mode: decompose the work, score each piece, and
  emit a single schema-conformant JSON blueprint (task→model→effort→budget→
  schema→confidence, per `schemas/blueprint.schema.json`), then STOP. No
  build, no file edits, no after-the-fact usage report — it is the
  what-would-this-cost / how-would-this-route preview lever, safe to run
  against any idea, and the JSON it returns is what an orchestrator parses
  to route dispatch. Read-only. Use when someone says "dry-run the
  right-sizer on …", "what's the map for …", "how would you route …", or
  "show me the blueprint for … before I build it".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-dryrun — map an intent, don't build it

This skill does exactly one thing: turn a plain-English **intent** into the
`model-right-sizer` agent's **blueprint** — a single JSON object, conformant
to
[`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json),
saying which model, effort, and reasoning budget each piece of the work
should run on — and then stop. Nothing is built, nothing is edited, no
closing usage report is run. It is the *preview* half of the agent's
bookend, unbundled from the work it normally brackets.

It is the companion to
[`model-right-sizer.md`](../../agents/model-right-sizer.md) (the agent that
produces the blueprint) and a sibling to
[`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) (which
stamps the standing mandate onto a repo — and, since that mandate now runs
this skill directly before every substantive task, this is no longer only
an *ad hoc* preview). Called on demand, against a hypothetical, it lets you
see the shape and the intelligence budget of a build before committing to
it; called by the mandate, it's the mechanism that produces the JSON the
orchestrating session routes real dispatch by.

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
   this is a **blueprint-only dry run**: produce the Pass A deliverable and
   stop. Tell it to set `mode: "dry_run"` and `intent` to the captured
   text. The deliverable is the single JSON object described in
   `model-right-sizer.md`'s Pass A section, conforming to
   [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
   — see
   [`../../schemas/blueprint.example.json`](../../schemas/blueprint.example.json)
   for a worked instance. Do not ask for, and do not accept, a markdown-table
   or prose rendering instead — if the agent returns one, ask it to re-emit
   as the JSON object.

4. **Validate, emit the JSON, and STOP.** Before printing anything,
   sanity-check the agent's response — top-level shape is necessary but not
   sufficient, so go one level deeper than "does it parse":
   - Does it parse as JSON, and are the required top-level keys
     (`schema_version`, `mode`, `intent`, `price_sheet`, `blueprint_rows`,
     `work_routing_map`, `message_schemas`, `uncertainty_ledger`) all
     present?
   - For every entry in `blueprint_rows[]` (and `work_routing_map[]`):
     `signals.effectiveness` / `.efficiency` / `.difficulty` each carry a
     `score` (0–100) and a non-empty `reason`; `pick.primary` and
     `pick.runner_up` each carry a `model` and a `confidence`; `budget`
     carries an actual integer `token_ceiling` (never missing, never
     `null` — `0` is the legitimate value for a row that spends no model
     tokens, e.g. one routed via `deterministic_query_layer`); any `effort`,
     `keep_or_override`, or `loop_class` value present is one of the
     schema's legal enum values, not free text.
   - Every `handoff_schema_ref` that isn't `"none"` or
     `"route_via_query_layer"` resolves to an actual entry `id` in
     `message_schemas[]` — a dangling reference is as broken as a missing
     key.

   If it doesn't parse, is missing a required key, or fails one of the
   nested checks above, ask the agent to re-emit once — a JSON blob with
   the right top-level shape but a hollow or dangling-reference row is not
   conformant, and passing it along silently would hand the orchestrator a
   blueprint it can't actually route by. Once it genuinely checks out,
   print the JSON verbatim (pretty-printed) to the chat as the whole
   deliverable — this is what an orchestrator or any downstream tooling
   should parse to route dispatch, not a paraphrase of it. Do not follow it
   with a build. Do not write it to a file unless the user explicitly asks.
   Close by naming, in one line, that this was a dry run — nothing was
   built, and the actual usage report (Pass B) would only exist if the work
   were really run.

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
  whose Pass A this skill surfaces, both on demand and as the mandate's
  before-hook.
- [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
  / [`blueprint.example.json`](../../schemas/blueprint.example.json) — the
  strict contract this skill's output must conform to; defined once here,
  not restated.
- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — the
  sibling that installs the standing before/after mandate. Its "before" hook
  now runs *this* skill directly, so this is no longer only an on-demand
  preview — it's also the live front-bookend mechanism.
