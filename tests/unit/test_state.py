"""Tests for the session state machine."""

import pytest

from chaos_sensei.core.exceptions import SessionError
from chaos_sensei.core.state import SessionStatus, assert_transition, can_transition


def test_legal_transition_allowed():
    assert can_transition(SessionStatus.CREATED, SessionStatus.INJECTED) is True
    assert can_transition(SessionStatus.INJECTED, SessionStatus.FIXED) is True
    assert can_transition(SessionStatus.FIXED, SessionStatus.ROLLED_BACK) is True


def test_same_state_is_always_legal():
    assert can_transition(SessionStatus.INJECTED, SessionStatus.INJECTED) is True


def test_illegal_transition_rejected():
    assert can_transition(SessionStatus.CREATED, SessionStatus.FIXED) is False
    assert can_transition(SessionStatus.ROLLED_BACK, SessionStatus.INJECTED) is False


def test_assert_transition_raises_on_illegal_move():
    with pytest.raises(SessionError):
        assert_transition(SessionStatus.ROLLED_BACK, SessionStatus.CREATED)


def test_terminal_states_have_no_outbound_transitions():
    assert can_transition(SessionStatus.ROLLED_BACK, SessionStatus.FIXED) is False
    assert can_transition(SessionStatus.FAILED, SessionStatus.INJECTED) is False
