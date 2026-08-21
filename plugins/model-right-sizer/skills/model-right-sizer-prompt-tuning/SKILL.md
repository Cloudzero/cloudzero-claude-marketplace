---
name: model-right-sizer-prompt-tuning
description: >-
  Tune the exact WORDING of model-right-sizer's four already-shipped
  research-grounded layers to maximize real-execution accuracy (this repo's
  fixed definition: expected effort stayed within the blueprint's own
  predicted budget, per `classify_budget_adherence`) — not whether to include
  a layer (see the sibling `model-right-sizer-layer-ablation` skill for that),
  but how a layer that's already included should be phrased. Runs a discrete
  coordinate-ascent search (the ordinal, finite-difference analog of gradient
  descent for prose — there's no derivative of a Markdown file) over four
  small wording knobs in `eval/tuning/knobs.py`, each anchored at one exact
  spot in the shipped agent text that plausibly moves the accuracy ratio:
  how much margin `token_ceiling` carries above expected spend, how hard the
  effort dial leans down under difficulty-uncertainty, and whether Pass A's
  calibration ledger and Pass B's budget-adherence line push a corrected
  ceiling number forward. Read-mostly: never edits
  `agents/model-right-sizer.md`, only ever writes a scratch working
  directory and a final report (though its own last step is proposing that
  report's winning wording AS an edit to the shipped file, for a human to
  review and merge). Use when someone says "tune model-right-sizer's
  wording for accuracy", "optimize the budget-ceiling wording", "run a
  gradient descent / hill-climbing search on the agent prompt", or "which
  wording of the four layers gives the highest budget-adherence accuracy".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-prompt-tuning — search for the highest-accuracy wording of the four layers

This skill runs the search designed in
[`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) — **read that
file first**, especially its "What 'gradient descent' means here" section;
this SKILL.md is the runbook; the design doc is the honest account of what
kind of search this actually is and isn't.

In short: [`../../eval/ablation/`](../../eval/ablation/) already established
that all four layers earn their place (or at least, the fixed benchmark
suite hasn't shown otherwise). This skill starts from that answer — every
knob at level `0`, i.e. the shipped agent file — and coordinate-ascent
searches four small, independently-editable wording knobs
([`../../eval/tuning/knobs.py`](../../eval/tuning/knobs.py)) for the setting
that maximizes real-execution `accuracy_rate` (secondarily, `mean_loss`) on
a held-back-checked benchmark subset.

## Before running anything: state the scope and get it confirmed

This is the expensive kind of experiment from the start — unlike the
ablation study's cheap composition sweep, EVERY candidate evaluation here
requires real builds (there is no blueprint-only version of "did the real
build stay within budget"). Compute and state, before spending anything:

- **Per-candidate cost**: 1 Pass A dry-run + a real build per
  `blueprint_rows[]` entry it produces, across the 3 **tuning tasks**
  (`t1_bulk_classifier`, `t4_interactive_latency_sensitive_chat`,
  `t6_bounded_wellspecified_fix`) — typically 3–9 real builds per candidate.
- **Per-pass cost**: one candidate evaluation per non-current level across
  all four knobs (~6 candidates in this registry) — roughly 20–50 real
  builds for a full pass over every knob once.
- **Full-search cost**: `MAX_PASSES` passes (propose 2–3 as a default,
  state it explicitly) until convergence or the cap, plus one held-out
  check (3 more tasks' worth of real builds) at the very end, run once.

If the person invoking this skill hasn't already specified `MAX_PASSES` or
a smaller pilot scope (e.g. "just sweep `budget_margin` once"), ask before
spending real build budget on a full multi-pass search. A reasonable
default when asked to "just run it": one full pass across all four knobs
(≈20–50 real builds), reporting whether it converged, before committing to
a second pass.

## Step 1 — measure (or reuse) the overhead floors

Real-execution measurement needs the same overhead-normalization discipline
[`../../eval/ablation/results/2026-08-21-full-independent-run.md`](../../eval/ablation/results/2026-08-21-full-independent-run.md)
established: raw dispatch-reported token usage includes fixed per-dispatch
overhead (system prompt, tool schemas), not just the row's own spend.

- If this run is happening on the same runtime/agent-dispatch mechanism as
  that prior run, reuse its floors
  (`../../eval/ablation/results/2026-08-21-full-independent-run-accuracy.json`'s
  `overhead_floors`: sonnet 38,401 / haiku 28,508 tokens) rather than
  re-measuring — but say explicitly that you're reusing them and why you
  judge them still valid (same runtime, same rough timeframe).
- Otherwise, dispatch one no-op control agent per model tier this search
  will actually use (at minimum, whichever tiers the shipped agent's own
  illustrative snapshot lists as live defaults) and record each one's
  reported token usage as that tier's floor.

## Step 2 — the search loop

For each pass (cap at the confirmed `MAX_PASSES`), for each knob in
`knobs.ALL_KNOBS`, in order:

1. **Render every neighbor.** For the current settings and this knob, every
   OTHER level of `knobs.KNOBS[knob_name]["levels"]` is one neighbor
   candidate (`optimizer.propose_neighbors`). Render each with
   [`../../eval/tuning/generate_variant.py`](../../eval/tuning/generate_variant.py)
   or `knobs.render_variant` directly.
2. **Evaluate each neighbor independently.** For each neighbor candidate,
   dispatch one independent sub-agent PER (candidate, tuning-task) cell —
   same non-negotiable rule as the ablation study's Step 2, for the same
   reason: a session correlated across tasks or across candidates can
   produce a false accept/reject decision, not just add noise to a correct
   one. Use the variant's full text as the system prompt, the task's
   `prompt` as the intent, blueprint-only/dry-run mode first, then a real
   build per resulting `blueprint_rows[]` entry at its stated model/effort/
   budget, exactly as
   [`../../eval/ablation/DESIGN.md`](../../eval/ablation/DESIGN.md)'s
   accuracy-sweep step does. Record `{actual_tokens, budgeted_tokens}` per
   row, `actual_tokens` normalized by the Step 1 floor for that row's model
   tier.
3. **Batch the fan-out under the concurrency cap, and watch for a silent
   stall.** The `Agent` tool caps concurrent dispatches (20 at last check);
   past it, calls fail hard rather than queue. Prefer the `Workflow` tool's
   `pipeline()` for a candidate batch large enough to need it — it paces
   concurrency automatically. Either way, a long-running batch can stall
   with no error and no notification; if a check-in is overdue, diagnose via
   the run's `journal.jsonl` (`started` vs. `result` event counts) and
   output-file mtimes before assuming it's still progressing, and recover
   by recomputing the missing set from the filesystem rather than an
   assumed cursor — see
   [`../../eval/ablation/results/2026-08-21-full-independent-run.md`](../../eval/ablation/results/2026-08-21-full-independent-run.md)
   for a worked recovery from exactly this stall.
4. **Score every neighbor.** `optimizer.score_candidate(records)` per
   neighbor, using the current settings' own already-computed score as the
   baseline to beat (compute it once per pass if it changed; carry it
   forward unchanged if this knob is the first one visited this pass and
   the prior pass's winner is already scored).
5. **Take the step.** `optimizer.coordinate_ascent_step(current_settings,
   current_score, knob_name, neighbor_evaluations)`. If `improved` is
   `True`, adopt `new_settings`/`new_score` as current before moving to the
   next knob in this pass; if `False`, leave current unchanged.

After a full pass, if no knob moved, stop — converged. Otherwise continue
to the next pass, up to the confirmed cap.

## Step 3 — the held-out check (once, at the end)

Take the final `settings` (converged or cap-reached) and evaluate it —
same real-build protocol as Step 2 — against the **held-out** task set
(`t2_ambiguous_cross_service_refactor`, `t3_long_horizon_agentic_build`,
`t5_fanout_pr_review`), which no candidate touched during the search.
Report both numbers side by side. A held-out `accuracy_rate` well below the
tuning-set `accuracy_rate` is itself the headline finding (the search
overfit the tuning subset) — report it as prominently as a clean win would
be reported.

## Step 4 — write the findings, and propose (don't apply) the winning edit

Render a markdown report (or an Artifact) with, at minimum:

- **The search trace** — every pass, every knob visited, every candidate's
  `settings`/`accuracy_rate`/`mean_loss`, and which move (if any) was taken,
  so a reader can audit the path, not just the endpoint.
- **Convergence status** — did it converge, or hit the pass cap.
- **Tuning-set vs. held-out accuracy** for the final settings, side by side.
- **The winning settings, rendered as an actual diff** against the shipped
  `agents/model-right-sizer.md` (via
  [`../../eval/tuning/generate_variant.py`](../../eval/tuning/generate_variant.py)
  + `diff`) — this skill never edits the shipped file itself; a human
  reviews the proposed wording change and applies it (or doesn't) as its
  own separate, reviewable change.
- Every limitation named in DESIGN.md's "Known limitations" section,
  restated with this run's actual numbers, not just referenced.

## What this skill does NOT do

- It does **not** edit `agents/model-right-sizer.md` — every variant and
  every result lives under a scratch directory; the winning wording is
  reported as a proposed diff for a human to apply.
- It does **not** decide whether to include a layer at all — that question
  belongs to `model-right-sizer-layer-ablation`; this skill's search space
  starts from all four layers present and stays there.
- It does **not** search jointly across multiple knobs in one move, or
  guarantee a global optimum — see DESIGN.md's limitations.
- It does **not** invent a benchmark task, a tuning/held-out split, or a
  real usage number — always the fixed suite and split named in DESIGN.md,
  and a `computation_errors` entry (never a silent drop or a fabricated
  figure) for any record the scoring function rejects.

## Related

- [`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) — the full
  experimental design, including what "gradient descent" means here and the
  known limitations.
- [`../../eval/tuning/knobs.py`](../../eval/tuning/knobs.py) — the knob
  registry and variant renderer.
- [`../../eval/tuning/optimizer.py`](../../eval/tuning/optimizer.py) — the
  scoring function and coordinate-ascent step logic (pure, no dispatch).
- [`../../eval/tuning/generate_variant.py`](../../eval/tuning/generate_variant.py) —
  CLI to render one knob-settings variant.
- [`../model-right-sizer-layer-ablation/SKILL.md`](../model-right-sizer-layer-ablation/SKILL.md) —
  the sibling study this one presupposes (all four layers stay); shares the
  independent-dispatch and overhead-normalization discipline this skill
  reuses verbatim.
