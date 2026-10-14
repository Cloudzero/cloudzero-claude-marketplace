---
name: model-right-sizer-eval-audit
description: >-
  Measure and improve the EFFECTIVENESS of the model-right-sizer eval suite
  itself (plugins/model-right-sizer/eval/ — the citation-ledger checks and
  the token-economics/reasoning-budget formula functions) via mutation
  testing: programmatically corrupt the ledger and probe the formula
  functions' domain boundaries, run the real checker against every mutant,
  and score the kill/pass rate — the concrete, deterministic metric to
  improve round over round. Every mechanical step (mutation generation,
  execution, scoring) is pure Python; no LLM reasons about whether a mutant
  was caught. Use when someone says "test the eval suite", "how good is our
  checker", "find gaps in check_citations.py", or after any change to
  citation_ledger.json / token_economics.py / reasoning_budget.py /
  check_citations.py — and iteratively: fix what it finds, re-run, repeat
  until the score plateaus.
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-eval-audit — mutation-test the eval suite, then close what it finds

`plugins/model-right-sizer/eval/` checks the agent's research grounding by
code, not by LLM judgment (see [`eval/README.md`](../../eval/README.md)). This
skill answers the next question: **how good is that checker, actually?** A
checker with zero failing tests could still be full of blind spots nobody's
looked for — the four review rounds that shipped `eval/`'s five binding
layers (see the plugin `CHANGELOG.md`) each found one by a human/reviewer
noticing a specific case. This skill turns that noticing into a repeatable,
scriptable sweep: **mutation testing**. Corrupt the thing under test in many
small, mechanical ways, run the real checker against every corruption, and
count how many it catches. A corruption the checker misses — an "escaped
mutant" — is a concrete, reproducible gap, not a vibe.

The engine is [`scripts/mutation_audit.py`](scripts/mutation_audit.py). Two
batteries:

- **Battery A — ledger mutation-kill.** Programmatically mutates
  `citation_ledger.json` entries (formula_expr operator flips / constant
  scaling / variable transposition / term drops; substring corruption;
  `numbers` scaling and low/high inversion; `expected_output` corruption) and
  runs the real `check_citations.py` functions against each mutant.
- **Battery B — formula boundary probing.** A hand-authored table of
  domain-boundary inputs (zero factors, negative exponents, extreme values)
  for every function in `token_economics.py` / `reasoning_budget.py`, each
  with an expected outcome (`raises_valueerror` | `computes_cleanly`) — this
  generalizes the exact bug class two PR review rounds already found by hand
  (a zero factor raised to a negative power leaking a raw `ZeroDivisionError`
  instead of a clean domain error) into a systematic sweep instead of relying
  on someone happening to try the right input next time.

**Effectiveness** = the overall kill/pass rate across both batteries, after
excluding two non-findings that would otherwise pollute the signal:
*equivalent mutants* (a mutation that doesn't actually change behavior — e.g.
`a*b` mutated to `b*a` — detected by evaluating original vs. mutant at a
generic, non-degenerate probe point, independent of whatever's in the ledger)
and *known-accepted escapes* (a reviewed, intentional design choice, named
with a reason in `KNOWN_ACCEPTED_ESCAPES` — not a silent exclusion).

## First real run (worked example, so the next person trusts the number)

Round 1 against a **working** harness — two bugs in the harness itself
(a mutator that silently no-op'd on a root-level AST node, and no equivalent-
mutant detection at all, which together manufactured 21 fake "escapes" out of
25) were found and fixed *before* trusting any score — found **4 real gaps**:
`math.exp(epsilon)` leaking a raw `OverflowError` in both CES production
functions (the same "zero/extreme input leaks a low-level exception instead
of a clean `ValueError`" pattern already fixed twice for K/M/L, just on a
parameter nobody had probed yet); one claim's two `sample_inputs` being too
degenerate (a repeated value, a zeroed-out coefficient) to distinguish a
variable transposition; and `check_arithmetic`'s per-claim-ID allowlist being
blind to a uniform, order-preserving scale of a claim's `numbers`. All four
fixed; round 2 hit 100%; round 3 (a fresh run, no changes) confirmed the
plateau. The full trend lives in
[`eval_audit_history.jsonl`](eval_audit_history.jsonl) — append to it, don't
overwrite it, so the curve stays legible across future runs.

## What to do

1. **Run it.**
   ```
   uv run --no-project plugins/model-right-sizer/skills/model-right-sizer-eval-audit/scripts/mutation_audit.py \
     --history plugins/model-right-sizer/skills/model-right-sizer-eval-audit/eval_audit_history.jsonl
   ```
   Add `-v`/`--verbose` to see every mutant/probe, not just the failing ones.
   Exit code is `0` only when unaccepted escapes are zero — safe to wire into
   a loop or a CI gate later without parsing prose.

2. **Triage every unaccepted escape — root-cause it, don't silence it.** Each
   one is one of:
   - **A real gap in `check_citations.py` or the target functions.** Fix the
     actual layer (add a binding, guard a domain boundary) — this is coding
     work, sized like any other bounded bugfix in this repo (no special
     sub-agent tier needed; every step up to this one is pure deterministic
     script, and this is the one step that takes judgment).
   - **A sample-diversity gap** — the checker's logic is fine, but the
     ledger's own `sample_inputs` happen to be degenerate for this specific
     mutation (two equal values, a zeroed coefficient). Fix: diversify the
     samples in `citation_ledger.json`, not the checker.
   - **A genuinely reviewed, intentional design choice.** Add it to
     `KNOWN_ACCEPTED_ESCAPES` in `mutation_audit.py` with a real reason — and
     remove the entry the moment a later fix actually closes it (this
     happened for free once already: adding a generic numbers-grounding
     check incidentally closed an existing accepted-escape entry).
   - **A bug in the mutation harness itself.** Also real, also worth fixing
     in `mutation_audit.py` directly — the harness is not exempt from the
     same rigor it applies to everything else (see the two harness bugs
     found and fixed during this skill's own first run, above).

3. **Re-run. Repeat.** Each fix round is a step; the effectiveness score is
   the loss you're descending. Append every genuine round to
   `eval_audit_history.jsonl` (via `--history`) so the trend is auditable,
   not just asserted.

4. **Stop when you plateau** — either 100% adjusted effectiveness, or two
   consecutive rounds with the same score and no new escapes left to
   triage (everything remaining is either a `KNOWN_ACCEPTED_ESCAPES` entry
   with a real reason, or an equivalent mutant). Report a plateau as a
   plateau; don't chase a fourth round that can't move the number.

## What this does NOT do

- It does **not** reproduce either cited paper's experiments (no MATH500
  rerun, no control-token retraining) — see `eval/README.md`'s own scoping
  note; this skill is scoped to the CHECKER's effectiveness, one layer up.
- It does **not** achieve airtight, mathematically-proven closure of the
  residual gap `check_citations.py`'s own docstring already names (a
  sufficiently coordinated multi-field edit across `formula_expr`, the
  implementation, `source_variables`, AND `expected_output` simultaneously
  could still slip through). It narrows that gap by finding concrete,
  fixable instances of it; it doesn't formally prove there are none left.
- **The full skill — running `mutation_audit.py` directly, triaging every
  escape, and deciding what to fix — does not run automatically in CI.** It's
  an on-demand / periodic invocation, because triaging an escape (real gap
  vs. sample-diversity issue vs. accepted design vs. harness bug) benefits
  from a human/agent glance at the report before concluding anything, not a
  script that decides for itself. **What DOES run automatically in CI is the
  narrower safety net**: `tests/model_right_sizer/test_mutation_audit.py::test_real_ledger_and_formulas_achieve_full_effectiveness`
  re-runs both batteries against the real ledger/functions on every
  `pytest tests/ -q` and fails the build if effectiveness drops below 100% —
  it locks in the plateau this skill reached, it doesn't perform the
  open-ended triage that got there. If that pytest ever fails, *that's* when
  this skill's full report + triage step is the right next move.
- It does **not** touch `agents/model-right-sizer.md`'s prose directly — a
  finding there routes back through `check_presence`'s existing
  `exact_substring` binding, which this skill exercises but doesn't bypass.

## Related

- [`eval/README.md`](../../eval/README.md) — what the checker itself does and
  why; this skill measures how well it does it.
- [`eval/citation_ledger.json`](../../eval/citation_ledger.json) — the answer
  key Battery A mutates.
- [`eval/check_citations.py`](../../eval/check_citations.py) — the six-check
  program under test.
- [`eval/token_economics.py`](../../eval/token_economics.py) /
  [`reasoning_budget.py`](../../eval/reasoning_budget.py) — the formula
  functions Battery B boundary-probes.
- [`eval_audit_history.jsonl`](eval_audit_history.jsonl) — the committed,
  append-only round-over-round effectiveness trend.
