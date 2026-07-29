# Security Policy

## Reporting a Vulnerability

The CloudZero team takes security issues seriously. We appreciate your efforts to responsibly disclose your findings.

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing [security@cloudzero.com](mailto:security@cloudzero.com).

Please include the following information in your report:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Scope Notes for This Repository

- **Supply chain:** the `model-right-sizer-install` skill may run `/plugin marketplace add cloudzero/cloudzero-claude-marketplace` and `/plugin install model-right-sizer@cloudzero` in a consumer's environment when the agent it points at isn't already discoverable — the only install action in this repository, scoped to this marketplace's own plugin, and gated on the user's explicit confirmation before the commands run. It otherwise writes a single marker-delimited block to the target repo's `CLAUDE.md`.
- **Tool grants:** the cost-analyst `optimize-triage` skill is the only skill granted `Bash`, used for read-only cloud CLI commands; its documentation instructs running with read-only credentials. The `model-right-sizer` agent is read-only (`Read, Grep, Glob, WebFetch, Task`).
- CI validators (`scripts/`) enforce that agent tool grants stay organization-agnostic and include a secret-shaped-string tripwire.

## Response Process

After submitting a vulnerability report, you can expect:

1. A response acknowledging your report
2. An assessment of the vulnerability and its impact
3. Communication about the fix timeline
4. Credit for your discovery (if desired) when the vulnerability is publicly disclosed

Thank you for helping keep CloudZero and our users safe!
