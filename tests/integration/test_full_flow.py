"""End-to-end regression test for the Phase 1 engine refactor.

Exercises scan -> start -> hint -> check -> rollback -> report against a
fake kubectl (no real cluster) to confirm the refactored engine still
delivers the same user-visible behavior as the pre-refactor monolith for
the one fully-implemented scenario (k8s-service-selector-mismatch).
"""

import json
from pathlib import Path

import pytest

from chaos_sensei.core.engine import ChaosSenseiEngine
from chaos_sensei.core.state import SessionStatus

SERVICE_OBJECT = {
    "kind": "Service",
    "metadata": {"name": "checkout", "namespace": "apps"},
    "spec": {"selector": {"app": "checkout"}},
}


class FakeKubectl:
    """Stands in for tools.kubectl.Kubectl so tests don't need a live cluster.

    Tracks a resourceVersion that bumps on every mutation and rejects
    apply_json() calls carrying a stale one, mirroring the real API
    server's optimistic-concurrency 409 that a raw snapshot replay hits.
    """

    def __init__(self, context=None):
        self.context = context
        self.current_selector = {"app": "checkout"}
        self.resource_version = 100

    def _service_obj(self):
        return {
            "kind": "Service",
            "metadata": {
                "name": "checkout",
                "namespace": "apps",
                "resourceVersion": str(self.resource_version),
                "uid": "fake-uid-1234",
            },
            "spec": {"selector": self.current_selector},
        }

    def get_json(self, args):
        if "deploy,svc,cm,secret" in " ".join(args):
            return {"items": []}
        return self._service_obj()

    def patch_json(self, kind, name, namespace, patch):
        # Real kubectl --type=merge semantics: adds/updates keys, never
        # removes ones already present. Left non-replacing on purpose so a
        # regression to using this for the selector fault would be caught
        # by the leftover-key assertions below instead of passing silently.
        new_selector = patch.get("spec", {}).get("selector", {})
        self.current_selector = {**self.current_selector, **new_selector}
        self.resource_version += 1
        return "service/checkout patched"

    def replace_field(self, kind, name, namespace, path, value):
        if path == "/spec/selector":
            self.current_selector = value
        self.resource_version += 1
        return "service/checkout replaced"

    def apply_json(self, obj):
        from chaos_sensei.core.exceptions import KubernetesToolError

        incoming_rv = obj.get("metadata", {}).get("resourceVersion")
        if incoming_rv and incoming_rv != str(self.resource_version):
            raise KubernetesToolError(
                'Error from server (Conflict): the object has been modified; '
                'please apply your changes to the latest version and try again'
            )
        self.current_selector = obj["spec"]["selector"]
        self.resource_version += 1
        return "service/checkout configured"

    def get_service(self, name, namespace):
        return {
            "kind": "Service",
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"selector": self.current_selector},
        }

    def get_pods(self, namespace, **kwargs):
        return "checkout-abc123   1/1   Running"

    def get_events(self, namespace):
        return ""


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "service.yaml").write_text(
        "apiVersion: v1\nkind: Service\nmetadata:\n  name: checkout\n"
    )
    monkeypatch.chdir(tmp_path)

    from chaos_sensei.providers.kubernetes import provider as provider_module

    monkeypatch.setattr(provider_module, "Kubectl", FakeKubectl)
    return tmp_path


def test_full_lifecycle_matches_pre_refactor_behavior(repo):
    engine = ChaosSenseiEngine(repo, environment="staging")

    # scan
    scan_result = json.loads(engine.scan())
    assert scan_result["detected_providers"][0]["name"] == "kubernetes"

    # start (defaults to the first/only fully-implemented scenario)
    start_result = json.loads(engine.start(scenario_id="k8s-service-selector-mismatch"))
    assert start_result["status"] == "incident_started"
    assert engine.session.status == SessionStatus.INJECTED
    # fault actually applied via the fake kubectl
    provider = engine.providers[0]
    assert provider.kubectl.current_selector != {"app": "checkout"}

    # hint
    hint_text = engine.hint()
    assert isinstance(hint_text, str) and hint_text
    assert engine.session.status == SessionStatus.UNDER_INVESTIGATION

    # check: not fixed yet (selector still broken)
    check_result = engine.check()
    assert "Not fixed" in check_result
    assert engine.session.status == SessionStatus.UNDER_INVESTIGATION

    # simulate the user fixing it directly against the (fake) cluster
    provider.kubectl.current_selector = {"app": "checkout"}
    check_result = engine.check()
    assert "Fixed" in check_result
    assert engine.session.status == SessionStatus.FIXED

    # rollback
    rollback_result = json.loads(engine.rollback())
    assert rollback_result["rolled_back"] is True
    assert engine.session.status == SessionStatus.ROLLED_BACK

    # rollback again is idempotent, does not raise
    second_rollback = json.loads(engine.rollback())
    assert second_rollback.get("already_done") is True

    # report
    report_text = engine.report()
    assert "Chaos Sensei Incident Report" in report_text
    assert Path(".chaos-sensei/report.md").exists()


def test_illegal_state_transition_is_rejected(repo):
    from chaos_sensei.core.exceptions import SessionError

    engine = ChaosSenseiEngine(repo, environment="staging")
    engine.start(scenario_id="k8s-service-selector-mismatch")

    # forcing report/mark_fixed twice in a row from a terminal state must fail
    engine.rollback()
    with pytest.raises(SessionError):
        engine.session.mark_fixed("too late, already rolled back")


def test_inject_and_rollback_fully_replace_selector_no_leftover_keys(repo):
    """Regression test for a real bug found via live-cluster testing: merge
    patches (kubectl patch --type=merge / kubectl apply) add or update map
    keys but never remove ones already present. A merge-based injector left
    the real selector labels intact alongside the broken one (so it worked
    by accident, via AND-match semantics), and a merge-based rollback then
    couldn't strip the leftover broken key back out - "rollback complete"
    was reported while the service stayed down. Both injection and rollback
    now use JSON Patch replace (see Kubectl.replace_field) and must leave
    the selector as *exactly* the expected value, with nothing left over
    from the previous state.
    """
    engine = ChaosSenseiEngine(repo, environment="staging")
    provider = None

    engine.start(scenario_id="k8s-service-selector-mismatch")
    provider = engine.providers[0]

    # injected selector must be exactly the broken one-key value - no
    # leftover "app": "checkout" from before the fault
    assert provider.kubectl.current_selector == {
        "app": "chaos-sensei-broken-selector-checkout"
    }

    engine.rollback()

    # restored selector must be exactly the original value - no leftover
    # "app": "chaos-sensei-broken-selector-checkout" from the fault
    assert provider.kubectl.current_selector == {"app": "checkout"}
