"""Session management for Chaos Sensei experiments."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

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


class Session(BaseModel):
    """Active experiment session."""

    metadata: SessionMetadata
    scenario: Dict[str, Any] = Field(default_factory=dict)
    snapshot: Dict[str, Any] = Field(default_factory=dict)
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

        return cls(
            metadata=metadata,
            scenario=scenario,
            snapshot=snapshot,
        )

    def start(self) -> None:
        """Mark session as started."""
        self.metadata.started_at = datetime.utcnow().isoformat()

    def end(self) -> None:
        """Mark session as ended."""
        self.metadata.ended_at = datetime.utcnow().isoformat()

    def get_hint_count(self) -> int:
        """Get number of hints requested."""
        return self.hint_count

    def increment_hint(self) -> None:
        """Increment hint counter."""
        self.hint_count += 1

    def record_check(self, result: Dict[str, Any]) -> None:
        """Record a verification check."""
        self.checks.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "result": result,
            }
        )
