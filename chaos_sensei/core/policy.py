"""General safety policy evaluation, independent of any one provider.

Provider.preflight() still exists for technology-specific checks (e.g. "does
this kubectl context have RBAC to patch this object"). PolicyEngine handles
the provider-agnostic rules that come from chaos-sensei.yaml: forbidden
namespaces/kinds/keywords, production gating, and confirmation requirements.
"""

import json
import logging
from typing import Any, Dict, Optional

from chaos_sensei.core.config import Config

logger = logging.getLogger(__name__)

_BLAST_RADIUS_SEVERITY = {
    "single-pod": "low",
    "single-service": "low",
    "single-deployment": "medium",
}

_PRODUCTION_ENVIRONMENTS = {"production", "prod"}


class PolicyEngine:
    """Evaluates a scenario against the configured safety policy."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def evaluate(
        self,
        scenario: Dict[str, Any],
        inventory: Optional[Dict[str, Any]] = None,
        environment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decide whether a scenario is safe enough to run.

        Returns:
            {
              "allowed": bool,
              "severity": "low" | "medium" | "high",
              "requires_confirmation": bool,
              "reasons": [str, ...],
              "blocked_by": [str, ...],
            }
        """
        safety = self.config.safety
        reasons = []
        blocked_by = []

        env = (environment or scenario.get("environment") or self.config.environment or "").lower()
        if env in _PRODUCTION_ENVIRONMENTS and not safety.allow_production:
            blocked_by.append("environment")
            reasons.append(f"Environment '{env}' is production and allow_production is False")

        target = scenario.get("target", {})
        namespace = target.get("namespace")
        kind = target.get("kind")

        if namespace and namespace in safety.forbidden_namespaces:
            blocked_by.append("namespace")
            reasons.append(f"Namespace '{namespace}' is in forbidden_namespaces")
        elif namespace and safety.allowed_namespaces and namespace not in safety.allowed_namespaces:
            blocked_by.append("namespace_not_allowlisted")
            reasons.append(f"Namespace '{namespace}' is not in allowed_namespaces")

        if kind:
            forbidden_kinds_lower = {k.lower() for k in safety.forbidden_kinds}
            if kind.lower() in forbidden_kinds_lower:
                blocked_by.append("kind")
                reasons.append(f"Resource kind '{kind}' is in forbidden_kinds")

        haystack = json.dumps(scenario).lower()
        matched_keywords = [kw for kw in safety.forbidden_keywords if kw.lower() in haystack]
        if matched_keywords:
            blocked_by.append("keyword")
            reasons.append(f"Scenario mentions forbidden keyword(s): {', '.join(matched_keywords)}")

        allowed = len(blocked_by) == 0
        severity = _BLAST_RADIUS_SEVERITY.get(scenario.get("blast_radius", ""), "medium")

        if not allowed:
            logger.info(f"Policy blocked scenario {scenario.get('id')}: {reasons}")

        return {
            "allowed": allowed,
            "severity": severity,
            "requires_confirmation": safety.require_confirmation,
            "reasons": reasons,
            "blocked_by": blocked_by,
        }
