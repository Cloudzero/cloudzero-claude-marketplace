#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Mutation-testing harness for the model-right-sizer eval suite -- the runtime
engine behind the model-right-sizer-eval-audit skill. See ../SKILL.md for what
this is and how the skill uses it round over round.

Two batteries, both scored the same way (killed/passed vs escaped/failed, no
LLM judgment anywhere in the scoring):

Battery A -- LEDGER MUTATION-KILL. Programmatically mutates
citation_ledger.json entries and runs the REAL check_citations functions
against each mutant:
  - formula_expr: operator flips (+/-, */÷, </>), constant scaling, variable
    transposition, additive-term drops -- run through check_formula_claims
    and check_formula_variable_coverage.
  - citation_substring / exact_substring: single-character corruption -- run
    through check_presence.
  - numbers: every numeric leaf scaled by 1000x -- run through
    check_arithmetic.
  - expected_output: value corruption -- run through check_formula_claims (a
    vacuity check: confirms the checker isn't a tautology that always passes
    regardless of ledger content).
A mutant "escapes" if the relevant check function returns zero errors
mentioning its claim_id. Some escapes are known, reviewed, and intentional
(see KNOWN_ACCEPTED_ESCAPES) -- those are reported, not scored as failures.
Anything else that escapes is a concrete gap.

Battery B -- FORMULA BOUNDARY PROBING. A hand-authored table of domain-
boundary inputs for token_economics.py / reasoning_budget.py functions, each
with an expected outcome (raises_valueerror | computes_cleanly). A probe that
gets a *different* exception type than expected (a raw ZeroDivisionError /
OverflowError leak) or the wrong presence/absence of an exception is a
concrete gap -- this is exactly the bug class two rounds of PR review found
by hand (K/M zero-base, L**beta zero-base); this battery generalizes that
search to every function and a wider boundary grid instead of relying on a
human happening to try the right input.

"Effectiveness" is the overall kill/pass rate across both batteries, adjusted
for known accepted escapes -- the metric the skill's dogfooding loop tracks
round over round until it plateaus.

Usage:
  uv run --no-project plugins/model-right-sizer/skills/model-right-sizer-eval-audit/scripts/mutation_audit.py
  uv run --no-project ... mutation_audit.py --history eval_audit_history.jsonl
  uv run --no-project ... mutation_audit.py -v   # list every mutant/probe, not just escapes/failures
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# .../skills/model-right-sizer-eval-audit/scripts/mutation_audit.py -> plugin root -> eval/
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVAL_DIR = PLUGIN_ROOT / "eval"
sys.path.insert(0, str(EVAL_DIR))
import check_citations  # noqa: E402
import reasoning_budget  # noqa: E402
import token_economics  # noqa: E402

# ---------------------------------------------------------------------------
# Known, reviewed, intentional escapes -- named here so they're visible in
# every report, not silently excluded. Remove an entry the moment a fix
# actually closes it; adding an entry without a `reason` is not allowed by
# the reporting code below.
#
# Empty as of round 2: the one entry this registry used to carry
# (ibpo-accuracy-per-compute-ratio's `numbers.ratio` going unchecked by
# check_arithmetic, because it's hardcoded to two other claim_ids) was closed
# for free by adding check_numbers_grounded_in_exact_substring, which checks
# every numbers-bearing claim generically rather than by claim_id allowlist.
# That claim's `verifiable: false` flag stays -- it's a different, still-open
# concern (the paper's own self-consistency baseline figure is unsourced),
# not the same thing as "is this number grounded in what's quoted."
# ---------------------------------------------------------------------------
KNOWN_ACCEPTED_ESCAPES: dict[tuple[str, str], str] = {}


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Battery A -- AST-level formula_expr mutators. Each takes a formula_expr
# string and yields (mutant_expr, description) pairs -- one mutation per
# mutant, so a killed/escaped verdict points at exactly one change.
# ---------------------------------------------------------------------------

_BINOP_FLIPS = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Div, ast.Div: ast.Mult}
_COMPARE_FLIPS = {ast.Lt: ast.Gt, ast.Gt: ast.Lt, ast.LtE: ast.GtE, ast.GtE: ast.LtE}


class _Renamer(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]):
        self.mapping = mapping

    def visit_Name(self, node: ast.Name):  # noqa: N802 (ast.NodeTransformer's own naming convention)
        if node.id in self.mapping:
            return ast.copy_location(ast.Name(id=self.mapping[node.id], ctx=node.ctx), node)
        return node


def mutate_flip_binop(expr: str) -> list[tuple[str, str]]:
    """+/- and */÷ flips, one at a time."""
    mutants = []
    base = ast.parse(expr, mode="eval")
    targets = [n for n in ast.walk(base) if isinstance(n, ast.BinOp) and type(n.op) in _BINOP_FLIPS]
    for i in range(len(targets)):
        tree = copy.deepcopy(base)
        node = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and type(n.op) in _BINOP_FLIPS][i]
        before = type(node.op).__name__
        node.op = _BINOP_FLIPS[type(node.op)]()
        mutants.append((ast.unparse(tree), f"flipped operator {before} -> {type(node.op).__name__}"))
    return mutants


def mutate_flip_compare(expr: str) -> list[tuple[str, str]]:
    """</> and <=/>= flips, one comparison operator at a time."""
    mutants = []
    base = ast.parse(expr, mode="eval")
    compares = [n for n in ast.walk(base) if isinstance(n, ast.Compare)]
    for ci in range(len(compares)):
        for oi, op in enumerate(compares[ci].ops):
            if type(op) not in _COMPARE_FLIPS:
                continue
            tree = copy.deepcopy(base)
            node = [n for n in ast.walk(tree) if isinstance(n, ast.Compare)][ci]
            before = type(node.ops[oi]).__name__
            node.ops[oi] = _COMPARE_FLIPS[type(node.ops[oi])]()
            mutants.append((ast.unparse(tree), f"flipped comparison {before} -> {type(node.ops[oi]).__name__}"))
    return mutants


def mutate_scale_constants(expr: str) -> list[tuple[str, str]]:
    """Every numeric literal, perturbed by +1, one at a time."""
    mutants = []
    base = ast.parse(expr, mode="eval")
    targets = [
        n for n in ast.walk(base) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
        and not isinstance(n.value, bool)
    ]
    for i in range(len(targets)):
        tree = copy.deepcopy(base)
        node = [
            n for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
            and not isinstance(n.value, bool)
        ][i]
        before = node.value
        node.value = before + 1
        mutants.append((ast.unparse(tree), f"perturbed constant {before!r} -> {node.value!r}"))
    return mutants


def mutate_transpose_variables(expr: str) -> list[tuple[str, str]]:
    """Every pair of distinct free variables, swapped throughout the expression."""
    mutants = []
    base = ast.parse(expr, mode="eval")
    names = sorted({n.id for n in ast.walk(base) if isinstance(n, ast.Name)} - {"math"})
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            tree = ast.fix_missing_locations(_Renamer({a: b, b: a}).visit(copy.deepcopy(base)))
            mutants.append((ast.unparse(tree), f"transposed {a} <-> {b}"))
    return mutants


def mutate_drop_additive_term(expr: str) -> list[tuple[str, str]]:
    """Collapse a +/- node to just one of its operands, one node at a time."""
    mutants = []
    base = ast.parse(expr, mode="eval")
    targets = [n for n in ast.walk(base) if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub))]
    for i in range(len(targets)):
        for side in ("left", "right"):
            tree = copy.deepcopy(base)
            node = [n for n in ast.walk(tree) if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub))][i]
            replacement = getattr(node, side)
            if node is tree.body:
                # node IS the whole expression -- there's no parent to splice
                # into, so the "mutant" is simply the replacement subtree on
                # its own. (An earlier version of this function silently
                # no-op'd here via _replace_child's root guard, producing a
                # "mutant" that was actually a formatting-only restatement of
                # the original -- found by running this harness against
                # itself and seeing several "escapes" that turned out to be
                # semantically identical to the unmutated formula.)
                mutant_tree = ast.Expression(body=replacement)
            else:
                _replace_child(tree.body, node, replacement)
                mutant_tree = tree
            mutants.append((ast.unparse(mutant_tree), f"dropped the {'right' if side == 'left' else 'left'} term at node {i}"))
    return mutants


def _replace_child(root: ast.AST, old: ast.AST, new: ast.AST) -> bool:
    """Find `old` among root's direct children (recursively) and replace it with
    `new` in place, including when `old` is root's own body itself."""
    if root is old:
        # Caller must handle the root-is-target case itself; this branch only
        # matters for non-root callers below.
        return False
    for field, value in ast.iter_fields(root):
        if value is old:
            setattr(root, field, new)
            return True
        if isinstance(value, list):
            for idx, item in enumerate(value):
                if item is old:
                    value[idx] = new
                    return True
        if isinstance(value, ast.AST) and _replace_child(value, old, new):
            return True
    return False


FORMULA_MUTATORS = {
    "flip_binop": mutate_flip_binop,
    "flip_compare": mutate_flip_compare,
    "scale_constant": mutate_scale_constants,
    "transpose_variables": mutate_transpose_variables,
    "drop_additive_term": mutate_drop_additive_term,
}


# ---------------------------------------------------------------------------
# Equivalent-mutant detection. A mutation that doesn't change the FORMULA's
# behavior at all (a commutative reorder like a*b -> b*a, or an algebraic
# rearrangement like x/y < z -> x/z < y for positive y, z) is a well-known
# mutation-testing phenomenon called an "equivalent mutant" -- it isn't a gap
# in the checker, and scoring it as an escape would just be noise. Detected
# by evaluating original vs. mutant at a fixed, generic, all-distinct-nonzero
# probe point (independent of whatever samples happen to be in the ledger) --
# NOT the same thing as "the ledger's own samples happen not to distinguish
# them," which is a real, separate, actionable finding (a sample-diversity
# gap) surfaced further down when a genuinely non-equivalent mutant still
# escapes the real checker.
# ---------------------------------------------------------------------------

_GENERIC_PROBE_VALUES = [2.0, 3.0, 5.0, 7.0, 11.0, 13.0, 17.0, 19.0, 23.0, 29.0, 31.0, 37.0]


def _generic_probe_inputs(expr: str) -> dict:
    tree = ast.parse(expr, mode="eval")
    names = sorted({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} - {"math"})
    if len(names) > len(_GENERIC_PROBE_VALUES):
        raise ValueError(f"formula has more free variables than generic probe values: {names}")
    return dict(zip(names, _GENERIC_PROBE_VALUES))


def is_equivalent_mutant(original_expr: str, mutant_expr: str) -> bool:
    """True only if both expressions evaluate to the same result at a
    generic, non-degenerate probe point -- a real semantic no-op, not a
    coincidence of whatever specific numbers happen to live in the ledger.
    Anything that fails to evaluate at all is treated as NOT equivalent (a
    broken mutant is a real, distinguishable difference, never a false
    alarm to suppress)."""
    try:
        inputs = _generic_probe_inputs(original_expr)
        namespace = {"math": math, "__builtins__": {}}
        original_value = eval(original_expr, dict(namespace), dict(inputs))  # noqa: S307
        mutant_value = eval(mutant_expr, dict(namespace), dict(inputs))  # noqa: S307
    except Exception:
        return False
    if isinstance(original_value, bool) or isinstance(mutant_value, bool):
        return bool(original_value) == bool(mutant_value)
    try:
        return math.isclose(original_value, mutant_value, rel_tol=1e-9, abs_tol=1e-9)
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# Battery A -- runners. Each returns a list of result dicts:
# {claim_id, mutator, description, killed, errors}
# ---------------------------------------------------------------------------


def run_formula_mutants(ledger: dict) -> list[dict]:
    results = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            formula_expr = claim.get("formula_expr")
            if formula_expr is None:
                continue
            claim_id = claim["claim_id"]
            # A mutation the mutator can't even generate (e.g. no BinOp to flip)
            # is not a finding either way -- skip mutators that produce nothing.
            for mutator_name, mutator in FORMULA_MUTATORS.items():
                try:
                    mutants = mutator(formula_expr)
                except SyntaxError:
                    continue
                for mutant_expr, description in mutants:
                    if mutant_expr == formula_expr:
                        continue  # a no-op mutation (e.g. transposing a var with itself); not a finding
                    if is_equivalent_mutant(formula_expr, mutant_expr):
                        results.append(
                            {
                                "battery": "A",
                                "target": "formula_expr",
                                "claim_id": claim_id,
                                "mutator": mutator_name,
                                "description": description,
                                "equivalent": True,
                                "killed": None,
                                "errors": [],
                            }
                        )
                        continue
                    tampered = copy.deepcopy(ledger)
                    t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
                    t_claim = next(c for c in t_paper["claims"] if c["claim_id"] == claim_id)
                    t_claim["formula_expr"] = mutant_expr
                    errors = check_citations.check_formula_claims(tampered) + check_citations.check_formula_variable_coverage(tampered)
                    relevant = [e for e in errors if claim_id in e]
                    results.append(
                        {
                            "battery": "A",
                            "target": "formula_expr",
                            "claim_id": claim_id,
                            "mutator": mutator_name,
                            "description": description,
                            "killed": bool(relevant),
                            "errors": relevant,
                        }
                    )
    return results


def run_substring_mutants(ledger: dict, agent_text: str) -> list[dict]:
    results = []
    for paper in ledger["papers"]:
        tampered = copy.deepcopy(ledger)
        t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
        t_paper["citation_substring"] = t_paper["citation_substring"][:-1] + "#"
        errors = check_citations.check_presence(tampered, agent_text)
        relevant = [e for e in errors if paper["id"] in e or paper["short_name"] in e]
        results.append(
            {
                "battery": "A",
                "target": "citation_substring",
                "claim_id": paper["id"],
                "mutator": "corrupt_last_char",
                "description": f"corrupted {paper['short_name']}'s citation_substring",
                "killed": bool(relevant),
                "errors": relevant,
            }
        )
        for claim in paper.get("claims", []):
            substring = claim.get("exact_substring")
            if substring is None or claim.get("appears_in_agent_file", True) is False:
                continue  # nothing to mutate, or deliberately unchecked by design
            claim_id = claim["claim_id"]
            tampered = copy.deepcopy(ledger)
            t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
            t_claim = next(c for c in t_paper["claims"] if c["claim_id"] == claim_id)
            t_claim["exact_substring"] = substring[:-1] + "#"
            errors = check_citations.check_presence(tampered, agent_text)
            relevant = [e for e in errors if claim_id in e]
            results.append(
                {
                    "battery": "A",
                    "target": "exact_substring",
                    "claim_id": claim_id,
                    "mutator": "corrupt_last_char",
                    "description": "corrupted exact_substring's last character",
                    "killed": bool(relevant),
                    "errors": relevant,
                }
            )
    return results


def _scale_numeric_leaves(obj, factor: float):
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float)):
        return obj * factor if obj != 0 else factor
    if isinstance(obj, dict):
        return {k: _scale_numeric_leaves(v, factor) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scale_numeric_leaves(v, factor) for v in obj]
    return obj


def _find_low_high_pairs(numbers: dict) -> list[tuple[str, str]]:
    """Heuristic pairing off this ledger's own naming convention (`_low`/
    `_high`, `start_`/`end_`) -- a uniform scale mutator can't stress-test an
    ORDERING invariant (scaling preserves order), so claims whose check is
    about ordering need their paired fields swapped instead."""
    pairs = []
    for key in numbers:
        if key.endswith("_low"):
            high_key = key[: -len("_low")] + "_high"
            if high_key in numbers:
                pairs.append((key, high_key))
        elif key.startswith("start_"):
            end_key = "end_" + key[len("start_") :]
            if end_key in numbers:
                pairs.append((key, end_key))
    return pairs


def run_numbers_mutants(ledger: dict) -> list[dict]:
    results = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            numbers = claim.get("numbers")
            if numbers is None:
                continue
            claim_id = claim["claim_id"]

            tampered = copy.deepcopy(ledger)
            t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
            t_claim = next(c for c in t_paper["claims"] if c["claim_id"] == claim_id)
            t_claim["numbers"] = _scale_numeric_leaves(numbers, 1000.0)
            errors = check_citations.check_arithmetic(tampered) + check_citations.check_numbers_grounded_in_exact_substring(tampered)
            relevant = [e for e in errors if claim_id in e]
            results.append(
                {
                    "battery": "A",
                    "target": "numbers",
                    "claim_id": claim_id,
                    "mutator": "scale_1000x",
                    "description": "scaled every numeric leaf in `numbers` by 1000x (order-preserving)",
                    "killed": bool(relevant),
                    "errors": relevant,
                }
            )

            for low_key, high_key in _find_low_high_pairs(numbers):
                tampered = copy.deepcopy(ledger)
                t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
                t_claim = next(c for c in t_paper["claims"] if c["claim_id"] == claim_id)
                t_claim["numbers"][low_key], t_claim["numbers"][high_key] = (
                    t_claim["numbers"][high_key],
                    t_claim["numbers"][low_key],
                )
                errors = check_citations.check_arithmetic(tampered) + check_citations.check_numbers_grounded_in_exact_substring(tampered)
                relevant = [e for e in errors if claim_id in e]
                results.append(
                    {
                        "battery": "A",
                        "target": "numbers",
                        "claim_id": claim_id,
                        "mutator": "invert_order",
                        "description": f"swapped {low_key} <-> {high_key}",
                        "killed": bool(relevant),
                        "errors": relevant,
                    }
                )
    return results


def run_expected_output_mutants(ledger: dict) -> list[dict]:
    """Vacuity check: corrupting expected_output should ALWAYS be caught -- if
    it isn't, the checker is tautological (always agrees with itself) rather
    than actually diffing against an independent value."""
    results = []
    for paper in ledger["papers"]:
        for claim in paper.get("claims", []):
            samples = claim.get("sample_inputs")
            if not samples:
                continue
            claim_id = claim["claim_id"]
            for i, sample in enumerate(samples):
                if "expected_output" not in sample:
                    continue
                tampered = copy.deepcopy(ledger)
                t_paper = next(p for p in tampered["papers"] if p["id"] == paper["id"])
                t_claim = next(c for c in t_paper["claims"] if c["claim_id"] == claim_id)
                original = t_claim["sample_inputs"][i]["expected_output"]
                t_claim["sample_inputs"][i]["expected_output"] = (
                    not original if isinstance(original, bool) else (original + 1000)
                )
                errors = check_citations.check_formula_claims(tampered)
                relevant = [e for e in errors if claim_id in e]
                results.append(
                    {
                        "battery": "A",
                        "target": "expected_output",
                        "claim_id": claim_id,
                        "mutator": "corrupt_value",
                        "description": f"corrupted sample[{i}]'s expected_output",
                        "killed": bool(relevant),
                        "errors": relevant,
                    }
                )
    return results


# ---------------------------------------------------------------------------
# Battery B -- formula boundary probes. Each entry: call `fn(**kwargs)` and
# check whether the outcome matches `expect`.
# ---------------------------------------------------------------------------

BOUNDARY_PROBES = [
    # ces_production
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=0, M=16, L=1, delta=0.5, rho=-1.0, theta=1, beta=0),
         expect="raises_valueerror", reason="K=0 with rho<0 -- 0**negative is undefined"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=0, L=1, delta=0.5, rho=-1.0, theta=1, beta=0),
         expect="raises_valueerror", reason="M=0 with rho<0 -- 0**negative is undefined"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=0, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0),
         expect="computes_cleanly", reason="K=0 with rho>0 is well-defined (0**positive == 0)"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=16, L=1, delta=0.5, rho=0, theta=1, beta=0),
         expect="raises_valueerror", reason="rho=0 is the Cobb-Douglas limit, not a value this fn accepts"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=16, L=0, delta=0.5, rho=0.5, theta=1, beta=-1.0),
         expect="raises_valueerror", reason="L=0 with beta<0 -- 0**negative is undefined"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=16, L=0, delta=0.5, rho=0.5, theta=1, beta=0.0),
         expect="computes_cleanly", reason="L=0 with beta=0 is well-defined (L**0 == 1)"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0, epsilon=1000),
         expect="raises_valueerror", reason="extreme epsilon overflows math.exp -- should be a clean domain error"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=4, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0, epsilon=-1000),
         expect="computes_cleanly", reason="a very negative epsilon underflows math.exp to 0.0, no exception"),
    dict(target="ces_production", fn=token_economics.ces_production,
         kwargs=dict(K=-1, M=16, L=1, delta=0.5, rho=0.5, theta=1, beta=0),
         expect="raises_valueerror", reason="negative factor quantities are out of domain"),
    # ces_production_cobb_douglas_limit
    dict(target="ces_production_cobb_douglas_limit", fn=token_economics.ces_production_cobb_douglas_limit,
         kwargs=dict(K=0, M=9, L=1, delta=0.5, theta=2, beta=0),
         expect="raises_valueerror", reason="Cobb-Douglas requires strictly positive K, M"),
    dict(target="ces_production_cobb_douglas_limit", fn=token_economics.ces_production_cobb_douglas_limit,
         kwargs=dict(K=4, M=9, L=0, delta=0.5, theta=2, beta=-1.0),
         expect="raises_valueerror", reason="L=0 with beta<0, same boundary as ces_production"),
    dict(target="ces_production_cobb_douglas_limit", fn=token_economics.ces_production_cobb_douglas_limit,
         kwargs=dict(K=4, M=9, L=1, delta=0.5, theta=2, beta=0, epsilon=1000),
         expect="raises_valueerror", reason="extreme epsilon overflows math.exp"),
    # nested_ces_M
    dict(target="nested_ces_M", fn=token_economics.nested_ces_M,
         kwargs=dict(M_int=0, M_ext=5, delta_m=0.5, rho_m=-1.0),
         expect="raises_valueerror", reason="M_int=0 with rho_m<0"),
    dict(target="nested_ces_M", fn=token_economics.nested_ces_M,
         kwargs=dict(M_int=5, M_ext=0, delta_m=0.5, rho_m=-1.0),
         expect="raises_valueerror", reason="M_ext=0 with rho_m<0"),
    dict(target="nested_ces_M", fn=token_economics.nested_ces_M,
         kwargs=dict(M_int=5, M_ext=5, delta_m=0.5, rho_m=0),
         expect="raises_valueerror", reason="rho_m=0 is the Cobb-Douglas limit"),
    dict(target="nested_ces_M", fn=token_economics.nested_ces_M,
         kwargs=dict(M_int=-1, M_ext=5, delta_m=0.5, rho_m=0.5),
         expect="raises_valueerror", reason="negative token counts are out of domain"),
    # elasticity_of_substitution / classify_substitution_regime
    dict(target="elasticity_of_substitution", fn=token_economics.elasticity_of_substitution,
         kwargs=dict(rho=1.0), expect="raises_valueerror", reason="sigma diverges to +inf at rho=1"),
    dict(target="classify_substitution_regime", fn=token_economics.classify_substitution_regime,
         kwargs=dict(rho=1.0), expect="computes_cleanly", reason="special-cased boundary, must not raise"),
    # mrts_target / marginal_rate_of_technical_substitution
    dict(target="mrts_target", fn=token_economics.mrts_target,
         kwargs=dict(P_ext_shadow=0.03, P_int_shadow=0.0),
         expect="raises_valueerror", reason="division by zero shadow price"),
    dict(target="marginal_rate_of_technical_substitution", fn=token_economics.marginal_rate_of_technical_substitution,
         kwargs=dict(M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5, step=0),
         expect="raises_valueerror", reason="a zero finite-difference step is meaningless"),
    dict(target="marginal_rate_of_technical_substitution", fn=token_economics.marginal_rate_of_technical_substitution,
         kwargs=dict(M_int=4, M_ext=9, delta_m=0.4, rho_m=0.5),
         expect="computes_cleanly", reason="typical, away-from-boundary inputs"),
    # graphrag_capital_leverage_justified
    dict(target="graphrag_capital_leverage_justified", fn=token_economics.graphrag_capital_leverage_justified,
         kwargs=dict(I_graph=1000, Q=0, delta_Y=0.2),
         expect="raises_valueerror", reason="can't amortize over zero query volume"),
    # openrouter_growth_multiple
    dict(target="openrouter_growth_multiple", fn=token_economics.openrouter_growth_multiple,
         kwargs=dict(start_trillion=0.0, end_trillion=27.0),
         expect="raises_valueerror", reason="division by zero start value"),
    # total_cost / shadow prices / pareto -- control probes, should never raise
    dict(target="total_cost", fn=token_economics.total_cost,
         kwargs=dict(K=1, M=1, L=1, P_k=1, P_m=1, w=1), expect="computes_cleanly", reason="typical inputs"),
    dict(target="shadow_price_multi_agent", fn=token_economics.shadow_price_multi_agent,
         kwargs=dict(P_m=0, w=0, tau_sync=0, delta_c_coord=0), expect="computes_cleanly", reason="an all-zero input is a valid (if trivial) cost"),
    dict(target="clears_quality_bar", fn=token_economics.clears_quality_bar,
         kwargs=dict(Y=0, Z=0), expect="computes_cleanly", reason="boundary equality is a valid, inclusive pass"),
    # reasoning_budget
    dict(target="budget_adherence_ratio", fn=reasoning_budget.budget_adherence_ratio,
         kwargs=dict(actual_tokens=5, budgeted_tokens=0), expect="raises_valueerror", reason="a zero-budget row that spent tokens must be reported, not divided by zero"),
    dict(target="budget_adherence_ratio", fn=reasoning_budget.budget_adherence_ratio,
         kwargs=dict(actual_tokens=-5, budgeted_tokens=100), expect="computes_cleanly", reason="not currently guarded against negative actual spend -- documents present behavior, not a specified requirement"),
    dict(target="agentic_downpin_gate", fn=reasoning_budget.agentic_downpin_gate,
         kwargs=dict(measured_wallclock=100, ambient_baseline_wallclock=0), expect="raises_valueerror", reason="division by zero baseline"),
    dict(target="accuracy_per_compute", fn=reasoning_budget.accuracy_per_compute,
         kwargs=dict(delta_accuracy_pct=4.14, budget_multiplier=0), expect="raises_valueerror", reason="division by zero budget multiplier"),
    dict(target="ibpo_accuracy_per_compute_gain", fn=reasoning_budget.ibpo_accuracy_per_compute_gain,
         kwargs=dict(baseline_accuracy_per_compute=0, ibpo_accuracy_per_compute=2.0), expect="raises_valueerror", reason="division by zero baseline"),
    dict(target="budget_control_token_reward", fn=reasoning_budget.budget_control_token_reward,
         kwargs=dict(accuracy=0.5, budget_adherence_score=0.5, weight_accuracy=0.9, weight_adherence=0.9),
         expect="raises_valueerror", reason="weights that don't sum to 1 shouldn't silently compute"),
]


def run_boundary_probes() -> list[dict]:
    results = []
    for probe in BOUNDARY_PROBES:
        outcome, exc_type, exc_msg = None, None, None
        try:
            probe["fn"](**probe["kwargs"])
            outcome = "computes_cleanly"
        except ValueError as e:
            outcome = "raises_valueerror"
            exc_msg = str(e)
        except Exception as e:  # noqa: BLE001 -- exactly what we're hunting for
            outcome = "raises_other"
            exc_type = type(e).__name__
            exc_msg = str(e)
        passed = outcome == probe["expect"]
        results.append(
            {
                "battery": "B",
                "target": probe["target"],
                "kwargs": probe["kwargs"],
                "expected": probe["expect"],
                "actual": outcome if outcome != "raises_other" else f"raises_{exc_type}",
                "reason": probe["reason"],
                "killed": passed,  # reuse the same field name as battery A for uniform scoring
                "errors": [] if passed else [f"expected {probe['expect']}, got {outcome} ({exc_type}: {exc_msg})"],
            }
        )
    return results


# ---------------------------------------------------------------------------
# Scoring + reporting
# ---------------------------------------------------------------------------


def score(results: list[dict]) -> dict:
    """Equivalent mutants (`killed is None`) are excluded from `total` entirely
    -- they're not a scored dimension at all, informational only. Everything
    else is either killed, a known-accepted escape (reviewed, named, not
    counted against effectiveness), or an unaccepted escape (a real gap)."""
    equivalents = [r for r in results if r.get("equivalent")]
    scored = [r for r in results if not r.get("equivalent")]
    total = len(scored)
    killed = sum(1 for r in scored if r["killed"])
    accepted = [
        r for r in scored
        if not r["killed"] and (r["target"], r["claim_id"] if "claim_id" in r else r["target"]) in KNOWN_ACCEPTED_ESCAPES
    ]
    unaccepted_escapes = [r for r in scored if not r["killed"] and r not in accepted]
    adjusted_killed = killed + len(accepted)
    return {
        "total": total,
        "killed": killed,
        "accepted_escapes": len(accepted),
        "unaccepted_escapes": len(unaccepted_escapes),
        "equivalent_mutants": len(equivalents),
        "raw_kill_rate": killed / total if total else 1.0,
        "effectiveness": adjusted_killed / total if total else 1.0,
        "escape_details": unaccepted_escapes,
        "accepted_details": accepted,
        "equivalent_details": equivalents,
    }


def print_report(battery_a: list[dict], battery_b: list[dict], verbose: bool) -> dict:
    all_results = battery_a + battery_b
    overall = score(all_results)
    a_score = score(battery_a)
    b_score = score(battery_b)

    print(f"Battery A (ledger mutation-kill): {a_score['killed']}/{a_score['total']} killed "
          f"({a_score['effectiveness']:.1%} effectiveness, {a_score['accepted_escapes']} known-accepted)")
    print(f"Battery B (formula boundary probes): {b_score['killed']}/{b_score['total']} passed "
          f"({b_score['effectiveness']:.1%} effectiveness)")
    print(f"OVERALL effectiveness: {overall['effectiveness']:.1%} "
          f"({overall['killed']}/{overall['total']} + {overall['accepted_escapes']} accepted)")
    print()

    if overall["escape_details"]:
        print(f"=== {len(overall['escape_details'])} UNACCEPTED ESCAPE(S)/FAILURE(S) -- concrete gaps ===")
        for r in overall["escape_details"]:
            label = r.get("claim_id", r.get("target"))
            print(f"  FAIL [{r['battery']}/{r['target']}] {label}: {r['description'] if 'description' in r else r.get('reason', '')}")
            for e in r["errors"]:
                print(f"        -> {e}")
    else:
        print("No unaccepted escapes or failures.")

    if overall["accepted_details"]:
        print(f"\n=== {len(overall['accepted_details'])} known-accepted escape(s) (reviewed, not scored as gaps) ===")
        for r in overall["accepted_details"]:
            key = (r["target"], r.get("claim_id", r["target"]))
            print(f"  ACCEPTED [{r['battery']}/{r['target']}] {key[1]}: {KNOWN_ACCEPTED_ESCAPES[key]}")

    if overall["equivalent_mutants"]:
        print(f"\n{overall['equivalent_mutants']} equivalent mutant(s) excluded from scoring "
              f"(mathematically identical to the original at a generic probe point -- not a checker gap).")
        if verbose:
            for r in overall["equivalent_details"]:
                print(f"  EQUIVALENT [{r['battery']}/{r['target']}] {r['claim_id']}: {r['description']}")

    if verbose:
        print(f"\n=== all {len(all_results)} mutants/probes ===")
        for r in all_results:
            status = "EQUIVALENT" if r.get("equivalent") else ("KILLED" if r["killed"] else "ESCAPED")
            label = r.get("claim_id", r.get("target"))
            print(f"  {status} [{r['battery']}/{r['target']}] {label}: {r.get('description', r.get('reason', ''))}")

    return overall


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true", help="list every mutant/probe, not just escapes")
    parser.add_argument("--history", type=Path, default=None, help="append this round's score as a JSONL line")
    args = parser.parse_args()

    ledger = check_citations.load_ledger()
    agent_text = check_citations.load_agent_text()

    battery_a = (
        run_formula_mutants(ledger)
        + run_substring_mutants(ledger, agent_text)
        + run_numbers_mutants(ledger)
        + run_expected_output_mutants(ledger)
    )
    battery_b = run_boundary_probes()

    overall = print_report(battery_a, battery_b, args.verbose)

    if args.history:
        round_number = 1
        if args.history.exists():
            round_number = sum(1 for _ in args.history.open()) + 1
        with args.history.open("a") as f:
            f.write(
                json.dumps(
                    {
                        "round": round_number,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "overall_effectiveness": overall["effectiveness"],
                        "raw_kill_rate": overall["killed"] / overall["total"] if overall["total"] else 1.0,
                        "total": overall["total"],
                        "unaccepted_escapes": overall["unaccepted_escapes"],
                        "accepted_escapes": overall["accepted_escapes"],
                    }
                )
                + "\n"
            )
        print(f"\nAppended round {round_number} to {args.history}")

    return 0 if overall["unaccepted_escapes"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
