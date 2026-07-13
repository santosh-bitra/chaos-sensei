"""Kubernetes kubectl command wrapper."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from chaos_sensei.core.exceptions import KubernetesToolError

logger = logging.getLogger(__name__)


class Kubectl:
    """Safe wrapper around kubectl commands."""

    def __init__(self, context: Optional[str] = None) -> None:
        """
        Initialize kubectl wrapper.

        Args:
            context: Kubernetes context to use. If None, uses current context.
        """
        self.context = context
        self._verify_kubectl_installed()

    def _verify_kubectl_installed(self) -> None:
        """Verify kubectl is installed and accessible."""
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client", "-o", "json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.returncode != 0:
                raise KubernetesToolError("kubectl not found or not configured")
        except FileNotFoundError as e:
            raise KubernetesToolError(f"kubectl executable not found: {e}")
        except subprocess.TimeoutExpired as e:
            raise KubernetesToolError(f"kubectl version check timed out: {e}")

    def run(self, args: List[str], check: bool = True) -> str:
        """
        Run kubectl command and return output.

        Args:
            args: kubectl arguments (without 'kubectl' prefix)
            check: Raise exception on non-zero exit code

        Returns:
            Command stdout as string

        Raises:
            KubernetesToolError: If command fails and check=True
        """
        command = ["kubectl"]
        if self.context:
            command.extend(["--context", self.context])
        command.extend(args)

        logger.debug(f"Running: {' '.join(command)}")

        try:
            result = subprocess.run(
                command,
                text=True,
                capture_output=True,
                check=False,
                timeout=30,
            )

            if result.returncode != 0 and check:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"kubectl failed: {error_msg}")
                raise KubernetesToolError(f"kubectl command failed: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired as e:
            raise KubernetesToolError(f"kubectl command timed out: {e}")
        except Exception as e:
            raise KubernetesToolError(f"kubectl command failed: {e}")

    def get_json(self, args: List[str]) -> Dict[str, Any]:
        """
        Run kubectl command returning JSON.

        Args:
            args: kubectl arguments

        Returns:
            Parsed JSON output
        """
        output = self.run(args + ["-o", "json"])
        try:
            return json.loads(output)
        except json.JSONDecodeError as e:
            raise KubernetesToolError(f"Failed to parse kubectl JSON output: {e}")

    def patch_json(
        self, kind: str, name: str, namespace: str, patch: Dict[str, Any]
    ) -> str:
        """
        Patch a Kubernetes resource.

        Args:
            kind: Resource kind (e.g., 'service', 'deployment')
            name: Resource name
            namespace: Kubernetes namespace
            patch: Patch content as dict

        Returns:
            Command output
        """
        patch_json = json.dumps(patch)
        logger.info(f"Patching {kind}/{name} in {namespace} with: {patch_json}")

        return self.run(
            [
                "patch",
                kind,
                name,
                "-n",
                namespace,
                "--type=merge",
                "-p",
                patch_json,
            ]
        )

    def replace_field(
        self, kind: str, name: str, namespace: str, path: str, value: Any
    ) -> str:
        """
        Atomically replace a single field via RFC 6902 JSON Patch.

        Unlike patch_json() (JSON Merge Patch, --type=merge) or apply_json()
        (kubectl apply), a JSON Patch "replace" op overwrites the value at
        `path` in full - it does not merge map/object values, so it's the
        right tool whenever a field (e.g. a Service's spec.selector) must
        end up exactly matching a desired value, with no leftover keys from
        whatever was there before.

        Args:
            kind: Resource kind (e.g., 'service')
            name: Resource name
            namespace: Kubernetes namespace
            path: RFC 6901 JSON Pointer (e.g. '/spec/selector')
            value: Replacement value

        Returns:
            Command output
        """
        patch = json.dumps([{"op": "replace", "path": path, "value": value}])
        logger.info(f"Replacing {path} on {kind}/{name} in {namespace} with: {patch}")

        return self.run(
            [
                "patch",
                kind,
                name,
                "-n",
                namespace,
                "--type=json",
                "-p",
                patch,
            ]
        )

    def apply_json(self, obj: Dict[str, Any]) -> str:
        """
        Apply a Kubernetes resource from JSON.

        Args:
            obj: Kubernetes resource as dict

        Returns:
            Command output
        """
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(obj, f)
            temp_path = f.name

        try:
            logger.info(f"Applying resource: {obj.get('kind', 'Unknown')}/{obj.get('metadata', {}).get('name', 'Unknown')}")
            return self.run(["apply", "-f", temp_path])
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def get_pods(self, namespace: str, **kwargs: Any) -> str:
        """
        Get pods in a namespace.

        Args:
            namespace: Kubernetes namespace
            **kwargs: Additional options (e.g., label_selector)

        Returns:
            kubectl output
        """
        args = ["get", "pods", "-n", namespace]
        if label_selector := kwargs.get("label_selector"):
            args.extend(["-l", label_selector])
        return self.run(args)

    def get_service(self, name: str, namespace: str) -> Dict[str, Any]:
        """
        Get a service resource.

        Args:
            name: Service name
            namespace: Kubernetes namespace

        Returns:
            Service object as dict
        """
        return self.get_json(["get", "service", name, "-n", namespace])

    def get_events(self, namespace: str) -> str:
        """
        Get events in a namespace sorted by timestamp.

        Args:
            namespace: Kubernetes namespace

        Returns:
            kubectl output
        """
        return self.run(
            [
                "get",
                "events",
                "-n",
                namespace,
                "--sort-by=.lastTimestamp",
            ]
        )

    def rollout_status(
        self, kind: str, name: str, namespace: str, timeout: str = "60s"
    ) -> str:
        """
        Check rollout status of a deployment/daemonset.

        Args:
            kind: Resource kind (e.g., 'deployment')
            name: Resource name
            namespace: Kubernetes namespace
            timeout: Command timeout

        Returns:
            kubectl output
        """
        return self.run(
            [
                "rollout",
                "status",
                f"{kind}/{name}",
                "-n",
                namespace,
                f"--timeout={timeout}",
            ]
        )
