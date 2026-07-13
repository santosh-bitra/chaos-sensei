"""Rollback orchestration, separated from engine.py so cleanup logic is
reviewed and tested as its own unit rather than buried in the main flow.
"""

import logging
from typing import Any, Dict

from chaos_sensei.core.events import EventType
from chaos_sensei.core.session import Session
from chaos_sensei.core.state import SessionStatus
from chaos_sensei.providers.base import Provider

logger = logging.getLogger(__name__)


class RollbackManager:
    """Restores original system state and keeps the session in sync."""

    def rollback(self, provider: Provider, session: Session) -> Dict[str, Any]:
        """
        Roll back a session's fault injection via its provider.

        Idempotent: calling this on an already-rolled-back session is a
        no-op that reports success instead of re-running provider.rollback().
        """
        if session.status == SessionStatus.ROLLED_BACK:
            logger.info(f"Session {session.metadata.session_id} already rolled back, skipping")
            return {"rolled_back": True, "details": "Already rolled back", "already_done": True}

        session.add_event(EventType.ROLLBACK_STARTED)

        result = provider.rollback(session.scenario, session.snapshot)
        session.mark_rolled_back(result.get("details", ""))

        logger.info(f"Session {session.metadata.session_id} rolled back")
        return result

    def verify_rollback(self, provider: Provider, session: Session) -> Dict[str, Any]:
        """
        Optionally confirm the rollback actually restored a healthy state.

        Providers aren't required to implement verify_rollback(); if they
        don't, we report the rollback's own result instead of failing.
        """
        verify = getattr(provider, "verify_rollback", None)
        if callable(verify):
            return verify(session.scenario, session.snapshot)

        return {"verified": session.status == SessionStatus.ROLLED_BACK, "details": "Provider does not implement verify_rollback()"}
