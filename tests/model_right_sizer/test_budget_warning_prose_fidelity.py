#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Citation-ledger-style presence check for the token-budget-enforcement feature's
"Between the passes" prose in agents/model-right-sizer.md.

Same discipline test_tuning_knobs.py applies to knobs.py's anchors and
test_citation_fidelity.py applies to citation_ledger.json's exact_substrings: bind
literal strings the agent file's prose claims to be quoting to the actual shipped
artifacts, so a real drift between them fails a test instead of going unnoticed.

Two artifacts are checked here, not just one:
  1. The two "Between the passes" section headings and the verbatim warning-
     template tail must be present character-for-character in the shipped agent
     file -- a plain substring check, no fuzzy matching.
  2. That same tail phrase must ALSO be what `budget_threshold.format_budget_warning()`
     actually returns for concrete inputs -- so the prose and the code are proven to
     agree with each other, not just independently checked against a hand-copied
     expectation that could itself have drifted from either one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "model-right-sizer" / "eval"))
import budget_threshold  # noqa: E402

AGENT_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "plugins"
    / "model-right-sizer"
    / "agents"
    / "model-right-sizer.md"
)
AGENT_TEXT = AGENT_FILE.read_text(encoding="utf-8")

STATUS_LEDGER_HEADING = (
    "### Between the passes — the invoking session is chief of staff over the status ledger"
)
THRESHOLD_WARNING_HEADING = (
    "### Between the passes — the threshold warning goes into the unit's own next turn, not into Pass B"
)

# The verbatim tail of the warning template quoted in the agent file -- everything
# after the {warning_threshold_pct}% placeholder, which is also exactly what
# format_budget_warning() emits as fixed, non-interpolated text (nothing in this
# span depends on the function's arguments).
WARNING_TEMPLATE_TAIL = (
    "Wrap up and report now, or tighten scope to finish within the remaining budget. "
    "If the remaining work genuinely needs more, stop and explicitly ask for "
    "additional budget rather than continuing silently past the ceiling."
)


# ---------------------------------------------------------------------------
# Prose presence: the two section headings and the invariant tail phrase
# ---------------------------------------------------------------------------


def test_status_ledger_heading_is_present_in_the_agent_file():
    assert STATUS_LEDGER_HEADING in AGENT_TEXT


def test_threshold_warning_heading_is_present_in_the_agent_file():
    assert THRESHOLD_WARNING_HEADING in AGENT_TEXT


def test_warning_template_tail_is_present_verbatim_in_the_agent_file():
    assert WARNING_TEMPLATE_TAIL in AGENT_TEXT


# ---------------------------------------------------------------------------
# Prose <-> code agreement: the same tail must be what the function returns
# ---------------------------------------------------------------------------


def test_warning_template_tail_matches_format_budget_warnings_actual_return_value():
    """Bind the prose's quoted tail to the function's real output for concrete
    inputs, rather than checking each independently against a third,
    hand-maintained expectation that could itself drift from either one."""
    message = budget_threshold.format_budget_warning(
        unit_id="unit-budget-threshold-library", actual_tokens=7500, token_ceiling=10000
    )

    assert WARNING_TEMPLATE_TAIL in message
    assert message.endswith(WARNING_TEMPLATE_TAIL)


def test_warning_template_tail_matches_format_budget_warnings_return_value_for_a_second_input_set():
    """A second, differently-shaped input set (custom threshold, different unit id
    and token counts) -- the tail is fixed text with no interpolation in it, so it
    must agree regardless of the arguments that produced the rest of the message."""
    message = budget_threshold.format_budget_warning(
        unit_id="some-other-unit", actual_tokens=550, token_ceiling=1000, warning_threshold_pct=0.5
    )

    assert WARNING_TEMPLATE_TAIL in message
    assert message.endswith(WARNING_TEMPLATE_TAIL)


def test_warning_template_tail_matches_even_at_the_zero_ceiling_degenerate_case():
    """format_budget_warning() has a branch for token_ceiling <= 0 that changes the
    percentage clause entirely ("an undefined percentage of") -- confirm the fixed
    tail survives that branch unchanged too, since it sits after the threshold
    clause, not inside the branch that changes."""
    message = budget_threshold.format_budget_warning(unit_id="zero-budget-unit", actual_tokens=5, token_ceiling=0)

    assert WARNING_TEMPLATE_TAIL in message
    assert message.endswith(WARNING_TEMPLATE_TAIL)
