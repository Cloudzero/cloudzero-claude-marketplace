# CloudZero Model Right Sizer for Codex

Native skills integrate right-sizing into the **main Codex agent**. No separate
economist persona, agent installation, daemon, API key, or user-level model
configuration is required. The package includes the main workflow and all eleven
companions, the existing formulas/schemas/evaluation machinery, and local helpers.

From this repository, enable it for an existing target repository:

```sh
uv run --no-project --with jsonschema \
  plugins/model-right-sizer/codex/runtime.py install /path/to/your/repo
```

The installer copies a self-contained `.agents/skills` bundle and adds one
managed section to `AGENTS.md`. It preserves existing instructions, rejects
unmanaged collisions and locally edited managed files, and is idempotent. Re-run
the installer to upgrade; review local customizations before resolving a collision.
It does not change `CLAUDE.md`, global settings, credentials, or provider policies.
One main agent writes each session ledger; simultaneous writers are not supported.

Codex CLI and IDE discover repository skills; host support for other surfaces
must be verified separately. Check real discovery without a model completion:

```sh
python plugins/model-right-sizer/codex/catalog.py --skills /path/to/your/repo
python plugins/model-right-sizer/codex/catalog.py
```

Start a fresh Codex session if the host has cached its skill list. Use normal
requests, or explicitly mention `$model-right-sizer`. On substantive work the
main agent validates a blueprint, executes the work, tracks real boundaries, and
adds a compact closing report. For a preview use `$model-right-sizer-dryrun`;
it returns JSON and stops. The full blueprint remains inspectable in normal work.

## Runtime helpers

In an installed repository, the helper is:
`.agents/skills/model-right-sizer/scripts/right_sizer <command>`. This executable
wrapper sets `UV_CACHE_DIR` to `.uv-cache` at the installed repository's git root,
resolved from the wrapper's directory at invocation time. If git root lookup
fails, it uses `${TMPDIR:-/tmp}/model-right-sizer-uv-cache`. It then runs the
Python helper through `uv run --no-project`.
Use the wrapper in a `workspace-write` sandbox: even bare `uv run` initializes
its cache, so vendoring alone does not avoid an unwritable home cache. The cache
directory can be git-ignored. Core resources live under `assets/core` in the
same bundle; the source checkout uses `codex/runtime.py`.
The installer vendors `jsonschema` and its dependencies under `assets/core/vendor`;
post-install helpers need no dependency download. Use the same uv-managed Python
version for installation and runtime because `rpds-py` includes a compiled extension.

| Installed wrapper command | Behavior |
|---|---|
| `.agents/skills/model-right-sizer/scripts/right_sizer doctor` | Reports local capabilities without inspecting credential contents. |
| `.agents/skills/model-right-sizer/scripts/right_sizer validate blueprint.json` | Complete shared JSON Schema plus native semantic checks. |
| `.agents/skills/model-right-sizer/scripts/right_sizer validate-handoff prescription.json` | Shared handoff schema, family and stamp-fidelity checks. |
| `.agents/skills/model-right-sizer/scripts/right_sizer budget --profile profile.json --model ID --effort medium --signals signals.json` | Deterministic six-signal calculation using explicit Codex calibration. |
| `.agents/skills/model-right-sizer/scripts/right_sizer start --blueprint blueprint.json --session session.json --session-id ID` | Creates an execution ledger; refuses dry-run blueprints or existing sessions. |
| `.agents/skills/model-right-sizer/scripts/right_sizer transition --session session.json --unit ID --status in_progress` | Checks transitions and reads a fresh timestamp. Blocked units require `--note`. |
| `.agents/skills/model-right-sizer/scripts/right_sizer observe --session session.json --unit ID --events events.jsonl` | Checks observed spend; add `--next-turn` only if a continuation exists. |
| `.agents/skills/model-right-sizer/scripts/right_sizer warning-delivered --session session.json --unit ID --message-file warning.txt` | Acknowledges exact warning delivery, separately from generation. |
| `.agents/skills/model-right-sizer/scripts/right_sizer report --session session.json` | Reconciles observations; unknowns stay unknown. |
| `.agents/skills/model-right-sizer/scripts/right_sizer realized-spend --session session.json --unit ID --amount-usd AMOUNT --source SOURCE` | Records explicitly sourced realized spend. |
| `.agents/skills/model-right-sizer/scripts/right_sizer export --session session.json` | Produces local attribution records; transmits nothing. |

An observation must be cumulative for **one real execution unit**. CLI
`turn.completed` usage is aggregated across the supplied completed turns. Cached
input is a subset of input; reasoning output is a subset of output, never an
extra charge added twice. Streams containing multiple threads or mixed CLI and
app-server scopes are rejected. For app-server thread totals supply
`--baseline unit-start.jsonl` or explicitly attest `--dedicated-thread`.
Otherwise thread totals are rejected rather than misattributed to a stage.

A `--next-turn` check emits the deterministic warning, but does not deliver it.
The main agent must put that text into the unit's continuation before recording
delivery. Last-turn crossings and unavailable usage are distinct report outcomes.
This package does not impose a provider-level token cap or silently interrupt work.

`live_guard.py` provides an active controller for hosts using Codex's app-server
transport. Attach it to the main turn: `tick` sends periodic `account/usage/read`
requests, and `handle` consumes replies and native usage notifications. At the
threshold it sends the exact warning with `turn/steer` and `expectedTurnId`.
Delivery requires a matching acknowledgement; missing billing data stays unknown.
For a later unit in the same main thread, pass a measured `baseline_tokens`
snapshot captured at the unit boundary; zero is appropriate only for a fresh
thread. Stalled polls time out and retry, while native telemetry continues.
This controller must be wired into the host transport; installing a skill alone
does not create a background polling process in every Codex surface.

## Calibration and prices

Claude calibration constants are retained for historical research, never treated
as Codex measurements. Shipped defaults in [`profiles/default.json`](profiles/default.json) contain measured
medium-effort fits for GPT-6.1-Sol and GPT-6-Astra. Both passed all four fresh
held-out tasks and the budget-efficiency gate. Luna failed coverage and is
excluded. Omit `--profile` to use these defaults. Other model/effort pairs require
an explicit profile; zero coefficients are conditional fit results, not a reason
to skip rating a signal. See [live calibration evidence](results/2026-10-01-live-calibration.json)
and [observed model spread](results/2026-10-01-measured-model-spread.json).

A provisional profile has this explicit shape:

```json
{
  "runtime": "codex",
  "profile_version": "example-provisional-v1",
  "models": {
    "YOUR_AVAILABLE_MODEL_ID": {
      "dispatch_floor": 10000,
      "work_span": 60000,
      "signal_weights": {
        "tool_call_volume": 0.16666666666666666,
        "content_volume": 0.16666666666666666,
        "cross_reference_load": 0.16666666666666666,
        "validation_loop_iterations": 0.16666666666666666,
        "context_ingestion_volume": 0.16666666666666666,
        "investigative_uncertainty": 0.16666666666666666
      },
      "status": "provisional",
      "assumption": "Illustrative planning inputs, not measured constants."
    }
  }
}
```

These example numbers are not shipped defaults or validated budgets. Rate all
six signals using the definitions in `benchmark_suite.py`. Explicit Codex weights
are required; shared Claude weights are never a fallback. The illustrative uniform
prior above is unvalidated. Version 0.2 rejects older profiles without weights.
The native formula is `(floor + span * weighted_signals) * uncertainty_multiplier`.
A measured profile must reference real execution evidence and pass held-out gates.

Run reproducible calibration with `calibrate.py --out /fresh/evidence --models
ID,ID,ID --effort medium`. It executes 12 task shapes per model, three overhead
probes per model, three blind rating draws and one readiness probe (49 calls for
three models). `remeasure.py` preserves original evidence when a training task
contract needs an explicit correction; it never replaces held-out tasks. Eight shapes
train the six nonnegative coefficients; four stay held out. Coefficients and the
uncertainty multiplier use training data only. Candidate weights cannot be published
unless held-out coverage and budget-efficiency gates pass. `validation_round.py`
preregisters four fresh held-out shapes when the first round fails, explicitly
moving previous holdouts into development data. It does not tune the gates or
multiplier against the new outcomes. Use `guard_experiment.py`
for matched baseline/guarded executions and `usage_report.py` for measured model
shares with explicit coverage. Account summaries do not expose historical model
breakdowns. See committed results for actual measurements and remaining failures.

Fetch authoritative prices separately from account-visible model discovery.
Unverified/schema-placeholder prices produce **no cost estimate**. A report
can accept `--rates rates.json` with a `models` array containing
`cached_in_per_1m` as well as input/output rates. Cache hits without a known
cache price also produce no estimate. Verified list-price estimates remain
separate from subscription charges and realized spend.

## Experiments and parity

All eleven companions have native entry points and workflow contracts in
[workflows.md](skills/model-right-sizer/references/workflows.md). Four research
layers share their canonical grounding; six native wording knobs share the
existing optimizer's finite level domains without inheriting Claude winners.

```sh
uv run --no-project --with jsonschema plugins/model-right-sizer/codex/experiments.py check
uv run --no-project --with jsonschema plugins/model-right-sizer/codex/experiments.py \
  render --layers token_economics,ibpo --settings '{"effort_tax":1}' --out /tmp/native-variant.md
```

Independent blind evaluations need genuinely separate contexts, with held-out
actuals and answer-revealing results inaccessible. Rendering variants or running
unit tests is not empirical model-evaluation parity. See [PARITY.md](PARITY.md)
and the [dogfood evidence](results/2026-10-01-dogfood.json) for verified scope.

Re-run the actual dogfood task's correctness checks from this repository:

```sh
python -m unittest discover -s plugins/model-right-sizer/codex/dogfood -v
```

## CloudZero attribution

The original plugin does not call CloudZero APIs. This integration adds a local
attribution contract containing session/unit IDs, recommendations, observed
execution, tokens, price estimates, and separately sourced realized spend.
It excludes task prompts and raw logs. This JSON is **not a verified CloudZero
AnyCost ingestion format**. No CloudZero account connection, ingestion endpoint,
or actual export delivery is claimed; that needs a verified account/API contract.

## Review hardening and isolated quality checks

Live calibration and guard grading require Linux, `bubblewrap` (`bwrap`),
working unprivileged user namespaces, and system `python3`. For example, install
`bubblewrap` with your Linux distribution's package manager before live runs.
Grading fails closed if isolation is unavailable. Ordinary installation, budget
calculation, attribution and workflows do not require this grading backend.
Model-written Python runs with a read-only task mount, private network and process
namespaces, a cleared environment, dropped capabilities, execution deadlines and
CPU, memory, output and descriptor limits. The checker uses system Python rather
than the caller's virtual environment; benchmark outputs must be compatible.
The committed isolated replay verifies 48 final benchmark outputs and seven
guard outputs without new model calls.

Installation stages every bundle file, AGENTS.md and manifest before publication.
Handled publication failures restore prior file contents; failed rollback retains
recovery backups and reports their location. Individual replacements are atomic;
this is not a global multi-file atomic transaction across process termination or
concurrent writers. Continuation budget warnings remain pending until acknowledged
and are not issued again after delivery. Calibration rejects duplicate
model/effort/task rows, including floor probes. Model-spread reports reject
overlapping thread records, require thread IDs for definitive attribution and
allow disjoint actual-model billing groups within one thread.

Checker-owned standard-library imports are loaded before model modules become
importable, and model helpers follow system modules on the import path. Pending
warnings stay visible, including their exact delivery text, when a later usage
observation is unavailable. Missing telemetry does not reset the last known
cumulative baseline. Billing aggregation preserves measured groups alongside an
explicit incomplete-group count; incomplete coverage cannot be definitive.
