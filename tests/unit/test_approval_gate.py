from src.approval.gate import ApprovalDecision, ApprovalGate, ApprovalRequest


def make_request() -> ApprovalRequest:
    return ApprovalRequest(
        action="Send outreach email",
        company_name="ABC Hotels",
        contact_name="John Smith",
        details={"Subject": "Hello", "Body": "..."},
    )


class TestApprovalGateNonInteractive:
    def test_auto_rejects_without_blocking(self):
        gate = ApprovalGate(non_interactive=True)
        result = gate.request_approval(make_request())
        assert result.decision == ApprovalDecision.REJECTED
        assert result.edited_fields is None


class TestApprovalGateInteractive:
    def test_approve(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "a")
        gate = ApprovalGate(non_interactive=False)
        result = gate.request_approval(make_request())
        assert result.decision == ApprovalDecision.APPROVED

    def test_reject(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "r")
        gate = ApprovalGate(non_interactive=False)
        result = gate.request_approval(make_request())
        assert result.decision == ApprovalDecision.REJECTED

    def test_edit_collects_new_fields(self, monkeypatch):
        responses = iter(["e", "New subject", "New body"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        gate = ApprovalGate(non_interactive=False)
        result = gate.request_approval(make_request())
        assert result.decision == ApprovalDecision.EDITED
        assert result.edited_fields == {"subject": "New subject", "body": "New body"}

    def test_invalid_input_reprompts(self, monkeypatch):
        responses = iter(["banana", "a"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        gate = ApprovalGate(non_interactive=False)
        result = gate.request_approval(make_request())
        assert result.decision == ApprovalDecision.APPROVED
