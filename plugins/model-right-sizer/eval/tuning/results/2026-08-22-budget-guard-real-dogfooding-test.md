# Real dogfooding test: `model-right-sizer-budget-guard` against a real build

Unlike a unit test of `eval/budget_threshold.py`'s three functions in isolation
(which already exist and pass — see `tests/model_right_sizer/test_budget_threshold.py`),
this is the mechanism exercised for real: a real Pass A blueprint, real
sub-agent dispatches, real reported token spend, and the deterministic
threshold check run against that real spend at each turn boundary — the same
"chief-of-staff" loop `model-right-sizer-budget-guard`'s skill describes, run
by the orchestrating session rather than simulated.

**The feature under test**: `unit-reconcile-fn` and `unit-reconcile-tests`
close v1.0.0 gap #6 (promote the two-harness floor reconciliation from ad hoc
arithmetic into a real utility) — a real, valuable unit of work, not a
throwaway task invented only to generate test data.

## Step 0 — real Pass A blueprint

`model-right-sizer` (opus, live price sheet fetched: Sonnet 5 is $2/$10 per
MTok, not the agent file's stale $3/$15 fallback) decomposed the intent into
two build units and set explicit `budget.token_ceiling` values by reasoning
about scope, not a boilerplate default:

| unit | tier | `budget.token_ceiling` |
|---|---|---:|
| `unit-reconcile-fn` | sonnet @ high | 88,810 |
| `unit-reconcile-tests` | sonnet @ low | 96,512 |

## Step 1 — `unit-reconcile-fn`: threshold crossed, warning injected, behavior changed

Real dispatch built `AGENT_TOOL_HARNESS_FLOORS` and `rebase_onto_canonical_floor()`
in `eval/token_ceiling_formula.py`, verified all four regression anchors
reproduce exactly, ran the repo's validators, and — on its own initiative —
bumped `FORMULA_VERSION` to `1.1.0`. Reported usage: **75,921 tokens**.

Run for real, not eyeballed:

```
threshold_crossed(75_921, 88_810)      -> True   (85% used)
remaining_budget_pct(75_921, 88_810)   -> 0.1451 (14.5% remaining)
```

The bump broke `test_formula_version_is_published_and_documented` (it expects
a matching dated release report, which correctly doesn't exist yet — the
test doing exactly its job). This created a genuine next-turn decision, so
the mechanism got a real test: `format_budget_warning()`'s exact string was
sent into the same agent's next turn, verbatim, alongside the real choice
(revert the bump — the tight-scope option — or explicitly ask for more
budget to write the release report).

**Result: the agent reverted the version bump**, citing the budget warning
directly and noting that a release report is `model-right-sizer-release-report`'s
job, not an afterthought under budget pressure. `FORMULA_VERSION` is back at
`1.0.0`. This is the first real evidence (n=1) that injecting the warning
string changes what a dispatched sub-agent actually does, not just what it's
told — the mechanism this whole feature exists for.

## Step 2 — `unit-reconcile-tests`: threshold crossed, no turn left to warn

Real dispatch added 8 test functions (11 cases) to
`test_token_ceiling_formula.py` — regression anchors, an identity invariant,
a real per-tier drift check, and three error paths — then ran the full suite
and all four validators. Reported usage: **91,376 tokens**.

```
threshold_crossed(91_376, 96_512)      -> True   (94.7% used)
remaining_budget_pct(91_376, 96_512)   -> 0.0532 (5.3% remaining)
```

Threshold crossed again, harder — but the unit's work was already complete
(tests written, suite green, validators clean) with no legitimate follow-up
task remaining. **No warning was injected here**, and that's the correct
call, not a gap: this is the documented limitation from
`model-right-sizer-budget-guard`'s own SKILL.md step 5 showing up in
practice — its author checked, rather than assumed, whether a live mid-turn
spend signal exists on this session's dispatch tools and found none, so a
crossing discovered only at turn-completion, on a turn that was already the
unit's last one, has nothing left to warn *into*. The mechanism is only
actionable when a next turn genuinely exists.

(Correction, applied during the sequel blog post's review: the original
draft of this section attributed the "no confirmed live mid-turn signal"
finding to `eval/budget_threshold.py`'s own docstring. That module's
docstring actually describes the check it implements, not the absence of a
live signal — the finding and its "checked, rather than assumed" framing
live in the `model-right-sizer-budget-guard` skill instead. Fixed here for
accuracy.)

## A real, new finding this test surfaced, not invented to fill the report

Writing the drift-check test forced computing the real per-tier drift
between `DISPATCH_FLOORS` and `AGENT_TOOL_HARNESS_FLOORS` instead of trusting
the "roughly 5–15%" characterization in
`2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`'s prose:

| tier | `DISPATCH_FLOORS` | `AGENT_TOOL_HARNESS_FLOORS` | real drift |
|---|---:|---:|---:|
| sonnet | 40,669 | 42,512 | 4.53% |
| opus | 38,260 | 42,416 | 10.86% |
| haiku | 25,664 | 32,653 | **27.23%** |

Sonnet and opus land inside the informally-claimed band; **haiku does not** —
its drift is nearly double the top of that range. This is independent,
additional evidence for v1.0.0 gap #1 (haiku-tier calibration is the single
weakest link): not just "haiku missed the one fresh-task classification,"
but "haiku's two independent floor measurements disagree by over 2x more
than the other two tiers do." The test asserts the real numbers with a
comment flagging the discrepancy, not a padded tolerance that would hide it.

## What this does and doesn't establish

- **n=1 per unit.** One real crossing led to one real behavior change; one
  real crossing had no turn left to act on. This is evidence the mechanism
  *can* work as designed, not a statistical claim about how often it will.
- **The budget-guard's own documented limitation is confirmed, not
  theoretical**: turn-boundary-only checking is a real constraint that
  materialized on the very first two real dispatches tried against it, not
  an edge case.
- **Both units still landed `within_budget` in the classical sense**
  (75,921 < 88,810; 91,376 < 96,512) — crossing the 70% warning line and
  exceeding the ceiling are different events, and this test exercised the
  former, not a real over-budget dispatch. That remains untested for real by
  this pass.
- **Gap #6 is now closed in code** (`rebase_onto_canonical_floor()` +
  `AGENT_TOOL_HARNESS_FLOORS`, `455 passed`, all four validators clean) —
  but `FORMULA_VERSION` deliberately stays at `1.0.0` until
  `model-right-sizer-release-report` produces the real v1.1.0 report this
  change now warrants, per the reverted unit's own reasoning.

## Concrete next step

Run `model-right-sizer-release-report` for a genuine v1.1.0 release,
covering: `rebase_onto_canonical_floor()` + `AGENT_TOOL_HARNESS_FLOORS`
(closing gap #6), and the haiku drift finding above as fresh evidence
sharpening gap #1 — both with their own "why this matters" clauses, per that
skill's own rule.
