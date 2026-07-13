# Safety Model

How Chaos Sensei ensures safe operation even when breaking things on purpose.

## Philosophy

> Safety must be enforced, not optional.

Key principles:
1. **Production disabled by default** — Requires explicit opt-in
2. **Whitelist model** — Only allowed things work, everything else fails safely
3. **Reversibility** — Every action can be undone
4. **Confirmation** — Always require human approval
5. **Limits** — Operations timeout automatically
6. **Logging** — Full audit trail

## Configuration-Based Safety

All safety rules are defined in `chaos-sensei.yaml`:

```yaml
safety:
  allow_production: false
  require_confirmation: true
  rollback_required: true
  max_duration_minutes: 20
  
  allowed_namespaces:
    - default
    - apps
    - staging
  
  forbidden_namespaces:
    - kube-system
    - production
    - prod
  
  forbidden_kinds:
    - PersistentVolumeClaim
    - Secret
    - ClusterRole
```

The Config class validates all settings:

```python
config = Config.from_yaml(Path("chaos-sensei.yaml"))
if not config.is_safe(namespace="kube-system"):
    raise SafetyPolicyError("Forbidden by policy")
```

## Layered Safety Checks

### Layer 1: Configuration Validation

```
Load chaos-sensei.yaml
  ↓
Validate structure
  ↓
Validate values
  ↓
Set defaults for production-safe values
  ↓
Check `allow_production` flag
```

### Layer 2: Detection & Discovery

```
Detect technology in repo
  ↓
List available scenarios
  ↓
Filter scenarios by safety
  ↓
Present only safe scenarios to user
```

### Layer 3: Pre-flight Checks

```
User selects scenario
  ↓
Provider.preflight(scenario)
  ↓
Check: namespace allowed?
  ↓
Check: resource kind allowed?
  ↓
Check: targets allowed?
  ↓
Approved? → Continue
Blocked? → Refuse with reason
```

### Layer 4: Snapshot & Rollback

```
Capture original state
  ↓
Inject fault (user approves)
  ↓
Monitor (user debugs)
  ↓
Rollback from snapshot
  ↓
Verify recovery
```

### Layer 5: Timeout Protection

```
Session created with timestamp
  ↓
max_duration_minutes enforced
  ↓
Auto-timeout if exceeded
  ↓
Auto-rollback on timeout
```

## Safety Rules

### Forbidden Namespaces

These namespaces are **never** allowed:

```yaml
forbidden_namespaces:
  - kube-system       # Kubernetes system components
  - kube-public       # Public information
  - kube-node-lease   # Kubelet heartbeats
  - production        # Production workloads
  - prod              # Production (variant)
  - default           # (Can be enabled if needed)
```

### Forbidden Resource Kinds

These resources **cannot** be modified:

```yaml
forbidden_kinds:
  - PersistentVolumeClaim   # Data storage
  - PersistentVolume        # Cluster storage
  - CustomResourceDefinition # API extensions
  - ClusterRole             # Cluster permissions
  - ClusterRoleBinding      # Cluster permissions
  - StorageClass            # Storage configuration
  - Secret                  # Credentials/secrets
  - Namespace               # Cluster structure
```

**Why forbidden?**
- Data loss risk
- Permission escalation risk
- Cluster destabilization
- Credential exposure

## Role-Based Access Control

Example RBAC for Chaos Sensei:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: chaos-sensei
  namespace: staging
rules:
# Read most things
- apiGroups: [""]
  resources:
    - pods
    - services
    - configmaps
  verbs: ["get", "list", "watch"]

# Patch services (for scenarios)
- apiGroups: [""]
  resources:
    - services
  verbs: ["patch", "update"]

# Never allow cluster-wide changes
# (No "get" on ClusterRole, ClusterRoleBinding, etc.)
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: chaos-sensei
  namespace: staging
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: chaos-sensei
subjects:
  - kind: User
    name: user@example.com
```

## Blast Radius Classification

Every scenario is classified by scope:

| Radius | Scope | Example |
|--------|-------|---------|
| `single-pod` | One pod instance | Delete one pod |
| `single-service` | One service | Patch service selector |
| `single-deployment` | All pods in deployment | Scale to 0 replicas |
| `namespace` | All in a namespace | (Planned for v0.2) |
| `cluster` | Cluster-wide | (Future, requires explicit approval) |

Blast radius is **enforced**:
- Users see blast radius before scenario starts
- Scenarios are limited to staging/dev blast radiuses
- Production scenarios are further limited

## Rollback Guarantees

Every scenario ensures:

1. **Snapshot captured** — Current state saved before injection
2. **Injection reversible** — Same operation can undo the change
3. **Rollback tested** — Rollback path verified before prod use
4. **Automatic timeout** — Session ends after max_duration_minutes
5. **Manual recovery** — Snapshot in JSON for manual fixes if needed

Rollback process:

```python
# 1. Capture snapshot
snapshot = provider.snapshot(scenario)
# Result: {"kind": "Service", "name": "checkout", "object": {...}}

# 2. Inject fault
provider.inject(scenario, snapshot)

# 3. User debugs...

# 4. Rollback using snapshot
provider.rollback(scenario, snapshot)
# Restores object from snapshot exactly as it was

# 5. Verify recovery
provider.verify_fix(scenario)  # Should return fixed=True
```

## Approval Workflow

Default: interactive approval

```
User: chaos-sensei start
  ↓
[OUTPUT] Summary of scenario
  ↓
[PROMPT] "Are you sure? (y/n)"
  ↓
Scenario: Service selector mismatch
Blast radius: single-service
Target: checkout service in apps namespace
  ↓
User: y
  ↓
[INJECT FAULT]
```

No way to bypass confirmation by default:
- `require_confirmation: true` is the default
- No `--yes` or `--force` flags
- Session file must be manually edited to circumvent (intentional friction)

## Audit Logging

All operations are logged:

```json
{
  "metadata": {
    "session_id": "abc123",
    "repo_path": "/path/to/repo",
    "environment": "staging",
    "provider": "kubernetes",
    "created_at": "2025-07-05T10:30:00Z",
    "started_at": "2025-07-05T10:31:00Z",
    "ended_at": "2025-07-05T10:45:00Z"
  },
  "scenario": {
    "id": "k8s-service-selector-mismatch",
    "title": "Service selector mismatch",
    "target": {"kind": "service", "name": "checkout"}
  },
  "checks": [
    {"timestamp": "...", "result": {"fixed": false}},
    {"timestamp": "...", "result": {"fixed": true}}
  ],
  "rolled_back": true
}
```

Keep logs for:
- Post-incident analysis
- Training effectiveness tracking
- Safety audit trails
- Debugging issues

## Environment Isolation

Recommended setup:

### Staging Cluster
- `chaos-sensei.yaml`: `allow_production: false`
- RBAC: Limited to staging namespace
- kubeconfig: Separate from production
- Team: Training and experimentation

### Production Cluster
- `chaos-sensei.yaml`: Disabled by default
- RBAC: Extremely restricted
- kubeconfig: Separate, different user
- Team: Incident response only, with approval

```bash
# Different kubeconfigs prevent accidents
export KUBECONFIG=~/.kube/staging-config    # Staging
export KUBECONFIG=~/.kube/production-config # Production

# Different profiles
alias cs-staging='KUBECONFIG=~/.kube/staging chaos-sensei'
alias cs-prod='KUBECONFIG=~/.kube/production chaos-sensei'
```

## Emergency Procedures

### If Something Goes Wrong

1. **STOP IMMEDIATELY** — Don't continue the scenario
2. **Run rollback** — `chaos-sensei rollback`
3. **Verify recovery** — Manual kubectl checks
4. **Investigate** — What went wrong?
5. **Document** — Update procedures if needed

### If Rollback Fails

1. Get snapshot: `cat .chaos-sensei/session.json | jq '.snapshot'`
2. Manual recovery using snapshot data
3. Alert the ops/SRE team
4. Post-incident review

### If Operator Credential Compromised

1. Rotate kubeconfig immediately
2. Audit all Chaos Sensei sessions
3. Review what was accessed/modified
4. Check logs: `.chaos-sensei/*.json`

## Best Practices

✅ **DO**
- Review `chaos-sensei.yaml` in version control
- Use separate kubeconfigs for staging vs. production
- Keep team informed when running training
- Monitor systems during and after scenarios
- Archive session reports
- Test rollback procedures in staging first
- Use least-privilege RBAC
- Communicate blast radius to team

❌ **DON'T**
- Run against production without explicit approval
- Disable safety checks
- Target data-bearing resources (PVCs, Secrets)
- Modify code to bypass safety checks
- Delete snapshot files before confirming recovery
- Share kubeconfig widely
- Run unattended without monitoring
- Ignore warnings or error messages

## See Also

- [Security Guidelines](../SECURITY.md)
- [Architecture Guide](architecture.md)
- [Getting Started](getting-started.md)

---

**Remember: Safety is everyone's responsibility.**

If you're unsure whether something is safe, assume it's not and ask for guidance.
