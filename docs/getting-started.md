# Getting Started with Chaos Sensei

A step-by-step guide to setting up and running your first incident training session.

## Prerequisites

- **Python 3.10+** (check with `python3 --version`)
- **A Kubernetes cluster** (local minikube/kind or remote)
- **kubectl configured** and pointing to your target cluster
- **Read SECURITY.md** before starting — seriously!

## Installation

### Option 1: Automated Install

```bash
curl -fsSL https://raw.githubusercontent.com/chaos-sensei/chaos-sensei/main/install.sh | bash
```

This installs to `~/.chaos-sensei/` and adds `~/.local/bin/` to PATH.

### Option 2: pip Install

```bash
pip install chaos-sensei
```

### Option 3: Docker

```bash
docker run -it \
  -v ~/.kube:/root/.kube \
  ghcr.io/chaos-sensei/chaos-sensei:latest \
  scan .
```

### Verify Installation

```bash
chaos-sensei --version
chaos-sensei --help
```

## Quick Start (5 minutes)

### Step 1: Choose Your Target Repo

```bash
cd your-infra-repo
# Should have Kubernetes manifests (YAML files)
ls *.yaml  # or find . -name "*.yaml"
```

### Step 2: Initialize Config

```bash
chaos-sensei init
cat chaos-sensei.yaml
```

This creates a default `chaos-sensei.yaml` with safe defaults.

### Step 3: Scan for Supported Tech

```bash
chaos-sensei scan .
```

Should detect: Kubernetes (if you have YAML manifests)

### Step 4: See Available Scenarios

```bash
chaos-sensei plan --env staging
```

Lists scenarios available for your infrastructure.

### Step 5: Start a Training Session

```bash
chaos-sensei start --scenario hidden
```

This injects a random scenario and hides the root cause.

### Step 6: Debug the Issue

You now have 3 tools:

```bash
# Get the next hint
chaos-sensei hint

# Check if you've fixed it
chaos-sensei check

# Give up and see the answer
chaos-sensei give-up
```

### Step 7: Review What You Learned

```bash
cat .chaos-sensei/report.md
```

## Step-by-Step Examples

### Example 1: Service Selector Mismatch

Real-world scenario: A service isn't routing to pods.

```bash
# Start
chaos-sensei start --scenario hidden

# Try debugging
kubectl get svc
kubectl describe svc checkout
kubectl get pods -L app
kubectl get endpoints

# The service selector doesn't match pod labels!

# Fix it
kubectl patch svc checkout -p '{"spec":{"selector":{"app":"checkout"}}}'

# Verify
chaos-sensei check

# Review
chaos-sensei report
```

### Example 2: Learn at Your Pace

```bash
# Start a specific scenario
chaos-sensei start --scenario k8s-service-selector-mismatch

# Take your time
kubectl get svc
kubectl get pods

# Stuck? Ask for hints
chaos-sensei hint      # Hint 1
chaos-sensei hint      # Hint 2
chaos-sensei hint      # Hint 3

# Ready to see the solution
chaos-sensei give-up
```

## Configuration

Edit `chaos-sensei.yaml` to customize:

### Target Environment

```yaml
environment: staging     # or development, testing, etc.
```

### Visibility

```yaml
mode:
  root_cause_visibility: hidden    # hidden | visible | partial
  hints_before_reveal: 3           # How many hints before showing answer
```

### Safety Settings

```yaml
safety:
  allow_production: false          # NEVER change this lightly
  require_confirmation: true       # Always get user approval
  rollback_required: true          # Always require rollback

  allowed_namespaces:
    - apps
    - staging

  forbidden_namespaces:
    - kube-system
    - production
```

### Provider Configuration

```yaml
providers:
  kubernetes:
    enabled: true
    context: minikube              # Which kubeconfig context
    namespace_default: apps        # Default namespace

  helm:
    enabled: false                 # Enable when ready

  terraform:
    enabled: false                 # Coming in v0.4
```

## Common Workflows

### Training Your Team

```bash
# 1. Choose a scenario
chaos-sensei plan --env staging

# 2. Brief your team on the scenario
# "A service has a networking issue. Debug it."

# 3. Start the session (visible root cause for first time)
chaos-sensei start --scenario k8s-service-selector-mismatch

# 4. Team debugs together
# (Usual debugging process)

# 5. After they fix it, show the automated verification
chaos-sensei check

# 6. Generate report for team learning
chaos-sensei report
```

### On-Call Training

```bash
# 1. Use hidden scenario
chaos-sensei start --scenario hidden

# 2. Trainee debugs with hints
chaos-sensei hint

# 3. Mentor observes approach and provides guidance

# 4. Trainee verifies fix
chaos-sensei check

# 5. Review and discuss findings
chaos-sensei report
```

### Before-Incident Drills

```bash
# 1. Set up in staging
chaos-sensei init

# 2. Practice common failure modes
# Run multiple scenarios to build muscle memory

# 3. Keep reports for future reference
ls .chaos-sensei/

# 4. Update your runbooks based on what you learned
```

## Troubleshooting

### "No providers detected"

**Problem**: `chaos-sensei scan .` shows no results.

**Solution**:
- Make sure you have Kubernetes YAML files
- Check file extensions are `.yaml` or `.yml`
- Verify files contain Kubernetes resource definitions

```bash
# Check for YAML files
find . -name "*.yaml" -o -name "*.yml"

# Verify they have Kubernetes content
grep "kind:" *.yaml
```

### "Namespace is forbidden"

**Problem**: `chaos-sensei start` says namespace is forbidden.

**Solution**: Update `chaos-sensei.yaml` `allowed_namespaces`:

```yaml
safety:
  allowed_namespaces:
    - my-namespace
```

### "kubectl not found or not configured"

**Problem**: Error about kubectl configuration.

**Solution**:
1. Install kubectl
2. Configure kubeconfig: `kubectl config get-contexts`
3. Set correct context: `kubectl config use-context <name>`
4. Test: `kubectl get pods`

### "Session not found"

**Problem**: Running `chaos-sensei check` without active session.

**Solution**: You need an active session. Start one:

```bash
chaos-sensei start
```

The session lasts until you:
- Run `chaos-sensei give-up` (auto-rollback)
- Run `chaos-sensei rollback` (manual)
- Delete `.chaos-sensei/session.json`

### "Rollback failed"

**Problem**: `chaos-sensei rollback` shows an error.

**Solution**: Manual recovery steps:
1. Check `cat .chaos-sensei/session.json`
2. Find the original state in `snapshot` field
3. Manually apply it: `kubectl apply -f <file>`
4. Verify: `kubectl get <resource>`

## Next Steps

1. **Read the docs**:
   - [Architecture Guide](architecture.md) — How it works
   - [Safety Model](safety-model.md) — Safety guidelines
   - [Writing Providers](writing-providers.md) — Extend Chaos Sensei

2. **Try scenarios**:
   - Start with easy scenarios (service selector mismatch)
   - Gradually try harder scenarios
   - Mix with hints and no-hints modes

3. **Customize**:
   - Write custom scenarios for your infrastructure
   - Create providers for your tech stack
   - Integrate with your incident response workflow

4. **Share**:
   - Use Chaos Sensei for team training
   - Contribute scenarios and providers to the community
   - Give feedback on the tool

## Learning Resources

- 📖 [Full Documentation](../docs/)
- 🔒 [Security Guidelines](../SECURITY.md)
- 🏗️ [Architecture](architecture.md)
- 💡 [FAQ](faq.md) (coming soon)
- 🐛 [GitHub Issues](https://github.com/chaos-sensei/chaos-sensei/issues)

---

**Ready to start training? Run:**

```bash
chaos-sensei init
chaos-sensei start --scenario hidden
```

Good luck! 🚀
