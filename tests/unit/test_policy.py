"""Tests for PolicyEngine safety evaluation."""

from chaos_sensei.core.config import Config
from chaos_sensei.core.policy import PolicyEngine

SCENARIO = {
    "id": "k8s-service-selector-mismatch",
    "blast_radius": "single-service",
    "target": {"kind": "service", "name": "checkout", "namespace": "apps"},
}


def test_allowed_scenario_in_allowed_namespace():
    policy = PolicyEngine(Config())
    result = policy.evaluate(SCENARIO, environment="staging")
    assert result["allowed"] is True
    assert result["blocked_by"] == []


def test_forbidden_namespace_blocks():
    policy = PolicyEngine(Config())
    scenario = {**SCENARIO, "target": {**SCENARIO["target"], "namespace": "kube-system"}}
    result = policy.evaluate(scenario, environment="staging")
    assert result["allowed"] is False
    assert "namespace" in result["blocked_by"]


def test_production_blocked_by_default():
    policy = PolicyEngine(Config())
    result = policy.evaluate(SCENARIO, environment="production")
    assert result["allowed"] is False
    assert "environment" in result["blocked_by"]


def test_production_allowed_when_explicitly_enabled():
    config = Config()
    config.safety.allow_production = True
    config.safety.allowed_namespaces = []
    policy = PolicyEngine(config)
    result = policy.evaluate(SCENARIO, environment="production")
    assert result["allowed"] is True


def test_forbidden_kind_blocks():
    policy = PolicyEngine(Config())
    scenario = {**SCENARIO, "target": {**SCENARIO["target"], "kind": "Secret"}}
    result = policy.evaluate(scenario, environment="staging")
    assert result["allowed"] is False
    assert "kind" in result["blocked_by"]


def test_forbidden_keyword_blocks():
    policy = PolicyEngine(Config())
    scenario = {**SCENARIO, "description": "affects billing system"}
    result = policy.evaluate(scenario, environment="staging")
    assert result["allowed"] is False
    assert "keyword" in result["blocked_by"]


def test_severity_derived_from_blast_radius():
    policy = PolicyEngine(Config())
    result = policy.evaluate(SCENARIO, environment="staging")
    assert result["severity"] == "low"
