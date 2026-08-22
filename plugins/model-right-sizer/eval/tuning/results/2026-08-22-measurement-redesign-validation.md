# Measurement redesign — floor characterization and validation

Follow-up to [pass 2](2026-08-21-pass2.md)'s "three ways forward"; this is option 1
(redesign the measurement), chosen and executed on 2026-08-22. Two things done, both via
real dispatch, neither eyeballed: characterize the overhead floor properly, then validate
the redesigned `t6_bounded_wellspecified_fix` real-execution target against it.

## Floor characterization

Prior runs (pass 1, pass 2) reused a single point estimate for the haiku overhead floor
(28,508 tokens, from the 2026-08-21 full-independent-run) and treated any deviation from it
as "floor noise." That conflated two different things. Five fresh, independent, zero-tool-
call haiku dispatches (prompt: `Reply with exactly one word: ok`):

| probe | raw tokens | tool_uses |
|---|---:|---:|
| 1 | 25,668 | 0 |
| 2 | 25,660 | 0 |
| 3 | 25,668 | 0 |
| 4 | 25,668 | 0 |
| 5 | 25,660 | 0 |

Mean 25,664.8, spread 8 tokens. **The floor itself is essentially deterministic** — not the
noisy quantity pass 2 blamed for t6's flat result. Three more probes isolate what actually
varies:

| probe | raw tokens | net of zero-tool floor | tool_uses |
|---|---:|---:|---|
| 1 `Bash` call (`echo ok`) | 27,294 | +1,630 | 1 |
| 3 `Bash` calls (`echo ok` ×3) | 27,473 | +1,809 | 3 |
| 1 `Read` of a real ~230-line `.py` file | 29,714 | +4,050 | 1 |

Going from 0 to 1 tool call costs most of a fixed jump (+1,630); going from 1 to 3 calls of
the *same trivial tool* adds very little more (+179) — the marginal cost is dominated by
which tools get loaded into context at all, not a per-call tax. Reading real, substantive
file content costs much more (+4,050 for one file) and scales with that content's size.

**Conclusion**: pass 2's t6 failure was never about a noisy floor. It was that the real
work the old prompt actually required (invent a trivial function, add one guard clause) was
inherently smaller — a few hundred net tokens — than any `token_ceiling` this rubric would
plausibly assign. The fix is a task whose genuine required work is bigger, not a less noisy
floor.

## Fixture + validation

`t6_bounded_wellspecified_fix` now points at a checked-in fixture,
[`../fixtures/cost_allocator.py`](../fixtures/cost_allocator.py) (+
[`../fixtures/test_cost_allocator.py`](../fixtures/test_cost_allocator.py)) — see
`../ablation/benchmark_tasks.json`'s schema_version 1.2 changelog entry for the task text.
One real haiku dispatch against it, run and then reverted (the fixture ships in its
"broken" — `apply_seat_discount` still unvalidated — state so the task stays usable):

- **Raw**: 34,771 tokens, 7 tool uses (read the target + convention functions, edit the
  guard clause, add two tests, run pytest, confirm 8/8 pass).
  - Read files, ran validation itself, tests genuinely passed — not simulated compliance.
- **Net of the (correctly characterized) zero-tool floor**: 34,771 − 25,664 = **9,107
  tokens**.

That's 9–27× the old, self-invented-scratch-function version of t6 (338–1,046 net tokens
across pass 2's 10 candidates) — comfortably above the floor's own noise band (single-digit
tokens) and in a range where a real `token_ceiling` (a well-calibrated one somewhere in the
7,000–15,000 range, per this one sample) can plausibly land `within_budget`, and a too-tight
or too-loose one can plausibly miss in either direction. Genuine discriminating power,
restored.

## What this does not do

- Does not re-run pass 2 or start passes 3–4 — this validates the *measurement*, not a new
  round of knob tuning. A future pass should re-establish `pass2_current`'s (or whatever the
  current point is) t6 score against the new fixture before taking any coordinate-ascent
  step, since the old t6 scores in `2026-08-21-pass2-report-t6-only.json` are not comparable
  to whatever this fixture produces.
- Does not touch `t1_bulk_classifier` (permanently excluded, structurally unmeasurable via
  full sub-agent dispatch — its per-item budget is smaller than even the zero-tool floor) or
  `t4_interactive_latency_sensitive_chat`'s pass-2 decomposition-explosion problem (a
  separate failure mode this redesign wasn't scoped to fix).
- One sample. Per this project's own "single-draw noise" caveat, this is a validation that
  the new target CAN discriminate, not a fully-powered measurement of any specific knob
  setting yet.
