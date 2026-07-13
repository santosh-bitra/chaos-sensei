"""Event type definitions for session timelines."""

from enum import Enum


class EventType(str, Enum):
    """Named events that can occur during a Chaos Sensei session."""

    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    PLAN_CREATED = "plan_created"
    PREFLIGHT_PASSED = "preflight_passed"
    PREFLIGHT_BLOCKED = "preflight_blocked"
    SNAPSHOT_CREATED = "snapshot_created"
    INJECTION_STARTED = "injection_started"
    INJECTION_COMPLETED = "injection_completed"
    HINT_REQUESTED = "hint_requested"
    CHECK_PERFORMED = "check_performed"
    FIX_VERIFIED = "fix_verified"
    ROLLBACK_STARTED = "rollback_started"
    ROLLBACK_COMPLETED = "rollback_completed"
    GAVE_UP = "gave_up"
    REPORT_GENERATED = "report_generated"
    SESSION_FAILED = "session_failed"
