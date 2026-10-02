---
name: model-right-sizer
description: Right-size substantive Codex work in the main agent using CloudZero's model economics, validated blueprints, explicit budgets, and closing usage reconciliation. Use for model/effort selection or the repository's standing right-sizing mandate. Use companion skills for audits, schema design, and research. Tiny tasks may skip.
author: CloudZero, Inc.
version: 0.2.0
license: Apache-2.0
---

# CloudZero Model Right Sizer for Codex

You are the main Codex agent. Apply right-sizing as part of your normal work;
do not dispatch or ask the user to install a separate economist agent. Preserve
the user's objective and the repository's instructions. Sizing advice is not
authorization to delegate, change models, edit configuration, or spend more.

Read `references/economics.md` for the shared research grounding and
`references/workflows.md` for the lifecycle and companion workflows. Find the
core at `assets/core/` in an installed bundle, or three directories above this
skill directory in the source checkout. Use its schemas and six signal
definitions in `eval/token_ceiling_formula.py` directly, not from memory.

Run deterministic helpers directly using the execution tool you already have:

```sh
<skill-directory>/scripts/right_sizer --help
```

The installed executable wrapper sets `UV_CACHE_DIR` to `.uv-cache` at the installed
repository's git root, resolved from the wrapper's directory at invocation time.
If git root lookup fails, it uses `${TMPDIR:-/tmp}/model-right-sizer-uv-cache`.
The wrapper runs `uv run --no-project` for you. Use it for every
runtime command (`doctor`, `validate`, `budget`, `validate-handoff`, and ledger
commands); do not invoke the Python helper through bare `uv run` in a sandbox.
Even without dependency resolution, uv initializes its cache. The installer
vendors `jsonschema` and its dependencies under `assets/core/vendor`, so
post-install commands need no dependency download. Keep the same uv-managed
Python version used for installation: `rpds-py` has a compiled extension.

In the source checkout use `uv run --no-project --with jsonschema
<core>/codex/runtime.py <command>` outside the sandbox instead. The helper is
local code, not a daemon, another agent, or a model API client. Never fabricate
a numeric result when you cannot execute the helper; disclose the limitation.

## Before substantive work

1. A tiny, obvious task can receive a one-line skip. Otherwise decompose the
   intent into design stages and real execution units. Separate application
   model calls being designed from the Codex model doing the development.
2. Discover models actually available through host controls or app-server
   `model/list`. Fetch current provider pricing and capabilities once per
   session, retaining source URLs and retrieval times in the uncertainty
   ledger. Never use the historical Claude model snapshot for Codex. Mark
   unavailable prices unverified; do not assume API pricing equals a user's
   subscription charge. Avoid invented model IDs and effort controls.
3. Score effectiveness, efficiency, and difficulty with reasons. Quality is
   the constraint; cost, latency, and human rework are the objective. Choose
   the smallest sufficient model and effort, not the cheapest at any quality.
   State a primary and runner-up summing to 100%, counter-cases, and what flips
   the decision. Confidence is a judgment, not a measured probability.
4. Consider caching, batch discounts for application APIs, loop length, and
   deterministic query routing. Speculative decoding is a recommendation
   only for inference stacks the organization controls. For agentic down-pins,
   hold the ambient default until a measured latency/quality sample qualifies:
   promote at <=1.15x baseline wall-clock, revert at >1.25x, hold between.
5. Rate all six work signals, including zero-weight candidates. Use the
   `budget` helper with its shipped Codex profile for listed model/effort pairs
   and the stated harness. Supply an explicit profile for other contexts. Never reuse a
   Claude dispatch floor as a Codex measurement. A provisional native profile
   must disclose its assumptions and its own six signal weights. Shared Claude
   weights are not a fallback. Measured profiles require held-out validation.
   Do not mistake an advisory token ceiling for an enforced provider limit.
6. Define minimal handoff payloads with exclusions: full transcripts, raw
   datasets, and private chain-of-thought. Read calibration history if provided;
   disclose when absent. Emit one blueprint object, preserving the complete
   shared schema shape. The schema accepts provider-native `minimal` and
   `ultra` effort; native validation also enforces IDs, references, and confidence sums.
7. Run `validate` on the JSON. Explicit dry runs return that JSON and stop.
   For normal work keep the complete JSON inspectable, show a short sizing
   decision if useful, and continue with the user's task. Do not flood the user
   with extra setup questions or a compulsory JSON transcript.

## During work

Use `start` to create a local session ledger in an agreed scratch/artifact
location. Run `transition` at actual unit boundaries in this main agent;
these units need not be sub-agents. Fresh timestamps come from code. Resume
the same ledger after interruption; never restart it to erase an overrun.

Apply model/effort overrides only through available host controls. Otherwise
keep the current model and record the recommendation as unapplied. Do not
change user-level Codex settings to simulate an in-session switch. Independent
workers are reserved for experiments that require blindness or user-authorized
delegation; they are not a dependency of ordinary sizing.

At verified usage boundaries run `observe` with actual CLI JSONL events.
For a host using app-server transport, attach `scripts/live_guard.py` to this
main turn. Its periodic billing polls and native notifications use measured
counts, and `turn/steer` delivers the exact warning to the active turn. Missing
billing totals remain unknown; a matching steer acknowledgement verifies delivery.
App-server cumulative thread totals require a real unit-start baseline or a
dedicated thread before attribution. Unknown usage skips the guard and is
reported. When `--next-turn` produces a warning, put the exact text into the
unit's next-turn context, then acknowledge with `warning-delivered`. Generating
a warning does not count as delivering it. Do not invent a live token ticker.
On a last-turn crossing record it; there is no next turn to steer.

## After work

Run `report` to obtain facts; add a lean markdown table in the main agent's
normal completion response. Include recommendations vs observed execution,
scores/reasons, budget adherence, delivered-warning outcomes, schema adherence,
latency against baseline where measured, estimated vs realized cost, and one
learning. Missing evidence stays unknown. A missing warning does not prove an
undersized ceiling; a delivered warning does not prove the cause of an overrun.

CloudZero attribution is optional. `export` emits local per-session/per-unit
records. `realized-spend` accepts a named measured source. These helpers do not
send data, invoke CloudZero APIs, or imply a live connection. Report artifacts
and published cost records must not contain prompts, raw tool logs, or secrets.
