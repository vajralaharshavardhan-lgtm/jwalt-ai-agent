"""Human approval gate. CLI implementation for the MVP
(config/settings.yaml approval.channel == "cli").

The gate itself does no persistence -- callers (the orchestrator) log the
decision via RunLogRepository so the audit trail always shows what was
asked and how a human resolved it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


@dataclass
class ApprovalRequest:
    action: str
    company_name: str
    contact_name: str
    details: dict = field(default_factory=dict)


@dataclass
class ApprovalResult:
    decision: ApprovalDecision
    edited_fields: dict | None = None


class ApprovalGate:
    """`non_interactive=True` auto-rejects instead of blocking on stdin --
    used by dry-run mode and by automated tests, neither of which should
    ever hang waiting for a human.
    """

    def __init__(self, *, non_interactive: bool = False):
        self._non_interactive = non_interactive

    def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
        print("\n" + "=" * 60)
        print("ACTION REQUIRES APPROVAL")
        print("=" * 60)
        print(f"Company:  {request.company_name}")
        print(f"Contact:  {request.contact_name}")
        print(f"Action:   {request.action}")
        for key, value in request.details.items():
            print(f"{key}: {value}")
        print("-" * 60)

        if self._non_interactive:
            print("[non-interactive mode: auto-rejecting, no human available to approve]")
            return ApprovalResult(decision=ApprovalDecision.REJECTED)

        while True:
            choice = input("[A]pprove / [R]eject / [E]dit? ").strip().lower()
            if choice in ("a", "approve"):
                return ApprovalResult(decision=ApprovalDecision.APPROVED)
            if choice in ("r", "reject"):
                return ApprovalResult(decision=ApprovalDecision.REJECTED)
            if choice in ("e", "edit"):
                new_subject = input("New subject (blank = keep current): ").strip()
                new_body = input("New body (blank = keep current): ").strip()
                edited = {}
                if new_subject:
                    edited["subject"] = new_subject
                if new_body:
                    edited["body"] = new_body
                return ApprovalResult(decision=ApprovalDecision.EDITED, edited_fields=edited)
            print("Please enter A, R, or E.")
