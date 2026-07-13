# Changelog

All notable changes to Chaos Sensei will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Helm provider support
- Docker Compose provider support
- Additional Kubernetes scenarios (pod crash, configmap)
- Hints system
- Scoring/difficulty system
- Prometheus integration
- Web UI
- Multi-agent orchestration

## [0.1.0] - 2025-07-05

### Added
- Initial MVP release
- Core Chaos Sensei engine
- Configuration management with Pydantic
- Session management for tracking experiments
- Kubernetes provider implementation
- Service selector mismatch scenario
- CLI with core commands (init, scan, plan, start, hint, check, give-up, rollback, report)
- Safety policy enforcement with whitelist model
- Snapshot and rollback system
- Tool wrappers for safe kubectl execution
- Exception hierarchy for error handling
- Unit test structure
- GitHub Actions CI/CD workflows
- Docker support
- Comprehensive documentation:
  - README with feature overview
  - Getting started guide
  - Architecture guide
  - Safety model documentation
  - Security guidelines
  - Contributing guidelines
- Apache 2.0 license
- Installation script (install.sh)
- Makefile for development commands

### Architecture
- Repo-agnostic: Detects technology via file patterns
- Tech-agnostic: Core engine independent of infrastructure specifics
- Provider-based: Pluggable providers for different technologies
- Safe by default: Whitelist model with conservative defaults
- Reversible: All operations are fully rollbackable

---

For the current development status and roadmap, see [README.md](README.md).
