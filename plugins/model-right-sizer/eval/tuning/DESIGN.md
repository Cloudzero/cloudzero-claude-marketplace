# model-right-sizer prompt-tuning experiment — design

Where [`../ablation/DESIGN.md`](../ablation/DESIGN.md) asks *does each
citation layer change anything*, this experiment starts from the answer
"yes, keep all four" and asks a different question: **given all four
layers are present, which exact wording of them makes real-execution
accuracy highest** — "accuracy" being this repo's fixed definition, "expected
effort stayed within prediction," the same `classify_budget_adherence`
function [`../ablation/results/2026-08-21-pilot-run.md`](../ablation/results/2026-08-21-pilot-run.md)
and [`../ablation/results/2026-08-21-full-independent-run.md`](../ablation/results/2026-08-21-full-independent-run.md)
already use.

## What "gradient descent" means here — read this before running anything

There is no derivative of a Markdown file. A literal gradient requires a
continuous, differentiable parameter space; the thing being tuned here is
prose. What this experiment actually runs is the discrete analog: **ordinal
coordinate-wise ascent via finite differences** — for each of a small set of
independently-editable wording knobs (each an ordered integer scale, e.g.
"budget margin: generous ↔ tight"), hold every other knob fixed, evaluate
every other level of that one knob against the current best, and move to
whichever level scored highest (staying put if none beat the current point).
Repeat across knobs, then repeat the whole sweep until a full pass produces
no move (a local optimum) or the round budget is spent.

This is named precisely rather than dressed up as literal gradient descent,
for the same reason the ablation study insists "coordinate-wise ascent" over
"we tried some things and X worked best" — matching this repo's citation-
fidelity/statistical-honesty discipline applied to the search procedure
itself, not just the findings it produces. It is also why the knobs below
are ordinal (a meaningful "direction" and "step") rather than an arbitrary
grab-bag of unrelated rewrites — a coordinate step only means something if
"level 2" is genuinely further in the same direction as "level 1".

## Objective — precisely, and why it's two numbers not one

Primary: **`accuracy_rate`** — the fraction of scored real-execution rows
classified `within_budget` by
[`../reasoning_budget.classify_budget_adherence`](../reasoning_budget.py),
exactly as the ablation study defines "accuracy." This is what the user
asked to maximize, so it is the primary criterion, not a proxy for it.

Tie-break: **`mean_loss`** — a continuous distance-to-the-band measure per
row (`0` for `within_budget`; how far the ratio sits past `1.0` for
`over_budget`; how far under `0.5` for `under_budget_oversized`), averaged
over scored rows. With only a handful of real-execution rows per candidate
in any single evaluation round, `accuracy_rate` is a coarse fraction (e.g.
2/4 vs 3/4) that ties constantly across nearby candidates; `mean_loss`
distinguishes a near-miss from a far-miss without changing what's being
optimized — a tie on `accuracy_rate` with a smaller `mean_loss` is a
strictly closer set of misses. Both are computed by
[`optimizer.py`](optimizer.py)'s `score_candidate`, which also carries
forward the same `computation_errors` discipline (a zero-budget row that
still spent tokens is reported, never silently dropped or divided by zero)
[`../ablation/metrics.py`](../ablation/metrics.py) already established.

Final tie-break, only if both of the above tie exactly: **prefer the
smaller total edit** — the candidate whose knob settings deviate least from
the shipped baseline (all levels `0`). This is the "Less is More" default:
among equally-accurate wordings, ship the one that changes the file least.

## Search space — four knobs, chosen because they touch the metric directly

[`knobs.py`](knobs.py) is the registry. Every knob is a small, worded edit
at one fixed anchor point inside the all-four-layers agent text (not a
whole section, unlike `../ablation/layers.py`'s ablation cuts) — chosen
because each one plausibly moves the actual/budgeted ratio the accuracy
metric reads, not because it's an interesting rewrite in the abstract:

| knob | location | what moving it up does |
|---|---|---|
| `budget_margin` | Pass A item 4, the `budget` bullet | Widens/tightens the stated headroom between `token_ceiling` and the expected token spend for the row's model+effort tier — the single most direct lever on the accuracy ratio's denominator. Levels −1 (generous, 2–3×) → 0 (shipped, no explicit margin) → +1 (1.2–1.5×) → +2 (explicit `expected_tokens` estimate, ×1.2–1.3, stated in the rationale). |
| `effort_tax` | Adaptive reasoning-budget layers, IBPO item 1 | Pushes the effort dial (and so the ratio's numerator, actual spend) down or up specifically when a stage's difficulty score is uncertain. Levels −1 (favor higher effort when uncertain) → 0 (shipped) → +1 (favor lower effort when uncertain). |
| `calibration_aggressiveness` | Pass A item 8, calibration ledger | Whether past `under_budget_oversized` rows for a task-shape explicitly pull the NEXT ceiling down, not just the model tier. Levels 0 (shipped) → +1 (adds the explicit ceiling-correction rule). |
| `pass_b_feedback` | Pass B, budget-adherence bullet | Whether a Pass B miss must name a corrected ceiling NUMBER for next time, not just the direction. Levels 0 (shipped) → +1 (requires the number). |

Deliberately excluded from v1, to keep the search cheap (four knobs, not
forty): model-tier wording, the message-schema layer, and the speculative-
decoding layer's own text — none of those anchors plausibly move the
budget-adherence ratio as directly as the four above, and a wider search
multiplies the number of expensive real-execution rounds needed. Propose an
addition to `KNOBS` as its own reviewable change if a future run wants to
widen the search.

All-knobs-at-`0` is required to render byte-identical to the shipped agent
file (checked by `tests/model_right_sizer/test_tuning_knobs.py`, the same
invariant `../ablation/layers.py`'s all-four condition holds) — the starting
point of this search IS the shipped file, since the brief is "tune the file
that already has all four layers," not "ablate a layer."

## Algorithm

```
settings = knobs.default_settings()          # all zeros = shipped baseline
current_score = evaluate(settings)           # real-execution round, see below

loop up to MAX_PASSES full passes:
    moved_this_pass = False
    for knob_name in ALL_KNOBS:
        neighbors = optimizer.propose_neighbors(settings, knob_name, KNOBS[knob_name]["levels"])
        neighbor_evals = [{"settings": n, "score_result": evaluate(n)} for n in neighbors]
        step = optimizer.coordinate_ascent_step(settings, current_score, knob_name, neighbor_evals)
        if step["improved"]:
            settings, current_score = step["new_settings"], step["new_score"]
            moved_this_pass = True
    if not moved_this_pass:
        break   # local optimum -- converged
```

`evaluate(settings)` is the one step this module does NOT implement — it
requires a real build per row, which needs an actual agent-dispatch runtime.
That belongs to the SKILL runbook
([`../../skills/model-right-sizer-prompt-tuning/SKILL.md`](../../skills/model-right-sizer-prompt-tuning/SKILL.md)),
which calls `optimizer.score_candidate()` on whatever real-execution records
it collected for that candidate's blueprint rows.

## Evaluation protocol per candidate

For each candidate's `evaluate()` call:

1. Render the variant (`knobs.render_variant`).
2. Run that variant's Pass A (blueprint-only, dry-run) against the
   **evaluation task subset** below, same discipline as the ablation study:
   one independent sub-agent dispatch per (candidate, task) cell — never one
   session across more than one task or more than one candidate, for the
   exact reason [`../ablation/DESIGN.md`](../ablation/DESIGN.md)'s "Lessons
   from the full-independent-dispatch rerun" section names: a correlated
   session can produce a false signal, not just a noisier one, and this
   experiment's whole output is a sequence of accept/reject decisions built
   on exactly that signal.
3. For each `blueprint_rows[]` entry, actually build the row's increment
   (same as `../ablation/DESIGN.md`'s accuracy sweep), dispatched at the
   row's `pick.primary.model`/`effort`, told its stated `budget.token_ceiling`.
4. Record `{actual_tokens, budgeted_tokens}` per row, with the harness's own
   reported usage figure minus the control-measured per-dispatch overhead
   floor for that model tier — reuse or re-measure the
   [`../ablation/results/2026-08-21-full-independent-run-accuracy.json`](../ablation/results/2026-08-21-full-independent-run-accuracy.json)
   floors (sonnet 38,401 / haiku 28,508 tokens) if the runtime is the same;
   re-measure with two fresh no-op control dispatches if not, or if enough
   time has passed that the floors are suspect — never subtract a floor you
   haven't verified still applies.
5. `optimizer.score_candidate(records)` on the resulting list.

### Evaluation task subset — and why it's not all six

Real-execution rounds are the expensive phase (a build per row, repeated
per candidate, repeated across a multi-pass search) — reusing all six
`../ablation/benchmark_tasks.json` tasks for every candidate multiplies cost
by the number of candidates evaluated, most of which get discarded. Use a
**tuning subset** of tasks whose `designed_to_probe`/hypothesis in
`benchmark_tasks.json` most directly engages the budget/effort mechanism
these knobs touch:

- **Tuning set** (used during search): `t1_bulk_classifier`,
  `t4_interactive_latency_sensitive_chat`, `t6_bounded_wellspecified_fix` —
  three tasks spanning tight-volume, latency-interactive, and
  trivially-bounded budget shapes, chosen for spread rather than for being
  "the budget tasks" narrowly.
- **Held-out set** (never touched during search, evaluated exactly once on
  the FINAL winning settings only): `t2_ambiguous_cross_service_refactor`,
  `t3_long_horizon_agentic_build`, `t5_fanout_pr_review`.

The held-out check exists because six tasks total is a small, fixed,
publicly-visible benchmark suite — a search free to look at all six risks
tuning the wording to this exact suite's quirks rather than to budget
calibration in general. Report the held-out accuracy alongside the tuning
accuracy in the final write-up; a large gap between them is itself a
finding (the tuned wording overfit the tuning subset), not something to
smooth over.

## Cost accounting

Per candidate evaluated: `n_tuning_tasks` (3) real-execution builds — one
Pass A dry-run plus a real build per `blueprint_rows[]` entry that dry-run
produces (typically 1–3 rows per task in this benchmark suite, so roughly
3–9 real builds per candidate). Per knob-sweep pass: each of the four knobs'
non-current levels gets one candidate evaluation (1–2 extra levels per knob
in this registry, so ~6 candidate evaluations per full pass ≈ 20–50 real
builds). State the actual candidate count up front before spending real
build budget on a pass, the same way
[`../../skills/model-right-sizer-layer-ablation/SKILL.md`](../../skills/model-right-sizer-layer-ablation/SKILL.md)
states composition-vs-accuracy scope before running — never silently scale
a pass up mid-run.

## Stopping criteria

- **Converged**: a full pass over all four knobs produces no improving
  move (every knob's best neighbor score is no better than staying put).
- **Round budget spent**: `MAX_PASSES` reached without convergence — report
  the best point found so far as provisional, explicitly not a confirmed
  local optimum.
- **Held-out check**: run exactly once, after either stopping condition,
  never mid-search.

## Known limitations (state these in the final write-up, don't discover them by re-running)

- **Single-draw noise per candidate.** One real-execution round per
  candidate is one noisy sample of an LLM's own output-length variance, not
  a stable estimate — a knob that looks better on one draw might not on a
  repeat. Repeating each candidate k>1 times and averaging would reduce this
  at k× the cost; v1 defaults to k=1 and names this as the reason a
  "winning" wording should be read as a promising direction, not a proven
  optimum, until it's been re-confirmed.
- **Coarse accuracy_rate at small n.** With 3 tuning tasks and ~1–3 rows
  each, `accuracy_rate` moves in large discrete steps (e.g. 2/6 → 3/6); the
  `mean_loss` tie-break exists because of this, but doesn't eliminate the
  underlying small-n problem.
- **A local, not global, optimum.** Coordinate ascent finds a point no
  single-knob move improves on — it does not search joint moves across
  multiple knobs at once, and a different starting point (or a different
  knob visitation order) could converge somewhere else. This is disclosed,
  not hidden, exactly like the ablation study's own "n=1 session" caveat.
- **Four knobs is a deliberately small v1 search space** (see "Search
  space" above) — a wording lever this experiment didn't include is simply
  untested, not ruled out.
