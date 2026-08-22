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

## Search space — five knobs, chosen because they touch the metric directly

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
| `calibration_decay` | Adaptive reasoning-budget layers, end of BudgetThinker item 2 | Whether a task-shape's calibration-ledger *tolerance* itself must tighten with repeat `within_budget` observations, grounded in SelfBudgeter's decaying tightness coefficient (arXiv 2505.11274, Formula 6). Levels 0 (shipped) → +1 (states the tightening qualitatively) → +2 (requires an explicit decay rate in the rationale). See "Grounding the 5th knob" below for why this replaced an initial, unsupportable `lambda` framing. |
| `pass_b_feedback` | Pass B, budget-adherence bullet | Whether a Pass B miss must name a corrected ceiling NUMBER for next time, not just the direction. Levels 0 (shipped) → +1 (requires the number). |

Deliberately excluded from v1, to keep the search cheap (five knobs, not
forty): model-tier wording, the message-schema layer, and the speculative-
decoding layer's own text — none of those anchors plausibly move the
budget-adherence ratio as directly as the five above, and a wider search
multiplies the number of expensive real-execution rounds needed. Propose an
addition to `KNOBS` as its own reviewable change if a future run wants to
widen the search.

All-knobs-at-`0` is required to render byte-identical to the shipped agent
file (checked by `tests/model_right_sizer/test_tuning_knobs.py`, the same
invariant `../ablation/layers.py`'s all-four condition holds) — the starting
point of this search IS the shipped file, since the brief is "tune the file
that already has all four layers," not "ablate a layer."

## Grounding the 5th knob — the `lambda` framing didn't survive contact with the sources

The 5th knob was originally proposed as tuning a `lambda` weight inside a
formula from "one of the research papers," following the platform PRD's
Phase 2 (Governed Pin Control Plane) governance-phase framing. That framing
does not hold up:

- `docs/model-right-sizer-platform/phase-2-pin-governance/DESIGN.md` (the
  actual "governance phase" doc, in the separate
  `Cloudzero/project-model-right-sizer-platform` repo) states outright:
  "**lambda is a governed field, not a subsystem.** Nothing in this Epic
  computes or optimizes `J = P - lambda*C`; lambda is stored, versioned, and
  delivered like any other policy attribute." Its Out-of-Scope section
  repeats this almost verbatim. `J = P - lambda*C` is the PRD author's own
  unattributed shorthand notation — not a quotation from IBPO, BudgetThinker,
  or SelfBudgeter.
- All three candidate papers were checked directly. Neither IBPO
  (arXiv:2501.17974) nor BudgetThinker (arXiv:2508.17196) contains a `lambda`
  cost-weight. SelfBudgeter (arXiv:2505.11274) — the paper both
  `RESEARCH.md` and `PROJECT.md` in the platform repo carry as the third
  research-grounding citation alongside IBPO and BudgetThinker — was read in
  full: its reward formalism (Formula 1, a piecewise GRPO reward) contains no
  `lambda` either. `agents/model-right-sizer.md` itself was also grepped:
  zero hits for "lambda", "λ", or "J = P" before this change.
- SelfBudgeter's real governing hyperparameter is `alpha`, a *tightness
  coefficient* — and, unlike the PRD's `lambda`, `alpha` genuinely IS
  scheduled to change within a formula over the course of training (Formula
  6, the dynamic linear decay `alpha_now = alpha_start -
  (alpha_start-alpha_end)*(step/Total_steps)`, from a permissive
  `alpha_start=6.0` to a strict `alpha_end=0.1`). That is the closest real
  mechanism available to the original ask — "a governance phase that
  changes lambda within a formula" — and `calibration_decay` (above)
  translates it into model-right-sizer's own calibration ledger: tolerance
  should tighten as a task-shape accumulates `within_budget` observations,
  the same way `alpha` tightens as training progresses.
- Deliberately deferred: `citation_ledger.json` (the shipped agent file's
  answer key, checked by `check_citations.py`) gets no SelfBudgeter entry
  from this change. That ledger only covers claims that actually appear in
  `agents/model-right-sizer.md` — `calibration_decay`'s SelfBudgeter text
  lives only in tuning-experiment variants (`knobs.py` levels 1/2), the same
  as every other knob in this registry, per this file's own "never edits
  `agents/model-right-sizer.md` itself" design choice. If a future pass's
  winning combination promotes `calibration_decay` into the shipped file (as
  a merged diff, human-reviewed, the same path pass 1's proposed diff
  already follows), add the SelfBudgeter ledger entry — with `formula_expr`,
  `source_variables`, and hand-computed `expected_output`s per
  `eval/tuning/selfbudgeter.py` — in that same PR, not before.

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
3–9 real builds per candidate). Per knob-sweep pass: each of the five knobs'
non-current levels gets one candidate evaluation (1–2 extra levels per knob
in this registry, so ~7 candidate evaluations per full pass ≈ 20–60 real
builds). State the actual candidate count up front before spending real
build budget on a pass, the same way
[`../../skills/model-right-sizer-layer-ablation/SKILL.md`](../../skills/model-right-sizer-layer-ablation/SKILL.md)
states composition-vs-accuracy scope before running — never silently scale
a pass up mid-run.

## Stopping criteria

- **Converged**: a full pass over all five knobs produces no improving
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

## Lessons from pass 1

[`results/2026-08-21-pass1.md`](results/2026-08-21-pass1.md) is the first
real execution of this search (one coordinate-ascent pass, all four knobs,
scope confirmed up front). One methodology gap surfaced by actually
running it, not anticipated when this design was written:

- **A real-execution build dispatched as a full sub-agent can't reach a
  tiny per-item `token_ceiling`, no matter what the wording says.**
  `t1_bulk_classifier`'s blueprint rows carry per-item ceilings in the
  tens-to-hundreds of tokens (correct for one raw classification call
  inside a 10,000-item batch) — but every real build this pass dispatched
  for `t1` was a full sub-agent call (tool access, its own reasoning), and
  even after subtracting the measured per-dispatch overhead floor, every
  single `t1` cell across every candidate landed 3–11× over budget,
  including the unmodified baseline. This is a build-harness gap, not
  something any of the four knobs could fix by wording alone — a real
  `t1`-shaped build needs to be dispatched as a raw model completion call
  (no sub-agent, no tools) before its accuracy signal can be trusted. Until
  that's fixed, exclude `t1` from the tuning-set score, the same way the
  ablation study excluded it from `mean_token_ceiling` for a different
  (prompt-convention) reason — two different `t1` problems, same response:
  name it and exclude it rather than let it swamp the other tasks' signal.
- **A parallelized "one pass" is not the same as DESIGN.md's sequential
  pass** — evaluating every knob's neighbors against the shared baseline in
  one round (cheaper, and what pass 1 actually did) finds each knob's
  independent effect, but never tests them combined. A real second pass —
  or a direct evaluation of the all-four-winners-combined candidate — is
  still open before any single "winning wording" can be called validated.

## Lessons from pass 2 — a second measurement breakdown, and why passes 3–4 are paused

[`results/2026-08-21-pass2.md`](results/2026-08-21-pass2.md) is pass 2 (evaluating the
combined pass-1 winners plus the new `calibration_decay` knob). Two more structural gaps
surfaced, on top of pass 1's t1 gap, and together they're serious enough that passes 3–4 are
**paused, not run to satisfy the confirmed count**:

- **t4 stopped being a single-row task.** At the combined pass-1-winner point, every one of
  pass 2's 10 candidates decomposed t4 into 5–7 real-execution rows (design, backend,
  speculative-decoding eval, frontend, benchmark, review), not the 1 row every pass-1 t4
  candidate got. Real-building all of that would have meant ~55 real dispatches instead of
  the stated 10 — an order of magnitude over the confirmed scope, discovered only after the
  dry-run stage (itself 65k–140k tokens per call) completed. t4 was excluded from pass 2's
  real-execution scoring as a result — a new, pass-2-specific exclusion, distinct from t1's.
- **t6 then turned out to have the SAME problem t1 has.** With t4 excluded, every one of the
  10 t6 real builds landed `under_budget_oversized` — `accuracy_rate=0.0` for the whole pass.
  A real single-guard-clause edit costs a haiku sub-agent only ~340–1,050 net tokens once the
  28,508-token overhead floor is subtracted, which is under half of every `budget_margin`
  level tested, including the loosest. The floor's own apparent variance (a ~700-token spread
  across ostensibly-identical no-op-adjacent dispatches) is now the same order of magnitude as
  the entire signal being measured.
- **Net effect: after two structural exclusions (t1 permanent, t4 this-pass), the tuning
  set's real-execution signal is currently zero tasks with a working `accuracy_rate` and one
  task (t6) that gives only a `mean_loss` tiebreak.** Continuing to passes 3–4 against that
  channel would spend real-build budget confirming a gap already found, not learning
  anything new — so they're paused pending a redesign (a real, appropriately-sized codebase
  target instead of a synthetic scratch file; multiple draws per candidate to average down
  the floor's noise; or explicit sign-off to keep going on mean_loss alone).
- **One usable finding survived anyway, taken via code**: `optimizer.coordinate_ascent_step`
  on the t6-only mean_loss data moves `budget_margin` from `+2` down to `+1` — a partial
  reversal of pass 1's own "clearest winner," because that pass 1 result turns out to have
  been carried almost entirely by t4's now-excluded single-row measurement.

## Measurement redesign (2026-08-22) — option 1 from pass 2's three ways forward

Chosen over the other two options (repeated draws; sign-off to keep going on `mean_loss`
alone). Two pieces of new evidence, both taken via real dispatch, not assumed:

1. **The overhead floor itself is not noisy — it's nearly a constant.** Five independent
   zero-tool-call haiku dispatches (`reply with exactly one word: ok`) came back at
   25,660/25,668/25,668/25,668/25,660 tokens — a **4-token** spread, not the ~700-token
   spread pass 2 attributed to "the floor's own apparent variance." Re-reading pass 2's data
   with this correction: that ~700-token spread across t6's real builds was never floor
   noise — it was genuine (if small) variance in how much real work each haiku sub-agent
   actually did (which scratch function it invented, how many tool calls it made). The
   floor pass 1 measured and reused (28,508) was evidently taken with a nonzero tool-call
   count baked in, not a true zero-tool floor; the two aren't the same measurement and
   shouldn't have been treated as interchangeable.
2. **Marginal cost scales with real tool use and real content, not a flat per-dispatch
   tax.** Three follow-up probes from the same zero-tool baseline (~25,664): one trivial
   `Bash` call (+1,630), three trivial `Bash` calls (+1,809 — most of the jump is a one-time
   cost of using the Bash tool AT ALL, not a per-call charge), and one `Read` of a real
   ~230-line Python file (+4,050 — proportional to real file content, not tool count).
   **This is the actual lesson**: the old t6 prompt's failure wasn't floor noise, it was
   that the REQUIRED real work (invent a 3-line function, add one guard clause) was
   inherently smaller than any token_ceiling this rubric would ever assign. A task needs
   real, substantive content to read and act on before its real cost can discriminate
   between differently-worded ceiling knobs.

**The fix**: `t6_bounded_wellspecified_fix`'s real-execution target is no longer "invent
your own scratch function" — it's the checked-in fixture
[`../fixtures/cost_allocator.py`](../fixtures/cost_allocator.py) (+
[`../fixtures/test_cost_allocator.py`](../fixtures/test_cost_allocator.py)), a small but
real multi-function module where one function (`apply_seat_discount`) is the deliberate
odd-one-out against an established-but-inconsistently-applied validation convention the
other three functions share. A correct fix requires reading and pattern-matching real
context, not just writing one guard clause from nothing — see `benchmark_tasks.json`
schema_version 1.2's changelog entry for the full account, and the fixture module's own
docstring for why it's shaped the way it is. `../ablation/benchmark_tasks.json` is the
canonical source (shared with the ablation study); this file doesn't duplicate the task
text.

**Validated once, for real, before calling this done**: a haiku sub-agent dispatched
against the redesigned target (see `results/2026-08-22-measurement-redesign-validation.md`)
— confirming the new task's real net cost lands comfortably above the floor's own
(now correctly characterized as near-zero) noise, restoring genuine discriminating power
before any further pass spends real-build budget on it.

**Still out of scope for this redesign**: `t1_bulk_classifier` stays permanently excluded
— its per-item budget (60–600 tokens) is smaller than even the zero-tool floor (~25,664),
so no real-content fixture can fix it; that would need a fundamentally different
measurement mechanism (e.g. a raw completion call outside the full agent-dispatch harness),
not a bigger fixture. `t4`'s pass-2 decomposition-explosion problem is also untouched here
— this redesign only addresses t6's failure mode, not t4's.
