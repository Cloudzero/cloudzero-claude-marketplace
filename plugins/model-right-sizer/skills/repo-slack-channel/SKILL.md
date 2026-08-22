---
name: repo-slack-channel
description: >-
  Stand up and maintain a Slack channel dedicated to this repo's
  model-right-sizer / cost-analyst plugins — provisioning the channel
  (where possible), posting a pinned intro, prefiltering and triaging
  inbound messages, answering status questions, and proactively posting
  notable events. Routes each stage through `model-right-sizer` rather
  than running everything at one tier. Use when someone says "set up a
  Slack channel for this repo", "route repo questions through Slack", or
  "keep the team posted on right-sizer status in Slack".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# repo-slack-channel — a right-sized Slack front end for this repo

This skill turns the intent "give this repo a Slack presence" into a set of
`model-right-sizer`-routed stages rather than one undifferentiated build. It
originates from the "Repo Slack Channel Routing" design
(`https://claude.ai/code/artifact/6101db3d-1af0-469a-b584-72736ef066f6`) and
was built by dispatching the model-right-sizer's own blueprint decisions —
not by hand-authoring the routing table — then validating one real unit
against a genuinely novel task (see
[`../../eval/tuning/results/2026-08-22-novel-use-case-validation.md`](../../eval/tuning/results/2026-08-22-novel-use-case-validation.md)).
Read that result before trusting the budgets below: on this one real probe,
the tuned settings' budget for the setup unit undershot real cost by ~2.8x.

## What to do

1. **Get a blueprint before building anything.** Invoke
   [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) with
   the intent ("stand up and maintain a Slack channel for this repo, covering
   provisioning, an intro post, inbound message triage, status lookups, and
   proactive event posting"). Use its `work_routing_map` output as the real
   decomposition — don't reuse the table below without re-checking it, since
   blueprints are intent- and price-sheet-dependent and can legitimately
   differ run to run. The table below is a **worked example** from one such
   dry-run, kept for orientation, not a fixed contract:

   | unit | tier (example run) | loop_class | what it does |
   |---|---|---|---|
   | `unit-channel-setup` | sonnet | low-tool-turn | create/find the channel, post pinned intro + canvas |
   | `unit-message-prefilter` | haiku | single-shot | cheap keyword/relevance pass on inbound messages |
   | `unit-triage-classifier` | haiku | single-shot | classify a prefiltered message's intent (status ask / bug / question / noise) |
   | `unit-ledger-status-lookup` | haiku | single-shot | answer a status question by reading the status ledger |
   | `unit-proactive-event-poster` | sonnet | low-tool-turn | post a message when a notable repo event fires |
   | `unit-escalation-deepdive` | sonnet→opus (flip) | agentic | investigate a repeated/ambiguous anomaly a triage stage flagged |

2. **Provisioning: check before creating, and know the tool gap.** Before
   assuming a channel needs to be created, search for one that may already
   exist (`slack_search_channels` against a few plausible name variants —
   the repo name, an abbreviation, a `-plugin`/`-bot` suffix). **As of this
   writing, the Slack MCP connection available in this environment has no
   channel-creation tool** — only read/search/send/schedule/canvas/reaction
   tools exist (`slack_search_channels`, `slack_read_channel`,
   `slack_send_message`, `slack_create_canvas`, etc.). This was discovered
   empirically, not assumed: enumerate the live tool set via `ToolSearch`
   before claiming a capability exists or doesn't. If no channel exists and
   none can be created:
   - Say so plainly rather than posting into an unrelated existing channel
     (scope creep) or fabricating a workaround.
   - Draft the intended channel name, topic, and pinned-intro-canvas content
     anyway, so a human with channel-creation permissions (a Slack admin, or
     a differently-scoped connector) can create the channel and drop the
     drafted content in directly.
   - If a suitable channel already exists, use it — don't create a
     duplicate.

3. **Prefilter and triage inbound messages cheaply.** `unit-message-prefilter`
   and `unit-triage-classifier` are both single-shot, haiku-tier by design —
   they exist specifically so that only messages worth a real answer escalate
   further. Don't let either stage grow tool calls or multi-turn reasoning;
   if a message needs more than a keyword/intent read, that's the next
   stage's job, not this one's.

4. **Status lookups depend on a ledger that does not exist on this branch
   yet.** `unit-ledger-status-lookup` (and the "look up current status"
   half of `unit-escalation-deepdive`) presuppose a status ledger —
   `status` / `status_updated_at` / `status_note` fields on
   `work_routing_map[]` rows. That schema addition exists only on the
   unmerged `claude/chief-of-staff-rightsizer-wdjo6v` branch (blueprint
   `schema_version: "1.2"`), not in this branch's
   [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
   (`schema_version: "1.0"`, no status fields). **Do not build this stage
   against invented ledger data.** Until that branch merges:
   - Name the dependency explicitly when a status question comes in
     ("status tracking isn't wired up in this repo yet — see
     `claude/chief-of-staff-rightsizer-wdjo6v`") rather than answering from a
     fabricated or stale-looking status.
   - If asked to implement this stage now, the honest first step is
     confirming with whoever owns that branch whether/when it merges, not
     independently re-deriving the same fields here.

5. **Proactive posting is real but should stay rare and factual.** Post to
   the channel only for genuinely notable events (a merged PR touching this
   repo, a validator or CI failure, a completed tuning pass with a real
   result) — not routine activity. Keep posts short, link back to the
   source (PR, commit, results file), and never post a fabricated status.

6. **Escalation deep-dives are the one stage that's allowed to be expensive
   — and should flip tiers, not stay fixed.** `unit-escalation-deepdive`
   exists for the case where triage flags something ambiguous or repeated
   enough to need real investigation (multiple related anomaly reports,
   contradictory signals). Its blueprint carries an explicit
   `why_not_tier_below` / flip condition to Opus — respect that condition
   rather than defaulting every escalation to the cheaper tier out of habit,
   and rather than routing everything here by default.

7. **Never open a PR or provision infrastructure unprompted.** This skill
   drafts and, where the tool exists, posts — it does not, on its own
   initiative, request Slack admin changes, create a PR against the
   `chief-of-staff` branch, or otherwise change anything outside this repo's
   own Slack presence. Per this repo's own [`../../../../CLAUDE.md`](../../../../CLAUDE.md)
   convention, if you do open a PR for follow-up work here, only do so when
   asked.

## What this does NOT do

- It does **not** create a Slack channel in this environment — that
  capability does not currently exist via the connected Slack MCP tools.
  It drafts what a channel-creator would need.
- It does **not** answer status questions from an invented ledger — that
  stage is explicitly blocked pending `claude/chief-of-staff-rightsizer-wdjo6v`
  merging.
- It does **not** treat the worked-example routing table as authoritative —
  re-run [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md)
  for the current blueprint rather than reusing stale tiers/budgets.
- It does **not** assume the tuned prompt-tuning settings
  (`plugins/model-right-sizer/eval/tuning/`) generalize cleanly to this
  skill's real traffic — the one real probe run against this skill's own
  setup stage came back `over_budget` by ~2.8x; treat budgets here as
  directional, not exact, until more real dispatches are observed.

## Related

- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — get
  the current blueprint for this or any other intent before building.
- [`../../eval/tuning/results/2026-08-22-novel-use-case-validation.md`](../../eval/tuning/results/2026-08-22-novel-use-case-validation.md) —
  the real-dispatch validation this skill's setup stage was checked against.
- [`../../agents/model-right-sizer.md`](../../agents/model-right-sizer.md) —
  the agent whose blueprint and routing concepts (`loop_class`,
  `what_flips_it`, `deterministic_query_layer`) this skill's stages are
  expressed in.
