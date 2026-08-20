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
| [`citation_ledger.json`](citation_ledger.json) | The answer key. One entry per cited paper, one sub-entry per claim: the exact source quote, the equation/section it comes from, its raw numbers (if any), and which function implements or checks it. Every formula claim also carries `exact_substring` (what must appear verbatim in the agent file), `formula_expr` + `sample_inputs` (what gets run against the implementation), and `source_variables` (the equation's declared free-variable set, independent of both). Claims that can't be verified from the source excerpt available when this ledger was built are marked `verifiable: false` with a note on what's missing — never silently assumed true. |
| [`token_economics.py`](token_economics.py) | Grounded in [arXiv:2605.09104](https://arxiv.org/abs/2605.09104) ("Token Economics for LLM Agents"). The CES production function (Eq. 1), the cost function (Eq. 2), the overall `min TC s.t. Y ≥ Z` objective (Eq. 3), elasticity of substitution (footnote 4), the shadow-price formulas at single-agent/multi-agent/ecosystem scale (footnote 5), the MRTS-at-optimum condition (Figure 5), and the GraphRAG capital-leverage inequality (§3.4). |
| [`reasoning_budget.py`](reasoning_budget.py) | Grounded in [arXiv:2501.17974](https://arxiv.org/abs/2501.17974) (IBPO) and [arXiv:2508.17196](https://arxiv.org/abs/2508.17196) (BudgetThinker), plus the agent's own literal wall-clock promote/revert gate and Pass-B budget-adherence classification — stated as exact prose in the agent file, so held to the same standard even though they aren't from either paper. |
| [`check_citations.py`](check_citations.py) | Standalone script, four checks: (1) literal substring presence of every citation/claim against `agents/model-right-sizer.md` — this is what binds the AGENT'S OWN PROSE to the ledger, independent of whether the ledger's `source_quote` is itself correct; (2) recomputes every claim with a derivable arithmetic relationship (the IBPO range, the OpenRouter growth multiple); (3) for every claim carrying `formula_expr` + `sample_inputs`, evaluates that literal formula on concrete numbers and diffs it against actually *calling* the function the claim says implements it; (4) for every `formula_expr`, its actual free variables (parsed via `ast`, never executed) must equal the claim's independently-declared `source_variables` — so `formula_expr` and the implementation can't silently drift together in the same wrong direction without also falsifying a third, separately-authored field. Fails loudly on drift in any of the four. |

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
5. **Make a coordinated lie cost more than one field.** `check_formula_claims`
   (implementation vs. formula) and `check_formula_variable_coverage`
   (formula vs. declared variables) are deliberately two separate checks
   fed by three independently-authored things (`token_economics.py`/
   `reasoning_budget.py`, `formula_expr`, `source_variables`) — a change that
   silently drops a term has to falsify more than one of them to pass. This
   is a real increase in assurance, not a proof: it does not machine-verify
   that `source_quote` is itself a faithful transcription of the live arXiv
   PDF. That was checked by hand against the fetched paper at authoring time
   (every equation claim cites its exact figure/equation/footnote for that
   audit trail) and stays a human/primary-source trust boundary — named here
   rather than quietly assumed closed, the same way `verifiable: false`
   names its own gap elsewhere in this file.

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
   names), at least one `sample_inputs` entry, and `source_variables`** (the
   equation's free-variable set, read off `source_quote` independently of
   what you just wrote in `formula_expr`). A `source_quote` and an
   `implemented_by` alone are documentation, not verification — nothing
   actually runs them without these fields (`check_formula_claims` and
   `check_formula_variable_coverage` in `check_citations.py` both skip any
   claim missing `formula_expr`).
4. Implement each formula as a pure function in a module here (a new module
   per paper is fine; don't force an unrelated paper's formulas into an
   existing module's namespace) — and add it to `FORMULA_MODULES` in
   `check_citations.py` if it's a new module.
5. Add a pytest file under `tests/model_right_sizer/` exercising it —
   closed-form values you can hand-check, boundary conditions on any gate/
   threshold, a tamper test proving `check_formula_variable_coverage` catches
   a dropped/invented term (ideally one whose sample value is 0, so you can
   also show `check_formula_claims` alone would have missed it), and (for a
   claim you can't fully verify from the excerpt you have) a test that
   asserts it's *honestly marked* unverifiable rather than silently trusted.
6. Run `check_citations.py` and the full pytest suite before opening the PR.
