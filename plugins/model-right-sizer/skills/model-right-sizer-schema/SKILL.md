---
name: model-right-sizer-schema
description: >-
  Prescribe a minimal output schema for ONE agent's handoff to its
  controller — the `model-right-sizer` agent's "Agent-to-agent
  message-schema design" lever, scoped to a single agent-to-controller seam
  instead of a whole flow's blueprint. You give it a target agent (a path to
  an existing agent `.md` file, or a plain description of one not yet
  written) and it returns a schema-conformant JSON prescription (per
  `schemas/agent-schema.schema.json`) naming which reusable family the
  agent's reply fits, the typed `in`/`out` fields, the exclusion list, and a
  ready-to-insert `## Agent-to-agent schema` markdown stamp — the same
  family-catalogue-plus-per-agent-stamp convention some internal
  multi-agent codebases at CloudZero already enforce, reproduced here in
  portable, organization-agnostic form. Offers to stamp that block directly
  into the target agent's file, idempotently. The point is concrete: an
  agent that used to hand its controller unscoped prose now hands it a
  half-dozen typed fields plus one bounded prose slot, so the controller
  reads less and re-parses nothing. Use when someone says "give this agent
  an output schema", "prescribe a schema for …", "minimize what this agent
  returns", or "stamp an agent-to-agent contract on …".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-schema — prescribe one agent's output contract

This skill applies the `model-right-sizer` agent's third lever —
["Agent-to-agent message-schema
design"](../../agents/model-right-sizer.md#agent-to-agent-message-schema-design-the-third-lever) —
to exactly **one seam**: a single agent's reply to whatever dispatches it
(an orchestrator, a skill, a parent agent). Where a full blueprint
(`model-right-sizer-dryrun`) designs a schema for every hop in a multi-stage
flow, this skill zooms in on one agent that today hands its controller
unscoped prose (or an ad-hoc, undocumented JSON shape) and prescribes the
smallest typed contract that still carries everything the controller
actually acts on.

**Expected result:** the agent this skill is run against ends up with a
prescribed output schema, stamped into its file in the same format as the
`## Agent-to-agent schema` convention used elsewhere for multi-agent output
enforcement — a `Family` / `task_type` / version line, typed **In**/**Out**
field lists, a **Never inline** exclusion list, and a closing
no-freelancing sentence — so the contract reads the same way whether a
human or another agent opens the file.

## Why this is a separate skill, not a `model-right-sizer-dryrun` flag

`model-right-sizer-dryrun` answers "how should this whole build be routed."
This skill answers a narrower, standing-maintenance question: "does this
*one* agent's reply carry more than its controller needs, and what's the
smallest shape that would still work." That question doesn't need a task
decomposition, a price sheet, or a work-routing map — just the seam itself.
Keep it that way: if you find yourself blueprinting multiple stages at
once, that's `model-right-sizer-dryrun`, not this skill.

## What to do

1. **Identify the target agent.** Either:
   - a path to an existing agent `.md` file (any repo, any plugin) — read
     it in full: frontmatter `description`, tool grants, and body; or
   - a plain description of an agent not yet written — its role, its
     inputs, and (in prose) what it's expected to return.

   If neither is given, ask for one line naming the target — do not guess
   which agent the user means.

2. **Establish today's shape.** If the file exists, read its actual output
   guidance (or the absence of any — many agents default to "answer in
   prose," which is `current_shape.kind: "unscoped_prose"`). If it doesn't
   exist yet, that's `"none_yet"` — the prescription is the agent's first
   schema, not a tightening of an existing one. Don't skip this step even
   when it seems obvious; the `savings_note` this skill produces is only
   honest if the baseline is real, not assumed.

3. **Name the controller and its actual needs.** Ask (or infer from
   context, and say which) what dispatches this agent and what it does
   with the reply. This is the one input the whole prescription is sized
   against — a schema designed without a named controller and its stated
   needs is a shape in a vacuum, prone to over- or under-including fields.

4. **Pick a catalogue.** Check whether the target repo already has its own
   agent-to-agent seam-shape catalogue (look for a file resembling
   `context/agent-schemas.md`, or ask if one is referenced from a
   `CLAUDE.md`/`AGENTS.md`/`AGENT-TEMPLATE.md`-shaped file). If it does,
   **use that one** — don't stand up a second taxonomy alongside a repo's
   existing one. If it doesn't, fall back to the family catalogue shipped
   with this plugin,
   [`../../schemas/agent-schema-families.md`](../../schemas/agent-schema-families.md).
   Say explicitly which catalogue you used — it's a required field
   (`family.catalogue_source`) on the output, not a footnote.

5. **Dispatch `model-right-sizer` for the schema-design lever only.**
   Give it: the target agent's role/description, the current shape from
   step 2, the controller + needs from step 3, and the chosen catalogue
   from step 4. Ask it to apply its own "design the schema, don't let it
   default to 'paste the transcript'" discipline to this one seam and
   return a single JSON object conforming to
   [`../../schemas/agent-schema.schema.json`](../../schemas/agent-schema.schema.json)
   — see
   [`agent-schema.example.json`](../../schemas/agent-schema.example.json)
   for a worked instance. It should pick an existing family where one
   genuinely fits and coin a new one only when none does (and say so via
   `family.is_new_family`); either way, `out_fields` names only what the
   controller's stated needs actually require, and `exclude` names what
   the old (or a naive) reply would have carried that the controller never
   used. Do not accept a prose or markdown-table answer instead — if the
   agent returns one, ask it to re-emit as the JSON object.

6. **Validate before showing or stamping anything.** Run the response
   through
   [`../../../../scripts/validate_agent_schema.py`](../../../../scripts/validate_agent_schema.py)
   rather than eyeballing a hand-picked field list — the same discipline
   `model-right-sizer-dryrun` applies to its own output, and for the same
   reason: a checklist of "the fields that seemed important" drifts out of
   sync with the schema it's paraphrasing. Pipe the response's JSON on
   stdin so nothing is written to disk:

   ```bash
   echo "$PRESCRIPTION_JSON" | uv run --no-project --with jsonschema \
     scripts/validate_agent_schema.py -
   ```

   This enforces the full nested contract *and* the one thing a JSON
   Schema can't express: that `stamp_markdown` actually restates the typed
   `out_fields`/`exclude` values sitting right next to it, rather than
   drifting into prose that looks right but doesn't match. If it doesn't
   validate clean, ask the agent to re-emit once, quoting the validator's
   exact error, before proceeding.

   If `scripts/validate_agent_schema.py` isn't present in the current
   checkout (this plugin was copied standalone rather than run from the
   marketplace clone), read `../../schemas/agent-schema.schema.json`
   directly and confirm every `required` key at every level is present and
   every enum value is legal — against the schema itself, not a paraphrase
   of it.

7. **Show the before/after, then offer to stamp.** Print, plainly:
   - today's shape (`current_shape`) vs. the prescribed one (`family.id` +
     `out_fields` + `prose_field`) — the concrete size delta
     (`savings_note`) is the point of this whole skill, so lead with it;
   - the `stamp_markdown` block, verbatim.

   Then, **only if the target agent exists as a file** (`target.file_ref`
   is non-null) and the user confirms, insert or refresh that block in the
   agent's `.md` file.

   **First, scan the WHOLE file and count, before branching on any single
   case.** A file can satisfy more than one of the states below at once — a
   clean matched pair sitting in the file does not rule out an orphaned
   marker or a second, unmarked heading elsewhere — so counting only enough
   to confirm the *first* matching case (the mistake an earlier version of
   this skill made) can refresh a legitimate pair while silently leaving a
   second anomaly untouched. Count, across the entire file: every begin
   marker (either style), every end marker (either style), and every
   `## Agent-to-agent schema` heading not already bounded by a marker pair.
   Only then pick the one case below whose counts actually match — **the
   single-pair case requires the counts to be exactly one begin, one end, in
   that order, and zero unmarked headings elsewhere; any other combination
   is one of the anomaly cases, even when a clean pair is also present.**
   Never guess past an ambiguous state — every case that isn't the exact
   clean single-pair match stops for a human rather than picking a placement
   on the agent's own judgment, because a wrong guess here writes into a
   file another session or a human may be relying on:

   - **Exactly one begin marker, one end marker (matched, in order), and no
     unmarked heading anywhere else in the file** (this skill's own
     `<!-- model-right-sizer-schema:begin -->`/`:end`, *or* a pre-existing
     `<!-- xdp-agent-schema:begin -->`/`:end`-style pair from a repo's own
     convention). The clean case, and the *only* case that proceeds without
     asking: **replace only the text between those two markers**, keep
     whichever marker naming was already there, and stop — never stand up a
     second, competing section alongside a clean one.
   - **No markers of either style anywhere, but at least one unmarked
     `## Agent-to-agent schema` heading exists.** Don't blindly append a
     duplicate section under a new heading — that produces two headings with
     the same name and no marker distinguishing which is current. Show the
     user every unmarked section's full extent (heading through the next
     `##` or end of file) alongside the new prescription, and ask whether to
     wrap the (or one specific) existing section in this skill's markers and
     replace it, or leave the file untouched and abandon the stamp for this
     run.
   - **An unmatched marker** — a `:begin` with no corresponding `:end`, or
     vice versa, anywhere in the file, *regardless of whether a separate
     clean pair also exists elsewhere*. This is a corrupted or
     partially-applied prior stamp, not a state this skill invented a rule
     for. Stop, report the exact line the orphaned marker is on (and the
     clean pair's location too, if one is also present, so the human isn't
     left guessing which is which), and ask a human to repair or remove it
     before re-running — do not attempt to infer where the missing half
     belongs, and do not refresh the clean pair in the same run without the
     human's go-ahead once an orphan is known to exist.
   - **More than one complete marker pair present** (from either marker
     style, or a mix), or **a complete pair coexisting with an unmarked
     heading elsewhere.** An existing anomaly, not something this run
     created — stop, report every pair and every unmarked heading found
     (with line numbers), and ask a human to consolidate to one before this
     skill writes anything. Picking one location to update and silently
     ignoring the rest would hide the anomaly rather than surface it.
   - **No markers and no `## Agent-to-agent schema` heading at all** (the
     ordinary first-time case). Append a new section, with this skill's own
     `model-right-sizer-schema:begin`/`:end` markers, directly after the
     frontmatter — or at the end of the file if that placement doesn't fit
     the agent file's existing structure.

   Whichever action was taken, **re-read the file afterward and confirm the
   block landed as written** — don't declare success on the strength of the
   write call alone.

   If the target agent doesn't exist as a file yet (`target.file_ref` is
   null), there's nothing to stamp — just hand over the `stamp_markdown` for
   the user to paste in when they write the agent.

8. **Report.** Which catalogue was used; the family picked (existing vs.
   newly coined); the before/after shape and the `savings_note`; and
   whether the stamp was inserted, refreshed, or left for the user to paste
   in themselves.

## What this does NOT do

- It does **not** blueprint a whole flow or assign models/effort/budget to
  anything — that's `model-right-sizer-dryrun`. This skill's only output is
  a schema for one seam.
- It does **not** change the target agent's actual reasoning or behavior —
  only the *shape* of what it hands its controller. Whether the agent
  actually honors the stamped contract at runtime is enforced the same way
  the rest of this convention is: the stamp itself, read by whichever
  model runs the agent next. This skill doesn't add runtime validation
  code, and doesn't pretend to.
- It does **not** invent a second family taxonomy in a repo that already
  has one — see step 4.
- It is not destructive: outside the marker-delimited section it inserts
  or refreshes, the target agent's file is untouched.

## Related

- [`model-right-sizer.md`](../../agents/model-right-sizer.md) — the agent
  whose "Agent-to-agent message-schema design" section this skill unbundles
  and scopes to one seam.
- [`../../schemas/agent-schema.schema.json`](../../schemas/agent-schema.schema.json)
  / [`agent-schema.example.json`](../../schemas/agent-schema.example.json) —
  the strict contract this skill's agent-dispatch output must conform to.
- [`../../schemas/agent-schema-families.md`](../../schemas/agent-schema-families.md) —
  the portable seam-shape catalogue this skill picks from when the target
  repo doesn't have its own.
- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — the
  sibling skill for a whole flow's routing blueprint, of which
  `message_schemas[]` is the same discipline applied at chain scale instead
  of one seam.
