"""Tests for configuration module."""

from pathlib import Path

import pytest

from chaos_sensei.core.config import Config, SafetyPolicy


def test_config_creation():
    """Test basic config creation."""
    config = Config()
    assert config.version == "v1"
    assert config.environment == "staging"


def test_safety_policy_defaults():
    """Test safety policy defaults."""
    policy = SafetyPolicy()
    assert policy.allow_production is False
    assert policy.require_confirmation is True
    assert "kube-system" in policy.forbidden_namespaces


def test_config_is_safe():
    """Test safety check."""
    config = Config()
    assert config.is_safe("default") is True
    assert config.is_safe("kube-system") is False
    assert config.is_safe("PersistentVolumeClaim", kind="PersistentVolumeClaim") is False
