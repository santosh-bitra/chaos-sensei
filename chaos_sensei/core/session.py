"""Session management for Chaos Sensei experiments."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from chaos_sensei.core.events import EventType
from chaos_sensei.core.state import SessionStatus, assert_transition

logger = logging.getLogger(__name__)


class SessionMetadata(BaseModel):
    """Metadata about a session."""

    session_id: str
    repo_path: str
    environment: str
    provider: str
    created_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None


class SessionEvent(BaseModel):
    """A single entry in a session's audit timeline."""

    type: str
    timestamp: str
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)


class Session(BaseModel):
    """Active experiment session."""

    metadata: SessionMetadata
    status: SessionStatus = SessionStatus.CREATED
    scenario: Dict[str, Any] = Field(default_factory=dict)
    snapshot: Dict[str, Any] = Field(default_factory=dict)
    events: List[SessionEvent] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    hint_count: int = 0
    checks: list = Field(default_factory=list)
    rolled_back: bool = False

    class Config:
        """Pydantic config."""

        extra = "allow"

    @classmethod
    def from_file(cls, path: Path) -> "Session":
        """Load session from JSON file."""
        if not path.exists():
            raise FileNotFoundError(f"Session file not found: {path}")

        try:
            with open(path) as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            logger.error(f"Failed to load session from {path}: {e}")
            raise

    def save(self, path: Path) -> None:
        """Save session to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.dict(), f, indent=2)
        logger.debug(f"Session saved to {path}")

    @classmethod
    def create(
        cls,
        session_id: str,
        repo_path: str,
        environment: str,
        provider: str,
        scenario: Dict[str, Any],
        snapshot: Dict[str, Any],
    ) -> "Session":
        """Create a new session."""
        metadata = SessionMetadata(
            session_id=session_id,
            repo_path=str(repo_path),
            environment=environment,
            provider=provider,
            created_at=datetime.utcnow().isoformat(),
        )

        session = cls(
            metadata=metadata,
            scenario=scenario,
            snapshot=snapshot,
        )
        session.add_event(EventType.SNAPSHOT_CREATED, "Session created with snapshot")
        return session

    def add_event(
        self, event_type: EventType, message: str = "", data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Append an entry to the session's audit timeline."""
        self.events.append(
            SessionEvent(
                type=event_type.value if isinstance(event_type, EventType) else str(event_type),
                timestamp=datetime.utcnow().isoformat(),
                message=message,
                data=data or {},
            )
        )

    def _transition(self, target: SessionStatus) -> None:
        """Move to a new status, raising if the transition is illegal."""
        assert_transition(self.status, target)
        self.status = target

    def start(self) -> None:
        """Mark session as started and transition to INJECTED."""
        self.metadata.started_at = datetime.utcnow().isoformat()
        self._transition(SessionStatus.INJECTED)
        self.add_event(EventType.INJECTION_COMPLETED, "Fault injected, session started")

    def mark_injected(self, details: str = "") -> None:
        """Transition to INJECTED and record the injection event."""
        self._transition(SessionStatus.INJECTED)
        self.add_event(EventType.INJECTION_COMPLETED, details)

    def mark_under_investigation(self) -> None:
        """Transition to UNDER_INVESTIGATION (first hint/check after injection)."""
        if self.status == SessionStatus.INJECTED:
            self._transition(SessionStatus.UNDER_INVESTIGATION)

    def mark_fixed(self, details: str = "") -> None:
        """Transition to FIXED and record the verification event."""
        self._transition(SessionStatus.FIXED)
        self.add_event(EventType.FIX_VERIFIED, details)

    def mark_rolled_back(self, details: str = "") -> None:
        """Transition to ROLLED_BACK and record the rollback event."""
        self._transition(SessionStatus.ROLLED_BACK)
        self.rolled_back = True
        self.add_event(EventType.ROLLBACK_COMPLETED, details)
        self.end()

    def mark_failed(self, details: str = "") -> None:
        """Transition to FAILED and record the failure event."""
        self._transition(SessionStatus.FAILED)
        self.add_event(EventType.SESSION_FAILED, details)
        self.end()

    def end(self) -> None:
        """Mark session as ended."""
        self.metadata.ended_at = datetime.utcnow().isoformat()

    def get_hint_count(self) -> int:
        """Get number of hints requested."""
        return self.hint_count

    def increment_hint(self) -> None:
        """Increment hint counter and record the event."""
        self.hint_count += 1
        self.mark_under_investigation()
        self.add_event(EventType.HINT_REQUESTED, f"hint #{self.hint_count}")

    def record_check(self, result: Dict[str, Any]) -> None:
        """Record a verification check."""
        self.mark_under_investigation()
        self.checks.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "result": result,
            }
        )
        self.add_event(EventType.CHECK_PERFORMED, "", data=result)

    def record_observation(self, observation: Dict[str, Any]) -> None:
        """Store a symptom/state snapshot collected during investigation."""
        self.observations.append(observation)
