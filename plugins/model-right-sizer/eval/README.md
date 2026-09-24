# model-right-sizer research-formula evals

`agents/model-right-sizer.md` cites four published results and states, in
prose, formulas and numeric claims it assumes hold. This directory is where
those claims stop being prose and become code — every formula the agent's
rubric leans on is implemented here as a pure function, and every numeric
claim tied to a citation is checked against a committed answer key. The
governing rule: **math is verified by running code, not by an LLM
re-deriving it in its head.**

## Files

| File | What it is |
|---|---|
| [`citation_ledger.json`](citation_ledger.json) | The answer key. One entry per cited paper, one sub-entry per claim: the exact source quote, the equation/section it comes from, its raw numbers (if any), and which function implements or checks it. Every formula claim also carries `exact_substring` (what must appear verbatim in the agent file), `source_variables` (the equation's declared free-variable set), and `formula_expr` + `sample_inputs` where each sample is `{"inputs": {...}, "expected_output": <value>}` — `expected_output` computed by hand from the paper's confirmed-correct formula, independently of both `formula_expr` and the implementation. Claims that can't be verified from the source excerpt available when this ledger was built are marked `verifiable: false` with a note on what's missing — never silently assumed true. |
| [`token_economics.py`](token_economics.py) | Grounded in [arXiv:2605.09104](https://arxiv.org/abs/2605.09104) ("Token Economics for LLM Agents"). The CES production function (Eq. 1), the cost function (Eq. 2), the overall `min TC s.t. Y ≥ Z` objective (Eq. 3), elasticity of substitution (footnote 4), the shadow-price formulas at single-agent/multi-agent/ecosystem scale (footnote 5), the MRTS-at-optimum condition (Figure 5), and the GraphRAG capital-leverage inequality (§3.4). |
| [`reasoning_budget.py`](reasoning_budget.py) | Grounded in [arXiv:2501.17974](https://arxiv.org/abs/2501.17974) (IBPO) and [arXiv:2508.17196](https://arxiv.org/abs/2508.17196) (BudgetThinker), plus the agent's own literal wall-clock promote/revert gate and Pass-B budget-adherence classification — stated as exact prose in the agent file, so held to the same standard even though they aren't from either paper. |
| [`speculative_decoding.py`](speculative_decoding.py) | Grounded in [arXiv:2211.17192](https://arxiv.org/abs/2211.17192) ("Fast Inference from Transformers via Speculative Decoding", Leviathan, Kalman & Matias, ICML 2023). The expected-tokens-per-iteration formula (Eq. 1), the expected walltime-improvement factor (Theorem 3.8), the gate and guaranteed minimum bound for whether the technique helps at all (Corollary 3.9), the always-≥1 total-arithmetic-operations increase factor (Theorem 3.11), and the acceptance-rate-from-distributions formula (Corollary 3.6, kept for completeness but not quoted in the agent's own prose — see its ledger entry's `appears_in_agent_file: false`). |
| [`check_citations.py`](check_citations.py) | Standalone script, five checks: (1) literal substring presence of every citation/claim against `agents/model-right-sizer.md` — binds the AGENT'S OWN PROSE to the ledger; (2) recomputes every claim with a derivable arithmetic relationship; (3) evaluates each formula claim's `formula_expr` on every sample's `inputs` and diffs it against actually *calling* the function the claim says implements it; (4) `formula_expr`'s actual free variables (parsed via `ast`, never executed) must equal the claim's independently-declared `source_variables`; (5) both `formula_expr`'s evaluation AND the implementation's return value are diffed against each sample's independently-computed `expected_output` — this is what (3)+(4) together still can't catch: `formula_expr` and the implementation edited TOGETHER to the same wrong structure (a sign flip, a swapped pairing) that keeps the same variable names. Fails loudly on drift in any of the five. Note that (3)'s eval sandbox (`{"math": math, "__builtins__": {}}`) only accepts bare arithmetic/comparison expressions — a claim whose equation needs a blocked builtin (e.g. `speculative_decoding.acceptance_rate`'s `sum`/`min` reduction over a list) is documented in the ledger with `source_quote`/`implemented_by` and pinned by the pytest suite instead of carrying an unrunnable `formula_expr`; its own ledger note says so. |

Corresponding pytest suites live at the repo root, under
[`tests/model_right_sizer/`](../../../tests/model_right_sizer/) — see that
directory for the actual test cases; this directory holds only the library
code and the answer key they exercise.

## Running it

```
uv run --no-project plugins/model-right-sizer/eval/check_citations.py
uv run --no-project --with pytest -- pytest tests/model_right_sizer/ -q
```

Both are included in this repo's standard validation command set — see the
root `CLAUDE.md`.

## Why this exists (and what it deliberately doesn't do)

This is **not** a reproduction of either paper's experiments — nothing here
reruns MATH500, retrains a control-token model, or fits a CES production
function to real telemetry. That's a different, much larger undertaking than
"does model-right-sizer's grounding say what it claims to say."

What it *does* do:

1. **Guard against citation drift.** If a future edit to `agents/model-right-sizer.md`
   changes a cited number (a typo, a copy-paste of the wrong figure, an LLM
   "helpfully" rounding `4.14` to `4`), `check_citations.py` and the pytest
   suite catch it — because the check is a string/arithmetic comparison, not
   a re-read of the prose.
2. **Make the assumed formulas testable.** The agent's rubric says things like
   "a `high`-effort mid-tier model can beat a `low`-effort top-tier model" and
   "schema debt is real debt" — plain-language claims that arXiv:2605.09104
   formalizes as factor substitution and a shadow-price term, respectively.
   `token_economics.py` turns that formalization into functions with unit
   tests, so the *relationship* (not just the citation) is exercised.
3. **Say what's unverified, not paper over it.** IBPO's "~2× the
   accuracy-per-compute of self-consistency" claim needs a baseline number
   this ledger doesn't have. Rather than assume the ratio or drop the claim,
   `citation_ledger.json` marks it `verifiable: false` and names exactly what
   sourcing it would take — the same "never assert a number from memory"
   discipline the agent itself is instructed to follow for model pricing.
4. **Catch the agent's own prose drifting from what it cites.** This is not
   hypothetical: an earlier version of the CES production function in
   `agents/model-right-sizer.md` read `K^p`/`M^p` (a stray superscript-p)
   instead of `K^ρ`/`M^ρ`, and nothing caught it, because neither
   `source_quote` nor `formula_expr` was ever checked against the agent
   file's actual text. `exact_substring` on every formula claim closes that:
   the agent's markdown is read through the same presence check as every
   other citation, not assumed consistent with the ledger just because both
   exist in the same repo.
5. **Make a coordinated lie cost more than two fields.** `check_formula_claims`,
   `check_formula_variable_coverage`, and the `expected_output` diff are three
   separate checks fed by FOUR independently-authored things
   (`token_economics.py`/`reasoning_budget.py`, `formula_expr`,
   `source_variables`, `expected_output`) — a change that silently drops a
   term, or edits `formula_expr` and the implementation together to the same
   wrong structure, has to falsify more than one of them to pass. This is a
   real, repeatedly-narrowed increase in assurance, not a proof: it does not
   machine-verify that `source_quote` is itself a faithful transcription of
   the live arXiv PDF, and `expected_output` was derived from that same
   `source_quote` rather than from an independent oracle. That fidelity was
   checked by hand against the fetched paper at authoring time (every
   equation claim cites its exact figure/equation/footnote for that audit
   trail) and stays a human/primary-source trust boundary — named here rather
   than quietly assumed closed, the same way `verifiable: false` names its
   own gap elsewhere in this file. Fully closing it would mean re-deriving
   the paper's math from an independent symbolic source at CI time, which is
   a materially larger undertaking than this file takes on.

## Extending this for a new paper

When another research result gets added as a grounding layer:

1. Add a `papers[]` entry to `citation_ledger.json` with every numeric claim
   or formula it's cited for, quoting the source exactly (`source_quote`,
   with its equation/section/figure reference — this is the part a human
   checks against the actual paper; there's no way to automate that step).
2. **Add the agent's own compact formula text to the agent file, then set
   `exact_substring` to that exact string** (character-for-character,
   copy-pasted from the file, not retyped by hand — that's exactly how the
   `K^ρ`/`K^p` typo happened). This is what binds the agent's prose to the
   ledger; skip it and a future transcription error in the markdown has
   nothing to catch it.
3. **For every equation-referencing claim, add `module`, `primary_function`,
   `formula_expr` (a literal Python expression over the sample's variable
   names), and `source_variables`** (the equation's free-variable set, read
   off `source_quote` independently of what you just wrote in `formula_expr`).
   A `source_quote` and an `implemented_by` alone are documentation, not
   verification — nothing actually runs them without these fields.
4. **For each `sample_inputs` entry, use the shape
   `{"inputs": {...}, "expected_output": <value>}`, and compute
   `expected_output` independently** — write the formula out longhand in a
   one-off script (not by calling `formula_expr` or the implementation, and
   not by mental arithmetic) and paste the printed number in. This is the
   witness that catches `formula_expr` and the implementation being edited
   TOGETHER to the same wrong structure; skip it and that coordinated-drift
   case passes silently no matter how many other fields you add.
5. Implement each formula as a pure function in a module here (a new module
   per paper is fine; don't force an unrelated paper's formulas into an
   existing module's namespace) — and add it to `FORMULA_MODULES` in
   `check_citations.py` if it's a new module.
6. Add a pytest file under `tests/model_right_sizer/` exercising it —
   closed-form values you can hand-check, boundary conditions on any gate/
   threshold, a tamper test proving `check_formula_variable_coverage` catches
   a dropped/invented term whose sample value is 0 (so `check_formula_claims`
   alone would miss it), a tamper test that monkeypatches the implementation
   AND edits `formula_expr` together to the same wrong structure (so you can
   show the `expected_output` diff is what catches it, not the other checks),
   and (for a claim you can't fully verify from the excerpt you have) a test
   that asserts it's *honestly marked* unverifiable rather than silently
   trusted.
7. Run `check_citations.py` and the full pytest suite before opening the PR.
