---
name: model-right-sizer-holdout-tuning
description: >-
  Tune model-right-sizer's wording knobs (`eval/tuning/knobs.py`) against a
  REAL, already-measured build's actual token spend — not the synthetic
  `t1`-`t6` benchmark `model-right-sizer-prompt-tuning` searches, and not a
  fresh real build per candidate. Picks a task from
  `eval/tuning/overfitting_guard.py`'s `HOLDOUT_TASKS` registry (one whose
  `real_outcome_doc` already records real `{actual_tokens, budgeted_tokens}`
  pairs from a genuine past dispatch), dispatches 3 INDEPENDENT BLIND
  dry-runs per candidate (no calibration-ledger access — none may read
  `eval/tuning/results/`, `eval/ablation/results/`, or
  `overfitting_guard.py` itself) using the current best-known settings,
  averages each unit's budget across the 3 draws (a single draw is not
  reliable evidence — this repo's own history found single-draw noise
  large enough to flip within/over-budget classifications and make a
  reported "win" evaporate on re-measurement), maps the averaged units back
  to the matching real actuals, scores the match via
  `reasoning_budget.classify_budget_adherence` + `optimizer.score_candidate`,
  diagnoses the dominant miss pattern, proposes ONE targeted knob-wording
  change grounded in that evidence, and re-runs the same 3-draw-averaged
  comparison to check whether accuracy improved — still cheap per iteration
  relative to a real build, because only the blueprint step re-runs, since
  the ground truth is already measured. Carries an explicit stopping
  discipline: the same held-out task's n stays fixed no matter how many
  iterations run against it, so this skill flags — rather than silently
  keeps going — once further squeezing one task starts to look like
  overfitting instead of tuning. Use when someone says "tune the knobs
  against this blueprint/build", "iterate the dry run with no prior context
  against the real actuals", "keep tuning until N%", "test the new knobs on
  a fresh task" (once that task has a real outcome recorded), or "how close
  does a blind estimate get to what this actually cost".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-holdout-tuning — tune against a real build's actuals, blind

This is the sibling of
[`model-right-sizer-prompt-tuning`](../model-right-sizer-prompt-tuning/SKILL.md),
not a replacement for it. That skill searches `knobs.py`'s wording against
the fixed synthetic `t1`–`t6` benchmark, and every candidate costs a full
real build per tuning task. This skill searches the exact same `knobs.py`
registry, but against a **held-out task whose real cost is already
known** — a genuine past build, not a benchmark fixture — which means each
iteration costs one blind dry-run, not a full re-build. That efficiency is
the whole point: the ground truth doesn't move, only the estimate does, so
only the estimate needs to be re-run.

It exists because this exact loop is how `dispatch_floor_awareness` (a
knob in the current registry) went from level 0 to level 4 across several
real sessions — first a novel-use-case validation exposed the gap, then a
full feature build produced a second, richer held-out task with six real
data points, then two more rounds of blind dry-run → diagnose → add a knob
level → re-run closed most of the gap. This skill is that same loop,
written down so it doesn't have to be re-invented per session.

## Before starting: read the two files this loop depends on

- [`../../eval/tuning/overfitting_guard.py`](../../eval/tuning/overfitting_guard.py)
  — `HOLDOUT_TASKS` is the registry of tasks with real outcomes recorded;
  each entry's `note` field tracks how many times it's already been read,
  which is exactly the contamination/overfitting state you need before
  deciding whether to reuse it again or ask for a fresh one.
- [`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) — read
  whichever "Pass N" sections cover prior holdout-tuning rounds (search for
  "held-out" / "blind") so you don't re-diagnose a miss this repo's own
  history already explains, and so your new pass's write-up slots into the
  same numbering.

**Do NOT invoke this skill's dry-run agent with access to `overfitting_guard.py`
itself, `eval/tuning/results/`, or `eval/ablation/results/`** — those are
exactly the files a blind run must not read; reading any of them is the
calibration-masking contamination `overfitting_guard.assess_generalization()`
exists to catch (see `model-right-sizer-prompt-tuning`'s sibling concern,
and this repo's own pass 6 finding where a "clean win" turned out to be the
dry-run finding and reading the exact answer).

## What to do

1. **Pick the held-out task.** From `HOLDOUT_TASKS`, choose one whose
   `real_outcome_doc` has real `{actual_tokens, budgeted_tokens}` per-unit
   data (richer than a single ratio, if available — more points to score
   against). Read that `note` field first: if it says the task has already
   been used for calibrated (non-blind) reads, that's fine for THIS skill
   (which only ever runs blind); if it says the task's own n has been used
   to select a knob level multiple times already, weigh that against the
   target — pushing a third or fourth blind iteration on the same n=6 task
   is a real overfitting cost, not a free lunch, and is worth naming to
   whoever asked before continuing regardless.

2. **Render the current best-known settings.** Via
   [`generate_variant.py`](../../eval/tuning/generate_variant.py)
   `--settings "..."` — the same settings string named in `DESIGN.md`'s
   most recent "current best-known settings" line. Write the rendered
   variant to a scratch file; this is the dry-run agent's system prompt.

3. **Dispatch 3 independent blind dry-runs per candidate, not one.**
   A single draw is not reliable evidence: this repo's own history found
   per-unit standard deviations of 10–30% of the mean between draws of the
   IDENTICAL settings, large enough to flip `within_budget`/`over_budget`
   classifications outright and to make a single-draw "improvement" or
   "regression" indistinguishable from noise (see
   [`results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`](../../eval/tuning/results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md)'s
   iteration 4 — a reported `accuracy_rate` of 0.333 from one draw turned
   out to be 0.167 once averaged over 3). Dispatch 3 independent agents per
   candidate setting (same persona, same intent, same decomposition
   instructions) and average each unit's `token_ceiling` across the 3
   before scoring. A single draw is acceptable only for a cheap first look
   at whether a candidate is worth evaluating properly — never as the basis
   for an accept/reject decision on its own. Give each dispatched agent:
   - The rendered variant's full text as its persona.
   - Explicit instructions that this is BLIND: set
     `uncertainty_ledger.calibration.ledger_found: false`, and do not read
     `eval/tuning/results/`, `eval/ablation/results/`, or
     `overfitting_guard.py`. It MAY read the shipped schema, example,
     `agents/model-right-sizer.md`, and any deterministic library module
     the real build actually shipped (`eval/budget_threshold.py`,
     `eval/reasoning_budget.py`) — those are legitimate artifacts a real
     dry-run would see, not calibration data.
   - The held-out task's exact intent wording, copied verbatim from the
     task's own entry or its `real_outcome_doc` — not paraphrased, so
     repeated iterations stay comparable to each other.
   - **On the second and later iterations against the same task**: also
     tell it the same build-unit decomposition shape a prior iteration
     already used (name each unit), and ask it to decompose the same way.
     Comparing a blind run's own freely-chosen decomposition against real
     actuals from a DIFFERENT decomposition produces exactly the ambiguous,
     can't-cleanly-score result this repo's own pass 6 hit on the
     repo-slack-channel task — pin the shape down instead of re-deriving it
     each time.
   - `mode: "dry_run"`, Pass A only, return the JSON blueprint alone.

4. **Validate, then map units to real actuals.** Run the returned JSON
   through [`../../../../scripts/validate_blueprint.py`](../../../../scripts/validate_blueprint.py).
   Then match each `work_routing_map[]` unit to its corresponding real
   `{actual_tokens, budgeted_tokens}` pair by role/shape (schema unit →
   schema unit, skill-authoring unit → skill-authoring unit). If a unit's
   scope doesn't cleanly correspond to one real unit, say so explicitly
   rather than forcing a match — an honest "ambiguous, not scored" beats a
   confident wrong pairing.

5. **Score it.** Per matched unit, average `token_ceiling` across the 3
   draws (`statistics.mean`), then compute
   `reasoning_budget.budget_adherence_ratio(actual_tokens, mean_ceiling)`
   and `classify_budget_adherence(...)`. Also report each unit's `stdev`
   across the 3 draws next to its mean — a high stdev relative to the mean
   is itself a finding worth naming, not just a number to average away.
   **Check which side of the
   floor-inclusive/floor-exclusive line the current wording puts
   `token_ceiling` on before picking `actual_tokens`** — `dispatch_floor_awareness`
   at level ≥1 makes the ceiling floor-inclusive (compare against raw
   dispatch cost), whereas the unmodified baseline is implicitly
   floor-exclusive (compare against cost net of the tier's zero-tool floor)
   — mixing the two is the exact methodological error pass 6 corrected;
   get it right for whatever knob levels are actually in play this run.
   Then `optimizer.score_candidate(records)` for the aggregate
   `accuracy_rate`/`mean_loss`. Render a table: unit, budgeted, actual,
   ratio, class — plus the aggregate — and keep every prior iteration's
   table in the same write-up so the trajectory is visible, not just the
   latest point.

6. **Diagnose the miss pattern, don't just note the numbers.** For each
   `over_budget` or `under_budget_oversized` unit, ask what specifically
   drove it: a `loop_class` classification that hides real tool-call volume
   (e.g. `low-tool-turn` on a unit gated behind a mandatory validate-then-
   fix loop), an effort pick that under- or over-rates genuine difficulty,
   or plain sampling variance on a single dry-run draw (most visible on
   opus-tier picks whose budget swings between iterations with no wording
   cause — this repo's own pass 5 and pass 7 both found this pattern; name
   it as noise rather than inventing a causal story for a single data
   point). Group misses by shared shape across units, not one at a time —
   a fix that targets a shape shared by three misses is worth more than
   three separate fixes.

7. **Propose ONE targeted change.** Prefer adding a new LEVEL to an
   existing knob in `knobs.py` (matching its exact anchor-discipline: level
   `0` unmodified, every non-zero level a full replacement text, disjoint
   non-overlapping anchors) over inventing a new knob, unless the diagnosed
   mechanism genuinely doesn't fit any existing knob's anchor location. If
   you ground a concrete numeric range in this session's own real-dispatch
   evidence, say so explicitly in the knob's own description/text — that's
   a disclosed, general-purpose calibration baked into the wording, not a
   hidden runtime ledger lookup, and the difference matters for
   `overfitting_guard`'s own contamination concern. Run
   `tests/model_right_sizer/test_tuning_knobs.py` after editing — it
   exercises every level generically, including new ones, with no changes
   needed on your part.

   **Two specific wording pitfalls this repo's own history hit, worth
   avoiding on purpose:**
   - **Enumerating named examples can narrow generalization instead of
     widening it.** A fix naming exactly two qualifying shapes with a
     concrete number improved the one unit it was diagnosed from but
     regressed two OTHER units that didn't cleanly match either named
     example — plausibly because the model read "these two shapes" as an
     exhaustive boundary, not an illustration. If citing examples, say
     explicitly that they are illustrative, not a checklist.
   - **An explicit numeric multiplier can shrink the base estimate it's
     applied to.** A fix asking the model to "apply a 1.3–1.9× multiplier"
     to its own real-work estimate scored WORSE on every single unit than a
     simpler "floor plus real work" framing with no stated multiplier —
     plausibly because naming a multiplier invites a smaller initial
     "apparent size" judgment to apply it to, netting lower than a holistic
     estimate would have. A calibration correction grounded in real
     evidence is good; making the arithmetic explicit is not automatically
     better than describing the target outcome directly.

8. **Re-render, re-dispatch (3 draws), re-score, compare.** Same task, same
   intent wording, same decomposition shape, new settings. Compare
   `accuracy_rate`/`mean_loss` against the immediately prior iteration —
   and against the ORIGINAL live-dispatch budgets recorded in the held-out
   task's own `real_outcome_doc`, since that's the number a genuinely good
   blind estimate should approach. Report every per-unit regression
   honestly even when the aggregate improves — a unit that flips from
   `within_budget` to `over_budget` is real information (about noise or
   about a real tension your change introduced), not noise to omit.

9. **Decide: iterate, adopt-and-stop, or ask for a fresh task.** Iterate
   only while each round shows real, attributable improvement. Stop and
   report honestly, without another round, when: the requested target is
   reached; two iterations in a row show no material `accuracy_rate`
   improvement; or continuing would mean a third-or-later blind pass
   against the same fixed n — at that point, say plainly that further
   squeezing this one task's data starts to look like overfitting rather
   than tuning, and that the right next move is a fresh held-out task (a
   different real build), not another wording tweak aimed at the same six
   numbers. If told explicitly to keep going anyway, that's a legitimate
   call for whoever asked to make — flag it once, then proceed.

10. **Write it up, update the registry, validate, commit.** A results file
    under `eval/tuning/results/` with every iteration's table, the
    diagnosis for each, and the final decision; a cross-reference from
    `DESIGN.md`'s "current best-known settings" line; an update to the used
    `HOLDOUT_TASKS` entry's `note` reflecting the new read count (so the
    NEXT run of this skill sees accurate contamination state, not a state
    that only lived in this session's chat transcript). Run this repo's
    full validator list from `CLAUDE.md` and the pytest suite before
    committing — this skill edits `knobs.py` (a real file), unlike its
    read-mostly sibling `model-right-sizer-prompt-tuning`.

## What this does NOT do

- It does **not** replace `model-right-sizer-prompt-tuning`'s synthetic-
  benchmark coordinate ascent — different ground truth (a real, already-
  measured build vs. `t1`–`t6`), and this skill never dispatches a fresh
  real build of its own; it only ever re-runs the (cheap) blueprint step
  against actuals someone already paid for once.
- It does **not** by itself satisfy `overfitting_guard.REQUIRED_GATE_NOTE`'s
  merge gate — that gate is about calibrated-vs-blind generalization
  specifically; this skill's every run is already blind, which is necessary
  for a clean comparison but not the same check. State both results
  side by side if this skill's output is being used to argue for a merge.
- It does **not** fabricate or estimate "real actuals" — every comparison
  is against a genuinely already-measured dispatch recorded in a held-out
  task's `real_outcome_doc`. If no such task fits the shape being tuned,
  the right move is building one for real first (see
  [`model-right-sizer-budget-guard`](../model-right-sizer-budget-guard/SKILL.md)-style
  real dispatch, or any real build), not inventing numbers here.
- It does **not** edit `agents/model-right-sizer.md` directly, and does not
  merge its own winning knob settings into the shipped file — same
  propose-a-diff-for-a-human discipline as its sibling skill.
- It does **not** silently keep iterating past the point where doing so is
  overfitting rather than tuning — see step 9.

## Related

- [`model-right-sizer-prompt-tuning`](../model-right-sizer-prompt-tuning/SKILL.md)
  — the sibling skill this one shares `knobs.py`/`optimizer.py` with; tunes
  against the synthetic benchmark instead of a real held-out build.
- [`../../eval/tuning/overfitting_guard.py`](../../eval/tuning/overfitting_guard.py)
  — `HOLDOUT_TASKS`, `assess_generalization()`, and `REQUIRED_GATE_NOTE`;
  the contamination-tracking this skill's step 1 and step 10 depend on.
- [`../../eval/tuning/knobs.py`](../../eval/tuning/knobs.py) /
  [`optimizer.py`](../../eval/tuning/optimizer.py) /
  [`generate_variant.py`](../../eval/tuning/generate_variant.py) — the
  knob registry, scoring functions, and variant renderer this skill drives.
- [`../../eval/reasoning_budget.py`](../../eval/reasoning_budget.py) —
  `budget_adherence_ratio` / `classify_budget_adherence`, the per-unit
  scoring functions.
- [`../../eval/tuning/DESIGN.md`](../../eval/tuning/DESIGN.md) — the running
  log of every tuning pass, including prior holdout-tuning rounds this
  skill's own future runs should read before re-diagnosing a known miss.
