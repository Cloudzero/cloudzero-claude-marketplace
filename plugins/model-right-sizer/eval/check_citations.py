#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Cross-check every numeric/formula claim in citation_ledger.json against
agents/model-right-sizer.md and against the deterministic implementations in
token_economics.py / reasoning_budget.py.

This is the mechanical half of keeping the agent's research grounding honest --
it does six things, none of them by LLM judgment:

  1. Presence check: every paper's `citation_substring`, and every claim's
     `exact_substring` (unless explicitly marked `appears_in_agent_file: false`),
     must appear character-for-character in agents/model-right-sizer.md. This is
     what binds the AGENT'S OWN PROSE to this ledger -- a claim's `source_quote`
     is the paper's wording, but the ledger only ever reads the agent file
     through this check, so a formula mistranscribed in the agent's markdown
     (a wrong exponent, a dropped term) fails here even if source_quote and
     formula_expr both stay correct.
  2. Arithmetic check: every claim that names a `numbers` dict with a derivable
     relationship (the IBPO gain/budget range, the OpenRouter growth multiple)
     gets recomputed via the eval library and compared to the claimed figure
     within a stated tolerance -- not re-derived by an LLM reading the prose.
  3. Formula-vs-implementation check: every claim that names a `formula_expr` +
     `sample_inputs` gets that literal expression evaluated on each sample's
     `inputs` and compared against actually *calling* the function it claims to
     implement (`module.primary_function(**inputs)`). This is what makes
     `source_quote` an enforced contract instead of documentation: a
     `source_quote` and an `implemented_by` naming a function are not, on their
     own, checked against anything -- this closes that gap by running both
     sides on concrete numbers and diffing them, for every formula claim, not a
     hand-picked couple.
  4. Formula-vs-declared-variables check: every claim that names `formula_expr`
     also names `source_variables` -- the free-variable set a human reading
     `source_quote` says the equation should contain. `formula_expr`'s actual
     free variables (parsed via `ast`, not eval'd) must equal that declared
     set exactly. This catches a dropped or invented term that (3) alone
     wouldn't, if the implementation was edited to match.
  5. Formula-vs-expected-output check: each sample also carries an
     `expected_output` -- computed by hand from the paper's confirmed-correct
     `source_quote`, independently of `formula_expr` and the implementation.
     Both `formula_expr`'s evaluation AND the implementation's return value are
     diffed against it. This is what (3) and (4) together still can't catch:
     `formula_expr` and the implementation being edited TOGETHER to the same
     wrong structure (a sign flip, a swapped pairing) that keeps the same
     variable names and so still passes (4). A coordinated two-way drift no
     longer passes silently, because `expected_output` lives in a third place
     neither edit touches.
  6. Numbers-grounded-in-prose check: every claim with BOTH `numbers` and
     `exact_substring` has each numeric leaf checked for literal presence in
     `exact_substring`. Found by mutation testing: (2)'s per-claim arithmetic
     checks assert INTERNAL properties (ordering, no-raise-on-a-derived-calc),
     not that the values match the cited text -- a uniform 1000x scale of
     every numeric leaf preserves ordering and passes (2) silently, even
     though it no longer matches a single digit of what's actually quoted.
     Mutation-tested and found wanting, not merely reasoned about.

A claim marked `verifiable: false` is reported as such, not silently skipped --
see citation_ledger.json's own notes for why each one is unverifiable from the
sources this ledger was built from. That flag is about fidelity to the paper;
checks (3)-(5) still run for such a claim if it carries a `formula_expr`,
because "is this code internally consistent with what the ledger says it
implements" is a separate question from "is this claim verified against the
paper's own source."

What none of this verifies: that `source_quote` itself is a faithful
transcription of the actual paper. That was checked by hand against the fetched
arXiv PDF at authoring time (each claim cites its exact equation/footnote/figure
reference for that audit trail), and `expected_output` was derived from that
same confirmed-correct source_quote -- so this is still a residual
human/primary-source trust boundary, the same one `verifiable: false` names
elsewhere in this file, not a claim that any finite set of cross-checks makes
it impossible for a sufficiently coordinated edit to slip through. Each round
of review on this file has narrowed that residual gap (implementation binding,
then agent-prose + declared-variable binding, then this independently-computed
third value); it narrows further with more/harder-to-fake bindings, but never
reaches a formal proof without re-deriving the paper's math from an independent
symbolic source, which is out of scope here.

Usage:
  uv run --no-project plugins/model-right-sizer/eval/check_citations.py
"""
from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reasoning_budget  # noqa: E402
import token_economics  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
LEDGER_PATH = EVAL_DIR / "citation_ledger.json"
AGENT_FILE_PATH = EVAL_DIR.parent / "agents" / "model-right-sizer.md"

# The only modules a claim's `module` field may name -- deliberately closed,
# not a dynamic import, so a ledger entry can't point formula_expr evaluation
# at an arbitrary module.
FORMULA_MODULES = {"token_economics": token_economics, "reasoning_budget": reasoning_budget}

# Absolute tolerance for "the recomputed figure should land within this much of
# the claimed one" -- loose enough to cover a paper's own rounding ("nearly
# 68-fold" for an exact 67.5), tight enough to catch a real transcription error.
GROWTH_MULTIPLE_TOLERANCE = 1.0


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def load_ledger() -> dict:
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


def load_agent_text() -> str:
    return AGENT_FILE_PATH.read_text(encoding="utf-8")


def check_presence(ledger: dict, agent_text: str) -> list[str]:
    """Part 1: literal substring presence, no fuzzy matching."""
    errors: list[str] = []
    for paper in ledger["papers"]:
        cite = paper["citation_substring"]
        if cite not in agent_text:
            errors.append(
                f"{paper['id']} ({paper['short_name']}): citation_substring {cite!r} "
                f"not found in {AGENT_FILE_PATH.name}"
            )
        for claim in paper.get("claims", []):
            substring = claim.get("exact_substring")
            if substring is None:
                continue
            if claim.get("appears_in_agent_file", True) is False:
                continue
            if substring not in agent_text:
                errors.append(
                    f"{paper['id']} claim {claim['claim_id']!r}: exact_substring "
                    f"{substring!r} not found in {AGENT_FILE_PATH.name}"
                )
    return errors


def check_arithmetic(ledger: dict) -> list[str]:
    """Part 2: recompute every claim this ledger knows how to recompute, and
    diff it against the claimed number. Unknown claim_ids are left alone here
    (they're still covered by the presence check above) rather than guessed at."""
    errors: list[str] = []
    claims_by_id = {
        claim["claim_id"]: claim
        for paper in ledger["papers"]
        for claim in paper.get("claims", [])
    }

    ibpo = claims_by_id.get("ibpo-math500-gain-and-budget")
    if ibpo is not None:
        n = ibpo["numbers"]
        if not (n["gain_pct_low"] <= n["gain_pct_high"]):
            errors.append("ibpo-math500-gain-and-budget: gain_pct_low > gain_pct_high")
        if not (n["budget_multiplier_low"] <= n["budget_multiplier_high"]):
            errors.append("ibpo-math500-gain-and-budget: budget_multiplier_low > budget_multiplier_high")
        for label, gain, budget in (
            ("low", n["gain_pct_low"], n["budget_multiplier_low"]),
            ("high", n["gain_pct_high"], n["budget_multiplier_high"]),
        ):
            try:
                reasoning_budget.accuracy_per_compute(gain, budget)
            except ValueError as e:
                errors.append(f"ibpo-math500-gain-and-budget[{label}]: {e}")

    growth = claims_by_id.get("te-openrouter-growth")
    if growth is not None:
        n = growth["numbers"]
        computed = token_economics.openrouter_growth_multiple(n["start_trillion"], n["end_trillion"])
        if abs(computed - n["claimed_multiple"]) > GROWTH_MULTIPLE_TOLERANCE:
            errors.append(
                f"te-openrouter-growth: computed {n['end_trillion']}/{n['start_trillion']} = "
                f"{computed:.2f}, more than {GROWTH_MULTIPLE_TOLERANCE} away from the claimed "
                f"{n['claimed_multiple']}-fold"
            )

    return errors


def _numeric_string_candidates(value: float) -> set[str]:
    """str(value), plus str(int(value)) when value is a whole-number float --
    a claim's prose often drops the trailing '.0' ('~2x', not '~2.0x')."""
    candidates = {str(value)}
    if isinstance(value, float) and value.is_integer():
        candidates.add(str(int(value)))
    return candidates


def check_numbers_grounded_in_exact_substring(ledger: dict) -> list[str]:
    """Part 6: for every claim carrying BOTH `numbers` and `exact_substring`,
    every numeric leaf in `numbers` must appear, formatted as a plain string,
    somewhere in `exact_substring`. This exists because check_arithmetic's
    per-claim checks assert INTERNAL properties (ordering, no-raise-on-a-
    derived-calculation), not that the values match what's actually quoted --
    found by mutation testing: uniformly scaling every numeric leaf by 1000x
    preserves ordering and so passes check_arithmetic silently, even though
    not a single scaled digit still matches the cited text.

    Deliberately does NOT skip `appears_in_agent_file: false` claims (unlike
    check_presence) -- that flag is about whether `exact_substring` appears in
    the AGENT FILE, a different question from whether `numbers` and
    `exact_substring` agree with EACH OTHER inside the ledger. A claim like
    te-openrouter-growth never shows up in the agent's markdown, but its own
    `numbers` should still match its own `exact_substring` -- skipping it here
    was an early bug (copied from check_presence's skip without checking
    whether it actually applied), caught by a test asserting this check finds
    a tampered value on exactly that claim.

    Known, named limitation: a literal substring match, not a tokenized one --
    a wrong value that happens to be a PREFIX of the correct one embedded in a
    longer number (claiming 4.1 when the text says 4.14) would still match.
    Reliable against gross drift (a unit error, an order of magnitude, a
    transcription slip); not a proof of exact correctness.
    """
    errors: list[str] = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            numbers = claim.get("numbers")
            substring = claim.get("exact_substring")
            if numbers is None or substring is None:
                continue
            claim_id = claim["claim_id"]
            for key, value in numbers.items():
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    continue
                candidates = _numeric_string_candidates(value)
                if not any(c in substring for c in candidates):
                    errors.append(
                        f"{claim_id}: numbers.{key} = {value!r} -- none of {sorted(candidates)} "
                        f"appear in exact_substring {substring!r}"
                    )
    return errors


def _values_differ(a, b) -> bool:
    """Bool-aware equality: a bare `a != b` on 1 vs True would pass when it
    shouldn't matter, and math.isclose on two bools works but reads oddly --
    branch explicitly instead of relying on Python's numeric/bool coercion.

    `math.isclose` itself raises TypeError on a complex operand -- reachable
    in practice, not just in theory: a mutated formula_expr can raise a
    negative base to a fractional power, which Python evaluates as a complex
    number instead of raising. Any such incomparable pair is treated as a
    definite mismatch (True) rather than letting the exception escape and
    crash the caller -- found by mutation-testing this function itself.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) != bool(b)
    try:
        return not math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
    except TypeError:
        return True


def check_formula_claims(ledger: dict) -> list[str]:
    """Part 3: for every claim carrying `formula_expr` + `sample_inputs`, and
    for each sample (`{"inputs": {...}, "expected_output": <value>}`), do
    THREE pairwise comparisons, not just one:

      (a) formula_expr evaluated on `inputs`  vs.  `expected_output`
      (b) module.primary_function(**inputs)   vs.  `expected_output`
      (c) formula_expr evaluated on `inputs`  vs.  module.primary_function(**inputs)

    (c) alone (the original version of this check) only proves formula_expr
    and the implementation agree with EACH OTHER -- it says nothing if both
    were edited together to the same wrong formula. `expected_output` is
    computed by hand from the paper's confirmed-correct source_quote,
    independently of both, and stored in a third place neither of those two
    edits touches -- so (a) and (b) are what actually catch a coordinated
    drift, not (c). All three run regardless; a claim only passes when none
    of the three pairs disagree.

    Runs for every claim with a `formula_expr`, regardless of `verifiable` --
    that flag is about fidelity to the paper's own source; this check is
    about whether the shipped code matches what THIS ledger says it
    implements, which is a separate and always-applicable question.
    """
    errors: list[str] = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            formula_expr = claim.get("formula_expr")
            if formula_expr is None:
                continue
            claim_id = claim["claim_id"]
            module_name = claim.get("module")
            fn_name = claim.get("primary_function")
            module = FORMULA_MODULES.get(module_name)
            if module is None:
                errors.append(
                    f"{claim_id}: formula_expr is present but `module` is {module_name!r}, "
                    f"not one of {sorted(FORMULA_MODULES)}"
                )
                continue
            fn = getattr(module, fn_name or "", None)
            if fn is None:
                errors.append(f"{claim_id}: {module_name}.{fn_name} does not exist")
                continue
            samples = claim.get("sample_inputs") or []
            if not samples:
                errors.append(f"{claim_id}: formula_expr is present but sample_inputs is empty")
                continue
            for i, sample in enumerate(samples):
                if "inputs" not in sample or "expected_output" not in sample:
                    errors.append(
                        f"{claim_id} sample[{i}]: must have both 'inputs' and 'expected_output' keys, "
                        f"got {sorted(sample.keys())}"
                    )
                    continue
                inputs = sample["inputs"]
                expected = sample["expected_output"]
                try:
                    expr_value = eval(formula_expr, {"math": math, "__builtins__": {}}, dict(inputs))  # noqa: S307
                except Exception as e:
                    errors.append(f"{claim_id} sample[{i}]: formula_expr {formula_expr!r} failed to evaluate: {e!r}")
                    continue
                try:
                    fn_value = fn(**inputs)
                except Exception as e:
                    errors.append(f"{claim_id} sample[{i}]: {module_name}.{fn_name}(**{inputs}) raised {e!r}")
                    continue
                if _values_differ(expr_value, expected):
                    errors.append(
                        f"{claim_id} sample[{i}]: formula_expr -> {expr_value!r}, "
                        f"but expected_output (independently computed) -> {expected!r}"
                    )
                if _values_differ(fn_value, expected):
                    errors.append(
                        f"{claim_id} sample[{i}]: {module_name}.{fn_name}(**inputs) -> {fn_value!r}, "
                        f"but expected_output (independently computed) -> {expected!r}"
                    )
                if _values_differ(expr_value, fn_value):
                    errors.append(
                        f"{claim_id} sample[{i}]: formula_expr -> {expr_value!r}, "
                        f"{module_name}.{fn_name}(**inputs) -> {fn_value!r}"
                    )
    return errors


def _free_variable_names(expr: str) -> set[str]:
    """Parse `expr` as a Python expression and return the set of names it
    references, minus `math` (the only module formula_expr is allowed to
    touch, per FORMULA_MODULES' eval namespace). Does not execute anything --
    this is a static AST walk, so a formula_expr that would raise at eval time
    can still be coverage-checked."""
    tree = ast.parse(expr, mode="eval")
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} - {"math"}


def check_formula_variable_coverage(ledger: dict) -> list[str]:
    """Part 4: for every claim carrying `formula_expr`, its actual free
    variables (per _free_variable_names) must equal the claim's declared
    `source_variables` exactly -- no fewer (a silently dropped term) and no
    more (an invented one). `source_variables` is authored by reading
    `source_quote`, independently of formula_expr and of the implementation,
    so this is a check formula_expr can't pass by agreeing with itself."""
    errors: list[str] = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            formula_expr = claim.get("formula_expr")
            if formula_expr is None:
                continue
            claim_id = claim["claim_id"]
            declared = claim.get("source_variables")
            if declared is None:
                errors.append(f"{claim_id}: has formula_expr but no source_variables to check it against")
                continue
            try:
                actual = _free_variable_names(formula_expr)
            except SyntaxError as e:
                errors.append(f"{claim_id}: formula_expr {formula_expr!r} is not a parseable expression: {e}")
                continue
            declared_set = set(declared)
            missing = declared_set - actual  # declared as part of the equation, but formula_expr doesn't use it
            extra = actual - declared_set  # formula_expr uses it, but it isn't in the declared equation
            if missing or extra:
                detail = []
                if missing:
                    detail.append(f"formula_expr is missing {sorted(missing)}")
                if extra:
                    detail.append(f"formula_expr references undeclared {sorted(extra)}")
                errors.append(f"{claim_id}: {'; '.join(detail)} (declared source_variables={sorted(declared_set)})")
    return errors


def report_unverifiable(ledger: dict) -> list[str]:
    """Not a failure -- a required acknowledgement. Returns one line per claim
    explicitly marked unverifiable, so main() can print them and a reviewer can
    see at a glance which claims still need a primary-source figure."""
    lines = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            if claim.get("verifiable") is False:
                lines.append(
                    f"UNVERIFIED (expected): {paper['short_name']} / {claim['claim_id']} -- "
                    f"{claim.get('verification_note', 'no note given')}"
                )
    return lines


def main() -> int:
    if not LEDGER_PATH.exists():
        fail(f"{LEDGER_PATH} does not exist")
        return 1
    if not AGENT_FILE_PATH.exists():
        fail(f"{AGENT_FILE_PATH} does not exist")
        return 1

    ledger = load_ledger()
    agent_text = load_agent_text()

    errors = (
        check_presence(ledger, agent_text)
        + check_arithmetic(ledger)
        + check_formula_claims(ledger)
        + check_formula_variable_coverage(ledger)
        + check_numbers_grounded_in_exact_substring(ledger)
    )
    if errors:
        for e in errors:
            fail(e)
        return 1

    for line in report_unverifiable(ledger):
        print(line)

    n_papers = len(ledger["papers"])
    n_claims = sum(len(p.get("claims", [])) for p in ledger["papers"])
    print(f"OK: {n_papers} paper(s), {n_claims} claim(s) checked against {AGENT_FILE_PATH.relative_to(EVAL_DIR.parent.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
