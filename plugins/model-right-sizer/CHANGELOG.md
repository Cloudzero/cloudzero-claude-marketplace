# Changelog

All notable changes to `model-right-sizer.md` are documented here, most recent first. This project doesn't cut version tags — entries are dated. Loosely follows [Keep a Changelog](https://keepachangelog.com/) conventions (Added / Changed / Fixed).

## 2026-08-06

### Added
- **Token Economics (arXiv:2605.09104) as a third research-grounded layer.**
  A new "Economic formalization" section in `agents/model-right-sizer.md`
  formalizes the effectiveness-vs-efficiency split itself as the paper's
  `min TC s.t. Y ≥ Z` constrained cost-minimization objective, maps the
  nested-CES production function and elasticity-of-substitution onto why
  model tier and tokens trade off (and why they stop trading off past a
  model floor — the paper's "Memory Wall"), and maps the paper's shadow-price
  formulas onto two levers already in the rubric: latency-as-cost on
  agentic loops (`w·τ_inf`) and message-schema debt (`ΔC_coord`). Also
  grounds the deterministic-query-layer lever in a literal amortization
  test (the paper's GraphRAG capital-leverage inequality,
  `I_graph/Q < ΔY`).
- **`eval/` — deterministic formula and citation checks for all three
  research-grounded papers.** Every numeric claim the agent file attributes
  to IBPO, BudgetThinker, or Token Economics is now checked against a
  committed answer key (`eval/citation_ledger.json`) instead of trusted on
  sight, and every formula those papers state or the agent's own rubric
  assumes (the CES production/cost functions, shadow prices, the MRTS-at-
  optimum condition, the GraphRAG leverage inequality, budget-adherence
  classification, the agentic-down-pin promote/revert gate, IBPO's
  accuracy-per-compute arithmetic) is implemented as a pure, stdlib-only
  Python function in `eval/token_economics.py` / `eval/reasoning_budget.py`
  — run by code, never re-derived by an LLM. `eval/check_citations.py` runs
  four independent checks per claim: (1) literal presence of the cited
  formula/number in the agent file's own prose (`exact_substring` — this
  caught a real bug: the agent file's CES equation had transcribed `K^ρ`/`M^ρ`
  as `K^p`/`M^p`); (2) recomputed arithmetic against the claimed figure; (3)
  the literal formula (`formula_expr`, evaluated on `sample_inputs`) against
  actually *calling* the function it claims to implement; and (4) that same
  `formula_expr`'s free variables against an independently-declared
  `source_variables` set, so `formula_expr` and the implementation can't
  silently drift together in the same wrong direction without also
  falsifying a third, separately-authored field. Together this makes a
  `source_quote`/`implemented_by` pair enforced, not just documented — what
  it does *not* do is machine-verify `source_quote` against the live arXiv
  PDF, which stays a human/primary-source check performed at authoring time
  (named explicitly, the same way `verifiable: false` names its own gap).
  Each `sample_inputs` entry also carries an independently hand-computed
  `expected_output` (fourth review pass), diffed against both `formula_expr`'s
  evaluation and the implementation's return value — this is what catches
  `formula_expr` and the implementation being edited TOGETHER to the same
  wrong structure (a sign flip, a swapped pairing) that keeps the same
  variable names and so would otherwise pass every other check silently.
  The checker and both modules are exercised by the pytest suite under
  `tests/model_right_sizer/` at the repo root, including tamper tests
  proving each check actually catches drift — one deliberately constructed
  so a dropped term's sample value is 0 (invisible to the arithmetic check)
  to show why the variable-coverage check is a distinct layer, and one that
  monkeypatches the implementation to match a tampered formula_expr to show
  the expected_output diff is what catches a coordinated drift, not the
  other two checks. `check_citations.py`'s own docstring is explicit that
  this narrows, but doesn't formally close, the residual gap of a
  sufficiently coordinated multi-field edit -- true closure would mean
  re-deriving the paper's math from an independent symbolic source at CI
  time, out of scope here. One claim — IBPO's "~2x the
  accuracy-per-compute of self-consistency" — is explicitly marked
  `verifiable: false` pending the paper's own self-consistency baseline
  figure, rather than assumed true. `ces_production` and
  `ces_production_cobb_douglas_limit` also guard `L**beta` against `L=0`
  combined with a negative `beta` (the same zero-base/negative-exponent
  `ZeroDivisionError` pattern already fixed for `K`/`M`, found on a second
  review pass after the K/M fix landed) — a residual boundary the
  K/M-specific guard didn't cover, since labor has no rigid-complementarity
  escape hatch to fall back on the way K/M do.
- `schemas/blueprint.schema.json` — a strict JSON Schema (draft 2020-12,
  `additionalProperties: false` throughout) for Pass A, the right-sizing
  blueprint. Requires every `blueprint_rows[]` entry to carry all
  **three signals** (effectiveness, efficiency, difficulty), each as a
  `{score, reason}` pair — a row can no longer omit a pillar or give a bare
  number with no reason. Also defines `work_routing_map[]` (the build-unit
  translation of the blueprint), `message_schemas[]` (deduplicated handoff
  shapes referenced by id), `price_sheet`, and `uncertainty_ledger`
  (including calibration-history adjustments). `budget.token_ceiling` is
  `required` and always an actual integer (`0` for a row that spends no
  model tokens at all, e.g. one routed via `deterministic_query_layer`) —
  an empty or all-null `budget` object cannot satisfy the schema. Shipped
  alongside `schemas/blueprint.example.json`, a worked instance that
  validates against it — added because an LLM conforms to a shown example
  more reliably than to a formal schema alone.
- `scripts/validate_blueprint.py` (wired into CI, plus
  `tests/test_validate_blueprint.py`) — validates a blueprint instance
  against `schemas/blueprint.schema.json` in full (every `required` key at
  every nesting level, not a hand-picked subset) and checks the one thing a
  JSON Schema can't express: that every `handoff_schema_ref` resolves to a
  real `message_schemas[].id`. CI runs it against the checked-in worked
  example; `model-right-sizer-dryrun` step 4 runs the same script against
  the agent's own output, so there is one implementation of "conformant"
  instead of a schema plus a separately-maintained prose checklist.

### Changed
- `model-right-sizer-install` now detects whether the target repo has
  `CLAUDE.md`, `AGENTS.md`, or both, instead of always targeting
  `CLAUDE.md`: only `AGENTS.md` present → stamp the mandate there alone
  (no redundant `CLAUDE.md` is created); both present → stamp both,
  independently; neither present → create `CLAUDE.md`, unchanged from
  prior behavior. New step 3 makes the detection explicit and requires it
  to be named in the step 6 report rather than assumed. Steps 4-6
  renumbered and generalized to "every targeted file" accordingly.
- **Pass A now emits a single schema-conformant JSON object instead of
  prose/markdown tables.** `agents/model-right-sizer.md`'s "Pass A" section
  now points at `schemas/blueprint.schema.json` (+ the worked example) as
  the output contract; the former "blueprint table" and "work-routing map"
  deliverables are now named as the JSON's `blueprint_rows[]` and
  `work_routing_map[]` fields respectively, populated as data, never
  re-rendered as a table. Added a matching "bounce from" condition and two
  vocabulary terms. Pass B (the closing usage report) is unchanged — it
  stays a lean markdown table printed to chat.
- `model-right-sizer-dryrun` now packages that same JSON contract as its
  own deliverable: step 3 points at the schema/example files instead of
  re-describing the shape in a second, hand-written prose list, and step 4
  now pipes the agent's raw JSON response through `validate_blueprint.py`
  rather than a hand-picked checklist of fields to eyeball — the checklist
  approach was tried first and missed that a payload could omit
  `pick.what_flips_it` and still pass, since a prose list of "the fields
  that matter" drifts out of sync with the schema it's paraphrasing. The
  script enforces the schema's full nested contract plus the
  `handoff_schema_ref` referential check a JSON Schema can't express —
  asking the agent to re-emit once, quoting the validator's exact error, if
  it doesn't validate clean, before printing the JSON verbatim as "what an
  orchestrator should parse to route dispatch."
- `model-right-sizer-install`'s standing mandate block now runs
  `model-right-sizer-dryrun` directly for the "before" pass — rather than
  generically "consulting the agent for a blueprint" — and hands the
  resulting JSON blueprint to the orchestrating session/agent to route
  sub-agent/model dispatch by its `blueprint_rows` / `work_routing_map`
  picks. The "after" pass is unchanged: it still consults `model-right-sizer`
  directly for Pass B, never through the dry-run skill, since a dry run has
  no "actual" to reconcile against. Step 2's discoverability check now also
  verifies `model-right-sizer-dryrun` resolves (not just the agent file),
  since the mandate depends on both.
- **Moved into CloudZero (the CloudZero plugin marketplace)** — this plugin now lives at
  `plugins/model-right-sizer/` in
  [cloudzero/cloudzero-claude-marketplace](https://github.com/cloudzero/cloudzero-claude-marketplace),
  which is its sole home going forward (the standalone
  `Cloudzero/cloudzero-model-right-sizer` repo is superseded). The install
  flow changed accordingly:
  `/plugin marketplace add cloudzero/cloudzero-claude-marketplace` followed by
  `/plugin install model-right-sizer@cloudzero`. The plugin's own
  `marketplace.json` was dropped (the marketplace catalog at the repo root
  registers it now), all `repository`/`homepage` URLs and the
  `model-right-sizer-install` skill's install commands and fallback links
  were repointed, and the CI validators moved to the marketplace repo's
  `scripts/` where they now validate every plugin in the catalog.
- Security-review hardening during the move: the install skill now asks for
  explicit user confirmation before running the plugin-install commands and
  before stamping the mandate when the agent is undiscoverable, and the
  agent's pricing-fetch URLs were fixed to the working
  `platform.claude.com/docs/en/about-claude/...` endpoints (the old paths
  had started returning 404, silently forcing every run onto the stale
  in-file snapshot).

### Added
- `scripts/validate_plugin_manifest.py` (wired into CI's `validate` job, plus
  `tests/test_validate_plugin_manifest.py`) — checks that
  `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` both
  parse as valid JSON, carry their required fields, that each marketplace
  entry's `source` resolves to a real plugin directory whose own `name`
  matches, and that the two manifests' `version` fields agree. Before this,
  CI only validated `agents/model-right-sizer.md` — a broken manifest (bad
  JSON, a stale `source` path, a version that drifted between the two
  files) would have shipped silently and only surfaced as an install-time
  failure for a consumer.

### Changed
- `model-right-sizer-install` step 2 now **actively installs** the
  `model-right-sizer` Claude Code plugin (`/plugin marketplace add` +
  `/plugin install`) when the agent isn't already discoverable in the target
  repo, instead of only telling the user how to add it themselves. Falls
  back to the previous manual copy/submodule instructions if plugin install
  isn't available in the runtime. Updated the frontmatter `description`,
  the skill's own scope framing, and the root README's "What's in this
  repo" and "Action scope" sections to match this widened (but still
  narrowly-scoped-to-its-own-dependency) blast radius; added a
  corresponding note to `SECURITY.md`'s supply-chain bullet.
- Restructured this repo into a proper installable **Claude Code plugin**:
  added `.claude-plugin/plugin.json` (the plugin manifest) and
  `.claude-plugin/marketplace.json` (so the repo self-hosts its own
  marketplace catalog and can be added with
  `/plugin marketplace add Cloudzero/cloudzero-model-right-sizer` followed by
  `/plugin install model-right-sizer@cloudzero-model-right-sizer`, with no
  separate marketplace repo required). Moved `model-right-sizer.md` to
  `agents/model-right-sizer.md` — the plugin convention's default
  auto-discovered agent directory — instead of the repo root. Motivated by
  making the agent and its companion skills installable as a single unit
  through Claude Code's plugin system, rather than requiring a manual
  copy-the-file drop-in for every consumer.
- Renamed the `model-right-sizer-init` skill to **`model-right-sizer-install`**
  (directory `skills/model-right-sizer-init/` → `skills/model-right-sizer-install/`,
  frontmatter `name` field, the mandate-block marker comment, and all
  cross-references in this skill, `model-right-sizer-dryrun`, and the root
  README/CLAUDE.md) — "install" more accurately names what the skill does
  (stamp a mandate into a target repo) now that this repo is a real
  installable plugin, and avoids confusion with Claude Code's own `/init`
  command. No behavior change: same idempotent, append-only mandate-stamping
  logic.
  **Migration note:** a repo onboarded before this rename has a stamped
  `CLAUDE.md` mandate block whose closing line says to re-run the
  `model-right-sizer-init` skill to refresh it — that skill name no longer
  exists in this plugin. If you hit that, just invoke
  `model-right-sizer-install` instead; running it once rewrites the block
  (including that closing line) to the current name, so this is a one-time
  fix-up per already-onboarded repo, not a recurring issue.
- Corrected several stale/inconsistent `repository` URLs across
  `agents/model-right-sizer.md`, both `SKILL.md` files, the README badge, and
  `.github/ISSUE_TEMPLATE/config.yml` (previously a mix of
  `Cloudzero/project-model-right-sizer` and `djo-cz/model-right-sizer`) to
  the actual repo, `Cloudzero/cloudzero-model-right-sizer`.
- The model lineup is now retrieved at spawn instead of hand-maintained: the agent delegates the pricing/model-overview fetch to the cheapest capable tier (a `Task` dispatch to a Haiku-class model, or the smallest tier your framework exposes), caches it for the run, and only falls back to the in-file table — now explicitly marked "illustrative snapshot, last-resort fallback only, do not hand-edit" — if delegation and direct `WebFetch` both fail. Motivated by the Opus 5 addition above: adding a new release by hand-editing this file every time a model ships doesn't scale, so retrieval replaces maintenance as the primary path. Added `Task` to the frontmatter `tools` field for the delegated fetch; added a new "bounce from" condition for hand-editing the table instead of delegating.
- Relicensed from MIT to Apache License 2.0 (`LICENSE`, `NOTICE` added) to
  comply with CloudZero's `govern-opensource-ai` standard, which mandates
  ALv2 for all CloudZero open-source releases. Added `license`, `author`,
  and `repository` frontmatter fields to `model-right-sizer.md` and both
  `SKILL.md` files; added inbound-licensing terms to `CONTRIBUTING.md`;
  added a License + Trademarks section pair and AI-specific README sections
  (prerequisites, configuration, supported models, action scope, example
  interactions, limitations) required for AI-project OSS releases.
- A `.pre-commit-config.yaml` (`gitleaks`) is available for local use.
  `.gitignore` now excludes `.env*` (never applicable to this repo's own
  code, but required by the standard for any consumer copying this repo's
  structure). Secret scanning in CI is handled by GitHub Advanced Security.

### Fixed
- Removed the `secrets` CI job (which used `gitleaks-action`, requiring a paid
  org secret) — secret scanning and push protection are handled by GitHub
  Advanced Security, already enabled on this repo. Removed `secrets` from
  branch protection required checks accordingly.
- `CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md` now list all seven
  required frontmatter fields (`name`, `description`, `tools`, `model`,
  `license`, `author`, `repository`) instead of only the original four.
- `SECURITY.md` now correctly attributes maintenance to CloudZero, Inc. and
  its open-source maintainers rather than describing a personal project.
- Added `.pytest_cache/` to `.gitignore`.
- Removed unused `import textwrap` from `tests/test_validate_agent_file.py`.
- `scripts/validate_agent_file.py` now enforces the `license`, `author`, and
  `repository` frontmatter fields introduced in this PR; previously they were
  present in the files but absent from `REQUIRED_FIELDS`, so CI would pass
  even if a contributor removed them. Added `tests/test_validate_agent_file.py`
  to prevent regression.

### Added
- Claude Opus 5 (`claude-opus-5`, $5/$25, 1M context, 128K max out) as a new flagship row in the model lineup, above Opus 4.8. Deliberately *not* made the live default: it sits at exact price parity with the proven Opus 4.8, so the row frames promotion over 4.8 as `measurement-required` — realized reliability, not token cost, is the only open question — keeping 4.8 as the live default until a real run clears the bar. This applies the agent's own cost-of-error / don't-marry-the-newest-model stance to a brand-new top-tier model. Pricing/specs anchored to platform.claude.com, not the system card (system cards carry no pricing).
- `skills/model-right-sizer-dryrun` — a companion skill that turns a free-text intent into the agent's Pass A (blueprint) routing map on demand, then stops: no build, no file edits, no Pass B usage report. It unbundles the front bookend as a "what would this cost / how would this route" preview, without inventing a new agent mode (a dry run is simply Pass A run against a hypothetical).
- Deterministic-query-layer guidance: the blueprint now flags data-query-shaped stages (lookups, joins, aggregation, arithmetic over the task's own data) that a semantic/deterministic query layer (e.g. PromptQL) would answer more reliably and cheaper than a raw model call. Framed as a routing fork ("model tier vs. query layer"), not just another tier.
- Agent-to-agent message-schema design as a first-class lever: a new "Agent-to-agent message-schema design" section, a `handoff schema` column in the blueprint table and work-routing map, and a dedicated blueprint deliverable specifying the structured payload (and exclusion list) each stage hands its consumer.
- Schema adherence as a Pass B (usage report) grading line, alongside the existing budget-adherence line.
- Two new model-selection principles, two new "bounce from" conditions, and new vocabulary terms (`deterministic query layer`, `query-plan reuse`, `message schema`, `handoff payload`, `schema adherence`) covering both additions above.

## 2026-07-21

### Added
- Agentic-loop latency economics: loop-class scoring and a measurement-gated down-pin rule for agentic (≥3 tool-turn) calls, so a smaller model isn't pinned live on token-cost projection alone.
- `skills/model-right-sizer-init` — a companion skill that stamps a narrow, organization-agnostic mandate onto a target repo's `CLAUDE.md`.
- Open-source hardening: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, CI validation script (`scripts/validate_agent_file.py`), issue templates.

### Initial release
- `model-right-sizer.md` — the agent core: effectiveness/efficiency/difficulty scoring, the model lineup table, adaptive reasoning-budget layers (IBPO, BudgetThinker), the blueprint (Pass A) and usage-report (Pass B) output shapes, voice/biases, and model-selection principles.
