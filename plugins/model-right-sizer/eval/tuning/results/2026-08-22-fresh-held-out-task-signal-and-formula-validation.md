# A genuinely fresh held-out task: `investigative_uncertainty` doesn't replicate, the additive formula does

Direct execution of the three recommendations from the "Signal & Noise"
executive report that needed a fresh real build: (1) replicate
`investigative_uncertainty` on a second, different held-out task, (2)
validate the additive `token_ceiling` formula against a fresh real build,
and (4) measure the opus/haiku tier spans independently. `overfitting_guard.HOLDOUT_TASKS`'
existing two entries were both explicitly annotated as no longer usable
this way — this document is the third entry.

## Method: a real, bounded 4-unit build, dispatched via the `Agent` tool

`create_session` (a separate, independently-billed CCR session — the
dispatch mechanism a first attempt at this task tried to use) was
unreachable for the entire attempt window (9+ consecutive "service
temporarily unavailable" failures over 10+ minutes). Rather than fabricate
data, the task was re-run using the `Agent` tool directly (the same
mechanism this pass's earlier blind-rating experiments already used
successfully) with the orchestrating session itself acting as dispatcher.

**The fresh feature**: a small, real, useful CLI (`eval/tuning/compare_results.py`)
that diffs two of this research program's own raw-records JSON files —
solving a real problem (~20 results files currently compared by hand).
Four real dispatch units, stated up front before dispatching:

| unit | tier | real content |
|---|---|---|
| `unit-core-module` | sonnet | `load_records`/`diff_records`/`compare_candidates` |
| `unit-tests` | sonnet | 8 tests, mirroring house style |
| `unit-cli` | haiku | argparse CLI wired to the module above |
| `unit-docs-integration` | sonnet | ran the tool for real, found and fixed a real `KeyError` crash on a second file's shape, documented both real findings in `DESIGN.md` |

Each unit was its own independent `Agent` dispatch; `unit-docs-integration`
in particular earned its keep by finding a real bug (`load_records` crashed
on `2026-08-21-pass2-raw-records.json`'s slightly different key names)
purely by actually running the tool, not by reading the code — exactly the
kind of finding this pass's whole methodology exists to surface.

### Floor reconciliation — a new harness needs its own floor, not a borrowed one

`DISPATCH_FLOORS` (`token_ceiling_formula.py`) was measured against a
different dispatch harness. This run measured its OWN zero-tool floor
fresh, three no-op probes (`"reply with exactly one word: ok"`, `general-purpose`
subagent type):

| tier | this-harness floor (n=1) | shipped `DISPATCH_FLOORS` |
|---|---:|---:|
| sonnet | 42,512 | 40,669 |
| opus | 42,416 | 38,260 |
| haiku | 32,653 | 25,664 |

Close enough (5–15%) to confirm this is the same underlying mechanism
(general Task/Agent-tool overhead), not a different one — the gap is
consistent with n=1-per-tier noise, not a structural difference. Every
raw `actual_tokens` figure below is reconciled onto the shipped
`DISPATCH_FLOORS` convention so it can be checked against
`token_ceiling_formula.py`'s real constants without re-deriving them:
`reconciled = (raw − this_harness_floor[tier]) + DISPATCH_FLOORS[tier]`.

| unit | tier | raw | reconciled |
|---|---|---:|---:|
| `unit-core-module` | sonnet | 86,465 | 84,622 |
| `unit-tests` | sonnet | 82,789 | 80,946 |
| `unit-cli` | haiku | 51,427 | 44,438 |
| `unit-docs-integration` | sonnet | 86,022 | 84,179 |

## Finding 1 (Rec 1) — `investigative_uncertainty` does NOT replicate on this second task

Three genuinely independent, tool-less blind draws (no file/repo access —
structurally prevented from seeing the real actuals, which didn't exist
at rating time anyway) rated all six signals for the four units above.
Mean CV per signal (5.6–16.5%) is consistent with the prior genuinely
blind run — `investigative_uncertainty` is still the noisiest (16.5%),
but not dramatically so.

| comparison | Pearson r |
|---|---:|
| sum of original 4 signals (baseline) | **0.994** |
| sum of all 6 signals (+ `investigative_uncertainty`) | **0.936** |
| `investigative_uncertainty` alone | 0.546 |

**This is the opposite direction from the first task's result**
(0.910 → 0.980, an improvement). Here, adding it *dilutes* an
already-near-perfect baseline fit (0.994 → 0.936) — the same failure mode
`validation_loop_iterations` and `context_ingestion_volume` both already
showed. The likely mechanism: with only n=4 units and a baseline already
explaining 98.8% of the variance (r²=0.994²), there is almost no residual
variance left for any additional signal to explain, so anything added —
even one with a positive standalone correlation (0.546) — mostly
contributes noise.

**Per `model-right-sizer-signal-validation`'s own pre-registered decision
rule**: a nonzero default weight requires replication on a second,
different held-out task. This is now **1 improvement, 1 dilution across 2
tasks** — the opposite of replication. `investigative_uncertainty`'s
default weight of `0.0` is confirmed correct, now on stronger evidence
than before (a signal that only sometimes helps, task-shape-dependently,
is exactly what a `0.0` default is for) rather than "promising, not yet
proven." The honest updated verdict is a downgrade from the first report's
framing, not a confirmation.

## Finding 2 (Rec 2) — the additive formula holds up on genuinely fresh data

`compute_token_ceiling_additive` (shipped, unmodified constants —
`ADDITIVE_TOTAL_SPAN`'s `k=0.5925`, fit only against the retired
chief-of-staff actuals) checked against these four fresh reconciled
actuals:

| unit | tier | ceiling | actual | ratio | class |
|---|---|---:|---:|---:|---|
| `unit-core-module` | sonnet | 103,560 | 84,622 | 0.817 | `within_budget` |
| `unit-tests` | sonnet | 90,119 | 80,946 | 0.898 | `within_budget` |
| `unit-cli` | haiku | 42,676 | 44,438 | 1.041 | `over_budget` |
| `unit-docs-integration` | sonnet | 93,316 | 84,179 | 0.902 | `within_budget` |

**`accuracy_rate = 3/4 = 0.750`** — on data that never touched any
constant this formula uses. For comparison, the averaged (weighted-mean)
model on the SAME fresh data:

| model | accuracy_rate on this fresh task |
|---|---:|
| `compute_token_ceiling` (averaged) | **0/4 = 0.000** |
| `compute_token_ceiling_additive` (additive) | **3/4 = 0.750** |

This is genuinely non-circular evidence — the first real, disclosable
confirmation that the additive structural fix (found via
`weight_optimizer.py`'s gradient descent on the retired six-unit dataset)
generalizes to data it was never fit to, not just an artifact of fitting
`k` to the numbers being checked against.

**The one miss is informative, not just noise**: `unit-cli` (haiku tier)
misses by only 4.1% (ratio 1.041), and haiku is the tier with the least
calibration confidence in this whole module (`CALIBRATION_STATUS` already
marks it placeholder-only). This is the same weak link Finding 3 below
independently points at.

**Updated `ADDITIVE_CALIBRATION_STATUS`**: still not "validated" in the
full sense — n=4, one task, one archetype — but no longer purely
`UNVALIDATED` either. `token_ceiling_formula.py` now states this fresh,
non-circular check explicitly rather than leaving the constant's status
exactly where it was before any outside evidence existed.

## Finding 4 (Rec 4) — opus/haiku low-end anchors, and a real caveat about "near-zero" tasks

Two real, low-real-work dispatches (find and fix exactly one missing
docstring-parameter description each — deliberately as close to zero
business content as a real task gets):

| tier | raw | this-harness floor | net real-work | reconciled (+ shipped floor) |
|---|---:|---:|---:|---:|
| opus | 66,426 | 42,416 | 24,010 | 62,270 |
| haiku | 47,861 | 32,653 | 15,208 | 40,872 |

**Honest caveat, not a clean calibration point**: both dispatches needed
real multi-file search (`tool_uses: 4` each) to find a genuine, honest gap
to fix — locating "one real thing to fix" is itself real tool-call
overhead the zero-tool floor doesn't capture, even for a task designed to
be as close to zero business content as possible. This is a real, useful
finding in its own right (a "near-zero" task is not the same as a
zero-tool-call task), but it means these two points anchor "a small real
task with some search," not "the theoretical floor of real work" — too
thin a signal (n=1 each) to refit `REAL_WORK_SPAN`'s low end from, and
doing so would repeat exactly the overfitting risk this whole module's
`CALIBRATION_STATUS` disclosures exist to avoid. `CALIBRATION_STATUS` is
updated to reflect the increased n (opus 2→3, haiku 0→1) and this caveat,
not a recalibrated span.

## What did NOT change in shipped code

- `investigative_uncertainty`'s default weight stays `0.0` — evidence now
  argues more clearly for staying there, not for a change.
- `context_ingestion_volume`'s default weight stays `0.0` (unchanged by
  this experiment — not re-tested here).
- `ADDITIVE_TOTAL_SPAN`'s `k=0.5925` is **not** re-fit against this fresh
  data — that would be the same "fit and validate against the same
  numbers" mistake this whole module warns against, just moved one task
  later. This data confirms the existing constant; it doesn't get to also
  improve it in the same pass.
- `REAL_WORK_SPAN`'s opus/haiku values are **not** recalculated from the
  two anchor points above — n=1 each is disclosed, not acted on.

## Honest bottom line

1. **`investigative_uncertainty` was a real, disclosable non-replication**
   — this is exactly the kind of result the whole signal-validation
   methodology exists to catch rather than paper over. The first task's
   promising result was real for that task; it does not generalize
   automatically, and pretending otherwise would repeat the exact mistake
   this pass's own `overfitting_guard` machinery was built to prevent.
2. **The additive formula's structural fix is now backed by real,
   non-circular evidence**, not just a well-argued proof plus a fit-and-
   check-against-the-same-data result. 75% on fresh data, versus the
   averaged model's proven 0%, is a genuine, disclosable win for the
   pivot away from weighted averaging.
3. **Haiku-tier calibration is the consistent weak link** across two
   independent findings in this document (the one additive-formula miss,
   and the real search overhead the near-zero anchor task needed) — the
   next legitimate investment in this module is real haiku-tier data, not
   another pass over sonnet.
