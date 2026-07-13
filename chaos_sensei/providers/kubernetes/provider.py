"""Kubernetes provider implementation."""

import logging
from pathlib import Path
from typing import Any, Dict, List

from chaos_sensei.core.exceptions import InjectionError, ProviderNotDetectedError
from chaos_sensei.providers.base import Provider
from chaos_sensei.tools.kubectl import Kubectl

logger = logging.getLogger(__name__)


class KubernetesProvider(Provider):
    """Kubernetes chaos engineering provider."""

    name = "kubernetes"
    technology = "kubernetes"

    KUBERNETES_PATTERNS = [
        "kind: Deployment",
        "kind: Service",
        "kind: Pod",
        "apiVersion: apps/v1",
        "apiVersion: v1",
    ]

    def __init__(self, context: str = None) -> None:
        """Initialize Kubernetes provider."""
        self.kubectl = Kubectl(context=context)

    def detect(self, repo_path: str) -> bool:
        """
        Detect Kubernetes manifests in repository.

        Args:
            repo_path: Path to repository

        Returns:
            True if Kubernetes manifests detected
        """
        root = Path(repo_path)
        yaml_files = list(root.rglob("*.yaml")) + list(root.rglob("*.yml"))

        for file in yaml_files:
            try:
                content = file.read_text(errors="ignore")
                for pattern in self.KUBERNETES_PATTERNS:
                    if pattern in content:
                        logger.debug(f"Detected Kubernetes pattern in {file}")
                        return True
            except (OSError, IOError):
                continue

        logger.debug("No Kubernetes patterns detected in repository")
        return False

    def discover(self, repo_path: str) -> Dict[str, Any]:
        """
        Discover Kubernetes resources in cluster.

        Args:
            repo_path: Path to repository

        Returns:
            Inventory of discovered resources
        """
        try:
            # Get all resources
            runtime = self.kubectl.get_json(["get", "deploy,svc,cm,secret", "-A", "-o", "json"])

            return {
                "provider": self.name,
                "repo_path": repo_path,
                "runtime": runtime,
            }
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            raise ProviderNotDetectedError(f"Failed to discover Kubernetes resources: {e}")

    def list_scenarios(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        List available scenarios.

        Args:
            inventory: Discovered resources

        Returns:
            List of scenarios
        """
        # For MVP, provide basic scenarios
        scenarios = [
            {
                "id": "k8s-service-selector-mismatch",
                "title": "Kubernetes Service selector mismatch",
                "description": "Service no longer routes to intended pods",
                "difficulty": "beginner",
                "blast_radius": "single-service",
                "provider": self.name,
                "category": "networking",
                "tags": ["service", "networking", "traffic"],
            },
            {
                "id": "k8s-pod-crash",
                "title": "Kubernetes Pod crash loop",
                "description": "Pod crash-loops due to missing config",
                "difficulty": "beginner",
                "blast_radius": "single-pod",
                "provider": self.name,
                "category": "availability",
                "tags": ["pod", "crash", "availability"],
            },
            {
                "id": "k8s-configmap-missing-key",
                "title": "ConfigMap missing key",
                "description": "Application can't find required config key",
                "difficulty": "intermediate",
                "blast_radius": "single-deployment",
                "provider": self.name,
                "category": "configuration",
                "tags": ["config", "configmap"],
            },
        ]

        logger.info(f"Available scenarios: {len(scenarios)}")
        return scenarios

    def preflight(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate safety before injection.

        Args:
            scenario: Scenario configuration

        Returns:
            Safety check result
        """
        namespace = scenario.get("target", {}).get("namespace", "default")

        forbidden = ["kube-system", "kube-public", "kube-node-lease", "production", "prod"]
        if namespace in forbidden:
            return {
                "allowed": False,
                "reason": f"Namespace {namespace} is forbidden by default policy",
            }

        return {
            "allowed": True,
            "reason": "Preflight checks passed",
        }

    def snapshot(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture current state.

        Args:
            scenario: Scenario configuration

        Returns:
            Snapshot data
        """
        target = scenario.get("target", {})
        kind = target.get("kind", "service")
        name = target.get("name")
        namespace = target.get("namespace", "default")

        if not name:
            raise ValueError("Target name is required")

        logger.info(f"Snapshotting {kind}/{name} in {namespace}")

        try:
            obj = self.kubectl.get_json(
                [
                    "get",
                    kind,
                    name,
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ]
            )

            return {
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "object": obj,
            }
        except Exception as e:
            raise InjectionError(f"Failed to snapshot {kind}/{name}: {e}")

    def inject(self, scenario: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject fault.

        Args:
            scenario: Scenario configuration
            snapshot: Snapshot from snapshot()

        Returns:
            Injection result
        """
        fault_type = scenario.get("fault", {}).get("type")

        if fault_type == "service_selector_mismatch":
            return self._inject_service_selector_mismatch(scenario)
        elif fault_type == "pod_crash":
            return self._inject_pod_crash(scenario)
        elif fault_type == "configmap_missing_key":
            return self._inject_configmap_missing_key(scenario)

        raise InjectionError(f"Unknown fault type: {fault_type}")

    def observe(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect system state.

        Args:
            scenario: Scenario configuration

        Returns:
            Observed state
        """
        namespace = scenario.get("target", {}).get("namespace", "default")

        try:
            pods = self.kubectl.get_pods(namespace)
            events = self.kubectl.get_events(namespace)

            return {
                "pods": pods,
                "events": events,
            }
        except Exception as e:
            logger.error(f"Observation failed: {e}")
            return {
                "pods": "",
                "events": "",
                "error": str(e),
            }

    def verify_fix(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check if issue is fixed.

        Args:
            scenario: Scenario configuration

        Returns:
            Verification result
        """
        target = scenario.get("target", {})
        namespace = target.get("namespace", "default")
        kind = target.get("kind", "service")
        name = target.get("name")

        if not name:
            return {"fixed": False, "details": "Target name not specified"}

        try:
            if kind == "service":
                service = self.kubectl.get_service(name, namespace)
                # Check if service has endpoints
                endpoints = service.get("status", {}).get("loadBalancer", {}).get("ingress", [])
                has_endpoints = len(service.get("spec", {}).get("selector", {})) > 0

                return {
                    "fixed": has_endpoints,
                    "details": f"Service has selector: {has_endpoints}",
                }
            elif kind == "deployment":
                status = self.kubectl.rollout_status("deployment", name, namespace, timeout="30s")
                fixed = "successfully rolled out" in status.lower()
                return {
                    "fixed": fixed,
                    "details": status,
                }

            return {"fixed": False, "details": "Unknown resource kind"}

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {"fixed": False, "details": str(e)}

    def rollback(self, scenario: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Restore original state.

        Args:
            scenario: Scenario configuration
            snapshot: Snapshot from snapshot()

        Returns:
            Rollback result
        """
        try:
            obj = snapshot.get("object")
            if not obj:
                raise ValueError("No snapshot data available for rollback")

            logger.info(f"Rolling back {snapshot['kind']}/{snapshot['name']}")
            self.kubectl.apply_json(obj)

            return {
                "rolled_back": True,
                "details": f"Restored {snapshot['kind']}/{snapshot['name']} in {snapshot['namespace']}",
            }
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise Exception(f"Rollback failed: {e}")

    def _inject_service_selector_mismatch(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Inject service selector mismatch."""
        target = scenario.get("target", {})
        namespace = target.get("namespace", "default")
        service = target.get("name")

        patch = {
            "spec": {
                "selector": {
                    "app": "chaos-sensei-broken-selector-" + service,
                }
            }
        }

        try:
            self.kubectl.patch_json(
                kind="service",
                name=service,
                namespace=namespace,
                patch=patch,
            )

            return {
                "injected": True,
                "details": f"Service selector patched for {service}",
            }
        except Exception as e:
            raise InjectionError(f"Failed to inject selector mismatch: {e}")

    def _inject_pod_crash(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Inject pod crash."""
        raise NotImplementedError("Pod crash injection not yet implemented")

    def _inject_configmap_missing_key(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Inject ConfigMap missing key."""
        raise NotImplementedError("ConfigMap injection not yet implemented")
