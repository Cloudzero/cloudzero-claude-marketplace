# model-right-sizer research-formula evals

`agents/model-right-sizer.md` cites three published results and states, in
prose, formulas and numeric claims it assumes hold. This directory is where
those claims stop being prose and become code — every formula the agent's
rubric leans on is implemented here as a pure function, and every numeric
claim tied to a citation is checked against a committed answer key. The
governing rule, shared with `xdp-tools:math-auditor`: **math is verified by
running code, not by an LLM re-deriving it in its head.**

## Files

| File | What it is |
|---|---|
| [`citation_ledger.json`](citation_ledger.json) | The answer key. One entry per cited paper, one sub-entry per claim: the exact source quote, the equation/section it comes from, its raw numbers (if any), and which function implements or checks it. Claims that can't be verified from the source excerpt available when this ledger was built are marked `verifiable: false` with a note on what's missing — never silently assumed true. |
| [`token_economics.py`](token_economics.py) | Grounded in [arXiv:2605.09104](https://arxiv.org/abs/2605.09104) ("Token Economics for LLM Agents"). The CES production function (Eq. 1), the cost function (Eq. 2), the overall `min TC s.t. Y ≥ Z` objective (Eq. 3), elasticity of substitution (footnote 4), the shadow-price formulas at single-agent/multi-agent/ecosystem scale (footnote 5), the MRTS-at-optimum condition (Figure 5), and the GraphRAG capital-leverage inequality (§3.4). |
| [`reasoning_budget.py`](reasoning_budget.py) | Grounded in [arXiv:2501.17974](https://arxiv.org/abs/2501.17974) (IBPO) and [arXiv:2508.17196](https://arxiv.org/abs/2508.17196) (BudgetThinker), plus the agent's own literal wall-clock promote/revert gate and Pass-B budget-adherence classification — stated as exact prose in the agent file, so held to the same standard even though they aren't from either paper. |
| [`check_citations.py`](check_citations.py) | Standalone script, three checks: (1) literal substring presence of every citation/claim against `agents/model-right-sizer.md`; (2) recomputes every claim with a derivable arithmetic relationship (the IBPO range, the OpenRouter growth multiple); (3) for every claim carrying `formula_expr` + `sample_inputs`, evaluates that literal formula on concrete numbers and diffs it against actually *calling* the function the claim says implements it — this is what makes a claim's `source_quote`/`implemented_by` pair enforced rather than merely documented. Fails loudly on drift in any of the three. |

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

## Extending this for a new paper

When another research result gets added as a grounding layer:

1. Add a `papers[]` entry to `citation_ledger.json` with every numeric claim
   or formula it's cited for, quoting the source exactly. **For every
   equation-referencing claim, also add `module`, `primary_function`,
   `formula_expr` (a literal Python expression over the sample's variable
   names), and at least one `sample_inputs` entry** — a `source_quote` and an
   `implemented_by` alone are documentation, not verification; nothing
   actually runs them without these four fields (`check_formula_claims` in
   `check_citations.py` skips any claim missing `formula_expr`).
2. Implement each formula as a pure function in a module here (a new module
   per paper is fine; don't force an unrelated paper's formulas into an
   existing module's namespace) — and add it to `FORMULA_MODULES` in
   `check_citations.py` if it's a new module.
3. Add a pytest file under `tests/model_right_sizer/` exercising it —
   closed-form values you can hand-check, boundary conditions on any gate/
   threshold, and (for a claim you can't fully verify from the excerpt you
   have) a test that asserts it's *honestly marked* unverifiable rather than
   silently trusted.
4. Run `check_citations.py` and the full pytest suite before opening the PR.
