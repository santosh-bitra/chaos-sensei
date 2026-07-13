# Chaos Sensei

Repo-aware chaos engineering and incident training agent.

Chaos Sensei reads your infrastructure-as-code repository, understands your tech stack, injects controlled reversible failures into safe environments, observes how you debug, provides hints, verifies your fixes, and generates a learning report.

## What it is

Chaos Sensei is an **incident training platform** for DevOps, SRE, platform, cloud, and application teams.

It helps you:
- Practice debugging real-world production-style failures in controlled environments
- Learn failure modes and resolution strategies without risk
- Develop muscle memory for troubleshooting
- Build team confidence before incidents happen
- Document incident patterns and solutions

## What it is not

Chaos Sensei is **not** a tool for:
- Attacking or damaging systems
- Running unapproved experiments
- Chaos testing in production without explicit safety controls

It is designed for **authorized training environments only**.

## Quick Start

### Installation

```bash
curl -fsSL https://raw.githubusercontent.com/chaos-sensei/chaos-sensei/main/install.sh | bash
```

Or with pip:

```bash
pip install chaos-sensei
```

### Basic Usage

```bash
# Initialize config in your infrastructure repo
cd your-infra-repo
chaos-sensei init

# Scan for supported technologies
chaos-sensei scan .

# See available training scenarios
chaos-sensei plan --env staging

# Start a training session (scenario is hidden)
chaos-sensei start --scenario hidden

# Get hints as you debug
chaos-sensei hint

# Check if you've fixed it
chaos-sensei check

# View full incident report and rollback
chaos-sensei give-up
```

## Supported Technologies

| Technology | Status | Notes |
|---|---|---|
| **Kubernetes** | ✅ MVP | Full support for core scenarios |
| **Helm** | 🔄 Planned | v0.2 |
| **Terraform** | 🔄 Planned | v0.4 (read-only initially) |
| **Terragrunt** | 🔄 Planned | v0.4 |
| **Docker Compose** | 🔄 Planned | v0.3 |
| **AWS** | 🔄 Planned | v0.5 |
| **Azure** | 🔄 Planned | v0.5 |
| **GCP** | 🔄 Planned | v0.5 |
| **Service Mesh** | 🔄 Planned | v0.5 |

## Available Scenarios

### Kubernetes (Current MVP)

- **Service Selector Mismatch** — Service no longer routes to intended pods
- **Pod Crash Loop** — Pod crashes due to missing configuration (Coming soon)
- **ConfigMap Missing Key** — Application can't find required config (Coming soon)
- More scenarios coming in v0.2+

## Safety by Default

Chaos Sensei enforces strict safety by default:

```yaml
safety:
  allow_production: false          # Production disabled by default
  require_confirmation: true        # User approval required
  rollback_required: true           # Rollback is mandatory
  max_duration_minutes: 20          # Automatic timeout
  
  forbidden_namespaces:
    - kube-system
    - production
    - prod
    - ...
  
  forbidden_resource_kinds:
    - PersistentVolumeClaim
    - Secret
    - ClusterRole
    - ...
```

All safety settings can be configured in `chaos-sensei.yaml`.

## Configuration

Create `chaos-sensei.yaml` in your repo:

```yaml
version: v1

project:
  name: my-platform

environment: staging

mode:
  root_cause_visibility: hidden      # hidden | visible | partial
  hints_before_reveal: 3
  auto_rollback_on_give_up: true
  auto_report: true

safety:
  allow_production: false
  require_confirmation: true
  rollback_required: true
  max_duration_minutes: 20
  
  allowed_namespaces:
    - apps
    - staging
  
  forbidden_namespaces:
    - kube-system
    - production
    - prod

providers:
  kubernetes:
    enabled: true
    context: minikube
    namespace_default: apps
  
  helm:
    enabled: false
  
  terraform:
    enabled: false
```

## Architecture

Chaos Sensei is built on a **repo-agnostic, tech-agnostic** core with pluggable providers:

```
┌─────────────────────────────────────────┐
│   Chaos Sensei Core Engine              │
│  (config, session, safety, orchestration)
└─────────────────────────────────────────┘
           │
           ├─ Provider Interface
           │
           ├─ KubernetesProvider ✅
           ├─ HelmProvider (v0.2)
           ├─ TerraformProvider (v0.4)
           ├─ DockerComposeProvider (v0.3)
           ├─ AWSProvider (v0.5)
           └─ ...
           │
           └─ Tool Wrappers
              (kubectl, helm, terraform, aws-cli, ...)
```

**Key principles:**

- **Repo-agnostic**: Detects technology via file patterns, not assumptions
- **Tech-agnostic**: Core engine doesn't care about infrastructure details
- **Provider-based**: Each technology is a plugin implementing the same interface
- **Safe by default**: Whitelist model with conservative defaults
- **Reversible**: Snapshots enable complete rollback

## Commands

```bash
chaos-sensei init                   # Create chaos-sensei.yaml
chaos-sensei scan .                 # Detect supported technologies
chaos-sensei plan --env staging     # List available scenarios
chaos-sensei start --scenario NAME  # Start session (hidden = random)
chaos-sensei hint                   # Get next hint
chaos-sensei check                  # Verify if fixed
chaos-sensei give-up                # Rollback and show answer
chaos-sensei rollback               # Manual rollback
chaos-sensei report                 # Show incident report
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/chaos-sensei/chaos-sensei.git
cd chaos-sensei
pip install -e ".[dev]"
pytest -v
```

## Security

This tool performs real infrastructure changes in controlled environments. See [SECURITY.md](SECURITY.md) for security guidelines and responsible disclosure.

**Critical principles:**

1. **Never enable production by default** — Always require explicit opt-in
2. **Always rollback** — Every fault is reversible
3. **Always verify permissions** — Check RBAC before injection
4. **Always log actions** — Full audit trail required
5. **Never automate without confirmation** — Always require human approval

## License

Apache License 2.0 — See [LICENSE](LICENSE)

## Roadmap

### v0.1 (Current)
- ✅ CLI with core commands
- ✅ Kubernetes provider MVP
- ✅ 1 scenario (service selector mismatch)
- ✅ Safety policy engine
- ✅ Rollback system
- ✅ Markdown reports

### v0.2
- 🔄 Helm provider
- 🔄 2+ Kubernetes scenarios
- 🔄 Hints and scoring
- 🔄 Git diff tracking

### v0.3
- 🔄 Docker Compose provider
- 🔄 Prometheus/log integration
- 🔄 Difficulty levels

### v0.4
- 🔄 Terraform provider (read-only)
- 🔄 Cloud dependency mapping
- 🔄 Provider SDK for custom providers

### v0.5
- 🔄 AWS/Azure/GCP providers
- 🔄 Service mesh support
- 🔄 Web UI

### v1.0
- 🔄 Multi-agent orchestration
- 🔄 Scenario marketplace
- 🔄 Team training mode
- 🔄 CI/CD integration

## Resources

- [Architecture Guide](docs/architecture.md) — Design and core concepts
- [Safety Model](docs/safety-model.md) — Security and safety guidelines
- [Writing Providers](docs/writing-providers.md) — Create custom providers
- [Writing Scenarios](docs/writing-scenarios.md) — Define new training scenarios

## Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/chaos-sensei/chaos-sensei/issues)
- 💬 [Discussions](https://github.com/chaos-sensei/chaos-sensei/discussions)

## Acknowledgments

Inspired by incident response drills, chaos engineering best practices, and the need for better operator training in modern infrastructure.

---

**Start your incident training journey today.**

```bash
chaos-sensei init
chaos-sensei scan .
chaos-sensei start --scenario hidden
```
