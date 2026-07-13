"""Configuration management for Chaos Sensei."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class SafetyPolicy(BaseModel):
    """Safety policy configuration."""

    allow_production: bool = False
    require_confirmation: bool = True
    rollback_required: bool = True
    max_duration_minutes: int = 20

    allowed_namespaces: List[str] = Field(default_factory=lambda: ["default", "apps", "staging"])
    forbidden_namespaces: List[str] = Field(
        default_factory=lambda: ["kube-system", "production", "prod"]
    )

    forbidden_kinds: List[str] = Field(
        default_factory=lambda: [
            "PersistentVolumeClaim",
            "PersistentVolume",
            "CustomResourceDefinition",
            "ClusterRole",
            "ClusterRoleBinding",
            "StorageClass",
            "Secret",
        ]
    )

    forbidden_keywords: List[str] = Field(
        default_factory=lambda: ["production", "prod", "live", "customer", "billing"]
    )

    class Config:
        """Pydantic config."""

        extra = "allow"


class ProviderConfig(BaseModel):
    """Provider-specific configuration."""

    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic config."""

        extra = "allow"


class ProvidersConfig(BaseModel):
    """All provider configurations."""

    kubernetes: ProviderConfig = Field(default_factory=ProviderConfig)
    helm: ProviderConfig = Field(default_factory=lambda: ProviderConfig(enabled=False))
    terraform: ProviderConfig = Field(default_factory=lambda: ProviderConfig(enabled=False))
    terragrunt: ProviderConfig = Field(default_factory=lambda: ProviderConfig(enabled=False))
    docker: ProviderConfig = Field(default_factory=lambda: ProviderConfig(enabled=False))

    class Config:
        """Pydantic config."""

        extra = "allow"


class ModeConfig(BaseModel):
    """Training mode configuration."""

    root_cause_visibility: str = "hidden"
    hints_before_reveal: int = 3
    auto_rollback_on_give_up: bool = True
    auto_report: bool = True

    @validator("root_cause_visibility")
    def validate_visibility(cls, v: str) -> str:
        """Validate visibility setting."""
        if v not in ["hidden", "visible", "partial"]:
            raise ValueError(f"Invalid visibility: {v}")
        return v


class Config(BaseModel):
    """Main configuration model."""

    version: str = "v1"
    project: Dict[str, str] = Field(default_factory=lambda: {"name": "unknown"})
    environment: str = "staging"
    mode: ModeConfig = Field(default_factory=ModeConfig)
    safety: SafetyPolicy = Field(default_factory=SafetyPolicy)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)

    class Config:
        """Pydantic config."""

        extra = "allow"

    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file."""
        if not path.exists():
            logger.warning(f"Config file not found: {path}, using defaults")
            return cls()

        try:
            with open(path) as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            raise

    def to_yaml(self, path: Path) -> None:
        """Save configuration to YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.dict(exclude_defaults=False), f, default_flow_style=False)
        logger.info(f"Config saved to {path}")

    def is_safe(self, namespace: Optional[str] = None, kind: Optional[str] = None) -> bool:
        """Check if operation is allowed by safety policy."""
        if namespace and namespace in self.safety.forbidden_namespaces:
            return False
        if kind and kind in self.safety.forbidden_kinds:
            return False
        return True
