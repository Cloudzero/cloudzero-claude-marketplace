---
name: model-right-sizer-chief-of-staff-drill
description: >-
  Dogfoods and scores the chief-of-staff status-ledger feature on
  `work_routing_map[]` (see `agents/model-right-sizer.md`'s "Chief of
  staff" section and `schemas/blueprint.schema.json`'s `status` field).
  Runs a small multi-stage intent through `model-right-sizer-dryrun` to get
  a real blueprint, actually DISPATCHES each `work_routing_map[]` unit as a
  live sub-agent doing real (if trivial) work, updates each row's `status`
  in place as dispatch proceeds exactly as the mandate instructs, then
  mid-flight — before every unit has finished — answers a simulated "give
  me a status update" purely by reading the ledger. Scores the result
  against ground truth on accuracy, completeness, and whether it actually
  saved a check versus re-opening every sub-agent thread, and prints a
  PASS/PARTIAL/FAIL verdict plus any concrete gap found. This is a
  behavioral drill, not a schema check — `tests/test_validate_blueprint.py`
  already proves the JSON shape is legal; this proves the role an
  orchestrator plays around it delivers on the "where am I at" promise
  end-to-end. It really dispatches sub-agents and writes real (throwaway)
  output; it does not simulate or narrate dispatch. Use when someone says
  "test the chief-of-staff feature", "dogfood the status ledger", "does the
  chief-of-staff pattern actually work", or "drill the work_routing_map
  status tracking".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-chief-of-staff-drill — prove the ledger works, don't just validate its shape

`tests/test_validate_blueprint.py` proves `work_routing_map[].status` is a
legal field with a legal enum. It says nothing about whether an orchestrator
that actually dispatches work, updates that field live, and answers a status
question from it produces something a person would find *accurate* and
*worth having*. This skill is the difference: it dispatches real sub-agents,
plays chief-of-staff over them for real, and grades the outcome.

## What to do

1. **Get (or default) an intent with >= 3 independent, small, genuinely
   dispatchable pieces of work.** If the user gave one, use it. If not,
   default to something trivial and harmless to run for real — e.g. three
   independent one-file, read-only or scratch-only sub-tasks (a short
   summary of a different doc each, or three tiny scratch files) — the work
   itself doesn't matter; what's under test is the ledger around it. Reject
   an intent that can't cleanly decompose into >= 3 units — the drill needs
   real concurrency to mean anything (a single-unit map can't go
   "mid-flight").

2. **Get a real blueprint.** Invoke the `model-right-sizer-dryrun` skill on
   the intent. Confirm the returned JSON has >= 3 `work_routing_map[]` rows,
   each `status: "not_started"` with `status_updated_at: null`. Validate it
   through
   [`../../../../scripts/validate_blueprint.py`](../../../../scripts/validate_blueprint.py)
   exactly as that skill's own step 4 does — this drill doesn't get to skip
   the check just because it's a test harness.

3. **Become the chief-of-staff thread — for real, not narrated.** Keep the
   blueprint JSON in hand (in context, or written to a scratch file) as the
   live status ledger. For each `work_routing_map[]` row:
   - Flip its `status` to `dispatched`, stamp `status_updated_at` with a
     **real clock read** taken at that moment (e.g. `date -u
     +%Y-%m-%dT%H:%M:%SZ`, never a guessed or remembered time), then
     actually dispatch a real sub-agent (the `Agent` tool, or your
     runtime's equivalent) to do that row's `build_unit`, honoring its
     `pick` (model/effort) when your runtime supports per-call overrides,
     and treating its `budget.token_ceiling` as a soft cap to note against
     if blown past.
   - Flip it to `in_progress` once dispatched and running, with a fresh
     `status_updated_at` reflecting *that* moment, not reused from the
     `dispatched` write.
   - On return, flip it to `done` — or `blocked` with a `status_note` naming
     the concrete reason, if it errored — with `status_updated_at` stamped
     again at that moment. Never silently drop a row, and never leave a
     status changed without also re-stamping the timestamp: a `status`
     write with no honest, freshly-read `status_updated_at` is exactly the
     schema violation `blueprint.schema.json`'s `routingMapRow.allOf`
     conditional rejects — this drill should never produce one.
   - Dispatch at least two rows so they are genuinely in flight
     concurrently (or staggered) rather than strictly serial one-at-a-time;
     a purely serial run can't expose a stale mid-flight read.

4. **Interrupt yourself mid-flight and answer a status question from the
   ledger alone.** After some rows have finished and at least one is still
   `not_started` or `in_progress`, stop and answer, as if a user just asked
   "where am I at?": read every row's current `status`, `status_updated_at`,
   and `status_note` (where set) and report one consolidated line per row.
   Do this by reading the ledger fields specifically — not by recalling
   from memory what you just did — since the whole point under test is
   whether the *fields* carry enough truth to answer from, independent of
   the asker's memory of the last few tool calls. For any non-terminal row
   (`dispatched`/`in_progress`), compare `status_updated_at` against the
   current time: if it's stale relative to how long that unit should
   plausibly take, report it as "unconfirmed, rechecking" rather than
   asserting it as fact — this is the freshness check the timestamp exists
   to enable, so use it, don't just carry the field for show.

5. **Let every dispatched unit finish, then diff the mid-flight answer
   against ground truth** (what had actually completed by that point,
   reconstructed from the real dispatch order/results). Score:
   - **Accuracy** — did the mid-flight report match what had actually
     happened, or did it over/under-claim any row's state?
   - **Completeness** — did every row in `work_routing_map[]` appear in the
     report, or did any get silently dropped?
   - **Value-add** — would answering the same question *without* the
     ledger have required re-opening/re-deriving state from each dispatched
     sub-agent's own output? State the concrete counterfactual, don't just
     assert yes.
   - **Friction** — anything about the `status`/`status_updated_at`/
     `status_note` fields that was awkward, ambiguous, or insufficient to
     update live (e.g. no way to express partial completion within a row).
     The original version of this drill found and named one such gap — no
     timestamp to tell a fresh `in_progress` from a stale one — which is
     now fixed (`status_updated_at`, schema-enforced non-null once `status`
     leaves `not_started`); don't re-discover it, but do watch for the next
     one the same way: report it, don't silently patch it inside the drill.

6. **Report a verdict — PASS, PARTIAL, or FAIL** — with the evidence from
   step 5, not just the label. PASS requires accuracy and completeness both
   clean; anything else is PARTIAL (name exactly what slipped) or FAIL (name
   why the ledger didn't actually answer the question it exists to answer).
   If the drill surfaces a concrete gap (e.g. "status has no timestamp"),
   say so as a named follow-up rather than silently patching the schema
   inside this drill — a test that quietly fixes what it's testing proves
   nothing.

## What this does NOT do

- Does not replace `tests/test_validate_blueprint.py`'s schema-shape
  checks — this is behavioral, those are structural; both are needed.
- Does not modify `agents/model-right-sizer.md`, the schema, or any other
  shipped file — it's a read/dispatch exercise against a scratch blueprint
  instance, not a change to the plugin.
- Does not simulate or narrate dispatch instead of doing it — a drill that
  pretends to dispatch sub-agents and imagines their results proves nothing
  about whether the pattern survives contact with real, concurrent work.
- Does not run Pass B (the closing usage report) — that's a real build's
  bookend; this is a targeted drill of one lever (the status ledger), not a
  full model-right-sizer run.

## Related

- [`../../agents/model-right-sizer.md`](../../agents/model-right-sizer.md) —
  the "Chief of staff" section this drill tests.
- [`../model-right-sizer-dryrun/SKILL.md`](../model-right-sizer-dryrun/SKILL.md)
  — produces the blueprint this drill dispatches against.
- [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
  — the `status` enum under test.
- [`../../../../tests/test_validate_blueprint.py`](../../../../tests/test_validate_blueprint.py)
  — the structural counterpart to this behavioral drill.
