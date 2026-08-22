---
name: model-right-sizer-budget-guard
description: >-
  The while-work-is-in-flight companion to `model-right-sizer-dryrun`: once a
  blueprint's `work_routing_map[]` is real and an orchestrating/chief-of-staff
  session is actually dispatching those units as sub-agents, this is the
  concrete runbook for keeping two things honest as dispatch proceeds — the
  status ledger (`status` / `status_updated_at` / `status_note` on each
  routing-map row, flipped at every real transition with a freshly-read
  timestamp, never guessed or reused) and the token-budget guard (checking
  real spend against `budget.token_ceiling` and, once
  `eval/budget_threshold.py`'s `threshold_crossed()` trips at
  `warning_threshold_pct`, sending that unit's own `format_budget_warning()`
  string verbatim into its next turn). Deliberately after-each-dispatch-returns
  rather than mid-turn: this skill states plainly that no confirmed live
  mid-turn token-spend signal exists in the dispatch mechanisms it could
  verify, so it checks at turn boundaries with whatever usage figure the
  dispatch mechanism reports on completion, not a fabricated live ticker. Only
  applies to `work_routing_map[]` rows actually being dispatched — never to
  `blueprint_rows[]` (design-time only) — and never replaces Pass B's closing
  usage report. Use when someone says "dispatch the work-routing map", "run
  the budget guard while units are in flight", "update the status ledger for
  unit X", or "did unit X cross its warning threshold".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-budget-guard — the ledger + threshold runbook while units are actually in flight

This skill is the **operational half** of dispatch: the concrete steps an
orchestrating/chief-of-staff session follows, per
[`work_routing_map[]`](../../schemas/blueprint.schema.json) row, while real
sub-agent dispatch is happening. It assumes
[`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) (or a real
Pass A) has already produced a blueprint with a non-empty `work_routing_map[]`
— this skill does not decompose work or pick models, it operationalizes a
map that already exists. Think of the pair as: dry-run produces the map,
budget-guard walks it.

It covers two things that are easy to state in prose and easy to fake in
practice, so both are pinned to deterministic checks and honest constraints
rather than vibes:

1. **The status ledger** — every `work_routing_map[]` row's `status` /
   `status_updated_at` / `status_note`, kept current as dispatch actually
   proceeds.
2. **The threshold warning** — real spend checked against
   `budget.token_ceiling`, using
   [`eval/budget_threshold.py`](../../eval/budget_threshold.py)'s
   `threshold_crossed()` / `format_budget_warning()`, never an LLM's
   per-turn guess about whether a unit is "getting expensive."

## When this runs

After a blueprint exists and its `work_routing_map[]` rows are about to be
(or already are) dispatched as real sub-agents — not against a hypothetical.
If there is no blueprint yet, or you're exploring "what would this cost"
before committing to a build, that's
[`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md), not this
skill. This skill is the thing that runs *between* dry-run producing the map
and Pass B closing it out — the "while work is in flight" middle, which
neither of those two bookends covers on their own.

## What to do

1. **Confirm you have a real map to walk.** Read the blueprint's
   `work_routing_map[]`. Every row starts `status: "not_started"`,
   `status_updated_at: null` (the schema enforces this pairing — see
   [`schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)'s
   `routingMapRow` `allOf`/`if`/`then`). If the map is empty, there is
   nothing yet to guard — that's expected for a dry run, and this skill has
   nothing to do until real build units exist.

2. **On dispatching a row, flip it to `dispatched` with a real, freshly-read
   timestamp.** Immediately before or as you issue the dispatch (via
   whatever sub-agent mechanism this session actually has — Claude Code's
   `Task` tool, an `Agent` tool in another plugin ecosystem, or a
   cross-session dispatch), set that row's `status: "dispatched"` and
   `status_updated_at` to the actual current time read at that moment. Never
   reuse an earlier timestamp from the same batch and never guess one —
   if two rows dispatch back-to-back, read the clock again for the second.
   The schema requires a real ISO-8601 string here (non-null the instant
   `status` leaves `"not_started"`), and "real" means read-not-invented: a
   plausible-looking timestamp that wasn't actually read at dispatch time is
   exactly the kind of fabricated status this skill exists to prevent.

3. **Once the dispatch is actually running, flip to `in_progress` and
   re-stamp.** Do this when you have positive evidence the sub-agent's turn
   has started (the dispatch call has returned an in-flight handle, or — for
   a synchronous dispatch with no separate "started" signal — fold this
   into step 2 and go straight from `not_started` to `in_progress` rather
   than inventing a `dispatched` state you never actually observed). Either
   way, `status_updated_at` gets re-stamped with a freshly-read timestamp at
   this transition too — every write to `status` carries its own fresh
   timestamp, not a copy of the previous one.

4. **On return, flip to `done` or `blocked`, with a concrete `status_note`,
   and re-stamp again.**
   - `done`: the unit's work actually completed. A `status_note` is optional
     here but useful — e.g. naming that it finished after a budget warning
     (see the worked example below).
   - `blocked`: the unit did not complete, and `status_note` is required in
     spirit (the schema marks it optional but the whole point of `blocked`
     is a *reason*): name the concrete blocker — a failing dependency, a
     question that needs a human answer, a budget ceiling blown with no
     more headroom to grant, etc. "Blocked" with no note is exactly the
     unhelpful status this field exists to avoid.
   - Re-stamp `status_updated_at` with a freshly-read timestamp at this
     write too — the same discipline as steps 2–3, on every transition, no
     exceptions.

5. **Check real spend against `budget.token_ceiling` after each dispatch
   returns — not on an assumed mid-turn callback.** Before writing anything
   here, this skill's own author checked (rather than assumed) whether this
   session's sub-agent dispatch mechanisms expose a *running* token-spend
   signal for a sub-agent whose turn has not yet closed. **Finding: no such
   signal was found or could be confirmed.** Concretely:
   - This session's own tool surface has no `Task`/`Agent`-style dispatch
     tool exposed to introspect, and no evidence turned up of a streamed,
     mid-turn usage callback on the dispatch mechanisms this plugin's own
     agent file names (`Task` in Claude Code, `Agent` in other plugin
     ecosystems, or a cross-session `create_session`/`send_message` handoff)
     — what these mechanisms give the caller is a result once the dispatched
     turn closes, not a live ticker while it runs.
   - Treat that as the honest default unless you can *positively confirm*
     otherwise in your own runtime: **check spend at turn boundaries —
     between turns, after each dispatch returns — using whatever usage/token
     figure that dispatch mechanism reports on completion**, not a live
     mid-turn interrupt. If your environment genuinely does expose a
     verified mid-turn signal, you may check more often, but say so
     explicitly rather than silently assuming one exists.
   - For each row whose dispatch just returned, take the real `actual_tokens`
     figure the dispatch reported and call
     `budget_threshold.threshold_crossed(actual_tokens, budget.token_ceiling,
     budget.warning_threshold_pct or 0.7)`. Never guess this boolean by eye —
     it is a deterministic function for exactly the reason `eval/budget_threshold.py`'s
     module docstring gives: one answer for "has this crossed its warning
     line," not an LLM's per-turn read of the vibes.

6. **If it crossed AND the unit has a follow-up turn coming, inject the
   warning verbatim.** `threshold_crossed()` returning `True` only matters
   operationally when there's a *next* turn to steer — a multi-step or
   iterative dispatch that will continue (another sub-task in the same
   unit, a continuation turn, a retry). In that case, call
   `budget_threshold.format_budget_warning(unit_id, actual_tokens,
   token_ceiling, warning_threshold_pct)` and send its exact return string —
   not a paraphrase, not a summary — into that unit's own next-turn context.
   The function's docstring is explicit that its wording is the contract a
   sibling agent-file instruction quotes as-is; this skill is the other
   consumer of that same contract, so match it exactly. If the unit's
   current turn is actually its last (it's about to report `done` or
   `blocked` regardless), there is no next turn to warn into — let it finish
   and record the crossing in `status_note` instead if it's useful context.

7. **Never fabricate what you can't observe.** If a dispatch mechanism
   doesn't report a token/usage figure on return, do not invent one to feed
   `threshold_crossed()` — say plainly (in your own narration, or in
   `status_note`) that spend is unknown for that row, and skip the
   threshold check for it rather than manufacturing a number. The same
   applies to `status`: a row you have not actually dispatched stays
   `not_started`, however tempting it is to mark it `dispatched` to make the
   ledger look further along than it is.

## Worked example

A blueprint's `work_routing_map[]` has row `unit-3` — `build_unit: "billing
webhook retry handler"` — with `budget: {token_ceiling: 40000,
warning_threshold_pct: 0.7}` (the default). It starts:

```json
{ "id": "unit-3", "status": "not_started", "status_updated_at": null }
```

**T0 — dispatch.** The orchestrator dispatches `unit-3` as a sub-agent and
reads the real clock:

```json
{ "id": "unit-3", "status": "dispatched", "status_updated_at": "2026-08-22T14:03:11Z" }
```

**T0+ε — running.** The dispatch call returns an in-flight handle. Re-stamp:

```json
{ "id": "unit-3", "status": "in_progress", "status_updated_at": "2026-08-22T14:03:12Z" }
```

**T1 — first turn returns.** The sub-agent's turn closes having made partial
progress and needing a continuation (a second sub-task within the same
unit). The dispatch mechanism reports `actual_tokens: 29500` for that turn.
Check it:

```
budget_threshold.threshold_crossed(29500, 40000, 0.7)
  → 29500 / 40000 = 0.7375 ≥ 0.7 → True
budget_threshold.remaining_budget_pct(29500, 40000)
  → 1.0 - 0.7375 = 0.2625   # ~26% headroom left
```

It crossed, and `unit-3` has a follow-up turn coming, so the orchestrator
calls `format_budget_warning("unit-3", 29500, 40000, 0.7)` and sends the
exact returned string into the continuation:

> Budget warning for 'unit-3': you have used 74% of your 40000-token budget
> (29500 tokens spent), crossing the 70% warning threshold. Wrap up and
> report now, or tighten scope to finish within the remaining budget. If the
> remaining work genuinely needs more, stop and explicitly ask for
> additional budget rather than continuing silently past the ceiling.

**T2 — second turn returns, unit finishes.** The sub-agent tightens scope
per the warning and reports done at a total of 36800 tokens — under the
ceiling. The orchestrator re-stamps once more and closes the row:

```json
{
  "id": "unit-3",
  "status": "done",
  "status_updated_at": "2026-08-22T14:11:47Z",
  "status_note": "Completed after crossing the 70% warning at turn 1 (29500/40000); tightened scope per the warning, finished at 36800/40000 (92%)."
}
```

Had the second turn instead blown past 40000 with no more useful scope to
cut, the correct close would have been `status: "blocked"` with a
`status_note` naming that concretely (e.g. "exceeded 40000-token ceiling at
turn 2 with retry logic still unhandled; needs a larger budget or a split
into two units") — not a `done` that papers over an overrun, and not a
silent continuation past the ceiling.

## What this does NOT do

- **Does not replace Pass B.** The closing, recommended-vs-actual usage
  report is a separate deliverable of the `model-right-sizer` agent itself
  (see its "Pass B — Closing Reconciliation" section) — this skill's
  in-flight warnings are a steering signal *during* dispatch, not the final
  accounting.
- **Does not fabricate a status or a token count it can't observe.** See
  step 7 above — an unknown stays unknown, narrated as such, rather than
  papered over with a plausible-looking value.
- **Does not warn on `blueprint_rows[]`.** Those are Pass A's design-time
  stage table — scored and picked, but never themselves dispatched. Only
  `work_routing_map[]` rows are real dispatches, so only they get a status
  ledger or a threshold check.
- **Does not change `warning_threshold_pct`'s default of `0.7`** on its own
  initiative. A blueprint row may set its own value (see
  [`schemas/blueprint.example.json`](../../schemas/blueprint.example.json)'s
  `unit-1`, at `0.65`) — honor whatever the row states — but this skill
  never overrides the schema's `0.7` default unless the user explicitly
  asks for a different one.
- **Does not assume a mid-turn token-spend callback exists.** See step 5:
  this is a deliberate, checked constraint, not an oversight — if your
  runtime genuinely has one, that's an enhancement to layer on top, not
  something to silently assume this skill already does.

## Related

- [`../../eval/budget_threshold.py`](../../eval/budget_threshold.py) — the
  deterministic `remaining_budget_pct` / `threshold_crossed` /
  `format_budget_warning` functions this runbook calls; read it for exact
  signatures and the zero-ceiling / invalid-percentage edge cases before
  wiring it into your own orchestration code.
- [`../model-right-sizer-dryrun/SKILL.md`](../model-right-sizer-dryrun/SKILL.md)
  — the front bookend that produces the `work_routing_map[]` this skill
  walks; run that first if no blueprint exists yet.
- [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
  — the `routingMapRow` and `budget` `$defs` that define `status` /
  `status_updated_at` / `status_note` and `warning_threshold_pct`, including
  the `allOf`/`if`/`then` that mechanically couples `status_updated_at` to
  `status`.
- [`../../agents/model-right-sizer.md`](../../agents/model-right-sizer.md) —
  the agent whose Pass A produces the map and whose Pass B closes it out;
  this skill is the concrete middle between those two bookends.
