"""Tests for Session state transitions and persistence."""

import json

import pytest

from chaos_sensei.core.exceptions import SessionError
from chaos_sensei.core.state import SessionStatus


def make_session():
    from chaos_sensei.core.session import Session

    return Session.create(
        session_id="abc123",
        repo_path="/tmp/repo",
        environment="staging",
        provider="kubernetes",
        scenario={"id": "k8s-service-selector-mismatch", "hints": ["a", "b"]},
        snapshot={"kind": "service", "name": "checkout"},
    )


def test_create_starts_in_created_status():
    session = make_session()
    assert session.status == SessionStatus.CREATED
    assert len(session.events) == 1  # snapshot_created event


def test_start_transitions_to_injected():
    session = make_session()
    session.start()
    assert session.status == SessionStatus.INJECTED
    assert session.metadata.started_at is not None


def test_hint_moves_to_under_investigation():
    session = make_session()
    session.start()
    session.increment_hint()
    assert session.status == SessionStatus.UNDER_INVESTIGATION
    assert session.hint_count == 1


def test_mark_fixed_then_rollback_is_legal():
    session = make_session()
    session.start()
    session.mark_fixed("selector restored")
    assert session.status == SessionStatus.FIXED
    session.mark_rolled_back("restored from snapshot")
    assert session.status == SessionStatus.ROLLED_BACK
    assert session.rolled_back is True
    assert session.metadata.ended_at is not None


def test_report_before_injection_is_illegal():
    session = make_session()
    with pytest.raises(SessionError):
        session.mark_fixed("too early")


def test_rollback_after_rollback_is_idempotent_at_state_level():
    session = make_session()
    session.start()
    session.mark_rolled_back("first rollback")
    # same-state transition is legal (no-op), covered by RollbackManager's
    # own idempotency check for the provider-call side.
    session._transition(SessionStatus.ROLLED_BACK)
    assert session.status == SessionStatus.ROLLED_BACK


def test_save_and_load_round_trip(tmp_path):
    from chaos_sensei.core.session import Session

    session = make_session()
    session.start()
    session.increment_hint()

    path = tmp_path / "session.json"
    session.save(path)

    raw = json.loads(path.read_text())
    assert raw["status"] == "under_investigation"

    loaded = Session.from_file(path)
    assert loaded.status == SessionStatus.UNDER_INVESTIGATION
    assert loaded.hint_count == 1
    assert loaded.metadata.session_id == "abc123"
    assert len(loaded.events) >= 3  # snapshot + injection(start) + hint
