"""Base provider interface for Chaos Sensei."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class Provider(ABC):
    """Abstract base provider for chaos engineering scenarios."""

    name: str = "base"
    technology: str = "base"

    @abstractmethod
    def detect(self, repo_path: str) -> bool:
        """
        Detect if this provider can operate on the target repo.

        Args:
            repo_path: Path to the repository

        Returns:
            True if provider can operate on the repo, False otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def discover(self, repo_path: str) -> Dict[str, Any]:
        """
        Discover infrastructure and services in the repo/environment.

        Args:
            repo_path: Path to the repository

        Returns:
            Normalized inventory of discovered resources
        """
        raise NotImplementedError

    @abstractmethod
    def list_scenarios(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        List available scenarios based on discovered inventory.

        Args:
            inventory: Discovered resources from discover()

        Returns:
            List of available scenarios with metadata
        """
        raise NotImplementedError

    @abstractmethod
    def preflight(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate permissions and safety before injection.

        Args:
            scenario: Scenario configuration

        Returns:
            Dict with 'allowed' (bool) and 'reason' (str) keys
        """
        raise NotImplementedError

    @abstractmethod
    def snapshot(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture current state needed for rollback.

        Args:
            scenario: Scenario configuration

        Returns:
            Snapshot data for rollback
        """
        raise NotImplementedError

    @abstractmethod
    def inject(self, scenario: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject the controlled fault.

        Args:
            scenario: Scenario configuration
            snapshot: Snapshot from snapshot()

        Returns:
            Result of injection with status and details
        """
        raise NotImplementedError

    @abstractmethod
    def observe(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect system state, logs, events, metrics.

        Args:
            scenario: Scenario configuration

        Returns:
            Observed symptoms and system state
        """
        raise NotImplementedError

    @abstractmethod
    def verify_fix(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if the user fixed the issue.

        Args:
            scenario: Scenario configuration

        Returns:
            Dict with 'fixed' (bool) and 'details' (str) keys
        """
        raise NotImplementedError

    @abstractmethod
    def rollback(self, scenario: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore original state from snapshot.

        Args:
            scenario: Scenario configuration
            snapshot: Snapshot from snapshot()

        Returns:
            Result of rollback with status and details
        """
        raise NotImplementedError
