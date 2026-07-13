# Contributing to Chaos Sensei

Thank you for your interest in contributing! This document provides guidelines and instructions.

## Code of Conduct

Be respectful and inclusive. Harassment, discrimination, and bad faith are not tolerated.

## How to Contribute

### Report Bugs

1. **Search existing issues** — Your bug may already be reported
2. **Create a clear issue** with:
   - Clear title describing the bug
   - Steps to reproduce
   - Expected vs. actual behavior
   - Environment info (OS, Python version, Kubernetes version, etc.)
   - Error messages or logs

### Suggest Features

1. **Check existing issues and discussions** — Avoid duplicates
2. **Explain the use case** — Why is this needed?
3. **Describe the proposed solution** — How should it work?
4. **Consider alternatives** — What else could address this?

### Improve Documentation

Documentation improvements are always welcome:

- Fix typos and clarify explanations
- Add examples and use cases
- Improve architecture documentation
- Expand the FAQ

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- Kubernetes cluster (for testing Kubernetes provider)
- kubectl (for local testing)

### Setup

```bash
# Clone the repository
git clone https://github.com/chaos-sensei/chaos-sensei.git
cd chaos-sensei

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
chaos-sensei --help
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=chaos_sensei

# Run specific test
pytest tests/test_config.py::test_config_creation
```

### Code Quality

```bash
# Format code with black
black chaos_sensei tests

# Sort imports with isort
isort chaos_sensei tests

# Lint with ruff
ruff check chaos_sensei tests

# Type check with mypy
mypy chaos_sensei
```

### Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Submitting Changes

### Creating a Branch

```bash
# Create a feature branch
git checkout -b feature/your-feature-name
# or for bugs
git checkout -b fix/issue-description
```

Branch naming conventions:
- `feature/` — New features
- `fix/` — Bug fixes
- `docs/` — Documentation
- `test/` — Tests
- `refactor/` — Code cleanup

### Commit Messages

Write clear, descriptive commit messages:

```
Short summary (50 chars or less)

More detailed explanation of the change if needed.
Explain WHY the change was made, not WHAT was changed
(the code already shows that).

- Bullet points for multiple changes
- Keep it concise and helpful
```

### Pull Request Process

1. **Update your branch** — Rebase on latest main
2. **Run tests** — `pytest -v`
3. **Run quality checks** — `black`, `ruff`, `mypy`
4. **Push to GitHub** — `git push origin feature/your-feature`
5. **Open a PR** with:
   - Clear title describing the change
   - Description of what changed and why
   - Link to related issues
   - Any breaking changes clearly noted

## Architecture Overview

```
chaos_sensei/
├── core/              # Engine, config, session, exceptions
├── providers/         # Base and implementation (Kubernetes, etc.)
├── tools/             # Safe command wrappers (kubectl, helm, etc.)
├── cli.py             # Command-line interface
└── __init__.py        # Package exports
```

### Key Design Principles

1. **Repo-agnostic** — Core shouldn't assume specific tech
2. **Tech-agnostic** — Each tech is a pluggable provider
3. **Safe by default** — Whitelist model, conservative defaults
4. **Reversible** — All operations have snapshots and rollbacks
5. **Well-tested** — Unit and integration tests required
6. **Well-documented** — Code and behavior should be clear

## Adding a New Provider

To add support for a new technology (Docker, Terraform, etc.):

1. **Create provider module** — `chaos_sensei/providers/name/`
2. **Implement the Provider interface** — `detect()`, `discover()`, `inject()`, etc.
3. **Create scenarios** — YAML files describing training scenarios
4. **Write tests** — Unit tests for your provider
5. **Update docs** — Document your provider
6. **Add to engine** — Register in `_init_providers()`

See [Writing Providers](docs/writing-providers.md) for detailed guide.

## Adding a New Scenario

To add a new training scenario:

1. **Create scenario YAML** — `chaos_sensei/providers/TECH/scenarios/name.yaml`
2. **Define the scenario** — target, fault, symptoms, root cause, hints, success criteria
3. **Implement injection** — Add `_inject_scenario_name()` to provider
4. **Add verification** — Update `verify_fix()` to detect the solution
5. **Test thoroughly** — Manual testing in staging environment
6. **Document** — Explain the learning objective and debugging path

See [Writing Scenarios](docs/writing-scenarios.md) for details.

## Testing Guidelines

### Unit Tests

Test individual functions and classes:

```python
def test_config_creation():
    config = Config()
    assert config.version == "v1"
```

### Integration Tests

Test multiple components together:

```python
def test_end_to_end_scenario(k8s_cluster):
    engine = ChaosSenseiEngine(repo_path)
    engine.start("k8s-service-selector-mismatch")
    engine.check()  # Should return not fixed
    # ... fix ...
    engine.check()  # Should return fixed
```

### Test Coverage

- Aim for >80% code coverage
- Test both happy and sad paths
- Test error conditions and exceptions

## Documentation

### Code Comments

- Default: No comments (self-explanatory code is best)
- Add comments for non-obvious "why" decisions
- Don't comment "what" the code does (name the variable well instead)

### Module Docstrings

Every module should have a docstring explaining its purpose.

### Function Docstrings

Use this format:

```python
def verify_fix(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if issue is fixed.

    Args:
        scenario: Scenario configuration

    Returns:
        Dict with 'fixed' (bool) and 'details' (str)
    """
```

### Architecture Documentation

Update docs when changing:
- Core concepts
- Provider interface
- Plugin system
- Configuration options

## Code Style

- Follow [PEP 8](https://pep8.org/)
- Use type hints for all functions
- Use f-strings (not `.format()`)
- Line length: 100 characters (configured in pyproject.toml)

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release commit
4. Tag release: `git tag v0.X.Y`
5. Push: `git push && git push --tags`
6. GitHub Actions builds and publishes to PyPI

## Becoming a Maintainer

Become a maintainer through demonstrated contribution:
- Multiple approved PRs
- Understanding of the codebase
- Commitment to the project's vision
- Willingness to review and mentor

Contact the maintainers to discuss.

## Questions?

- 📖 [Documentation](docs/)
- 💬 [GitHub Discussions](https://github.com/chaos-sensei/chaos-sensei/discussions)
- 🐛 [Issues](https://github.com/chaos-sensei/chaos-sensei/issues)

## Thank You

Contributing to Chaos Sensei makes it better for everyone. Your effort is appreciated!

---

Happy contributing! 🚀
