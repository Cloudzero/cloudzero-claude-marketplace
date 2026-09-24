# Pass 6 — `dispatch_floor_awareness`, and the first real use of the overfitting gate

Motivated by a dedicated research pass on best practices for composing an agent
instruction `.md` file, then a gap analysis against the shipped
`agents/model-right-sizer.md`. Its top finding: Pass A's budget bullet demands
`token_ceiling` be "an actual integer... not a vibe" but gives no method for
deriving that integer — no concept of a real `Task`-tool dispatch's near-fixed
overhead floor, and no instruction to scale the estimate by expected tool-call
count or generated-content volume. That is a close causal match for the ~2.8x
`over_budget` miss recorded in
[`2026-08-22-novel-use-case-validation.md`](2026-08-22-novel-use-case-validation.md).

Added a 6th knob, `dispatch_floor_awareness` (`knobs.py`): level 0 unmodified,
level 1 names the real dispatch floor, level 2 adds explicit tool-call-count /
content-volume scaling with a worked example.

## An important semantic shift — read the comparison basis carefully

The old wording (level 0) never mentions a dispatch floor, so its
`token_ceiling` was always, implicitly, a **floor-exclusive** "expected real
work" estimate — which is why the original validation compared it against
**net** actual spend (raw minus the sonnet zero-tool floor of 40,669):
`42,046 / 15,000 = 2.803`, `over_budget`.

`dispatch_floor_awareness`'s new wording explicitly instructs `token_ceiling =
floor + expected_real_work` — i.e. **floor-inclusive**. Comparing a
floor-inclusive ceiling against net (floor-excluded) actual would double-count
the floor subtraction and understate how tight the new ceiling really is. The
correct comparison for every result in this pass is against **raw** actual
spend (82,715), not net.

## Result 1 — calibrated dry-run (ledger access allowed)

Rendered `budget_margin=-1, effort_tax=1, calibration_aggressiveness=1,
calibration_decay=0, pass_b_feedback=1, dispatch_floor_awareness=2` and
dry-ran it against the same repo-slack-channel intent used in the original
validation. Result: `unit-channel-setup`'s `token_ceiling` came back as
**100,000** — but its own `uncertainty_ledger.calibration.notes` showed it had
found and read `2026-08-22-novel-use-case-validation.md` (this exact task's
real prior outcome) and padded above the 82,715 it read there.

```
raw=82,715  ceiling=100,000  ratio=0.827  class=within_budget
```

**This alone is not evidence the wording generalizes.** Pass A item 8 ("if a
calibration history exists... read it before you finalize picks") is always
active in the shipped file — any dry-run against a task whose real outcome is
already written up somewhere readable will find it and can simply pad above
the known answer. That is calibration working as designed, not proof
`dispatch_floor_awareness`'s prose does the job on its own.

## Result 2 — blind dry-run (calibration ledger access explicitly withheld)

Re-ran the identical settings, this time instructing the dispatched agent not
to read anything under `eval/tuning/results/` or `eval/ablation/results/` and
to set `calibration.ledger_found: false`. Its blueprint decomposed the work
differently from what was actually built and measured — it split channel
**discovery** (haiku, 30,000) from **provisioning + intro/canvas drafting**
(sonnet, agentic, 75,000) into two rows, where the original real dispatch did
both in one combined sonnet call.

That decomposition difference makes the comparison genuinely ambiguous, and
it's reported both ways rather than picking the flattering one:

| reading | ceiling used | ratio | class |
|---|---:|---:|---|
| sum of both rows (same total scope as what was measured) | 105,000 | 0.788 | `within_budget` |
| the closest single row alone (provision+intro) | 75,000 | 1.103 | `over_budget` (barely — ~10%, not ~180%) |

Feeding both into `overfitting_guard.assess_generalization()` against the
calibrated result (`within_budget`):

- Sum reading → **`genuine_win`**.
- Stage-2-only reading → **`calibration_masked`**.

## Honest conclusion — real improvement, not a clean proof

Whichever reading you take, `dispatch_floor_awareness` moved the estimate by
roughly two orders of magnitude of error down to near the `within_budget`
boundary — from a baseline that would have scored `over_budget` at ratio 5.51
against this task's raw actual (`82,715 / 15,000`, wildly worse once you use
the comparison basis the *old* wording actually implied it needed to clear)
down to a blind estimate that is either cleanly within budget or only ~10%
over, depending on decomposition. That is a genuine, large, disclosable
improvement in the right direction. It is **not** a clean, unambiguous proof
of generalization: the ambiguity comes from the blind run choosing a different
task decomposition than the one that was actually measured, not from a flaw in
either dry-run's reasoning.

Two honest follow-ups, not pursued in this pass:
1. The held-out pool (`overfitting_guard.HOLDOUT_TASKS`) has now had its one
   entry's real outcome dry-run against twice (calibrated and blind) — per
   the module's own note on that entry, a genuinely fresh held-out task
   should be added before leaning on this one again for a clean blind check.
2. A task simple/atomic enough that decomposition choice can't create this
   kind of ambiguity (e.g. a single bounded build unit, not a multi-stage
   skill) would make the blind-vs-calibrated comparison unambiguous next time.

## Current best-known settings

`budget_margin=-1, effort_tax=1, calibration_aggressiveness=1,
calibration_decay=0, pass_b_feedback=1, dispatch_floor_awareness=2` — carried
forward as the working point. **Not yet proposed as a `*-final-winner.patch`**:
per `overfitting_guard.REQUIRED_GATE_NOTE`, that requires a clean
`genuine_win` on a blind, held-out check, and this pass's blind result is
ambiguous rather than clean.
