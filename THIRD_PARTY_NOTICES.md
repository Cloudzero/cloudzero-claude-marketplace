# Third-Party Notices

This document lists third-party software components included in or used by CloudZero, the CloudZero plugin marketplace for Claude Code.

## Overview

CloudZero (this plugin marketplace) is a collection of AI-powered skills and plugins for cloud cost analysis. This project primarily consists of documentation and configuration files (Markdown, JSON) and does not include third-party software libraries or dependencies.

## Runtime Dependencies

This project relies on the following external services at runtime:

### CloudZero MCP Server

- **Provider:** CloudZero, Inc.
- **Description:** Model Context Protocol server for cloud cost data access
- **License:** CloudZero Terms of Service
- **URL:** https://www.cloudzero.com

### Claude Code

- **Provider:** Anthropic
- **Description:** AI assistant platform that executes the skills
- **License:** Anthropic Terms of Service
- **URL:** https://www.anthropic.com

## Development Dependencies

Used only for developing and validating this repository — not shipped with, or required by, any plugin at runtime:

### pytest

- **Description:** Test framework used by CI to run the validator test suites in `tests/`
- **License:** MIT
- **URL:** https://pytest.org

### PyYAML

- **Description:** YAML parser used by the CI validators in `scripts/` to check agent and skill frontmatter
- **License:** MIT
- **URL:** https://pyyaml.org

### uv

- **Description:** Python package runner used to execute the validators and tests in CI and locally
- **License:** Apache-2.0 OR MIT
- **URL:** https://docs.astral.sh/uv/

## Embedded Code

This repository does not embed any third-party code or libraries.

---

If you believe any third-party components have been overlooked, please contact [support@cloudzero.com](mailto:support@cloudzero.com).
