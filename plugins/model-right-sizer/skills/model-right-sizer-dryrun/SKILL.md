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
   as the JSON object. Every `work_routing_map[]` row's `status` should come
   back `not_started` with `status_updated_at: null` — a dry run previews
   the map, it never dispatches, so nothing has a status or a clock-stamped
   change to report yet.

4. **Validate against the schema itself, emit the JSON, and STOP.** Before
   printing anything, run the agent's raw JSON response through
   [`../../../../scripts/validate_blueprint.py`](../../../../scripts/validate_blueprint.py)
   — the same validator CI runs against `blueprint.example.json` — rather
   than eyeballing a hand-picked list of "the fields that seemed important":
   that's exactly how an earlier version of this step went stale (it
   checked `budget.token_ceiling` but not, say, `pick.what_flips_it`, and a
   payload missing the latter passed silently). Pipe the response's JSON on
   stdin so nothing is written to disk:

   ```bash
   echo "$BLUEPRINT_JSON" | uv run --no-project --with jsonschema \
     scripts/validate_blueprint.py -
   ```

   That one command enforces the *complete* contract — every `required`
   key at every nesting level, every enum, every type, defined once in
   [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
   — plus the one thing a JSON Schema can't express: that every
   `handoff_schema_ref` which isn't `"none"` or `"route_via_query_layer"`
   actually resolves to a real `message_schemas[].id`.

   If `scripts/validate_blueprint.py` isn't present in the current checkout
   (this plugin was copied standalone into a consumer repo rather than
   installed from the marketplace clone — see
   [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md)'s
   fallback path), do not skip validation: read
   `../../schemas/blueprint.schema.json` directly and confirm every
   `required` array at every `$defs` level is satisfied, every enum value
   is legal, and every `handoff_schema_ref` resolves — against the schema
   itself, not a paraphrase of it kept here.

   If the command doesn't parse the input, or exits non-zero, ask the
   agent to re-emit once, quoting the validator's error output (it names
   the exact path and requirement violated) so it knows precisely what's
   missing or malformed — a JSON blob with the right top-level shape but a
   hollow field or a dangling reference is not conformant, and passing it
   along silently would hand the orchestrator a blueprint it can't
   actually route by. Once it genuinely validates clean, print the JSON
   verbatim (pretty-printed) to the chat as the whole deliverable — this
   is what an orchestrator or any downstream tooling should parse to route
   dispatch, not a paraphrase of it. Do not follow it with a build. Do not
   write it to a file unless the user explicitly asks. Close by naming, in
   one line, that this was a dry run — nothing was built, and the actual
   usage report (Pass B) would only exist if the work were really run.

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
