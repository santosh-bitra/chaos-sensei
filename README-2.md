# Chaos Sensei Build Guide

This document is a practical build guide for finishing the missing parts of this repository.

It is based on:

- the reference design in `/home/bitra/Workplace/repositories/github-santosh-bitra/project-template-devops/docs/ai/chaos_sensei_design.md`
- the code already present in this repo
- the current package shape under `chaos_sensei/`

The goal is simple:

```text
scan repo -> detect stack -> choose safe scenario -> inject failure
-> observe symptoms -> guide user -> verify fix -> rollback -> write report
```

If you keep that one sentence in your head, every file below becomes easier to understand.

## 1. What is already built in this repo

Right now the repo already has a useful starting point:

- `chaos_sensei/core/engine.py` exists
- `chaos_sensei/core/session.py` exists
- `chaos_sensei/core/config.py` exists
- `chaos_sensei/providers/base.py` exists
- `chaos_sensei/providers/kubernetes/provider.py` exists
- `chaos_sensei/tools/kubectl.py` exists
- `chaos_sensei/cli.py` exists
- one Kubernetes scenario YAML already exists

That means you do not need to "start over".

You mainly need to:

1. split responsibilities more cleanly
2. add missing modules
3. make the current code less hard-coded
4. add scanners, tools, hooks, templates, docs, and tests around the core

## 2. The easiest way to think about the system

Think of Chaos Sensei like a training game master.

- `scanners/` answer: "What kind of project is this?"
- `providers/` answer: "How do I break and restore this technology safely?"
- `core/` answer: "What step are we in right now?"
- `agents/` answer: "How do we explain, hint, judge, and narrate?"
- `tools/` answer: "How do we talk to real systems without messy shell code everywhere?"
- `hooks/` answer: "What extra logic should run before or after important moments?"
- `templates/` answer: "How do we generate standard files and reports?"
- `data/` answer: "What fixed metadata do we want to keep outside Python code?"

## 3. Best build order

Do not build everything randomly. Build in this order:

1. Finish `core/` models and orchestration boundaries
2. Finish `tools/` wrappers
3. Finish `scanners/`
4. Improve `providers/base.py`
5. Finish `providers/kubernetes/provider.py`
6. Add scenario YAMLs
7. Add `policy.py`, `rollback.py`, `report.py`
8. Add hooks
9. Add agent folders and `SKILL.md` files
10. Add templates and data files
11. Add examples
12. Add tests
13. Expand docs

Why this order matters:

- core defines the language of the app
- tools make external calls consistent
- scanners tell you which provider should even wake up
- providers depend on tools and core contracts
- agents are easier once the workflow is stable

## 4. Core folder: what each file should do

The `core/` folder is the brain stem of the app. It should not know Kubernetes details, Terraform syntax, or Helm flags. It should only know process, state, safety, and reporting.

### `core/engine.py`

Plain-English job:

"Run the whole experiment from start to finish."

What it should do:

- load config
- load provider registry
- run repo scan
- ask planner for possible scenarios
- ask policy if a scenario is allowed
- create session state
- ask provider to snapshot and inject
- ask observer/judge/report pieces later
- call rollback when needed

What is already good in your current file:

- `ChaosSenseiEngine` already exists
- `scan()`, `plan()`, `start()`, `hint()`, `check()`, `rollback()`, `report()` already exist

What should improve:

- move planning logic into `planner.py`
- move safety logic into `policy.py`
- move rollback logic into `rollback.py`
- move report generation into `report.py`
- stop hard-coding provider init inside `_init_providers()`
- stop assuming "first detected provider wins"

The clean design:

```python
class ChaosSenseiEngine:
    def __init__(self, repo_path: Path, environment: str = "staging"):
        self.repo_path = repo_path
        self.environment = environment
        self.config = Config.from_yaml(...)
        self.planner = ScenarioPlanner(...)
        self.policy = PolicyEngine(...)
        self.rollback_manager = RollbackManager(...)
        self.report_builder = ReportBuilder(...)
```

Methods to keep:

- `init_config()`
- `scan()`
- `plan()`
- `start()`
- `hint()`
- `check()`
- `rollback()`
- `give_up()`
- `report()`

Layman mental model:

- `scan()` = look around the room
- `plan()` = decide which drill is possible
- `start()` = begin the drill
- `hint()` = nudge the student
- `check()` = see whether the student fixed it
- `rollback()` = clean up the room
- `report()` = write what happened

### `core/planner.py`

Plain-English job:

"Given a repo and detected technologies, decide which scenarios can be offered."

Why this file should exist:

Right now `engine.plan()` does too much by itself.

`planner.py` should:

- take scanner results
- ask matching providers for inventory
- ask providers for possible scenarios
- filter or rank scenarios
- return a normalized list

Suggested class:

```python
class ScenarioPlanner:
    def __init__(self, providers, policy_engine):
        self.providers = providers
        self.policy_engine = policy_engine

    def detect_providers(self, repo_path: Path) -> list[Provider]:
        ...

    def build_plan(self, repo_path: Path, environment: str) -> dict:
        ...

    def choose_scenario(self, scenarios: list[dict], requested_id: str | None) -> dict:
        ...
```

What goes inside the returned plan:

- detected providers
- discovered inventory summary
- candidate scenarios
- blocked scenarios with reasons
- recommended scenario

Layman explanation:

This file is the "trip planner". It decides which routes are possible before the journey begins.

### `core/session.py`

Plain-English job:

"Store what is happening in the current training session."

Your current file is a good start. Keep it, but enrich it.

Add fields like:

- `status`: planned, injected, fixed, rolled_back, failed, expired
- `events`: list of timeline events
- `observations`: latest observed symptoms
- `selected_provider`
- `selected_scenario_id`
- `report_path`
- `rollback_result`

Recommended models:

```python
class SessionMetadata(BaseModel):
    session_id: str
    repo_path: str
    environment: str
    provider: str
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None

class SessionEvent(BaseModel):
    type: str
    timestamp: str
    message: str
    data: dict = Field(default_factory=dict)

class Session(BaseModel):
    metadata: SessionMetadata
    status: str = "created"
    scenario: dict = Field(default_factory=dict)
    snapshot: dict = Field(default_factory=dict)
    events: list[SessionEvent] = Field(default_factory=list)
    observations: list[dict] = Field(default_factory=list)
    checks: list[dict] = Field(default_factory=list)
    hint_count: int = 0
    rolled_back: bool = False
```

Methods to add:

- `add_event()`
- `record_observation()`
- `mark_injected()`
- `mark_fixed()`
- `mark_rolled_back()`
- `mark_failed()`

Layman explanation:

This file is the notebook of the experiment.

### `core/events.py`

Plain-English job:

"Define the important things that can happen during a session."

Do not make this file complicated. It can just centralize event names and event models.

Good content:

```python
from enum import Enum

class EventType(str, Enum):
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    PLAN_CREATED = "plan_created"
    PREFLIGHT_PASSED = "preflight_passed"
    SNAPSHOT_CREATED = "snapshot_created"
    INJECTION_STARTED = "injection_started"
    INJECTION_COMPLETED = "injection_completed"
    HINT_REQUESTED = "hint_requested"
    CHECK_PERFORMED = "check_performed"
    FIX_VERIFIED = "fix_verified"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    REPORT_GENERATED = "report_generated"
```

Why this helps:

- avoids random string typos
- gives a stable audit timeline
- helps reports and tests

### `core/state.py`

Plain-English job:

"Define the allowed states of the session and how it can move from one state to another."

Think of this as a traffic-light file.

Suggested enum:

```python
class SessionStatus(str, Enum):
    CREATED = "created"
    SCANNED = "scanned"
    PLANNED = "planned"
    PREFLIGHT_PASSED = "preflight_passed"
    SNAPSHOTTED = "snapshotted"
    INJECTED = "injected"
    UNDER_INVESTIGATION = "under_investigation"
    FIXED = "fixed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    EXPIRED = "expired"
```

Add a helper like:

```python
ALLOWED_TRANSITIONS = {
    "created": {"scanned", "planned"},
    "planned": {"preflight_passed", "failed"},
    "preflight_passed": {"snapshotted", "failed"},
    "snapshotted": {"injected", "failed"},
    "injected": {"under_investigation", "rolled_back", "fixed"},
    "under_investigation": {"fixed", "rolled_back", "expired"},
}
```

Layman explanation:

This file stops the app from doing silly things like generating a report before an experiment even started.

### `core/policy.py`

Plain-English job:

"Decide whether a scenario is safe enough to run."

This file should use your `Config.safety` data and scenario metadata.

It should answer questions like:

- is this namespace forbidden?
- is this resource kind forbidden?
- is the blast radius too large?
- is production blocked?
- does the scenario violate any keyword rules?
- is manual confirmation needed?

Suggested class:

```python
class PolicyEngine:
    def __init__(self, config: Config):
        self.config = config

    def evaluate(self, scenario: dict, inventory: dict | None = None) -> dict:
        ...
```

Return structure:

```python
{
  "allowed": True,
  "severity": "low",
  "requires_confirmation": True,
  "reasons": [],
  "blocked_by": [],
}
```

Keep provider preflight and policy separate:

- `policy.py` = general safety rules
- `provider.preflight()` = technology-specific safety checks

Layman explanation:

This file is the safety officer.

### `core/rollback.py`

Plain-English job:

"Restore the original system safely and consistently."

Why this deserves its own file:

Rollback is important enough to not be hidden inside `engine.py`.

Suggested class:

```python
class RollbackManager:
    def rollback(self, provider: Provider, session: Session) -> dict:
        ...

    def verify_rollback(self, provider: Provider, session: Session) -> dict:
        ...
```

Responsibilities:

- call provider rollback
- update session state
- store rollback result
- optionally verify health after rollback
- write timeline events

Important rule:

Rollback should be idempotent if possible.

That means:

If the same rollback runs twice, it should not destroy more things. It should either do nothing safely or say "already restored".

### `core/report.py`

Plain-English job:

"Convert session data into a useful human-readable learning report."

Right now your report is built by a big string in `engine.py`. Move that here.

Suggested class:

```python
class ReportBuilder:
    def build_markdown(self, session: Session) -> str:
        ...

    def build_json(self, session: Session) -> dict:
        ...

    def save(self, content: str, path: Path) -> None:
        ...
```

Sections to include:

- session info
- scenario summary
- symptoms seen
- hints requested
- user verification attempts
- root cause
- ideal debugging path
- rollback result
- lessons learned
- next drills to practice

Layman explanation:

This file is the teacher's final feedback sheet.

## 5. Agents folder: what each agent should do

Treat these agents as specialized helpers. They should not own the experiment lifecycle. The engine owns the lifecycle. Agents help with reasoning and explanation.

Each agent folder should contain:

- `agent.py`
- `SKILL.md`

`agent.py` holds the Python interface.

`SKILL.md` explains the agent's role, boundaries, inputs, outputs, tone, and safety rules.

### Common `agent.py` pattern

You can keep all agent classes lightweight:

```python
class BaseAgent:
    name = "base-agent"

    def run(self, context: dict) -> dict:
        raise NotImplementedError
```

If you want LLM-backed agents later, wrap the LLM call behind `tools/llm.py`.

### `agents/repo_cartographer/agent.py`

Plain-English job:

"Understand the repository map."

Responsibilities:

- read scanner outputs
- summarize project technologies
- describe folder patterns
- point to likely app/service entry points
- identify which provider families match the repo

Expected input:

- repo scan results
- file summaries
- detector matches

Expected output:

```python
{
  "stack_summary": "...",
  "detected_technologies": [...],
  "service_candidates": [...],
  "risk_notes": [...],
}
```

`SKILL.md` should explain:

- do not invent technologies not found in scan output
- prefer evidence from files
- summarize in plain English

### `agents/scenario_designer/agent.py`

Plain-English job:

"Turn inventory into a teachable failure scenario."

Responsibilities:

- choose target resource candidates
- choose a safe fault style
- enrich scenario with hints, symptoms, and success criteria
- rank scenarios by learning value

Output should look like scenario YAML fields:

- `id`
- `title`
- `description`
- `target`
- `fault`
- `visible_symptoms`
- `hints`
- `success_criteria`
- `rollback`

`SKILL.md` should say:

- prefer reversible faults
- avoid data-loss faults
- beginner scenarios first

### `agents/safety_governor/agent.py`

Plain-English job:

"Explain safety decisions clearly."

Responsibilities:

- summarize why a scenario is allowed or blocked
- convert raw policy findings into human language
- recommend smaller blast radius alternatives

Useful output:

```python
{
  "allowed": False,
  "summary": "Blocked because namespace is production",
  "recommendations": ["Try apps namespace", "Use staging context"],
}
```

### `agents/observer/agent.py`

Plain-English job:

"Collect symptoms after the fault is injected."

Responsibilities:

- gather provider observations
- summarize pods, logs, events, metrics
- convert noisy raw data into a concise symptom list

This agent is especially useful when `provider.observe()` returns too much raw detail.

### `agents/judge/agent.py`

Plain-English job:

"Decide whether the user really fixed the problem."

Responsibilities:

- inspect `verify_fix()` output
- compare success criteria with current state
- decide pass/fail/partial
- explain what is still missing

Useful return shape:

```python
{
  "fixed": False,
  "confidence": "high",
  "explanation": "...",
  "missing_checks": [...],
}
```

### `agents/hint_master/agent.py`

Plain-English job:

"Give progressive hints without spoiling too early."

Hint ladder:

1. broad direction
2. narrower subsystem clue
3. concrete command clue
4. near-solution clue

If scenario YAML already contains hints, this agent can:

- reformat them nicely
- adapt them to user progress
- avoid repeating the same clue

### `agents/postmortem_writer/agent.py`

Plain-English job:

"Write the learning summary after the exercise."

Responsibilities:

- combine session timeline, scenario metadata, hints used, and checks
- explain root cause simply
- explain ideal troubleshooting flow
- extract lessons learned

### Common `SKILL.md` template for all agents

Each `SKILL.md` can follow this shape:

```md
# Agent Name

## Purpose
One clear sentence.

## Inputs
- item 1
- item 2

## Outputs
- item 1
- item 2

## Rules
- never invent facts
- prefer repo evidence
- keep language beginner-friendly
- respect safety policy

## Example
Short example input/output
```

## 6. Providers folder: what to build

Providers are translators between the generic engine and a real technology.

### `providers/base.py`

Your current base class is already useful. Improve it a bit.

Add optional helper methods like:

- `load_scenarios()`
- `supports(scenario_id: str) -> bool`
- `health_check()`
- `verify_rollback()`

Also add standard return shapes in docstrings so every provider behaves similarly.

Example normalized return contracts:

```python
{
  "allowed": True,
  "reason": "..."
}
```

```python
{
  "injected": True,
  "details": "...",
  "changes": {...}
}
```

### `providers/kubernetes/provider.py`

This is your first real provider and should become the reference implementation for future providers.

What is already there:

- detection
- discovery
- basic scenarios list
- preflight
- snapshot
- inject dispatch
- observe
- verify
- rollback

What it still needs:

- scenario loading from YAML files instead of hard-coded Python dicts
- better target selection from discovered inventory
- safer preflight checks using config
- stronger verification logic
- support for all scenario YAMLs

A better structure:

```python
class KubernetesProvider(Provider):
    def detect(self, repo_path: str) -> bool: ...
    def discover(self, repo_path: str) -> dict: ...
    def list_scenarios(self, inventory: dict) -> list[dict]: ...
    def preflight(self, scenario: dict) -> dict: ...
    def snapshot(self, scenario: dict) -> dict: ...
    def inject(self, scenario: dict, snapshot: dict) -> dict: ...
    def observe(self, scenario: dict) -> dict: ...
    def verify_fix(self, scenario: dict) -> dict: ...
    def rollback(self, scenario: dict, snapshot: dict) -> dict: ...
```

Important internal private helpers to add:

- `_load_scenario_files()`
- `_resolve_target_from_inventory()`
- `_inject_service_selector_mismatch()`
- `_inject_pod_crash()`
- `_inject_configmap_missing_key()`
- `_inject_readiness_probe_failure()`
- `_verify_service_selector()`
- `_verify_deployment_rollout()`

Layman explanation:

If the engine says "cause a safe training failure", the Kubernetes provider decides how that looks in actual `kubectl` terms.

### `providers/kubernetes/scenarios/*.yaml`

Each YAML file is the lesson plan for one drill.

You already have `service_selector_mismatch.yaml`.

Create the others with the same shape:

- `pod_crash.yaml`
- `configmap_missing_key.yaml`
- `readiness_probe_failure.yaml`

Every scenario file should include:

- identity
- title
- description
- target
- fault
- visible symptoms
- root cause
- hints
- ideal path
- success criteria
- rollback
- learning objectives

### `providers/kubernetes/SKILL.md`

This file should explain:

- this provider only works on Kubernetes-like repos and clusters
- it should use safe, reversible mutations
- it must avoid forbidden namespaces and resource kinds
- it should prefer service, deployment, configmap, and probe-level failures before destructive ones

## 7. Scanners folder: what each scanner should do

Scanners answer one question:

"What technologies are present in this repo?"

Keep scanners dumb and evidence-based. They should inspect files, not make huge assumptions.

### `scanners/repo_scanner.py`

This is the top-level orchestrator for scanning.

Responsibilities:

- walk the repo
- gather file inventory
- call each specialized scanner
- combine results

Output:

```python
{
  "repo_path": "...",
  "files_scanned": 123,
  "technologies": {
    "kubernetes": {...},
    "helm": {...},
    "terraform": {...},
  },
  "matched_scanners": [...],
}
```

### `scanners/k8s_scanner.py`

Detect:

- `kind: Deployment`
- `kind: Service`
- `apiVersion: apps/v1`
- namespace usage
- labels/selectors

Also collect:

- probable service names
- probable namespaces
- manifest file paths

### `scanners/helm_scanner.py`

Detect:

- `Chart.yaml`
- `values.yaml`
- `templates/`

Collect:

- chart names
- release-style values structure
- whether Kubernetes scanner should also run

### `scanners/terraform_scanner.py`

Detect:

- `*.tf`
- `.terraform.lock.hcl`
- providers like aws, azurerm, google, kubernetes

Collect:

- module folders
- resource types
- environment folder patterns

### `scanners/terragrunt_scanner.py`

Detect:

- `terragrunt.hcl`

Collect:

- stack layout
- include blocks
- dependency blocks

### `scanners/docker_scanner.py`

Detect:

- `Dockerfile`
- `docker-compose.yml`
- `compose.yaml`

Collect:

- service names
- ports
- health checks

### `scanners/ci_scanner.py`

Detect:

- `.github/workflows/`
- GitLab CI
- Jenkinsfile
- ArgoCD / Flux patterns if you want later

Collect:

- pipeline file paths
- deploy stage hints
- test/build/release workflow presence

Best implementation pattern for all scanners:

```python
class KubernetesScanner:
    patterns = [...]

    def scan(self, repo_path: Path) -> dict:
        ...
```

## 8. Tools folder: what each tool should do

Tools are wrappers. Their job is to stop command logic from leaking all over the codebase.

Rule:

Never scatter raw `subprocess.run()` across many files.

### `tools/shell.py`

Base helper for safe subprocess execution.

It should:

- run commands
- capture stdout/stderr
- support timeouts
- return structured results
- optionally redact secrets from logs

Suggested return shape:

```python
{
  "command": [...],
  "returncode": 0,
  "stdout": "...",
  "stderr": "...",
}
```

### `tools/git.py`

Use for repo facts, not for mutations at first.

Safe methods:

- `current_branch()`
- `status_short()`
- `tracked_files()`
- `last_commit()`

Why:

Useful for reports and repo context.

### `tools/kubectl.py`

You already have a solid start.

Possible additions:

- `get_deployments()`
- `get_endpoints()`
- `describe()`
- `logs()`
- `delete_pod()`
- `wait()`

### `tools/helm.py`

Methods:

- `list_releases()`
- `get_values()`
- `template()`
- `status()`

Start read-only first.

### `tools/terraform.py`

Methods:

- `version()`
- `fmt_check()`
- `validate()`
- `plan_json()`

Again, start read-only.

### `tools/terragrunt.py`

Methods:

- `version()`
- `validate()`
- `run_all_plan()`

### `tools/prometheus.py`

This can remain a lightweight HTTP client wrapper.

Methods:

- `query()`
- `query_range()`
- `health()`

Use it later for richer observation and verification.

### `tools/llm.py`

This wrapper should isolate all LLM calls from the rest of the app.

Methods:

- `complete(prompt: str, context: dict | None = None) -> str`
- `json(prompt: str, schema_name: str, context: dict | None = None) -> dict`

Why this matters:

If you change model/provider later, only one file changes.

## 9. Hooks folder: when to use each hook

Hooks are optional extension points. They let you inject extra behavior without bloating `engine.py`.

Make each hook simple:

```python
def run(context: dict) -> dict:
    return context
```

### `hooks/pre_scan.py`

Use for:

- validating repo path
- checking required tools
- initializing audit context

### `hooks/pre_experiment.py`

Use for:

- final safety confirmation
- environment checks
- lock creation to avoid parallel experiments

### `hooks/post_injection.py`

Use for:

- recording first symptom snapshot
- emitting audit events
- starting timers

### `hooks/on_user_attempt.py`

Use for:

- tracking manual actions
- storing investigation milestones

### `hooks/on_hint_request.py`

Use for:

- incrementing counters
- recording hint timestamps
- adapting future hint difficulty

### `hooks/on_verify.py`

Use for:

- storing verification result
- recording whether fix passed or failed

### `hooks/on_give_up.py`

Use for:

- mark session as surrendered
- trigger reveal flow

### `hooks/on_rollback.py`

Use for:

- store rollback details
- trigger post-rollback health check

### `hooks/post_report.py`

Use for:

- saving extra artifacts
- sending report to a file or integration later

## 10. Templates folder: what to put in each template

### `templates/chaos-sensei.yaml`

This should be the default config template written by `init`.

Include:

- project name
- environment
- mode
- safety
- provider enable/disable flags

### `templates/safety-policy.yaml`

This can be a more explicit version of the safety section, useful for teams that want standalone policy review.

### `templates/report.md.j2`

Use Jinja to render:

- session metadata
- scenario info
- observations
- checks
- hints
- root cause
- lessons

### `templates/scenario.yaml.j2`

Use this as a starter template for new scenarios so all scenario files stay consistent.

## 11. Data folder: what belongs there

### `data/scenario_taxonomy.yaml`

Put reusable classifications here:

- categories
- difficulty levels
- blast radius definitions
- learning objective tags

Example:

```yaml
categories:
  - networking
  - configuration
  - availability
  - observability

difficulty:
  - beginner
  - intermediate
  - advanced
```

### `data/provider_registry.yaml`

This should map provider names to import paths and metadata.

Example:

```yaml
providers:
  - name: kubernetes
    module: chaos_sensei.providers.kubernetes.provider
    class: KubernetesProvider
    enabled_by_default: true
  - name: helm
    module: chaos_sensei.providers.helm.provider
    class: HelmProvider
    enabled_by_default: false
```

Why this is better than hard-coding:

The engine can load providers dynamically later.

## 12. Examples folder: what each example should contain

These examples are not just demos. They are teaching fixtures.

### `examples/k8s-helm-demo/`

Include:

- a simple app deployment
- service
- configmap
- Helm chart overlay if possible
- a README explaining how to practice

### `examples/terraform-aws-demo/`

Include:

- safe mock Terraform modules
- sample variables
- intentionally imperfect but non-destructive infrastructure definitions

### `examples/docker-compose-demo/`

Include:

- two or three services
- one broken health-check or dependency scenario

### `examples/mixed-stack-demo/`

Include:

- Kubernetes manifests
- Helm chart
- Terraform folder
- CI workflow

This example is useful for showing off the repo-agnostic design.

## 13. Docs folder: what each document should explain

### `docs/architecture.md`

Already exists. Expand it with:

- scanners -> planner -> provider -> hooks -> report flow
- session state machine
- provider registry design

### `docs/getting-started.md`

Already exists. Expand it with:

- example repo walkthrough
- sample output snippets
- troubleshooting section

### `docs/safety-model.md`

Already exists. Expand it with:

- policy engine behavior
- rollback guarantees
- risk grading

### `docs/writing-providers.md`

Explain:

- provider contract
- required methods
- normalized return structures
- how to write safe `preflight()`

### `docs/writing-scenarios.md`

Explain:

- scenario YAML schema
- good hint design
- success criteria design
- rollback design

### `docs/report-format.md`

Explain:

- Markdown report sections
- JSON report structure
- what is mandatory vs optional

## 14. Tests folder: what to test first

Build tests in this order:

1. config validation tests
2. session load/save tests
3. policy engine tests
4. scanner detection tests
5. provider preflight tests
6. provider rollback tests
7. report generation tests
8. CLI smoke tests

### `tests/unit/`

Good targets:

- `test_state.py`
- `test_policy.py`
- `test_session.py`
- `test_repo_scanner.py`
- `test_k8s_provider.py`
- `test_report.py`

### `tests/integration/`

Good targets:

- start -> hint -> check -> rollback flow
- fake kubectl responses
- scenario file loading

### `tests/fixtures/`

Store:

- fake repo structures
- fake YAML manifests
- fake Terraform files
- fake kubectl JSON outputs
- fake session JSON files

## 15. Recommended file-by-file MVP content

If you want the fastest path, here is the minimum version to write into each missing file.

### Core MVP

- `planner.py`: detect providers, gather scenarios, choose one
- `events.py`: enum of event names
- `state.py`: enum of session statuses and allowed transitions
- `policy.py`: evaluate namespace/kind/blast-radius restrictions
- `rollback.py`: one class that calls provider rollback and updates session
- `report.py`: build and save markdown report

### Agents MVP

- every `agent.py`: one class with `run(context)` returning a dict
- every `SKILL.md`: purpose, inputs, outputs, rules, example

### Kubernetes provider MVP

- load scenarios from YAML
- map inventory to target candidates
- inject four scenario types
- verify success criteria
- rollback using stored snapshot

### Scanners MVP

- each scanner returns `detected`, `evidence`, and `summary`

### Tools MVP

- each wrapper exposes read-only operations first
- add mutation methods only where needed for scenario injection

### Hooks MVP

- each hook is a simple function that reads and returns context

### Templates MVP

- default config
- default report template
- default scenario template

### Data MVP

- one taxonomy file
- one provider registry file

## 16. Suggested normalized Python shapes

If you keep return values consistent, your whole codebase becomes easier.

### Scan result

```python
{
  "detected": True,
  "technology": "kubernetes",
  "evidence": ["manifests/app.yaml", "manifests/svc.yaml"],
  "summary": "Kubernetes manifests detected"
}
```

### Provider preflight result

```python
{
  "allowed": True,
  "reason": "Namespace apps is allowed",
  "warnings": [],
  "requires_confirmation": True
}
```

### Injection result

```python
{
  "injected": True,
  "fault_type": "service_selector_mismatch",
  "target": {"kind": "service", "name": "checkout", "namespace": "apps"},
  "details": "Service selector patched"
}
```

### Verification result

```python
{
  "fixed": False,
  "details": "Service endpoints still empty",
  "observed_state": {...}
}
```

### Rollback result

```python
{
  "rolled_back": True,
  "details": "Original Service manifest restored",
  "verified": True
}
```

## 17. Biggest design mistake to avoid

Do not let `engine.py` become a giant file that:

- scans repos
- parses YAML
- applies safety rules
- builds reports
- runs kubectl
- writes hints
- verifies fixes

That becomes hard to test and hard to trust.

Keep this boundary:

- engine orchestrates
- scanners inspect
- policy decides
- providers act
- tools execute
- agents explain
- report writes

## 18. Best next coding steps for this exact repo

Based on the files that already exist here, this is the smartest next sequence:

1. create `chaos_sensei/core/events.py`
2. create `chaos_sensei/core/state.py`
3. create `chaos_sensei/core/policy.py`
4. create `chaos_sensei/core/planner.py`
5. create `chaos_sensei/core/rollback.py`
6. create `chaos_sensei/core/report.py`
7. refactor `engine.py` to call those classes
8. extend `session.py` with status and events
9. add `scanners/repo_scanner.py` and `scanners/k8s_scanner.py`
10. refactor Kubernetes provider to load YAML scenarios instead of hard-coded lists
11. add the remaining Kubernetes scenario YAMLs
12. add agent folders with minimal `agent.py` + `SKILL.md`
13. add tests for session, policy, and provider loading

## 19. If you want to keep things simple

You do not need full AI behavior on day one.

A very practical version is:

- scanners are regular Python code
- providers are regular Python code
- hints come from scenario YAML
- reports come from templates
- agents are thin wrappers that mostly transform data
- `tools/llm.py` stays optional until later

That keeps the project reliable while still matching the reference design.

## 20. Final advice

When writing each file, answer these four questions:

1. What single job does this file own?
2. What data comes in?
3. What data goes out?
4. What file should own this instead if it starts growing too much?

If you stay disciplined about those four questions, the project will stay clean and extensible.

## 21. Short starter checklist

Use this as your working checklist:

- [ ] add `events.py`
- [ ] add `state.py`
- [ ] add `policy.py`
- [ ] add `planner.py`
- [ ] add `rollback.py`
- [ ] add `report.py`
- [ ] extend `session.py`
- [ ] refactor `engine.py`
- [ ] add scanners
- [ ] improve provider loading
- [ ] add missing Kubernetes scenarios
- [ ] add hooks
- [ ] add agents and `SKILL.md`
- [ ] add templates
- [ ] add data files
- [ ] add examples
- [ ] add docs
- [ ] add tests

If you want, the next best step after this document is for me to help you generate the actual starter code for `core/` first, one file at a time, in the same style as your current repo.
