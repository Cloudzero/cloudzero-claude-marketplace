---
name: model-right-sizer-verify
description: >-
  Prove the model-right-sizer learning loop is actually installed, actually
  universal, and actually preserved — three checks that a passing install
  report cannot substitute for. DISCOVERY spawns a session in a fresh,
  unrelated repo and confirms the learned skill is found there with its
  content intact, using a canary token. PRESERVATION re-runs the installer
  and confirms accumulated learnings survive byte-for-byte while the
  protected regions refresh. INTEGRITY validates every ledger row against
  the schema and scans for repo-identifying leakage. Use after installing
  the loop, after upgrading the plugin, or whenever someone asks "is this
  actually working in my other repos".
license: Apache-2.0
author: CloudZero, Inc.
version: 0.1.0
repository: https://github.com/cloudzero/cloudzero-claude-marketplace
---

# model-right-sizer-verify — prove the install is real

`model-right-sizer-install` reports what it wrote. That is not the same as the
loop working. Three claims sit between "files written" and "working", and each
one fails silently:

| Claim | How it fails silently |
|---|---|
| **Universal** — every session in every repo reads it | The skill is written somewhere the runtime doesn't scan. Sessions simply never mention it, and nothing errors. |
| **Preserved** — a re-install doesn't destroy learnings | The one artifact in this system that cannot be regenerated gets overwritten by a template. You find out when the ledger reads as new. |
| **Repo-agnostic** — rows are safe to read anywhere | A row carries a repo name or path. Nothing breaks; the evidence is just wrong everywhere else, and quietly leaks. |

This skill checks all three. Run it after install, after a plugin upgrade, and
any time someone asks whether the loop is live.

## Check 1 — DISCOVERY (the universal claim)

The only honest test is a session in a repo that has nothing to do with this
plugin.

1. **Build a throwaway repo** outside your working tree: `git init` a scratch
   directory with a file or two, **no `CLAUDE.md`**, no plugin, no mention of
   model-right-sizer anywhere in it.
2. **Plant a canary.** Add one learning to the installed skill's trainable body
   carrying a nonsense codename generated for this run (`HALYARD-31`). Without
   it you can only prove the skill's *name* was listed — the canary proves its
   *content* reached the model.
3. **Probe non-interactively** from inside that repo:
   ```
   cd /path/to/throwaway-repo
   claude -p --allowedTools "Read,Glob,Skill" <<'EOF'
   Do you have a skill available named model-right-sizer-learned? Answer in exactly this shape and nothing else:
   DISCOVERED: yes|no
   SOURCE: <where it came from, or n/a>
   CANARY: <the codename token appearing in its Calibration learnings section, or n/a>
   LEDGER_ROWS: <how many rows in its ledger.jsonl, or n/a>
   EOF
   ```
4. **Pass = all four lines.** `DISCOVERED: yes`, a `SOURCE` naming the user-level
   skill directory, the exact canary token, and a correct row count (which also
   proves the sibling `ledger.jsonl` is reachable, not just `SKILL.md`).
5. **Remove the canary.** Non-negotiable — see the warning below.

**Two traps worth knowing before you run it:**

- **Do not try to sandbox this with `CLAUDE_CONFIG_DIR`.** Relocating the config
  directory also relocates authentication away from the OS keychain, and the
  probe fails with `Not logged in` rather than telling you anything about
  discovery. The test has to run against the real config directory.
- **Therefore it writes into the user's actual environment** — confirm with them
  first, check the target directory doesn't already exist (never clobber a real
  ledger), and clean up afterward.

> **Never leave canary content behind.** A fabricated learning sitting in a real
> learned skill is indistinguishable from a measured one, and the agent will
> cite it with the authority of evidence. Deleting the test install is part of
> the test, not cleanup you can skip. If the target already held real learnings,
> remove *only* the canary line — never the directory.

## Check 2 — PRESERVATION (the re-install claim)

The installer's contract is that a re-run refreshes the frontmatter and the two
protected regions while leaving everything between them untouched. Verify it
rather than trusting it:

1. Note the current learned `SKILL.md` and `ledger.jsonl` (hash them).
2. Append a sentinel line to the **trainable body** — between
   `<!-- SLOW_UPDATE_END -->` and `<!-- APPENDIX_START -->`.
3. Re-run `model-right-sizer-install`.
4. **Pass:** the sentinel survives verbatim, `ledger.jsonl` is byte-identical,
   and both protected regions now match the current template.
5. Re-run once more and confirm the file is **byte-identical** to step 4 —
   idempotency is the property most likely to regress.
6. **Also test the tampered case:** remove one protected marker and re-run. The
   installer must *report* the unbalanced markers and leave the file alone, not
   guess where the region should go.

## Check 3 — INTEGRITY (the repo-agnostic claim)

Validate every row in `ledger.jsonl` against
[`templates/ledger-entry.schema.json`](../../templates/ledger-entry.schema.json)
— `additionalProperties: false` and the closed `stage_kind` vocabulary catch
most leakage structurally. Then read the `lesson` fields yourself, because prose
is the one place a repo name can still hide inside a schema-valid row.

Flag any row whose lesson names a repo, path, ticket, service, or person. A
leaked row isn't just a disclosure problem — it is *wrong evidence* in every
other repo that reads it.

## Known result — 2026-08-05, plugin 0.2.0

**Check 1 passed.** Probe run from a freshly `git init`-ed scratch repo with no
`CLAUDE.md`, no plugin, and no reference to this marketplace:

```
DISCOVERED:   yes
SOURCE:       ~/.claude/skills/model-right-sizer-learned/
CANARY:       HALYARD-31
LEDGER_ROWS:  1
```

Corroborated live: the skill also appeared in a *separate*, already-running
session's available-skills list moments after installation — cross-session
propagation observed, not inferred. The test install was removed afterward.

**Check 2 passed** against a simulated home directory across a fresh install, a
re-install with accumulated learnings present, a third idempotency run, and a
tampered-marker case (correctly refused).

**Check 3 passed** on synthetic rows: well-formed and deliberately sparse rows
validate; rows carrying a `repo` field, a nested file path, an off-vocabulary
`stage_kind`, a PR-style id, or a session-identifying timestamp are rejected.

## Related

- [`model-right-sizer-install`](../model-right-sizer-install/SKILL.md) — writes
  what this skill verifies.
- [`model-right-sizer-eval`](../model-right-sizer-eval/SKILL.md) — the next
  question. This skill asks *is the memory there*; that one asks *does it
  change the picks*. Run this one first: an eval against a memory that was
  never discovered measures nothing.
- [`model-right-sizer-calibrate`](../model-right-sizer-calibrate/SKILL.md) —
  `summary` is a fast informal read on whether the ledger is accumulating.
