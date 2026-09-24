# Layer-ablation study — full independent rerun, 2026-08-21

A rerun of [`2026-08-21-pilot-run.md`](2026-08-21-pilot-run.md), executed via
[`../../../skills/model-right-sizer-layer-ablation/SKILL.md`](../../../skills/model-right-sizer-layer-ablation/SKILL.md),
specifically to close the three limitations that pilot disclosed rather than
smoothed over. Same 16-condition × 6-task composition grid; the three fixes
below, and what each one actually changed, are the point of this report —
not a new headline number.

Published as a graphical companion with charts at
<https://claude.ai/code/artifact/406ff937-db28-4417-8ded-c1ff91bd34dc>; this
file is the checked-in record with the exact figures behind it.

## The three fixes, and whether they mattered

### 1. Independent dispatch (session-correlation confound)

The pilot dispatched one sub-agent per **condition**, handling all six tasks
in one session — a cost shortcut the SKILL's own Step 2 already warned
against. This rerun dispatched all **96 (condition × task) cells
independently**, one sub-agent per cell, no session shared across more than
one task. All 96 blueprints validated against
`schemas/blueprint.schema.json` on first or second pass.

**This fix changed a real conclusion, not just the confidence around it.**
The pilot reported `query_shaped_rate` as ~2x higher at baseline (0.188)
than in every layer-bearing condition (0.067–0.083) — reported as one of
the two patterns that "survive the caveats." With independent dispatch,
that pattern **does not replicate**: baseline's `query_shaped_rate`
(0.100, excluding `t1`) now sits mid-pack among all 16 conditions, not
above them —

| condition | query_shaped_rate |
|---|---:|
| token_economics+ibpo+speculative_decoding | 0.158 |
| budget_thinker+speculative_decoding | 0.158 |
| budget_thinker | 0.158 |
| token_economics+speculative_decoding | 0.136 |
| token_economics+ibpo | 0.120 |
| token_economics+budget_thinker | 0.105 |
| ibpo+speculative_decoding | 0.105 |
| token_economics+ibpo+budget_thinker | 0.100 |
| **baseline** | **0.100** |
| ibpo | 0.095 |
| all_four | 0.095 |
| ibpo+budget_thinker+speculative_decoding | 0.067 |
| token_economics+budget_thinker+speculative_decoding | 0.053 |
| ibpo+budget_thinker | 0.050 |
| token_economics | 0.045 |
| speculative_decoding | 0.000 |

The pilot's "adding any citation layer halves query-shaping" claim was most
plausibly the one-session-per-condition confound itself, not a real effect
of the layers — exactly the kind of artifact independent dispatch exists to
catch, and exactly why it's reported here as a correction rather than
dropped quietly.

The other pilot pattern — `mean_difficulty` higher in every layer-bearing
condition than baseline — holds directionally but is far more modest than
the pilot's numbers suggested: baseline 47.6 vs. 48.3–57.6 for the four
single layers (a ~1–10pt spread, not the pilot's ~5–10pt-with-a-43.0-floor
picture). Treat this as a weak, not a strong, signal.

### 2. `token_ceiling` convention clarified (t1/t5 prompts)

`benchmark_tasks.json` moved to schema_version 1.1: `t1` and `t5` now state
explicitly that `token_ceiling` is a **per-item** budget, not a per-campaign
total. This closes the gap that produced a 12,500x swing in the pilot
(200 vs. 2,500,000 for the identical `t1` intent). It does not fix the
underlying ambiguity in `schemas/blueprint.schema.json` itself for a general
fan-out stage — that remains an open follow-up, named again here.

### 3. Accuracy-overhead normalization (control-measured floors)

The pilot's `accuracy_rate` (real-execution measurement) came back `0.0` —
every cell 6–20x "over budget" — because the raw `subagent_tokens` figure
includes the dispatching harness's own fixed overhead (system prompt, tool
schemas), not just the task's own reasoning/output. This rerun measured that
floor directly with two no-op control dispatches before touching any real
accuracy cell:

| control | overhead floor (tokens) |
|---|---:|
| sonnet | 38,401 |
| haiku | 28,508 |

Subtracting the matching floor from each of the 4 real-execution cells
before classifying against `budget.token_ceiling` via
`reasoning_budget.classify_budget_adherence()`:

| condition | task | model | raw actual | normalized actual | budgeted |
|---|---|---|---:|---:|---:|
| baseline | t6 | sonnet | 40,842 | 2,441 | 8,000 |
| baseline | t4 | haiku | 31,452 | 2,944 | 4,000 |
| all_four | t6 | sonnet | 41,081 | 2,680 | 6,000 |
| all_four | t4 | sonnet | 43,290 | 4,889 | 2,000 |

```
n = 4, n_scored = 4
accuracy_rate            = 0.25   (1 of 4 within budget)
over_budget_rate         = 0.25   (1 of 4 over)
under_budget_oversized_rate = 0.50   (2 of 4 — budget set well above real spend)
mean_adherence_ratio     = 0.983
computation_errors       = []
```

Still a 4-cell slice (composition got the full 96-cell grid; accuracy did
not, the same cost tradeoff the pilot named), so this is not a claim about
accuracy at scale — but it is now a real, interpretable number instead of a
measurement artifact reading `0.0` regardless of the layers under test.

## Outcome 1 — isolation (baseline vs. each layer alone, + all_four)

Excluding `t1` (5 tasks/condition), now with true per-cell independence:

| metric | baseline | +Token Economics | +IBPO | +BudgetThinker | +Speculative Decoding | all_four (shipped) |
|---|---:|---:|---:|---:|---:|---:|
| n_rows | 20 | 22 | 21 | 19 | 14 | 21 |
| mean_token_ceiling | 95,950 | 47,568 | 70,429 | 92,053 | 84,857 | 50,571 |
| mean_confidence | 63.7 | 63.4 | 65.0 | 65.5 | 65.4 | 62.3 |
| mean_effectiveness | 58.3 | 60.1 | 63.5 | 59.6 | 68.4 | 65.0 |
| mean_efficiency | 46.3 | 41.6 | 40.5 | 46.3 | 42.2 | 43.5 |
| mean_difficulty | 47.6 | 49.3 | 51.2 | 48.3 | 57.6 | 53.2 |
| query_shaped_rate | 0.100 | 0.045 | 0.095 | 0.158 | 0.000 | 0.095 |

## Outcome 2 — combination (all 16 conditions, full 6-task grid)

Sorted by `mean_token_ceiling` — the clearest non-additive signal in this
data:

| condition | n_rows | mean_token_ceiling |
|---|---:|---:|
| ibpo+speculative_decoding | 21 | 37,334 |
| token_economics+budget_thinker | 20 | 38,508 |
| ibpo+budget_thinker | 21 | 43,348 |
| token_economics | 23 | 45,501 |
| **all_four (shipped)** | 23 | **46,187** |
| token_economics+budget_thinker+speculative_decoding | 20 | 50,360 |
| token_economics+ibpo+speculative_decoding | 21 | 51,198 |
| token_economics+speculative_decoding | 24 | 60,025 |
| ibpo | 22 | 67,236 |
| token_economics+ibpo | 26 | 69,131 |
| ibpo+budget_thinker+speculative_decoding | 16 | 70,362 |
| token_economics+ibpo+budget_thinker | 22 | 75,330 |
| speculative_decoding | 15 | 79,210 |
| budget_thinker | 20 | 87,458 |
| baseline | 21 | 91,398 |
| budget_thinker+speculative_decoding | 20 | 111,810 |

**Why this matters:** if the four layers combined additively, `all_four`
would land somewhere between its four single-layer parents. It doesn't —
it sits near the *cheap* end (46,187), close to `token_economics` alone
(45,501), even though `budget_thinker` alone (87,458) and
`speculative_decoding` alone (79,210) both push the ceiling up, and their
pairing without `token_economics` present (`budget_thinker+speculative_decoding`,
111,810) is the single most expensive condition in the whole grid. The
simplest reading: `token_economics`' cost-minimization framing dominates
the other three layers' ceiling-raising tendencies when all four are
present together — an interaction visible only in the full 16-cell grid,
not from any pairwise or isolation comparison alone. That's the entire
argument for running the combination sweep instead of trusting isolation
results to generalize.

## The clearest single finding: speculative decoding's mention rate is a perfect separator

Grouping all 16 conditions by whether the speculative-decoding layer is
present (`speculative_decoding`, its five pairwise/triple combinations, and
`all_four` — 8 conditions) or absent (baseline plus the other 7 combinations
of the remaining three layers — 8 conditions), and reading each condition's
`lever_mention_rates.speculative_decoding` (does any blueprint row for that
condition mention the lever by name):

| has speculative_decoding layer | mention rate range | conditions |
|---|---|---:|
| yes | 0.042 – 0.158 (every one > 0) | 8 / 8 |
| no | exactly 0.000 (every one) | 8 / 8 |

This is a perfect separator in this data: **no condition without the layer
ever mentions speculative decoding; every condition with it sometimes
does.** Unlike the composition metrics above (means with real overlap
across conditions), this one has zero overlap between the two groups. It's
the strongest evidence in this rerun that the layer is doing something the
baseline agent structurally cannot do on its own — surface a specific,
named, gated serving-layer lever — rather than just restating knowledge a
sufficiently capable model already has.

The qualitative pilot finding on `t4_interactive_latency_sensitive_chat`
(baseline names speculative decoding only as one item in a list and still
downgrades model tier; `all_four` invokes the formal gate — Corollary 3.9,
α > c — by name and keeps the stronger model) is unchanged by independent
dispatch, since it's a single task/pair comparison, not an aggregate; see
[`2026-08-21-pilot-run.md`](2026-08-21-pilot-run.md#the-clearest-single-finding-speculative-decoding's-signature-task-read-qualitatively)
for the full quotes.

## What this rerun still can't show

- **Accuracy is still a 4-cell slice**, not the DESIGN.md default scope
  (36 builds) or the full 96-cell grid. The `0.25` accuracy_rate above is a
  real, correctly-normalized number, not a statistically powered one.
- **`schemas/blueprint.schema.json` still doesn't state the `token_ceiling`
  unit convention** for a general fan-out stage — the benchmark-prompt fix
  (schema_version 1.1) works around this for `t1`/`t5` specifically; the
  schema-level fix is still an open follow-up.
- **Six tasks per condition remains a pilot-scale sample.** The combination
  surface and the SD mention-rate separator are the two findings with the
  least single-task sensitivity (they aggregate across all six tasks per
  condition, or read a binary presence/absence, respectively); the
  isolation table's per-metric means are still six-task pilot numbers, not
  large-sample statistics.

## Raw data

- [`2026-08-21-full-independent-run-report.json`](2026-08-21-full-independent-run-report.json) —
  `composition_metrics()` output for both `composition` (all 6 tasks) and
  `composition_excluding_t1` (5 tasks), all 16 conditions.
- [`2026-08-21-full-independent-run-accuracy.json`](2026-08-21-full-independent-run-accuracy.json) —
  the 4 real-execution cells: raw usage, the two control-measured overhead
  floors, the normalized records, and `accuracy_metrics()`'s output.
