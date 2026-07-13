# Architecture Guide

This document describes Chaos Sensei's architecture and core design principles.

## Core Principles

### 1. Repo-Agnostic

Chaos Sensei does **not** assume a specific infrastructure stack.

- **Detection**: Scans repository for file patterns (YAML, HCL, compose, etc.)
- **Discovery**: Queries running infrastructure to detect what exists
- **Plugins**: Each technology is a pluggable provider

### 2. Tech-Agnostic

The core engine is **completely independent** of specific technologies.

```
Core Engine (configuration, session, safety, orchestration)
    ↓
    Provider Interface
    ↓
    ├─ KubernetesProvider (Kubernetes-specific)
    ├─ HelmProvider (Helm-specific)
    ├─ TerraformProvider (Terraform-specific)
    └─ ...
```

The engine only knows about:
- `detect()` — Can this provider handle the repo?
- `discover()` — What resources exist?
- `list_scenarios()` — What failures can we teach?
- `inject()` — Break it
- `verify_fix()` — Is it fixed?
- `rollback()` — Restore it

### 3. Safe by Default

Safety is **enforced by default** with whitelist model:

```yaml
safety:
  allow_production: false              # Production disabled
  require_confirmation: true           # User approval required
  rollback_required: true              # Rollback is mandatory
  forbidden_namespaces: [...]          # Deny list
  forbidden_kinds: [...]               # Deny list
```

### 4. Reversible

Every operation is **fully reversible**:

1. **Snapshot** — Capture current state
2. **Inject** — Break something controlled
3. **Observe** — Collect symptoms
4. **Verify** — Check if user fixed it
5. **Rollback** — Restore original state

### 5. Pluggable

New technologies can be added as providers without touching the core:

```python
class CustomProvider(Provider):
    name = "custom"
    technology = "custom"
    
    def detect(self, repo_path: str) -> bool:
        # Can this provider run on this repo?
    
    def discover(self, repo_path: str) -> Dict[str, Any]:
        # What resources exist?
    
    # ... implement other methods ...
```

## Component Architecture

### Engine (`chaos_sensei/core/engine.py`)

Central orchestrator:

```
ChaosSenseiEngine
├── scan()          → Detect technologies
├── plan()          → List scenarios
├── start()         → Inject fault
├── hint()          → Get hint
├── check()         → Verify fix
├── rollback()      → Restore state
├── give_up()       → Rollback + report
└── report()        → Generate report
```

### Config (`chaos_sensei/core/config.py`)

Configuration management with validation:

```
Config
├── version
├── environment
├── mode
├── safety          → SafetyPolicy
└── providers       → ProvidersConfig
    ├── kubernetes
    ├── helm
    ├── terraform
    └── ...
```

### Session (`chaos_sensei/core/session.py`)

Active experiment state:

```
Session
├── metadata        → SessionMetadata
├── scenario        → Scenario dict
├── snapshot        → State snapshot
├── hint_count      → Number of hints requested
├── checks          → Verification attempts
└── rolled_back     → Rollback status
```

### Provider Interface (`chaos_sensei/providers/base.py`)

Abstract base class all providers implement:

```python
class Provider(ABC):
    name: str
    technology: str
    
    @abstractmethod
    def detect(self, repo_path: str) -> bool: ...
    
    @abstractmethod
    def discover(self, repo_path: str) -> Dict[str, Any]: ...
    
    @abstractmethod
    def list_scenarios(self, inventory: Dict[str, Any]) -> List[Dict]: ...
    
    @abstractmethod
    def preflight(self, scenario: Dict) -> Dict: ...
    
    @abstractmethod
    def snapshot(self, scenario: Dict) -> Dict: ...
    
    @abstractmethod
    def inject(self, scenario: Dict, snapshot: Dict) -> Dict: ...
    
    @abstractmethod
    def observe(self, scenario: Dict) -> Dict: ...
    
    @abstractmethod
    def verify_fix(self, scenario: Dict) -> Dict: ...
    
    @abstractmethod
    def rollback(self, scenario: Dict, snapshot: Dict) -> Dict: ...
```

### Kubernetes Provider (`chaos_sensei/providers/kubernetes/`)

Concrete implementation for Kubernetes:

```
KubernetesProvider(Provider)
├── detect()        → Look for *.yaml/*.yml with kind: fields
├── discover()      → kubectl get resources
├── list_scenarios()→ Return available scenarios
├── preflight()     → Check safety policy
├── snapshot()      → kubectl get and save
├── inject()        → kubectl patch to break
├── observe()       → kubectl get pods, events
├── verify_fix()    → kubectl rollout status
└── rollback()      → kubectl apply from snapshot
```

### Tools (`chaos_sensei/tools/`)

Safe command wrappers (never run arbitrary shell):

```
Kubectl
├── run()           → Execute kubectl with args
├── get_json()      → Get and parse JSON
├── patch_json()    → Patch resource
├── apply_json()    → Apply from dict
├── get_pods()      → Helper for pods
├── get_events()    → Helper for events
└── ...
```

### CLI (`chaos_sensei/cli.py`)

Command-line interface with rich formatting:

```bash
chaos-sensei init              # Create config
chaos-sensei scan .            # Detect techs
chaos-sensei plan --env staging# List scenarios
chaos-sensei start             # Inject fault
chaos-sensei hint              # Get hint
chaos-sensei check             # Verify fix
chaos-sensei give-up           # Rollback + report
chaos-sensei rollback          # Manual rollback
chaos-sensei report            # Show report
```

## Data Flow

### Session Lifecycle

```
1. User: chaos-sensei start
   ↓
2. Engine: Detect provider
   ↓
3. Engine: Discover resources
   ↓
4. Provider: List scenarios
   ↓
5. User: Chooses scenario (or random)
   ↓
6. Provider: Preflight check (safety)
   ↓
7. Provider: Snapshot current state
   ↓
8. Provider: Inject fault
   ↓
9. Engine: Save session to .chaos-sensei/session.json
   ↓
10. User: Debugs the problem
    ↓
11. User: chaos-sensei hint  (repeats)
    ↓
12. User: chaos-sensei check (repeats)
    ↓
13. User: chaos-sensei give-up
    ↓
14. Provider: Rollback from snapshot
    ↓
15. Engine: Generate report
    ↓
16. User: Reviews report
```

### File Organization

```
user-repo/
├── chaos-sensei.yaml           ← Configuration
├── .chaos-sensei/              ← Session data (gitignored)
│   ├── session.json           ← Active session state
│   └── report.md              ← Generated report
├── (your infra files)
└── ...
```

## Extension Points

### Adding a Provider

1. Create `chaos_sensei/providers/name/provider.py`
2. Inherit from `Provider`
3. Implement all abstract methods
4. Add provider-specific scenarios as YAML
5. Register in engine's `_init_providers()`

### Adding Scenarios

1. Create YAML file: `chaos_sensei/providers/TECH/scenarios/name.yaml`
2. Define: target, fault, symptoms, root_cause, hints, success_criteria
3. Implement injection/verification in provider
4. Test thoroughly in staging

### Adding Tools

1. Create tool wrapper in `chaos_sensei/tools/`
2. Whitelist allowed commands (never arbitrary shell)
3. Parse outputs carefully
4. Raise specific exceptions

### Adding Safety Checks

1. Add policy to `SafetyPolicy` model
2. Implement check in `config.is_safe()`
3. Enforce in provider's `preflight()`
4. Document in SECURITY.md

## Error Handling

Custom exception hierarchy:

```
ChaosSenseiException
├── ConfigError
├── ProviderError
│   ├── ProviderNotDetectedError
│   └── ProviderNotAvailableError
├── ScenarioError
│   └── ScenarioNotFoundError
├── SafetyPolicyError
├── SessionError
│   └── SessionNotFoundError
├── InjectionError
├── RollbackError
└── ToolError
    └── KubernetesToolError
```

All exceptions inherit from `ChaosSenseiException` for easy handling.

## Testing Strategy

- **Unit tests** — Test individual components
- **Integration tests** — Test provider + engine together
- **End-to-end tests** — Full scenarios in test cluster
- **Safety tests** — Verify safety policies work

## Performance Considerations

- **Lazy loading** — Providers only initialized if enabled
- **Caching** — Discovery results cached for session
- **Timeouts** — kubectl commands have 30s timeout
- **Logging** — Debug logs only if verbose flag set

## Future Enhancements

### Multi-Agent System

```
┌────────────────────────────────────┐
│  Chaos Sensei Orchestration Agent  │
├────────────────────────────────────┤
│ ├─ Repo Cartographer Agent         │
│ ├─ Scenario Designer Agent         │
│ ├─ Safety Governor Agent           │
│ ├─ Observer Agent                  │
│ ├─ Judge Agent                     │
│ ├─ Hint Master Agent               │
│ └─ Postmortem Writer Agent         │
└────────────────────────────────────┘
```

### Provider Ecosystem

- Community providers
- Provider marketplace
- Custom provider SDK

### Integration

- CI/CD pipelines
- Incident response workflows
- Team training programs
- Web UI

---

**Key insight**: By separating core from providers, Chaos Sensei can support any infrastructure without modification to the core.
