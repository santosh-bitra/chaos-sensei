"""Main Chaos Sensei engine — thin orchestrator over core/ and providers/."""

import json
import logging
import uuid
from pathlib import Path
from typing import List

from chaos_sensei.core.config import Config
from chaos_sensei.core.exceptions import (
    ProviderNotDetectedError,
    SafetyPolicyError,
    SessionNotFoundError,
)
from chaos_sensei.core.planner import ScenarioPlanner
from chaos_sensei.core.policy import PolicyEngine
from chaos_sensei.core.report import ReportBuilder
from chaos_sensei.core.rollback import RollbackManager
from chaos_sensei.core.session import Session
from chaos_sensei.providers.base import Provider
from chaos_sensei.providers.kubernetes.provider import KubernetesProvider

logger = logging.getLogger(__name__)


class ChaosSenseiEngine:
    """Orchestrates a training session: delegates planning, safety, rollback,
    and reporting to their own modules instead of implementing them inline."""

    SESSION_DIR = Path(".chaos-sensei")
    SESSION_FILE = SESSION_DIR / "session.json"
    CONFIG_FILE = Path("chaos-sensei.yaml")

    def __init__(self, repo_path: Path, environment: str = "staging") -> None:
        self.repo_path = repo_path.resolve()
        self.environment = environment

        self.config = Config.from_yaml(self.repo_path / self.CONFIG_FILE)
        self.config.environment = environment

        self.providers = self._init_providers()
        self.policy = PolicyEngine(self.config)
        self.planner = ScenarioPlanner(self.providers, self.policy)
        self.rollback_manager = RollbackManager()
        self.report_builder = ReportBuilder()

        logger.info(f"Engine initialized for {self.repo_path} in {environment}")

    def _init_providers(self) -> List[Provider]:
        """Initialize available providers based on config."""
        providers = []

        if self.config.providers.kubernetes.enabled:
            try:
                provider = KubernetesProvider(
                    context=self.config.providers.kubernetes.config.get("context")
                )
                providers.append(provider)
                logger.debug("Kubernetes provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Kubernetes provider: {e}")

        return providers

    @classmethod
    def from_current_session(cls) -> "ChaosSenseiEngine":
        """Load engine from current session."""
        if not cls.SESSION_FILE.exists():
            raise SessionNotFoundError("No active chaos-sensei session found")

        try:
            session = Session.from_file(cls.SESSION_FILE)
            engine = cls(
                repo_path=Path(session.metadata.repo_path),
                environment=session.metadata.environment,
            )
            engine.session = session
            return engine
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            raise SessionNotFoundError(f"Failed to load session: {e}")

    def init_config(self) -> str:
        """Create default configuration file."""
        config_path = self.repo_path / self.CONFIG_FILE

        if config_path.exists():
            logger.warning(f"{self.CONFIG_FILE} already exists")
            return f"{self.CONFIG_FILE} already exists"

        self.config.to_yaml(config_path)
        return f"Created {self.CONFIG_FILE}"

    def scan(self) -> str:
        """Scan repository for supported technologies."""
        detected = self.planner.detect_providers(self.repo_path)

        if not detected:
            logger.warning("No supported technologies detected")

        return json.dumps(
            {
                "repo": str(self.repo_path),
                "environment": self.environment,
                "detected_providers": [
                    {"name": p.name, "technology": p.technology} for p in detected
                ],
            },
            indent=2,
        )

    def plan(self) -> str:
        """Plan available scenarios."""
        plan = self.planner.build_plan(self.repo_path, self.environment)
        return json.dumps(plan, indent=2)

    def start(self, scenario_id: str = "hidden") -> str:
        """Start an incident training session."""
        provider = self.planner.first_matching_provider(self.repo_path)

        inventory = provider.discover(str(self.repo_path))
        scenarios = provider.list_scenarios(inventory)
        scenario = self.planner.choose_scenario(scenarios, scenario_id)

        policy_result = self.policy.evaluate(scenario, inventory, self.environment)
        if not policy_result["allowed"]:
            raise SafetyPolicyError(
                f"Safety policy violation: {'; '.join(policy_result['reasons']) or 'blocked'}"
            )

        preflight = provider.preflight(scenario)
        if not preflight.get("allowed", False):
            raise SafetyPolicyError(
                f"Safety policy violation: {preflight.get('reason', 'Unknown reason')}"
            )

        snapshot = provider.snapshot(scenario)

        session_id = str(uuid.uuid4())[:8]
        self.session = Session.create(
            session_id=session_id,
            repo_path=self.repo_path,
            environment=self.environment,
            provider=provider.name,
            scenario=scenario,
            snapshot=snapshot,
        )

        injection = provider.inject(scenario, snapshot)
        self.session.start()
        self.session.save(self.SESSION_FILE)

        logger.info(f"Session {session_id} started with scenario {scenario.get('id')}")

        return json.dumps(
            {
                "status": "incident_started",
                "session_id": session_id,
                "message": "A training incident has been injected. Root cause is hidden.",
                "scenario": {
                    "id": scenario.get("id"),
                    "title": scenario.get("title"),
                    "difficulty": scenario.get("difficulty"),
                },
                "visible_symptoms": scenario.get("visible_symptoms", []),
                "injection": {
                    "done": injection.get("injected", False),
                    "details": injection.get("details", ""),
                },
            },
            indent=2,
        )

    def hint(self) -> str:
        """Get the next hint."""
        self.session = Session.from_file(self.SESSION_FILE)
        hints = self.session.scenario.get("hints", [])

        if self.session.hint_count < len(hints):
            hint = hints[self.session.hint_count]
        else:
            hint = "No more hints available. Use `chaos-sensei give-up` for the full explanation."

        self.session.increment_hint()
        self.session.save(self.SESSION_FILE)

        return hint

    def check(self) -> str:
        """Check if incident is fixed."""
        self.session = Session.from_file(self.SESSION_FILE)
        provider = self._provider_by_name(self.session.metadata.provider)

        result = provider.verify_fix(self.session.scenario)
        self.session.record_check(result)
        if result.get("fixed"):
            self.session.mark_fixed(result.get("details", ""))
        self.session.save(self.SESSION_FILE)

        if result.get("fixed"):
            return "✓ Fixed! Great work. Run `chaos-sensei report` to generate the learning report."

        return "✗ Not fixed yet. Try `chaos-sensei hint` or continue investigating."

    def rollback(self) -> str:
        """Rollback the incident."""
        self.session = Session.from_file(self.SESSION_FILE)
        provider = self._provider_by_name(self.session.metadata.provider)

        result = self.rollback_manager.rollback(provider, self.session)
        self.session.save(self.SESSION_FILE)

        return json.dumps(result, indent=2)

    def give_up(self) -> str:
        """Give up and reveal the answer."""
        self.rollback()
        return self.report()

    def report(self) -> str:
        """Generate incident report."""
        self.session = Session.from_file(self.SESSION_FILE)
        content = self.report_builder.build_markdown(self.session)
        self.report_builder.save(content, self.SESSION_DIR / "report.md")
        return content

    def _provider_by_name(self, name: str) -> Provider:
        """Find provider by name."""
        for provider in self.providers:
            if provider.name == name:
                return provider
        raise ProviderNotDetectedError(f"Provider not found: {name}")
