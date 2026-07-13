"""Main Chaos Sensei engine."""

import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from chaos_sensei.core.config import Config
from chaos_sensei.core.exceptions import (
    ProviderNotDetectedError,
    SafetyPolicyError,
    ScenarioNotFoundError,
    SessionNotFoundError,
)
from chaos_sensei.core.session import Session
from chaos_sensei.providers.base import Provider
from chaos_sensei.providers.kubernetes.provider import KubernetesProvider

logger = logging.getLogger(__name__)


class ChaosSenseiEngine:
    """Main orchestration engine for Chaos Sensei."""

    SESSION_DIR = Path(".chaos-sensei")
    SESSION_FILE = SESSION_DIR / "session.json"
    CONFIG_FILE = Path("chaos-sensei.yaml")

    def __init__(self, repo_path: Path, environment: str = "staging") -> None:
        """
        Initialize the engine.

        Args:
            repo_path: Path to target repository
            environment: Target environment (staging, production, etc.)
        """
        self.repo_path = repo_path.resolve()
        self.environment = environment

        # Load or create config
        self.config = Config.from_yaml(self.repo_path / self.CONFIG_FILE)
        self.config.environment = environment

        # Initialize providers
        self.providers = self._init_providers()

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
        """
        Load engine from current session.

        Returns:
            Engine instance with active session loaded

        Raises:
            SessionNotFoundError: If no active session exists
        """
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
        """
        Create default configuration file.

        Returns:
            Status message
        """
        config_path = self.repo_path / self.CONFIG_FILE

        if config_path.exists():
            logger.warning(f"{self.CONFIG_FILE} already exists")
            return f"{self.CONFIG_FILE} already exists"

        try:
            self.config.to_yaml(config_path)
            return f"Created {self.CONFIG_FILE}"
        except Exception as e:
            logger.error(f"Failed to create config: {e}")
            raise

    def scan(self) -> str:
        """
        Scan repository for supported technologies.

        Returns:
            JSON string with detection results
        """
        detected = []

        for provider in self.providers:
            try:
                if provider.detect(str(self.repo_path)):
                    detected.append({
                        "name": provider.name,
                        "technology": provider.technology,
                    })
                    logger.info(f"Detected: {provider.name}")
            except Exception as e:
                logger.warning(f"Error detecting {provider.name}: {e}")

        if not detected:
            logger.warning("No supported technologies detected")

        return json.dumps({
            "repo": str(self.repo_path),
            "environment": self.environment,
            "detected_providers": detected,
        }, indent=2)

    def plan(self) -> str:
        """
        Plan available scenarios.

        Returns:
            JSON string with available scenarios
        """
        scenarios = []

        for provider in self.providers:
            try:
                if not provider.detect(str(self.repo_path)):
                    continue

                inventory = provider.discover(str(self.repo_path))
                provider_scenarios = provider.list_scenarios(inventory)
                scenarios.extend(provider_scenarios)

                logger.info(f"Found {len(provider_scenarios)} scenarios from {provider.name}")
            except Exception as e:
                logger.warning(f"Error planning scenarios for {provider.name}: {e}")

        return json.dumps({
            "environment": self.environment,
            "available_scenarios": scenarios,
            "total": len(scenarios),
        }, indent=2)

    def start(self, scenario_id: str = "hidden") -> str:
        """
        Start an incident training session.

        Args:
            scenario_id: Scenario ID or "hidden" to pick randomly

        Returns:
            JSON string with session start result
        """
        # Find a suitable provider
        provider = None
        for p in self.providers:
            if p.detect(str(self.repo_path)):
                provider = p
                break

        if not provider:
            raise ProviderNotDetectedError(
                "No compatible provider detected. Ensure you have Kubernetes manifests or other supported tech."
            )

        # Get scenarios
        inventory = provider.discover(str(self.repo_path))
        scenarios = provider.list_scenarios(inventory)

        if not scenarios:
            return json.dumps({
                "status": "error",
                "message": "No supported scenarios found",
            }, indent=2)

        # Select scenario
        if scenario_id == "hidden":
            scenario = scenarios[0]
        else:
            scenario = self._find_scenario(scenarios, scenario_id)

        # Validate safety
        preflight = provider.preflight(scenario)
        if not preflight.get("allowed", False):
            raise SafetyPolicyError(
                f"Safety policy violation: {preflight.get('reason', 'Unknown reason')}"
            )

        # Create snapshot
        snapshot = provider.snapshot(scenario)

        # Create session
        session_id = str(uuid.uuid4())[:8]
        self.session = Session.create(
            session_id=session_id,
            repo_path=self.repo_path,
            environment=self.environment,
            provider=provider.name,
            scenario=scenario,
            snapshot=snapshot,
        )

        # Inject fault
        try:
            injection = provider.inject(scenario, snapshot)
            self.session.start()
            self.session.save(self.SESSION_FILE)

            logger.info(f"Session {session_id} started with scenario {scenario.get('id')}")

            return json.dumps({
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
            }, indent=2)
        except Exception as e:
            logger.error(f"Failed to inject fault: {e}")
            raise

    def hint(self) -> str:
        """
        Get the next hint.

        Returns:
            Hint text
        """
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
        """
        Check if incident is fixed.

        Returns:
            Status message
        """
        self.session = Session.from_file(self.SESSION_FILE)
        provider = self._provider_by_name(self.session.metadata.provider)

        result = provider.verify_fix(self.session.scenario)
        self.session.record_check(result)
        self.session.save(self.SESSION_FILE)

        if result.get("fixed"):
            return "✓ Fixed! Great work. Run `chaos-sensei report` to generate the learning report."

        return "✗ Not fixed yet. Try `chaos-sensei hint` or continue investigating."

    def rollback(self) -> str:
        """
        Rollback the incident.

        Returns:
            Rollback status
        """
        self.session = Session.from_file(self.SESSION_FILE)
        provider = self._provider_by_name(self.session.metadata.provider)

        result = provider.rollback(self.session.scenario, self.session.snapshot)
        self.session.rolled_back = True
        self.session.end()
        self.session.save(self.SESSION_FILE)

        logger.info(f"Session {self.session.metadata.session_id} rolled back")

        return json.dumps(result, indent=2)

    def give_up(self) -> str:
        """
        Give up and reveal the answer.

        Returns:
            Rollback and report combined
        """
        self.rollback()
        report = self.report()
        return report

    def report(self) -> str:
        """
        Generate incident report.

        Returns:
            Markdown report
        """
        self.session = Session.from_file(self.SESSION_FILE)
        scenario = self.session.scenario

        report = f"""# Chaos Sensei Incident Report

## Session Information

- **Session ID**: {self.session.metadata.session_id}
- **Environment**: {self.session.metadata.environment}
- **Provider**: {self.session.metadata.provider}
- **Created At**: {self.session.metadata.created_at}

## Scenario

**Title**: {scenario.get("title", "Unknown")}

**Difficulty**: {scenario.get("difficulty", "Unknown")}

**Category**: {scenario.get("category", "Unknown")}

## Problem Description

{scenario.get("description", "No description available")}

## Visible Symptoms

{self._format_list(scenario.get("visible_symptoms", []))}

## Root Cause

{scenario.get("root_cause", "Root cause not available")}

## Ideal Debugging Path

{self._format_list(scenario.get("ideal_path", []))}

## Your Attempts

You requested {self.session.hint_count} hints.

Verification checks: {len(self.session.checks)}

## Key Learnings

- Always check service selector labels match pod labels
- Use `kubectl get endpoints` to verify service connectivity
- Events and logs provide crucial debugging context

## Next Steps

1. Review the solution and understand the root cause
2. Practice similar scenarios to build muscle memory
3. Check the documentation for related concepts

---
Generated by Chaos Sensei v0.1.0
"""

        report_path = self.SESSION_DIR / "report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)

        logger.info(f"Report saved to {report_path}")

        return report

    def _find_scenario(self, scenarios: List[Dict], scenario_id: str) -> Dict:
        """Find scenario by ID."""
        for scenario in scenarios:
            if scenario.get("id") == scenario_id:
                return scenario
        raise ScenarioNotFoundError(f"Scenario not found: {scenario_id}")

    def _provider_by_name(self, name: str) -> Provider:
        """Find provider by name."""
        for provider in self.providers:
            if provider.name == name:
                return provider
        raise ProviderNotDetectedError(f"Provider not found: {name}")

    @staticmethod
    def _format_list(items: List[str]) -> str:
        """Format list as markdown."""
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)
