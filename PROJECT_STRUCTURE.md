# Chaos Sensei Project Structure

This document describes the complete structure of the Chaos Sensei repository.

## Directory Tree

```
chaos-sensei/
├── chaos_sensei/                      # Main package
│   ├── __init__.py                   # Package initialization
│   ├── cli.py                        # Command-line interface
│   │
│   ├── core/                         # Core orchestration
│   │   ├── __init__.py
│   │   ├── engine.py                 # Main ChaosSenseiEngine
│   │   ├── config.py                 # Configuration management (Pydantic)
│   │   ├── session.py                # Session state management
│   │   └── exceptions.py             # Custom exceptions
│   │
│   ├── providers/                    # Technology providers (pluggable)
│   │   ├── __init__.py
│   │   ├── base.py                   # Abstract Provider base class
│   │   │
│   │   └── kubernetes/               # Kubernetes provider
│   │       ├── __init__.py
│   │       ├── provider.py           # KubernetesProvider implementation
│   │       └── scenarios/            # Training scenarios
│   │           └── service_selector_mismatch.yaml
│   │
│   └── tools/                        # Safe command wrappers
│       ├── __init__.py
│       └── kubectl.py                # Kubernetes kubectl wrapper
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── test_config.py               # Config tests
│   ├── unit/                        # Unit tests (to be created)
│   ├── integration/                 # Integration tests (to be created)
│   └── fixtures/                    # Test fixtures (to be created)
│
├── docs/                            # Documentation
│   ├── architecture.md              # Architecture and design
│   ├── safety-model.md              # Safety guidelines
│   ├── getting-started.md           # Quick start guide
│   ├── writing-providers.md         # (Placeholder)
│   ├── writing-scenarios.md         # (Placeholder)
│   └── faq.md                       # (Placeholder)
│
├── examples/                        # Example scenarios
│   ├── k8s-helm-demo/              # (Placeholder)
│   ├── terraform-aws-demo/         # (Placeholder)
│   └── docker-compose-demo/        # (Placeholder)
│
├── .github/
│   └── workflows/
│       ├── test.yml                # Test CI/CD
│       └── release.yml             # Release CI/CD
│
├── .gitignore                      # Git ignore patterns
├── pyproject.toml                  # Project configuration
├── README.md                       # Project overview
├── SECURITY.md                     # Security guidelines (CRITICAL)
├── CONTRIBUTING.md                # Contribution guidelines
├── LICENSE                        # Apache 2.0 license
├── CHANGELOG.md                   # Version history
├── Dockerfile                     # Container image
├── Makefile                       # Development commands
├── install.sh                     # Installation script
└── PROJECT_STRUCTURE.md           # This file
```

## Key Files Explained

### Core Application

- **chaos_sensei/__init__.py** — Package exports and version
- **chaos_sensei/cli.py** — CLI commands (init, scan, plan, start, hint, check, etc.)
- **chaos_sensei/core/engine.py** — Main orchestration engine
- **chaos_sensei/core/config.py** — Configuration with Pydantic validation
- **chaos_sensei/core/session.py** — Active session state
- **chaos_sensei/core/exceptions.py** — Custom exception hierarchy

### Providers

- **chaos_sensei/providers/base.py** — Abstract Provider interface
- **chaos_sensei/providers/kubernetes/provider.py** — Kubernetes implementation
- **chaos_sensei/providers/kubernetes/scenarios/\*.yaml** — Scenario definitions

### Tools

- **chaos_sensei/tools/kubectl.py** — Safe kubectl wrapper (no arbitrary shell)

### Configuration & Packaging

- **pyproject.toml** — Dependencies, metadata, tool configs (ruff, mypy, pytest)
- **Dockerfile** — Container image
- **install.sh** — Bash installation script

### Documentation

- **README.md** — Project overview, quick start, roadmap
- **SECURITY.md** — **CRITICAL** — Security and safety guidelines
- **CONTRIBUTING.md** — Contribution guidelines
- **docs/architecture.md** — Architecture and design decisions
- **docs/safety-model.md** — Safety enforcement mechanisms
- **docs/getting-started.md** — Step-by-step getting started guide

### CI/CD

- **.github/workflows/test.yml** — Run tests on all Python versions
- **.github/workflows/release.yml** — Build and publish to PyPI

### Development

- **Makefile** — Development commands (test, lint, format, etc.)
- **tests/test_config.py** — Example unit test

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│         Chaos Sensei Application                │
├─────────────────────────────────────────────────┤
│                                                 │
│   CLI (typer + rich)                           │
│   ↓                                             │
│   Engine (orchestration)                       │
│   ↓                                             │
│   Config (validation) + Safety (enforcement)   │
│   ↓                                             │
│   Session (state management)                   │
│   ↓                                             │
│   Provider Interface                           │
│   ├─ KubernetesProvider ✅                      │
│   ├─ HelmProvider (v0.2)                       │
│   ├─ TerraformProvider (v0.4)                  │
│   └─ ...                                       │
│   ↓                                             │
│   Tools (safe command wrappers)                │
│   ├─ Kubectl                                   │
│   ├─ Helm                                      │
│   └─ ...                                       │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Development Workflow

### Setup

```bash
git clone https://github.com/chaos-sensei/chaos-sensei.git
cd chaos-sensei
pip install -e ".[dev]"
```

### Code Quality

```bash
# Test
pytest -v

# Lint
ruff check .
mypy chaos_sensei

# Format
black chaos_sensei
isort chaos_sensei

# All checks
make check
```

### Adding Features

1. **Adding a Provider** — Create new folder in `chaos_sensei/providers/`
2. **Adding a Scenario** — Create YAML in `providers/TECH/scenarios/`
3. **Adding a Tool** — Create wrapper in `chaos_sensei/tools/`
4. **Adding CLI Commands** — Add functions in `chaos_sensei/cli.py`

## Configuration Files

### pyproject.toml

Defines:
- Project metadata
- Dependencies (typer, pydantic, pyyaml, etc.)
- Optional dependencies (dev, kubernetes)
- Tool configs (ruff, mypy, pytest, black, isort)

### chaos-sensei.yaml

User creates in their repo:
- Environment (staging, production, etc.)
- Safety settings (forbidden namespaces, kinds)
- Provider configuration

## Dependencies

### Core

- **typer** — CLI framework
- **pydantic** — Configuration validation
- **pyyaml** — YAML parsing
- **rich** — Terminal formatting
- **jinja2** — Template rendering
- **requests** — HTTP client

### Optional

- **kubernetes** — Kubernetes Python client (optional)

### Development

- **pytest** — Testing
- **ruff** — Linting
- **mypy** — Type checking
- **black** — Code formatting
- **isort** — Import sorting

## Testing Strategy

Current test coverage:
- **Unit tests** — `tests/test_config.py`
- **Integration tests** — Planned
- **E2E tests** — Planned

Run tests:

```bash
pytest -v --cov=chaos_sensei
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Commit: `git commit -am "Release v0.X.Y"`
4. Tag: `git tag v0.X.Y`
5. Push: `git push && git push --tags`
6. GitHub Actions builds and publishes to PyPI

## Important Notes

### Security

- **READ SECURITY.md FIRST** — This is critical!
- All safety checks are in `chaos_sensei/core/config.py`
- Tool wrappers never execute arbitrary shell
- Whitelist model for allowed operations

### Extensibility

- Provider interface is well-defined in `base.py`
- Adding a provider doesn't require modifying core
- Scenarios are data-driven (YAML files)
- Tools are modular and reusable

### Packaging

- Package is installable via pip
- Docker image available
- Installation script for manual setup
- CI/CD handles publishing

## Status: MVP (v0.1.0)

Current implementation includes:
- ✅ Core engine
- ✅ CLI with all core commands
- ✅ Kubernetes provider (partial)
- ✅ 1 scenario (service selector mismatch)
- ✅ Configuration management
- ✅ Safety enforcement
- ✅ Session management
- ✅ Comprehensive documentation

Not yet implemented:
- ❌ Additional Kubernetes scenarios (pod crash, configmap)
- ❌ Other providers (Helm, Terraform, etc.)
- ❌ Hints system (hardcoded hints in scenarios)
- ❌ Scoring/difficulty filtering
- ❌ Web UI
- ❌ Multi-agent system

## Next Steps for Development

1. **Expand Kubernetes scenarios** — Pod crash, configmap missing key
2. **Add Helm provider** — v0.2
3. **Improve hints system** — Hint generator from LLM
4. **Add Docker provider** — v0.3
5. **Add Terraform provider** — v0.4
6. **Add cloud providers** — AWS, Azure, GCP (v0.5)

---

**For more information:**
- See [README.md](README.md) for overview
- See [docs/architecture.md](docs/architecture.md) for design details
- See [SECURITY.md](SECURITY.md) for safety model
- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
