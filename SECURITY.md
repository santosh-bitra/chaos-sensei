# Security Guidelines

This tool performs real infrastructure changes. Safety is paramount.

## Core Principles

1. **Never enable production by default** — Always require explicit, intentional opt-in
2. **Always rollback** — Every fault injection must be fully reversible
3. **Always verify permissions** — Check RBAC and access controls before acting
4. **Always log actions** — Full audit trail for all operations
5. **Always require confirmation** — Never automate dangerous operations
6. **Trust but verify** — Test rollback procedures before running live scenarios

## Usage Guidelines

### ✅ Recommended

- Use staging, development, or test environments
- Start with low-blast-radius scenarios (single pod, single service)
- Verify rollback procedures in safe environments first
- Use kubeconfig with limited permissions (staging only)
- Run during business hours with team availability
- Communicate planned training with your team
- Review `chaos-sensei.yaml` before each session
- Monitor systems during and after experiments

### ❌ Never

- Run against production without explicit, documented approval
- Disable safety checks or rollback requirements
- Target PersistentVolumes, Secrets, or ClusterRoles
- Target production namespaces (prod, production, live)
- Target billing systems or payment processors
- Target customer-facing services without explicit authorization
- Run without understanding what you're about to break
- Delete the snapshot file before confirming rollback

## Safety Configuration

Chaos Sensei enforces strict defaults in `chaos-sensei.yaml`:

```yaml
safety:
  allow_production: false                    # Never enable lightly
  require_confirmation: true                 # Always require user approval
  rollback_required: true                    # Rollback is mandatory
  max_duration_minutes: 20                   # Automatic safety timeout
  
  allowed_namespaces:
    - default
    - apps
    - staging
  
  forbidden_namespaces:
    - kube-system
    - kube-public
    - kube-node-lease
    - cert-manager
    - external-secrets
    - production
    - prod
  
  forbidden_kinds:
    - PersistentVolumeClaim
    - PersistentVolume
    - CustomResourceDefinition
    - ClusterRole
    - ClusterRoleBinding
    - StorageClass
    - Secret
    - Namespace
```

These defaults **should not be relaxed without strong justification**.

## Permissions

Chaos Sensei requires specific Kubernetes permissions. Use this RBAC policy:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: chaos-sensei
  namespace: apps
rules:
# Allow reading most resources
- apiGroups: [""]
  resources:
    - pods
    - services
    - configmaps
    - endpoints
    - events
  verbs: ["get", "list", "watch"]

- apiGroups: ["apps"]
  resources:
    - deployments
    - daemonsets
    - statefulsets
  verbs: ["get", "list", "watch"]

# Allow patching services (for scenarios)
- apiGroups: [""]
  resources:
    - services
  verbs: ["patch", "update"]

# Allow patching deployments (for scenarios)
- apiGroups: ["apps"]
  resources:
    - deployments
  verbs: ["patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: chaos-sensei
  namespace: apps
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: chaos-sensei
subjects:
  - kind: User
    name: your-user@example.com
    apiGroup: rbac.authorization.k8s.io
```

**Principle of least privilege**: Grant only permissions for the scenarios you're actually running.

## Secure Operation Checklist

Before each session:

- [ ] Confirm you're in the correct environment (not production)
- [ ] Review the scenario description and blast radius
- [ ] Confirm `chaos-sensei.yaml` safety settings
- [ ] Verify your kubeconfig context
- [ ] Ensure team awareness (if required by policy)
- [ ] Review the incident report after completion
- [ ] Archive or delete session data if needed

## Incident Response

If something goes wrong:

1. **IMMEDIATELY STOP** — Don't continue the scenario
2. **Run rollback** — `chaos-sensei rollback`
3. **Verify recovery** — Check system health manually
4. **Investigate** — Understand what went wrong
5. **Report** — Document the incident and lessons learned
6. **Update** — Improve safety checks if needed

## Incident Severity

| Level | Criteria | Action |
|---|---|---|
| **Critical** | Production impact, data loss risk, security issue | STOP, rollback, incident response team, review safety |
| **High** | System unavailability, performance impact | Stop, rollback, team notification |
| **Medium** | Degradation, partial functionality loss | Rollback, review, continue with caution |
| **Low** | Expected behavior, cosmetic issues | Continue, document |

## Reporting Security Issues

**Do not open public issues for security vulnerabilities.**

Please report security issues responsibly:

1. Email: security@chaos-sensei.io
2. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Your recommended fix (if any)

We will:
- Acknowledge receipt within 48 hours
- Investigate and validate
- Develop and release a fix
- Credit the reporter (if desired)
- Publish a security advisory

## Audit Logging

All Chaos Sensei operations are logged in `.chaos-sensei/`:

```
.chaos-sensei/
├── session.json           # Active session state
├── report.md              # Incident report
└── audit.log              # (Coming in v0.2) Full audit trail
```

Sessions contain:
- Operator information (when available)
- Timestamp of creation and modifications
- Scenario details
- Injection details
- Verification attempts
- Rollback status

**Retention**: Keep session logs for post-incident analysis.

## FAQ

**Q: Can I use this in production?**

A: Only with explicit, documented approval from security and ops leadership. Production scenarios must be:
- Pre-approved in writing
- Performed with on-call team present
- Monitored by automated alerting
- Limited to very safe operations
- Fully reversible within seconds

**Q: What if rollback fails?**

A: This is a critical scenario:
1. Immediately alert the ops/SRE team
2. Begin manual recovery using the snapshot data
3. Document what happened
4. Review and improve the provider's rollback implementation
5. Never rely on auto-rollback without manual verification first

**Q: Can I delete or modify the snapshot?**

A: **Never** delete the snapshot file before confirming the system is healthy after rollback. The snapshot is your recovery tool.

**Q: How do I prevent accidental production scenarios?**

A: Use these strategies:
1. Set `allow_production: false` in your base config
2. Use separate kubeconfigs for staging vs. production
3. Enforce code review before modifying `chaos-sensei.yaml`
4. Monitor for `allow_production: true` in version control
5. Use different shell prompts or colors for prod kubeconfig

**Q: What's the blast radius of each scenario?**

A: Each scenario is marked with a blast radius:
- `single-pod` — Affects one pod instance
- `single-service` — Affects one service
- `single-deployment` — Affects all pods in one deployment
- `namespace` — Affects entire namespace
- `cluster` — Cluster-wide impact (not in v0.1)

## Version

- Security advisory URL: https://github.com/chaos-sensei/chaos-sensei/security/advisories
- Last Updated: 2025-07-05
- Chaos Sensei Version: v0.1.0

## See Also

- [Safety Model](docs/safety-model.md)
- [Architecture Guide](docs/architecture.md)
- [Kubernetes RBAC Reference](https://kubernetes.io/docs/reference/access-authn-authz/rbac/)

---

**Remember: Great power requires great responsibility.**

If you're unsure whether something is safe, assume it's not and ask for guidance.
