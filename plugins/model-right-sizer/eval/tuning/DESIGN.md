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

## Passes 3–4 — the redesign works, and finds the experiment's first real win

[`results/2026-08-22-pass3.md`](results/2026-08-22-pass3.md) and
[`results/2026-08-22-pass4.md`](results/2026-08-22-pass4.md) are the first two passes run
against the redesigned t6 target. The direction flips from pass 2's uniform
`under_budget_oversized`: **every candidate across both passes now lands `over_budget`
instead** — the real content cost of the fixture task clusters tightly around 12,500–15,100
net tokens, and every ceiling tested through pass 3 (3,000–10,000) undershoots that. This is
the redesign doing exactly what it was built to do: a genuine, discriminating signal instead
of a floor artifact.

- **Pass 3**: `budget_margin` moves `+1 → -1` (the loosest margin level) — mean_loss drops
  from 3.50 to 0.34, an order of magnitude, because `-1`'s 10,000-token ceiling comes closest
  to the real requirement of any tested level.
- **Pass 4**: `effort_tax` moves `-1 → +1` — and lands the experiment's **first-ever
  `within_budget` real-execution result** (accuracy_rate 0.0 → 1.0, mean_loss → 0.0000).
  `effort_tax=+1`'s wording pushed the dry-run's own quoted `token_ceiling` up to 15,000,
  which happens to bracket the real ~12,960-token spend inside `[0.5, 1.0]`. Read honestly:
  this is a win by the metric the experiment optimizes (ceiling calibration), not evidence the
  wording made the real work cheaper — the real net spend stayed in the same 12,500–15,100
  cluster every candidate has shown.
- **`calibration_decay` has now been tested at three different base points across passes 2–4
  and never once won a move** — real negative evidence against promoting it, not just an
  absence of a win.
- Final settings: `budget_margin=-1, effort_tax=1, calibration_aggressiveness=1,
  calibration_decay=0, pass_b_feedback=1`. Proposed diff:
  [`results/2026-08-22-final-winner.patch`](results/2026-08-22-final-winner.patch) — not
  applied, per this study's design; a human reviews and merges separately.
- Passes 1–2 ran against the since-fixed t6 target and should not be treated as comparable to
  passes 3–4's numbers — say so explicitly rather than averaging across the redesign boundary.
- Same standing caveats apply: n=1 per candidate (the `within_budget` win is one draw, not a
  repeated-and-confirmed one), and the parallel-sweep gap (neighbors evaluated against a
  shared start point, not re-checked after each accepted move).

## Investigating `calibration_decay`'s null result — a diagnosis, then a `calibration_decay=3`

`calibration_decay` (levels 1–2) never won a single move across three different base points
(pass 2, pass 3, pass 4). Before writing that off as "the wording just doesn't help," it's
worth diagnosing *why* — and the dry-run data already collected across every pass answers
this directly, no new dispatch needed to see it:

- **Every single dry-run this experiment has ever run reports
  `uncertainty_ledger.calibration.ledger_found: false`.** `calibration_decay`'s levels 1 and 2
  are both worded as *"tolerance should tighten as more `within_budget` rows accumulate for
  that shape"* / *"state the tightening rate... a calibration ledger with no stated decay
  rate is under-specified."* Both presuppose a calibration ledger already holding past rows
  to tighten against. This benchmark's real-execution protocol dispatches a single, fresh
  sub-agent per candidate with no history — there is never a ledger for the wording's own
  conditional to act on.
- **The dry-run rationale text confirms this behaviorally, not just structurally**: across
  every `calibration_decay=1` and `=2` dry-run in passes 2–4, the blueprint's own rationale
  never once mentions tightening, decay, or a ledger — the model isn't declining to apply the
  guidance, it's reading it as inapplicable to a first (and only) observation, which is
  exactly right given what the wording literally says.

**`calibration_decay=3`** reframes the same real SelfBudgeter mechanism (Formula 6's decay
schedule) for the regime this benchmark actually tests — a *first* observation, not a
*repeated* one: *"absent a calibration ledger, a task-shape's first observation is still on
the schedule's permissive starting end, not its tight asymptote... pad `token_ceiling`
generously the same way the schedule's own early-training α does, and only tighten once real
`within_budget` rows for that shape actually exist to justify it."* This doesn't invent a new
concept — it's the same Formula 6 curve, just correctly identifying which end of it applies
when no ledger exists, instead of describing behavior that only makes sense once one does.

Tested at the current winning point (`budget_margin=-1, effort_tax=1,
calibration_aggressiveness=1, pass_b_feedback=1` — the first time `calibration_decay` has
been tested combined with the actual winning `effort_tax`, not a stale earlier point). See
[`results/2026-08-22-pass5.md`](results/2026-08-22-pass5.md) for the full result — summary:
**the fix didn't win.** `calibration_decay=3` scored worse than doing nothing
(`over_budget`, mean_loss 0.1007 vs. the current point's 0.0000). `calibration_decay=1` tied
the current point's `accuracy_rate`/`mean_loss`, but its dry-run happened to pick Sonnet
(every other `calibration_decay` dry-run across all five passes picked Haiku) — Sonnet's real
net spend on this task ran substantially lower, which explains the tie without any causal
role for the wording. `select_best`'s own "Less is More" tiebreak correctly declined to move
on a tie. `calibration_decay` stays at level 0 in the current best-known settings. This is a
second, deliberately better-targeted negative result, not just an absence of a win yet — and
it's disclosed as such rather than quietly dropped.

## Novel-use-case validation (2026-08-22)

Everything above tunes and scores against this benchmark's own synthetic `t1`–`t6` tasks. A
separate check asked whether the settled settings generalize past that benchmark at all: the
tuned variant (`budget_margin=-1, effort_tax=1, calibration_aggressiveness=1,
calibration_decay=0, pass_b_feedback=1`) was dry-run against a genuinely novel, real intent
(the "Repo Slack Channel Routing" design) and then one of its own recommended units
(`unit-channel-setup`, sonnet tier, 15,000-token budget) was actually dispatched for real.

Result: **`over_budget` by ~2.8x** (raw=82,715, sonnet zero-tool floor=40,669, net=42,046,
ratio=2.803). Full write-up, including the dry-run's own routing table and the honest n=1
scope caveat:
[`results/2026-08-22-novel-use-case-validation.md`](results/2026-08-22-novel-use-case-validation.md).
This does not undo the on-benchmark pass 3–4 findings (`budget_margin`/`effort_tax` are still
this benchmark's best-known settings), but it is evidence that budgets tuned against
single-shot/low-tool-turn synthetic tasks don't reliably transfer to real multi-tool-call,
content-generation-heavy work — the same shape of miss as `t1`'s exclusion and `t4`'s
decomposition explosion, on the budget-magnitude axis instead of the decomposition axis. The
skill built from this test — and its own documentation of this gap — lives at
[`../../skills/repo-slack-channel/SKILL.md`](../../skills/repo-slack-channel/SKILL.md).

## Pass 6 — closing the gap, and guarding against overfitting (2026-08-22)

A dedicated research pass reviewed best practices for composing an agent
instruction `.md` file and evaluated the delta against the shipped
`agents/model-right-sizer.md`. Its top finding causally matched the 2.8x miss
above: the budget bullet demands `token_ceiling` be "an actual integer... not
a vibe" with no method for deriving it — no dispatch-overhead-floor concept,
no scaling by tool-call count or content volume. Added a 6th knob,
`dispatch_floor_awareness`, encoding that fix. Full write-up, including an
important semantic correction (the new wording makes `token_ceiling`
floor-INCLUSIVE, so it must be compared against raw actual spend, not the
floor-net actual the other five knobs' comparisons use) and the pass's two
dry-run results (a calibrated one that turned out to have read the exact
prior real outcome via the calibration ledger, and a blind one that didn't):
[`results/2026-08-22-pass6-dispatch-floor-awareness.md`](results/2026-08-22-pass6-dispatch-floor-awareness.md).

**Guarding against overfitting.** The calibrated dry-run's clean-looking win
turned out to be partly attributable to the dry-run agent finding and reading
`results/2026-08-22-novel-use-case-validation.md` — this exact task's own
real prior outcome — rather than to the new wording alone. That is a real
contamination path this project's own methodology creates: Pass A item 8
always instructs reading a calibration history if one exists, and after
enough validation passes, every task this experiment tests against has one
written up somewhere readable. `overfitting_guard.py` formalizes the fix: a
held-out task pool disjoint from the coordinate-ascent benchmark, plus
`assess_generalization()`, which requires a **blind** dry-run (calibration
access explicitly withheld) to also land acceptably before a settings
combination can be proposed for merge — a calibrated-only win is
`calibration_masked`, not a `genuine_win`. Pass 6's own blind check came back
ambiguous (its verdict depends on a decomposition choice that differed from
what was actually measured, not a flaw in the reasoning) — reported as such,
not rounded up to a clean pass.

## Pass 7 — a real-actuals check against a second held-out task, blind vs. blind (2026-08-22)

Building the chief-of-staff token-budget-enforcement feature itself (via the
tuned blueprint's own real dispatches, never hand-authored) produced six
real `{actual_tokens, budgeted_tokens}` pairs — added as
`overfitting_guard.HOLDOUT_TASKS`' second entry. Pass 7 used it directly: two
genuinely blind dry-runs (no calibration ledger, so no contamination
possible on either side) against the exact same intent, one at
`dispatch_floor_awareness=2` and one at a new level 3 diagnosed from the
first run's worst miss (a `low-tool-turn`-classified schema edit gated
behind a mandatory validate-then-fix loop, priced as if that loop were
free). Result: `accuracy_rate` 0.167 → 0.333 (now matching the real build's
own live-dispatch rate), `mean_loss` 0.448 → 0.256 — a real, uncontaminated
improvement, though not a complete fix (one unit regressed, plausibly
sampling noise; the targeted miss improved but didn't close). Full
comparison: [`results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`](results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md).
`dispatch_floor_awareness=3` was adopted as the new current best-known
level, replacing 2.

**A third iteration (level 4) was then tried and rejected.** Asked to keep
tuning toward a 90% target, a level 4 added a concrete calibrated range for
the two shapes iteration 2's misses shared. Result: `accuracy_rate`
regressed to 0.167 (mean_loss flat at 0.256) — the specifically-targeted
unit did improve into `within_budget`, but two OTHER units that had been
`within_budget` at level 3 flipped to `over_budget`, one by a large margin.
Per `optimizer.select_best`'s own primary criterion, this is a straight
rejection, not a mixed result to average away — level 4 stays in
`knobs.py`'s registry as a tried-and-rejected data point (same discipline
`calibration_decay`'s own history keeps), and **level 3 remains the current
best-known level**. The more consequential finding from this iteration:
two units swung by large margins with no wording change targeting either of
them, suggesting single-draw sampling noise is roughly the same magnitude
as the wording effects this loop is trying to detect — a real ceiling on
how far single-draw-per-candidate blind tuning can reliably push
`accuracy_rate` on this one task without averaging multiple draws per
candidate first. Full three-iteration comparison and diagnosis:
[`results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`](results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md).

Deliberately not pursuing a fourth single-draw iteration on this same task
this pass, per that write-up's own call: squeezing one held-out task's n=6
harder, on a signal already shown to be noise-dominated at this sample
size, looks like the same overfitting risk this whole mechanism exists to
catch, not further tuning.

**Iteration 4 corrected the record with proper multi-draw averaging.** Asked
to keep pushing toward a 90% target, and having found single-draw noise was
roughly the same size as the wording effects being measured, the methodology
changed to 3 independent blind draws per candidate, averaged before scoring.
Re-measuring level 3 this way revealed its TRUE `accuracy_rate` is **0.167**,
not the 0.333 a single lucky draw had reported — two units (module, skill)
that looked `within_budget` in the original single draw are `over_budget` on
2 of their own 3 draws; only the mean survives near the boundary. This
doesn't reverse the level-3 adoption (its `mean_loss`, 0.246 averaged, still
beats level 2's 0.448), but it does mean the "0.333, matching the real
build" framing above should be read as superseded by this correction.

**Iteration 5 tested a general, non-enumerated fix (level 5) with the same
3-draw-averaged rigor — and it lost cleanly.** Rather than repeat level 4's
example-narrowing mistake, level 5 added a general "apply a 1.3–1.9×
multiplier" instruction. Result: worse than level 3 on every single unit
(not just in aggregate), `accuracy_rate` 0.167 → 0.000, `mean_loss` 0.246 →
0.487. Diagnosis: naming an explicit multiplier plausibly invited a smaller
base estimate to apply it to, netting lower than level 3's simpler
"floor-plus-real-work" framing with no stated multiplier — a second, distinct
prompt-engineering failure mode this pass surfaced (after level 4's
enumeration-narrows-generalization finding).

**Where this leaves the tuning thread**: two deliberate wording fixes (levels
4 and 5) tried and rejected, one confirmed by noise-controlled averaging, one
initially by a since-superseded single draw. Level 3 remains the current
best-known setting, backed now by a real 3-draw average rather than a lucky
single one. This held-out task has been read blind 8 times across this pass
and is no longer a reliable discriminator at this sample size — the next
legitimate move is a fresh held-out task, not a sixth attempt against these
same six numbers. Full iteration-by-iteration detail, including both
rejected levels' exact per-unit tables:
[`results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md`](results/2026-08-22-pass7-blind-vs-chief-of-staff-actuals.md).

The current best-known settings
(`budget_margin=-1, effort_tax=1, calibration_aggressiveness=1,
calibration_decay=0, pass_b_feedback=1, dispatch_floor_awareness=3`) are
carried forward as the working point but are **not yet proposed as a
`*-final-winner.patch`** — per `overfitting_guard.REQUIRED_GATE_NOTE`, that
requires a clean `genuine_win` first, and both held-out tasks have now been
read more than once.

## A different mechanism, not another wording pass: `token_ceiling_formula.py` (2026-08-22)

Rather than keep searching `knobs.py`'s wording space against the same
retired task, tested a structurally different fix: instead of the LLM
free-handing a raw `token_ceiling` integer, have it rate three bounded
[0.0, 1.0] signals (`tool_call_volume`, `content_volume`,
`cross_reference_load` — the same KIND of judgment call
`signals.effectiveness/efficiency/difficulty` already make reliably) and
let deterministic code (`../token_ceiling_formula.py`) compute the integer.
A first, completely untuned validation (3 blind draws rating only the
signals, against the same six chief-of-staff actuals) found: noise reduced
but modestly, not dramatically (mean CV 12.9% vs. the 10–30% found for raw
integers); the formula matched level 3's `accuracy_rate` (0.167) on its
first attempt with zero tuning; and the misses clustered tightly (1.21–1.32
ratio on 5/6 units), suggesting one uniform under-calibrated constant
rather than scattered per-unit errors. Deliberately did NOT re-fit the
formula's constants against this same result — that would be fitting to
the same retired six numbers a second time. Full write-up:
[`results/2026-08-22-signal-rating-formula-validation.md`](results/2026-08-22-signal-rating-formula-validation.md).
Not yet wired into the schema or the shipped agent file — this was a
validation-first step; a fresh held-out task's real actuals should confirm
the ~1.25x gap before any recalibration or schema integration.

## Gradient descent on the 3 signal weights — a proven ceiling, not a bug (2026-08-22)

Asked to derive the three signal weights via a real gradient-descent
pipeline (offline, no LLM dispatch — training data is the 18 raw signal
readings already collected) and tune toward 90% accuracy.
`../tuning/weight_optimizer.py` implements this for real: analytic
gradients through the convex-combination formula, gradient-checked against
finite differences (`tests/model_right_sizer/test_weight_optimizer.py`),
batch gradient descent for thousands of epochs.

Result, both proven mathematically before training and confirmed
empirically after: **90% is not reachable by tuning these weights alone.**
`compute_real_work_scale` is a convex combination, so it can never predict
a scale above the per-example max of the three signals — and even the
theoretical best case (100% weight on whichever signal is highest, per
example) leaves 5 of 6 units `over_budget` on this data, capping accuracy
at ~16.7% before any training runs. A real, converged, gradient-checked
training run (loss 0.0625 → 0.0433, plateaus by epoch ~500 of 5,000) landed
exactly there: final training accuracy 16.7%, identical to the equal-
weights baseline. The pipeline is correct; the target was mathematically
unreachable with the parameters it was scoped to tune. Full derivation and
results: [`results/2026-08-22-weight-gradient-descent.md`](results/2026-08-22-weight-gradient-descent.md).

Moving past this ceiling needs either training `REAL_WORK_SPAN`/
`DISPATCH_FLOORS` too (more free parameters against the same 18 rows —
real overfitting risk on an already tiny, already-retired dataset) or
fresh real dispatch data. Neither done here; reported as a legitimate
negative result, not a bug to keep chasing.

## The actual fix: the aggregation formula, not more signals (2026-08-22)

Asked how to expand signal reach / whether to add more signals, tested the
cheaper hypothesis first: is the ceiling really about signal count, or
about the AGGREGATION formula? `compute_real_work_scale` normalizes
weights to sum to 1 — a weighted average, bounded within
`[min(signal), max(signal)]` per example. Removing that normalization (a
genuine unconstrained linear regression, same three signals, zero new
signals) reached **94.4% (17/18)** training accuracy after gradient
descent — `../token_ceiling_formula.py` now ships this as
`compute_token_ceiling_additive`.

**Critical check before trusting that number**: a model with a SINGLE
shared scalar (no per-signal weighting at all) reaches the identical
accuracy — proof the "3 independently learned weights" were really one
effective degree of freedom (a global scale correction) in a three-
parameter costume, not genuine per-signal learning. Now a permanent
regression test
(`test_gradient_descended_weights_do_not_beat_uniform_weights`), not just
a footnote. The sum of the three existing signals already correlates at
r=0.849 with real cost — the signals were never the weak link; the
formula's artificial cap was.

`ADDITIVE_TOTAL_SPAN`'s constant is fit against the same six retired real
actuals `REAL_WORK_SPAN` already used — `ADDITIVE_CALIBRATION_STATUS`
says `"UNVALIDATED"` explicitly, checked by its own test. Do not wire this
into the schema or trust it beyond this exercise until a fresh held-out
task's real actuals confirm it holds.

Four concrete NEW signal candidates are proposed (not yet tested) as a
generalization lever for FUTURE task shapes — not to raise this already-
maxed-out training number further: `validation_loop_iterations`,
`shared_file_blast_radius`, `voice_or_precision_consistency_requirement`,
`investigative_uncertainty`. Full derivation, the overfitting-check table,
and the reasoning behind each candidate signal:
[`results/2026-08-22-additive-formula-and-signal-expansion.md`](results/2026-08-22-additive-formula-and-signal-expansion.md).

## First candidate tested: `validation_loop_iterations` — real signal, not a helpful default (2026-08-22)

Wired into the API (4-argument signals/weights, default value AND default
weight `0.0`, fully backward-compatible), then tested against a fresh,
independently-rated 3-draw pass (not the stale 3-signal draws) for the
same six real units. Result: the signal runs ~2.5x noisier than the other
three (mean CV 25.8% vs. 9.7–10.6%), correlates weakly with real cost
alone (r=0.344), and *dilutes* the existing 3-signal sum's correlation
when added at equal weight (0.910 → 0.865). Root cause: it correctly
flags exactly the 2 of 6 units genuinely gated behind a validate-then-fix
loop (a schema/changelog validator, a test suite) but the other 4 units
are expensive for reasons it doesn't capture (cross-referencing, general
volume) — so most of the time it adds noise, not coverage. The shipped
default weight of `0.0` stays as-is, now backed by evidence rather than
just caution; both findings are permanent regression tests
(`test_validation_loop_iterations_is_noisier_than_the_other_three_signals`,
`test_validation_loop_iterations_dilutes_the_existing_signal_correlation`).
Full write-up, including an honest note that the accuracy-based comparison
saturated near ceiling and was NOT decisive either way:
[`results/2026-08-22-validation-loop-iterations-signal.md`](results/2026-08-22-validation-loop-iterations-signal.md).

## Breaking down token consumption by sub-agent archetype, not just by task (2026-08-22)

Asked to break down what drives token consumption in each sub-agent and
derive signals from that, rather than keep reasoning from one task's six
build units. Worked from `model-right-sizer.md`'s own decomposition list
(build stage, review stage, finder → verifier fan-out, synthesis/panel
stage, query-shaped stage) and named the dominant token driver per
archetype. Two gaps repeated across multiple archetypes (not just one
task's guess): (1) **`context_ingestion_volume`** — how much pre-existing
material a unit must read before acting, distinct from
`cross_reference_load`'s "must stay consistent with" (a review unit
reading a large diff has near-zero cross-referencing but high ingestion
cost); (2) **`investigative_uncertainty`** — whether a unit's tool calls
are searching for something not known to exist vs. executing an
already-specified sequence, distinct from `tool_call_volume`'s raw count
(two finders can share a call count and differ entirely in how many of
those calls were dead ends). Deliberately did NOT re-propose the other
two candidates from the prior signal-expansion pass
(`shared_file_blast_radius`, `voice_or_precision_consistency_requirement`)
since neither showed up as a repeated cross-archetype gap the way these
two did — a `Less is More` call, not an oversight, especially with
`validation_loop_iterations` as a fresh example of a plausible-sounding
signal that measured out to hurt. Neither new candidate is wired into
`token_ceiling_formula.py` yet — both still need the same
validate-before-integrate treatment every signal in this pass has gone
through, this time against real review-unit/finder-unit data rather than
another pass over the same six retired build-unit numbers. Full
breakdown table and reasoning:
[`results/2026-08-22-signal-candidates-by-subagent-archetype.md`](results/2026-08-22-signal-candidates-by-subagent-archetype.md).

## Wiring all six signals into the shipped agent, explicitly, before the two new ones are validated (2026-08-22)

Explicit instruction to have the model-right-sizer itself derive all six
real-work signals for every archetype and feed them into
`../token_ceiling_formula.py`, rather than leave the archetype breakdown
above as an unintegrated design doc. This is a deliberate departure from
this pass's own "test signal-rating reliability first" sequencing for
`context_ingestion_volume`/`investigative_uncertainty` specifically —
they ship in the schema and the agent's Pass A instructions with their
formula weight still at `0.0` (untested, not tested-and-rejected), on the
premise that requiring every row to rate them is how real calibration
data for them actually accumulates, rather than waiting for a dedicated
experiment that may never get prioritized. `schemas/blueprint.schema.json`
bumped to `1.2` (`budget.real_work_signals`, required whenever
`token_ceiling` is nonzero); the agent's Pass A gained an explicit item 5
(rate all six, guided by a per-archetype table, then derive the ceiling
via `compute_token_ceiling_additive` rather than free-handing it,
disclosing that formula's own `UNVALIDATED` status every time it's used).
Also fixed a real regression this caused: `eval/tuning/knobs.py`'s
`budget_margin` and `dispatch_floor_awareness` knobs anchor on exact
substrings of the agent file's original budget bullet (item 4) — the
first draft of this change rewrote that bullet in place and broke both
anchors (`tests/model_right_sizer/test_tuning_knobs.py` caught it
immediately, 75 failures). Fixed by restoring item 4 verbatim and adding
the new signal-derivation content as a distinct item 5 instead of folding
it into item 4 — the tuning-knob infrastructure from earlier passes still
targets exactly the wording it was built against. Full validator
checklist and pytest (430 passed) run clean; see the plugin `CHANGELOG.md`
for the complete schema/agent/formula diff.

## Re-running the signal-validation experiment with the two new signals — and catching a contamination bug in the process (2026-08-22)

Asked to re-run the `validation_loop_iterations`-style experiment for
`context_ingestion_volume` and `investigative_uncertainty`. The first
attempt self-authored the "blind" draws inline, already holding the real
actual costs and this repo's own write-up explaining exactly why each
unit missed its budget — a suspiciously clean r=0.989 was the tell that
the ratings had been reverse-engineered from the answer, not predicted
blind. Discarded before being reported; re-run properly with three
genuinely independent `Agent`-dispatched raters, each given only a
forward-looking task spec and the signal definitions, no access to real
actuals or this repo's retired write-ups. Result, on the corrected data:
**`investigative_uncertainty` looks promising** (adding it to the
existing 4-signal sum's correlation with real cost: 0.910 → 0.980) while
**`context_ingestion_volume` repeats `validation_loop_iterations`'s exact
dilution failure** (0.910 → 0.880 once summed in, despite a respectable
0.766 standalone correlation). Noise (CV) also came in lower across every
signal than any prior estimate in this pass — itself a signal that
earlier "blind" draws, self-authored the same contaminated way, may have
overstated noise, not just this run's correlation. Also flagged as
structurally circular, not just uninformative: the accuracy-based
comparison on this dataset checks the shipped formula against the exact
six real actuals `ADDITIVE_TOTAL_SPAN` was already fit to, so it proves
nothing either way — only the correlation analysis is real evidence
here. Neither new signal's default weight changed (`0.0` stays correct
for both); `investigative_uncertainty` is now the stronger of the two
candidates for a future fresh-held-out-task validation. Full write-up,
including the contamination catch itself as the headline finding:
[`results/2026-08-22-second-signal-experiment-genuinely-blind.md`](results/2026-08-22-second-signal-experiment-genuinely-blind.md).

## Comparing two passes: `compare_results.py` (2026-08-22)

Up to this point, "did pass N+1 actually beat pass N, and on which rows
specifically" has been answered by a human opening two dated
`*-raw-records.json` files side by side — exactly the kind of judgment
call this whole experiment insists on running by code
(`classify_budget_adherence`, `score_candidate`) rather than by eye.
[`compare_results.py`](compare_results.py) is that discipline applied one
level up, as a small, tested CLI:

- **`load_records(path)`** reads one raw-records file and returns its flat
  list of build records (`{"candidate", "task", "row_id", "model",
  "budgeted_tokens", "actual_raw"}`), stripping out the file's
  `overhead_floors`/`overhead_floor_<model>` map, which neither of the
  other two functions needs.
- **`diff_records(old, new)`** matches records across the two lists on the
  full `(candidate, task, row_id)` triple — not `row_id` alone, since this
  repo's own files reuse the same `row_id` (e.g. `"stage-1"`) across
  different candidates/tasks within one pass — and reports, per key, a
  paired old/new classification (via `classify_budget_adherence`) with a
  `classification_flipped` flag, or `only_in_old`/`only_in_new` for a key
  present on just one side. A row that fails classification (e.g. a
  zero-budget row that still spent tokens) gets an `"error: ..."` string
  instead of aborting the whole diff.
- **`compare_candidates(old, new)`** scores both sides with
  `optimizer.score_candidate` and reports `accuracy_rate_delta` and
  `mean_loss_delta` (the latter `None`, not `nan`, whenever either side is
  all-errors and its `mean_loss` is infinite).
- The **CLI** (`python compare_results.py old.json new.json [--format
  text|json]`) loads both files, runs both comparisons, and prints either
  a compact human-readable summary or the raw JSON.

**Run for real** against the two actual files whose shapes are close
enough to compare: [`results/2026-08-21-pass1-raw-records.json`](results/2026-08-21-pass1-raw-records.json)
(25 records, tasks `t1`/`t4`/`t6`) and [`results/2026-08-21-pass2-raw-records.json`](results/2026-08-21-pass2-raw-records.json)
(7 records, task `t6` only). Pass2's file isn't pass1's exact shape —
its top-level list key is `records`, not `build_results`, and its records
omit `row_id` entirely — but the mismatch is genuinely trivial (a renamed
key, plus a field every one of pass2's records can safely default since
each of its `(candidate, task)` pairs is already unique within the file),
so `load_records` was fixed for real to accept both: it now falls back
from `build_results` to `records`, and fills in `row_id: "default"` when
a record doesn't carry one. Before this fix the CLI crashed outright
(`KeyError: 'build_results'`) on pass2's file — a real bug caught by
actually running the tool, not by reading the code. Two other files in
this directory, `2026-08-22-pass3-4-raw-records.json` and
`2026-08-22-pass5-raw-records.json`, use a substantively different shape
(per-candidate-keyed dicts — `{"pass3": {"<candidate>": {"budgeted",
"raw", "settings"}, ...}}` — with no flat per-task-row list and no
`row_id` concept at all) and were left alone rather than forced to fit;
supporting them is future work, not something worth faking here.

Real output, `--format text`:

```
Comparison: results/2026-08-21-pass1-raw-records.json vs results/2026-08-21-pass2-raw-records.json
Total diff entries: 32
  Classifications flipped: 0
  Only in old: 25
  Only in new: 7
Accuracy rate delta: +0.000000
Mean loss delta: -55.799803
```

Two real findings came out of actually running this, not just reading the
code:

1. **`compare_candidates` (aggregate) is genuinely informative here even
   though `diff_records` (row-level) isn't.** `accuracy_rate` is `0.0` on
   both sides (pass1's and pass2's candidates in this file were all still
   `over_budget` at the ratios recorded — these are early coordinate-ascent
   candidates, not the eventual winner), but `mean_loss` drops from
   `64.23` to `8.43` — a real, large improvement the flat `accuracy_rate`
   alone would have hidden, exactly the tie-break `score_candidate`'s own
   docstring says `mean_loss` exists for.
2. **`diff_records`'s row-level output degenerates to zero matches for
   this particular pair, for a real and non-obvious reason**: `row_id`
   values in this repo's files are freeform per-run stage labels
   generated by that specific dry-run's blueprint (e.g. `"stage-1"`,
   `"row-1"`, `"validate_input_check_1"`, `"build-validation-check"`),
   not a stable identifier for "the same logical stage" across separate
   passes. Even the three candidates pass1 and pass2 genuinely share for
   task `t6` (`budget_margin_1`, `budget_margin_neg1`, `effort_tax_1`)
   carry different `row_id` strings in each pass's file, so every one of
   pass1's 25 records and pass2's 7 records shows up as `only_in_old` /
   `only_in_new` rather than a matched pair — correct behavior per the
   function's own contract (no silent drops; every record is accounted
   for), but a real limitation on how useful row-level diffing is
   *across* passes versus *within* one pass's own candidate sweep, where
   `row_id` is assigned once per row and stays fixed across the
   candidates being compared. Not a bug to fix here — reshaping `row_id`
   into a cross-pass-stable key would need a different kind of alignment
   (by row position or by explicit stage semantics) that these files
   don't currently carry, and forcing one would be exactly the kind of
   silent reshaping this module's own docstring warns against.

## Running the four "Signal & Noise" recommendations for real (2026-08-22)

Direct execution (`create_session` unreachable for the first attempt at
this — 9+ consecutive "service temporarily unavailable" failures; re-run
using the `Agent` tool with the orchestrating session as dispatcher) of
all four recommendations the executive report closed with:

**1 & 2 — a genuinely fresh third held-out task**, built for real (a small
CLI, `compare_results.py`, that diffs two of this program's own results
files — real, useful, not throwaway): `overfitting_guard.HOLDOUT_TASKS`
now has 3 entries. On this fresh data, **`investigative_uncertainty` did
NOT replicate** its first task's improvement — it diluted an already-
near-perfect baseline (0.994 → 0.936), the opposite of the first task's
0.910 → 0.980. Per `model-right-sizer-signal-validation`'s own
pre-registered bar (replicate on a SECOND task before proposing a nonzero
weight), this is a clean miss, not a partial win — the signal's `0.0`
default is now backed by stronger evidence, not weaker. **The additive
formula, by contrast, held up**: `compute_token_ceiling_additive`'s
shipped, UNCHANGED constants classified 3/4 of this fresh data
`within_budget` (vs. the averaged model's proven 0/4) — real, non-circular
confirmation the structural fix generalizes.
`ADDITIVE_CALIBRATION_STATUS` moved from `UNVALIDATED` to "partially
confirmed," not further. Full write-up, including the harness-specific
floor-reconciliation methodology a new dispatch mechanism required:
[`results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md`](results/2026-08-22-fresh-held-out-task-signal-and-formula-validation.md).

**3 — 2 new layer-ablation accuracy cells** (`ibpo` and `budget_thinker`
alone, both on `t6` only — `t4` deliberately excluded to avoid the
decomposition-explosion risk pass 2 already found). Both landed
`over_budget`, and both independently converged on the same haiku-no-
effort pick `baseline` already made for this task shape — real evidence
these two layers alone shape decomposition/ceiling more than model tier,
at least here. A real process mistake was caught mid-run: the first
real build committed its fix directly to the shared, reusable
`cost_allocator.py` fixture, which would have permanently "used up" that
benchmark target for every future `t6` run — caught and reverted before
either fixture change was committed. Full write-up:
[`../ablation/results/2026-08-22-accuracy-sweep-n8.md`](../ablation/results/2026-08-22-accuracy-sweep-n8.md).

**4 — opus/haiku low-end anchors.** Two real, deliberately near-zero-work
dispatches (find and fix one missing docstring-parameter description
each) — `CALIBRATION_STATUS` n increases (opus 2→3, haiku 0→1), but both
points needed real multi-file search to find their own tiny edit, so
they anchor "a small real task with some search," not the theoretical
zero-work floor — too thin (n=1 each) to refit `REAL_WORK_SPAN` from, and
disclosed as such rather than acted on. Haiku is now the consistent weak
link across two independent findings in this pass (this anchor's search
overhead, and the one `compute_token_ceiling_additive` miss on the fresh
task) — the next real investment this module needs is haiku-tier data,
not more sonnet.

All four are permanent regression tests in
`tests/model_right_sizer/test_token_ceiling_formula.py` (the two new
correlation-direction tests use their own dataset, kept separate from the
first task's, specifically so the non-replication can't be silently
averaged away in a shared fixture) and a third `HOLDOUT_TASKS` entry in
`overfitting_guard.py`.
