"""Chaos Sensei exceptions."""


class ChaosSenseiException(Exception):
    """Base exception for Chaos Sensei."""

    pass


class ConfigError(ChaosSenseiException):
    """Configuration error."""

    pass


class ProviderError(ChaosSenseiException):
    """Provider-related error."""

    pass


class ProviderNotDetectedError(ProviderError):
    """Provider not detected in repository."""

    pass


class ProviderNotAvailableError(ProviderError):
    """Provider is not available."""

    pass


class ScenarioError(ChaosSenseiException):
    """Scenario-related error."""

    pass


class ScenarioNotFoundError(ScenarioError):
    """Scenario not found."""

    pass


class SafetyPolicyError(ChaosSenseiException):
    """Safety policy violation."""

    pass


class SessionError(ChaosSenseiException):
    """Session-related error."""

    pass


class SessionNotFoundError(SessionError):
    """No active session found."""

    pass


class InjectionError(ChaosSenseiException):
    """Fault injection error."""

    pass


class RollbackError(ChaosSenseiException):
    """Rollback error."""

    pass


class ToolError(ChaosSenseiException):
    """Tool execution error."""

    pass


class KubernetesToolError(ToolError):
    """Kubernetes tool error."""

    pass
