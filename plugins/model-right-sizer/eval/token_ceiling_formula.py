#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic `token_ceiling` computation from bounded [0.0, 1.0] signals,
instead of asking an LLM to free-hand a raw integer.

**Versioned as of 2026-08-22** -- see `FORMULA_VERSION` below and
`tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md` for
v1.0.0's exact published configuration, plus a ranked list of gaps and
opportunities for whoever picks this up next (haiku-tier calibration is
the single highest-value next experiment).

## Why this exists

`eval/tuning/`'s holdout-tuning passes (see
`tuning/results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`)
repeatedly found that asking a dry-run to state `token_ceiling` directly
carries real, large run-to-run noise -- per-unit standard deviations of
10-30% of the mean across three otherwise-identical blind draws, large
enough to flip `within_budget`/`over_budget` classifications outright and
to make a reported wording "improvement" evaporate on re-measurement. Two
deliberate attempts to fix this by adjusting the WORDING the LLM reasons
from (naming concrete examples; naming an explicit multiplier) both made
things worse, not better -- see that same results file's iterations 3 and
5.

The schema already has a field shape that does NOT show this noise
problem: `blueprint_rows[].signals.effectiveness/efficiency/difficulty` are
bounded 0-100 scores with a one-clause reason each, and nothing in this
project's tuning history has found THOSE scores to be unreliable the way
raw `token_ceiling` integers are. The hypothesis this module tests: move
`token_ceiling` from "the LLM invents a raw integer" to "the LLM rates
three bounded [0.0, 1.0] signals (the same kind of judgment call it
already makes reliably elsewhere), and CODE computes the integer" --
removing free-hand arithmetic and content-size guessing from the LLM's job
entirely, the same way `budget_threshold.py` moved the threshold-crossing
CHECK out of the LLM's job and into deterministic code.

## The six input signals

- `tool_call_volume` — how many real tool calls (search, edit, re-run a
  validator, re-run tests) this unit will plausibly make. 0.0 = a single
  content-only turn with no tool calls; 1.0 = many rounds of tool use.
- `content_volume` — how much original content (prose, code) this unit
  will actually produce. 0.0 = a one-line change; 1.0 = several hundred
  lines/words of new original material.
- `cross_reference_load` — how many OTHER already-landed artifacts this
  unit must read and stay consistent with (a shared schema, a sibling
  module's exact function signature, another section's exact wording) as
  opposed to working in isolation. 0.0 = a standalone new file with nothing
  to reconcile against; 1.0 = must read and stay faithful to several other
  artifacts at once.
- `validation_loop_iterations` — how many real re-run-and-fix cycles
  against a validator or test suite this unit specifically requires,
  distinct from `tool_call_volume`'s broader notion of any tool use. 0.0 =
  nothing to validate work against (no CI gate, no schema, no test file
  covering it); 1.0 = a mandatory validate-then-fix loop expected to take
  several iterations to converge. Added 2026-08-22 (see
  `tuning/results/2026-08-22-additive-formula-and-signal-expansion.md`'s
  proposed candidates) — every one of the five under-estimated real units
  in this pass's own training data was gated behind a real validate-then-
  fix loop; the one correctly-estimated unit had none. **Defaults to
  weight `0.0` in `compute_token_ceiling_additive`, and a fresh 3-draw
  rating experiment confirms that default is correct, not just cautious**
  — see `tuning/results/2026-08-22-validation-loop-iterations-signal.md`.
  That experiment found `validation_loop_iterations` runs ~2.5x noisier
  than the other three signals (mean CV 25.8% vs. 9.7-10.6%), correlates
  weakly with real cost alone (r=0.344), and DILUTES the existing signal
  sum's correlation when added at equal weight (0.910 → 0.865) — it
  correctly flags 2 of the 6 real training units (a schema/changelog
  validator, a test suite's fix loop) but the other 4 are expensive for
  reasons this signal doesn't capture, so it adds noise more often than it
  adds explanatory power. Do not give it a nonzero default weight without
  new evidence.
- `context_ingestion_volume` — how much *pre-existing* material (a file, a
  diff, a prior handoff) this unit must read and hold in context before
  producing anything, independent of whether it must stay *consistent*
  with that material. 0.0 = works from a short prompt with no meaningful
  pre-existing material to ingest; 1.0 = must read and hold a large body
  of existing content before acting at all. Distinct from
  `cross_reference_load`: that signal asks whether the OUTPUT must stay
  faithful to other artifacts; this one asks how much must be READ first,
  full stop -- a review unit reading a 2,000-line diff to write a 10-line
  verdict scores high here and near-zero on `cross_reference_load` (there
  is nothing downstream to stay consistent with). Added 2026-08-22 from
  the archetype breakdown in
  `tuning/results/2026-08-22-signal-candidates-by-subagent-archetype.md`,
  most load-bearing for review/QA units and build units editing inside
  large pre-existing files. **Defaults to weight `0.0`** -- unlike
  `validation_loop_iterations`, this signal has not yet been TESTED at
  all (no rating experiment run against it), so the zero default reflects
  "unproven," not "tested and found wanting" -- don't conflate the two
  when reading this module's calibration status.
- `investigative_uncertainty` — whether this unit's tool-call sequence is
  searching for something whose existence or shape isn't known going in
  (open-ended research, "does X exist -- if so, what shape") vs. executing
  an already-fully-specified sequence of calls. 0.0 = every tool call's
  target is already known before dispatch; 1.0 = genuinely open-ended
  search where most calls are exploratory and some will be dead ends.
  Distinct from `tool_call_volume`: that signal scores HOW MANY calls;
  this scores how likely each call is to be a productive step vs. a dead
  end -- two finder units can share a `tool_call_volume` rating while one
  converges exactly on target and the other burns half its calls on blind
  alleys. Added 2026-08-22 alongside `context_ingestion_volume`, most
  load-bearing for finder/discovery units and the exploratory phase of
  synthesis/judge units. **Defaults to weight `0.0`**, likewise unproven
  rather than tested-and-rejected.

These map directly onto the causal drivers `dispatch_floor_awareness`
(see `tuning/knobs.py`) named from real-dispatch evidence but could only
ever gesture at in prose: tool-call count, content-generation volume,
cross-referencing several already-landed artifacts, and a mandatory
validate-then-fix loop specifically.

## Calibration status per tier — stated honestly, not uniformly

`REAL_WORK_SPAN`'s sonnet value is fit to n=4 real sonnet-tier dispatches
from one real build (`tuning/results/2026-08-22-chief-of-staff-budget-guard-build.md`):
module (56,932), schema (76,292), tests (99,532), skill (104,219), net of
the independently-measured sonnet zero-tool floor (40,669). Backing out the
scale each actual implies from `(actual - floor) / span` with span=65,000
reproduces all four points closely (0.25, 0.55, 0.91, 0.98) -- but this is
n=4, one build, one task-shape; it is a working calibration, not a proven
constant. Opus has only n=2 real dispatches, both clustered at the
agentic/high-cross-reference end (57,185 and 54,114 net of the n=1-measured
opus floor of 38,260) -- there is no real data anchoring the LOW end of
opus's span, so `REAL_WORK_SPAN["claude-opus-4-8"]` is a PLACEHOLDER
(scaled proportionally from sonnet's measured span by the floor ratio),
explicitly flagged as such below, not a second real calibration. Haiku has
zero real per-unit dispatches from this task and is placeholder-only.
Do not treat the opus/haiku spans as validated until real low-scale
dispatches exist for those tiers.

## First validation result (2026-08-22)

Three blind draws asking an LLM to rate the three signals (not a raw
token count) for the same six real chief-of-staff units found: (1) signal
rating carries real but MODEST noise reduction vs. raw token estimates --
mean CV 12.9% vs. the 10-30% this project's wording-tuning passes found for
raw integers, at the low end of that range, not a dramatic collapse; (2)
the formula, fed the averaged signals with ZERO tuning, matched the best
wording-tuned knob level's `accuracy_rate` (0.167) on its first attempt;
(3) 5 of 6 units missed high but TIGHTLY clustered at ratio 1.21-1.32,
consistent with `REAL_WORK_SPAN` being uniformly a bit small rather than
per-unit ratings being wrong -- a real, disclosable hypothesis for the next
fix, NOT yet acted on here (recalibrating against these same six retired
numbers a second time would be re-fitting to the same fixed dataset, not
validating against anything new). See
`tuning/results/2026-08-22-signal-rating-formula-validation.md` for the
full data. Next real step: a fresh held-out task's real actuals, not
another pass over this one.
"""
from __future__ import annotations

__all__ = [
    "FORMULA_VERSION",
    "DISPATCH_FLOORS",
    "REAL_WORK_SPAN",
    "CALIBRATION_STATUS",
    "compute_real_work_scale",
    "compute_token_ceiling",
    "ADDITIVE_TOTAL_SPAN",
    "ADDITIVE_CALIBRATION_STATUS",
    "compute_real_work_additive",
    "compute_token_ceiling_additive",
    "AGENT_TOOL_HARNESS_FLOORS",
    "rebase_onto_canonical_floor",
]

# This module's own version, independent of the plugin-wide version in
# `.claude-plugin/plugin.json` and of each skill's own `version:` frontmatter
# -- this one tracks changes to the SIGNAL SET and CALIBRATION CONSTANTS
# specifically (which signals exist, their default weights, DISPATCH_FLOORS/
# REAL_WORK_SPAN/ADDITIVE_TOTAL_SPAN's actual numbers), since those are what
# a future contributor needs to know changed, separately from prose/wording
# changes elsewhere in this file. Bump policy: PATCH for a calibration
# constant re-measured with more data but no shape change (e.g. a
# CALIBRATION_STATUS n-count going up); MINOR for a signal's default weight
# changing, or a new signal added at weight 0.0; MAJOR for a signal being
# removed, an existing nonzero weight changing what it multiplies, or the
# preferred formula (`compute_token_ceiling_additive` vs.
# `compute_token_ceiling`) switching. Full rationale for each version lives
# in a dated `tuning/results/*-release.md` file, not just in this comment --
# see `tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md`
# for v1.0.0's own.
#
# v1.0.0 -> v1.1.0 (this bump): closes gap #6 of that same v1.0.0 release
# report (the two-harness floor reconciliation) by adding
# `AGENT_TOOL_HARNESS_FLOORS` and `rebase_onto_canonical_floor`. None of the
# three bump-policy bullets above names "new utility function/constant"
# directly -- this isn't a recalibration of an existing constant (not
# PATCH), doesn't touch any signal or its weight (not the MINOR case as
# literally written), and removes nothing, changes no existing nonzero
# weight's meaning, and switches no preferred formula (not MAJOR). Treated
# as MINOR by the same semver spirit the MINOR bullet already applies to
# "a new signal added at weight 0.0": purely additive, backward-compatible
# surface area with zero effect on any existing constant or function's
# output -- `DISPATCH_FLOORS`, `REAL_WORK_SPAN`, `ADDITIVE_TOTAL_SPAN`, and
# every existing function's behavior are byte-for-byte unchanged.
FORMULA_VERSION = "1.0.0"

# Zero-tool-call dispatch floors, per model tier -- see
# `tuning/DESIGN.md`'s "Measurement redesign" section (haiku, sonnet: 5 and
# 2 probes respectively, both near-deterministic) and
# `tuning/results/2026-08-21-pass1.md` (opus: a single no-op control
# dispatch, n=1 -- least certain of the three).
DISPATCH_FLOORS = {
    "claude-haiku-4-5": 25_664,
    "claude-sonnet-5": 40_669,
    "claude-opus-4-8": 38_260,
}

# A SECOND, independent zero-tool-call floor measurement, taken on the
# `Agent`-tool dispatch harness (three no-op probes, n=1-per-tier) during
# the fresh-held-out-task pass -- see
# `tuning/results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`'s
# "Floor reconciliation" section and gap #6 of
# `tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md`. NOT a
# replacement for `DISPATCH_FLOORS` -- it exists only so `rebase_onto_canonical_floor`
# below can translate a raw actual measured on THIS harness onto the
# canonical `DISPATCH_FLOORS` frame for comparison.
AGENT_TOOL_HARNESS_FLOORS = {
    "claude-haiku-4-5": 32_653,
    "claude-sonnet-5": 42_512,
    "claude-opus-4-8": 42_416,
}

# The additional real-work token range a scale of 0.0 -> 1.0 spans, on top
# of that tier's dispatch floor. Only sonnet's is a real, if small-n (n=4,
# one build), calibration. Opus's and haiku's are PLACEHOLDERS scaled
# proportionally from sonnet's by the floor ratio, not independent
# calibrations -- see `CALIBRATION_STATUS` for which is which.
REAL_WORK_SPAN = {
    "claude-sonnet-5": 65_000,
    "claude-opus-4-8": 65_000 * (DISPATCH_FLOORS["claude-opus-4-8"] / DISPATCH_FLOORS["claude-sonnet-5"]),
    "claude-haiku-4-5": 65_000 * (DISPATCH_FLOORS["claude-haiku-4-5"] / DISPATCH_FLOORS["claude-sonnet-5"]),
}

# Machine-readable so a caller (or a test) can assert on calibration
# confidence rather than just trusting a docstring. "measured": fit to real
# per-unit dispatch data with a low/high spread. "placeholder": scaled by
# analogy from another tier's measured span, not independently fit.
CALIBRATION_STATUS = {
    "claude-sonnet-5": "measured (n=4, one build, low/high spread 0.25-0.98)",
    "claude-opus-4-8": (
        "placeholder (n=3 real points as of 2026-08-22 -- 2 clustered high, "
        "1 fresh low-real-work anchor at net 24,010 tokens; still no clean "
        "low-end anchor, since that anchor point needed real multi-file "
        "search to even find its own tiny edit, so it's not a pure zero-"
        "work sample either -- see tuning/results/2026-08-22-fresh-held-out-"
        "task-signal-and-formula-validation.md; scaled from sonnet's span "
        "by floor ratio, not independently fit)"
    ),
    "claude-haiku-4-5": (
        "placeholder (n=1 real per-unit dispatch as of 2026-08-22 -- a "
        "fresh low-real-work anchor at net 15,208 tokens, same "
        "search-overhead caveat as opus's; see tuning/results/2026-08-22-"
        "fresh-held-out-task-signal-and-formula-validation.md; scaled from "
        "sonnet's span by floor ratio, not independently fit). This is "
        "also the tier that missed compute_token_ceiling_additive's one "
        "fresh-task classification (ratio 1.041, over_budget by 4.1%) -- "
        "the consistent weak link across this pass's real evidence, not "
        "yet enough to recalibrate from."
    ),
}


# Canonical signal order shared by every function below -- a single place
# to add a 7th signal later instead of six call sites drifting out of sync.
SIGNAL_NAMES = (
    "tool_call_volume",
    "content_volume",
    "cross_reference_load",
    "validation_loop_iterations",
    "context_ingestion_volume",
    "investigative_uncertainty",
)


def compute_real_work_scale(
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    validation_loop_iterations: float = 0.0,
    context_ingestion_volume: float = 0.0,
    investigative_uncertainty: float = 0.0,
    *,
    weights: tuple[float, float, float, float, float, float] = (1 / 3, 1 / 3, 1 / 3, 0.0, 0.0, 0.0),
) -> float:
    """Combine the six bounded signals into one [0.0, 1.0] real-work scale
    via a weighted average. Each input and each weight-adjusted combination
    is validated to stay in [0.0, 1.0] -- callers should adjust `weights`
    only with a stated reason (e.g. a task-shape where cross-referencing
    dominates), never silently. The last three signals default to `0.0`
    (both value and weight) so an existing caller passing only the first
    three or four positional args keeps its prior behavior exactly --
    `context_ingestion_volume` and `investigative_uncertainty` are UNTESTED
    candidates (see this module's docstring), not yet earning a nonzero
    default weight the way `validation_loop_iterations` was tested and
    rejected for one."""
    signals = (
        tool_call_volume,
        content_volume,
        cross_reference_load,
        validation_loop_iterations,
        context_ingestion_volume,
        investigative_uncertainty,
    )
    for name, value in zip(SIGNAL_NAMES, signals):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
    if len(weights) != 6:
        raise ValueError(f"weights must have exactly 6 entries, got {len(weights)}")
    if any(w < 0 for w in weights):
        raise ValueError(f"weights must be non-negative, got {weights!r}")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must not all be zero")
    scale = sum(s * w for s, w in zip(signals, weights)) / total_weight
    # Guard against float drift pushing a legitimate boundary case (e.g.
    # every input and weight at 1.0) a hair outside [0.0, 1.0].
    return min(1.0, max(0.0, scale))


def compute_token_ceiling(
    tier: str,
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    validation_loop_iterations: float = 0.0,
    context_ingestion_volume: float = 0.0,
    investigative_uncertainty: float = 0.0,
    *,
    weights: tuple[float, float, float, float, float, float] = (1 / 3, 1 / 3, 1 / 3, 0.0, 0.0, 0.0),
) -> int:
    """`token_ceiling = dispatch_floor(tier) + real_work_span(tier) *
    real_work_scale`. The one function a blueprint's Pass A budget bullet
    should call instead of free-handing an integer -- see this module's
    docstring for why, and `CALIBRATION_STATUS[tier]` for how much to trust
    the result on a given tier. A row with `token_ceiling: 0` (a
    deterministic-query-layer row, per the shipped agent's own convention)
    is never computed by this function -- that's a `model: "deterministic_query_layer"`
    row's own explicit zero, set directly, not derived from a scale."""
    if tier not in DISPATCH_FLOORS:
        raise ValueError(f"Unknown tier {tier!r} -- must be one of {sorted(DISPATCH_FLOORS)}")
    scale = compute_real_work_scale(
        tool_call_volume,
        content_volume,
        cross_reference_load,
        validation_loop_iterations,
        context_ingestion_volume,
        investigative_uncertainty,
        weights=weights,
    )
    return round(DISPATCH_FLOORS[tier] + REAL_WORK_SPAN[tier] * scale)


# ---------------------------------------------------------------------------
# The additive alternative -- found while gradient-descending the weights
# above, not by adding a fourth signal
# ---------------------------------------------------------------------------
# `compute_real_work_scale`'s weighted AVERAGE has a hard capacity ceiling:
# it can never predict a scale above `max(tool_call_volume, content_volume,
# cross_reference_load)` for a given example (see `tuning/weight_optimizer.py`'s
# docstring and `tuning/results/2026-08-22-weight-gradient-descent.md`).
# Gradient-descending the SAME three signals with the normalization removed
# -- a genuine linear regression, `w0*a + w1*b + w2*c`, no longer bounded to
# [0, 1] -- reached 94% training accuracy on the same 18-row dataset,
# without a single new signal. A follow-up check with just ONE shared scalar
# (`k*(a+b+c)`, zero per-signal weight learning at all) reached the
# IDENTICAL accuracy -- proof the three-weight fit above was really one
# effective degree of freedom (a global scale correction) in a three-
# parameter costume, not genuine per-signal learning. See
# `tuning/results/2026-08-22-additive-formula-and-signal-expansion.md` for
# the full derivation.
#
# ADDITIVE_TOTAL_SPAN is that single scalar (k=0.5925, fit via gradient
# descent on the same 18 rows) times the averaged model's own span --
# TRAINED ON THE SAME RETIRED SIX REAL ACTUALS THIS WHOLE MODULE ALREADY
# DISCLOSES AS n=4/n=2/n=0 BY TIER. This is a second fit against the same
# fixed dataset, not independent validation. Treat `compute_token_ceiling_additive`
# as an unvalidated candidate structural fix, not a proven replacement, until
# a fresh held-out task's real actuals confirm it.
ADDITIVE_TOTAL_SPAN = {tier: span * 0.5925 for tier, span in REAL_WORK_SPAN.items()}

ADDITIVE_CALIBRATION_STATUS = (
    "PARTIALLY CONFIRMED, still not fully validated -- k=0.5925 was fit by "
    "gradient descent against the retired 18-row / 6-real-unit dataset "
    "REAL_WORK_SPAN was already fit to (94% TRAINING accuracy on that same "
    "data -- with only 6 independent real targets and one effective fitted "
    "parameter, that alone was a strong overfitting signal, not evidence of "
    "a working general formula; see tuning/results/2026-08-22-weight-"
    "gradient-descent.md and -additive-formula-and-signal-expansion.md). "
    "As of 2026-08-22, a SECOND, genuinely fresh held-out task (4 real "
    "units, never used to fit k or any other constant here) checked the "
    "UNCHANGED shipped constants and got accuracy_rate=3/4=0.750 -- vs. the "
    "averaged model's 0/4=0.000 on the identical fresh data. That is real, "
    "non-circular evidence the structural fix generalizes, not just an "
    "artifact of fitting k to the numbers being checked against. Still not "
    "'validated' in the full sense -- n=4, one task, one archetype, and the "
    "one miss was haiku tier (the least-calibrated tier already flagged in "
    "CALIBRATION_STATUS) -- see tuning/results/2026-08-22-fresh-held-out-"
    "task-signal-and-formula-validation.md. Do not re-fit k against either "
    "dataset again; the next legitimate step is a THIRD held-out task, "
    "ideally one that can also anchor haiku's calibration."
)


def compute_real_work_additive(
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    validation_loop_iterations: float = 0.0,
    context_ingestion_volume: float = 0.0,
    investigative_uncertainty: float = 0.0,
    *,
    weights: tuple[float, float, float, float, float, float] = (1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
) -> float:
    """Sum (not average) of the six weighted signals -- deliberately NOT
    bounded to [0.0, 1.0]; ranges from 0 to `sum(weights)`. This is the
    structural fix `compute_real_work_scale`'s normalization was missing:
    real work costs from independent axes (tool calls, content, cross-
    referencing, validation iterations, context ingestion, investigative
    uncertainty) are additive, not a severity rating to average. The last
    three signals' default WEIGHT is `0.0`, not `1.0` like the first three
    -- `ADDITIVE_TOTAL_SPAN` was fit before any of them existed, so giving
    one a nonzero default would silently shift every existing prediction
    with no data behind the shift. `validation_loop_iterations` earned its
    zero through an actual experiment that found it dilutes rather than
    helps (see `tuning/results/2026-08-22-validation-loop-iterations-signal.md`);
    `context_ingestion_volume` and `investigative_uncertainty` are simply
    UNTESTED -- their zero is "unproven," not "tested and rejected." See
    this module's `ADDITIVE_CALIBRATION_STATUS` before trusting any result
    at all, and don't give any of the last three signals a nonzero default
    weight without a dedicated rating experiment first."""
    signals = (
        tool_call_volume,
        content_volume,
        cross_reference_load,
        validation_loop_iterations,
        context_ingestion_volume,
        investigative_uncertainty,
    )
    for name, value in zip(SIGNAL_NAMES, signals):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0.0, 1.0], got {value!r}")
    if len(weights) != 6:
        raise ValueError(f"weights must have exactly 6 entries, got {len(weights)}")
    if any(w < 0 for w in weights):
        raise ValueError(f"weights must be non-negative, got {weights!r}")
    return sum(s * w for s, w in zip(signals, weights))


def compute_token_ceiling_additive(
    tier: str,
    tool_call_volume: float,
    content_volume: float,
    cross_reference_load: float,
    validation_loop_iterations: float = 0.0,
    context_ingestion_volume: float = 0.0,
    investigative_uncertainty: float = 0.0,
    *,
    weights: tuple[float, float, float, float, float, float] = (1.0, 1.0, 1.0, 0.0, 0.0, 0.0),
) -> int:
    """`token_ceiling = dispatch_floor(tier) + additive_total_span(tier) *
    (sum of the six weighted signals)`. UNVALIDATED -- see
    `ADDITIVE_CALIBRATION_STATUS`. Provided as a tested candidate, not a
    recommendation to switch `compute_token_ceiling` over to this today."""
    if tier not in DISPATCH_FLOORS:
        raise ValueError(f"Unknown tier {tier!r} -- must be one of {sorted(DISPATCH_FLOORS)}")
    real_work = compute_real_work_additive(
        tool_call_volume,
        content_volume,
        cross_reference_load,
        validation_loop_iterations,
        context_ingestion_volume,
        investigative_uncertainty,
        weights=weights,
    )
    return round(DISPATCH_FLOORS[tier] + ADDITIVE_TOTAL_SPAN[tier] * real_work)


# ---------------------------------------------------------------------------
# Two-harness floor reconciliation (closes gap #6 of
# `tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md`)
# ---------------------------------------------------------------------------
def rebase_onto_canonical_floor(
    raw_actual: int,
    tier: str,
    foreign_harness_floors: dict[str, int],
) -> int:
    """Re-base a raw actual token count, measured on some OTHER dispatch
    harness than the one `DISPATCH_FLOORS` was measured on, onto
    `DISPATCH_FLOORS`'s frame -- replacing the ad hoc by-hand arithmetic
    (`reconciled = (raw - this_harness_floor[tier]) + DISPATCH_FLOORS[tier]`)
    that
    `tuning/results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`'s
    "Floor reconciliation" section performed manually for four real units.

    Args:
        raw_actual: the real token count as measured on the FOREIGN harness
            (e.g. a unit dispatched via the `Agent` tool).
        tier: one of `DISPATCH_FLOORS`' keys.
        foreign_harness_floors: that OTHER harness's own per-tier zero-tool
            floor measurement -- e.g. `AGENT_TOOL_HARNESS_FLOORS` -- i.e.
            the floor `raw_actual` was actually measured against, NOT
            `DISPATCH_FLOORS` itself. Passing `DISPATCH_FLOORS` here (there
            is nothing foreign to reconcile) raises `ValueError`.

    Design decision, already made -- see gap #6 of
    `tuning/results/2026-08-22-token-ceiling-formula-v1.0.0-release.md` --
    state it, don't re-litigate it here: this function adopts
    CANONICAL-FRAME RE-BASING (translate the foreign actual onto
    `DISPATCH_FLOORS`), NOT mean-of-both-floors and NOT max-of-both-floors.
    `DISPATCH_FLOORS` is the frame `REAL_WORK_SPAN` and `ADDITIVE_TOTAL_SPAN`
    are already fit against -- averaging or maxing the two floor sets would
    silently shift what every existing prediction from those spans means,
    with no new calibration evidence behind the shift. If the canonical
    frame itself ever needs to move, that is a re-fit of `DISPATCH_FLOORS`
    (and everything fit against it), which is a different, much larger
    undertaking than this function performs.

    IMPORTANT: the return value is a REBASED ACTUAL, useful only for
    comparing one already-measured raw number against the canonical frame
    (e.g. checking it against `compute_token_ceiling_additive`'s output for
    that same unit). It is NOT itself a new dispatch floor, and must never
    be fed back into `DISPATCH_FLOORS`, `REAL_WORK_SPAN`, or
    `ADDITIVE_TOTAL_SPAN` as a drop-in replacement calibration constant --
    that would require an actual re-fit against real evidence, not a
    one-line translation of a single already-measured actual.
    """
    if tier not in DISPATCH_FLOORS:
        raise ValueError(f"Unknown tier {tier!r} -- must be one of {sorted(DISPATCH_FLOORS)}")
    if foreign_harness_floors is DISPATCH_FLOORS:
        raise ValueError(
            "foreign_harness_floors must be a DIFFERENT harness's floor set -- "
            "DISPATCH_FLOORS is already the canonical frame, so there is nothing to reconcile"
        )
    if tier not in foreign_harness_floors:
        raise ValueError(f"foreign_harness_floors is missing tier {tier!r}")
    return round(raw_actual - foreign_harness_floors[tier] + DISPATCH_FLOORS[tier])
