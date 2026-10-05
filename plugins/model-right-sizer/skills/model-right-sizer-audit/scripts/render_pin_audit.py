#!/usr/bin/env python3
#  SPDX-FileCopyrightText: Copyright (c) CloudZero, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0
"""Deterministic renderer for model-right-sizer-audit's suggestions doc.

Step 4 of skills/model-right-sizer-audit/SKILL.md is a templating job, not a
reasoning job: it joins the discovery sweep's candidate list against
model-right-sizer's Pass A blueprint_rows and prints two markdown tables. It
is written as an f-string renderer, not a model call, because the whole
point of the "Exact edit" column is that it is copy-paste literal — a model
transcribing dozens of rows will occasionally paraphrase or drop one; this
never will. The join (on `candidate_id` / `blueprint_rows[].id`) is necessary
because `blueprint.schema.json` has no file/line/literal field — a
blueprint row describes a model decision, not where in the codebase it
lives, so this candidate list has to carry that mapping itself.

Stdlib only, no external dependency — this is a skill-local utility, not a
library module.

Input shapes (both required, both plain JSON):

  candidates.json — a list of objects, one per discovery-sweep finding:
    {
      "candidate_id": str,           # joins to blueprint_rows[].id
      "file": str,                   # path relative to the TARGET repo root
      "line": int,
      "component": str,              # e.g. "foo agent", "ci:build.yml:test job"
      "current_pin_literal": str,    # the MINIMAL substitutable token — see
                                      #   SKILL.md step 2's minimal-literal rule
      "pin_syntax": str,             # frontmatter_tier_keyword | full_model_id |
                                      #   cli_flag | env_var | bare_value |
                                      #   sdk_string_literal
      "job_description": str
    }

  blueprint.json — model-right-sizer's Pass A output (or just the
  blueprint_rows array) per schemas/blueprint.schema.json: each row carries
  `id`, `keep_or_override`, `pick.primary.{model,effort,confidence}`,
  `pick.runner_up.{model,confidence}`, and `rationale`.

Usage:
  python3 render_pin_audit.py --candidates candidates.json \
      --blueprint blueprint.json --target-label "org/repo" --out audit.md
Prints a one-line JSON of counts ({"found": N, "override": M, "keep": K,
"unmatched": U}) to stdout for the skill's step-7 report.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date

# Tier-keyword extraction is intentionally a dumb substring match — every
# model ID this agent ever emits (claude-opus-5, claude-sonnet-5,
# claude-haiku-4-5, claude-fable-5, and their dated predecessors) contains
# exactly one of these words. If a future model family breaks that pattern,
# this raises instead of guessing.
_TIER_WORDS = ("opus", "sonnet", "haiku", "fable")

# blueprint.schema.json's `modelChoice.model` allows this literal in place of
# a real model ID: "the pick is to route via a deterministic query layer
# instead of a model." A candidate scored this way (e.g. a hardcoded set the
# code should instead read from its own config) has no equivalent *literal*
# on the suggested side — the fix is structural, not a token swap — so every
# helper below that formats a suggested literal must special-case it rather
# than feed it to `_tier_keyword`, which only knows real Claude model IDs.
_DETERMINISTIC_QUERY_LAYER = "deterministic_query_layer"

# `blueprint.schema.json`'s `modelChoice.model` also allows a `local:<model-id>`
# pick: an open-weight model on hardware the operator owns. Like the query
# layer, it has no pasteable counterpart on this side of the swap (you cannot
# pin `model: local:...` in Claude Code frontmatter, and the pick is only valid
# behind the routing gate the agent file describes), so it gets its own label
# rather than being reported as a cross-provider reference, which it is not.
_LOCAL_PREFIX = "local:"


def _tier_keyword(model_id: str) -> str:
    lowered = model_id.lower()
    for word in _TIER_WORDS:
        if word in lowered:
            return word
    raise ValueError(
        f"can't derive a frontmatter tier keyword from model id {model_id!r} "
        "— none of opus/sonnet/haiku/fable appear in it"
    )


def _has_tier_keyword(model_id: str) -> bool:
    """True if `model_id` contains one of the real Claude tier words — the
    same substring check `_tier_keyword` makes, exposed as a boolean so a
    caller can branch on it (`is_cross_provider_pick` in `render()`) without
    a try/except for ordinary control flow."""
    lowered = model_id.lower()
    return any(word in lowered for word in _TIER_WORDS)


def _model_label(model_id: str) -> str:
    """Human-readable label for a `pick.*.model` value, including the one
    non-model sentinel the schema allows (`deterministic_query_layer`).

    Never raises. A cross-provider reference pick (a `gpt-*`, `gemini-*`, ...
    id in `pick.primary.model` or `pick.runner_up.model`) has no Claude tier
    keyword to extract, and that is an expected, documented outcome (SKILL.md
    step 3: "a call whose current model isn't Claude gets a cross-provider
    reference pick"), not a defect worth crashing the whole render over.
    Falls back to the raw id verbatim — the same graceful degradation
    `render_pr_table.py`'s own `_tier_label` already uses for an
    unrecognized id, rather than letting `_tier_keyword`'s ValueError
    propagate out of a display-only helper."""
    if model_id == _DETERMINISTIC_QUERY_LAYER:
        return "deterministic query layer, no model"
    if model_id.startswith(_LOCAL_PREFIX):
        return f"local tier ({model_id[len(_LOCAL_PREFIX):]}), unverified output"
    try:
        return _tier_keyword(model_id)
    except ValueError:
        return model_id


def _format_literal(model_id: str, pin_syntax: str) -> str:
    """Render a suggested model pick in the same idiom as the pin it
    replaces. This is the SUBSTITUTABLE literal only — effort is rendered
    separately (see `_with_effort`, used only for the human-readable
    "Suggested" cell) and never folded in here: most `pin_syntax` values have
    no adjacent "effort:" token in the source file to fold it into, and doing
    so would repeat the exact mistake the `frontmatter_tier_keyword` branch
    below used to make."""
    if pin_syntax == "frontmatter_tier_keyword":
        # Bare tier keyword only. `current_pin_literal` for this pin_syntax
        # is itself the bare value (e.g. "opus"), per SKILL.md step 2's
        # minimal-substitutable-token rule — the frontmatter's `model:` key
        # is not part of what current_pin_literal names, so it can't be part
        # of what replaces it either. Returning "model: {tier}" here used to
        # produce a non-substitutable edit: pasted over the bare token `opus`,
        # it left a duplicated key in the file (`model: model: sonnet`). A
        # candidate on a differently-keyed frontmatter line (e.g. `producer:`)
        # belongs under `bare_value` below instead.
        return _tier_keyword(model_id)
    if pin_syntax == "full_model_id":
        return model_id
    if pin_syntax == "cli_flag":
        return f"--model {model_id}"
    if pin_syntax in ("env_var", "bare_value"):
        # Same rendering — a bare, unwrapped literal with no key/flag/quote
        # around it. `env_var` is the literal case (an environment variable
        # whose whole value is the model id); `bare_value` is the general
        # form for any OTHER unprefixed value token — e.g. the value half
        # of a `producer: claude-opus` line once current_pin_literal has
        # been narrowed to just `claude-opus`, per the minimal-literal rule
        # in SKILL.md step 2. Kept as two enum names because "this came
        # from an env var" and "this is some other repo's bare value" are
        # different discovery-time facts worth recording distinctly, even
        # though they render identically today.
        return model_id
    if pin_syntax == "sdk_string_literal":
        return f'"{model_id}"'
    raise ValueError(f"unknown pin_syntax {pin_syntax!r}")


def _with_effort(label: str, effort: str | None) -> str:
    """Append the effort annotation to a human-readable label — never to an
    `_format_literal` return value. Uses the same ` @{effort}` convention
    `render_pr_table.py`'s `_pick_cell` already established for this plugin,
    so the two renderers agree on how effort reads. This is display-only:
    effort has no reliable adjacent token in the source file for most
    `pin_syntax` values, so it can't be folded into the copy-paste-literal
    "Exact edit" column without risking the same non-substitutable-edit bug
    fixed in `_format_literal` above — surfacing it here (never silently
    dropping it, as this script used to) is the fix that doesn't reintroduce
    that one."""
    return f"{label} @{effort}" if effort else label


def _has_line_break(text: str) -> bool:
    """True if `text` contains ANY line-break form — \\n, \\r\\n, or a lone
    \\r. A bare \\r (old Mac-style line ending, or one that simply slipped
    into an LLM-authored string) is exactly as capable of splitting a GFM
    table row as \\n is; checking only for \\n is how the multiline guard
    in `render()` would silently miss it and hand a lone-\\r literal to
    `_code_span()` believing it was single-line."""
    return "\n" in text or "\r" in text


def _needs_appendix(text: str) -> bool:
    """True if `text` can't go inline in a table cell as a byte-exact code
    span — a line break (handled by `_has_line_break`) or a literal pipe.
    Routing a pipe-containing value to the fenced-code appendix instead of
    `_code_span()` is the fix for a real defect: `_code_span()` escapes a
    pipe with a backslash so the TABLE stays intact, but that means the
    escaped text is no longer the exact literal the "Exact edit" column
    promises — a reader copy-pasting it gets an extra backslash that was
    never in the source file. A fenced code block has no column-boundary
    problem at all, so routing there preserves both properties: the table
    never breaks, AND the appendix shows the true, unaltered literal."""
    return _has_line_break(text) or "|" in text


def _escape_cell(text: str) -> str:
    """Make free text safe to drop into one GFM table cell: escape a pipe so
    it can't be mistaken for a column boundary, and replace every line-break
    form (\\r\\n, \\n, or a lone \\r) with `<br>` (GitHub's table renderer
    supports it) since a raw line break ends the row outright — splitting it
    across the following line with no leading `|`, which corrupts every row
    after it, not just this one. Order matters: collapse the two-character
    \\r\\n sequence before either single-character form, or it becomes two
    `<br>`s instead of one. An LLM-authored rationale is the most likely
    source of any of these: it's free prose, occasionally multi-line, that
    this script never controls the shape of."""
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", "<br>")
        .replace("\n", "<br>")
        .replace("\r", "<br>")
    )


def _code_span(text: str) -> str:
    """Wrap `text` in a Markdown code span, per GFM's code-span rule: use a
    backtick fence one longer than the longest run of backticks already
    inside `text` (CommonMark's own rule for nesting code spans).

    Callers on the main current/suggested path never hand this a
    pipe-containing value — `render()` routes those to the fenced-code
    appendix instead (see `_needs_appendix`), specifically because
    escaping a pipe here would alter the literal (a copy-pasted "exact
    edit" would carry a backslash that was never in the source file). The
    pipe-escape below is kept only as a defensive fallback for this
    function's other caller (`loc`, built from a file path + line number,
    which should never contain a pipe but isn't worth a second code path
    to guarantee).
    """
    text = text.replace("|", "\\|")
    if "`" not in text:
        return f"`{text}`"
    longest_run = max(len(run) for run in re.findall(r"`+", text))
    fence = "`" * (longest_run + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _diff_fence(*blocks: str) -> str:
    """Pick a fenced-code-block backtick length that safely encloses every
    block, per the same nesting rule as `_code_span` — a discovered pin
    literal could itself contain a run of backticks long enough to break
    out of a fixed ``` fence."""
    longest_run = max(
        (len(run) for block in blocks for run in re.findall(r"`+", block)),
        default=0,
    )
    return "`" * max(3, longest_run + 1)


def _confidence_cell(pick: dict) -> str:
    primary = pick["primary"]
    runner_up = pick.get("runner_up") or {}
    cell = f"{primary['confidence']}% ({_model_label(primary['model'])})"
    if runner_up.get("model"):
        cell += f" / runner-up {runner_up['confidence']}% ({_model_label(runner_up['model'])})"
    return cell


def render(candidates: list[dict], blueprint_rows: list[dict], target_label: str) -> tuple[str, dict]:
    by_id = {row["id"]: row for row in blueprint_rows}
    overrides, keeps, unmatched, appendix = [], [], [], []

    for idx, cand in enumerate(candidates, start=1):
        row = by_id.get(cand["candidate_id"])
        if row is None:
            unmatched.append(cand)
            continue

        pick = row["pick"]
        is_query_layer_pick = pick["primary"]["model"] == _DETERMINISTIC_QUERY_LAYER
        # A cross-provider reference pick (gpt-5, gemini-..., or a sentinel
        # this schema doesn't document like inherit_session_model) has no
        # real Claude tier and isn't the one sentinel _format_literal knows
        # how to leave alone either — SKILL.md step 4 is explicit that a
        # cross-provider-reference row gets no routing-map row, because
        # there is no real edit to apply yet, only a reference pick. Before
        # this check existed, `_format_literal` happily formatted a
        # syntactically valid but semantically wrong literal for most
        # pin_syntax values (only `frontmatter_tier_keyword` ever validated
        # the model id at all), so a reader could copy-paste "gpt-5" into
        # an Anthropic SDK call.
        is_local_pick = pick["primary"]["model"].startswith(_LOCAL_PREFIX)
        is_cross_provider_pick = (
            not is_query_layer_pick
            and not is_local_pick
            and not _has_tier_keyword(pick["primary"]["model"])
        )
        current = cand["current_pin_literal"]
        is_keep = row["keep_or_override"] != "override"
        effort = pick["primary"].get("effort")

        if is_query_layer_pick or is_cross_provider_pick or is_local_pick:
            # Neither has a real, pasteable edit to apply yet — a structural
            # fix (query layer) or a reference pick with no counterpart on
            # this provider (cross-provider) alike. `None` (not a
            # placeholder string) signals "no counterpart literal" to the
            # appendix renderer below.
            suggested = None
        else:
            try:
                suggested = _format_literal(pick["primary"]["model"], cand["pin_syntax"])
            except ValueError as exc:
                suggested = f"⚠️ {exc}"

        # Decide ONCE, from current/suggested alone, whether this needs the
        # appendix — then every branch below (keep / query-layer / override)
        # reads that single decision rather than re-deriving its own. This
        # is the fix for a real bug: three branches used to decide
        # independently whether to show "see appendix #N", but only ONE of
        # them actually appended to `appendix` — a keep row or a
        # query-layer row with a pipe/newline in its current literal could
        # point at an appendix entry that was never created.
        needs_appendix = _needs_appendix(current) or (
            suggested is not None and _needs_appendix(suggested)
        )
        if needs_appendix:
            # A keep row has no counterpart literal to diff against either —
            # same reason the query-layer branch already passes `None`
            # below. Without this, a keep row whose literal happens to
            # contain a pipe/newline would store its (near-identical)
            # `suggested` formatting alongside `current`, and the appendix
            # renders any non-None pair as a `-`/`+` diff — telling the
            # reviewer to replace a pin the table, one section up, just
            # labeled "no change".
            appendix.append((
                idx,
                current,
                None if is_keep else suggested,
                None
                if (is_keep or is_query_layer_pick or is_cross_provider_pick or is_local_pick)
                else effort,
            ))
            current_cell = f"*(see appendix #{idx})*"
        else:
            current_cell = _code_span(current)

        if is_keep:
            # A keep row's whole point is "reviewed, unchanged" — showing a
            # suggested literal (even one identical to current) reads as a
            # proposal where there isn't one.
            suggested_cell = "*(no change)*"
            edit_cell = "*(no change)*"
        elif is_query_layer_pick:
            suggested_cell = "*(structural fix — see Why; no literal substitution)*"
            edit_cell = "*(no literal substitution — see Why)*"
        elif is_local_pick:
            suggested_cell = "*(local tier, gated: see Why)*"
            edit_cell = "*(no live edit: routing-gate decision, not a pin swap)*"
        elif is_cross_provider_pick:
            suggested_cell = "*(cross-provider reference — see Why)*"
            edit_cell = "*(reference pick only — no live edit)*"
        elif needs_appendix:
            suggested_cell = f"*(see appendix #{idx})*"
            edit_cell = f"see appendix #{idx}"
        else:
            # `_with_effort` annotates the human-readable cell only — the
            # "Exact edit" column stays the bare substitutable literal, per
            # `_format_literal`'s own contract.
            suggested_cell = _code_span(_with_effort(suggested, effort))
            edit_cell = f"{_code_span(current)} → {_code_span(suggested)}"

        record = {
            "idx": idx,
            "loc": _code_span(f"{cand['file']}:{cand['line']}"),
            "component": _escape_cell(cand["component"]),
            "current": current_cell,
            "suggested": suggested_cell,
            "confidence": _confidence_cell(pick),
            "why": _escape_cell(row["rationale"]),
            "edit": edit_cell,
            "primary_confidence": pick["primary"]["confidence"],
        }
        (overrides if row["keep_or_override"] == "override" else keeps).append(record)

    overrides.sort(key=lambda r: -r["primary_confidence"])
    keeps.sort(key=lambda r: -r["primary_confidence"])

    def _table(rows: list[dict]) -> str:
        if not rows:
            return "*(none)*\n"
        header = "| # | File:line | Component | Current | Suggested | Confidence | Why | Exact edit |\n"
        header += "|---|---|---|---|---|---|---|---|\n"
        body = "\n".join(
            f"| {r['idx']} | {r['loc']} | {r['component']} | {r['current']} | "
            f"{r['suggested']} | {r['confidence']} | {r['why']} | {r['edit']} |"
            for r in rows
        )
        return header + body + "\n"

    counts = {
        "found": len(candidates),
        "override": len(overrides),
        "keep": len(keeps),
        "unmatched": len(unmatched),
    }

    parts = [
        f"# Model right-sizing audit — {target_label}",
        "",
        f"Audited {counts['found']} existing Claude model pin(s): "
        f"**{counts['override']} suggested change(s)**, {counts['keep']} already right-sized.",
        f"Generated {date.today().isoformat()}. This PR adds only this doc — no real "
        "config in this repo was changed. Apply a row by copy-pasting its \"Exact edit\" "
        "column into the file named in \"File:line\".",
        "",
        "## Suggested changes",
        "",
        _table(overrides),
        "## Reviewed, no change",
        "",
        _table(keeps),
    ]

    if appendix:
        parts.append("## Appendix: edits shown as fenced diffs")
        parts.append(
            "*(A literal here contains a line break or a pipe, either of which "
            "would corrupt or falsify a table cell — shown as an exact "
            "unaltered diff instead.)*"
        )
        parts.append("")
        for idx, current, suggested, appendix_effort in appendix:
            heading = f"### #{idx}"
            if suggested is not None and appendix_effort:
                # Same reason as the main-table `_with_effort` call — an
                # appendix entry is a fenced diff of the literal alone, so
                # the effort recommendation has to surface in the heading
                # text instead, or it goes missing here the same way it used
                # to go missing everywhere else.
                heading += f" (suggested effort: {appendix_effort})"
            parts.append(heading)
            if suggested is None:
                # A structural fix (query-layer pick) has no counterpart
                # literal to diff against — show the current value alone,
                # unaltered, rather than fabricating a "+" side.
                fence = _diff_fence(current)
                parts.append(fence)
                parts.extend(current.splitlines())
                parts.append(fence)
            else:
                fence = _diff_fence(current, suggested)
                parts.append(f"{fence}diff")
                # Prefix EVERY line, not just the first — a multi-line
                # current/suggested value has embedded \n's, and
                # `f"- {current}"` only marks its first line as
                # removed/added; every continuation line renders as
                # unmarked diff context, which is not what a multi-line
                # replacement means.
                parts.extend(f"- {line}" for line in current.splitlines())
                parts.extend(f"+ {line}" for line in suggested.splitlines())
                parts.append(fence)
            parts.append("")

    if unmatched:
        parts.append("## Unmatched candidates (no blueprint row returned)")
        parts.append("")
        parts.append(
            "The right-sizer's response didn't include a `blueprint_rows[].id` "
            "matching these — reported, not silently dropped:"
        )
        for cand in unmatched:
            loc = _code_span("{}:{}".format(cand["file"], cand["line"]))
            parts.append(f"- {loc} ({_escape_cell(cand['candidate_id'])})")
        parts.append("")

    return "\n".join(parts), counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=argparse.FileType("r"))
    parser.add_argument("--blueprint", required=True, type=argparse.FileType("r"))
    parser.add_argument("--target-label", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    candidates = json.load(args.candidates)
    blueprint = json.load(args.blueprint)
    blueprint_rows = blueprint.get("blueprint_rows", blueprint) if isinstance(blueprint, dict) else blueprint

    doc, counts = render(candidates, blueprint_rows, args.target_label)

    with open(args.out, "w") as fh:
        fh.write(doc)

    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
