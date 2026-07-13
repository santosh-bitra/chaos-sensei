"""Kubernetes provider implementation."""

import copy
import logging
from pathlib import Path
from typing import Any, Dict, List

import yaml

from chaos_sensei.core.exceptions import InjectionError, ProviderNotDetectedError, RollbackError
from chaos_sensei.providers.base import Provider
from chaos_sensei.tools.kubectl import Kubectl

logger = logging.getLogger(__name__)

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


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

    # Stub entries for scenarios whose injector isn't implemented yet
    # (see providers/kubernetes/scenarios/ for the full YAML-defined ones).
    # These stay listable (so `plan` shows the roadmap) but `start` on them
    # will fail loudly at inject() rather than silently doing nothing.
    _UNIMPLEMENTED_STUBS = [
        {
            "id": "k8s-pod-crash",
            "title": "Kubernetes Pod crash loop",
            "description": "Pod crash-loops due to missing config",
            "difficulty": "beginner",
            "blast_radius": "single-pod",
            "provider": "kubernetes",
            "category": "availability",
            "tags": ["pod", "crash", "availability"],
            "implemented": False,
        },
        {
            "id": "k8s-configmap-missing-key",
            "title": "ConfigMap missing key",
            "description": "Application can't find required config key",
            "difficulty": "intermediate",
            "blast_radius": "single-deployment",
            "provider": "kubernetes",
            "category": "configuration",
            "tags": ["config", "configmap"],
            "implemented": False,
        },
    ]

    def _load_scenario_files(self) -> List[Dict[str, Any]]:
        """Load every fully-defined scenario from scenarios/*.yaml."""
        scenarios = []
        if not SCENARIOS_DIR.exists():
            return scenarios

        for path in sorted(SCENARIOS_DIR.glob("*.yaml")):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                if data and data.get("id"):
                    data.setdefault("provider", self.name)
                    data["implemented"] = True
                    scenarios.append(data)
            except Exception as e:
                logger.warning(f"Failed to load scenario file {path}: {e}")

        return scenarios

    def list_scenarios(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        List available scenarios: fully-defined ones loaded from YAML first,
        followed by not-yet-implemented stubs so `plan` still shows the roadmap.

        Args:
            inventory: Discovered resources

        Returns:
            List of scenarios
        """
        scenarios = self._load_scenario_files()
        loaded_ids = {s["id"] for s in scenarios}
        scenarios.extend(s for s in self._UNIMPLEMENTED_STUBS if s["id"] not in loaded_ids)

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
                selector = service.get("spec", {}).get("selector", {}) or {}
                has_selector = len(selector) > 0

                expected_selector = scenario.get("success_criteria", {}).get("expected_selector")
                if expected_selector:
                    fixed = selector == expected_selector
                    details = (
                        f"Selector is {selector}, expected {expected_selector}"
                        if not fixed
                        else "Selector matches expected value"
                    )
                else:
                    # No known-good selector to compare against (unimplemented
                    # scenario stub) - fall back to a weaker existence check.
                    fixed = has_selector
                    details = f"Service has selector: {has_selector}"

                return {"fixed": fixed, "details": details}
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

        Prefers a field-level JSON Patch replace when the fault type is
        known to have mutated exactly one field (mirrors the injector) -
        this sidesteps kubectl apply's merge semantics, which silently
        fail to remove keys a fault added to a map field like a Service's
        spec.selector (see _strip_server_fields for the related
        resourceVersion issue). Falls back to a whole-object apply for any
        fault type without a dedicated field-level rollback.

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
            fault_type = scenario.get("fault", {}).get("type")

            if fault_type == "service_selector_mismatch":
                original_selector = obj.get("spec", {}).get("selector", {})
                self.kubectl.replace_field(
                    kind=snapshot["kind"],
                    name=snapshot["name"],
                    namespace=snapshot["namespace"],
                    path="/spec/selector",
                    value=original_selector,
                )
            else:
                self.kubectl.apply_json(self._strip_server_fields(obj))

            return {
                "rolled_back": True,
                "details": f"Restored {snapshot['kind']}/{snapshot['name']} in {snapshot['namespace']}",
            }
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise RollbackError(f"Rollback failed: {e}")

    @staticmethod
    def _strip_server_fields(obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Drop server-managed fields from a captured object before re-applying it.

        A snapshot's metadata.resourceVersion reflects the object's state at
        snapshot time. By the time rollback runs, the object has always been
        modified at least once (the injection itself), so resourceVersion is
        stale - kubectl apply then rejects it with a 409 Conflict, treating
        it as a concurrent edit rather than an intentional restore. uid,
        creationTimestamp, generation, and status are similarly server-owned
        and must not be sent back on a write.
        """
        clean = copy.deepcopy(obj)
        metadata = clean.get("metadata", {})
        for field in ("resourceVersion", "uid", "creationTimestamp", "generation", "selfLink", "managedFields"):
            metadata.pop(field, None)
        clean.pop("status", None)
        return clean

    def _inject_service_selector_mismatch(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Inject service selector mismatch.

        Uses a JSON Patch replace (not a merge patch) so the selector is
        fully overwritten with the broken value - a merge patch would only
        add the broken key alongside the real ones, which still breaks
        routing (selectors AND their keys) but leaves a misleading
        half-broken object behind instead of a clean single-cause fault.
        """
        target = scenario.get("target", {})
        namespace = target.get("namespace", "default")
        service = target.get("name")

        broken_selector = {"app": "chaos-sensei-broken-selector-" + service}

        try:
            self.kubectl.replace_field(
                kind="service",
                name=service,
                namespace=namespace,
                path="/spec/selector",
                value=broken_selector,
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
