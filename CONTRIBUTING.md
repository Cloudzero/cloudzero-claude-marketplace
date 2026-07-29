# Contributing to CloudZero

Thank you for your interest in contributing to CloudZero, the CloudZero plugin marketplace for Claude Code! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check if the issue already exists in GitHub Issues
2. If not, create a new issue with a clear description
3. Include steps to reproduce for bugs
4. For feature requests, explain the use case

### Submitting Changes

1. Fork the repository
2. Create a new branch for your changes
3. Make your changes following our coding standards
4. Test your changes thoroughly
5. Submit a pull request with a clear description

### Pull Request Guidelines

- Keep changes focused and atomic
- Follow existing code style and conventions
- Update documentation as needed
- Ensure all SKILL.md files include proper frontmatter (name, description, author, version, license)
- Include tests for new functionality when applicable

## Coding Standards

### SKILL.md Files

All skill files must include YAML frontmatter with:

```yaml
---
name: skill-name
description: Brief description of the skill
author: Your Name <email@example.com>
version: X.Y.Z
license: Apache-2.0
---
```

### Adding a New Plugin

To add a plugin to the marketplace:

1. Create a self-contained directory at `plugins/<plugin-name>/` with a `.claude-plugin/plugin.json` manifest (`name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords` — mirror an existing plugin's manifest)
2. Put skills in `skills/<skill-name>/SKILL.md` and agents in `agents/<agent-name>.md` inside the plugin directory
3. Register the plugin in `.claude-plugin/marketplace.json` with an entry like `{ "name": "<plugin-name>", "source": "./plugins/<plugin-name>/" }` (keep the leading `./` and trailing `/`)
4. Check for name conflicts with existing plugins' skills, agents, commands, and MCP server keys — installed plugins share one namespace
5. Update the root README (Available Plugins, Repository Structure, Installation, Available Skills) and the changelog

CI runs `scripts/validate_plugin_manifest.py` and `scripts/validate_agent_file.py` on every push/PR — run them locally (plus `pytest tests/`) before opening a PR.

### Documentation

- Use clear, concise language
- Include examples where helpful
- Keep README files up to date

## License

By contributing to this project, you agree that your contributions will be licensed under the Apache License 2.0.

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to providing a welcoming and inclusive environment for all contributors.

## Questions?

If you have questions about contributing, please contact [support@cloudzero.com](mailto:support@cloudzero.com).
