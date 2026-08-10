---
name: model-right-sizer-audit
description: One-shot, PER-CALL-SITE audit of a repo's EXISTING LLM calls — every place code actually invokes a model (an SDK/API call, a sub-agent dispatch, an agent frontmatter definition), decomposed by INTENT into the distinct jobs it does, never a grep hit on a model-name string and never one candidate per FILE either — a single skill pinned by one static `model:` key still gets its own documented steps read and split by intent (a deterministic scorer call and a templated report next to real judgment are not the same job just because one frontmatter key covers both), checked for whether the split is actually severable given Claude Code's per-turn model binding. For each discovered call or severable sub-step, this skill DELEGATES to `model-right-sizer-dryrun` (does not re-implement its scoring) so the two stay in sync as the dry-run skill evolves — that's a genuine Pass A blueprint per call, not a model-for-model swap collapsed across every place the same fact happens to be mentioned. Shipped as a PR committing ONE schema-conformant JSON blueprint file (`model-right-sizer`'s own `blueprint.schema.json`, the same strict contract `model-right-sizer-dryrun` already validates against) at the TARGET REPO'S ROOT — not a markdown table, not a hosted artifact — with every narrative field (`description`, signal `reason`s, `rationale`, `what_flips_it`, `why_not_tier_*`, `uncertainty_ledger`) written in full prose, since strict JSON has no comment syntax and those fields are where this skill's whole reasoning has to live. Also folds in the cross-cutting structural findings a per-call sweep surfaces (hardcoded literals that can drift, dead config keys, missing bias guards) that a batched or grep-based pass misses, via `uncertainty_ledger.assumptions` — never as invented top-level fields the strict schema doesn't define. Distinct from `model-right-sizer-dryrun` itself (this skill's own engine, scoped per call by this skill's orchestration — invoke the dry-run skill directly for a single hypothetical task; invoke this skill to sweep every real call in a shipped repo) and from the standing before/after MANDATE (`model-right-sizer-install`, which brackets a build already in flight). Works against the current repo or any other repo the caller can clone. Use when someone says "audit this repo's model calls", "right-size the models in <repo> per call site", "find every LLM call and right-size it", or "commit a model right-sizing blueprint for <repo>".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-audit — dry-run every real LLM call, one at a time

This skill finds every place a target repo **actually invokes a model** — an
SDK/API call, a sub-agent dispatch site, an agent's `model:` frontmatter —
and, for **each one**, runs a dedicated `/model-right-sizer-dryrun` pass
scored on that one call's own job. It does **not** grep for `claude-*`
string mentions and it does **not** batch every call into one combined
scoring request: a single-file scan that finds "claude-opus-4-6" mentioned
in six places is one fact, not six findings, and a batched scoring call
tends to return one verdict applied to every "similar-looking" row instead
of the differentiated, sub-step-level picks each call's actual job earns.
The corrective for both is the same: **decompose by intent, then dry-run
each intent-unit on its own.**

**Delegates, doesn't duplicate.** Every one of the N dry-runs in step 3 is a
real invocation of the existing
[`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) skill —
this skill never calls the `model-right-sizer` agent directly and never
re-implements that skill's framing, validation, or output contract. If
`model-right-sizer-dryrun` changes (a new schema field, a different
validation step, a new effort default), this skill's audits pick that up
automatically on the next run, with zero edits here. The only things this
skill owns are (1) finding the real call sites and decomposing them by
intent, (2) driving one dry-run per call with the right framing, and (3)
merging the N already-validated JSON blueprints into **one** blueprint,
still schema-conformant, committed at the target repo's root.

**The deliverable is the JSON file itself, not a rendering of it.** The
committed file at repo root **is** the audit, machine-readable and
re-diffable on the next run, with every explanatory sentence living inside
the schema's own narrative fields rather than in a format nothing else can
parse. A markdown rendering of the committed JSON is still fine to produce
*in addition*, on request — see
[`scripts/render_pin_audit.py`](scripts/render_pin_audit.py) — but it is
optional, not what the PR commits.

It never edits the repo's real config itself. `model-right-sizer` is
read-only by design; this skill inherits that discipline — it proposes, a
human or a follow-up Claude turn applies. **The one exception to
"read-only": this skill DOES write one new file** (the blueprint JSON) and
open a PR in the target repo — see the "Action scope" note in this plugin's
[README](../../README.md).

## When to use

- Auditing a repo you don't actively develop day-to-day (a sibling repo in
  your org, an OSS consumer of this plugin) for model-selection drift,
  without installing the standing mandate there.
- A repo runs several distinct model-invoking jobs behind one file or one
  config (a multi-persona pipeline, a rotation, a multi-round loop) and a
  single blended verdict would hide which specific job is over- or
  under-provisioned.
- Periodic hygiene sweep — run it quarterly, the same discipline you'd
  apply to a dependency or vulnerability audit.

**Not** for: right-sizing ONE task that hasn't been built yet — call
`/model-right-sizer-dryrun` directly, this skill's own engine, without the
discovery/fan-out wrapper; installing a standing before/after mandate for
future work (→ `model-right-sizer-install`); reconciling one just-finished
build's recommended-vs-actual spend (→ the agent's own Pass B).

## Invocation

```
/model-right-sizer-audit <target>
```

`<target>` is one of:
- a GitHub `org/repo` slug or full URL (e.g. `octocat/hello-world`) — cloned
  to a scratch dir
- a local path to an existing checkout
- omitted — defaults to the current repo

Optional trailing flags: `--base <branch>` (default: the repo's detected
default branch) · `--no-pr` (print the validated JSON blueprint to chat
only, skip cloning a branch and opening a PR — the "just show me" mode,
useful for a repo you don't have push access to) · `--scope <path>` (limit
discovery to one
file/directory instead of the whole repo — recommended on a first run
against an unfamiliar codebase, since the fan-out in step 3 is one dry-run
per discovered call and an unscoped sweep of a large repo can find dozens).

## Prerequisites

- `gh` CLI authenticated with at least read access to `<target>` (push access
  too, unless `--no-pr`).
- The `model-right-sizer-dryrun` skill available in this session (it ships
  with the `model-right-sizer` plugin — see that skill's own prerequisites).

---

## Steps

### 1. Resolve the target and get it on disk

**Quote every interpolated value, always** — `<target>` is caller-supplied
and the default branch comes back from the repo itself, so both can carry
shell metacharacters (spaces, `;`, `$()`, backticks). Assign them to shell
variables and quote every expansion (`"$target"`, not a bare `<target>`
spliced into the command string) in every step below and in steps 4-5 — an
unquoted interpolation here means a crafted target or ref alters the
command actually run on the machine doing the audit, not just the one being
audited.

- **Local path or current repo** (`<target>` is a filesystem path, or was
  omitted) → use it directly, no clone. `cd` into it (or stay put if
  omitted) and detect the default branch with **no repo argument**:
  `gh repo view --json defaultBranchRef` — passing the local path or an
  empty string as `gh repo view`'s argument fails outright, since that
  argument must be an `OWNER/REPO` slug or a URL, never a filesystem path;
  omitting the argument entirely is what makes `gh` read the *current
  directory's own* git remote instead.
- **GitHub slug/URL** (`<target>` is `org/repo` or a full URL) → detect the
  default branch first — `gh repo view "$target" --json defaultBranchRef`
  is correct here, since `$target` really is a resolvable identifier — then
  look for an existing local clone, but **verify it before reusing it**: a
  directory that merely matches the repo's basename is not proof it's the
  same repo, or that it's safe to touch.
  ```bash
  candidate=$(find ~ -maxdepth 4 -type d -name "$repo_name" 2>/dev/null | head -1)
  if [ -n "$candidate" ] \
    && git -C "$candidate" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    && git -C "$candidate" remote get-url origin 2>/dev/null | grep -qi "$target" \
    && [ -z "$(git -C "$candidate" status --porcelain)" ]; then
    ( cd "$candidate" && git fetch && git checkout "$default_branch" && git pull )
  else
    gh repo clone "$target" "$scratch_dir/$repo_name"
  fi
  ```
  All three checks matter, not just the first: a same-named but *unrelated*
  repo (wrong `origin` remote) and a genuinely-matching checkout with
  uncommitted work in it are both real, distinct ways a bare basename match
  can go wrong — the first silently audits the wrong project, the second
  clobbers someone's in-progress edits the moment `checkout`/`pull` runs.
  Neither is proven safe by "a directory with this name exists"; clone
  fresh into the scratch dir instead of guessing.
- Unless `--no-pr`, create the working branch now:
  `craft/model-right-sizing-audit-$(date +%Y-%m-%d)` off `"$default_branch"`,
  checked out. Don't share this branch with unrelated work already sitting
  on the checkout — keep it isolated to this audit.

This step is pure mechanical git/`gh` plumbing — no model judgment. Run it
inline in the orchestrating session; it doesn't warrant a sub-agent dispatch
of its own.

### 2. Find every real call site, and decompose each by intent

A "real LLM call" is a place code (or an agent/skill definition) actually
**invokes** a model to do work — not a place a model's name is merely
*mentioned*:

- **A direct SDK/API call** — an Anthropic/OpenAI/LiteLLM/etc. client
  invocation (`.messages.create(...)`, `_call_litellm(...)`, an HTTP POST to
  a chat-completions endpoint). Read the function that wraps it, not just
  the call line — the wrapper's callers are what tell you the actual job.
- **A sub-agent dispatch site** — `Agent(...)`/`Task(...)` in a skill, or
  the equivalent in whatever framework the repo uses.
- **An agent/persona definition** — a `.claude/agents/*.md` file's `model:`
  frontmatter, or a config-driven persona→model map a dispatcher reads at
  runtime (e.g. a `persona_model_map` JSON/YAML value).

Read the code around each call site well enough to answer: **what job is
this specific invocation doing, and does it fire more than once with a
different effective job each time?** A single call site inside a loop over
N personas, or a rotation across M rounds, is not one candidate — it's N or
M, because a security-lens challenger and a pm-lens challenger sharing one
line of code do very different work and should never be forced through one
verdict. This is the decomposition that matters; a `for` loop or a
`models[i % len(models)]` rotation is exactly where a grep-based sweep (or a
single batched scoring call) collapses distinct jobs into one finding. A
recurring example of this shape: a debate/panel script's refine stage is one
call site (one function, inside a `for` loop over rounds), but its real
intent-decomposition is one candidate **per rotation seat**, because each
seat is a different model doing the same prompt against a different
position in a multi-round chain — round 1 sets structure every later round
inherits, an interior round only needs to catch the prior round's
regressions, and a terminal round's output ships with nothing downstream to
catch its mistakes. Collapsing those into "the refine stage, keep or
override" throws away exactly the distinction the requester needed.

**A flat, single-frontmatter skill is the same trap, at a different grain.**
Everything above decomposes a *literal* call site (a loop, a rotation) into
N candidates. The identical failure also shows up one level up, on a
skill/agent that has exactly one call site — one `model:` frontmatter key
governing one Claude Code turn — but whose own documented steps do several
different jobs. Treating "the skill" as the candidate here is the file-level
version of treating "the refine stage" as the candidate above: it forces a
single verdict onto steps that don't share an intent, just because they
share one static pin.

Read the skill's own numbered steps (or an agent's documented phases) the
way you'd read a `for` loop body: do the steps differ in *kind* —
deterministic tool-invocation, templated formatting, and rule-following
case-table lookups on one side; open-ended synthesis, contradiction-spotting,
and prioritization judgment on the other? If yes, decompose into one
candidate per phase-group, briefed and dry-run separately in step 3, the
same as any other decomposition.

A recurring shape worth naming: a health-check-style skill pinned `model:
opus` for its entire six-step run, where some steps mostly invoke a
deterministic scorer script and walk a fixed case table, and other steps do
the actual judgment — spotting a claim contradicted by recent activity,
prioritizing gaps by impact vs. effort, deciding whether a lower live count
is a data-lag artifact or a real regression before overwriting a record. If
that whole file is scored as one candidate, it gets pinned Opus end to end;
the corrective is to dry-run the scorer-invocation/formatting steps and the
judgment steps as separate candidates, because their difficulty scores are
nowhere near each other.

**But check severability before you brief the split — this is where a
phase-level pick differs from a persona/rotation one.** A Claude Code skill
invocation is atomic per turn: one `model:` key governs everything from the
first tool call to the last, with no mid-turn escalation. The pattern that
already works for this: a repo can split a skill's mechanical work
(tooling pull, templated summary) from its judgment-heavy work (triage,
extraction, prioritization) into **two separate skills** — the first ends
its own turn on a plain-text offer instead of inlining the second, because
a `model:` pin applies to the entire turn that runs it and cannot escalate
partway through; that pin only takes effect once the second skill is
invoked in a fresh turn. That split is real and already proves the pattern
works — cite it as the target shape when a phase genuinely can be pulled
out into its own dispatched call (a sub-agent dispatch with its own model
override works too, if the phase doesn't need a fully separate skill
invocation — see the guardrail below on what "severable" actually requires).

Not every riskiest-step problem is severable that way, though. A session-
bootstrap-style skill's steps can be mostly mechanical (a data pull, file
reads, a templated summary) except for one step that verifies some binding
or identity is correct before any live query runs — miss that and every
later step (including anything a downstream skill later reads back)
inherits the wrong context. That step's output gates every step after it
in the *same* turn, so it cannot become its own dispatched sub-call the way
the mechanical/judgment split above could — there is no later turn to hand
it off to, and whether a sub-agent dispatch could inherit that already-
verified state instead is a real open question, not something to assert
either way without checking. When a dry-run's own `what_flips_it` names the
one step driving an up-pin, decide explicitly whether that step is
severable. If not, the row's `pick` legitimately covers the whole skill
inheriting its riskiest step's tier, and the `rationale` must say so
plainly — "the whole turn inherits step N's tier because step N gates
everything after it, not because the other steps independently need the
stronger tier" — rather than letting a single flat pick read as if every
step earned it on its own merits.

**Filter before decomposing**: drop anything inside `CHANGELOG.md`, `docs/`
pages that *describe* a past decision rather than *invoke* a model live,
test fixtures/mocks, and vendored/third-party code the repo doesn't own —
none of those are calls.

For each decomposed candidate, record enough context to brief a dedicated
dry-run in step 3 and to write a concrete edit later if it's overridden:

```json
{
  "candidate_id": "c-<n>",
  "file": "scripts/debate.py",
  "line": 865,
  "job_description": "one or two sentences — what THIS specific invocation does, its position in any loop/chain/rotation, what consumes its output and how errors there propagate",
  "current_pin_literal": "the MINIMAL substitutable token — just the model ID or tier keyword, never a surrounding statement/array/line, unless that whole line IS only the literal",
  "pin_syntax": "frontmatter_tier_keyword | full_model_id | cli_flag | env_var | bare_value | sdk_string_literal | shared_frontmatter_key_needs_split"
}
```

Keep this candidate list a **separate structured artifact** from each
dry-run's own output — `blueprint.schema.json` carries no file/line/literal
field (a blueprint row describes a model *decision*, not where in the
codebase it lives), so this skill has to track the file/line/literal mapping
itself, joined back to each dry-run's `blueprint_rows[].id` by
`candidate_id`. The `current_pin_literal` minimality rule (the MINIMAL
substitutable token, never a surrounding statement) and the `pin_syntax`
enum (including `bare_value` for a differently-keyed field, e.g. `producer:
claude-opus` narrowed to just `claude-opus`) apply the same way every run.
What matters is what counts as a candidate in the first place: a call SITE
decomposed by intent, never a string-mention grep hit — including a single
skill's own step sequence, per the flat-file guidance above.

One `pin_syntax` value needs a note: **`shared_frontmatter_key_needs_split`**,
for a phase decomposed out of one flat skill where that phase is severable.
`current_pin_literal` there is the ONE shared `model:` key every phase is
currently forced through — there is no separate literal edit point for this
phase alone yet, only the shared one — and step 4's `work_routing_map` must
name the restructuring that creates one, not a one-line substitution. A
non-severable phase keeps the file's existing `frontmatter_tier_keyword`
`pin_syntax` and is never marked `shared_frontmatter_key_needs_split`, since
there is no split to eventually apply.

If the sweep finds **zero** real calls, stop here and report that plainly.

**Model note (efficiency):** reading real code for call sites and
job-intent is genuinely agentic work (multi-file, judgment-bearing) — treat
it as Sonnet-tier work at minimum. A Haiku-tier attempt on a large,
unscoped sweep risks needing more turns to converge, which can erase the
per-token saving; if you try a cheaper tier here, treat the down-pin as
provisional until you've measured wall-clock against a Sonnet baseline on
at least one real sweep. Dispatch via a built-in read-only search/discovery
agent (Claude Code's `Explore` agent, or your runtime's equivalent) with a
model override, rather than standing up a new dedicated agent for this — a
generic discovery agent already has the right tool-scoping (read/search,
no edits) for this step.

### 3. Dry-run EACH candidate separately — delegate, don't score it yourself

For every candidate from step 2, invoke `/model-right-sizer-dryrun` **on
its own** — one call, one dry-run. Do not hand the whole candidate list to
one dispatch and ask for a combined verdict; do not call the
`model-right-sizer` agent directly and reimplement the dry-run skill's
framing yourself. Route through the skill every time, so this audit stays
correct as that skill's own contract evolves.

Brief each dry-run with:
- The one candidate's `job_description`, `file:line`, `current_pin_literal`,
  and — critically — enough of its *loop/chain position* that the dry-run
  can score it as a distinct job (e.g. "round 1 of 6, no downstream
  backstop for what it misses" vs. "round 2 of 6, two later rounds still
  re-check this") — or, for a phase decomposed out of one flat skill, its
  position in that skill's documented step sequence and whether step 2's
  severability check found it severable or not (e.g. "step 5 of 9, gates
  every later step in the same turn, non-severable" vs. "steps 2-3 of 6,
  run a deterministic scorer + fixed case table, severable from the
  judgment steps"). Copy the worked-example level of detail from step 2 —
  a thin brief produces a generic score.
- The explicit retroactive-audit framing from `model-right-sizer-dryrun`'s
  own instructions: **score this AS WRITTEN, don't redesign it.** This is a
  real call already running in production, not a build to plan.
- An instruction to use `"$candidate_id"` as that dry-run's
  `blueprint_rows[].id` — the join key step 4 uses to pair each dry-run's
  verdict back to the file/line/literal context recorded in step 2 (the
  blueprint schema carries no source-location field itself; see the note
  above).

Each dry-run returns its own schema-conformant JSON blueprint (per
`model-right-sizer-dryrun`'s own validation step — trust its contract, no
re-validation needed here). Collect the N blueprints' `blueprint_rows[]`
arrays and concatenate them into one list — this is `blueprint.json` for
step 4, structurally identical to what a single combined dispatch would
have produced, just built from N independently-scored calls instead of one
batched guess.

**A call whose current model isn't Claude gets a cross-provider reference
pick, not a keep/override verdict** — `model-right-sizer`'s price sheet only
covers Claude, so for a non-Claude call the honest deliverable is "if this
seat ran on Claude, what's right-sized," clearly labeled as a reference. Say
so explicitly in the brief; don't let the dry-run silently invent a
non-Claude price.

**Don't skip candidates that "look like siblings."** Several personas
sharing one code path is exactly the shape most likely to get flattened into
one verdict if you let it — dispatch every dry-run anyway, even when you
expect (and sometimes get) different picks per persona. A shared call path
can and does produce materially different verdicts across personas
precisely because each one got its own dry-run instead of a shared one.

### 4. Assemble ONE schema-conformant blueprint — no rendering, no model

Merge the N dry-runs into a single document conforming to
`model-right-sizer`'s `blueprint.schema.json` v1.0 — this merge is
mechanical assembly, not a model call:

- `schema_version: "1.0"`, `mode: "dry_run"`, `intent`: one sentence naming
  the target repo and what was swept.
- `price_sheet`: reuse whichever dry-run's fetched sheet is most complete
  (dedupe `models[]` by `id`) — don't re-fetch per candidate if one dry-run
  already did.
- `blueprint_rows`: every dry-run's `blueprint_rows[]`, concatenated —
  already keyed by `candidate_id` per step 3's briefing instruction.
- `work_routing_map`: **one row per candidate that is `override` AND whose
  current model actually IS Claude** — name the literal file:line edit
  using step 2's `current_pin_literal`/`pin_syntax` in the `build_unit`
  string (this is the "exact copy-paste edit" this skill has always
  promised — it now lives in routing-map prose instead of a rendered
  table column). **Cross-provider-reference rows get no routing-map row**
  — there is no real edit to apply yet, only a reference pick; that
  distinction must be explicit in the row's own `rationale`, never implied
  by the routing map's presence or absence alone. **A row whose `pin_syntax`
  is `shared_frontmatter_key_needs_split` gets no literal-edit `build_unit`
  either** — same reasoning as the cross-provider case, for a different
  reason: the split itself doesn't exist yet. Its `build_unit` instead names
  the restructuring (which step becomes its own dispatched sub-agent or
  standalone skill invocation, and at what tier) that would create a real
  edit point — the same idea as splitting one overloaded CLI flag into two,
  applied to a skill-frontmatter shape instead of a CLI-flag shape.
- `message_schemas`: one entry per distinct handoff shape a dry-run
  proposed, deduped by seam — several personas feeding one judge share one
  schema; don't author near-duplicate entries for structurally identical
  seams.
- `uncertainty_ledger`: merge every dry-run's `assumptions` /
  `would_measure` / `calibration`, **plus fold in any cross-cutting
  structural finding that surfaced across multiple dry-runs but doesn't
  belong to any single row** — a hardcoded literal duplicated in two
  places, a dead config key, a missing bias guard, a rotation's modulo
  arithmetic silently reassigning which seat holds the terminal position.
  These go in `assumptions`, stated as facts, **never as an invented
  top-level field** — `additionalProperties: false` at every level in the
  schema means there is no other place for them to live, and that's a
  feature, not a limitation to route around: it's what stops this skill
  from growing a free-form "cross-cutting findings" section outside the
  contract.

**Every narrative field is where the "comments" live.** `description`,
each signal's `reason`, `rationale`, `what_flips_it`,
`why_not_tier_above`/`why_not_tier_below`, and every string in
`uncertainty_ledger` are free text — write them with real density
(multi-sentence, specific to the one call's actual job, citing the concrete
mechanism a claim rests on), not compressed to a fragment. Strict JSON has
no comment syntax; these fields are the only channel the schema gives you
for the reasoning a reader needs before applying anything.

**Validate the MERGED document, not just each dry-run's own output.** Each
dry-run already validated its own JSON before returning it (per
`model-right-sizer-dryrun`'s own step 4), but the merge is new — a
duplicate `id` across two candidates, a `handoff_schema_ref` pointing at a
schema you deduped away, or a malformed `work_routing_map` row are all
merge-time mistakes no per-dry-run validation could have caught:

```
cat model-right-sizing-blueprint.json | uv run --no-project --with jsonschema \
  <marketplace-checkout>/scripts/validate_blueprint.py -
```

`<marketplace-checkout>` is wherever you have `cloudzero/cloudzero-claude-
marketplace` cloned locally. If it isn't available locally to supply that
script (this plugin was installed via `/plugin install` rather than a git
clone), do not skip validation: read `blueprint.schema.json` directly and
confirm every `required` field at every nesting level, every enum value,
and every `handoff_schema_ref` resolves — against the schema itself, not a
paraphrase of it kept here. Do not write the file anywhere until it
validates clean.

### 5. Write the blueprint and open the PR

Skip this step under `--no-pr`; print the validated JSON to chat instead
and stop.

- Write the validated document to `model-right-sizing-blueprint.json` **at
  the target checkout's root** — not `docs/`, not any subdirectory. The
  whole point of committing the schema (rather than a rendering of it) is
  that it's one canonical file a future run diffs against, and root is
  where a reader expects to find it without hunting. If a file of that
  name already exists from an earlier run, don't silently overwrite it —
  diff the two `blueprint_rows[]` arrays by `id` and note in the PR which
  rows are new, which changed pick, and which are unchanged, so the PR
  reads as a delta, not a replacement.
- **Gate**: show the assembled blueprint (or at minimum a per-row summary —
  id, current model, pick, confidence, keep_or_override) to the user before
  committing — an audit is a proposal, and the person running it should see
  it before it becomes a PR on someone else's repo. Skip the gate only when
  the caller has already explicitly pre-authorized
  opening the PR for this run (e.g. asked to "open a PR" up front, not just
  "check this repo").
- **Render the PR-body summary table — deterministically, from the
  committed JSON, not by hand:**
  ```
  python3 <this-skill's-directory>/scripts/render_pr_table.py \
    model-right-sizing-blueprint.json > /tmp/pr-table.md
  ```
  This is the same "don't let a model transcribe it" discipline as the
  JSON assembly itself, applied to the one thing a reviewer actually reads
  before opening the file: a scannable table (stage / current / pick /
  confidence / verdict, overrides first) generated straight from
  `blueprint_rows[]`. Never hand-write this table or paraphrase the
  numbers into prose — a reviewer comparing the PR body against the
  committed JSON should find them byte-identical.
- Commit, push, `gh pr create` against the detected default branch — quote
  `"$default_branch"` the same as step 1 (it came back from `gh repo view`,
  which is repo-controlled, not a fixed literal). **Build the PR body by
  concatenating three literal pieces to a file — never by interpolating
  the rendered table into a shell heredoc.** The table's content
  ultimately derives from LLM-authored dry-run output; switching to an
  *interpolating* heredoc (`<<EOF` instead of `<<'EOF'`) just to splice it
  in would let a stray `` ` `` or `$(...)` inside a stage name or rationale
  execute as a shell command — the exact class of defect step 1's quoting
  guardrail exists to prevent, reintroduced at the last step instead of
  the first:
  ```
  cat > /tmp/pr-body.md <<'EOF'
  ## Summary
  - Found {N} real LLM calls, decomposed by intent, each dry-run
    independently via model-right-sizer-dryrun (no batched scoring).
  - {M} suggested overrides, {K} confirmed as already right-sized, {R}
    cross-provider reference picks (no Claude default was ever live there).

  ## Row by row
  EOF
  cat /tmp/pr-table.md >> /tmp/pr-body.md
  cat >> /tmp/pr-body.md <<'EOF'

  ## How to apply
  `model-right-sizing-blueprint.json` at repo root is the audit — every
  narrative field (`rationale`, `what_flips_it`, each signal's `reason`)
  explains its row in full prose; the table above is a scan aid, not a
  substitute for reading the row you're about to act on. `work_routing_map[]`
  names the exact edit for every row with a real, live-eligible override.
  This PR does not change any real config; it only adds the blueprint file.

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  EOF
  gh pr create --base "$default_branch" \
    --title "Model right-sizing blueprint — $(date +%Y-%m-%d)" \
    --body-file /tmp/pr-body.md
  ```
  Every heredoc above stays **quoted** (`<<'EOF'`) — no shell expansion
  happens inside any of them — and the table is appended by plain file
  redirection (`>>`), never substituted into a string a shell re-parses.
  `{N}`/`{M}`/`{K}`/`{R}` are placeholders for you to fill with real counts
  before writing the file; they are not shell variables.

### 6. Confirm the PR is actually clear before reporting done

"PR open" is not "done." Poll `gh pr checks <pr-number>` until every check
reaches a genuinely terminal state — a single empty poll doesn't mean
settled; some checks take minutes, and a bot code-review integration (if the
target repo has one) can take longer than the standard CI checks. If a check
fails or a review comment raises a real finding, fix it, push, and re-poll
from scratch — don't report success on a check that's merely still running.
If your runtime supports dispatching a lightweight sub-agent for this kind
of wait-and-report polling loop, use one instead of tying up the main
session on a sleep loop; a plain retry loop works fine too if it doesn't.

### 7. Report

- The PR URL (or, under `--no-pr`, just the validated JSON).
- Counts: real calls found, overrides suggested, kept-as-is, and how many
  were cross-provider references vs. real Claude-default verdicts.
- Any cross-cutting finding folded into `uncertainty_ledger` rather than
  scored as its own row.
- Any surface the sweep couldn't reach — name the gap, don't silently
  under-report.

## Guardrails

- **Decompose by intent, never by string mention — and never by file
  either.** A call site's model name mentioned in six places (config, code,
  docs) is one fact; a call site invoked with four different personas is
  four candidates; a single skill whose steps run a deterministic scorer,
  fill a template, AND spot contradictions in prose is not one candidate
  just because one `model:` key covers all of it.
- **A phase-level pick is only useful if the runtime can act on it — say
  whether it can.** Claude Code's `model:` frontmatter binds an entire turn;
  a phase decomposed out of a flat skill is either severable into its own
  dispatched call (a genuinely separate skill invocation, or a sub-agent
  dispatch with its own model override) or it isn't (a step that gates
  every later step in the *same* turn). Every such row's `rationale` states
  which, explicitly — a flat pick that quietly implies a split the runtime
  can't deliver is worse than no decomposition at all, because it reads as
  actionable and isn't. Per-subagent model assignment already works today
  (a dispatched sub-agent can run on a different model than its parent
  turn) — the gap this check is for is narrower: knowing which inline steps
  of a flat skill can be pulled OUT into their own dispatch versus which one
  has to stay inline because a later step needs the same turn's already-
  verified state.
- **Delegate scoring to `model-right-sizer-dryrun`; never re-score
  yourself.** If you find yourself writing "score this the way the dry-run
  skill would," stop and actually invoke it. Duplicated logic drifts;
  delegation doesn't.
- **Quote every shell interpolation of a caller- or repo-controlled value —
  `<target>`, the detected default branch, any discovered file path.** None
  of them are trusted literals. Every command example in this doc uses a
  quoted shell variable (`"$target"`) for exactly this reason.
- **Read-only against the target's real configuration.** The only file this
  skill ever writes in the target repo is `model-right-sizing-blueprint.json`
  at repo root.
- **Never invent a model ID or price**, and never invent a non-Claude
  price — a non-Claude call gets a labeled cross-provider *reference* (say
  so explicitly in that row's `rationale`), not a fabricated keep/override
  delta, and gets no `work_routing_map` row.
- **A `keep` verdict is a real finding, not a non-event.**
- **Never add a field the schema doesn't define.** A cross-cutting finding
  that doesn't fit any row belongs in `uncertainty_ledger.assumptions`, not
  in a hand-invented top-level key. `additionalProperties: false` at every
  level is load-bearing — treat a validation failure as a sign the finding
  belongs in a narrative field, not as an obstacle to work around.
- **Don't re-scope into a broader code review.** This skill audits *model
  choice* only. Real adjacent defects a close read surfaces (a dead config
  key, a missing guard, a duplicated hardcoded literal) go in
  `uncertainty_ledger` or an individual row's `rationale` as asides — this
  skill never edits application code.
- **Validate the merged document before writing it anywhere.** Each
  dry-run validates itself; the merge does not validate itself.
- **Respect `--no-pr` and missing push access.** If `gh pr create` fails on
  a permissions error, say the push failed and why, and offer the validated
  JSON in chat as the fallback.

## Related

- [`model-right-sizer-dryrun`](../model-right-sizer-dryrun/SKILL.md) — the
  engine this skill dispatches once per discovered candidate. This skill
  adds discovery, decomposition, and synthesis; it owns none of the actual
  scoring logic.
- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) —
  stamps the standing before/after mandate; this skill is a one-shot audit,
  not a standing process.
- [`../../schemas/blueprint.schema.json`](../../schemas/blueprint.schema.json)
  (+ [`blueprint.example.json`](../../schemas/blueprint.example.json)) — the
  strict contract step 4 assembles into and validates against;
  single-sourced there, never restated here.
- [`scripts/render_pin_audit.py`](scripts/render_pin_audit.py) — **legacy,
  optional, not part of the primary flow.** An earlier design rendered a
  markdown table as the shipped deliverable; the deliverable is now the
  committed JSON blueprint itself. This script's CLI (`--candidates` +
  `--blueprint`, two separate files) predates that change — superseded for
  the PR-body use case by `render_pr_table.py` below; kept only as a
  reference for anyone building a fuller standalone rendering.
- [`scripts/render_pr_table.py`](scripts/render_pr_table.py) — **part of the
  primary flow, step 5.** Takes the single committed blueprint JSON and
  prints the scannable summary table (stage / current / pick / confidence
  / verdict) that goes verbatim into the PR body's `## Row by row` section.
  Same no-model-transcription discipline as the JSON assembly step itself.
