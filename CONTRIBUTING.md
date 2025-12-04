# Contribution

Thank you for your interest in contributing! Please read [CloudZero's general contribution guidelines](GENERAL-CONTRIBUTING.md) before getting started.

## Documentation

All code changes should include appropriate documentation:

- **Code-level documentation**: Add docstrings for all public functions, classes, and modules
- **README updates**: Update the README.md if your changes affect installation, usage, or features
- **Docs site**: If this project has external documentation, include a link to the corresponding docs PR
- **CloudZero integration**: Include links to relevant [CloudZero documentation](https://docs.cloudzero.com/) where applicable

**Documentation standards:**
- Aim for 100% documentation coverage for new public APIs
- Use clear, concise language
- Include code examples where helpful
- Document parameters, return values, and exceptions

## Environment Setup

### Prerequisites

Before contributing, ensure you have:
- Python 3.11 or higher (for Python projects)
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager (for Python projects)
- Node.js 18+ and npm (for JavaScript projects)
- Git configured with your GitHub account

### Initial Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
   cd REPO_NAME
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/cloudzero/REPO_NAME.git
   ```

4. Install dependencies:

   **For Python projects:**
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Sync dependencies (creates venv automatically)
   uv sync

   # Or install with dev dependencies
   uv sync --extra dev
   ```

   **For JavaScript projects:**
   ```bash
   npm install
   ```

5. Create a new branch for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

For more detailed installation steps, see the [README installation section](README.md#installation).

## Testing

We maintain high test coverage to ensure code quality and prevent regressions.

### Test Structure

- Place tests in the `tests/` directory
- Name test files with the pattern `test_*.py` (Python) or `*.test.js` (JavaScript)
- Group related tests in test classes or describe blocks
- Use descriptive test names that explain what is being tested

### Writing Tests

**Python testing guidelines:**
- Use `pytest` for all tests
- Follow the Arrange-Act-Assert pattern
- Use fixtures for common test setup
- Mock external dependencies

**JavaScript testing guidelines:**
- Use Jest or your project's test framework
- Write unit tests for individual functions
- Write integration tests for component interactions
- Maintain test isolation

### Running Tests

**Python projects:**
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_module.py

# Run specific test
uv run pytest tests/test_module.py::test_function_name
```

**JavaScript projects:**
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

### Test Coverage Requirements

- New code should have at least 80% test coverage
- Critical paths should have 100% coverage
- PRs that decrease overall coverage may be rejected unless justified

## Code Quality Tools

We use automated tools to maintain code quality and consistency.

### Python Projects

**Formatting with Ruff:**
```bash
uv run ruff format .
```

**Linting with Ruff:**
```bash
uv run ruff check .
uv run ruff check --fix .  # Auto-fix issues
```

**Run all checks:**
```bash
# Format, lint, and test
uv run ruff format . && uv run ruff check . && uv run pytest
```

### JavaScript Projects

**Formatting with Prettier:**
```bash
npm run format
```

**Linting with ESLint:**
```bash
npm run lint
npm run lint:fix  # Auto-fix issues
```

**Type checking (if using TypeScript):**
```bash
npm run type-check
```

### Pre-commit Hooks

We recommend using pre-commit hooks to catch issues before committing:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for function signatures
- Maximum line length: 100 characters
- Use meaningful variable and function names
- Write docstrings for all public APIs (Google or NumPy style)
- Code formatting is handled by Ruff formatter (replaces Black)

**Preferred Python Libraries:**
- **Data manipulation**: Use `polars` (prefer over `pandas`)
- **HTTP client**: Use `httpx` (prefer over `requests`)
- **Data validation**: Use `pydantic` v2
- **AWS Lambda**: Use `aws-lambda-powertools` (when building Lambda functions)

### JavaScript Style

- Use ES6+ features
- Prefer `const` over `let`, avoid `var`
- Use meaningful variable and function names
- Add JSDoc comments for complex functions
- Follow the project's ESLint configuration

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or auxiliary tool changes

**Examples:**
```
feat(api): add support for new endpoint

fix(auth): resolve token expiration issue

docs(readme): update installation instructions
```

## Assets Compilation

### Python Projects

If your project includes compiled assets:

```bash
# Build distribution packages
uv build

# Build Docker images (if applicable)
docker build -t project-name .
```

### JavaScript Projects

If your project requires asset compilation:

```bash
# Build for production
npm run build

# Build for development
npm run build:dev

# Watch mode for development
npm run watch
```

## CI/CD Information

All PRs must pass continuous integration checks before merging.

### GitHub Actions Checks

Our CI pipeline runs:
1. **Linting**: Code style and quality checks
2. **Tests**: Full test suite with coverage reporting
3. **Security scanning**: Dependency vulnerability checks
4. **Build verification**: Ensures project builds successfully

### Passing CI Checks

To ensure your PR passes CI:

1. Run all quality checks locally before pushing
2. Fix any linting errors
3. Ensure all tests pass
4. Maintain or improve test coverage
5. Resolve any security vulnerabilities in dependencies

If CI fails:
- Review the error logs in GitHub Actions
- Fix issues locally
- Push updates to your branch
- CI will automatically re-run

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows the project's style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventional commits format
- [ ] Branch is up to date with main/master

### PR Description

Include in your PR description:
- **Summary**: What changes does this PR introduce?
- **Motivation**: Why are these changes needed?
- **Testing**: How was this tested?
- **Screenshots**: Include screenshots for UI changes
- **Breaking changes**: Clearly mark any breaking changes
- **Related issues**: Link to related GitHub issues

### Review Process

- PRs require at least one approval from maintainers
- Address all reviewer feedback
- Keep PRs focused and reasonably sized
- Be responsive to comments and questions
- Once approved, a maintainer will merge your PR

## Getting Help

If you need help:
- Check existing [GitHub Issues](../../issues)
- Review the [README](README.md) documentation
- Ask questions in PR comments
- Contact the team at support@cloudzero.com

## Additional Resources

- [CloudZero General Contributing Guidelines](GENERAL-CONTRIBUTING.md)
- [Code of Conduct](CODE-OF-CONDUCT.md)
- [Security Policy](SECURITY.md)
- [CloudZero Documentation](https://docs.cloudzero.com/)

Thank you for contributing to make this project better!