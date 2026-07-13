"""Turns detected providers + discovered inventory into a scenario plan."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from chaos_sensei.core.exceptions import ProviderNotDetectedError, ScenarioNotFoundError
from chaos_sensei.core.policy import PolicyEngine
from chaos_sensei.providers.base import Provider

logger = logging.getLogger(__name__)


class ScenarioPlanner:
    """Builds the menu of scenarios a session can be started from."""

    def __init__(self, providers: List[Provider], policy_engine: PolicyEngine) -> None:
        self.providers = providers
        self.policy_engine = policy_engine

    def detect_providers(self, repo_path: Path) -> List[Provider]:
        """Return the subset of registered providers that match this repo."""
        detected = []
        for provider in self.providers:
            try:
                if provider.detect(str(repo_path)):
                    detected.append(provider)
            except Exception as e:
                logger.warning(f"Error detecting {provider.name}: {e}")
        return detected

    def build_plan(self, repo_path: Path, environment: str) -> Dict[str, Any]:
        """
        Discover inventory and produce a policy-filtered scenario plan.

        Returns:
            {
              "environment": str,
              "detected_providers": [str, ...],
              "available_scenarios": [scenario, ...],   # policy-allowed
              "blocked_scenarios": [scenario, ...],      # policy-blocked, with reasons
              "recommended_scenario": scenario | None,
              "total": int,
            }
        """
        detected = self.detect_providers(repo_path)
        available: List[Dict[str, Any]] = []
        blocked: List[Dict[str, Any]] = []

        for provider in detected:
            try:
                inventory = provider.discover(str(repo_path))
                scenarios = provider.list_scenarios(inventory)
            except Exception as e:
                logger.warning(f"Error planning scenarios for {provider.name}: {e}")
                continue

            for scenario in scenarios:
                evaluation = self.policy_engine.evaluate(scenario, inventory, environment)
                entry = {**scenario, "policy": evaluation}
                (available if evaluation["allowed"] else blocked).append(entry)

        return {
            "environment": environment,
            "detected_providers": [p.name for p in detected],
            "available_scenarios": available,
            "blocked_scenarios": blocked,
            "recommended_scenario": available[0] if available else None,
            "total": len(available),
        }

    def choose_scenario(
        self, scenarios: List[Dict[str, Any]], requested_id: Optional[str]
    ) -> Dict[str, Any]:
        """Pick a scenario by id, or the first available one for 'hidden'/None."""
        if not scenarios:
            raise ScenarioNotFoundError("No supported scenarios found")

        if not requested_id or requested_id == "hidden":
            return scenarios[0]

        for scenario in scenarios:
            if scenario.get("id") == requested_id:
                return scenario

        raise ScenarioNotFoundError(f"Scenario not found: {requested_id}")

    def first_matching_provider(self, repo_path: Path) -> Provider:
        """Return the first provider that detects this repo, or raise."""
        detected = self.detect_providers(repo_path)
        if not detected:
            raise ProviderNotDetectedError(
                "No compatible provider detected. Ensure you have Kubernetes manifests or other supported tech."
            )
        return detected[0]
