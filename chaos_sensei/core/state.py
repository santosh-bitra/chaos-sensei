"""Session status state machine."""

from enum import Enum

from chaos_sensei.core.exceptions import SessionError


class SessionStatus(str, Enum):
    """Lifecycle states a session can be in.

    A session is only persisted to disk once a fault has actually been
    injected (see ``ChaosSenseiEngine.start``), so the machine starts at
    CREATED (== just injected) rather than modeling the pre-injection
    planning steps, which happen in-memory before any session exists.
    """

    CREATED = "created"
    INJECTED = "injected"
    UNDER_INVESTIGATION = "under_investigation"
    FIXED = "fixed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    EXPIRED = "expired"


# Terminal states are omitted as keys - no transitions are allowed out of them.
ALLOWED_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.CREATED: {SessionStatus.INJECTED, SessionStatus.FAILED},
    SessionStatus.INJECTED: {
        SessionStatus.UNDER_INVESTIGATION,
        SessionStatus.FIXED,
        SessionStatus.ROLLED_BACK,
        SessionStatus.FAILED,
        SessionStatus.EXPIRED,
    },
    SessionStatus.UNDER_INVESTIGATION: {
        SessionStatus.FIXED,
        SessionStatus.ROLLED_BACK,
        SessionStatus.FAILED,
        SessionStatus.EXPIRED,
    },
    SessionStatus.FIXED: {SessionStatus.ROLLED_BACK},
    SessionStatus.EXPIRED: {SessionStatus.ROLLED_BACK},
}


def can_transition(current: SessionStatus, target: SessionStatus) -> bool:
    """Return True if moving from current to target is a legal transition."""
    if current == target:
        return True
    return target in ALLOWED_TRANSITIONS.get(current, set())


def assert_transition(current: SessionStatus, target: SessionStatus) -> None:
    """Raise SessionError if moving from current to target is not allowed."""
    if not can_transition(current, target):
        raise SessionError(
            f"Illegal session transition: {current.value} -> {target.value}"
        )
