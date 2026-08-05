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
2. **Plant a canary — but make removing it failure-safe first.** The canary is
   one learning carrying a nonsense codename generated for this run
   (`HALYARD-31`). Without it you can only prove the skill's *name* was listed;
   the canary proves its *content* reached the model.

   A trailing "delete it afterwards" step is **not sufficient**, and this is the
   most dangerous part of the whole skill. If the probe errors, times out, or
   the session is interrupted between insertion and cleanup, fabricated
   calibration is left sitting in the real machine-wide skill, where it is
   indistinguishable from measured evidence and will be cited across every repo
   on the machine. Order the steps so an abort can't leave it behind:

   1. **Sweep first.** Before doing anything else, delete any
      `verify-canary` block already present — a leftover from a previous run
      that died. Report it if you find one; it means a prior run aborted, and
      that is worth knowing.
   2. **Record whether the skill pre-existed at all.** If it did, cleanup is a
      block delete (below) and the file is otherwise never touched. If it did
      not, cleanup is removing the directory your run created — after confirming
      nothing else has written to it in the meantime.
   3. **Write the canary inside explicit delimiters** so removal is a
      deterministic delete of a delimited block rather than a fuzzy line match:
      ```
      <!-- verify-canary:BEGIN (temporary — delete me; see model-right-sizer-verify) -->
      - **L-777** · `provenance: canary (NOT evidence)` · discovery canary **HALYARD-31**.
      <!-- verify-canary:END -->
      ```
      Tagging it `provenance: canary (NOT evidence)` is belt-and-braces: if it
      does survive an abort, the agent's own contract tells it not to treat the
      line as measured.
   4. **Install a real exit trap before you write the canary** — an instruction
      to "restore afterwards" is not a mechanism, and an aborted session never
      reaches its own last step. Register the cleanup with the shell so it fires
      on normal exit, error, and interrupt alike:
      ```bash
      SKILL=~/.claude/skills/model-right-sizer-learned/SKILL.md
      cp "$SKILL" "$SKILL.verify-backup"   # diagnostic + manual recovery only

      cleanup() {
        # Range-delete ONLY when both delimiters are present. An unpaired BEGIN
        # would make sed cut from there to EOF — taking the learnings and the
        # protected regions with it.
        if grep -q 'verify-canary:BEGIN' "$SKILL" && grep -q 'verify-canary:END' "$SKILL"; then
          sed -i.tmp '/verify-canary:BEGIN/,/verify-canary:END/d' "$SKILL" && rm -f "$SKILL.tmp"
        elif grep -q 'verify-canary:' "$SKILL"; then
          echo "UNPAIRED canary delimiter in $SKILL — refusing to range-delete." >&2
          echo "Recover from $SKILL.verify-backup after checking for concurrent edits." >&2
          return 1
        fi
      }
      trap cleanup EXIT INT TERM

      # Insert ATOMICALLY: build the canaried copy alongside, then rename over
      # the target. rename(2) is atomic, so the file is either the original or
      # the fully-delimited version — never a torn half with an orphan BEGIN.
      add_canary "$SKILL" > "$SKILL.new" && mv -f "$SKILL.new" "$SKILL"
      # ...run the probe...
      ```
      Then confirm the canary token no longer appears anywhere under the
      learned skill.

      **Two failure modes are closed here, and both are worth naming.** A
      non-atomic insert can be interrupted after `BEGIN` is written and before
      `END` is — and a naive `sed '/BEGIN/,/END/d'` on that file deletes
      everything from `BEGIN` to end-of-file, destroying the accumulated
      learnings *and* the protected regions. Writing through a temp file and
      renaming makes that state unreachable; the paired-delimiter guard means
      that even if it somehow occurs, cleanup refuses rather than amputating the
      file. This is the one case where the backup earns its keep — as the
      recovery path a human reaches for, not as an automatic restore.

      **Cleanup must be a surgical block delete, not a snapshot restore.** The
      learned skill is machine-wide and other sessions write to it: if one
      adopts a staged learning or re-runs the installer while your probe is in
      flight, restoring a backup taken beforehand silently destroys that
      legitimate update — and leaves its author believing their approved
      calibration is live. A range delete of the delimiters touches only the
      lines you added and leaves any concurrent edit intact. This is the reason
      the canary is delimited at all.

      Keep a backup if you like, but as a diagnostic, never as the restore
      mechanism. The only case where deleting the directory is right is when the
      skill **did not exist before** your run — and even then, re-check that no
      ledger rows appeared meanwhile before removing it.

      Then confirm the canary token no longer appears anywhere under the
      learned skill.

   **Residual risk, stated plainly:** a `SIGKILL`, a power loss, or a container
   torn out from under the session beats every trap. No in-session instruction
   can close that hole, so the canary is designed to be **harmless if it does
   survive**, and three independent things clean up after it:
   - it is tagged `provenance: canary (NOT evidence)`, and the learned skill's
     protected APPENDIX instructs the agent never to treat such a line as
     evidence — so a survivor is inert, not misleading;
   - it sits inside `verify-canary` delimiters, so any sweep is a deterministic
     block delete with no false positives;
   - **every entry point to the loop sweeps it** — this skill, and
     `model-right-sizer-install` — so the next touch of the learned skill from
     any direction removes it, rather than waiting for someone to re-run a
     verification they have no reason to run.
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
5. **Restore, then verify the restore.** Delete the delimited canary block (or
   restore the backup), then grep for the codename under the learned skill and
   confirm zero hits. An unverified cleanup is not a cleanup.

**Two traps worth knowing before you run it:**

- **Do not try to sandbox this with `CLAUDE_CONFIG_DIR`.** Relocating the config
  directory also relocates authentication away from the OS keychain, and the
  probe fails with `Not logged in` rather than telling you anything about
  discovery. The test has to run against the real config directory.
- **Therefore it writes into the user's actual environment** — confirm with them
  first, never clobber an existing install (back it up and restore it, or abort),
  and treat cleanup as failure-safe rather than best-effort.

> **Never leave canary content behind.** A fabricated learning sitting in a real
> learned skill is indistinguishable from a measured one, and the agent will
> cite it with the authority of evidence. Cleanup is part of the test, not an
> optional step afterwards — which is why it is structured as sweep → back up →
> delimited insert → restore-on-every-exit-path rather than a trailing
> "remember to delete this". If the target already held real learnings, restore
> the backup or remove *only* the delimited block — never the directory.

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
[`templates/ledger-entry.schema.json`](../../templates/ledger-entry.schema.json).
That catches unknown keys and off-vocabulary `stage_kind` values — but be clear
about the boundary: **schema validation is not content sanitization.** `lesson`
and both model fields accept arbitrary strings, so a row naming a repo passes
validation cleanly.

So the automated half cannot finish this check. **Read every `lesson` field
yourself.** This human/agent read is the *only* control on free-text leakage
after the fact, which is why INTEGRITY is a check in its own right rather than
a line item under "run the validator".

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
